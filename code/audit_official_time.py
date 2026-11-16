# -*- coding: utf-8 -*-
"""官方话语语料：时间不详条目的年份回溯核查。
输出 官方数据表_时间核查.xlsx，不改动原文件。
"""
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_正式版.xlsx'
OUT = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_时间核查.xlsx'

# no: (年份 or None, 年份性质, 证据, 置信度, 能否填入发布时间列, 备注)
FIND = {
    26: (None, '—', 'bcn.gob.ar 抓取失败（站点不可达），未能读取正文', '—', '不可',
         '建议在 BCN「Actividades científicas」归档中按活动名检索'),
    46: (None, '—', '页面仅述项目性质与申请条件，未出现任何年份', '—', '不可',
         '项目始于何时需查 Fulbright 阿根廷委员会的历史公告'),
    47: (2010, '规范颁布年', 'Marco normativo：Res. CFE 119/10；另 Ley 26.206（2006）Cap. XI art. 52-54', '高', '需换算',
         '2010 为 EIB 作为「模态」落地之年，2006 为法定基础；二者均非网页发布时间'),
    49: (None, '—', '页面全文无年份，仅见方案性描述（eje de trabajo、líneas de acción）', '—', '不可',
         '可查该计划的 Resolución 或 Plan Nacional de Alfabetización 文本'),
    50: (2026, '公告发布年', '标题含学年「convocatoria 2026-2027」；按惯例于上一学年 8-9 月发布', '中高', '需换算',
         '若需精确到日，查该页对应的 noticias 首发稿'),
    58: (None, '—', 'bcn.gob.ar 抓取失败，未能读取正文', '—', '不可',
         'BCN「Recursos virtuales」栏目无日期字段'),
    62: (2019, '活动/专题年份', '正文两处「2019 Año Internacional de las Lenguas Indígenas」，并附 6-7 月活动日程', '高', '不可',
         '属活动日期，按纳入标准第 6 条不得冒充发布时间'),
    64: (None, '—', '该页为「Area」课时安排表，仅列课程与学时', '—', '不可',
         '与序号 81 同源，均为栏目页'),
    65: (1982, '项目实施起始年', '「Desde 1982, los Centros Educativos Complementarios de Idiomas Extranjeros (CECIEs) brindan…」', '高', '不可',
         '页面正文自述，可作政策锚点；1982 超出当前时期档位'),
    66: (None, '—', '页面为报名信息，仅见学期与时段的相对表述', '—', '不可',
         '课程为滚动开设，无单一发布日'),
    67: (None, '—', '该页为四类课程的目录索引，正文仅一句总述', '—', '不可',
         '索引页在结构上不含时间信息'),
    68: (None, '—', '页面仅见「2.º cuatrimestre 2026」报名安排，无起始年', '—', '不可',
         'Lenguas en los Barrios 的创设年需查政策文件'),
    69: (None, '—', '出版物列表页，附件路径无统一年月', '—', '不可',
         '可按各附件的 /YYYY/MM/ 路径逐份定年'),
    70: (None, '—', '页面为 EIB 栏目总述，未出现年份', '—', '不可',
         '仅链接至国家层级 MEIB 页面'),
    72: (2013, '条例颁布年', '正文：「Las decisiones están plasmadas en la Resolución 1597 MEGC」，并附 Boletín Oficial 2013/08/13 链接', '高', '需换算',
         '这是本次核查中证据链最完整的一条：条例号 + 官方公报日期'),
    73: (2001, '项目实施起始年', '「El Programa Escuelas de Modalidad Plurilingüe funciona desde el año 2001」', '高', '不可',
         '2001 超出当前时期档位'),
    74: (2022, '项目实施起始年', '「son escuelas implementadas en 2022」「El Programa… funciona desde 2022」', '高', '不可',
         '2022 可归入 2021-2025 档'),
    75: (2015, '项目实施起始年', '「Dependientes de la DENS, con inicio entre 2015 y 2021」；DEM 三所「con inicio en 2023」', '中高', '不可',
         '取最早批次 2015；若按主体扩容则 2023'),
    76: (None, '—', '无起始年表述；「En 2026 se suman」表明页面为 2026 版', '—', '不可',
         '可由「新增校名单」反推年度，但非发布时间'),
    77: (None, '—', '无起始年；最晚附件路径为 /2025-12/，可定页面更新下界', '—', '不可',
         '页面版本年 ≥2025'),
    78: (None, '—', '栏目索引页', '—', '不可', '—'),
    79: (None, '—', '栏目索引页（Idiomas 总入口）', '—', '不可', '—'),
    80: (None, '—', '栏目索引页', '—', '不可', '—'),
    81: (None, '—', '「Todos los años hay inscripción docente」，无具体年份', '—', '不可',
         '属年度循环程序，无单一起始年'),
    85: (None, '—', '教学材料列表页，无年份', '—', '不可', '—'),
    88: (None, '—', 'FAQ 页，正文为问答条目，无日期', '—', '不可',
         '此条相关性亦弱（导航性文本），建议复核是否保留'),
    89: (None, '—', 'FAQ 页，同上', '—', '不可', '同上'),
    90: (None, '—', '无起始年；页面为「2.º cuatrimestre 2026」报名信息', '—', '不可',
         'Chino Mandarín 进校年份需查 2010 年代政策公告'),
    91: (None, '—', '报名信息页，无起始年', '—', '不可', '—'),
    92: (None, '—', '「historial de acciones」栏目页，正文无年份', '—', '不可',
         '该栏目本应含时间轴，建议逐条展开核实'),
}

