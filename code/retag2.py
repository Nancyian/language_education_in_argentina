# -*- coding: utf-8 -*-
"""按标题规律重排 289 条新增条目的相关性类别（A / B / AB / C）——计分版。"""
import io, json, re, sys, unicodedata, collections
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl

SRC = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
idx2row = {int(k): v for k, v in json.load(io.open('work/idx2row.json', encoding='utf-8')).items()}


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', s).lower()


# 人工覆盖（行号 -> 类别）：用于规则难以判定的条目
MANUAL = {
    108: 'C',   # 阿根廷西语口语特征综述：方言描写
    122: 'B',   # 非手部特征（语言学术语，非手语）：语言学本体
    145: 'AB',  # 语言与认同 + 教育
    176: 'B',   # 从卡斯蒂利亚化到 EIB：教育政策
    219: 'C',   # 与儿童/教师合作的社会语言学调查
    244: 'C',   # 原住民语言翻译问题
    255: 'C',   # portuñol 认同访谈
    272: 'C',   # 文学中的语言问题
    286: 'A',   # 性别与语法：语言干预/规范
    297: 'B',   # 英语教师话语中的母语者概念
}

POL = [r'pol[ií]tic[ao]s? lingü[ií]stic', r'pol[ií]tica (del |de la )?lengua',
       r'planificaci[oó]n lingü', r'glotopol', r'legislaci', r'derechos? lingü',
       r'regulaci[oó]n lingü', r'ideolog[ií]a', r'norma(s|tiv)', r'estandarizaci',
       r'est[aá]ndar', r'meridiano', r'panhisp[aá]nic', r'hispanidad', r'academia',
       r'diccionari', r'lexicograf', r'ortograf', r'oficial', r'pol[ií]tica educativa',
       r'pol[ií]ticas p[uú]blicas', r'estado', r'dispositivo', r'debate', r'pol[eé]mica',
       r'lengua nacional', r'idioma (nacional|de los argentinos)', r'identidad lingü',
       r'imposici', r'discriminaci', r'prejuicio', r'actitud', r'representaci',
       r'hablante nativo', r'nacionalismo', r'censo', r'institucional']

EDU = [r'ense[ñn]anza', r'educaci[oó]n', r'educaci', r'escolar', r'escuela', r'docente',
       r'maestr', r'curricul', r'aula', r'aprendizaje', r'estudiante', r'alfabetizaci',
       r'libro de texto', r'manual(es)?', r'did[aá]ctic', r'formaci[oó]n', r'universi',
       r'intercultural', r'biling[üu]', r'programa', r'materia', r'clase']

CONTACT = [r'lenguas? en contacto', r'contacto', r'multiling', r'pluriling',
           r'desplazamiento lingü', r'sociolingü', r'comunidad', r'inmigra', r'migra',
           r'ind[ií]gena', r'abor[ií]gen', r'pueblo', r'revitalizaci', r'vitalidad',
           r'mapuche', r'guaran[ií]', r'quechua', r'quichua', r'toba\b', r'qom',
           r'wich[ií]', r'aymara', r'variedad', r'variaci', r'contacto de lenguas']


def hits(pats, t):
    return sum(1 for p in pats if re.search(p, t))


def classify(title, cur):
    t = norm(title)
    p, e, c = hits(POL, t), hits(EDU, t), hits(CONTACT, t)
    # 弱势/元语言类词，单独出现不足以判 A
    if p >= 1 and e >= 1:
        return 'AB'
    if p >= 1 and p >= c:
        return 'A'
    if e >= 1 and e > c:
        return 'B'
    if c >= 1:
        return 'C'
    return cur


def main():
    wb = openpyxl.load_workbook(SRC, read_only=True)
    ws = wb['Sheet2']
    titles = {}
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=400, max_col=4, values_only=True), start=1):
        if r >= 101 and row and row[3]:
            titles[r] = row[3]
    wb.close()

    old = {int(k): v for k, v in json.load(io.open('work/clean_tags.json', encoding='utf-8')).items()}
    T = {'A·政策/规划/意识形态': 'A', 'B·语言教育政策与实践': 'B',
         'A+B·政策与教育': 'AB', 'C·社会语言学/多语接触': 'C'}
    cur = {r: T[old[i]] for i, r in idx2row.items() if i in old}

    new = {}
    for r in sorted(titles):
        if r not in cur:
            continue
        new[r] = MANUAL.get(r) or classify(titles[r], cur[r])
    print('kept rows', len(new))
    print(collections.Counter(new.values()))
    for r in sorted(new):
        if new[r] != cur.get(r):
            print('  r%-3d %-2s -> %-2s | %s' % (r, cur.get(r), new[r], str(titles[r])[:76]))
    json.dump({str(r): c for r, c in new.items()}, io.open('work/cats_by_row.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
