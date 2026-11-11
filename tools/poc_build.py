# -*- coding: utf-8 -*-
"""앨리스 1 한글 PoC 묶음 (2026-11-11) → work/poc/
  pak9_korean.pk3        fonts/asrafel.ritualfont · gfx/fonts/asrafel.tga(2048) · dialog/*.tlk(자막 앞에 «한글 시험 »)
                         ★폴더 항목(dir/) 함께 [[feedback_q3_pk3_needs_directory_entries]]
  INT/*.urc              메뉴 낱말 몇 개 CP949 한글
  alice.ppu.self         tools/patch_elf.py 결과(평문 ELF — RPCS3 는 SCE 머리 없으면 ELF 로 읽음, 실기는 재서명 필요)
  preview_font_ko.png    한글 영역 미리보기
python tools/poc_build.py
"""
import os, sys, zipfile, re, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'work', 'pkg', 'USRDIR', 'UNREALENGINE3', 'Alice1', 'bin', 'base')
OUT = os.path.join(ROOT, 'work', 'poc')
UI = {'Select': '선택', 'Back': '뒤로', 'Controls': '조작', 'Apply': '적용', 'Cancel': '취소',
      'Brightness': '밝기', 'Music Volume': '음악 음량', 'Effects Volume': '효과음 음량', 'Sensitivity': '감도',
      'Invert Vertical Look': '상하 시점 반전', 'Subtitles': '자막', 'Screen Scale': '화면 크기', 'Load': '불러오기',
      'Save': '저장', 'Delete': '삭제', 'Yes': '예', 'No': '아니요'}


def pk3(path, files):
    dirs = set()
    for n in files:
        p = n.split('/')[:-1]
        for i in range(1, len(p) + 1):
            dirs.add('/'.join(p[:i]) + '/')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for d in sorted(dirs):
            z.writestr(zipfile.ZipInfo(d), b'')
        for n in sorted(files):
            z.writestr(n, files[n])
    return sorted(dirs)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'INT'))
    files, canvas = build_font.build(os.path.join(BASE, 'pak0.pk3'))
    canvas.crop((0, 0, 2048, 256 + 37 * 32)).resize((1024, (256 + 37 * 32) // 2)).save(os.path.join(OUT, 'preview_font_ko.png'))
    e = zipfile.ZipFile(os.path.join(BASE, 'pak4_english.pk3'))
    nt = 0
    for i in e.infolist():
        if not i.filename.endswith('.tlk'):
            continue
        L = e.read(i).split(b'\n')
        for k in range(len(L) - 1):
            if L[k].strip().startswith(b'"sound/'):
                L[k + 1] = '한글 시험 '.encode('cp949') + L[k + 1]
                nt += 1
        files[i.filename] = b'\n'.join(L)
    dirs = pk3(os.path.join(OUT, 'pak9_korean.pk3'), files)
    nu = 0
    for f in os.listdir(os.path.join(BASE, 'INT')):
        if not f.endswith('.urc') or f.lower().startswith('credits'):
            continue
        b = open(os.path.join(BASE, 'INT', f), 'rb').read()
        def rep(m):
            global_n = m.group(2).decode('latin1')
            if global_n in UI:
                return m.group(1) + b'"' + UI[global_n].encode('cp949') + b'"'
            return m.group(0)
        nb, n = re.subn(rb'(\btitle\s+)"([^"]*)"', rep, b)
        nu += sum(1 for m in re.finditer(rb'\btitle\s+"([^"]*)"', b) if m.group(1).decode('latin1') in UI)
        open(os.path.join(OUT, 'INT', f), 'wb').write(nb)
    subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'patch_elf.py'),
                    os.path.join(ROOT, 'work', 'bin', 'alice.ppu.elf'), os.path.join(OUT, 'alice.ppu.self')], check=True)
    print('pak9_korean.pk3 : 파일 %d · 폴더 항목 %s · 자막 %d줄에 «한글 시험»' % (len(files), dirs, nt))
    print('INT urc 메뉴 한글 %d곳' % nu)


if __name__ == '__main__':
    main()
