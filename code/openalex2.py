# -*- coding: utf-8 -*-
import urllib.request, urllib.error, urllib.parse, json, time, io, re, ssl, unicodedata
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

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 3]
    bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an in bn or bn in an: ov = max(ov, 0.93)
    if an[:20] and an[:20] == bn[:20]: ov = max(ov, 0.9)
    return ov

def get(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except urllib.error.HTTPError as e:
            last=e
            if e.code == 429:
                time.sleep(6 + i*6); continue
            time.sleep(2+i*2)
        except Exception as e:
            last=e; time.sleep(2+i*2)
    return None

def jnorm(s):
    s = re.sub(r'^(rahl|gist|signos ele|integracion y conocimiento|revista sobre estudios e investigaciones|ciencia e interculturalidad|anuario de letras|magis|revista latinoamericana de educacion)[:.,]?\s*', '', norm(s))
    return s

def jmatch(a, b):
    na, nb = jnorm(a), jnorm(b)
    if not na or not nb: return False
    na2 = na.replace(' ', ''); nb2 = nb.replace(' ', '')
    if na2[:16] in nb2 or nb2[:16] in na2: return True
    aw = set(w for w in na.split() if len(w) > 4); bw = set(w for w in nb.split() if len(w) > 4)
    if aw and bw and len(aw & bw)/max(1,min(len(aw),len(bw))) >= 0.6: return True
    return False

REPO = ('dialnet','repositorio','la referencia','americanae','conicet','archive ouverte','zenodo','redalyc','scielo','citeseer','core','semantic','dspace','ri.conicet')

def work(d):
    title = d['title']; journal = d['journal']; issns = d.get('issns') or []
    year = d.get('year')
    cands = []
    for url in [
        'https://api.openalex.org/works?per-page=25&mailto=researcher@example.org&search=' + urllib.parse.quote(title),
        'https://api.openalex.org/works?per-page=25&mailto=researcher@example.org&filter=title.search:' + urllib.parse.quote(title.split(':')[0][:120]),
    ]:
        r = get(url)
        if r: cands.extend(r.get('results', []))
    seen = {}
    for w in cands:
        doi = (w.get('doi') or '').replace('https://doi.org/','')
        if not doi: continue
        seen[doi] = w
    best=None; bestsc=0; info=None
    for doi, w in seen.items():
        sc = sim(title, w.get('title') or '')
        loc = w.get('primary_location') or {}
        srco = loc.get('source') or {}
        sj = srco.get('display_name') or ''
        siss = set(x.upper() for x in (srco.get('issn') or []))
        jm = jmatch(journal, sj) or (bool(siss) and bool(set(i.upper() for i in issns) & siss))
        yr = w.get('publication_year')
        yr_ok = (not year) or (not yr) or abs(yr-year) <= 1
        if jm and yr_ok: sc += 0.25
        if sc > bestsc:
            bestsc=sc; best=w; info={'j':sj,'jm':jm,'yr':yr,'iss':sorted(siss)}
    out = {'seq': d['seq'], 'row': d['row'], 'title': title, 'journal': journal,
           'oa2_score': round(bestsc,3)}
    if best:
        out['oa2_doi'] = (best.get('doi') or '').replace('https://doi.org/','')
        out['oa2_j'] = info['j']; out['oa2_jmatch']=info['jm']; out['oa2_year']=info['yr']; out['oa2_iss']=info['iss']
        out['oa2_title'] = best.get('title')
        out['oa2_authors'] = [a['author']['display_name'] for a in best.get('authorships', [])]
    return out

if __name__=='__main__':
    rows=[json.loads(l) for l in io.open('work/assembly.tsv',encoding='utf-8')]
    res=[]
    with ThreadPoolExecutor(max_workers=2) as ex:
        for o in ex.map(work, rows):
            res.append(o)
            jm = o.get('oa2_jmatch')
            print('%s|%s|%s|%s|%s|%s' % (o['seq'], o.get('oa2_score'), 'JM' if jm else '--', o.get('oa2_doi') or '-', (o.get('oa2_j') or '')[:26], o['title'][:42]), flush=True)
    with io.open('work/meta_oa2.tsv','w',encoding='utf-8') as f:
        for o in res: f.write(json.dumps(o,ensure_ascii=False)+'\n')
    print('DONE', len(res))
