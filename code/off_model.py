# -*- coding: utf-8 -*-
"""官方话语 71 篇：LDA 多 K 扫描（u_mass）+ 主题-年份矩阵 + 极性得分
输出 work/off_results.json。口径与专家话语完全一致：同一分词与词干化、
同一 seed=7、α=0.1、β=0.02、200 轮 Gibbs；极性词典沿用同一 POS/NEG 词根，
保证两个语料库的结果可直接对照。
分组维度：发布平台（对应专家版的期刊分组）；时间维度用发布年份，时间不详的
文档不纳入年份类图表。
"""
import openpyxl, json, io, math, random, re, collections
import numpy as np

random.seed(7); np.random.seed(7)

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_正式版_v2.xlsx'

SW = set("""a al algo algun alguna alguna alguno algunos ante antes aquel aquella aquellas aquello aquellos asi
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
    for a, b in NORM: w = re.sub(a, b, w)
    return w

def stem(w):
    for suf, rep in (('ciones', 'cion'), ('cion', 'cion'), ('idades', 'idad'), ('idad', 'idad'),
                     ('mente', ''), ('amientos', ''), ('amiento', ''), ('aciones', 'acion'),
                     ('ando', ''), ('iendo', ''), ('ados', 'ado'), ('idos', 'ido'),
                     ('ivos', 'ivo'), ('ivas', 'iva')):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + rep
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

# ---------- load ----------
ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
docs, meta, raw_text = [], [], []
for r in range(2, ws.max_row + 1):
    title = str(ws.cell(r, 4).value or '').strip()
    ab = str(ws.cell(r, 9).value or '').strip()
    text = (title + '. ') * 2 + ab
    toks = tokenize(text)
    if len(toks) < 15: continue
    docs.append(toks); raw_text.append(title + '. ' + ab)
    yr_s = str(ws.cell(r, 7).value or '').strip()[:4]
    year = int(yr_s) if yr_s.isdigit() else None
    meta.append({'no': ws.cell(r, 1).value, 'title': title,
                 'venue': str(ws.cell(r, 5).value or ''),
                 'period': str(ws.cell(r, 8).value or ''),
                 'year': year,
                 'kw': str(ws.cell(r, 3).value or '')})
N = len(docs)

df = collections.Counter()
for d in docs: df.update(set(d))
VOC = sorted([w for w, c in df.items() if c >= 2 and c <= 0.55 * N])
v2i = {w: i for i, w in enumerate(VOC)}
V = len(VOC)
D = [[v2i[w] for w in d if w in v2i] for d in docs]
print('docs', N, 'vocab', V, 'tokens', sum(len(d) for d in D), flush=True)

# ---------- u_mass（文档级共现，与 lab_model2.py 完全一致）----------
dcount = collections.Counter(); pair_d = collections.Counter()
for s in (set(d) for d in D):
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

# ---------- Gibbs ----------
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
                k = int(np.searchsorted(np.cumsum(p), random.random()))
                k = min(k, K - 1)
                z[i][j] = k; ndk[i, k] += 1; nkw[k, w] += 1; nk[k] += 1
    theta = ndk + alpha; theta = theta / theta.sum(1, keepdims=True)
    phi = nkw + beta; phi = phi / phi.sum(1, keepdims=True)
    return theta, phi

Ks = list(range(2, 21))
curve_um, store = {}, {}
for K in Ks:
    th, ph = lda(K)
    curve_um[K] = round(umass(ph), 4)
    store[K] = (th, ph)
    print('K=%2d umass=%.4f' % (K, curve_um[K]), flush=True)

# 主题数择优：K<=12（每主题平均篇数 >= 5.9），与图 2 口径一致
cmp_ks = [k for k in Ks if k <= 12]
K = max(cmp_ks, key=lambda k: curve_um[k])
print('selected K =', K, curve_um[K], flush=True)
theta, phi = store[K]

# ---------- 主题词 ----------
def top_words(k, n=14):
    return [(VOC[i], round(float(phi[k, i]), 5)) for i in np.argsort(-phi[k])[:n]]

topics = [{'id': k + 1, 'words': top_words(k),
           'share': float(theta[:, k].mean()),
           'size': int((theta.argmax(1) == k).sum())} for k in range(K)]

# ---------- 极性（词典法，与专家版同一词根）----------
POS = """relevan significativ fundamental necesari important avanc fortalec garantiz derecho inclus
diversidad igualdad particip mejor potencial contribu promov sosten reconoc legitim vital riqueza
oportun adecuad eficaz logro consolid ampli democrat preserv valor respeto equidad justici acces
libertad identidad patrimonio memoria empoder transform innov cooperaci articulaci compromis progres
bienestar solidar autonom dignidad visibiliz recuper rescate vigencia dialogo reconocimiento
""".split()
NEG = """deficit ausenci falta carenci desigual exclu discrimin crisis problem limitaci obstacul dificultad
precari vulnerab margin subaltern hegemon colonial imposici silencio invisibil brech conflict tensi
critic cuestion denunci riesg amenaz perdid declin escase restricci segreg estigmat racismo estereotip
dominaci subordinaci negaci olvido abandon fractur deterior retroces desprotecc precariz desmantel
recort desfinanci inequidad asimetr jerarquiz homogeneiz folkloriz exotiz subestima
""".split()

def polarity(text):
    t = ' '.join(norm_tok(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text))
    pos = sum(t.count(r) for r in POS)
    neg = sum(t.count(r) for r in NEG)
    if pos + neg == 0: return 0.0, pos, neg
    # +2 平滑（与报告公式 s=(P-N)/(P+N+2) 一致）：避免正面词密集的官方文本被钉在 +1
    return (pos - neg) / (pos + neg + 2.0), pos, neg

pol = [polarity(x) for x in raw_text]
print('polarity hit rate', sum(1 for p in pol if p[1] + p[2] > 0), '/', N, flush=True)

# ---------- 年份 × 主题（时间不详不纳入）----------
years = sorted(set(m['year'] for m in meta if m['year']))
year_theta = {y: theta[[i for i, m in enumerate(meta) if m['year'] == y]].mean(0) for y in years}
year_pol = {}
for y in years:
    idx = [i for i, m in enumerate(meta) if m['year'] == y]
    w = theta[idx]
    s = np.array([pol[i][0] for i in idx])
    iv = w.sum(0)
    year_pol[y] = [float((w[:, k] * s).sum() / iv[k]) if iv[k] > 0 else 0.0 for k in range(K)]

# ---------- 平台分组 ----------
ven_cnt = collections.Counter(m['venue'] for m in meta)
big = [v for v, c in ven_cnt.most_common() if c >= 3]
small = [v for v, c in ven_cnt.most_common() if c < 3]
groups = {v: [i for i, m in enumerate(meta) if m['venue'] == v] for v in big}
if small:
    groups['其他平台（%d 个，各 1–2 篇）' % len(small)] = [i for i, m in enumerate(meta) if m['venue'] in small]
print('venue groups', [(k[:34], len(v)) for k, v in groups.items()], flush=True)

# ---------- 主题网络边 ----------
topsets = [set(VOC[i] for i in np.argsort(-phi[k])[:20]) for k in range(K)]
edges = []
for a in range(K):
    for b in range(a + 1, K):
        sh = topsets[a] & topsets[b]
        if sh: edges.append({'a': a + 1, 'b': b + 1, 'w': len(sh), 'shared': sorted(sh)[:5]})

# ---------- 10 词窗口共现（图 3 用）----------
win = 10
pair_w = collections.Counter()
for d in D:
    for i, w in enumerate(d):
        for j in range(i + 1, min(i + win, len(d))):
            a, b = w, d[j]
            pair_w[(min(a, b), max(a, b))] += 1
co = {}
for (a, b), c in pair_w.items():
    co[(VOC[a], VOC[b])] = c

docrows = [{'no': m['no'], 'title': m['title'], 'year': m['year'], 'period': m['period'],
            'venue': m['venue'],
            'topic': int(theta[i].argmax()) + 1, 'p': round(float(theta[i].max()), 3),
            'theta': [round(float(x), 4) for x in theta[i]],
            'pol': round(pol[i][0], 3), 'pos': pol[i][1], 'neg': pol[i][2],
            'cnt': len([1 for x in docs[i] if x])} for i, m in enumerate(meta)]

out = {
    'N': N, 'K': K, 'vocab_size': V,
    'coherence_curve': {str(k): v for k, v in curve_um.items()},
    'best_k': K, 'best_val': curve_um[K],
    'phi': [[round(float(x), 6) for x in row] for row in phi],
    'vocab': VOC,
    'topics': topics,
    'edges': edges,
    'years': years,
    'year_theta': {str(y): [round(float(x), 4) for x in year_theta[y]] for y in years},
    'year_pol': {str(y): [round(float(x), 4) for x in year_pol[y]] for y in years},
    'docs': docrows,
    'polarity_hit': sum(1 for p in pol if p[1] + p[2] > 0),
    'pos_roots': POS, 'neg_roots': NEG,
    'venue_groups': {k: v for k, v in groups.items()},
    'venue_matrix': {k: [int((theta[idx].argmax(1) == t).sum()) for t in range(K)]
                     for k, idx in groups.items()},
    'co': [[a, b, c] for (a, b), c in co.items()],
    'n_year_known': sum(1 for m in meta if m['year']),
    'year_n': {str(y): sum(1 for m in meta if m['year'] == y) for y in years},
}
json.dump(out, io.open('work/off_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved work/off_results.json', flush=True)
print('curve', {k: curve_um[k] for k in cmp_ks}, flush=True)
for t in topics:
    print(t['id'], t['size'], '%.3f' % t['share'], [w for w, _ in t['words'][:7]], flush=True)
