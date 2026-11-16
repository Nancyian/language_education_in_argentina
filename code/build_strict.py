# -*- coding: utf-8 -*-
"""从专家数据表_正式版.xlsx 生成严格版：剔除境外期刊 + 学科偏离条目"""
import shutil, openpyxl
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版.xlsx'
DST = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_阿根廷期刊_严格版.xlsx'
shutil.copy(SRC, DST)

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
COUNTRY = {
    'Lengua y Habla': '委内瑞拉', 'Anuario de lingüística hispánica': '西班牙',
    'Gist: Revista Colombiana de Educación Bilingüe': '哥伦比亚',
    'Estudios Interlingüísticos': '西班牙',
    'Revista Historia de la Educación Latinoamericana': '哥伦比亚',
    'Acta Poética': '墨西哥', 'Práxis Educativa': '巴西',
    'Ianua: Revista Philologica Romanica': '西班牙',
    'Journal for Educators, Teachers and Trainers': '西班牙',
    'Normas: revista de estudios lingüísticos hispánicos': '西班牙',
    'Cuadernos de Lingüística Hispánica': '哥伦比亚', 'Infancias Imágenes': '哥伦比亚',
    'HOW': '哥伦比亚', 'Revista Latinoamericana de Educación Inclusiva': '智利',
    'Ciencia e Interculturalidad': '尼加拉瓜', 'Analecta Malacitana (AnMal electrónica)': '西班牙',
    'Foro de Educación': '西班牙', 'Lingüística y Literatura': '哥伦比亚',
    'Praxis': '哥伦比亚', 'Revista Mexicana de Investigación Educativa': '墨西哥',
    'Magis: Revista Internacional de Investigación en Educación': '哥伦比亚',
    'Oltreoceano: Rivista sulle migrazioni': '意大利', 'Caracol': '巴西', 'Íkala': '哥伦比亚',
    'Investigaciones Sobre Lectura': '西班牙', 'Cuaderno de Pedagogía Universitaria': '多米尼加',
    'Revista Internacional de Estudios en Educación': '墨西哥', 'Rastros Rostros': '哥伦比亚',
    'Lingüística y Filología': '墨西哥',
    'Revista sobre Estudios e Investigaciones del Saber Académico': '巴拉圭',
}
# 学科偏离剔除
DISC_DROP = {
    33: '学科偏离：双语诗歌的文学文本分析，非语言教育/语言政策/话语研究',
    58: '学科偏离：文学与思想史批评（Contorno 的语言批评），非语言教育/语言政策研究',
}
# 保留但标注文献类型
TYPE_NOTE = {
    27: '文献类型：书评（暂保留）', 63: '文献类型：书评/Reseña（暂保留）',
    95: '文献类型：书评/RESEÑA（暂保留）', 76: '文献类型：访谈（暂保留）',
    77: '文献类型：访谈（暂保留）', 78: '文献类型：专辑导言（暂保留）',
    92: '文献类型：专辑导言（暂保留）',
    96: '期刊属行为科学（RACC），但论文主题为双语识字语码转换，内容合规，保留',
    5: '文学人物研究中的语言政策议题，内容合规，保留',
    50: '书信史料，语言史学取向，内容合规，保留',
}

wb = openpyxl.load_workbook(DST)
ws = wb['Sheet2']
hdr = [ws.cell(1, c).value for c in range(1, 10)]

records, drops = [], []
for r in range(2, ws.max_row + 1):
    old = int(ws.cell(r, 1).value)
    j = str(ws.cell(r, 5).value or '').strip()
    rec = {'row': r, 'old': old, 'journal': j, 'title': ws.cell(r, 4).value,
           'year': ws.cell(r, 7).value, 'authors': ws.cell(r, 6).value,
           'url': ws.cell(r, 2).value}
    if j not in ARG:
        rec['country'] = COUNTRY.get(j, '未知')
        rec['reason'] = '期刊非阿根廷本土（%s）' % rec['country']
        drops.append(rec)
    elif old in DISC_DROP:
        rec['country'] = '阿根廷'
        rec['reason'] = DISC_DROP[old]
        drops.append(rec)
    else:
        records.append(rec)

print('keep', len(records), 'drop', len(drops))

# 删行（降序）
for rec in sorted(drops, key=lambda x: -x['row']):
    ws.delete_rows(rec['row'], 1)

# 重编号 + 新增三列
from copy import copy
for c, h in ((10, '原序号'), (11, '期刊国别'), (12, '核查备注')):
    cell = ws.cell(1, c, h)
    cell._style = copy(ws.cell(1, 9)._style)
    ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 12 if c < 12 else 34

for i, rec in enumerate(records, start=1):
    r = i + 1
    ws.cell(r, 1, i)
    ws.cell(r, 10, rec['old'])
    ws.cell(r, 11, '阿根廷')
    note = TYPE_NOTE.get(rec['old'], '')
    if note:
        ws.cell(r, 12, note).alignment = Alignment(vertical='top', wrap_text=True)

# 数据验证区间修正
ws.data_validations.dataValidation = []
dv = DataValidation(type='list',
                    formula1='"1996-2000,2001-2005,2006-2010,2011-2015,2016-2020,2021-2025,2026-2030,时间不详"',
                    allow_blank=True, showDropDown=False)
ws.add_data_validation(dv)
dv.add('H2:H%d' % (len(records) + 1))
ws.freeze_panes = 'A2'

# 核查记录同步
ws3 = wb['核查记录']
keep_old = {rec['old'] for rec in records}
to_del = [r for r in range(2, ws3.max_row + 1) if ws3.cell(r, 1).value not in keep_old]
for r in sorted(to_del, reverse=True):
    ws3.delete_rows(r, 1)
for i in range(2, ws3.max_row + 1):
    ws3.cell(i, 1, i - 1)

# 剔除清单
ws4 = wb.create_sheet('剔除清单')
head = ['原序号', '期刊名称', '国别', '作者', '文章标题', '年份', '剔除理由', '原文链接']
for c, h in enumerate(head, start=1):
    cell = ws4.cell(1, c, h)
    cell.font = copy(ws.cell(1, 1).font)
    cell.fill = copy(ws.cell(1, 1).fill)
    cell.border = copy(ws.cell(1, 1).border)
    cell.alignment = Alignment(horizontal='center', vertical='center')
for i, rec in enumerate(sorted(drops, key=lambda x: x['old']), start=2):
    vals = [rec['old'], rec['journal'], rec['country'], rec['authors'],
            rec['title'], rec['year'], rec['reason'], rec['url']]
    for c, v in enumerate(vals, start=1):
        cell = ws4.cell(i, c, v)
        cell.alignment = Alignment(vertical='top', wrap_text=True)
for col, w in zip('ABCDEFGH', (8, 34, 12, 24, 52, 8, 42, 46)):
    ws4.column_dimensions[col].width = w
ws4.freeze_panes = 'A2'
ws4.auto_filter.ref = 'A1:H%d' % (len(drops) + 1)

wb.save(DST)
print('saved', DST)
