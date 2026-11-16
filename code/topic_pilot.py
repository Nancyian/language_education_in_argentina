# -*- coding: utf-8 -*-
"""专家话语 66 篇：LDA(Gibbs, numpy 自实现) + 一致性选 K + 时间聚合 + 主题网络边"""
import openpyxl, json, io, math, random, re, collections
import numpy as np

random.seed(7); np.random.seed(7)

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx'

SW = set("""a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas aquello aquellos asi
aun bajo bien cada casi como con contra cual cuales cualquier cuando de del desde donde dos durante e el ella ellas
ello ellos en entre era eran eres es esa esas ese eso esos esta estaba estado estan estar estas este esto estos
estuvo ha habia han hasta hay la las le les lo los mas me mi mis mucho muchos muy nada ni no nos nosotros nuestra
nuestro o os otra otras otro otros para pero poco por porque que quien quienes se sea segun ser si sin sobre son
su sus tal tambien tan tanto te tiene tienen todo todos tu tus un una unas uno unos y ya yo
the of and in to for with on by from that this these those as at be been is are was were it its an or we our
their they which has have not but can also such more study article paper research results using used
ser sido siendo estar estado este esta estos estas dicho dicha puede pueden debe deben tanto cuanto
""".split())

STOP_EXTRA = set("""revista journal article articulo articulos trabajo texto textos analisis analizar aborda abordar
propone propone objetivo objetivos resultado resultados conclusion conclusiones metodologia partir partir
presente trabajo caso casos manera forma parte veces mundo siglo xix xx xxi
issn doi rahl anclajes traslaciones signo sena quimu quimun gramma pilquen argonautas
masquedos entramados conocimento integracion cuadernos ciencias comportamiento
universidad nacional revista journal article paper research study results using used
""".split())

NORM = [(r'[áà]','a'),(r'[éè]','e'),(r'[íì]','i'),(r'[óò]','o'),(r'[úù]','u'),(r'ñ','n'),(r'ü','u')]

def norm_tok(w):
    w = w.lower()
    for a,b in NORM: w = re.sub(a,b,w)
    return w

def stem(w):
    for suf, rep in (('ciones','cion'),('cion','cion'),('idades','idad'),('idad','idad'),
                     ('mente',''),('amientos',''),('amiento',''),('aciones','acion'),('acion','acion'),
                     ('ando',''),('iendo',''),('ados','ado'),('idos','ido'),('ivos','ivo'),('ivas','iva')):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + rep
    if w.endswith('es') and len(w) > 5: return w[:-2]
    if w.endswith('s') and len(w) > 4: return w[:-1]
    return w

FIX = {'languag': 'language', 'languaje': 'lenguaje'}

def tokenize(t):
    t = t or ''
    t = re.sub(r'<[^>]+>', ' ', t)
    out = []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t):
        n = norm_tok(w)
        if len(n) < 4 or n in SW or n in STOP_EXTRA: continue
        out.append(FIX.get(stem(n), stem(n)))
    return out

# ---------- load ----------
ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
docs, meta = [], []
for r in range(2, ws.max_row + 1):
    title = str(ws.cell(r, 4).value or '').strip()
    ab = str(ws.cell(r, 9).value or '').strip()
    text = (title + '. ') * 2 + ab
    toks = tokenize(text)
    if len(toks) < 15: continue
    docs.append(toks)
    meta.append({'no': ws.cell(r, 1).value, 'title': title,
                 'venue': str(ws.cell(r, 5).value or ''), 'authors': str(ws.cell(r, 6).value or ''),
                 'year': int(str(ws.cell(r, 7).value or 0)[:4] or 0),
                 'kw': str(ws.cell(r, 3).value or '')})
N = len(docs)

# ---------- vocab ----------
df = collections.Counter()
for d in docs: df.update(set(d))
VOC = sorted([w for w, c in df.items() if c >= 2 and c <= 0.55 * N])
v2i = {w: i for i, w in enumerate(VOC)}
V = len(VOC)
D = [[v2i[w] for w in d if w in v2i] for d in docs]
print('docs', N, 'tokens', sum(len(d) for d in D), 'vocab', V)

