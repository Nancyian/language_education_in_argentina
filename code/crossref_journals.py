# -*- coding: utf-8 -*-
import urllib.error
import urllib.request, urllib.parse, json, time, io, re, ssl, unicodedata, os

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'MetadataEnrichment/1.0 (mailto:researcher@example.org)'}

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+>|&[a-z]+;|&#\d+;', ' ', s)
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
    if an[:22] and an[:22] == bn[:22]: ov = max(ov, 0.9)
    return ov

def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=60, context=ctx))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(10+i*10); continue
            time.sleep(3+i*3)
        except Exception:
            time.sleep(3+i*3)
    return None

def dump_journal(issn):
    out=[]; cursor='*'
    while True:
        url=('https://api.crossref.org/works?filter=issn:%s&rows=500&cursor=%s'
             '&select=DOI,title,author,container-title,issued,volume,issue,page,type,ISSN'
             % (issn, urllib.parse.quote(cursor)))
        d=get(url)
        if not d: break
        items=d['message'].get('items',[])
        out.extend(items)
        cursor=d['message'].get('next-cursor')
        if not items or not cursor or len(out)>=3000: break
        time.sleep(0.7)
    return out

if __name__=='__main__':
    rows=[json.loads(l) for l in io.open('work/assembly.tsv',encoding='utf-8')]
    issn_set=set()
    for r in rows:
        for i in r.get('issns') or []: issn_set.add(i.upper())
    print('journals/issns:', len(issn_set))
    os.makedirs('work/journals', exist_ok=True)
    cache={}
    for i in sorted(issn_set):
        fp='work/journals/%s.json' % i.replace('-','')
        if os.path.exists(fp):
            cache[i]=json.load(io.open(fp,encoding='utf-8'))
            print('cached', i, len(cache[i])); continue
        w=dump_journal(i)
        cache[i]=w
        json.dump(w, io.open(fp,'w',encoding='utf-8'), ensure_ascii=False)
        print('dumped', i, len(w), flush=True)
    # match
    res={}
    for r in rows:
        best=None; bs=0; bj=''
        for i in (r.get('issns') or []):
            for w in cache.get(i.upper(), []):
                sc=sim(r['title'], (w.get('title') or [''])[0])
                if sc>bs: bs=sc; best=w
        if best and bs>=0.62:
            res[r['seq']]={'doi':best.get('DOI'),'score':round(bs,3),
                'title':(best.get('title') or [''])[0],
                'journal':(best.get('container-title') or [''])[0],
                'year':(best.get('issued',{}).get('date-parts') or [[None]])[0][0],
                'authors':[' '.join(x for x in [a.get('given'),a.get('family')] if x) for a in best.get('author',[])],
                'vol':best.get('volume'),'issue':best.get('issue'),'page':best.get('page')}
    json.dump(res, io.open('work/journal_matches.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print('MATCHED', len(res))
    for r in rows:
        m=res.get(r['seq'])
        print('%s|%s|%s|%s|%s' % (r['seq'], (m or {}).get('score'), (m or {}).get('doi') or '-', (m or {}).get('journal') or '', r['title'][:45]))
