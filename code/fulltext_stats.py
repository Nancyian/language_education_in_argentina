# -*- coding: utf-8 -*-
"""专家 16 篇 DOI 文献：从期刊 OJS/Zenodo 下载全文 PDF，抽取文本统计词数。
输出：work/fulltext/*.pdf、work/fulltext_stats.json
"""
import io, json, os, re, ssl, urllib.request, warnings
warnings.filterwarnings('ignore')
import fitz  # pymupdf

OUT = 'work/fulltext'
os.makedirs(OUT, exist_ok=True)
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'}
TOK = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")

DOIS = {
    4:  '10.48162/rev.5.133', 3:  '10.48162/rev.5.003', 56: '10.48162/rev.5.111',
    64: '10.48162/rev.5.122',
    27: '10.19137/anclajes-2019-2323', 30: '10.19137/anclajes-2020-2411',
    3 + 0: None,  # placeholder
}
DOIS = {k: v for k, v in {
    4: '10.48162/rev.5.133', 3: '10.48162/rev.5.003', 56: '10.48162/rev.5.111',
    64: '10.48162/rev.5.122', 27: '10.19137/anclajes-2019-2323',
    30: '10.19137/anclajes-2020-2411', 30 + 1: '10.19137/anclajes-2025-29211',
    29: '10.19137/els-2019-161608', 18: '10.34096/sys.n29.2807',
    28: '10.34096/sys.n35.6936', 57: '10.34096/sys.n45.14493',
    58: '10.34096/sys.n45.14570', 59: '10.34096/sys.n45.15621',
    38: '10.61203/2347-0658.v5.n1.14720', 40: '10.61203/2347-0658.v4.n0.12571',
    62: '10.5281/zenodo.14236148',
}.items() if v}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return r.read(), r.geturl(), r.headers.get('Content-Type', '')


def find_pdf_links(html):
    """OJS landing 页中的 PDF 下载链接，按优先级排序"""
    links = re.findall(r'(?:href|content)="([^"]*(?:/article/download/|/article/view/[^"]*download)[^"]*)"', html)
    links = [l if l.startswith('http') else None for l in links]
    return [l for l in links if l]


def pdf_words(path):
    d = fitz.open(path)
    txt = '\n'.join(p.get_text() for p in d)
    d.close()
    return len(TOK.findall(txt)), len(txt)


def fetch_doi(doi, no):
    """返回 (words, chars, src_url) 或抛异常"""
    data, final, ct = get('https://doi.org/' + doi)
    if b'%PDF' in data[:8] or 'pdf' in ct.lower():
        return data, final, 'pdf-direct'
    html = data.decode('utf-8', 'ignore')
    if 'zenodo' in final:
        rec = json.loads(get('https://zenodo.org/api/records/' + doi.rsplit('.', 1)[-1])[0])
        f = rec['files'][0]
        data, final, ct = get(f['links']['self'])
        return data, final, 'zenodo'
    cands = find_pdf_links(html)
    if not cands:
        # OJS 3 兜底：/view/<id> → /download/<id>/<id>
        m = re.search(r'/article/view/(\d+)', final)
        if m:
            cands = [final.rsplit('/view/', 1)[0] + '/article/download/%s/%s' % (m.group(1), m.group(1))]
    for c in cands[:4]:
        try:
            d2, f2, ct2 = get(c)
            if b'%PDF' in d2[:8] or 'pdf' in ct2.lower():
                return d2, f2, 'pdf-link'
            html2 = d2.decode('utf-8', 'ignore')
            for c3 in find_pdf_links(html2)[:2]:
                d3, f3, ct3 = get(c3)
                if b'%PDF' in d3[:8] or 'pdf' in ct3.lower():
                    return d3, f3, 'pdf-link2'
        except Exception:
            continue
    raise RuntimeError('no PDF found at ' + final)


def main():
    import openpyxl
    ws = openpyxl.load_workbook(r'C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/专家数据表_正式版(1).xlsx',
                                data_only=True)['Sheet2']
    titles = {}
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value is None:
            continue
        titles[ws.cell(r, 1).value] = str(ws.cell(r, 4).value or '')

    res = {}
    for no, doi in sorted(DOIS.items()):
        try:
            data, src, how = fetch_doi(doi, no)
            path = os.path.join(OUT, 'doc%02d.pdf' % no)
            io.open(path, 'wb').write(data)
            w, ch = pdf_words(path)
            res[str(no)] = dict(doi=doi, words=w, chars=ch, src=src, how=how, file=path)
            print('doc%02d %-32s %5d words %7d chars  %s' % (no, doi, w, ch, how), flush=True)
        except Exception as e:
            res[str(no)] = dict(doi=doi, error=repr(e)[:120])
            print('doc%02d %-32s FAIL %s' % (no, doi, repr(e)[:70]), flush=True)
    json.dump(res, io.open('work/fulltext_stats.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    ok = [v for v in res.values() if 'words' in v]
    print('ok %d/%d, total words %d' % (len(ok), len(res), sum(v['words'] for v in ok)))


if __name__ == '__main__':
    main()
