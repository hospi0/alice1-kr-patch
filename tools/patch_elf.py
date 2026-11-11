# -*- coding: utf-8 -*-
"""앨리스 1 alice.ppu.elf 한글(CP949 2바이트) 글꼴 훅 (2026-11-11 PoC)

  python tools/patch_elf.py <원본.elf> <출력.elf>

글꼴 구조체(0x1510 B): +0x000 간접표 int[256] · +0x400 칸 {x,y,w,h}×256 (텍스처 좌표 = 화소/256, y·h 는 ×aspect)
                       +0x1500 height · +0x1504 aspect · +0x1508 텍스처
원래 코드: 텍스처 폭 256 가정 → 칸 w 하나를 «텍스처 폭»과 «화면 폭(w×256)»에 같이 쓴다.
훅 규약(글꼴 파일의 안 쓰는 칸에 매개변수):
  칸 255 = {K, -, -, -}      K = 큰 텍스처 폭/256 (파일 값 K×256). 0 이면 1(원래 글꼴은 그대로 동작)
  칸 254 = {u0, v0, cw, ch}  한글 격자 원점·간격(텍스처 좌표)
  칸 253 = {gw, gh, -, -}    한글 글자 칸 크기(텍스처 좌표)
한글 = CP949 완성형 2바이트(선행 B0~C8, 후행 A1~FE) → 음절 번호 = (선행−B0)×94 + (후행−A1) → 열 = 번호&63, 행 = 번호>>6
훅 4곳 — 원래 명령어가 예상과 같을 때만 덮는다. ⛔공간→원래 코드는 1MB 넘게 떨어져 조건 분기(±32KB)로 못 감 → 조건 뒤집고 b.
⛔addi rD, r0, x 의 r0 은 «0» 이다(mr 로 옮긴 뒤 뺄 것).
  A  0x1AF7FC 그리기: 바이트 판별(한글이면 r29 = 0x10000|번호, 글자 위치 r30 한 칸 더)
  B  0x1AF82C 그리기: 칸 {x,y,w,h,화면폭=w×K} 를 r1−0x80(레드 존)에 만들고 r9 = 그 주소
     (+ 0x1AF838/840/848 의 r9 계산을 nop, 0x1AF864 lfs f11,8(r9) → 0x10(r9) = 화면폭)
  M1 0x1AF498 문자열 폭  M2 0x1C55BC 여러 줄 최대 폭 — 한글 폭(gw×K), 영문 폭 ×K
  M3 0x1C5698 글자 하나 폭(자막 줄바꿈이 바이트마다 부름) — K 글꼴에서 0xA1~0xFE 바이트 = 한글 폭 절반, 영문 ×K
코드 공간: 세그먼트 0 끝 0x33F768 ~ 0x340000 (0) — 세그먼트 크기를 늘려 씀.
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keystone import Ks, KS_ARCH_PPC, KS_MODE_PPC64, KS_MODE_BIG_ENDIAN

CAVE = 0x33F780
SEG_END = 0x340000

EXPECT = {                 # 원래 명령어(어셈블리 문장 → keystone 인코딩과 파일 바이트 대조)
    0x1AF7FC: 'rlwinm r0, r0, 2, 22, 29',
    0x1AF800: 'lwzx r29, r18, r0',
    0x1AF82C: 'slwi r9, r29, 4',
    0x1AF838: 'addi r9, r9, 0x400',
    0x1AF840: 'add r9, r20, r9',
    0x1AF848: 'clrldi r9, r9, 32',
    0x1AF864: 'lfs f11, 8(r9)',
    0x1AF498: 'lwzx r0, r11, r9',
    0x1C55BC: 'rlwinm r9, r0, 2, 22, 29',
    0x1C5698: 'lwz r10, 0x14(r3)',
}

ks = Ks(KS_ARCH_PPC, KS_MODE_PPC64 | KS_MODE_BIG_ENDIAN)


def _norm(src):
    """keystone 표기: r3 → %r3 · f1 → %f1 · cr7 → 7"""
    import re
    src = re.sub(r'\bcr([0-7])\b', r'\1', src)
    src = re.sub(r'\br([0-9]{1,2})\b', r'%r\1', src)
    src = re.sub(r'\bf([0-9]{1,2})\b', r'%f\1', src)
    return src


def asm(src, addr):
    """라벨을 직접 절대 주소로 풀고 명령을 «한 줄씩» 그 주소에서 어셈블한다.
    ⛔keystone 은 라벨이 섞인 블록에서 절대 주소 분기(b 0x…)를 «목표+라벨 위치»로 잘못 만든다(실측)."""
    import re
    lines = [l.split('#')[0].strip() for l in src.split('\n')]
    lines = [l for l in lines if l]
    labels, pc = {}, addr
    for l in lines:
        if l.endswith(':'):
            labels[l[:-1]] = pc
        else:
            pc += 4
    out, pc = bytearray(), addr
    for l in lines:
        if l.endswith(':'):
            continue
        for name, v in labels.items():
            l = re.sub(r'(?<![\w.])' + re.escape(name) + r'(?![\w])', '0x%x' % v, l)
        enc, _ = ks.asm(_norm(l), pc)
        assert len(enc) == 4, l
        out += bytes(enc); pc += 4
    return bytes(out)


def KOREAN_CHECK(lead, trailsrc, nolabel):
    # lead 레지스터가 B0..C8 이고 trailsrc 로 읽은 r12 가 A1..FE 인지
    return f"""
    cmplwi cr7, {lead}, 0xb0
    blt cr7, {nolabel}
    cmplwi cr7, {lead}, 0xc8
    bgt cr7, {nolabel}
    {trailsrc}
    cmplwi cr7, r12, 0xa1
    blt cr7, {nolabel}
    cmplwi cr7, r12, 0xfe
    bgt cr7, {nolabel}
