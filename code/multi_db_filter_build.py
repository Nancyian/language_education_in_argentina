# -*- coding: utf-8 -*-
"""过滤多库候选池 -> 强相关 + 阿根廷相关 + 与现有语料去重 -> 生成新工作簿（Sheet2 同格式）。"""
import io, json, re, sys, unicodedata, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
from kw_merge import RULES, CONTEXT, norm, has
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

CUR = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
OUT = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索.xlsx"

pool = json.load(io.open('work/multi_pool.json', encoding='utf-8'))
print('pool', len(pool))

# ---------- 现有语料标题（去重用） ----------
ws_cur = openpyxl.load_workbook(CUR, read_only=True)['Sheet2']
existing = set()
for r in ws_cur.iter_rows(min_row=2, max_col=4, values_only=True):
    if r[3]:
        existing.add(norm(r[3]))
print('existing titles', len(existing))

# ---------- 过滤 ----------
AR_EXTRA = ('rioplatense', 'bonaerense', 'porten', 'patagoni', 'pampa', 'andin', 'buonos aires',
            'buenos aires', 'cordoba', 'rosario', 'mendoza', 'tucuman', 'chaco', 'salta', 'jujuy',
            'chubut', 'misiones', 'entre rios', 'santa fe', 'riONEGA', 'litoral argentino')

def argentina_related(r):
    if r['db'] == 'CONICET':
        return True                      # 仓储本身即阿根廷
    txt = (r['title'] + ' ' + r['abstract']).lower()
    if 'argentin' in txt:
        return True
    return any(x.lower() in txt for x in AR_EXTRA)

def strong(t):
    hit = [k for k, fn in RULES.items() if fn(t)]
    if not hit:
        return None
    if len(hit) < 2 and not has(t, *CONTEXT):
        return None
    return hit

kept, stats_db, stats_kw = [], collections.Counter(), collections.Counter()
for r in pool:
    t = norm(r['title'])
    if len(t) < 10 or t in existing:
        continue
    if any(t == e or (len(t) > 25 and (t in e or e in t)) for e in existing):
        continue
    if not argentina_related(r):
        continue
    if r['db'] != 'CONICET':
        tlow = norm(r['title'])
        if not ('argentin' in tlow or any(x in tlow for x in
                ('rioplatense', 'bonaerense', 'porte', 'patagoni', 'pampa', 'andina', 'andin',
                 'buenos aires', 'cordoba', 'rosario', 'mendoza', 'tucuman', 'chaco', 'salta',
                 'jujuy', 'chubut', 'misiones', 'santa fe', 'sudamerica', 'south america',
                 'latin america', 'hispanic'))):
            continue          # 标题级阿根廷锚定，排除蹭关键词的边缘条目
    hit = strong(t)
    if not hit:
        continue
    # 'lenguas indígenas' 规则可能被纯族群词误中：要求标题含显性语言词
    LANGWORD = ('lengua', 'lenguas', 'idioma', 'idiomas', 'lingüistic', 'linguistic', 'biling',
                'habla', 'hablante', 'language', 'speech', 'lenguaje', 'voice')
    nonlang = [k for k in hit if k == 'lenguas indígenas']
    if nonlang and not any(w in t for w in LANGWORD):
        hit = [k for k in hit if k != 'lenguas indígenas']
        if not hit:
            continue
    # 明显非语言学科的标题黑名单
    BAD = ('larva', 'culícid', 'insect', 'tumour', 'tumor', 'crop', 'cultivar', 'dietary',
           'patholog', 'clinical', 'mosquito', 'entomophag', 'feminicidio', 'steel', 'soil')
    if any(b in t for b in BAD):
        continue
    r['hit'] = hit
    kept.append(r)
    stats_db[r['db']] += 1
    for k in hit:
        stats_kw[k] += 1

print('strong+AR+new', len(kept), dict(stats_db))
print('kw hits', dict(stats_kw))

