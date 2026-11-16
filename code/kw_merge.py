# -*- coding: utf-8 -*-
"""Merge harvested lists, dedupe against existing table, keep title-matched items."""
import json, glob, re, io, unicodedata, os

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace('ñ', 'n')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def has(t, *words):
    return any(w in t for w in words)

RULES = {
    'español': lambda t: has(t, 'espanol', 'espanola', 'castellano'),
    'inglés': lambda t: has(t, 'ingles', 'inglesa', 'english'),
    'francés': lambda t: has(t, 'frances', 'francesa', 'french'),
    'chino': lambda t: has(t, 'chino', 'china', 'chinese', 'mandarin'),
    'mandarín': lambda t: has(t, 'mandarin') and has(t, 'chino', 'lengua', 'espanol', 'hablante'),
    'idioma': lambda t: has(t, 'idioma', 'idiomas'),
    'lingüística': lambda t: has(t, 'linguistic', 'linguistica'),
    'bilingüe': lambda t: has(t, 'bilingue', 'bilingues', 'bilingual', 'bilingue'),
    'multilingüismo': lambda t: has(t, 'multiling', 'pluriling'),
    'política lingüística': lambda t: has(t, 'politica', 'politicas', 'planificacion') and has(t, 'linguistic'),
    'enseñanza de la lengua': lambda t: has(t, 'ensenanza', 'didactica', 'educacion') and has(t, 'lengua', 'lenguas', 'idioma'),
    'uso de la lengua': lambda t: has(t, 'uso', 'usos') and has(t, 'lengua', 'lenguas', 'idioma'),
    'derechos lingüísticos': lambda t: has(t, 'derecho', 'derechos') and has(t, 'linguistic'),
    'lenguas indígenas': lambda t: has(t, 'indigena', 'indigenas', 'originari', 'aborigen'),
    'lenguas de migración': lambda t: has(t, 'migra', 'migrante', 'migrantes', 'inmigra') and has(t, 'lengua', 'lenguas', 'idioma'),
    'portugués': lambda t: has(t, 'portugues', 'portuguesa', 'portuguese'),
    'lengua extranjera': lambda t: has(t, 'extranjer') and has(t, 'lengua', 'lenguas'),
    'segunda lengua': lambda t: has(t, 'segunda lengua', 'segundas lenguas', 'lengua segunda'),
    'L2': lambda t: re.search(r'\bl2\b', t) is not None or 'segunda lengua' in t,
}

CONTEXT = ['lengua', 'lenguas', 'idioma', 'idiomas', 'linguistic', 'bilingue', 'bilingual', 'multiling',
           'pluriling', 'ensenanza', 'educacion', 'educativa', 'escolar', 'escuela', 'didactica',
           'politica', 'planificacion', 'derecho', 'intercultural', 'indigena', 'originari', 'migra',
           'inmigra', 'habla', 'hablante', 'discurso', 'norma', 'normativa', 'academia', 'lexico',
           'gramatica', 'vocabulario', 'dialecto', 'sociolingu', 'glotopolit', 'lenguaje', 'traduccion',
           'escritura', 'alfabetizacion', 'curriculum', 'docente', 'profesor', 'universidad', 'identidad',
           'nacion', 'legislacion', 'ley', 'ele', 'else', 'sinohablante', 'aprendizaje', 'adquisicion']

EXISTING = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全.xlsx"

def load_existing():
    import openpyxl
    wb = openpyxl.load_workbook(EXISTING, read_only=True)
    ws = wb['Sheet2']
    cods, titles = set(), []
    for r in ws.iter_rows(min_row=2, max_col=9, values_only=True):
        src = str(r[1] or '')
        m = re.search(r'codigo=(\d+)', src)
        if m:
            cods.add(m.group(1))
        titles.append(norm(r[3]))
    wb.close()
    return cods, titles

def main():
    cods, titles = load_existing()
    pool = {}
    per_kw = {}
    for f in glob.glob('work/kw_raw/*.json'):
        rows = json.load(io.open(f, encoding='utf-8'))
        for r in rows:
            if 'codigo' not in r:
                continue
            c = r['codigo']
            if c not in pool:
                pool[c] = dict(r, kws=[])
            if r['kw'] not in pool[c]['kws']:
                pool[c]['kws'].append(r['kw'])
    print('unique codigo in pool:', len(pool))

    matched, seen_titles = [], []
    for c, r in pool.items():
        if c in cods:
            continue
        t = norm(r['title'])
        if len(t) < 8:
            continue
        if any(t == x or (len(t) > 25 and (t in x or x in t)) for x in titles if x):
            continue
        hit = [k for k, fn in RULES.items() if fn(t)]
        if not hit:
            continue
        if len(hit) < 2 and not has(t, *CONTEXT):
            continue
        r['title_match'] = hit
        matched.append(r)
        for k in hit:
            per_kw[k] = per_kw.get(k, 0) + 1
        seen_titles.append(t)

    matched.sort(key=lambda r: (-len(r['kws']), r['title']))
    json.dump(matched, io.open('work/new_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('title-matched & new:', len(matched))
    for k, v in sorted(per_kw.items(), key=lambda x: -x[1]):
        print('   %-24s %d' % (k, v))

if __name__ == '__main__':
    main()
