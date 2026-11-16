# -*- coding: utf-8 -*-
import urllib.request, re, time, json, ssl, io
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

def fetch(url, tries=5):
    last=None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return urllib.request.urlopen(req, timeout=30, context=ctx).read().decode('utf-8','ignore')
        except Exception as e:
            last=e; time.sleep(1.5+i*2)
    raise last

def clean(s):
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    for a,b in [('&amp;','&'),('&quot;','"'),('&#39;',"'"),('&lt;','<'),('&gt;','>'),('&nbsp;',' '),('&aacute;','á'),('&eacute;','é'),('&iacute;','í'),('&oacute;','ó'),('&uacute;','ú'),('&ntilde;','ñ')]:
        s = s.replace(a,b)
    return re.sub(r'\s+',' ',s).strip()

def parse(html):
    d={}; metas={}
    for m in re.finditer(r'<meta\s+([^>]+?)/?>', html, re.I):
        attrs=dict(re.findall(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', m.group(1)))
        n=(attrs.get('name') or attrs.get('property') or '').lower()
        if n: metas.setdefault(n,[]).append(attrs.get('content',''))
    g=lambda k: metas.get(k,[''])[0]
    d['cit_title']=clean(g('citation_title'))
    d['cit_authors']=[clean(x) for x in metas.get('citation_author',[])]
    d['cit_journal']=clean(g('citation_journal_title'))
    d['cit_date']=g('citation_publication_date')
    d['cit_volume']=g('citation_volume'); d['cit_issue']=g('citation_issue')
    d['cit_fp']=g('citation_firstpage'); d['cit_lp']=g('citation_lastpage')
    d['cit_doi']=g('citation_doi'); d['cit_issn']=g('citation_issn')
    # localization: first occurrence AFTER <h1 or inside main info block; take the one containing 'págs' or 'Vol'
    cands = re.findall(r'Localizaci[óo]n:\s*<[^>]*>(.*?)</p>', html, re.S)
    loc=''
    for c in cands:
        cc=clean(c)
        if 'Localizaci' in cc or 'págs' in cc or 'Vol' in cc or 'Nº' in cc or 'ISSN' in cc:
            loc=cc; break
    if not loc and cands: loc=clean(cands[0])
    d['loc']=loc
    # year candidates
    yrs = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', loc)
    d['loc_years']=yrs
    # DOI fallback
    if not d['cit_doi']:
        m=re.search(r'(?i)\bDOI\b[:\s]*(?:</?[a-zA-Z][^>]*>)*\s*(10\.\d{4,9}/[^\s"<&]+)', html)
        if m: d['cit_doi']=m.group(1).rstrip('.').rstrip(',')
    # links
    d['links']=list(dict.fromkeys(re.findall(r'href="(https?://[^"]+)"', html)))
    return d

def work(args):
    row, seq, src = args
    cod = re.search(r'codigo=(\d+)', src).group(1)
    url='https://dialnet.unirioja.es/servlet/articulo?codigo='+cod
    try:
        d=parse(fetch(url)); d.update({'row':row,'seq':seq,'codigo':cod,'url':url})
    except Exception as e:
        d={'row':row,'seq':seq,'codigo':cod,'url':url,'error':str(e)}
    return d

if __name__=='__main__':
    ids=[l.rstrip('\n').split('\t') for l in io.open('work/match_result.tsv',encoding='utf-8') if l.strip()]
    results={}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for d in ex.map(work, ids):
            results[d['row']]=d
            print(d['row'], d['seq'], '|', d.get('cit_doi') or '-', '|', d.get('loc','')[:100], flush=True)
    with io.open('work/meta_full.tsv','w',encoding='utf-8') as f:
        for l in ids:
            f.write(json.dumps(results[l[0]], ensure_ascii=False)+'\n')
    print('TOTAL', len(results))
