# -*- coding: utf-8 -*-
"""Build the cleaned corpus: drop weakly relevant items, add 相关性 + 剔除记录 sheets."""
import io, json, re, copy
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

SRC = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
DST = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_整理_清洗版.xlsx"
FIRST_NEW = 101          # 新增条目在 Sheet2 中的起始行

d = json.load(io.open('work/final_new.json', encoding='utf-8'))
meta = {}
for line in io.open('work/new_meta.jsonl', encoding='utf-8'):
    try:
        o = json.loads(line)
    except Exception:
        continue
    if 'title' in o:
        meta[o['codigo']] = o

# ---------- 人工分类（index -> (类别, 理由)；未列出的按关键词规则判定） ----------
AUTO = json.load(io.open('work/clean_tags.json', encoding='utf-8'))   # idx(str) -> tag
DROP = set(json.load(io.open('work/clean_drop_idx.json'))['drop_idx'])

# 复核后再剔除
DROP |= {89, 114, 132, 134, 241, 276, 289}   # 方言/词汇描写，与政策无关
KEEP_OVERRIDE = {
    139: ('A', '标准化与国际化：西语变体选择之争'),
    125: ('A', '语言、文化与歧视'),
    46:  ('A', '少数群体与文化接触中的语言政策'),
    237: ('A', '民族语言与文学规范的论争'),
    88:  ('A', '语言规范（正误观）'),
    254: ('A', '报刊中的语言规范'),
    272: ('A', '报刊中的规范关切'),
    223: ('A', '对西班牙/阿根廷西语变体的态度'),
    192: ('A', '1920 年代国语与 lunfardo 之争'),
    269: ('A', '殖民时期语言政策文献'),
    270: ('A', '耶稣会语言政策'),
    170: ('A', '语言立法（加利西亚-阿根廷）'),
    282: ('C', '原住民语言现状（丘布特）'),
    138: ('A', '里奥普拉滕塞规范之争'),
}
# 自动类别字母化
TAG2CAT = {
    'A·政策/规划/意识形态': 'A',
    'B·语言教育政策与实践': 'B',
    'A+B·政策与教育': 'AB',
    'C·社会语言学/多语接触': 'C',
}
CAT_LABEL = {
    'A': 'A 语言政策/规划/意识形态',
    'B': 'B 语言教育政策与教学实践',
    'AB': 'A+B 政策与教育交叉',
    'C': 'C 社会语言学/多语与接触',
    'X': 'X 已剔除',
}

def classify(i):
    if i in KEEP_OVERRIDE:
        return KEEP_OVERRIDE[i]
    return (TAG2CAT[AUTO.get(str(i), 'C·社会语言学/多语接触')], '')

# ---------- 读原表 ----------
wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']
last = FIRST_NEW - 1 + len(d)   # 原 99 行 + 新增 289 行（.max_row 受 K 列说明影响，不可用）
LAST_DATA = last
header = [ws.cell(row=1, column=c).value for c in range(1, 10)]

def row_vals(r):
    return [ws.cell(row=r, column=c).value for c in range(1, 10)]

old_rows = [row_vals(r) for r in range(2, FIRST_NEW)]     # 原 99 行
new_rows = [(i, row_vals(FIRST_NEW + i)) for i in range(len(d))]
LEFT = [row_vals(r) for r in range(LAST_DATA + 1, ws.max_row + 1)]
LEFT = [r for r in LEFT if any(v is not None for v in r)]
print('extra rows after data:', len(LEFT))

kept = [(i, r) for i, r in new_rows if i not in DROP]
dropped = [(i, r) for i, r in new_rows if i in DROP]

# ---------- 新建工作簿 ----------
out = openpyxl.Workbook()
w = out.active
w.title = 'Sheet2'
w.append(header)
hdr_fill = PatternFill('solid', fgColor='D9E2F3')
for c in range(1, 10):
    cell = w.cell(row=1, column=c)
    cell.font = Font(bold=True)
    cell.fill = hdr_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')

seq = 0
def put(seq, r):
    for c, v in enumerate([seq] + list(r[1:9]), start=1):   # 逐格写，避免 append 追加空行
        w.cell(row=seq + 1, column=c).value = v

for r in old_rows:
    seq += 1
    put(seq, r)
