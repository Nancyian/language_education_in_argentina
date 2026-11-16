# -*- coding: utf-8 -*-
"""按参考图版式重制 7 张图：matplotlib 学术风格 + 海洋清风配色 + 浅绿图注条"""
import json, io, math, collections, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'

OUT = os.environ.get('FIG_OUT') or r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/图'
NO_CAP = os.environ.get('NO_CAP') == '1'
os.makedirs(OUT, exist_ok=True)

D = json.load(io.open('work/lab_results.json', encoding='utf-8'))
K = D['K']; topics = D['topics']; years = D['years']
YT = {int(k): v for k, v in D['year_theta'].items()}
YP = {int(k): v for k, v in D['year_pol'].items()}

PAL = ['#4A8E94', '#4198AC', '#7BC0CD', '#BFDFD2', '#DBCB92', '#ECB66C', '#EA9E58', '#ED8D5A', '#9C5C4A']
CMAP = LinearSegmentedColormap.from_list('ocean', ['#FFFDF6', '#DBCB92', '#ECB66C', '#ED8D5A', '#A84A2E'])
CAP_BG = '#DCEDDF'

KW2 = {t['id']: '%s / %s' % (t['words'][0][0], t['words'][1][0]) for t in D['topics']}

SHORT = {
 'RAHL: Revista argentina de historiografía lingüística': 'RAHL',
 'Traslaciones: Revista Latinoamericana de Lectura y Escritura': 'Traslaciones',
 'Quintú Quimün: revista de lingüística': 'Quintú Quimün',
 'Signos ELE: Revista de Español como Lengua Extranjera': 'Signos ELE',
 'Revista Argentina de Educación Superior (RAES)': 'RAES',
 'Revista Latinoamericana de Educación Comparada (RELEC)': 'RELEC',
 'Revista Argentina de Ciencias del Comportamiento (RACC)': 'RACC',
}

def short(v):
    if v in SHORT: return SHORT[v]
    return v.split(':')[0][:30]

def cap(fig, text, fs=13):
    if NO_CAP:
        return
    fig.add_artist(Rectangle((0, 0), 1, 0.060, transform=fig.transFigure,
                             facecolor=CAP_BG, edgecolor='none', zorder=0))
    fig.text(0.5, 0.030, text, ha='center', va='center', fontsize=fs, color='#1A1A1A')

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=320)
    plt.close(fig)
    print('saved', name, flush=True)

# ============ 图1 年度主题堆叠柱 ============
def fig1():
    yr = list(years)
    cnt = {y: [0] * K for y in yr}
    for d in D['docs']:
        if d['year'] in cnt: cnt[d['year']][d['topic'] - 1] += 1
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    x = np.arange(len(yr)); bottom = np.zeros(len(yr))
    for k in range(K):
        h = np.array([cnt[y][k] for y in yr])
        ax.bar(x, h, bottom=bottom, width=0.70, color=PAL[k], label='topic%d' % (k + 1),
               edgecolor='white', linewidth=0.5)
        bottom += h
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in yr], rotation=45, ha='right', fontsize=10)
    ax.set_xlabel('年份', fontsize=11.5)
    ax.set_ylabel('文献数量', fontsize=11.5)
    ax.set_xlim(-0.8, len(yr) - 0.2)
    ax.set_ylim(0, max(bottom) * 1.10 + 0.4)
    ax.legend(title='主题', bbox_to_anchor=(1.012, 1.0), loc='upper left', fontsize=10,
              title_fontsize=11, frameon=False, handlelength=1.1, labelspacing=0.55)
    fig.subplots_adjust(left=0.085, right=0.825, top=0.965, bottom=0.20)
    cap(fig, '图 1. 各年度主题文献数量堆叠图')
    save(fig, '图1_年度主题文献数量堆叠图.png')

