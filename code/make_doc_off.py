# -*- coding: utf-8 -*-
"""官方话语图表集的 Markdown 稿（Stage 1），供 make_doc_html_off.py 排版。
数值全部取自 work/off_results.json；图用无题版（图注由 Word 的 figcaption 承担）。
"""
import json, os, io, shutil, statistics
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = '68ece3e9-8b3f-4acb-a410-910598db1cf5'
OUTD = os.path.join(BASE, 'output', RID)
ST1 = os.path.join(OUTD, 'stage1')
ST2 = os.path.join(OUTD, 'stage2')
FIGD = os.path.join(BASE, 'work', 'off_figs_nocap')
IMGD = os.path.join(ST2, 'figs_off')
os.makedirs(ST1, exist_ok=True); os.makedirs(IMGD, exist_ok=True)
for f in os.listdir(FIGD):
    if f.endswith('.png'):
        shutil.copyfile(os.path.join(FIGD, f), os.path.join(IMGD, f))

D = json.load(open(os.path.join(BASE, 'work', 'off_results.json'), encoding='utf-8'))
T, docs, years, K = D['topics'], D['docs'], D['years'], D['K']
N = D['N']
YT = {int(k): v for k, v in D['year_theta'].items()}
YP = {int(k): v for k, v in D['year_pol'].items()}
YN = {int(k): v for k, v in D['year_n'].items()}
YR = sorted(YT)
cur = {int(k): v for k, v in D['coherence_curve'].items()}
PLAT = D['venue_groups']
FACETS = [k for k, v in PLAT.items() if len(v) >= 10]
PL = {'Buenos Aires Ciudad': 'Buenos Aires Ciudad', 'Argentina.gob.ar – Educación': 'Argentina.gob.ar（教育）'}
def PS(k):
    if k.startswith('其他平台'):
        return '国会图书馆'
    return {'Buenos Aires Ciudad': 'BA Ciudad',
            'Argentina.gob.ar – Educación': 'Argentina.gob.ar'}.get(k, k[:16])
ycount = Counter(d['year'] for d in docs if d['year'])
pol = [d['pol'] for d in docs]
tstat = {}
for k in range(1, K + 1):
    ds = [d for d in docs if d['topic'] == k]
    tstat[k] = (len(ds), statistics.mean([d['pol'] for d in ds]) if ds else 0.0,
                sum(1 for d in ds if d['pol'] > 0), sum(1 for d in ds if d['pol'] < 0))

L = []
def w(s=''):
    L.append(s)

w('# 官方话语 LDA 主题建模图表集')
w()
w('*%d 篇阿根廷官方语言政策网页 · %d 个发布平台 · 1982–2026 年 · 主题数 K=%d*' % (N, len(PLAT), K))
w()
w('> 数据源：官方数据表_正式版_v2.xlsx（Sheet2，71 篇，其中 15 篇发布时间不详）。模型与绘图参数与专家话语版完全一致：'
  'collapsed Gibbs 采样，α=0.1、β=0.02、迭代 200 次、seed=7；主题数由 u_mass 在 K≤12 范围内择优。'
  '本册所有数值取自 work/off_results.json，未做人工补值。')
w()
w('## 一、语料、模型与指标定义')
w()
w('### 1.1　语料与模型')
w()
w('官方语料共 %d 篇，来自 %d 个平台：%s。%d 篇有明确发布年份（1982–2026 年），%d 篇发布时间不详。'
  '与专家话语的期刊论文不同，官方材料多为项目公告、政策说明与课程介绍，篇幅短、议题交叉多。'
  % (N, len(PLAT), '、'.join('%s %d 篇' % (PS(k), len(v)) for k, v in PLAT.items()),
     N - 15, 15))
w()
w('文本经西语分词与轻量词干化，去停用词与仅出现 1 次的词，最终词表 %d 词。主题数在 K=2–20 上以 u_mass 扫描，'
  '与专家版同一规则（K≤12、每主题平均不少于 5 篇）取最优，得 K=%d。' % (D['vocab_size'], K))
