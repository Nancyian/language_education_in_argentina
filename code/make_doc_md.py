# -*- coding: utf-8 -*-
"""由 work/lab_results.json 现算数值，生成 Word 版图表集的 Markdown 源（stage1/final_draft.md）。

数值口径与 专家话语_LDA主题建模_图表集.pdf 完全一致：
同一份 lab_results.json、同一套图注/读图要点文字、同一批 320 dpi 图件。
"""
import json, os, shutil, statistics
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = '68ece3e9-8b3f-4acb-a410-910598db1cf5'
OUTD = os.path.join(BASE, 'output', RID)
IMGD = os.path.join(OUTD, 'stage2', 'images')
FIGD = os.path.join(BASE, 'work', 'figs_nocap')
os.makedirs(os.path.join(OUTD, 'stage1'), exist_ok=True)
os.makedirs(IMGD, exist_ok=True)

D = json.load(open(os.path.join(BASE, 'work', 'lab_results.json'), encoding='utf-8'))
T, docs = D['topics'], D['docs']
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
N, hit, K = D['N'], D['polarity_hit'], D['K']
LEX  = '正面 %d 条、负面 %d 条' % (len(D['pos_roots']), len(D['neg_roots']))

SHORT = {'RAHL: Revista argentina de historiografía lingüística': 'RAHL · 语言学史',
         'Traslaciones: Revista Latinoamericana de Lectura y Escritura': 'Traslaciones · 读写',
         'Signo y Seña': 'Signo y Seña', 'Quintú Quimün: revista de lingüística': 'Quintú Quimün',
         'Anclajes': 'Anclajes', 'Integración y Conocimiento': 'Integración y Conocimiento',
         'Signos ELE: Revista de Español como Lengua Extranjera': 'Signos ELE',
         'Argonautas': 'Argonautas', '其他期刊（9 种）': '其他期刊（9 种）'}
FIGS = [(1, '图1_年度主题文献数量堆叠图.png', '年度主题文献数量堆叠图', '66 篇文献按发表年份与主导主题归属统计（每篇计 1 次）'),
        (2, '图2_主题一致性结果.png', '主题一致性结果', 'K=2–12 的 u_mass 主题一致性曲线'),
        (3, '图3_主题网络图.png', '主题网络图', '9 个主题节点、各主题后验概率前 15 位主题词及其共现连线'),
        (4, '图4_全部主题时间热度图.png', '全部主题时间热度图', '9 个主题 × 20 个有文献年份的主题强度矩阵'),
        (5, '图5_各期刊主题热度图.png', '各期刊主题热度图', '9 个期刊面板，每面板为 主题 × 年份 的强度矩阵'),
        (6, '图6_各主题情感倾向曲线图.png', '各主题情感倾向曲线图', '9 个主题的加权情感值随年份变化'),
        (7, '图7_各期刊主题情感倾向热图.png', '各期刊主题情感倾向热图', '9 个期刊面板，每面板为 主题 × 年份 的情感矩阵')]

ycount = Counter(d['year'] for d in docs)
period = {'≤2013': 0, '2014-2018': 0, '2019-2022': 0, '2023-2026': 0}
PLABEL = {'≤2013': '1999–2013', '2014-2018': '2014–2018', '2019-2022': '2019–2022', '2023-2026': '2023–2026'}
for y, c in ycount.items():
    period['≤2013' if y <= 2013 else '2014-2018' if y <= 2018 else '2019-2022' if y <= 2022 else '2023-2026'] += c
P4 = period['2014-2018'] + period['2019-2022'] + period['2023-2026']

pol = lambda ds: [d['pol'] for d in ds]
pos_n = sum(1 for d in docs if d['pol'] > 0)
neg_n = sum(1 for d in docs if d['pol'] < 0)
zero_n = N - pos_n - neg_n
cancel = sum(1 for d in docs if d['pol'] == 0 and (d['pos'] + d['neg']) > 0)
cur = {int(k): v for k, v in D['coherence_curve'].items()}
vg = D['venue_groups']
vstat = {v: (lambda ms: (ms.index(max(ms)) + 1, statistics.mean(pol([docs[i] for i in idx]))))(
    [sum(docs[i]['theta'][k] for i in idx) / len(idx) for k in range(9)]) for v, idx in vg.items()}
