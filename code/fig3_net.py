# -*- coding: utf-8 -*-
"""图 3 主题网络图（关键词共现网络，标签即节点）
9 个主题节点 + 每主题后验概率前 15 位主题词：词的文字本身作为网络节点（字号 ∝ β），
连线为语料 10 词窗口共现 / 词属主题 / 主题间共享词数。
标签位置用「候选方向 × 候选距离 + 迭代下降」做碰撞避让，保证不压字、不出框。
数值全部来自 work/lab_results.json 与同一语料，仅改变呈现方式。
"""
import os, sys, json, io, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.collections import LineCollection
import matplotlib.patheffects as pe

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

if os.environ.get('OFF') == '1':
    import net_data_off as net_data
else:
    import net_data

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('FIG_OUT') or r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/图'
NO_CAP = os.environ.get('NO_CAP') == '1'
os.makedirs(OUT, exist_ok=True)

PAL = ['#4A8E94', '#4198AC', '#7BC0CD', '#BFDFD2', '#DBCB92', '#ECB66C', '#EA9E58', '#ED8D5A', '#9C5C4A',
       '#3E5C76', '#6B8F71', '#8C6D4F']
TXT = ['#2C666B', '#276B7C', '#2A7C8D', '#4C8A6F', '#8A7434', '#AE6E22', '#BB6321', '#BF4E2B', '#8A4534',
       '#31485E', '#4C6E55', '#6E5438']
CAP_BG = '#DCEDDF'

IS_OFF = os.environ.get('OFF') == '1'
CARD = os.environ.get('CARD') == '1'      # 1 = 词卡版（备用），默认用散点标签版
W_CAP = 0.46        # 官方版单词的最大宽度（数据单位）

if IS_OFF:          # 官方版：12 簇 × 15 词，散点标签，字号加大到可读
    TOPN = int(os.environ.get('TOPN', '15'))
    FS_MIN = float(os.environ.get('FSMIN', '9.6'))
    FS_MAX = float(os.environ.get('FSMAX', '11.6'))
    FS_ID, FS_SH = 9.4, 8.2
else:               # 专家版交付口径（9 簇 × 15 词，环形锚点）
    TOPN = 15
    FS_MIN, FS_MAX = 6.2, 8.3
    FS_ID, FS_SH = 7.3, 6.9

W_BASE, H_BASE = 11.0, 10.2
RX, RY = 0.95, 0.95
RINGS = (0.155, 0.265, 0.375, 0.485)
COUNTS = (4, 4, 4, 3)
HALF = (30.0, 34.0, 38.0, 42.0)

ANG = np.deg2rad(np.arange(0.0, 360.0, 11.25 if os.environ.get('OFF') != '1' else 7.5))
COTH = int(os.environ.get('COTH', '6'))
if os.environ.get('OFF') == '1':     # 官方版：候选位移放宽，允许标签在簇内自由找位
    DD = np.array([0.006, 0.012, 0.020, 0.030, 0.042, 0.056, 0.072, 0.090,
                   0.110, 0.135, 0.163, 0.195, 0.232, 0.274, 0.320])
else:
    DD = np.array([0.004, 0.009, 0.015, 0.023, 0.033, 0.045, 0.058, 0.073, 0.090, 0.110])


# ---------------------------------------------------------------- 布局
def topic_angles(words, edges, need):
    """先弹簧定序（共享词多的主题相邻），再按各簇标签面积分配扇区宽度。"""
    K = len(words)
    R = np.random.RandomState(11)
    pos = R.randn(K, 2) * 0.5
    pos /= np.linalg.norm(pos, axis=1, keepdims=True)
    wmat = np.zeros((K, K))
    for e in edges:
        wmat[e['a'] - 1, e['b'] - 1] = wmat[e['b'] - 1, e['a'] - 1] = e['w']
    for _ in range(600):
        f = np.zeros_like(pos)
        for i in range(K):
            for j in range(i + 1, K):
                d = pos[i] - pos[j]
                dist = max(np.linalg.norm(d), 1e-4)
                dirv = d / dist
                f[i] += dirv * (0.20 / dist ** 2)
                f[j] -= dirv * (0.20 / dist ** 2)
                if wmat[i, j] > 0:
                    f[i] -= dirv * 0.034 * wmat[i, j] * (dist - 1.0)
                    f[j] += dirv * 0.034 * wmat[i, j] * (dist - 1.0)
        pos += 0.30 * f
        pos *= 1.0 / max(1e-9, np.linalg.norm(pos, axis=1).max())
    ang = np.arctan2(pos[:, 1], pos[:, 0])
    order = np.argsort(ang)

    widths = 2 * np.pi * (need / need.sum())
    centers = np.zeros(K)
    cur = ang[order[0]] - widths[order[0]] / 2
    for k in range(K):
        i = order[k]
        centers[i] = cur + widths[i] / 2
        cur += widths[i]
    return centers, widths


