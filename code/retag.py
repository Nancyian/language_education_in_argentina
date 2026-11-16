# -*- coding: utf-8 -*-
"""按标题规律重排 289 条新增条目的相关性类别（A / B / AB / C）。"""
import io, json, re, sys, unicodedata
sys.stdout.reconfigure(encoding='utf-8')

SRC = r"C:/Users/Administrator/Desktop/阿根廷语料库/专家话语/dialnet_language_corpus_merged_整理_补全_扩充.xlsx"
import openpyxl

idx2row = {int(k): v for k, v in json.load(io.open('work/idx2row.json', encoding='utf-8')).items()}


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', s).lower()


# 人工指定（行号 -> 类别），优先于规则
MANUAL = {
    # —— A：语言政策/规划/立法/语言权利/意识形态/规范之争 ——
    108: 'A', 126: 'A', 146: 'A', 147: 'A', 149: 'A', 166: 'A', 192: 'A',
    258: 'A', 154: 'A', 161: 'A', 183: 'A', 378: 'A', 224: 'A',
    # —— AB：政策 + 教育交叉 ——
    122: 'AB', 128: 'AB', 143: 'AB', 160: 'AB', 191: 'AB', 198: 'AB', 147: 'A',
    # —— B：教育政策与教学实践 ——
    123: 'B', 137: 'B', 142: 'B', 151: 'B', 185: 'B', 196: 'B',
    # —— C：社会语言学/接触（背景材料） ——
    100: 'C', 101: 'C', 105: 'C', 109: 'C', 111: 'C', 118: 'C', 124: 'C',
    132: 'C', 136: 'C', 139: 'C', 144: 'C', 145: 'C', 156: 'C', 176: 'C',
    186: 'C', 193: 'C', 195: 'C', 206: 'B', 343: 'C',
}
# 去重修正（后写覆盖前写）
MANUAL[147] = 'A'

# 规则：(正则, 类别) —— 顺序敏感，先匹配先生效
RULES = [
    # AB：政策/规划 + 教育/学校/教学 同时出现
    (r'(pol[ií]tic|planificaci|legislaci|glotopol|derech).*(educaci|escolar|escuela|ense[ñn]anza|biling|docente|curricul|aula)', 'AB'),
    (r'(educaci[oó]n intercultural|educaci[oó]n biling|EIB|intercultural biling).*(pol[ií]tic|legislaci|derecho|estado|p[uú]blic)', 'AB'),
    (r'(escuela|educaci|ense[ñn]anza|docente|maestr|curricul|aula|universi|libro de texto|manual).*(pol[ií]tic|legislaci|derecho|glotopol|regulaci|normativ)', 'AB'),
    # B：教育政策与实践
    (r'educaci[oó]n intercultural|intercultural biling|biling[üu]e|biling[üu]ismo escolar', 'B'),
    (r'ense[ñn]anza|docente|maestr|curricul|aula|escolar|escuela|universi|estudiante|aprendizaje|alfabetizaci|libro de texto|manual|did[aá]ctic|formaci[oó]n', 'B'),
    (r'ense[ñn]anza de (la )?lengua|ense[ñn]anza del espa[ñn]ol|E/?LE|espa[ñn]ol como lengua|segunda lengua|L2|lengua extranjera|herencia', 'B'),
    # A：语言政策/规划/意识形态/规范
    (r'pol[ií]tic[ao]s? lingü[ií]stic|pol[ií]tica del lenguaje|planificaci[oó]n lingü|glotopol|legislaci|derechos? lingü|regulaci[oó]n lingü|ideolog[ií]a lingü|codo|estatuto|oficialidad', 'A'),
    (r'norma|normativ|est[aá]ndar|estandarizaci|meridiano|panhisp[aá]nic|hispanidad|academia|diccionario|lexicograf|ortograf|idioma (nacional|de los argentinos)|lengua nacional|identidad lingü|debate|pol[eé]mica', 'A'),
    (r'actitud|representaci|prejuicio|discriminaci|glotofobia', 'C'),
    # C：社会语言学 / 接触 / 移民语言 / 原住民语言现状
    (r'contacto|lenguas en contacto|multiling|pluriling|desplazamiento lingü|sociolingü|etnograf|comunidad|inmigra|migra|ind[ií]gena|abor[ií]gen|pueblo|mapuche|guaran[ií]|quechua|quichua|toba|qom|wich[ií]|aymara', 'C'),
    (r'lingü[ií]stica|filolog|gram[aá]tica|fonolog|morfolog|sintaxis|l[eé]xico|discurso', 'C'),
]


def classify(title, cur):
    t = norm(title)
    for pat, cat in RULES:
        if re.search(pat, t):
            return cat
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
    changed = 0
    for r in sorted(titles):
        if r not in cur:
            continue           # 这些是被剔除的，不需要类别
        if r in MANUAL:
            new[r] = MANUAL[r]
        else:
            new[r] = classify(titles[r], cur[r])
        if new[r] != cur[r]:
            changed += 1
    print('kept rows', len(new), 'changed', changed)
    import collections
    print(collections.Counter(new.values()))

    # 打印变更明细供复核
    for r in sorted(new):
        if new[r] != cur.get(r):
            print('  r%-3d %-2s -> %-2s | %s' % (r, cur.get(r), new[r], str(titles[r])[:78]))

    json.dump({str(r): c for r, c in new.items()}, io.open('work/cats_by_row.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
