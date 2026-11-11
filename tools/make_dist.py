# -*- coding: utf-8 -*-
r"""앨리스 1 (American McGee's Alice, PS3 — 매드니스 리턴즈 디스크판 BLUS30607 + DLC) 배포 묶음 (2026-11-11)
  dist/AmericanMcGeesAlice_PS3_KR_v0.9/  (+ .zip)
    patch\alice.ppu.elf.xdelta      복호화한 원본 ELF → 한글 ELF  (★원본 SELF 는 암호화라 bat 가 RPCS3 --decrypt 로 푼다)
    patch\INT\*.urc.xdelta          DLC 메뉴 7개
    files\pak9_korean.pk3           새 파일(한글 글꼴·자막·메뉴) — DLC base 폴더에 넣음
    xdelta.exe · readme.txt · 한글패치_적용.bat · 되돌리기.bat
  python tools/make_dist.py            (tools/build.py 뒤에)

대상 두 곳: ① 게임(디스크) 폴더  PS3_GAME\USRDIR\Alice1\bin\alice.ppu.self
            ② RPCS3 HDD 의 DLC  dev_hdd0\game\BLUS30607\USRDIR\UNREALENGINE3\Alice1\bin\base
만들고 나서 «원본에 적용 → 빌드와 바이트 동일» 되짚기. 한글 ELF 는 평문(재서명 안 함) → RPCS3 전용.
규칙: MD5 대문자 · 문서·bat 은 CP949(CRLF) · 버전 v0.9 · bat 의 if 블록 안 echo 에 괄호 금지(괄호 블록 자체를 안 씀).
"""
import hashlib, os, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
VER = 'v0.9'
NAME = 'AmericanMcGeesAlice_PS3_KR_' + VER
XDELTA = r'C:\claude\utils\xdelta.exe'
BASE = os.path.join(ROOT, 'work', 'pkg', 'USRDIR', 'UNREALENGINE3', 'Alice1', 'bin', 'base')
BUILD = os.path.join(ROOT, 'work', 'build')
SELF_ORIG = os.path.join(ROOT, 'work', 'bin', 'alice.ppu.self')
ELF_ORIG = os.path.join(ROOT, 'work', 'bin', 'alice.ppu.elf')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = """아메리칸 맥기의 앨리스 (American McGee's Alice, PS3) 한글 패치 {ver}
================================================================

「앨리스 매드니스 리턴즈」 북미 디스크판(BLUS30607)에 딸린 1편(DLC 코드로 받는 것) 용입니다.
RPCS3 전용입니다. (한글 실행 파일을 재서명하지 않아서 실기 PS3 에서는 돌지 않습니다)
2편 한글 패치와는 따로입니다. 2편 패치는 hospi0/alice2-kr-patch.


[ 준비 ]

- RPCS3 에 2편 디스크판(BLUS30607)이 등록돼 있고, 1편 DLC 가 설치돼 있어야 합니다.
  (1편 DLC 는 RPCS3 의 dev_hdd0\\game\\BLUS30607\\USRDIR\\UNREALENGINE3\\Alice1 에 깔립니다)


[ 적용 방법 ]

1. 이 묶음을 아무 폴더에나 풉니다.
2. 「한글패치_적용.bat」 을 실행합니다.
3. 첫 질문: RPCS3 폴더(rpcs3.exe 가 있는 곳)를 끌어다 놓거나 경로를 적고 Enter.
4. 둘째 질문: 게임(디스크) 폴더를 끌어다 놓거나 경로를 적고 Enter.
   예) ...\\Alice - Madness Returns (USA)   (PS3_GAME 이 들어 있는 폴더)
5. 배치가
     - 실행 파일 alice.ppu.self 를 원본 확인 → 「원본백업」 에 복사 → RPCS3 로 복호화 → 패치 → 결과 확인
     - DLC 메뉴 파일 7개를 원본 확인 → 백업 → 패치 → 결과 확인
     - DLC base 폴더에 pak9_korean.pk3 복사
   를 합니다. 이미 한글판인 파일은 건너뜁니다.
6. RPCS3 에서 2편을 켜고 메인 메뉴의 1편 항목으로 들어갑니다.

되돌리기 : 「되돌리기.bat」 → 같은 두 폴더를 주면 「원본백업」 으로 되돌리고 pak9_korean.pk3 를 지웁니다.
          (「원본백업」 폴더를 지우지 마세요)


[ 바뀌는 것 ]

■ 음성 대사 자막 전부 (848줄)
■ 메뉴 · 설정 · 조작 · 불러오기/저장 · 장 이름
■ 저장·불러오기·새 게임 확인창 문구 (실행 파일 안)
■ 한글 글꼴 (고운바탕 Bold). 실행 파일에 2바이트 한글 그리기를 덧붙였습니다


[ 알려진 사항 ]

■ 그림으로 된 글자(New Game, Load/Save 등 큰 제목 글씨)는 영어 그대로입니다.
■ 엔딩 크레딧(제작진 명단)은 영어 그대로입니다.
■ XMB 에 보이는 저장 데이터 이름(Config Data, AUTOSAVE 등)은 영어 그대로입니다.
■ 글꼴에 「…」 가 없어 말줄임표는 「...」 로 나옵니다.


[ 원본 → 한글판 MD5 ]

{table}
"""