def anchors_of(tpos, words, widths=None):
    """每簇 15 个词的理想位置：沿外向扇区环排布；扇区半角按各簇份额宽度自适应。"""
    K = len(words)
    if widths is None:
        widths = np.full(K, 2 * np.pi / K)
    base = 2 * np.pi / 9                       # 9 簇为基准口径
    kw, k0, owner = [], [], []
    for k in range(len(words)):
        c = tpos[k]
        u = c / max(np.linalg.norm(c), 1e-9)
        v = np.array([-u[1], u[0]])
        shrink = min(1.0, widths[k] / base)    # 簇多时扇区变窄，等比收紧半角
        idx = 0
        for r_i, cnt in enumerate(COUNTS):
            rad = RINGS[r_i]
            half = math.radians(HALF[r_i]) * 0.86 * shrink
            for j in range(cnt):
                if idx >= len(words[k]):
                    break
                w, p = words[k][idx]
                a = (j - (cnt - 1) / 2) * (2 * half / max(1, cnt - 1))
                kw.append((k, w, p))
                k0.append(c + u * (rad * math.cos(a)) + v * (rad * math.sin(a)))
                owner.append(k)
                idx += 1
    return kw, np.array(k0), np.array(owner)


def anchors_spiral(tpos, words, r0=0.125, dr=0.036):
    """每簇的词按黄金角螺旋锚定在簇周围：锚点本身已散开，碰撞优化只需微调。"""
    kw, k0, owner = [], [], []
    for k, ws in enumerate(words):
        c = tpos[k]
        for i, (w, p) in enumerate(ws):
            a = i * 2.39996                       # 黄金角，避免同心排布
            kw.append((k, w, p))
            k0.append(c + np.array([math.cos(a), math.sin(a)]) * (r0 + dr * i))
            owner.append(k)
    return kw, np.array(k0), np.array(owner)


def anchors_col(tpos, words, r_top, colh, wcol, gap):
    """每簇的关键词在主题圆外侧排成一个竖直词列（列内按 β 降序、自上而下），
    列中心沿径向偏移，偏移量随该簇朝向自适应：竖直方向的簇要让开列的半高，
    水平方向的簇要让开列的半宽，保证词列不压主题圆。"""
    kw, k0, owner = [], [], []
    for k, ws in enumerate(words):
        c = tpos[k]
        nrm = max(np.linalg.norm(c), 1e-9)
        u = c / nrm
        off = r_top[k] + 0.055 + 0.5 * (abs(u[1]) * colh + abs(u[0]) * wcol[k])
        col = c + u * off
        n = len(ws)
        for i, (w, p) in enumerate(ws):
            kw.append((k, w, p))
            k0.append(col + np.array([0.0, ((n - 1) / 2 - i) * gap]))
            owner.append(k)
    return kw, np.array(k0), np.array(owner)


def anchors_chain(tpos, words, start, step):
    """每簇关键词沿外向射线等距成链：词按 β 由内向外，链起点在主题圆外侧。
    半径与层距由字号决定，保证同链不叠、邻链不撞。"""
    kw, k0, owner = [], [], []
    for k in range(len(words)):
        c = tpos[k]
        u = c / max(np.linalg.norm(c), 1e-9)
        for i, (w, p) in enumerate(words[k]):
            kw.append((k, w, p))
            k0.append(c + u * (start + i * step))
            owner.append(k)
    return kw, np.array(k0), np.array(owner)


