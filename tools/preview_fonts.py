# -*- coding: utf-8 -*-
"""한글 글꼴 후보 비교 미리보기 (2026-11-11) → work/preview/글꼴후보_비교.png
글자를 텍스처 크기(칸 높이 30)로 그린 뒤 게임처럼 쌍선형 3배 확대 · 양피지 바탕 · 진한 갈색 · 같은 줄에 원본 asrafel 영문.
python tools/preview_fonts.py
"""
import os, re, sys, zipfile, io
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAK0 = os.path.join(ROOT, 'work', 'pkg', 'USRDIR', 'UNREALENGINE3', 'Alice1', 'bin', 'base', 'pak0.pk3')
F = r'C:\claude\utils\font'
CANDS = [
    ('지금: Noto Serif KR 22', r'C:\Windows\Fonts\NotoSerifKR-VF.ttf', 22, 'Regular'),
    ('A: Noto Serif KR SemiBold 20', r'C:\Windows\Fonts\NotoSerifKR-VF.ttf', 20, 'SemiBold'),
    ('B: 고운바탕 Bold 20', F + r'\gowunbatang\GowunBatang-Bold.ttf', 20, None),
    ('C: 나눔명조 Bold 20', F + r'\nanum-myeongjo\NanumMyeongjoBold.ttf', 20, None),
    ('D: 송명 20', F + r'\songmyung\SongMyung-Regular.ttf', 20, None),
]
KO = '꽤 꾀죄죄해졌구나, 고양이. 그래도 네 웃음은 위안이 돼.'
EN = 'Alice, we are late!'
SCALE = 3


def asrafel():
    z = zipfile.ZipFile(PAK0)
    t = z.read('fonts/asrafel.ritualfont').decode('latin1')
    ind = [int(x) for x in re.findall(r'-?\d+', re.sub(r'//[^\n]*', '', re.search(r'indirections\s*\{(.*?)\}', t, re.S).group(1)))]
    locs = [tuple(map(float, m.groups())) for m in re.finditer(r'\{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\}', t[t.index('locations'):])]
    im = Image.open(io.BytesIO(z.read('gfx/fonts/asrafel.tga'))).convert('RGBA')
    return ind, locs, im.split()[3]


def line(fontpath, size, var, ind, locs, atlas):
    font = ImageFont.truetype(fontpath, size)
    if var:
        try:
            font.set_variation_by_name(var)
        except Exception:
            pass
    dy = -font.getbbox('한')[1]
    gw = size
    W = len(KO) * gw + 400
    a = Image.new('L', (W, 30), 0)
    x = 0
    for ch in KO:
        if ch == ' ':
            x += 7; continue
        if ord(ch) < 128:
            i = ind[ord(ch)]
            if i >= 0:
                lx, ly, lw, lh = locs[i]
                a.paste(atlas.crop((int(lx), int(ly), int(lx + lw + .99), int(ly + lh))), (x, 0)); x += int(round(lw))
            continue
        g = Image.new('L', (gw, 30), 0)
        d = ImageDraw.Draw(g)
        bb = font.getbbox(ch)
        d.text(((gw - (bb[2] - bb[0])) // 2 - bb[0], dy), ch, font=font, fill=255)
        a.paste(g, (x, 0)); x += gw
    x += 10
    for ch in EN:
        i = ind[ord(ch)]
        if i < 0:
            continue
        lx, ly, lw, lh = locs[i]
        a.paste(atlas.crop((int(lx), int(ly), int(lx + lw + .99), int(ly + lh))), (x, 0)); x += int(round(lw))
    a = a.crop((0, 0, x + 4, 30)).resize(((x + 4) * SCALE, 30 * SCALE), Image.BILINEAR)
    bg = Image.new('RGB', a.size, (214, 196, 160))
    ink = Image.new('RGB', a.size, (52, 36, 24))
    bg.paste(ink, (0, 0), a)
    return bg


def main():
    ind, locs, atlas = asrafel()
    rows = [(lab, line(p, s, v, ind, locs, atlas)) for lab, p, s, v in CANDS]
    lf = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 22)
    W = max(r.width for _, r in rows) + 20
    H = sum(r.height + 44 for _, r in rows) + 10
    sheet = Image.new('RGB', (W, H), (40, 40, 48))
    d = ImageDraw.Draw(sheet); y = 8
    for lab, r in rows:
        d.text((10, y), lab, font=lf, fill=(255, 230, 120)); y += 32
        sheet.paste(r, (10, y)); y += r.height + 12
    os.makedirs(os.path.join(ROOT, 'work', 'preview'), exist_ok=True)
    out = os.path.join(ROOT, 'work', 'preview', '글꼴후보_비교.png')
    sheet.save(out)
    print(out)


if __name__ == '__main__':
    main()
