# -*- coding: utf-8 -*-
"""ProQuest 高级检索：Python 生成单行 JS -> eval 填表 -> 提交 -> 读结果数。
所有 JS 压成一行，避免 shell/heredoc 换行问题。"""
import os, re, subprocess, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

AB = r"C:/Users/Administrator/.workbuddy/binaries/node/workspace/node_modules/.bin/agent-browser.cmd"

Q1 = ('"language policy" OR "language planning" OR "politica linguistica" OR '
      '"politicas linguisticas" OR "lenguas indigenas" OR "indigenous language*" OR '
      '"language rights" OR "lenguas en contacto" OR "language contact" OR bilingual* OR '
      'multilingual* OR pluriling* OR "language teaching" OR "foreign language" OR '
      '"second language" OR "lengua extranjera" OR "segunda lengua" OR '
      '"linguistic landscape" OR "paisaje linguistico" OR "language ideology" OR '
      '"language education"')

Q2 = ('Argentina OR Argentine OR "Buenos Aires" OR Patagonia OR rioplatense OR '
      '"Rio de la Plata" OR Mercosur OR mapuche OR guarani OR quechua OR qom OR wichi OR toba')


def run(js_or_args, timeout=120, is_js=True):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    args = ['eval', js_or_args] if is_js else js_or_args
    try:
        p = subprocess.run([AB] + args, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    return (p.stdout or b'').decode('utf-8', 'replace').strip()


def unwrap(out):
    """eval 输出形如 "{\"a\":1}" -> 解析成对象"""
    if not out or out == 'TIMEOUT':
        return None
    try:
        v = json.loads(out)
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
    except Exception:
        return out


FILL_JS = (
    "(function(){"
    "var fire=function(el){['input','change','keyup','blur'].forEach(function(t){"
    "el.dispatchEvent(new Event(t,{bubbles:true}))})};"
    "var t0=document.querySelector('textarea[name=\"queryTermField\"]');"
    "var t1=document.querySelector('textarea[name=\"queryTermField_0\"]');"
    "var s0=document.querySelector('select[name=\"fieldsSelect\"]');"
    "var s1=document.querySelector('select[name=\"fieldsSelect_0\"]');"
    "if(!t0||!t1){return JSON.stringify({ok:0,msg:'noTextarea'})}"
    "if(s0){s0.value='noft';fire(s0)}"
    "if(s1){s1.value='title';fire(s1)}"
    "t0.value=" + json.dumps(Q1) + ";fire(t0);"
    "t1.value=" + json.dumps(Q2) + ";fire(t1);"
    "return JSON.stringify({ok:1,f0:s0?s0.value:'-',f1:s1?s1.value:'-',"
    "len0:t0.value.length,len1:t1.value.length})"
    "})()"
)

SUBMIT_JS = (
    "(function(){"
    "var btn=null;"
    "[].slice.call(document.querySelectorAll('button,input[type=submit]')).forEach(function(b){"
    "var x=(b.innerText||b.value||'').trim();"
    "if(!btn&&(x==='检索'||x==='Search')&&b.offsetParent){btn=b}});"
    "if(btn){btn.click();return 'clicked:'+(btn.innerText||'').trim()}"
    "var t=document.querySelector('textarea[name=\"queryTermField\"]');"
    "var f=t?t.closest('form'):null;"
    "if(f){f.submit();return 'formSubmit'}"
    "return 'noSubmit'})()"
)


def main():
    print('step1 fill')
    r = unwrap(run(FILL_JS))
    print('  ', r)
    if not isinstance(r, dict) or not r.get('ok'):
        return

    if '--no-submit' in sys.argv:
        return

    print('step2 submit')
    r = unwrap(run(SUBMIT_JS))
    print('  ', r)

    for i in range(6):
        time.sleep(5)
        u = unwrap(run('location.href'))
        n = unwrap(run('document.querySelectorAll("li.resultItem").length'))
        print('  [%ds] items=%s url=%s' % ((i + 1) * 5, n, str(u)[:110]))
        if isinstance(n, int) and n > 0:
            break


if __name__ == '__main__':
    main()
