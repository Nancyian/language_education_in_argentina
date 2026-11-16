# -*- coding: utf-8 -*-
"""Probe Dialnet result counts for keyword+Argentina searches."""
import urllib.parse, urllib.request, re, sys, time, json

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

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
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception as e:
            if i == tries - 1:
                return ''
            time.sleep(2 + i * 2)
    return ''

def count(q):
    url = 'https://dialnet.unirioja.es/buscar/documentos?querysDismax.DOCUMENTAL_TODO=' + urllib.parse.quote_plus(q)
    h = get(url)
    m = re.search(r'([\d\.]+)\s*documentos encontrados', h)
    return int(m.group(1).replace('.', '')) if m else -1

out = []
for k in KEYWORDS:
    q = k + ' argentina'
    c = count(q)
    out.append((k, c))
    print('%-26s %6s' % (k, c), flush=True)
    time.sleep(1.2)

json.dump(out, open('work/kw_counts.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('total candidates (capped 60 each):', sum(min(c, 60) for _, c in out if c > 0))