for i, r in kept:
    seq += 1
    put(seq, r)

widths = [6, 52, 34, 60, 34, 30, 12, 14, 60]
for i, wd in enumerate(widths, start=1):
    w.column_dimensions[get_column_letter(i)].width = wd

# 清掉 A-I 列中序号之后的空白残留行
DATA_END = seq + 1
for rr in range(w.max_row, DATA_END, -1):
    if all(w.cell(row=rr, column=c).value is None for c in range(1, 10)):
        for c in range(1, 11):
            w._cells.pop((rr, c), None)
        w.row_dimensions.pop(rr, None)

# 时间选项（隐藏）
opt = out.create_sheet('时间选项')
opt.append(['时期分布（发表年 5 年分箱）'])
buckets = ['1981-1985', '1986-1990', '1991-1995', '1996-2000', '2001-2005',
           '2006-2010', '2011-2015', '2016-2020', '2021-2025', '2026-2030',
           '1980年以前', '时间不详']
for b in buckets:
    opt.append([b])
opt.sheet_state = 'hidden'

from openpyxl.worksheet.datavalidation import DataValidation
dv = DataValidation(type='list', formula1='时间选项!$A$2:$A$13', allow_blank=True)
w.add_data_validation(dv)
dv.add('H2:H%d' % w.max_row)

# ---------- 相关性清单 ----------
rel = out.create_sheet('相关性清单')
rel.append(['序号', '标题', '年份', '类别', '判定理由', '保留/剔除'])
for c in range(1, 7):
    rel.cell(row=1, column=c).font = Font(bold=True)
    rel.cell(row=1, column=c).fill = hdr_fill
s = 0
for r in old_rows:
    s += 1
    rel.append([s, r[3], r[6], 'AB', '原表人工精选条目', '保留'])
for i, r in kept:
    s += 1
    cat, why = classify(i)
    rel.append([s, r[3], r[6], CAT_LABEL[cat], why, '保留'])
for i, r in dropped:
    s += 1
    rel.append([s, r[3], r[6], 'X 已剔除', '弱相关/口径外', '剔除'])
for i, wd in enumerate([6, 66, 10, 24, 34, 10], start=1):
    rel.column_dimensions[get_column_letter(i)].width = wd

# ---------- 剔除记录 ----------
dj = out.create_sheet('剔除记录')
dj.append(['Dialnet codigo', '标题', '期刊', '年份', '剔除理由'])
for c in range(1, 6):
    dj.cell(row=1, column=c).font = Font(bold=True)
    dj.cell(row=1, column=c).fill = PatternFill('solid', fgColor='FBE4D5')

