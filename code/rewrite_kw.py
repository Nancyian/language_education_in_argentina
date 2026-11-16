# -*- coding: utf-8 -*-
"""按 Dialnet 同款 19 个西语关键词重算 C 列（标题优先，摘要仅在标题无命中时兜底；
补充 lectura/escritura/interculturalidad 等教育语言类西语关键词，保证区分度）。"""
import io, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'tools')
from kw_merge import RULES, norm

WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work')

# 在原 19 个关键词基础上补充（同属用户给定关键词体系）
EXTRA = {
    'lectura y escritura': lambda t: any(w in t for w in
        ('lectura', 'escritura', 'alfabetiz', 'literacy', 'literacidad', 'leer', 'escribir')),
    'interculturalidad': lambda t: any(w in t for w in
        ('intercultur', 'multicultur', 'pluricultur', 'diversidad cultural', 'eib', 'ebi')),
    'adquisición de lenguas': lambda t: any(w in t for w in
        ('adquisicion', 'aprendizaje', 'acquisition', 'learning')) and
        any(w in t for w in ('lengua', 'lenguas', 'idioma', 'language')),
    'léxico': lambda t: any(w in t for w in ('lexic', 'vocabulari', 'vocabulario', 'lexico')),
    'traducción': lambda t: any(w in t for w in ('traducc', 'translation', 'traductor')),
    'discurso': lambda t: any(w in t for w in ('discurso', 'discourse', 'discursiv')),
    'gramática': lambda t: any(w in t for w in ('gramat', 'grammar', 'morfosintax', 'sintax')),
    'hablantes': lambda t: any(w in t for w in ('hablante', 'hablantes', 'speaker')),
    'docentes': lambda t: any(w in t for w in ('docente', 'docentes', 'profesor', 'teacher')),
    'estudiantes': lambda t: any(w in t for w in ('estudiante', 'estudiantes', 'alumn', 'student')),
}

ALL_RULES = dict(RULES)
ALL_RULES.update(EXTRA)

ORDER = ['español', 'inglés', 'francés', 'portugués', 'chino', 'mandarín',
         'bilingüe', 'multilingüismo', 'lingüística', 'idioma',
         'política lingüística', 'derechos lingüísticos', 'lenguas indígenas',
         'lenguas de migración', 'lengua extranjera', 'segunda lengua', 'L2',
         'enseñanza de la lengua', 'adquisición de lenguas',
         'lectura y escritura', 'uso de la lengua', 'discurso', 'léxico',
         'gramática', 'traducción', 'interculturalidad',
         'hablantes', 'docentes', 'estudiantes']

# 摘要兜底时只允许这些「具体」关键词（避免 lingüística 泛滥）
CONCRETE = {'lenguas indígenas', 'lenguas de migración', 'política lingüística',
            'derechos lingüísticos', 'lengua extranjera', 'segunda lengua', 'L2',
            'bilingüe', 'multilingüismo', 'enseñanza de la lengua', 'lectura y escritura',
            'interculturalidad', 'español', 'inglés', 'portugués', 'traducción', 'discurso'}

TITLE_ONLY = {'lectura y escritura', 'interculturalidad', 'léxico', 'gramática',
              'hablantes', 'docentes', 'estudiantes', 'discurso'}


def hits_of(text, allowed=None):
    out = [k for k, fn in ALL_RULES.items() if fn(text)]
    if allowed is not None:
        out = [k for k in out if k in allowed]
    return out


def kws_for(title, abstract):
    tt = norm(title)
    hits = hits_of(tt)
    if not hits:
        aa = norm(abstract or '')
        hits = hits_of(aa, allowed=CONCRETE)
    if not hits:
        hits = ['lingüística']
    hits = sorted(set(hits), key=lambda k: ORDER.index(k) if k in ORDER else 99)
    return '; '.join(hits)


def main():
    path = os.path.join(WORK, 'final_argjr.json')
    rows = json.load(io.open(path, encoding='utf-8'))
    # 若已被上一版污染，从备份恢复原始 kw 字段不必要——src kw 只用于展示
    for r in rows:
        r['kw'] = kws_for(r.get('title', ''), r.get('abs', ''))
    json.dump(rows, io.open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    from collections import Counter
    c = Counter(r['kw'] for r in rows)
    print('distinct', len(c), 'rows', len(rows))
    for k, v in c.most_common(18):
        print(' %3d  %s' % (v, k))
    print('\n单关键词占比: %.0f%%' % (100.0 * sum(v for k, v in c.items() if ';' not in k) / len(rows)))
    print('\n示例:')
    for r in rows[:8]:
        print('  ', r['kw'][:64], '||', r['title'][:46])


if __name__ == '__main__':
    main()
