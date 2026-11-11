# -*- coding: utf-8 -*-
"""앨리스 1 asrafel 한글 글꼴 (2026-11-11 PoC) — tools/patch_elf.py 훅과 짝
  from build_font import build ; files = build(pak0경로)  → {pk3 안 경로: 바이트}

텍스처 2048×2048 RGBA (TGA 32bpp 무압축·원점 아래 — 원본과 같은 형식)
  (0,0)~(256,256)  원본 영문 asrafel 그대로
  (0,256)~          한글 KS X 1001 완성형 2,350자 — 음절 번호 n = (선행−B0)×94 + (후행−A1)
                    열 = n & 63, 행 = n >> 6 · 간격 32×32 · 글자 칸 GW×30 (위 0~20줄에 잉크, 영문 대문자 높이에 맞춤)
정의(.ritualfont): 글꼴이 칸 값에 1/256 을 곱해 텍스처 좌표로 쓴다 →
  영문 칸 = 원래 화소 ÷ 8 (2048 = 256×8)
  칸 255 = {K×256 = 2048, 0,0,0}  · 칸 254 = {0, 256/8, 32/8, 32/8}  · 칸 253 = {GW/8, 30/8, 0,0}
흰 RGB + 알파(글자 모양) — 원본과 같음. 한글 원도: Noto Serif KR(OFL).
"""
import io, re, zipfile
from PIL import Image, ImageDraw, ImageFont

TW = 2048
CELL = 32
GW = 20
GH = 30
KFONT = r'C:\claude\utils\font\gowunbatang\GowunBatang-Bold.ttf'  # 2026-11-11 하스피 선택(후보 B)
KSIZE = 20


def ks_syllables():
    out = []
    for lead in range(0xB0, 0xC9):
        for trail in range(0xA1, 0xFF):
            out.append(bytes([lead, trail]).decode('cp949'))
    assert len(out) == 2350
    return out


def tga_bytes(im):
    w, h = im.size
    hdr = bytes([0, 0, 2]) + bytes(9) + w.to_bytes(2, 'little') + h.to_bytes(2, 'little') + bytes([32, 0x08])
    px = im.transpose(Image.FLIP_TOP_BOTTOM).tobytes('raw', 'BGRA')
    return hdr + px


def render_korean(canvas):
    font = ImageFont.truetype(KFONT, KSIZE)
    try:
        font.set_variation_by_name('Regular')
    except Exception:
        pass
    # 잉크 위쪽을 0 근처로: 기준 글자 '한' 의 잉크 범위로 세로 위치를 정한다
    ref = font.getbbox('한')
    dy = -ref[1]
    for n, ch in enumerate(ks_syllables()):
        col, row = n & 63, n >> 6
        x0, y0 = col * CELL, 256 + row * CELL
        g = Image.new('L', (GW, GH), 0)
        d = ImageDraw.Draw(g)
        bb = font.getbbox(ch)
        dx = (GW - (bb[2] - bb[0])) // 2 - bb[0]
        d.text((dx, dy), ch, font=font, fill=255)
        rgba = Image.merge('RGBA', (Image.new('L', g.size, 255),) * 3 + (g,))
        canvas.paste(rgba, (x0, y0))


def ritualfont(orig_text):
    head, rest = orig_text.split('locations', 1)
    locs = [list(map(float, m.groups())) for m in re.finditer(r'\{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\}', rest)]
    assert len(locs) == 256
    assert re.search(r'aspect\s+1\.0', head), 'aspect 1 가정'
    new = [[v / 8.0 for v in l] for l in locs]
    assert all(v == 0 for l in locs[253:] for v in l), '칸 253~255 가 비어 있지 않다'
    new[255] = [TW * 1.0, 0, 0, 0]
    new[254] = [0, 256 / 8.0, CELL / 8.0, CELL / 8.0]
    new[253] = [GW / 8.0, GH / 8.0, 0, 0]
    body = 'locations { \r\n' + ''.join('{ %.8f %.8f %.8f %.8f } \r\n' % tuple(l) for l in new) + '}\r\n'
    return head + body


def build(pak0):
    z = zipfile.ZipFile(pak0)
    orig = Image.open(io.BytesIO(z.read('gfx/fonts/asrafel.tga'))).convert('RGBA')
    assert orig.size == (256, 256)
    canvas = Image.new('RGBA', (TW, TW), (255, 255, 255, 0))
    canvas.paste(orig, (0, 0))
    render_korean(canvas)
    rf = ritualfont(z.read('fonts/asrafel.ritualfont').decode('latin1'))
    return {
        'fonts/asrafel.ritualfont': rf.encode('latin1'),
        'gfx/fonts/asrafel.tga': tga_bytes(canvas),
    }, canvas
