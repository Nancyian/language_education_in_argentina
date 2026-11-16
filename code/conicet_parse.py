# -*- coding: utf-8 -*-
"""从 CONICET 本地仓储快照提取文章级元数据（利用标准引用串：作者; 标题; 期刊; 卷; 期; 日期; 页码）"""
import io, json, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'work')
sys.path.insert(0, 'tools')
from kw_merge import norm, RULES, has, CONTEXT

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/conicet_language_corpus.xlsx'

MONTHS = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
          'septiembre', 'setiembre', 'octubre', 'noviembre', 'diciembre')
# 尾部：; 12-2016; 16-21   /  ; 5-2016; 338-353   /  ; 2016   /  ; 2; 5-2016
TAIL = re.compile(r';\s*(?:\d{1,4};\s*)*(?:(?:\d{1,2}-)?(?:19|20)\d{2})(?:\s*;\s*[\d\-–]+)?\s*\.?$')
DATE_SEG = re.compile(r'^(?:\d{1,2}-)?(19|20)\d{2}$')
NUMSEG = re.compile(r'^\d{1,4}([\-–]\d{1,4})?$')


def parse_citation(seg_list):
    """结构：作者(可多段/含 et al.) ; 标题 ; 机构 ; 期刊 ; 卷 ; 期 ; 日期 ; 页码
    日期段之前固定为  机构 ; 期刊 ; 卷 ; (期)  -> 标题段 = 机构段前一段。"""
    segs = [s.strip() for s in seg_list if s and s.strip()]
    if len(segs) < 6:
        return None
    di = None
    for i in range(len(segs) - 1, -1, -1):
        if DATE_SEG.match(segs[i]):
            di = i
            break
    if di is None or di < 5:
        return None
    year = int(segs[di][-4:])
    # 从日期段向前数：卷(必)、期刊(必)、机构(必)、标题(必)
    k = di - 1
    # 卷 与 期 可能是纯数字段，跳过
    skipped = 0
    while k >= 0 and NUMSEG.match(segs[k]) and skipped < 2:
        k -= 1
        skipped += 1
    if k < 3:
        return None
    journal = segs[k]
    inst = segs[k - 1]
    title = segs[k - 2]
    authors = '; '.join(segs[:k - 2])
    # 期刊/机构段不应像标题（过长且带句号/冒号后小写）
    if len(title) < 12 or NUMSEG.match(title) or DATE_SEG.match(title):
        return None
    # 若「机构」段明显更像标题（长度远大于期刊），则以它为标题，标题段降为机构
    if len(inst) > len(journal) * 1.8 and len(inst) > 25:
        title, inst = inst, title
    return {'title': title, 'authors': authors, 'venue': journal, 'year': year}


INST_START = ('asociacion', 'sociedad', 'instituto', 'universidad', 'facultad', 'departamento',
              'consejo', 'centro', 'grupo', 'programa', 'revista', 'editorial', 'ministerio',
              'secretaria', 'laboratorio', 'escuela', 'colegio', 'fundacion')


def main():
    import openpyxl
    ws = openpyxl.load_workbook(SRC, read_only=True)['corpus']
    by_handle = collections.OrderedDict()
    for r in ws.iter_rows(min_row=2, max_row=12951, max_col=3, values_only=True):
        if not r[0]:
            continue
        d = by_handle.setdefault(r[0], {'kws': [], 'frags': []})
        if r[1] and r[1] not in d['kws']:
            d['kws'].append(r[1])
        if r[2] and str(r[2]) not in d['frags']:
            d['frags'].append(str(r[2]))
    print('handles', len(by_handle))

    recs = []
    for h, d in by_handle.items():
        best = None
        for f in d['frags']:
            f = re.sub(r'<[^>]+>', '', f).strip()
            if f.count(';') < 4:
                continue
            p = parse_citation(f.split(';'))
            if not p:
                continue
            p['title'] = re.sub(r'\s+', ' ', p['title']).strip(' .')
            if not (15 <= len(p['title']) <= 260):
                continue
            if p['title'][0].islower():
                continue
            if norm(p['title']).split(' ')[0] in INST_START:
                continue
            p['score'] = len(p['title']) + (10 if p['venue'] else 0)
            if not best or p['score'] > best['score']:
                best = p
        if not best:
            continue
        best.update({'db': 'CONICET', 'url': h, 'kws': d['kws'],
                     'abstract': re.sub(r'\s+', ' ', ' '.join(d['frags']))[:2500],
                     'kw': '; '.join(d['kws'])})
        best.pop('score', None)
        recs.append(best)
    print('parsed recs', len(recs))

    # 关键词强相关过滤（与 Dialnet 同规则）
    def strong(t):
        hit = [k for k, fn in RULES.items() if fn(t)]
        if not hit:
            return None
        if len(hit) < 2 and not has(t, *CONTEXT):
            return None
        return hit

    kept = []
    LANGWORD = ('lengua', 'lenguas', 'idioma', 'idiomas', 'linguistic', 'biling', 'habla',
                'hablante', 'language', 'lenguaje', 'discurso', 'lexic', 'gramat', 'dialect',
                'sociolingu', 'glotopolit', 'escritur', 'alfabetiz', 'traducc')
    for r in recs:
        t = norm(r['title'])
        if len(t) < 12:
            continue
        hit = strong(t)
        if not hit:
            continue
        # 必须含语言学科词（CONICET 仓储关键词检索噪声大：如 "del inglés" 是术语说明）
        if not any(w in t for w in LANGWORD):
            continue
        if any(b in t for b in ('larva', 'culicid', 'insect', 'tumor', 'tumour', 'crop',
                                'dietary', 'patholog', 'clinical', 'mosquito', 'steel',
                                'soil', 'nitrate', 'carbon', 'materials')):
            continue
        r['hit'] = hit
        kept.append(r)
    print('strong & language', len(kept))
    for r in kept[:40]:
        print(' -', r['year'], '|', r['title'][:100], '|', r['venue'][:40])
    json.dump(kept, io.open('work/pool_conicet.json', 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
