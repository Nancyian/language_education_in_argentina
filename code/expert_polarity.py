# -*- coding: utf-8 -*-
"""专家话语 66 篇：情感极性逐篇标注
口径与官方话语完全一致——同一 POS/NEG 词根表、同一公式 s=(P-N)/(P+N+2)、
同一文本构造（标题 + '. ' + 原文，取自 Sheet2 第 4 / 第 9 列）。
输出：work/expert_polarity.json、桌面/阿根廷语料库/专家话语/专家话语_情感极性标注.xlsx
"""
import collections, io, json, os, re
import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx'
RES = 'work/topic_results.json'
OUT_JSON = 'work/expert_polarity.json'
OUT_XLSX = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家话语_情感极性标注.xlsx'
LAM = 2.0

# ---- 与 off_model.py 逐字相同的词根表 ----
POS = """relevan significativ fundamental necesari important avanc fortalec garantiz derecho inclus
diversidad igualdad particip mejor potencial contribu promov sosten reconoc legitim vital riqueza
oportun adecuad eficaz logro consolid ampli democrat preserv valor respeto equidad justici acces
libertad identidad patrimonio memoria empoder transform innov cooperaci articulaci compromis progres
bienestar solidar autonom dignidad visibiliz recuper rescate vigencia dialogo reconocimiento
""".split()
NEG = """deficit ausenci falta carenci desigual exclu discrimin crisis problem limitaci obstacul dificultad
precari vulnerab margin subaltern hegemon colonial imposici silencio invisibil brech conflict tensi
critic cuestion denunci riesg amenaz perdid declin escase restricci segreg estigmat racismo estereotip
dominaci subordinaci negaci olvido abandon fractur deterior retroces desprotecc precariz desmantel
recort desfinanci inequidad asimetr jerarquiz homogeneiz folkloriz exotiz subestima
""".split()

NORM = [(r'[áà]', 'a'), (r'[éè]', 'e'), (r'[íì]', 'i'), (r'[óò]', 'o'), (r'[úù]', 'u'),
        (r'ñ', 'n'), (r'ü', 'u')]


def norm_tok(w):
    w = w.lower()
    for a, b in NORM:
        w = re.sub(a, b, w)
    return w


def polarity(text):
    t = ' '.join(norm_tok(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text))
    pos = sum(t.count(r) for r in POS)
    neg = sum(t.count(r) for r in NEG)
    if pos + neg == 0:
        return 0.0, pos, neg
    return (pos - neg) / (pos + neg + LAM), pos, neg


def hits(text):
    """命中的词根（去重，供人工复核）"""
    t = ' '.join(norm_tok(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text))
    hp = [r for r in POS if r in t]
    hn = [r for r in NEG if r in t]
    return hp, hn


# ---- 读语料 ----
wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Sheet2']
rows = []
for r in range(2, ws.max_row + 1):
    if ws.cell(r, 1).value is None:
        continue
    title = str(ws.cell(r, 4).value or '').strip()
    venue = str(ws.cell(r, 5).value or '').strip()
    body = str(ws.cell(r, 9).value or '').strip()
    year_s = str(ws.cell(r, 7).value or '').strip()[:4]
    try:
        year = int(year_s)
    except ValueError:
        year = None
    rows.append(dict(no=ws.cell(r, 1).value, title=title, venue=venue,
                     year=year, period=str(ws.cell(r, 8).value or '').strip(), body=body))

D = json.load(io.open(RES, encoding='utf-8'))
N, K = D['N'], D['K']
assert len(rows) == N, 'rows=%d N=%d' % (len(rows), N)
theta = np.array([d['theta'] for d in D['docs']])

# ---- 逐篇极性 ----
recs = []
for i, r in enumerate(rows):
    txt = r['title'] + '. ' + r['body']
    s, p, n = polarity(txt)
    hp, hn = hits(txt)
    recs.append(dict(no=r['no'], title=r['title'], venue=r['venue'], year=r['year'],
                     period=r['period'], topic=int(D['docs'][i]['topic']),
                     p=float(D['docs'][i]['p']),
                     pos=p, neg=n, pol=round(s, 4),
                     pos_hits=hp, neg_hits=hn))

hit = sum(1 for x in recs if x['pos'] + x['neg'] > 0)
vals = [x['pol'] for x in recs if x['pos'] + x['neg'] > 0]
print('hit %d/%d  range %.3f..%.3f  mean %.3f' % (hit, N, min(vals), max(vals), np.mean(vals)))

# 与既有 lab_results 交叉校验（若存在）
try:
    L = json.load(io.open('work/lab_results.json', encoding='utf-8'))
    old = [d.get('pol') for d in L['docs']]
    same = sum(1 for i, x in enumerate(recs)
               if old[i] is not None and abs(old[i] - x['pol']) < 0.005)
    print('cross-check with lab_results: %d/%d identical' % (same, len(old)))