# ============ 图2 一致性曲线 ============
def fig2():
    cur = {int(k): v for k, v in D['coherence_curve'].items()}
    ks = [k for k in sorted(cur) if k <= 12]     # K>12 时每主题平均不足 4 篇，不纳入比较
    ys = [cur[k] for k in ks]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(ks, ys, color='#2F6D72', linewidth=1.5)
    k9 = 9
    ax.plot([k9], [cur[k9]], 'o', ms=5, color='#ED8D5A', zorder=5)
    ax.annotate('K=9', (k9, cur[k9]), textcoords='offset points', xytext=(8, -16),
                fontsize=11.5, color='#A84A2E', fontweight='bold')
    ax.set_xticks(ks)
    ax.set_xlim(min(ks) - 0.6, max(ks) + 0.6)
    ax.set_xlabel('Number of topics (K)', fontsize=11.5)
    ax.set_ylabel('Coherence (u_mass)', fontsize=11.5)
    fig.subplots_adjust(left=0.115, right=0.97, top=0.965, bottom=0.20)
    cap(fig, '图 2. 主题一致性结果')
    save(fig, '图2_主题一致性结果.png')

# ============ 图3 主题网络图 ============
def fig3():
    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    ax.axis('off')
    share = np.array([t['share'] for t in topics])
    rs = 0.058 + 0.072 * np.sqrt(share / share.max())
    pos = {}
    for k in range(K):
        a = -math.pi / 2 + 2 * math.pi * k / K
        pos[k] = (0.72 * math.cos(a), 0.72 * math.sin(a))
    for e in D['edges']:
        a, b = e['a'] - 1, e['b'] - 1
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]],
                color='#D2D7D9', lw=0.3 + 0.16 * e['w'], alpha=0.40, zorder=1)

    # 第一遍：主题词。近水平节点纵向堆叠，近垂直节点沿半径单列
    wtext = {k: [] for k in range(K)}
    for k in range(K):
        cx, cy = pos[k]
        ang = math.atan2(cy, cx)
        ux, uy = math.cos(ang), math.sin(ang)
        words = [w for w, _ in topics[k]['words'][:3]]
        n = len(words)
        if abs(uy) < 0.55:
            xa = cx + ux * (rs[k] + 0.10)
            ha = 'left' if ux > 0 else 'right'
            for i, w in enumerate(words):
                y = cy + ((n - 1) / 2.0 - i) * 0.105
                ax.add_patch(Circle((xa, y), 0.009, facecolor=PAL[k], edgecolor='none',
                                    alpha=0.75, zorder=2))
                wtext[k].append(ax.text(xa + (0.022 if ux > 0 else -0.022), y, w,
                                        fontsize=7.8, ha=ha, va='center',
                                        color='#4C4C49', zorder=4))
        else:
            for i, w in enumerate(words):
                rr = rs[k] + 0.14 + i * 0.125
                x, y = cx + ux * rr, cy + uy * rr
                ax.add_patch(Circle((x, y), 0.009, facecolor=PAL[k], edgecolor='none',
                                    alpha=0.75, zorder=2))
                va = 'bottom' if uy > 0 else 'top'
                wtext[k].append(ax.text(x, y, w, fontsize=7.8, ha='center', va=va,
                                        color='#4C4C49', zorder=4))

    for k in range(K):
        cx, cy = pos[k]
        ax.add_patch(Circle((cx, cy), rs[k], facecolor=PAL[k], edgecolor='white', lw=1.1, zorder=5))
        ax.text(cx, cy, 'topic%d' % (k + 1), fontsize=8.8, ha='center', va='center',
                color='white', zorder=6, fontweight='bold')

    # 第二遍：按词块实测边界放主题名，保证不压字
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    def bbox(t):
        bb = t.get_window_extent(renderer=rend)
        (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    names = []
    for k in range(K):
        cx, cy = pos[k]
        ang = math.atan2(cy, cx)
        ux, uy = math.cos(ang), math.sin(ang)
        bs = [bbox(t) for t in wtext[k]]
        x0 = min(b[0] for b in bs); x1 = max(b[1] for b in bs)
        y0 = min(b[2] for b in bs); y1 = max(b[3] for b in bs)
        if abs(uy) < 0.55:
            if ux > 0:
                lx, ha, ly = x1 + 0.10, 'left', cy
            else:
                lx, ha, ly = x0 - 0.10, 'right', cy
            ly = cy
        else:
            if abs(cx) < 0.20:
                lx, ha = cx, 'center'
            elif cx > 0:
                lx, ha = x1 + 0.10, 'left'
            else:
                lx, ha = x0 - 0.10, 'right'
            ly = (y1 + 0.10) if uy > 0 else (y0 - 0.10)
        names.append(ax.text(lx, ly, 'topic%d\n%s' % (k + 1, KW2[k + 1]), fontsize=11.2, ha=ha, va='center',
                             color='#2E5F66' if k % 2 == 0 else '#8A5A3C', zorder=7))

    fig.subplots_adjust(left=0.012, right=0.988, top=0.985, bottom=0.075)
    # 第三遍：按全部文字实测范围扩坐标，避免任何标签被裁切
    fig.canvas.draw()
    inv = ax.transData.inverted()   # subplots_adjust 后必须重新取变换
    xs, ys = [], []
    for t in names + [t for k in range(K) for t in wtext[k]]:
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        xs += [x0, x1]; ys += [y0, y1]
    padx = (max(xs) - min(xs)) * 0.05 + 0.06
    pady = (max(ys) - min(ys)) * 0.05 + 0.06
    ax.set_xlim(min(xs) - padx, max(xs) + padx)
    ax.set_ylim(min(ys) - pady, max(ys) + pady)
    cap(fig, '图 3. 主题网络图')
    save(fig, '图3_主题网络图.png')

# ============ 图4 主题×年份 热图 ============
def fig4():
    yrs = sorted(YT)
    M = np.array([[YT[y][k] for y in yrs] for k in range(K)])
    M = (M - M.min()) / (M.max() - M.min() + 1e-9)
    fig, ax = plt.subplots(figsize=(8.4, 4.1))
    im = ax.imshow(M, aspect='auto', cmap=CMAP, vmin=0, vmax=1, interpolation='nearest')
    ax.set_yticks(range(K)); ax.set_yticklabels(['topic%d' % (i + 1) for i in range(K)], fontsize=10)
    ax.set_xticks(range(len(yrs)))
    ax.set_xticklabels([str(y) for y in yrs], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('主题', fontsize=11.5)
    cax = fig.add_axes([0.105, 0.155, 0.79, 0.021])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Intensity', fontsize=10, labelpad=3)
    cb.ax.tick_params(labelsize=8.5)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.965, bottom=0.285)
    cap(fig, '图 4. 全部主题时间热度图')
    save(fig, '图4_全部主题时间热度图.png')

# ============ 图5 分面热图（期刊）============
def fig5():
    groups = D['venue_groups']; keys = list(groups.keys()); yrs = sorted(YT)
    fig, axes = plt.subplots(3, 3, figsize=(9.0, 7.5))
    grids = []; vmax = 0
    for key in keys:
        idx = groups[key]
        M = np.full((K, len(yrs)), np.nan)
        for j, y in enumerate(yrs):
            ids = [i for i in idx if D['docs'][i]['year'] == y]
            if ids:
                for k in range(K):
                    M[k, j] = np.mean([D['docs'][i]['theta'][k] for i in ids])
        grids.append(M); vmax = max(vmax, np.nanmax(M))
    for ai, (ax, key, M) in enumerate(zip(axes.flat, keys, grids)):
        im = ax.imshow(M, aspect='auto', cmap=CMAP, vmin=0, vmax=vmax, interpolation='nearest')
        ax.set_title('%s（n=%d）' % (short(key), len(groups[key])), fontsize=10.5, pad=5)
        ax.set_yticks(range(K)); ax.set_yticklabels([str(i + 1) for i in range(K)], fontsize=9.0)
        ax.set_xticks(range(0, len(yrs), 3))
        ax.set_xticklabels([str(y) for y in yrs[::3]], fontsize=8.2)
        ax.tick_params(length=1.8, pad=2)
        if ai % 3 == 0:
            ax.set_ylabel('主题', fontsize=9.5)
    for ax in list(axes.flat)[len(keys):]: ax.axis('off')
    cax = fig.add_axes([0.24, 0.108, 0.52, 0.014])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Intensity', fontsize=10, labelpad=8)
    cb.ax.tick_params(labelsize=8.5)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.955, bottom=0.175, hspace=0.60, wspace=0.24)
    cap(fig, '图 5. 各期刊主题热度图')
    save(fig, '图5_各期刊主题热度图.png')

