import urllib.request, urllib.error, urllib.parse, json, ssl, time, io, re, unicodedata, sys

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'MetadataEnrichment/1.0 (mailto:researcher@example.org)'}

def get(url, tries=3, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=timeout, context=ctx))
        except urllib.error.HTTPError as e:
            last = 'HTTP%d' % e.code
            time.sleep(1.5 + i * 2)
        except Exception as e:
            last = str(e)[:50]
            time.sleep(1.5 + i * 2)
    return {'__err__': last}

def unesc(s):
    import html
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

def cr_issn(issn, title, year=None, rows=100):
    """Crossref: query within a journal ISSN."""
    u = ('https://api.crossref.org/journals/%s/works?rows=%d&select=DOI,title,container-title,issued,author,volume,issue,page'
         '&query.bibliographic=%s' % (issn.replace('-', ''), rows, urllib.parse.quote(title)))
    d = get(u)
    if '__err__' in d: return []
    out = []
    for it in d.get('message', {}).get('items', []):
        t = (it.get('title') or [''])[0]
        y = ((it.get('issued', {}).get('date-parts') or [[None]])[0] or [None])[0]
        out.append({'doi': it.get('DOI'), 'title': t, 'year': y,
                    'journal': (it.get('container-title') or [''])[0],
                    'authors': '; '.join((a.get('family') or '') + ' ' + (a.get('given') or '') for a in (it.get('author') or []))[:120],
                    'vol': it.get('volume'), 'issue': it.get('issue'), 'page': it.get('page'),
                    'score': round(sim(title, t), 3)})
    out.sort(key=lambda x: -x['score'])
    return out

def dc_title(title, rows=10):
    u = 'https://api.datacite.org/dois?page[size]=%d&query=%s' % (rows, urllib.parse.quote(title))
    d = get(u)
    if '__err__' in d: return []
    out = []
    for it in d.get('data', []):
        a = it['attributes']
        t = ((a.get('titles') or [{}])[0]).get('title') or ''
        ct = (a.get('container') or {}).get('title') or ''
        out.append({'doi': a.get('doi'), 'title': t, 'year': a.get('publicationYear'),
                    'journal': ct,
                    'authors': '; '.join(c.get('name', '') for c in (a.get('creators') or []))[:120],
                    'score': round(sim(title, t), 3), 'src': 'datacite'})
    out.sort(key=lambda x: -x['score'])
    return out

def zenodo(title, rows=20):
    u = 'https://zenodo.org/api/records?size=%d&q=%s' % (rows, urllib.parse.quote('"%s"' % title))
    d = get(u)
    if '__err__' in d or 'hits' not in d: return []
    out = []
    for h in d['hits']['hits']:
        md = h.get('metadata', {})
        t = md.get('title') or ''
        out.append({'doi': md.get('doi') or h.get('doi'), 'title': t,
                    'year': (md.get('publication_date') or '')[:4],
                    'journal': (md.get('journal') or {}) if isinstance(md.get('journal'), str) else '',
                    'authors': '; '.join(c.get('name', '') for c in (md.get('creators') or []))[:120],
                    'score': round(sim(title, t), 3), 'src': 'zenodo'})
    out.sort(key=lambda x: -x['score'])
    return out

if __name__ == '__main__':
    need = []
    for line in io.open('work/need_doi.tsv', encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        need.append({'seq': p[0], 'year': p[1], 'issns': [x for x in (p[2] or '').split(',') if x],
                     'journal': p[3], 'title': p[4], 'src': p[5]})
    res = {}
    for r in need:
        cands = []
        for i in r['issns']:
            cands += cr_issn(i, r['title'], r['year'])
        c2 = dc_title(r['title'])
        cands += c2
        if 'Quint' in r['journal'] or r['seq'] in ('82',):
            cands += zenodo(r['title'])
        # dedupe by doi
        seen = {}
        for c in cands:
            k = (c['doi'] or '').lower()
            if not k: continue
            if k not in seen or c['score'] > seen[k]['score']:
                seen[k] = c
        cl = sorted(seen.values(), key=lambda x: -x['score'])[:6]
        res[r['seq']] = {'meta': r, 'cands': cl}
        best = cl[0] if cl else None
        print('=== seq %s | %s | %s' % (r['seq'], r['year'], r['title'][:70]))
        print('    J: %s | IS: %s' % (r['journal'][:50], ','.join(r['issns'])))
        for c in cl[:4]:
            print('     %.2f %-42s %-5s %-26s %s' % (c['score'], c['doi'], c['year'], (c['journal'] or '')[:26], (c['title'] or '')[:60]))
        sys.stdout.flush()
    json.dump(res, io.open('work/find_doi.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE', len(res))
