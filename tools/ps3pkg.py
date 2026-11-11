# -*- coding: utf-8 -*-
"""PS3 리테일 PKG 풀기 (2026-11-11) — RPCS3 설치 없이 work/ 에 꺼낸다.
  python tools/ps3pkg.py <pkg> <출력폴더> [--list]

형식(공개 자료 기준):
  머리 0x00 '\\x7FPKG' · 0x04 u16 pkg_revision(0x8000=리테일) · 0x06 u16 type(1=PS3)
       0x14 u32 item_count · 0x18 u64 total_size · 0x20 u64 data_offset · 0x28 u64 data_size
       0x30 content_id[0x24] · 0x70 digest[0x10] (= CTR 초기값)
  데이터 = AES-128-CTR(키 = PS3 PKG 공용 키, IV = digest). 블록 번호 = (데이터 안 오프셋 / 16).
  항목 표(데이터 맨 앞, 32 B × item_count): name_off u32 · name_size u32 · data_off u64 · data_size u64 · flags u32 · pad u32
     flags & 0xFF : 4 = 폴더, 그 밖 = 파일
검산: 항목 끝 오프셋 ≤ data_size, 이름이 인쇄 가능한 경로인지.
"""
import os, sys, struct
from Crypto.Cipher import AES
from Crypto.Util import Counter

PS3_KEY = bytes.fromhex('2E7B71D7C9C9A14EA3221F188828B8F8')
CHUNK = 1 << 20


def ctr(iv, off):
    blk = int.from_bytes(iv, 'big') + off // 16
    c = AES.new(PS3_KEY, AES.MODE_CTR, counter=Counter.new(128, initial_value=blk % (1 << 128)))
    return c


def read_dec(f, data_off, iv, off, n):
    a = off - off % 16
    f.seek(data_off + a)
    raw = f.read(n + (off - a))
    return ctr(iv, a).decrypt(raw)[off - a:off - a + n]


def main():
    pkg, out = sys.argv[1], sys.argv[2]
    lst = '--list' in sys.argv
    sys.stdout.reconfigure(encoding='utf-8')
    with open(pkg, 'rb') as f:
        h = f.read(0x80)
        assert h[:4] == b'\x7fPKG', 'PKG 아님'
        rev, typ = struct.unpack('>HH', h[4:8])
        n = struct.unpack('>I', h[0x14:0x18])[0]
        data_off, data_size = struct.unpack('>QQ', h[0x20:0x30])
        cid = h[0x30:0x54].split(b'\0')[0].decode()
        iv = h[0x70:0x80]
        print('%s · rev %04X type %d · 항목 %d · 데이터 0x%X + %d' % (cid, rev, typ, n, data_off, data_size))
        assert rev == 0x8000, '리테일 PKG 만 지원'
        tbl = read_dec(f, data_off, iv, 0, n * 32)
        items = []
        for i in range(n):
            no, ns, do, ds, fl = struct.unpack('>IIQQI', tbl[i * 32:i * 32 + 28])
            name = read_dec(f, data_off, iv, no, ns).decode('utf-8', 'replace')
            assert do + ds <= data_size and all(32 <= ord(c) < 0x7F or ord(c) > 0x9F for c in name), '항목 이상 %r' % name
            items.append((name, do, ds, fl & 0xFF))
        tot = 0
        for name, do, ds, t in items:
            p = os.path.join(out, name.replace('/', os.sep))
            if t == 4:
                if not lst:
                    os.makedirs(p, exist_ok=True)
                continue
            tot += ds
            if lst:
                print('%10d %s' % (ds, name)); continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as w:
                pos = 0
                while pos < ds:
                    k = min(CHUNK, ds - pos)
                    w.write(read_dec(f, data_off, iv, do + pos, k)); pos += k
        print('파일 %d개 · %.1f MB %s' % (sum(1 for x in items if x[3] != 4), tot / 1e6, '(목록만)' if lst else '→ ' + out))


if __name__ == '__main__':
    main()
