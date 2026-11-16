# -*- coding: utf-8 -*-
"""ProQuest 高级检索填表提交（修正选择器：textarea[name=queryTermField*] / select[name=fieldsSelect*]）"""
import os, subprocess, sys, time, json
sys.stdout.reconfigure(encoding='utf-8')

AB = r"C:/Users/Administrator/.workbuddy/binaries/node/workspace/node_modules/.bin/agent-browser.cmd"

NOFT = ('"language policy" OR "language planning" OR "politica linguistica" OR '
        '"politicas linguisticas" OR "lenguas indigenas" OR "indigenous language*" OR '
        '"language rights" OR "lenguas en contacto" OR "language contact" OR bilingual* OR '
        'multilingual* OR pluriling* OR "language teaching" OR "foreign language" OR '
        '"second language" OR "lengua extranjera" OR "segunda lengua" OR '
        '"linguistic landscape" OR "paisaje linguistico" OR "language ideology" OR '
        '"language education"')

TITLE = ('Argentina OR Argentine OR "Buenos Aires" OR Patagonia OR rioplatense OR '
         '"Rio de la Plata" OR Mercosur OR mapuche OR guarani OR quechua OR qom OR wichi OR toba')


def run(args, timeout=180):
    env = dict(os.environ)
    env['AGENT_BROWSER_PROXY'] = 'http://127.0.0.1:58354'
    try:
        p = subprocess.run([AB] + args, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return '', 'TIMEOUT'
    out = (p.stdout or b'').decode('utf-8', 'replace').strip()
    err = (p.stderr or b'').decode('utf-8', 'replace').strip()
    return out, err


FILL = """
(function(){
  function fire(el){
    ['input','change','keyup','blur'].forEach(function(t){
      el.dispatchEvent(new Event(t,{bubbles:true}));
    });
  }
  var t0 = document.querySelector('textarea[name="queryTermField"]');
  var t1 = document.querySelector('textarea[name="queryTermField_0"]');
  var s0 = document.querySelector('select[name="fieldsSelect"]');
  var s1 = document.querySelector('select[name="fieldsSelect_0"]');
  if(!t0 || !t1) return JSON.stringify({ok:false,msg:'no textarea'});
  if(s0){ s0.value='NOFT'; fire(s0); }
  if(s1){ s1.value='TITLE'; fire(s1); }
  t0.value = %s; fire(t0);
  t1.value = %s; fire(t1);
  // 提交按钮
  var btn = null;
  [].slice.call(document.querySelectorAll('button')).forEach(function(b){
    var x=(b.innerText||'').trim();
    if(!btn && (x==='检索' || x==='Search') && b.offsetParent) btn=b;
  });
  if(btn){ btn.click(); return JSON.stringify({ok:true,via:'btn',f0:s0?s0.value:'',f1:s1?s1.value:''}); }
  var f = t0.closest('form');
  if(f){ f.submit(); return JSON.stringify({ok:true,via:'form'}); }
  return JSON.stringify({ok:false,msg:'no submit'});
})()
""" % (json.dumps(NOFT), json.dumps(TITLE))


def main():
    out, err = run(['get', 'url'], timeout=60)
    print('url:', out)

    out, err = run(['eval', FILL], timeout=120)
    print('fill:', out[:300] or err[:150])
    if '"ok":false' in out:
        sys.exit(1)

    time.sleep(14)
    out, _ = run(['get', 'url'], timeout=60)
    print('after url:', out)
    out, _ = run(['eval', 'document.querySelectorAll("li.resultItem").length+" items | "+((document.querySelector("h1")||{}).innerText||"")'], timeout=90)
    print('count:', out[:200])


if __name__ == '__main__':
    main()
