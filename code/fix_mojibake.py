# -*- coding: utf-8 -*-
"""方案A：定向修复 U+FFFD 乱码（法文省音、英文所有格、成对引号、已知复合词）"""
import re, shutil, openpyxl, collections
from openpyxl.styles import Alignment

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_阿根廷期刊_严格版.xlsx'
DST = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_阿根廷期刊_严格版_乱码修复.xlsx'
shutil.copy(SRC, DST)

ELISION = re.compile(r"(?<![\wÀ-ÿ])([dDlLnNsSjJmMtTcC])\ufffd(?=[A-Za-zÀ-ÿ])")
POSSESS = re.compile(r"(?<=[A-Za-zÀ-ÿ])\ufffd(?=[st]\b)")
POSS_FS = re.compile(r"\ufffdfs\b")
PAIR_WORD = re.compile(r"\ufffd(\S{1,40}?)\ufffd")
PAIR = re.compile(r"\ufffd([^\ufffd\n]{1,60}?)\ufffd")
PLURAL_POSS = re.compile(r"(?<=s)\ufffd(?=\s)")
DIGIT_RANGE = re.compile(r"(?<=\d)\ufffd(?=\d)")
COMPOUND = {
    'sexo\ufffdgénero': 'sexo-género',
    'ender\ufffdneutral': 'ender-neutral',
    'Ye\ufffdkuana': "Ye'kuana",
}

def repair(text, stats):
    t = text
    for k, v in COMPOUND.items():
        if k in t:
            stats['已知复合词'] += t.count(k); t = t.replace(k, v)
    n = len(ELISION.findall(t))
    if n: stats['法文省音/撇号'] += n; t = ELISION.sub(r"\1'", t)
    # 先修成对引号，再做撇号类规则，避免把右引号误当撇号
    for pat, need in ((PAIR_WORD, 1), (PAIR, 2)):
        for _ in range(3):
            def rep(m):
                inner = m.group(1)
                if len(re.sub(r'[^A-Za-zÀ-ÿ]', '', inner)) < need:
                    return m.group(0)
                before = t[m.start() - 1] if m.start() > 0 else ' '
                after = t[m.end()] if m.end() < len(t) else ' '
                if before.isalnum() or after.isalnum():
                    return m.group(0)
                stats['成对引号'] += 1
                return '“' + inner + '”'
            new = pat.sub(rep, t)
            if new == t: break
            t = new
    n = len(DIGIT_RANGE.findall(t))
    if n: stats['数字区间 –'] += n; t = DIGIT_RANGE.sub('–', t)
    n = len(POSS_FS.findall(t))
    if n: stats['英文所有格 ’s'] += n; t = POSS_FS.sub('’s', t)
    n = len(POSSESS.findall(t))
    if n: stats['英文所有格 ’s'] += n; t = POSSESS.sub('’', t)
    n = len(PLURAL_POSS.findall(t))
    if n: stats['复数所有格 s’'] += n; t = PLURAL_POSS.sub('’', t)
    return t

wb = openpyxl.load_workbook(DST)
stats = collections.Counter()
changed = 0
leftovers = []

for ws in wb.worksheets:
    if ws.title not in ('corpus_merged', 'Sheet2'):
        continue
    col = 3 if ws.title == 'corpus_merged' else 9
    for r in range(1, ws.max_row + 1):
        cell = ws.cell(r, col)
        v = cell.value
        if not isinstance(v, str) or '\ufffd' not in v:
            continue
        nv = repair(v, stats)
        if nv != v:
            cell.value = nv
            changed += 1
        if '\ufffd' in nv:
            i = nv.find('\ufffd')
            leftovers.append((ws.title, cell.coordinate,
                              nv[max(0, i - 30):i + 30].replace('\n', ' ')))

# 台账
ws5 = wb.create_sheet('乱码修复台账')
ws5['A1'] = '修复汇总'; ws5['A1'].font = openpyxl.styles.Font(bold=True, size=12)
rows = [('修复规则', '处理次数')] + [(k, v) for k, v in stats.most_common()]
for i, (k, v) in enumerate(rows, start=3):
    ws5.cell(i, 1, k); ws5.cell(i, 2, v)
ws5.cell(len(rows) + 4, 1, '修复后仍残留 U+FFFD 的单元格')
ws5.cell(len(rows) + 4, 1).font = openpyxl.styles.Font(bold=True)
ws5.cell(len(rows) + 5, 1, '工作表'); ws5.cell(len(rows) + 5, 2, '单元格')
ws5.cell(len(rows) + 5, 3, '上下文')
base = len(rows) + 6
for i, (sh, coord, ctx) in enumerate(leftovers[:400], start=base):
    ws5.cell(i, 1, sh); ws5.cell(i, 2, coord)
    ws5.cell(i, 3, ctx).alignment = Alignment(vertical='top')
ws5.column_dimensions['A'].width = 22
ws5.column_dimensions['B'].width = 12
ws5.column_dimensions['C'].width = 80

wb.save(DST)
print('changed cells', changed)
print('stats', dict(stats))
print('leftover cells', len(leftovers))
print('saved', DST)