BAT = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "XD=%~dp0xdelta.exe"
set "BK=%~dp0원본백업"
set "TMPD=%~dp0_tmp"

echo.
echo  ================================================================
echo    American McGee's Alice PS3 Korean Patch {ver}   [BLUS30607 DLC]
echo  ================================================================
echo.

if not exist "%XD%" goto NOXD

set "RP=%~1"
if not defined RP set /p RP=  RPCS3 폴더 - rpcs3.exe 가 있는 곳 - 를 끌어다 놓거나 경로를 적고 Enter:
set RP=%RP:"=%
if "%RP:~-1%"=="\" set "RP=%RP:~0,-1%"
if exist "%RP%\rpcs3.exe" goto RPOK
for %%I in ("%RP%") do set "RP=%%~dpI"
if "%RP:~-1%"=="\" set "RP=%RP:~0,-1%"
if not exist "%RP%\rpcs3.exe" goto NORP
:RPOK
set "DLC=%RP%\dev_hdd0\game\BLUS30607\USRDIR\UNREALENGINE3\Alice1\bin\base"
if exist "%DLC%\INT\title.urc" goto DLCOK
echo  RPCS3 기본 위치에 1편 DLC 가 없습니다: %DLC%
set /p DLC=  DLC 의 base 폴더 - ...\Alice1\bin\base - 를 끌어다 놓거나 경로를 적고 Enter:
set DLC=%DLC:"=%
if "%DLC:~-1%"=="\" set "DLC=%DLC:~0,-1%"
if not exist "%DLC%\INT\title.urc" goto NODLC
:DLCOK

set "GAME=%~2"
if not defined GAME set /p GAME=  게임 - 디스크 - 폴더를 끌어다 놓거나 경로를 적고 Enter:
set GAME=%GAME:"=%
if "%GAME:~-1%"=="\" set "GAME=%GAME:~0,-1%"
set "BIN="
if exist "%GAME%\alice.ppu.self" set "BIN=%GAME%"
if exist "%GAME%\bin\alice.ppu.self" set "BIN=%GAME%\bin"
if exist "%GAME%\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\Alice1\bin"
if exist "%GAME%\USRDIR\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\USRDIR\Alice1\bin"
if exist "%GAME%\PS3_GAME\USRDIR\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\PS3_GAME\USRDIR\Alice1\bin"
if not defined BIN goto NOBIN

echo.
echo  RPCS3 : %RP%
echo  DLC   : %DLC%
echo  실행  : %BIN%
echo.
if not exist "%BK%\INT" mkdir "%BK%\INT"
set /a DONE=0
set /a SKIP=0

rem ---- 실행 파일 ----
call :HASH "%BIN%\alice.ppu.self"
if /I "%H%"=="{kr}" set /a SKIP+=1
if /I "%H%"=="{kr}" goto URC
if /I not "%H%"=="{so}" goto WRONGSELF
if exist "%TMPD%" rmdir /s /q "%TMPD%"
mkdir "%TMPD%"
copy /y "%BIN%\alice.ppu.self" "%BK%\alice.ppu.self" >nul
copy /y "%BIN%\alice.ppu.self" "%TMPD%\alice.ppu.self" >nul
echo  RPCS3 로 실행 파일 복호화 중...
start "" /wait "%RP%\rpcs3.exe" --no-gui --decrypt "%TMPD%\alice.ppu.self"
if not exist "%TMPD%\alice.ppu.elf" goto DECFAIL
call :HASH "%TMPD%\alice.ppu.elf"
if /I not "%H%"=="{eo}" goto DECFAIL
"%XD%" -d -f -s "%TMPD%\alice.ppu.elf" "patch\alice.ppu.elf.xdelta" "%TMPD%\kr.elf"
if errorlevel 1 goto XFAILSELF
call :HASH "%TMPD%\kr.elf"
if /I not "%H%"=="{kr}" goto XFAILSELF
copy /y "%TMPD%\kr.elf" "%BIN%\alice.ppu.self" >nul
rmdir /s /q "%TMPD%"
set /a DONE+=1
echo      alice.ppu.self

