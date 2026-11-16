# -*- coding: utf-8 -*-
"""Append curated new Dialnet items to the corpus workbook (same 9-column format)."""
import json, io, re, copy
import openpyxl
from openpyxl.styles import Alignment

SRC = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全.xlsx"
DST = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_扩充.xlsx"

def year_of(loc, date):
    if date and re.fullmatch(r'\d{4}', str(date).strip()):
        return int(str(date).strip())
    s = loc or ''
    i = s.find('Idioma:')
    if i > 0:
        s = s[:i]
    s = re.sub(r'ISSN[^,;]{0,22}', ' ', s)
    s = re.sub(r'p[áa]gs?\.\s*[\d\-–]+', ' ', s)
    s = re.sub(r'\d+\s*p[áa]gs?\.?', ' ', s)
    s = re.sub(r'Vol\.\s*[\d\-–]+', ' ', s)
    s = re.sub(r'N[ºo]\.\s*[\d\-–]+', ' ', s)
    ys = [int(y) for y in re.findall(r'(19[5-9]\d|20[0-2]\d)', s)]
    ys = [y for y in ys if 1950 <= y <= 2026]
    return ys[0] if ys else None

def bucket(y):
    if not y:
        return '时间不详'
    for a, b, lab in [(1981, 1985, '1981-1985'), (1986, 1990, '1986-1990'), (1991, 1995, '1991-1995'),
                      (1996, 2000, '1996-2000'), (2001, 2005, '2001-2005'), (2006, 2010, '2006-2010'),
                      (2011, 2015, '2011-2015'), (2016, 2020, '2016-2020'), (2021, 2025, '2021-2025'),
                      (2026, 2030, '2026-2030')]:
        if a <= y <= b:
            return lab
    return '时间不详'

def venue_from_loc(loc, title):
    s = (loc or '').strip()
    if not s:
        return ''
    s = re.split(r'\s+/\s+', s)[0]
    s = re.split(r'\s*:\s*(?=[A-ZÁÉÍÓÚÑ])', s)[0] if s.count(':') and ',' not in s.split(':')[0] else s
    s = re.sub(r'[,;]?\s*(ISSN[^,;]*|p[áa]gs?\..*|Vol\..*|N[ºo]\..*)$', '', s)
    s = s.strip(' ,;.')
    if s.lower().startswith((title or '')[:18].lower()):
        return ''
    return s

def main():
    meta = {}
    for line in io.open('work/new_meta.jsonl', encoding='utf-8'):
        r = json.loads(line)
        if 'title' in r:
            meta[r['codigo']] = r
    order = [r['codigo'] for r in json.load(io.open('work/final_new.json', encoding='utf-8'))]

    rows, seen = [], set()
    for c in order:
        r = meta.get(c)
        if not r:
            continue
        t = re.sub(r'[^a-z0-9]+', ' ', (r['title'] or '').lower()).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        y = year_of(r.get('loc'), r.get('date'))
        journal = (r.get('journal') or '').strip() or venue_from_loc(r.get('loc'), r.get('title'))
        rows.append((r, y, journal))
    rows.sort(key=lambda x: (x[1] or 9999, x[0]['title']))

    wb = openpyxl.load_workbook(SRC)
    ws = wb['Sheet2']
    last = ws.max_row
    seq0 = 0
    for row in range(2, last + 1):
        try:
            seq0 = max(seq0, int(ws.cell(row=row, column=1).value))
        except Exception:
            pass
    tmpl = [ws.cell(row=2, column=c) for c in range(1, 10)]

    n = 0
    for r, y, journal in rows:
        n += 1
        row = last + n
        src = 'https://dialnet.unirioja.es/servlet/articulo?codigo=' + r['codigo']
        vals = [seq0 + n, src, '; '.join(r.get('kws') or r.get('title_match') or []),
                re.sub(r'\s+', ' ', r['title']).strip(), journal,
                '; '.join(r.get('authors') or []), y if y else '', bucket(y),
                (r.get('abstract') or '').strip()]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c)
            cell.value = v
            t = tmpl[c - 1]
            cell.font = copy.copy(t.font)
            cell.border = copy.copy(t.border)
            cell.fill = copy.copy(t.fill)
            cell.alignment = copy.copy(t.alignment)
        ws.cell(row=row, column=8).alignment = Alignment(horizontal='left', vertical='center')

    new_last = last + n
    for dv in ws.data_validations.dataValidation:
        if '时间选项' in (dv.formula1 or ''):
            dv.sqref = 'H2:H%d' % new_last
    wb.save(DST)
    print('appended', n, '| total rows', new_last - 1)
    print('no abstract:', sum(1 for r, y, j in rows if not (r.get('abstract') or '').strip()))
    print('no journal:', sum(1 for r, y, j in rows if not j))
    print('no year:', sum(1 for r, y, j in rows if not y))
    print('saved', DST)

if __name__ == '__main__':
    main()
