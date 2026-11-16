# -*- coding: utf-8 -*-
import urllib.request, urllib.error, ssl, re, io, json, time, html, unicodedata
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
HDR = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}

def get(u, t=40):
    req = urllib.request.Request(u, headers=HDR)
    return urllib.request.urlopen(req, timeout=t, context=ctx).read().decode('utf-8','ignore')

def unesc(s):
    for _ in range(2):
        s2 = html.unescape(s)
        if s2 == s: break
        s = s2
    return s

issues = sorted(set(re.findall(r'issue/view/(\d+)', get('https://www.rahl.ar/index.php/rahl/issue/archive'))), key=int)
print('issues:', len(issues))
items = []
for n in issues:
    try:
        h = get('https://www.rahl.ar/index.php/rahl/issue/view/%s' % n)
    except Exception as e:
        print('issue', n, 'ERR', str(e)[:50]); continue
    for m in re.finditer(r'<a[^>]+href="(https://www\.rahl\.ar/index\.php/rahl/article/view/\d+)"[^>]*>(.*?)</a>', h, re.S):
        url = m.group(1)
        txt = unesc(re.sub(r'<[^>]+>', ' ', m.group(2)))
        txt = re.sub(r'\s+', ' ', txt).strip()
        if len(txt) > 8:
            items.append({'issue': n, 'url': url, 'title': txt})
    time.sleep(0.3)
# dedupe by (url,title)
seen=set(); out=[]
for it in items:
    k=(it['url'], it['title'])
    if k in seen: continue
    seen.add(k); out.append(it)
json.dump(out, io.open('work/rahl_issues.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('items:', len(out))
for it in out[:6]: print('  ', it['issue'], it['url'], '|', it['title'][:80])
