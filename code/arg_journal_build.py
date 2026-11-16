# -*- coding: utf-8 -*-
"""六库检索结果 × 阿根廷本地期刊 过滤构建。
候选池：CONICET 182 + multi_pool 471 (ERIC/Crossref) + pool2 1030 + ProQuest 373
过滤：语言学科相关 + 期刊在阿根廷白名单 + 与 Dialnet 317 去重
输出：work/final_argjr.json
"""
import io, json, os, re, sys, glob
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
DESK = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语'

# ---------------- 阿根廷期刊白名单 ----------------
CURATED = """
Signo y Seña
Cuadernos del Sur
Cuadernos del Sur Letras
Lenguas en Contexto
Estudios Interlingüísticos
Entramados
Revista Entramados
Quintú Quimün
Cuadernos del CILHA
Anclajes
Traslaciones
Archivos de Ciencias de la Educación
Praxis Educativa
Contextos de Educación
Runa
Avá
Revista del Museo de Antropología
Historia de la Educación Anuario
Revista Argentina de Investigación Educativa
Austral Comunicación
RASAL Lingüística
Revista de la Sociedad Argentina de Lingüística
RELART
Rétor
Confabulaciones
Tábano
Calamus
Argentum
Intersecciones en Antropología
Cuadernos del Instituto Nacional de Antropología y Pensamiento Latinoamericano
Relaciones de la Sociedad Argentina de Antropología
Publicar en Antropología y Ciencias Sociales
Revista Argentina de Antropología Biológica
La Zaranda de Ideas
Revista argentina de historiografía lingüística
Boletín de la Academia Argentina de Letras
Argentinian Journal of Applied Linguistics
Pacha. Revista de Estudios Contemporáneos del Sur Global
""".split('\n')
CURATED = [x.strip() for x in CURATED if x.strip()]

def build_whitelist():
    wl = set()
    for x in CURATED:
        x = x.strip()
        if x:
            wl.add(x)
    try:
        for x in io.open(os.path.join(WORK, 'arg_j_doaj.txt'), encoding='utf-8').read().split('\n'):
            if x.strip():
                wl.add(x.strip())
        dj = json.load(io.open(os.path.join(WORK, 'doaj_journals.json'), encoding='utf-8'))
        for t in dj.values():
            wl.add(t.strip())
    except Exception as e:
        print('whitelist warn', e)
    return sorted(wl)


def norm(s):
    s = (s or '').lower()
    for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'),
                 ('à', 'a'), ('è', 'e'), ('ì', 'i'), ('ò', 'o'), ('ù', 'u'), ('ü', 'u')]:
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


VENUE_BLACK = [
    'estudios rurales', 'prudentia iuris', 'anuario del instituto de historia argentina',
    'temas de historia argentina', 'revista de historia americana', 'res gesta',
    'epistemus', 'cuadernos de economia critica', 'ensayos de politica economica',
    'estudios economicos', 'investigaciones y ensayos', 'revista coleccion',
    'siglo dieciocho', 'imagofagia', 'austral comunicacion', 'testimonios',
    'vivienda y ciudad', 'cultura economica', 'cartografias del sur',
    'revista iberoamericana de estudios municipales', 'cuadernos de politica exterior',
    'estudios sociales contemporaneos', 'analisis filosofico', 'cuyo anuario',
    'boletin de historia argentina', 'semiarida', 'huellas', 'perspectivas',
    'ideas', 'revista pilquen', 'intersecciones en antropologia', 'la zaranda de ideas',
    'publicar en antropologia', 'runa', 'ava', 'revista del museo de antropologia',
    'archivos de ciencias de la educacion', 'lenguas en contexto',
]


def venue_is_arg(venue, wl_norms):
    v = norm(venue)
    if not v:
        return False
    if BAD.search(venue):
        return False
    for b in VENUE_BLACK:
        nb = norm(b)
        if nb and (nb == v or nb in v or v in nb):
            return False
    for w in wl_norms:
        wn = norm(w)
        if not wn or len(wn) < 3:
            continue
        if v == wn:
            return True
        # 包含式匹配需长度比≥0.6，防止 Applied Linguistics 误配 Argentinian J. of Applied Linguistics
        if len(wn) >= 12 and wn in v and len(wn) >= 0.6 * len(v):
            return True
        if len(v) >= 12 and v in wn and len(v) >= 0.6 * len(wn):
            return True
    return False