except Exception as e:
    print('cross-check skipped:', e)

# ---- 汇总 ----
def agg(idx):
    w = theta[idx]
    s = np.array([recs[i]['pol'] for i in idx])
    iv = w.sum(0)
    wpol = [float((w[:, k] * s).sum() / iv[k]) if iv[k] > 0 else 0.0 for k in range(K)]
    return dict(n=len(idx), mean=float(np.mean(s)), pos=int((s > 0).sum()),
                neg=int((s < 0).sum()), zero=int((s == 0).sum()),
                wpol=[round(x, 4) for x in wpol])


by_topic = {str(t['id']): agg([i for i, x in enumerate(recs) if x['topic'] == t['id']])
            for t in D['topics']}
by_year = {str(y): agg([i for i, x in enumerate(recs) if x['year'] == y])
           for y in sorted({x['year'] for x in recs if x['year']})}
venues = collections.Counter(x['venue'] for x in recs)
by_venue = {v: agg([i for i, x in enumerate(recs) if x['venue'] == v]) for v in venues}

year_pol = {y: v['wpol'] for y, v in by_year.items()}

# ---- 写 JSON ----
out = dict(N=N, K=K, lam=LAM, pos_roots=POS, neg_roots=NEG,
           hit=hit, docs=recs, by_topic=by_topic, by_year=by_year,
           by_venue={k: dict(v) for k, v in by_venue.items()},
           year_pol=year_pol)
