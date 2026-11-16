# -*- coding: utf-8 -*-
"""重建清洗版（干净版）：以「行号」为主键；数据区、清单、剔除记录三表严格同源。"""
import io, json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from clean_fix import RESCUE, KEEP_OVERRIDE, EXTRA_DROP, REASON
from cats_manual import CATS as SEQ_CATS     # 序号 100..317 -> 人工类别
from cats_orig import ORIG as ORIG_CATS      # 原表序号 1..99 -> 人工类别

SRC = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
DST = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_整理_清洗版.xlsx"
FIRST_NEW = 101                              # 源表新增段起始行

idx2row = {int(k): v for k, v in json.load(io.open('work/idx2row.json', encoding='utf-8')).items()}
dnew = json.load(io.open('work/final_new.json', encoding='utf-8'))
codigo_of_row = {r: dnew[i]['codigo'] for i, r in idx2row.items()}

# ---------- 剔除集合（行号） ----------
DROP_IDX = set(json.load(io.open('work/clean_drop_idx.json'))['drop_idx']) | {89, 114, 132, 134, 241, 276, 289}
drop_rows = {idx2row[i] for i in DROP_IDX if i in idx2row} - set(RESCUE) | set(EXTRA_DROP)

# ---------- 读源表 ----------
sw = openpyxl.load_workbook(SRC)['Sheet2']
header = [sw.cell(row=1, column=c).value for c in range(1, 10)]

def rv(r):
    return [sw.cell(row=r, column=c).value for c in range(1, 10)]

old_rows = [rv(r) for r in range(2, FIRST_NEW)]                                  # 99
new_rlist = [r for r in range(FIRST_NEW, sw.max_row + 1) if sw.cell(row=r, column=4).value]
new_rows = [(r, rv(r)) for r in new_rlist]                                       # 289
assert len(old_rows) == 99 and len(new_rows) == 289, (len(old_rows), len(new_rows))

kept = [(r, v) for r, v in new_rows if r not in drop_rows]
drp = [(r, v) for r, v in new_rows if r in drop_rows]
print('old 99 | new %d | kept %d | drop %d | total %d' % (len(new_rows), len(kept), len(drp), 99 + len(kept)))

# 记录：序号 -> (类别, 说明, 状态)
records = []      # (title, year, journal, cat, why, status, codigo)
SUSPECT = {49: '⚠ 原表条目，题名为智利戏剧史，主题疑似离题（未剔除，请人工确认）'}
for i, r in enumerate(old_rows, start=1):
    why = SUSPECT.get(i, '原表人工精选条目')
    records.append((r[3], r[6], r[4], ORIG_CATS.get(i, 'C'), why, '保留', ''))
offset = len(old_rows)
for k, (r, v) in enumerate(kept):
    seqno = offset + k + 1
    cat = SEQ_CATS.get(seqno) or 'C'
    why = KEEP_OVERRIDE.get(r, (None, ''))[1] or RESCUE.get(r, (None, ''))[1] or ''
    records.append((v[3], v[6], v[4], cat, why, '保留', codigo_of_row.get(r, '')))
for r, v in drp:
    why = EXTRA_DROP.get(r, (None, REASON.get(r, '')))[1]
    assert why, ('no reason', r, v[3])
    records.append((v[3], v[6], v[4], 'X', why, '剔除', codigo_of_row.get(r, '')))

# ---------- 工作簿 ----------
out = openpyxl.Workbook()
w = out.active
w.title = 'Sheet2'
HFILL = PatternFill('solid', fgColor='D9E2F3')
for c, v in enumerate(header, start=1):
    cell = w.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True); cell.fill = HFILL
    cell.alignment = Alignment(horizontal='center', vertical='center')

data_src = old_rows + [v for r, v in kept]
EXPECT = [x[3] for x in data_src]
for i, vals in enumerate(data_src, start=1):
    for c, v in enumerate([i] + list(vals[1:9]), start=1):
        w.cell(row=i + 1, column=c).value = v
DATA_LAST = len(data_src) + 1
have = [w.cell(row=r, column=4).value for r in range(2, DATA_LAST + 1)]
assert have == EXPECT, 'data region mismatch'

for i, wd in enumerate([6, 52, 34, 60, 34, 30, 12, 14, 60], start=1):
    w.column_dimensions[get_column_letter(i)].width = wd

opt = out.create_sheet('时间选项')
opt.append(['时期分布（发表年 5 年分箱）'])
for b in ['1981-1985', '1986-1990', '1991-1995', '1996-2000', '2001-2005', '2006-2010',
          '2011-2015', '2016-2020', '2021-2025', '2026-2030', '1980年以前', '时间不详']:
    opt.append([b])
opt.sheet_state = 'hidden'

dv = DataValidation(type='list', formula1='时间选项!$A$2:$A$13', allow_blank=True)
w.add_data_validation(dv)
dv.add('H2:H%d' % DATA_LAST)
w.auto_filter.ref = 'A1:I%d' % DATA_LAST
w.freeze_panes = 'A2'