# ---------------- 语言学科过滤 ----------------
STRONG_WORDS = re.compile(
    r'\b(?:lengua|lenguas|idioma|idiomas|lenguaje|language|languages|linguistic|'
    r'linguistics|linguistica|linguistica|bilingue|bilingues|bilingual|bilingualism|multilingual|'
    r'plurilingual|plurilingualism|multilingualism|espanol|castellano|ingles|english|'
    r'frances|french|portugues|portuguese|chino|chinese|mandarin|indigena|indigenas|'
    r'hablantes|alfabetizacion|literacy|escritura|lectura|gramatica|grammar|dialecto|'
    r'dialect|traduccion|translation|discurso|discourse|interlengua|interlanguage|'
    r'intonation|pronunciation|syntax|semantics|morfologia|morphology|pragmatica|'
    r'pragmatics|corpus|lexico|lexicon|vocabulary|phonology|fonologia|sociolinguistic|'
    r'sociolinguistica|pidgin|creole|intercultural|interculturalidad|biliteracy|'
    r'literacies|multiliteracies|translanguaging|code-switching|diglossia|'
    r'quechua|guarani|mapuche|mapudungun|toba|qom|wichi|nahuatl|mocovi|tapiete|chané|chane|'
    r'language\s+policy|language\s+planning|language\s+rights|language\s+ideolog|'
    r'language\s+contact|language\s+teaching|language\s+education|language\s+shift|'
    r'language\s+revitali|language\s+maintenance|language\s+attitude|glotopolitic)\b', re.I)

SHORT_WORD = re.compile(r'\b(?:ele|l2|sla|esp|efl|esl|clil|lsp|tefl|tesol)\b', re.I)

BAD = re.compile(
    r'\b(?:oncology|carcinoma|tumor|tumour|patient|patients|cancer|gene|genes|genom|'
    r'protein|enzyme|receptor|mice|mouse|rats?|vaccine|pandemic|earthquake|volcan|'
    r'geolog|mineral|hydrolog|glacier|accounting|audit|stock\s+market|inflation|gdp|banking|fintech|'
    r'diabetes|obesity|hypertension|dental|nursing|surgery|surgical|clinical\s+trial|'
    r'nanoparticle|polymer|catalys|electrode|semiconductor|laser|plasma|'
    r'wheat|soybean|maize|crop\s+yield|pesticide|fertiliz|livestock|'
    r'homicide|penal\s+code|fossil|paleontolog|astronom|astrophysic|'
    r'mental\s+health|psychosis|neurocognitive|rheumat|musculoskeletal|oral\s+health|'
    r'gad-7|psychiatr|anxiety|depress|reumatolog|radiolog|cardiolog|neurocirug|'
    r'otorrinolaringolog|dermatolog|neuropsicolog|toxicolog|hematolog|microbiolog)', re.I)

POLICY = re.compile(
    r'\b(?:policy|policies|politica|politicas|planning|planificacion|reform|reforma|'
    r'curricul\w*|law|laws|ley|leyes|legislat\w*|rights|derechos|ideolog\w*|ideologia|'
    r'attitude\w*|actitud\w*|discourse|discurso|identidad|standardization|'
    r'estandarizaci\w*|normativ\w*|glotopolitic\w*|inmigracion|inmigraci)\b', re.I)
EDUC = re.compile(
    r'\b(?:school|schools|escuela\w*|teacher\w*|docente\w*|profesor\w*|student\w*|'
    r'alumn\w*|estudiante\w*|classroom|aula\w*|teaching|ensenanza|didactic\w*|'
    r'pedagog\w*|educacion|educativa\w*|educativ\w*|eib|ebi|formacion|literacy|alfabetizacion)\b', re.I)
SOCIO = re.compile(
    r'\b(?:sociolinguist\w*|contacto|migration|migracion|migracion|migrant|inmigra\w*|'
    r'indigenous|indigena\w*|revitali\w*|vitalidad|shift|maintenance|mantenimiento|'
    r'identidad|ethnic|etnic|racismo|paisaje|landscape|comunidad\w*|hablantes)\b', re.I)


WEAK_ONLY = {'lengua', 'lenguas', 'lenguaje', 'language', 'languages', 'linguistic',
             'linguistics', 'linguistica', 'escritura', 'lectura', 'literacy',
             'literature', 'literacies', 'traduccion', 'translation', 'corpus'}


