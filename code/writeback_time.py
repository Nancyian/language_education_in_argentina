# -*- coding: utf-8 -*-
"""把核查到的年份写回 官方数据表_正式版.xlsx：
G 发布时间 / H 时期分布 / J 时间依据（新增列）；同步更新核查记录、时间选项、下拉验证。
文件被占用时输出到 官方数据表_正式版_时间补充.xlsx。
"""
import os, shutil, datetime
import openpyxl
from openpyxl.styles import Alignment
from openpyxl.worksheet.datavalidation import DataValidation

D = r'C:/Users/Administrator/Desktop/阿根廷语料库/官方话语'
SRC = os.path.join(D, '官方数据表_正式版.xlsx')

# 序号: (年份, 时期档位, 年份性质, 依据摘要, 置信度)
FILLS = {
    47: ('2010', '2001-2010', '规范颁布年', '页面援引 Res. CFE 119/10（2010）；法定基础为 Ley 26.206（2006）Cap.XI art.52-54', '中高'),
    50: ('2026', '2026-2030', '公告发布年', '标题即「convocatoria 2026-2027」学年招募公告', '中高'),
    62: ('2019', '2016-2020', '专题/活动年', '页面内容为 2019 国际土著语言年系列活动（活动日期，仅作参考锚点）', '中高'),
    65: ('1982', '1981-1990', '项目实施起始年', '页面自述「Desde 1982, los CECIEs brindan igualdad de oportunidades…」', '高'),
    66: ('2018', '2016-2020', '规范颁布年', '页面援引 Res. 2440-MEIGC/18（另 Res. 1345-MEIGC/19）', '高'),
    69: ('2023', '2021-2025', '页面版本年', '最新附件 recurseroEIBAT2023.pdf 上传于 2023-12', '中高'),
    72: ('2013', '2011-2015', '条例颁布年', 'Resolución 1597/MEGC，官方公报 2013-08-13（页面附公报 PDF 链接）', '高'),
    73: ('2001', '2001-2010', '项目实施起始年', '页面自述「El Programa… funciona desde el año 2001」', '高'),
    74: ('2022', '2021-2025', '项目实施起始年', '页面自述「escuelas implementadas en 2022」「funciona desde 2022」', '高'),
    75: ('2015', '2011-2015', '项目实施起始年', '页面载明 DENS 首批「con inicio entre 2015 y 2021」（DEM 三校 2023 起）', '高'),
    76: ('2026', '2026-2030', '页面版本年', '页面载明「En 2026 se suman」（2026 年新增学校名单）', '中高'),
    77: ('2025', '2021-2025', '页面版本年', '最新附件上传路径 /2025-12/（HaLeDiEs 诊断工具 2025 版）', '中高'),
    85: ('2021', '2021-2025', '材料生产年', '系列材料附件上传于 2021-12-02，为 2020-2021 学年设计', '高'),
    90: ('2026', '2026-2030', '页面版本年', '页面为 2026 学年第二学期报名信息（7 月报名、8 月开课）', '中高'),
    92: ('2022', '2021-2025', '活动年', '归档栏目：Módulo 1 于 2022-05-11 开课，配套 PDF 上传于 2022-04-27', '高'),
}
NEW_BINS = ['1981-1990', '1991-2000', '2001-2010']
ALL_BINS = NEW_BINS + ['2011-2015', '2016-2020', '2021-2025', '2026-2030', '时间不详']

# 1) 备份
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
bak = os.path.join(D, '官方数据表_正式版_备份_%s.xlsx' % ts)
shutil.copy(SRC, bak)
print('backup:', os.path.basename(bak))

wb = openpyxl.load_workbook(SRC)
ws = wb['Sheet2']

# 2) 表头样式参照 I1
i1 = ws.cell(1, 9)
j1 = ws.cell(1, 10, '时间依据（核查补充）')
j1.font = i1.font.copy()
j1.fill = i1.fill.copy()
j1.border = i1.border.copy()
j1.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
ws.column_dimensions['J'].width = 46

# 3) 逐行填写
filled = 0
for r in range(2, ws.max_row + 1):
    no = ws.cell(r, 1).value
    if no is None or int(no) not in FILLS:
        continue
    year, binname, nature, evid, conf = FILLS[int(no)]
    ws.cell(r, 7).value = year            # G 发布时间
    ws.cell(r, 8).value = binname         # H 时期分布
    jc = ws.cell(r, 10, '%s：%s' % (nature, evid))
    ref = ws.cell(r, 9)
    jc.font = ref.font.copy()
    jc.border = ref.border.copy()
    jc.alignment = Alignment(vertical='center', wrap_text=True)
    # 同步核查记录（按序号匹配）
    filled += 1

# 4) 下拉验证：重建内联列表
old_dv = ws.data_validations.dataValidation
sqref = old_dv[0].sqref if old_dv else 'H2:H%d' % ws.max_row
ws.data_validations.dataValidation = []
dv = DataValidation(type='list', formula1='"%s"' % ','.join(ALL_BINS),
                    allow_blank=True, showDropDown=False)
ws.add_data_validation(dv)
dv.add(str(sqref))

# 5) 时间选项页同步
ws4 = wb['时间选项']
opts = [ws4.cell(r, 1).value for r in range(2, ws4.max_row + 1) if ws4.cell(r, 1).value]
merged = list(dict.fromkeys(NEW_BINS + opts))
for i, v in enumerate(merged, start=2):
    ws4.cell(i, 1).value = v

# 6) 核查记录更新
ws3 = wb['核查记录']
upd = 0
for r in range(2, ws3.max_row + 1):
    no = ws3.cell(r, 1).value
    if no is None or int(no) not in FILLS:
        continue
    year, binname, nature, evid, conf = FILLS[int(no)]
    ws3.cell(r, 5).value = '核查补充（%s）：%s' % (year, evid)
    ws3.cell(r, 6).value = conf
    upd += 1

# 7) 冻结窗格复位（避免白屏）
for name in ('Sheet2', '核查记录'):
    w = wb[name]
    w.freeze_panes = 'A2'
    w.sheet_view.topLeftCell = 'A1'
    try:
        w.sheet_view.selection[0].activeCell = 'A1'
        w.sheet_view.selection[0].sqref = 'A1'
    except Exception:
        pass

# 8) 保存：优先原文件，被占用则另存
out = SRC
try:
    wb.save(SRC)
    target = '原文件（就地更新）'
except PermissionError:
    out = os.path.join(D, '官方数据表_正式版_时间补充.xlsx')
    wb.save(out)
    target = '另存新文件（原文件被占用）'
print('filled', filled, '| 核查记录更新', upd, '->', target, os.path.basename(out))
