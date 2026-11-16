# -*- coding: utf-8 -*-
"""图 3 / 4 / 5 / 7 重制：和弦网络、幂律色标热图、分面带情感曲线。
仅改呈现，数据口径不变（同一份 work/lab_results.json）。
"""
import json, io, math, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Wedge
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
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
CMAP.set_bad('#F4F2EB')
CAP_BG = '#DCEDDF'
GAMMA = 0.60

TOP2 = {t['id']: (t['words'][0][0], t['words'][1][0]) for t in D['topics']}

LAB = {
 1: '跨文化双语教育', 2: '首都语言政策与中文书写', 3: '区域一体化与外语政策',
 4: '外语课程与教学', 5: '手语、瓜拉尼语与翻译', 6: '西语二语习得与教学法',
 7: '语法学史与语言态度', 8: '社区双语与聋人读写', 9: '西班牙语变体与阿根廷西语',
}
SHORT = {
 'RAHL: Revista argentina de historiografía lingüística': 'RAHL',
 'Traslaciones: Revista Latinoamericana de Lectura y Escritura': 'Traslaciones',
 'Quintú Quimün: revista de lingüística': 'Quintú Quimün',
 'Signos ELE: Revista de Español como Lengua Extranjera': 'Signos ELE',
}

def short(v):
    if v in SHORT: return SHORT[v]
    return v.split(':')[0][:30]

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


# ============ 图3 主题网络图（见 fig3_net.py） ============
def fig3():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('fig3_net', os.path.join(here, 'fig3_net.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.make('图3_主题网络图.png')


# ============ 图4 主题×年份 热图（幂律色标） ============
def fig4():
    yrs = sorted(YT)
    M = np.array([[YT[y][k] for y in yrs] for k in range(K)])
    top = M.max()
    fig, ax = plt.subplots(figsize=(8.4, 4.1))
    im = ax.imshow(M, aspect='auto', cmap=CMAP, interpolation='nearest',
                   norm=PowerNorm(GAMMA, vmin=0, vmax=top))
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
    cb.set_label('Intensity（γ=0.6 幂律拉伸）', fontsize=9.5, labelpad=2)
    cb.ax.tick_params(labelsize=8.5)
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.09, right=0.985, top=0.965, bottom=0.305)
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
        im = ax.imshow(M, aspect='auto', cmap=CMAP, interpolation='nearest',
                       norm=PowerNorm(GAMMA, vmin=0, vmax=vmax))
        for j in range(len(yrs) + 1):
            ax.axvline(j - 0.5, color='white', lw=0.55, zorder=3)
        for k in range(K + 1):
            ax.axhline(k - 0.5, color='white', lw=0.55, zorder=3)
        ax.set_title('%s（n=%d）' % (short(key), len(groups[key])), fontsize=10.5,
                     pad=6, loc='left', color='#2C2C2A')
        ax.set_yticks(range(K))
        ax.set_yticklabels([str(i + 1) for i in range(K)], fontsize=8.4)
        ax.set_xticks(range(0, len(yrs), 3))
        ax.set_xticklabels([str(y) for y in yrs[::3]], fontsize=8.2)
        ax.tick_params(length=0, pad=2.5)
        for s in ax.spines.values(): s.set_visible(False)
        if ai % 3 == 0:
            ax.set_ylabel('主题', fontsize=9.5, labelpad=3)
    for ax in list(axes.flat)[len(keys):]: ax.axis('off')
    cax = fig.add_axes([0.26, 0.128, 0.48, 0.012])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.set_label('Intensity　γ=0.6 幂律拉伸；灰色 = 该年无文献', fontsize=9.2, labelpad=4)
    cb.ax.tick_params(labelsize=8.2)
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.955, bottom=0.190, hspace=0.52, wspace=0.20)
    cap(fig, '图 5. 各期刊主题热度图')
    save(fig, '图5_各期刊主题热度图.png')


