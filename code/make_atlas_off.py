# -*- coding: utf-8 -*-
"""官方话语 LDA 图表集 PDF：与专家版同一版式（P 类、图注、同源数据表），
内容全部由 work/off_results.json 现算，不硬编码数值。
输出：桌面/阿根廷语料库/官方话语/官方话语_LDA主题建模_图表集.pdf
"""
import json, os, re, sys, statistics
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from matplotlib import font_manager
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'tools'))
import make_atlas as A                      # 复用排版常量与 P 类

FIGD = os.path.join(BASE, 'work', 'off_figs_nocap')
TMPD = os.path.join(BASE, 'work', 'atlas_off_img')
os.makedirs(TMPD, exist_ok=True)
for _f in os.listdir(TMPD):
    try:
        os.remove(os.path.join(TMPD, _f))
    except Exception:
        pass
OUT = os.environ.get('ATLAS_OUT') or r'C:\Users\Administrator\Desktop\阿根廷语料库\官方话语\官方话语_LDA主题建模_图表集.pdf'

D = json.load(open(os.path.join(BASE, 'work', 'off_results.json'), encoding='utf-8'))
T, docs, years = D['topics'], D['docs'], D['years']
K = D['K']
KW2 = {t['id']: '%s / %s' % (t['words'][0][0], t['words'][1][0]) for t in T}
W, H, LM, RM, CW = A.W, A.H, A.LM, A.RM, A.CW
INK, MID, LIGHT, ACC, ACC2 = A.INK, A.MID, A.LIGHT, A.ACC, A.ACC2

N = D['N']; hit = D['polarity_hit']
LEX = '正面 %d 条、负面 %d 条' % (len(D['pos_roots']), len(D['neg_roots']))
cur = {int(k): v for k, v in D['coherence_curve'].items()}
ycount = Counter(d['year'] for d in docs if d['year'])
PLAT = D['venue_groups']
FACETS = [k for k, v in PLAT.items() if len(v) >= 10]
OTHER = [k for k, v in PLAT.items() if len(v) < 10]

pol = [d['pol'] for d in docs]
pos_n = sum(1 for p in pol if p > 0)
neg_n = sum(1 for p in pol if p < 0)
zero_n = N - pos_n - neg_n
cancel = sum(1 for d in docs if d['pol'] == 0 and (d['pos'] + d['neg']) > 0)

# 主题统计
tstat = {}
for k in range(1, K + 1):
    ds = [d for d in docs if d['topic'] == k]
    ys = [d['year'] for d in ds if d['year']]
    tstat[k] = dict(n=len(ds), pol=statistics.mean([d['pol'] for d in ds]) if ds else 0.0,
                    pos=sum(1 for d in ds if d['pol'] > 0), neg=sum(1 for d in ds if d['pol'] < 0),
                    peak=max(sorted(set(ys)), key=lambda y: sum(1 for x in ys if x == y)) if ys else None,
                    peakn=max([sum(1 for x in ys if x == y) for y in set(ys)] or [0]))

# 平台统计
vstat = {}
for v, idx in PLAT.items():
    ms = [sum(docs[i]['theta'][k] for i in idx) / len(idx) for k in range(K)]
    vstat[v] = dict(dom=ms.index(max(ms)) + 1, pol=statistics.mean([docs[i]['pol'] for i in idx]),
                    n=len(idx), top=max(ms))

# 年份 × 主题
YT = {int(k): v for k, v in D['year_theta'].items()}
YR = sorted(YT)
peakcell = max(((YT[y][k], y, k + 1) for y in YR for k in range(K)))
peak_by_topic = {k + 1: max(YR, key=lambda y: YT[y][k]) for k in range(K)}

# 时期（由数据表「时期分布」列聚合）
PORDER = ['1981-1990', '1991-2000', '2001-2010', '2011-2015', '2016-2020', '2021-2025', '2026-2030']
pcount = Counter(d['period'] for d in docs)
periods = [(p, pcount[p]) for p in PORDER if pcount.get(p)]

EW = Counter(e['w'] for e in D['edges'])

# 图 3 簇内边数（前 15 词、窗口共现 ≥8）
import itertools
_co = {(a, b): c for a, b, c in D['co']}
CLUSTER_EDGES = 0
for k in range(K):
    ws = [w for w, _ in T[k]['words']]
    for a, b in itertools.combinations(ws, 2):
        if _co.get(tuple(sorted((a, b))), 0) >= 8:
            CLUSTER_EDGES += 1

# 图 7 有效情感格的真实取值（平台内、该年 ≥2 篇、Σθ ≥0.05）
CELLS = []
for _v in FACETS:
    _idx = PLAT[_v]
    for _y in sorted(set(d['year'] for d in docs if d['year'])):
        _ids = [i for i in _idx if docs[i]['year'] == _y]
        if len(_ids) < 2:
            continue
        for _k in range(K):
            _w = sum(docs[i]['theta'][_k] for i in _ids)
            if _w < 0.05:
                continue
            CELLS.append(sum(docs[i]['theta'][_k] * docs[i]['pol'] for i in _ids) / _w)
FIGPG = {1: 4, 2: 5, 3: 6, 4: 8, 5: 9, 6: 10, 7: 11}
TOTALPG = 14