"""


def build_cave(base):
    parts = []
    addr = base
    lab = {}

    # ── A : 그리기 바이트 판별 ──
    lab['A'] = addr
    srcA = KOREAN_CHECK('r0', "add r11, r22, r30\n    clrldi r11, r11, 32\n    lbz r12, 1(r11)", 'A_ascii') + f"""
    mr r11, r0
    addi r11, r11, -0xb0
    mulli r11, r11, 94
    addi r12, r12, -0xa1
    add r29, r11, r12
    oris r29, r29, 1
    addi r30, r30, 1
    b 0x1af80c
A_ascii:
    rlwinm r0, r0, 2, 22, 29
    lwzx r29, r18, r0
    cmpwi cr7, r29, -1
    bne cr7, A_found
    b 0x1afa14
A_found:
    b 0x1af80c
"""
    a = asm(srcA, addr); parts.append(a); addr += len(a)

    # ── B : 칸 + 화면폭 → 레드 존 ──
    addr = (addr + 15) & ~15
    lab['B'] = addr
    srcB = """
    lfs f13, 0x13f0(r20)
    lfs f12, -0xb58(r2)
    fcmpu cr0, f13, f12
    bne cr0, B_k
    lis r12, 0x3f80
    stw r12, -0x50(r1)
    lfs f13, -0x50(r1)
B_k:
    andis. r11, r29, 1
    beq cr0, B_ascii
    clrlwi r11, r29, 16
    clrlwi r12, r11, 26
    srwi r11, r11, 6
    std r12, -0x60(r1)
    lfd f0, -0x60(r1)
    fcfid f0, f0
    frsp f0, f0
    std r11, -0x58(r1)
    lfd f11, -0x58(r1)
    fcfid f11, f11
    frsp f11, f11
    lfs f12, 0x13e8(r20)
    fmuls f0, f0, f12
    lfs f12, 0x13e0(r20)
    fadds f0, f0, f12
    stfs f0, -0x80(r1)
    lfs f12, 0x13ec(r20)
    fmuls f11, f11, f12
    lfs f12, 0x13e4(r20)
    fadds f11, f11, f12
    stfs f11, -0x7c(r1)
    lfs f0, 0x13d0(r20)
    stfs f0, -0x78(r1)
    lfs f12, 0x13d4(r20)
    stfs f12, -0x74(r1)
    b B_ws
