# -*- coding: utf-8 -*-
import json, io, re, unicodedata, os


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0
    aw = [w for w in an.split() if len(w) > 3]; bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an in bn or bn in an: ov = max(ov, 0.93)
    return ov


rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]
targets = set(int(x) for x in os.environ.get('T', '').split(',') if x.strip())
if not targets:
    targets = set(int(r['seq']) for r in rows if not r.get('doi'))

for r in rows:
    if int(r['seq']) not in targets:
        continue
    best = []
    for i in r['issns']:
        p = 'work/journals/%s.json' % i.replace('-', '')
        if not os.path.exists(p):
            continue
        for w in json.load(io.open(p, encoding='utf-8')):
            sc = sim(r['title'], (w.get('title') or [''])[0])
            if sc > 0.3:
                best.append((sc, w.get('DOI'), (w.get('issued', {}).get('date-parts') or [[None]])[0][0], (w.get('title') or [''])[0]))
    best.sort(reverse=True)
    print('### seq %s | y=%s | %s' % (r['seq'], r['year'], r['title'][:65]))
    for b in best[:3]:
        print('     %.2f  %s  %s  %s' % (b[0], b[1], b[2], b[3][:72]))
