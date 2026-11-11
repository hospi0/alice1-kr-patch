# -*- coding: utf-8 -*-
"""PS3 PPU ELF(64비트 빅엔디언) 분석 도우미 (2026-11-11) — 앨리스 1 alice.ppu.elf
  from elfx import Elf ; e = Elf(path)
  e.va(off) / e.off(va)             파일 오프셋 ↔ 가상 주소
  e.toc                            .opd 에서 얻은 TOC(r2) 값(가장 흔한 것)
  e.toc_slots(va)                  32비트 값 va 를 담은 TOC 칸들(주소)
  e.refs_r2(slot)                  lwz/ld rX, d(r2) 로 그 칸을 읽는 명령 주소
  e.dis(va, n)                     capstone 역어셈블
  e.func_start(va)                 함수 시작 추정(mflr r0 / stdu r1 앞)
"""
import struct, collections
import capstone

PT_LOAD = 1


class Elf:
    def __init__(self, path):
        self.d = open(path, 'rb').read()
        d = self.d
        assert d[:4] == b'\x7fELF' and d[4] == 2 and d[5] == 2
        phoff, = struct.unpack_from('>Q', d, 0x20)
        phentsize, phnum = struct.unpack_from('>HH', d, 0x36)
        self.segs = []
        for i in range(phnum):
            p = phoff + i * phentsize
            typ, flags, off, va, pa, fsz, msz, al = struct.unpack_from('>IIQQQQQQ', d, p)
            if typ == PT_LOAD:
                self.segs.append((va, off, fsz, msz, flags))
        self.cs = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)
        self.cs.detail = False
        self._opd()

    def va(self, off):
        for va, o, fsz, msz, fl in self.segs:
            if o <= off < o + fsz:
                return va + off - o
        return None

    def off(self, va):
        for v, o, fsz, msz, fl in self.segs:
            if v <= va < v + fsz:
                return o + va - v
        return None

    def u32(self, va):
        return struct.unpack_from('>I', self.d, self.off(va))[0]

    def _opd(self):
        # .opd 항목 = (함수 주소 u32, TOC u32) 쌍(PS3 는 32비트 포인터) — 데이터 세그먼트에서 «코드 주소 + 같은 TOC» 반복을 찾는다
        code = [s for s in self.segs if s[4] & 1]
        lo, hi = min(s[0] for s in code), max(s[0] + s[2] for s in code)
        cnt = collections.Counter()
        for va, o, fsz, msz, fl in self.segs:
            if fl & 1:
                continue
            for p in range(o, o + fsz - 8, 8):
                a, t = struct.unpack_from('>II', self.d, p)
                if lo <= a < hi and a % 4 == 0 and t:
                    cnt[t] += 1
        self.toc = cnt.most_common(1)[0][0] if cnt else None
        self.code = (lo, hi)

    def find_u32(self, val, data_only=True):
        out = []
        b = struct.pack('>I', val)
        for va, o, fsz, msz, fl in self.segs:
            if data_only and fl & 1:
                continue
            p = self.d.find(b, o, o + fsz)
            while p >= 0:
                if (p - o) % 4 == 0:
                    out.append(va + p - o)
                p = self.d.find(b, p + 1, o + fsz)
        return out

    def refs_r2(self, slot):
        """r2 기준 d 로 slot 을 읽는 lwz/ld 명령(rD, d(r2)) — 코드 전체 스캔."""
        disp = slot - self.toc
        if not -0x8000 <= disp < 0x8000:
            return []
        out = []
        lo, hi = self.code
        o0 = self.off(lo)
        for p in range(o0, o0 + (hi - lo), 4):
            w = struct.unpack_from('>I', self.d, p)[0]
            op = w >> 26
            if op in (32, 58) and ((w >> 16) & 31) == 2 and struct.unpack('>h', struct.pack('>H', w & 0xFFFF if op == 32 else w & 0xFFFC))[0] == disp:
                out.append(lo + p - o0)
        return out

    def dis(self, va, n=40):
        o = self.off(va)
        return ['%08X  %-8s %s' % (i.address, i.mnemonic, i.op_str) for i in self.cs.disasm(self.d[o:o + n * 4], va)]

    def func_start(self, va):
        a = va
        while a > self.code[0]:
            w = self.u32(a)
            if (w & 0xFFFF0000) in (0xF8210000, 0xF821FF00) or (w >> 16) == 0xF821:   # stdu r1,-x(r1)
                # 앞에 mflr r0 가 있으면 그게 시작
                if self.u32(a - 4) == 0x7C0802A6:
                    return a - 4
                return a
            a -= 4
        return None