# ============ 图6 主题情感曲线（保留原版） ============
def fig6():
    yrs = sorted(YP); xi = list(range(len(yrs)))
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.axhspan(0, 1, color='#FBEFE4', alpha=0.55, zorder=0)
    ax.axhspan(-1, 0, color='#E8F1F1', alpha=0.55, zorder=0)
    for k in range(K):
        ax.plot(xi, [YP[y][k] for y in yrs], color=PAL[k], lw=1.3, marker='o', ms=2.8,
                label='topic%d' % (k + 1))
    ax.axhline(0, color='#93AEB2', lw=0.7, ls=(0, (4, 3)))
    ax.set_xlabel('Year', fontsize=11.5)
    ax.set_ylabel('Weighted Sentiment (P(pos) - P(neg))', fontsize=10.5)
    ax.set_xticks(xi); ax.set_xticklabels([str(y) for y in yrs], rotation=45, ha='right', fontsize=8.8)
    ax.set_xlim(-0.6, len(yrs) - 0.4)
    allv = [v for y in YP for v in YP[y]]
    ax.set_ylim(math.floor(min(allv) * 10) / 10 - 0.08, math.ceil(max(allv) * 10) / 10 + 0.08)
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
    ylo = math.floor(lo * 10) / 10 - 0.06
    yhi = math.ceil(hi * 10) / 10 + 0.06
    fig, axes = plt.subplots(3, 3, figsize=(9.2, 7.6), sharex=True, sharey=True)
    for ai, (ax, key) in enumerate(zip(axes.flat, keys)):
        ax.axhspan(0, yhi, color='#FCF2EA', alpha=0.80, zorder=0)
        ax.axhspan(ylo, 0, color='#EAF2F2', alpha=0.80, zorder=0)
        idx = groups[key]
        yrs = sorted(set(D['docs'][i]['year'] for i in idx))
        xi = [GI[y] for y in yrs]
        for k in range(K):
            vals = []; wts = []
            for y in yrs:
                ids = [i for i in idx if D['docs'][i]['year'] == y]
                w = np.array([D['docs'][i]['theta'][k] for i in ids])
                sp = np.array([D['docs'][i]['pol'] for i in ids])
                if w.sum() < 0.10:
                    vals.append(np.nan); wts.append(0.0); continue
                vals.append(float((w * sp).sum() / w.sum())); wts.append(float(w.sum()))
            ax.plot(xi, vals, color=PAL[k], lw=2.0, solid_capstyle='round', zorder=3)
            ms = [3.4 + 3.4 * min(w, 2.0) / 2.0 for w in wts]
            ax.scatter(xi, vals, s=[m ** 2 for m in ms], color=PAL[k],
                       edgecolor='white', linewidth=0.9, zorder=4)
        ax.axhline(0, color='#8FA9AD', lw=0.8, ls=(0, (3, 2)), zorder=2)
        ax.set_title('%s（n=%d）' % (short(key), len(idx)), fontsize=10.5, pad=6,
                     loc='left', color='#2C2C2A')
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
        ax.spines['left'].set_color('#C9C6B8'); ax.spines['bottom'].set_color('#C9C6B8')
        ax.tick_params(labelsize=8.2, colors='#4C4C49', length=2.5)
        ax.set_ylim(ylo, yhi)
        ax.set_xlim(-0.6, len(ally) - 0.4)
        ax.grid(axis='y', color='#DEDBD0', lw=0.5, alpha=0.7, zorder=1)
    for ax in list(axes.flat):
        ax.set_xticks(range(0, len(ally), 3))
        ax.set_xticklabels([str(y) for y in ally[::3]], fontsize=8.0)
        ax.tick_params(labelbottom=(ax in list(axes.flat)[-3:]), pad=2)
    handles = [Line2D([], [], color=PAL[k], lw=2.2, marker='o', ms=3.2,
                      markeredgecolor='white', label='topic%d' % (k + 1)) for k in range(K)]
    fig.legend(handles=handles, ncol=9, fontsize=9.5, frameon=False,
               loc='lower center', bbox_to_anchor=(0.5, 0.098), handlelength=1.4)
    fig.text(0.016, 0.57, '加权情感值', rotation=90, va='center', fontsize=10.5, color='#2C2C2A')
    fig.text(0.085, 0.065, '暖色区 = 正面　冷色区 = 负面　圆点大小 = 该主题在该年的证据量（Σθ）',
             fontsize=8.4, color='#7A7A74')
    fig.subplots_adjust(left=0.095, right=0.985, top=0.955, bottom=0.185, hspace=0.34, wspace=0.10)
    cap(fig, '图 7. 各期刊主题情感倾向曲线图')
    save(fig, '图7_各期刊主题情感倾向曲线图.png')