:URC
set "DEST=%DLC%"
{calls}
copy /y "files\pak9_korean.pk3" "%DLC%\pak9_korean.pk3" >nul
call :HASH "%DLC%\pak9_korean.pk3"
if /I not "%H%"=="{pk}" goto PKFAIL
echo      pak9_korean.pk3
echo.
echo  [OK] 끝났습니다. 새로 패치 %DONE%개 · 이미 한글판 %SKIP%개 · pak9_korean.pk3 넣음
echo       원본은 "원본백업" 폴더에 있습니다.
goto END

:DO
set "NAME=%~1"
set "SRCMD5=%~2"
set "DSTMD5=%~3"
if not exist "%DEST%\%NAME%" goto MISSING
call :HASH "%DEST%\%NAME%"
if /I "%H%"=="%DSTMD5%" set /a SKIP+=1
if /I "%H%"=="%DSTMD5%" exit /b 0
if /I not "%H%"=="%SRCMD5%" goto WRONG
copy /y "%DEST%\%NAME%" "%BK%\%NAME%" >nul
"%XD%" -d -f -s "%DEST%\%NAME%" "patch\%NAME%.xdelta" "%BK%\%NAME%.new"
if errorlevel 1 goto XFAIL
call :HASH "%BK%\%NAME%.new"
if /I not "%H%"=="%DSTMD5%" goto XFAIL
move /y "%BK%\%NAME%.new" "%DEST%\%NAME%" >nul
set /a DONE+=1
echo      %NAME%
exit /b 0

:HASH
set "H="
for /f "skip=1 tokens=* delims=" %%A in ('certutil -hashfile "%~1" MD5') do if not defined H set "H=%%A"
set "H=%H: =%"
exit /b 0

:MISSING
echo  [!] %NAME% 이 DLC 폴더에 없습니다.
goto FAIL
:WRONG
echo  [!] %NAME% 이 원본과 다릅니다. 다른 판이거나 이미 다른 패치가 들어가 있습니다.
echo      원본 MD5 %SRCMD5%
goto FAIL
:XFAIL
echo  [!] %NAME% 패치 결과가 맞지 않습니다.
if exist "%BK%\%NAME%.new" del "%BK%\%NAME%.new"
goto FAIL
:WRONGSELF
echo  [!] alice.ppu.self 가 원본과 다릅니다. 다른 판이거나 이미 다른 패치가 들어가 있습니다.
echo      원본 MD5 {so}
goto FAIL
:DECFAIL
echo  [!] RPCS3 복호화에 실패했습니다. RPCS3 를 최신으로 올리고 다시 해 보세요.
if exist "%TMPD%" rmdir /s /q "%TMPD%"
goto FAIL
:XFAILSELF
echo  [!] 실행 파일 패치 결과가 맞지 않습니다.
if exist "%TMPD%" rmdir /s /q "%TMPD%"
goto FAIL
:PKFAIL
echo  [!] pak9_korean.pk3 복사가 맞지 않습니다.
goto FAIL
:NOXD
echo  [!] xdelta.exe 가 없습니다. 묶음을 그대로 풀고 실행하세요.
goto END
:NORP
echo  [!] rpcs3.exe 를 찾지 못했습니다: %RP%
goto END
:NODLC
echo  [!] 1편 DLC 폴더를 찾지 못했습니다: %DLC%
goto END
:NOBIN
echo  [!] PS3_GAME\USRDIR\Alice1\bin\alice.ppu.self 를 찾지 못했습니다: %GAME%
goto END
:FAIL
echo.
echo  중단했습니다. 이미 바꾼 파일은 되돌리기.bat 로 되돌릴 수 있습니다.
:END
echo.
if "%~3"=="" pause
endlocal
exit /b 0
"""

UNDO = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "BK=%~dp0원본백업"
echo.
echo  American McGee's Alice PS3 Korean Patch {ver} - 되돌리기
echo.
if not exist "%BK%\INT\title.urc" goto NOBK
set "RP=%~1"
if not defined RP set /p RP=  RPCS3 폴더를 끌어다 놓거나 경로를 적고 Enter:
set RP=%RP:"=%
if "%RP:~-1%"=="\" set "RP=%RP:~0,-1%"
set "DLC=%RP%\dev_hdd0\game\BLUS30607\USRDIR\UNREALENGINE3\Alice1\bin\base"
if exist "%DLC%\INT\title.urc" goto DLCOK
set /p DLC=  DLC 의 base 폴더 - ...\Alice1\bin\base - 를 끌어다 놓거나 경로를 적고 Enter:
set DLC=%DLC:"=%
if "%DLC:~-1%"=="\" set "DLC=%DLC:~0,-1%"
if not exist "%DLC%\INT\title.urc" goto NODLC
:DLCOK
for %%F in ("%BK%\INT\*") do copy /y "%%F" "%DLC%\INT\%%~nxF" >nul
if exist "%DLC%\pak9_korean.pk3" del "%DLC%\pak9_korean.pk3"
echo  [OK] DLC 를 원본으로 되돌렸습니다: %DLC%
if not exist "%BK%\alice.ppu.self" goto END
set "GAME=%~2"
if not defined GAME set /p GAME=  게임 - 디스크 - 폴더를 끌어다 놓거나 경로를 적고 Enter:
set GAME=%GAME:"=%
if "%GAME:~-1%"=="\" set "GAME=%GAME:~0,-1%"
set "BIN="
if exist "%GAME%\alice.ppu.self" set "BIN=%GAME%"
if exist "%GAME%\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\Alice1\bin"
if exist "%GAME%\USRDIR\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\USRDIR\Alice1\bin"
if exist "%GAME%\PS3_GAME\USRDIR\Alice1\bin\alice.ppu.self" set "BIN=%GAME%\PS3_GAME\USRDIR\Alice1\bin"
if not defined BIN goto NOBIN
copy /y "%BK%\alice.ppu.self" "%BIN%\alice.ppu.self" >nul
echo  [OK] 실행 파일을 원본으로 되돌렸습니다: %BIN%
goto END
:NOBK
echo  [!] 원본백업 폴더가 비어 있습니다. 한글패치_적용.bat 을 먼저 쓴 묶음에서 실행하세요.
goto END
:NODLC
echo  [!] 1편 DLC 폴더를 찾지 못했습니다: %DLC%
goto END
:NOBIN
echo  [!] alice.ppu.self 를 찾지 못했습니다: %GAME%
:END
echo.
if "%~3"=="" pause
endlocal
"""


