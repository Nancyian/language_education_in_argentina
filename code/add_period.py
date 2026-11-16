# -*- coding: utf-8 -*-
"""Add 研究时段 (content period) + 时段依据 columns, keep 时期分布 (publication-year bins)."""
import openpyxl, copy
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

SRC = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_DOI.xlsx"
DST = r"C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_DOI_时段.xlsx"

P_COL = "殖民时期（16-18世纪）"
P_19 = "19世纪（国家建构）"
P_20A = "20世纪上半叶（1901-1945）"
P_20B = "20世纪下半叶（1946-1999）"
P_21 = "21世纪（2000-）"
P_X = "跨时段"
P_N = "通论/不详"
OPTIONS = [P_COL, P_19, P_20A, P_20B, P_21, P_X, P_N]

A = {
 '1': (P_19, '1878年起国家政府向巴塔哥尼亚推行西语，威尔士语—西语接触（丘布特殖民初期）'),
 '2': (P_19, '分析1893年Dobranich & Monner Sans《Gramática de la lengua castellana》'),
 '3': (P_X, '1884年Ley 1420至2006年Ley 26.206的学校语言教育'),
 '4': (P_21, '2012年拉普拉塔11名EFL教师访谈'),
 '5': (P_19, '1869-70年《El Río de la Plata》政论及《Martín Fierro》'),
 '6': (P_21, '布宜诺斯艾利斯华人学校民族志（当代）'),
 '7': (P_21, '圣地亚哥-德尔埃斯特罗克丘亚语移民（当代田野）'),
 '8': (P_21, '米西奥内斯Mbyá Guaraní双语识字实践（当代）'),
 '9': (P_X, '1853年宪法、1884年Ley 1420、1985年Ley 23302'),
 '10': (P_21, 'PFCLE线上外语培训项目（近年）'),
 '11': (P_21, '高校语言政策微观实施（近年）'),
 '12': (P_20A, '书评对象为Grossmann 1926年原著（2008年重版）'),
 '13': (P_X, '1860-1930年潘帕与巴塔哥尼亚传教语言学'),
 '14': (P_19, '19世纪阿根廷面向原住民的bilingual教育构想'),
 '15': (P_20A, 'Porchia（1885-1968）的移民与语言经验'),
 '16': (P_21, 'EIB现状调查（在研项目首轮结果）'),
 '17': (P_20B, '小说《Shunko》(1949)中的西语—克丘亚语接触'),
 '18': (P_21, '英语师资培养中的批判教育学（当代课堂）'),
 '19': (P_X, '南方共同市场成立后第一个十年（1991-2001）'),
 '20': (P_21, 'LSA—西语双语识字（当代）'),
 '21': (P_19, '19世纪乌拉圭词典编纂（1816年Larrañaga等）'),
 '22': (P_X, 'Koessler-Ilg 1920-1962年在巴塔哥尼亚的采集'),
 '23': (P_N, '面向NEA地区的西语交际语法教学建议，未限定年代'),
 '24': (P_21, '布省西南移民社区语码交替（当代调查）'),
 '25': (P_21, '家庭语言社会化研究（当代）'),
 '26': (P_21, '双语/单语儿童语篇发展对比（当代）'),
 '27': (P_N, '书评：Boyer & Penner《El Paraguay bilingüe》，未标时段'),
 '28': (P_N, 'ELSE研究专辑导言，学科现状综述'),
 '29': (P_21, '师范生阅读日志分析（当代）'),
 '30': (P_N, '里奥普拉滕塞西语与巴西葡语体貌对比（共时描写）'),
 '31': (P_X, '查科省EIB政策1987-2014'),
 '32': (P_21, '科连特斯瓜拉尼语—西语双语儿童（当代）'),
 '33': (P_21, 'Ancalao（1961年生）的当代双语诗作'),
 '34': (P_21, '32名聋人语料（当代共时分析）'),
 '35': (P_21, '查科省EIB教师角色（当代）'),
 '36': (P_X, 'EIB政策历史脉络＋当前状况综述'),
 '37': (P_19, '1850年代巴斯克移民的西语语法教材'),
 '38': (P_19, '圣地亚哥-德尔埃斯特罗克丘亚语共时描写'),
 '39': (P_21, '特雷利乌威尔士语—西语社区（1865年移民至今）'),
 '40': (P_X, '1993年联邦教育法与2004/2006年国家教育法'),
 '41': (P_21, 'AAL 2011年《阿根廷惯用语疑问词典》等'),
 '42': (P_21, '2018年大学聋生西语写作工作坊'),
 '43': (P_21, '里奥内格罗省聋人识字研究（当代）'),
 '44': (P_X, '20世纪末以来的双模态EIB'),
 '45': (P_21, 'Educar频道风格手册2012-2015'),
 '46': (P_21, '布宜诺斯艾利斯华人社区语言景观（当代）'),
 '47': (P_21, '合作民族志（当代）'),
 '48': (P_21, '布宜诺斯艾利斯克丘亚语接触与标准语教学（当代）'),
 '49': (P_X, 'Aguirre剧作1963/1982/1987，涉17世纪征服至当代'),
 '50': (P_20A, 'Rojas与Menéndez Pidal通信（一战前后至1930年代）'),
 '51': (P_20A, '1912年布宜诺斯艾利斯巴斯克语教材'),
 '52': (P_X, '19世纪末至20世纪初的西语教学文本'),
 '53': (P_20A, '1926年布大语文学研究所的机构化'),
 '54': (P_COL, 'Minsheu 1599年西语学习对话集'),
 '55': (P_21, '卡塔马卡农村学校EIB（当代）'),
 '56': (P_21, '南方共同市场语言教育政策（1990年代至今）'),
 '57': (P_X, '萨尔塔/米西奥内斯瓜拉尼人EIB（历史法规＋当代调研）'),
 '58': (P_20B, '《Contorno》杂志1953-1959'),
 '59': (P_21, '科连特斯农村中学瓜拉尼语—西语（当代）'),
 '60': (P_X, '阿根廷外语教育政策史（19世纪末至20世纪上半叶）'),
 '61': (P_N, '安第斯西语口语叙事（共时）'),
 '62': (P_21, '高教国际化与语言政策（当代）'),
 '63': (P_N, '书评：Mercosur语言文化衔接项目'),
 '64': (P_N, '以博尔赫斯《El otro》(1975)为教学材料的当代课堂设计'),
 '65': (P_21, '阿根廷—巴西高校合作项目（当代）'),
 '66': (P_21, 'Piglia《El camino de Ida》(2013)'),
 '67': (P_21, '罗萨里奥海地移民西语教学（当代）'),
 '68': (P_20A, '1910年Berlitz“阿根廷语”会话手册'),
 '69': (P_21, '克罗地亚语传承（当代调查）'),
 '70': (P_N, '高校英语阅读教学（未限定年代）'),
 '71': (P_21, '圣路易斯英语教材跨文化分析（当代）'),
 '72': (P_21, 'UNSL英语阅读教学实践（当代）'),
 '73': (P_21, '“La quichua en mi escuela”项目（当代）'),
 '74': (P_N, '探戈歌词中的伦法多，未限年代，落脚当代教学'),
 '75': (P_21, 'COIL课程（当代）'),
 '76': (P_X, 'Di Tullio学术生涯访谈（1970年代至今）'),
 '77': (P_X, 'Cvejanov访谈（LSA研究1990年代至今）'),
 '78': (P_X, '中介语概念提出五十年（1972年至今）'),
 '79': (P_21, '传承语者二语习得（当代数据）'),
 '80': (P_21, '课堂互动分析（当代）'),
 '81': (P_21, 'UNAM手语课程（当代）'),
 '82': (P_X, 'Mercosur成立三十余年后（1991年至今）'),
 '83': (P_N, '语法教学中的语言变异（教学设计）'),
 '84': (P_N, '螺旋课程设计建议，未限定年代'),
 '85': (P_21, '玻利维亚移民社群语用研究（当代）'),
 '86': (P_21, '巴拉圭—阿根廷边境瓜拉尼语（当代）'),
 '87': (P_21, '边境语言态度调查（当代）'),
 '88': (P_21, '哥伦比亚/阿根廷双语政策（当代）'),
 '89': (P_21, '全球化下的语言接触（当代）'),
 '90': (P_21, 'LSA笔译实践（当代）'),
 '91': (P_21, 'LSA经济术语口译（当代）'),
 '92': (P_X, 'LSA语言学三十年（1990年代至今）'),
 '93': (P_19, '19世纪加利西亚语/巴斯克语/加泰罗尼亚语著作'),
 '94': (P_20A, '20世纪上半叶阿根廷东北部西语研究'),
 '95': (P_21, '书评：Klett 2024'),
 '96': (P_21, 'qom语—西语儿童识字互动（当代）'),
 '97': (P_21, '移民叙事中的土著语言（当代）'),
 '98': (P_X, 'Santa Olalla语法批评（19-20世纪）'),
 '99': (P_X, '阿根廷ELE/ELSE语法专著文献基础（19-20世纪）'),
}

wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']
ws.cell(row=1, column=10).value = '研究时段'
ws.cell(row=1, column=11).value = '时段依据'

# style headers like existing header row
h8 = ws.cell(row=1, column=8)
for c in (10, 11):
    cell = ws.cell(row=1, column=c)
    cell.font = copy.copy(h8.font)
    cell.fill = copy.copy(h8.fill)
    cell.border = copy.copy(h8.border)
    cell.alignment = copy.copy(h8.alignment)

missing = []
for row in range(2, ws.max_row + 1):
    seq = str(ws.cell(row=row, column=1).value).strip()
    if seq not in A:
        missing.append(seq)
        continue
    lab, note = A[seq]
    c10 = ws.cell(row=row, column=10)
    c11 = ws.cell(row=row, column=11)
    c10.value = lab
    c11.value = note
    c10.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    c11.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

# hidden option sheet + dropdown
if '时段选项' in wb.sheetnames:
    del wb['时段选项']
opt = wb.create_sheet('时段选项')
opt['A1'] = '研究时段选项'
for i, v in enumerate(OPTIONS, start=2):
    opt.cell(row=i, column=1).value = v
opt.sheet_state = 'hidden'

dv = DataValidation(type='list', formula1='时段选项!$A$2:$A$%d' % (len(OPTIONS) + 1), allow_blank=True)
ws.add_data_validation(dv)
dv.add('J2:J%d' % ws.max_row)

# clarify col H header
ws['H1'].comment = Comment(
    '本列＝发表时间按5年分箱（1981-1985 … 2021-2025），反映的是文献出版年代，'
    '不是论文研究/涉及的历史时段。论文涉及的历史时段见 J 列「研究时段」。', '整理说明', width=320, height=110)

ws.column_dimensions['J'].width = 24
ws.column_dimensions['K'].width = 46

wb.save(DST)
print('saved ->', DST)
print('missing seq:', missing)

import collections
cnt = collections.Counter(v[0] for v in A.values())
print('rows:', len(A))
for k in OPTIONS:
    print('  %-26s %d' % (k, cnt[k]))