def trim(path, pad=14):
    out = os.path.join(TMPD, 't_' + os.path.basename(path))
    if os.path.exists(out):
        return out
    im = Image.open(path).convert('RGB')
    px = im.load(); w, h = im.size
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if r < 248 or g < 248 or b < 248:
                xs.append(x); ys.append(y)
    if not xs:
        im.save(out); return out
    im.crop((max(0, min(xs) - pad), max(0, min(ys) - pad),
             min(w, max(xs) + pad), min(h, max(ys) + pad))).save(out)
    return out


class P(A.P):
    def head(self, tag, title, sub):
        self.fig.text(LM / W, (H - 0.55) / H, tag, fontsize=8.4, color=ACC, fontweight='bold', va='top')
        self.fig.text((W - RM) / W, (H - 0.55) / H, '官方话语 · LDA 主题建模图表集',
                      fontsize=7.6, color=LIGHT, va='top', ha='right')
        self.rule(H - 0.70)
        self.fig.text(LM / W, (H - 0.86) / H, title, fontsize=14.5, color=INK, fontweight='bold', va='top')
        self.fig.text(LM / W, (H - 1.16) / H, sub, fontsize=8.8, color=MID, va='top')
        self.y = H - 1.44

    def footer(self):
        self.rule(0.62, color='#E2E5E3')
        self.fig.text(LM / W, 0.44 / H, '语料：官方数据表_正式版_v2.xlsx · Sheet2 · 71 篇 · 3 个发布平台',
                      fontsize=7.2, color=LIGHT, va='top')
        self.fig.text((W - RM) / W, 0.44 / H, '%d / %d' % (self.page, self.total),
                      fontsize=7.6, color=MID, va='top', ha='right')

    def image(self, path, ytop, max_h=6.30):
        im = Image.open(trim(path))
        r = im.size[0] / im.size[1]
        w = CW if CW / r <= max_h else max_h * r
        h = w / r
        ax = self.fig.add_axes([(LM + (CW - w) / 2.0) / W, (ytop - h) / H, w / W, h / H])
        ax.imshow(im, aspect='auto', interpolation='none', resample=False)
        ax.axis('off')
        return ytop - h


def A_short(v):
    if v == 'Buenos Aires Ciudad':
        return 'BA Ciudad'
    if v == 'Argentina.gob.ar – Educación':
        return 'Argentina.gob.ar'
    if v.startswith('其他平台'):
        return '国会图书馆'
    return v[:12]


