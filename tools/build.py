# -*- coding: utf-8 -*-
"""앨리스 1 한글 빌드 (2026-11-11) → work/build/
  입력  work/text/ko.tsv (tools/merge_ko.py) · work/text/all.tsv (모든 출현 위치) · 원본 work/pkg/…/base (읽기만)
  산출  pak9_korean.pk3   fonts/asrafel.ritualfont · gfx/fonts/asrafel.tga · dialog/*.tlk · ui/*.urc|scr (pak0 덮기)
                          ★폴더 항목(dir/) 함께 [[feedback_q3_pk3_needs_directory_entries]]
        INT/*.urc         PS3 메뉴(낱파일) — credits*.urc 는 손대지 않음
        alice.ppu.self    tools/patch_elf.py (한글 그리기 훅 + 시스템 메시지)
  인코딩 CP949(KS X 1001 한글 2,350 + ASCII — merge_ko.py 가 이미 막음)
  검산  모든 출현 위치가 바뀌었는지(못 바꾼 곳 = 0) · 따옴표 안 문자열에 « " » 금지 · 원문 줄 수·소리 줄 그대로
python tools/build.py
"""
import os, sys, re, zipfile, shutil, subprocess, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_font

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'work', 'pkg', 'USRDIR', 'UNREALENGINE3', 'Alice1', 'bin', 'base')
OUT = os.path.join(ROOT, 'work', 'build')


def load():
    ko = {}
    for l in open(os.path.join(ROOT, 'work', 'text', 'ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if l:
            no, at, en, k = l.split('\t')
            ko[en] = k
    locs = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'text', 'all.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    return ko, locs


def enc(s):
    return s.encode('cp949')


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


def build_tlk(ko, errs):
    z = zipfile.ZipFile(os.path.join(BASE, 'pak4_english.pk3'))
    files = {}; n = 0
    for i in z.infolist():
        if not i.filename.endswith('.tlk'):
            continue
        raw = z.read(i)
        L = raw.split(b'\n')
        for k in range(len(L) - 1):
            if L[k].strip().startswith(b'"sound/'):
                line = L[k + 1]
                cr = line.endswith(b'\r')
                en = line.rstrip(b'\r').strip().decode('latin1')
                if en not in ko:
                    errs.append('tlk %s 번역 없음: %s' % (i.filename, en[:40])); continue
                L[k + 1] = enc(ko[en]) + (b'\r' if cr else b'')
                n += 1
        nb = b'\n'.join(L)
        assert nb.count(b'\n') == raw.count(b'\n')
        files[i.filename] = nb
    return files, n


def replace_ui(text, locs, ko, fname, errs):
    """text = latin1 로 푼 파일 · locs = [(줄, 키, 순번, EN)] — 줄 단위로 그 순번의 문자열만 바꾼다"""
    L = text.split('\n')
    n = 0
    byline = collections.defaultdict(list)
    for ln, key, j, en in locs:
        byline[ln].append((j, key, en))
    for ln, items in byline.items():
        line = L[ln - 1]
        for j, key, en in sorted(items, reverse=True):
            k = ko.get(en)
            if k is None:
                errs.append('%s:%d 번역 없음 %s' % (fname, ln, en)); continue
            kk = enc(k).decode('latin1')
            m = re.match(r'(\s*)(\w+)(\s+)(.*)$', line, re.S)
            low = key.lower()
            if low == 'mouseentercmd':
                spans = [mm.span(1) for mm in re.finditer(r'title\s+([^;"\\]+)', line)]
                if j >= len(spans):
                    errs.append('%s:%d 자리 못 찾음' % (fname, ln)); continue
                a, b = spans[j]
                seg = line[a:b]
                b = a + len(seg.rstrip())          # 뒤 공백 보존
                if ';' in k or '\\' in k or '"' in k:
                    errs.append('%s:%d mouseEnterCmd 금지 글자 %s' % (fname, ln, k)); continue
                if line[a:b] != en:
                    errs.append('%s:%d 원문 다름 %r' % (fname, ln, line[a:b])); continue
                line = line[:a] + kk + line[b:]
            else:
                spans = [mm.span(1) for mm in re.finditer(r'"([^"]*)"', line)]
                if low == 'title' and not spans:
                    # 따옴표 없는 title — 나머지 전체
                    st = m.start(4); rest = line[st:]
                    if rest.rstrip('\r') != en:
                        errs.append('%s:%d 원문 다름 %r' % (fname, ln, rest)); continue
                    line = line[:st] + kk + ('\r' if rest.endswith('\r') else '')
                    n += 1; continue
                if j >= len(spans):
                    errs.append('%s:%d 자리 못 찾음' % (fname, ln)); continue
                a, b = spans[j]
                if line[a:b] != en:
                    errs.append('%s:%d 원문 다름 %r' % (fname, ln, line[a:b])); continue
                if '"' in k:
                    errs.append('%s:%d 따옴표 안에 " %s' % (fname, ln, k)); continue
                line = line[:a] + kk + line[b:]
            n += 1
        L[ln - 1] = line
    return '\n'.join(L), n


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ko, locs = load()
    errs = []
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'INT'))
    files, canvas = build_font.build(os.path.join(BASE, 'pak0.pk3'))
    canvas.crop((0, 0, 2048, 256 + 37 * 32)).resize((1024, (256 + 37 * 32) // 2)).save(os.path.join(OUT, 'preview_font_ko.png'))
    tf, nt = build_tlk(ko, errs)
    files.update(tf)
    # UI — 파일별 위치 모으기
    per = collections.defaultdict(list)
    for at, b, en, _ in locs:
        if at.startswith('U|'):
            _, f, ln, key, j = at.split('|')
            per[f].append((int(ln), key, int(j), en))
    nu = 0
    z0 = zipfile.ZipFile(os.path.join(BASE, 'pak0.pk3'))
    for f, ll in sorted(per.items()):
        if f.startswith('INT/'):
            src = open(os.path.join(BASE, f.replace('/', os.sep)), 'rb').read().decode('latin1')
        else:
            src = z0.read(f[len('pak0/'):]).decode('latin1')
        new, n = replace_ui(src, ll, ko, f, errs)
        nu += n
        data = new.encode('latin1')
        if f.startswith('INT/'):
            open(os.path.join(OUT, f.replace('/', os.sep)), 'wb').write(data)
        else:
            files[f[len('pak0/'):]] = data
    # 손대지 않은 INT urc(크레디트 등)는 내보내지 않는다
    nloc = sum(1 for r in locs if r[0].startswith('U|'))
    ntl = sum(1 for r in locs if r[0].startswith('T|'))
    if nu != nloc:
        errs.append('UI 바꾼 곳 %d ≠ 위치 %d' % (nu, nloc))
    if nt != ntl:
        errs.append('자막 바꾼 줄 %d ≠ 위치 %d' % (nt, ntl))
    for e in errs[:30]:
        print('  ✗', e)
    if errs:
        raise SystemExit('★빌드 막음 %d' % len(errs))
    pk3(os.path.join(OUT, 'pak9_korean.pk3'), files)
    subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'patch_elf.py'),
                    os.path.join(ROOT, 'work', 'bin', 'alice.ppu.elf'), os.path.join(OUT, 'alice.ppu.self')], check=True)
    print('자막 %d/%d줄 · UI %d/%d곳 · pak9 파일 %d · INT urc %d개' % (nt, ntl, nu, nloc, len(files), len(os.listdir(os.path.join(OUT, 'INT')))))


if __name__ == '__main__':
    main()
