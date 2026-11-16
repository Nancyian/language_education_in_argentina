# -*- coding: utf-8 -*-
"""ProQuest 全页抓取：会话内逐页导航 + eval 抽取，带超时重试与断线自愈。
用法: python pq_crawl.py 1 2 3 4 5 6 7 8
"""
import io, json, os, re, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

AB = r"C:/Users/Administrator/.workbuddy/binaries/node/workspace/node_modules/.bin/agent-browser.cmd"
SID = 'B1552B95A5DD4902PQ'
BASE = "https://www.proquest.com/results/%s/%%d?accountid=10025" % SID
WORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/work'

JS = (
 "JSON.stringify([].slice.call(document.querySelectorAll('li.resultItem')).map(function(li){"
 "var a=li.querySelector('h3 a'); if(!a) return null;"
 "var title=a.textContent.trim();"
 "var authors=[].slice.call(li.querySelectorAll('.truncatedAuthor,.scholUnivAuthors')).map(function(e){return e.textContent.trim()}).join('; ');"
 "var fmt=''; var f=li.querySelector('.jnlArticle')||li.querySelector('.dissertation')||li.querySelector('.dissertations');"
 "if(f) fmt=f.textContent.trim();"
 "var full=li.innerText.replace(/\\s+/g,' ');"
 "var sn=li.querySelector('.snippet'); var ab=sn?sn.textContent.trim():'';"
 "return {title:title, authors:authors.slice(0,300), fmt:fmt.slice(0,250), abs:ab.slice(0,600), full:full.slice(0,700)};"
 "}).filter(function(x){return x}))"
)


def raw(js, timeout=100):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    try:
        p = subprocess.run([AB, 'eval', js], capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None
    s = (p.stdout or b'').decode('utf-8', 'replace').strip()
    if not s or s.startswith('✗'):
        return None
    try:
        v = json.loads(s)
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
    except Exception:
        return None


def nav(url, timeout=130):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    try:
        subprocess.run([AB, 'open', url], capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False
    return True


def cur_url():
    return raw('location.href', timeout=60)


def grab(p):
    """返回 (items, ok)"""
    url = cur_url()
    if not isinstance(url, str) or '/results/' not in url:
        return None, 'notResults:%s' % str(url)[:60]
    items = raw(JS, timeout=110)
    if isinstance(items, list) and items:
        io.open(os.path.join(WORK, 'pq_page%d.json' % p), 'w', encoding='utf-8').write(
            json.dumps(items, ensure_ascii=False, indent=1))
        return len(items), 'ok'
    return None, 'emptyOrNull'


def main():
    pages = [int(x) for x in sys.argv[1:]] or list(range(1, 9))
    for p in pages:
        outfile = os.path.join(WORK, 'pq_page%d.json' % p)
        if os.path.exists(outfile) and os.path.getsize(outfile) > 2000:
            print('page%-2d SKIP exists (%d B)' % (p, os.path.getsize(outfile)))
            continue

        url = BASE % p
        ok = False
        for attempt in range(1, 4):
            nav(url, timeout=130)
            time.sleep(5)
            u = cur_url()
            if isinstance(u, str) and 'sessionexpired' in u:
                print('page%-2d attempt%d SESSION EXPIRED' % (p, attempt))
                return
            n, why = grab(p)
            if n:
                print('page%-2d OK items=%d (attempt %d)' % (p, n, attempt))
                ok = True
                break
            print('page%-2d attempt%d fail: %s' % (p, attempt, why))
            time.sleep(8)
        if not ok:
            print('page%-2d GIVE UP' % p)
        time.sleep(2)


if __name__ == '__main__':
    main()
