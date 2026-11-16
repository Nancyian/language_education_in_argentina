# -*- coding: utf-8 -*-
"""在 Sheet2 内原地删改：删除 71 条弱相关行，重排序号，J 列加相关性类别。"""
import io, json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from cats_manual import CATS as SEQ_CATS
from cats_orig import ORIG as ORIG_CATS

PATH = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
idx2row = {int(k): v for k, v in json.load(io.open('work/idx2row.json', encoding='utf-8')).items()}

# 剔除集合（源表行号）
DROP_IDX = set(json.load(io.open('work/clean_drop_idx.json'))['drop_idx']) | {89, 114, 132, 134, 241, 276, 289}
from clean_fix import RESCUE, EXTRA_DROP
drop_rows = {idx2row[i] for i in DROP_IDX if i in idx2row} - set(RESCUE) | set(EXTRA_DROP)

wb = openpyxl.load_workbook(PATH)
ws = wb['Sheet2']
print('before: max_row', ws.max_row, 'dims', ws.dimensions)

# 1) 从后往前删行（delete_rows 会移动下方内容，倒序最安全）
targets = sorted(drop_rows, reverse=True)
print('rows to delete', len(targets))
for r in targets:
    ws.delete_rows(r, 1)

print('after delete: max_row', ws.max_row)

# 2) 重排序号 + 写 J 列类别
# 映射：删除后新序号 = 原序号 - 前面被删数量
deleted = sorted(drop_rows)
def new_seq(old_row):
    # old_row 为源表行号（数据从第 2 行起）
    return old_row - 1 - sum(1 for d in deleted if d < old_row)

HDR = '相关性类别'
src_hdr = ws.cell(row=1, column=1)
hdr_cell = ws.cell(row=1, column=10, value=HDR)
hdr_cell.font = Font(bold=True)
hdr_cell.fill = PatternFill('solid', fgColor='D9E2F3')
hdr_cell.alignment = Alignment(horizontal='center', vertical='center')

LABEL = {'A': 'A 政策/规划/意识形态', 'B': 'B 教育政策与实践',
         'AB': 'A+B 政策与教育', 'C': 'C 社会语言学/多语接触'}

stats = {}
for r in range(2, ws.max_row + 1):
    seq = ws.cell(row=r, column=1).value
    if seq is None:
        continue
    s = int(seq)                    # 原序号 = 源表行号 - 1
    old_row = s + 1
    ns = new_seq(old_row)
    if old_row < 101:               # 原表段（全部保留）
        cat = ORIG_CATS.get(s, 'C')
    else:                           # 新增段：类别表按清洗后序号 100..317 编排
        cat = SEQ_CATS.get(ns, 'C')
    ws.cell(row=r, column=1).value = ns
    c = ws.cell(row=r, column=10, value=LABEL[cat])
    c.alignment = Alignment(horizontal='center', vertical='center')
    stats[cat] = stats.get(cat, 0) + 1

print('after reseq: max_row', ws.max_row, 'rows', ws.max_row - 1)
print('cats', stats)

# 3) 修正范围引用
LAST = ws.max_row
ws.auto_filter.ref = 'A1:J%d' % LAST
for dv in ws.data_validations.dataValidation:
    dv.sqref = 'H2:H%d' % LAST
last_row_data = LAST

# 4) 更新 M/N 统计小表
ws.cell(row=1, column=13, value='批次')
ws.cell(row=1, column=14, value='条数')
ws.cell(row=2, column=13, value='原表')
ws.cell(row=2, column=14, value=99)
ws.cell(row=3, column=13, value='新增（保留）')
ws.cell(row=3, column=14, value=len(SEQ_CATS))
ws.cell(row=4, column=13, value='合计')
ws.cell(row=4, column=14, value=LAST - 1)

# 5) 追加清洗说明
note = ('【清洗说明】已删除 71 条弱相关条目（纯语言/方言描写、非阿根廷核心、书评致辞纪念短文、'
        '纯文学分析、与语言政策无关的通用教学法），剩余 %d 条。\n'
        '【相关性类别】新增 J 列：A=政策/规划/意识形态；B=教育政策与实践；A+B=政策与教育交叉（核心语料）；'
        'C=社会语言学/多语接触（背景材料）。可据此筛选后再做编码。' % (LAST - 1))
ws.cell(row=5, column=11, value=note).alignment = Alignment(wrap_text=True, vertical='top')

wb.save(PATH)
print('saved | rows', LAST - 1)
