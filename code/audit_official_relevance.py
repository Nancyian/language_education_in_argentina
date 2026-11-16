# -*- coding: utf-8 -*-
"""官方话语表主题相关性核查：分级 + 问题标记 + 汇总"""
import shutil, openpyxl, collections
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from copy import copy

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_正式版.xlsx'
DST = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语/官方数据表_主题相关性核查.xlsx'
shutil.copy(SRC, DST)

A = {1: '语言选择政策：与葡萄牙卡蒙斯学院合作在布市学校推葡语',
     2: '五个语种的双语/多语学校制度设计',
     4: 'NES 课程方案中的“附加语言”目标与内容',
     5: '多语学校第二外语课时安排（制度性）',
     17: '语言多样性在课堂中的定位（意识形态表述）',
     21: '首批 6 所公立双语学校落地（政策宣示）',
     22: '国家层外语培训与认证计划（Programa de Formación y Certificación）',
     25: '外语认证与奖学金加分的激励机制',
     26: '土著语言、语言权利与禁语史（权利话语）',
     27: '英语测评纳入 7 年级与 3 年级（评估政策）',
     30: '法语教学质量认证标识（sello de calidad）',
     34: '「BA Ciudad Bilingüe」政策框架下的教师英语培训',
     35: '学生英/法双语认证制度',
     44: '认证政策延续与扩面（政策宣示）',
     47: '国家层面双语跨文化教育（EIB）模式',
     49: '国家英语教学强化计划（Programa Nacional）',
     58: '易读文本与阿根廷手语（语言无障碍服务）',
     62: '土著语言年与 EIB 机构设置',
     69: 'EIB 教学手册（课程与教材制度）',
     72: 'NES 附加语言教学制度',
     73: '多语学校网络（制度）',
     74: '公立小学双语项目（2022 起，制度）',
     75: '中学双语项目：决议与课程方案（PCI）',
     76: '英语强化中学（制度）',
     77: 'ELSI：西班牙语作为第二语言促进包容（语言权利）',
     78: '小学阶段语言教学安排',
     79: '中学阶段语言教学安排',
     80: '中学阶段语言教学安排（“附加语言”术语界定）',
     81: '外语教师资格与入职制度'}

B = {3: '免费法语/英语课程报名通知（政策落地）',
     6: '“布宜诺斯艾利斯与它的语言”活动（宣传）',
     7: '英语奖学金公告（企业合作）',
     10: '英语奖学金公告',
     11: '英语奖学金公告（SEA 合作）',
     12: '英语奖学金公告',
     13: '英语奖学金公告（300 名）',
     18: '外语教师招聘通告',
     19: '英语选修工作坊报名通知',
     24: 'Progresar 奖学金学员修读外语（规模数据）',
     28: '法国语言助理奖学金（国际交流）',
     29: '英国语言助理项目通告',
     31: '英语测评实施通知',
     33: '官员与英国大使参访（活动报道）',
     36: 'Fulbright DAST 双语教育教师培训',
     37: 'Ciudad Bilingüe 图书馆数字点（项目落地）',
     38: '法阿语言助理项目（合作）',
     39: '英国语言助理项目 2026-2027 招募',
     40: '成人小学语言中心英语课（资源配置）',
     41: 'Ciudad Bilingüe 数字点重启（运营）',
     42: 'Mugica 街区英语课（社会公平话语）',
     43: '向小学发放 11.8 万册英语读物（资源投入）',
     45: '选修语言工作坊报名',
     46: '赴美语言助理奖学金',
     50: '美方语言助理项目招募',
     60: '英语奖学金公告（105 名）',
     61: '英语奖学金公告（35 名）',
     64: '标题仅作 “Area”，正文为第二外语课时安排',
     65: '外语补充教育中心（机构设置）',
     66: '教师英语课程',
     67: '课外语言课程（六语种）',
     68: '社区语言课程（Lenguas en los Barrios）',
     70: '跨文化课堂活动材料',
     82: 'Fulbright-GCBA 教师奖学金',
     85: '跨文化反思教学材料',
     87: '法语奖学金公告',
     90: '小学汉语选修工作坊',
     91: '小学英语选修工作坊',
     92: '教师培训模块（教学路径）'}

