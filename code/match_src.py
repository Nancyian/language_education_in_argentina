# -*- coding: utf-8 -*-
import sys, io, collections

# load sheet1
src_of = collections.defaultdict(set)   # sentence -> set of sources
sent_of = collections.defaultdict(list)
with io.open(r'work/sheet1_full.tsv', encoding='utf-8') as f:
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 4: continue
        row, src, kw, sent = p[0], p[1], p[2], '\t'.join(p[3:])
        sent = sent.replace('\\n', '\n').strip()
        if not sent: continue
        src_of[sent].add(src)
        sent_of[src].append(sent)

print('unique sources:', len(sent_of))

# read sheet2
rows = []
with io.open(r'work/sheet2.tsv', encoding='utf-8') as f:
    for line in f:
        p = line.rstrip('\n').split('\t')
        rows.append(p)

for p in rows[1:]:
    seq = p[1] if len(p) > 1 else ''
    orig = p[9] if len(p) > 9 else ''
    lines = [x.strip() for x in orig.split('\\n') if x.strip()]
    # try match each line
    cand = None
    matched = 0
    allsrc = collections.Counter()
    for L in lines:
        if L in src_of:
            matched += 1
            for s in src_of[L]:
                allsrc[s] += 1
    top = allsrc.most_common(3)
    print(f"seq={seq} lines={len(lines)} matched={matched} top={top}")
