# -*- coding: utf-8 -*-
"""DOAJ 文章检索：按标题查 DOI。"""
import urllib.request, urllib.parse, json, ssl, time, io, re, unicodedata, html, sys

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'MetadataEnrichment/1.0'}

def g(u, tries=3):
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception as e:
            last = str(e)[:60]; time.sleep(1.5 + i * 2)
    return {'__err__': last}

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or ''); s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'<[^>]+>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

STOP = set('de la el los las un una y en del al para por con sobre como su sus desde entre the of and a to in on for with'.split())

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 2 and w not in STOP]
    bw = set(bn.split())
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an == bn: ov = 1.0
    elif an in bn or bn in an: ov = max(ov, 0.94)
    return ov

def doaj_articles(query, page_size=20):
    u = 'https://doaj.org/api/search/articles/%s?pageSize=%d' % (urllib.parse.quote(query, safe=''), page_size)
    d = g(u)
    if '__err__' in d: return []
    out = []
    for r in d.get('results', []):
        b = r.get('bibjson', {})
        t = b.get('title') or ''
        dois = [i.get('id') for i in (b.get('identifier') or []) if i.get('type') == 'doi']
        jr = (b.get('journal') or {})
        yr = b.get('year')
        out.append({'doi': dois[0] if dois else '', 'title': t, 'year': yr,
                    'journal': jr.get('title') or '', 'issn': (jr.get('issns') or [''])[0],
                    'authors': '; '.join(a.get('name', '') for a in (b.get('author') or []))[:120]})
    return out

# 目标行: seq, title(实测标题)
targets = []
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    seq = p[0]
    t = unesc(meta.get(seq, {}).get('cit_title') or p[4])
    targets.append({'seq': seq, 'title': t, 'year': p[1], 'journal': p[3], 'issns': p[2]})

res = {}
for t in targets:
    hits = []
    # 按标题检索
    for q in ['bibjson.title:"%s"' % t['title'].replace('"', '')]:
        hits += doaj_articles(q, 10)
        time.sleep(0.3)
    scored = []
    for h in hits:
        sc = sim(t['title'], h['title'])
        scored.append({**h, 'score': round(sc, 3)})
    scored.sort(key=lambda x: -x['score'])
    good = [x for x in scored if x['score'] >= 0.6 and x['doi']]
    res[t['seq']] = good[:3]
    if good:
        print('=== seq %s | %s | %s' % (t['seq'], t['year'], t['title'][:70]))
        for x in good[:3]:
            print('     %.2f %-42s %-5s %-24s %s' % (x['score'], x['doi'], x['year'], (x['journal'] or '')[:24], (x['title'] or '')[:60]))
    sys.stdout.flush()

json.dump(res, io.open('work/doaj_hits.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE, rows with hits:', sum(1 for v in res.values() if v))
