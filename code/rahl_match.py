# -*- coding: utf-8 -*-
"""Match RAHL corpus records to RAHL OJS article URLs via OAI-PMH harvest."""
import re, io, json, html, unicodedata

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s)
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+[^>]*>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 3]
    bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an in bn or bn in an: ov = max(ov, 0.95)
    return ov

x = io.open('work/rahl_oai.xml', encoding='utf-8').read()
recs = re.findall(r'<record>(.*?)</record>', x, re.S)
oai = []
for r in recs:
    t = re.search(r'<dc:title[^>]*>(.*?)</dc:title>', r, re.S)
    ids = re.findall(r'<dc:identifier>(.*?)</dc:identifier>', r)
    src = re.search(r'<dc:source[^>]*>(.*?)</dc:source>', r, re.S)
    oai.append({'title': unesc(t.group(1)).strip() if t else '',
                'url': ids[0] if ids else '',
                'source': unesc(src.group(1)).strip() if src else ''})

rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]
res = {}
for r in rows:
    if 'RAHL' not in (r.get('journal') or ''): continue
    best = []
    for o in oai:
        sc = sim(r['title'], o['title'])
        if sc > 0.40:
            best.append((sc, o['url'], o['title']))
    best.sort(reverse=True)
    res[r['seq']] = best[:3]
    print('### seq %s | %s | %s' % (r['seq'], r['year'], r['title'][:70]))
    for b in best[:3]:
        print('    %.2f %s | %s' % (b[0], b[1], b[2][:75]))

json.dump(res, io.open('work/rahl_matches.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('\ntotal RAHL', sum(1 for r in rows if 'RAHL' in (r.get('journal') or '')))
