# -*- coding: utf-8 -*-
"""增量探测 ISSN：每次跑一批，结果累积写入 work/issn_found.json
用法: python find_issn2.py 0 10    # 处理名单第 0..9 个
"""
import io, json, os, sys, time
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
UA = {'User-Agent': 'corpus-builder/1.0 (mailto:research@example.org)'}
OUT = os.path.join(WORK, 'issn_found.json')

ARG_PUB = ('universidad nacional', 'universidad de buenos aires', 'universidad de la plata',
           'conicet', 'facultad de', 'universidad austral', 'universidad catolica argentina',
           'universidad del salvador', 'universidad de palermo', 'academia nacional',
           'sociedad argentina', 'instituto nacional', 'universidad provincial',
           'universidad nacional de la pampa', 'universidad nacional de cuyo',
           'universidad nacional del litoral', 'universidad nacional de rosario',
           'universidad nacional de cuyo', 'universidad nacional del sur',
           'universidad nacional de la patagonia', 'universidad nacional de misiones',
           'universidad nacional de salta', 'universidad nacional de tucuman',
           'universidad nacional de cordoba', 'universidad de flores', 'ediuns', 'eduuns')


def get(url, timeout=45):
    proxy = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:58354', 'https': 'http://127.0.0.1:58354'})
    op = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers=UA)
    with op.open(req, timeout=timeout) as f:
        return json.load(f)


def load():
    try:
        return json.load(io.open(OUT, encoding='utf-8'))
    except Exception:
        return {}


def main():
    names = json.load(io.open(os.path.join(WORK, 'target_names.json'), encoding='utf-8'))
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len(names)
    found = load()
    done = set(found.values())

    for nm in names[a:b]:
        if nm in done:
            print('%-50s SKIP done' % nm[:50])
            continue
        q = urllib.parse.quote(nm)
        try:
            d = get('https://api.crossref.org/journals?query=%s&rows=6' % q)
        except Exception as e:
            print('%-50s ERR %s' % (nm[:50], str(e)[:45]))
            time.sleep(4)
            continue
        hit = None
        cands = []
        for it in d['message']['items']:
            pub = (it.get('publisher') or '')
            issns = it.get('ISSN') or []
            if issns:
                cands.append((issns[0], pub))
                if any(k in pub.lower() for k in ARG_PUB):
                    hit = (issns[0], pub)
                    break
        if hit:
            found[hit[0]] = nm
            print('%-50s %s <- %s' % (nm[:50], hit[0], hit[1][:38]))
        else:
            print('%-50s --   %s' % (nm[:50], '; '.join(' '.join(c) for c in cands[:2])[:60]))
        io.open(OUT, 'w', encoding='utf-8').write(json.dumps(found, ensure_ascii=False, indent=1))
        time.sleep(0.8)

    print('\nfound total', len(found))


if __name__ == '__main__':
    main()
