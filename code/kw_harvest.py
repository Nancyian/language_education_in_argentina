# -*- coding: utf-8 -*-
"""Harvest Dialnet search lists (keyword + 'argentina'), page-level checkpointing."""
import urllib.parse, urllib.request, re, time, json, io, os, ssl, math, sys

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE = 'https://dialnet.unirioja.es'
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
PAGE = 50
CAP = 100
PAGES_DIR = 'work/kw_pages'

KEYWORDS = [
    'español', 'inglés', 'francés', 'chino', 'mandarín', 'idioma',
    'lingüística', 'bilingüe', 'multilingüismo',
    'política lingüística', 'enseñanza de la lengua', 'uso de la lengua',
    'derechos lingüísticos', 'lenguas indígenas', 'lenguas de migración',
    'portugués', 'lengua extranjera', 'segunda lengua', 'L2',
]

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'es-ES,es;q=0.9'})
            with urllib.request.urlopen(req, timeout=50, context=CTX) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1.0 + i * 1.5)
    return ''

TAG = re.compile(r'<[^>]+>')
def clean(s):
    s = TAG.sub('', s)
    for a, b in [('&amp;', '&'), ('&quot;', '"'), ('&#39;', "'"), ('&lt;', '<'), ('&gt;', '>'), ('&nbsp;', ' ')]:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()

def parse_page(h, kw):
    items = []
    for p in re.split(r'(?=<li id="articulo)', h):
        m = re.match(r'<li id="articulo(\d+)" class="([^"]*)">(.*)', p, re.S)
        if not m:
            continue
        cod, cls, blk = m.group(1), m.group(2), m.group(3)
        mt = re.search(r'<p class="titulo">(.*?)</p>', blk, re.S)
        ma = re.search(r'<p class="autores">(.*?)</p>', blk, re.S)
        ml = re.search(r'<p class="localizacion">(.*?)</p>', blk, re.S)
        items.append({
            'codigo': cod, 'cls': cls.strip(), 'kw': kw,
            'title': clean(mt.group(1)) if mt else '',
            'authors': clean(ma.group(1)) if ma else '',
            'loc': clean(ml.group(1)) if ml else '',
        })
    return items

def slug(kw):
    return re.sub(r'[^a-z0-9]+', '_', kw.lower())

def page_file(kw, start):
    d = os.path.join(PAGES_DIR, slug(kw))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, '%04d.json' % start)

def harvest(kw):
    os.makedirs(os.path.join(PAGES_DIR, slug(kw)), exist_ok=True)
    q = urllib.parse.quote_plus(kw + ' argentina')
    f0 = page_file(kw, 0)
    if os.path.exists(f0):
        page0 = json.load(io.open(f0, encoding='utf-8'))
        total, items0 = page0['total'], page0['items']
    else:
        url = '%s/buscar/documentos?querysDismax.DOCUMENTAL_TODO=%s&registrosPorPagina=%d' % (BASE, q, PAGE)
        h = get(url)
        mc = re.search(r'([\d\.]+)\s*documentos encontrados', h) if h else None
        total = int(mc.group(1).replace('.', '')) if mc else -1
        items0 = parse_page(h, kw) if h else []
        if total >= 0 and items0:
            json.dump({'total': total, 'items': items0}, io.open(f0, 'w', encoding='utf-8'), ensure_ascii=False)
    n_pages = max(1, math.ceil(min(max(total, 0), CAP) / float(PAGE)))
    items = list(items0)
    for pg in range(1, n_pages):
        start = pg * PAGE
        fp = page_file(kw, start)
        if os.path.exists(fp):
            items.extend(json.load(io.open(fp, encoding='utf-8'))['items'])
            continue
        url = '%s/buscar/documentos?querysDismax.DOCUMENTAL_TODO=%s&registrosPorPagina=%d&inicio=%d' % (BASE, q, PAGE, start)
        h = get(url)
        if not h:
            continue
        got = parse_page(h, kw)
        json.dump({'total': total, 'items': got}, io.open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
        items.extend(got)
        time.sleep(0.3)
    return kw, total, n_pages, items

def run(kw):
    kw, total, n_pages, items = harvest(kw)
    os.makedirs('work/kw_raw', exist_ok=True)
    json.dump([{'_meta': kw, 'total': total, 'pages': n_pages}] + items,
              io.open('work/kw_raw/%s.json' % slug(kw), 'w', encoding='utf-8'), ensure_ascii=False)
    print('%-24s total=%-6s pages=%-3s items=%-4d' % (kw, total, n_pages, len(items)), flush=True)

if __name__ == '__main__':
    from concurrent.futures import ThreadPoolExecutor
    kws = sys.argv[1:] or KEYWORDS
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(run, kws))
