import urllib.request, urllib.parse, json, ssl, time, io, re, unicodedata

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'MetadataEnrichment/1.0'}

def g(u, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=45, context=ctx))
        except Exception as e:
            last = str(e)[:50]; time.sleep(1.5 + i * 2)
    return {'__err__': last}

# 1) which journals are in DOAJ
issns = ['2340-9274', '2422-6459', '1852-8171', '1616-413X', '1851-4863', '2244-811X',
         '1853-3744', '1853-9092', '2591-541X', '1852-1495', '1852-9615', '1668-4753',
         '1405-6666', '0718-7378', '1692-5777', '1989-9572', '1851-4669', '1657-9089',
         '2314-2189', '1851-3115', '2362-6194', '1697-4239', '1973-9370', '1852-4206', '1850-0153']
print('==== DOAJ journal lookup ====')
doaj_journals = {}
for i in issns:
    d = g('https://doaj.org/api/search/journals/issn:%s' % i)
    if '__err__' in d:
        print('%-12s ERR %s' % (i, d['__err__'])); continue
    n = d.get('total', 0)
    if n:
        r = d['results'][0]['bibjson']
        doaj_journals[i] = r.get('title')
        print('%-12s IN-DOAJ  %s' % (i, (r.get('title') or '')[:60]))
    else:
        print('%-12s not in DOAJ' % i)
    time.sleep(0.25)

json.dump(doaj_journals, io.open('work/doaj_journals.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n=== DOAJ journals:', len(doaj_journals), '===')
