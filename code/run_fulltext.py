# -*- coding: utf-8 -*-
"""按清单抓取全文并统计词数。用法：
  python run_fulltext.py off|exp
"""
import io
import json
import os
import re
import subprocess
import sys
import time

import fitz
import trafilatura

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
TOK = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, 'work')


def curl(url, out, timeout=75, tls12=True, referer=None):
    cmd = ['curl', '-sSL', '-k', '--ssl-no-revoke', '--compressed',
           '-A', UA, '-H', 'Accept-Language: es-ES,es;q=0.9,en;q=0.8',
           '-o', out, '--max-time', str(timeout),
           '-w', '%{http_code}\t%{content_type}\t%{url_effective}']
    if tls12:
        cmd += ['--tls-max', '1.2']
    if referer:
        cmd += ['-e', referer]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    m = (p.stdout or '').strip().split('\t')
    return (m[0] if m else '000',
            m[1] if len(m) > 1 else '',
            m[2] if len(m) > 2 else url)


def is_pdf(path):
    try:
        with open(path, 'rb') as f:
            return f.read(5) == b'%PDF-'
    except OSError:
        return False


def pdf_text(path):
    d = fitz.open(path)
    txt = '\n'.join(p.get_text() for p in d)
    n = d.page_count
    d.close()
    return txt, n


def html_text(path):
    raw = io.open(path, 'r', encoding='utf-8', errors='ignore').read()
    t = trafilatura.extract(raw, include_comments=False, include_tables=True,
                            include_formatting=False, favor_recall=True)
    return t or ''


def grab(url, tag, sub, referer=None, timeout=75, tries=4):
    d = os.path.join(WORK, sub)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, tag + '.part')
    code = ct = '000'
    final = url
    for i in range(tries):
        code, ct, final = curl(url, tmp, timeout=timeout, tls12=(i % 2 == 0), referer=referer)
        if code != '000' and os.path.exists(tmp) and os.path.getsize(tmp) >= 400:
            break
        time.sleep(1.5 + i)
    info = dict(final=final, http=code, ctype=ct)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 400:
        info['error'] = 'http=%s size=%s' % (code, os.path.getsize(tmp) if os.path.exists(tmp) else 0)
        return info
    if is_pdf(tmp):
        txt, pages = pdf_text(tmp)
        os.replace(tmp, os.path.join(d, tag + '.pdf'))
        info.update(kind='pdf', pages=pages)
    else:
        txt = html_text(tmp)
        os.replace(tmp, os.path.join(d, tag + '.html'))
        info.update(kind='html', raw_bytes=os.path.getsize(os.path.join(d, tag + '.html')))
    if 'sobrepasado los l' in txt or 'límites de acceso' in txt:
        info['error'] = 'ratelimit'
        info['chars'] = len(txt)
        return info
    info['chars'] = len(txt)
    info['words'] = len(TOK.findall(txt))
    io.open(os.path.join(d, tag + '.txt'), 'w', encoding='utf-8').write(txt)
    return info


def find_pdf(html, base):
    """从 OJS/期刊落地页找 PDF 链接"""
    pats = [r'(?:href|content)="([^"]*article/download/[^"]+)"',
            r'(?:href|content)="([^"]*/article/view/[^"]*/[^"]*\d+[^"]*)"',
            r'href="([^"]*\.pdf[^"]*)"']
    out = []
    for p in pats:
        for m in re.findall(p, html):
            u = m if m.startswith('http') else None
            if u and u not in out:
                out.append(u)
    return out


def resolve_doi(doi, tag):
    """doi -> pdf/html 文本"""
    info = grab('https://doi.org/' + doi, tag, 'ft_exp')
    if info.get('kind') == 'pdf' or info.get('error'):
        return info
    # 落地页：找 PDF
    hpath = os.path.join(WORK, 'ft_exp', tag + '.html')
    html = io.open(hpath, 'r', encoding='utf-8', errors='ignore').read()
    links = find_pdf(html, info['final'])
    m = re.search(r'/article/view/(\d+)', info['final'])
    if m:
        links.insert(0, info['final'].rsplit('/view/', 1)[0] +
                     '/article/download/%s/%s' % (m.group(1), m.group(1)))
    for u in links[:4]:
        i2 = grab(u, tag, 'ft_exp', referer=info['final'])
        if i2.get('kind') == 'pdf':
            i2['via'] = 'pdf-link'
            i2['words'] = i2.get('words', 0)
            return i2
    info['landing_words'] = info.get('words', 0)
    info['error'] = info.get('error', 'no-pdf-link')
    return info


def main():
    mode = sys.argv[1]
    lst = json.load(io.open(os.path.join(WORK, 'off_list.json' if mode == 'off' else 'exp_list.json'),
                            encoding='utf-8'))
    out_path = os.path.join(WORK, 'ft_%s.json' % mode)
    res = json.load(io.open(out_path, encoding='utf-8')) if os.path.exists(out_path) else {}
    host_fail = {}
    for d in lst:
        no = d['no']
        if no in res and res[no].get('words'):
            continue
        u = d['url']
        tag = 'd%03d' % int(no)
        host = u.split('/')[2] if '://' in u else u[:20]
        if host_fail.get(host, 0) >= 3:
            res[no] = dict(no=no, url=u, title=d['title'], error='host-unreachable(%s)' % host)
            continue
        print(no, u[:80], flush=True)
        try:
            if u.startswith('10.'):
                info = resolve_doi(u, tag)
            elif 'dialnet.unirioja.es' in u:
                m = re.search(r'codigo=(\d+)', u)
                pdf = 'https://dialnet.unirioja.es/descarga/articulo/%s.pdf' % m.group(1)
                info = grab(pdf, tag, 'ft_' + mode, referer=u)
                if info.get('error'):
                    info2 = grab(u, tag + '_landing', 'ft_' + mode)
                    info['landing'] = info2
            else:
                info = grab(u, tag, 'ft_' + mode)
        except Exception as e:
            info = dict(error=repr(e)[:120])
        if info.get('error') == 'ratelimit':
            print('   ratelimit -> sleep 150s', flush=True)
            time.sleep(150)
            try:
                if 'dialnet' in u:
                    m = re.search(r'codigo=(\d+)', u)
                    info = grab('https://dialnet.unirioja.es/descarga/articulo/%s.pdf' % m.group(1),
                                tag, 'ft_' + mode, referer=u)
                else:
                    info = grab(u, tag, 'ft_' + mode)
            except Exception as e:
                info = dict(error=repr(e)[:100])
        info['no'] = no
        info['url'] = u
        info['title'] = d['title']
        res[no] = info
        if not info.get('words'):
            host_fail[host] = host_fail.get(host, 0) + 1
        ok = 'OK ' if info.get('words') else 'ERR'
        print('   %s %-5s %6s words  %s' % (ok, info.get('kind', '-'), info.get('words', '-'),
                                            info.get('error', '')), flush=True)
        json.dump(res, io.open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(10)
    ok = [v for v in res.values() if v.get('words')]
    print('done %d/%d  total %d words' % (len(ok), len(res), sum(v['words'] for v in ok)))


if __name__ == '__main__':
    main()
