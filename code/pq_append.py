# -*- coding: utf-8 -*-
"""把 ProQuest 251 条追加进 multi_db_language_corpus_检索.xlsx 的 Sheet2，
保持 A-J 十列同格式，重排序号，更新筛选/数据验证/统计/说明。"""
import io, json, os, sys
from collections import Counter
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import BarChart, Reference

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索.xlsx'
OUT = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索_含ProQuest.xlsx'
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/work'

LABEL = {'A': 'A 政策/规划/意识形态', 'B': 'B 教育政策与实践',
         'AB': 'A+B 政策与教育', 'C': 'C 社会语言学/多语接触'}
BINS = ['1980年以前', '1980-1984', '1985-1989', '1990-1994', '1995-1999',
        '2000-2004', '2005-2009', '2010-2014', '2015-2019', '2020-2024', '2025-2029']


def bin5(y):
    if not y:
        return ''
    if y < 1980:
        return '1980年以前'
    b = (y - 1980) // 5 * 5 + 1980
    return '%d-%d' % (b, b + 4)


def norm(s):
    import re
    s = (s or '').lower()
    for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'),
                 ('à', 'a'), ('è', 'e'), ('ì', 'i'), ('ò', 'o'), ('ù', 'u')]:
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '', s)


def main():
    wb = openpyxl.load_workbook(SRC)
    ws = wb['Sheet2']

    # 读现有 1..152 行（A-J）
    rows = []
    for r in range(2, ws.max_row + 1):
        v = [ws.cell(row=r, column=c).value for c in range(1, 11)]
        if v[3]:  # 有标题
            rows.append(v)
    old_n = len(rows)
    print('existing rows:', old_n)

    pq = json.load(io.open(os.path.join(WORK, 'final_pq.json'), encoding='utf-8'))
    print('pq to add:', len(pq))

    seen = set(norm(x[3])[:70] for x in rows)
    added = 0
    for c in pq:
        k = norm(c['title'])[:70]
        if k in seen:
            continue
        seen.add(k)
        kw = 'language policy; language planning; indigenous languages; language contact; bilingual education'
        rows.append([None, 'https://www.proquest.com', kw, c['title'],
                     c.get('venue') or '', c.get('authors') or '',
                     c.get('year'), bin5(c.get('year')),
                     (c.get('abs') or '')[:1800], LABEL[c['cat']]])
        added += 1
    print('added after final dedup:', added, '-> total', len(rows))

    # 写回：清空旧数据区（2..max）再写
    last_old = ws.max_row
    for r in range(2, last_old + 1):
        for c in range(1, 11):
            try:
                ws._cells.pop((r, c), None)
            except Exception:
                pass

    thin = Side(style='thin', color='D9D9D9')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    align = Alignment(vertical='top', wrap_text=True)

    for i, v in enumerate(rows, start=1):
        r = i + 1
        ws.cell(row=r, column=1, value=i)
        for c in range(2, 11):
            ws.cell(row=r, column=c, value=v[c - 1])
        for c in range(1, 11):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            cell.alignment = align
        ws.row_dimensions[r].height = 46

    last = len(rows) + 1
    print('data range A1:J%d' % last)

    ws.auto_filter.ref = 'A1:J%d' % last
    ws.freeze_panes = 'A2'

    # 数据验证
    ws.data_validations.dataValidation = []
    dv1 = DataValidation(type='list', formula1='"'+','.join(BINS)+'"', allow_blank=True)
    dv1.add('H2:H%d' % last)
    ws.add_data_validation(dv1)
    dv2 = DataValidation(type='list',
                         formula1='"'+','.join(LABEL[k] for k in ['A', 'B', 'AB', 'C'])+'"',
                         allow_blank=True)
    dv2.add('J2:J%d' % last)
    ws.add_data_validation(dv2)

    wb.save(OUT)
    print('saved ->', OUT)
    print('done rows:', last - 1)


if __name__ == '__main__':
    main()
