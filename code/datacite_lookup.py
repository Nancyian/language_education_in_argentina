# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, time, io, re, ssl, unicodedata
from concurrent.futures import ThreadPoolExecutor

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
    if an in bn or bn in an: ov = max(ov, 0.93)
    return ov

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception:
            time.sleep(2+i*3)
    return None

def work(r):
    title = r['title']
    d = get('https://api.datacite.org/dois?page[size]=20&query=' + urllib.parse.quote(title))
    best=None; bs=0
    if d:
        for it in d.get('data', []):
            a=it['attributes']; t=(a.get('titles') or [{}])[0].get('title') or ''
            sc = sim(title, t)
            if sc > bs: bs=sc; best=(a.get('doi'), t, a.get('publicationYear'), a.get('publisher'))
    return {'seq': r['seq'], 'dc_score': round(bs,3),
            'dc_doi': (best or [None])[0], 'dc_title': (best or [None,None])[1],
            'dc_year': (best or [None,None,None])[2], 'dc_pub': (best or [None,None,None,None])[3]}

if __name__=='__main__':
    rows=[json.loads(l) for l in io.open('work/assembly.tsv',encoding='utf-8')]
    out=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        for o in ex.map(work, rows):
            out.append(o)
            print('%s|%s|%s|%s|%s' % (o['seq'], o.get('dc_score'), o.get('dc_doi') or '-', (o.get('dc_pub') or '')[:18], (o.get('dc_title') or '')[:60]), flush=True)
    json.dump(out, io.open('work/meta_dc.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE', len(out))
