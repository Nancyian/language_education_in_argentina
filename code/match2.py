# -*- coding: utf-8 -*-
import io, collections

# load sheet1: normalize multi-line 原句 -> source
norm = {}
for line in io.open('work/sheet1_full.tsv', encoding='utf-8'):
    p = line.rstrip('\n').split('\t')
    if len(p) < 4: continue
    src = p[1]
    sent = '\t'.join(p[3:]).strip()
    key = sent
    if key in norm and norm[key] != src:
        norm[key] = norm[key]  # keep first
    else:
        norm[key] = src

print('sheet1 rows:', len(norm))

rows = []
for line in io.open('work/sheet2.tsv', encoding='utf-8'):
    rows.append(line.rstrip('\n').split('\t'))

out = io.open('work/match_result.tsv', 'w', encoding='utf-8')
hit = 0
for p in rows[1:]:
    g = lambda i: p[i] if i < len(p) else ''
    seq = g(1)
    orig = g(9)  # already has \n as literal backslash-n
    cands = []
    if orig in norm:
        cands.append(norm[orig])
    else:
        # try without trailing/leading
        if orig.strip() in norm:
            cands.append(norm[orig.strip()])
        else:
            # find best by longest common prefix line: try each line joined subsets
            lines = orig.split('\\n')
            # try progressive join from start
            for n in range(len(lines), 0, -1):
                k = '\\n'.join(lines[:n])
                if k in norm:
                    cands.append(norm[k]); break
            if not cands:
                for n in range(len(lines), 0, -1):
                    k = '\\n'.join(lines[-n:])
                    if k in norm:
                        cands.append(norm[k]); break
    src = cands[0] if cands else ''
    if src: hit += 1
    out.write('%s\t%s\t%s\n' % (g(0), seq, src))
out.close()
print('matched:', hit, '/', len(rows)-1)
