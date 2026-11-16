import urllib.request, urllib.parse, json, ssl, io, time, sys, re, unicodedata

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def g(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'MetadataEnrichment/1.0'})
    return json.load(urllib.request.urlopen(req, timeout=50, context=ctx))

def unesc(s):
    import html
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or ''); s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
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

allr = {}
queries = ['relatedIdentifiers.relatedIdentifier:2591-541X',
           'publisher:"Universidad Nacional del Comahue"']
for q in queries:
    for page in range(1, 8):
        u = 'https://api.datacite.org/dois?page[size]=100&page[number]=%d&query=%s' % (page, urllib.parse.quote(q))
        try:
            d = g(u)
        except Exception as e:
            print(q, 'ERR', str(e)[:50]); break
        tot = d['meta']['total']
        if page == 1: print('QUERY:', q, '-> total', tot)
        for it in d['data']:
            a = it['attributes']
            t = ((a.get('titles') or [{}])[0]).get('title') or ''
            allr[a.get('doi')] = {'title': t, 'year': a.get('publicationYear'),
                                  'pub': a.get('publisher'),
                                  'creators': '; '.join(c.get('name', '') for c in (a.get('creators') or []))[:130]}
        if page * 100 >= tot: break
        time.sleep(0.3)

print('unique', len(allr))
json.dump(allr, io.open('work/dc_qq.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for doi, v in sorted(allr.items()):
    print(' ', doi, '|', v['year'], '|', v['title'][:88])
