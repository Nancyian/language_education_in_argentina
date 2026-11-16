# -*- coding: utf-8 -*-
"""专家语料库多线程并发抓取，剩余条目补齐。"""
import io
import json
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_fulltext as R

WORK = R.WORK
LOCK = threading.Lock()


def job(lst, wid, done):
    out = {}
    for d in lst:
        no = d['no']
        u = d['url']
        tag = 'd%03d' % int(no)
        if done.get(no, {}).get('words'):
            continue
        try:
            if u.startswith('10.'):
                info = R.resolve_doi(u, tag)
            elif 'dialnet.unirioja.es' in u:
                m = re.search(r'codigo=(\d+)', u)
                info = R.grab('https://dialnet.unirioja.es/descarga/articulo/%s.pdf' % m.group(1),
                              tag, 'ft_exp', referer=u)
                if not info.get('words'):
                    info['landing'] = R.grab(u, tag + '_landing', 'ft_exp')
            else:
                info = R.grab(u, tag, 'ft_exp')
        except Exception as e:
            info = dict(error=repr(e)[:120])
        info.update(no=no, url=u, title=d['title'])
        out[no] = info
        with LOCK:
            print('w%d %s %s words=%s %s' % (wid, no, info.get('kind', '-'),
                                             info.get('words'), (info.get('error') or '')[:40]), flush=True)
        io.open(os.path.join(WORK, 'ft_exp_w%d.json' % wid), 'w', encoding='utf-8').write(
            json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main():
    lst = json.load(io.open(os.path.join(WORK, 'exp_list.json'), encoding='utf-8'))
    cur = json.load(io.open(os.path.join(WORK, 'ft_exp.json'), encoding='utf-8'))
    todo = [d for d in lst if not cur.get(d['no'], {}).get('words')]
    # 排除已知 404 的
    todo = [d for d in todo if d['no'] != '18']
    print('todo', len(todo))
    n = 4
    chunks = [todo[i::n] for i in range(n)]
    ths = [threading.Thread(target=job, args=(c, i, cur)) for i, c in enumerate(chunks)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()


if __name__ == '__main__':
    main()