# ---------------------------------------------------------------- 标签避让
def _cands(cx, cy, wd, hd):
    A = ANG[:, None]
    D = DD[None, :]
    xs = cx + np.cos(A) * D
    ys = cy + np.sin(A) * D
    A2 = np.broadcast_to(A, xs.shape)
    D2 = np.broadcast_to(D, xs.shape)
    left = np.cos(A2) >= 0
    x0 = np.where(left, xs, xs - wd)
    x1 = x0 + wd
    y0 = ys - hd / 2
    y1 = ys + hd / 2
    B = np.stack([x0.ravel(), y0.ravel(), x1.ravel(), y1.ravel()], 1)
    return B, xs.ravel(), ys.ravel(), left.ravel(), D2.ravel(), A2.ravel()


def _ov(B, O, w, pad=0.0):
    if len(O) == 0:
        return np.zeros(len(B))
    ox = (np.minimum(B[:, 2:3], O[None, :, 2] + pad) -
          np.maximum(B[:, 0:1], O[None, :, 0] - pad))
    oy = (np.minimum(B[:, 3:4], O[None, :, 3] + pad) -
          np.maximum(B[:, 1:2], O[None, :, 1] - pad))
    return (np.clip(ox, 0, None) * np.clip(oy, 0, None) * w[None, :]).sum(1)


def place_labels(anchor, wd, hd, outward, order, sb, sw, lim, ctr=None, rmax=0.34):
    N = len(anchor)
    cand = [_cands(anchor[i, 0], anchor[i, 1], wd[i], hd[i]) for i in range(N)]
    boxes = np.zeros((N, 4))
    ocost = np.zeros(N)
    cidx = np.zeros(N, dtype=int)

    def cost(i):
        B, xs, ys, left, D, A = cand[i]
        mask = np.ones(N, dtype=bool)
        mask[i] = False
        c = 900.0 * _ov(B, sb, sw, 0.012 if not IS_OFF else 0.020) + \
            1200.0 * _ov(B, boxes[mask], np.ones(int(mask.sum())),
                         0.013 if not IS_OFF else 0.024)
        c = c + (0.25 if IS_OFF else 0.85) * D + (0.12 if IS_OFF else 0.55) * (1 - np.cos(A - outward[i]))
        if ctr is not None:               # 向心约束：不许飘到别的簇地盘
            bx = (B[:, 0] + B[:, 2]) / 2
            by = (B[:, 1] + B[:, 3]) / 2
            dd = np.hypot(bx - ctr[i, 0], by - ctr[i, 1])
            c = c + 6.0 * np.clip(dd - rmax, 0, None)
        bad = ((B[:, 0] < lim[0]) | (B[:, 2] > lim[1]) |
               (B[:, 1] < lim[2]) | (B[:, 3] > lim[3]))
        c = c + 1e4 * bad
        return c

    for i in order:                       # 贪心初始：高 β 先占位
        c = cost(i)
        k = int(np.argmin(c))
        boxes[i] = cand[i][0][k]
        ocost[i] = c[k]
        cidx[i] = k

    R = np.random.RandomState(3)
    for _ in range(30 if IS_OFF else 14):  # 迭代下降：逐条重选最优候选
        moved = 0
        seq = order.copy()
        R.shuffle(seq)
        for i in seq:
            c = cost(i)
            k = int(np.argmin(c))
            if c[k] < c[cidx[i]] - 1e-9:  # 与"当前位置"同口径比较
                boxes[i] = cand[i][0][k]
                cidx[i] = k
                ocost[i] = c[k]
                moved += 1
        if moved == 0:
            break
    return boxes, ocost


def measure(ax, fig, strings, fs, weight='normal'):
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    out = []
    for s in strings:
        t = ax.text(0, 0, s, fontsize=fs, fontweight=weight)
        bb = t.get_window_extent(rend)
        out.append((bb.width, bb.height))
        t.remove()
    k = fig.dpi / 72.0
    return np.array([(w / k, h / k) for w, h in out])


def set_lim(ax, lim):
    ax.set_xlim(lim[0], lim[1])
    ax.set_ylim(lim[2], lim[3])


def ppu_of(ax, fig):
    fig.canvas.draw()
    bb = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return min(bb.width / (x1 - x0), bb.height / (y1 - y0)) * 72 / fig.dpi


