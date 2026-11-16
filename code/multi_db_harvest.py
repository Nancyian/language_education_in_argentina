# -*- coding: utf-8 -*-
"""多库检索：ERIC(官方API) + Crossref(覆盖WoS/Scopus期刊内容) + CONICET(本地语料聚合)。
输出 work/multi_pool.json —— 文章级候选池。"""
import io, json, re, sys, time, unicodedata, collections
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
from kw_merge import RULES, CONTEXT, norm, has

OUT = 'work/multi_pool.json'

# 每个关键词的跨语言检索式（ERIC/Crossref 均为英/西双语索引）
QUERIES = [
    ('español',                '("Spanish language" OR español) AND argentina'),
    ('inglés',                 '("English language" OR inglés) AND argentina'),
    ('francés',                '(french OR francés) AND argentina'),
    ('chino',                  '(chinese OR chino) AND argentina'),
    ('mandarín',               'mandarin AND argentina'),
    ('idioma',                 '(language OR idioma) AND argentina'),
    ('lingüística',            '(linguistics OR lingüística) AND argentina'),
    ('bilingüe',               '(bilingual OR bilingüe) AND argentina'),
    ('multilingüismo',         '(multilingualism OR plurilingual) AND argentina'),
    ('política lingüística',   '("language policy" OR "language policies" OR "política lingüística") AND argentina'),
    ('enseñanza de la lengua', '("language teaching" OR "teaching language" OR "enseñanza de la lengua") AND argentina'),
    ('uso de la lengua',       '("language use" OR "uso de la lengua") AND argentina'),
    ('derechos lingüísticos',  '("language rights" OR "linguistic rights") AND argentina'),
    ('lenguas indígenas',      '("indigenous languages" OR "lenguas indígenas") AND argentina'),
    ('lenguas de migración',   '(migrants AND language AND argentina) OR ("immigrant language" AND argentina)'),
    ('portugués',              '(portuguese OR portugués) AND argentina'),
    ('lengua extranjera',      '("foreign language" OR "lengua extranjera") AND argentina'),
    ('segunda lengua',         '("second language" OR "lengua segunda") AND argentina'),
    ('L2',                     '("second language" OR L2) AND argentina'),
]

UA = {'User-Agent': 'Mozilla/5.0 (research-corpus-builder; mailto:corpus@example.com)'}


