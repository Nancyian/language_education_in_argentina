# -*- coding: utf-8 -*-
"""重建清洗版：以「行号」为主键，避免索引错位；彻底清空尾部 _cells。"""
import io, json, sys, unicodedata, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from clean_fix import RESCUE, KEEP_OVERRIDE, EXTRA_DROP, REASON
from cats_manual import CATS as SEQ_CATS   # 序号(100..317) -> 人工类别
from cats_orig import ORIG as ORIG_CATS    # 原表序号(1..99) -> 人工类别

SRC = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
DST = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_整理_清洗版.xlsx"
FIRST_NEW = 101

# ---------- 索引 -> 行号（按规范化标题唯一匹配） ----------
idx2row = {int(k): v for k, v in json.load(io.open('work/idx2row.json', encoding='utf-8')).items()}
row2idx = {v: k for k, v in idx2row.items()}

d = json.load(io.open('work/final_new.json', encoding='utf-8'))
codigo_of_row = {}
for i, r in idx2row.items():
    codigo_of_row[r] = d[i]['codigo']

# ---------- 标签（索引 -> 类别） ----------
TAG2CAT = {'A·政策/规划/意识形态': 'A', 'B·语言教育政策与实践': 'B',
           'A+B·政策与教育': 'AB', 'C·社会语言学/多语接触': 'C'}
AUTO = {int(k): TAG2CAT[v] for k, v in json.load(io.open('work/clean_tags.json', encoding='utf-8')).items()}
cat_of_row = {idx2row[i]: c for i, c in AUTO.items() if i in idx2row}

# ---------- 剔除集合（行号） ----------
DROP_IDX = set(json.load(io.open('work/clean_drop_idx.json'))['drop_idx']) | {89, 114, 132, 134, 241, 276, 289}
drop_rows = {idx2row[i] for i in DROP_IDX if i in idx2row}
drop_rows -= set(RESCUE)                      # 复核恢复
drop_rows |= set(EXTRA_DROP)                  # 复核新增剔除

# ---------- 读原表 ----------
wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']
header = [ws.cell(row=1, column=c).value for c in range(1, 10)]
def row_vals(r):
    return [ws.cell(row=r, column=c).value for c in range(1, 10)]

NEW_ROW_LIST = [r for r in range(FIRST_NEW, ws.max_row + 1) if ws.cell(row=r, column=4).value]
LAST_NEW_ROW = NEW_ROW_LIST[-1]
old_rows = [row_vals(r) for r in range(2, FIRST_NEW)]                     # 原 99 条
new_rows = [(r, row_vals(r)) for r in NEW_ROW_LIST]                       # 289 条
print('old', len(old_rows), 'new', len(new_rows), 'range', NEW_ROW_LIST[0], '-', LAST_NEW_ROW,
      'drop', len(drop_rows))
assert len(new_rows) == 289 and LAST_NEW_ROW == 389

kept_new = [(r, v) for r, v in new_rows if r not in drop_rows]
drop_new = [(r, v) for r, v in new_rows if r in drop_rows]
TOTAL = len(old_rows) + len(kept_new)
print('kept new', len(kept_new), 'total', TOTAL)

# ---------- 新建工作簿 ----------
out = openpyxl.Workbook()
w = out.active
w.title = 'Sheet2'
hdr_fill = PatternFill('solid', fgColor='D9E2F3')
for c, v in enumerate(header, start=1):
    cell = w.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True); cell.fill = hdr_fill
    cell.alignment = Alignment(horizontal='center', vertical='center')

seq = 0
EXPECT_TITLES = []
def put(s, r):
    vals = [s] + list(r[1:9])
    assert len(vals) == 9, len(vals)
    EXPECT_TITLES.append(vals[3])
    for c, v in enumerate(vals, start=1):
        w.cell(row=s + 1, column=c).value = v
for r in old_rows:
    seq += 1; put(seq, r)
DATA_END = seq + 1                     # 最后数据行 + 1
print('DATA_END', DATA_END)
# 写出前自检：数据区应恰好是 EXPECT_TITLES
have = [w.cell(row=rr, column=4).value for rr in range(2, DATA_END)]
print('pre-save rows', len(have), 'expect', len(EXPECT_TITLES))
assert have == EXPECT_TITLES, 'data region mismatch before save'

