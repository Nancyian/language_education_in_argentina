# -*- coding: utf-8 -*-
"""按 gensim c_v 的思路计算各 K 的一致性（滑动窗口共现 → PPMI+SVD 词向量 → 余弦×NPMI）"""
import openpyxl, json, io, math, random, re, collections
import numpy as np
random.seed(7); np.random.seed(7)

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx'
OLD = json.load(io.open('work/topic_results.json', encoding='utf-8'))
VOC = OLD['vocab']; V = len(VOC); v2i = {w: i for i, w in enumerate(VOC)}

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
propone objetivo objetivos resultado resultados conclusion conclusiones metodologia partir
presente caso casos manera forma parte veces mundo siglo xix xx xxi
issn doi rahl anclajes traslaciones signo sena quimu quimun gramma pilquen argonautas
masquedos entramados conocimento integracion cuadernos ciencias comportamiento
universidad nacional paper research study results using used
""".split())
NORM = [(r'[áà]', 'a'), (r'[éè]', 'e'), (r'[íì]', 'i'), (r'[óò]', 'o'), (r'[úù]', 'u'), (r'ñ', 'n'), (r'ü', 'u')]

def norm_tok(w):
    w = w.lower()
    for a, b in NORM: w = re.sub(a, b, w)
    return w

def stem(w):
    for suf, rep in (('ciones', 'cion'), ('cion', 'cion'), ('idades', 'idad'), ('idad', 'idad'),
                     ('mente', ''), ('amientos', ''), ('amiento', ''), ('aciones', 'acion'),
                     ('ando', ''), ('iendo', ''), ('ados', 'ado'), ('idos', 'ido'),
                     ('ivos', 'ivo'), ('ivas', 'iva')):
        if w.endswith(suf) and len(w) - len(suf) >= 4: return w[:-len(suf)] + rep
    if w.endswith('es') and len(w) > 5: return w[:-2]
    if w.endswith('s') and len(w) > 4: return w[:-1]
    return w

FIX = {'languag': 'language', 'languaje': 'lenguaje'}

def tokenize(t):
    t = re.sub(r'<[^>]+>', ' ', t or '')
    out = []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t):
        n = norm_tok(w)
        if len(n) < 4 or n in SW or n in STOP_EXTRA: continue
        out.append(FIX.get(stem(n), stem(n)))
    return out

ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
D = []
for r in range(2, ws.max_row + 1):
    title = str(ws.cell(r, 4).value or '').strip(); ab = str(ws.cell(r, 9).value or '').strip()
    toks = tokenize((title + '. ') * 2 + ab)
    D.append([v2i[w] for w in toks if w in v2i])
N = len(D)

# 滑动窗口共现
W = 10
C = np.zeros((V, V))
for d in D:
    for i, w in enumerate(d):
        for j in range(i + 1, min(i + W, len(d))):
            C[w, d[j]] += 1; C[d[j], w] += 1
tot = C.sum()
P = C / tot
pw = np.array([P[i, :].sum() for i in range(V)])
PPMI = np.zeros_like(C)
with np.errstate(divide='ignore', invalid='ignore'):
    M = np.log((P * tot) * tot / (np.outer(pw * tot, pw * tot) + 1e-12) + 1e-12)
PPMI = np.maximum(M, 0)
U, S, _ = np.linalg.svd(PPMI, full_matrices=False)
EMB = U[:, :100] * np.sqrt(S[:100] + 1e-12)

def cv_score(phi, topn=10):
    sc = []
    for k in range(phi.shape[0]):
        top = list(np.argsort(-phi[k])[:topn])
        vals = []
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                a, b = top[i], top[j]
                pab = P[a, b]
                if pab <= 1e-12: continue
                npmi = math.log(pab / (pw[a] * pw[b] + 1e-12)) / (-math.log(pab))
                va, vb = EMB[a], EMB[b]
                cos = float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-12))
                vals.append(cos * (1 + npmi) / 2)
        if vals: sc.append(float(np.mean(vals)))
    return float(np.mean(sc)) if sc else 0.0

def lda(K, iters=200):
    z = [[random.randrange(K) for _ in d] for d in D]
    ndk = np.zeros((N, K)); nkw = np.zeros((K, V)); nk = np.zeros(K)
    for i, d in enumerate(D):
        for j, w in enumerate(d):
            k = z[i][j]; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    alpha, beta = 0.1, 0.02; vb = V * beta
    for it in range(iters):
        for i, d in enumerate(D):
            for j, w in enumerate(d):
                k0 = z[i][j]
                ndk[i, k0] -= 1; nkw[k0, w] -= 1; nk[k0] -= 1
                p = (ndk[i] + alpha) * (nkw[:, w] + beta) / (nk + vb)
                p = p / p.sum()
                k = min(int(np.searchsorted(np.cumsum(p), random.random())), K - 1)
                z[i][j] = k; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    th = ndk + alpha; th = th / th.sum(1, keepdims=True)
    ph = nkw + beta; ph = ph / ph.sum(1, keepdims=True)
    return th, ph

cv = {}
for K in range(2, 21):
    _, ph = lda(K)
    cv[K] = round(cv_score(ph), 4)
    print('K=%2d c_v=%.4f' % (K, cv[K]), flush=True)
json.dump(cv, io.open('work/cv_curve.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('best', max(cv, key=cv.get), flush=True)
print(dict(sorted(cv.items())), flush=True)
