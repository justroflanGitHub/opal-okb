# -*- coding: utf-8 -*-
"""corpus_stats.py — JSON результата сканера корпуса → markdown-отчёт распределений.

Инструмент задачи TASK_CORPUS_SCAN (порт оптического САПР OPAL-PC): читает
corpus.json (контракт schema_version 1 — docs/tasks/CORPUS_PLAN.md, раздел
«Контракт JSON») и строит markdown-отчёт: обзор конвейера, распределение f',
число поверхностей, стёкла, сверка f' имени каталога с расчётом (f_check)
и группировка отказов. Все числа берутся только из входного JSON.

Зависимости — только stdlib.

Использование:
    py scripts/corpus_stats.py --json <corpus.json> [--out <report.md>]
        [--section all|overview|focal|surfaces|glasses|fcheck|errors]

Без --out markdown печатается в stdout. Коды возврата: 0 — успех;
2 — отсутствующий/битый входной JSON (или неверные аргументы).
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

# Консоль Windows (cp1251): принудительно UTF-8, непечатаемое — заменой.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # корень проекта

OPS_ORDER = ('load', 'parse', 'paraxial', 'seidel', 'taboc1', 'pupils')
FCHECK_ORDER = ('ok', 'sign_flip', 'hydro', 'truncated', 'diverge')
# (нижняя граница включительно, верхняя исключительно, метка)
EFL_BINS = ((None, 3.0, '<3'), (3.0, 10.0, '3–10'), (10.0, 30.0, '10–30'),
            (30.0, 100.0, '30–100'), (100.0, 300.0, '100–300'),
            (300.0, 1000.0, '300–1000'), (1000.0, math.inf, '>1000'))
SURF_BINS = ((2, 5, '2–4'), (5, 9, '5–8'), (9, 13, '9–12'),
             (13, 21, '13–20'), (21, math.inf, '>20'))
BAR_WIDTH = 40
NAME_LIMIT = 40


# ---------------------------------------------------------------- утилиты --

def is_num(v):
    """Число (не bool) и конечное."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def esc(value) -> str:
    """Ячейка GFM-таблицы: экранировать '|', убрать переводы строк."""
    return str(value).replace('|', '\\|').replace('\n', ' ')


def cut(text, limit=NAME_LIMIT) -> str:
    """Обрезка длинного имени системы до limit символов."""
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + '…'


def bar(count, top, width=BAR_WIDTH) -> str:
    """ASCII-бар из '#': длина пропорциональна count/top."""
    if count <= 0 or top <= 0:
        return ''
    return '#' * max(1, round(width * count / top))


def fmt_mm(v) -> str:
    """Фокусное расстояние — с точностью 0.1 мм (null/NaN → прочерк)."""
    return '—' if not is_num(v) else f'{v:.1f}'


def pct(a, b) -> str:
    """Доля a/b в процентах (один знак)."""
    return f'{a / b * 100:.1f}' if b else '0.0'


def bin_index(value, bins):
    """Индекс диапазона, в который попадает value (либо None)."""
    for i, (lo, hi, _label) in enumerate(bins):
        if (lo is None or value >= lo) and value < hi:
            return i
    return None


def _ops_rows(data, systems):
    """ops_summary из JSON; отсутствующие операции досчитываются по systems."""
    declared = data.get('ops_summary')
    declared = declared if isinstance(declared, dict) else {}
    rows = {}
    for op in OPS_ORDER:
        row = declared.get(op)
        if isinstance(row, dict) and ('ok' in row or 'fail' in row):
            rows[op] = row
        else:
            oks = sum(1 for s in systems if (s.get('ops') or {}).get(op) is True)
            rows[op] = {'ok': oks, 'fail': len(systems) - oks}
    for op in sorted(set(declared) - set(OPS_ORDER)):
        row = declared.get(op)
        if isinstance(row, dict):
            rows[op] = row
    return rows


# ---------------------------------------------------------------- разделы --

def sec_overview(data, systems):
    total = len(systems)
    ok = sum(1 for s in systems if s.get('status') == 'ok')
    fail = total - ok
    lines = ['', '## Обзор', '',
             f'- Всего систем: {total}',
             f'- ok: {ok} ({pct(ok, total)}%)',
             f'- fail: {fail} ({pct(fail, total)}%)',
             '',
             '| Операция | ok | fail | % успеха |',
             '|---|---:|---:|---:|']
    for op, row in _ops_rows(data, systems).items():
        o = int(row.get('ok') or 0)
        f = int(row.get('fail') or 0)
        lines.append(f'| {esc(op)} | {o} | {f} | {pct(o, o + f)} |')
    return lines