def get(url, timeout=40, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace'))
        except Exception as e:
            if i == tries - 1:
                print('  FAIL', url[:90], type(e).__name__)
                return None
            time.sleep(2 + 2 * i)


def strip_html(s):
    return re.sub(r'<[^>]+>', ' ', str(s or '')).replace('&quot;', '"').replace('&#39;', "'").strip()


# ---------------- ERIC ----------------
def harvest_eric():
    out = []
    for kw, q in QUERIES:
        u = ('https://api.ies.ed.gov/eric/?search=' + urllib.parse.quote(q) +
             '&format=json&rows=40&fields=title,author,source,publicationdateyear,description,id')
        j = get(u)
        if not j:
            continue
        docs = j.get('response', {}).get('docs', [])
        n = 0
        for d in docs:
            t = strip_html(d.get('title'))
            if not t or len(t) < 10:
                continue
            if 'argentina' not in t.lower():
                # ERIC 检索含 argentina 过滤，标题无 argentina 也保留（描述命中）
                pass
            out.append({
                'db': 'ERIC', 'kw': kw, 'title': t,
                'authors': '; '.join(d.get('author') or [])[:200],
                'venue': strip_html(d.get('source'))[:150],
                'year': d.get('publicationdateyear'),
                'abstract': strip_html(d.get('description'))[:2500],
                'url': 'https://eric.ed.gov/?id=' + str(d.get('id', '')),
            })
            n += 1
        print('ERIC %-26s %d' % (kw, n))
        time.sleep(0.6)
    return out


# ---------------- Crossref ----------------
def harvest_crossref():
    out = []
    for kw, q in QUERIES:
        u = ('https://api.crossref.org/works?query.bibliographic=' + urllib.parse.quote(q) +
             '&filter=type:journal-article&rows=40&select=title,author,container-title,issued,DOI,abstract' +
             '&query.affiliation=Argentina')
        j = get(u)
        if not j:
            continue
        items = j.get('message', {}).get('items', [])
        n = 0
        for d in items:
            t = strip_html((d.get('title') or [''])[0])
            if not t or len(t) < 10:
                continue
            yr = None
            try:
                yr = d['issued']['date-parts'][0][0]
            except Exception:
                pass
            if yr and (yr < 1950 or yr > 2026):
                continue
            out.append({
                'db': 'Crossref', 'kw': kw, 'title': t,
                'authors': '; '.join([('%s %s' % (a.get('given', ''), a.get('family', ''))).strip()
                                      for a in (d.get('author') or [])])[:200],
                'venue': strip_html((d.get('container-title') or [''])[0])[:150],
                'year': yr,
                'abstract': strip_html(d.get('abstract'))[:2500],
                'url': 'https://doi.org/' + str(d.get('DOI', '')),
            })
            n += 1
        print('CR   %-26s %d' % (kw, n))
        time.sleep(1.0)
    return out


# ---------------- CONICET（本地语料聚合，严格标题抽取） ----------------
BAD_START = ('este trabajo', 'en espanol', 'para reflexionar', 'sin negar', 'con mas de',
             'este articulo', 'primeramente', 'the present', 'this paper', 'this article',
             'in this', 'se analiza', 'se enfoca')
NUMERIC = re.compile(r'^[\d\s:;,.\-()]+$')

def title_like(t):
    if not (25 <= len(t) <= 220):
        return False
    if t.lower() != t and t.upper() != t and t[0].islower():
        return False
    low = ' ' + t.lower() + ' '
    if any((' ' + b) in t.lower()[:40] for b in BAD_START):
        return False
    if ' et al' in t.lower() or 'http' in t.lower():
        return False
    # 句中句号（排除缩写/小数）：句号后跟空格+小写视为句子延续
    if re.search(r'[a-zà-ÿ]\.\s+[a-zà-ÿ]', t):
        return False
    if NUMERIC.match(t):
        return False
    return True

def harvest_conicet():
    import openpyxl
    ws = openpyxl.load_workbook(r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/conicet_language_corpus.xlsx',
                                read_only=True)['corpus']
    by_handle = collections.OrderedDict()
    for r in ws.iter_rows(min_row=2, max_row=13000, max_col=3, values_only=True):
        if not r[0]:
            continue
        by_handle.setdefault(r[0], {'kws': [], 'frags': []})
        if r[1] and r[1] not in by_handle[r[0]]['kws']:
            by_handle[r[0]]['kws'].append(r[1])
        if r[2] and r[2] not in by_handle[r[0]]['frags']:
            by_handle[r[0]]['frags'].append(str(r[2]))

    AUTH = re.compile(r'^[^.;]{4,60}(?:;[^.;]{4,60}){1,8};\s+(.+)$', re.S)
    VEN = re.compile(r'^([A-ZÁÉÍÓÚÑ][^;]{4,80});\s*(\d{1,3})\s*;')
    YR = re.compile(r'\b(19[5-9]\d|20[0-2]\d)\b')
    out = []
    for h, d in by_handle.items():
        frags = d['frags']
        title, authors, venue, year = None, '', '', None
        for f in frags:
            m = AUTH.match(f.strip())
            if m:
                cand = m.group(1).strip(' .')
                if title_like(cand):
                    authors, title = f[:f.rfind(';')], cand
                    break
        if not title:
            for f in frags:
                cand = f.strip(' .')
                if title_like(cand):
                    title = cand
                    break
        if not title:
            continue
        for f in frags:
            m2 = VEN.match(f.strip())
            if m2 and not venue:
                venue = m2.group(1)
            if year is None:
                m3 = YR.search(f)
                if m3:
                    year = int(m3.group(1))
        out.append({
            'db': 'CONICET', 'kw': '; '.join(d['kws']), 'title': re.sub(r'\s+', ' ', title),
            'authors': re.sub(r'\s+', ' ', authors)[:200], 'venue': venue[:120], 'year': year,
            'abstract': re.sub(r'\s+', ' ', ' '.join(frags))[:2500],
            'url': h,
        })
    print('CONICET strict', len(out))
    return out


def conicet_reachable():
    try:
        req = urllib.request.Request('https://ri.conicet.gov.ar', headers=UA)
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print('CONICET unreachable:', type(e).__name__)
        return False

def main():
    pool = harvest_eric() + harvest_crossref()
    if conicet_reachable():
        pool += harvest_conicet()
    else:
        print('skip CONICET (site down); using local snapshot is unreliable -> excluded')
    # 去重（规范化标题）
    dedup = {}
    for r in pool:
        k = norm(r['title'])
        if len(k) < 10:
            continue
        if k not in dedup:
            dedup[k] = dict(r, kws=[r['kw']])
        elif r['kw'] not in dedup[k]['kws']:
            dedup[k]['kws'].append(r['kw'])
    print('after title dedup', len(dedup))
    json.dump(list(dedup.values()), io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('->', OUT)


if __name__ == '__main__':
    main()
