# -*- coding: utf-8 -*-
"""OAI-PMH 采集：从各期刊接口取回全部文章元数据（含 DOI），并本地匹配。"""
import urllib.request, urllib.error, urllib.parse, json, ssl, re, time, io, html, unicodedata, sys, os

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36'

def fetch(u, timeout=20, tries=2):
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA})
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'ignore')
        except Exception as e:
            last = str(e)[:60]; time.sleep(1.5 + i * 2)
    return None

JOURNALS = {
    'RACC':        'https://revistas.unc.edu.ar/index.php/racc/oai',
    'Traslaciones': 'https://revistas.uncu.edu.ar/ojs3/index.php/traslaciones/oai',
    'CILHA':       'https://revistas.uncu.edu.ar/ojs3/index.php/cilha/oai',
    'Entramados':  'https://fh.mdp.edu.ar/revistas/index.php/entramados/oai',
    'LenguaHabla': 'http://erevistas.saber.ula.ve/index.php/lenguayhabla/oai',
    'AnalectaMal': 'https://revistas.uma.es/index.php/analecta/oai',
    'SignosELE':   'https://p3.usal.edu.ar/index.php/ele/oai',
    'Gramma':      'https://p3.usal.edu.ar/index.php/gramma/oai',
    'Argonautas':  'https://www.argonautas.unsl.edu.ar/index.php/revista/oai',
    'RAES':        'https://revistas.untref.edu.ar/index.php/raes/oai',
    'Pilquen':     'http://revele.uncoma.edu.ar/index.php/psicopedagogia/oai',
    'RLEI':        'https://revistas.ucentral.cl/revistainclusiones/oai',
    'RMIE':        'https://www.comie.org.mx/revista/v2018/rmie/index.php/nrmie/oai',
    'Oltreoceano': 'https://riviste.unimi.it/index.php/oltreoceano/oai',
    'EstInter':    'https://revistas.uva.es/index.php/estudiosinterlinguisticos/oai',
    'RAHL':        'https://www.rahl.ar/index.php/rahl/oai',
    'Ianua':       'http://www.romaniaminor.net/ianua/oai',
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

def harvest(base, maxpages=25):
    url = base + '?verb=ListRecords&metadataPrefix=oai_dc'
    recs = []
    for i in range(maxpages):
        h = fetch(url)
        if not h:
            return recs, 'fetch-fail'
        for r in re.findall(r'<record>(.*?)</record>', h, re.S):
            def g1(tag, multi=False):
                m = re.findall(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), r, re.S)
                vals = [unesc(re.sub(r'\s+', ' ', x)).strip() for x in m]
                return vals if multi else (vals[0] if vals else '')
            recs.append({'title': g1('dc:title'), 'ids': g1('dc:identifier', True),
                         'relations': g1('dc:relation', True), 'creators': g1('dc:creator', True),
                         'date': g1('dc:date'), 'source': g1('dc:source'),
                         'desc': g1('dc:description')[:300]})
        m = re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>', h)
        if not m: break
        url = base + '?verb=ListRecords&resumptionToken=' + m.group(1)
        time.sleep(0.3)
    return recs, 'ok'

allrec = {}
for name, base in JOURNALS.items():
    try:
        recs, st = harvest(base)
    except Exception as e:
        print('%-14s ERR %s' % (name, str(e)[:50])); continue
    nd = 0
    for r in recs:
        blob = ' '.join(r['ids'] + r['relations'] + [r['source']])
        dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', blob)
        r['doi'] = dois[0].rstrip('.').rstrip(',') if dois else ''
        if r['doi']: nd += 1
    allrec[name] = recs
    print('%-14s recs=%-5d withDOI=%-4d [%s]' % (name, len(recs), nd, st))
    sys.stdout.flush()

json.dump(allrec, io.open('work/oai_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 匹配
meta = {}
for l in io.open('work/meta_full.tsv', encoding='utf-8'):
    r = json.loads(l); meta[r['seq']] = r
best = {}
for l in io.open('work/need_doi.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    seq = p[0]
    t = unesc(meta.get(seq, {}).get('cit_title') or p[4])
    scored = []
    for name, recs in allrec.items():
        for r in recs:
            s = sim(t, r['title'])
            if s >= 0.62:
                scored.append({'score': round(s, 3), 'journal': name, 'doi': r['doi'],
                               'title': r['title'], 'date': r['date'],
                               'url': next((x for x in r['ids'] if x.startswith('http')), '')})
    scored.sort(key=lambda x: -x['score'])
    best[seq] = scored[:4]
    if scored:
        print('=== seq %s | %s | %s' % (seq, p[1], t[:58]))
        for x in scored[:3]:
            print('     %.2f DOI=%-40s %-6s %-14s %s' % (x['score'], x['doi'] or '(none)', (x['date'] or '')[:6], x['journal'], x['title'][:52]))
json.dump(best, io.open('work/oai_match.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('DONE')
