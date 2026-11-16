# -*- coding: utf-8 -*-
"""统一「来源」列：优先 DOI；无 DOI 时优先期刊原生文章页，其次保留原链接。"""
import openpyxl, json, io, os, re, unicodedata, html, sys

DST = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_DOI.xlsx'

# ---- 新增确认的 DOI ----
NEW_DOI = {
    '35': '10.19137/els-2017-1414010',      # Crossref 已注册、可解析
    '45': '10.19137/anclajes-2019-2323',    # Crossref 已注册、可解析
    '95': '10.5281/zenodo.14236147',        # DataCite/Zenodo 已注册
}
# ---- 期刊在 DOAJ 元数据中正式声明、但未注册、解析 404 的 DOI ----
DECLARED_UNREGISTERED = {
    '25': '10.14483/16579089.4642',
    '27': '10.34096/sys.n24.3217',
    '28': '10.34096/sys.n22.3046',
    '32': '10.34096/sys.n29.2807',
}
USE_UNREGISTERED = True   # 置 False 则这些行保留可用的文章链接

# 人工核对确认的期刊原生文章页（OAI 标题为英文导致自动匹配失败）
MANUAL_URL = {
    '58': 'https://revistas.uncu.edu.ar/ojs3/index.php/cilha/article/view/1511',
}

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or ''); s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'<[^>]+>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

STOP = set('de la el los las un una y en del al para por con sobre como su sus desde entre the of and a to in on for with'.split())

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 2 and w not in STOP]
    bw = set(bn.split())
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw) / len(aw)
    if an == bn: ov = 1.0
    elif an in bn or bn in an: ov = max(ov, 0.94)
    return ov

# ---- OAI 语料（期刊原生 URL） ----
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
# OAI 源 -> 期刊名关键词（只有两者对应时才允许替换链接）
SRC_KEY = {
    'Traslaciones': 'Traslaciones',
    'CILHA': 'CILHA',
    'Gramma': 'Gramma',
    'RAHL': 'RAHL',
    'SignosELE': 'Signos ELE',
    'Entramados': 'Entramados',
    'AnalectaMal': 'Analecta',
}
oai = {}
for f in os.listdir('work/oai2'):
    name = f[:-5]
    if name not in SRC_KEY: continue
    try:
        oai[name] = [x for x in json.load(io.open('work/oai2/' + f, encoding='utf-8')) if x.get('url')]
    except Exception:
        pass
print('oai sources:', {k: len(v) for k, v in oai.items()})

wb = openpyxl.load_workbook(DST)
ws = wb['Sheet2']
plan = []
for r in range(2, ws.max_row + 1):
    seq = str(ws.cell(row=r, column=1).value or '').strip()
    if not seq: continue
    cur = str(ws.cell(row=r, column=2).value or '').strip()
    title = unesc(meta.get(seq, {}).get('cit_title') or '')
    journal = str(meta.get(seq, {}).get('cit_journal') or '')
    new, why = cur, 'keep'
    if seq in NEW_DOI:
        new, why = NEW_DOI[seq], 'DOI(new)'
    elif seq in DECLARED_UNREGISTERED and USE_UNREGISTERED:
        new, why = DECLARED_UNREGISTERED[seq], 'DOI(declared)'
    elif cur.startswith('10.'):
        new, why = cur, 'DOI(keep)'
    elif seq in MANUAL_URL and cur != MANUAL_URL[seq]:
        new, why = MANUAL_URL[seq], 'URL(manual)'
    else:
        best = None
        for name, recs in oai.items():
            if SRC_KEY[name].lower() not in journal.lower():
                continue
            for x in recs:
                s = sim(title, x.get('title') or '')
                # 要求词重叠足够多，避免短标题误配
                an = set(w for w in norm(title).split() if len(w) > 2 and w not in STOP)
                xn = set(w for w in norm(x.get('title') or '').split())
                overlap = len(an & xn)
                if s >= 0.80 and overlap >= 5 and (not best or s > best[0]):
                    best = (s, x['url'])
        if best and best[1] != cur:
            new, why = best[1], 'URL(oai %.2f)' % best[0]
    plan.append((r, seq, cur, new, why))

print('\n%-4s %-4s %-16s %s' % ('row', 'seq', 'why', 'value'))
for r, seq, cur, new, why in plan:
    if new != cur:
        print('%-4d %-4s %-16s %s' % (r, seq, why, new[:96]))

# 应用
for r, seq, cur, new, why in plan:
    if new != cur:
        ws.cell(row=r, column=2).value = new

ndoi = sum(1 for r, seq, cur, new, why in plan if new.startswith('10.'))
print('\nTOTAL=%d  DOI=%d  URL=%d' % (len(plan), ndoi, len(plan) - ndoi))
if '--save' in sys.argv:
    wb.save(DST)
    print('SAVED')
else:
    print('(dry-run; 添加 --save 以写入)')