def is_lang(title, ab=''):
    t = title + ' ' + (ab or '')
    if BAD.search(title):
        return False
    return bool(STRONG_WORDS.search(t) or SHORT_WORD.search(t))


def weak_only(title):
    """标题命中全为泛词（多为文学研究，需人工甄别）"""
    hits = [m.group(0).lower() for m in STRONG_WORDS.finditer(title)] + \
           [m.group(0).lower() for m in SHORT_WORD.finditer(title)]
    return bool(hits) and set(hits) <= WEAK_ONLY


def relevance(title, ab=''):
    t = title + ' ' + (ab or '')
    a = bool(POLICY.search(t)); b = bool(EDUC.search(t)); c = bool(SOCIO.search(t))
    if a and b:
        return 'AB'
    if a and c:
        return 'A'
    if b:
        return 'B'
    if c:
        return 'C'
    if a:
        return 'A'
    return 'C'


def bin5(y):
    if not y:
        return ''
    if y < 1980:
        return '1980年以前'
    b = (y - 1980) // 5 * 5 + 1980
    return '%d-%d' % (b, b + 4)


def load_dialnet_titles():
    import openpyxl
    seen = set()
    wb = openpyxl.load_workbook(os.path.join(DESK, 'dialnet_language_corpus_merged_整理_补全_扩充.xlsx'),
                                read_only=True, data_only=True)
    ws = wb['Sheet2']
    for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
        if row[3]:
            seen.add(norm(row[3])[:70])
    wb.close()
    return seen