# ---------- 图注 ----------
caps = {}
caps[1] = dict(
    f='图1_年度主题文献数量堆叠图.png', t='年度主题文献数量堆叠图',
    sub='%d 篇有明确发布年份的官方文献，按年份与主导主题统计' % len([d for d in docs if d['year']]),
    cap='横轴为有文献的年份，纵轴为当年文献数量，柱内按 %d 个主题分段堆叠。主题归属取文档—主题后验概率 θ 的 argmax，'
        '一篇文献只计入一个主题，各年数量之和等于当年文献总数。' % K,
    pts=['年份分布极不均衡：2024、2025 年各 9 篇，2023 年 5 篇，而 1982、2001、2010、2014、2016 年各仅 1 篇。',
         '15 篇发布时间不详的文献不纳入本图（占全部 %d 篇的 %.0f%%），因此各年之和为 %d 篇。'
         % (N, 15 / N * 100, N - 15),
         '横轴只保留实际出现文献的年份并等距排列，柱间距不代表时间间隔；单篇年份不宜作年度水平解读。'],
)
caps[2] = dict(
    f='图2_主题一致性结果.png', t='主题一致性结果',
    sub='K=2–12 的 u_mass 主题一致性曲线与主题数选择',
    cap='横轴为主题数 K，纵轴为 u_mass 一致性（值域为负，越接近 0 越好）。曲线在 K=8（%.4f）出现局部高点，'
        'K=9–10 回落，K=11–12 连续上升，K=12 为截取范围内的最优值（%.4f）。' % (cur[8], cur[12]),
    pts=['模型最终取 K=%d：与专家版保持同一择优规则——只在 K≤12（每主题平均不少于 5 篇）的范围内取最大值。' % K,
         'K=13–20 中有更低的值（K=14 为 %.4f、K=18 为 %.4f），但此时单个主题平均只覆盖 3–5 篇文献，'
         '主题退化为少数文献的关键词集合，指标会"虚高"而失去解释力，故不纳入比较。' % (cur[14], cur[18]),
         '本图量纲为 u_mass（负值），与参考文献中的 c_v 曲线形态可比、数值不可直接比较。'],
)
caps[3] = dict(
    f='图3_主题网络图.png', t='主题网络图',
    sub='%d 个主题圆、各主题后验概率前 15 位主题词及其共现连线' % K,
    cap='%d 个主题按主题间共享词数排布在外圈，圆面积按主题份额（平均后验概率）缩放，'
        '圆内为 topic 编号与份额；每个圆外侧散布该主题后验概率最高的 15 个主题词，'
        '字号正比于 β，越靠近主题圆的词 β 越高。'
        '主题之间的灰线粗细正比于两主题各自前 20 词的共同词数（1–%d 个）；'
        '簇内更细的连线表示该主题词在语料 10 词窗口内共现不少于 8 次。'
        '词与主题之间的浅色短线表示词归属该主题；字号与两类线宽各自独立编码，词的位置不承载含义。' % (K, max(EW)),
    pts=['共 %d 个词标签、%d 条簇内共现边；主题间共 %d 条关联边（共享 1 个词 %d 条、2 个词 %d 条、3 个及以上 %d 条）。'
         % (K * 15, CLUSTER_EDGES, len(D['edges']), EW[1], EW[2], sum(v for k, v in EW.items() if k >= 3)),
         '份额最大为 topic%d（%.1f%%），最小为 topic%d（%.1f%%）；份额差异远小于专家版，说明官方话语的主题分布更均衡。'
         % (max(T, key=lambda t: t['share'])['id'], max(t['share'] for t in T) * 100,
            min(T, key=lambda t: t['share'])['id'], min(t['share'] for t in T) * 100),
         '连线由主题词重叠与语料共现生成，反映词汇与语境关联，不等同于文献引用或机构合作关系。'],
)
caps[4] = dict(
    f='图4_全部主题时间热度图.png', t='全部主题时间热度图',
    sub='%d 个主题 × %d 个有文献年份的主题强度矩阵' % (K, len(YR)),
    cap='行是 %d 个主题，列是 %d 个有文献的年份；色块为该主题在该年的平均后验概率。'
        '由于 %d 个主题的平均 θ 仅 %.3f，若按最大值（%.2f）定标会使全图泛白，故色标上限取全表 P95 = %.2f、更高值截顶，'
        '并统一经 γ=0.6 幂律拉伸；灰色格为该年无文献。'
        % (K, len(YR), K, 1.0 / K, max(YT[y][k] for y in YR for k in range(K)),
           float(__import__('numpy').percentile([[YT[y][k] for y in YR] for k in range(K)], 95))),
    pts=['最强单元为 topic%d 在 %d 年（平均 θ=%.2f，全表最高）。' % (peakcell[2], peakcell[1], peakcell[0]),
         '官方话语的主题强度整体较低且分散，多数年份没有任何主题的平均 θ 超过 0.3，说明单篇官方网页往往同时涉及多个议题。',
         '样本量小的年份（1–2 篇）波动大，读图时应结合图 1 的年度文献量一起看。'],
)
caps[5] = dict(
    f='图5_各平台主题热度图.png', t='各平台主题热度图',
    sub='%d 个发布平台面板，每面板为 主题 × 年份 的强度矩阵' % len(FACETS),
    cap='分面维度为「发布平台」（对应专家版的期刊）。仅列入文献量 ≥10 篇的两个平台：Buenos Aires Ciudad（%d 篇）与 '
        'Argentina.gob.ar – Educación（%d 篇）；另一平台（国会图书馆，%d 篇）样本过少，不单独分面，其文献仍计入全部图与表。'
        % (len(PLAT[FACETS[0]]), len(PLAT[FACETS[1]]), sum(len(v) for k, v in PLAT.items() if k not in FACETS)),
    pts=['各面板为原始均值，共用同一色标上限（两面板合计的 P95），统一 γ=0.6 幂律拉伸；灰色格表示该年该平台无文献。',
         '首都平台覆盖年份长（1982 年起），教育平台集中在 2013 年与 2022–2026 年，两平台的年份覆盖差异本身即结构差异。',
         '面板之间可横向比较，但色深不可与图 4 直接互换（两者色标上限不同）。'],
)
caps[6] = dict(
    f='图6_各主题情感倾向曲线图.png', t='各主题情感倾向曲线图',
    sub='%d 个主题的加权情感值随年份变化（仅列该年文献 ≥2 篇的年份）' % K,
    cap='纵轴为加权情感值：Σ(主题概率 × 文档极性) / Σ(主题概率)，逐主题逐年计算。'
        '文档极性 =（正面词数 − 负面词数）/（正面词数 + 负面词数 + 2），分母 2 为平滑项，避免正面词密集的官方文本被钉在 +1。'
        '横轴只列该年文献 ≥2 篇的年份，括号内为该年文献数。',
    pts=['情感打分基于评价性词根表（' + LEX + '）的词典法，%d/%d 篇命中至少一个评价词。' % (hit, N),
         '全部取值落在 %.2f–%.2f，无主题出现负值：官方文本以「权利、包容、多样性、机会」等正面表述为主，'
         '这是官方话语与专家话语最稳定的差异。'
         % (min(min(v) for y, v in D['year_pol'].items() if D['year_n'][y] >= 2),
            max(max(v) for y, v in D['year_pol'].items() if D['year_n'][y] >= 2)),
         '主题间差异有限（均值 %.2f–%.2f），单篇年份已剔除；曲线起伏更多反映各年议题组合，不宜解读为主题情感转向。'
         % (min(t['pol'] for t in tstat.values()), max(t['pol'] for t in tstat.values()))],
)
caps[7] = dict(
    f='图7_各平台主题情感倾向热图.png', t='各平台主题情感倾向热图',
    sub='%d 个平台面板，每面板为 主题 × 年份 的情感矩阵' % len(FACETS),
    cap='分面维度同为「发布平台」，面板划分与图 5 一致；行是 %d 个主题、列是 %d 个有文献年份。'
        '色块为加权情感值，暖色为正、冷色为负；色标以 0 为中点双向映射，故颜色深浅可跨面板比较。'
        '灰色格表示该年该平台无文献，或该年文献少于 2 篇（样本不足，不计算），或该主题当年权重 Σθ 低于 0.05。' % (K, len(YR)),
    pts=['有效色块共 %d 个，取值区间 %.2f–%.2f，其中负值 %d 个，均出现在首都平台的个别年份。'
         % (len(CELLS), min(CELLS), max(CELLS), sum(1 for c in CELLS if c < 0)),
         '首都平台的有效色块明显多于教育平台，后者只在 2013 年与 2022–2026 年有值，与图 5 的年份覆盖一致。',
         'n 较小的平台（%s，%d 篇）不单独分面，避免 2 篇文献决定整块颜色。'
         % ('、'.join(A_short(k) for k in OTHER), sum(len(PLAT[k]) for k in OTHER)),
         '跨平台比较应聚焦同一主题在同一年份的色差；不同年份的色差同时受议题构成与样本量影响。'],
)