# ---------- Gibbs ----------
def lda(K, iters=260):
    Nd = [len(d) for d in D]
    z = [[random.randrange(K) for _ in d] for d in D]
    ndk = np.zeros((N, K)); nkw = np.zeros((K, V)); nk = np.zeros(K)
    for i, d in enumerate(D):
        for j, w in enumerate(d):
            k = z[i][j]; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    alpha, beta = 0.1, 0.02
    vb = V * beta
    for it in range(iters):
        for i, d in enumerate(D):
            for j, w in enumerate(d):
                k0 = z[i][j]
                ndk[i, k0] -= 1; nkw[k0, w] -= 1; nk[k0] -= 1
                p = (ndk[i] + alpha) * (nkw[:, w] + beta) / (nk + vb)
                p = p / p.sum()
                k = int(np.searchsorted(np.cumsum(p), random.random()))
                k = min(k, K - 1)
                z[i][j] = k; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    theta = (ndk + alpha); theta = theta / theta.sum(1, keepdims=True)
    phi = (nkw + beta); phi = phi / phi.sum(1, keepdims=True)
    return theta, phi

# ---------- coherence (UMass) ----------
dcount = collections.Counter()
pair_d = collections.Counter()
sets = [set(d) for d in D]
for s in sets:
    for w in s: dcount[w] += 1
    for w in s:
        for v in s:
            if w != v: pair_d[(w, v)] += 1

def umass(phi, topn=10):
    sc = []
    for k in range(phi.shape[0]):
        top = np.argsort(-phi[k])[:topn]
        s, n = 0.0, 0
        for i in range(1, len(top)):
            for j in range(i):
                wi, wj = top[i], top[j]
                dwi = dcount.get(wi, 0)
                if dwi == 0: continue
                s += math.log((pair_d.get((wi, wj), 0) + 1.0) / dwi); n += 1
        if n: sc.append(s / n)
    return float(np.mean(sc)) if sc else -99.0

results = {}
best = None
for K in (4, 5, 6, 7, 8, 9):
    th, ph = lda(K)
    c = umass(ph)
    results[K] = (th, ph, c)
    print('K=%d coherence=%.4f' % (K, c), flush=True)
    if best is None or c > best[1]: best = (K, c, th, ph)

# 论文常用：一致性最高附近取解释性更好的 K
Ks = sorted(results)
print('coherence curve', {k: round(results[k][2], 4) for k in Ks})
K = best[0]
theta, phi, coh = results[K][0], results[K][1], results[K][2]
print('chosen K', K, 'coh', round(coh, 4))

# ---------- outputs ----------
def top_words(k, n=12):
    return [(VOC[i], round(float(phi[k, i]), 5)) for i in np.argsort(-phi[k])[:n]]

topics = [{'id': k + 1, 'words': top_words(k), 'share': float(theta[:, k].mean()),
           'size': int((theta.argmax(1) == k).sum()),
           'periods': {}} for k in range(K)]

PERIODS = [(1996, 2013, '≤2013'), (2014, 2018, '2014-2018'), (2019, 2022, '2019-2022'), (2023, 2030, '2023-2026')]
for lo, hi, lab in PERIODS:
    idx = [i for i, m in enumerate(meta) if lo <= m['year'] <= hi]
    for k in range(K):
        share = float(theta[idx, k].mean()) if idx else 0.0
        topics[k]['periods'][lab] = round(share, 4)
    print(lab, len(idx), 'docs')

# 主题网络：共享 top20 词加权
topsets = [set(VOC[i] for i in np.argsort(-phi[k])[:20]) for k in range(K)]
edges = []
for a in range(K):
    for b in range(a + 1, K):
        sh = topsets[a] & topsets[b]
        if sh:
            edges.append({'a': a + 1, 'b': b + 1, 'w': len(sh), 'shared': sorted(sh)[:6]})

# 期刊 × 主题
venues = sorted(set(m['venue'] for m in meta))
vmat = {v: [0] * K for v in venues}
for i, m in enumerate(meta):
    vmat[m['venue']][int(theta[i].argmax())] += 1

# 文档级
docrows = []
for i, m in enumerate(meta):
    docrows.append({'no': m['no'], 'title': m['title'], 'year': m['year'],
                    'venue': m['venue'], 'topic': int(theta[i].argmax()) + 1,
                    'p': round(float(theta[i].max()), 3),
                    'theta': [round(float(x), 4) for x in theta[i]]})

out = {'N': N, 'K': K, 'coherence': round(coh, 4),
       'vocab': VOC, 'phi': [[round(float(x), 6) for x in row] for row in phi],
       'coherence_curve': {k: round(results[k][2], 4) for k in Ks},
       'topics': topics, 'edges': edges,
       'periods': [{'lo': lo, 'hi': hi, 'label': lab,
                    'n': len([1 for m in meta if lo <= m['year'] <= hi])} for lo, hi, lab in PERIODS],
       'venue_matrix': vmat, 'docs': docrows,
       'years': sorted([m['year'] for m in meta])}
json.dump(out, io.open('work/topic_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved work/topic_results.json')
for t in topics:
    print(t['id'], 'size', t['size'], 'share %.3f' % t['share'], [w for w, _ in t['words'][:8]])