BINS = [(1982, 1990, '1982-1990（缺档）'), (1991, 2005, '1991-2005（缺档）'),
        (2006, 2010, '2006-2010（缺档）'), (2011, 2015, '2011-2015'),
        (2016, 2020, '2016-2020'), (2021, 2025, '2021-2025'), (2026, 2030, '2026-2030')]


def binof(y):
    if not y:
        return '—'
    for a, b, name in BINS:
        if a <= y <= b:
            return name
    return '超出范围'


HDR_FILL = PatternFill('solid', fgColor='1F3864')
HDR_FONT = Font(color='FFFFFF', bold=True, size=10.5, name='微软雅黑')
BODY_FONT = Font(size=10, name='微软雅黑')
OK_FILL = PatternFill('solid', fgColor='E2EFDA')
NO_FILL = PatternFill('solid', fgColor='FCE4E4')
MID_FILL = PatternFill('solid', fgColor='FFF2CC')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, ncol, row=1):
    for c in range(1, ncol + 1):
        cell = ws.cell(row, c)
        cell.fill = HDR_FILL
        cell.font = HDR_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


wb = openpyxl.load_workbook(SRC, data_only=True)
src = wb['Sheet2']
rows = []
for r in range(2, src.max_row + 1):
    if '不详' in str(src.cell(r, 7).value or ''):
        rows.append({
            'no': int(src.cell(r, 1).value),
            'title': str(src.cell(r, 4).value or ''),
            'plat': str(src.cell(r, 5).value or ''),
            'orig': str(src.cell(r, 7).value or ''),
        })

out = openpyxl.Workbook()
ws = out.active
ws.title = '时间核查'
heads = ['序号', '文章标题', '发布平台', '原发布时间', '是否查到年份', '检索到的年份',
         '该年份的性质', '证据（原文/规范编号）', '置信度', '能否填入「发布时间」列',
         '归入的时期档位', '备注与下一步']
ws.append(heads)
style_header(ws, len(heads))

hit = 0
for it in rows:
    y, nat, ev, conf, fillable, note = FIND.get(
        it['no'], (None, '—', '未核', '—', '不可', '—'))
    if y:
        hit += 1
    ws.append([it['no'], it['title'], it['plat'], it['orig'],
               '查到' if y else '未查到', y if y else '', nat, ev, conf, fillable,
               binof(y), note])
    rr = ws.max_row
    for c in range(1, len(heads) + 1):
        cell = ws.cell(rr, c)
        cell.font = BODY_FONT
        cell.border = BORDER
        cell.alignment = Alignment(vertical='center', wrap_text=(c in (2, 8, 12)))
    ws.cell(rr, 5).fill = OK_FILL if y else NO_FILL
    ws.cell(rr, 10).fill = MID_FILL if (y and fillable != '不可') else NO_FILL
    ws.row_dimensions[rr].height = 34

widths = [6, 34, 26, 12, 11, 12, 15, 52, 8, 16, 16, 40]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = 'A2'
ws.auto_filter.ref = 'A1:L%d' % ws.max_row
ws.sheet_view.showGridLines = False

