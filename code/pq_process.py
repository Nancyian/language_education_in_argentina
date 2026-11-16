# -*- coding: utf-8 -*-
"""处理 ProQuest 抓取结果：解析 fmt -> 期刊/卷/期/年份，过滤语言学科 + 阿根廷锚定，
与 Dialnet 317 + 多库 152 去重，输出 work/final_pq.json"""
import io, json, os, re, sys, glob
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
DESK = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语'

# ---------- 语言学科词表（复用多库逻辑） ----------
STRONG_WORDS = re.compile(
    r'\b(?:lengua|lenguas|idioma|idiomas|lenguaje|language|languages|linguistic|'
    r'linguistics|linguistica|bilingue|bilingues|bilingual|bilingualism|multilingual|'
    r'plurilingual|plurilingualism|multilingualism|espanol|castellano|ingles|english|'
    r'frances|french|portugues|portuguese|chino|chinese|mandarin|indigena|indigenas|'
    r'hablantes|alfabetizacion|literacy|escritura|lectura|gramatica|grammar|dialecto|'
    r'dialect|traduccion|translation|discurso|discourse|interlengua|interlanguage|'
    r'intonation|pronunciation|syntax|semantics|morfologia|morphology|pragmatica|'
    r'pragmatics|corpus|lexico|lexicon|vocabulary|phonology|fonologia|sociolinguistic|'
    r'sociolinguistica|pidgin|creole|intercultural|interculturalidad|biliteracy|'
    r'literacies|multiliteracies|translanguaging|code-switching|diglossia|'
    r'language\s+policy|language\s+planning|language\s+rights|language\s+ideolog|'
    r'language\s+contact|language\s+teaching|language\s+education|language\s+shift|'
    r'language\s+revitali|language\s+maintenance|language\s+attitude)\b', re.I)

# 明显非语言学科
BAD = re.compile(
    r'\b(?:oncology|carcinoma|tumor|tumour|patient|patients|cancer|gene|genes|genom|'
    r'protein|enzyme|receptor|mice|mouse|rats?|covid|sars-cov|vaccine|pandemic|'
    r'earthquake|volcan|geolog|mineral|hydrolog|climate\s+change|glacier|'
    r'accounting|audit|tax\s+evasion|stock\s+market|inflation|gdp|banking|fintech|'
    r'diabetes|obesity|hypertension|dental|nursing|surgery|surgical|clinical\s+trial|'
    r'nanoparticle|polymer|catalys|electrode|semiconductor|laser|plasma|'
    r'wheat|soybean|maize|crop\s+yield|pesticide|fertiliz|livestock|'
    r'constitutional\s+court|supreme\s+court|amparo|penal\s+code|homicide|'
    r'archaeolog|paleontolog|fossil|prehistor|ceramic|pottery|'
    r'earth\s+observation|satellite|remote\s+sensing|astronom|astrophysic)\b', re.I)

ARG = re.compile(
    r'\b(?:argentin\w*|buenos\s+aires|patagoni\w*|rioplatense|'
    r'r[ií]o\s+de\s+la\s+plata|merc\w*sur|mapuche\w*|guaran[ií]\w*|quechua\w*|'
    r'qom|wich[ií]|toba|aymara\w*|diaguita|calchaqu[ií]|pampa\w*|'
    r'c[oó]rdoba|mendoza|tucum[aá]n|salta|jujuy|chaco|misiones|neuqu[eé]n|'
    r'r[ií]o\s+negro|chubut|santa\s+fe|entre\s+r[ií]os|corrientes|formosa|'
    r'la\s+plata|rosario|mar\s+del\s+plata|bah[ií]a\s+blanca|ushuaia|'
    r'caba|conurbano|gran\s+buenos\s+aires|villa\s+\d+|'
    r'espa[nñ]a|spain|chile|chilean|uruguay\w*|paraguay\w*|bolivia\w*|'
    r'per[uú]|peruvian|brasil|brazil|m[eé]xic\w*|colombia\w*|'
    r'latin\s+america\w*|latinoameric\w*|sudam[eé]rica|south\s+america\w*|'
    r'andes|andino|andina|bilingual\s+intercultural)\b', re.I)