REASON = {
    32: '纯接触语法描写，无政策维度', 73: '专辑导言（论文介绍）', 74: '文学文本时态用法', 129: '缩小词形态学',
    146: '方言区划', 162: 'voseo 形态描写', 171: '地理语言学（saber/soler）', 234: 'clíticos 变体描写',
    251: '新词构词法', 260: '(de)queísmo 句法', 290: '接触导致的音系趋同', 294: '接触引发的句法重分析',
    301: '借词词汇学', 57: '熟语中的原住民词汇成分', 181: '语言产业（非阿根廷政策）', 267: '语言规划与翻译理论（泛论）',
    40: '西语-汉语在拉美，阿根廷非核心', 49: '巴西 ELE 教学', 60: '尼加拉瓜 Bilwi 的 L2 水平',
    63: '哥伦比亚 ELE 教材', 75: '中国学生西语变体态度（非阿根廷政策）', 95: '美国高校传承语教学',
    144: '拉丁语与母语教学（泛论）', 154: '巴西 RS 边境 ELE', 164: '18 世纪泛拉美语法教学史',
    188: '马略卡耶稣会士宣教史', 189: '《圣经》与原住民语言（宗教）', 235: '艾马拉语现状（玻利维亚/秘鲁）',
    262: '西共和派流亡刊物（文学政治史）', 271: '哥伦比亚/哥斯达黎加英语政策比较',
    24: '书评', 83: '书评', 107: '书评', 112: '书评', 226: '书评', 231: '书评',
    96: '纪念日致辞', 118: '纪念日致辞', 176: '纪念性短文', 201: '教师随笔', 256: '纪念性短文',
    304: '短论（为何学西语）', 305: '短论（语言与流亡）',
    62: '文学中的多语现象', 133: '探戈歌词语言分析', 145: '阿根廷文学中的多语现象', 175: '移民文学中的语言冲突',
    193: '爱尔兰移民小说（与另一条重复）', 285: '流亡文学（Molloy/Meruane）', 277: 'Coetzee 小说翻译',
    286: '拉美裔美国文学', 310: '出版黄金时代的语言（文学史）', 173: '演讲文本', 279: '文学中的语言反思',
    205: '文学中的语言认同（Borges/Puig）', 142: 'Borges 与 Bordelois 的语言观（文学思想史）',
    105: 'Borges 与 V.F. López（语文学史）',
    6: 'ELE 会话策略（教学法）', 22: '熟语教学', 23: '学习策略', 31: '数字生态外语学习（泛论）',
    44: '后疫情英语教学（泛论）', 90: '无摘要，题名泛论', 130: '认知语言学教学序列（泛论）',
    191: '句法教学（泛论）', 218: '无摘要，泛论', 257: '搭配习得（泛论）', 263: '语法教学时机（教学法）',
    264: '教师书面反馈（教学法）', 302: '语法教学时机（教学法）', 303: 'CDA 理论（非阿根廷）',
    19: '无摘要，题名过泛', 180: '无障碍与复兴（会议发言）', 268: '无摘要，航空专门领域',
    141: '1930 年原住民语言词表', 209: '学科史', 210: '学科史', 265: '学科史',
    89: '方言特征描写', 114: '科尔多瓦通俗语描写', 132: '口语西班牙语概述', 134: '圣菲方言史',
    241: '科尔多瓦词汇汇编', 276: '圣菲语言演变特征', 289: '罗萨里奥社会语言学个案（音变）',
}
for i, r in dropped:
    o = meta.get(d[i]['codigo'], {})
    dj.append([d[i]['codigo'], r[3], r[4], r[6], REASON.get(i, '弱相关')])
for i, wd in enumerate([16, 70, 34, 10, 40], start=1):
    dj.column_dimensions[get_column_letter(i)].width = wd

# ---------- 口径说明（右侧） ----------
w.cell(row=1, column=11, value='语料库口径与清洗说明')
w.cell(row=1, column=11).font = Font(bold=True, color='FFFFFF')
w.cell(row=1, column=11).fill = PatternFill('solid', fgColor='C00000')
note = (
 '【研究对象】阿根廷的语言政策 / 语言教育政策 / 语言意识形态与规划（含历史）\n'
 '【检索口径】Dialnet 全字段 = 关键词 + argentina（阿根廷“主题”口径，不限作者国籍）\n'
 '【清洗结果】原表 99 条（人工精选，全部保留）+ 新增 226 条；剔除 85 条，明细见「剔除记录」表\n'
 '【剔除标准】① 纯语言/方言描写（音系、句法、词汇、构词）② 非阿根廷核心（他国/泛拉美）\n'
 '            ③ 书评、致辞、纪念短文、会议发言 ④ 纯文学分析 ⑤ 与语言政策无关的通用教学法\n'
 '【分类说明】「相关性清单」按 A/B/AB/C 标注：\n'
 '   A = 语言政策、规划、立法、权利、语言意识形态\n'
 '   B = 语言教育政策与教学实践（EIB、课程、教材、教师培养、外语教育）\n'
 '   AB = 同时涉及政策与教育（可直接作为核心语料）\n'
 '   C = 社会语言学/多语与接触（原住民语言、移民语言、语言态度——政策背景材料）\n'
 '【使用建议】做政策话语分析可只取 A+AB（56 条新增）；做全貌研究可保留全部 325 条。'
)
c = w.cell(row=2, column=11, value=note)
c.alignment = Alignment(wrap_text=True, vertical='top')
c.font = Font(size=9)
w.column_dimensions['K'].width = 46
w.freeze_panes = 'A2'
w.auto_filter.ref = 'A1:I%d' % w.max_row

print('max_row after trim', w.max_row, 'max_col', w.max_column)

out.save(DST)
print('rows', w.max_row - 1, '| kept new', len(kept), '| dropped', len(dropped))
print('cats', {k: sum(1 for i, r in kept if classify(i)[0] == k) for k in ['A', 'B', 'AB', 'C']})
