# -*- coding: utf-8 -*-
"""补充检索：OpenAlex / Europe PMC / Crossref(更多句式) / ERIC(更多句式)
输出 work/pool2.json，并记录各通道状态 work/channel_status.json
"""
import io, json, re, sys, time, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
from kw_merge import norm

OUT = 'work/pool2.json'
STAT = 'work/channel_status.json'
UA = {'User-Agent': 'corpus-builder/1.0 (mailto:corpus@example.com)'}
STATUS = {}


def get(url, timeout=40, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            raw = urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace')
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            STATUS.setdefault('_last_err', '')  # noqa
            if e.code == 429:
                return {'__429__': True}
            if i == tries - 1:
                return None
            time.sleep(3)
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(3)


def strip_html(s):
    return re.sub(r'<[^>]+>', ' ', str(s or '')).replace('&quot;', '"').replace('&#39;', "'").strip()


# ---------------- 检索式（英/西双语，覆盖 20 组关键词） ----------------
QUERIES = [
    ('español', 'spanish language argentina'),
    ('inglés', 'english language argentina'),
    ('francés', 'french language argentina'),
    ('chino', 'chinese language argentina'),
    ('mandarín', 'mandarin argentina'),
    ('idioma', 'language argentina'),
    ('lingüística', 'linguistics argentina'),
    ('bilingüe', 'bilingual education argentina'),
    ('multilingüismo', 'multilingualism argentina'),
    ('política lingüística', 'language policy argentina'),
    ('enseñanza de la lengua', 'language teaching argentina'),
    ('uso de la lengua', 'language use argentina'),
    ('derechos lingüísticos', 'language rights argentina'),
    ('lenguas indígenas', 'indigenous languages argentina'),
    ('lenguas de migración', 'migrant languages argentina'),
    ('portugués', 'portuguese language argentina'),
    ('lengua extranjera', 'foreign language argentina'),
    ('segunda lengua', 'second language argentina'),
    ('L2', 'L2 argentina'),
]


# ---------------- OpenAlex ----------------
def harvest_openalex():
    out, ok = [], False
    for kw, q in QUERIES:
        u = ('https://api.openalex.org/works?search=' + urllib.parse.quote(q) +
             '&filter=type:article&per-page=50&select=id,doi,title,publication_year,'
             'primary_location,authorships,abstract_inverted_index,language')
        j = get(u, tries=1)
        if not j or j.get('__429__'):
            STATUS['openalex'] = 'rate_limited'
            continue
        ok = True
        n = 0
        for d in j.get('results', []):
            t = strip_html(d.get('title'))
            if not t or len(t) < 10:
                continue
            # 摘要：倒排索引还原
            inv = d.get('abstract_inverted_index') or {}
            words = []
            if inv:
                pos = {}
                for w, idxs in inv.items():
                    for i in idxs:
                        pos[i] = w
                words = [pos[i] for i in sorted(pos)][:400]
            src = (d.get('primary_location') or {}).get('source') or {}
            out.append({
                'db': 'OpenAlex', 'kw': kw, 'title': t,
                'authors': '; '.join([(a.get('author') or {}).get('display_name', '')
                                      for a in (d.get('authorships') or [])])[:200],
                'venue': (src.get('display_name') or '')[:150],
                'year': d.get('publication_year'),
                'abstract': ' '.join(words)[:2500],
                'url': d.get('doi') or d.get('id') or '',
                'issn': (src.get('issn_l') or ''),
            })
            n += 1
        print('OA  %-26s %d' % (kw, n))
        time.sleep(1.0)
    STATUS['openalex'] = 'ok' if ok else STATUS.get('openalex', 'fail')
    return out


# ---------------- Europe PMC ----------------
def harvest_epmc():
    out, ok = [], False
    for kw, q in QUERIES:
        # Europe PMC 语法：自由词 + 布尔
        qq = '(%s) AND (argentina OR argentine)' % ' '.join('"%s"' % w if ' ' in w else w for w in q.split())
        u = ('https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=' +
             urllib.parse.quote(qq) + '&format=json&pageSize=50&resultType=core')
        j = get(u, tries=2)
        if not j:
            STATUS['europepmc'] = 'fail'
            continue
        ok = True
        n = 0
        for d in j.get('resultList', {}).get('result', []):
            t = strip_html(d.get('title'))
            if not t or len(t) < 10:
                continue
            out.append({
                'db': 'EuropePMC', 'kw': kw, 'title': t,
                'authors': strip_html(d.get('authorString'))[:200],
                'venue': strip_html(d.get('journalTitle') or d.get('bookOrReportDetails', {}).get('publisher', ''))[:150],
                'year': d.get('pubYear'),
                'abstract': strip_html(d.get('abstractText'))[:2500],
                'url': ('https://doi.org/' + d['doi']) if d.get('doi') else ('https://europepmc.org/article/' + str(d.get('source', 'MED')) + '/' + str(d.get('id', ''))),
            })
            n += 1
        print('EPMC %-26s %d' % (kw, n))
        time.sleep(0.6)
    STATUS['europepmc'] = 'ok' if ok else 'fail'
    return out


# ---------------- Crossref 补充句式（西语版 + 更多组合） ----------------
CR_EXTRA = [
    ('política lingüística', 'política lingüística Argentina'),
    ('política lingüística', 'planificación lingüística Argentina'),
    ('política lingüística', 'glotopolítica Argentina'),
    ('lenguas indígenas', 'lenguas indígenas Argentina'),
    ('lenguas indígenas', 'intercultural bilingüe Argentina'),
    ('lenguas de migración', 'inmigración lenguas Argentina'),
    ('enseñanza de la lengua', 'enseñanza lengua Argentina'),
    ('enseñanza de la lengua', 'didáctica lengua Argentina'),
    ('español', 'español de la Argentina'),
    ('español', 'español rioplatense'),
    ('portugués', 'portugués Argentina frontera'),
    ('segunda lengua', 'español como segunda lengua Argentina'),
    ('L2', 'español L2 Argentina'),
    ('bilingüe', 'educación bilingüe Argentina'),
    ('derechos lingüísticos', 'derechos lingüísticos Argentina'),
    ('lengua extranjera', 'lengua extranjera Argentina'),
    ('idioma', 'políticas lingüísticas Argentina'),
    ('lingüística', 'sociolingüística Argentina'),
    ('multilingüismo', 'plurilingüismo Argentina'),
]


def harvest_crossref():
    out = []
    for kw, q in CR_EXTRA:
        u = ('https://api.crossref.org/works?query.bibliographic=' + urllib.parse.quote(q) +
             '&filter=type:journal-article&rows=30&select=title,author,container-title,issued,DOI,abstract' +
             '&query.affiliation=Argentina')
        j = get(u)
        if not j:
            STATUS['crossref'] = 'fail'
            continue
        n = 0
        for d in j.get('message', {}).get('items', []):
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
        print('CR+  %-26s %d' % (kw, n))
        time.sleep(1.0)
    STATUS['crossref'] = 'ok'
    return out


# ---------------- ERIC 补充句式 ----------------
ERIC_EXTRA = [
    ('política lingüística', 'language planning Argentina'),
    ('enseñanza de la lengua', 'language instruction Argentina'),
    ('idioma', 'language Argentina education'),
    ('bilingüe', 'bilingual Argentina'),
    ('lenguas indígenas', 'indigenous language Argentina'),
    ('inglés', 'English language teaching Argentina'),
    ('lengua extranjera', 'foreign language teaching Argentina'),
    ('segunda lengua', 'Spanish second language Argentina'),
    ('L2', 'L2 Spanish Argentina'),
    ('multilingüismo', 'multilingual Argentina'),
    ('derechos lingüísticos', 'linguistic rights Argentina'),
    ('portugués', 'Portuguese Argentina'),
]


def harvest_eric():
    out = []
    for kw, q in ERIC_EXTRA:
        u = ('https://api.ies.ed.gov/eric/?search=' + urllib.parse.quote(q) +
             '&format=json&rows=40&fields=title,author,source,publicationdateyear,description,id')
        j = get(u)
        if not j:
            STATUS['eric'] = 'fail'
            continue
        n = 0
        for d in j.get('response', {}).get('docs', []):
            t = strip_html(d.get('title'))
            if not t or len(t) < 10:
                continue
            out.append({
                'db': 'ERIC', 'kw': kw, 'title': t,
                'authors': '; '.join(d.get('author') or [])[:200],
                'venue': strip_html(d.get('source'))[:150],
                'year': d.get('publicationdateyear'),
                'abstract': strip_html(d.get('description'))[:2500],
                'url': 'https://eric.ed.gov/?id=' + str(d.get('id', '')),
            })
            n += 1
        print('ERIC+ %-26s %d' % (kw, n))
        time.sleep(0.6)
    STATUS['eric'] = 'ok'
    return out


def main():
    out = []
    # OpenAlex 额度耗尽（429），本轮跳过
    STATUS['openalex'] = 'rate_limited_429'
    out += harvest_epmc()
    out += harvest_crossref()
    out += harvest_eric()
    dedup = {}
    for r in out:
        k = norm(r['title'])
        if len(k) < 10:
            continue
        if k not in dedup:
            dedup[k] = dict(r, kws=[r['kw']])
        elif r['kw'] not in dedup[k]['kws']:
            dedup[k]['kws'].append(r['kw'])
    print('pool2 after dedup', len(dedup))
    json.dump(list(dedup.values()), io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(STATUS, io.open(STAT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('status', STATUS)


if __name__ == '__main__':
    main()
