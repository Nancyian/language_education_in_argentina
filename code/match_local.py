# -*- coding: utf-8 -*-
"""本地匹配：把 need_doi 的每一行 与 已下载的 Crossref 期刊全量记录 做比对。"""
import json, io, os, re, glob, unicodedata, html, sys

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s or '')
        if s2 == s: break
        s = s2
    return s

def norm(s):
    s = unesc(s or '')
    s = unicodedata.normalize('NFKD', s)
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

# --- load crossref corpus ---
recs = []
for f in glob.glob('work/journals/*.json'):
    issn = os.path.basename(f)[:-5]
    try:
        for w in json.load(io.open(f, encoding='utf-8')):
            y = ((w.get('issued', {}).get('date-parts') or [[None]])[0] or [None])[0]
            auth = '; '.join(((a.get('family') or '') + ' ' + (a.get('given') or '')).strip()
                             for a in (w.get('author') or []) if a.get('family'))
            recs.append({'doi': w.get('DOI') or '', 'title': (w.get('title') or [''])[0],
                         'journal': (w.get('container-title') or [''])[0], 'year': y,
                         'authors': auth, 'issn': issn, 'vol': w.get('volume'),
                         'issue': w.get('issue'), 'page': w.get('page')})
    except Exception:
        pass
print('corpus:', len(recs))

# --- load target rows ---
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
asmb = {}
for l in io.open('work/assembly.tsv', encoding='utf-8'):
    r = json.loads(l); asmb[r['seq']] = r

targets = []
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    seq = p[0]
    tgt = {'seq': seq, 'year': p[1], 'issns': [x for x in (p[2] or '').split(',') if x],
           'journal': p[3], 'sheet_title': p[4], 'src': p[5]}
    tgt['real_title'] = unesc((meta.get(seq, {}).get('cit_title') or ''))
    tgt['authors'] = '; '.join(meta.get(seq, {}).get('cit_authors') or [])
    targets.append(tgt)

def year_num(y):
    m = re.findall(r'\d{4}', str(y or ''))
    return int(m[0]) if m else None

results = {}
for t in targets:
    cands = []
    jset = set(i.upper().replace('-', '') for i in t['issns'])
    for r in recs:
        if not r['doi'] or not r['title']:
            continue
        s1 = sim(t['real_title'], r['title'])
        s2 = sim(t['sheet_title'], r['title'])
        sc = max(s1, s2)
        if sc < 0.45:
            continue
        # author bonus
        ab = 0.0
        if t['authors'] and r['authors']:
            an = set(norm(t['authors']).split())
            rn = set(norm(r['authors']).split())
            if an & rn:
                ab = min(0.15, 0.05 * len(an & rn))
        # year
        ty, ry = year_num(t['year']), r['year']
        yb = 0.10 if (ty and ry and abs(ty - ry) <= 1) else (-0.25 if (ty and ry and abs(ty - ry) > 3) else 0.0)
        # same journal bonus
        jb = 0.08 if (r['issn'].upper() in jset or str(r['journal']).lower()[:14] in str(t['journal']).lower()[:14]) else 0.0
        cands.append({**r, 'title_score': round(sc, 3), 'final_score': round(sc + ab + yb + jb, 3),
                      'same_journal': bool(jb)})
    cands.sort(key=lambda x: -x['final_score'])
    # dedupe by doi
    seen = set(); ded = []
    for c in cands:
        k = c['doi'].lower()
        if k in seen: continue
        seen.add(k); ded.append(c)
    results[t['seq']] = {'target': t, 'cands': ded[:5]}
    print('=== seq %s | %s | %s' % (t['seq'], t['year'], t['real_title'][:78]))
    print('    sheet: %s' % t['sheet_title'][:78])
    print('    J: %s | A: %s' % (t['journal'][:52], t['authors'][:70]))
    for c in ded[:3]:
        print('     fs=%.2f ts=%.2f [%s] %-40s %-5s %-24s %s' % (
            c['final_score'], c['title_score'], 'J' if c['same_journal'] else ' ', c['doi'], c['year'],
            (c['journal'] or '')[:24], (c['title'] or '')[:58]))
    if not ded:
        print('     -- no candidate >=0.45 --')
    sys.stdout.flush()

json.dump(results, io.open('work/match_local.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
