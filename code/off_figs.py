# -*- coding: utf-8 -*-
"""官方话语 7 张图：与专家话语同一套可视化方法，数据源为 work/off_results.json。
与专家版的必要差异（均由官方数据的分布特征决定，已在图注中说明）：
1) 主题数由 u_mass 择优得 K=12，配色扩至 12 色；
2) 情感值按报告公式 s=(P-N)/(P+N+2) 计算（+2 平滑），避免正面词密集的官方文本被钉在 +1；
3) 每个「年×主题」情感格要求该年文献 ≥2 篇，单篇年份不计算（样本不足）；
4) 分面图只保留 n≥10 的发布平台（国会图书馆仅 2 篇，不单独分面），组内共用色标；
5) 热度图色标上限取 P95 并截顶，否则 12 主题下均值仅 0.083、少数主导年 0.85 会使全图泛白。
FIGS 选择图号，FIG_OUT 指定输出目录，NO_CAP=1 输出无图题版。
"""
import json, io, math, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap, PowerNorm, TwoSlopeNorm
from matplotlib.lines import Line2D

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'work', 'off_results.json')
OUT = os.environ.get('FIG_OUT') or r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/图'
NO_CAP = os.environ.get('NO_CAP') == '1'
os.makedirs(OUT, exist_ok=True)

D = json.load(io.open(RES, encoding='utf-8'))
K = D['K']; topics = D['topics']; years = D['years']
YT = {int(k): v for k, v in D['year_theta'].items()}
YP = {int(k): v for k, v in D['year_pol'].items()}
YN = {int(k): v for k, v in D['year_n'].items()}
MINN = 2                                     # 情感格最少文献数

PAL = ['#4A8E94', '#4198AC', '#7BC0CD', '#BFDFD2', '#DBCB92', '#ECB66C', '#EA9E58', '#ED8D5A', '#9C5C4A',
       '#3E5C76', '#6B8F71', '#8C6D4F'][:max(K, 9)]
CMAP = LinearSegmentedColormap.from_list('ocean', ['#FFFDF6', '#DBCB92', '#ECB66C', '#ED8D5A', '#A84A2E'])
CMAP.set_bad('#F4F2EB')
DIV = LinearSegmentedColormap.from_list('div', ['#2F7A80', '#8FBFC4', '#F7F4EA', '#E8A87C', '#B4472A'])
DIV.set_bad('#F4F2EB')
CAP_BG = '#DCEDDF'
GAMMA = 0.60

SHORT = {
 'Buenos Aires Ciudad': 'Buenos Aires Ciudad',
 'Argentina.gob.ar – Educación': 'Argentina.gob.ar（教育）',
 'Biblioteca del Congreso de la Nación': '国会图书馆',
}
FACETS = [k for k, v in D['venue_groups'].items() if len(v) >= 10]   # 分面只留 n≥10

def short(v):
    return SHORT.get(v, v[:20])

def cap(fig, text, fs=13):
    if NO_CAP: return
    fig.add_artist(Rectangle((0, 0), 1, 0.060, transform=fig.transFigure,
                             facecolor=CAP_BG, edgecolor='none', zorder=0))
    fig.text(0.5, 0.030, text, ha='center', va='center', fontsize=fs, color='#1A1A1A')

def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=320)
    plt.close(fig)
    print('saved', name, flush=True)


# ============ 图1 各年度主题文献数量堆叠图 ============
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
    cap(fig, '图 1. 各年度主题文献数量堆叠图（时间不详的 %d 篇未纳入）' % (D['N'] - D['n_year_known']))
    save(fig, '图1_年度主题文献数量堆叠图.png')


# ============ 图2 一致性曲线 ============
def fig2():
    cur = {int(k): v for k, v in D['coherence_curve'].items()}
    ks = [k for k in sorted(cur) if k <= 12]
    ys = [cur[k] for k in ks]
    kbest = D['best_k']
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(ks, ys, color='#2F6D72', linewidth=1.5)
    ax.plot([kbest], [cur[kbest]], 'o', ms=5, color='#ED8D5A', zorder=5)
    xy = (-44, -16) if kbest >= max(ks) else (8, -16)
    ax.annotate('K=%d' % kbest, (kbest, cur[kbest]), textcoords='offset points',
                xytext=xy, fontsize=11.5, color='#A84A2E', fontweight='bold')
    ax.set_xticks(ks)
    ax.set_xlim(min(ks) - 0.6, max(ks) + 0.6)
    ax.set_xlabel('Number of topics (K)', fontsize=11.5)
    ax.set_ylabel('Coherence (u_mass)', fontsize=11.5)
    fig.subplots_adjust(left=0.115, right=0.97, top=0.965, bottom=0.20)
    cap(fig, '图 2. 主题一致性结果')
    save(fig, '图2_主题一致性结果.png')