# ---------- 相关性清单 ----------
rel = out.create_sheet('相关性清单')
for c, v in enumerate(['序号', '标题', '年份', '期刊', '相关性类别', '判定说明', '状态'], start=1):
    cell = rel.cell(row=1, column=c, value=v); cell.font = Font(bold=True); cell.fill = HFILL
LABEL = {'A': 'A', 'B': 'B', 'AB': 'A+B', 'C': 'C', 'X': 'X 已剔除'}
for i, (t, y, j, cat, why, st, cg) in enumerate(records, start=2):
    rel.cell(row=i, column=1, value=i - 1)
    rel.cell(row=i, column=2, value=t)
    rel.cell(row=i, column=3, value=y)
    rel.cell(row=i, column=4, value=j)
    rel.cell(row=i, column=5, value=LABEL[cat])
    rel.cell(row=i, column=6, value=why)
    rel.cell(row=i, column=7, value=st)
for i, wd in enumerate([6, 64, 10, 30, 14, 44, 8], start=1):
    rel.column_dimensions[get_column_letter(i)].width = wd
rel.freeze_panes = 'A2'
rel.auto_filter.ref = 'A1:G%d' % len(records) + ''

# ---------- 剔除记录 ----------
dj = out.create_sheet('剔除记录')
for c, v in enumerate(['Codigo', '标题', '期刊', '年份', '剔除理由'], start=1):
    cell = dj.cell(row=1, column=c, value=v)
    cell.font = Font(bold=True); cell.fill = PatternFill('solid', fgColor='FBE4D5')
drops = [x for x in records if x[5] == '剔除']
drops.sort(key=lambda x: (x[2] or '', str(x[1] or '')))
for i, (t, y, j, cat, why, st, cg) in enumerate(drops, start=2):
    dj.cell(row=i, column=1, value=cg)
    dj.cell(row=i, column=2, value=t)
    dj.cell(row=i, column=3, value=j)
    dj.cell(row=i, column=4, value=y)
    dj.cell(row=i, column=5, value=why)
for i, wd in enumerate([16, 66, 34, 10, 46], start=1):
    dj.column_dimensions[get_column_letter(i)].width = wd
dj.freeze_panes = 'A2'
dj.auto_filter.ref = 'A1:E%d' % (len(drops) + 1)

# ---------- 右侧说明（只写 K1/K2，写完立即清掉越界 cell） ----------
catn = {k: sum(1 for x in records[99:] if x[3] == k and x[5] == '保留') for k in ('A', 'B', 'AB', 'C')}
note = (
 '【研究对象】阿根廷的语言政策 / 语言教育政策 / 语言意识形态与规划（含历史）\n'
 '【检索口径】Dialnet 全字段 = 关键词 + argentina（阿根廷“主题”口径，不限作者国籍）\n'
 '【清洗结果】原表 99 条（人工精选，全部保留）+ 新增保留 %d 条 = 共 %d 条；剔除 %d 条（见「剔除记录」）\n'
 '【剔除标准】① 纯语言/方言描写（音系、句法、词汇、构词）② 非阿根廷核心（他国/泛拉美）\n'
 '            ③ 书评、致辞、纪念短文、会议发言 ④ 纯文学分析 ⑤ 与语言政策无关的通用教学法\n'
 '【分类口径】「相关性清单」E 列按 A / B / A+B / C 标注（新增段：A=%d, B=%d, A+B=%d, C=%d）：\n'
 '   A   = 语言政策、规划、立法、语言权利、语言意识形态（含语言史中的规范之争）\n'
 '   B   = 语言教育政策与教学实践（EIB、课程、教材、教师培养、外语教育）\n'
 '   A+B = 同时涉及政策与教育，可直接作为核心语料\n'
 '   C   = 社会语言学 / 多语与接触（原住民语言、移民语言、语言态度——政策背景材料）\n'
 '【使用建议】聚焦政策话语分析：筛 E 列 = A 或 A+B；做全貌研究：保留全部 %d 条。'
) % (len(kept), len(data_src), len(drops), catn['A'], catn['B'], catn['AB'], catn['C'], len(data_src))
k1 = w.cell(row=1, column=11, value='语料库口径与清洗说明')
k1.font = Font(bold=True, color='FFFFFF'); k1.fill = PatternFill('solid', fgColor='C00000')
k2 = w.cell(row=2, column=11, value=note)
k2.alignment = Alignment(wrap_text=True, vertical='top'); k2.font = Font(size=9)
w.column_dimensions['K'].width = 50
# 清掉数据区之外的多余 cell（K 列说明仅占第 1、2 行）
for (rr, cc) in [k for k in list(w._cells) if k[0] > DATA_LAST]:
    w._cells.pop((rr, cc), None)
for rr in [k for k in list(w.row_dimensions) if k > DATA_LAST]:
    w.row_dimensions.pop(rr, None)

assert w.max_row == DATA_LAST, (w.max_row, DATA_LAST)
out.save(DST)
print('max_row', w.max_row, '| sheets', out.sheetnames)
print('cats(新增保留)', catn)
print('saved ->', DST)