# 强相关信号（政策/教育/社会语言学三簇）
POLICY = re.compile(
    r'\b(?:policy|policies|politica|politicas|planning|planificacion|'
    r'reform|reforma|curricul\w*|curriculum|law|laws|ley|leyes|legislat\w*|'
    r'rights|derechos|ideolog\w*|ideologia|attitude\w*|actitud\w*|'
    r'discourse|discurso|national\s+identity|identidad\s+nacional|'
    r'standardization|estandarizaci\w*|normativ\w*|regulat\w*)\b', re.I)
EDUC = re.compile(
    r'\b(?:school|schools|escuela\w*|teacher\w*|docente\w*|profesor\w*|'
    r'student\w*|alumn\w*|estudiante\w*|classroom|aula\w*|teaching|'
    r'ensenanza|didactic\w*|didactica|pedagog\w*|pedagogia|'
    r'higher\s+education|universit\w*|universidad\w*|'
    r'education|educacion|educativ\w*|educativa\w*|'
    r'intercultural\s+bilingual\s+education|ebi|eib|'
    r'teacher\s+training|formacion\s+docente|literacy|alfabetizacion)\b', re.I)
SOCIO = re.compile(
    r'\b(?:sociolinguist\w*|sociolinguistica|contacto\s+de\s+lenguas|'
    r'language\s+contact|migration\w*|migraci\w*|migrant\w*|inmigra\w*|'
    r'indigenous|indigena\w*|pueblo\w*\s+originari\w*|revitali\w*|'
    r'vitality|vitalidad|shift|desplazamiento|maintenance|mantenimiento|'
    r'identity|identidad|ethnic\w*|etnic\w*|racism|racismo|'
    r'glotopolitic\w*|glotopolitica|landscape|paisaje\s+linguistico)\b', re.I)


def norm(s):
    s = (s or '').lower()
    s = re.sub(r'[áàä]', 'a', s); s = re.sub(r'[éèë]', 'e', s)
    s = re.sub(r'[íìï]', 'i', s); s = re.sub(r'[óòö]', 'o', s)
    s = re.sub(r'[úùü]', 'u', s); s = s.replace('ñ', 'n')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


FMT = re.compile(
    r'^(?P<journal>.*?)(?:\s*;\s*[A-Za-zÀ-ÿ\.\s]+)?\s*Vol\.\s*(?P<vol>[\d]+)'
    r'(?:\s*,\s*Iss\.\s*(?P<iss>[^,]+))?'
    r'(?:,\s*(?P<date>\([^)]*\)))?\s*:\s*(?P<pages>[\d\-\+]+)\.?$')

YR = re.compile(r'\((?:[A-Za-z]{3}[a-z]*\s*)?(?:[A-Za-z]{3}[a-z]*\s*[-–]\s*[A-Za-z]{3}[a-z]*\s*)?((?:19|20)\d{2})')


def parse_fmt(fmt):
    """返回 journal, year"""
    journal, year = '', None
    if not fmt:
        return journal, year
    m = FMT.match(fmt.strip())
    if m:
        j = m.group('journal').strip()
        j = re.sub(r'\s*;\s*[A-Za-zÀ-ÿ]{3,}\s*$', '', j)   # 去城市名 (Philadelphia/London...)
        journal = j.strip(' .;')
        d = m.group('date') or ''
        ym = YR.search(d)
        if ym:
            year = int(ym.group(1))
    if not year:
        ym = YR.search(fmt)
        if ym:
            year = int(ym.group(1))
    if not journal:
        journal = re.sub(r'\s*(Vol\.|$).*', '', fmt).strip(' ;.')
    return journal, year


def bin5(y):
    if not y:
        return ''
    if y < 1980:
        return '1980年以前'
    b = (y - 1980) // 5 * 5 + 1980
    return '%d-%d' % (b, b + 4)


