# -*- coding: utf-8 -*-
import urllib.request, re, time, os, json, ssl, io, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HDR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

def fetch(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return urllib.request.urlopen(req, timeout=45, context=ctx).read().decode('utf-8', 'ignore')
        except Exception as e:
            last = e
            time.sleep(2 + i * 3)
    raise last

def clean(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'").replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', s).strip()

def parse(html):
    d = {}
    # citation meta
    metas = {}
    for m in re.finditer(r'<meta\s+([^>]+?)/?>', html, re.I):
        attrs = dict(re.findall(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', m.group(1)))
        n = (attrs.get('name') or attrs.get('property') or '').lower()
        if n:
            metas.setdefault(n, []).append(attrs.get('content', ''))
    d['cit_title'] = metas.get('citation_title', [''])[0]
    d['cit_authors'] = metas.get('citation_author', [])
    d['cit_journal'] = metas.get('citation_journal_title', [''])[0]
    d['cit_date'] = metas.get('citation_publication_date', [''])[0]
    d['cit_volume'] = metas.get('citation_volume', [''])[0]
    d['cit_issue'] = metas.get('citation_issue', [''])[0]
    d['cit_fp'] = metas.get('citation_firstpage', [''])[0]
    d['cit_lp'] = metas.get('citation_lastpage', [''])[0]
    d['cit_doi'] = metas.get('citation_doi', [''])[0]
    d['cit_issn'] = metas.get('citation_issn', [''])[0]
    d['cit_pdf'] = metas.get('citation_pdf_url', [''])[0]
    # DOI anywhere
    if not d['cit_doi']:
        m = re.search(r'(?:doi|DOI)[:\s]*</?[^>]*>?\s*(10\.\d{4,9}/[^\s"<]+)', html)
        if m: d['cit_doi'] = m.group(1)
    # title from h1
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if m: d['h1'] = clean(m.group(1))
    # journal block "Localización:"
    m = re.search(r'Localizaci[óo]n:\s*(.*?)</', html, re.S)
    if m: d['localizacion'] = clean(m.group(1))
    m = re.search(r'Localizaci[óo]n:\s*<[^>]*>(.*?)</p>', html, re.S)
    if m: d['localizacion2'] = clean(m.group(1))
    # authors block
    m = re.search(r'Autores?:\s*(.*?)</p>', html, re.S)
    if m: d['autores'] = clean(m.group(1))
    # raw region
    return d

if __name__ == '__main__':
    ids = [l.split('\t') for l in io.open('work/match_result.tsv', encoding='utf-8') if l.strip()]
    out = io.open('work/dialnet_meta.tsv', 'w', encoding='utf-8')
    for row, seq, src in ids:
        cod = re.search(r'codigo=(\d+)', src).group(1)
        url = 'https://dialnet.unirioja.es/servlet/articulo?codigo=' + cod
        try:
            html = fetch(url)
            d = parse(html)
            rec = {'row': row, 'seq': seq, 'codigo': cod, **d}
        except Exception as e:
            rec = {'row': row, 'seq': seq, 'codigo': cod, 'error': str(e)}
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        print(row, seq, cod, rec.get('cit_doi') or rec.get('error') or '', '|', (rec.get('cit_title') or rec.get('h1') or '')[:60])
        time.sleep(1.2)
    out.close()
