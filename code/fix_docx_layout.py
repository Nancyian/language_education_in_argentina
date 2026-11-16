# -*- coding: utf-8 -*-
"""交付前的两处确定性修补（只改版式属性，不动文字、表格数据与图片）。

1. 末节 sectPr 缺 pgSz/pgMar —— 引擎只给封面/目录两节写全页面设置，正文所在末节
   只剩 type/pgNumType/footerReference，Word 会按默认信纸打开。按首节参数补齐 A4。
2. 表格跨页 —— 给每张表加「标题行重复（tblHeader）」与「行内禁止断页（cantSplit）」，
   长表跨页时表头自动重现、单元格不被拦腰截断。
"""
import copy, re, shutil, sys, zipfile
from lxml import etree

DOC = sys.argv[1] if len(sys.argv) > 1 else \
    r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\专家话语_LDA主题建模_图表集.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
PG = ('<w:pgSz w:w="11906" w:h="16838"/>'
      '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800" '
      'w:header="851" w:footer="992" w:gutter="0"/>')

zin = zipfile.ZipFile(DOC)
items = [(i, zin.read(i.filename)) for i in zin.infolist()]
zin.close()

# --- 图片 rId -> 真实宽高比（宽/高），供第 3 项修补使用 ---
import io
from PIL import Image
_rels = dict((i.filename, d) for i, d in items)
NAT = {}
_rmap = {}
_relxml = _rels.get('word/_rels/document.xml.rels', b'').decode('utf-8', 'ignore')
for m in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', _relxml):
    _rmap[m.group(1)] = m.group(2).lstrip('/')
for rid, tgt in _rmap.items():
    key = tgt if tgt.startswith('word/') else 'word/' + tgt
    raw = _rels.get(key)
    if not raw:
        continue
    try:
        im = Image.open(io.BytesIO(raw))
        NAT[rid] = im.size[0] / float(im.size[1])
    except Exception:
        pass

