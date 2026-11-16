# -*- coding: utf-8 -*-
"""Crossref 按阿根廷期刊 ISSN 定向拉取，输出 work/cr_argjr.json"""
import io, json, os, sys, time
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
MAILTO = 'research@example.org'

JOURNALS = {
    '2340-9274': 'Estudios Interlingüísticos',
    '2422-6459': 'Revista Entramados',
    '2591-541X': 'Quintú Quimün',
    '1852-9615': 'Cuadernos del CILHA',
    '1851-4669': 'Anclajes',
    '2314-2189': 'Signo y Seña',
    '1851-3115': 'Revista Pilquen: Sección Psicopedagogía',
    '1852-4206': 'Revista Argentina de Ciencias del Comportamiento',
}


def get(url, timeout=60):
    proxy = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:58354', 'https': 'http://127.0.0.1:58354'})
    opener = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers={'User-Agent': 'corpus-builder/1.0 (mailto:%s)' % MAILTO})
    with opener.open(req, timeout=timeout) as f:
        return json.load(f)


def main():
    out = []
    for issn, name in JOURNALS.items():
        for attempt in range(3):
            try:
                d = get('https://api.crossref.org/journals/%s/works?rows=1000&select=title,author,container-title,issued,DOI'
                        % issn)
                items = d['message']['items']
                print('%-14s %-45s %d items' % (issn, name[:45], len(items)))
                for it in items:
                    t = (it.get('title') or [''])[0]
                    if not t:
                        continue
                    yr = None
                    try:
                        yr = it['issued']['date-parts'][0][0]
                    except Exception:
                        pass
                    out.append({'db': 'Crossref', 'kw': '阿根廷期刊定向检索',
                                'title': t, 'authors': '; '.join(
                                    (a.get('given', '') + ' ' + a.get('family', '')).strip()
                                    for a in it.get('author', [])),
                                'venue': name, 'year': yr,
                                'abstract': '', 'url': 'https://doi.org/' + it.get('DOI', '')})
                break
            except Exception as e:
                print('%s attempt%d ERR %s' % (issn, attempt + 1, str(e)[:80]))
                time.sleep(6)
        time.sleep(1)
    io.open(os.path.join(WORK, 'cr_argjr.json'), 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print('total', len(out))


if __name__ == '__main__':
    main()
