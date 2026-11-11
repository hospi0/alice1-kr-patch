# -*- coding: utf-8 -*-
r"""한글 ELF → 실기(CFW·HEN)용 서명 SELF (2026-11-12)
  python tools/sign_self.py      → work/build/alice_kr_signed.self
도구: C:\claude\utils\scetool\scetool.exe (ErikPshat/scetool 소스를 zig c++ 로 빌드, 키 = jevinskie/ps3dotdir 의 keys·ldr_curves·vsh_curves → data\)
원본 SELF 정보(scetool -i): 키 개정 0x10(FW 3.60) · Auth-ID 1010000001000003 · Vendor 01000002 · APP · 앱 버전 01.00
                            capability flags 0x3B · unk6 1 · unk7 0x40000
서명: 키 개정 0x0A(3.55, 개인키 공개) · FW 3.55 · 같은 Auth-ID·cap flags. 압축 켬.
검산: scetool --decrypt 왕복 = 한글 ELF 와 바이트 동일 (RPCS3 --decrypt 도 동일 확인).
"""
import os, subprocess, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCE = r'C:\claude\utils\scetool'
B = os.path.join(ROOT, 'work', 'build')


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest().upper()


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    elf = os.path.join(B, 'alice.ppu.self')            # build.py 결과 = 평문 ELF
    assert open(elf, 'rb').read(4) == b'\x7fELF'
    out = os.path.join(B, 'alice_kr_signed.self')
    chk = os.path.join(B, '_chk.elf')
    exe = os.path.join(SCE, 'scetool.exe')
    subprocess.run([exe, '--sce-type=SELF', '--compress-data=TRUE', '--skip-sections=TRUE', '--key-revision=0A',
                    '--self-auth-id=1010000001000003', '--self-vendor-id=01000002', '--self-type=APP',
                    '--self-app-version=0001000000000000', '--self-fw-version=0003005500000000', '--self-add-shdrs=TRUE',
                    '--self-cap-flags=00000000000000000000000000000000000000000000003B0000000100040000',
                    '--encrypt', elf, out], cwd=SCE, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([exe, '--decrypt', out, chk], cwd=SCE, check=True, stdout=subprocess.DEVNULL)
    ok = md5(chk) == md5(elf)
    os.remove(chk)
    if not ok:
        raise SystemExit('⛔ 서명본을 풀어 보니 한글 ELF 와 다르다')
    print('서명 SELF %s (MD5 %s) · 왕복 = 한글 ELF %s' % (out, md5(out), md5(elf)))


if __name__ == '__main__':
    main()