tstat = {k: (sum(1 for d in docs if d['topic'] == k),
             statistics.mean(pol([d for d in docs if d['topic'] == k])),
             sum(1 for d in docs if d['topic'] == k and d['pol'] > 0),
             sum(1 for d in docs if d['topic'] == k and d['pol'] < 0)) for k in range(1, 10)}

# ---------- 图件复制为 ASCII 名，避免转换链上的编码问题 ----------
for i, fn, _, _ in FIGS:
    shutil.copyfile(os.path.join(FIGD, fn), os.path.join(IMGD, 'fig%d.png' % i))

L = []
w = L.append

w('# 专家话语 · LDA 主题建模图表集')
w('')
w('66 篇阿根廷语言教育类期刊论文 · 17 种期刊 · 1999–2026 年 · 主题数 K=9')
w('')
w('> 说明：本文件所有数值均直接来自同一份 LDA 结果文件（work/lab_results.json），未做任何人工补值或重新拟合；'
  '每张图下方的数据表即为该图所用数值的直接汇总，可逐项核对。')
w('')
w('## 摘要')
w('')
w('本文件汇编「专家数据表_正式版」Sheet2 中 66 篇阿根廷语言教育类期刊论文摘要的 LDA 主题建模结果，'
  '含 7 张图与 13 张同源数据表。语料时间跨度 1999–2026 年，涉及 17 种阿根廷本土期刊。'
  '建模以摘要正文为输入，经西语分词与轻量词干化后得到 815 词词表；主题数由 u_mass 一致性在 K=2–20 上扫描选定，取 K=9；'
  '推断采用 collapsed Gibbs 采样（α=0.1，β=0.02，迭代 200 次，seed=7）。'
  '情感倾向由评价性词根表（' + LEX + '）以词典法打分，非预训练情感模型。')
w('')
w('**关键词：**LDA 主题建模；阿根廷；语言教育；期刊话语；u_mass 一致性；情感倾向')
w('')
w('## 图表目录')
w('')
w('| 编号 | 名称 | 内容 |')
w('|------|------|------|')
for i, _, name, sub in FIGS:
    w('| 图 %d | %s | %s |' % (i, name, sub))
w('')

# ---------- 一 ----------
w('## 一、语料、模型与指标定义')
w('')
w('读图前应先确认以下四组定义，图中的每一个数字都按此口径生成。')
w('')
w('### 1.1 语料与模型')
w('')
w('语料为「专家数据表_正式版」Sheet2 的 66 篇文献摘要，全部发表于阿根廷本土期刊，涉及 17 种期刊、1999–2026 年。'
  '建模只用摘要正文，按西语分词并作轻量词干化（去复数、去部分屈折），保留名词、动词、形容词，'
  '去掉停用词与仅出现 1 次的词，最终词表 815 词。')
w('')
w('主题数 K 通过 u_mass 一致性在 K=2–20 上扫描确定，取曲线第一个高平台 K=9（详见「图 2 主题一致性结果」）。'
  '推断用 collapsed Gibbs 采样，α=0.1、β=0.02、迭代 200 次、随机种子 7，可复现。')
w('')
w('**表 1　运行参数与数据来源**')
w('')
w('| 项目 | 说明 |')
w('|------|------|')
w('| 语料 | 专家数据表_正式版(1).xlsx · Sheet2 · 66 篇（已剔除境外期刊记录） |')
w('| 模型 | LDA · collapsed Gibbs 采样 · α=0.1，β=0.02，迭代 200 次，seed=7 |')
w('| 词表 | min_df=2、max_df=0.55，西语轻量词干化后 815 词；主题数由 u_mass 择优 |')
w('| 绘图 | Python 3.13 + matplotlib 3.11，320 dpi 位图原像素嵌入 |')
w('| 配色 | 「海洋清风」8 色：#BFDFD2 #51999F #4198AC #7BC0CD #DBCB92 #ECB66C #EA9E58 #ED8D5A |')
w('')
w('### 1.2 三个指标的确切定义')
w('')
w('**一致性（图 2）**：u_mass。对每个主题的前 10 个词，统计词对在文档共现中的对数概率比，'
  '主题内平均后再对 9 个主题取平均。值域为负，越接近 0 越好。')
