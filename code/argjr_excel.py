# -*- coding: utf-8 -*-
"""把 92 条阿根廷期刊语料写成新 Excel（与 Sheet2 同格式）"""
import io, json, os, sys
from collections import Counter
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import BarChart, Reference

sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
OUT = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/六库检索_阿根廷期刊语料_扩充版v3.xlsx'
BINS = ['1980年以前', '1980-1984', '1985-1989', '1990-1994', '1995-1999',
        '2000-2004', '2005-2009', '2010-2014', '2015-2019', '2020-2024', '2025-2029']
LABEL = {'A': 'A 政策/规划/意识形态', 'B': 'B 教育政策与实践',
         'AB': 'A+B 政策与教育', 'C': 'C 社会语言学/多语接触'}
LABELS = list(LABEL.values())


def bin5(y):
    if not y:
        return ''
    if y < 1980:
        return '1980年以前'
    b = (y - 1980) // 5 * 5 + 1980
    return '%d-%d' % (b, b + 4)


def main():
    rows = json.load(io.open(os.path.join(WORK, 'final_argjr.json'), encoding='utf-8'))
    print('rows', len(rows))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet2'

    hdr = ['序号', '来源', '关键词', '文章标题', '期刊名称', '作者',
           '发表时间', '时期分布', '原文', '相关性类别']
    ws.append(hdr)
    for c in range(1, 11):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color='FFFFFF', size=11)
        cell.fill = PatternFill('solid', fgColor='1F4E79')
        cell.alignment = Alignment(horizontal='center', vertical='center')

    for i, c in enumerate(rows, 1):
        r = i + 1
        vals = [i, c.get('url') or c.get('db', ''), c.get('kw', ''), c['title'],
                c.get('venue', ''), c.get('authors', ''), c.get('year'),
                bin5(c.get('year')), c.get('abs', ''), LABEL[c['cat']]]
        for j, v in enumerate(vals, 1):
            ws.cell(row=r, column=j, value=v)
    last = len(rows) + 1

    thin = Side(style='thin', color='D9D9D9')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    align = Alignment(vertical='top', wrap_text=True)
    for r in range(2, last + 1):
        for c in range(1, 11):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            cell.alignment = align
        ws.row_dimensions[r].height = 46

    widths = {'A': 6, 'B': 34, 'C': 24, 'D': 58, 'E': 32, 'F': 26,
              'G': 12, 'H': 14, 'I': 80, 'J': 24, 'K': 78}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    ws.auto_filter.ref = 'A1:J%d' % last
    ws.freeze_panes = 'A2'

    dv1 = DataValidation(type='list', formula1='"'+','.join(BINS)+'"', allow_blank=True)
    dv1.add('H2:H%d' % last)
    ws.add_data_validation(dv1)
    dv2 = DataValidation(type='list', formula1='"'+','.join(LABELS)+'"', allow_blank=True)
    dv2.add('J2:J%d' % last)
    ws.add_data_validation(dv2)

    # 隐藏表 时间选项
    ws2 = wb.create_sheet('时间选项')
    ws2['A1'] = '时期选项（5 年分箱）'
    ws2['A1'].font = Font(bold=True)
    for i, b in enumerate(BINS, 2):
        ws2.cell(row=i, column=1, value=b)
    ws2.sheet_state = 'hidden'

    # 统计区
    srcs = Counter('CONICET' if 'conicet' in str(r.get('url')) else
                   'Crossref' if 'doi.org' in str(r.get('url')) else
                   'ProQuest' if 'proquest' in str(r.get('url')) else
                   'ERIC' if 'eric' in str(r.get('url')) else '其他' for r in rows)
    cats = Counter(LABEL[r['cat']] for r in rows)
    binsc = Counter(bin5(r.get('year')) for r in rows)
    total = len(rows)

    hdr_fill = PatternFill('solid', fgColor='1F4E79')
    hdr_font = Font(bold=True, color='FFFFFF', size=11)
    sub_font = Font(bold=True, size=11)

    def block(start, title, pairs):
        r = start
        for col, v in ((13, title), (14, '条数'), (15, '占比')):
            cell = ws.cell(row=r, column=col, value=v)
            cell.font = hdr_font
            cell.fill = hdr_fill
        r += 1
        for k, v in pairs:
            ws.cell(row=r, column=13, value=k)
            ws.cell(row=r, column=14, value=v)
            ws.cell(row=r, column=15, value=round(v / total * 100, 1) if total else 0)
            r += 1
        ws.cell(row=r, column=13, value='合计').font = sub_font
        ws.cell(row=r, column=14, value=total).font = sub_font
        ws.cell(row=r, column=15, value=100.0).font = sub_font
        return r

    order = [s for s in ['CONICET', 'Crossref', 'ProQuest', 'ERIC', 'EuropePMC', '其他']
             if srcs.get(s)]
    end1 = block(2, '来源', [(s, srcs[s]) for s in order])
    end2 = block(end1 + 2, '相关性类别', [(l, cats.get(l, 0)) for l in LABELS])
    end3 = block(end2 + 2, '时期分布', [(b, binsc.get(b, 0)) for b in BINS if binsc.get(b)])

    def chart(anchor, title, n, top):
        ch = BarChart()
        ch.type = 'col'
        ch.title = title
        ch.y_axis.title = '条数'
        data = Reference(ws, min_col=14, min_row=top, max_row=top + n)
        cats_ref = Reference(ws, min_col=13, min_row=top + 1, max_row=top + n)
        ch.add_data(data, titles_from_data=True)
        ch.set_categories(cats_ref)
        ch.height, ch.width = 7.5, 10
        ws.add_chart(ch, anchor)

    chart('M%d' % (end1 + 2), '来源分布', len(order), 2)
    chart('M%d' % (end2 + 2), '相关性类别分布', len(LABELS), end1 + 2)

    # K 列说明
    note = (
        '【检索与筛选说明】（六库 × 阿根廷本地期刊版）\n\n'
        '一、数据规模\n'
        '本表共 %d 条：六个数据库检索结果中，发表于阿根廷本地期刊的强相关文献，'
        '全部与 Dialnet 主表（317 条）去重。\n\n'
        '二、检索范围与通道\n'
        '· CONICET 仓储（%d 条）：机构知识库快照全量解析（5870 handle → 656 篇可解析）。\n'
        '· Crossref（%d 条）：两条通道——① 阿根廷主题关键词检索池 555 条；'
        '② 阿根廷期刊定向检索：按 ISSN 全量拉取 21 种阿根廷期刊全部论文约 2790 篇'
        '（第一批：Signo y Seña / Anclajes / Cuadernos del CILHA / RACC 等 8 种 1113 篇；'
        '第二批：Traslaciones / Praxis Educativa / Cuadernos del Sur Letras / '
        'Contextos de Educación 等 13 种 1677 篇）。\n'
        '· ERIC（392 条候选）：全部发表在国际期刊，无阿根廷期刊命中。\n'
        '· Europe PMC（554 条候选）：无阿根廷期刊命中。\n'
        '· ProQuest（373 条候选，复旦大学 EZproxy）：仅 1 条发表在阿根廷期刊。\n'
        '· Web of Science / Scopus / PsycINFO：需订阅机构会话，自动化环境无法稳定登录，'
        '未直接检索；其收录的阿根廷期刊论文已通过 Crossref DOI 元数据部分覆盖。\n\n'
        '三、筛选口径（三层）\n'
        '1) 期刊限定：期刊名须命中阿根廷期刊白名单并避开学科黑名单'
        '（剔除 Estudios Rurales、Prudentia Iuris、各历史类期刊、Epistemus（音乐）等'
        '非语言学科刊物）。\n'
        '2) 学科限定：标题或摘要须命中语言学科实体词；命中仅为泛词（escritura/translation 等）'
        '的条目逐条人工甄别，剔除纯文学评论、书评、心理量表、艺术类。\n'
        '3) 去重：与 Dialnet 317 条及本表内部逐一去重。\n\n'
        '四、主要期刊分布\n'
        'Traslaciones（UNCuyo，语言教育/读写研究）86、Signo y Seña（UBA）45、'
        'Praxis Educativa（UNLPam）31、Anclajes（UNLP）20、Cuadernos del Sur Letras（UNS）15、'
        'RACC 10、Contextos de Educación（UNRC）8、Boletín de la Academia Argentina de Letras 3 等。\n\n'
        '五、关键词（C 列）口径\n'
        'C 列统一使用西班牙语主题词，与 Dialnet 主表同一套词表：español / inglés / francés / '
        'portugués / chino / bilingüe / multilingüismo / lingüística / idioma / '
        'política lingüística / derechos lingüísticos / lenguas indígenas / lenguas de migración / '
        'lengua extranjera / segunda lengua / L2 / enseñanza de la lengua / uso de la lengua，'
        '并补充 lectura y escritura、interculturalidad、adquisición de lenguas、discurso、'
        'léxico、gramática、traducción、hablantes、docentes、estudiantes 等教育语言类主题词。'
        '取值方式：先用标题匹配，标题无命中时再用摘要匹配具体主题词（避免泛词淹没），'
        '仍无命中则记 lingüística。\n\n'
        '六、字段说明\n'
        '· 发表时间：期刊论文取出版年。\n'
        '· 时期分布：按发表年每 5 年分箱，仅作文献计量参考，非论文研究的历史时段。\n'
        '· 原文：Crossref 定向条目多数无摘要，需经 DOI 回跳原文。\n'
        '· 相关性类别：A=政策/规划/意识形态；B=教育政策与实践；A+B=政策与教育；'
        'C=社会语言学/多语接触。'
        ) % (total, srcs.get('CONICET', 0), srcs.get('Crossref', 0))

    c = ws.cell(row=1, column=11, value='检索与筛选说明')
    c.font = Font(bold=True, color='FFFFFF', size=12)
    c.fill = PatternFill('solid', fgColor='C00000')
    c.alignment = Alignment(horizontal='center', vertical='center')
    n = ws.cell(row=2, column=11, value=note)
    n.alignment = Alignment(wrap_text=True, vertical='top')
    n.font = Font(size=10)
    ws.row_dimensions[2].height = 620

    wb.save(OUT)
    print('saved ->', OUT)


if __name__ == '__main__':
    main()
