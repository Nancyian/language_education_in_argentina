# -*- coding: utf-8 -*-
"""Author-affiliation probe for the 311 newly added rows.
Sources: Dialnet article page (author block / institution links) then OpenAlex by title."""
import json, io, re, ssl, time, urllib.request, urllib.parse, difflib
from concurrent.futures import ThreadPoolExecutor

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def get(url, timeout=40, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1 + i)
    return ''

def dialnet_authors(codigo):
    h = get('https://dialnet.unirioja.es/servlet/articulo?codigo=%s' % codigo)
    if not h:
        return None
    # author links: /servlet/autor?codigo=NNN">Name</a>
    out = []
    for m in re.finditer(r'/servlet/autor\?codigo=\d+"[^>]*>([^<]{2,80})</a>', h):
        out.append(m.group(1).strip())
    return out

def openalex(title):
    q = urllib.parse.quote(title[:180])
    h = get('https://api.openalex.org/works?search=%s&per-page=3&mailto=corpus@example.com' % q, timeout=30)
    if not h:
        return None
    try:
        js = json.loads(h)
    except Exception:
        return None
    best, bs = None, 0.0
    for w in js.get('results', []):
        t = w.get('title') or w.get('display_name') or ''
        s = difflib.SequenceMatcher(None, t.lower(), title.lower()).ratio()
        if s > bs:
            best, bs = w, s
    if not best or bs < 0.82:
        return None
    insts = []
    for a in best.get('authorships', []):
        for ins in a.get('institutions', []):
            insts.append({'name': ins.get('display_name'), 'cc': ins.get('country_code'),
                          'type': ins.get('type'), 'author': (a.get('author') or {}).get('display_name')})
    return {'score': round(bs, 3), 'id': best.get('id'), 'insts': insts,
            'n_auth': len(best.get('authorships', []))}

def probe(rec):
    cod = rec['codigo']
    oa = openalex(rec['title'])
    return {'codigo': cod, 'title': rec['title'], 'authors': rec['authors'], 'loc': rec['loc'], 'openalex': oa}

if __name__ == '__main__':
    recs = json.load(io.open('work/final_new.json', encoding='utf-8'))
    done = {}
    try:
        for l in io.open('work/author_scope.jsonl', encoding='utf-8'):
            try:
                o = json.loads(l); done[o['codigo']] = o
            except Exception:
                pass
    except IOError:
        pass
    todo = [r for r in recs if r['codigo'] not in done]
    print('todo', len(todo), flush=True)
    f = io.open('work/author_scope.jsonl', 'a', encoding='utf-8')
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, o in enumerate(ex.map(probe, todo), 1):
            f.write(json.dumps(o, ensure_ascii=False) + '\n'); f.flush()
            if i % 20 == 0:
                print(i, flush=True)
    f.close()
    print('done', flush=True)