C = {16: '引用 EF EPI 第三方排名，非官方政策表述',
     88: '栏目页“常见问题”，正文为导航文本，无政策内容',
     89: '栏目页“常见问题”，与 88 高度重复'}

FLAG = {79: '与 80 疑似同页重复（标题仅大小写差异）',
        80: '与 79 疑似同页重复',
        64: '标题残缺（“Area”），建议按正文重命名',
        88: '与 89 重复',
        89: '与 88 重复'}

wb = openpyxl.load_workbook(DST)
ws = wb['Sheet2']
rows = []
for r in range(2, ws.max_row + 1):
    n = int(ws.cell(r, 1).value)
    if n in A: lvl, why = '强相关', A[n]
    elif n in B: lvl, why = '中等', B[n]
    elif n in C: lvl, why = '弱', C[n]
    else: lvl, why = '待定', ''
    rows.append((n, ws.cell(r, 4).value, ws.cell(r, 5).value, ws.cell(r, 7).value,
                 lvl, why, FLAG.get(n, '')))

unknown = [x[0] for x in rows if x[4] == '待定']
print('未分级:', unknown)

if '主题相关性核查' in wb.sheetnames:
    del wb['主题相关性核查']
ws5 = wb.create_sheet('主题相关性核查', 1)
head = ['序号', '文章标题', '发布平台', '发布时间', '主题相关等级', '判定理由', '问题标记']
for c, h in enumerate(head, 1):
    cell = ws5.cell(1, c, h)
    cell.font = Font(bold=True)
    cell.fill = PatternFill('solid', fgColor='DDEBF7')
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = Border(bottom=Side(style='thin'))
for i, row in enumerate(rows, start=2):
    for c, v in enumerate(row, 1):
        cell = ws5.cell(i, c, v)
        cell.alignment = Alignment(vertical='top', wrap_text=(c in (2, 6, 7)))
for col, w in zip('ABCDEFG', (7, 48, 30, 13, 12, 46, 30)):
    ws5.column_dimensions[col].width = w
ws5.freeze_panes = 'A2'
ws5.auto_filter.ref = 'A1:G%d' % (len(rows) + 1)

# 汇总页
ws6 = wb.create_sheet('核查汇总', 0)
cnt = collections.Counter(x[4] for x in rows)
plat = collections.Counter(x[2] for x in rows)
ws6['A1'] = '官方话语语料 · 主题相关性核查'; ws6['A1'].font = Font(bold=True, size=14)
data = [('总数', len(rows)), ('强相关', cnt['强相关']), ('中等', cnt['中等']), ('弱', cnt['弱'])]
r0 = 3
for k, v in data:
    ws6.cell(r0, 1, k); ws6.cell(r0, 2, v); r0 += 1
r0 += 1
ws6.cell(r0, 1, '按发布平台').font = Font(bold=True); r0 += 1
for k, v in plat.most_common():
    ws6.cell(r0, 1, k); ws6.cell(r0, 2, v); r0 += 1
r0 += 1
notes = [('主要风险 1', '57/71（80%）为布宜诺斯艾利斯市（CABA）级材料，国家层级仅 12 条（教育部）+ 2 条（国会图书馆）'),
         ('主要风险 2', '30 条“发布时间不详”（静态栏目页），占 42%，无法参与历时比较'),
         ('主要风险 3', '约 38 条为奖学金/报名/活动通告，话语层面以项目实施语为主，政策表述密度较低'),
         ('主要风险 4', '4 组重复或近似重复（79/80、88/89），1 条标题残缺（64 “Area”）')]
ws6.cell(r0, 1, '核查结论').font = Font(bold=True); r0 += 1
for k, v in notes:
    ws6.cell(r0, 1, k); ws6.cell(r0, 2, v).alignment = Alignment(vertical='top', wrap_text=True); r0 += 1
ws6.column_dimensions['A'].width = 16
ws6.column_dimensions['B'].width = 95

wb.save(DST)
print('saved', DST)
print('计数', dict(cnt))
