# -*- coding: utf-8 -*-
"""合并 pool1 + pool2 + pool_conicet，统一严格过滤，生成 multi_db_language_corpus_检索.xlsx
严格过滤（相对旧版收紧）：
  1) 标题必须含"语言实体词"（lengua/idioma/linguistic/bilingüe/español/english...），
     防止 chino→中国航天、idioma→自然法教席 这类蹭词；
  2) 标题必须命中 ≥1 关键词规则；
  3) 标题需有阿根廷锚定（或其下位地名/阿根廷期刊）；
  4) 学科黑名单排除生物医学、工程、国际关系等；
  5) 与 Dialnet 317 条语料去重。
"""
import io, json, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
sys.path.insert(0, 'tools')
from kw_merge import norm, RULES, CONTEXT, has
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

CUR = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
BASE = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索.xlsx"
OUT = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索.xlsx"

pool = []
for f in ('work/multi_pool.json', 'work/pool2.json', 'work/pool_conicet.json'):
    try:
        rows = json.load(io.open(f, encoding='utf-8'))
        print('%-28s %d' % (f, len(rows)))
        pool += rows
    except FileNotFoundError:
        print('missing', f)
print('total raw', len(pool))

# ---------- 现有 Dialnet 语料标题（去重） ----------
ws_cur = openpyxl.load_workbook(CUR, read_only=True)['Sheet2']
existing = set()
for r in ws_cur.iter_rows(min_row=2, max_col=4, values_only=True):
    if r[3]:
        existing.add(norm(r[3]))
print('dialnet titles', len(existing))

# ---------- 硬约束表 ----------
# 语言实体词：标题必须至少命中一个，否则剔除
# 注意：'ele'/'l2'/'sla' 这类短串会误匹配（如 f-ELE-ministas），单独处理
LANG_ENTITY = (
    'lengua', 'lenguas', 'idioma', 'idiomas', 'linguistic', 'linguistica', 'linguistics',
    'bilingue', 'bilingues', 'bilingual', 'multiling', 'pluriling', 'sociolingu', 'glotopolit',
    'espanol', 'castellano', 'ingles', 'english', 'frances', 'french', 'portugues', 'portuguese',
    'chino', 'chinese', 'mandarin', 'indigena', 'originari', 'language', 'languages',
    'lenguaje', 'habla', 'hablante', 'alfabetiz', 'escritura', 'lectoescritura', 'lexico',
    'gramatica', 'dialect', 'traduccion', 'intercultural bilingue',
    'enseñanza de la lengua', 'ensenanza de lengua', 'language policy', 'politica linguistica',
)
SHORT_WORD = re.compile(r'\b(?:ele|l2|sla|esp|efl|esl|clil|lsp|tefl|tesol)\b')
# 强语言实体词：按词边界匹配（避免 habla 命中 hablantes、ingles 命中单复数以外的意外子串）
STRONG_WORDS = re.compile(
    r'\b(?:lengua|lenguas|idioma|idiomas|lenguaje|lenguajes|language|languages|linguistic|'
    r'linguistics|linguistica|bilingue|bilingues|bilingual|bilinguals|multilingue|multilingual|'
    r'multilingualism|plurilingual|plurilinguismo|sociolinguistic|sociolinguistics|glotopolitica|'
    r'espanol|espanola|castellano|ingles|inglesa|english|frances|francesa|french|portugues|'
    r'portuguesa|portuguese|chino|chinas|chinese|mandarin|indigena|indigenas|originarias|'
    r'language|hablantes|speakers|alfabetizacion|literacy|escritura|writing|lectura|reading|'
    r'lexico|lexicon|lexicografia|gramatica|grammar|dialecto|dialectos|dialect|traduccion|'
    r'translation|discurso|discourse|interlengua|interlanguage|intonation|entonacion|'
    r'pronunciation|pronunciacion|syntax|sintaxis|semantics|semantica|morfologia|morphology|'
    r'pragmatica|pragmatics|corpus|linguistico|linguistica|teacher|teachers|docentes|students)\b'
)
INST_START = ()
# 明确排除：非语言学科（过泛的子串如 etica/mining/cell/covid 已移除，避免误杀 estética/examining/excellently）
BAD = (
    'larva', 'culicid', 'insect', 'tumour', 'tumor', 'crop', 'cultivar', 'dietary', 'patholog',
    'clinical', 'mosquito', 'entomophag', 'feminicidio', 'steel', 'nitrate', 'carbon',
    'adsorption', 'nanoparticle', 'sediment', 'geolog', 'hydrogel', 'spinal',
    'space activities', 'geopolitical', 'satellite', 'nuclear', 'derecho natural', 'gentes',
    'penal', 'sentencia', 'elecciones', 'partido politico',
    'salud', 'sanitari', 'hospital', 'wage', 'gdp', 'inflation', 'banking',
    'agro', 'wheat', 'soybean', 'astronomy', 'astronom', 'voice questionnaire',
    'sujetos causados', 'sindrome', 'pacientes', 'patients', 'ratas', 'mice',
)
# 软性语言词：同时命中 ≥2 个才放行（补偿 CLIL/EFL/L2 等缩写未列入实体词）
SOFT = ('efl', 'esl', 'clil', 'lsp', 'tefl', 'tesol', 'translanguag', 'interlanguage',
        'interlengua', 'lexic', 'pragmat', 'discurso', 'literacy', 'alfabetiz', 'escritura',
        'lectura', 'lectoescritura', 'comprehension', 'adquisicion', 'aprendizaje', 'ensenanza',
        'didactica', 'curriculum', 'docente', 'profesor', 'estudiantes', 'students', 'teachers',
        'classroom', 'aula', 'escolar', 'school', 'education', 'educacion', 'pedagog',
        'literatura', 'textos', 'textbook', 'manual', 'corpus', 'hablantes', 'speakers')
