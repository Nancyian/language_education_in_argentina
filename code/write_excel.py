# -*- coding: utf-8 -*-
"""Write the enriched data back into a new copy of the workbook."""
import json, io, re, os, sys

SRC = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理.xlsx'
DST = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全版.xlsx'

def citstr(loc):
    if not loc: return ''
    s = loc
    for cut in [' Idioma:', ' Enlaces', ' Resumen', ' Títulos paralelos']:
        i = s.find(cut)
        if i > 0: s = s[:i]
    return re.sub(r'\s+', ' ', s).strip().rstrip(',')

def main():
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    rows = json.load(io.open('work/final.json', encoding='utf-8'))
    by_row = {int(r['row'][1:]): r for r in rows}

    wb = openpyxl.load_workbook(SRC)
    ws = wb['Sheet2']

    # header for new note column
    ws.cell(row=1, column=10, value='备注（卷期页码/ISSN/DOI状态）')
    for c in range(1, 11):
        ws.cell(row=1, column=c).font = Font(bold=True)

    filled = 0
    for r in range(2, 101):
        d = by_row.get(r)
        if not d: continue
        doi = d.get('final_doi') or ''
        if doi:
            srcval = doi
        else:
            srcval = '无DOI｜Dialnet: https://dialnet.unirioja.es/servlet/articulo?codigo=%s' % d['codigo']
        ws.cell(row=r, column=2, value=srcval)
        ws.cell(row=r, column=4, value=d['title'])
        ws.cell(row=r, column=5, value=d['journal'])
        ws.cell(row=r, column=6, value=d['authors'])
        if d.get('year'):
            ws.cell(row=r, column=7, value=int(d['year']))
        ws.cell(row=r, column=8, value=d['bucket'])
        note = citstr(d.get('loc'))
        extra = []
        if d.get('year2'): extra.append('出版年跨 %s-%s' % (d['year'], d['year2']))
        if not doi: extra.append('该刊未注册DOI（已全网检索Crossref/OpenAlex/DataCite/Dialnet）')
        if d.get('final_src'): extra.append('DOI来源: ' + d['final_src'])
        ws.cell(row=r, column=10, value=(note + ('；' + '；'.join(extra) if extra else '')))
        filled += 1

    # extend the "period" option list to cover 2026-2030 if needed
    need = any((d.get('bucket') or '') == '2026-2030' for d in rows)
    if need:
        ws3 = wb['时间选项']
        vals = [ws3.cell(row=i, column=1).value for i in range(2, 12)]
        if '2026-2030' not in vals:
            ws3.cell(row=12, column=1, value='2026-2030')
        for dv in ws.data_validations.dataValidation:
            if dv.formula1 and '时间选项' in dv.formula1:
                dv.formula1 = '时间选项!$A$2:$A$12'

    ws.column_dimensions['J'].width = 60
    wb.save(DST)
    print('saved', DST, 'rows filled:', filled)

if __name__ == '__main__':
    main()