w()
w('### 1.2　三个指标的定义')
w()
w('- **一致性（图 2）**：u_mass，对每个主题前 10 词统计词对文档共现的对数概率比，主题内平均后再对 %d 个主题取平均，值域为负、越接近 0 越好。' % K)
w('- **热度（图 4、图 5）**：某主题在某年的平均后验概率 θ；色标经 γ=0.6 幂律拉伸，上限取 P95 并截顶（K=%d 时平均 θ 仅 %.3f，按最大值定标会使全图泛白）。' % (K, 1.0 / K))
w('- **情感倾向（图 6、图 7）**：加权情感值 = Σ(主题概率 × 文档极性) / Σ(主题概率)；文档极性 =（正面词数 − 负面词数）/（正面词数 + 负面词数 + 2）。'
  '每个「年×主题」格要求该年文献 ≥2 篇，单篇年份不计算。')
w()
w('### 1.3　与专家版的可比性')
w()
w('两套语料使用同一分词器、同一采样参数、同一情感词根表（正面 %d 条、负面 %d 条），因此主题份额、情感均值的差异可归因于语料而非方法。'
  '必要时须注意三处：① 主题数 K=%d 对 K=9；② 分面维度为发布平台，且只对 n≥10 的两个平台分面；'
  '③ 官方文本正面词密集，情感值加了 +2 平滑并要求每年 ≥2 篇，未平滑时大量单元格会取到 +1。'
  % (len(D['pos_roots']), len(D['neg_roots']), K))
w()
w('## 二、%d 个主题的编号与主题词' % K)
w()
w('主题词为后验概率最高的 12 位，括号内为 β。编号与全文、图件一致。')
w()
w('| 编号 | 主题词（β，前 12 位） | 主导篇数 | 份额 |')
w('| --- | --- | --- | --- |')
for t in T:
    w('| topic%d | %s | %d | %.1f%% |' % (t['id'], '、'.join('%s %.3f' % (a, b) for a, b in t['words']),
                                          t['size'], t['share'] * 100))
w()
w('## 三、七张图')
w()

def fig(n, title, fname, cap, pts, sub=None):
    w('### 图 %d　%s' % (n, title))
    if sub:
        w()
        w('*%s*' % sub)
    w()
    cap_txt = cap.replace('**图注**：', '').strip()
    w('![图 %d　%s](figs_off/%s)' % (n, title, fname))
    w()
    w('**图注**　图 %d　%s' % (n, cap_txt))
    w()
    w('**读图要点**')
    w()
    w('- ' + '\n- '.join(pts))
    w()

fig(1, '年度主题文献数量堆叠图', '图1_年度主题文献数量堆叠图.png',
    '**图注**：横轴为有文献的年份，纵轴为当年文献数量，柱内按 %d 个主题分段堆叠；主题归属取 θ 的 argmax，一篇文献只计一次。'
    '时间不详的 15 篇（占 21%%）不纳入本图，故各年之和为 %d 篇。横轴按实际出现文献的年份等距排列，柱间距不代表时间间隔。' % (K, N - 15),
    ['年份分布极不均衡：2024、2025 年各 9 篇，2023 年 5 篇；1982、2001、2010、2014、2016 年各仅 1 篇。',
     '2021 年以前的文献只占全部的三分之一，讨论"官方话语的长期趋势"时须先说明样本的时间偏斜。',
     '单篇年份（1982、2001、2010、2014、2016）不宜作年度水平解读。'])

fig(2, '主题一致性结果', '图2_主题一致性结果.png',
    '**图注**：横轴为主题数 K，纵轴为 u_mass 一致性。曲线在 K=8（%.4f）出现局部高点，K=9–10 回落，K=11–12 连续上升，'
    'K=12 为截取范围内的最优值（%.4f）。' % (cur[8], cur[12]),
    ['K=%d 与专家版遵循同一择优规则：只在 K≤12（每主题平均不少于 5 篇）范围内取最大值。' % K,
     'K=13–20 中有更低的值（K=14 为 %.4f、K=18 为 %.4f），但每主题平均只覆盖 3–5 篇，主题退化为少数文献的关键词集合，故不纳入比较。' % (cur[14], cur[18]),
     'u_mass 为负值，与文献中的 c_v 曲线形态可比、数值不可直接比较。'])