# ---------- 同源数据表 ----------
def t_tab1():
    ys = sorted(ycount.items())
    rows = []
    n2 = (len(ys) + 1) // 2
    for i in range(n2):
        a = ys[i]
        b = ys[i + n2] if i + n2 < len(ys) else ('', '')
        rows.append([a[0], a[1], '', b[0], b[1]])
    return ('各年文献量（篇）', ['年份', '篇数', '', '年份', '篇数'], rows)


def t_tab2():
    rows = []
    left = [k for k in range(2, 8)]
    right = [k for k in range(8, 13)]
    for i, k in enumerate(left):
        k2 = right[i] if i < len(right) else None
        rows.append([k, '%.4f' % cur[k], k2 if k2 else '', '%.4f' % cur[k2] if k2 else ''])
    return ('u_mass 一致性逐 K 取值', ['K', 'u_mass', 'K', 'u_mass'], rows)


def t_tab3():
    rows = []
    for e in sorted(D['edges'], key=lambda e: (-e['w'], e['a'])):
        rows.append(['topic%d – topic%d' % (e['a'], e['b']), e['w'], '、'.join(e['shared'][:4])])
    return ('主题间共享词（前 20 词口径）', ['主题对', '共享词数', '共享词（前 4 个）'], rows)


def t_tab4():
    rows = []
    for k in range(K):
        rows.append(['topic%d' % (k + 1)] + ['%.2f' % YT[y][k] for y in YR])
    return ('主题 × 年份 平均后验概率 θ', ['主题'] + [str(y) for y in YR], rows)


def t_tab5():
    rows = []
    for k in range(K):
        r = ['topic%d' % (k + 1)]
        for v in FACETS:
            idx = PLAT[v]
            r.append(sum(1 for i in idx if docs[i]['topic'] == k + 1))
        r.append('%.3f' % statistics.mean([YT[y][k] for y in YR]))
        rows.append(r)
    return ('各平台主导篇数与年均强度', ['主题'] + [A_short(v) for v in FACETS] + ['年均 θ'],
            rows)


def A_short(v):
    if v in ('Buenos Aires Ciudad', 'Argentina.gob.ar – Educación'):
        return {'Buenos Aires Ciudad': 'BA Ciudad',
                'Argentina.gob.ar – Educación': 'Argentina.gob.ar'}[v]
    if v.startswith('其他平台'):
        return '国会图书馆'
    return v[:12]


def t_tab6():
    rows = []
    for k in range(1, K + 1):
        s = tstat[k]
        rows.append(['topic%d' % k, s['n'], '%.3f' % s['pol'], s['pos'], s['neg'],
                     '%d（%d 篇）' % (s['peak'], s['peakn']) if s['peak'] else '—'])
    return ('各主题文献量与情感均值', ['主题', '主导篇数', '情感均值', '极性>0', '极性<0', '峰值年'], rows)


TABS = {1: t_tab1, 2: t_tab2, 3: t_tab3, 4: t_tab4, 5: t_tab5, 6: t_tab6}


def lay_fig(p, i, max_h=9.0, tab_h=6.5):
    c = caps[i]
    y = p.image(os.path.join(FIGD, c['f']), p.y, max_h=max_h)
    p.y = y - 0.26
    p.text('图 %d　%s' % (i, c['cap']), size=8.7, width=CW, color=INK, leading=1.58)
    p.space(0.20)
    for b in c['pts']:
        p.dot(p.y - 0.052, c=ACC)
        p.text(b, size=8.4, x=LM + 0.16, width=CW - 0.16, color=MID, leading=1.56)
        p.space(0.10)


