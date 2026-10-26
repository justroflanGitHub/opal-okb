# -*- coding: utf-8 -*-
"""Сканер корпуса оптических систем из библиотек .LBO (TASK_CORPUS_SCAN_V2).

Все системы каждой .LBO библиотеки прогоняются через конвейер порта
OPAL-PC: load → parse (system) → paraxial (efl finite) → seidel →
taboc1 → зрачки (entrance/exit pupil finite) → vignette (виньетирование
на макс. поле, %) → chief (дисторсия и астигматические отрезки главного
луча) → spot (полихроматический RMS пятна, мкм) → mtf_geo (геометрическая
ЧКХ: контраст 30/50 лин/мм). Отказ этапа не валит ни систему, ни скан:
фиксируется в ops/error, скан продолжается. Результат — один JSON
(schema_version 2, контракт: docs/tasks/CORPUS_PLAN.md, раздел
«Контракт v2»): успехи/отказы по этапам, параксиальные метрики, суммы
Зейделя, TABOC1, новые метрики волны 2 и сверка f' «имя каталога vs
расчёт» (правила docs/LBO_FORMAT.md) — вход для corpus_stats.py и
отчётов по корпусу.

CLI:
    py scripts/corpus_scan.py --lib <файл.LBO | каталог Lib> --out <.json>
                              [--limit N] [--quiet]
                              [--ops all|base|v2|имена через запятую]

--ops — выбор операций конвейера: all — все 10 (по умолчанию); base —
6 базовых v1 (base-ключи JSON — как в волне 1, но schema_version
всегда 2); v2 — 4 новые; список имён OPS через запятую (регистр как
в OPS, пробелы допустимы). load и parse выполняются всегда.
Неизвестное имя → код возврата 2.

Коды возврата: 0 — скан дошёл до конца (отказ отдельной системы — не
ошибка скана); 2 — нет/неверен путь --lib, --out или --ops.
"""
import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime

# Консоль Windows (cp1251): имена систем cp866 → utf-8 без падений вывода
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

# Корень проекта (родитель scripts/) — импорты порта из любого cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fileio.lbo_io import load_lbo                                 # noqa: E402
from domain.calculations import paraxial_trace, seidel_aberrations  # noqa: E402
from analysis.tables import taboc1_rows                            # noqa: E402
from analysis.vignetting import compute_vignetting                 # noqa: E402
from analysis.aberrations import (                                 # noqa: E402
    compute_chief_ray_characteristics,
    compute_geometric_mtf,
    compute_polychromatic_rms,
    compute_spot_diagram_polychromatic,
)
from optics_utils import get_primary_wl                            # noqa: E402

SCHEMA_VERSION = 2
# Конвейер — единый источник для corpus_stats.py (импортирует OPS):
# base — 6 базовых операций волны 1, v2 — 4 новые волны 2.
OPS = ('load', 'parse', 'paraxial', 'seidel', 'taboc1', 'pupils',
       'vignette', 'chief', 'spot', 'mtf_geo')
OPS_BASE = OPS[:6]
OPS_V2 = OPS[6:]
WATER_N = 1.331  # показатель преломления воды — «Гидро»-объективы каталога
# Пороги классификации f_check (именованные — единый источник, см. make_f_check)
F_EPS = 1e-9                # |f имени| ниже этого — сверка невозможна
TRUNC_NAME_F_MAX = 10.0     # признак усечённой записи каталога: |f| мал, а
TRUNC_RATIO_MIN = 8.0       # ... отношение расчёт/f в диапазоне
TRUNC_RATIO_MAX = 25.0      # ... [8..25] → «f'=1» может означать 12.2 мм
SIGN_FLIP_TOL = 0.05        # совпадение модулей в пределах 5% при обратном знаке
OK_TOL_PCT = 5.0            # порог категории ok, %

