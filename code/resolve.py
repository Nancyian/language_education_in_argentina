# -*- coding: utf-8 -*-
import json, io, unicodedata, re

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'</?[a-z]+>|&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def sim(a, b):
    an, bn = norm(a), norm(b)
    if not an or not bn: return 0.0
    aw = [w for w in an.split() if len(w) > 3]; bw = set(w for w in bn.split() if len(w) > 3)
    if not aw: return 0.0
    ov = sum(1 for w in aw if w in bw)/len(aw)
    if an in bn or bn in an: ov = max(ov, 0.93)
    return ov

rows = [json.loads(l) for l in io.open('work/assembly.tsv', encoding='utf-8')]
jm = json.load(io.open('work/journal_matches.json', encoding='utf-8'))
oa = {}
for l in io.open('work/meta_oa.tsv', encoding='utf-8'):
    d = json.loads(l); oa[d['seq']] = d

out = []
for r in rows:
    seq = r['seq']
    m = jm.get(seq)
    o = oa.get(seq, {})
    doi = ''; src = ''; note = ''
    # 1) journal-scoped Crossref by ISSN
    if m and m.get('score', 0) >= 0.72:
        doi = m['doi']; src = 'CR-journal(%.2f)' % m['score']
    # 2) OpenAlex validated (journal+year) from assembly
    if not doi and r.get('doi'):
        doi = r['doi']; src = 'OpenAlex(j+y)'
    # 3) weak journal match -> keep as suggestion
    if not doi and m and m.get('score', 0) >= 0.5:
        doi = m['doi']; src = 'CR-journal?(%.2f)' % m['score']
    out.append({**r, 'final_doi': doi, 'final_src': src,
                'jm_score': (m or {}).get('score'), 'jm_doi': (m or {}).get('doi'),
                'jm_title': (m or {}).get('title'), 'jm_year': (m or {}).get('year'),
                'oa_doi': o.get('oa_doi'), 'oa_score': o.get('oa_score')})

json.dump(out, io.open('work/final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

resolved = sum(1 for x in out if x['final_doi'])
print('resolved:', resolved, '/', len(out))
print()
for x in out:
    print('%-3s R%-4s y=%-5s %-30s | %s | %s' % (x['seq'], x['row'][1:], x['year'], (x['journal'] or '?')[:30],
          (x['final_doi'] or '—').ljust(42), x['final_src']))
