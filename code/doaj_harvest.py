# -*- coding: utf-8 -*-
"""拉取 DOAJ 期刊全部文章，与目标行匹配。"""
import urllib.request, urllib.parse, json, ssl, time, io, re, unicodedata, html, sys, os

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'MetadataEnrichment/1.0'}

def g(u, tries=4):
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=50, context=ctx))
        except Exception as e:
            last = str(e)[:60]; time.sleep(2 + i * 2)
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

ISSNS = ['2340-9274', '2422-6459', '2591-541X', '1852-9615', '0718-7378', '1692-5777',
         '1851-4669', '1657-9089', '2314-2189', '1851-3115', '1852-4206',
         '1668-4753', '1697-4239', '2362-6194', '1405-6666', '1973-9370', '1850-0153']

corpus = []
os.makedirs('work/doaj', exist_ok=True)
for issn in ISSNS:
    cnt = 0
    for page in range(1, 12):
        u = 'https://doaj.org/api/search/articles/bibjson.journal.issns:%s?pageSize=100&page=%d' % (issn, page)
        d = g(u)
        if '__err__' in d:
            print('%-12s page%-2d ERR %s' % (issn, page, d['__err__'])); break
        tot = d.get('total', 0)
        rs = d.get('results', [])
        for r in rs:
            b = r.get('bibjson', {})
            dois = [i.get('id') for i in (b.get('identifier') or []) if i.get('type') == 'doi']
            corpus.append({'issn': issn, 'doi': dois[0] if dois else '', 'title': b.get('title') or '',
                           'year': b.get('year'), 'journal': (b.get('journal') or {}).get('title') or '',
                           'authors': '; '.join(a.get('name', '') for a in (b.get('author') or []))[:130],
                           'link': next((l.get('url') for l in (b.get('link') or []) if l.get('type') == 'fulltext'), '')})
        cnt += len(rs)
        if page * 100 >= tot or not rs: break
        time.sleep(0.35)
    print('%-12s articles=%d' % (issn, cnt))
    sys.stdout.flush()

json.dump(corpus, io.open('work/doaj_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('corpus', len(corpus))

# 匹配目标
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
best = {}
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    seq = p[0]
    t = unesc(meta.get(seq, {}).get('cit_title') or p[4])
    scored = []
    for c in corpus:
        s = sim(t, c['title'])
        if s >= 0.6:
            scored.append({**c, 'score': round(s, 3)})
    scored.sort(key=lambda x: -x['score'])
    best[seq] = scored[:3]
    if scored:
        print('=== seq %s | %s | %s' % (seq, p[1], t[:62]))
        for x in scored[:3]:
            print('     %.2f DOI=%-40s %-5s %-22s %s' % (x['score'], x['doi'] or '(none)', x['year'], (x['journal'] or '')[:22], x['title'][:58]))
json.dump(best, io.open('work/doaj_match.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
