# -*- coding: utf-8 -*-
import openpyxl, collections
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

P = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
wb = openpyxl.load_workbook(P)
ws = wb['Sheet2']
n_before, n_after = 99, ws.max_row - 1

def is_ar(src):
    s = (src or '').lower()
    return ('dialnet' not in s) and ('rahl.ar' in s or '.edu.ar' in s or '.gob.ar' in s)

old_ar = sum(1 for r in ws.iter_rows(min_row=2, max_row=n_before + 1, min_col=2, max_col=2, values_only=True) if is_ar(r[0]))
new_ar = sum(1 for r in ws.iter_rows(min_row=n_before + 2, max_row=n_after + 1, min_col=2, max_col=2, values_only=True) if is_ar(r[0]))
print('old AR-source', old_ar, 'new AR-source', new_ar)

# 图例文字
legend = (
    "【筛选口径说明 / 请勿直接引用为“阿根廷学者研究”】\n"
    "本表不是按作者国别检索的。Dialnet 检索式为“关键词 + argentina”全文匹配，"
    "即主题/文本层面涉及阿根廷，作者国别不限（阿根廷、智利、西班牙、巴西、德国等均有）。\n"
    "原因：Dialnet 高级检索有“作者机构/国别”字段，但仅对部分收录期刊填该作者单位，"
    "覆盖率低，按机构过滤会漏掉大量阿根廷学者的文章（本表 311 条中 191 条无机构信息）。\n"
    "若确需“阿根廷学者”口径，需逐条核作者单位（CONICET / UBA / UNLP / UNC 等）或用 Scopus/OpenAlex 作者机构字段重检。\n"
    "注：来源列标注 dialnet.unirioja.es 的条目均为 Dialnet 索引记录；原表中直接给出本土期刊网址（*.edu.ar / rahl.ar）的条目为阿根廷本土来源。"
)
ws.cell(row=1, column=11).value = "筛选口径说明"
ws.cell(row=1, column=11).font = Font(bold=True, color='FFFFFF')
ws.cell(row=1, column=11).fill = PatternFill('solid', fgColor='C00000')
ws.cell(row=1, column=11).alignment = Alignment(horizontal='center', vertical='center')
c = ws.cell(row=2, column=11)
c.value = legend
c.alignment = Alignment(wrap_text=True, vertical='top')
c.font = Font(size=9)

# 统计表
s0 = 1
ws.cell(row=s0, column=13).value = "批次"
ws.cell(row=s0, column=14).value = "条数"
ws.cell(row=s0 + 1, column=13).value = "原表(99条)"
ws.cell(row=s0 + 1, column=14).value = n_before
ws.cell(row=s0 + 2, column=13).value = "本次新增"
ws.cell(row=s0 + 2, column=14).value = n_after - n_before
for rr in range(s0, s0 + 3):
    ws.cell(row=rr, column=13).font = Font(bold=(rr == s0))
    ws.cell(row=rr, column=14).font = Font(bold=(rr == s0))

ch = BarChart()
ch.type = "col"
ch.title = "条目数"
ch.height, ch.width = 5, 8
data = Reference(ws, min_col=14, min_row=s0, max_row=s0 + 2)
cats = Reference(ws, min_col=13, min_row=s0 + 1, max_row=s0 + 2)
ch.add_data(data, titles_from_data=True)
ch.set_categories(cats)
ch.legend = None
ws.add_chart(ch, "M6")

wb.save(P)
print('saved')
