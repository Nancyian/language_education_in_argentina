# -*- coding: utf-8 -*-
"""Fetch Dialnet article pages for new candidates: metadata + abstract."""
import json, io, re, time, os, ssl, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
HDR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}
TAG = re.compile(r'<[^>]+>')

def clean(s):
    s = TAG.sub(' ', s)
    for a, b in [('&amp;', '&'), ('&quot;', '"'), ('&#39;', "'"), ('&lt;', '<'), ('&gt;', '>'),
                 ('&nbsp;', ' '), ('&aacute;', 'á'), ('&eacute;', 'é'), ('&iacute;', 'í'),
                 ('&oacute;', 'ó'), ('&uacute;', 'ú'), ('&ntilde;', 'ñ'), ('&uuml;', 'ü')]:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()

def fetch(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return urllib.request.urlopen(req, timeout=45, context=CTX).read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1.2 + i * 1.8)
    return ''

def parse(html):
    d = {}
    metas = {}
    for m in re.finditer(r'<meta\s+([^>]+?)/?>', html, re.I):
        attrs = dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', m.group(1)))
        n = (attrs.get('name') or attrs.get('property') or '').lower()
        if n:
            metas.setdefault(n, []).append((attrs, attrs.get('content', '')))
    g = lambda k: (metas.get(k, [('', '')])[0][1])
    d['title'] = clean(g('citation_title'))
    d['authors'] = [clean(v) for a, v in metas.get('citation_author', [])]
    d['journal'] = clean(g('citation_journal_title'))
    d['date'] = g('citation_date')
    d['doi'] = g('citation_doi')
    d['issn'] = ','.join(v for a, v in metas.get('citation_issn', []))
    d['pdf'] = g('citation_pdf_url')
    # abstracts: DC.description with xml:lang
    abst = []
    for a, v in metas.get('dc.description', []):
        lang = (a.get('xml:lang') or a.get('lang') or '').lower()
        t = clean(v)
        if len(t) > 60:
            abst.append((lang, t))
    seen, keep = set(), []
    for lang, t in sorted(abst, key=lambda x: 0 if x[0].startswith('es') else 1):
        if t not in seen:
            seen.add(t)
            keep.append(t)
    d['abstract'] = ' '.join(keep)
    # localization
    loc = ''
    for c in re.findall(r'Localizaci[óo]n:\s*<[^>]*>(.*?)</(?:p|div)>', html, re.S):
        cc = clean(c)
        if any(k in cc for k in ('págs', 'Vol', 'Nº', 'ISSN', 'Núm')):
            loc = cc
            break
    if not loc:
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
        if m:
            loc = clean(m.group(1)).replace('Información del artículo ', '')
    d['loc'] = loc
    if not d['doi']:
        m = re.search(r'(?i)\bDOI\b[:\s]*(?:</?[a-zA-Z][^>]*>)*\s*(10\.\d{4,9}/[^\s"<&]+)', html)
        if m:
            d['doi'] = m.group(1).rstrip('.').rstrip(',')
    return d

def work(c):
    url = 'https://dialnet.unirioja.es/servlet/articulo?codigo=' + c['codigo']
    h = fetch(url)
    if not h:
        return dict(codigo=c['codigo'], error='fetch')
    d = parse(h)
    d['codigo'] = c['codigo']
    d['kws'] = c['kws']
    d['title_match'] = c.get('title_match', [])
    d['list_title'] = c['title']
    d['list_loc'] = c['loc']
    return d

if __name__ == '__main__':
    import sys
    cands = json.load(io.open(sys.argv[1] if len(sys.argv) > 1 else 'work/final_new.json', encoding='utf-8'))
    done = {}
    if os.path.exists('work/new_meta.jsonl'):
        for line in io.open('work/new_meta.jsonl', encoding='utf-8'):
            try:
                r = json.loads(line)
                done[r['codigo']] = r
            except Exception:
                pass
    todo = [c for c in cands if c['codigo'] not in done]
    print('candidates', len(cands), '| already', len(done), '| todo', len(todo), flush=True)
    f = io.open('work/new_meta.jsonl', 'a', encoding='utf-8')
    with ThreadPoolExecutor(max_workers=5) as ex:
        for i, d in enumerate(ex.map(work, todo), 1):
            f.write(json.dumps(d, ensure_ascii=False) + '\n')
            if i % 25 == 0:
                f.flush()
                print('  %d/%d' % (i, len(todo)), flush=True)
    f.close()
    print('done')