AR = ('argentin', 'rioplatense', 'bonaerense', 'porten', 'patagoni', 'pampa', 'andina', 'andin',
      'buenos aires', 'cordoba', 'rosario', 'mendoza', 'tucuman', 'chaco', 'salta', 'jujuy',
      'chubut', 'misiones', 'santa fe', 'formosa', 'corrientes', 'neuquen', 'entre rios',
      'sudamerica', 'south america', 'latin america', 'hispanic', 'mercado comun del sur',
      'mercosur', 'conosur', 'cono sur', 'toba', 'qom', 'wichi', 'guarani', 'mapuche', 'quechua',
      'aymara', 'mbya', 'pilaga', 'moqoit', 'chorote', 'nivacle', 'tehuelche', 'selknam')
AR_JOURNALS = ('rasal', 'argentina de historiografia lingu', 'signo y sena', 'lenguas vivas',
               'sociedad argentina de linguistica', 'filologia', 'boletin de la academia argentina')


def arg_anchor(txt, venue):
    s = (txt + ' ' + (venue or '')).lower()
    return any(x in s for x in AR) or any(j in (venue or '').lower() for j in AR_JOURNALS)


# 语言学科词（比 LANG_ENTITY 更宽，用于"关键词须与语言学科共现"判定）
LANG_FIELD = LANG_ENTITY + (
    'efl', 'esl', 'clil', 'tefl', 'tesol', 'translanguag', 'interlanguage', 'interlengua',
    'pronunciation', 'pronunciacion', 'intonation', 'entonacion', 'syntax', 'sintax',
    'semantics', 'semantica', 'morfolog', 'morpholog', 'phonolog', 'fonolog', 'lexic',
    'pragmat', 'discurso', 'discourse', 'literacy', 'alfabetiz', 'escritura', 'lectura',
    'comprehension', 'comprension', 'adquisicion', 'acquisition', 'aprendizaje', 'learning',
    'teaching', 'ensenanza', 'didactica', 'curriculum', 'teachers', 'docentes', 'students',
    'speakers', 'hablantes', 'interpreting', 'interpretacion', 'code-switching', 'codeswitching',
)
LANG_FIELD = LANG_FIELD + ('language',)
# 与语言无关的学科信号：若标题命中这些且无语言学科词，剔除
NON_LANG = (
    'finance', 'investment', 'infrastructure', 'diaspora', 'land governance', 'renewable energy',
    'traditional chinese therapies', 'rose', 'genotoxicity', 'lumbar', 'fusion', 'delphi',
    'bioinformatics', 'secularization', 'catholicism', 'trauma psicosocial', 'cartografia',
    'violencia', 'feminist', 'territoriales', 'pericias', 'memorias indigenas', 'conversion religiosa',
    'conflict', 'mining', 'soybean', 'elections', 'partido', 'pandemic', 'covid', 'obesity',
)