# --------------------------- #
# Классы отказов волны 3 (TASK_CORPUS_V3, пакет B) — единый источник:
# отсюда импортируют corpus_stats.py (маркировка unscannable-групп) и
# генератор реестра docs/reports/corpus_v3_failures.{json,md}; пакет C
# подключит skip-правила к scan_system().
#
# 216 отказов spot/mtf_geo корпуса v2 (612 систем, 396 ok / 216 fail)
# разбиты на 7 классов первопричин (семантика — ТЗ docs/tasks/
# TASK_CORPUS_V3.md, реестр с классами — docs/reports/corpus_v3_failures.md):
#
# unscannable_efl0 (24 fail + 7 ok-систем v2) — efl ровно 0.0 при конечном
#     L: блок стёкол US-библиотек не декодирован (glass='' у всех
#     поверхностей → n≡1, рефракции нет), лучи идут прямиком; spot-значения
#     таких систем — мусор прямых лучей (три разные ok-системы v2 дают
#     одинаковый осевой RMS 3501.6096850617296 мкм — «поддельный ok»).
#     Сканеру не место трассировать: op false + error = класс (skip как
#     unscannable); vignette/chief остаются — геометрия декодирована.
# unscannable_l0 (9 fail + 8 ok-систем v2) — L ровно 0.0: layout сломан
#     (толщины обнулены, efl~1e-270); у MICROLEN[3..9] вдобавок vignette
#     падает ZeroDivisionError в _pupil_field_ray (деление на d=0 для
#     FINITE-предмета). Layout сломан — все полевые операции (vignette,
#     chief, spot, mtf_geo) пропускаются как unscannable.
# chief_degenerate_axis (12) — осевой главный луч (field_y=0) MISS на
#     поверхности с нулевым зазором (предыдущая thickness==0 → старт
#     сегмента точно на вершине сферы): intersect_sphere возвращает
#     ДАЛЬНИЙ корень вместо t=0, физический cap GFIX P6 бракует «спину
#     сферы» → MISS → пятно пустое → RMS=inf. Движковая находка
#     (пересчёт пересечений; в сканере не чинить).
# field_fully_vignetted (134) — честный отказ: chief на макс. поле падает
#     (EDGE/TIR/MISS/STOP) даже при полудиаметрах ×1.4, у 133 из 134
#     виньетирование на макс. поле = 100%; поле каталога за пределами
#     полезного поля зрения — пучок срезан полностью, пятна не существует.
# field_edge_inflate (26) — полевой RMS=inf при штатных полудиаметрах, но
#     конечен при временном расширении ×1.4: полудиаметры LBO часто чуть
#     занижены (прецедент проекта CODDINGTON_SD_INFLATE=1.4 в
#     analysis/aberrations.py, analysis/tables.py, analysis/chromatism.py).
#     Чинится в сканере пакетом C раздутыми полудиаметрами.
# axis_beam_blocked (9) — FINITE-предмет (микрообъективы, репродукционные):
#     chief оси OK, но ВСЕ зрачковые лучи оси падают (EDGE/MISS/TIR) даже
#     при ×3.0 → осевой RMS=inf. Движковая находка (построение пучка для
#     конечного предмета; в сканере не чинить).
# spot_few_spots (2) — осевой/полевой RMS конечен, но полихроматическое
#     пятно < 10 точек (большинство лучей срезано/ПВО) → 'no axial/max
#     field MTF'; честный отказ.
#
# Порядок FAIL_CLASSES — канонический (от машинных причин к физическим);
# классификация строк реестра идёт по приоритету проверок: efl0 → l0 →
# chief_degenerate → field_edge_inflate → axis_beam_blocked →
# field_fully_vignetted → spot_few_spots.
FAIL_CLASS_EFL0 = 'unscannable_efl0'          # efl == 0.0: стёкла не декодированы
FAIL_CLASS_L0 = 'unscannable_l0'              # L == 0.0: layout сломан
FAIL_CLASS_CHIEF_DEGENERATE = 'chief_degenerate_axis'  # осевой chief MISS на zerogap
FAIL_CLASS_FIELD_VIGNETTED = 'field_fully_vignetted'   # пучок поля срезан полностью
FAIL_CLASS_FIELD_EDGE_INFLATE = 'field_edge_inflate'   # полю помогли бы ×1.4 полудиаметры
FAIL_CLASS_AXIS_BLOCKED = 'axis_beam_blocked' # FINITE: весь осевой пучок срезан
FAIL_CLASS_FEW_SPOTS = 'spot_few_spots'       # пятно < 10 точек → MTF пуста