stat = {'sect': 0, 'tbl': 0, 'row': 0}
out = []
for info, data in items:
    if info.filename == 'word/document.xml':
        s = data.decode('utf-8')

        # --- 1) 末节页面设置 ---
        start = s.rfind('<w:sectPr')
        end = s.find('</w:sectPr>', start)
        seg = s[start:end]
        if '<w:pgSz' not in seg:
            m = re.search(r'<w:type [^/]*/>', seg)
            seg2 = (seg[:m.end()] + PG + seg[m.end():]) if m else \
                seg.replace('<w:sectPr>', '<w:sectPr>' + PG, 1)
            s = s[:start] + seg2 + s[end:]
            stat['sect'] += 1

        # --- 2) 表格跨页处理（lxml，精确到 trPr） ---
        # --- 3) 图片宽度归一：Word 按 DPI 自行缩放，且引擎写回的纵横比不可靠 ---
        # 按图片文件的真实像素比重算：宽统一 13.6cm（版心 14.66cm），高超过 14.6cm 时按高压回
        root = etree.fromstring(s.encode('utf-8'))
        WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
        A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
        R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        TARGET = int(13.6 * 360000)
        HMAX = int(float(__import__('os').environ.get('HMAX', '12.6')) * 360000)
        for ext in root.iter('{%s}extent' % WP):
            blip = ext.getparent().find('.//{%s}blip' % A)
            rid = blip.get('{%s}embed' % R) if blip is not None else None
            nat = NAT.get(rid)
            if not nat:
                continue
            ar = nat                                    # 宽 / 高
            w, h = TARGET, int(TARGET / ar)
            if h > HMAX:
                h = HMAX
                w = int(HMAX * ar)
            ext.set('cx', str(w)); ext.set('cy', str(h))
            for a in ext.getparent().iter('{%s}ext' % A):
                a.set('cx', str(w)); a.set('cy', str(h))
            stat['img'] = stat.get('img', 0) + 1
        # --- 4) 图片段落：图与图注拆成两段并居中，否则图文同段会让整行超宽、图被推向左边距 ---
        for p in list(root.iter('{%s}p' % W)):
            dw = p.find('.//{%s}drawing' % W)
            if dw is None:
                continue
            pPr = p.find('{%s}pPr' % W)
            if pPr is None:
                pPr = etree.Element('{%s}pPr' % W)
                p.insert(0, pPr)
            jc = pPr.find('{%s}jc' % W)
            if jc is None:
                jc = etree.SubElement(pPr, '{%s}jc' % W)
            jc.set('{%s}val' % W, 'center')
            # 图与图注必须同页：给图段加 keepNext（图注单独成段后 Word 会把图留在上一页页脚）
            if pPr.find('{%s}keepNext' % W) is None:
                pPr.insert(0, etree.Element('{%s}keepNext' % W))
            # 找到包住 drawing 的那个 run，其后若还有 run（图注文字），整段拆出去
            runs = p.findall('{%s}r' % W)
            idx = [i for i, r in enumerate(runs) if r.find('.//{%s}drawing' % W) is not None]
            if idx:
                tail = runs[idx[-1] + 1:]
                if tail:
                    p2 = etree.Element('{%s}p' % W)
                    pPr2 = copy.deepcopy(pPr)
                    pPr2.remove(pPr2.find('{%s}keepNext' % W))
                    jc2 = pPr2.find('{%s}jc' % W)
                    if jc2 is None:
                        jc2 = etree.SubElement(pPr2, '{%s}jc' % W)
                    jc2.set('{%s}val' % W, 'both')
                    # 图注行距 1.25、段前略减：长图注不把要点挤到下一页
                    sp = pPr2.find('{%s}spacing' % W)
                    if sp is not None:
                        sp.set('{%s}line' % W, '300')
                        sp.set('{%s}before' % W, '80')
                    p2.append(pPr2)
                    for r in tail:
                        p.remove(r)
                        p2.append(r)
                    p.addnext(p2)
            stat['ctr'] = stat.get('ctr', 0) + 1
        # --- 5) 图页分页：「三、七张图」另起一页，其后每张图的标题再各起一页 ---
        def _pbr(p):
            pPr = p.find('{%s}pPr' % W)
            if pPr is None:
                pPr = etree.Element('{%s}pPr' % W)
                p.insert(0, pPr)
            if pPr.find('{%s}pageBreakBefore' % W) is None:
                k = pPr.find('{%s}keepNext' % W)
                el = etree.Element('{%s}pageBreakBefore' % W)
                if k is not None:
                    k.addnext(el)
                else:
                    pPr.insert(0, el)
                stat['pbr'] = stat.get('pbr', 0) + 1

        seen_fig = 0
        for p in root.iter('{%s}p' % W):
            txt = ''.join(t.text or '' for t in p.iter('{%s}t' % W)).strip()
            # 目录条目也是「图 n　标题+页码」，必须排除，否则每条目录各占一页
            if p.find('.//{%s}hyperlink' % W) is not None or \
               p.find('.//{%s}fldChar' % W) is not None or \
               p.find('.//{%s}instrText' % W) is not None:
                continue
            if txt.startswith('三、七张图'):
                _pbr(p)                     # 章标题另起一页，图 1 紧随其后
                continue
            if txt.startswith('图 ') and '　' in txt and len(txt) < 40:
                seen_fig += 1
                if seen_fig > 1:            # 图 1 跟在章标题后，不单独分页
                    _pbr(p)
        for tbl in root.iter('{%s}tbl' % W):
            stat['tbl'] += 1
            for ri, tr in enumerate(tbl.findall('{%s}tr' % W)):
                trPr = tr.find('{%s}trPr' % W)
                if trPr is None:
                    trPr = etree.SubElement(tr, '{%s}trPr' % W)
                    tr.remove(trPr)
                    tr.insert(0, trPr)
                if trPr.find('{%s}cantSplit' % W) is None:
                    etree.SubElement(trPr, '{%s}cantSplit' % W)
                    stat['row'] += 1
                if ri == 0 and trPr.find('{%s}tblHeader' % W) is None:
                    etree.SubElement(trPr, '{%s}tblHeader' % W)
        s = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True).decode('utf-8')
        data = s.encode('utf-8')
    out.append((info, data))

tmp = DOC + '.tmp'
with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
    for info, data in out:
        zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, data)
shutil.move(tmp, DOC)
print('patched: sectPr=%d tables=%d rows=%d img=%d centered=%d pbr=%d' % (stat['sect'], stat['tbl'], stat['row'], stat.get('img', 0), stat.get('ctr', 0), stat.get('pbr', 0)))
