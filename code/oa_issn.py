# -*- coding: utf-8 -*-
import urllib.request, urllib.error, urllib.parse, json, ssl, io, os, time, re, unicodedata
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'MetadataEnrichment/1.0 (mailto:researcher@example.org)','Accept':'application/json'}

ISSUES = {
 'Anuario de Lingüística Hispánica':['0213-053X'],
 'Argonautas':['1853-9092'],
 'Entramados':['2422-6459'],
 'Estudios Interlingüísticos':['2340-9274'],
 'Ianua':['1616-413X'],
 'Lengua y Habla':['2244-811X'],
 'Quintu Quimun':['2591-541X'],
 'RAHL':['1852-1495'],
 'RAES':['1852-8171'],
 'RLEComp':['1853-3744'],
 'Signos ELE':['1851-4863'],
 'Pilquen':['1851-3115'],
 'RMIE':['1405-6666'],
 'RMIE2':['2594-2439'],
 'RLEIncl':['0718-5480','0718-7378'],
}

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=50, context=ctx))
        except Exception as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (404,):
                return {'_err':'404'}
            time.sleep(2+i*3)

for name, issns in ISSUES.items():
    for issn in issns:
        url = ('https://api.openalex.org/works?per-page=200&mailto=researcher@example.org'
               '&filter=primary_location.source.issn:%s&select=doi,title,publication_year,authorships,primary_location' % issn)
        d = get(url)
        if not d or d.get('_err'):
            print('%-28s %-10s ERR' % (name, issn)); continue
        cnt = d.get('meta',{}).get('count')
        print('%-28s %-10s count=%s' % (name, issn, cnt))
        out=[]
        for w in d.get('results',[]):
            out.append({
              'doi': (w.get('doi') or '').replace('https://doi.org/',''),
              'title': w.get('title'),
              'year': w.get('publication_year'),
              'authors': [a.get('author',{}).get('display_name') for a in (w.get('authorships') or [])],
              'source': ((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
            })
        os.makedirs('work/oaissn', exist_ok=True)
        json.dump(out, io.open('work/oaissn/%s.json' % issn.replace('-',''), 'w', encoding='utf-8'), ensure_ascii=False)
        for o in out[:60]:
            print('    ', o['doi'] or '-', '|', o['year'], '|', (o['title'] or '')[:70])
        time.sleep(1)