#: 7 классов первопричин отказов волны 3 (канонический порядок — см. блок выше).
FAIL_CLASSES = (
    FAIL_CLASS_EFL0,
    FAIL_CLASS_L0,
    FAIL_CLASS_CHIEF_DEGENERATE,
    FAIL_CLASS_FIELD_VIGNETTED,
    FAIL_CLASS_FIELD_EDGE_INFLATE,
    FAIL_CLASS_AXIS_BLOCKED,
    FAIL_CLASS_FEW_SPOTS,
)

#: Операции, пропускаемые как unscannable по классу (пакет C — skip-правила
#: scan_system: op false + error = unscannable_error(op, класс)):
#: efl0 — геометрия декодирована (vignette/chief осмысленны), полевых
#: расчётов пятна нет; l0 — layout сломан, все полевые операции бессмысленны
#: (vignette у MICROLEN[3..9] к тому же падает ZeroDivisionError).
SKIP_OPS_BY_CLASS = {
    FAIL_CLASS_EFL0: ('spot', 'mtf_geo'),
    FAIL_CLASS_L0: ('vignette', 'chief', 'spot', 'mtf_geo'),
}


def detect_unscannable(efl, L):
    """efl/L системы → unscannable-класс (EFL0 | L0) | None.

    Правила (ТЗ TASK_CORPUS_V3, пакет B; skip-правила сканера — пакет C):
    - efl ровно 0.0 при конечном L → FAIL_CLASS_EFL0 (стёкла не
      декодированы, n≡1);
    - иначе L ровно 0.0 → FAIL_CLASS_L0 (layout сломан, толщины обнулены).

    efl/L могут быть None (отказ paraxial) — не класс; NaN тоже не 0.0.
    Крошечный, но не нулевой efl (1e-270 у L=0-систем) — НЕ efl0:
    сравнение точное, «почти ноль» сканируется. efl приоритетен:
    (0.0, 0.0) → EFL0 (система Цуканова LENS_SPC[5], класс по efl0).
    """
    if efl == 0.0:
        return FAIL_CLASS_EFL0
    if L == 0.0:
        return FAIL_CLASS_L0
    return None


def unscannable_error(op, cls):
    """Оп + unscannable-класс → человекочитаемая строка error сканера.

    Токен 'unscannable: efl=0' / 'unscannable: L=0' — стабильный префикс
    для парсинга: его ищет corpus_stats (маркировка групп отказов), его
    пишет пакет C в поле error вместо сообщения о трассировке.

    cls вне {EFL0, L0} — программная ошибка (ValueError): skip-правил
    для других классов нет.
    """
    if cls == FAIL_CLASS_EFL0:
        return f'{op}: unscannable: efl=0 (стёкла не декодированы, n≡1)'
    if cls == FAIL_CLASS_L0:
        return f'{op}: unscannable: L=0 (layout сломан, толщины обнулены)'
    raise ValueError(f'unscannable_error: класс {cls!r} не unscannable')


