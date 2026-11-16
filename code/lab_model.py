# -*- coding: utf-8 -*-
"""专家话语 66 篇：LDA 多 K 扫描 + 一致性 + 主题-年份矩阵 + 极性得分
输出 work/lab_results.json，供绘图脚本使用。
口径与上一轮报告完全一致：同一语料、同一分词、seed=7、K=9 为选定主题数。
"""
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
propone objetivo objetivos resultado resultados conclusion conclusiones metodologia partir
presente caso casos manera forma parte veces mundo siglo xix xx xxi
issn doi rahl anclajes traslaciones signo sena quimu quimun gramma pilquen argonautas
masquedos entramados conocimento integracion cuadernos ciencias comportamiento
universidad nacional paper research study results using used
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
    meta.append({'no': ws.cell(r, 1).value, 'title': title,
                 'venue': str(ws.cell(r, 5).value or ''),
                 'authors': str(ws.cell(r, 6).value or ''),
                 'year': int(str(ws.cell(r, 7).value or 0)[:4] or 0),
                 'kw': str(ws.cell(r, 3).value or '')})
N = len(docs)

df = collections.Counter()
for d in docs: df.update(set(d))
VOC = sorted([w for w, c in df.items() if c >= 2 and c <= 0.55 * N])
v2i = {w: i for i, w in enumerate(VOC)}
V = len(VOC)
D = [[v2i[w] for w in d if w in v2i] for d in docs]
print('docs', N, 'vocab', V, 'tokens', sum(len(d) for d in D), flush=True)

# ---------- coherent 统计（词对共现，窗口 10）----------
win = 10
pair_w = collections.Counter(); uni = collections.Counter(); total = 0
for d in D:
    for i, w in enumerate(d):
        uni[w] += 1; total += 1
        for j in range(i + 1, min(i + win, len(d))):
            a, b = w, d[j]
            pair_w[(min(a, b), max(a, b))] += 1
NPAIR = sum(pair_w.values())

def npmi_coherence(phi, topn=10):
    sc = []
    for k in range(phi.shape[0]):
        top = list(np.argsort(-phi[k])[:topn])
        vals = []
        for i in range(1, len(top)):
            for j in range(i):
                a, b = min(top[i], top[j]), max(top[i], top[j])
                pab = pair_w.get((a, b), 0) / NPAIR if NPAIR else 0
                if pab <= 0: continue
                pa = uni[a] / total; pb = uni[b] / total
                pmi = math.log(pab / (pa * pb))
                vals.append(pmi / (-math.log(pab)))
        if vals: sc.append(float(np.mean(vals)))
    return float(np.mean(sc)) if sc else 0.0

# ---------- Gibbs ----------
def lda(K, iters=200):
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
    theta = ndk + alpha; theta = theta / theta.sum(1, keepdims=True)
    phi = nkw + beta; phi = phi / phi.sum(1, keepdims=True)
    return theta, phi

Ks = list(range(2, 21))
curve_npmi, curve_umass, store = {}, {}, {}
for K in Ks:
    th, ph = lda(K)
    c1 = npmi_coherence(ph); c2 = None
    curve_npmi[K] = round(c1, 4)
    store[K] = (th, ph)
    print('K=%2d npmi=%.4f' % (K, c1), flush=True)

best_npmi = max(curve_npmi, key=curve_npmi.get)
print('best by npmi:', best_npmi, curve_npmi[best_npmi], flush=True)

K = 9  # 选定主题数，与上一轮报告一致
theta, phi = store[K]

# ---------- 主题词 ----------
def top_words(k, n=14):
    return [(VOC[i], round(float(phi[k, i]), 5)) for i in np.argsort(-phi[k])[:n]]

topics = [{'id': k + 1, 'words': top_words(k),
           'share': float(theta[:, k].mean()),
           'size': int((theta.argmax(1) == k).sum())} for k in range(K)]

# ---------- 极性（词典法，词表随结果一同输出，保证可复现）----------
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
    return (pos - neg) / (pos + neg), pos, neg

pol = [polarity(x) for x in raw_text]
print('polarity hit rate', sum(1 for p in pol if p[1] + p[2] > 0), '/', N, flush=True)

# ---------- 年份 × 主题 ----------
years = sorted(set(m['year'] for m in meta))
year_theta = {y: theta[[i for i, m in enumerate(meta) if m['year'] == y]].mean(0) for y in years}
year_pol = {}
for y in years:
    idx = [i for i, m in enumerate(meta) if m['year'] == y]
    w = theta[idx]                      # 文档 × 主题
    s = np.array([pol[i][0] for i in idx])
    iv = w.sum(0)
    year_pol[y] = [float((w[:, k] * s).sum() / iv[k]) if iv[k] > 0 else 0.0 for k in range(K)]

# ---------- 期刊分组 ----------
ven_cnt = collections.Counter(m['venue'] for m in meta)
big = [v for v, c in ven_cnt.most_common() if c >= 3]
small = [v for v, c in ven_cnt.most_common() if c < 3]
groups = {v: [i for i, m in enumerate(meta) if m['venue'] == v] for v in big}
groups['其他期刊（%d 种，各 1–2 篇）' % len(small)] = [i for i, m in enumerate(meta) if m['venue'] in small]
print('venue groups', [(k[:28], len(v)) for k, v in groups.items()], flush=True)

# ---------- 主题网络 --------
topsets = [set(VOC[i] for i in np.argsort(-phi[k])[:20]) for k in range(K)]
edges = []
for a in range(K):
    for b in range(a + 1, K):
        sh = topsets[a] & topsets[b]
        if sh: edges.append({'a': a + 1, 'b': b + 1, 'w': len(sh), 'shared': sorted(sh)[:5]})

docrows = [{'no': m['no'], 'title': m['title'], 'year': m['year'], 'venue': m['venue'],
            'topic': int(theta[i].argmax()) + 1, 'p': round(float(theta[i].max()), 3),
            'theta': [round(float(x), 4) for x in theta[i]],
            'pol': round(pol[i][0], 3), 'pos': pol[i][1], 'neg': pol[i][2],
            'cnt': [len([1 for x in docs[i] if x])]} for i, m in enumerate(meta)]

out = {
    'N': N, 'K': K, 'vocab_size': V,
    'coherence_curve': curve_npmi, 'best_k_npmi': best_npmi,
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
    'venue_year_pol': {k: {
        str(y): [round(float((theta[[i for i in idx if meta[i]['year'] == y]][:, t]
                              * np.array([pol[i][0] for i in idx if meta[i]['year'] == y])).mean()
                          if [i for i in idx if meta[i]['year'] == y] else 0.0), 3)
        for t in range(K)] for y in years if [i for i in idx if meta[i]['year'] == y]}
        for k, idx in groups.items()},
}
json.dump(out, io.open('work/lab_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved work/lab_results.json', flush=True)
print('curve', curve_npmi, flush=True)
for t in topics:
    print(t['id'], t['size'], '%.3f' % t['share'], [w for w, _ in t['words'][:7]], flush=True)