w('')
w('**热度（图 4、图 5）**：某主题在某年的平均后验概率 θ。图 4 对全表做 min–max 归一化到 0–1；图 5 用原始均值、九面板共用色标上限。'
  '0 表示该年该主题几乎不出现，1 表示全样本中最高强度。')
w('')
w('**情感倾向（图 6、图 7）**：加权情感值 = Σ(主题概率 × 文档极性) / Σ(主题概率)；'
  '文档极性 = (正面词数 − 负面词数) / (正面词数 + 负面词数 + 2)，分母 2 为平滑项，'
  '避免单篇仅 1 个评价词时取到 ±1。')
w('')
w('### 1.3 必须交代的一点')
w('')
w('情感指标由评价性词根表（' + LEX + '）打分，属词典法，不是预训练情感模型。'
  '论文方法章应写「基于评价词表的词典法情感打分」，不宜写作 BERT 或深度学习情感分类。词表随结果一并给出，可逐条复核。')
w('')
w('### 1.4 时间片划分口径')
w('')
w('四个时期由文献量的自然断点确定，用于图 4 的分期读图；时间片再细分则每片不足 8 篇，主题均值不可估计。')
w('')
w('| 年份区间 | 篇数 | 占语料 | 该期平均 θ 超过 10% 的主题数 | 该期平均 θ 最高的主题 |')
w('|---------|-----:|-------:|---------------------------:|----------------------|')
for k, v in period.items():
    j = max(range(1, 10), key=lambda x: T[x - 1]['periods'][k])
    w('| %s | %d | %.1f%% | %d | topic%d（%s） |' % (PLABEL[k], v, v / N * 100,
      sum(1 for t in T if t['periods'][k] > 0.10), j, KW2[j]))
w('')
w('注：「该期主题数」为平均 θ 超过 10% 的主题个数，用于说明分期后主题集中度的变化，不是新增指标。')
w('')

# ---------- 二 ----------
w('## 二、九个主题的编号与主题词')
w('')
w('主题词为模型输出中后验概率最高的 12 位，括号内为 β 值。')
w('')
w('| 编号 | 主题词（β，前 12 位） | 主导篇数 | 份额 |')
w('|------|----------------------|--------:|-----:|')
for t in T:
    ws = '、'.join('%s（%.3f）' % (wd, v) for wd, v in t['words'][:12])
    w('| topic%d | %s | %d | %.1f%% |' % (t['id'], ws, t['size'], t['share'] * 100))
w('')
w('合计：主导篇数 %d 篇（= 全部语料），份额合计 100%%。「主导篇数」为按 argmax 归属的篇数，'
  '「份额」为平均后验概率之和，两者口径不同，故不完全成比例。' % sum(t['size'] for t in T))
w('')
w('三点阅读提示：')
w('')
w('1. 词表经轻量词干化，故主题词常为词干残缺形式（sena ← seña、guarani ← guaraní、'
  'politica ← política、ensenanza ← enseñanza），这是词干化的产物，不是拼写错误。')
w('2. 主题仅以编号与主题词呈现，不附加人工命名；主题词表本身即模型输出，解读时应以词表为唯一依据。')
w('3. topic2 的 aire、bueno 与 topic5 的 anos、escrito 属语料中高频的通用词，虽进入前 12 位但区分度低，'
  '解读时应结合后验概率与跨主题分布，不宜单看个别词。')
w('')

# ---------- 三 ----------
w('## 三、七张图与读图要点')
w('')
w('每张图后附三部分：图注（说明坐标与算法口径）、读图要点（可直接写入论文正文的结论）、'
  '数据表（该图所用数值的直接汇总，可逐项核对）。')
w('')

caps = {}
caps[1] = (
    '横轴为 1999–2026 年，纵轴为当年文献数量，柱内按 9 个主题分段堆叠。主题归属取文档—主题后验概率 θ 的最大值（argmax），'
    '一篇文献只计入一个主题，故各年数量之和等于当年文献总数。图例编号与全文主题编号一致。',
    ['分期文献量：≤2013 年 %d 篇、2014–2018 年 %d 篇、2019–2022 年 %d 篇、2023–2026 年 %d 篇；'
     '2014 年及以后的文献占全部的 %.0f%%。' % (period['≤2013'], period['2014-2018'], period['2019-2022'],
                                        period['2023-2026'], P4 / N * 100),
     '2000–2008 年无文献。横轴只保留实际出现文献的年份并等距排列，刻度标签为真实年份，因此柱间距不代表时间间隔。',
     '1999、2002 年各仅 1 篇，2026 年为当年入库文献（收录尚不完整），三处不宜作为年度水平解读。'])