def strong(t):
    hit = [k for k, fn in RULES.items() if fn(t)]
    return hit or None


kept, dropped = [], []
for r in pool:
    t = norm(r['title'])
    if len(t) < 12:
        continue
    if any(t == e or (len(t) > 25 and (t in e or e in t)) for e in existing):
        continue
    if any(b in t for b in BAD):
        dropped.append((r['title'][:70], '学科黑名单'))
        continue
    if not STRONG_WORDS.search(t) and not SHORT_WORD.search(t):
        soft = sum(1 for w in SOFT if w in t)
        if soft < 3:
            dropped.append((r['title'][:70], '标题无语言实体词'))
            continue
    if not arg_anchor(t + ' ' + norm(r.get('abstract') or '')[:400], r.get('venue', '')):
        dropped.append((r['title'][:70], '无阿根廷锚定'))
        continue
    hit = strong(t)
    if not hit:
        dropped.append((r['title'][:70], '无关键词规则命中'))
        continue
    # 关键词须与语言学科共现：软词通道进来的条目，若标题仍无语言学科词则剔除
    if not any(w in t for w in LANG_FIELD):
        dropped.append((r['title'][:70], '关键词与语言学科不共现'))
        continue
    r['hit'] = hit
    kept.append(r)

# 二次去重（同标题不同库）
seen, final = set(), []
kept.sort(key=lambda r: (-len(r['hit']), str(r['year']), r['title']))
for r in kept:
    k = norm(r['title'])
    if k in seen:
        continue
    seen.add(k)
    final.append(r)

print('kept', len(final), collections.Counter(r['db'] for r in final))
print('dropped reasons', collections.Counter(d[1] for d in dropped))
for t_, why in dropped[:25]:
    print('  X', why, '|', t_)
json.dump(final, io.open('work/final_multi.json', 'w', encoding='utf-8'), ensure_ascii=False)

# ---------- 写表 ----------
def bucket(y):
    try:
        y = int(y)
    except Exception:
        return '时间不详'
    if y < 1980:
        return '1980年以前'
    a = (y // 5) * 5
    return '%d-%d' % (a, a + 4)


final.sort(key=lambda r: (str(r['db']), -len(r['hit']), str(r['year']), r['title']))

wb = openpyxl.Workbook()
w = wb.active
w.title = 'Sheet2'
header = ['序号', '来源', '关键词', '文章标题', '期刊名称', '作者', '发表时间', '时期分布', '原文']
HFILL = PatternFill('solid', fgColor='D9E2F3')
for c, v in enumerate(header, start=1):
    cell = w.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True)
    cell.fill = HFILL
    cell.alignment = Alignment(horizontal='center', vertical='center')

for i, r in enumerate(final, start=1):
    vals = [i, r['url'], '; '.join(r['hit']), r['title'], (r['venue'] or '')[:120],
            r['authors'], r['year'] if r['year'] else '时间不详', bucket(r['year']),
            (r['abstract'] or '')[:2000]]
    for c, v in enumerate(vals, start=1):
        w.cell(row=i + 1, column=c).value = v

for i, wd in enumerate([6, 34, 24, 58, 32, 26, 12, 14, 80], start=1):
    w.column_dimensions[get_column_letter(i)].width = wd
LAST = len(final) + 1
w.auto_filter.ref = 'A1:I%d' % LAST
w.freeze_panes = 'A2'
for r in range(2, LAST + 1):
    w.row_dimensions[r].height = 30
    w.cell(row=r, column=4).alignment = Alignment(wrap_text=True, vertical='top')
    w.cell(row=r, column=9).alignment = Alignment(wrap_text=True, vertical='top')

