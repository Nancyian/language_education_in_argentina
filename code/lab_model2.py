# -*- coding: utf-8 -*-
"""在上一轮 K=9 结果基础上补算 UMass 一致性曲线（K=2..20），并计算极性得分与各汇总矩阵。
K=9 的主题划分、词表、份额完全沿用 work/topic_results.json，保证与既有报告一致。
"""
import openpyxl, json, io, math, random, re, collections
import numpy as np

random.seed(7); np.random.seed(7)
SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx'
OLD = json.load(io.open('work/topic_results.json', encoding='utf-8'))

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

ws = openpyxl.load_workbook(SRC, data_only=True)['Sheet2']
docs, meta, raw_text = [], [], []
for r in range(2, ws.max_row + 1):
    title = str(ws.cell(r, 4).value or '').strip()
    ab = str(ws.cell(r, 9).value or '').strip()
    toks = tokenize((title + '. ') * 2 + ab)
    docs.append(toks); raw_text.append(title + '. ' + ab)
    meta.append({'no': ws.cell(r, 1).value, 'title': title,
                 'venue': str(ws.cell(r, 5).value or ''),
                 'year': int(str(ws.cell(r, 7).value or 0)[:4] or 0)})
N = len(docs)
VOC = OLD['vocab']; V = len(VOC)
v2i = {w: i for i, w in enumerate(VOC)}
D = [[v2i[w] for w in d if w in v2i] for d in docs]
assert N == 66, N

# 文档顺序必须与旧结果对齐
for i, d in enumerate(OLD['docs']):
    assert d['no'] == meta[i]['no'], (i, d['no'], meta[i]['no'])
print('aligned', N, 'docs', flush=True)

# ---- UMass ----
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

curve = {int(k): v for k, v in OLD['coherence_curve'].items()}
for K in range(2, 21):
    if K in curve: continue
    th, ph = lda(K)
    curve[K] = round(umass(ph), 4)
    print('K=%2d umass=%.4f' % (K, curve[K]), flush=True)

theta = np.array([[d['theta'][k] for k in range(9)] for d in OLD['docs']])
print('curve', dict(sorted(curve.items())), flush=True)
print('best', max(curve, key=curve.get), flush=True)

# ---- 极性 ----
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
    pos = sum(t.count(r) for r in POS); neg = sum(t.count(r) for r in NEG)
    if pos + neg == 0: return 0.0, pos, neg
    return (pos - neg) / (pos + neg), pos, neg

pol = [polarity(x) for x in raw_text]
hit = sum(1 for p in pol if p[1] + p[2] > 0)
print('polarity hits', hit, '/', N, flush=True)

years = sorted(set(m['year'] for m in meta))
year_theta = {}; year_pol = {}
for y in years:
    idx = [i for i, m in enumerate(meta) if m['year'] == y]
    w = theta[idx]; year_theta[y] = [float(x) for x in w.mean(0)]
    s = np.array([pol[i][0] for i in idx]); iv = w.sum(0)
    year_pol[y] = [float((w[:, k] * s).sum() / iv[k]) if iv[k] > 0 else 0.0 for k in range(9)]

ven_cnt = collections.Counter(m['venue'] for m in meta)
big = [v for v, c in ven_cnt.most_common() if c >= 3]
small = [v for v, c in ven_cnt.most_common() if c < 3]
groups = {v: [i for i, m in enumerate(meta) if m['venue'] == v] for v in big}
groups['其他期刊（%d 种）' % len(small)] = [i for i, m in enumerate(meta) if m['venue'] in small]

docrows = []
for i, d in enumerate(OLD['docs']):
    docrows.append(dict(d, pol=round(pol[i][0], 3), pos=pol[i][1], neg=pol[i][2]))

out = {
 'N': N, 'K': 9, 'vocab_size': V,
 'coherence_curve': dict(sorted(curve.items())),
 'best_k': max(curve, key=curve.get),
 'phi': OLD['phi'], 'vocab': VOC,
 'topics': OLD['topics'], 'edges': OLD['edges'],
 'years': years,
 'year_theta': {str(y): [round(x, 4) for x in year_theta[y]] for y in years},
 'year_pol': {str(y): [round(x, 4) for x in year_pol[y]] for y in years},
 'docs': docrows,
 'polarity_hit': hit,
 'pos_roots': POS, 'neg_roots': NEG,
 'venue_groups': groups,
}
json.dump(out, io.open('work/lab_results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved', flush=True)
print('groups', [(k[:26], len(v)) for k, v in groups.items()], flush=True)
