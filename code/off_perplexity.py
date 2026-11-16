# -*- coding: utf-8 -*-
"""官方话语 71 篇：LDA 困惑度曲线（K=2..20，5 折交叉验证 × 2 次重复）
语料/分词/超参与 tools/off_model.py 完全一致（Sheet2 标题×2 + 相关性正文，
alpha=0.1, beta=0.02, 200 轮 Gibbs, seed=7），保证困惑度与主题模型同一 DTM。

困惑度定义（Blei 2003 留出法）：
  ppl = exp( - sum_d sum_i log p(w_di) / sum_d n_d ),  p(w|d) = sum_k theta_dk * phi_kw
留出文档的 theta 用固定 phi 的 EM 折叠推断（不参与训练）。
"""
import openpyxl, json, io, re, math, random, collections, statistics, os
import numpy as np

random.seed(7); np.random.seed(7)

BASE = r'C:/Users/Administrator/WorkBuddy/2026-10-15-20-02-36'
SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_正式版_v2.xlsx'

SW = set("""a al algo algun alguna alguno algunos ante antes aquel aquella aquellas aquello aquellos asi
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
buenos aires ciudad gobierno autonoma nacional pagina web sitio sitioweb gob
""".split())

NORM = [(r'[áà]', 'a'), (r'[éè]', 'e'), (r'[íì]', 'i'), (r'[óò]', 'o'), (r'[úù]', 'u'),
        (r'ñ', 'n'), (r'ü', 'u')]


def norm_tok(w):
    w = w.lower()
    for a, b in NORM:
        w = re.sub(a, b, w)
    return w


def stem(w):
    for suf, rep in (('ciones', 'cion'), ('cion', 'cion'), ('idades', 'idad'), ('idad', 'idad'),
                     ('mente', ''), ('amientos', ''), ('amiento', ''), ('aciones', 'acion'),
                     ('ando', ''), ('iendo', ''), ('ados', 'ado'), ('idos', 'ido'),
                     ('ivos', 'ivo'), ('ivas', 'iva')):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + rep
    if w.endswith('es') and len(w) > 5:
        return w[:-2]
    if w.endswith('s') and len(w) > 4:
        return w[:-1]
    return w


FIX = {'languag': 'language', 'languaje': 'lenguaje'}


def tokenize(t):
    t = re.sub(r'<[^>]+>', ' ', t or '')
    out = []
    for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t):
        n = norm_tok(w)
        if len(n) < 4 or n in SW or n in STOP_EXTRA:
            continue
        out.append(FIX.get(stem(n), stem(n)))
    return out


ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
docs = []
for r in range(2, ws.max_row + 1):
    title = str(ws.cell(r, 4).value or '').strip()
    ab = str(ws.cell(r, 9).value or '').strip()
    toks = tokenize((title + '. ') * 2 + ab)
    if len(toks) < 15:
        continue
    docs.append(toks)
N = len(docs)

df = collections.Counter()
for d in docs:
    df.update(set(d))
VOC = sorted([w for w, c in df.items() if c >= 2 and c <= 0.55 * N])
v2i = {w: i for i, w in enumerate(VOC)}
V = len(VOC)
D = [[v2i[w] for w in d if w in v2i] for d in docs]
print('docs %d vocab %d tokens %d' % (N, V, sum(len(d) for d in D)), flush=True)

ALPHA, BETA, ITERS = 0.1, 0.02, 120


