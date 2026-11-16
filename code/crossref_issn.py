# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, time, io, re, ssl, unicodedata
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'MetadataEnrichment/1.0 (mailto:researcher@example.org)'}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'&[a-z]+;|&#\d+;', ' ', s)
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def issns(loc):
    out = []
    for m in re.finditer(r'ISSN[^0-9A-Za-z]{0,12}([0-9]{4}-[0-9]{3}[0-9Xx])', loc or ''):
        out.append(m.group(1).upper())
    return list(dict.fromkeys(out))

def cr(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=40, context=ctx))['message']
        except Exception as e:
            last=e; time.sleep(2+i*2)
    return None

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = set(w for w in an.split() if len(w) > 3)
    bw = set(w for w in bn.split() if len(w) > 3)
    if not aw or not bw: return 0.0
    ov = len(aw & bw) / len(aw)
    if an in bn or bn in an: ov = max(ov, 0.9)
    return ov

def work(d):
    title = d.get('cit_title') or ''
    iss = issns(d.get('loc'))
    best = None; bestsc = 0; src=''
    for i in iss:
        m = cr('https://api.crossref.org/works?rows=6&filter=issn:%s&query.bibliographic=%s' % (i, urllib.parse.quote(title)))
        if not m: continue
        for it in m.get('items', []):
            sc = sim(title, (it.get('title') or [''])[0])
            if sc > bestsc:
                bestsc = sc; best = it; src = 'issn:'+i
        time.sleep(0.3)
    if not iss:
        m = cr('https://api.crossref.org/works?rows=6&query.bibliographic=%s' % urllib.parse.quote(title))
        if m:
            for it in m.get('items', []):
                sc = sim(title, (it.get('title') or [''])[0])
                if sc > bestsc:
                    bestsc = sc; best = it; src='free'
    d['match_src'] = src
    d['match_score'] = round(bestsc, 3)
    d['issns'] = iss
    if best:
        d['m_doi'] = best.get('DOI')
        d['m_title'] = (best.get('title') or [''])[0]
        d['m_journal'] = (best.get('container-title') or [''])[0]
        d['m_year'] = (best.get('issued', {}).get('date-parts') or [[None]])[0][0]
        d['m_authors'] = [' '.join(x for x in [a.get('given'), a.get('family')] if x) for a in best.get('author', [])]
        d['m_vol'] = best.get('volume'); d['m_issue'] = best.get('issue'); d['m_page'] = best.get('page')
        d['m_type'] = best.get('type')
    return d

if __name__=='__main__':
    rows = [json.loads(l) for l in io.open('work/dialnet_meta_cr.tsv', encoding='utf-8')]
    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(work, rows):
            out.append(r)
            print(r['seq'], '|', r.get('match_score'), '|', r.get('m_doi') or '-', '|', r.get('match_src'), '|', (r.get('cit_title') or '')[:50], flush=True)
    with io.open('work/meta_doi.tsv', 'w', encoding='utf-8') as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False)+'\n')
    print('DONE', len(out))
