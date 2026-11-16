# -*- coding: utf-8 -*-
"""官方语料：K=5..14 的一致性稳健性检验（每 K 跑 6 个随机种子，取均值与标准差）"""
import io, json
import numpy as np

src = open('off_model.py', encoding='utf-8').read()
head = src.split("Ks = list(range(2, 21))")[0]
g = {'__name__': 'probe'}
exec(compile(head, 'om', 'exec'), g)

import random as _r
lda, VOC, umass, N = g['lda'], g['VOC'], g['umass'], g['N']

Ks = list(range(6, 14))
SEEDS = [1, 7, 13, 21, 33]
res = {}
for K in Ks:
    vals = []
    for s in SEEDS:
        _r.seed(s); np.random.seed(s)
        th, ph = lda(K, iters=100)
        vals.append(float(umass(ph)))
    res[K] = vals
    print('K=%2d  mean=%.4f  sd=%.4f  min=%.4f max=%.4f' %
          (K, np.mean(vals), np.std(vals), min(vals), max(vals)), flush=True)

mean = {K: float(np.mean(v)) for K, v in res.items()}
sd = {K: float(np.std(v)) for K, v in res.items()}
peaks = [K for K in Ks if Ks[0] < K < Ks[-1] and mean[K] > mean[K - 1] and mean[K] > mean[K + 1]]
best = max(Ks, key=lambda k: mean[k])
print('\n局部峰值:', peaks, '| 最佳:', best, round(mean[best], 4))
json.dump({'ks': Ks, 'seeds': SEEDS,
           'mean': {str(k): round(mean[k], 4) for k in Ks},
           'sd': {str(k): round(sd[k], 4) for k in Ks},
           'raw': {str(k): [round(x, 4) for x in res[k]] for k in Ks},
           'local_peaks': peaks, 'best_k': best},
          io.open('../work/off_coh_seeds.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved work/off_coh_seeds.json')
