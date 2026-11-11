# -*- coding: utf-8 -*-
"""앨리스 1편(PS3 DLC) 번역 대상 추출 (2026-11-11)
원본(읽기만): work/pkg/USRDIR/UNREALENGINE3/Alice1/bin/base  (tools/ps3pkg.py 로 DLC pkg 를 푼 것 — RPCS3 클린 설치본과 73개 md5 동일)

출처
  T  pak4_english.pk3 dialog/*.tlk — "소리 경로" 줄 다음 줄이 자막        위치 = T|<tlk>|<소리경로>
  U  base/INT/*.urc (PS3 메뉴) · pak0.pk3 ui/*.urc·*.scr (기본 메뉴)
       title "…" · additem N "…" · binditem "…" … · mouseEnterCmd "…title …" · maplist 장 이름
                                                                 위치 = U|<파일>|<줄>|<키>|<줄 안 순번>
  ⛔credits.urc · credits2.urc (스태프 명단) — 허락 전 번역 금지 → 뽑지 않음
산출
  work/text/all.tsv  : 위치 · 꾸러미 · EN · KO        (재삽입 기준)
  my files/tsv/<꾸러미>_NNN.tsv : 번호 · 위치 · EN · KO — UTF-8 18KB 단위 (꾸러미 = ui · dialog)
검산: tlk 는 «소리 줄 + 자막 줄» 쌍이 빠짐없이 잡혔는지(소리 줄 수 = 추출 수).
python tools/extract.py
"""
import os, sys, re, glob, zipfile, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'work', 'pkg', 'USRDIR', 'UNREALENGINE3', 'Alice1', 'bin', 'base')
SPLIT = 18 * 1024
SKIP = re.compile(r'credits2?\.urc$', re.I)
HAS = re.compile('[A-Za-z]{2}')


def esc(s):
    assert '\t' not in s
    return s.replace('\\n', '\\n')


def ui_sources():
    out = []
    for f in sorted(glob.glob(os.path.join(BASE, 'INT', '*.urc'))):
        out.append(('INT/' + os.path.basename(f), open(f, 'rb').read().decode('latin1')))
    z = zipfile.ZipFile(os.path.join(BASE, 'pak0.pk3'))
    for i in z.infolist():
        n = i.filename
        if n.startswith('ui/') and n.endswith(('.urc', '.scr', '.inc')):
            out.append(('pak0/' + n, z.read(i).decode('latin1')))
    return [(f, t) for f, t in out if not SKIP.search(f)]


def ui_rows():
    rows = []
    for f, t in ui_sources():
        for ln, line in enumerate(t.split('\n'), 1):
            s = line.strip()
            m = re.match(r'(\w+)\s+(.*)$', s)
            if not m:
                continue
            key, rest = m.group(1), m.group(2)
            k = key.lower()
            strs = []
            if k in ('title', 'additem', 'binditem', 'highlighttextwidget') or (f.endswith('maplist.scr') and re.match(r'\d+$', key)):
                if k in ('highlighttextwidget',):
                    continue                     # 위젯 이름(내부)
                q = re.findall(r'"([^"]*)"', rest)
                if k == 'binditem':
                    q = q[:1]                    # 첫 따옴표 = 화면 이름, 뒤는 명령
                elif k == 'title' and not q:
                    q = [rest]                   # 따옴표 없는 title
                strs = q
            elif k == 'mouseentercmd':
                strs = [x.strip() for x in re.findall(r'title\s+([^;"\\]+)', rest)]
            for j, sv in enumerate(strs):
                if HAS.search(sv):
                    rows.append(('U|%s|%d|%s|%d' % (f, ln, key, j), 'ui', esc(sv)))
    return rows


def dialog_rows():
    z = zipfile.ZipFile(os.path.join(BASE, 'pak4_english.pk3'))
    rows = []; nsnd = 0
    for i in sorted(z.infolist(), key=lambda x: x.filename):
        if not i.filename.endswith('.tlk'):
            continue
        L = z.read(i).decode('latin1').replace('\r\n', '\n').split('\n')
        for a, b in zip(L, L[1:]):
            if a.strip().startswith('"sound/'):
                nsnd += 1
                rows.append(('T|%s|%s' % (os.path.basename(i.filename), a.strip().strip('"')), 'dialog', esc(b.strip())))
    assert nsnd == len(rows)
    return rows


def write_split(folder, stem, head, lines):
    chunks = []; cur = []; hb = len(head.encode('utf-8')); size = hb
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT:
            chunks.append(cur); cur = []; size = hb
        cur.append(ln); size += n
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        with open(os.path.join(folder, '%s_%03d.tsv' % (stem, i)), 'w', encoding='utf-8', newline='\n') as w:
            w.write(head + ''.join(c))
    return len(chunks)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = ui_rows() + dialog_rows()
    tdir = os.path.join(ROOT, 'work', 'text'); os.makedirs(tdir, exist_ok=True)
    with open(os.path.join(tdir, 'all.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('위치\t꾸러미\tEN\tKO\n')
        for at, b, en in rows:
            w.write('%s\t%s\t%s\t\n' % (at, b, en))
    uniq = collections.OrderedDict()
    for at, b, en in rows:
        u = uniq.setdefault(en, [0, at, b]); u[0] += 1
    out = os.path.join(ROOT, 'my files', 'tsv'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, '*.tsv')):
        os.remove(f)
    per = collections.OrderedDict(); no = 0
    for en, (n, at, b) in uniq.items():
        no += 1
        per.setdefault(b, []).append('%05d\t%s\t%s\t\n' % (no, at, en))
    print('출현 %d줄 · 고유 %d줄' % (len(rows), len(uniq)))
    for b, lines in per.items():
        words = sum(len(l.split('\t')[2].split()) for l in lines)
        nf = write_split(out, b, '번호\t위치\tEN\tKO\n', lines)
        print('  %-7s 고유 %4d줄 · 낱말 %6d · 파일 %d개' % (b, len(lines), words, nf))


if __name__ == '__main__':
    main()
