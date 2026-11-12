# -*- coding: utf-8 -*-
"""앨리스 1 ELF 시스템 메시지(저장·불러오기 확인창) 한글 (2026-11-11) — patch_elf.py 가 부른다

구조: 0xAD1E8(번호, r4, r5, r6, r7) 가 메시지 표[번호] 에 언어별 문자열 4개를 등록 — r7 = 영어.
      문자열 주소는 TOC 칸(r2 상대 lwz)에 들어 있다 → 영어 TOC 칸 값만 한글 주소로 바꾼다.
한글 놓을 곳: 바꾸는 메시지들의 FR·DE·ES 문자열 바이트(영어 쓸 때는 안 읽힘) — 각 문자열은 TOC 칸 하나에서만 가리킴(검산).
예외: 번호 6·7 은 r7 = [TOC 0x358EC0] 값과 그 +0x40 (코드가 더함) → 칸을 못 바꾸고 «제자리» (원래 바이트 범위 안).
번역: work/ko/sysmsg.tsv (번호 \\t 한글, «\\n» = 줄바꿈) · CP949 · 글꼴 밖 글자 막음
"""
import os, re, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 번호: (영어 TOC 칸, [FR·DE·ES TOC 칸], 영어 앞부분 — 원본 대조)
ROWS = {
    0x26: (0x358edc, [0x358ed0, 0x358ed4, 0x358ed8], 'Saving...'),
    0x27: (0x358eec, [0x358ee0, 0x358ee4, 0x358ee8], 'Loading'),
    0x28: (0x358efc, [0x358ef0, 0x358ef4, 0x358ef8], 'Deleting'),
    0x17: (0x358f0c, [0x358f00, 0x358f04, 0x358f08], 'An error occurred while deleting'),
    0x8: (0x358f1c, [0x358f10, 0x358f14, 0x358f18], 'Warning: \nStarting a new game will overwrite the existing autosave. '),
    0x9: (0x358f2c, [0x358f20, 0x358f24, 0x358f28], 'Warning: \nStarting a new game will overwrite the existing autosave, '),
    0xa: (0x358f3c, [0x358f30, 0x358f34, 0x358f38], 'Warning: \nStarting a new game will lose'),
    0xb: (0x358f4c, [0x358f40, 0x358f44, 0x358f48], 'Warning: \nThis game autosaves'),
    0xc: (0x358f5c, [0x358f50, 0x358f54, 0x358f58], 'Loading will cause'),
    0x1c: (0x358f6c, [0x358f60, 0x358f64, 0x358f68], 'Quiting will cause'),
    0xf: (0x358f7c, [0x358f70, 0x358f74, 0x358f78], 'This will overwrite'),
    0x18: (0x358f8c, [0x358f80, 0x358f84, 0x358f88], 'The selected device'),
    0x11: (0x358f9c, [0x358f90, 0x358f94, 0x358f98], 'This slot is restricted'),
    0x12: (0x358fac, [0x358fa0, 0x358fa4, 0x358fa8], 'You must be in a game'),
    0x13: (0x358fbc, [0x358fb0, 0x358fb4, 0x358fb8], "You can't save when dead"),
    0x14: (0x358fcc, [0x358fc0, 0x358fc4, 0x358fc8], 'You must be signed in to save.'),
    0x1b: (0x358fd4, [0x358fd0], 'You must be signed in to change'),
    0x1a: (0x358fe4, [0x358fd8, 0x358fdc, 0x358fe0], 'You must sign-in to a non-guest'),
    0x1d: (0x358ff4, [0x358fe8, 0x358fec, 0x358ff0], 'You are not signed in.'),
    0x1e: (0x359004, [0x358ff8, 0x358ffc, 0x359000], 'No Storage Device was chosen.'),
    0x21: (0x359014, [0x359008, 0x35900c, 0x359010], 'An error occurred while trying to enumerate save games. No'),
    0x22: (0x359024, [0x359018, 0x35901c, 0x359020], 'An error occurred while trying to enumerate save games. Conf'),
    0x2b: (0x359034, [0x359028, 0x35902c, 0x359030], 'Please Wait'),
    0x1f: (0x359044, [0x359038, 0x35903c, 0x359040], 'The previously selected'),
    0x20: (0x359054, [0x359048, 0x35904c, 0x359050], 'You have returned'),
    0x16: (0x359064, [0x359058, 0x35905c, 0x359060], 'Are you sure you want to delete'),
    0x19: (0x359074, [0x359068, 0x35906c, 0x359070], 'Cancel? All changes'),
    0x15: (0x359084, [0x359078, 0x35907c, 0x359080], 'Not enough space'),
    0x10: (0x359094, [0x359088, 0x35908c, 0x359090], 'An error prevented the file from saving'),
    0xe: (0x3590a4, [0x359098, 0x35909c, 0x3590a0], 'The save data is corrupt'),
    0xd: (0x3590b4, [0x3590a8, 0x3590ac, 0x3590b0], 'An error prevented the file from loading'),
    0x23: (0x3590b8, [0x3590bc], 'OK'),
    0x25: (0x3590cc, [0x3590c0, 0x3590c4, 0x3590c8], 'Yes'),
    0x24: (0x3590d8, [0x3590d0, 0x3590d4], 'No'),
    0x2c: (0x3590e8, [0x3590dc, 0x3590e0, 0x3590e4], 'Empty Savegame'),
    0x29: (0x3590f8, [0x3590ec, 0x3590f0, 0x3590f4], 'Save Slot'),
    0x0: (0x359108, [0x3590fc, 0x359100, 0x359104], 'Please reconnect the controller'),
}
INPLACE = {0x6: (0x2fea60, 'One or more save games is corrupt'), 0x7: (0x2feaa0, 'Error %d KB free space')}
KS = set(bytes([a, b]).decode('cp949') for a in range(0xB0, 0xC9) for b in range(0xA1, 0xFF))


