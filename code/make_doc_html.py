# -*- coding: utf-8 -*-
"""Stage 2 排版：stage1/final_draft.md → academic-paper 模板完整 HTML。

遵循 doc-typeset / academic-paper 规范：
- 封面独立 <section role="cover">（无页眉页脚；标题用 <p> 不用 h1，避免被目录收录）
- 目录独立 <section role="cover">，nav.doc-toc 锚点对应正文标题 id
- 正文 <section role="body" data-page-restart="1">，页脚居中页码
- 三线表（thead/tbody/th）、图用 figure+figcaption、样式全部走 CSS 变量
"""
import io, os, re, json, html as H

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = '68ece3e9-8b3f-4acb-a410-910598db1cf5'
OUTD = os.path.join(BASE, 'output', RID)
MD = os.path.join(OUTD, 'stage1', 'final_draft.md')
OUT = os.path.join(OUTD, 'stage2', 'formatted-专家话语_LDA主题建模_图表集.html')

TOK = json.load(open(os.path.join(
    r'C:\Users\Administrator\.workbuddy\plugins\cache\workbuddy-builtin\workbuddy-docx'
    r'\5.9.3-wb.42398134.gd4692421.h480e8d1fee0f\skills\design-token\tokens\compiled'
    r'\academic-paper.json'), encoding='utf-8'))