widths = [6, 52, 34, 60, 34, 30, 12, 14, 60]
for i, wd in enumerate(widths, start=1):
    w.column_dimensions[get_column_letter(i)].width = wd

# 时间选项（隐藏）
opt = out.create_sheet('时间选项')
opt.append(['时期分布（发表年 5 年分箱）'])
for b in ['1981-1985', '1986-1990', '1991-1995', '1996-2000', '2001-2005',
          '2006-2010', '2011-2015', '2016-2020', '2021-2025', '2026-2030',
          '1980年以前', '时间不详']:
    opt.append([b])
opt.sheet_state = 'hidden'

dv = DataValidation(type='list', formula1='时间选项!$A$2:$A$13', allow_blank=True)
w.add_data_validation(dv)
dv.add('H2:H%d' % (DATA_END - 1))
w.auto_filter.ref = 'A1:I%d' % (DATA_END - 1)
w.freeze_panes = 'A2'

# ---------- 相关性清单 ----------
CAT_LABEL = {'A': 'A 语言政策/规划/意识形态', 'B': 'B 语言教育政策与教学实践',
             'AB': 'A+B 政策与教育交叉', 'C': 'C 社会语言学/多语与接触', 'X': 'X 已剔除'}
rel = out.create_sheet('相关性清单')
for c, v in enumerate(['序号', '标题', '年份', '期刊', '相关性类别', '判定说明', '状态'], start=1):
    cell = rel.cell(row=1, column=c, value=v); cell.font = Font(bold=True); cell.fill = hdr_fill
s = 0
for r in old_rows:
    s += 1
    rel.cell(row=s + 1, column=1).value = s
    rel.cell(row=s + 1, column=2).value = r[3]
    rel.cell(row=s + 1, column=3).value = r[6]
    rel.cell(row=s + 1, column=4).value = r[4]
    rel.cell(row=s + 1, column=5).value = 'A+B' if ORIG_CATS.get(s) == 'AB' else ORIG_CATS.get(s, 'C')
    rel.cell(row=s + 1, column=6).value = '原表人工精选条目'
    rel.cell(row=s + 1, column=7).value = '保留'
for r, v in kept_new:
    s += 1
    cat = SEQ_CATS.get(s - len(old_rows)) or KEEP_OVERRIDE.get(r, (None,))[0] or cat_of_row.get(r, 'C')
    why = KEEP_OVERRIDE.get(r, (None, ''))[1] or RESCUE.get(r, (None, ''))[1] or ''
    rel.cell(row=s + 1, column=1).value = s
    rel.cell(row=s + 1, column=2).value = v[3]
    rel.cell(row=s + 1, column=3).value = v[6]
    rel.cell(row=s + 1, column=4).value = v[4]
    rel.cell(row=s + 1, column=5).value = 'A+B' if cat == 'AB' else cat
    rel.cell(row=s + 1, column=6).value = why
    rel.cell(row=s + 1, column=7).value = '保留'
for r, v in drop_new:
    s += 1
    why = EXTRA_DROP.get(r, (None, REASON.get(r, '')))[1]
    rel.cell(row=s + 1, column=1).value = s
    rel.cell(row=s + 1, column=2).value = v[3]
    rel.cell(row=s + 1, column=3).value = v[6]
    rel.cell(row=s + 1, column=4).value = v[4]
    rel.cell(row=s + 1, column=5).value = 'X 已剔除'
    rel.cell(row=s + 1, column=6).value = why
    rel.cell(row=s + 1, column=7).value = '剔除'
for i, wd in enumerate([6, 64, 10, 30, 22, 44, 8], start=1):
    rel.column_dimensions[get_column_letter(i)].width = wd
rel.freeze_panes = 'A2'
rel.auto_filter.ref = 'A1:G%d' % (s + 1)

# ---------- 剔除记录 ----------
dj = out.create_sheet('剔除记录')
for c, v in enumerate(['Codigo', '标题', '期刊', '年份', '剔除理由'], start=1):
    cell = dj.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True); cell.fill = PatternFill('solid', fgColor='FBE4D5')
for n, (r, v) in enumerate(sorted(drop_new, key=lambda x: -(x[1][6] if isinstance(x[1][6], int) else 0)), start=2):
    why = EXTRA_DROP.get(r, (None, REASON.get(r, '')))[1]
    dj.cell(row=n, column=1).value = codigo_of_row.get(r, '')
    dj.cell(row=n, column=2).value = v[3]
    dj.cell(row=n, column=3).value = v[4]
    dj.cell(row=n, column=4).value = v[6]
    dj.cell(row=n, column=5).value = why