# ============ 图7 备选：分面情感热图 ============
from matplotlib.colors import TwoSlopeNorm
DIV = LinearSegmentedColormap.from_list('div', ['#2F7A80', '#8FBFC4', '#F7F4EA', '#E8A87C', '#B4472A'])
DIV.set_bad('#F4F2EB')

def fig7b():
    groups = D['venue_groups']; keys = list(groups.keys()); Ally = sorted(YT)
    mats = []
    for key in keys:
        idx = groups[key]
        M = np.full((K, len(Ally)), np.nan)
        for j, y in enumerate(Ally):
            ids = [i for i in idx if D['docs'][i]['year'] == y]
            if not ids: continue
            for k in range(K):
                w = np.array([D['docs'][i]['theta'][k] for i in ids])
                sp = np.array([D['docs'][i]['pol'] for i in ids])
                if w.sum() < 0.05: continue
                M[k, j] = float((w * sp).sum() / w.sum())
        mats.append(M)
    vals = np.concatenate([m[~np.isnan(m)] for m in mats])
    lo, hi = float(vals.min()), float(vals.max())
    norm = TwoSlopeNorm(vcenter=0.0, vmin=lo, vmax=hi)
    fig, axes = plt.subplots(3, 3, figsize=(9.2, 7.6))
    im = None
    for ai, (ax, key) in enumerate(zip(axes.flat, keys)):
        idx = groups[key]
        im = ax.imshow(mats[ai], aspect='auto', cmap=DIV, norm=norm, interpolation='nearest')
        for j in range(len(Ally) + 1):
            ax.axvline(j - 0.5, color='white', lw=0.55, zorder=3)
        for k in range(K + 1):
            ax.axhline(k - 0.5, color='white', lw=0.55, zorder=3)
        ax.set_title('%s（n=%d）' % (short(key), len(idx)), fontsize=10.5, pad=6,
                     loc='left', color='#2C2C2A')
        ax.set_yticks(range(K)); ax.set_yticklabels([str(i + 1) for i in range(K)], fontsize=8.4)
        ax.set_xticks(range(0, len(Ally), 3))
        ax.set_xticklabels([str(y) for y in Ally[::3]], fontsize=8.2)
        ax.tick_params(length=0, pad=2.5)
        for s in ax.spines.values(): s.set_visible(False)
        if ai % 3 == 0: ax.set_ylabel('主题', fontsize=9.5, labelpad=3)
    cax = fig.add_axes([0.24, 0.128, 0.52, 0.012])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal', ticks=[-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8])
    cb.set_label('加权情感值　冷色 = 负面；暖色 = 正面；灰色 = 该年无文献', fontsize=9.2, labelpad=4)
    cb.ax.tick_params(labelsize=8.2)
    for s in cb.outline.get_children(): s.set_visible(False)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.955, bottom=0.190, hspace=0.52, wspace=0.20)
    cap(fig, '图 7. 各期刊主题情感倾向热图')
    save(fig, '图7_各期刊主题情感倾向热图.png')


if __name__ == '__main__':
    which = os.environ.get('FIGS', '3,4,5,7').split(',')
    fn = {'3': fig3, '4': fig4, '5': fig5, '6': fig6, '7': fig7b, '7c': fig7}
    for w in which:
        fn[w.strip()]()
