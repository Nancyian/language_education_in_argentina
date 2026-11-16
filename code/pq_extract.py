# -*- coding: utf-8 -*-
"""从 ProQuest 结果页抽取：标题/作者/期刊或学位论文/年份。单行 eval。"""
import io, json, os, re, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

AB = r"C:/Users/Administrator/.workbuddy/binaries/node/workspace/node_modules/.bin/agent-browser.cmd"

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


def run(args, timeout=110):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    p = subprocess.run([AB] + args, capture_output=True, text=True, timeout=timeout, env=env)
    return p.stdout.strip(), p.stderr.strip()


def main():
    page_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out, err = run(['eval', JS])
    try:
        raw = json.loads(out)          # 外层 JSON 字符串 -> 内层 JSON 文本
        items = json.loads(raw)
    except Exception as e:
        print('PARSE FAIL', e, out[:150])
        sys.exit(1)
    io.open('work/pq_page%d.json' % page_no, 'w', encoding='utf-8').write(
        json.dumps(items, ensure_ascii=False, indent=1))
    print('page%d items=%d' % (page_no, len(items)))
    for it in items[:2]:
        print(' -', it['fmt'][:60], '|', it['title'][:60])


if __name__ == '__main__':
    main()