def lda_gibbs(idx_docs, K, iters=ITERS, seed=7):
    rng = random.Random(seed)
    sub = [D[i] for i in idx_docs]
    ndk = np.zeros((len(sub), K)); nkw = np.zeros((K, V)); nk = np.zeros(K)
    z = []
    for i, d in enumerate(sub):
        zi = [rng.randrange(K) for _ in d]
        z.append(zi)
        for j, w in enumerate(d):
            k = zi[j]; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    vb = V * BETA
    for it in range(iters):
        for i, d in enumerate(sub):
            for j, w in enumerate(d):
                k0 = z[i][j]
                ndk[i, k0] -= 1; nkw[k0, w] -= 1; nk[k0] -= 1
                p = (ndk[i] + ALPHA) * (nkw[:, w] + BETA) / (nk + vb)
                p = p / p.sum()
                k = min(int(np.searchsorted(np.cumsum(p), rng.random())), K - 1)
                z[i][j] = k; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    phi = nkw + BETA
    phi = phi / phi.sum(1, keepdims=True)
    return phi


def doc_ll(d, phi, em=60):
    """固定 phi，用 EM 推断 theta，返回该文档的 log 似然"""
    K = phi.shape[0]
    th = np.full(K, 1.0 / K)
    idx = np.array(d)
    for _ in range(em):
        # p(k|w_i) ∝ theta_k * phi[k, w_i]
        w = th[:, None] * phi[:, idx]           # K x n
        w = w / w.sum(0, keepdims=True)
        th = w.sum(1) / len(idx)
    p_w = (th[:, None] * phi[:, idx]).sum(0)
    return float(np.log(np.maximum(p_w, 1e-12)).sum())


def perplexity(train_idx, test_idx, K, seed=7):
    phi = lda_gibbs(train_idx, K, seed=seed)
    ll, ntok = 0.0, 0
    for i in test_idx:
        if not D[i]:
            continue
        ll += doc_ll(D[i], phi); ntok += len(D[i])
    if ntok == 0:
        return float('nan')
    return math.exp(-ll / ntok)


Ks = list(range(2, 21))
NSPLIT, NREP = 5, 2
curve = {}
for K in Ks:
    vals = []
    for rep in range(NREP):
        rng = np.random.RandomState(7 + 10 * rep)
        order = rng.permutation(N)
        folds = np.array_split(order, NSPLIT)
        for f in range(NSPLIT):
            te = [int(x) for x in folds[f]]
            tr = [int(x) for x in order if int(x) not in set(te)]
            vals.append(perplexity(tr, te, K, seed=7 + f))
    curve[K] = vals
    print('K=%2d ppl mean=%.1f sd=%.1f' % (K, statistics.mean(vals), statistics.pstdev(vals)), flush=True)

mean = {K: float(np.mean(v)) for K, v in curve.items()}
sd = {K: float(np.std(v)) for K, v in curve.items()}
mins = [K for K in Ks if 2 < K < 20 and mean[K] < mean[K - 1] and mean[K] < mean[K + 1]]
best = min(Ks, key=lambda k: mean[k])

out = {
    'N': N, 'vocab_size': V, 'tokens': sum(len(d) for d in D),
    'corpus': 'Sheet2 标题×2 + 相关性正文（与 off_model.py 同一 DTM）',
    'alpha': ALPHA, 'beta': BETA, 'iters': ITERS,
    'nfold': NSPLIT, 'nrep': NREP,
    'ks': Ks,
    'perplexity_mean': {str(k): round(mean[k], 2) for k in Ks},
    'perplexity_sd': {str(k): round(sd[k], 2) for k in Ks},
    'raw': {str(k): [round(x, 2) for x in curve[k]] for k in Ks},
    'local_minima': mins,
    'global_min_k': best, 'global_min_ppl': round(mean[best], 2),
    'ppl_k8': round(mean[8], 2),
    'k8_is_local_min': 8 in mins,
    'k8_drop_pct': round((mean[7] - mean[8]) / mean[7] * 100, 2),
    'k8_rise_pct': round((mean[9] - mean[8]) / mean[8] * 100, 2),
}
os.makedirs(os.path.join(BASE, 'work'), exist_ok=True)
json.dump(out, io.open(os.path.join(BASE, 'work/off_perplexity.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('local minima', mins, '| global min K=%d ppl=%.1f' % (best, mean[best]))
print('saved work/off_perplexity.json')