caps[2] = (
    '横轴为主题数 K，纵轴为 u_mass 一致性（值域为负，越接近 0 越好）。曲线在 K=8（%.4f）与 K=9（%.4f）出现第一个高平台，'
    'K=9 为截取范围内的最优值；K=10–11 回落，K=12 回升至 %.4f，与 K=9 数值相同但主题已更碎。' % (cur[8], cur[9], cur[12]),
    ['模型最终取 K=9，与上一轮建模报告一致；图 1、3、4、5、6、7 的主题编号均据此排列。',
     '横轴截到 K=12：再往上单个主题平均只覆盖 5 篇左右（K=18 时不到 4 篇），主题逐渐退化为少数文献的关键词集合，指标会「虚高」而失去解释力'
     '（K=18 的 %.4f 即属此类）。' % cur[18],
     '本图量纲为 u_mass（负值），若与参考文献中的 c_v 曲线对照，形态可比、数值不可直接比较。'])
EW = Counter(e['w'] for e in D['edges'])
caps[3] = (
    '9 个主题按主题间共享词数做力导向排布，圆面积按主题份额（平均后验概率）缩放，圆内为 topic 编号与份额；'
    '每个主题外围是其 φ 值最高的 15 个主题词，词的文字本身即网络节点，字号正比于 β，连线两端裁到文字边缘。'
    '主题之间的灰线粗细正比于两主题各自前 20 词的共同词数（1–6 个）；簇内更细的连线表示该主题词在语料 10 词窗口内共现不少于 6 次。'
    '字号与两类线宽各自独立编码，词的角度位置不承载含义。',
    ['主题间共 %d 条关联边：共享 1 个词 %d 条、2 个词 %d 条、3 个词 %d 条、6 个词 1 条（topic4 与 topic9）。'
     % (len(D['edges']), EW[1], EW[2], EW[3]),
     '份额差异：最大为 topic2（%.1f%%）与 topic7（%.1f%%），最小为 topic5（%.1f%%）。'
     % (T[1]['share'] * 100, T[6]['share'] * 100, T[4]['share'] * 100),
     '连线由主题词重叠与语料共现生成（如 educacion、linguistic、ensenanza 同时出现在多个主题），'
     '因此反映词汇与语境关联，不等同于文献引用或作者合作关系。'])
caps[4] = (
    '行是 9 个主题，列是 1999–2026 年中有文献的 20 个年份；色块为该主题在该年的平均后验概率，'
    '全表 min–max 归一化到 0–1，深色代表强度高；色标再经 γ=0.6 幂律拉伸，以放大低强度区间的差异。白色格为该年无文献。',
    ['走向明确的三个主题：topic7 由 ≤2013 年的 %.3f 降至 2019–2022 年的 %.3f；topic8 由 %.3f 降至 %.3f；'
     'topic5 则相反，由 2019–2022 年的 %.3f 升至 2023–2026 年的 %.3f。'
     % (T[6]['periods']['≤2013'], T[6]['periods']['2019-2022'], T[7]['periods']['≤2013'],
        T[7]['periods']['2019-2022'], T[4]['periods']['2019-2022'], T[4]['periods']['2023-2026']),
     'topic2 在 2019–2022 年达峰（%.3f），topic4 同期达峰（%.3f），topic9 由 2014–2018 年的 %.3f 升至 2023–2026 年的 %.3f。'
     % (T[1]['periods']['2019-2022'], T[3]['periods']['2019-2022'],
        T[8]['periods']['2014-2018'], T[8]['periods']['2023-2026']),
     '单元格为该年平均 θ，样本量小的年份（1–2 篇）波动大，读图时应结合图 1 的年度文献量一起看。'])
