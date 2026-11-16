# -*- coding: utf-8 -*-
import json, io, os, time, urllib.request, urllib.parse
os.environ['http_proxy']='http://127.0.0.1:58354'; os.environ['https_proxy']='http://127.0.0.1:58354'

def get(u):
    req = urllib.request.Request(u, headers={'User-Agent':'venue-check/1.0 (mailto:check@example.org)'})
    return json.load(urllib.request.urlopen(req, timeout=40))

data = json.load(io.open('work/expert_journals.json', encoding='utf-8'))
out = []
for name, n in data:
    q = name.split(':')[0].split('(')[0].strip()
    rec = {'journal': name, 'n': n, 'cands': []}
    try:
        d = get('https://api.crossref.org/journals?query=%s&rows=4' % urllib.parse.quote(q))
        for it in d['message']['items']:
            rec['cands'].append({
                'title': it.get('title',''),
                'publisher': it.get('publisher',''),
                'issn': it.get('ISSN', []),
            })
    except Exception as e:
        rec['err'] = str(e)[:80]
    out.append(rec)
    time.sleep(0.8)
json.dump(out, io.open('work/venue_verify.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
for r in out:
    print('==', r['n'], r['journal'])
    for c in r['cands'][:3]:
        print('    ', c['title'][:45], '|', c['publisher'][:60], '|', (c['issn'][:2] if c['issn'] else ''))
    if r.get('err'): print('    ERR', r['err'])