# ============ 图3 主题网络图（见 fig3_net.py，OFF=1）============
def fig3():
    import importlib.util
    os.environ['OFF'] = '1'
    os.environ.setdefault('COTH', '8')     # 官方语料共现更密，阈值 8 与专家版密度相当
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('fig3_net', os.path.join(here, 'fig3_net.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.OUT = OUT
    m.make('图3_主题网络图.png')


# ============ 图4 主题×年份 热图（幂律色标 + P95 截顶） ============
def fig4():
    yrs = sorted(YT)
    M = np.array([[YT[y][k] for y in yrs] for k in range(K)])
    vmax = float(np.percentile(M, 95))
    fig, ax = plt.subplots(figsize=(8.4, 4.1))
    im = ax.imshow(M, aspect='auto', cmap=CMAP, interpolation='nearest',
                   norm=PowerNorm(GAMMA, vmin=0, vmax=vmax))
    for j in range(len(yrs) + 1):
        ax.axvline(j - 0.5, color='white', lw=0.9, zorder=3)
    for k in range(K + 1):
        ax.axhline(k - 0.5, color='white', lw=0.9, zorder=3)
    ax.set_yticks(range(K)); ax.set_yticklabels(['topic%d' % (i + 1) for i in range(K)], fontsize=10)
    ax.set_xticks(range(len(yrs)))
    ax.set_xticklabels([str(y) for y in yrs], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('主题', fontsize=11.5)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    cax = fig.add_axes([0.105, 0.175, 0.79, 0.020])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Intensity（γ=0.6 幂律拉伸；色标上限 = P95 = %.2f，更高值截顶）' % vmax,
                 fontsize=9.2, labelpad=2)
    cb.ax.tick_params(labelsize=8.5)
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.965, bottom=0.305)
    cap(fig, '图 4. 全部主题时间热度图（时间不详的 %d 篇未纳入）' % (D['N'] - D['n_year_known']))
    save(fig, '图4_全部主题时间热度图.png')


# ============ 图5 分面热图（n≥10 的发布平台）============
def fig5():
    keys = FACETS; yrs = sorted(YT)
    n = len(keys)
    fig, axes = plt.subplots(1, n, figsize=(4.55 * n, 5.15), squeeze=False)
    axes = axes[0]
    grids = []
    for key in keys:
        idx = D['venue_groups'][key]
        M = np.full((K, len(yrs)), np.nan)
        for j, y in enumerate(yrs):
            ids = [i for i in idx if D['docs'][i]['year'] == y]
            if ids:
                for k in range(K):
                    M[k, j] = np.mean([D['docs'][i]['theta'][k] for i in ids])
        grids.append(M)
    vmax = float(np.percentile(np.concatenate([m[~np.isnan(m)] for m in grids]), 95))
    for ax, key, M in zip(axes, keys, grids):
        im = ax.imshow(M, aspect='auto', cmap=CMAP, interpolation='nearest',
                       norm=PowerNorm(GAMMA, vmin=0, vmax=vmax))
        for j in range(len(yrs) + 1):
            ax.axvline(j - 0.5, color='white', lw=0.55, zorder=3)
        for k in range(K + 1):
            ax.axhline(k - 0.5, color='white', lw=0.55, zorder=3)
        ax.set_title('%s（n=%d）' % (short(key), len(D['venue_groups'][key])), fontsize=10.5,
                     pad=6, loc='left', color='#2C2C2A')
        ax.set_yticks(range(K))
        ax.set_yticklabels([str(i + 1) for i in range(K)], fontsize=8.4)
        ax.set_xticks(range(0, len(yrs), 3))
        ax.set_xticklabels([str(y) for y in yrs[::3]], rotation=45, ha='right', fontsize=8.0)
        ax.tick_params(length=0, pad=2.5)
        for s in ax.spines.values(): s.set_visible(False)
        ax.set_ylabel('主题', fontsize=9.5, labelpad=3)
    cax = fig.add_axes([0.335, 0.882, 0.33, 0.015])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Intensity　γ=0.6 幂律拉伸；上限 P95=%.2f；灰色 = 该年无文献' % vmax,
                 fontsize=9.0, labelpad=3)
    cb.ax.tick_params(labelsize=8.2)
    cb.ax.xaxis.set_ticks_position('top')
    cb.ax.xaxis.set_label_position('top')
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.838, bottom=0.185, wspace=0.28)
    cap(fig, '图 5. 各发布平台主题热度图（仅 n≥10 的平台；国会图书馆 2 篇不单独分面）')
    save(fig, '图5_各平台主题热度图.png')