# f' из имени системы (порядок паттернов как в scripts/lbo_verify_f.py):
# f'=…, f=… (без апострофа — признак гидрообъектива), ф'/f' с пробелами.
# re.IGNORECASE: US-патентные библиотеки пишут заглавным «F'=1» (261 система).
_F_PATTERNS = (
    (re.compile(r"f'=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE), True),
    (re.compile(r"f=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE), False),
    (re.compile(r"[fф]\s*'?\s*=\s*(-?\d+(?:\.\d+)?)", re.IGNORECASE), None),
)

_PARAX_METRICS = (
    ('back_focal_distance', 'bfd'),
    ('f_number', 'f_number'),
    ('L', 'L'),
    ('entrance_pupil', 'entrance_pupil'),
    ('exit_pupil', 'exit_pupil'),
    ('entrance_pupil_diameter', 'entrance_pupil_diameter'),
)


def _finite(value):
    """Значение → float, если конечно; None/NaN/±inf/мусор → None (null)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _exc(exc):
    """Компактная подпись исключения для поля error."""
    msg = str(exc).strip()
    return f'{type(exc).__name__}: {msg}' if msg else type(exc).__name__


def parse_name_f(name):
    """f' из имени системы → (значение, есть_ли_апостроф) | (None, None)."""
    for pat, apos in _F_PATTERNS:
        m = pat.search(name)
        if m:
            return float(m.group(1)), apos
    return None, None


def make_f_check(name, calc_f):
    """Сверка f' «имя каталога vs расчёт» → dict | None (в имени нет f).

    Категории — docs/tasks/CORPUS_PLAN.md, особые случаи — docs/LBO_FORMAT.md:
    hydro      — «f=» без апострофа + «Гидро»: каталог даёт фокус в воде,
                 сверяем |расчёт·1.331| vs |f каталога|, знак условен;
    truncated  — |f имени|<10 при |расчёт/f| в 8..25 — усечённая запись
                 каталога (Юпитер-24 «f'=1» = реально 12.2 мм);
    sign_flip  — знак каталога противоположен при совпадении модулей ≤5%
                 (типично для зеркально-линзовых; находка, не баг);
    ok ≤5%, diverge — остальное; расчёт не конечен → diverge, err_pct=null.
    """
    name_f, apos = parse_name_f(name)
    if name_f is None or abs(name_f) < F_EPS:  # f=0 — сверка невозможна
        return None
    fc = {'name_f': name_f, 'calc_f': _finite(calc_f),
          'err_pct': None, 'category': 'diverge'}
    calc = fc['calc_f']
    if calc is None:
        return fc
    if apos is False and 'Гидро' in name:
        fc['err_pct'] = abs(abs(calc) * WATER_N - abs(name_f)) / abs(name_f) * 100
        fc['category'] = 'hydro'
        return fc
    fc['err_pct'] = abs(calc - name_f) / abs(name_f) * 100
    if abs(name_f) < TRUNC_NAME_F_MAX and \
            TRUNC_RATIO_MIN <= abs(calc / name_f) <= TRUNC_RATIO_MAX:
        fc['category'] = 'truncated'
    elif (calc > 0) != (name_f > 0) and \
            abs(abs(calc) - abs(name_f)) / abs(name_f) <= SIGN_FLIP_TOL:
        fc['category'] = 'sign_flip'
    elif fc['err_pct'] <= OK_TOL_PCT:
        fc['category'] = 'ok'
    return fc


#: Базовые 15 ключей metrics волны 1 (порядок = порядок в JSON).
_BASE_METRICS = (
    'efl', 'bfd', 'f_number', 'L', 'entrance_pupil', 'exit_pupil',
    'entrance_pupil_diameter', 'seidel_SI', 'seidel_SII', 'seidel_SIII',
    'seidel_SIV', 'seidel_SV', 'taboc1_rows', 'taboc1_ok',
    'taboc1_max_abs_longitudinal_mm')

#: Новые ключи metrics волны 2 по операциям (контракт «Контракт v2»):
#: выходной зрачок не дублируется — это v1-ключ exit_pupil. Публичное
#: имя — единый источник для corpus_stats.py (обратный индекс V2_KEY_OPS).
V2_METRICS = {
    'vignette': ('vignette_max_field', 'vignette_up_pct',
                 'vignette_down_pct'),
    'chief': ('chief_max_field', 'distortion_pct', 'astig_Zm_mm',
              'astig_Zs_mm'),
    'spot': ('spot_rms_axis_um', 'spot_rms_max_field_um'),
    'mtf_geo': ('mtf30_axis', 'mtf50_axis', 'mtf30_max_field',
                'mtf50_max_field'),
}


def _empty_metrics(selected=OPS):
    """Шаблон metrics контракта (все ключи на месте, значения None).

    Базовые 15 ключей волны 1 — всегда; новые v2 — только для выбранных
    операций (--ops base даёт набор ключей волны 1 побитово). Ключи
    остаются на месте и при раннем отказе операции.
    """
    keys = list(_BASE_METRICS)
    for op in selected:
        keys.extend(V2_METRICS.get(op, ()))
    return dict.fromkeys(keys)


def parse_ops(value):
    """--ops → кортеж операций конвейера в порядке OPS | None (неверный).

    'all' — все 10, 'base' — 6 базовых v1, 'v2' — 4 новые; иначе имена
    OPS через запятую (регистр как в OPS, пробелы вокруг допустимы).
    load/parse входят в любую выборку — без них нет системы.
    """
    name = (value or 'all').strip()
    preset = {'all': OPS, 'base': OPS_BASE, 'v2': OPS_V2}.get(name)
    if preset is not None:
        selected = set(preset)
    else:
        selected = {p.strip() for p in name.split(',')} - {''}
        if not selected or not set(selected) <= set(OPS):
            return None
    selected |= {'load', 'parse'}      # выполняются всегда
    return tuple(op for op in OPS if op in selected)


def _max_field(system):
    """Макс. поле системы (max |fp.y|, град/мм); нет точек → 0.0.

    Все поля нулевые или списка нет — безполевая система (max 0.0):
    осевой случай валиден для всех операций волны 2.
    """
    fields = [abs(fp.y) for fp in (system.field_points or [])]
    return max(fields) if fields else 0.0


def _mtf_at(mtf, freq):
    """Тангенциальный контраст ЧКХ на частоте freq, лин/мм | None.

    Ближайшая точка кривой compute_geometric_mtf; частота мимо сетки
    или не конечное значение → None.
    """
    row = min(mtf, key=lambda r: abs(r[0] - freq), default=None)
    if row is None or abs(row[0] - freq) > 1e-6:
        return None
    return _finite(row[1])


def _mtf_contrast(system, field_y):
    """Пара контрастов (30, 50 лин/мм) на поле field_y | None.

    Пятно — полихроматическое (сетка 30×30, все λ системы); ЧКХ —
    compute_geometric_mtf (FFT гистограммы пятна, max_freq=50, 5
    частот; тангенциальный срез). None — пятен < 10, ЧКХ пустая или
    нужной частоты на кривой нет.
    """
    spots = compute_spot_diagram_polychromatic(system, num_rays=30,
                                               field_y=field_y)
    if len(spots) < 10:
        return None
    mtf = compute_geometric_mtf([(x, y) for x, y, _ in spots],
                                max_freq=50.0, num_freqs=5)
    if not mtf:
        return None
    mtf30 = _mtf_at(mtf, 30.0)
    mtf50 = _mtf_at(mtf, 50.0)
    if mtf30 is None or mtf50 is None:
        return None
    return mtf30, mtf50


def scan_system(entry, lib, index, selected=OPS):
    """Конвейер одной записи load_lbo → dict системы по контракту JSON.

    selected — выбор операций (--ops); load/parse всегда в выборке.
    """
    ops = dict.fromkeys(selected, False)
    why = {}  # op → сообщение об отказе (для error первого сбойного этапа)
    metrics = _empty_metrics(selected)
    rec = {
        'lib': lib, 'index': index,
        'name': entry.get('name'), 'filename': entry.get('filename'),
        'n_surfaces': None, 'n_wavelengths': None,
        'glasses': None, 'has_mirror': None,
        'status': 'fail', 'error': None,
        'ops': ops, 'metrics': metrics, 'f_check': None,
    }

    ops['load'] = True  # запись найдена в .LBO (load_lbo её вернул)

    system = entry.get('system')
    if system is not None:
        ops['parse'] = True
    else:
        warnings = entry.get('warnings') or []
        why['parse'] = warnings[0] if warnings else 'system is None'
        for op in selected:
            if op not in ('load', 'parse'):
                why[op] = 'system is None'
        rec['error'] = f"parse: {why['parse']}"
        rec['f_check'] = make_f_check(rec['name'] or '', None)  # diverge
        return rec

    # Описательные поля системы
    rec['n_surfaces'] = len(system.surfaces)
    rec['n_wavelengths'] = len(system.wavelengths)
    glasses = []
    for surf in system.surfaces:
        g = (surf.glass or '').strip()
        if g and g not in glasses:
            glasses.append(g)
    rec['glasses'] = glasses
    rec['has_mirror'] = any(bool(s.is_reflective) for s in system.surfaces)

    # paraxial: без исключения и efl finite (efl = EFL, fallback focal_length)
    if 'paraxial' in ops:
        try:
            parax = paraxial_trace(system)
        except Exception as exc:  # noqa: BLE001 — отказ этапа не валит скан
            parax = None
            why['paraxial'] = _exc(exc)
        if isinstance(parax, dict):
            efl = _finite(parax.get('effective_focal_length'))
            if efl is None:
                efl = _finite(parax.get('focal_length'))
            metrics['efl'] = efl
            for src, dst in _PARAX_METRICS:
                metrics[dst] = _finite(parax.get(src))
        if metrics['efl'] is None:
            why.setdefault('paraxial', 'efl not finite')
        else:
            ops['paraxial'] = True

    # seidel: суммы Зейделя 3-го порядка (этап независим от paraxial)
    if 'seidel' in ops:
        try:
            seidel = seidel_aberrations(system)
        except Exception as exc:  # noqa: BLE001
            why['seidel'] = _exc(exc)
        else:
            ops['seidel'] = True
            for key in ('SI', 'SII', 'SIII', 'SIV', 'SV'):
                metrics['seidel_' + key] = _finite(seidel.get(key))

    # taboc1: остаточные аберрации осевого пучка, хотя бы одна строка
    if 'taboc1' in ops:
        try:
            rows = taboc1_rows(system)
        except Exception as exc:  # noqa: BLE001
            why['taboc1'] = _exc(exc)
        else:
            if rows:
                ops['taboc1'] = True
                metrics['taboc1_rows'] = len(rows)
                lons = [r.get('longitudinal_mm') for r in rows
                        if r.get('longitudinal_mm') is not None]
                metrics['taboc1_ok'] = len(lons)
                vals = [v for v in (_finite(x) for x in lons) if v is not None]
                if vals:
                    metrics['taboc1_max_abs_longitudinal_mm'] = \
                        max(abs(v) for v in vals)
            else:
                why['taboc1'] = 'no rows'

    # зрачки: входной и выходной зрачок конечны (по данным paraxial)
    if 'pupils' in ops:
        if not ops.get('paraxial', False):
            why.setdefault('pupils', 'no paraxial data')
        elif metrics['entrance_pupil'] is None:
            why['pupils'] = 'entrance_pupil not finite'
        elif metrics['exit_pupil'] is None:
            why['pupils'] = 'exit_pupil not finite'
        else:
            ops['pupils'] = True

    # vignette: виньетирование верх/низ на макс. поле, % (TABBEA);
    # выходной зрачок не дублируется — это v1-ключ exit_pupil
    if 'vignette' in ops:
        try:
            field_max = _max_field(system)
            vign = compute_vignetting(system, field_max,
                                      wl=get_primary_wl(system))
            up = _finite(vign.get('vignet_up'))
            down = _finite(vign.get('vignet_down'))
            if up is None or down is None:
                why['vignette'] = 'vignetting not finite'
            else:
                ops['vignette'] = True
                metrics['vignette_max_field'] = field_max
                metrics['vignette_up_pct'] = up
                metrics['vignette_down_pct'] = down
        except Exception as exc:  # noqa: BLE001
            why['vignette'] = _exc(exc)

    # chief: дисторсия и астигматические отрезки главного луча на макс.
    # поле; безполевая система (макс. поле 0) — валидный осевой случай:
    # ops true, метрики не определены (None), ошибки нет
    if 'chief' in ops:
        try:
            field_max = _max_field(system)
            if field_max <= 0.0:
                ops['chief'] = True
            else:
                chars = compute_chief_ray_characteristics(
                    system, wl=get_primary_wl(system))
                best = None
                for c in chars:
                    fy = _finite(c.get('field_y'))
                    if fy is not None and (
                            best is None or
                            abs(fy) > abs(best.get('field_y') or 0.0)):
                        best = c
                if best is None:
                    why['chief'] = 'no chief ray data'
                else:
                    dist = _finite(best.get('distortion_rel'))
                    zm = _finite(best.get('Zm'))
                    zs = _finite(best.get('Zs'))
                    if dist is None or zm is None or zs is None:
                        why['chief'] = 'chief characteristics not finite'
                    else:
                        ops['chief'] = True
                        metrics['chief_max_field'] = field_max
                        metrics['distortion_pct'] = dist
                        metrics['astig_Zm_mm'] = zm
                        metrics['astig_Zs_mm'] = zs
        except Exception as exc:  # noqa: BLE001
            why['chief'] = _exc(exc)

    # spot: полихроматический RMS пятна на оси и на макс. поле (мкм,
    # мм ×1000); сетка 30×30, все λ системы с весами; безполевая —
    # только осевой RMS, op true
    if 'spot' in ops:
        try:
            rms_axis = _finite(compute_polychromatic_rms(
                system, num_rays=30, field_y=0.0))
            if rms_axis is None:
                why['spot'] = 'axis RMS not finite'
            else:
                metrics['spot_rms_axis_um'] = rms_axis * 1000.0
                field_max = _max_field(system)
                if field_max > 0.0:
                    rms_field = _finite(compute_polychromatic_rms(
                        system, num_rays=30, field_y=field_max))
                    if rms_field is None:
                        why['spot'] = 'max field RMS not finite'
                    else:
                        metrics['spot_rms_max_field_um'] = rms_field * 1000.0
                if not why.get('spot'):
                    ops['spot'] = True
        except Exception as exc:  # noqa: BLE001
            why['spot'] = _exc(exc)

    # mtf_geo: геометрическая ЧКХ (FFT пятна) — тангенциальный контраст
    # на 30 и 50 лин/мм, ось и макс. поле; безполевая — только осевые,
    # op true; пустое пятно/ЧКХ — отказ этапа
    if 'mtf_geo' in ops:
        try:
            axis = _mtf_contrast(system, 0.0)
            if axis is None:
                why['mtf_geo'] = 'no axial MTF (empty spot?)'
            else:
                metrics['mtf30_axis'], metrics['mtf50_axis'] = axis
                field_max = _max_field(system)
                if field_max > 0.0:
                    oblique = _mtf_contrast(system, field_max)
                    if oblique is None:
                        why['mtf_geo'] = 'no max field MTF (empty spot?)'
                    else:
                        (metrics['mtf30_max_field'],
                         metrics['mtf50_max_field']) = oblique
                if not why.get('mtf_geo'):
                    ops['mtf_geo'] = True
        except Exception as exc:  # noqa: BLE001
            why['mtf_geo'] = _exc(exc)

    rec['f_check'] = make_f_check(rec['name'] or '', metrics['efl'])
    for op in selected:
        if not ops[op]:
            rec['error'] = f'{op}: {why.get(op, "failed")}'
            break
    else:
        rec['status'] = 'ok'
    return rec


def collect_lib_files(lib_path):
    """--lib → список полных путей .LBO (файл | каталог по алфавиту) | None."""
    if os.path.isfile(lib_path):
        return [os.path.abspath(lib_path)]
    if os.path.isdir(lib_path):
        names = sorted(n for n in os.listdir(lib_path)
                       if n.upper().endswith('.LBO')
                       and os.path.isfile(os.path.join(lib_path, n)))
        return [os.path.join(os.path.abspath(lib_path), n) for n in names]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Скан корпуса оптических систем из .LBO библиотек '
                    '(контракт v2, schema 2: docs/tasks/CORPUS_PLAN.md)')
    ap.add_argument('--lib', required=True,
                    help='файл .LBO или каталог с *.LBO (все по алфавиту)')
    ap.add_argument('--out', required=True,
                    help='выходной JSON (родительский каталог создаётся)')
    ap.add_argument('--limit', type=int, default=None,
                    help='первые N систем каждой библиотеки (по умолчанию все)')
    ap.add_argument('--quiet', action='store_true',
                    help='без прогресса в stdout')
    ap.add_argument('--ops', default='all', metavar='OPS',
                    help='операции конвейера: all | base | v2 | имена через '
                         'запятую из: ' + ', '.join(OPS) +
                         ' (по умолчанию all)')
    args = ap.parse_args(argv)

    selected = parse_ops(args.ops)
    if selected is None:
        print(f'corpus_scan: неверное значение --ops: {args.ops!r} '
              f'(допустимо: all | base | v2 | имена из: {", ".join(OPS)})',
              file=sys.stderr)
        return 2

    lib_files = collect_lib_files(args.lib)
    if not lib_files:
        print(f'corpus_scan: --lib не найден или нет файлов .LBO: {args.lib}',
              file=sys.stderr)
        return 2

    systems = []
    ops_summary = {op: {'ok': 0, 'fail': 0} for op in selected}
    t0 = time.perf_counter()
    for path in lib_files:
        lib = os.path.splitext(os.path.basename(path))[0]
        t_lib = time.perf_counter()
        try:
            entries = load_lbo(path)
        except Exception as exc:  # noqa: BLE001 — отказ библиотеки не валит скан
            print(f'corpus_scan: не удалось загрузить {path}: {_exc(exc)}',
                  file=sys.stderr)
            continue
        if args.limit is not None:
            entries = entries[:max(0, args.limit)]
        n_ok = n_fail = 0
        for i, entry in enumerate(entries):
            rec = scan_system(entry, lib, i, selected)
            systems.append(rec)
            for op in selected:
                ops_summary[op]['ok' if rec['ops'][op] else 'fail'] += 1
            if rec['status'] == 'ok':
                n_ok += 1
            else:
                n_fail += 1
        if not args.quiet:
            print(f'{lib}: {len(entries)} систем, ok={n_ok}, fail={n_fail}, '
                  f'{time.perf_counter() - t_lib:.1f} c')

    n_ok = sum(1 for r in systems if r['status'] == 'ok')
    result = {
        'tool': 'corpus_scan.py',
        'schema_version': SCHEMA_VERSION,
        'generated': datetime.now().astimezone().isoformat(timespec='seconds'),
        'source': lib_files,
        'limit': args.limit,
        'total': len(systems),
        'ok': n_ok,
        'fail': len(systems) - n_ok,
        'ops_summary': ops_summary,
        'systems': systems,
    }

    out_path = os.path.abspath(args.out)
    try:
        parent = os.path.dirname(out_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f'corpus_scan: не удалось записать {out_path}: {_exc(exc)}',
              file=sys.stderr)
        return 2

    if not args.quiet:
        print(f'Итого: {result["total"]} систем, ok={result["ok"]}, '
              f'fail={result["fail"]}, {time.perf_counter() - t0:.1f} c '
              f'(библиотек: {len(lib_files)})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
