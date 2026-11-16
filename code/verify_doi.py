# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, urllib.error, json, ssl, time, sys

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36'

def fetch(u, method='GET', timeout=35, tries=4):
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA}, method=method)
            r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return r.status, r.geturl(), r.read()
        except urllib.error.HTTPError as e:
            return e.code, u, b''
        except Exception as e:
            last = str(e)[:60]; time.sleep(2 + i * 2)
    return None, last, b''

def cr(doi):
    s, u, b = fetch('https://api.crossref.org/works/' + urllib.parse.quote(doi))
    if s == 200:
        try:
            d = json.loads(b.decode())['message']
            return 'CR-OK  ' + (d.get('title') or [''])[0][:66] + ' | ' + (d.get('container-title') or [''])[0][:24]
        except Exception:
            return 'CR-parse-err'
    return 'CR-%s' % s
def rslv(doi):
    s, u, b = fetch('https://doi.org/' + urllib.parse.quote(doi), method='HEAD')
    return 'RESOLVE-%s %s' % (s, str(u)[:66])

for doi in ['10.34096/sys.n22.3046', '10.34096/sys.n24.3217', '10.34096/sys.n29.2807',
            '10.14483/16579089.4642', '10.34096/sys.n35.6936', '10.34096/sys.n33.5254',
            '10.19137/anclajes-2019-2323', '10.19137/els-2017-1414010', '10.5281/zenodo.14236147']:
    print('%-30s | %-52s | %s' % (doi, cr(doi), rslv(doi)))
    sys.stdout.flush()