def load_ko():
    out = {}
    for l in open(os.path.join(ROOT, 'work', 'ko', 'sysmsg.tsv'), encoding='utf-8').read().splitlines():
        if not l.strip() or l.startswith('#'):
            continue
        a, b = l.split('\t')
        k = re.sub(r' *\\n', ' \n', b)   # 원본처럼 줄바꿈 앞에 공백 — 게임은 «공백으로 끝난 낱말»만 찍어 줄 끝 낱말이 사라짐(2026-11-12 실기)
        bad = [c for c in k if ord(c) >= 0x80 and c not in KS]
        assert not bad, '글꼴 밖 글자 %s %r' % (a, bad)
        out[int(a, 16)] = k.encode('cp949')
    return out


def apply(d):
    """d = ELF bytearray (제자리 수정) · 반환 = 보고 문자열"""
    phoff, = struct.unpack_from('>Q', d, 0x20)
    phnum, = struct.unpack_from('>H', d, 0x38)
    segs = []
    for i in range(phnum):
        typ, fl, off, va, pa, fsz, msz, al = struct.unpack_from('>IIQQQQQQ', d, phoff + i * 0x38)
        if typ == 1:
            segs.append((va, off, fsz, fl))

    def o(a):
        for va, off, fsz, _ in segs:
            if va <= a < va + fsz:
                return a - va + off
        raise ValueError(hex(a))

    u32 = lambda a: struct.unpack_from('>I', d, o(a))[0]

    def cstr(a):
        p = o(a); e = d.index(b'\0', p); return bytes(d[p:e])

    ko = load_ko()
    assert set(ko) == set(ROWS) | set(INPLACE), '번호 다름 %s' % sorted(set(ko) ^ (set(ROWS) | set(INPLACE)))
    en_strs = {u32(en) for en, _, _ in ROWS.values()}
    # 빈 자리 모으기
    pool = []
    for no, (en, oth, head) in ROWS.items():
        got = cstr(u32(en)).decode('latin1')
        assert got.startswith(head), '영어 다름 0x%x: %r' % (no, got[:40])
        for s in oth:
            a = u32(s)
            if a in en_strs:
                continue
            pk = struct.pack('>I', a)       # 데이터 세그먼트(실행 안 되는 것)만 — 코드에 우연히 같은 4바이트가 있다
            n = sum(bytes(d[off:off + fsz]).count(pk) for va, off, fsz, fl in segs if not fl & 1)
            assert n == 1, '문자열 0x%x 를 %d곳이 가리킴' % (a, n)
            pool.append((a, len(cstr(a)) + 1))
    pool = sorted(set(pool))
    # 같은 주소 겹침 없이 — 이어진 자리는 합친다(문자열 끝 NUL 뒤 패딩 0 도 포함)
    merged = []
    for a, n in pool:
        e = a + n
        while True:                           # 뒤 패딩 0 까지(다음 문자열 시작 전)
            try:
                if d[o(e)] != 0 or any(a2 == e for a2, _ in pool) or e in en_strs:
                    break
            except ValueError:
                break
            e += 1
        if merged and merged[-1][1] >= a:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([a, e])
    free = sum(e - a for a, e in merged)
    need = 0
    # 큰 것부터 처음 맞는 자리
    for no in sorted(ROWS, key=lambda n: -len(ko[n])):
        b = ko[no] + b'\0'
        for blk in merged:
            a = (blk[0] + 3) & ~3
            if a + len(b) <= blk[1]:
                d[o(a):o(a) + len(b)] = b
                struct.pack_into('>I', d, o(ROWS[no][0]), a)
                blk[0] = a + len(b)
                need += len(b)
                break
        else:
            raise SystemExit('★시스템 메시지 자리 부족 0x%x' % no)
    # 제자리 6·7
    for no, (a, head) in INPLACE.items():
        got = cstr(a)
        assert got.decode('latin1').startswith(head), '제자리 원문 다름 0x%x' % no
        p = o(a) + len(got)
        while d[p] == 0:
            p += 1
        room = p - o(a)
        if no == 0x6:
            room = min(room, 0x40)               # 7번 = 6번 주소 + 0x40
        b = ko[no] + b'\0'
        assert len(b) <= room, '★제자리 넘침 0x%x %d > %d' % (no, len(b), room)
        d[o(a):o(a) + room] = b + b'\0' * (room - len(b))
    return '시스템 메시지 %d개(제자리 %d) · 자리 %d/%d B' % (len(ROWS) + len(INPLACE), len(INPLACE), need, free)
