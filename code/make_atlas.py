# -*- coding: utf-8 -*-
"""把七张图 + 图注 + 数据口径 + 同源数据表合成一个 PDF（A4 纵向，11 页）。"""
import json, os, re, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from matplotlib import font_manager
from PIL import Image
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGD = os.path.join(BASE, 'work', 'figs_nocap')
TMPD = os.path.join(BASE, 'work', 'atlas_img')
OUT  = os.environ.get('ATLAS_OUT') or r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\专家话语_LDA主题建模_图表集.pdf'
os.makedirs(TMPD, exist_ok=True)
D    = json.load(open(os.path.join(BASE, 'work', 'lab_results.json'), encoding='utf-8'))

CN = 'DejaVu Sans'
for f in ['Microsoft YaHei', 'SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False); CN = f; break
    except Exception:
        pass
matplotlib.rcParams['font.sans-serif'] = [CN, 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

W, H = 8.268, 11.693
LM, RM = 0.78, 0.78
CW = W - LM - RM
INK, MID, LIGHT = '#2C2C2A', '#55554F', '#9A9E9C'
ACC, ACC2 = '#3F8189', '#B0763F'

SHORT = {'RAHL: Revista argentina de historiografía lingüística': 'RAHL · 语言学史',
         'Traslaciones: Revista Latinoamericana de Lectura y Escritura': 'Traslaciones · 读写',
         'Signo y Seña': 'Signo y Seña', 'Quintú Quimün: revista de lingüística': 'Quintú Quimün',
         'Anclajes': 'Anclajes', 'Integración y Conocimiento': 'Integración y Conocimiento',
         'Signos ELE: Revista de Español como Lengua Extranjera': 'Signos ELE',
         'Argonautas': 'Argonautas', '其他期刊（9 种）': '其他期刊（9 种）'}

T, docs, years = D['topics'], D['docs'], D['years']
KW2 = {t['id']: '%s / %s' % (t['words'][0][0], t['words'][1][0]) for t in T}

def _pol_cells():
    vals = []
    for _idx in D['venue_groups'].values():
        for _y in D['years']:
            _ids = [i for i in _idx if D['docs'][i]['year'] == _y]
            if not _ids:
                continue
            for _k in range(D['K']):
                _w = sum(D['docs'][i]['theta'][_k] for i in _ids)
                if _w < 0.05:
                    continue
                vals.append(sum(D['docs'][i]['theta'][_k] * D['docs'][i]['pol'] for i in _ids) / _w)
    return min(vals), max(vals)


PRLO, PRHI = _pol_cells()
PRLO_S, PRHI_S = '%.2f' % abs(PRLO), '%.2f' % PRHI
N, hit = D['N'], D['polarity_hit']
LEX  = '正面 %d 条、负面 %d 条' % (len(D['pos_roots']), len(D['neg_roots']))

# ---------- 派生统计（全部由 lab_results.json 直接汇总） ----------
ycount = Counter(d['year'] for d in docs)
period = {'≤2013': 0, '2014-2018': 0, '2019-2022': 0, '2023-2026': 0}
PLABEL = {'≤2013': '1999–2013', '2014-2018': '2014–2018', '2019-2022': '2019–2022', '2023-2026': '2023–2026'}
for y, c in ycount.items():
    period['≤2013' if y <= 2013 else '2014-2018' if y <= 2018 else '2019-2022' if y <= 2022 else '2023-2026'] += c
pol = lambda ds: [d['pol'] for d in ds]
pos_n = sum(1 for d in docs if d['pol'] > 0)
neg_n = sum(1 for d in docs if d['pol'] < 0)
zero_n = N - pos_n - neg_n
cancel = sum(1 for d in docs if d['pol'] == 0 and (d['pos'] + d['neg']) > 0)
cur = {int(k): v for k, v in D['coherence_curve'].items()}
vg = D['venue_groups']


def vstat(idx):
    ms = [sum(docs[i]['theta'][k] for i in idx) / len(idx) for k in range(9)]
    return ms.index(max(ms)) + 1, statistics.mean(pol([docs[i] for i in idx]))


vstat = {v: vstat(i) for v, i in vg.items()}
tstat = {k: (sum(1 for d in docs if d['topic'] == k), statistics.mean(pol([d for d in docs if d['topic'] == k])),
             sum(1 for d in docs if d['topic'] == k and d['pol'] > 0),
             sum(1 for d in docs if d['topic'] == k and d['pol'] < 0)) for k in range(1, 10)}


# ---------- 排版 ----------
def em(ch):
    o = ord(ch)
    if o > 0x2E7F or ch in '（）：；，。、“”《》':
        return 1.0
    if ch == ' ':
        return 0.30
    if ch in '.,;:()[]/|%':
        return 0.31
    return 0.545


def wrap(s, size, width):
    limit, toks = width * 72.0, re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9'’\-\.]*|.", s)
    lines, cur_l, cur_w = [], '', 0.0
    for t in toks:
        tw = sum(em(c) for c in t) * size
        if cur_w + tw > limit and cur_l:
            if t == ' ':
                lines.append(cur_l); cur_l, cur_w = '', 0.0; continue
            lines.append(cur_l.rstrip())
            cur_l, cur_w = ('' if t == ' ' else t), (0.0 if t == ' ' else tw)
        else:
            cur_l += t; cur_w += tw
    if cur_l.strip():
        lines.append(cur_l.rstrip())
    return lines



def trim(path, pad=14):
    """裁掉纯白外边（保留 pad 像素），使图表在版面上更饱满。"""
    out = os.path.join(TMPD, 't_' + os.path.basename(path))
    if os.path.exists(out):
        return out
    im = Image.open(path).convert('RGB')
    px = im.load()
    w, h = im.size
    xs, ys = [], []
    step = 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if r < 248 or g < 248 or b < 248:
                xs.append(x); ys.append(y)
    if not xs:
        im.save(out); return out
    box = (max(0, min(xs) - pad), max(0, min(ys) - pad),
           min(w, max(xs) + pad), min(h, max(ys) + pad))
    im.crop(box).save(out)
    return out

class P:
    def __init__(self, pdf, page=1, total=11):
        self.fig = plt.figure(figsize=(W, H))
        self.fig.patch.set_facecolor('white')
        self.y = H - 0.72
        self.page, self.total = page, total

    def rule(self, y, x0=LM, x1=W - RM, color='#CDD2D0', lw=0.6):
        self.fig.add_artist(plt.Line2D([x0 / W, x1 / W], [y / H, y / H],
                                       color=color, lw=lw, transform=self.fig.transFigure))

    def text(self, s, size=10, x=LM, y=None, color=INK, weight='normal',
             width=None, leading=1.55, style='normal'):
        y = self.y if y is None else y
        lines = wrap(s, size, width) if width else [s]
        step = size * leading / 72.0
        for i, ln in enumerate(lines):
            self.fig.text(x / W, (y - i * step) / H, ln, fontsize=size, color=color,
                          fontweight=weight, style=style, va='top')
        self.y = y - len(lines) * step
        return self.y

    def space(self, d=0.10):
        self.y -= d

    def dot(self, y, x=LM, c=ACC, s=0.050):
        self.fig.add_artist(Rectangle((x / W, (y - s) / H), s / W, s / H,
                                      facecolor=c, edgecolor='none', transform=self.fig.transFigure))

    def head(self, tag, title, sub):
        self.fig.text(LM / W, (H - 0.55) / H, tag, fontsize=8.4, color=ACC, fontweight='bold', va='top')
        self.fig.text((W - RM) / W, (H - 0.55) / H, '专家话语 · LDA 主题建模图表集',
                      fontsize=7.6, color=LIGHT, va='top', ha='right')
        self.rule(H - 0.70)
        self.fig.text(LM / W, (H - 0.86) / H, title, fontsize=14.5, color=INK, fontweight='bold', va='top')
        self.fig.text(LM / W, (H - 1.16) / H, sub, fontsize=8.8, color=MID, va='top')
        self.y = H - 1.44

    def footer(self):
        self.rule(0.62, color='#E2E5E3')
        self.fig.text(LM / W, 0.44 / H, '语料：专家数据表_正式版(1).xlsx · Sheet2 · 66 篇 · 阿根廷本土期刊 17 种',
                      fontsize=7.2, color=LIGHT, va='top')
        self.fig.text((W - RM) / W, 0.44 / H, '%d / %d' % (self.page, self.total),
                      fontsize=7.6, color=MID, va='top', ha='right')

    def image(self, path, ytop, max_h=6.30):
        """去掉 PNG 底部自带的图注色条后居中置入。"""
        im = Image.open(trim(path))
        r = im.size[0] / im.size[1]
        w = CW if CW / r <= max_h else max_h * r
        h = w / r
        ax = self.fig.add_axes([(LM + (CW - w) / 2.0) / W, (ytop - h) / H, w / W, h / H])
        # 关键：不让 matplotlib 按画布 dpi 重采样，按原像素嵌入，PDF 放大后仍清晰
        ax.imshow(im, aspect='auto', interpolation='none', resample=False)
        ax.axis('off')
        return ytop - h

    def table(self, header, rows, widths, x=LM, size=7.7, rh=0.225, hh=0.30, first_bold=False):
        y = self.y
        xs, cx = [], x
        for w in widths:
            xs.append(cx); cx += w
        self.rule(y + 0.04, x0=x, x1=x + sum(widths), color='#BCC2BF', lw=0.7)
        for i, h in enumerate(header):
            self.fig.text(xs[i] / W, y / H, h, fontsize=size - 0.5, color=LIGHT, va='top')
        y -= hh
        self.rule(y + 0.09, x0=x, x1=x + sum(widths), color='#CBD1CE', lw=0.6)
        for r in rows:
            for i, c in enumerate(r):
                self.fig.text(xs[i] / W, y / H, str(c), fontsize=size,
                              color=INK if (i == 0 or first_bold) else MID, va='top')
            y -= rh
        self.rule(y + 0.075, x0=x, x1=x + sum(widths), color='#BCC2BF', lw=0.7)
        self.y = y

    def save(self, pdf):
        pdf.savefig(self.fig); plt.close(self.fig)


# ---------- 图注 ----------
caps = {}
caps[1] = dict(
    f='图1_年度主题文献数量堆叠图.png', t='年度主题文献数量堆叠图',
    sub='66 篇文献按发表年份与主导主题归属统计（每篇计 1 次）',
    cap='横轴为 1999–2026 年，纵轴为当年文献数量，柱内按 9 个主题分段堆叠。主题归属取文档—主题后验概率 θ 的最大值（argmax），'
        '一篇文献只计入一个主题，故各年数量之和等于当年文献总数。图例编号与全文主题编号一致。',
    pts=['分期文献量：≤2013 年 %d 篇、2014–2018 年 %d 篇、2019–2022 年 %d 篇、2023–2026 年 %d 篇；2014 年及以后的文献占全部的 %.0f%%。'
         % (period['≤2013'], period['2014-2018'], period['2019-2022'], period['2023-2026'],
            (period['2014-2018'] + period['2019-2022'] + period['2023-2026']) / N * 100),
         '2000–2008 年无文献。横轴只保留实际出现文献的年份并等距排列，刻度标签为真实年份，因此柱间距不代表时间间隔。',
         '1999、2002 年各仅 1 篇，2026 年为当年入库文献（收录尚不完整），三处不宜作为年度水平解读。'],
    tab=('各年文献量（篇）', ['年份', '篇数', '年份', '篇数'],
         [[y, c] for y, c in [(0, 0)]] and None))
caps[2] = dict(
    f='图2_主题一致性结果.png', t='主题一致性结果', sub='K=2–12 的 u_mass 主题一致性曲线',
    cap='横轴为主题数 K，纵轴为 u_mass 一致性（值域为负，越接近 0 越好）。曲线在 K=8（%.4f）与 K=9（%.4f）出现第一个高平台，'
        'K=9 为截取范围内的最优值；K=10–11 回落，K=12 回升至 %.4f，与 K=9 数值相同但主题已更碎。' % (cur[8], cur[9], cur[12]),
    pts=['模型最终取 K=9，与上一轮建模报告一致；图 1、3、4、5、6、7 的主题编号均据此排列。',
         '横轴截到 K=12：再往上单个主题平均只覆盖 5 篇左右（K=18 时不到 4 篇），主题逐渐退化为少数文献的关键词集合，指标会"虚高"而失去解释力（K=18 的 %.4f 即属此类）。' % cur[18],
         '本图量纲为 u_mass（负值），若与参考文献中的 c_v 曲线对照，形态可比、数值不可直接比较。'])
EW = Counter(e['w'] for e in D['edges'])
caps[3] = dict(
    f='图3_主题网络图.png', t='主题网络图', sub='9 个主题节点、各主题后验概率前 15 位主题词及其共现连线',
    cap='9 个主题按主题间共享词数做力导向排布，圆面积按主题份额（平均后验概率）缩放，圆内为 topic 编号与份额；'
        '每个主题外围是其 φ 值最高的 15 个主题词，词的文字本身即网络节点，字号正比于 β，连线两端裁到文字边缘。'
        '主题之间的灰线粗细正比于两主题各自前 20 词的共同词数（1–6 个）；簇内更细的连线表示该主题词在语料 10 词窗口内共现不少于 6 次。'
        '字号与两类线宽各自独立编码，词的角度位置不承载含义。',
    pts=['主题间共 %d 条关联边：共享 1 个词 %d 条、2 个词 %d 条、3 个词 %d 条、6 个词 1 条（topic4 与 topic9）。'
         % (len(D['edges']), EW[1], EW[2], EW[3]),
         '份额差异：最大为 topic2（%.1f%%）与 topic7（%.1f%%），最小为 topic5（%.1f%%）。'
         % (T[1]['share'] * 100, T[6]['share'] * 100, T[4]['share'] * 100),
         '连线由主题词重叠与语料共现生成（如 educacion、linguistic、ensenanza 同时出现在多个主题），'
         '因此反映词汇与语境关联，不等同于文献引用或作者合作关系。'])
caps[4] = dict(
    f='图4_全部主题时间热度图.png', t='全部主题时间热度图', sub='9 个主题 × 20 个有文献年份的主题强度矩阵',
    cap='行是 9 个主题，列是 1999–2026 年中有文献的 20 个年份；色块为该主题在该年的平均后验概率，全表 min–max 归一化到 0–1，'
        '深色代表强度高；色标再经 γ=0.6 幂律拉伸，以放大低强度区间的差异。白色格为该年无文献。',
    pts=['走向明确的三个主题：topic7 由 ≤2013 年的 %.3f 降至 2019–2022 年的 %.3f；topic8 由 %.3f 降至 %.3f；'
         'topic5 则相反，由 2019–2022 年的 %.3f 升至 2023–2026 年的 %.3f。'
         % (T[6]['periods']['≤2013'], T[6]['periods']['2019-2022'], T[7]['periods']['≤2013'],
            T[7]['periods']['2019-2022'], T[4]['periods']['2019-2022'], T[4]['periods']['2023-2026']),
         'topic2 在 2019–2022 年达峰（%.3f），topic4 同期达峰（%.3f），topic9 由 2014–2018 年的 %.3f 升至 2023–2026 年的 %.3f。'
         % (T[1]['periods']['2019-2022'], T[3]['periods']['2019-2022'],
            T[8]['periods']['2014-2018'], T[8]['periods']['2023-2026']),
         '单元格为该年平均 θ，样本量小的年份（1–2 篇）波动大，读图时应结合图 1 的年度文献量一起看。'])
caps[5] = dict(
    f='图5_各期刊主题热度图.png', t='各期刊主题热度图', sub='9 个期刊面板，每面板为 主题 × 年份 的强度矩阵',
    cap='分面维度由参考图的"国家"改为"期刊"——本语料 66 篇全部发表于阿根廷本土期刊，不存在国别差异。'
        '9 个面板 = 文献量 ≥3 篇的 8 种期刊 + "其他期刊（9 种，各 1–2 篇）"，覆盖全部 66 篇，无遗漏、无合并删减。'
        '各面板为原始均值，共用同一色标上限（vmax 取全部面板最大值），并统一经 γ=0.6 幂律拉伸；灰色格表示该年该期刊无文献。'
        '面板之间可横向比较，但色深不可与图 4 直接互换。',
    pts=['期刊取向差异清晰：RAHL（n=15）以 topic7（gramatica / historiografia）为主，Traslaciones（n=10）以 topic9（espanol / spanish）为主，'
         'Signo y Seña（n=8）以 topic5（sena / guarani）为主，Quintú Quimün 与 Signos ELE 均以 topic6（espanol / segunda）为主。',
         '文献量少的期刊面板大面积灰格，仅表示"该年无文献"，不代表强度为零。',
         '同一主题在不同期刊的峰值年份常不一致，说明主题热度同时受期刊取向与年度议题设置影响，不能只归因于时间趋势。'])
caps[6] = dict(
    f='图6_各主题情感倾向曲线图.png', t='各主题情感倾向曲线图', sub='9 个主题的加权情感值随年份变化',
    cap='纵轴为加权情感值：Σ(主题概率 × 文档极性) / Σ(主题概率)，逐主题逐年计算。'
        '文档极性 =（正面词数 − 负面词数）/（正面词数 + 负面词数 + 2），分母的 2 为平滑项。横轴年份与图 1 一致，仅列有文献的年份。',
    pts=['情感打分基于评价性词根表（' + LEX + '）的词典法，%d/%d 篇命中至少一个评价词。' % (hit, N),
         '全样本极性为正 %d 篇、为负 %d 篇、为 0 的 %d 篇（其中 %d 篇正负相抵、%d 篇未命中评价词），整体偏正（均值 %.3f）。'
         % (pos_n, neg_n, zero_n, cancel, zero_n - cancel, statistics.mean(pol(docs))),
         '主题间差异明显：topic3（%.3f）与 topic9（%.3f）最高，topic2（%.3f）最低。这是词典法而非预训练情感模型，'
         '方法章须写作「基于评价词表的词典法情感打分」；单篇文献主导的年份波动大，不构成趋势证据。'
         % (tstat[3][1], tstat[9][1], tstat[2][1])])
caps[7] = dict(
    f='图7_各期刊主题情感倾向热图.png', t='各期刊主题情感倾向热图', sub='9 个期刊面板，每面板为 主题 × 年份 的情感矩阵',
    cap='分面维度同为"期刊"，面板划分与图 5 完全一致；行是 9 个主题、列是 20 个有文献年份。'
        '色块为加权情感值 Σ(主题概率 × 文档极性) / Σ(主题概率)，暖色为正、冷色为负；色标以 0 为中点双向映射'
        '（负端 −' + PRLO_S + '、正端 ' + PRHI_S + '），故颜色深浅可跨面板直接比较。灰色格表示该年该期刊无文献，或该主题在当年的权重 Σθ 低于 0.05。',
    pts=['色块只在该期刊当年确有文献且该主题权重 ≥0.05 时才有取值，同一面板内不同主题的有效年份可能不同。',
         '期刊均值极性区间为 %.2f（Signo y Seña，n=8）至 %.2f（Integración y Conocimiento，n=4）；'
         '文献量最大的 RAHL（n=15）为 %.2f，Traslaciones（n=10）为 %.2f。'
         % (vstat['Signo y Seña'][1], vstat['Integración y Conocimiento'][1],
            vstat['RAHL: Revista argentina de historiografía lingüística'][1],
            vstat['Traslaciones: Revista Latinoamericana de Lectura y Escritura'][1]),
         'n ≤5 的面板（Anclajes、Integración y Conocimiento、Signos ELE、Argonautas）由 2–3 篇文献即可决定色块取值，'
         '不宜据此判断期刊层面的情感倾向；跨期刊比较应只针对 RAHL 与 Traslaciones。'])

# 每图配套的同源数据表
def t_tab1():
    ys = sorted(ycount.items())
    rows = []
    for i in range(10):
        a = ys[i] if i < len(ys) else ('', '')
        b = ys[i + 10] if i + 10 < len(ys) else ('', '')
        rows.append([a[0], a[1], b[0], b[1]])
    rows = [[r[0], r[1], '', r[2], r[3]] for r in rows]
    return ('各年文献量（篇，共 %d 篇）' % N, ['年份', '篇数', '', '年份', '篇数'], rows,
            [0.80, 0.80, 0.70, 0.80, 0.80])


def t_tab2():
    ks = [k for k in sorted(cur) if k <= 12]
    a = [[k, '%.4f' % cur[k]] for k in ks if k <= 6]
    b = [[k, '%.4f' % cur[k]] for k in ks if k >= 7]
    rows = []
    for i in range(max(len(a), len(b))):
        ra = a[i] if i < len(a) else ['', '']
        rb = b[i] if i < len(b) else ['', '']
        rows.append([ra[0], ra[1], rb[0], rb[1]])
    rows = [[r[0], r[1], '', r[2], r[3]] for r in rows]
    return ('u_mass 一致性逐 K 取值', ['K', 'u_mass', '', 'K', 'u_mass'], rows,
            [0.70, 1.00, 0.75, 0.70, 1.00])


def t_tab3():
    es = sorted(D['edges'], key=lambda e: -e['w'])[:9]
    rows = [['topic%d' % e['a'], 'topic%d' % e['b'], e['w'], '、'.join(e['shared'][:3])] for e in es]
    return ('权重最高的 9 条主题关联（共 %d 条）' % len(D['edges']),
            ['主题 A', '主题 B', '共享词数', '共享词（前 3 个）'], rows, [0.95, 0.95, 1.05, 3.55])


def t_tab4():
    rows = []
    for t in T:
        p = t['periods']
        v = [p['≤2013'], p['2014-2018'], p['2019-2022'], p['2023-2026']]
        rows.append(['topic%d（%s）' % (t['id'], KW2[t['id']]), '%.3f' % v[0], '%.3f' % v[1],
                     '%.3f' % v[2], '%.3f' % v[3], '%.1f' % ((max(v) - min(v)) * 100)])
    return ('各主题分期平均 θ 与峰谷差（百分点）',
            ['主题', '≤2013', '2014–18', '2019–22', '2023–26', '峰谷差'], rows,
            [2.55, 0.85, 0.85, 0.85, 0.85, 0.75])


def t_tab5():
    rows = []
    order = sorted(vg.items(), key=lambda kv: -len(kv[1]))
    for v, idx in order:
        t, _ = vstat[v]
        rows.append([SHORT.get(v, v), len(idx), '%.1f%%' % (len(idx) / N * 100), 'topic%d（%s）' % (t, KW2[t])])
    return ('期刊分面构成与各期刊主导主题', ['期刊面板', '篇数', '占语料', '主导主题（均值 θ 最大）'], rows,
            [2.45, 0.60, 0.70, 2.90])


def t_tab6():
    rows = []
    for k in range(1, 10):
        n, m, p, ng = tstat[k]
        rows.append(['topic%d（%s）' % (k, KW2[k]), n, '%.3f' % m, '%d / %d / %d' % (p, ng, n - p - ng)])
    return ('各主题篇数与极性均值', ['主题', '篇数', '均值极性', '正 / 负 / 中性'], rows,
            [2.70, 0.70, 0.95, 1.55])


def t_tab7():
    items = []
    for v, idx in sorted(vg.items(), key=lambda kv: -len(kv[1])):
        p = pol([docs[i] for i in idx])
        items.append([SHORT.get(v, v), len(idx), '%.3f' % statistics.mean(p)])
    rows = []
    for i in range(5):
        a = items[i] if i < len(items) else ['', '', '']
        b = items[i + 5] if i + 5 < len(items) else ['', '', '']
        rows.append([a[0], a[1], a[2], '', b[0], b[1], b[2]])
    return ('各期刊篇数与极性均值（左栏前 5 位，右栏其余 4 位）',
            ['期刊面板', '篇数', '均值极性', '', '期刊面板', '篇数', '均值极性'], rows,
            [2.00, 0.45, 0.62, 0.42, 2.00, 0.45, 0.62])


tabs = {1: t_tab1, 2: t_tab2, 3: t_tab3, 4: t_tab4, 5: t_tab5, 6: t_tab6, 7: t_tab7}


# ---------- 组页 ----------
def build():
    with PdfPages(OUT) as pdf:
        # ---- 预计算：图幅按版心满宽，内容溢出时数据表顺延次页 ----
        avail0 = (H - 1.44) - 0.82
        SPLIT, FIGPG = {}, {}
        _pg = 3
        for i in range(1, 8):
            c = caps[i]
            _p = trim(os.path.join(FIGD, c['f']))
            _r = Image.open(_p).size[0] / Image.open(_p).size[1]
            _rows = tabs[i]()[2]
            _himg = CW / _r
            _hcap = len(wrap('图 %d　%s' % (i, c['cap']), 8.7, CW)) * 8.7 * 1.58 / 72
            _hpts = sum(len(wrap(b, 8.4, CW - 0.16)) * 8.4 * 1.56 / 72 + 0.10 for b in c['pts'])
            _htab = 0.28 + 0.30 + len(_rows) * 0.225 + 0.075
            SPLIT[i] = (_himg + 0.38 + 0.24 + _hcap + 0.20 + 0.26 + _hpts + 0.22 + _htab) > avail0
            FIGPG[i] = _pg + 1
            _pg += 2 if SPLIT[i] else 1
        TOTALPG = _pg + 1

        # ===== 1 封面 =====
        p = P(pdf, 1, TOTALPG)
        p.fig.text(LM / W, (H - 1.60) / H, '专家话语语料', fontsize=9.2, color=ACC, fontweight='bold', va='top')
        p.fig.text(LM / W, (H - 1.92) / H, 'LDA 主题建模图表集', fontsize=25, color=INK, fontweight='bold', va='top')
        p.rule(H - 2.48, color=ACC, lw=1.4, x1=LM + 1.55)
        p.fig.text(LM / W, (H - 2.78) / H, '66 篇阿根廷语言教育类期刊论文 · 17 种期刊 · 1999–2026 年 · 主题数 K=9',
                   fontsize=10.2, color=MID, va='top')

        meta = [('语　　料', '专家数据表_正式版(1).xlsx · Sheet2 · 66 篇（已剔除境外期刊记录）'),
                ('模　　型', 'LDA · collapsed Gibbs 采样 · α=0.1，β=0.02，迭代 200 次，seed=7'),
                ('词　　表', 'min_df=2、max_df=0.55，西语轻量词干化后 815 词；主题数由 u_mass 择优'),
                ('绘图工具', 'Python 3.13 + matplotlib 3.11，320 dpi 位图原像素嵌入，A4 版面合成 PDF'),
                ('配　　色', '「海洋清风」8 色：#BFDFD2 #51999F #4198AC #7BC0CD #DBCB92 #ECB66C #EA9E58 #ED8D5A')]
        y = H - 3.40
        for k, v in meta:
            p.fig.text(LM / W, y / H, k, fontsize=8.2, color=LIGHT, va='top')
            p.fig.text((LM + 0.92) / W, y / H, v, fontsize=8.6, color=INK, va='top')
            y -= 0.30

        p.rule(H - 5.10)
        p.fig.text(LM / W, (H - 5.36) / H, '图 表 目 录', fontsize=9.6, color=INK, fontweight='bold', va='top')
        toc = [('01', '年度主题文献数量堆叠图', '年份 × 主题的文献量构成', str(FIGPG[1])),
               ('02', '主题一致性结果', 'K=2–12 的 u_mass 曲线与 K 值选择', str(FIGPG[2])),
               ('03', '主题网络图', '主题—主题词—共现关系', str(FIGPG[3])),
               ('04', '全部主题时间热度图', '9 主题 × 20 年份强度矩阵', str(FIGPG[4])),
               ('05', '各期刊主题热度图', '9 个期刊面板的主题强度', str(FIGPG[5])),
               ('06', '各主题情感倾向曲线图', '9 条主题情感曲线', str(FIGPG[6])),
               ('07', '各期刊主题情感倾向曲线图', '9 个期刊面板的情感曲线', str(FIGPG[7]))]
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
        for a, b in [('第 2 页', '语料、模型与三个指标的定义，含时间片划分口径'),
                     ('第 3 页', '9 个主题的编号、前 12 位主题词、主导篇数与份额'),
                     ('第 4–%d 页' % (TOTALPG - 1),
                      '七张图，每页 = 图 + 图注 + 读图要点 + 同源数据表（图 3、图 5、图 7 的数据表见次页）'),
                     ('第 %d 页' % TOTALPG, '与参考图的三处差异、复现方式与随册文件清单')]:
            p.fig.text((LM + 0.05) / W, y / H, a, fontsize=8.4, color=ACC if a.startswith('第') else MID, va='top')
            p.fig.text((LM + 1.05) / W, y / H, b, fontsize=8.4, color=MID, va='top')
            y -= 0.27

        p.y = 1.42
        p.text('说明：本册所有数值均直接来自同一份 LDA 结果文件（work/lab_results.json），未做任何人工补值或重新拟合；'
               '每张图下方的数据表即为该图所用数值的直接汇总，可逐项核对。',
               size=7.8, width=CW, color=LIGHT, leading=1.5)
        p.footer()
        p.save(pdf)

        # ===== 2 数据口径 =====
        p = P(pdf, 2, TOTALPG)
        p.head('数据口径', '一 · 语料、模型与指标定义', '读图前应先确认以下四组定义，图中的每一个数字都按此口径生成。')
        p.fig.text(LM / W, p.y / H, '1.1　语料与模型', fontsize=10.6, color=INK, fontweight='bold', va='top')
        p.y -= 0.30
        p.text('语料为「专家数据表_正式版」Sheet2 的 66 篇文献摘要，全部发表于阿根廷本土期刊，涉及 17 种期刊、1999–2026 年。'
               '建模只用摘要正文，按西语分词并作轻量词干化（去复数、去部分屈折），保留名词、动词、形容词，去掉停用词与仅出现 1 次的词，最终词表 815 词。',
               size=9.4, width=CW, color=INK, leading=1.62)
        p.space(0.08)
        p.text('主题数 K 通过 u_mass 一致性在 K=2–20 上扫描确定，取曲线第一个高平台 K=9（详见第 5 页图 2）。'
               '推断用 collapsed Gibbs 采样，α=0.1、β=0.02、迭代 200 次、随机种子 7，可复现。',
               size=9.4, width=CW, color=INK, leading=1.62)
        p.space(0.34)

        p.fig.text(LM / W, p.y / H, '1.2　三个指标的确切定义', fontsize=10.6, color=INK, fontweight='bold', va='top')
        p.y -= 0.34
        for name, body in [('一致性（图 2）',
                            'u_mass：对每个主题的前 10 个词，统计词对在文档共现中的对数概率比，主题内平均后再对 9 个主题取平均。值域为负，越接近 0 越好。'),
                           ('热度（图 4、图 5）',
                            '某主题在某年的平均后验概率 θ。图 4 对全表做 min–max 归一化到 0–1；图 5 用原始均值、九面板共用色标上限。0 表示该年该主题几乎不出现，1 表示全样本中最高强度。'),
                           ('情感倾向（图 6、图 7）',
                            '加权情感值 = Σ(主题概率 × 文档极性) / Σ(主题概率)；文档极性 = (正面词数 − 负面词数) / (正面词数 + 负面词数 + 2)，分母 2 为平滑项，避免单篇仅 1 个评价词时取到 ±1。')]:
            p.dot(p.y - 0.055)
            p.fig.text((LM + 0.17) / W, p.y / H, name, fontsize=9.4, color=INK, fontweight='bold', va='top')
            p.y -= 0.27
            p.text(body, size=9.0, x=LM + 0.17, width=CW - 0.17, color=MID, leading=1.58)
            p.space(0.21)

        p.fig.text(LM / W, p.y / H, '1.3　必须交代的一点', fontsize=10.6, color=ACC2, fontweight='bold', va='top')
        p.y -= 0.30
        p.text('情感指标由评价性词根表（' + LEX + '）打分，属词典法，不是预训练情感模型。'
               '论文方法章应写「基于评价词表的词典法情感打分」，不宜写作 BERT 或深度学习情感分类。词表随结果一并给出，可逐条复核。',
               size=9.2, width=CW, color=MID, leading=1.62)
        p.space(0.42)

        p.fig.text(LM / W, p.y / H, '1.4　时间片划分口径', fontsize=10.6, color=INK, fontweight='bold', va='top')
        p.y -= 0.34
        p.text('四个时期由文献量的自然断点确定，用于图 4 的分期读图；时间片再细分则每片不足 8 篇，主题均值不可估计。',
               size=8.8, width=CW, color=MID, leading=1.55)
        p.space(0.14)
        p.table(['年份区间', '篇数', '占语料', '该期平均 θ 超过 10% 的主题数', '该期平均 θ 最高的主题'],
                [[PLABEL[k], v, '%.1f%%' % (v / N * 100),
                  sum(1 for t in T if t['periods'][k] > 0.10),
                  'topic%d（%s）' % (max(range(1, 10), key=lambda j: T[j - 1]['periods'][k]),
                                    KW2[max(range(1, 10), key=lambda j: T[j - 1]['periods'][k])])]
                 for k, v in period.items()],
                [1.35, 0.65, 0.75, 1.95, 2.00], rh=0.24)
        p.space(0.10)
        p.text('注：「该期主题数」为平均 θ 超过 10% 的主题个数，用于说明分期后主题集中度的变化，不是新增指标。',
               size=7.8, width=CW, color=LIGHT, leading=1.45)
        p.footer()
        p.save(pdf)

        # ===== 3 主题总表 =====
        p = P(pdf, 3, TOTALPG)
        p.head('主题总表', '二 · 9 个主题的编号与主题词',
               '主题词为模型输出中后验概率最高的 12 位，括号内为 β 值。')
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
            p.text(ws, size=7.2, x=cols[1], y=row_y, width=4.50, color=MID, leading=1.48)
            p.fig.text(cols[2] / W, row_y / H, str(t['size']), fontsize=8.6, color=MID, va='top')
            p.fig.text(cols[3] / W, row_y / H, '%.1f%%' % (t['share'] * 100), fontsize=8.6, color=MID, va='top')
            p.y = row_y - 0.70
            p.rule(p.y + 0.14, color='#EDEFED', lw=0.45)
        p.space(0.06)
        p.text('合计：主导篇数 %d 篇（= 全部语料），份额合计 100%%。「主导篇数」为按 argmax 归属的篇数，「份额」为平均后验概率之和，'
               '两者口径不同，故不完全成比例。' % sum(t['size'] for t in T),
               size=8.6, width=CW, color=MID, leading=1.55)
        p.space(0.16)
        p.fig.text(LM / W, p.y / H, '三点阅读提示', fontsize=9.0, color=INK, fontweight='bold', va='top')
        p.y -= 0.28
        for b in ['词表经轻量词干化，故主题词常为词干残缺形式（sena ← seña、guarani ← guaraní、politica ← política、'
                  'ensenanza ← enseñanza），这是词干化的产物，不是拼写错误。',
                  '主题仅以编号与主题词呈现，不附加人工命名；主题词表本身即模型输出，解读时应以词表为唯一依据。',
                  'topic2 的 aire、bueno 与 topic5 的 anos、escrito 属语料中高频的通用词，虽进入前 12 位但区分度低，'
                  '解读时应结合后验概率与跨主题分布，不宜单看个别词。']:
            p.dot(p.y - 0.055, c='#C8CDCA', s=0.042)
            p.text(b, size=8.6, x=LM + 0.16, width=CW - 0.16, color=MID, leading=1.58)
            p.space(0.12)
        p.footer()
        p.save(pdf)

        # ===== 4–11 七张图（表格溢出时数据表顺延一页，不压图） =====
        pg = 3
        for i in range(1, 8):
            c = caps[i]
            fpath = os.path.join(FIGD, c['f'])
            ratio = Image.open(trim(fpath)).size[0] / Image.open(trim(fpath)).size[1]
            title, hdr, rows, wid = tabs[i]()
            split = SPLIT[i]

            def need_h(mh, body_only=False):
                w = CW if CW / ratio <= mh else mh * ratio
                h_img = w / ratio
                h_cap = len(wrap('图 %d\u3000%s' % (i, c['cap']), 8.7, CW)) * 8.7 * 1.58 / 72
                h_pts = sum(len(wrap(b, 8.4, CW - 0.16)) * 8.4 * 1.56 / 72 + 0.10 for b in c['pts'])
                h_tab = 0.28 + 0.30 + len(rows) * 0.225 + 0.075
                body = h_img + 0.38 + 0.24 + h_cap + 0.20 + 0.26 + h_pts + 0.22
                return body if body_only else body + h_tab

            avail = (H - 1.44) - 0.82
            pg += 1
            p = P(pdf, pg, TOTALPG)
            p.head('图 %02d' % i, c['t'], c['sub'])
            p.y = H - 1.44 - max(0.0, (avail - need_h(9.0, split)) * 0.42)
            ybot = p.image(fpath, p.y + 0.02, max_h=9.0)
            p.y = ybot - 0.38
            p.rule(p.y + 0.13, color='#DDE1DF')
            p.fig.text(LM / W, p.y / H, '图注', fontsize=8.2, color=ACC, fontweight='bold', va='top')
            p.y -= 0.24
            p.text('%s\u3000%s' % ('图 %d' % i, c['cap']), size=8.7, width=CW, color=MID, leading=1.58)
            p.space(0.20)
            p.fig.text(LM / W, p.y / H, '读图要点', fontsize=8.2, color=LIGHT, fontweight='bold', va='top')
            p.y -= 0.26
            for b in c['pts']:
                p.dot(p.y - 0.052, c='#C8CDCA', s=0.040)
                p.text(b, size=8.4, x=LM + 0.16, width=CW - 0.16, color=INK, leading=1.56)
                p.space(0.10)
            if split:
                p.space(0.24)
                p.fig.text(LM / W, p.y / H, '注：本图数据表见次页（第 %d 页）。' % (pg + 1),
                           fontsize=8.2, color=LIGHT, va='top')
                p.footer()
                p.save(pdf)
                pg += 1
                p = P(pdf, pg, TOTALPG)
                p.head('图 %02d' % i, c['t'] + '（续）', '同源数据表（接上页）')
                p.y = H - 4.05
                p.fig.text(LM / W, p.y / H, '数据表 · ' + title, fontsize=8.2, color=LIGHT, fontweight='bold', va='top')
                p.y -= 0.34
                p.table(hdr, rows, wid, rh=0.42, hh=0.38)
                p.space(0.26)
                p.text('表注：本表与上页图同源，数值直接取自 work/lab_results.json；为保持图的纵横比、不压缩图幅，本表顺延至本页。',
                       size=8.2, width=CW, color=LIGHT, leading=1.55)
            else:
                p.space(0.22)
                p.fig.text(LM / W, p.y / H, '数据表 · ' + title, fontsize=8.2, color=LIGHT, fontweight='bold', va='top')
                p.y -= 0.28
                p.table(hdr, rows, wid)
            p.footer()
            p.save(pdf)

        # ===== 11 附录 =====
        pg += 1
        p = P(pdf, pg, TOTALPG)
        p.head('附录', '三 · 与参考图的差异、复现方式与文件清单',
               '以下三点在论文的方法或图注中需要明确交代，否则容易被误读为数据缺失。')
        for i, (h, b) in enumerate([('分面维度：国家 → 期刊',
                                     '参考图以国家为分面，本语料 66 篇全部为阿根廷本土期刊，不存在国别差异。故改为期刊分面，'
                                     '9 个面板 = 文献量 ≥3 篇的 8 种期刊 + 「其他期刊（9 种，各 1–2 篇）」，覆盖全部 66 篇。'),
                                    ('年份轴：连续年份 → 有文献年份等距',
                                     '2000–2008 年无文献。若按连续年份绘制，横轴会出现近十年的空白直线，视觉上被误读为「研究中断」。'
                                     '故图 1、4、6、7 仅保留有文献的年份等距排列，刻度标签仍为真实年份。'),
                                    ('一致性量纲：c_v → u_mass',
                                     '参考图为 c_v（正值，0.42–0.54），本图为 u_mass（负值，%.2f 至 %.2f）。两者单调方向相反，'
                                     '形态可比、数值不可直接对照，引用时须注明量纲。' % (min(cur.values()), max(cur.values())))], 1):
            p.fig.text(LM / W, p.y / H, '差异 %d' % i, fontsize=7.8, color=ACC2, fontweight='bold', va='top')
            p.y -= 0.24
            p.fig.text(LM / W, p.y / H, h, fontsize=9.8, color=INK, fontweight='bold', va='top')
            p.y -= 0.30
            p.text(b, size=9.0, x=LM + 0.14, width=CW - 0.14, color=MID, leading=1.58)
            p.space(0.18)

        p.rule(p.y + 0.04)
        p.space(0.18)
        p.fig.text(LM / W, p.y / H, '复现方式', fontsize=10.2, color=INK, fontweight='bold', va='top')
        p.y -= 0.30
        for ln in ['tools/lab_model2.py　　K=9 主题结果 + u_mass 曲线 K=2–20 + 极性计算',
                   'tools/lab_pol.py　　　　 极性平滑（λ=2）',
                   'tools/lab_figs.py　　　　七张图（320 dpi PNG）',
                   'tools/make_atlas.py　　　本册合成（A4 纵向，11 页）']:
            p.fig.text((LM + 0.14) / W, p.y / H, ln, fontsize=8.4, color=MID, va='top')
            p.y -= 0.23
        p.space(0.04)
        p.text('中间结果：work/lab_results.json（主题词、θ 矩阵、年度矩阵、极性、期刊分组）。所有图与表均以该文件为唯一输入，未二次拟合。',
               size=8.5, x=LM + 0.14, width=CW - 0.14, color=MID, leading=1.55)

        p.space(0.30)
        p.rule(p.y + 0.04)
        p.space(0.18)
        p.fig.text(LM / W, p.y / H, '随册文件', fontsize=10.2, color=INK, fontweight='bold', va='top')
        p.y -= 0.28
        for a, b in [('本 PDF', '图、图注、读图要点、同源数据表合订，A4 纵向 11 页，可直接打印或作为论文附录提交'),
                     ('图 1–7 PNG', '320 dpi 独立位图，可直接插入 Word / LaTeX'),
                     ('图注说明.md', '纯文本版图注与口径说明，便于复制到论文正文')]:
            p.fig.text((LM + 0.14) / W, p.y / H, a, fontsize=8.6, color=INK, va='top')
            p.text(b, size=8.5, x=LM + 1.02, width=CW - 1.02, color=MID, leading=1.52)
            p.space(0.06)
        p.space(0.10)
        p.text('待补：BERTopic 的层次聚类图、主题相似度热图与二维散点图需联网安装 bertopic、sentence-transformers 后生成；'
               '其余七张图与全部数据表不依赖该环境。',
               size=8.3, x=LM + 0.14, width=CW - 0.14, color=LIGHT, leading=1.55)

        p.space(0.24)
        p.rule(p.y + 0.04)
        p.space(0.14)
        p.fig.text(LM / W, p.y / H, '符号与术语对照', fontsize=10.2, color=INK, fontweight='bold', va='top')
        p.y -= 0.32
        p.table(['符号 / 术语', '含义', '本册取值'],
                [['N', '语料文献总数', '66'],
                 ['K', '主题数（由一致性曲线选定）', '9'],
                 ['θ（theta）', '文档 d 属于主题 k 的后验概率，每篇 9 个值，和为 1', '—'],
                 ['β（beta）', '主题 k 中词 w 的出现概率，主题词表按此排序', '—'],
                 ['主导主题', 'argmax θ，用于图 1 的篇数归属', '—'],
                 ['份额', '全语料 θ 的列均值，9 个主题合计 100%', '9.9%–13.5%'],
                 ['分面（facet）', '图 5、图 7 按期刊切分面板', '9 个面板']],
                [1.45, 4.20, 1.05], rh=0.195)
        p.footer()
        p.save(pdf)

    print('OK ->', OUT, os.path.getsize(OUT))


if __name__ == '__main__':
    build()