for i, wd in enumerate([16, 66, 34, 10, 46], start=1):
    dj.column_dimensions[get_column_letter(i)].width = wd
dj.freeze_panes = 'A2'
dj.auto_filter.ref = 'A1:E%d' % (len(drop_new) + 1)

# ---------- 右侧口径说明（写在数据区之外，最后再清尾部） ----------
note = (
 '【研究对象】阿根廷的语言政策 / 语言教育政策 / 语言意识形态与规划（含历史）\n'
 '【检索口径】Dialnet 全字段 = 关键词 + argentina（阿根廷“主题”口径，不限作者国籍）\n'
 '【清洗结果】原表 99 条（人工精选，全部保留）+ 新增保留 %d 条 = 共 %d 条；剔除 %d 条（见「剔除记录」）\n'
 '【剔除标准】① 纯语言/方言描写（音系、句法、词汇、构词）② 非阿根廷核心（他国/泛拉美）\n'
 '             ③ 书评、致辞、纪念短文、会议发言 ④ 纯文学分析 ⑤ 与语言政策无关的通用教学法\n'
 '【分类说明】「相关性清单」按 A / B / A+B / C 标注：\n'
 '   A   = 语言政策、规划、立法、语言权利、语言意识形态\n'
 '   B   = 语言教育政策与教学实践（EIB、课程、教材、教师培养、外语教育）\n'
 '   A+B = 同时涉及政策与教育（可直接作为核心语料）\n'
 '   C   = 社会语言学 / 多语与接触（原住民语言、移民语言、语言态度——政策背景材料）\n'
 '【使用建议】聚焦政策话语分析：只取 A + A+B；做全貌研究：保留全部 %d 条。'
) % (len(kept_new), TOTAL, len(drop_new), TOTAL)
c = w.cell(row=2, column=11, value=note)
c.alignment = Alignment(wrap_text=True, vertical='top'); c.font = Font(size=9)
w.cell(row=1, column=11, value='语料库口径与清洗说明').font = Font(bold=True, color='FFFFFF')
w.cell(row=1, column=11).fill = PatternFill('solid', fgColor='C00000')
w.column_dimensions['K'].width = 48

# ---------- 关键：清掉超出数据区的所有 cell 记录 ----------
for (r, cc) in [k for k in list(w._cells) if k[0] > DATA_END - 1]:
    w._cells.pop((r, cc), None)
for r in [k for k in w.row_dimensions if k > DATA_END - 1]:
    w.row_dimensions.pop(r, None)
# K 列说明需要保留在第 1、2 行，重新写入
w.cell(row=1, column=11, value='语料库口径与清洗说明').font = Font(bold=True, color='FFFFFF')
w.cell(row=1, column=11).fill = PatternFill('solid', fgColor='C00000')
c2 = w.cell(row=2, column=11, value=note)
c2.alignment = Alignment(wrap_text=True, vertical='top'); c2.font = Font(size=9)

print('max_row', w.max_row, 'expect', DATA_END - 1, 'max_col', w.max_column)
assert w.max_row == DATA_END - 1, 'max_row mismatch'

out.save(DST)
cats = {}
for k, (r, v) in enumerate(kept_new):
    cat = SEQ_CATS.get(100 + k, '?')
    cats[cat] = cats.get(cat, 0) + 1
print('cats(new)', cats)
print('sheets', out.sheetnames)
print('OK ->', DST)

# ---------- 写盘后自检 ----------
chk = openpyxl.load_workbook(DST)
cw = chk['Sheet2']
missing = []
for idx, (s_, v) in enumerate([(i, r) for i, r in enumerate(old_rows)] + [(None, v) for r, v in kept_new]):
    pass
written = [cw.cell(row=r, column=4).value for r in range(2, cw.max_row + 1)]
expect = [r[3] for r in old_rows] + [v[3] for r, v in kept_new]
print('written', len(written), 'expect', len(expect))
if written != expect:
    for i, (a, b) in enumerate(zip(written, expect)):
        if a != b:
            print('  first mismatch at index', i, '\n   written:', str(a)[:60], '\n   expect :', str(b)[:60])
            break
    sw, se = set(written), set(expect)
    print('  missing:', [str(t)[:50] for t in expect if t not in sw])