json.dump(TOK, open(os.path.join(OUTD, 'stage2', 'design_tokens.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
CV = TOK['css_variables']

lines = io.open(MD, encoding='utf-8').read().split('\n')


def inline(s):
    s = H.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)
    return s


blocks = []
i = 0
while i < len(lines):
    ln = lines[i]
    if not ln.strip():
        i += 1
        continue
    if ln.startswith('# ') and not blocks:
        blocks.append(('title', ln[2:].strip())); i += 1; continue
    if ln.startswith('## '):
        blocks.append(('h1', ln[3:].strip())); i += 1; continue
    if ln.startswith('### '):
        blocks.append(('h2', ln[4:].strip())); i += 1; continue
    if ln.startswith('> '):
        buf = [ln[2:].strip()]; i += 1
        while i < len(lines) and lines[i].startswith('> '):
            buf.append(lines[i][2:].strip()); i += 1
        blocks.append(('quote', ' '.join(buf))); continue
    if ln.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            rows.append(lines[i]); i += 1
        blocks.append(('table', rows)); continue
    if ln.startswith('- '):
        items = []
        while i < len(lines) and lines[i].startswith('- '):
            items.append(lines[i][2:].strip()); i += 1
        blocks.append(('ul', items)); continue
    if re.match(r'^\d+\. ', ln):
        items = []
        while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
            items.append(re.sub(r'^\d+\. ', '', lines[i]).strip()); i += 1
        blocks.append(('ol', items)); continue
    m = re.match(r'^!\[(.+?)\]\((.+?)\)$', ln.strip())
    if m:
        blocks.append(('img', (m.group(1), m.group(2)))); i += 1; continue
    if ln.startswith('*') and ln.endswith('*') and not ln.startswith('**'):
        blocks.append(('sub', ln.strip('*').strip())); i += 1; continue
    buf = [ln.strip()]; i += 1
    while i < len(lines) and lines[i].strip() and not re.match(
            r'^(#|>|\||- |\d+\. |!\[|\*[^*]+\*$)', lines[i]):
        buf.append(lines[i].strip()); i += 1
    blocks.append(('p', ' '.join(buf)))

title = blocks[0][1]
subtitle = blocks[1][1]
note = next(b[1] for b in blocks if b[0] == 'quote')

CN_NUM = '一二三四五六七八九十'
out, toc = [], []
idn = 0
h2cnt = 0
in_abs = False
in_ref = False
pending_caption = None


# 各表列宽（百分比，合计 100）——转换引擎会读取 colgroup 宽度，避免等宽把长列挤成竖条
WIDTHS = {
    ('编号', '名称', '内容'): [10, 32, 58],
    ('项目', '说明'): [14, 86],
    ('年份区间', '篇数', '占语料', '该期平均 θ 超过 10% 的主题数', '该期平均 θ 最高的主题'): [16, 8, 10, 26, 40],
    ('编号', '主题词（β，前 12 位）', '主导篇数', '份额'): [10, 66, 12, 12],
    ('年份', '篇数', '年份', '篇数'): [30, 20, 30, 20],
    ('主题数 K', 'u_mass'): [50, 50],
    ('主题 A', '主题 B', '共享词数', '共享词（前三个）'): [15, 15, 16, 54],
    ('主题', '≤2013', '2014–18', '2019–22', '2023–26', '峰谷差'): [29, 13, 13, 13, 13, 19],
    ('主题', '篇数', '均值极性', '正 / 负 / 中性'): [38, 12, 16, 34],
    ('期刊面板', '篇数', '占语料', '主导主题（均值 θ 最大）'): [27, 9, 11, 53],
    ('期刊面板', '篇数', '均值极性'): [40, 14, 46],
    ('脚本', '作用'): [38, 62],
    ('文件', '说明'): [26, 74],
    ('符号 / 术语', '含义', '本册取值'): [20, 52, 28],
}


def table_html(payload, caption=None):
    rows = [r for r in payload if not re.match(r'^\|[\s:\-|]+\|$', r)]
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], cells[1:]
    t = []
    if caption:
        t.append('<p class="table-caption">%s</p>' % inline(caption))
    t.append('<table class="three-line-table">')
    widths = WIDTHS.get(tuple(head))
    if widths and len(widths) == len(head):
        t.append('<colgroup>' + ''.join('<col style="width:%d%%">' % w for w in widths) + '</colgroup>')
    t.append('<thead><tr>')
    t += ['<th>%s</th>' % inline(c) for c in head]
    t.append('</tr></thead><tbody>')
    for r in body:
        t.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>')
    t.append('</tbody></table>')
    return ''.join(t)


for k, (kind, payload) in enumerate(blocks):
    if k in (0, 1) or kind == 'quote':
        continue
    if kind == 'h1':
        in_abs = (payload == '摘要')
        in_ref = (payload == '参考文献')
        if in_abs:
            out.append('<div class="abstract" aria-label="摘要">')
            out.append('<p class="abstract-heading">摘要</p>')
            continue
        if in_ref:
            out.append('<div class="references" aria-label="参考文献">')
        idn += 1
        sid = 'section-%d' % idn
        h2cnt = 0
        out.append('<h1 id="%s">%s</h1>' % (sid, inline(payload)))
        toc.append((1, payload, sid))
    elif kind == 'h2':
        h2cnt += 1
        idn += 1
        sid = 'section-%d' % idn
        if payload.startswith('图 ') or re.match(r'^\d+\.\d+', payload):
            name = payload                     # 已有编号（图 N／1.1）不再加（一）
        else:
            name = '（%s）%s' % (CN_NUM[h2cnt - 1], payload)
        out.append('<h2 id="%s">%s</h2>' % (sid, inline(name)))
        toc.append((2, name, sid))
    elif kind == 'p':
        if in_abs and payload.startswith('关键词'):
            out.append('<p class="keywords">%s</p>' % inline(payload))
        elif re.match(r'^\*\*(表 \d+　|数据表 · )', payload):
            pending_caption = payload.replace('**', '')
        else:
            cls = ' class="lead"' if payload.startswith(('**图注**', '**读图要点**', '**差异')) else ''
            out.append('<p%s>%s</p>' % (cls, inline(payload)))
    elif kind == 'sub':
        out.append('<p class="fig-sub">%s</p>' % inline(payload))
    elif kind == 'ul':
        out.append('<ul class="points">' + ''.join('<li>%s</li>' % inline(x) for x in payload) + '</ul>')
    elif kind == 'ol':
        tag = 'ol class="reference-list"' if in_ref else 'ol class="points"'
        out.append('<%s>' % tag + ''.join('<li>%s</li>' % inline(x) for x in payload) + '</ol>')
    elif kind == 'img':
        alt, src = payload
        # 转换引擎只认绝对文件路径（相对路径会退化成「[图片: xxx]」文本）
        abssrc = os.path.join(OUTD, 'stage2', src.replace('/', os.sep)).replace(os.sep, '/')
        out.append('<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
                   % (abssrc, H.escape(alt), inline(alt)))
    elif kind == 'table':
        out.append(table_html(payload, pending_caption))
        pending_caption = None

if in_abs:
    out.append('</div>')
if in_ref:
    out.append('</div>')

html_body = '\n'.join(out)

toc_items = []
for lvl, text, sid in toc:
    cls = ' class="toc-1"' if lvl == 1 else ' class="toc-2"'
    toc_items.append('<li%s><a href="#%s">%s</a></li>' % (cls, sid, H.escape(text)))
toc_html = '\n      '.join(['<ol class="toc-list">'] + toc_items + ['</ol>'])

CSS = """
  @page { @bottom-center { content: counter(page); } }
  @page cover { @bottom-center { content: none; } }
  @page front { @bottom-center { content: none; } }
  @page main { @bottom-center { content: counter(page); } }
  section[role="cover"] { page: cover; }
  section[role="toc"] { page: front; }
  section[role="body"] { page: main; }

  :root {
    --fs-h1: @@--typography-fontSize-h1@@;
    --fs-h2: @@--typography-fontSize-h2@@;
    --fs-body: @@--typography-fontSize-body@@;
    --fs-small: @@--typography-fontSize-caption@@;
    --fs-note: @@--typography-fontSize-footnote@@;
    --fs-title: @@--typography-fontSize-title@@;
    --fs-cover-sub: @@--typography-fontSize-h2@@;
    --fs-toc-title: @@--typography-fontSize-h2@@;
    --ff-heading: @@--typography-fontFamily-heading@@;
    --ff-body: @@--typography-fontFamily-body@@;
    --lh-body: @@--typography-lineHeight-body@@;
    --fw-bold: @@--typography-fontWeight-heading@@;
    --color-text: @@--color-text@@;
    --color-heading: @@--color-heading@@;
    --color-muted: @@--color-muted@@;
    --color-rule: @@--color-tableBorder@@;
    --color-bg: @@--color-background@@;
    --color-shade: @@--color-tableHeaderBg@@;
    --color-accent: @@--color-link@@;
    --spacing-paragraph: @@--spacing-paragraph@@;
    --spacing-section: @@--spacing-sectionGap@@;
    --spacing-block: @@--spacing-paragraph@@;
    --spacing-cell: @@--spacing-paragraph@@;
    --spacing-list: @@--spacing-indent@@;
    --margin-page: @@--layout-marginLeft@@;
    --page-content-width: 15.4cm;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--ff-body);
    font-size: var(--fs-body);
    line-height: var(--lh-body);
    color: var(--color-text);
    background: var(--color-bg);
    padding: var(--margin-page);
    max-width: calc(var(--page-content-width) + 2 * var(--margin-page));
    margin-left: auto;
    margin-right: auto;
  }
  h1, h2 { font-family: var(--ff-heading); font-weight: var(--fw-bold); color: var(--color-heading); }
  h1 { font-size: var(--fs-h1); margin-top: var(--spacing-section); margin-bottom: var(--spacing-block); }
  h2 { font-size: var(--fs-h2); margin-top: var(--spacing-block); margin-bottom: var(--spacing-paragraph); }
  p { margin-bottom: var(--spacing-paragraph); text-indent: var(--spacing-list); text-align: justify; }
  strong { font-weight: var(--fw-bold); }
  em { font-style: italic; }

  section[role="cover"] { text-align: center; }
  .cover-eyebrow { text-align: center; font-size: var(--fs-small); color: var(--color-muted);
                   text-indent: 0; margin-top: var(--spacing-section); }
  .cover-title { text-align: center; font-family: var(--ff-heading); font-size: var(--fs-title);
                 font-weight: var(--fw-bold); margin-top: var(--spacing-block);
                 margin-bottom: var(--spacing-paragraph); text-indent: 0; line-height: 1.35; }
  .cover-sub { text-align: center; font-size: var(--fs-cover-sub); color: var(--color-muted);
               text-indent: 0; margin-bottom: var(--spacing-section); }
  .cover-note { text-align: left; font-size: var(--fs-note); color: var(--color-muted);
                text-indent: 0; margin-top: var(--spacing-section); }

  .toc-title { text-align: center; font-family: var(--ff-heading); font-size: var(--fs-toc-title);
               font-weight: var(--fw-bold); text-indent: 0; margin-bottom: var(--spacing-block); }
  .doc-toc { margin-top: var(--spacing-section); }
  .toc-list, .toc-list ol, .toc-list ul { list-style: none; list-style-type: none; padding-left: 0; }
  .toc-list li { margin-bottom: var(--spacing-cell); text-indent: 0; font-size: var(--fs-small); }
  .toc-list li.toc-1 { font-weight: var(--fw-bold); margin-top: var(--spacing-cell); }
  .toc-list li.toc-2 { padding-left: var(--spacing-list); font-weight: normal; }
  .toc-list a { color: var(--color-text); text-decoration: none; }
  .toc-end { text-indent: 0; margin-bottom: 0; }

  .abstract { margin-bottom: var(--spacing-section); padding: var(--spacing-block);
              border-left: 3px solid var(--color-muted); background: var(--color-shade); }
  .abstract-heading { font-family: var(--ff-heading); font-weight: var(--fw-bold);
                      text-indent: 0; margin-bottom: var(--spacing-cell); }
  .keywords { text-indent: 0; font-size: var(--fs-small); }

  .fig-sub { text-align: center; font-size: var(--fs-small); color: var(--color-muted);
             text-indent: 0; margin-bottom: var(--spacing-paragraph); }
  .lead { text-indent: 0; margin-top: var(--spacing-block); margin-bottom: var(--spacing-cell); }
  .note { text-indent: 0; font-size: var(--fs-note); color: var(--color-muted);
          border-left: 3px solid var(--color-muted); padding-left: var(--spacing-block);
          background: var(--color-shade); }
  .table-caption { text-indent: 0; font-family: var(--ff-heading); font-size: var(--fs-small);
                   font-weight: var(--fw-bold); margin-top: var(--spacing-block);
                   margin-bottom: var(--spacing-cell); }

  ul.points, ol.points { margin: 0 0 var(--spacing-block) 0; padding-left: var(--spacing-list); }
  ul.points li, ol.points li { margin-bottom: var(--spacing-cell); text-align: justify; }
  .reference-list { padding-left: var(--spacing-list); }
  .reference-list li { font-size: var(--fs-small); margin-bottom: var(--spacing-cell);
                       text-align: justify; }

  figure { margin: var(--spacing-block) 0; text-align: center; }
  figure img { width: 100%; }
  figcaption { font-size: var(--fs-small); color: var(--color-muted); margin-top: var(--spacing-cell);
               text-align: center; }

  table.three-line-table { border-collapse: collapse; width: 100%;
                           margin-bottom: var(--spacing-block); font-size: var(--fs-small); }
  table.three-line-table thead tr:first-child { border-top: 2px solid var(--color-rule); }
  table.three-line-table thead tr:last-child { border-bottom: 1px solid var(--color-rule); }
  table.three-line-table tbody tr:last-child { border-bottom: 2px solid var(--color-rule); }
  table.three-line-table th, table.three-line-table td {
    border-left: none; border-right: none; border-top: none; border-bottom: none;
    padding: var(--spacing-cell) var(--spacing-block); text-align: left; text-indent: 0; }
  table.three-line-table th { font-weight: var(--fw-bold); background: transparent; }
"""
for _k, _v in CV.items():
    CSS = CSS.replace('@@' + _k + '@@', _v)

doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="docx-page-size" content="A4">
  <title>%s</title>
  <style>%s
  </style>
</head>
<body>
  <section role="cover">
    <p class="cover-eyebrow">专家话语语料 · 图表集</p>
    <p class="cover-title">%s</p>
    <p class="cover-sub">%s</p>
    <p class="cover-note">%s</p>
  </section>

  <section role="toc">
    <nav class="doc-toc" aria-label="文档目录">
      <p class="toc-title">目　录</p>
      %s
    </nav>
    <p class="toc-end"></p>
  </section>

  <section role="body" data-page-restart="1">
%s
  </section>
</body>
</html>
""" % (H.escape(title), CSS, inline(title), inline(subtitle), inline(note), toc_html, html_body)

io.open(OUT, 'w', encoding='utf-8').write(doc)
print('html ->', OUT, len(doc), 'chars')
print('h1 =', sum(1 for x in toc if x[0] == 1), 'h2 =', sum(1 for x in toc if x[0] == 2))
print('tables =', html_body.count('<table'), 'figures =', html_body.count('<figure>'))