# ============ 图6 主题情感曲线（每点要求该年 ≥2 篇） ============
def fig6():
    yrs = [y for y in sorted(YP) if YN.get(y, 0) >= MINN]
    xi = list(range(len(yrs)))
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    allv = [YP[y][k] for y in yrs for k in range(K)]
    ylo = min(-0.15, math.floor(min(allv) * 10) / 10 - 0.06)
    yhi = max(0.15, math.ceil(max(allv) * 10) / 10 + 0.06)
    ax.axhspan(0, yhi, color='#FBEFE4', alpha=0.55, zorder=0)
    ax.axhspan(ylo, 0, color='#E8F1F1', alpha=0.55, zorder=0)
    for k in range(K):
        ax.plot(xi, [YP[y][k] for y in yrs], color=PAL[k], lw=1.35, marker='o', ms=3.0,
                label='topic%d' % (k + 1))
    ax.axhline(0, color='#93AEB2', lw=0.7, ls=(0, (4, 3)))
    ax.set_xlabel('年份', fontsize=11.5)
    ax.set_ylabel('加权情感值 (P(pos)-P(neg))', fontsize=10.5)
    ax.set_xticks(xi)
    ax.set_xticklabels(['%d\n(n=%d)' % (y, YN[y]) for y in yrs], fontsize=8.6)
    ax.set_xlim(-0.6, len(yrs) - 0.4)
    ax.set_ylim(ylo, yhi)
    ax.grid(axis='y', color='#DEDBD0', lw=0.5, alpha=0.7, zorder=1)
    ax.legend(ncol=1, fontsize=9.2, frameon=False, loc='upper left',
              bbox_to_anchor=(1.012, 1.0), handlelength=1.5, labelspacing=0.55,
              title='主题', title_fontsize=9.6)
    fig.subplots_adjust(left=0.085, right=0.845, top=0.965, bottom=0.215)
    cap(fig, '图 6. 各主题情感倾向曲线图（该年文献 <2 篇的年份不计算；时间不详 %d 篇未纳入）'
        % (D['N'] - D['n_year_known']))
    save(fig, '图6_各主题情感倾向曲线图.png')


# ============ 图7 分面情感热图（n≥10 的发布平台）============
def fig7b():
    keys = FACETS; Ally = sorted(YT)
    mats = []
    for key in keys:
        idx = D['venue_groups'][key]
        M = np.full((K, len(Ally)), np.nan)
        for j, y in enumerate(Ally):
            ids = [i for i in idx if D['docs'][i]['year'] == y]
            if len(ids) < MINN: continue                     # 单篇年份样本不足
            for k in range(K):
                w = np.array([D['docs'][i]['theta'][k] for i in ids])
                sp = np.array([D['docs'][i]['pol'] for i in ids])
                if w.sum() < 0.05: continue
                M[k, j] = float((w * sp).sum() / w.sum())
        mats.append(M)
    vals = np.concatenate([m[~np.isnan(m)] for m in mats])
    lo, hi = float(vals.min()), float(vals.max())
    norm = TwoSlopeNorm(vcenter=0.0, vmin=min(lo, -0.05), vmax=max(hi, 0.05))
    n = len(keys)
    fig, axes = plt.subplots(1, n, figsize=(4.55 * n, 5.15), squeeze=False)
    axes = axes[0]
    im = None
    for ax, key, M in zip(axes, keys, mats):
        im = ax.imshow(M, aspect='auto', cmap=DIV, norm=norm, interpolation='nearest')
        for j in range(len(Ally) + 1):
            ax.axvline(j - 0.5, color='white', lw=0.55, zorder=3)
        for k in range(K + 1):
            ax.axhline(k - 0.5, color='white', lw=0.55, zorder=3)
        ax.set_title('%s（n=%d）' % (short(key), len(D['venue_groups'][key])), fontsize=10.5,
                     pad=6, loc='left', color='#2C2C2A')
        ax.set_yticks(range(K)); ax.set_yticklabels([str(i + 1) for i in range(K)], fontsize=8.4)
        ax.set_xticks(range(0, len(Ally), 3))
        ax.set_xticklabels([str(y) for y in Ally[::3]], rotation=45, ha='right', fontsize=8.0)
        ax.tick_params(length=0, pad=2.5)
        for s in ax.spines.values(): s.set_visible(False)
        ax.set_ylabel('主题', fontsize=9.5, labelpad=3)
    ticks = [t for t in (-0.2, 0.0, 0.2, 0.4, 0.6, 0.8) if norm.vmin <= t <= norm.vmax]
    cax = fig.add_axes([0.335, 0.882, 0.33, 0.015])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal', ticks=ticks)
    cb.set_label('加权情感值（+2 平滑）　冷色 = 负面；暖色 = 正面；灰色 = 该年无文献或 <2 篇',
                 fontsize=9.0, labelpad=3)
    cb.ax.tick_params(labelsize=8.2)
    cb.ax.xaxis.set_ticks_position('top')
    cb.ax.xaxis.set_label_position('top')
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.838, bottom=0.185, wspace=0.28)
    cap(fig, '图 7. 各发布平台主题情感倾向热图（仅 n≥10 的平台；<2 篇的年份不计）')
    save(fig, '图7_各平台主题情感倾向热图.png')


if __name__ == '__main__':
    which = os.environ.get('FIGS', '1,2,3,4,5,6,7').split(',')
    fn = {'1': fig1, '2': fig2, '3': fig3, '4': fig4, '5': fig5, '6': fig6, '7': fig7b}
    for w in which:
        fn[w.strip()]()