# ============ 图6 主题情感曲线 ============
def fig6():
    yrs = sorted(YP)
    xi = list(range(len(yrs)))
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for k in range(K):
        ax.plot(xi, [YP[y][k] for y in yrs], color=PAL[k], lw=1.3, marker='o', ms=2.8,
                label='topic%d' % (k + 1))
    ax.axhline(0, color='#93AEB2', lw=0.7, ls=(0, (4, 3)))
    ax.set_xlabel('Year', fontsize=11.5)
    ax.set_ylabel('Weighted Sentiment (P(pos) - P(neg))', fontsize=10.5)
    ax.set_xticks(xi); ax.set_xticklabels([str(y) for y in yrs], rotation=45, ha='right', fontsize=8.8)
    ax.set_xlim(-0.6, len(yrs) - 0.4)
    allv = [v for y in YP for v in YP[y]]
    lo = min(allv); hi = max(allv)
    ax.set_ylim(math.floor(lo * 10) / 10 - 0.08, math.ceil(hi * 10) / 10 + 0.08)
    ax.legend(ncol=9, fontsize=9.5, frameon=False, loc='upper center',
              bbox_to_anchor=(0.5, 1.10), handlelength=1.2, columnspacing=0.9)
    fig.subplots_adjust(left=0.115, right=0.985, top=0.86, bottom=0.20)
    cap(fig, '图 6. 各主题情感倾向曲线图')
    save(fig, '图6_各主题情感倾向曲线图.png')

