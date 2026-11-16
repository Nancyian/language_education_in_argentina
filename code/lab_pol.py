# -*- coding: utf-8 -*-
"""极性得分：加平滑的分母，避免单篇文档只含 1 个评价词时得到 ±1 的极端值"""
import openpyxl, json, io, re, collections
SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx'
D = json.load(io.open('work/lab_results.json', encoding='utf-8'))
POS, NEG = D['pos_roots'], D['neg_roots']
LAM = 2.0

NORM = [(r'[áà]', 'a'), (r'[éè]', 'e'), (r'[íì]', 'i'), (r'[óò]', 'o'), (r'[úù]', 'u'), (r'ñ', 'n'), (r'ü', 'u')]

def norm_tok(w):
    w = w.lower()
    for a, b in NORM: w = re.sub(a, b, w)
    return w

ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
texts = []
for r in range(2, ws.max_row + 1):
    texts.append(str(ws.cell(r, 4).value or '').strip() + '. ' + str(ws.cell(r, 9).value or '').strip())
assert len(texts) == len(D['docs'])

def polarity(t):
    s = ' '.join(norm_tok(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t))
    pos = sum(s.count(r) for r in POS); neg = sum(s.count(r) for r in NEG)
    return (pos - neg) / (pos + neg + LAM), pos, neg

pol = [polarity(t) for t in texts]
K = D['K']
import numpy as np
theta = np.array([d['theta'] for d in D['docs']])
years = D['years']

for i, d in enumerate(D['docs']):
    d['pol'] = round(pol[i][0], 3); d['pos'] = pol[i][1]; d['neg'] = pol[i][2]

year_pol = {}
for y in years:
    idx = [i for i, d in enumerate(D['docs']) if d['year'] == y]
    w = theta[idx]; s = np.array([pol[i][0] for i in idx]); iv = w.sum(0)
    year_pol[str(y)] = [round(float((w[:, k] * s).sum() / iv[k]) if iv[k] > 0 else 0.0, 4) for k in range(K)]
D['year_pol'] = year_pol
D['polarity_lambda'] = LAM
D['polarity_hit'] = sum(1 for p in pol if p[1] + p[2] > 0)

vals = [p[0] for p in pol if p[1] + p[2] > 0]
print('hit', D['polarity_hit'], 'range', round(min(vals), 2), round(max(vals), 2),
      'mean', round(sum(vals) / len(vals), 3))
allv = [v for y in years for v in year_pol[str(y)]]
print('year_pol range', round(min(allv), 2), round(max(allv), 2))
json.dump(D, io.open('work/lab_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved')