caps[5] = (
    '分面维度由参考图的「国家」改为「期刊」——本语料 66 篇全部发表于阿根廷本土期刊，不存在国别差异。'
    '9 个面板 = 文献量 ≥3 篇的 8 种期刊 +「其他期刊（9 种，各 1–2 篇）」，覆盖全部 66 篇，无遗漏、无合并删减。'
    '各面板为原始均值，共用同一色标上限（vmax 取全部面板最大值），并统一经 γ=0.6 幂律拉伸；灰色格表示该年该期刊无文献。'
    '面板之间可横向比较，但色深不可与图 4 直接互换。',
    ['期刊取向差异清晰：RAHL（n=15）以 topic7（gramatica / historiografia）为主，Traslaciones（n=10）以 topic9（espanol / spanish）为主，'
     'Signo y Seña（n=8）以 topic5（sena / guarani）为主，Quintú Quimün 与 Signos ELE 均以 topic6（espanol / segunda）为主。',
     '文献量少的期刊面板大面积灰格，仅表示「该年无文献」，不代表强度为零。',
     '同一主题在不同期刊的峰值年份常不一致，说明主题热度同时受期刊取向与年度议题设置影响，不能只归因于时间趋势。'])
caps[6] = (
    '纵轴为加权情感值：Σ(主题概率 × 文档极性) / Σ(主题概率)，逐主题逐年计算。'
    '文档极性 = (正面词数 − 负面词数) / (正面词数 + 负面词数 + 2)，分母的 2 为平滑项。'
    '横轴年份与图 1 一致，仅列有文献的年份。',
    ['情感打分基于评价性词根表（' + LEX + '）的词典法，%d/%d 篇命中至少一个评价词。' % (hit, N),
     '全样本极性为正 %d 篇、为负 %d 篇、为 0 的 %d 篇（其中 %d 篇正负相抵、%d 篇未命中评价词），'
     '整体偏正（均值 %.3f）。' % (pos_n, neg_n, zero_n, cancel, zero_n - cancel, statistics.mean(pol(docs))),
     '主题间差异明显：topic3（%.3f）与 topic9（%.3f）最高，topic2（%.3f）最低。这是词典法而非预训练情感模型，'
     '方法章须写作「基于评价词表的词典法情感打分」；单篇文献主导的年份波动大，不构成趋势证据。'
     % (tstat[3][1], tstat[9][1], tstat[2][1])])
caps[7] = (
    '分面维度同为「期刊」，面板划分与图 5 完全一致；行是 9 个主题、列是 20 个有文献年份。'
    '色块为加权情感值 Σ(主题概率 × 文档极性) / Σ(主题概率)，暖色为正、冷色为负；色标以 0 为中点双向映射'
    '（负端 −' + PRLO_S + '、正端 ' + PRHI_S + '），故颜色深浅可跨面板直接比较。灰色格表示该年该期刊无文献，或该主题在当年的权重 Σθ 低于 0.05。',
    ['色块只在该期刊当年确有文献且该主题权重 ≥0.05 时才有取值，同一面板内不同主题的有效年份可能不同。',
     '期刊均值极性区间为 %.2f（Signo y Seña，n=8）至 %.2f（Integración y Conocimiento，n=4）；'
     '文献量最大的 RAHL（n=15）为 %.2f，Traslaciones（n=10）为 %.2f。'
     % (vstat['Signo y Seña'][1], vstat['Integración y Conocimiento'][1],
        vstat['RAHL: Revista argentina de historiografía lingüística'][1],
        vstat['Traslaciones: Revista Latinoamericana de Lectura y Escritura'][1]),
     'n ≤5 的面板（Anclajes、Integración y Conocimiento、Signos ELE、Argonautas）由 2–3 篇文献即可决定色块取值，'
     '不宜据此判断期刊层面的情感倾向；跨期刊比较应只针对 RAHL 与 Traslaciones。'])


