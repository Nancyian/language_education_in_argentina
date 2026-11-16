# -*- coding: utf-8 -*-
"""一次性抓 ProQuest 多页：直接 open 目标页 -> 等结果 -> eval 抽 DOM。
用法: python pq_pages.py 3 4 5 6 7 8
"""
import io, json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

AB = r"C:/Users/Administrator/.workbuddy/binaries/node/workspace/node_modules/.bin/agent-browser.cmd"
BASE = "https://www.proquest.com/results/C14690B81C40456DPQ/%d?accountid=10025"

JS = (
 "JSON.stringify([].slice.call(document.querySelectorAll('li.resultItem')).map(function(li){"
 "var a=li.querySelector('h3 a'); if(!a) return null;"
 "var title=a.textContent.trim();"
 "var authors=[].slice.call(li.querySelectorAll('.truncatedAuthor,.scholUnivAuthors')).map(function(e){return e.textContent.trim()}).join('; ');"
 "var fmt=''; var f=li.querySelector('.jnlArticle')||li.querySelector('.dissertation')||li.querySelector('.dissertations');"
 "if(f) fmt=f.textContent.trim();"
 "var sn=li.querySelector('.snippet'); var ab=sn?sn.textContent.trim():'';"
 "return {title:title, authors:authors.slice(0,300), fmt:fmt.slice(0,250), abs:ab.slice(0,600)};"
 "}).filter(function(x){return x}))"
)


def run(args, timeout=200):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    try:
        p = subprocess.run([AB] + args, capture_output=True, text=True, timeout=timeout, env=env)
        return p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return '', 'TIMEOUT'


def grab(page_no):
    out, err = run(['open', BASE % page_no], timeout=240)
    if 'TIMEOUT' in err or not out:
        print('  open failed', err[:60])
        return 0
    time.sleep(4)
    out, err = run(['eval', JS], timeout=180)
    if not out:
        print('  eval failed', err[:60])
        return 0
    try:
        items = json.loads(json.loads(out))
    except Exception as e:
        print('  parse fail', e, out[:80])
        return 0
    if not items:
        return 0
    io.open('work/pq_page%d.json' % page_no, 'w', encoding='utf-8').write(
        json.dumps(items, ensure_ascii=False, indent=1))
    print('  page%d items=%d  e.g. %s' % (page_no, len(items), items[0]['title'][:50]))
    return len(items)


if __name__ == '__main__':
    pages = [int(x) for x in sys.argv[1:]] or [3]
    for p in pages:
        print('-> page', p)
        n = grab(p)
        if n == 0:
            print('  retry once after 15s')
            time.sleep(15)
            grab(p)
        time.sleep(3)
