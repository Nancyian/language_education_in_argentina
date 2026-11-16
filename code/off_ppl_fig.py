# -*- coding: utf-8 -*-
"""官方话语 LDA：困惑度曲线 + 边际收益/一致性交叉验证图（风格与 off_figs.py 一致）"""
import json, io, os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

BASE = r'C:/Users/Administrator/WorkBuddy/2026-10-15-20-02-36'
OUT = r'C:/Users/Administrator/Desktop/阿根廷语料库'
D = json.load(io.open(os.path.join(BASE, 'work/off_perplexity.json'), encoding='utf-8'))
C = json.load(io.open(os.path.join(BASE, 'work/off_results.json'), encoding='utf-8'))

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.0
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['savefig.facecolor'] = 'white'

TEAL, DARK, ORANGE, RUST, BAND, CAP = '#4A8E94', '#2F6D72', '#ED8D5A', '#A84A2E', '#8FBFC4', '#DCEDDF'

ks = np.array(D['ks'])
mu = np.array([D['perplexity_mean'][str(k)] for k in ks])
sd = np.array([D['perplexity_sd'][str(k)] for k in ks])
coh = {int(k): v for k, v in C['coherence_curve'].items()}
cks = np.array(sorted(coh))
cys = np.array([coh[k] for k in cks])


def caption(fig, text, y=0.018):
    fig.text(0.5, y, text, ha='center', va='center', fontsize=9.3, color='#1A1A1A',
             bbox=dict(boxstyle='round,pad=0.45', facecolor=CAP, edgecolor='none'))


# ===== 图A：困惑度曲线 =====
fig, ax = plt.subplots(figsize=(7.6, 4.6))
ax.fill_between(ks, mu - sd, mu + sd, color=BAND, alpha=0.28, linewidth=0, zorder=1)
ax.plot(ks, mu, color=DARK, linewidth=1.7, marker='o', ms=4.2, mfc='white', mew=1.2,
        zorder=3, label='held-out perplexity（均值 ± 标准差）')
y8 = mu[ks.tolist().index(8)]
ax.plot([8], [y8], 'o', ms=9, color=ORANGE, zorder=6)
ax.axvline(8, color=RUST, lw=0.9, ls=(0, (4, 3)), zorder=2, alpha=0.55)
ax.annotate('K = 8\nppl = %s\n（此后边际下降 6.0%%→1.5%%）' % format(int(round(y8)), ','),
            xy=(8, y8), xytext=(24, 44), textcoords='offset points', fontsize=9.5,
            color=RUST, linespacing=1.5,
            arrowprops=dict(arrowstyle='-', color=RUST, lw=0.9,
                            connectionstyle='arc3,rad=-0.18'))
ax.set_xlabel('主题数 K', fontsize=11.5)
ax.set_ylabel('留出困惑度（Perplexity）', fontsize=11.5)
ax.set_xticks(ks); ax.xaxis.set_major_locator(MaxNLocator(integer=True))
ax.set_ylim(mu.min() - 60, mu.max() + 70)
ax.grid(axis='y', color='#E6E3DA', lw=0.8, zorder=0); ax.set_axisbelow(True)
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)
ax.legend(frameon=False, fontsize=9.5, loc='upper right')
caption(fig, '图  官方语料（%d 篇 / %d 词表 / %d 词次）LDA 留出困惑度，5 折交叉验证 × %d 次重复'
        % (D['N'], D['vocab_size'], D['tokens'], D['nrep']))
fig.tight_layout(rect=[0, 0.055, 1, 1])
p1 = os.path.join(OUT, '官方LDA困惑度曲线.png')
fig.savefig(p1, dpi=300); plt.close(fig)
print('saved', p1)

# ===== 图B：边际收益 + 一致性 =====
fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5))
ax1, ax2 = axes

delta = np.diff(mu)
rel = delta / mu[:-1] * 100
cols = [ORANGE if k == 8 else TEAL for k in ks[1:]]
ax1.bar(ks[1:], rel, width=0.66, color=cols, edgecolor='white', linewidth=0.5, zorder=3)
ax1.axhline(0, color='#666666', lw=0.8)
ax1.set_xlabel('主题数 K', fontsize=11.5)
ax1.set_ylabel('每增加一个主题的困惑度降幅（%）', fontsize=11)
ax1.set_xticks(ks[1:]); ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
ax1.grid(axis='y', color='#E6E3DA', lw=0.8, zorder=0); ax1.set_axisbelow(True)
for s in ('top', 'right'):
    ax1.spines[s].set_visible(False)
i8 = list(ks[1:]).index(8)
ax1.annotate('-6.0%', xy=(8, rel[i8]), xytext=(0, -14), textcoords='offset points',
             ha='center', fontsize=9.5, color=RUST, fontweight='bold')
ax1.annotate('-1.5%', xy=(9, rel[i8 + 1]), xytext=(0, -14), textcoords='offset points',
             ha='center', fontsize=9.5, color=RUST)
ax1.set_title('(a) 困惑度的边际收益', fontsize=11.5, color='#1A1A1A', pad=8)

ax2.axvspan(7.5, 9.5, color=ORANGE, alpha=0.12, zorder=0)
ax2.plot(cks, cys, color=DARK, linewidth=1.7, marker='s', ms=4, mfc='white', mew=1.1, zorder=3)
ax2.plot([8], [coh[8]], 'o', ms=9, color=ORANGE, zorder=6)
ax2.plot([12], [coh[12]], 'o', ms=7, mfc='white', mew=1.6, color='#3E5C76', zorder=6)
ax2.annotate('K=8 局部峰值  -0.613', xy=(8, coh[8]), xytext=(-14, -40), textcoords='offset points',
             ha='right', fontsize=9.5, color=RUST)
ax2.annotate('K=12\n-0.573', xy=(12, coh[12]), xytext=(0, 15), textcoords='offset points',
             ha='center', fontsize=9.5, color='#3E5C76', linespacing=1.3)
ax2.set_xlabel('主题数 K', fontsize=11.5)
ax2.set_ylabel('主题一致性（u_mass，越接近 0 越好）', fontsize=11)
ax2.set_ylim(cys.min() - 0.018, cys.max() + 0.045)
ax2.set_xticks(cks); ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
ax2.grid(axis='y', color='#E6E3DA', lw=0.8, zorder=0); ax2.set_axisbelow(True)
for s in ('top', 'right'):
    ax2.spines[s].set_visible(False)
ax2.set_title('(b) 主题一致性曲线', fontsize=11.5, color='#1A1A1A', pad=8)

caption(fig, '图  官方语料 K 值选择的双重证据：困惑度在 K=8 后边际收益骤降，u_mass 一致性在 K=8 出现局部峰值')
fig.tight_layout(rect=[0, 0.06, 1, 1])
p2 = os.path.join(OUT, '官方LDA_K值选择_双证据.png')
fig.savefig(p2, dpi=300); plt.close(fig)
print('saved', p2)
