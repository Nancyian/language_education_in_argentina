# -*- coding: utf-8 -*-
"""按出版商判定阿根廷期刊 ISSN。输入 work/target_names.json，输出 work/issn_found.json"""
import io, json, os, sys, time
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
UA = {'User-Agent': 'corpus-builder/1.0 (mailto:research@example.org)'}

ARG_PUB = ('universidad nacional', 'universidad de buenos aires', 'universidad de la plata',
           'conicet', 'facultad de', 'universidad de flores', 'universidad austral',
           'universidad catolica argentina', 'universidad del salvador', 'universidad de palermo',
           'universidad de san andres', 'academia nacional', 'sociedad argentina',
           'instituto nacional', 'ministerio de educacion', 'universidad provincial',
           'universidad nacional de la pampa', 'universidad nacional de cuyo',
           'universidad nacional del litoral', 'universidad nacional de rosario')


def get(url, timeout=60):
    proxy = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:58354', 'https': 'http://127.0.0.1:58354'})
    op = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers=UA)
    with op.open(req, timeout=timeout) as f:
        return json.load(f)


def probe(name, tries=3):
    q = urllib.parse.quote(name)
    d = None
    for t in range(tries):
        try:
            d = get('https://api.crossref.org/journals?query=%s&rows=6' % q)
            break
        except Exception as e:
            if t == tries - 1:
                return None, 'ERR %s' % str(e)[:50]
            time.sleep(6)
    cands = []
    for it in d['message']['items']:
        pub = (it.get('publisher') or '')
        issns = it.get('ISSN') or []
        if not issns:
            continue
        cands.append({'issn': issns[0], 'publisher': pub})
    for c in cands:
        if any(k in c['publisher'].lower() for k in ARG_PUB):
            return c, 'ok'
    return None, 'noARG(%s)' % ('; '.join(c['publisher'][:24] for c in cands[:2]) or 'empty')


def main():
    names = json.load(io.open(os.path.join(WORK, 'target_names.json'), encoding='utf-8'))
    found = {}
    for nm in names:
        r, st = probe(nm)
        if r:
            found[r['issn']] = nm
            print('%-52s %s  <- %s' % (nm[:52], r['issn'], r['publisher'][:42]))
        else:
            print('%-52s --   %s' % (nm[:52], st))
        time.sleep(1.2)
    io.open(os.path.join(WORK, 'issn_found.json'), 'w', encoding='utf-8').write(
        json.dumps(found, ensure_ascii=False, indent=1))
    print('\nfound', len(found))


if __name__ == '__main__':
    main()