def write_cp949(path, text):
    with open(path, 'wb') as f:
        f.write(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('cp949'))


def xd(src, dst, patch, chk):
    os.makedirs(os.path.dirname(patch), exist_ok=True)
    subprocess.run([XDELTA, '-e', '-9', '-S', 'djw', '-f', '-s', src, dst, patch], check=True)
    subprocess.run([XDELTA, '-d', '-f', '-s', src, patch, chk], check=True)
    if md5(chk) != md5(dst):
        raise SystemExit('⛔ xdelta 되짚기 결과가 다르다: ' + dst)
    return os.path.getsize(patch)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dist = os.path.join(ROOT, 'dist', NAME)
    if os.path.exists(dist):
        shutil.rmtree(dist)
    os.makedirs(os.path.join(dist, 'files'))
    chk = os.path.join(ROOT, 'work', 'dist_check.bin')
    rows, calls, total = [], [], 0
    kr = os.path.join(BUILD, 'alice.ppu.self')
    so, eo, km = md5(SELF_ORIG), md5(ELF_ORIG), md5(kr)
    total += xd(ELF_ORIG, kr, os.path.join(dist, 'patch', 'alice.ppu.elf.xdelta'), chk)
    rows.append(('alice.ppu.self', so, km))
    rows.append(('  (RPCS3 복호화 ELF)', eo, km))
    for f in sorted(os.listdir(os.path.join(BUILD, 'INT'))):
        src, dst = os.path.join(BASE, 'INT', f), os.path.join(BUILD, 'INT', f)
        total += xd(src, dst, os.path.join(dist, 'patch', 'INT', f + '.xdelta'), chk)
        rows.append(('INT\\' + f, md5(src), md5(dst)))
        calls.append('call :DO "INT\\%s" %s %s' % (f, md5(src), md5(dst)))
    os.remove(chk)
    pk = os.path.join(BUILD, 'pak9_korean.pk3')
    shutil.copy(pk, os.path.join(dist, 'files', 'pak9_korean.pk3'))
    rows.append(('pak9_korean.pk3 (새 파일)', '-', md5(pk)))
    shutil.copy(XDELTA, os.path.join(dist, 'xdelta.exe'))
    table = '\n'.join('%-28s %s -> %s' % r for r in rows)
    write_cp949(os.path.join(dist, 'readme.txt'), README.format(ver=VER, table=table))
    write_cp949(os.path.join(dist, '한글패치_적용.bat'), BAT.replace('{calls}', '\n'.join(calls)).replace('{ver}', VER)
                .replace('{so}', so).replace('{eo}', eo).replace('{kr}', km).replace('{pk}', md5(pk)))
    write_cp949(os.path.join(dist, '되돌리기.bat'), UNDO.replace('{ver}', VER))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for r, _, fs in os.walk(dist):
            for f in fs:
                p = os.path.join(r, f)
                zf.write(p, os.path.join(NAME, os.path.relpath(p, dist)))
    print('%s : xdelta %d개 %.1f KB · zip %.1f MB · zip MD5 %s' % (NAME, len(calls) + 1, total / 1e3, os.path.getsize(z) / 1e6, md5(z)))
    print('self 원본 %s · 복호화 ELF %s · 한글 %s' % (so, eo, km))


if __name__ == '__main__':
    main()
