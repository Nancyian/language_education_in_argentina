# -*- coding: utf-8 -*-
"""图 3（官方话语）数据准备：直接从 work/off_results.json 取 phi、主题词与窗口共现。
off_model.py 已把 10 词窗口词对共现（词形→次数）存入结果的 'co' 字段，无需再跑语料构建。
"""
import json, io, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'work', 'off_results.json')

D = json.load(io.open(RES, encoding='utf-8'))


def load(topn=18):
    vocab, phi, K = D['vocab'], D['phi'], D['K']
    words = []
    for k in range(K):
        idx = sorted(range(len(vocab)), key=lambda i: -phi[k][i])[:topn]
        words.append([(vocab[i], phi[k][i]) for i in idx])
    co = {}
    for a, b, c in D['co']:
        co[(a, b)] = c
    return dict(topics=D['topics'], phi=phi, words=words, co=co,
                docs=D['docs'], vocab=vocab)


if __name__ == '__main__':
    d = load(15)
    for k, ws in enumerate(d['words'], 1):
        print(k, ' '.join(w for w, _ in ws))
