# -*- coding: utf-8 -*-
"""按 ISSN 批量拉取 Crossref 全量论文，输出 work/cr_argjr2.json"""
import io, json, os, sys, time
import urllib.request
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
UA = {'User-Agent': 'corpus-builder/1.0 (mailto:research@example.org)'}

# 人工核对后的阿根廷期刊 ISSN（剔除误配）
TARGETS = {
    '1668-7426': 'Cuadernos del Sur Letras',
    '0328-9702': 'Praxis Educativa',
    '2314-3932': 'Contextos de Educación',
    '1669-3914': 'Revista Pilquen',
    '2362-6194': 'Traslaciones',
    '1666-8146': 'Temas de Historia Argentina y Americana',
    '0556-5960': 'Revista de Historia Americana y Argentina',
    '0325-772X': 'Res Gesta',
    '2250-4001': 'Estudios Rurales',
    '0329-0573': 'Huellas',
    '1853-0494': 'Epistemus',
    '0326-2774': 'Prudentia Iuris',
    '1668-950X': 'Anuario del Instituto de Historia Argentina',
}

OUT = os.path.join(WORK, 'cr_argjr2.json')


def get(url, timeout=60):
    proxy = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:58354', 'https': 'http://127.0.0.1:58354'})
    op = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers=UA)
    with op.open(req, timeout=timeout) as f:
        return json.load(f)


def main():
    try:
        out = json.load(io.open(OUT, encoding='utf-8'))
    except Exception:
        out = []
    have = set(x.get('issn') for x in out)

    only = sys.argv[1:] if len(sys.argv) > 1 else list(TARGETS)
    for issn in only:
        name = TARGETS.get(issn, issn)
        if issn in have:
            print('%-12s SKIP' % issn)
            continue
        got = []
        for attempt in range(3):
            try:
                d = get('https://api.crossref.org/journals/%s/works?rows=1000'
                        '&select=title,author,container-title,issued,DOI,abstract' % issn,
                        timeout=90)
                got = d['message']['items']
                break
            except Exception as e:
                print('  %s attempt%d ERR %s' % (issn, attempt + 1, str(e)[:55]))
                time.sleep(7)
        print('%-12s %-46s %d' % (issn, name[:46], len(got)))
        for it in got:
            t = (it.get('title') or [''])[0]
            if not t:
                continue
            yr = None
            try:
                yr = it['issued']['date-parts'][0][0]
            except Exception:
                pass
            out.append({'db': 'Crossref', 'issn': issn, 'kw': '阿根廷期刊 ISSN 定向',
                        'title': t,
                        'authors': '; '.join((a.get('given', '') + ' ' + a.get('family', '')).strip()
                                             for a in it.get('author', [])),
                        'venue': name, 'year': yr,
                        'abstract': (it.get('abstract') or '')[:1500],
                        'url': 'https://doi.org/' + it.get('DOI', '')})
        io.open(OUT, 'w', encoding='utf-8').write(
            json.dumps(out, ensure_ascii=False, indent=1))
        time.sleep(1.5)
    print('total', len(out))


if __name__ == '__main__':
    main()
