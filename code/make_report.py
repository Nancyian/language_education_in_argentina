# -*- coding: utf-8 -*-
"""把 LDA 预演结果渲染为 SVG 图表 + 组装 HTML 报告"""
import json, io, math
import numpy as np

d = json.load(io.open('work/topic_results.json', encoding='utf-8'))
K = d['K']
topics = d['topics']
periods = [p['label'] for p in d['periods']]
pn = [p['n'] for p in d['periods']]
PHI = np.array(d['phi'])
VOC = d['vocab']

COL = ['#5B7C99', '#C08552', '#6B8E7B', '#9A7AA0', '#C4A04A',
       '#8A6E5D', '#4E8E8A', '#A8756B', '#6E8B5A']
LAB = {
    1: ('跨文化双语教育', 'educación intercultural bilingüe'),
    2: ('首都语言政策与中文书写', 'política lingüística CABA / chino'),
    3: ('区域一体化与外语政策', 'Mercosur / educación superior'),
    4: ('外语课程与教学', 'enseñanza de lenguas extranjeras'),
    5: ('手语、瓜拉尼语与翻译', 'lengua de señas / guaraní / traducción'),
    6: ('西语二语习得与教学法', 'español como L2 / didáctica'),
    7: ('语法学史与语言态度', 'historiografía gramatical / actitud'),
    8: ('社区双语与聋人读写', 'bilingüismo comunitario / sordera'),
    9: ('西班牙语变体与阿根廷西语', 'variedades del español / argentino'),
}

def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def T(x, y, s, size=12, anchor='start', fill='#2C2C2A', weight=400, opacity=1):
    return ('<text x="%.1f" y="%.1f" font-size="%s" text-anchor="%s" fill="%s" font-weight="%s" '
            'opacity="%.2f">%s</text>' % (x, y, size, anchor, fill, weight, opacity, esc(s)))

def R(x, y, w, h, fill, stroke='none', rx=0, sw=1, op=1):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" stroke="%s" '
            'stroke-width="%.1f" opacity="%.2f"/>' % (x, y, w, h, rx, fill, stroke, sw, op))

def L(x1, y1, x2, y2, stroke, w=1, dash=None, op=1):
    da = ' stroke-dasharray="%s"' % dash if dash else ''
    return ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"%s opacity="%.2f"/>'
            % (x1, y1, x2, y2, stroke, w, da, op))

def svg(w, h, body):
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img" '
            'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">%s</svg>' % (w, h, ''.join(body)))

def hex2rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

def mix(c1, c2, t):
    a, b = hex2rgb(c1), hex2rgb(c2)
    return '#%02X%02X%02X' % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def heat_color(v, vmax):
    t = 0 if vmax <= 0 else min(1, v / vmax)
    return mix('#F4F6F8', '#2E5A73', t ** 0.75)

def wrap_trunc(s, n=26):
    s = s.replace('Revista ', 'R. ').replace('argentina de ', 'arg. ')
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[:cut.rfind(' ')] + '…'

# ---------------- 图1 ----------------
def fig_coherence():
    W, H = 720, 300
    x0, y0, w, h = 90, 40, 560, 200
    ks = sorted(int(k) for k in d['coherence_curve'])
    vals = [d['coherence_curve'][str(k)] for k in ks]
    lo, hi = min(vals) - 0.03, max(vals) + 0.03
    X = lambda k: x0 + (k - ks[0]) / (ks[-1] - ks[0]) * w
    Y = lambda v: y0 + h - (v - lo) / (hi - lo) * h
    b = []
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        b.append(L(x0, Y(v), x0 + w, Y(v), '#EDEEEB', 1))
        b.append(T(x0 - 8, Y(v) + 4, '%.2f' % v, 11, 'end', '#8A8A85'))
    b.append(L(x0, y0 + h, x0 + w, y0 + h, '#B4B2A9', 1))
    for k in ks:
        b.append(T(X(k), y0 + h + 20, str(k), 11.5, 'middle', '#5F5E5A'))
    pts = ' '.join('%.1f,%.1f' % (X(k), Y(d['coherence_curve'][str(k)])) for k in ks)
    b.append('<polyline points="%s" fill="none" stroke="#5B7C99" stroke-width="2"/>' % pts)
    bestk = max(ks, key=lambda k: d['coherence_curve'][str(k)])
    for k in ks:
        v = d['coherence_curve'][str(k)]
        sel = (k == bestk)
        b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="#FFFFFF" stroke-width="1.5"/>'
                 % (X(k), Y(v), 5 if sel else 3.5, '#C08552' if sel else '#5B7C99'))
        if sel:
            b.append(T(X(k), Y(v) - 14, 'K=%d 最优 %.2f' % (k, v), 11.5, 'middle', '#8B5A2B', 500))
    b.append(T(x0 + w / 2, H - 12, '主题数 K', 11.5, 'middle', '#5F5E5A'))
    b.append(T(20, y0 - 14, '主题一致性（UMass，越接近 0 越好）', 11.5, 'start', '#5F5E5A'))
    return svg(W, H, b)

