# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, time, io, re, ssl, unicodedata

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'MetadataEnrichment/1.0 (mailto:researcher@example.org)'}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def crossref(query, rows=6):
    url = 'https://api.crossref.org/works?rows=%d&query.bibliographic=%s' % (rows, urllib.parse.quote(query))
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=40, context=ctx))['message']['items']
        except Exception as e:
            time.sleep(2+i*2)
    return []

def pick(title, items, journal=None):
    tn = norm(title)
    tw = set(w for w in tn.split() if len(w) > 4)
    best = None; bestscore = 0
    for it in items:
        ct = norm((it.get('title') or [''])[0])
        if not ct: continue
        cw = set(w for w in ct.split() if len(w) > 4)
        if not tw: continue
        ov = len(tw & cw) / max(1, len(tw))
        # containment bonus
        if tn and (tn in ct or ct in tn):
            ov = max(ov, 0.85)
        jc = norm((it.get('container-title') or [''])[0])
        if journal and norm(journal) and (norm(journal) in jc or jc in norm(journal)):
            ov += 0.15
        if ov > bestscore:
            bestscore = ov; best = it
    if best is not None and bestscore >= 0.6:
        return best, bestscore
    return None, bestscore

if __name__ == '__main__':
    recs = []
    for line in io.open('work/dialnet_meta.tsv', encoding='utf-8'):
        d = json.loads(line)
        t = d.get('cit_title') or d.get('h1') or ''
        if not t:
            recs.append(d); continue
        items = crossref(t)
        best, sc = pick(t, items, d.get('cit_journal'))
        d['cr_score'] = round(sc, 2)
        if best:
            d['cr_doi'] = best.get('DOI')
            d['cr_title'] = (best.get('title') or [''])[0]
            d['cr_journal'] = (best.get('container-title') or [''])[0]
            d['cr_year'] = (best.get('issued', {}).get('date-parts') or [[None]])[0][0]
            d['cr_authors'] = [' '.join(x for x in [a.get('given'), a.get('family')] if x) for a in best.get('author', [])]
            d['cr_vol'] = best.get('volume'); d['cr_issue'] = best.get('issue'); d['cr_page'] = best.get('page')
        recs.append(d)
        print(d['seq'], '|', sc, '|', d.get('cr_doi') or '-', '|', t[:55])
        time.sleep(0.6)
    with io.open('work/dialnet_meta_cr.tsv', 'w', encoding='utf-8') as f:
        for d in recs:
            f.write(json.dumps(d, ensure_ascii=False) + '\n')