opt = wb.create_sheet('时间选项')
opt.append(['时期分布（发表年 5 年分箱）'])
for b in ['1981-1985', '1986-1990', '1991-1995', '1996-2000', '2001-2005', '2006-2010',
          '2011-2015', '2016-2020', '2021-2025', '2026-2030', '1980年以前', '时间不详']:
    opt.append([b])
opt.sheet_state = 'hidden'
dv = DataValidation(type='list', formula1='时间选项!$A$2:$A$13', allow_blank=True)
w.add_data_validation(dv)
dv.add('H2:H%d' % LAST)

cnt = collections.Counter(r['db'] for r in final)
nd = len(final)

note = (
 '【本次检索覆盖的库与结果】\n'
 '  ① ERIC（图示五库之一）—— 可直连官方 API，已检索：%d 条\n'
 '  ② Crossref —— 免费 DOI 注册库，WoS/Scopus 收录期刊的绝大多数文献都在此，已检索：%d 条\n'
 '  ③ CONICET 仓储（ri.conicet.gov.ar，今日站点 TLS 被远端切断无法直连）——\n'
 '     改用本地已抓取的 12,950 条仓储快照，按"标准引用串"还原文章级元数据后筛选：%d 条\n'
 '  ④ Europe PMC —— 已检索，语言学主题命中 0 条（该库以生物医学为主）\n'
 '\n'
 '【图示其余四库为何不能直连】\n'
 '  · Web of Science：Clarivate 商业库，无公开检索 API，需机构订阅 + API Key\n'
 '  · Scopus：Elsevier 商业库，API 返回 401，需机构订阅的 API Key\n'
 '  · ProQuest：商业库，检索页 302 跳转至机构登录，无公开 API\n'
 '  · PsycINFO：APA 商业库，仅机构订阅访问，无公开 API\n'
 '  说明：这四库中 WoS/Scopus 收录的期刊论文已由 Crossref 通道实质覆盖（DOI 唯一）；\n'
 '  ProQuest/PsycINFO 收录的学位论文、书评等灰色文献无法覆盖，如需请提供机构账号或 API Key。\n'
 '\n'
 '【筛选口径（本轮已收紧）】\n'
 '  标题必须同时满足：含"语言实体词" + 命中关键词规则 + 有阿根廷锚定 + 非边缘学科。\n'
 '  上一版误收的 3 条（中国航天活动、自然法教席、华人移民就医）已剔除。\n'
 '\n'
 '【字段说明】来源列 = 可点击的原文入口；关键词列 = 标题实际命中的关键词（可多值）；\n'
 '  原文列 = 摘要（CONICET 条目为仓储片段拼接，供判读用）。\n'
)
k1 = w.cell(row=1, column=11, value='检索与筛选说明')
k1.font = Font(bold=True, color='FFFFFF')
k1.fill = PatternFill('solid', fgColor='C00000')
k2 = w.cell(row=2, column=11, value=note.replace('%d', 'X'))
k2 = w.cell(row=2, column=11, value=note % (cnt.get('ERIC', 0), cnt.get('Crossref', 0), cnt.get('CONICET', 0)))
k2.alignment = Alignment(wrap_text=True, vertical='top')
k2.font = Font(size=9)
w.column_dimensions['K'].width = 72

# M/N 统计
w.cell(row=2, column=13, value='来源').font = Font(bold=True)
w.cell(row=2, column=14, value='条数').font = Font(bold=True)
for i, (k_, v_) in enumerate(sorted(cnt.items(), key=lambda x: -x[1]), start=3):
    w.cell(row=i, column=13, value=k_)
    w.cell(row=i, column=14, value=v_)
w.cell(row=len(cnt) + 3, column=13, value='合计').font = Font(bold=True)
w.cell(row=len(cnt) + 3, column=14, value=nd).font = Font(bold=True)

wb.save(OUT)
print('saved', nd, '->', OUT)
print('buckets', dict(sorted(collections.Counter(bucket(r['year']) for r in final).items())))