def clean_authors(a):
    if not a:
        return ''
    parts = [p.strip(' .;') for p in re.split(r';', a) if p.strip(' .;')]
    out, seen = [], []
    for p in parts:
        k = norm(p)
        if not k or k in seen:
            continue
        seen.append(k)
        out.append(p)
    return '; '.join(out)


def relevance(title, ab, fmt):
    t = title + ' ' + (ab or '') + ' ' + (fmt or '')
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


def is_lang(title, ab):
    t = title + ' ' + (ab or '')
    if BAD.search(title):
        return False
    if STRONG_WORDS.search(t):
        return True
    return False


def load_pq():
    items = []
    for f in sorted(glob.glob(os.path.join(WORK, 'pq_page*.json')),
                    key=lambda p: int(re.search(r'page(\d+)', p).group(1))):
        d = json.load(io.open(f, encoding='utf-8'))
        items.extend(d)
        print('load', os.path.basename(f), len(d))
    return items


def main():
    # 已有库的标题指纹
    import openpyxl
    seen = set()
    dn = os.path.join(DESK, 'dialnet_language_corpus_merged_整理_补全_扩充.xlsx')
    wb = openpyxl.load_workbook(dn, read_only=True, data_only=True)
    ws = wb['Sheet2']
    for r in ws.iter_rows(min_row=2, max_row=3, max_col=4, values_only=True):
        pass
    for row in ws.iter_rows(min_row=2, max_col=4, values_only=True):
        if row[3]:
            seen.add(norm(row[3])[:70])
    wb.close()
    print('dialnet titles:', len(seen))

    prev = json.load(io.open(os.path.join(WORK, 'final_multi.json'), encoding='utf-8'))
    for it in prev:
        seen.add(norm(it['title'])[:70])
    print('+multi titles -> total seen:', len(seen))

    raw = load_pq()
    print('pq raw:', len(raw))

    cand, drop_bad, drop_dup, drop_arg = [], 0, 0, 0
    for it in raw:
        title = (it.get('title') or '').strip().rstrip('.')
        if len(title) < 12:
            drop_bad += 1; continue
        ab = it.get('abs') or ''
        if not is_lang(title, ab):
            drop_bad += 1; continue
        key = norm(title)[:70]
        if key in seen:
            drop_dup += 1; continue
        journal, year = parse_fmt(it.get('fmt') or '')
        if not year:
            # 回退：整条结果文本里第一个 (年份) 或 (Mon 年份)
            full = it.get('full') or ''
            ym = re.search(r'\((?:[A-Za-z]{3,9}\.?\s*)?(?:\d{1,2},?\s*)?((?:19|20)\d{2})\)', full)
            if not ym:
                ym = re.search(r'\b((?:19|20)\d{2})\b', full)
            if ym:
                year = int(ym.group(1))
        if not journal:
            # 学位论文等：取标题后、作者后的机构/学校名
            full = it.get('full') or ''
            m2 = re.search(r'\.\s*([A-Z][^.]{6,90}(?:University|Universidad|College|Institute|Universidade)[^.]{0,40})\.', full)
            if m2:
                journal = m2.group(1).strip()
        blob = title + ' ' + ab + ' ' + journal
        if not ARG.search(blob):
            drop_arg += 1; continue
        seen.add(key)
        cand.append({
            'source': 'ProQuest',
            'host': 'proquest.com',
            'title': title,
            'authors': clean_authors(it.get('authors')),
            'venue': journal,
            'year': year,
            'abs': ab,
            'cat': relevance(title, ab, journal),
        })

    print('drop bad=%d dup=%d not-arg=%d -> keep %d' % (drop_bad, drop_dup, drop_arg, len(cand)))
    io.open(os.path.join(WORK, 'final_pq.json'), 'w', encoding='utf-8').write(
        json.dumps(cand, ensure_ascii=False, indent=1))
    from collections import Counter
    print('cat:', Counter(c['cat'] for c in cand))
    print('year:', Counter(bin5(c['year']) for c in cand).most_common())
    for c in cand[:8]:
        print(' -', c['cat'], c['year'], '|', c['venue'][:40], '|', c['title'][:60])


if __name__ == '__main__':
    main()