B_ascii:
    slwi r11, r29, 4
    add r11, r11, r20
    clrldi r11, r11, 32
    lfs f0, 0x400(r11)
    stfs f0, -0x80(r1)
    lfs f0, 0x404(r11)
    stfs f0, -0x7c(r1)
    lfs f0, 0x408(r11)
    stfs f0, -0x78(r1)
    lfs f0, 0x40c(r11)
    stfs f0, -0x74(r1)
B_ws:
    lfs f0, -0x78(r1)
    fmuls f0, f0, f13
    stfs f0, -0x70(r1)
    addi r9, r1, -0x80
    b 0x1af830
"""
    b = asm(srcB, addr); parts.append(b'\0' * (addr - base - sum(len(p) for p in parts)) + b); addr += len(b)

    # ── M1 : 문자열 폭 ──
    addr = (addr + 15) & ~15
    lab['M1'] = addr
    srcM1 = KOREAN_CHECK('r0', 'lbz r12, 0(r10)', 'M1_a') + """
    lfs f0, 0x13d0(r11)
    addi r10, r10, 1
    b M1_k
M1_a:
    lwzx r0, r11, r9
    cmpwi cr7, r0, -1
    bne cr7, M1_ok
    b 0x1af4bc
M1_ok:
    slwi r12, r0, 4
    add r12, r12, r11
    clrldi r12, r12, 32
    lfs f0, 0x408(r12)
M1_k:
    lfs f12, 0x13f0(r11)
    lfs f11, -0xb58(r2)
    fcmpu cr7, f12, f11
    beq cr7, M1_n
    fmuls f0, f0, f12
M1_n:
    fadds f1, f1, f0
    b 0x1af4bc
"""
    m1 = asm(srcM1, addr); parts.append(b'\0' * (addr - base - sum(len(p) for p in parts)) + m1); addr += len(m1)

    # ── M2 : 여러 줄 최대 폭 ──
    addr = (addr + 15) & ~15
    lab['M2'] = addr
    srcM2 = KOREAN_CHECK('r0', 'lbz r12, 1(r9)', 'M2_a') + """
    lfs f0, 0x13d0(r8)
    addi r11, r11, 1
    b M2_k
M2_a:
    rlwinm r9, r0, 2, 22, 29
    lwzx r0, r8, r9
    cmplwi cr7, r0, 0xff
    ble cr7, M2_ok
    b 0x1c55ec
M2_ok:
    slwi r9, r0, 4
    add r9, r9, r8
    clrldi r9, r9, 32
    lfs f0, 0x408(r9)
M2_k:
    lfs f10, 0x13f0(r8)
    lfs f9, -0xb58(r2)
    fcmpu cr7, f10, f9
    beq cr7, M2_n
    fmuls f0, f0, f10
M2_n:
    fadds f13, f13, f0
    fcmpu cr7, f13, f12
    ble cr7, M2_le
    b 0x1c5650
M2_le:
    b 0x1c55ec
"""
    m2 = asm(srcM2, addr); parts.append(b'\0' * (addr - base - sum(len(p) for p in parts)) + m2); addr += len(m2)

    # ── M3 : 글자 하나 폭 (자막 줄바꿈 0x8FE10·0x8FF30 등이 바이트마다 부른다) ──
    #   K 있는 글꼴: 0xA1~0xFE 바이트 = 한글 폭의 절반(선행+후행 = 한 글자) · 영문 = w×K
    addr = (addr + 15) & ~15
    lab['M3'] = addr
    srcM3 = """
    lwz r10, 0x14(r3)
    lfs f12, 0x13f0(r10)
    lfs f11, -0xb58(r2)
    fcmpu cr7, f12, f11
    bne cr7, M3_hasK
    lis r12, 0x3f80
    stw r12, -0x20(r1)
    lfs f12, -0x20(r1)
    b M3_chk