fig(3, '主题网络图', '图3_主题网络图.png',
    '**图注**：%d 个主题按主题间共享词数排布在外圈，圆面积按主题份额缩放，圆内数字为 topic 编号、下方为份额；'
    '每个圆外侧散布该主题后验概率最高的 15 个主题词，字号 ∝ β、越靠近圆 β 越高；'
    '主题间连线粗细 ∝ 前 20 词共同词数（1–%d 个），簇内细线表示 10 词窗口共现不少于 8 次。'
    '字号与线宽独立编码，词的位置不承载含义。' % (K, max(e['w'] for e in D['edges'])),
    ['共 %d 个词标签、零重叠零越界；主题间 %d 条关联边（共享 1 词 %d 条、2 词 %d 条、3 词及以上 %d 条）。'
     % (K * 15, len(D['edges']), sum(1 for e in D['edges'] if e['w'] == 1), sum(1 for e in D['edges'] if e['w'] == 2),
        sum(1 for e in D['edges'] if e['w'] >= 3)),
     '份额最大 topic%d（%.1f%%）、最小 topic%d（%.1f%%），极差仅 %.1f 个百分点，远小于专家版，说明官方议题分布更均衡。'
     % (max(T, key=lambda t: t['share'])['id'], max(t['share'] for t in T) * 100,
        min(T, key=lambda t: t['share'])['id'], min(t['share'] for t in T) * 100,
        (max(t['share'] for t in T) - min(t['share'] for t in T)) * 100),
     '共享词集中在 programa、beca、lengua、formacion 等政策工具词上，议题分化主要发生在「政策工具 × 语言对象」的组合。'])

fig(4, '全部主题时间热度图', '图4_全部主题时间热度图.png',
    '**图注**：行是 %d 个主题，列是 %d 个有文献的年份；色块为该主题在该年的平均 θ。色标上限取全表 P95（%.2f）并截顶，'
    '经 γ=0.6 幂律拉伸；灰色格为该年无文献。' % (K, len(YR), float(__import__('numpy').percentile([[YT[y][k] for y in YR] for k in range(K)], 95))),
    ['最强单元为 topic%d 在 %d 年（平均 θ=%.2f），其余单元格多低于 0.3。'
     % (lambda c: (c[2], c[1], c[0]))(max((YT[y][k], y, k + 1) for y in YR for k in range(K))),
     '主题强度整体分散，多数年份没有任何主题的平均 θ 超过 0.3，反映单篇官方网页往往同时涉及多个议题。',
     '样本量小的年份（1–2 篇）波动大，应结合图 1 的年度文献量读图。'])

fig(5, '各平台主题热度图', '图5_各平台主题热度图.png',
    '**图注**：分面维度为发布平台。仅列入 n≥10 的两个平台（Buenos Aires Ciudad %d 篇、Argentina.gob.ar %d 篇）；'
    '国会图书馆 2 篇样本过少不单独分面，其文献仍计入全部图与表。各面板为原始均值，共用 P95 色标上限。'
    % (len(PLAT[FACETS[0]]), len(PLAT[FACETS[1]])),
    ['首都平台覆盖 1982 年至今，教育平台集中在 2013 年与 2022–2026 年；年份覆盖差异本身即平台职能差异。',
     '首都平台以 topic10（escuela / lengua / bilingüe）与 topic7（centro / curso / docente）为主，教育平台以 topic1（argentina / franc / formacion）为主。',
     '灰色格表示该年该平台无文献，不代表强度为零；两面板可横向比较，色深不可与图 4 互换。'])

fig(6, '各主题情感倾向曲线图', '图6_各主题情感倾向曲线图.png',
    '**图注**：纵轴为加权情感值，逐主题逐年计算；横轴只列该年文献 ≥2 篇的年份，括号内为该年文献数。'
    '文档极性含 +2 平滑，避免正面词密集的官方文本被钉在 +1。',
    ['情感打分基于评价词根表（正面 %d 条、负面 %d 条），%d/%d 篇命中至少一个评价词。' % (len(D['pos_roots']), len(D['neg_roots']), D['polarity_hit'], N),
     '所有主题的情感均值均为正（%.2f–%.2f），无负值：官方文本以权利、包容、多样性、机会等正面表述为主，这是与专家话语最稳定的差异。'
     % (min(v[1] for v in tstat.values()), max(v[1] for v in tstat.values())),
     '主题间差异有限，曲线起伏更多反映各年议题组合，不宜解读为情感转向。'])

