# -*- coding: utf-8 -*-
"""앨리스 1 번역 병합·검사 (2026-11-11) — 2편 tools/merge_ko.py 규칙 + 1편 글꼴 제약

입력  my files/번역/*.tsv (번호 · 위치 · EN · KO) — ⛔읽기만 · 받은 파일의 \\" 는 " 로
      work/ko/fix_*.tsv  (번호 \\t KO | 번호 \\t @찾을말=>바꿀말 ;; …) — 내 다듬기
기준  work/text/all.tsv (extract.py — 고유 원문 순서 = 번호)
산출  work/text/ko.tsv · work/text/ko_report.txt
막음  번호·EN 불일치 · 빈 KO · 탭/개행 · ★글꼴 밖 글자(ASCII + KS X 1001 한글 2,350자만 그릴 수 있다)
정리  … ‥ → ... · “ ” 「 」 『 』 → " · ‘ ’ → ' · · → , (2바이트 기호는 엔진이 라틴 두 글자로 찍어 깨진다)
      docs/표기치환.tsv (2편과 같은 표 — 받침 같은 것만, EN조건 열)
python tools/merge_ko.py
"""
import os, re, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'my files', '번역')
FIX = os.path.join(ROOT, 'work', 'ko')
KS = set(bytes([a, b]).decode('cp949') for a in range(0xB0, 0xC9) for b in range(0xA1, 0xFF))
ASCIIFY = [('……', '...'), ('…', '...'), ('‥', '..'), ('“', '"'), ('”', '"'), ('「', '"'), ('」', '"'),
           ('『', '"'), ('』', '"'), ('‘', "'"), ('’', "'"), ('·', ','), ('～', '~'), ('—', '-'), ('–', '-')]


def source_rows():
    rows = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'text', 'all.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    uniq = collections.OrderedDict()
    for at, b, en, _ in rows:
        uniq.setdefault(en, (at, b))
    return collections.OrderedDict(('%05d' % (i + 1), (at, b, en)) for i, (en, (at, b)) in enumerate(uniq.items()))


def load_subst():
    out = []
    jong = lambda ch: (ord(ch) - 0xAC00) % 28 if '가' <= ch <= '힣' else -1
    for l in open(os.path.join(ROOT, 'docs', '표기치환.tsv'), encoding='utf-8').read().splitlines():
        if not l.strip() or l.startswith('#'):
            continue
        c = l.split('\t')
        a, b = c[0], c[1]
        if jong(a[-1]) != jong(b[-1]):
            raise SystemExit('★표기치환 «%s→%s» 받침 다름' % (a, b))
        out.append((a, b, re.compile(c[3]) if len(c) > 3 and c[3].strip() else None))
    return out


def subst_one(k, a, b):
    i = b.find(a)
    pre, post = (b[:i], b[i + len(a):]) if i >= 0 else ('', '')
    pat = (('(?<!' + re.escape(pre) + ')') if pre else '') + re.escape(a) + (('(?!' + re.escape(post) + ')') if post else '')
    return re.subn(pat, lambda m: b, k)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print('── 병합 규칙: 번호·EN 일치 · 글꼴 밖 글자 막음(ASCII + 한글 2,350) · 기호 ASCII 로 · 표기치환 ──')
    src = source_rows()
    ko, origin, errs = {}, {}, []
    for f in sorted(glob.glob(os.path.join(SRC, '*.tsv'))):
        bn = os.path.basename(f)
        for i, l in enumerate(open(f, encoding='utf-8-sig').read().split('\n')[1:], 2):
            if not l.strip():
                continue
            c = l.split('\t')
            if len(c) < 4:
                errs.append('%s:%d 열 부족' % (bn, i)); continue
            no, en, k = c[0], c[2].replace('\\"', '"'), '\t'.join(c[3:]).replace('\\"', '"')
            if no not in src or src[no][2] != en:
                errs.append('%s:%d 번호/EN 불일치 %s' % (bn, i, no)); continue
            ko[no] = k; origin[no] = bn
    for f in sorted(glob.glob(os.path.join(FIX, 'fix_*.tsv'))):
        bn = os.path.basename(f)
        for i, l in enumerate(open(f, encoding='utf-8-sig').read().split('\n'), 1):
            if not l.strip() or l.startswith('#'):
                continue
            c = l.split('\t')
            if len(c) != 2 or c[0] not in src:
                errs.append('%s:%d 형식/번호 %r' % (bn, i, l[:50])); continue
            v = c[1]
            if v.startswith('@') and '=>' in v:
                cur = ko.get(c[0], '')
                for part in v.split(' ;; '):
                    a, b2 = part[1:].split('=>', 1)
                    if a not in cur:
                        errs.append('%s:%d «%s» 못 찾음 %s' % (bn, i, a[:20], c[0])); break
                    cur = cur.replace(a, b2)
                ko[c[0]] = cur
            else:
                ko[c[0]] = v
            origin[c[0]] = bn
    miss = [n for n in src if n not in ko]
    if miss:
        errs.append('번역 없음 %d: %s' % (len(miss), miss[:10]))
    subst = load_subst(); nsub = collections.Counter(); nfix = collections.Counter()
    out = []
    for no, (at, b, en) in src.items():
        if no not in ko:
            continue
        k = ko[no].strip()
        for a, b2 in ASCIIFY:
            if a in k:
                nfix[a] += k.count(a); k = k.replace(a, b2)
        for a, b2, cond in subst:
            if cond and not cond.search(en):
                continue
            if a in k:
                k, n = subst_one(k, a, b2); nsub[a] += n
        if not k:
            errs.append('%s 빈 KO' % no); continue
        if '\t' in k or '\n' in k:
            errs.append('%s 탭/개행' % no); continue
        bad = sorted(set(ch for ch in k if ord(ch) >= 0x80 and ch not in KS))
        if bad:
            errs.append('%s 글꼴 밖 글자 %s : %s [%s]' % (no, bad, k[:50], origin[no]))
        out.append((no, at, en, k))
    with open(os.path.join(ROOT, 'work', 'text', 'ko_report.txt'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('막음 %d\n%s\n' % (len(errs), '\n'.join(errs)))
    print('원문 %d · 번역 %d · 막음 %d' % (len(src), len(ko), len(errs)))
    print('기호 ASCII:', dict(nfix) or '없음', '· 표기치환:', dict(nsub) or '없음')
    for e in errs[:20]:
        print('  ✗', e)
    if errs:
        raise SystemExit('★막힌 줄 — ko.tsv 안 씀')
    with open(os.path.join(ROOT, 'work', 'text', 'ko.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('번호\t위치\tEN\tKO\n')
        for r in out:
            w.write('\t'.join(r) + '\n')
    print('→ work/text/ko.tsv %d줄' % len(out))


if __name__ == '__main__':
    main()
