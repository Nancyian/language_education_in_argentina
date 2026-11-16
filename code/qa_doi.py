# -*- coding: utf-8 -*-
import openpyxl, urllib.request, urllib.error, urllib.parse, json, ssl, time, io, sys
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36'
P = r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\dialnet_language_corpus_merged_整理_补全_DOI.xlsx'

def check(doi):
    for base in ['https://api.crossref.org/works/%s', 'https://api.datacite.org/dois/%s']:
        u = base % urllib.parse.quote(doi)
        for i in range(3):
            try:
                req = urllib.request.Request(u, headers={'User-Agent': UA})
                d = json.load(urllib.request.urlopen(req, timeout=25, context=ctx))
                if 'message' in d:
                    m = d['message']
                    return (doi, 'OK-CR', (m.get('title') or [''])[0][:70], (m.get('container-title') or [''])[0][:26],
                            (((m.get('issued') or {}).get('date-parts') or [[None]])[0] or [None])[0])
                a = d['data']['attributes']
                return (doi, 'OK-DC', ((a.get('titles') or [{}])[0]).get('title', '')[:70],
                        (a.get('container') or {}).get('title') or '', a.get('publicationYear'))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                time.sleep(1.5)
            except Exception:
                time.sleep(1.5)
    return (doi, 'NOT-FOUND', '', '', '')

wb = openpyxl.load_workbook(P)
ws = wb['Sheet2']
dois = []
for r in range(2, 101):
    v = str(ws.cell(row=r, column=2).value or '')
    if v.startswith('10.'):
        dois.append((r, str(ws.cell(row=r, column=1).value), v))
print('validating', len(dois))
res = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for out in ex.map(lambda x: check(x[2]), dois):
        res.append(out)

bad = []
for (r, seq, doi), out in zip(dois, res):
    if out[1] != 'OK-CR' and out[1] != 'OK-DC':
        bad.append((r, seq, doi))
print('OK:', len(res) - len(bad), '/', len(res))
print('UNRESOLVED:')
for b in bad:
    print('   row%-4d seq=%-3s %s' % b)
print()
print('samples:')
for (r, seq, doi), out in list(zip(dois, res))[:12]:
    print('   seq %-3s %-42s %-7s %s' % (seq, doi, out[1], out[2][:50]))