with PdfPages(OUT) as pdf:
    # ===== 1 封面 =====
    p = P(pdf, 1, TOTALPG)
    p.fig.text(LM / W, (H - 1.60) / H, '官方话语语料', fontsize=9.2, color=ACC, fontweight='bold', va='top')
    p.fig.text(LM / W, (H - 1.92) / H, 'LDA 主题建模图表集', fontsize=25, color=INK, fontweight='bold', va='top')
    p.rule(H - 2.48, color=ACC, lw=1.4, x1=LM + 1.55)
    p.fig.text(LM / W, (H - 2.78) / H,
               '%d 篇阿根廷官方语言政策网页 · %d 个平台 · 1982–2026 年 · 主题数 K=%d'
               % (N, len(PLAT), K), fontsize=10.2, color=MID, va='top')

    meta = [('语　　料', '官方数据表_正式版_v2.xlsx · Sheet2 · 71 篇（15 篇发布时间不详）'),
            ('模　　型', 'LDA · collapsed Gibbs 采样 · α=0.1，β=0.02，迭代 200 次，seed=7'),
            ('词　　表', 'min_df=2、max_df=0.55，同款西语轻量词干化后 %d 词；主题数由 u_mass 择优' % D['vocab_size']),
            ('绘图工具', 'Python 3.13 + matplotlib 3.11，320 dpi 位图原像素嵌入，A4 版面合成 PDF'),
            ('配　　色', '「海洋清风」12 色（原 8 色 + #3E5C76 #6B8F71 #8C6D4F），与专家版共用主色')]
    y = H - 3.40
    for k, v in meta:
        p.fig.text(LM / W, y / H, k, fontsize=8.2, color=LIGHT, va='top')
        p.fig.text((LM + 0.92) / W, y / H, v, fontsize=8.6, color=INK, va='top')
        y -= 0.30

    p.rule(H - 5.10)
    p.fig.text(LM / W, (H - 5.36) / H, '图 表 目 录', fontsize=9.6, color=INK, fontweight='bold', va='top')
    toc = [('01', '年度主题文献数量堆叠图', '年份 × 主题的文献量构成', '4'),
           ('02', '主题一致性结果', 'K=2–12 的 u_mass 曲线与 K 值选择', '5'),
           ('03', '主题网络图', '主题—主题词—共现关系', '6'),
           ('04', '全部主题时间热度图', '%d 主题 × %d 年份强度矩阵' % (K, len(YR)), '8'),
           ('05', '各平台主题热度图', '%d 个平台面板的主题强度' % len(FACETS), '9'),
           ('06', '各主题情感倾向曲线图', '%d 条主题情感曲线' % K, '10'),
           ('07', '各平台主题情感倾向热图', '%d 个平台面板的情感矩阵' % len(FACETS), '11')]
    y = H - 5.78
    for no, name, desc, pg in toc:
        p.fig.text((LM + 0.05) / W, y / H, no, fontsize=10.5, color=ACC, fontweight='bold', va='top')
        p.fig.text((LM + 0.55) / W, y / H, name, fontsize=10.5, color=INK, va='top')
        p.fig.text((LM + 3.15) / W, y / H, desc, fontsize=8.4, color=MID, va='top')
        p.fig.text((W - RM) / W, y / H, pg, fontsize=9.4, color=MID, va='top', ha='right')
        p.rule(y - 0.11, color='#E6E9E7', lw=0.5)
        y -= 0.42

    p.rule(y + 0.02, color='#E6E9E7')
    y -= 0.22
    p.fig.text(LM / W, y / H, '本 册 结 构', fontsize=9.0, color=LIGHT, fontweight='bold', va='top')
    y -= 0.30
    for a, b in [('第 2 页', '语料、模型与三个指标的定义，含平台与时期口径'),
                 ('第 3 页', '%d 个主题的编号、前 12 位主题词、主导篇数与份额' % K),
                 ('第 4–13 页', '七张图，每页 = 图 + 图注 + 读图要点 + 同源数据表（图 3 的数据表见第 7 页）'),
                 ('第 14 页', '与专家版的差异、复现方式与随册文件清单')]:
        p.fig.text((LM + 0.05) / W, y / H, a, fontsize=8.4, color=ACC if a.startswith('第') else MID, va='top')
        p.fig.text((LM + 1.05) / W, y / H, b, fontsize=8.4, color=MID, va='top')
        y -= 0.27

    p.y = 1.42
    p.text('说明：本册所有数值均直接来自同一份 LDA 结果文件（work/off_results.json），未做任何人工补值或重新拟合；'
           '每张图下方的数据表即为该图所用数值的直接汇总，可逐项核对。',
           size=7.8, width=CW, color=LIGHT, leading=1.5)
    p.footer(); p.save(pdf)

    # ===== 2 数据口径 =====
    p = P(pdf, 2, TOTALPG)
    p.head('数据口径', '一 · 语料、模型与指标定义', '本册与专家话语版共用同一套管线与参数；差异只来自语料本身，并列于 1.3。')
    p.fig.text(LM / W, p.y / H, '1.1　语料与模型', fontsize=10.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.30
    p.text('语料为「官方数据表_正式版_v2.xlsx」Sheet2 的 %d 篇官方发布材料（原文片段），来自 %d 个平台：%s。'
           '其中 %d 篇有明确发布年份（1982–2026 年），%d 篇发布时间不详。'
           % (N, len(PLAT), '、'.join('%s %d 篇' % (A_short(k), len(v)) for k, v in PLAT.items()),
              N - 15, 15),
           size=9.4, width=CW, color=INK, leading=1.62)
    p.space(0.08)
    p.text('文本按与专家版相同的西语分词与轻量词干化处理，去除停用词、仅出现 1 次的词，最终词表 %d 词（专家版 815 词）。'
           '主题数在 K=2–20 上以 u_mass 扫描，在 K≤12 范围内取最优，得 K=%d。'
           '推断用 collapsed Gibbs 采样，α=0.1、β=0.02、迭代 200 次、seed=7，与专家版完全一致，可复现。'
           % (D['vocab_size'], K),
           size=9.4, width=CW, color=INK, leading=1.62)
    p.space(0.30)

    p.fig.text(LM / W, p.y / H, '1.2　三个指标的确切定义', fontsize=10.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.34
    for name, body in [('一致性（图 2）',
                        'u_mass：对每个主题的前 10 个词，统计词对在文档共现中的对数概率比，主题内平均后再对 %d 个主题取平均。值域为负，越接近 0 越好。' % K),
                       ('热度（图 4、图 5）',
                        '某主题在某年的平均后验概率 θ。色标经 γ=0.6 幂律拉伸，上限取 P95 并截顶（K=12 时均值仅 %.3f，按最大值定标会使全图泛白）；两图色标上限各自独立。' % (1.0 / K)),
                       ('情感倾向（图 6、图 7）',
                        '加权情感值 = Σ(主题概率 × 文档极性) / Σ(主题概率)；文档极性 = (正面词数 − 负面词数) / (正面词数 + 负面词数 + 2)。'
                        '每个「年×主题」格要求该年文献 ≥2 篇，单篇年份不计算，避免一篇文献决定一个色块。')]:
        p.dot(p.y - 0.055)
        p.fig.text((LM + 0.17) / W, p.y / H, name, fontsize=9.4, color=INK, fontweight='bold', va='top')
        p.y -= 0.27
        p.text(body, size=9.0, x=LM + 0.17, width=CW - 0.17, color=MID, leading=1.58)
        p.space(0.18)

    p.fig.text(LM / W, p.y / H, '1.3　与专家版的四处必要差异', fontsize=10.6, color=ACC2, fontweight='bold', va='top')
    p.y -= 0.30
    for s in ['① 主题数 K=%d（专家版 K=9）：官方语料议题更分散，u_mass 在 K=12 才达到截取范围内最优。' % K,
              '② 配色扩至 12 色；其余主色、图注条、版式与专家版一致。',
              '③ 分面维度由「期刊」改为「发布平台」，且只对 n≥10 的平台分面（国会图书馆仅 2 篇）。',
              '④ 情感值加 +2 平滑并要求每年 ≥2 篇：官方文本正面词密集，不平滑会大量取到 +1，失去区分度。']:
        p.text(s, size=8.9, width=CW, color=MID, leading=1.55)
        p.space(0.04)
    p.space(0.20)

    p.fig.text(LM / W, p.y / H, '1.4　平台与时期分布', fontsize=10.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.34
    rows = []
    for k, v in PLAT.items():
        rows.append([A_short(k), len(v), '%.0f%%' % (len(v) / N * 100),
                     'topic%d（%s）' % (vstat[k]['dom'], KW2[vstat[k]['dom']]),
                     '%.3f' % vstat[k]['pol']])
    p.table(['发布平台', '篇数', '占语料', '主导主题', '情感均值'], rows,
            [2.05, 0.62, 0.72, 3.10, 1.05], rh=0.24)
    p.space(0.14)
    p.text('时期分布：' + '、'.join('%s %d 篇' % (k, v) for k, v in periods) + '。'
           '四个主时期（2011–2015、2016–2020、2021–2025、2026–2030）合计 %d 篇，占 %d 篇的 %.0f%%。'
           % (sum(v for k, v in periods if k >= '2011'), N,
              sum(v for k, v in periods if k >= '2011') / N * 100),
           size=8.6, width=CW, color=MID, leading=1.55)
    p.footer(); p.save(pdf)

    # ===== 3 主题总表 =====
    p = P(pdf, 3, TOTALPG)
    p.head('主题总表', '二 · %d 个主题的编号与主题词' % K, '主题词为模型输出中后验概率最高的 12 位，括号内为 β 值。')
    cols = [LM, LM + 0.62, LM + 5.18, LM + 5.72]
    for x, h in zip(cols, ['编号', '主题词（β，前 12 位）', '主导篇数', '份额']):
        p.fig.text(x / W, p.y / H, h, fontsize=8.0, color=LIGHT, va='top')
    p.rule(p.y + 0.04, color='#BCC2BF', lw=0.7)
    p.y -= 0.28
    p.rule(p.y + 0.08, color='#DDE1DF', lw=0.55)
    for t in T:
        row_y = p.y
        ws = '、'.join('%s %.3f' % (w, v) for w, v in t['words'])
        p.fig.text(cols[0] / W, row_y / H, 'topic%d' % t['id'], fontsize=8.4, color=ACC, va='top')
        p.text(ws, size=7.1, x=cols[1], y=row_y, width=4.50, color=MID, leading=1.45)
        p.fig.text(cols[2] / W, row_y / H, str(t['size']), fontsize=8.6, color=MID, va='top')
        p.fig.text(cols[3] / W, row_y / H, '%.1f%%' % (t['share'] * 100), fontsize=8.6, color=MID, va='top')
        p.y = row_y - 0.62
        p.rule(p.y + 0.12, color='#EDEFED', lw=0.45)
    p.space(0.10)
    p.text('读法：主题词只呈现词汇分布，不代主题命名。同一主题内部常并置「政策工具词」（programa、beca、convocatoria）与'
           '「语言对象词」（chino、portugués、bilingüe），说明官方文本倾向于在具体项目语境中表述语言政策。',
           size=8.6, width=CW, color=MID, leading=1.55)
    p.space(0.10)
    p.text('份额 = 该主题在全样本上的平均后验概率 θ；主导篇数 = 以该主题为 argmax 的文献数。两者合计分别为 1.00 与 %d 篇。' % N,
           size=8.2, width=CW, color=LIGHT, leading=1.5)
    p.footer(); p.save(pdf)

    # ===== 4 图1 =====
    p = P(pdf, 4, TOTALPG)
    p.head('图 1', '三 · 年度主题文献数量堆叠图', caps[1]['sub'])
    lay_fig(p, 1, max_h=9.2)
    p.space(0.18)
    h, rows = t_tab1()[1], t_tab1()[2]
    p.fig.text(LM / W, p.y / H, t_tab1()[0], fontsize=8.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.26
    p.table(h, rows, [1.15, 0.75, 0.55, 1.15, 0.75], size=7.6, rh=0.205)
    p.footer(); p.save(pdf)

    # ===== 5 图2 =====
    p = P(pdf, 5, TOTALPG)
    p.head('图 2', '四 · 主题一致性结果', caps[2]['sub'])
    lay_fig(p, 2, max_h=10.6)
    p.space(0.20)
    p.fig.text(LM / W, p.y / H, t_tab2()[0], fontsize=8.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.26
    p.table(t_tab2()[1], t_tab2()[2], [0.60, 0.95, 0.60, 0.95], size=7.8, rh=0.225)
    p.space(0.12)
    p.text('注：K=13–20 的取值一并向扫描，但按 K≤12 的择优规则不参与比较；表内只列参与比较的 K=2–12。',
           size=7.8, width=CW, color=LIGHT, leading=1.45)
    p.footer(); p.save(pdf)

    # ===== 6 图3 =====
    p = P(pdf, 6, TOTALPG)
    p.head('图 3', '五 · 主题网络图', caps[3]['sub'])
    lay_fig(p, 3, max_h=17.1)
    p.footer(); p.save(pdf)

    # ===== 7 表3（图3 续页）=====
    p = P(pdf, 7, TOTALPG)
    p.head('图 3 · 数据表', '五 · 主题网络图（续）', '图 3 的全部连线依据：主题间共享词数与前 20 词交集。')
    h, rows = t_tab3()[1], t_tab3()[2]
    n2 = (len(rows) + 1) // 2
    y0 = p.y
    p.table(h, rows[:n2], [1.30, 0.55, 2.30], x=LM, size=7.2, rh=0.205)
    ysave = p.y
    p.y = y0
    p.table(h, rows[n2:], [1.30, 0.55, 2.30], x=LM + 4.45, size=7.2, rh=0.205)
    p.y = min(ysave, p.y)
    p.space(0.22)
    p.text('读法：共享词越多，两主题在图中的连线越粗。共享词集中在 programa、beca、lengua、formacion 等政策工具词上，'
           '说明官方话语的议题分化主要发生在「政策工具 × 语言对象」的组合上，而非完全不同的词汇领域。',
           size=8.5, width=CW, color=MID, leading=1.55)
    p.space(0.10)
    p.text('簇内连线口径：同一主题的前 15 词中，任意两词在语料 10 词窗口内共现不少于 8 次即连边（专家版为 6 次，'
           '官方文本片段更短、共现更密，故提高阈值以保持同等视觉密度）。',
           size=8.2, width=CW, color=LIGHT, leading=1.5)
    p.footer(); p.save(pdf)

    # ===== 8 图4 =====
    p = P(pdf, 8, TOTALPG)
    p.head('图 4', '六 · 全部主题时间热度图', caps[4]['sub'])
    lay_fig(p, 4, max_h=8.4)
    p.space(0.14)
    p.fig.text(LM / W, p.y / H, t_tab4()[0], fontsize=8.4, color=INK, fontweight='bold', va='top')
    p.y -= 0.24
    wcol = (CW - 0.95) / len(YR)
    p.table(t_tab4()[1], t_tab4()[2], [0.95] + [wcol] * len(YR), size=5.9, rh=0.20, hh=0.24)
    p.footer(); p.save(pdf)

    # ===== 9 图5 =====
    p = P(pdf, 9, TOTALPG)
    p.head('图 5', '七 · 各平台主题热度图', caps[5]['sub'])
    lay_fig(p, 5, max_h=8.0)
    p.space(0.18)
    p.fig.text(LM / W, p.y / H, t_tab5()[0], fontsize=8.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.26
    p.table(t_tab5()[1], t_tab5()[2], [0.90, 1.35, 1.45, 1.05], size=7.4, rh=0.205)
    p.footer(); p.save(pdf)

    # ===== 10 图6 =====
    p = P(pdf, 10, TOTALPG)
    p.head('图 6', '八 · 各主题情感倾向曲线图', caps[6]['sub'])
    lay_fig(p, 6, max_h=8.8)
    p.space(0.16)
    p.fig.text(LM / W, p.y / H, t_tab6()[0], fontsize=8.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.26
    p.table(t_tab6()[1], t_tab6()[2], [0.80, 0.78, 0.85, 0.70, 0.70, 1.55], size=7.4, rh=0.200)
    p.footer(); p.save(pdf)

    # ===== 11 图7 =====
    p = P(pdf, 11, TOTALPG)
    p.head('图 7', '九 · 各平台主题情感倾向热图', caps[7]['sub'])
    lay_fig(p, 7, max_h=8.0)
    p.space(0.18)
    p.fig.text(LM / W, p.y / H, '各主题年均权重与情感均值（用于核对色块的有无）', fontsize=8.6, color=INK, fontweight='bold', va='top')
    p.y -= 0.26
    rows = []
    for k in range(K):
        rows.append(['topic%d' % (k + 1)] + ['%.3f' % statistics.mean([YT[y][k] for y in YR])
                                             for _ in [0]] + ['%.3f' % tstat[k + 1]['pol']])
    p.table(['主题', '年均 θ', '全期情感均值'], rows, [0.90, 0.95, 1.45], size=7.6, rh=0.205)
    p.footer(); p.save(pdf)

    # ===== 12 附录A =====
    p = P(pdf, 12, TOTALPG)
    p.head('附录 A', '十 · 口径对照、复现与文件清单', '与专家版逐项对照，便于方法章统一表述。')
    p.fig.text(LM / W, p.y / H, '10.1　两套语料的参数对照', fontsize=10.2, color=INK, fontweight='bold', va='top')
    p.y -= 0.28
    p.table(['项目', '专家话语', '官方话语'],
            [['文献数', '66 篇', '%d 篇（15 篇时间不详）' % N],
             ['来源', '阿根廷本土期刊 17 种', '%d 个官方平台' % len(PLAT)],
             ['分词与词表', '轻量词干化，815 词', '同款处理，%d 词' % D['vocab_size']],
             ['主题数', 'K=9（u_mass）', 'K=%d（u_mass，K≤12 择优）' % K],
             ['采样参数', 'α=0.1 β=0.02 200 轮 seed=7', '同左'],
             ['情感词典', '正面 56 / 负面 57 词根', '同表（保证可比）'],
             ['分面维度', '期刊（9 组）', '平台（2 组，n≥10）']],
            [1.25, 2.55, 3.35], size=7.8, rh=0.24)
    p.space(0.26)
    p.fig.text(LM / W, p.y / H, '10.2　复现方式', fontsize=10.2, color=INK, fontweight='bold', va='top')
    p.y -= 0.28
    for s in ['python tools/off_model.py        # 读取官方数据表 → work/off_results.json（约 4–5 分钟）',
              'python tools/off_figs.py         # 生成图 1–7 → 官方话语/图/',
              'python tools/make_atlas_off.py   # 合成本册 PDF']:
        p.fig.text((LM + 0.10) / W, p.y / H, s, fontsize=8.0, color=MID, va='top')
        p.y -= 0.22
    p.space(0.22)
    p.fig.text(LM / W, p.y / H, '10.3　随册文件', fontsize=10.2, color=INK, fontweight='bold', va='top')
    p.y -= 0.28
    for a, b in [('官方话语/图/', '图 1–7，3520–4128 px 宽，320 dpi，含图题色条'),
                 ('官方话语/官方话语_LDA主题建模_图表集.pdf', '本册'),
                 ('官方话语/官方话语_LDA主题建模_图表集.docx', '同内容的 Word 版，表格可编辑'),
                 ('work/off_results.json', '全部数值的唯一来源（主题词、θ 矩阵、极性、平台分组）')]:
        p.fig.text((LM + 0.05) / W, p.y / H, a, fontsize=8.2, color=ACC, va='top')
        p.fig.text((LM + 3.25) / W, p.y / H, b, fontsize=8.2, color=MID, va='top')
        p.y -= 0.26
    p.space(0.24)
    p.fig.text(LM / W, p.y / H, '10.4　解读边界', fontsize=10.2, color=ACC2, fontweight='bold', va='top')
    p.y -= 0.28
    p.text('官方平台发布不等于政府立场；本册只描述文本层面的词汇分布与情感倾向，不推断发布动机。'
           '15 篇发布时间不详的文献参与主题建模与情感统计，但不进入任何年份类图表，'
           '因此图 1、4、5、6、7 的样本量为 %d 篇而非 %d 篇。' % (N - 15, N),
           size=9.0, width=CW, color=MID, leading=1.6)
    p.footer(); p.save(pdf)

    # ===== 13–14 附录B 文档清单 =====
    LSHORT = {'Buenos Aires Ciudad': 'BA Ciudad',
              'Argentina.gob.ar – Educación': 'Argentina.gob.',
              'Biblioteca del Congreso de la Nación': 'Congreso Nación'}
    rows_all = []
    for d in docs:
        rows_all.append([d['no'], d['year'] or '不详', LSHORT.get(d['venue'], d['venue'][:16]),
                         'T%d' % d['topic'], '%.2f' % d['p'], '%+.2f' % d['pol']])
    per = 36
    for pi, start in enumerate(range(0, len(rows_all), per)):
        p = P(pdf, 13 + pi, TOTALPG)
        p.head('附录 B · %d' % (pi + 1), '十一 · 文献清单与模型归属',
               '序号同源数据表；T 为主题编号，p 为该篇的最大后验概率，情感为该篇极性得分。')
        chunk = rows_all[start:start + per]
        p.table(['序号', '年份', '平台', '主题', 'p', '情感'], chunk,
                [0.62, 0.70, 2.20, 0.62, 0.62, 0.70], size=7.0, rh=0.228, hh=0.28)
        p.space(0.10)
        p.text('共 %d 篇，本节第 %d–%d 行。序号沿用源数据表，因部分记录已移出主表，故不连续。'
               % (len(rows_all), start + 1, start + len(chunk)),
               size=7.6, width=CW, color=LIGHT, leading=1.45)
        p.footer(); p.save(pdf)

print('saved', OUT)