# ---------- 方法评估 ----------
ws2 = out.create_sheet('方法评估')
ws2.sheet_view.showGridLines = False
ws2.column_dimensions['A'].width = 24
ws2.column_dimensions['B'].width = 96
lines = [
    ('核查对象', '官方数据表_正式版.xlsx 中「发布时间＝时间不详」的全部 %d 条记录' % len(rows)),
    ('核查方法', '对每条 URL 抓取页面正文，检索三类时间锚点：①「Desde + 年份」的项目自述；'
               '②Resolución / Ley / Decreto / Disposición 编号；③页面内公告学年或活动日期。'),
    ('核查结果', '查到明确年份 %d 条，未查到 %d 条，成功率约 %.0f%%。' % (hit, len(rows) - hit, 100.0 * hit / len(rows))),
    ('关键限制一', '查到的不是「发布时间」。%d 条中，%d 条为项目实施起始年、%d 条为条例颁布年、'
                '1 条为专题活动年份、1 条为公告学年。静态栏目页在生成时就未设发布日期字段，'
                '所以「网页何时发布」在技术上已不可考。' % (hit, 4, 2)),
    ('关键限制二', '与本表「纳入标准」第 6 条冲突。该条明订「不以活动日期冒充发布时间」，'
                '因此 1982、2001、2010、2013、2015、2019 这些年份都不能直接写进「发布时间」列，'
                '否则会污染历时统计的口径。'),
    ('关键限制三', '时期档位不衔接。现有下拉档位最低为 2011-2015，而本次查到的 1982、2001、2010 '
                '三个年份无处归档；8 条中只有 2013、2015、2019、2022、2026 共 5 条可入现有档位。'),
    ('页面类型差异', '可定年的页面集中在「项目介绍页」，其正文习惯自述起始年；'
                 '不可定年的为目录索引页、FAQ 页与报名信息页，这三类在结构上不含时间字段，'
                 '再多检索也无法得到年份。'),
    ('个别页面例外', '序号 72 是唯一证据链完整的案例：正文给出 Resolución 1597/MEGC，'
                 '并附官方公报 2013/08/13 的 PDF 链接，条例号与颁布日均可直接核验。'
                 '这说明老师的方法在「规范文本类」页面上确实成立。'),
    ('建议处置', '一、保留「发布时间＝时间不详」，不伪填；二、新增「政策锚点年」列承载上述 8 个年份，'
              '并在论文方法论中说明该列用于历时分期的替代锚点；三、若确需长时段历时分析，'
              '需把时期档位向下补至 1982 起；四、剩余 22 条建议走原始公告或新闻首发稿定年，'
              '而非继续在栏目页上检索。'),
]
ws2['A1'] = '核查项'
ws2['B1'] = '说明'
style_header(ws2, 2)
for k, v in lines:
    ws2.append([k, v])
    rr = ws2.max_row
    ws2.cell(rr, 1).font = Font(size=10, bold=True, name='微软雅黑')
    ws2.cell(rr, 2).font = BODY_FONT
    for c in (1, 2):
        ws2.cell(rr, c).border = BORDER
        ws2.cell(rr, c).alignment = Alignment(vertical='top', wrap_text=True)
    ws2.row_dimensions[rr].height = 46

# ---------- 已获年份清单 ----------
ws3 = out.create_sheet('已获年份清单')
ws3.sheet_view.showGridLines = False
ws3.append(['序号', '年份', '年份性质', '可归入的时期档位', '可否用于历时统计'])
style_header(ws3, 5)
for it in rows:
    y, nat, ev, conf, fillable, note = FIND.get(it['no'], (None,) * 6)
    if not y:
        continue
    b = binof(y)
    if '活动' in str(nat):
        usable = '否（属活动日期）'
    elif '缺档' in b or b == '超出范围':
        usable = '否（档位不足）'
    else:
        usable = '可'
    ws3.append([it['no'], y, nat, b, usable])
    rr = ws3.max_row
    for c in range(1, 6):
        ws3.cell(rr, c).font = BODY_FONT
        ws3.cell(rr, c).border = BORDER
        ws3.cell(rr, c).alignment = Alignment(horizontal='center' if c != 3 else 'left',
                                              vertical='center')
for i, w in enumerate([8, 10, 20, 22, 20], 1):
    ws3.column_dimensions[get_column_letter(i)].width = w
ws3.freeze_panes = 'A2'

out.save(OUT)
print('saved:', OUT)
print('rows', len(rows), 'hit', hit)
