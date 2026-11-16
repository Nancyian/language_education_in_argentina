# -*- coding: utf-8 -*-
"""Read an xlsx sheet without third-party deps (stdlib only)."""
import sys, re, os, zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def col_to_idx(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n - 1

def load_shared(z):
    ss = []
    with z.open('xl/sharedStrings.xml') as f:
        # stream parse
        for ev, el in ET.iterparse(f, events=('end',)):
            if el.tag == NS + 'si':
                txt = ''.join(t.text or '' for t in el.iter(NS + 't'))
                ss.append(txt)
                el.clear()
    return ss

def read_sheet(path, sheet_file, max_rows=None):
    z = zipfile.ZipFile(path)
    ss = load_shared(z)
    rows = []
    with z.open(sheet_file) as f:
        cur = None
        for ev, el in ET.iterparse(f, events=('end',)):
            if el.tag == NS + 'row':
                rnum = int(el.get('r'))
                cells = {}
                for c in el.findall(NS + 'c'):
                    ref = c.get('r')
                    col = re.match(r'[A-Z]+', ref).group(0)
                    ci = col_to_idx(col)
                    t = c.get('t')
                    v = c.find(NS + 'v')
                    isel = c.find(NS + 'is')
                    if t == 's' and v is not None:
                        val = ss[int(v.text)]
                    elif t == 'inlineStr' and isel is not None:
                        val = ''.join(x.text or '' for x in isel.iter(NS + 't'))
                    elif v is not None:
                        val = v.text
                    else:
                        val = None
                    if val is not None and str(val).strip() != '':
                        cells[ci] = val
                rows.append((rnum, cells))
                el.clear()
                if max_rows and len(rows) >= max_rows:
                    break
    return rows

if __name__ == '__main__':
    path = sys.argv[1]
    sheet_file = sys.argv[2] if len(sys.argv) > 2 else 'xl/worksheets/sheet1.xml'
    max_rows = int(sys.argv[3]) if len(sys.argv) > 3 else None
    rows = read_sheet(path, sheet_file, max_rows)
    for rnum, cells in rows:
        if not cells:
            continue
        mx = max(cells)
        out = []
        for i in range(mx + 1):
            v = cells.get(i, '')
            v = str(v).replace('\t', ' ').replace('\n', '\\n')
            out.append(v)
        print(f"R{rnum}\t" + "\t".join(out))
