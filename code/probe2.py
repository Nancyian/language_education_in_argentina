# -*- coding: utf-8 -*-
"""在已下载的期刊全量记录中，按作者/关键词检索，人工核对是否存在对应文献。"""
import json, io, os, re, glob, unicodedata, html, sys

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or ''); s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'<[^>]+>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

recs_by_issn = {}
for f in glob.glob('work/journals/*.json'):
    issn = os.path.basename(f)[:-5]
    lst = []
    try:
        for w in json.load(io.open(f, encoding='utf-8')):
            y = ((w.get('issued', {}).get('date-parts') or [[None]])[0] or [None])[0]
            auth = '; '.join(((a.get('family') or '') + ' ' + (a.get('given') or '')).strip()
                             for a in (w.get('author') or []) if a.get('family'))
            lst.append({'doi': w.get('DOI') or '', 'title': (w.get('title') or [''])[0], 'year': y,
                        'authors': auth, 'journal': (w.get('container-title') or [''])[0]})
    except Exception:
        pass
    recs_by_issn[issn] = lst

# (issn, 年份范围, 检索词列表)
PROBES = [
    ('18514669', (2018, 2020), ['neutralidad linguistica', 'manuales de estilo', 'Kornfeld']),
    ('18524206', (2023, 2025), ['cambio de codigo', 'input bilingue', 'Junyent', 'alfabetizacion inicial']),
    ('23626194', (2017, 2019), ['sordos', 'Yarza', 'Llambi', 'Cvejanov', 'alfabetizacion comunidad']),
    ('18529615', (2016, 2018), ['Contorno', 'Roca', 'emancipacion']),
    ('19739370', (2016, 2018), ['latinoamericano', 'Gomez', 'viaje academico', 'camino de los santos']),
    ('19724527', (2016, 2018), ['latinoamericano', 'Gomez', 'viaje academico']),
    ('16974239', (2017, 2019), ['quichua', 'santiagueno', 'Ghiorghila', 'influencia del espanol']),
    ('16579089', (2012, 2014), ['adultocentrismo', 'agencia infantil', 'Hecht', 'socializacion']),
    ('16925777', (2011, 2013), ['cultura', 'Moirano', 'culture teaching', 'students']),
    ('14056666', (2019, 2021), ['guarani', 'intercultural bilingue', 'Salta', 'Casimiro']),
    ('07187378', (2014, 2016), ['intercultural bilingue', 'Chaco', 'Hecht']),
    ('16684753', (2016, 2018), ['docente contextos interculturales', 'Aliata', 'reflexiones figura']),
    ('23142189', (2011, 2017), ['Bengochea', 'Fernandez Silva', 'Gandulfo', 'Paraguay bilingue', 'investigacion ELSE', 'guarani']),
    ('18514669', (1999, 2004), ['Trelew', 'Virkel', 'inmigracion', 'galés', 'bonaerense']),
    ('18513115', (2013, 2015), ['politicas educativas', 'Cuesta', 'diversidad linguistica']),
    ('18500153', (2015, 2017), ['Ancalao', 'postmonolingue', 'Stocco', 'frontera']),
    ('18500161', (2015, 2017), ['Ancalao', 'postmonolingue', 'Stocco', 'frontera']),
]
for issn, yrange, kws in PROBES:
    lst = recs_by_issn.get(issn, [])
    sel = [r for r in lst if r['year'] and yrange[0] - 1 <= r['year'] <= yrange[1] + 1]
    print('===== ISSN %s | %s-%s | recs_in_range=%d (total %d)' % (issn, yrange[0], yrange[1], len(sel), len(lst)))
    for kw in kws:
        kwl = norm(kw)
        hits = [r for r in lst if kwl in norm(r['title'] + ' ' + r['authors'])]
        print('  -- kw: %-28s hits=%d' % (kw, len(hits)))
        for h in hits[:6]:
            print('       %-42s %-5s %s' % (h['doi'], h['year'], (h['title'] or '')[:72]))
    if not any(kwl for kwl in [norm(k) for k in kws]):
        pass
    sys.stdout.flush()
