# -*- coding: utf-8 -*-
"""逐个期刊 OAI 采集（增量保存），并立即与目标行匹配。"""
import urllib.request, urllib.error, urllib.parse, json, ssl, re, time, io, html, unicodedata, sys, os, glob

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36'

def fetch(u, timeout=15, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'ignore')
        except Exception:
            time.sleep(1)
    return None

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

JOURNALS = {
    'Argonautas':  'https://www.argonautas.unsl.edu.ar/index.php/revista/oai',
    'RAES':        'https://revistas.untref.edu.ar/index.php/raes/oai',
    'Pilquen':     'http://revele.uncoma.edu.ar/index.php/psicopedagogia/oai',
    'RLEI':        'https://revistas.ucentral.cl/revista_inclusion/oai',
    'RMIE':        'https://www.comie.org.mx/revista/v2018/rmie/index.php/nrmie/oai',
    'Oltreoceano': 'https://riviste.unimi.it/index.php/oltreoceano/oai',
    'EstInter':    'https://revistas.uva.es/index.php/estudiosinterlinguisticos/oai',
    'Gramma':      'https://p3.usal.edu.ar/index.php/gramma/oai',
    'Ianua':       'http://www.romaniaminor.net/ianua/oai2.php',
    'LenguaHabla': 'http://erevistas.saber.ula.ve/index.php/lenguayhabla/oai',
    'AnalectaMal': 'https://revistas.uma.es/index.php/analecta/oai',
    'RACC':        'https://revistas.unc.edu.ar/index.php/racc/oai',
    'Traslaciones': 'https://revistas.uncu.edu.ar/ojs3/index.php/traslaciones/oai',
    'CILHA':       'https://revistas.uncu.edu.ar/ojs3/index.php/cilha/oai',
    'RAHL':        'https://www.rahl.ar/index.php/rahl/oai',
}

def harvest(base, maxpages=20, budget=90):
    url = base + '?verb=ListRecords&metadataPrefix=oai_dc'
    recs = []; t0 = time.time()
    for i in range(maxpages):
        if time.time() - t0 > budget: break
        h = fetch(url)
        if not h: return recs, 'fetch-fail'
        for r in re.findall(r'<record>(.*?)</record>', h, re.S):
            def g1(tag, multi=False):
                m = re.findall(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), r, re.S)
                vals = [unesc(re.sub(r'\s+', ' ', x)).strip() for x in m]
                return vals if multi else (vals[0] if vals else '')
            ids = g1('dc:identifier', True); rel = g1('dc:relation', True)
            blob = ' '.join(ids + rel + [g1('dc:source')])
            dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', blob)
            recs.append({'title': g1('dc:title'), 'doi': (dois[0].rstrip('.').rstrip(',') if dois else ''),
                         'date': g1('dc:date'), 'creators': g1('dc:creator', True),
                         'url': next((x for x in ids if x.startswith('http')), '')})
        m = re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>', h)
        if not m: break
        url = base + '?verb=ListRecords&resumptionToken=' + m.group(1)
        time.sleep(0.2)
    return recs, 'ok'

# 目标
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
targets = []
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    targets.append({'seq': p[0], 'year': p[1], 'title': unesc(meta.get(p[0], {}).get('cit_title') or p[4]),
                    'journal': p[3]})

os.makedirs('work/oai2', exist_ok=True)
results = {}
for name, base in JOURNALS.items():
    af = 'work/oai2/%s.json' % name
    if os.path.exists(af):
        recs = json.load(io.open(af, encoding='utf-8'))
        st = 'cached'
    else:
        recs, st = harvest(base)
        json.dump(recs, io.open(af, 'w', encoding='utf-8'), ensure_ascii=False)
    nd = sum(1 for r in recs if r['doi'])
    print('%-13s recs=%-5d withDOI=%-4d [%s]' % (name, len(recs), nd, st))
    for t in targets:
        scored = []
        for r in recs:
            s = sim(t['title'], r['title'])
            if s >= 0.62:
                scored.append({'score': round(s, 3), 'doi': r['doi'], 'title': r['title'],
                               'date': r['date'], 'url': r['url'], 'from': name})
        if scored:
            scored.sort(key=lambda x: -x['score'])
            results.setdefault(t['seq'], []).extend(scored[:3])
    sys.stdout.flush()

json.dump(results, io.open('work/oai2_match.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('===== MATCHES =====')
for seq in sorted(results, key=lambda s: int(s)):
    t = [x for x in targets if x['seq'] == seq][0]
    print('=== seq %s | %s | %s' % (seq, t['year'], t['title'][:58]))
    seen = set()
    for x in sorted(results[seq], key=lambda y: -y['score'])[:3]:
        k = (x['doi'], x['title'][:40])
        if k in seen: continue
        seen.add(k)
        print('     %.2f DOI=%-42s %-6s %-13s %s' % (x['score'], x['doi'] or '(none)', (x['date'] or '')[:6], x['from'], x['title'][:50]))
print('DONE')
