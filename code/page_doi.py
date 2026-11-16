# -*- coding: utf-8 -*-
"""对 57 行中仍无 DOI 的记录：抓取其期刊原文页面，抽取 DOI 元数据。"""
import urllib.request, urllib.error, urllib.parse, ssl, re, json, io, time, unicodedata, html, sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36'
HDR = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'}

def get(u, timeout=35, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=HDR)
            r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return r.status, r.read().decode('utf-8', 'ignore')
        except Exception as e:
            last = str(e)[:60]; time.sleep(1 + i)
    return None, last

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def find_doi(h):
    out = []
    for m in re.finditer(r'<meta[^>]+(?:name|property)\s*=\s*["\']([^"\']*doi[^"\']*)["\'][^>]*content\s*=\s*["\']([^"\']+)["\']', h, re.I):
        out.append((m.group(1), m.group(2).strip()))
    for m in re.finditer(r'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]*(?:name|property)\s*=\s*["\']([^"\']*doi[^"\']*)["\']', h, re.I):
        out.append((m.group(2), m.group(1).strip()))
    # DOI textual en página (excluir referencias): buscar bloque 'DOI:' cerca de la cabecera
    for m in re.finditer(r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s"\'<>,;)\]]+)', h):
        out.append(('doi.org-url', m.group(1)))
    for m in re.finditer(r'(?:^|[>\s])(?:DOI|doi)\s*[:：]\s*(10\.\d{4,9}/[^\s"\'<>,;)\]]+)', h):
        out.append(('label-DOI', m.group(1)))
    return out

# cargar filas objetivo
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r

targets = []
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    seq = p[0]
    d = meta.get(seq, {})
    # 候选URL：来源列 + Dialnet links
    urls = []
    if p[5].startswith('http'):
        urls.append(p[5])
    for ln in (d.get('links') or []):
        if isinstance(ln, str) and ln.startswith('http') and 'dialnet' not in ln and 'purl' not in ln:
            urls.append(ln)
    targets.append({'seq': seq, 'title': unesc(d.get('cit_title') or p[4]), 'journal': p[3],
                    'year': p[1], 'urls': urls[:4]})

print('targets', len(targets))
out = {}
def work(t):
    rec = {'seq': t['seq'], 'title': t['title'], 'tried': [], 'hits': []}
    for u in t['urls']:
        s, h = get(u)
        rec['tried'].append((u, s))
        if s and isinstance(h, str) and len(h) > 500:
            for src, doi in find_doi(h):
                if src in ('citation_doi', 'dc.identifier', 'DC.Identifier') or 'doi' in src.lower():
                    rec['hits'].append({'src': src, 'doi': doi, 'page': u})
    return rec

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(work, t) for t in targets]
    for i, f in enumerate(as_completed(futs)):
        r = f.result()
        out[r['seq']] = r
        hh = [x for x in r['hits'] if re.match(r'^10\.\d{4,9}/', x['doi'] or '')]
        if hh:
            print('=== seq %s | %s' % (r['seq'], r['title'][:60]))
            for x in hh[:5]:
                print('     [%s] %s  <- %s' % (x['src'], x['doi'], x['page'][:70]))
        sys.stdout.flush()

json.dump(out, io.open('work/page_doi.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
