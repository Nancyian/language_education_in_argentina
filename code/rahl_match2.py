# -*- coding: utf-8 -*-
import json, io, re, unicodedata, html

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
    aw = [w for w in an.split() if len(w) > 3]; bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw)/len(aw)
    if an in bn or bn in an: ov = max(ov, 0.95)
    return ov

cands = json.load(io.open('work/rahl_all.json', encoding='utf-8'))
rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]

res = {}
for r in rows:
    if 'RAHL' not in (r.get('journal') or ''): continue
    auth = (r.get('authors') or '')
    scored = []
    for c in cands:
        s = sim(r['title'], c['title'])
        # author bonus
        for a in (c.get('creators') or []):
            sn = norm(a).split(',')[0]
            if sn and sn in norm(auth): s = min(1.0, s + 0.12)
        scored.append((round(s,3), c['url'], c['title'], '; '.join(c.get('creators') or [])))
    scored.sort(reverse=True)
    res[r['seq']] = scored[:3]
    print('### %s | %s | %s' % (r['seq'], r['year'], (r['title'] or '')[:68]))
    for s in scored[:2]:
        print('    %.2f %s | %s | %s' % (s[0], s[1], s[3][:28], s[2][:62]))

json.dump(res, io.open('work/rahl_final.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
