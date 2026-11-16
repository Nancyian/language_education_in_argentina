# -*- coding: utf-8 -*-
"""用 OpenAlex 补齐 I 列空缺摘要。输入 work/final_argjr.json，就地更新 abs 字段。"""
import io, json, os, sys, time
import urllib.request, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')
UA = {'User-Agent': 'corpus-builder/1.0 (mailto:research@example.org)'}


def get(url, timeout=45):
    proxy = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:58354', 'https': 'http://127.0.0.1:58354'})
    op = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers=UA)
    with op.open(req, timeout=timeout) as f:
        return json.load(f)


def rebuild(inv):
    if not inv:
        return ''
    pos = {}
    for w, ps in inv.items():
        for p in ps:
            pos[p] = w
    return ' '.join(pos[i] for i in sorted(pos))[:1800]


def main():
    path = os.path.join(WORK, 'final_argjr.json')
    rows = json.load(io.open(path, encoding='utf-8'))
    todo = [r for r in rows
            if not (r.get('abs') or '').strip()
            and 'doi.org/' in str(r.get('url', ''))]
    print('to fill:', len(todo), '/', len(rows))

    ok = 0
    for i, r in enumerate(todo):
        doi = r['url'].split('doi.org/')[-1]
        try:
            d = get('https://api.openalex.org/works/doi:%s?select=abstract_inverted_index' %
                    urllib.parse.quote(doi))
            ab = rebuild(d.get('abstract_inverted_index'))
            if ab:
                r['abs'] = ab
                ok += 1
        except Exception as e:
            if '429' in str(e):
                print('rate limited at', i, '- pausing 60s')
                time.sleep(60)
                continue
        if (i + 1) % 20 == 0:
            print('  %d/%d ok=%d' % (i + 1, len(todo), ok))
            io.open(path, 'w', encoding='utf-8').write(
                json.dumps(rows, ensure_ascii=False, indent=1))
        time.sleep(0.35)

    io.open(path, 'w', encoding='utf-8').write(
        json.dumps(rows, ensure_ascii=False, indent=1))

    still = [r for r in rows if not (r.get('abs') or '').strip()]
    print('filled:', ok, '| still empty:', len(still))
    from collections import Counter
    print('still by venue:', Counter(r['venue'] for r in still).most_common(8))


if __name__ == '__main__':
    main()