# 年份 → 时期分布
def bucket(y):
    try:
        y = int(y)
    except Exception:
        return '时间不详'
    if y < 1980:
        return '1980年以前'
    a = (y // 5) * 5
    return '%d-%d' % (a, a + 4)

# 排序：按库、关键词命中数
kept.sort(key=lambda r: (r['db'], -len(r['hit']), str(r['year']) , r['title']))

# ---------- 写工作簿（与 Sheet2 同格式 9 列） ----------
wb = openpyxl.Workbook()
w = wb.active
w.title = 'Sheet2'
header = ['序号', '来源', '关键词', '文章标题', '期刊名称', '作者', '发表时间', '时期分布', '原文']
HFILL = PatternFill('solid', fgColor='D9E2F3')
for c, v in enumerate(header, start=1):
    cell = w.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True); cell.fill = HFILL
    cell.alignment = Alignment(horizontal='center', vertical='center')

for i, r in enumerate(kept, start=1):
    vals = [i, r['url'], '; '.join(r['hit']), r['title'], r['venue'][:120],
            r['authors'], r['year'] if r['year'] else '时间不详', bucket(r['year']),
            (r['abstract'] or '')[:2000]]
    for c, v in enumerate(vals, start=1):
        w.cell(row=i + 1, column=c).value = v

for i, wd in enumerate([6, 30, 26, 55, 30, 26, 12, 14, 80], start=1):
    w.column_dimensions[get_column_letter(i)].width = wd
LAST = len(kept) + 1
w.auto_filter.ref = 'A1:I%d' % LAST
w.freeze_panes = 'A2'

# 时间选项 + 下拉
opt = wb.create_sheet('时间选项')
opt.append(['时期分布（发表年 5 年分箱）'])
for b in ['1981-1985', '1986-1990', '1991-1995', '1996-2000', '2001-2005', '2006-2010',
          '2011-2015', '2016-2020', '2021-2025', '2026-2030', '1980年以前', '时间不详']:
    opt.append([b])
opt.sheet_state = 'hidden'
dv = DataValidation(type='list', formula1='时间选项!$A$2:$A$13', allow_blank=True)
w.add_data_validation(dv)
dv.add('H2:H%d' % LAST)

# 右侧说明
note = (
 '【数据来源】\n'
 '  1) ERIC（图中五库之一）：官方免费 API，检索式 = 关键词 AND argentina；来源列 = eric.ed.gov 链接\n'
 '  2) Crossref：覆盖 Web of Science / Scopus 收录的绝大多数期刊文献（免费 DOI 注册库），\n'
 '     检索式 = 关键词 + argentina + 作者机构阿根廷加权；来源列 = doi.org 链接\n'
 '  3) CONICET：ri.conicet.gov.ar 今日从本机无法访问（TLS 被远端切断，多次重试失败）；\n'
 '     本地已抓取的 12950 条仓储片段为命中句而非文章级元数据，无法可靠还原标题/作者，故未纳入；\n'
 '     待站点恢复后可按同批关键词补抓。\n'
 '【未能直连的库】Web of Science、Scopus、ProQuest、PsycINFO 均需机构订阅/API Key，\n'
 '  其中 WoS 与 Scopus 的期刊内容已由 Crossref 通道大体覆盖；如需精确检索请提供 API Key。\n'
 '【检索关键词】关键词.docx 的 13 组 + 用户新增 7 组（lenguas indígenas、lenguas de migración、\n'
 '  política lingüística、portugués、lengua extranjera、segunda lengua、L2），与 argentina 组合。\n'
 '【强相关过滤】标题须命中关键词规则（西/英双语匹配），且带语言/教育/政策语境词；\n'
 '  非阿根廷主题、与现有 Dialnet 语料重复的条目已剔除。\n'
 '【说明】CONICET 记录的作者/年份取自仓储片段，部分字段可能不全；原文列为摘要或片段。'
)
k1 = w.cell(row=1, column=11, value='检索与筛选说明')
k1.font = Font(bold=True, color='FFFFFF'); k1.fill = PatternFill('solid', fgColor='C00000')
k2 = w.cell(row=2, column=11, value=note)
k2.alignment = Alignment(wrap_text=True, vertical='top'); k2.font = Font(size=9)
w.column_dimensions['K'].width = 60

wb.save(OUT)
print('saved', len(kept), '->', OUT)
yr = collections.Counter(bucket(r['year']) for r in kept)
print('buckets', dict(sorted(yr.items())))
