# -*- coding: utf-8 -*-
"""Harvest OJS OAI-PMH records for journals lacking DOIs -> get article URLs."""
import urllib.request, urllib.error, ssl, re, io, json, time, html, unicodedata
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

BASES = {
 'SignosELE': 'https://p3.usal.edu.ar/index.php/ele/oai',
 'RAES': 'https://revistas.untref.edu.ar/index.php/raes/oai',
 'Entramados': 'https://fh.mdp.edu.ar/revistas/index.php/entramados/oai',
 'LenguaHabla': 'http://erevistas.saber.ula.ve/index.php/lenguayhabla/oai',
 'Arg1': 'https://www.argonautas.unsl.edu.ar/ojs/index.php/revista/oai',
 'Arg2': 'https://www.argonautas.unsl.edu.ar/oai',
 'Arg3': 'http://www.argonautas.unsl.edu.ar/index.php/revista/oai',
 'Ianua': 'http://www.romaniaminor.net/ianua/oai',
 'EstInter': 'https://estudiosinterlinguisticos.com/oai',
 'RMIE': 'https://www.comie.org.mx/revista/v2018/rmie/index.php/nrmie/oai',
 'Pilquen': 'http://revele.uncoma.edu.ar/index.php/psicopedagogia_2/oai',
 'ALH': 'https://revistas.uva.es/index.php/alh/oai',
 'RACC': 'https://revistas.unc.edu.ar/index.php/racc/oai',
 'RLEComp': 'https://revistas.untref.edu.ar/index.php/recom/oai',
}

def get(u, t=35):
    req = urllib.request.Request(u, headers={'User-Agent':'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=t, context=ctx).read().decode('utf-8','ignore')

def unesc(s):
    for _ in range(3):
        s2 = html.unescape(s)
        if s2 == s: break
        s = s2
    return s

out = {}
for name, base in BASES.items():
    try:
        ident = get(base + '?verb=Identify')
        if 'OAI-PMH' not in ident:
            print('%-12s no-OAI' % name); continue
        allx = ''
        url = base + '?verb=ListRecords&metadataPrefix=oai_dc'
        for i in range(15):
            h = get(url); allx += h
            m = re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>', h)
            if not m: break
            url = base + '?verb=ListRecords&resumptionToken=' + m.group(1)
            time.sleep(0.6)
        recs = re.findall(r'<record>(.*?)</record>', allx, re.S)
        items = []
        for r in recs:
            t = re.search(r'<dc:title[^>]*>(.*?)</dc:title>', r, re.S)
            ids = re.findall(r'<dc:identifier>(.*?)</dc:identifier>', r)
            cr = re.findall(r'<dc:creator>(.*?)</dc:creator>', r)
            dt = re.findall(r'<dc:date>(.*?)</dc:date>', r)
            items.append({'title': unesc(t.group(1)).strip() if t else '',
                          'url': ids[0] if ids else '',
                          'ids': ids, 'creators': [unesc(c).strip() for c in cr],
                          'date': dt[0] if dt else ''})
        out[name] = items
        ndoi = sum(1 for it in items if any('doi' in i.lower() for i in it['ids']))
        print('%-12s records=%-4d withDOIid=%d' % (name, len(items), ndoi))
    except Exception as e:
        print('%-12s ERR %s' % (name, str(e)[:60]))

json.dump(out, io.open('work/oai_journals.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved')
