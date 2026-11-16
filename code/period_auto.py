# -*- coding: utf-8 -*-
"""Extract study-period evidence from title + abstract, suggest a period label."""
import openpyxl, re, io, json

SRC = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_DOI.xlsx"

LABELS = [
    ("殖民与独立（至1850）", -9999, 1850),
    ("国家建构（1850-1900）", 1851, 1900),
    ("20世纪上半叶（1901-1945）", 1901, 1945),
    ("20世纪下半叶（1946-1999）", 1946, 1999),
    ("21世纪（2000-）", 2000, 2100),
]


def lab(y0, y1):
    if y0 is None:
        return None
    if y1 is None:
        y1 = y0
    for name, a, b in LABELS:
        if y0 >= a and y1 <= b:
            return name
    return "跨时段"


ROMAN = {'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20, 'xxi': 21}

def years_in(text):
    """4-digit years 1500-2026, excluding page-like / citation noise is left to manual review."""
    ys = [int(m) for m in re.findall(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', text)]
    return [y for y in ys if 1500 <= y <= 2026]

def century_in(text):
    out = []
    for m in re.finditer(r'siglos?\s+([XVIxvi]{2,4})', text, re.I):
        r = m.group(1).lower()
        if r in ROMAN:
            out.append(ROMAN[r])
    return out

wb = openpyxl.load_workbook(SRC, read_only=True)
ws = wb['Sheet2']
rows = list(ws.iter_rows(min_row=2, max_col=9, values_only=True))
wb.close()

out = []
for r in rows:
    seq, title, abstract = r[0], (r[3] or ''), (r[8] or '')
    body = abstract
    ys = years_in(body)
    cents = century_in(body)
    cand = []
    if ys:
        cand.append((min(ys), max(ys)))
    for c in cents:
        cand.append((c * 100 - 99, c * 100))
    sug, evidence = None, ''
    if cand:
        y0 = min(c[0] for c in cand)
        y1 = max(c[1] for c in cand)
        sug = lab(y0, y1)
        # sentences that carry years / century
        sents = re.split(r'(?<=[.;!?])\s+', body)
        hits = [s.strip() for s in sents if re.search(r'\b(1[5-9]\d{2}|20[0-2]\d)\b|siglos?\s+[XVIxvi]{2,4}', s)]
        evidence = ' || '.join(h[:190] for h in hits[:2])
    out.append({
        'seq': seq, 'title': title, 'sug': sug or '通论/不详',
        'y0': cand and min(c[0] for c in cand) or None,
        'y1': cand and max(c[1] for c in cand) or None,
        'years': sorted(set(ys))[:12], 'evidence': evidence,
    })

with io.open('work/period_auto.tsv', 'w', encoding='utf-8') as f:
    f.write('seq\ty0\ty1\tsug\tyears\ttitle\tevidence\n')
    for o in out:
        f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (
            o['seq'], o['y0'], o['y1'], o['sug'],
            ','.join(map(str, o['years'])), o['title'][:90].replace('\t', ' '),
            o['evidence'].replace('\t', ' ').replace('\n', ' ')))

import collections
print(collections.Counter(o['sug'] for o in out))
print('saved work/period_auto.tsv', len(out))
