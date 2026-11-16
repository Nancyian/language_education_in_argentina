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

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 3]
    bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an in bn or bn in an: ov = max(ov, 0.92)
    # prefix match of first 12 chars
    if an[:18] and an[:18] == bn[:18]: ov = max(ov, 0.9)
    return ov

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception as e:
            last=e; time.sleep(2+i*2)
    return None

def work(d):
    title = d.get('cit_title') or ''
    iss = set((d.get('issns') or []))
    inp = set(x.upper() for x in (d.get('issns') or []))
    url = 'https://api.openalex.org/works?per-page=8&mailto=researcher@example.org&search=' + urllib.parse.quote(title)
    r = get(url)
    best=None; bestsc=0; bestinfo=None
    if r:
        for w in r.get('results', []):
            sc = sim(title, w.get('title') or '')
            loc = w.get('primary_location') or {}
            srco = loc.get('source') or {}
            siss = set(x.upper() for x in (srco.get('issn') or []))
            if inp and siss and (inp & siss): sc += 0.2
            if sc > bestsc:
                bestsc=sc; best=w; bestinfo={'issn':sorted(siss),'journal':srco.get('display_name')}
    out = {'seq': d['seq'], 'row': d['row'], 'cit_title': title, 'cit_journal': d.get('cit_journal'),
           'oa_score': round(bestsc,3)}
    if best:
        out['oa_doi'] = (best.get('doi') or '').replace('https://doi.org/','')
        out['oa_title'] = best.get('title')
        out['oa_journal'] = bestinfo['journal']
        out['oa_journal_issn'] = bestinfo['issn']
        out['oa_year'] = best.get('publication_year')
        out['oa_authors'] = [a['author']['display_name'] for a in best.get('authorships', [])]
        bib = best.get('biblio') or {}
        out['oa_vol'] = bib.get('volume'); out['oa_issue'] = bib.get('issue')
        out['oa_fp'] = bib.get('first_page'); out['oa_lp'] = bib.get('last_page')
        out['oa_type'] = best.get('type')
    return out

if __name__=='__main__':
    rows=[json.loads(l) for l in io.open('work/meta_doi.tsv',encoding='utf-8')]
    res=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for o in ex.map(work, rows):
            res.append(o)
            print(o['seq'],'|',o.get('oa_score'),'|',o.get('oa_doi') or '-','|',(o.get('oa_journal') or '')[:32],'|',o['cit_title'][:48], flush=True)
    with io.open('work/meta_oa.tsv','w',encoding='utf-8') as f:
        for o in res: f.write(json.dumps(o,ensure_ascii=False)+'\n')
    print('DONE', len(res))