def table1():
    ys = sorted(ycount.items())
    rows = []
    for i in range(len(ys) // 2 + len(ys) % 2):
        a = ys[i]
        b = ys[i + 10] if i + 10 < len(ys) else ('', '')
        rows.append('| %s | %s | %s | %s |' % (a[0], a[1], b[0], b[1]))
    return '各年文献量（篇，共 %d 篇）' % N, '| 年份 | 篇数 | 年份 | 篇数 |\n|-----:|-----:|-----:|-----:|', rows


def table2():
    ks = [k for k in sorted(cur) if k <= 12]
    rows = ['| %d | %.4f |' % (k, cur[k]) for k in ks]
    return 'u_mass 一致性逐 K 取值', '| 主题数 K | u_mass |\n|--------:|-------:|', rows


def table3():
    es = sorted(D['edges'], key=lambda e: -e['w'])[:9]
    rows = ['| topic%d | topic%d | %d | %s |' % (e['a'], e['b'], e['w'], '、'.join(e['shared'][:3])) for e in es]
    return ('权重最高的 9 条主题关联（共 %d 条）' % len(D['edges']),
            '| 主题 A | 主题 B | 共享词数 | 共享词（前三个） |\n|--------|--------|--------:|------------------|', rows)


def table4():
    rows = []
    for t in T:
        p = t['periods']
        v = [p['≤2013'], p['2014-2018'], p['2019-2022'], p['2023-2026']]
        rows.append('| topic%d（%s） | %.3f | %.3f | %.3f | %.3f | %.1f |'
                    % (t['id'], KW2[t['id']], v[0], v[1], v[2], v[3], (max(v) - min(v)) * 100))
    return ('各主题分期平均 θ 与峰谷差（百分点）',
            '| 主题 | ≤2013 | 2014–18 | 2019–22 | 2023–26 | 峰谷差 |\n|------|------:|--------:|--------:|--------:|-------:|', rows)


def table5():
    rows = []
    for v, idx in sorted(vg.items(), key=lambda kv: -len(kv[1])):
        t, _ = vstat[v]
        rows.append('| %s | %d | %.1f%% | %s |'
                    % (SHORT.get(v, v), len(idx), len(idx) / N * 100, 'topic%d（%s）' % (t, KW2[t])))
    return ('期刊分面构成与各期刊主导主题',
            '| 期刊面板 | 篇数 | 占语料 | 主导主题（均值 θ 最大） |\n|----------|-----:|-------:|------------------------|', rows)


def table6():
    rows = []
    for k in range(1, 10):
        n, m, p, ng = tstat[k]
        rows.append('| topic%d（%s） | %d | %.3f | %d / %d / %d |' % (k, KW2[k], n, m, p, ng, n - p - ng))
    return ('各主题篇数与极性均值', '| 主题 | 篇数 | 均值极性 | 正 / 负 / 中性 |\n|------|-----:|--------:|---------------|', rows)


def table7():
    rows = []
    for v, idx in sorted(vg.items(), key=lambda kv: -len(kv[1])):
        rows.append('| %s | %d | %.3f |' % (SHORT.get(v, v), len(idx), statistics.mean(pol([docs[i] for i in idx]))))
    return ('各期刊篇数与极性均值', '| 期刊面板 | 篇数 | 均值极性 |\n|----------|-----:|--------:|', rows)


tabs = {1: table1, 2: table2, 3: table3, 4: table4, 5: table5, 6: table6, 7: table7}

for i, fn, name, sub in FIGS:
    cap, pts = caps[i]
    title, hdr, rows = tabs[i]()
    w('### 图 %d　%s' % (i, name))
    w('')
    w('*%s*' % sub)
    w('')
    w('![图 %d　%s](images/fig%d.png)' % (i, name, i))
    w('')
    w('**图注**　图 %d　%s' % (i, cap))
    w('')
    w('**读图要点**')
    w('')
    for p in pts:
        w('- %s' % p)
    w('')
    w('**数据表 · %s**' % title)
    w('')
    w(hdr)
    for r in rows:
        w(r)
    w('')

# ---------- 四 ----------
w('## 四、与参考图的差异、复现方式与文件清单')
w('')
w('以下三点在论文的方法或图注中需要明确交代，否则容易被误读为数据缺失。')
w('')
w('**差异 1　分面维度：国家 → 期刊**')
w('')
w('参考图以国家为分面，本语料 66 篇全部为阿根廷本土期刊，不存在国别差异。故改为期刊分面，'
  '9 个面板 = 文献量 ≥3 篇的 8 种期刊 +「其他期刊（9 种，各 1–2 篇）」，覆盖全部 66 篇。')
w('')
w('**差异 2　年份轴：连续年份 → 有文献年份等距**')
w('')
w('2000–2008 年无文献。若按连续年份绘制，横轴会出现近十年的空白直线，视觉上被误读为「研究中断」。'
  '故图 1、4、6、7 仅保留有文献的年份等距排列，刻度标签仍为真实年份。')
w('')
w('**差异 3　一致性量纲：c_v → u_mass**')
w('')
w('参考图为 c_v（正值，0.42–0.54），本图为 u_mass（负值，%.2f 至 %.2f）。两者单调方向相反，'
  '形态可比、数值不可直接对照，引用时须注明量纲。' % (min(cur.values()), max(cur.values())))
w('')
w('### 复现方式')
w('')
w('| 脚本 | 作用 |')
w('|------|------|')
w('| tools/lab_model2.py | K=9 主题结果 + u_mass 曲线 K=2–20 + 极性计算 |')
w('| tools/lab_pol.py | 极性平滑（λ=2） |')
w('| tools/lab_figs.py | 七张图（320 dpi PNG） |')
w('| tools/make_atlas.py | 合订本合成（A4 纵向，11 页） |')
w('')
w('中间结果：work/lab_results.json（主题词、θ 矩阵、年度矩阵、极性、期刊分组）。'
  '所有图与表均以该文件为唯一输入，未二次拟合。')
w('')
w('### 随附文件')
w('')
w('| 文件 | 说明 |')
w('|------|------|')
w('| 本文件（.docx） | 图、图注、读图要点、同源数据表合订，可直接插入论文附录或在 Word 中续写 |')
w('| 专家话语_LDA主题建模_图表集.pdf | 同内容的 A4 纵向 11 页定版，可直接打印 |')
w('| 图/图 1–7 PNG | 320 dpi 独立位图，可直接插入 Word / LaTeX |')
w('| 图注与数据口径说明.md | 纯文本版图注与口径说明，便于复制到论文正文 |')
w('')
w('待补：BERTopic 的层次聚类图、主题相似度热图与二维散点图需联网安装 bertopic、sentence-transformers 后生成；'
  '其余七张图与全部数据表不依赖该环境。')
w('')

# ---------- 附录 ----------
w('## 附录　符号与术语对照')
w('')
w('| 符号 / 术语 | 含义 | 本册取值 |')
w('|-------------|------|----------|')
w('| N | 语料文献总数 | 66 |')
w('| K | 主题数（由一致性曲线选定） | 9 |')
w('| θ（theta） | 文档 d 属于主题 k 的后验概率，每篇 9 个值，和为 1 | — |')
w('| β（beta） | 主题 k 中词 w 的出现概率，主题词表按此排序 | — |')
w('| 主导主题 | argmax θ，用于图 1 的篇数归属 | — |')
w('| 份额 | 全语料 θ 的列均值，9 个主题合计 100% | 9.9%–13.5% |')
w('| 分面（facet） | 图 5、图 7 按期刊切分面板 | 9 个面板 |')
w('')
w('## 参考文献')
w('')
w('1. Blei, D. M., Ng, A. Y., and Jordan, M. I. (2003). Latent Dirichlet Allocation. '
  '*Journal of Machine Learning Research*, 3, 993–1022.')
w('2. Mimno, D., Wallach, H. M., Talley, E., Leenders, M., and McCallum, A. (2011). '
  'Optimizing Semantic Coherence in Topic Models. In *Proceedings of the 2011 Conference on '
  'Empirical Methods in Natural Language Processing* (pp. 262–272).')
w('3. Grimmer, J., and Stewart, B. M. (2013). Text as Data: The Promise and Pitfalls of Automatic '
  'Content Analysis Methods for Political Texts. *Political Analysis*, 21(3), 267–297.')
w('4. 专家数据表_正式版(1).xlsx. Sheet2：阿根廷语言教育类期刊论文摘要语料（66 篇）[DB]. 自建语料库.')
w('')

md = '\n'.join(L) + '\n'
open(os.path.join(OUTD, 'stage1', 'final_draft.md'), 'w', encoding='utf-8').write(md)
print('md chars =', len(md), 'lines =', md.count('\n'))
print('images ->', sorted(os.listdir(IMGD)))
