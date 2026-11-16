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
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception:
            time.sleep(1.5+i*2)
    return None

rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]
INVALID = {'25','27','32'}

def best_in(recs, title, year=None, ytol=2):
    out=[]
    for w in recs:
        t=(w.get('title') or [''])[0]
        y=(w.get('issued',{}).get('date-parts') or [[None]])[0][0]
        sc=sim(title,t)
        if sc>=0.45:
            out.append({'score':round(sc,3),'doi':w.get('DOI'),'title':t,'year':y,
                        'journal':(w.get('container-title') or [''])[0],
                        'authors':[ (a.get('family') or '')+' '+(a.get('given') or '') for a in (w.get('author') or [])]})
    # prefer year match
    for o in out:
        if year and o['year'] and abs(int(o['year'])-int(year))<=ytol: o['score']=min(1.0, o['score']+0.15)
    out.sort(key=lambda x:-x['score'])
    return out[:4]

res={}
for r in rows:
    seq=r['seq']
    if r.get('doi'): continue
    if seq in INVALID: pass
    elif seq not in INVALID:
        # already resolved?
        pass
    found=None
    for issn in r.get('issns') or []:
        p='work/journals/%s.json'%(issn.replace('-',''))
        if os.path.exists(p):
            recs=json.load(io.open(p,encoding='utf-8'))
            b=best_in(recs, r['title'], r.get('year'))
            if b and (found is None or b[0]['score']>found[0]['score']):
                found=b
    if not found:
        # direct crossref query by ISSN
        for issn in (r.get('issns') or []):
            u=('https://api.crossref.org/works?rows=5&select=DOI,title,issued,container-title,author'
               '&filter=issn:'+issn+'&query.bibliographic='+urllib.parse.quote(r['title'][:150]))
            d=g(u)
            if d:
                b=best_in(d['message']['items'], r['title'], r.get('year'))
                if b and (found is None or b[0]['score']>found[0]['score']): found=b
            time.sleep(0.5)
    res[seq]=found or []
    print('### %s | %s | %s' % (seq, r.get('year'), (r['title'] or '')[:70]))
    if found:
        for c in found[:2]:
            print('    %.2f %s | %s | %s | %s' % (c['score'], c['doi'], c['year'], (c['journal'] or '')[:26], (c['title'] or '')[:62]))
    else:
        print('    (none)')
    time.sleep(0.4)

json.dump(res, io.open('work/cr_scoped.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