json.dump(out, io.open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- 回填 topic_results.json（与 off_results.json 结构对齐）----
for i, d in enumerate(D['docs']):
    d['pol'] = round(recs[i]['pol'], 3)
    d['pos'] = recs[i]['pos']
    d['neg'] = recs[i]['neg']
D['year_pol'] = year_pol
D['polarity_lambda'] = LAM
D['polarity_hit'] = hit
D['pos_roots'] = POS
D['neg_roots'] = NEG
json.dump(D, io.open(RES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- 写 Excel ----
INK = '1F2421'
HDR_FILL = PatternFill('solid', fgColor='2E4A3D')
HDR_FONT = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
BDY = Font(name='微软雅黑', size=9.5, color=INK)
THIN = Side(style='thin', color='D8DED9')
BOX = Border(bottom=THIN)


def sheet(wb, name, title, hdr, rows_, widths, note=None, wrap_cols=(5,), row_h=None):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    # 打印版式：横向、按宽度缩到一页、每页重复表头、右下页码
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = '3:3'
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    ws.oddFooter.right.text = '第 &P 页 / 共 &N 页'
    ws.oddFooter.right.size = 8
    ws.oddFooter.right.color = '808080'
    ws['A1'] = title
    ws['A1'].font = Font(name='微软雅黑', size=13, bold=True, color=INK)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(hdr))
    ws.row_dimensions[1].height = 26
    hr = 3
    for j, h in enumerate(hdr, 1):
        c = ws.cell(hr, j, h)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[hr].height = 30
    for i, rw in enumerate(rows_, hr + 1):
        for j, v in enumerate(rw, 1):
            c = ws.cell(i, j, v)
            c.font = BDY
            c.border = BOX
            c.alignment = Alignment(horizontal='center' if j not in wrap_cols else 'left',
                                    vertical='center',
                                    wrap_text=(j in wrap_cols))
        if i % 2 == 0:
            for j in range(1, len(hdr) + 1):
                ws.cell(i, j).fill = PatternFill('solid', fgColor='F6F8F7')
        # 行高随标题长度自适应（Word/Excel 自动行高在合并与换行混排时会失效）
        if row_h:
            ws.row_dimensions[i].height = row_h
        elif 5 in wrap_cols and len(rw) > 4:
            tl = len(str(rw[4]))
            ws.row_dimensions[i].height = max(19, 12.8 * (1 + tl // 44))
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
    if note:
        r0 = hr + len(rows_) + 2
        ws.cell(r0, 1, note).font = Font(name='微软雅黑', size=8.5, color='6E746F')
        ws.merge_cells(start_row=r0, start_column=1, end_row=r0, end_column=min(6, len(hdr)))
        ws.cell(r0, 1).alignment = Alignment(wrap_text=True, vertical='top')
        ws.row_dimensions[r0].height = 42
    ws.freeze_panes = ws.cell(hr + 1, 1)
    return ws


xb = openpyxl.Workbook()
xb.remove(xb.active)

r1 = [[x['no'], x['year'] or '', x['venue'], 'T%d' % x['topic'], x['title'],
       x['pos'], x['neg'], round(x['pol'], 3),
       '偏正' if x['pol'] > 0.05 else ('偏负' if x['pol'] < -0.05 else '中性'),
       '、'.join(x['pos_hits'][:6]), '、'.join(x['neg_hits'][:6])] for x in recs]
r1.sort(key=lambda r: (-(r[7] if isinstance(r[7], (int, float)) else 0)))
sheet(xb, '逐篇极性', '专家话语 66 篇 · 情感极性逐篇标注（按极性得分降序）',
      ['序号', '年份', '期刊', '主导主题', '标题', '正面词', '负面词', '极性得分', '倾向', '命中正面词根', '命中负面词根'],
      r1, [6, 8, 24, 9, 52, 8, 8, 9, 8, 27, 27], wrap_cols=(3, 5, 10, 11),
      note='极性得分 s =（正面词数 − 负面词数）/（正面词数 + 负面词数 + %d），分母的 2 为平滑项；'
           's > 0.05 计为偏正、s < −0.05 计为偏负，其余为中性。词根取自人工构建的西班牙语评价词干表（正 56 / 负 57），'
           '按词干前缀匹配，故同一词根的屈折变体都计入。' % int(LAM))

r2 = []
for t in D['topics']:
    a = by_topic[str(t['id'])]
    r2.append(['T%d' % t['id'], a['n'], round(a['mean'], 3), a['pos'], a['neg'], a['zero'],
               ', '.join(w for w, _ in t['words'][:6]) + ' …'])
r2.sort(key=lambda r: -r[2])
sheet(xb, '按主题汇总', '各主题的极性均值（篇级得分，未加权）',
      ['主题', '篇数', '均值极性', '偏正篇数', '偏负篇数', '中性篇数', '前 6 位主题词'],
      r2, [8, 7, 10, 10, 10, 10, 70], wrap_cols=(7,), row_h=26,
      note='均值为该主题所辖文献（θ argmax 归属）的篇级极性算术平均，与图 6 的“主题概率加权”口径不同：'
           '图 6 用 Σ(θ×s)/Σθ 逐年计算，此处只做主题内的简单汇总。')

r3 = []
for v, c in venues.most_common():
    a = by_venue[v]
    r3.append([v, c, round(a['mean'], 3), a['pos'], a['neg'], a['zero']])
sheet(xb, '按期刊汇总', '各期刊的极性均值（按篇数降序）',
      ['期刊', '篇数', '均值极性', '偏正篇数', '偏负篇数', '中性篇数'],
      r3, [44, 7, 10, 10, 10, 10],
      note='期刊名沿用数据表原始著录。篇数 1–2 的期刊均值波动大，仅作参考，不宜单独推断期刊倾向。')

r4 = []
for y, a in by_year.items():
    r4.append([int(y), a['n'], round(a['mean'], 3), a['pos'], a['neg'], a['zero']])
sheet(xb, '按年份汇总', '各年份的极性均值（仅列有文献的年份）',
      ['年份', '篇数', '均值极性', '偏正篇数', '偏负篇数', '中性篇数'],
      r4, [8, 7, 10, 10, 10, 10],
      note='本语料多数年份仅 1–6 篇，年度均值对单篇文本高度敏感；解读时应看相邻年份的联动，'
           '而非单点涨落。逐主题的年度加权序列见图表集图 6。')

r5 = [['样本', '专家话语 %d 篇（1999–2026）' % N],
      ['情感计算', '词典法：s =（P − N）/（P + N + %d）' % int(LAM)],
      ['正面词根', '共 %d 个：%s …' % (len(POS), '、'.join(POS[:12]))],
      ['负面词根', '共 %d 个：%s …' % (len(NEG), '、'.join(NEG[:12]))],
      ['匹配方式', '先小写并去除西语重音（á→a、ñ→n 等），再按词干做子串计数，因此 reconocer / reconocimiento 合并计入同一词根'],
      ['文本范围', '标题 + 原文（数据表 Sheet2 第 4 列 + 第 9 列），与官方话语口径完全一致'],
      ['有效命中', '%d / %d 篇（%.0f%%）含至少一个评价词；未命中的篇目极性记为 0，不计入均值分母' % (hit, N, 100 * hit / N)],
      ['与官方版可比性', '两套语料使用同一 POS/NEG 词根表、同一公式、同一文本构造，得分可直接比较；但样本量（66 vs 71）与主题数（9 vs 12）不同，主题级均值不可直接对齐'],
      ['同源文件', 'work/expert_polarity.json（逐篇 + 汇总）、work/topic_results.json（已回填 pol/pos/neg 与 year_pol）']]
sheet(xb, '口径说明', '情感极性标注口径', ['项目', '说明'], r5, [16, 104])

xb.save(OUT_XLSX)
print('saved', OUT_XLSX)
print('mean by topic:', [(k, round(v['mean'], 3)) for k, v in sorted(by_topic.items(), key=lambda x: int(x[0]))])
print('mean by year:', [(k, round(v['mean'], 3)) for k, v in by_year.items()])
print('overall mean %.3f' % np.mean([x['pol'] for x in recs]))