def main():
    wl = build_whitelist()
    print('whitelist size:', len(wl))
    wl_norms = wl

    seen = load_dialnet_titles()
    print('dialnet seen:', len(seen))

    cand = []
    stat_pool = Counter()

    def add(db, url, kw, title, venue, authors, year, ab):
        stat_pool[db] += 1
        if not venue_is_arg(venue, wl_norms):
            return 'notArg'
        if not title or len(title) < 12:
            return 'short'
        if not is_lang(title, ab):
            return 'notLang'
        k = norm(title)[:70]
        if k in seen:
            return 'dup'
        seen.add(k)
        cand.append({'db': db, 'url': url, 'kw': kw, 'title': title.strip().rstrip('.'),
                     'venue': venue.strip(' ;.'), 'authors': authors, 'year': year,
                     'abs': (ab or '')[:1800], 'cat': relevance(title, ab)})
        return 'ok'

    rejects = Counter()

    # 1) CONICET（全量解析）
    for it in json.load(io.open(os.path.join(WORK, 'conicet_all.json'), encoding='utf-8')):
        r = add('CONICET', it.get('url', ''), it.get('kw', ''), it.get('title', ''),
                it.get('venue', ''), it.get('authors', ''), it.get('year'),
                it.get('abstract', ''))
        rejects['CONICET:' + r] += 1

    # 2) ERIC + Crossref + EuropePMC 池
    for f in ['multi_pool.json', 'pool2.json']:
        for it in json.load(io.open(os.path.join(WORK, f), encoding='utf-8')):
            db = it.get('db', '?')
            if db == 'EuropePMC':
                pass  # 仍试，期刊白名单会拦
            r = add(db, it.get('url', ''), it.get('kw', ''), it.get('title', ''),
                    it.get('venue', ''), it.get('authors', ''), it.get('year'),
                    it.get('abstract', ''))
            rejects[db + ':' + r] += 1

    # 2b) Crossref 阿根廷期刊定向（ISSN 全量，第一批 + 第二批）
    for fname in ['cr_argjr.json', 'cr_argjr2.json']:
        fj = os.path.join(WORK, fname)
        if os.path.exists(fj):
            n0 = len([c for c in cand])
            for it in json.load(io.open(fj, encoding='utf-8')):
                r = add('Crossref', it.get('url', ''), it.get('kw', ''), it.get('title', ''),
                        it.get('venue', ''), it.get('authors', ''), it.get('year'),
                        it.get('abstract', ''))
                rejects['CR:' + r] += 1
            print(fname, 'kept +%d' % (len(cand) - n0))

    # 2c) 按 ISSN 白名单直接放行（Crossref 定向条目免期刊名匹配）
    try:
        ISSU = json.load(io.open(os.path.join(WORK, 'issn_whitelist.json'), encoding='utf-8'))
    except Exception:
        ISSU = {}
    # 只纳入学科对口的新增期刊（剔除 Estudios Rurales/Prudentia Iuris/历史类/Epistemus 音乐等）
    KEEP_NEW = {'1668-7426', '0328-9702', '2314-3932', '2362-6194', '1669-3914'}
    for issn, nm in ISSU.items():
        if issn in KEEP_NEW and nm not in wl:
            wl.append(nm)
    wl_norms = wl

    # 3) ProQuest 原始页
    pqraw = []
    for f in sorted(glob.glob(os.path.join(WORK, 'pq_page*.json')),
                    key=lambda p: int(re.search(r'page(\d+)', p).group(1))):
        pqraw.extend(json.load(io.open(f, encoding='utf-8')))
    print('pq raw', len(pqraw))
    YR = re.compile(r'\((?:[A-Za-z]{3,9}\.?\s*)?(?:\d{1,2},?\s*)?((?:19|20)\d{2})\)')
    for it in pqraw:
        title = (it.get('title') or '').strip().rstrip('.')
        fmt = it.get('fmt') or ''
        full = it.get('full') or ''
        ab = it.get('abs') or ''
        venue = ''
        j = re.match(r'^(.*?)(?:\s*;\s*[A-Za-zÀ-ÿ\.\s]+)?\s*Vol\.', fmt)
        if j:
            venue = re.sub(r'\s*;\s*[A-Za-zÀ-ÿ]{3,}\s*$', '', j.group(1)).strip(' ;.')
        year = None
        ym = YR.search(fmt) or YR.search(full)
        if ym:
            year = int(ym.group(1))
        r = add('ProQuest', 'https://www.proquest.com', 'language policy; language education', title,
                venue, it.get('authors', ''), year, ab)
        rejects['ProQuest:' + r] += 1

    print('pool sizes:', dict(stat_pool))
    print('rejects:', dict(rejects))
    print('kept(before manual drop):', len(cand))

    # 人工甄别剔除：纯文学评论/书评/心理量表/艺术类（2026-10-21 逐条核过）
    MANUAL_DROP = [
        'El Archivo Arturo Costa Álvarez',
        '«Defender mi boliche literario',
        'Viajes de la escritura literaria',
        'fantástico como',
        'Fragmento, memoria y escritura: Museo de la Bruma',
        'El régimen despótico de la escritura epistolar',
        'La escritura espacial de Roberto Bolaño',
        'Escritura y traducción en América Latina',
        'Transcrippled subjectivity',
        'Translation and Spread of Hispanic Litterature',
        'La escritura de la Unión Soviética',
        'Reminders of a language in Diamela Eltit',
        'Los Diarios de Rafael Chirbes',
        'Reseña de La escritura meta-final',
        'Translation Scenes in Inca Garcilaso',
        'Reseña de Ciudad y escritura',
        'Violencia, comunidad y escritura',
        'El régimen de la ficción en la prensa mexicana',
        'Aguas cerradas: cuerpo, experiencia y escritura',
        'Reseña de Cuerpos ilegales',
        'Paisaje y escritura en Los llanos',
        'The desiring tongue',
        'Lecciones de lengua mexicana',
        'Escritura y producción de conocimiento en las artes',
        'Didáctica de la lengua y la literatura. Diez temas',
        'Siete miradas sobre el lenguaje inclusivo',
        'Reseña del Manual para estudiar textos académicos',
        'Evaluación de las dimensiones del desarrollo socioemocional',
        'Psychometric Properties of a Peruvian Translation',
    ]
    before = len(cand)
    cand = [c for c in cand
            if not any(d in c['title'] for d in MANUAL_DROP)]
    print('manual drop:', before - len(cand), '-> kept', len(cand))

    print('cat:', Counter(c['cat'] for c in cand))
    print('db:', Counter(c['db'] for c in cand))
    print('year:', Counter(bin5(c['year']) for c in cand).most_common())
    io.open(os.path.join(WORK, 'final_argjr.json'), 'w', encoding='utf-8').write(
        json.dumps(cand, ensure_ascii=False, indent=1))
    print('\n--- 期刊分布 ---')
    for v, n in Counter(c['venue'] for c in cand).most_common(30):
        print(' %3d %s' % (n, v[:70]))


if __name__ == '__main__':
    main()
