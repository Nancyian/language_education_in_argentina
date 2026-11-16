# -*- coding: utf-8 -*-
"""CONICET 快照全量解析（不做强相关预筛），输出 work/conicet_all.json"""
import io, json, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'tools')
from conicet_parse import parse_citation, INST_START
from kw_merge import norm

SRC = r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/conicet_language_corpus.xlsx'

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
    json.dump(recs, io.open('work/conicet_all.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    from collections import Counter
    print(Counter(r['venue'][:40] for r in recs).most_common(15))


if __name__ == '__main__':
    main()