# ============ 图7 分面情感曲线 ============
def fig7():
    groups = D['venue_groups']; keys = list(groups.keys())
    ally = sorted(YT); GI = {y: i for i, y in enumerate(ally)}
    allv = [v for y in YP for v in YP[y]]
    lo, hi = min(allv), max(allv)
    fig, axes = plt.subplots(3, 3, figsize=(9.2, 7.6), sharex=True, sharey=True)
    for ax, key in zip(axes.flat, keys):
        idx = groups[key]
        yrs = sorted(set(D['docs'][i]['year'] for i in idx))
        xi = [GI[y] for y in yrs]
        for k in range(K):
            vals = []
            for y in yrs:
                ids = [i for i in idx if D['docs'][i]['year'] == y]
                w = np.array([D['docs'][i]['theta'][k] for i in ids])
                sp = np.array([D['docs'][i]['pol'] for i in ids])
                if w.sum() < 0.10:            # 该主题在该年几乎不存在，不画
                    vals.append(np.nan); continue
                vals.append(float((w * sp).sum() / w.sum()))
            ax.plot(xi, vals, color=PAL[k], lw=1.3, marker='o', ms=3.0)
        ax.axhline(0, color='#93AEB2', lw=0.6, ls=(0, (4, 3)))
        ax.set_title('%s（n=%d）' % (short(key), len(idx)), fontsize=10.5, pad=5)
        ax.tick_params(labelsize=8.2)
        ax.set_ylim(math.floor(lo * 10) / 10 - 0.05, math.ceil(hi * 10) / 10 + 0.05)
        ax.set_xlim(-0.6, len(ally) - 0.4)
    for ax in list(axes.flat):
        ax.set_xticks(range(0, len(ally), 3))
        ax.set_xticklabels([str(y) for y in ally[::3]], fontsize=8.0)
        ax.tick_params(labelbottom=(ax in list(axes.flat)[-3:]), pad=2)
    handles = [Line2D([], [], color=PAL[k], lw=1.4, marker='o', ms=2.8, label='topic%d' % (k + 1))
               for k in range(K)]
    fig.legend(handles=handles, ncol=9, fontsize=9.5, frameon=False,
               loc='lower center', bbox_to_anchor=(0.5, 0.062), handlelength=1.2)
    fig.text(0.020, 0.56, '加权情感值', rotation=90, va='center', fontsize=10.5)
    fig.text(0.085, 0.040, '横轴为年份（每 3 年标注一次）', fontsize=9, color='#5A5A56')
    fig.subplots_adjust(left=0.085, right=0.985, top=0.955, bottom=0.165, hspace=0.32, wspace=0.12)
    cap(fig, '图 7. 各期刊主题情感倾向曲线图')
    save(fig, '图7_各期刊主题情感倾向曲线图.png')

if __name__ == '__main__':
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