def sec_focal(data, systems):
    oks = [s for s in systems if s.get('status') == 'ok']
    efls = []
    for s in oks:
        v = (s.get('metrics') or {}).get('efl')
        if is_num(v) and v != 0:
            efls.append(abs(v))
    lines = ['', "## Распределение f'", '',
             f"По ok-системам с конечным efl≠0: {len(efls)} из {len(oks)}; "
             'гистограмма |efl| по лог-диапазонам (мм).']
    if not efls:
        lines.extend(['', '_Нет систем с конечным efl≠0._'])
        return lines
    counts = [0] * len(EFL_BINS)
    for v in efls:
        counts[bin_index(v, EFL_BINS)] += 1
    top = max(counts)
    lines.extend(['',
                  '| Диапазон | Кол-во | Гистограмма |',
                  '|---|---:|---|'])
    for (_lo, _hi, label), c in zip(EFL_BINS, counts):
        lines.append(f'| {label} мм | {c} | {bar(c, top)} |')
    lines.append('')
    med = statistics.median(efls)
    lines.append(f'Мин |efl| = {min(efls):.1f} мм; медиана = {med:.1f} мм; '
                 f'макс = {max(efls):.1f} мм.')
    return lines


def sec_surfaces(data, systems):
    counts = [0] * len(SURF_BINS)
    below = 0
    known = 0
    for s in systems:
        n = s.get('n_surfaces')
        if not is_num(n):
            continue
        known += 1
        i = bin_index(n, SURF_BINS)
        if i is None:
            below += 1
        else:
            counts[i] += 1
    lines = ['', '## Число поверхностей', '',
             f'Систем с известным n_surfaces: {known} из {len(systems)}.',
             '',
             '| n_surfaces | Кол-во | Гистограмма |',
             '|---|---:|---|']
    top = max(counts) if counts else 0
    if below:
        lines.append(f'| <2 | {below} | {bar(below, top)} |')
    for (_lo, _hi, label), c in zip(SURF_BINS, counts):
        lines.append(f'| {label} | {c} | {bar(c, top)} |')
    return lines


def sec_glasses(data, systems):
    per_system = []
    for s in systems:
        glasses = s.get('glasses')
        per_system.append({str(g) for g in glasses if g is not None}
                          if isinstance(glasses, list) else set())
    counts = {}
    for glasses in per_system:
        for g in glasses:
            counts[g] = counts.get(g, 0) + 1
    lines = ['', '## Стёкла', '',
             f'Всего уникальных стёкол: {len(counts)} '
             '(частота — число систем, где стекло встречается).']
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    if not top:
        lines.extend(['', '_Стёкла в corpus.json отсутствуют._'])
        return lines
    lines.extend(['',
                  '| # | Стекло | Систем |',
                  '|---:|---|---:|'])
    for i, (g, c) in enumerate(top, 1):
        lines.append(f'| {i} | {esc(g)} | {c} |')
    return lines


def sec_fcheck(data, systems):
    total = len(systems)
    cats = {}
    nulls = 0
    for s in systems:
        fc = s.get('f_check')
        if not isinstance(fc, dict):
            nulls += 1
            continue
        cat = str(fc.get('category') or '(без категории)')
        cats[cat] = cats.get(cat, 0) + 1
    lines = ['', "## Сверка f' (f_check)", '',
             f"f_check заполнен (есть f= / f'= в имени): {total - nulls}; "
             f'f_check = null: {nulls}.',
             '',
             '| Категория | Систем |',
             '|---|---:|']
    order = [c for c in FCHECK_ORDER if c in cats] + sorted(set(cats) - set(FCHECK_ORDER))
    for cat in order:
        lines.append(f'| {esc(cat)} | {cats[cat]} |')
    lines.append(f'| f_check = null | {nulls} |')
    lines.append(f'| **Итого** | **{total}** |')

    def _err(s):
        fc = s.get('f_check')
        return fc.get('err_pct') if isinstance(fc, dict) else None

    ok_all = cats.get('ok', 0)
    le1 = sum(1 for s in systems
              if isinstance(s.get('f_check'), dict)
              and s['f_check'].get('category') == 'ok' and is_num(_err(s))
              and _err(s) <= 1)
    mid = sum(1 for s in systems
              if isinstance(s.get('f_check'), dict)
              and s['f_check'].get('category') == 'ok' and is_num(_err(s))
              and 1 < _err(s) <= 5)
    lines.extend(['',
                  f'Внутри ok ({ok_all}): err ≤ 1% — {le1}; 1–5% — {mid}.'])

    worst = []
    for s in systems:
        fc = s.get('f_check')
        if isinstance(fc, dict) and is_num(fc.get('err_pct')):
            worst.append((fc['err_pct'], s))
    worst.sort(key=lambda t: t[0], reverse=True)
    lines.extend(['', 'Топ-10 наибольших err_pct:'])
    if not worst:
        lines.extend(['', '_Нет систем с числовым err_pct._'])
        return lines
    lines.extend(['',
                  '| lib | name | name_f | calc_f | err_pct | category |',
                  '|---|---|---:|---:|---:|---|'])
    for err, s in worst[:10]:
        fc = s['f_check']
        lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                     f"| {fmt_mm(fc.get('name_f'))} | {fmt_mm(fc.get('calc_f'))} "
                     f"| {err:.2f} | {esc(fc.get('category', ''))} |")
    lines.extend(['',
                  "Примечание: `sign_flip` — расхождение только знака при совпадении "
                  "модуля (в пределах 5%) — норма каталога для зеркально-линзовых "
                  "систем: находка, а не баг (docs/LBO_FORMAT.md, ТЗ TASK_CORPUS_SCAN)."])
    return lines


