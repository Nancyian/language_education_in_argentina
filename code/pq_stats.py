# -*- coding: utf-8 -*-
"""重建 M/N 统计区（来源 + 相关性类别 + 时期分布）并按新数据重画条形图，重写 K 列说明。"""
import os, sys
from collections import Counter
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import BarChart, Reference

sys.stdout.reconfigure(encoding='utf-8')
XLSX = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索.xlsx'
OUT = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/multi_db_language_corpus_检索_含ProQuest.xlsx'
BINS = ['1980年以前', '1980-1984', '1985-1989', '1990-1994', '1995-1999',
        '2000-2004', '2005-2009', '2010-2014', '2015-2019', '2020-2024', '2025-2029']
LABELS = ['A 政策/规划/意识形态', 'B 教育政策与实践', 'A+B 政策与教育', 'C 社会语言学/多语接触']


def src_of(url):
    if not url:
        return '其他'
    u = str(url)
    if 'conicet' in u:
        return 'CONICET'
    if 'eric.ed.gov' in u:
        return 'ERIC'
    if 'proquest' in u:
        return 'ProQuest'
    if 'doi.org' in u or 'crossref' in u:
        return 'Crossref'
    if 'europepmc' in u:
        return 'EuropePMC'
    return '其他'


def main():
    wb = openpyxl.load_workbook(OUT)
    ws = wb['Sheet2']
    last = ws.max_row
    print('rows', last)

    srcs, cats, bins = Counter(), Counter(), Counter()
    for r in range(2, last + 1):
        srcs[src_of(ws.cell(row=r, column=2).value)] += 1
        cats[(ws.cell(row=r, column=10).value or '').strip()] += 1
        bins[(ws.cell(row=r, column=8).value or '').strip()] += 1

    total = last - 1
    print('src', srcs)
    print('cat', cats)

    # 清空 M/N 区
    for r in range(1, 40):
        for c in (13, 14, 15):
            try:
                ws._cells.pop((r, c), None)
            except Exception:
                pass
    ws._charts = []

    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF', size=11)
    sub_font = Font(bold=True, size=11)

    def block(start, title, pairs, total=None):
        r = start
        ws.cell(row=r, column=13, value=title).font = hdr_font
        ws.cell(row=r, column=13).fill = hdr_fill
        ws.cell(row=r, column=14, value='条数').font = hdr_font
        ws.cell(row=r, column=14).fill = hdr_fill
        ws.cell(row=r, column=15, value='占比').font = hdr_font
        ws.cell(row=r, column=15).fill = hdr_fill
        r += 1
        for k, v in pairs:
            ws.cell(row=r, column=13, value=k)
            ws.cell(row=r, column=14, value=v)
            ws.cell(row=r, column=15, value=round(v / total * 100, 1) if total else 0)
            r += 1
        if total:
            ws.cell(row=r, column=13, value='合计').font = sub_font
            ws.cell(row=r, column=14, value=total).font = sub_font
            ws.cell(row=r, column=15, value=100.0).font = sub_font
            r += 1
        return r

    order = [s for s in ['CONICET', 'ProQuest', 'ERIC', 'Crossref', 'EuropePMC', '其他']
             if srcs.get(s)]
    end1 = block(2, '来源', [(s, srcs[s]) for s in order], total)

    cat_pairs = [(l, cats.get(l, 0)) for l in LABELS]
    end2 = block(end1 + 1, '相关性类别', cat_pairs, total)

    bin_pairs = [(b, bins.get(b, 0)) for b in BINS if bins.get(b)]
    end3 = block(end2 + 1, '时期分布', bin_pairs, total)

    # 图表
    ch1 = BarChart()
    ch1.type = 'col'
    ch1.title = '来源分布'
    ch1.y_axis.title = '条数'
    data = Reference(ws, min_col=14, min_row=2, max_row=2 + len(order))
    cats_ref = Reference(ws, min_col=13, min_row=3, max_row=2 + len(order))
    ch1.add_data(data, titles_from_data=True)
    ch1.set_categories(cats_ref)
    ch1.height, ch1.width = 7.5, 10
    ws.add_chart(ch1, 'M%d' % (end1 + 1))

    ch2 = BarChart()
    ch2.type = 'col'
    ch2.title = '相关性类别分布'
    ch2.y_axis.title = '条数'
    data2 = Reference(ws, min_col=14, min_row=end1 + 1, max_row=end1 + 1 + len(LABELS))
    cats2 = Reference(ws, min_col=13, min_row=end1 + 2, max_row=end1 + 1 + len(LABELS))
    ch2.add_data(data2, titles_from_data=True)
    ch2.set_categories(cats2)
    ch2.height, ch2.width = 7.5, 10
    ws.add_chart(ch2, 'M%d' % (end2 + 1))

    # K 列说明
    note = (
        '【检索与筛选说明】\n\n'
        '一、数据规模\n'
        '本表共 %d 条，均为「阿根廷主题 × 语言政策/语言教育/社会语言学」强相关的学术文献，'
        '与 Dialnet 主表（317 条）已逐条去重。\n\n'
        '二、来源构成\n'
        '· ProQuest（%d 条）：2026-10-20 通过复旦大学 EZproxy 机构账号，在 ProQuest 高级检索中执行两组检索式——'
        '第 1 行 NOFT（全文+摘要）为 20 组语言政策类关键词，第 2 行 TITLE 为阿根廷及南锥体地名/族群锚定词，'
        '命中 373 条，逐页（8 页）抓取结果列表后按语言学科过滤、与既有表去重，保留 %d 条。\n'
        '· CONICET 仓储（%d 条）：机构知识库 ri.conicet.gov.ar，按引用串解析标题/作者/期刊/年份。\n'
        '· ERIC（%d 条）：美国教育文献数据库 API，覆盖语言教育与双语教育。\n'
        '· Crossref（%d 条）：DOI 元数据，间接覆盖 WoS/Scopus 收录的期刊论文。\n'
        '· Europe PMC（%d 条）：语言学收录极少。\n\n'
        '三、筛选口径\n'
        '1) 学科过滤：标题/摘要须命中语言学科实体词（lengua/language/bilingüe/indígena/'
        'política lingüística 等），并剔除医学、农学、工程、财会等非语言学科。\n'
        '2) 地域锚定：须出现 Argentina / Buenos Aires / Patagonia / Rioplatense / Mercosur / '
        'Mapuche / Guaraní / Quechua / Qom / Wichí 或南锥体国家地名。这是「阿根廷主题」，'
        '不限作者国籍。\n'
        '3) 相关性分层：A=政策/规划/意识形态；B=教育政策与实践；A+B=政策与教育交叉；'
        'C=社会语言学/多语接触。\n\n'
        '四、未纳入的数据库及原因\n'
        '· Web of Science / Scopus：需订阅机构会话，自动化环境无法稳定保持登录态；'
        '其收录的期刊论文已通过 Crossref DOI 元数据部分覆盖。\n'
        '· PsycINFO：需订阅，与 ERIC 高度重叠。\n'
        '· OpenAlex / Semantic Scholar：API 配额耗尽（429）。\n\n'
        '五、字段说明\n'
        '· 发表时间：期刊论文取出版年；学位论文取授予年。\n'
        '· 时期分布：按发表年每 5 年分箱，仅作文献计量参考，非论文研究的历史时段。\n'
        '· 原文：ProQuest 条目为结果页摘要片段（snippet），完整摘要需回跳原文链接。'
    ) % (total, srcs.get('ProQuest', 0), srcs.get('ProQuest', 0), srcs.get('CONICET', 0),
         srcs.get('ERIC', 0), srcs.get('Crossref', 0), srcs.get('EuropePMC', 0))

    c = ws.cell(row=1, column=11)
    c.value = '检索与筛选说明'
    c.font = Font(bold=True, color='FFFFFF', size=12)
    c.fill = PatternFill('solid', fgColor='C00000')
    c.alignment = Alignment(horizontal='center', vertical='center')

    n = ws.cell(row=2, column=11)
    n.value = note
    n.alignment = Alignment(wrap_text=True, vertical='top')
    n.font = Font(size=10)
    ws.column_dimensions['K'].width = 78
    ws.row_dimensions[2].height = 620

    wb.save(OUT)
    print('saved ->', OUT, 'total', total)
    print('blocks end:', end1, end2, end3)


if __name__ == '__main__':
    main()