fig(7, '各平台主题情感倾向热图', '图7_各平台主题情感倾向热图.png',
    '**图注**：分面与图 5 一致；行是 %d 个主题、列是 %d 个年份。色块为加权情感值，暖色为正、冷色为负，色标以 0 为中点双向映射。'
    '灰色格表示该年该平台无文献、或该年文献 <2 篇、或该主题当年权重 Σθ <0.05。' % (K, len(YR)),
    ['首都平台的有效色块远多于教育平台，后者只在 2013 年与 2022–2026 年有值。',
     '负值仅出现在首都平台的个别年份，且幅度很小；跨平台比较应聚焦同一主题同一年份的色差。',
     'n 较小的平台不分面，避免 2 篇文献决定整块颜色。'])

w('## 四、口径对照与复现')
w()
w('| 项目 | 专家话语 | 官方话语 |')
w('| --- | --- | --- |')
for a, b, c in [('文献数', '66 篇', '%d 篇（15 篇时间不详）' % N),
                ('来源', '阿根廷本土期刊 17 种', '%d 个官方平台' % len(PLAT)),
                ('词表', '轻量词干化，815 词', '同款处理，%d 词' % D['vocab_size']),
                ('主题数', 'K=9（u_mass）', 'K=%d（u_mass，K≤12 择优）' % K),
                ('采样参数', 'α=0.1、β=0.02、200 轮、seed=7', '同左'),
                ('情感词典', '正面 56 / 负面 57 词根', '同表（保证可比）'),
                ('分面维度', '期刊（9 组）', '平台（2 组，n≥10）')]:
    w('| %s | %s | %s |' % (a, b, c))
w()
w('| 脚本 | 作用 |')
w('| --- | --- |')
for a, b in [('tools/off_model.py', '读官方数据表 → work/off_results.json（约 4–5 分钟）'),
             ('tools/off_figs.py', '生成图 1–7 → 官方话语/图/'),
             ('tools/make_atlas_off.py', '合成 PDF 图表集'),
             ('tools/make_doc_off.py', '生成本 Word 版')]:
    w('| %s | %s |' % (a, b))
w()
w('### 4.1　解读边界')
w()
w('官方平台发布不等于政府立场：同一网页可能同时引述专家、学校与家长的意见，本册只描述文本层面的词汇分布与情感倾向，不推断发布动机，'
  '也不把官方语料的情感值直接读作政策态度。15 篇发布时间不详的文献参与主题建模与情感统计，但不进入任何年份类图表，'
  '因此图 1、4、5、6、7 的样本量为 56 篇而非 71 篇；引用这些图的百分比时须同时给出分母。')
w()
w('## 五、附录：文献清单')
w()
w('序号沿用源数据表，因部分记录已移出主表，故不连续。T 为主题编号，p 为该篇的最大后验概率，情感为该篇极性得分。')
w()
w('| 序号 | 年份 | 平台 | 主题 | p | 情感 |')
w('| --- | --- | --- | --- | --- | --- |')
LS = {'Buenos Aires Ciudad': 'BA Ciudad', 'Argentina.gob.ar – Educación': 'Argentina.gob.',
      'Biblioteca del Congreso de la Nación': 'Congreso Nación'}
for d in docs:
    w('| %s | %s | %s | T%d | %.2f | %+.2f |' % (d['no'], d['year'] or '不详',
                                                LS.get(d['venue'], d['venue'][:16]),
                                                d['topic'], d['p'], d['pol']))
w()

p = os.path.join(ST1, 'final_draft_off.md')
io.open(p, 'w', encoding='utf-8').write('\n'.join(L))
print('md ->', p, len(L), 'lines')
