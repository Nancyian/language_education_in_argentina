# -*- coding: utf-8 -*-
"""图 3 数据准备：从 lab_results.json 取 phi 前 N 词，从语料重算词对共现（窗口 10）。
仅复用 lab_model.py 的语料构建段（不跑 LDA），结果缓存到 work/net_cache.pkl。
"""
import json, io, os, pickle, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'work', 'lab_results.json')
CACHE = os.path.join(ROOT, 'work', 'net_cache.pkl')

D = json.load(io.open(RES, encoding='utf-8'))


def _corpus():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    src = io.open(os.path.join(ROOT, 'tools', 'lab_model.py'), encoding='utf-8').read()
    prefix = src.split('def lda(')[0]
    ns = {}
    exec(compile(prefix, 'lab_model_prefix', 'exec'), ns)
    docs, VOC, pair = ns['docs'], ns['VOC'], ns['pair_w']
    # 只保留 815 词范围内的共现，转成词对字符串 -> 次数
    i2w = VOC
    co = {}
    for (a, b), c in pair.items():
        co[(i2w[a], i2w[b])] = c
    data = dict(docs=docs, vocab=VOC, co=co)
    pickle.dump(data, open(CACHE, 'wb'))
    return data


def load(topn=18):
    c = _corpus()
    vocab, co, docs = c['vocab'], c['co'], c['docs']
    phi = D['phi']
    words = []
    for k in range(D['K']):
        idx = sorted(range(len(vocab)), key=lambda i: -phi[k][i])[:topn]
        words.append([(vocab[i], phi[k][i]) for i in idx])
    return dict(topics=D['topics'], phi=phi, words=words, co=co, docs=docs, vocab=vocab)


if __name__ == '__main__':
    d = load(18)
    for k, ws in enumerate(d['words'], 1):
        print(k, ' '.join(w for w, _ in ws))
    # 同主题内共现强度分布
    cnt = collections.Counter()
    for ws in d['words']:
        names = [w for w, _ in ws]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = sorted((names[i], names[j]))
                v = d['co'].get((a, b), 0)
                cnt[min(v, 10)] += 1
    print('同主题词对共现分布', dict(sorted(cnt.items())))
