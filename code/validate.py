# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, ssl, io, time, re, unicodedata

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
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception as e:
            time.sleep(1+i*1.5)
    return None

dois = []
for l in io.open('work/dois_resolved.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 4: dois.append((p[0], p[1], p[3]))

# add DataCite candidates
for seq, doi in [('38','10.5281/zenodo.5196039'), ('73','10.13140/rg.2.2.12967.93603'), ('82','10.5281/zenodo.10162214')]:
    dois.append((seq, doi, ''))

res = []
for seq, doi, title in dois:
    ok = None
    # 1) Crossref
    d = g('https://api.crossref.org/works/' + urllib.parse.quote(doi))
    if d and d.get('status') == 'ok':
        m = d['message']
        t = (m.get('title') or [''])[0]
        j = (m.get('container-title') or [''])[0]
        y = (m.get('issued', {}).get('date-parts') or [[None]])[0][0]
        ok = ('CR', t, j, y)
    else:
        # 2) DataCite
        d2 = g('https://api.datacite.org/dois/' + urllib.parse.quote(doi))
        if d2 and d2.get('data'):
            a = d2['data']['attributes']
            t = ((a.get('titles') or [{}])[0]).get('title') or ''
            j = (a.get('container') or {}).get('title') or ''
            y = a.get('publicationYear')
            ok = ('DC', t, j, y)
    if ok:
        sc = sim(title, ok[1]) if title else -1
        print('%3s OK%-2s %-42s sim=%.2f | %s | %s | %s' % (seq, ok[0], doi, sc, ok[3], (ok[2] or '')[:26], ok[1][:65]))
    else:
        print('%3s FAIL %-42s | %s' % (seq, doi, title[:60]))
    res.append({'seq':seq,'doi':doi,'reg':ok[0] if ok else None,'t':ok[1] if ok else None,'j':ok[2] if ok else None,'y':ok[3] if ok else None,'sim':(sim(title,ok[1]) if (ok and title) else None)})
    time.sleep(0.4)

json.dump(res, io.open('work/doi_validate.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