def enter_point(p, q, box):
    """从 p 指向 q 的射线与矩形 box 的首个交点（p 在 box 内则返回 p）。"""
    x0, y0, x1, y1 = box
    dx, dy = q[0] - p[0], q[1] - p[1]
    ts = []
    if abs(dx) > 1e-12:
        for X in (x0, x1):
            t = (X - p[0]) / dx
            if -1e-9 <= t <= 1.0:
                y = p[1] + t * dy
                if y0 - 1e-9 <= y <= y1 + 1e-9:
                    ts.append(t)
    if abs(dy) > 1e-12:
        for Y in (y0, y1):
            t = (Y - p[1]) / dy
            if -1e-9 <= t <= 1.0:
                x = p[0] + t * dx
                if x0 - 1e-9 <= x <= x1 + 1e-9:
                    ts.append(t)
    if not ts:
        return np.array(q, dtype=float)
    t = min(ts)
    return np.array([p[0] + t * dx, p[1] + t * dy])


# ---------------------------------------------------------------- 出图
def make(fname='图3_主题网络图.png'):
    d = net_data.load(TOPN)
    topics, words = d['topics'], d['words']
    D = net_data.D
    edges = D['edges']
    share = np.array([t['share'] for t in topics])
    K = len(topics)
    # 画布随簇数放大：每簇标签面积近似线性增长
    scale = 1.0 if K <= 9 else (K / 9.0) ** 0.5
    if IS_OFF:
        scale *= float(os.environ.get('SCALE', '1.24'))   # 官方版再多留一成余量，给放大后的字号
    W, H = W_BASE * scale, H_BASE * scale
    kw_labels = [w for ws in words for w, _ in ws]
    pvals = np.array([p for ws in words for _, p in ws])
    fs = FS_MIN + (FS_MAX - FS_MIN) * np.sqrt(pvals / pvals.max())

    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_aspect('equal')
    ax.axis('off')
    base = 1.75 * scale * float(os.environ.get('BASEF', '0.96'))   # 画布随簇数放大，边界同步外扩
    lim = [-base, base, -base * (0.94 * H) / (0.98 * W), base * (0.94 * H) / (0.98 * W)]
    set_lim(ax, lim)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.995,
                        bottom=0.055 if not NO_CAP else 0.008)

    ppu = ppu_of(ax, fig)
    raw = measure(ax, fig, kw_labels, 10.0) / ppu          # 10pt 基准尺寸（数据单位）
    if IS_OFF:
        fs = np.round(fs * 2) / 2                          # 0.5pt 档，便于逐档精测
        kwsz = np.zeros((len(fs), 2))
        for qf in np.unique(fs):                           # 按实际字号逐档测量，消除线性外推误差
            sel = np.where(fs == qf)[0]
            kwsz[sel] = measure(ax, fig, [kw_labels[i] for i in sel], float(qf)) / ppu
        kwsz = kwsz * np.array([1.03, 1.02])
    else:
        kwsz = raw * (fs / 10.0)[:, None]
    idsz = measure(ax, fig, ['topic%d' % t['id'] for t in topics], FS_ID, 'bold') / ppu
    shsz = measure(ax, fig, ['%.1f%%' % (s * 100) for s in share], FS_SH) / ppu

    need = np.array([np.sum(kwsz[kk * TOPN:(kk + 1) * TOPN, 0] *
                             kwsz[kk * TOPN:(kk + 1) * TOPN, 1]) for kk in range(K)])
    need = 0.30 + need / need.max()

    centers, widths = topic_angles(words, edges, need)

    r_top = np.maximum((0.086 if not IS_OFF else 0.104) + 0.020 * np.sqrt(share / share.max()),
                       0.5 * np.maximum(idsz[:, 0], shsz[:, 0]) + 0.016)
    share_y = 0.046

    if CARD:
        # 备用词卡版：每簇的词排成一列，环半径由"相邻列不互撞"反推
        gap = float(kwsz[:, 1].max()) * 1.20
        colh = (TOPN - 1) * gap
        wcol = np.array([float(kwsz[k * TOPN:(k + 1) * TOPN, 0].max()) for k in range(K)])
        rr = max(float(r_top.max()) * 1.18 / math.sin(math.pi / K),
                 (wcol.sum() + K * 0.13) / (2 * math.pi))
        RX = RY = rr
        tpos = np.stack([np.cos(centers) * RX, np.sin(centers) * RY], 1)
        kw, anchor, owner = anchors_col(tpos, words, r_top, colh, wcol, gap)
    else:
        rr = 0.95 * scale * float(os.environ.get('RRF', '1.02'))
        RX = RY = rr
        tpos = np.stack([np.cos(centers) * RX, np.sin(centers) * RY], 1)
        kw, anchor, owner = anchors_of(tpos, words, widths)

    sb, sw = [], []
    for k in range(K):                     # 主题圆 + 编号/份额文字（均为障碍）
        cx, cy = tpos[k]
        sb.append([cx - r_top[k] - 0.008, cy - r_top[k] - 0.008,
                   cx + r_top[k] + 0.008, cy + r_top[k] + 0.008]); sw.append(8.0)
        sb.append([cx - idsz[k, 0] / 2 - 0.004, cy + share_y - idsz[k, 1] / 2 - 0.004,
                   cx + idsz[k, 0] / 2 + 0.004, cy + share_y + idsz[k, 1] / 2 + 0.004]); sw.append(2.0)
        sb.append([cx - shsz[k, 0] / 2 - 0.004, cy - share_y - shsz[k, 1] / 2 - 0.004,
                   cx + shsz[k, 0] / 2 + 0.004, cy - share_y + shsz[k, 1] / 2 + 0.004]); sw.append(2.0)

    rows = ['主题节点：编号 + 份额',
            '主题词：后验概率前 %d 位，字号 ∝ β' % TOPN,
            '粗线：两主题共享词数（1–6）',
            '细线：词间窗口共现 / 词属主题']
    lfs = 7.0 * (1.30 if IS_OFF else 1.0)
    lw_ = measure(ax, fig, rows, lfs) / ppu
    box_w = 0.150 + lw_[:, 0].max() + 0.022
    box_h = 0.300 * (1.30 if IS_OFF else 1.0)
    lx, ly = 0.0, 0.03
    sb.append([lx - box_w / 2, ly - box_h / 2 + 0.02,
               lx + box_w / 2, ly + box_h / 2 + 0.02]); sw.append(3.0)

    outward = np.arctan2(anchor[:, 1] - tpos[owner][:, 1],
                         anchor[:, 0] - tpos[owner][:, 0])
    order = np.argsort(-pvals)
    if CARD:
        boxes = np.stack([anchor[:, 0] - kwsz[:, 0] / 2, anchor[:, 1] - kwsz[:, 1] / 2,
                          anchor[:, 0] + kwsz[:, 0] / 2, anchor[:, 1] + kwsz[:, 1] / 2], 1)
        ocost = np.zeros(len(kw))
    else:
        boxes, ocost = place_labels(anchor, kwsz[:, 0], kwsz[:, 1], outward, order,
                                    np.array(sb), np.array(sw), lim)
    cent = np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2], 1)

    # ---- 主题—主题连线（裁到圆边） ----
    segs, lws = [], []
    for e in edges:
        a, b = tpos[e['a'] - 1], tpos[e['b'] - 1]
        u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        segs.append([a + u * (r_top[e['a'] - 1] + 0.006), b - u * (r_top[e['b'] - 1] + 0.006)])
        lws.append(0.5 + 0.36 * e['w'])
    ax.add_collection(LineCollection(segs, colors='#9AA6A1', linewidths=lws,
                                     alpha=0.42, zorder=1, capstyle='round'))

    # ---- 词—词共现连线（两端裁到文字框） ----
    segs, lws, cols = [], [], []
    name2i = {(k, w): i for i, (k, w, p) in enumerate(kw)}
    co = d['co']
    for k, ws in enumerate(words):
        names = [w for w, _ in ws]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = sorted((names[i], names[j]))
                c = co.get((a, b), 0)
                if c < COTH:
                    continue
                ia, ib = name2i[(k, a)], name2i[(k, b)]
                segs.append([cent[ia], cent[ib]])
                lws.append(0.26 + 0.062 * min(c, 18))
                cols.append(PAL[k])
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws,
                                     alpha=0.22, zorder=1))

    # ---- 主题—词连线 ----
    segs, cols = [], []
    for i in range(len(kw)):
        u = (cent[i] - tpos[owner[i]]) / max(np.linalg.norm(cent[i] - tpos[owner[i]]), 1e-9)
        p0 = tpos[owner[i]] + u * (r_top[owner[i]] + 0.006)
        segs.append([p0, cent[i]])
        cols.append(PAL[kw[i][0]])
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.42,
                                     alpha=0.26 if IS_OFF else 0.17, zorder=1))

    # ---- 主题节点 ----
    for k in range(K):
        ax.add_patch(Circle(tpos[k], r_top[k], facecolor=PAL[k], edgecolor='white',
                            lw=1.6, alpha=1.0, zorder=6))

    # ---- 主题色底条（把每列词包成一张卡片，同时压住穿过的连线） ----
    if CARD:
        for k in range(K):
            sel = owner == k
            bx0, bx1 = boxes[sel, 0].min() - 0.036, boxes[sel, 2].max() + 0.036
            by0, by1 = boxes[sel, 1].min() - 0.032, boxes[sel, 3].max() + 0.032
            # 不透明「白 + 主题色 13%」底色：既压住穿过的连线，又不留半透明叠影
            c = np.array(plt.matplotlib.colors.to_rgb(PAL[k]))
            face = 1.0 - 0.13 * (1.0 - c)
            ax.add_patch(Rectangle((bx0, by0), bx1 - bx0, by1 - by0,
                                   facecolor=face, edgecolor=0.55 + 0.45 * c, lw=0.9,
                                   zorder=2.2))
        # 官方版：卡片已在连线之上，无需白底衬（否则会切出白色条带）
    else:
        # ---- 关键词标签白底衬（遮住穿字的连线） ----
        pad = 1.3 / ppu
        for i in range(len(kw)):
            x0, y0, x1, y1 = boxes[i]
            ax.add_patch(Rectangle((x0 - pad, y0 - pad * 0.6), (x1 - x0) + 2 * pad,
                                   (y1 - y0) + 1.2 * pad, facecolor='white',
                                   edgecolor='none', zorder=7))

    # ---- 关键词标签 ----
    txs = []
    for i in range(len(kw)):
        x0, y0, x1, y1 = boxes[i]
        left = (x0 + x1) / 2 >= anchor[i, 0]
        if CARD:
            txs.append(ax.text((x0 + x1) / 2, (y0 + y1) / 2, kw_labels[i], fontsize=fs[i],
                               ha='center', va='center', color=TXT[kw[i][0]], zorder=8,
                               fontweight='bold' if i % TOPN == 0 else 'normal'))
        else:
            txs.append(ax.text(x0 if left else x1, (y0 + y1) / 2, kw_labels[i], fontsize=fs[i],
                               ha='left' if left else 'right', va='center', color=TXT[kw[i][0]],
                               zorder=8,
                               path_effects=[pe.withStroke(linewidth=1.5, foreground='white')]))
    if os.environ.get('DEBUG') == '1':
        fig.canvas.draw(); rend = fig.canvas.get_renderer()
        dev = []
        for i, t in enumerate(txs):
            bb = t.get_window_extent(rend)
            bx = ax.transData.inverted().transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            dev.append([bx[0, 0] - boxes[i, 0], bx[0, 1] - boxes[i, 1],
                        bx[1, 0] - boxes[i, 2], bx[1, 1] - boxes[i, 3]])
        dev = np.array(dev)
        print('bbox dev  dx0 %.4f dy0 %.4f dx1 %.4f dy1 %.4f' %
              tuple(dev.min(0)), tuple(dev.max(0)), flush=True)
        for i in range(len(kw)):
            if kw_labels[i] in ('aprendizaje', 'programa'):
                bx = ax.transData.inverted().transform(
                    [[txs[i].get_window_extent(rend).x0, txs[i].get_window_extent(rend).y0],
                     [txs[i].get_window_extent(rend).x1, txs[i].get_window_extent(rend).y1]])
                print('  %-12s box %s bbox_x %.4f %.4f' %
                      (kw_labels[i], np.round(boxes[i], 4), bx[0, 0], bx[1, 0]), flush=True)

    # ---- 主题编号与份额 ----
    for k, t in enumerate(topics):
        cx, cy = tpos[k]
        if K <= 9:      # 专家版交付口径：按簇硬编码
            col = 'white' if k in (0, 1, 6, 7, 8) else '#2C3A35'
        else:           # 通用：按底色亮度自动选深/浅
            def _lum(hc):
                hc = hc.lstrip('#')
                return 0.299 * int(hc[0:2], 16) + 0.587 * int(hc[2:4], 16) + 0.114 * int(hc[4:6], 16)
            col = '#2C3A35' if _lum(PAL[k]) > 165 else 'white'
        lab = 'topic%d' % t['id']
        ax.text(cx, cy + share_y, lab, fontsize=FS_ID, fontweight='bold',
                ha='center', va='center', color=col, zorder=10)
        ax.text(cx, cy - share_y, '%.1f%%' % (t['share'] * 100), fontsize=FS_SH,
                ha='center', va='center', color=col, alpha=0.95, zorder=10)

    # ---- 图心图例 ----
    zs = 1.30 if IS_OFF else 1.0
    ax.add_patch(Rectangle((lx - box_w / 2, ly - box_h / 2 + 0.02), box_w, box_h,
                           facecolor='white', edgecolor='#E2E6E3', lw=0.8,
                           alpha=0.93, zorder=11))
    ax.text(lx - box_w / 2 + 0.022 * zs, ly + box_h / 2 - 0.024 * zs, '读图',
            fontsize=7.8 * zs, color='#6E746F', zorder=12)
    y0 = ly + 0.075 * zs
    for i, txt in enumerate(rows):
        yy = y0 - 0.060 * zs * i
        col = lx - box_w / 2
        if i == 0:
            ax.add_patch(Circle((col + 0.050 * zs, yy), 0.025 * zs, facecolor='#8E9A96',
                                edgecolor='white', lw=0.6, zorder=12))
        elif i == 1:
            ax.text(col + 0.050 * zs, yy, 'Aa', fontsize=6.6 * zs, ha='center', va='center',
                    color='#4C8A6F', zorder=12)
        elif i == 2:
            ax.plot([col + 0.028 * zs, col + 0.072 * zs], [yy, yy], color='#9AA6A1', lw=1.5,
                    alpha=0.9, zorder=12, solid_capstyle='round')
        else:
            ax.plot([col + 0.028 * zs, col + 0.072 * zs], [yy, yy], color='#B9C1BD', lw=0.7,
                    alpha=0.9, zorder=12)
        ax.text(col + 0.090 * zs, yy, txt, fontsize=lfs, va='center', color='#3A403C', zorder=12)

    # ---- 按标签实际包围盒收边，避免画布四周留白过大 ----
    if IS_OFF:                     # 固定坐标范围，避免收边改变 ppu 后标签溢出碰撞盒
        set_lim(ax, lim)
        allx = None
    else:
        allx = np.concatenate([boxes[:, 0], boxes[:, 2]])
    if not IS_OFF:
      ally = np.concatenate([boxes[:, 1], boxes[:, 3]])
      px = 0.030 * (allx.max() - allx.min())
      py = 0.030 * (ally.max() - ally.min())
      cx, cy = (allx.min() + allx.max()) / 2, (ally.min() + ally.max()) / 2
      bw, bh = (allx.max() - allx.min()) + 2 * px, (ally.max() - ally.min()) + 2 * py
      ar = (0.94 * H) / (0.98 * W)        # 画布纵横比，短边补齐，保证等比例不留异形留白
      if bh / bw < ar:
          bh = bw * ar
      else:
          bw = bh / ar
      set_lim(ax, [cx - bw / 2, cx + bw / 2, cy - bh / 2, cy + bh / 2])

    if not NO_CAP:
        fig.add_artist(Rectangle((0, 0), 1, 0.052, transform=fig.transFigure,
                                 facecolor=CAP_BG, edgecolor='none', zorder=0))
        fig.text(0.5, 0.026, '图 3. 主题网络图', ha='center', va='center',
                 fontsize=13, color='#1A1A1A')

    fig.subplots_adjust(left=0.01, right=0.99, top=0.995, bottom=0.055)
    p = os.path.join(OUT, fname)
    fig.savefig(p, dpi=320)
    plt.close(fig)

    ov, mx = 0, 0.0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ox = min(boxes[i, 2], boxes[j, 2]) - max(boxes[i, 0], boxes[j, 0])
            oy = min(boxes[i, 3], boxes[j, 3]) - max(boxes[i, 1], boxes[j, 1])
            if ox > 0 and oy > 0:
                ov += 1
                mx = max(mx, ox * oy)
    out = ((boxes[:, 0] < lim[0]) | (boxes[:, 2] > lim[1]) |
           (boxes[:, 1] < lim[2]) | (boxes[:, 3] > lim[3])).sum()
    print('saved', fname, 'labels', len(kw), 'pairs_overlap', ov, 'max_overlap %.5f' % mx,
          'out_of_bounds', int(out), 'maxcost %.3f' % ocost.max(), flush=True)


if __name__ == '__main__':
    make()
