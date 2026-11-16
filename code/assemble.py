# -*- coding: utf-8 -*-
import json, io, re, unicodedata

def clean_journal(j):
    if not j: return ''
    j = re.sub(r'\s+', ' ', j).strip()
    j = j.replace('( RACC )', '').strip()
    return j

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\s+', ' ', s.lower()))

def get_year(loc, fallback_years=None):
    loc = loc or ''
    # remove ISSN patterns to avoid matching years inside ISSNs
    t = re.sub(r'ISSN[^0-9]{0,14}[0-9]{4}-[0-9]{3}[0-9Xx]', ' ', loc)
    m = re.search(r'((?:19|20)\d{2})(?:-((?:19|20)\d{2}))?\s*,?\s*\d*\s*p[áa]gs?', t)
    if m: return int(m.group(1)), int(m.group(2)) if m.group(2) else None
    m = re.search(r'N[ºo°.]\s*\d+[^,]*,\s*((?:19|20)\d{2})', t)
    if m: return int(m.group(1)), None
    yrs = re.findall(r'\b((?:19|20)\d{2})\b', t)
    if yrs: return int(yrs[0]), None
    if fallback_years: return int(fallback_years[0]), None
    return None, None

def bucket(y):
    if not y: return '时间不详'
    start = (y - 1)//5*5 + 1
    return '%d-%d' % (start, start+4)

oa = {}
for l in io.open('work/meta_oa.tsv', encoding='utf-8'):
    d = json.loads(l); oa[d['seq']] = d

cr = {}
for l in io.open('work/meta_doi.tsv', encoding='utf-8'):
    d = json.loads(l); cr[d['seq']] = d

full = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    d = json.loads(l); full[d['seq']] = d

match = {}
for l in io.open('work/match_result.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t'); match[p[1]] = {'row': p[0], 'codigo': re.search(r'codigo=(\d+)', p[2]).group(1)}

rows = []
for seq in sorted(full, key=lambda x: int(x)):
    f = full[seq]; o = oa.get(seq, {}); c = cr.get(seq, {})
    title = f.get('cit_title') or f.get('page_title') or ''
    journal = clean_journal(f.get('cit_journal'))
    authors = '; '.join(f.get('cit_authors') or [])
    y, y2 = get_year(f.get('loc'), f.get('loc_years'))
    loc = f.get('loc') or ''
    issns = re.findall(r'ISSN[^0-9]{0,14}([0-9]{4}-[0-9]{3}[0-9Xx])', loc)
    issns = [i.upper() for i in issns]
    # validate OpenAlex
    doi = ''; src = ''; oaj = o.get('oa_journal') or ''
    jmatch = False
    if journal and oaj:
        nj, no = norm(journal), norm(oaj)
        if nj and no and (nj[:14] in no or no[:14] in nj or nj in no or no in nj):
            jmatch = True
    if o.get('oa_journal_issn') and issns:
        if set(x.upper() for x in o['oa_journal_issn']) & set(issns):
            jmatch = True
    yr_ok = (not y) or (not o.get('oa_year')) or abs((o.get('oa_year') or 0) - y) <= 1
    if o.get('oa_doi') and (jmatch and yr_ok):
        doi = o['oa_doi']; src = 'OpenAlex(journal+year)'
    rows.append({
        'seq': seq, 'row': match[seq]['row'], 'codigo': match[seq]['codigo'],
        'title': title, 'journal': journal, 'authors': authors,
        'year': y, 'year2': y2, 'bucket': bucket(y), 'issns': issns,
        'loc': loc, 'doi': doi, 'doi_src': src,
        'oa_doi': o.get('oa_doi') or '', 'oa_score': o.get('oa_score'), 'oa_journal': oaj,
        'oa_year': o.get('oa_year'), 'oa_authors': o.get('oa_authors') or [],
        'cr_doi': c.get('m_doi') or '', 'cr_score': c.get('match_score'),
        'cr_journal': c.get('m_journal') or '', 'cr_title': c.get('m_title') or '',
    })

with io.open('work/assembly.tsv', 'w', encoding='utf-8') as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + '\n')

print('rows', len(rows))
print('DOI resolved:', sum(1 for r in rows if r['doi']))
print()
for r in rows:
    flag = 'OK' if r['doi'] else '--'
    print('%s %2s R%-4s y=%-5s %-34s | OA:%s(%s) %s' % (
        flag, r['seq'], r['row'][1:], r['year'], (r['journal'] or '?')[:34],
        r['oa_score'], (r['oa_journal'] or '')[:20], r['doi'] or r['oa_doi'] or ''))
