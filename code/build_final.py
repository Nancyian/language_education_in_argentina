# -*- coding: utf-8 -*-
"""Build the enriched Excel: fill 来源(DOI/URL), 文章标题, 期刊名称, 作者, 发表时间, 时期分布."""
import json, io, re, unicodedata, openpyxl, html, copy

SRC = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理.xlsx'
DST = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全.xlsx'

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s)
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+[^>]*>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 3]; bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw)/len(aw)
    if an in bn or bn in an: ov = max(ov, 0.95)
    return ov

# ---- verified DOIs ----
DOI = {
 '5':'10.19137/anclajes-2025-29211','6':'10.48162/rev.5.133','8':'10.48162/rev.5.144',
 '14':'10.19053/01227238.1572','15':'10.19130/iifl.ap.2008.2.261','16':'10.5212/praxeduc.v.7iespecial.0002',
 '20':'10.7203/normas.3.4674','22':'10.19053/0121053x.2334','29':'10.19183/how.22.2.150',
 '36':'10.5377/rci.v16i1.2351','37':'10.34096/sys.n33.5254','41':'10.19130/iifl.adel.6.1.2018.1480',
 '46':'10.34096/sys.n35.6936','47':'10.14516/fde.701','48':'10.19137/els-2019-161608',
 '49':'10.17533/udea.lyl.1006','50':'10.19137/anclajes-2020-2411','55':'10.21676/23897856.3243',
 '59':'10.11144/javeriana.m13.hbrl','61':'10.19130/iifl.adel.2021.9.2.47365',
 '62':'10.61203/2347-0658.v5.n1.14720','63':'10.61203/2347-0658.v5.n2.16360',
 '64':'10.61203/2347-0658.v4.n0.12571','65':'10.61203/2347-0658.v3.n0.9381',
 '67':'10.11606/issn.2317-9651.i24p140-169','69':'10.17533/udea.ikala.v28n1a05',
 '73':'10.13140/rg.2.2.12967.93603','74':'10.24310/isl.v18i1.15626','75':'10.29197/cpu.v20i39.479',
 '81':'10.37354/riee.2002.019','82':'10.5281/zenodo.10162214','83':'10.48162/rev.5.102',
 '84':'10.48162/rev.5082','85':'10.48162/rev.5.003','86':'10.70833/rseisa8item113',
 '87':'10.70833/rseisa11item182','88':'10.16925/2382-4921.2024.01.03','89':'10.48162/rev.5.111',
 '90':'10.34096/sys.n45.14493','91':'10.34096/sys.n45.14570','92':'10.34096/sys.n45.15621',
 '97':'10.48162/rev.5.122',
}

# ---- verified article URLs (journals that do not assign DOIs) ----
RAHL = {'2':'40','3':'55','12':'17','13':'23','21':'69','51':'75','52':'126','53':'132','54':'137',
        '60':'196','68':'224','93':'261','94':'263','98':'273','99':'271'}
URL = {k: 'https://www.rahl.ar/index.php/rahl/article/view/%s' % v for k, v in RAHL.items()}
URL.update({
 '19': 'https://p3.usal.edu.ar/index.php/ele/article/view/667',
 '23': 'https://p3.usal.edu.ar/index.php/ele/article/view/2086',
 '30': 'https://p3.usal.edu.ar/index.php/ele/article/view/3439',
 '9':  'https://fh.mdp.edu.ar/revistas/index.php/entramados/article/view/9302',
})