# ---------------- 图2 ----------------
def fig_stack():
    W, H = 720, 380
    x0, y0, w, h = 60, 40, 430, 250
    bw = w / len(periods) * 0.62
    b = []
    for i, lab in enumerate(periods):
        cx = x0 + w / len(periods) * (i + 0.5)
        acc = 0
        for t in topics:
            v = t['periods'][lab]
            seg = v * h
            yy = y0 + h - acc * h - seg
            b.append(R(cx - bw / 2, yy, bw, seg, COL[t['id'] - 1]))
            if seg > 13:
                b.append(T(cx, yy + seg / 2 + 3.5, '%d%%' % round(v * 100), 9.5, 'middle', '#FFFFFF', 500, 0.95))
            acc += v
        b.append(T(cx, y0 + h + 18, lab, 11, 'middle', '#5F5E5A'))
        b.append(T(cx, y0 + h + 33, 'n=%d' % pn[i], 10.5, 'middle', '#9A9A94'))
    b.append(L(x0, y0 + h, x0 + w, y0 + h, '#B4B2A9', 1))
    b.append(T(20, y0 - 14, '主题份额（各时期合计 100%）', 11.5, 'start', '#5F5E5A'))
    for i, t in enumerate(topics):
        ly = y0 + 2 + i * 26
        b.append(R(520, ly, 11, 11, COL[t['id'] - 1], rx=2))
        b.append(T(538, ly + 10, 'T%d %s' % (t['id'], LAB[t['id']][0]), 10.5, 'start', '#3F3F3C'))
    b.append(T(20, H - 14, '注：份额＝该时期各文档主题概率的均值，反映主题的相对突出程度，不是绝对篇数。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图3 ----------------
def fig_heat_time():
    W = 720
    cw, ch, lx, ty = 118, 30, 215, 42
    H = ty + ch * K + 46
    vmax = max(t['periods'][p] for t in topics for p in periods)
    b = []
    for j, p in enumerate(periods):
        b.append(T(lx + cw * (j + .5), ty - 10, p, 11, 'middle', '#5F5E5A'))
    for i, t in enumerate(topics):
        yy = ty + i * ch
        b.append(T(lx - 10, yy + ch / 2 + 4, 'T%d  %s' % (t['id'], LAB[t['id']][0]), 11, 'end', '#3F3F3C'))
        for j, p in enumerate(periods):
            v = t['periods'][p]
            b.append(R(lx + j * cw, yy, cw - 4, ch - 4, heat_color(v, vmax), rx=3))
            b.append(T(lx + j * cw + (cw - 4) / 2, yy + ch / 2 + 2, '%.1f' % (v * 100), 10.5, 'middle',
                       '#FFFFFF' if v > vmax * 0.55 else '#3F3F3C', 500))
    b.append(T(20, H - 18, '单元格＝主题在该时期的平均概率（%）。深色＝该主题在该阶段更突出。', 10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图4 ----------------
def fig_kw():
    pw, ph = 228, 122
    W, H = 720, 20 + ph * 3 + 30
    b = []
    for idx, t in enumerate(topics):
        cx = 4 + (idx % 3) * (pw + 6)
        cy = 8 + (idx // 3) * (ph + 8)
        b.append(R(cx, cy, pw, ph, '#FBFBFA', '#E8E8E5', rx=6, sw=1))
        b.append(T(cx + 10, cy + 17, 'T%d' % t['id'], 11, 'start', COL[t['id'] - 1], 500))
        b.append(T(cx + 34, cy + 17, LAB[t['id']][0][:13], 10.5, 'start', '#3F3F3C'))
        words = t['words'][:5]
        mx = max(v for _, v in words)
        for i, (w, v) in enumerate(words):
            yy = cy + 30 + i * 16.5
            b.append(R(cx + 10, yy, (pw - 96) * v / mx, 9, COL[t['id'] - 1], rx=2, op=0.85))
            b.append(T(cx + 13, yy + 7.6, w[:17], 9.2, 'start', '#FFFFFF', 500))
    b.append(T(8, H - 8, '每格为该主题权重最高的 5 个词（已归一化）。词形经过西语轻量词干化，故出现 historiografia 等无重音形式。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图5 ----------------
def fig_net():
    W, H = 720, 505
    cx, cy, Rr = 330, 228, 148
    pos = {}
    for i, t in enumerate(topics):
        a = -math.pi / 2 + 2 * math.pi * i / K
        pos[t['id']] = (cx + Rr * math.cos(a), cy + Rr * math.sin(a))
    b = []
    mw = max([e['w'] for e in d['edges']] or [1])
    for e in sorted(d['edges'], key=lambda x: x['w']):
        x1, y1 = pos[e['a']]
        x2, y2 = pos[e['b']]
        w = 0.7 + 3.6 * e['w'] / mw
        b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#9AA5AE" stroke-width="%.1f" opacity="%.2f"/>'
                 % (x1, y1, x2, y2, w, 0.22 + 0.30 * e['w'] / mw))
    mxs = max(t['share'] for t in topics)
    for t in topics:
        x, y = pos[t['id']]
        r = 14 + 26 * math.sqrt(t['share'] / mxs)
        b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.92"/>' % (x, y, r, COL[t['id'] - 1]))
        b.append(T(x, y + 4, 'T%d' % t['id'], 11.5, 'middle', '#FFFFFF', 500))
        dx, dy = (x - cx) / Rr, (y - cy) / Rr
        lx, ly = x + dx * (r + 15), y + dy * (r + 13)
        anchor = 'middle' if abs(dx) < 0.55 else ('start' if dx > 0 else 'end')
        b.append(T(lx, ly + 3, LAB[t['id']][0][:12], 10.2, anchor, '#4A4A46'))
    b.append(L(60, 450, 100, 450, '#9AA5AE', 1.2, op=0.30))
    b.append(T(108, 454, '共享 1 词', 9.8, 'start', '#7A7A74'))
    b.append(L(200, 450, 240, 450, '#9AA5AE', 4.0, op=0.55))
    b.append(T(248, 454, '共享 6 词', 9.8, 'start', '#7A7A74'))
    b.append(T(20, 490, '节点面积∝主题份额；连线＝两主题共享的前 20 个主题词数量，越粗表示主题间边界越模糊。T4–T9 共享 6 词为最高。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图6 ----------------
def fig_venue():
    vm = d['venue_matrix']
    vs = sorted(vm, key=lambda v: -sum(vm[v]))
    cw, ch, lx, ty = 46, 24, 258, 44
    W = lx + cw * K + 40
    H = ty + ch * len(vs) + 44
    b = []
    for j in range(K):
        b.append(T(lx + cw * (j + .5), ty - 10, 'T%d' % (j + 1), 10.5, 'middle', '#5F5E5A'))
    for i, v in enumerate(vs):
        yy = ty + i * ch
        b.append(T(lx - 8, yy + ch / 2 + 3, wrap_trunc(v, 34), 9.8, 'end', '#3F3F3C'))
        for j in range(K):
            c = vm[v][j]
            if c:
                b.append(R(lx + j * cw, yy, cw - 3, ch - 3, mix('#F4F6F8', '#2E5A73', min(1, c / 6) ** 0.8), rx=3))
                b.append(T(lx + j * cw + (cw - 3) / 2, yy + ch / 2 + 1, str(c), 10, 'middle',
                           '#FFFFFF' if c >= 3 else '#3F3F3C', 500))
    b.append(T(20, H - 16, '单元格＝该刊以该主题为主主题的篇数。用于判断主题是否由单一期刊的学科定位所驱动（如 T7 集中于 RAHL）。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图7：语料时间轴 ----------------
def fig_timeline():
    docs = sorted(d['docs'], key=lambda x: (x['year'], x['no']))
    W, H = 720, 250
    x0, y0, w, h = 56, 34, 630, 150
    n = len(docs)
    step = w / n
    bw = step - 1.6
    b = []
    for i, doc in enumerate(docs):
        cx = x0 + i * step
        acc = 0
        for t in topics:
            wgt = doc['theta'][t['id'] - 1]
            seg = wgt * h
            b.append(R(cx, y0 + h - acc * h - seg, bw, seg, COL[t['id'] - 1], op=0.9))
            acc += wgt
    b.append(L(x0, y0 + h, x0 + w, y0 + h, '#B4B2A9', 1))
    seen = set()
    for i, doc in enumerate(docs):
        y = doc['year']
        if y not in seen and (y % 5 == 0 or y in (1999, 2026)):
            seen.add(y)
            b.append(L(x0 + i * step, y0 + h, x0 + i * step, y0 + h + 4, '#B4B2A9', 1))
            b.append(T(x0 + i * step, y0 + h + 18, str(y), 10, 'middle', '#5F5E5A'))
    b.append(T(20, y0 - 12, '66 篇文献按发表年排序（每列一篇，色块＝主题概率构成）', 11.5, 'start', '#5F5E5A'))
    b.append(T(20, H - 20, '每列按该篇真实的主题概率分布堆叠（theta），顶部最大色块即主导主题；色块越集中说明该篇主题归属越单一。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

# ---------------- 图8 ----------------
def fig_dist():
    X = PHI - PHI.mean(0, keepdims=True)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    Z = U[:, :2] * S[:2]
    Z = Z / (np.abs(Z).max() or 1)
    W, H = 720, 430
    cx, cy, sx, sy = 250, 186, 150, 96
    mxs = max(t['share'] for t in topics)
    pts = [(cx + Z[i][0] * sx, cy - Z[i][1] * sy) for i in range(K)]
    rs = [9 + 18 * math.sqrt(t['share'] / mxs) for t in topics]
    # 最小间距微调：仅消除遮挡，不改变右侧已分离主题的位置
    for _ in range(60):
        moved = False
        for i in range(K):
            for j in range(i + 1, K):
                x1, y1 = pts[i]; x2, y2 = pts[j]
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy) or 0.01
                need = rs[i] + rs[j] + 5
                if dist < need:
                    push = (need - dist) / 2
                    ux, uy = dx / dist, dy / dist
                    pts[i] = (x1 - ux * push, y1 - uy * push)
                    pts[j] = (x2 + ux * push, y2 + uy * push)
                    moved = True
        if not moved:
            break
    b = []
    b.append(L(50, cy, 470, cy, '#F0F0ED', 1))
    b.append(L(cx, 34, cx, 350, '#F0F0ED', 1))
    for i in sorted(range(K), key=lambda i: -topics[i]['share']):
        t = topics[i]; x, y = pts[i]; r = rs[i]
        b.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity="0.60" stroke="%s" stroke-width="1"/>'
                 % (x, y, r, COL[t['id'] - 1], COL[t['id'] - 1]))
        b.append(T(x, y + 3.5, 'T%d' % t['id'], 10, 'middle', '#FFFFFF', 500))
    for i, t in enumerate(topics):
        ly = 56 + i * 32
        b.append(R(498, ly - 9, 10, 10, COL[t['id'] - 1], rx=2))
        b.append(T(514, ly, 'T%d' % t['id'], 10, 'start', '#5F5E5A', 500))
        b.append(T(536, ly, LAB[t['id']][0], 9.8, 'start', '#3F3F3C'))
    b.append(T(20, H - 32, '圆面积∝主题份额，圆心距离∝主题词语分布的差异（对 K×V 词分布矩阵做 PCA 投影）。', 10.5, 'start', '#8A8A85'))
    b.append(T(20, H - 14, '左侧五点原始位置几乎完全重合（T1/T2/T3/T5/T7），已做最小间距微调以避免遮挡；重合本身即说明其语义边界不清。',
               10.5, 'start', '#8A8A85'))
    return svg(W, H, b)

FIGS = [
    ('fig1', '图 1　主题数选择：一致性曲线', fig_coherence(),
     '横轴为主题数 K（4–9），纵轴为 UMass 一致性。K=9 最高（−0.744），K=8 次之（−0.756），二者差距仅 0.012，'
     '说明数据能支撑的粒度已接近上限——再加主题，边界会开始靠人为切分。这张图是论文中"为什么选这个 K"的唯一依据，必须给出。',
     '方法章 · 模型设定'),
    ('fig2', '图 2　主题份额的历时变化（100% 堆叠）', fig_stack(),
     '清晰的议题迁移：<b>T8 社区双语</b>由 ≤2013 期的 25.9% 跌至 5.7%，<b>T7 语法学史</b>由 21.0% 降至 6.0% 后回稳；'
     '同期 <b>T5 手语/瓜拉尼/翻译</b>从 4.7% 跃升至 16.6%，<b>T9 西语变体</b>在 2019 年后稳定在 15% 上下，'
     '<b>T4 外语课程</b>在 2019–2022 期达到 17.8% 的峰值。整体是从"语言史与语法编纂"向"少数群体语言权利与语言多样性"的转向。',
     '研究问题一 · 主题演化'),
    ('fig3', '图 3　主题 × 时期热力图（数值版）', fig_heat_time(),
     '与图 2 同源，但保留具体数值便于正文引证（如"T5 在 2023–2026 期达 16.6%"）。两图在论文中只保留一张：'
     '做时序比较用图 3，强调构成变化用图 2。',
     '研究问题一 · 主题演化（备选）'),
    ('fig4', '图 4　各主题关键词与小倍数条形', fig_kw(),
     '替代论文里冗长的"主题-词"表格，每个小格展示权重最高的 5 个词，可直接据此命名主题。'
     '这也是审稿人核查"主题是否真的可解释"的主要入口。',
     '研究问题一 · 主题命名'),
    ('fig5', '图 5　主题共现网络', fig_net(),
     '对应老师论文的"主题网络"一步：连边＝两主题共享的前 20 词数量。共享越多，说明语义边界越模糊，解释时需合并或明确区分。'
     '当前 <b>T4–T9（外语课程 vs 西语变体）共享 6 词最高</b>，T1–T3、T2–T3、T7–T9 各共享 3 词，构成网络的主干。',
     '研究问题一 · 主题结构'),
    ('fig6', '图 6　期刊 × 主题交叉分布', fig_venue(),
     '本研究的效度检验：若某主题几乎只由一种期刊贡献，它反映的是<b>期刊定位</b>而非学术议题。'
     '图示 T7 高度集中在 RAHL（该刊本身即语言史学专刊），这类主题在结论中须注明来源偏差。',
     '稳健性检验'),
    ('fig7', '图 7　语料时间轴构成图', fig_timeline(),
     '66 篇逐篇排列，每列色块为该篇的主题概率构成。相比图 2 的时期汇总，这张图保留到篇级——'
     '可以看清单篇的多主题混合程度，也便于定位"转折点"出现在哪几篇文献上。',
     '附录 · 语料概览'),
    ('fig8', '图 8　主题间距离图（LDAvis 风格）', fig_dist(),
     'BERTopic 的 intertopic distance map 在 LDA 下的等价物：圆面积代表主题份额，圆心距离代表词语分布差异。'
     '此处有五个主题原点位几乎重合（T1/T2/T3/T5/T7），说明 K=9 对这份语料已偏大——这也是上一节建议 K 取 7–8 的直接证据。',
     '附录 · 模型诊断'),
]
# ---------------- HTML 组装 ----------------
CSS = """
*{box-sizing:border-box}
body{margin:0;background:#F7F6F3;color:#232323;font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;line-height:1.75;font-size:14px}
.page{max-width:1000px;margin:0 auto;padding:48px 40px 80px;background:#FFFFFF}
h1{font-size:26px;font-weight:600;margin:0 0 6px;letter-spacing:-.3px}
.sub{color:#6B6B66;font-size:13.5px;margin:0 0 22px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 34px}
.chip{background:#F1F3F2;border:1px solid #E3E5E4;border-radius:20px;padding:5px 13px;font-size:12.5px;color:#3E4A4F}
.chip b{font-weight:600;color:#1F3A47}
h2{font-size:18px;font-weight:600;margin:44px 0 10px;padding-bottom:8px;border-bottom:1px solid #E7E7E4}
h3{font-size:14.5px;font-weight:600;margin:26px 0 8px;color:#2E5A73}
p{margin:10px 0}
figure{margin:18px 0 30px;background:#FFFFFF;border:1px solid #E7E7E4;border-radius:10px;padding:18px 18px 14px}
figcaption{margin-top:12px;font-size:12.8px;color:#4A4A46}
figcaption b{color:#1F3A47}
.tag{display:inline-block;background:#EAF0F4;color:#2E5A73;border-radius:4px;padding:1px 7px;font-size:11.5px;margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:12.8px;margin:14px 0}
th,td{border:1px solid #E7E7E4;padding:8px 10px;text-align:left;vertical-align:top}
th{background:#F5F6F5;font-weight:600;color:#2C2C2A}
.note{background:#FBF7EF;border-left:3px solid #C4A04A;padding:12px 16px;margin:20px 0;font-size:13px;color:#4A4237;border-radius:0 6px 6px 0}
.warn{background:#FCF2F1;border-left:3px solid #A8756B;padding:12px 16px;margin:20px 0;font-size:13px;color:#5A3B36;border-radius:0 6px 6px 0}
.flow{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}
.step{flex:1;min-width:150px;background:#F7F8FA;border:1px solid #E3E7EB;border-radius:8px;padding:12px 14px}
.step .n{font-size:11px;color:#8A8A85;letter-spacing:.5px}
.step .t{font-size:13.5px;font-weight:600;margin:2px 0 4px;color:#1F3A47}
.step .d{font-size:12px;color:#5F5E5A;line-height:1.6}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:#F5F6F7;padding:1px 5px;border-radius:3px}
ul{margin:8px 0 8px 18px;padding:0}
li{margin:5px 0}
.foot{margin-top:46px;padding-top:16px;border-top:1px solid #E7E7E4;font-size:12px;color:#8A8A85}
"""

rows = ''.join(
    '<tr><td>T%d</td><td>%s</td><td>%s</td><td>%d</td><td>%.1f%%</td></tr>' %
    (t['id'], LAB[t['id']][0], ', '.join(w for w, _ in t['words'][:6]), t['size'], t['share'] * 100)
    for t in topics)

figs = ''.join(
    '<figure id="%s"><h3 style="margin:0 0 12px">%s</h3>%s<figcaption><span class="tag">%s</span>%s</figcaption></figure>'
    % (fid, title, svgstr, where, cap)
    for fid, title, svgstr, cap, where in FIGS)

FIG_TITLES = ''.join('<h3>%s</h3>' % t for _, t, _, _, _ in FIGS)

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>专家话语语料 · 主题建模仿真报告</title>
<style>%s</style></head><body><div class="page">

<h1>专家话语语料：主题建模可视化方案与预演结果</h1>
<p class="sub">语料：专家数据表_正式版(1).xlsx　·　建模：LDA（Gibbs 采样）预演　·　目标方法：DTM + BERTopic 双轨</p>
<div class="chips">
  <span class="chip">文献 <b>66</b> 篇</span>
  <span class="chip">期刊 <b>17</b> 种</span>
  <span class="chip">年份 <b>1999–2026</b></span>
  <span class="chip">时间片 <b>4</b> 段</span>
  <span class="chip">主题数 <b>K=9</b></span>
  <span class="chip">一致性 <b>-0.744</b></span>
  <span class="chip">平均摘要 <b>193</b> 词</span>
</div>

<h2>一、三种方法各自负责哪张图</h2>
<p>老师的论文用的是"DTM 看演化 + 情感看态度"的组合。你的语料是学术论文摘要而非媒体报道，因此建议把三条技术路线按分工组合，而不是三选一：</p>

<table>
<tr><th style="width:16%%">方法</th><th style="width:30%%">在这份语料里的职责</th><th>能产出的图</th><th style="width:20%%">本报告是否已预演</th></tr>
<tr><td><b>LDA</b><br><span style="color:#8A8A85;font-size:11.5px">2003，词袋统计</span></td>
<td>确定主题体系与命名，是后续两张图的坐标轴。必须先用一致性选出 K。</td>
<td>一致性曲线、主题关键词条形、主题间距离图</td>
<td>已预演（图 1、4、8）</td></tr>
<tr><td><b>DTM</b><br><span style="color:#8A8A85;font-size:11.5px">Blei &amp; Lafferty 2006<br>LdaSeqModel</span></td>
<td>回答"主题如何随时间延续与变化"。学术议题的演化比媒体报道慢，需要按 5 年期切片。</td>
<td>主题份额堆叠图、主题×时期热力图、主题词演化线</td>
<td>已预演近似版（图 2、3）<br><b>真 DTM 需装 gensim</b></td></tr>
<tr><td><b>BERTopic</b><br><span style="color:#8A8A85;font-size:11.5px">2022，语义嵌入</span></td>
<td>对短摘要更稳健，用来<b>交叉验证</b> LDA 的主题划分是否成立，而非替代它。</td>
<td>主题间距离图（UMAP）、层次聚类树、主题相似度热力图、topics_over_time</td>
<td>未预演<br><b>需装 sentence-transformers</b></td></tr>
</table>

<h3>建议的建模范式</h3>
<div class="flow">
  <div class="step"><div class="n">STEP 1</div><div class="t">BERTopic 探索</div><div class="d">语义聚类自动发现主题数与边界，作为"无先验"的参照系</div></div>
  <div class="step"><div class="n">STEP 2</div><div class="t">LDA 定题</div><div class="d">用一致性选出 K，得到可命名的主题词表，便于论文表述</div></div>
  <div class="step"><div class="n">STEP 3</div><div class="t">DTM 看演化</div><div class="d">固定主题数，按时间片估计主题强度轨迹</div></div>
  <div class="step"><div class="n">STEP 4</div><div class="t">一致性检验</div><div class="d">比较两法的主题归属（ARI/NMI），报告一致率</div></div>
</div>
<p style="font-size:12.8px;color:#5F5E5A">这样做的额外好处：审稿人常质疑"主题数是你凑出来的"。有 BERTopic 的自动结果为参照，K 的选择就不再是主观决定。</p>

<h2>二、主题体系（K=9，预演结果）</h2>
<p>下表是 LDA 在 66 篇语料上收敛后的主题清单。<b>主题名称需由你人工命名</b>——这是主题建模不可省略的一步，也是论文方法论必须写明的环节。</p>
<table>
<tr><th style="width:8%%">编号</th><th style="width:26%%">建议命名</th><th>主题词（前 6）</th><th style="width:10%%">主导篇数</th><th style="width:10%%">份额</th></tr>
%s
</table>
<div class="note"><b>读表提示：</b>T2 同时含 "política / Buenos Aires / china / escritura"，是因为首都语言政策与中文书写教学两类文献共享了地理与制度词汇；T5（手语/瓜拉尼/翻译）与 T8（社区双语/聋人）存在部分重叠，是 K=9 时主题偏细的表现。若你希望主题更聚合，取 K=7 或 K=8。</div>

<h2>三、八张可视化结果（附真实数据的预演）</h2>
<p>下面每张图都是用你这 66 篇的真实摘要跑出来的，不是示意图。图下标注了它在论文里的位置与读法。</p>
%s

<h2>四、装了 BERTopic 之后还会多出三张图</h2>
<p>这三张图是本机当前无法生成的（离线环境装不了 sentence-transformers），但它们是 BERTopic 相对 LDA 的主要增量，建议补上：</p>
<table>
<tr><th style="width:26%%">图</th><th>作用</th><th style="width:30%%">对应代码</th></tr>
<tr><td><b>主题间距离图</b><br>Intertopic Distance Map</td><td>UMAP 二维投影，圆面积＝主题规模。比图 8 更可靠，因为它基于语义向量而非词频。</td><td class="mono">model.visualize_topics()</td></tr>
<tr><td><b>层次聚类树</b><br>Hierarchical Dendrogram</td><td>展示主题如何逐级合并，用于论证"为什么这些主题不能进一步合并"。</td><td class="mono">model.visualize_hierarchy()</td></tr>
<tr><td><b>主题演化图</b><br>Topics over Time</td><td>按年份追踪主题强度，是 DTM 的可视化替代品，且不需要额外模型。</td><td class="mono">model.topics_over_time(docs, timestamps)</td></tr>
</table>

<h2>五、情感分析（老师论文的第二部分）能不能照搬</h2>
<p>老师用 <span class="mono">pysentimiento</span> 对西班牙语文本做正负向识别，再按主题归属加权汇总。你的语料可以复用这条路径，但有一处必须调整：</p>
<ul>
<li><b>对象不同。</b>媒体文本有明确的评价立场（赞扬/批评某政策），学术摘要的情感极性极弱，多数为中性陈述。直接算正负值，结果大概率集中在 0 附近，缺乏区分度。</li>
<li><b>建议改写指标。</b>把"情感极性"换成<b>立场性词汇密度</b>：统计每篇摘要中评价性表达（如 <span class="mono">crítico, necesario, limitado, ausencia, déficit, desigualdad</span>）的比例，作为"批判性话语强度"，再按主题与时期汇总。这在学术语料上是可解释的，也比强行套情感模型更站得住。</li>
<li>若坚持用 pysentimiento，建议只保留 <span class="mono">positivo/negativo/neutro</span> 三分类的"非中性比例"作为指标，并在方法章说明学术文本的中性偏置。</li>
</ul>

<h2>六、方法与限制（写进论文 limitation 的部分）</h2>
<div class="warn">
<p><b>1. 语料规模偏小。</b>66 篇、平均摘要 193 词，有效词表仅 820 词。LDA 在千篇以下语料上主题稳定性有限——换随机种子重跑，主题边界会变化。建议：(a) 报告 3–5 次不同种子的结果并取共识；(b) 把六库那 230 篇阿根廷期刊文献并入，规模立刻翻三倍。</p>
<p><b>2. 文本单元是摘要，不是全文。</b>摘要高度压缩，套语（"本文分析…""结果表明…"）会稀释主题信号。若要用 DTM 做严谨的历时比较，应抓全文或至少"引言 + 结论"。</p>
<p><b>3. 混合语言。</b>语料含西班牙语、英语、葡萄牙语三种，共用一套西语停用词表会让英语文献的词频偏高。正式建模建议按语言分层或统一翻译后再建模，并在方法中说明。</p>
<p><b>4. DTM 的时间片不可过细。</b>1999–2013 共 9 篇，若切成年度序列，多数年份只有 0–3 篇，LdaSeqModel 无法估计。合并为 4 段（≤2013 / 2014–2018 / 2019–2022 / 2023–2026）是当前数据能支撑的最细粒度。</p>
</div>

<h2>七、下一步可执行的事</h2>
<ul>
<li><b>A. 出正式版结果</b>：把 9 个主题的归属写回 Excel 新增列（主题编号、主导概率、关键词），并附主题-文献对照表。</li>
<li><b>B. 扩样后重跑</b>：把 230 篇六库语料并入，K 会稳定很多，DTM 也能切到 6–7 个时间片。</li>
<li><b>C. 补 BERTopic</b>：需要联网安装 <span class="mono">bertopic sentence-transformers</span>，装好后我可以直接跑并生成上面第四节的四张图。</li>
<li><b>D. 情感/立场指标</b>：按第五节的替代方案，构建立场词表并生成"批判性话语强度 × 主题 × 时期"三交叉图。</li>
</ul>

<div class="foot">预演参数：collapsed Gibbs 采样，α=0.1，β=0.02，迭代 260 次，K 在 4–9 间以 UMass 一致性择优；词表 min_df=2、max_df=0.55，共 820 词；西语轻量词干化；时间片按发表年划分。<br>
本报告所有图表均由该语料实际计算生成，可用于方法验证；因语料规模限制，主题边界在正式论文中需以多随机种子共识结果确认。</div>

</div></body></html>""" % (CSS, rows, figs)

out = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家话语_主题建模_可视化方案.html'
io.open(out, 'w', encoding='utf-8').write(html)
print('written', out, len(html))