def sec_errors(data, systems):
    fails = [s for s in systems if s.get('status') != 'ok']
    lines = ['', '## Отказы', '', f'fail-систем: {len(fails)}.']
    if not fails:
        lines.extend(['', '_Отказов нет._'])
        return lines
    groups = {}
    for s in fails:
        err = s.get('error')
        prefix = str(err).split(':', 1)[0].strip() if err else '(без error)'
        prefix = prefix or '(без error)'
        groups.setdefault(prefix, []).append(s)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    lines.extend(['',
                  '| Префикс ошибки | Кол-во | Примеры (до 3) |',
                  '|---|---:|---|'])
    for prefix, group in ordered:
        names = '; '.join(cut(s.get('name', '')) for s in group[:3])
        lines.append(f'| {esc(prefix)} | {len(group)} | {esc(names)} |')
    return lines


SECTION_BUILDERS = (
    ('overview', sec_overview),
    ('focal', sec_focal),
    ('surfaces', sec_surfaces),
    ('glasses', sec_glasses),
    ('fcheck', sec_fcheck),
    ('errors', sec_errors),
)


def build_report(data, section='all'):
    systems = data.get('systems') or []
    source = data.get('source')
    if isinstance(source, list) and source:
        src = ', '.join(str(p) for p in source)
    elif isinstance(source, str) and source:
        src = source
    else:
        src = '—'
    generated = data.get('generated')
    lines = ['# Corpus scan — статистика', '',
             f'- Источник: {src}',
             f"- Сгенерировано (generated): {generated if generated else '—'}",
             f'- Всего систем (total): {len(systems)}']
    for key, builder in SECTION_BUILDERS:
        if section in ('all', key):
            lines.extend(builder(data, systems))
    return '\n'.join(lines).rstrip() + '\n'


# ------------------------------------------------------------------- CLI --

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='corpus_stats.py',
        description='JSON сканера корпуса (schema_version 1) → markdown-отчёт '
                    'распределений (docs/tasks/CORPUS_PLAN.md).')
    parser.add_argument('--json', required=True,
                        help='путь к corpus.json — выходу scripts/corpus_scan.py')
    parser.add_argument('--out', help='записать markdown в файл вместо stdout')
    parser.add_argument('--section', default='all',
                        choices=['all'] + [k for k, _b in SECTION_BUILDERS],
                        help='построить только указанный раздел (по умолчанию all)')
    args = parser.parse_args(argv)

    src = Path(args.json)
    if not src.is_file():
        print(f'Ошибка: входной JSON не найден: {src}', file=sys.stderr)
        return 2
    try:
        with open(src, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:  # JSONDecodeError/UnicodeDecodeError ⊂ ValueError
        print(f'Ошибка: не удалось прочитать/разобрать JSON {src}: {exc}', file=sys.stderr)
        return 2
    if not isinstance(data, dict) or not isinstance(data.get('systems'), list):
        print(f'Ошибка: {src} не соответствует контракту schema_version 1 '
              '(ожидался объект с массивом systems)', file=sys.stderr)
        return 2

    report = build_report(data, args.section)
    if args.out:
        out = Path(args.out)
        if not out.parent.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding='utf-8')
    else:
        print(report, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
