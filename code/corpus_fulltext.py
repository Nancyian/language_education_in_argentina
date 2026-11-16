# -*- coding: utf-8 -*-
"""语料全文抓取与词数统计（官方 71 + 专家 66）

curl 使用 schannel + TLS1.2 上限，绕过 dialnet 等站点的 TLS1.3 握手问题。
HTML 正文用 trafilatura 抽取；PDF 用 PyMuPDF 抽取。
"""
import io
import json
import os
import re
import subprocess
import sys

import fitz
import trafilatura

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
TOK = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def curl(url, out, timeout=70, referer=None):
    cmd = ['curl', '-sSL', '-k', '--tls-max', '1.2', '--compressed',
           '-A', UA, '-H', 'Accept-Language: es-ES,es;q=0.9,en;q=0.8',
           '-o', out, '--max-time', str(timeout),
           '-w', '%{http_code}\t%{content_type}\t%{url_effective}']
    if referer:
        cmd += ['-e', referer]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    meta = (p.stdout or '').strip().split('\t')
    code = meta[0] if meta else '000'
    ct = meta[1] if len(meta) > 1 else ''
    final = meta[2] if len(meta) > 2 else url
    return code, ct, final


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
    txt = trafilatura.extract(raw, include_comments=False, include_tables=True,
                              include_formatting=False, favor_recall=True)
    return txt or ''


def wc(txt):
    return len(TOK.findall(txt))


def fetch(url, workdir, tag, timeout=70, referer=None):
    """下载并抽取正文，返回 dict"""
    os.makedirs(workdir, exist_ok=True)
    tmp = os.path.join(workdir, tag + '.bin')
    code, ct, final = curl(url, tmp, timeout=timeout, referer=referer)
    info = dict(url=url, final=final, http=code, ctype=ct)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 500:
        info['error'] = 'empty/http=%s' % code
        return info
    if is_pdf(tmp):
        txt, pages = pdf_text(tmp)
        info.update(kind='pdf', pages=pages)
        os.replace(tmp, os.path.join(workdir, tag + '.pdf'))
    else:
        txt = html_text(tmp)
        info.update(kind='html')
        if len(txt) < 200:
            info['warn'] = 'short-html'
        os.replace(tmp, os.path.join(workdir, tag + '.html'))
    info['chars'] = len(txt)
    info['words'] = wc(txt)
    info['text'] = txt
    return info


if __name__ == '__main__':
    r = fetch(sys.argv[1], os.path.join(ROOT, 'work', '_probe'), 'probe')
    print({k: v for k, v in r.items() if k != 'text'})
    print((r.get('text') or '')[:500])