def year_of(loc):
    """Extract publication year from a Dialnet citation string (avoids ISSN/pages)."""
    s = loc or ''
    i = s.find('Idioma:')
    if i > 0: s = s[:i]
    s = re.sub(r'ISSN[^,;]{0,22}', ' ', s)
    s = re.sub(r'p[áa]gs?\.\s*[\d\-–]+', ' ', s)
    s = re.sub(r'\d+\s*p[áa]gs?\.?', ' ', s)
    s = re.sub(r'Vol\.\s*[\d\-–]+', ' ', s)
    s = re.sub(r'N[ºo]\.\s*[\d\-–]+', ' ', s)
    m = re.search(r'(19[8-9]\d|20[0-2]\d)\s*[-–]\s*(19[8-9]\d|20[0-2]\d)', s)
    if m: return m.group(1) + '-' + m.group(2)
    ys = [int(y) for y in re.findall(r'(19[8-9]\d|20[0-2]\d)', s)]
    ys = [y for y in ys if 1981 <= y <= 2027]
    return str(ys[0]) if ys else ''

def bucket(y):
    if not y: return '时间不详'
    try: y = int(str(y)[:4])
    except Exception: return '时间不详'
    if 1981 <= y <= 1985: return '1981-1985'
    if 1986 <= y <= 1990: return '1986-1990'
    if 1991 <= y <= 1995: return '1991-1995'
    if 1996 <= y <= 2000: return '1996-2000'
    if 2001 <= y <= 2005: return '2001-2005'
    if 2006 <= y <= 2010: return '2006-2010'
    if 2011 <= y <= 2015: return '2011-2015'
    if 2016 <= y <= 2020: return '2016-2020'
    if 2021 <= y <= 2025: return '2021-2025'
    if 2026 <= y <= 2030: return '2026-2030'
    return '时间不详'

meta = {r['seq']: r for r in (json.loads(l) for l in io.open('work/meta_full.tsv', encoding='utf-8'))}

wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']

# extend 时间选项 with 2026-2030
opt = wb['时间选项']
if opt.cell(row=12, column=1).value is None:
    opt.cell(row=12, column=1).value = '2026-2030'
for dv in ws.data_validations.dataValidation:
    if dv.type == 'list' and '时间选项' in (dv.formula1 or ''):
        dv.formula1 = '时间选项!$A$2:$A$12'

report = []
for row in range(2, ws.max_row + 1):
    seq = str(ws.cell(row=row, column=1).value).strip()
    m = meta.get(seq)
    if not m:
        continue
    # authoritative title/journal/authors
    title = unesc(m.get('cit_title') or '').strip()
    journal = (m.get('cit_journal') or '').strip()
    authors = '; '.join(m.get('cit_authors') or [])
    if not authors:
        authors = '; '.join(m.get('authors') or []) if isinstance(m.get('authors'), list) else ''
    year = year_of(m.get('loc') or '')

    # 来源 (col 2)
    src = DOI.get(seq) or URL.get(seq) or ('https://dialnet.unirioja.es/servlet/articulo?codigo=%s' % m.get('codigo'))
    ws.cell(row=row, column=2).value = src

    # 文章标题 (col 4) — replace when blank, vague, or a fragment of the real title
    cur_t = ws.cell(row=row, column=4).value
    cn, rn = norm(cur_t), norm(title)
    is_fragment = bool(cn) and rn and len(cn) < 0.62 * len(rn)
    if (not cur_t) or sim(cur_t, title) < 0.75 or is_fragment:
        ws.cell(row=row, column=4).value = title

    # 期刊名称 (col 5)
    if journal:
        ws.cell(row=row, column=5).value = journal

    # 作者 (col 6)
    ws.cell(row=row, column=6).value = authors

    # 发表时间 (col 7)
    ws.cell(row=row, column=7).value = (int(year) if re.fullmatch(r'\d{4}', str(year)) else year)

    # 时期分布 (col 8)
    ws.cell(row=row, column=8).value = bucket(year)

    report.append((seq, src, journal[:34], authors[:26], year, bucket(year), title[:46]))

wb.save(DST)
print('saved ->', DST)
print('rows:', len(report))
n_doi = sum(1 for r in report if not r[1].startswith('http'))
print('DOI rows:', n_doi, '| URL rows:', len(report) - n_doi)