M3_hasK:
    clrlwi r12, r4, 24
    cmplwi cr7, r12, 0xa1
    blt cr7, M3_chk
    cmplwi cr7, r12, 0xfe
    bgt cr7, M3_chk
    lfs f0, 0x13d0(r10)
    fmuls f0, f0, f12
    lis r12, 0x3f00
    stw r12, -0x20(r1)
    lfs f11, -0x20(r1)
    fmuls f0, f0, f11
    b M3_conv
M3_chk:
    rlwinm r11, r4, 2, 22, 29
    lwzx r0, r10, r11
    cmplwi cr7, r0, 0xff
    ble cr7, M3_ok
    b 0x1c56fc
M3_ok:
    slwi r9, r0, 4
    add r9, r9, r10
    clrldi r9, r9, 32
    lfs f0, 0x408(r9)
    fmuls f0, f0, f12
M3_conv:
    lfs f13, -0x64c(r2)
    fmuls f0, f0, f13
    addi r9, r1, -0x10
    fctiwz f0, f0
    stfiwx f0, 0, r9
    lwz r3, -0x10(r1)
    extsw r3, r3
    blr
"""
    m3 = asm(srcM3, addr); parts.append(b'\0' * (addr - base - sum(len(p) for p in parts)) + m3); addr += len(m3)
    return b''.join(parts), lab, addr


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src, dst = sys.argv[1], sys.argv[2]
    d = bytearray(open(src, 'rb').read())
    phoff, = struct.unpack_from('>Q', d, 0x20)
    phentsize, phnum = struct.unpack_from('>HH', d, 0x36)
    # 세그먼트 0
    p0 = phoff
    typ, flags, off, va, pa, fsz, msz, al = struct.unpack_from('>IIQQQQQQ', d, p0)
    assert typ == 1 and va == 0x10000 and off == 0 and fsz == msz == 0x32F768, '세그먼트 0 이 예상과 다름'
    f2o = lambda a: a - va + off
    for a, w in EXPECT.items():
        want = asm(w, a)
        got = bytes(d[f2o(a):f2o(a) + 4])
        assert got == want, '원래 명령어 다름 0x%X: %s != %s (%s)' % (a, got.hex(), want.hex(), w)
    cave, lab, end = build_cave(CAVE)
    assert end <= SEG_END, '코드 공간 부족'
    assert set(d[f2o(CAVE):f2o(CAVE) + len(cave)]) <= {0}
    d[f2o(CAVE):f2o(CAVE) + len(cave)] = cave
    newsz = end - va
    struct.pack_into('>QQ', d, p0 + 0x20, newsz, newsz)
    # 훅 분기
    def put(a, src):
        enc = asm(src, a); d[f2o(a):f2o(a) + len(enc)] = enc
    put(0x1AF7FC, 'b 0x%x' % lab['A'])
    put(0x1AF82C, 'b 0x%x' % lab['B'])
    for a in (0x1AF838, 0x1AF840, 0x1AF848):
        put(a, 'nop')
    put(0x1AF864, 'lfs f11, 0x10(r9)')
    put(0x1AF498, 'b 0x%x' % lab['M1'])
    put(0x1C55BC, 'b 0x%x' % lab['M2'])
    put(0x1C5698, 'b 0x%x' % lab['M3'])
    import sysmsg
    print(sysmsg.apply(d))
    open(dst, 'wb').write(d)
    print('훅 코드 %d B @0x%X~0x%X · A 0x%X B 0x%X M1 0x%X M2 0x%X M3 0x%X · 세그먼트0 크기 0x%X'
          % (len(cave), CAVE, end, lab['A'], lab['B'], lab['M1'], lab['M2'], lab['M3'], newsz))


if __name__ == '__main__':
    main()
