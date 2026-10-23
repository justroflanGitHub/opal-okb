# -*- coding: utf-8 -*-
"""Сканер корпуса оптических систем из библиотек .LBO (TASK_CORPUS_SCAN).

Все системы каждой .LBO библиотеки прогоняются через конвейер порта
OPAL-PC: load → parse (system) → paraxial (efl finite) → seidel →
taboc1 → зрачки (entrance/exit pupil finite). Отказ этапа не валит
ни систему, ни скан: фиксируется в ops/error, скан продолжается.
Результат — один JSON (schema_version 1, контракт: docs/tasks/
CORPUS_PLAN.md): успехи/отказы по этапам, параксиальные метрики,
суммы Зейделя, TABOC1 и сверка f' «имя каталога vs расчёт»
(правила docs/LBO_FORMAT.md) — вход для corpus_stats.py и отчёта
по аномалиям корпуса.

CLI:
    py scripts/corpus_scan.py --lib <файл.LBO | каталог Lib> --out <.json>
                              [--limit N] [--quiet]

Коды возврата: 0 — скан дошёл до конца (отказ отдельной системы — не
ошибка скана); 2 — нет/неверен путь --lib или --out.
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

SCHEMA_VERSION = 1
OPS = ('load', 'parse', 'paraxial', 'seidel', 'taboc1', 'pupils')
WATER_N = 1.331  # показатель преломления воды — «Гидро»-объективы каталога

# f' из имени системы (порядок паттернов как в scripts/lbo_verify_f.py):
# f'=…, f=… (без апострофа — признак гидрообъектива), ф'/f' с пробелами
_F_PATTERNS = (
    (re.compile(r"f'=\s*(-?\d+(?:\.\d+)?)"), True),
    (re.compile(r"f=\s*(-?\d+(?:\.\d+)?)"), False),
    (re.compile(r"[fф]\s*'?\s*=\s*(-?\d+(?:\.\d+)?)"), None),
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
    if name_f is None or abs(name_f) < 1e-9:  # f=0 — сверка невозможна
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
    if abs(name_f) < 10 and 8 <= abs(calc / name_f) <= 25:
        fc['category'] = 'truncated'
    elif (calc > 0) != (name_f > 0) and \
            abs(abs(calc) - abs(name_f)) / abs(name_f) <= 0.05:
        fc['category'] = 'sign_flip'
    elif fc['err_pct'] <= 5:
        fc['category'] = 'ok'
    return fc


def _empty_metrics():
    """Шаблон metrics контракта (все ключи на месте, значения None)."""
    return dict.fromkeys((
        'efl', 'bfd', 'f_number', 'L', 'entrance_pupil', 'exit_pupil',
        'entrance_pupil_diameter', 'seidel_SI', 'seidel_SII', 'seidel_SIII',
        'seidel_SIV', 'seidel_SV', 'taboc1_rows', 'taboc1_ok',
        'taboc1_max_abs_longitudinal_mm'))


def scan_system(entry, lib, index):
    """Конвейер одной записи load_lbo → dict системы по контракту JSON."""
    ops = dict.fromkeys(OPS, False)
    why = {}  # op → сообщение об отказе (для error первого сбойного этапа)
    metrics = _empty_metrics()
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
        for op in ('paraxial', 'seidel', 'taboc1', 'pupils'):
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
    try:
        seidel = seidel_aberrations(system)
    except Exception as exc:  # noqa: BLE001
        why['seidel'] = _exc(exc)
    else:
        ops['seidel'] = True
        for key in ('SI', 'SII', 'SIII', 'SIV', 'SV'):
            metrics['seidel_' + key] = _finite(seidel.get(key))

    # taboc1: остаточные аберрации осевого пучка, хотя бы одна строка
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
    if not ops['paraxial']:
        why.setdefault('pupils', 'no paraxial data')
    elif metrics['entrance_pupil'] is None:
        why['pupils'] = 'entrance_pupil not finite'
    elif metrics['exit_pupil'] is None:
        why['pupils'] = 'exit_pupil not finite'
    else:
        ops['pupils'] = True

    rec['f_check'] = make_f_check(rec['name'] or '', metrics['efl'])
    for op in OPS:
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
                    '(контракт: docs/tasks/CORPUS_PLAN.md)')
    ap.add_argument('--lib', required=True,
                    help='файл .LBO или каталог с *.LBO (все по алфавиту)')
    ap.add_argument('--out', required=True,
                    help='выходной JSON (родительский каталог создаётся)')
    ap.add_argument('--limit', type=int, default=None,
                    help='первые N систем каждой библиотеки (по умолчанию все)')
    ap.add_argument('--quiet', action='store_true',
                    help='без прогресса в stdout')
    args = ap.parse_args(argv)

    lib_files = collect_lib_files(args.lib)
    if not lib_files:
        print(f'corpus_scan: --lib не найден или нет файлов .LBO: {args.lib}',
              file=sys.stderr)
        return 2

    systems = []
    ops_summary = {op: {'ok': 0, 'fail': 0} for op in OPS}
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
            rec = scan_system(entry, lib, i)
            systems.append(rec)
            for op in OPS:
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
