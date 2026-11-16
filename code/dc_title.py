# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, ssl, io, time, re, unicodedata, os
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'MetadataEnrichment/1.0 (mailto:researcher@example.org)'}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+>|&[a-z]+;|&#\d+;', ' ', s)
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

def g(u, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=50, context=ctx))
        except Exception as e:
            time.sleep(1.5+i*2)
    return None

rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]
MISS = set('1,2,3,4,7,9,10,11,12,13,17,18,19,21,23,24,26,28,30,31,33,34,35,38,39,40,42,43,44,45,50,51,52,53,54,56,57,58,60,66,68,69,70,71,72,73,76,77,78,79,80,82,93,94,95,96,98,99'.split(','))

out = {}
for r in rows:
    if r['seq'] not in MISS: continue
    q = (r['title'] or '')[:180]
    u = 'https://api.datacite.org/dois?page[size]=20&query=' + urllib.parse.quote(q)
    d = g(u)
    cands = []
    if d:
        for it in d.get('data', []):
            a = it['attributes']
            t = ((a.get('titles') or [{}])[0]).get('title') or ''
            ct = (a.get('container') or {}).get('title') or ''
            sc = sim(r['title'], t)
            cands.append({'score': round(sc,3), 'doi': a.get('doi'), 'title': t,
                          'journal': ct, 'year': a.get('publicationYear'),
                          'creators': [c.get('name') for c in (a.get('creators') or [])]})
    cands.sort(key=lambda x: -x['score'])
    out[r['seq']] = cands[:5]
    print('### %s | %s | %s' % (r['seq'], r['year'], (r['title'] or '')[:75]))
    for c in cands[:3]:
        print('    %.2f %s | %s | %s | %s' % (c['score'], c['doi'], c['year'], (c['journal'] or '')[:28], (c['title'] or '')[:65]))
    time.sleep(0.6)

json.dump(out, io.open('work/dc_title.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
