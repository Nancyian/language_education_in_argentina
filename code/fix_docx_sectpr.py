# -*- coding: utf-8 -*-
"""补全最后一节的页面设置。

转换引擎把封面/目录两节写全了 pgSz + pgMar，但正文所在末节的 sectPr 只有
type / pgNumType / footerReference，缺 pgSz 与 pgMar —— Word 会按默认信纸
(Letter) 打开这一节，与 A4 封面不一致。此处按首节参数补齐（A4 + 3.17cm 边距），
不改任何文字、表格或图片。
"""
import io, re, shutil, sys, zipfile

DOC = sys.argv[1] if len(sys.argv) > 1 else \
    r'C:\Users\Administrator\Desktop\阿根廷语料库\专家话语\专家话语_LDA主题建模_图表集.docx'
PG = ('<w:pgSz w:w="11906" w:h="16838"/>'
      '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800" '
      'w:header="851" w:footer="992" w:gutter="0"/>')

zin = zipfile.ZipFile(DOC)
items = [(i, zin.read(i.filename)) for i in zin.infolist()]
zin.close()

out = []
changed = False
for info, data in items:
    if info.filename == 'word/document.xml':
        s = data.decode('utf-8')
        start = s.rfind('<w:sectPr')
        end = s.find('</w:sectPr>', start)
        seg = s[start:end]
        if '<w:pgSz' not in seg:
            m = re.search(r'<w:type [^/]*/>', seg)
            if m:
                seg2 = seg[:m.end()] + PG + seg[m.end():]
            else:
                seg2 = seg.replace('<w:sectPr>', '<w:sectPr>' + PG, 1)
            s = s[:start] + seg2 + s[end:]
            changed = True
        data = s.encode('utf-8')
    out.append((info, data))

if not changed:
    print('already ok, nothing to do')
else:
    tmp = DOC + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in out:
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    shutil.move(tmp, DOC)
    print('patched last sectPr ->', DOC)
