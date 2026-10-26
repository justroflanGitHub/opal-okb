# -*- coding: utf-8 -*-
"""corpus_stats.py — JSON результата сканера корпуса → markdown-отчёт распределений.

Инструмент задач TASK_CORPUS_SCAN / TASK_CORPUS_SCAN_V2 (порт оптического
САПР OPAL-PC): читает corpus.json / corpus_v2.json (контракт schema_version 1
и 2 — docs/tasks/CORPUS_PLAN.md, разделы «Контракт JSON» и «Контракт v2») и
строит markdown-отчёт: обзор конвейера, распределение f', число поверхностей,
стёкла, сверка f' имени каталога с расчётом (f_check), группировка отказов.
Формат входа различается по data['schema_version']: 1 — только базовые
секции (поведение волны 1 без изменений); 2 — базовые плюс секции волны 2
(RMS пятна, дисторсия, астигматизм, ЧКХ, корреляция «RMS поле/ось», аномалии
и отказы v2 — для v1-входа они не выводятся). Все числа берутся только из
входного JSON.

Зависимости — только stdlib.

Использование:
    py scripts/corpus_stats.py --json <corpus.json> [--out <report.md>]
        [--section all|overview|focal|surfaces|glasses|fcheck|spot|
                    distortion|astigmatism|mtf|rms_vs_field|v2_anomalies|
                    v2_errors|errors]

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
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # корень проекта
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ — corpus_scan

# Единый источник контракта операций — сам сканер (не дублируем кортежи):
# OPS — весь конвейер, OPS_BASE — 6 базовых операций волны 1, V2_METRICS —
# новые ключи по операциям (обратный индекс ниже выводится из него);
# FAIL_CLASS_* — токены классов отказов волны 3 (TASK_CORPUS_V3): маркировка
# unscannable-групп в таблице отказов.
from corpus_scan import (OPS as OPS_ORDER, OPS_BASE as OPS_BASE_ORDER,  # noqa: E402
                         V2_METRICS as SCAN_V2_METRICS,                 # noqa: E402
                         FAIL_CLASS_EFL0, FAIL_CLASS_L0)                # noqa: E402

FCHECK_ORDER = ('ok', 'sign_flip', 'hydro', 'truncated', 'diverge')
# (нижняя граница включительно, верхняя исключительно, метка)
EFL_BINS = ((None, 3.0, '<3'), (3.0, 10.0, '3–10'), (10.0, 30.0, '10–30'),
            (30.0, 100.0, '30–100'), (100.0, 300.0, '100–300'),
            (300.0, 1000.0, '300–1000'), (1000.0, math.inf, '>1000'))
SURF_BINS = ((2, 5, '2–4'), (5, 9, '5–8'), (9, 13, '9–12'),
             (13, 21, '13–20'), (21, math.inf, '>20'))
BAR_WIDTH = 40
NAME_LIMIT = 40
# Диапазоны метрик волны 2 (schema 2): RMS и астигматизм — лог-шкалы,
# дисторсия %, контраст — доля 0..1, отношение поле/ось.
RMS_UM_BINS = ((None, 0.1, '<0.1'), (0.1, 1.0, '0.1–1'), (1.0, 10.0, '1–10'),
               (10.0, 100.0, '10–100'), (100.0, 1000.0, '100–1000'),
               (1000.0, 10000.0, '1000–10000'), (10000.0, math.inf, '>10000'))
DIST_PCT_BINS = ((0.0, 1.0, '0–1'), (1.0, 3.0, '1–3'), (3.0, 10.0, '3–10'),
                 (10.0, 30.0, '10–30'), (30.0, math.inf, '>30'))
ASTIG_MM_BINS = ((None, 0.01, '<0.01'), (0.01, 0.1, '0.01–0.1'),
                 (0.1, 1.0, '0.1–1'), (1.0, 10.0, '1–10'),
                 (10.0, 100.0, '10–100'), (100.0, 1000.0, '100–1000'),
                 (1000.0, 10000.0, '1000–10000'), (10000.0, math.inf, '>10000'))
MTF_BINS = ((0.0, 0.1, '0–0.1'), (0.1, 0.3, '0.1–0.3'), (0.3, 0.5, '0.3–0.5'),
            (0.5, 0.7, '0.5–0.7'), (0.7, math.inf, '0.7–1.0'))
RATIO_BINS = ((None, 1.0, '<1'), (1.0, 3.0, '1–3'), (3.0, 10.0, '3–10'),
              (10.0, math.inf, '>10'))
# Секции волны 2: выводятся только для входа schema_version == 2 (v1-вход —
# поведение волны 1 без изменений).
V2_SECTIONS = frozenset(('spot', 'distortion', 'astigmatism', 'mtf',
                         'rms_vs_field', 'v2_anomalies', 'v2_errors'))
# 13 новых ключей metrics волны 2 → операция (обратный индекс V2_METRICS
# сканера — выводится, а не дублируется руками: единый источник ключей —
# corpus_scan.py).
V2_KEY_OPS = tuple((key, op)
                   for op, keys in SCAN_V2_METRICS.items() for key in keys)
# Ключи, чей null при true-опе валиден у безполевой системы (макс. поле == 0):
# виньетирование и осевые RMS/контраст считаются всегда — их null не валиден.
V2_NULLABLE_FIELDLESS = frozenset((
    'chief_max_field', 'distortion_pct', 'astig_Zm_mm', 'astig_Zs_mm',
    'spot_rms_max_field_um', 'mtf30_max_field', 'mtf50_max_field'))


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


def fmt_g(v, digits=4) -> str:
    """Число с digits значащими цифрами (null/NaN/±inf → прочерк)."""
    return '—' if not is_num(v) else f'{v:.{digits}g}'


def _max_field_of(s):
    """Макс. поле системы по метрикам (vignette_max_field, иначе chief_max_field)."""
    m = s.get('metrics') or {}
    for key in ('vignette_max_field', 'chief_max_field'):
        v = m.get(key)
        if is_num(v):
            return v
    return None


def _hist_lines(values, bins):
    """Строки GFM-гистограммы (шапка + диапазоны с ASCII-барами) и counts."""
    counts = [0] * len(bins)
    for v in values:
        i = bin_index(v, bins)
        if i is not None:
            counts[i] += 1
    top = max(counts) if counts else 0
    lines = ['', '| Диапазон | Кол-во | Гистограмма |', '|---|---:|---|']
    for (_lo, _hi, label), c in zip(bins, counts):
        lines.append(f'| {label} | {c} | {bar(c, top)} |')
    return lines, counts


def _ops_rows(data, systems):
    """ops_summary из JSON; отсутствующие операции досчитываются по systems.

    Операции, которых нет во входе вовсе (ни в ops_summary, ни в ops систем —
    например v2-ops в v1-JSON), не выводятся: v1-отчёт не должен менять вид
    из-за расширения кортежа OPS в сканере.
    """
    declared = data.get('ops_summary')
    declared = declared if isinstance(declared, dict) else {}
    rows = {}
    for op in OPS_ORDER:
        row = declared.get(op)
        if isinstance(row, dict) and ('ok' in row or 'fail' in row):
            rows[op] = row
            continue
        if op not in declared and \
                not any(op in (s.get('ops') or {}) for s in systems):
            continue  # операции нет во входном JSON
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


def sec_spot(data, systems):
    axis, field = [], []
    for s in systems:
        m = s.get('metrics') or {}
        v = m.get('spot_rms_axis_um')
        if is_num(v):
            axis.append(v)
        v = m.get('spot_rms_max_field_um')
        if is_num(v):
            field.append(v)
    lines = ['', '## RMS пятна (spot)', '',
             f'По системам с конечным spot_rms_axis_um: {len(axis)} из {len(systems)} '
             '(полихроматический RMS, сетка 30×30; ось считается и при отказе этапа '
             'на макс. поле); гистограмма по лог-диапазонам.']
    if not axis:
        lines.extend(['', '_Нет систем с конечным spot_rms_axis_um._'])
        return lines
    hist, _counts = _hist_lines(axis, RMS_UM_BINS)
    lines.extend(hist)
    lines.append('')
    lines.append(f'Ось: мин = {fmt_g(min(axis))} мкм; '
                 f'медиана = {fmt_g(statistics.median(axis))} мкм; '
                 f'макс = {fmt_g(max(axis))} мкм.')
    if field:
        lines.append(f'Макс. поле (spot_rms_max_field_um): не-null у {len(field)} '
                     f'систем; медиана = {fmt_g(statistics.median(field))} мкм; '
                     f'макс = {fmt_g(max(field))} мкм.')
    else:
        lines.append('Макс. поле (spot_rms_max_field_um): не-null у 0 систем.')
    return lines


def sec_distortion(data, systems):
    vals = []
    for s in systems:
        v = (s.get('metrics') or {}).get('distortion_pct')
        if is_num(v):
            vals.append((abs(v), s))
    lines = ['', '## Дисторсия (chief)', '',
             f'По системам с конечным distortion_pct: {len(vals)} из {len(systems)} '
             '(дисторсия главного луча на макс. поле, %; значение в JSON знаковое — '
             'гистограмма и топ по модулю |distortion_pct|).']
    if not vals:
        lines.extend(['', '_Нет систем с конечным distortion_pct._'])
        return lines
    absv = [v for v, _s in vals]
    hist, _counts = _hist_lines(absv, DIST_PCT_BINS)
    lines.extend(hist)
    lines.append('')
    lines.append(f'Медиана |distortion_pct| = {fmt_g(statistics.median(absv))} %; '
                 f'макс = {fmt_g(max(absv))} %.')
    vals.sort(key=lambda t: (-t[0], str(t[1].get('lib')), t[1].get('index') or 0))
    lines.extend(['', 'Топ-20 наибольшей |дисторсии|:', '',
                  '| lib | name | макс. поле, ° | \\|distortion\\|, % |',
                  '|---|---|---:|---:|'])
    for d, s in vals[:20]:
        field = (s.get('metrics') or {}).get('chief_max_field')
        lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                     f"| {fmt_g(field)} | {fmt_g(d)} |")
    return lines


def sec_astigmatism(data, systems):
    vals = []
    for s in systems:
        m = s.get('metrics') or {}
        zm, zs = m.get('astig_Zm_mm'), m.get('astig_Zs_mm')
        if is_num(zm) and is_num(zs):
            vals.append((max(abs(zm), abs(zs)), zm, zs, s))
    lines = ['', '## Астигматизм (chief)', '',
             f'По системам с конечными astig_Zm_mm и astig_Zs_mm: {len(vals)} из '
             f'{len(systems)} (астигматические отрезки главного луча Z\'m/Z\'s на '
             'макс. поле, мм); гистограмма max(|Zm|, |Zs|) по лог-диапазонам.']
    if not vals:
        lines.extend(['', '_Нет систем с конечными astig_Zm_mm/astig_Zs_mm._'])
        return lines
    tops = [t[0] for t in vals]
    hist, _counts = _hist_lines(tops, ASTIG_MM_BINS)
    lines.extend(hist)
    lines.append('')
    lines.append(f'Медиана max(|Zm|, |Zs|) = {fmt_g(statistics.median(tops))} мм; '
                 f'макс = {fmt_g(max(tops))} мм.')
    vals.sort(key=lambda t: (-t[0], str(t[3].get('lib')), t[3].get('index') or 0))
    lines.extend(['', 'Топ-20 наибольшего max(|Zm|, |Zs|):', '',
                  "| lib | name | макс. поле, ° | Z'm, мм | Z's, мм | "
                  'макс. модуль, мм |',
                  '|---|---|---:|---:|---:|---:|'])
    for top, zm, zs, s in vals[:20]:
        field = (s.get('metrics') or {}).get('chief_max_field')
        lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                     f"| {fmt_g(field)} | {fmt_g(zm)} | {fmt_g(zs)} | {fmt_g(top)} |")
    return lines


def sec_mtf(data, systems):
    axis_pairs, field = [], []
    for s in systems:
        m = s.get('metrics') or {}
        v = m.get('mtf30_axis')
        if is_num(v):
            axis_pairs.append((v, s))
        v = m.get('mtf30_max_field')
        if is_num(v):
            field.append(v)
    axis = [v for v, _s in axis_pairs]
    lines = ['', '## ЧКХ (mtf_geo)', '',
             f'По системам с конечным mtf30_axis: {len(axis)} из {len(systems)}; '
             f'с конечным mtf30_max_field: {len(field)} из {len(systems)} '
             '(тангенциальный контраст на 30 лин/мм, 0..1; геометрическая ЧКХ '
             'из полихроматического пятна).']
    if not axis and not field:
        lines.extend(['', '_Нет систем с конечным mtf30_axis/mtf30_max_field._'])
        return lines
    if axis:
        hist, _counts = _hist_lines(axis, MTF_BINS)
        lines.extend(['', f'mtf30_axis ({len(axis)} систем):'])
        lines.extend(hist)
    if field:
        hist, _counts = _hist_lines(field, MTF_BINS)
        lines.extend(['', f'mtf30_max_field ({len(field)} систем):'])
        lines.extend(hist)
    meds = []
    if axis:
        meds.append(f'mtf30_axis = {fmt_g(statistics.median(axis))}')
    if field:
        meds.append(f'mtf30_max_field = {fmt_g(statistics.median(field))}')
    lines.extend(['', 'Медианы: ' + '; '.join(meds) + '.'])

    def _worst_key(t):
        # Наименьший контраст первым; при равном — наибольший осевой RMS.
        rms = (t[1].get('metrics') or {}).get('spot_rms_axis_um')
        return (t[0], -(rms if is_num(rms) else 0.0),
                str(t[1].get('lib')), t[1].get('index') or 0)

    worst = sorted(axis_pairs, key=_worst_key)
    lines.extend(['', 'Топ-20 наименьших mtf30_axis (аномалии размытия; при равном '
                      'контрасте — по наибольшему осевому RMS):', '',
                  '| lib | name | mtf30_axis | mtf50_axis | осевой RMS, мкм |',
                  '|---|---|---:|---:|---:|'])
    for v, s in worst[:20]:
        m = s.get('metrics') or {}
        lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                     f"| {fmt_g(v)} | {fmt_g(m.get('mtf50_axis'))} "
                     f"| {fmt_g(m.get('spot_rms_axis_um'))} |")
    return lines


def sec_rms_vs_field(data, systems):
    ratios = []
    for s in systems:
        m = s.get('metrics') or {}
        a, f = m.get('spot_rms_axis_um'), m.get('spot_rms_max_field_um')
        if is_num(a) and is_num(f):
            ratios.append((f / a if a != 0 else (math.inf if f > 0 else math.nan), s))

    def _ratio_order(t):
        # inf (ось = 0) — наихудшие, конечные по убыванию, NaN в конце.
        r = t[0]
        if math.isnan(r):
            return (2, 0.0, str(t[1].get('lib')), t[1].get('index') or 0)
        if math.isinf(r):
            return (0, 0.0, str(t[1].get('lib')), t[1].get('index') or 0)
        return (1, -r, str(t[1].get('lib')), t[1].get('index') or 0)

    lines = ['', '## Корреляция «RMS поле/ось» (spot)', '',
             f'По системам с конечными spot_rms_axis_um и spot_rms_max_field_um: '
             f'{len(ratios)} из {len(systems)}; отношение поле/ось '
             '(spot_rms_max_field_um / spot_rms_axis_um; <1 — на поле пятно '
             'меньше осевого).']
    if not ratios:
        lines.extend(['', '_Нет систем с обоими конечными RMS._'])
        return lines
    fin = [r for r, _s in ratios if math.isfinite(r)]
    nonfin = len(ratios) - len(fin)
    hist, counts = _hist_lines(fin, RATIO_BINS)
    lines.extend(hist)
    if nonfin:
        lines.append(f'| inf/NaN | {nonfin} | {bar(nonfin, max(counts) if counts else 0)} |')
    if fin:
        lines.append('')
        lines.append(f'Медиана (конечные отношения) = {fmt_g(statistics.median(fin))}.')
    ratios.sort(key=_ratio_order)
    lines.extend(['', 'Топ-20 наибольших отношений (деградация пятна к полю):', '',
                  '| lib | name | ось, мкм | поле, мкм | поле/ось |',
                  '|---|---|---:|---:|---:|'])
    for r, s in ratios[:20]:
        m = s.get('metrics') or {}
        r_txt = '∞' if math.isinf(r) else 'NaN' if math.isnan(r) else fmt_g(r)
        lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                     f"| {fmt_g(m.get('spot_rms_axis_um'))} "
                     f"| {fmt_g(m.get('spot_rms_max_field_um'))} | {r_txt} |")
    return lines


def sec_v2_anomalies(data, systems):
    # (а) null/не-числовые метрики при true-опе (валидный null — безполевая)
    suspect = []
    valid_null = 0
    for s in systems:
        ops = s.get('ops') or {}
        m = s.get('metrics') or {}
        field = _max_field_of(s)
        for key, op in V2_KEY_OPS:
            if ops.get(op) is not True:
                continue  # null при отказе операции нормален (partial-значения валидны)
            v = m.get(key)
            if v is None:
                if field is None:
                    # поле неизвестно (JSON с --ops-подмножеством без
                    # vignette/chief) — валидность null проверить нельзя
                    continue
                if field == 0 and key in V2_NULLABLE_FIELDLESS:
                    valid_null += 1  # валидный null безполевой системы
                else:
                    suspect.append((s, op, key, v, field))
            elif not is_num(v):
                suspect.append((s, op, key, v, field))  # NaN/±inf/не-число
    # (б) |дисторсия| > 50%
    over50 = []
    for s in systems:
        v = (s.get('metrics') or {}).get('distortion_pct')
        if is_num(v) and abs(v) > 50:
            over50.append((abs(v), s))
    over50.sort(key=lambda t: (-t[0], str(t[1].get('lib')), t[1].get('index') or 0))
    # (в) осевой RMS = 0 — подозрение на вырождение («идеальная» система)
    zero_rms = []
    for s in systems:
        v = (s.get('metrics') or {}).get('spot_rms_axis_um')
        if is_num(v) and v == 0:
            zero_rms.append(s)
    # (г) контраст ≈ 1 при ненулевом пятне — сверка согласованности spot/mtf
    near_one = []
    for s in systems:
        m = s.get('metrics') or {}
        mtf, rms = m.get('mtf30_axis'), m.get('spot_rms_axis_um')
        if is_num(mtf) and is_num(rms) and mtf > 0.99 and rms > 0:
            near_one.append((mtf, rms, s))
    near_one.sort(key=lambda t: (-t[0], -t[1], str(t[2].get('lib')),
                                 t[2].get('index') or 0))

    lines = ['', '## Аномалии v2', '',
             'Проверки по 13 новым ключам metrics (контракт «Контракт v2», '
             'docs/tasks/CORPUS_PLAN.md). Валидный null при true-опе — только у '
             'безполевой системы (макс. поле == 0; поле системы — '
             'vignette_max_field, иначе chief_max_field; нет обеих — поле '
             'неизвестно, null полевых ключей не классифицируется); null при '
             'поле > 0 и не-числовые значения (NaN/±inf/не число) — нарушение '
             'контракта.',
             '',
             f'- а) null/не-числовые метрики: {len(suspect)}',
             f'- б) |дисторсия| > 50%: {len(over50)}',
             f'- в) осевой RMS = 0 (вырождение): {len(zero_rms)}',
             f'- г) mtf30_axis > 0.99 при осевом RMS > 0: {len(near_one)}']

    lines.extend(['', f'**а) null/не-числовые метрики при true-опе** — систем: '
                      f'{len(suspect)}; валидных null (безполевая, op true): '
                      f'{valid_null}.'])
    if not suspect:
        lines.extend(['', '_Таких случаев нет._'])
    else:
        lines.extend(['',
                      '| lib | name | op | ключ | значение | поле, ° |',
                      '|---|---|---|---|---|---:|'])
        for s, op, key, v, field in suspect[:20]:
            v_txt = 'null' if v is None else esc(str(v))
            lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                         f"| {esc(op)} | {esc(key)} | {v_txt} | {fmt_g(field)} |")
        if len(suspect) > 20:
            lines.extend(['', f'Показаны первые 20 из {len(suspect)}.'])

    lines.extend(['', f'**б) |дисторсия| > 50%** — систем: {len(over50)}.'])
    if not over50:
        lines.extend(['', '_Таких случаев нет._'])
    else:
        lines.extend(['',
                      '| lib | name | макс. поле, ° | \\|distortion\\|, % |',
                      '|---|---|---:|---:|'])
        for d, s in over50[:20]:
            field = (s.get('metrics') or {}).get('chief_max_field')
            lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                         f"| {fmt_g(field)} | {fmt_g(d)} |")
        if len(over50) > 20:
            lines.extend(['', f'Показаны первые 20 из {len(over50)}.'])

    lines.extend(['', f'**в) осевой RMS = 0** (подозрение на вырождение — '
                      f'«идеальная» система) — систем: {len(zero_rms)}.'])
    if not zero_rms:
        lines.extend(['', '_Таких случаев нет._'])
    else:
        lines.extend(['',
                      '| lib | name | осевой RMS, мкм | mtf30_axis |',
                      '|---|---|---:|---:|'])
        for s in zero_rms[:20]:
            m = s.get('metrics') or {}
            lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                         f"| {fmt_g(m.get('spot_rms_axis_um'))} "
                         f"| {fmt_g(m.get('mtf30_axis'))} |")
        if len(zero_rms) > 20:
            lines.extend(['', f'Показаны первые 20 из {len(zero_rms)}.'])

    lines.extend(['', f'**г) mtf30_axis > 0.99 при осевом RMS > 0** (сверка '
                      f'согласованности spot/mtf) — систем: {len(near_one)}.'])
    if not near_one:
        lines.extend(['', '_Таких случаев нет._'])
    else:
        lines.extend(['',
                      '| lib | name | mtf30_axis | mtf50_axis | осевой RMS, мкм |',
                      '|---|---|---:|---:|---:|'])
        for mtf, rms, s in near_one[:20]:
            m = s.get('metrics') or {}
            lines.append(f"| {esc(s.get('lib', ''))} | {esc(cut(s.get('name', '')))} "
                         f"| {fmt_g(mtf)} | {fmt_g(m.get('mtf50_axis'))} "
                         f"| {fmt_g(rms)} |")
        if len(near_one) > 20:
            lines.extend(['', f'Показаны первые 20 из {len(near_one)}.'])
        lines.extend(['',
                      'Примечание: геометрическая ЧКХ — FFT гистограммы пятна; '
                      'контраст ≈ 1 при пятне много меньше периода 30 лин/мм '
                      'физичен — группа перечисляет крайние случаи для разбора.'])
    return lines


# Стабильные unscannable-токены поля error (пишет scan_system волны 3 через
# unscannable_error — corpus_scan.py, skip-правила пакет C) → токен класса
# первопричины. Поиск подстрокой: op перед токеном вариируется
# ('spot: unscannable: efl=0 …'); регистр значим — 'efl=0' не содержит 'L=0'.
_UNSCANNABLE_MARKS = (
    ('unscannable: efl=0', FAIL_CLASS_EFL0),
    ('unscannable: L=0', FAIL_CLASS_L0),
)


def _error_groups_lines(fails):
    """Строки таблицы отказов по префиксу error (sec_errors/sec_v2_errors).

    Группы, чей error содержит unscannable-токен ('unscannable: efl=0' /
    'unscannable: L=0'), помечаются токеном класса первопричины — приписка
    '[unscannable_efl0]' / '[unscannable_l0]' к префиксу (волна 3,
    TASK_CORPUS_V3). На входах без таких error (v1/v2) вывод битово прежний.
    """
    groups = {}
    for s in fails:
        err = s.get('error')
        prefix = str(err).split(':', 1)[0].strip() if err else '(без error)'
        prefix = prefix or '(без error)'
        if err:
            err_s = str(err)
            for token, cls in _UNSCANNABLE_MARKS:
                if token in err_s:
                    prefix = f'{prefix} [{cls}]'
                    break
        groups.setdefault(prefix, []).append(s)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    lines = ['',
             '| Префикс ошибки | Кол-во | Примеры (до 3) |',
             '|---|---:|---|']
    for prefix, group in ordered:
        names = '; '.join(cut(s.get('name', '')) for s in group[:3])
        lines.append(f'| {esc(prefix)} | {len(group)} | {esc(names)} |')
    return lines


def sec_v2_errors(data, systems):
    fails = [s for s in systems
             if s.get('status') != 'ok'
             and all((s.get('ops') or {}).get(op) is True for op in OPS_BASE_ORDER)]
    lines = ['', '## Отказы v2 (базовый конвейер прошёл)', '',
             f'fail-систем, у которых все {len(OPS_BASE_ORDER)} базовых операций '
             f'true: {len(fails)} (отказ — на операциях волны 2; base-отказы — '
             'в разделе «Отказы»).']
    if not fails:
        lines.extend(['', '_Таких систем нет._'])
        return lines
    lines.extend(_error_groups_lines(fails))
    return lines


def sec_errors(data, systems):
    fails = [s for s in systems if s.get('status') != 'ok']
    lines = ['', '## Отказы', '', f'fail-систем: {len(fails)}.']
    if not fails:
        lines.extend(['', '_Отказов нет._'])
        return lines
    lines.extend(_error_groups_lines(fails))
    return lines


SECTION_BUILDERS = (
    ('overview', sec_overview),
    ('focal', sec_focal),
    ('surfaces', sec_surfaces),
    ('glasses', sec_glasses),
    ('fcheck', sec_fcheck),
    ('spot', sec_spot),
    ('distortion', sec_distortion),
    ('astigmatism', sec_astigmatism),
    ('mtf', sec_mtf),
    ('rms_vs_field', sec_rms_vs_field),
    ('v2_anomalies', sec_v2_anomalies),
    ('v2_errors', sec_v2_errors),
    ('errors', sec_errors),
)


def build_report(data, section='all'):
    systems = data.get('systems') or []
    schema = data.get('schema_version')
    source = data.get('source')
    if isinstance(source, list) and source:
        src = ', '.join(str(p) for p in source)
    elif isinstance(source, str) and source:
        src = source
    else:
        src = '—'
    generated = data.get('generated')
    schema_txt = schema if schema is not None else '—'
    lines = ['# Corpus scan — статистика', '',
             f'- Источник: {src}',
             f"- Сгенерировано (generated): {generated if generated else '—'}",
             f'- Schema_version входного файла: {schema_txt}',
             f'- Всего систем (total): {len(systems)}']
    for key, builder in SECTION_BUILDERS:
        if section not in ('all', key):
            continue
        if key in V2_SECTIONS and schema != 2:
            continue  # v1-вход: секции волны 2 не выводятся (контракт: 1 → v1)
        lines.extend(builder(data, systems))
    return '\n'.join(lines).rstrip() + '\n'


# ------------------------------------------------------------------- CLI --

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='corpus_stats.py',
        description='JSON сканера корпуса (schema_version 1 или 2) → markdown-'
                    'отчёт распределений (docs/tasks/CORPUS_PLAN.md, разделы '
                    '«Контракт JSON» и «Контракт v2»).')
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
        print(f'Ошибка: {src} не соответствует контракту schema_version 1/2 '
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
