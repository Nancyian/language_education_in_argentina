# -*- coding: utf-8 -*-
"""在正式版上直接删除非阿根廷期刊记录（先备份）"""
import shutil, openpyxl, datetime, os
from openpyxl.worksheet.datavalidation import DataValidation

DIR = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语'
SRC = os.path.join(DIR, '专家数据表_正式版.xlsx')
BAK = os.path.join(DIR, '专家数据表_正式版_备份_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M'))
shutil.copy(SRC, BAK)
print('backup ->', BAK)

ARG = {
    'RAHL: Revista argentina de historiografía lingüística',
    'Traslaciones: Revista Latinoamericana de Lectura y Escritura',
    'Signo y Seña', 'Quintú Quimün: revista de lingüística', 'Anclajes',
    'Integración y Conocimiento', 'Signos ELE: Revista de Español como Lengua Extranjera',
    'Argonautas', 'Revista Argentina de Educación Superior (RAES)',
    'Educación, Lenguaje y Sociedad', 'Entramados: educación y sociedad', 'Gramma',
    'Pilquen - Sección Psicopedagogía', 'Revista Latinoamericana de Educación Comparada (RELEC)',
    'Cuadernos del CILHA', 'Masquedós: Revista de Extensión Universitaria',
    'Revista Argentina de Ciencias del Comportamiento (RACC)',
}

wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']
del_rows, survivors = [], []
for r in range(2, ws.max_row + 1):
    j = str(ws.cell(r, 5).value or '').strip()
    if j not in ARG:
        del_rows.append(r)
    else:
        survivors.append(ws.cell(r, 1).value)
print('delete rows', len(del_rows), '| survivors', len(survivors))
for r in sorted(del_rows, reverse=True):
    ws.delete_rows(r, 1)

for i in range(2, ws.max_row + 1):
    ws.cell(i, 1, i - 1)
ws.data_validations.dataValidation = []
dv = DataValidation(type='list',
                    formula1='"1996-2000,2001-2005,2006-2010,2011-2015,2016-2020,2021-2025,2026-2030,时间不详"',
                    allow_blank=True, showDropDown=False)
ws.add_data_validation(dv)
dv.add('H2:H%d' % ws.max_row)

# 核查记录：按「删除前的原始序号」对齐后删除，再统一重编号
ws3 = wb['核查记录']
keep = set(survivors)
for r in range(ws3.max_row, 1, -1):
    if ws3.cell(r, 1).value not in keep:
        ws3.delete_rows(r, 1)
for i in range(2, ws3.max_row + 1):
    ws3.cell(i, 1, i - 1)

wb.save(SRC)
print('saved in place:', SRC, '| Sheet2 rows', ws.max_row - 1, '| 核查记录', ws3.max_row - 1)
