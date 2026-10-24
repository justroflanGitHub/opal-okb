# -*- coding: utf-8 -*-
"""Тесты сканера корпуса (scripts/corpus_scan.py) — TASK_CORPUS_SCAN, SA-4,
плюс волна 2 (TASK_CORPUS_SCAN_V2): CLI --ops, schema_version 2, 13 новых
метрик, читатель обоих schema — scripts/corpus_stats.py.

Тестируем строго против контрактов из docs/tasks/CORPUS_PLAN.md: «Контракт CLI
сканера» (--lib/--out/--limit/--quiet, коды возврата 0/2), «Контракт JSON» и
«Контракт v2» (schema_version 2). Полный корпус (612 систем) в тестах НЕ
гоняется — только --limit на маленьких выборках реальных библиотек.

Данные .LBO — read-only, вне git и вне этого worktree (лежат в main checkout),
поэтому штатный requires_lbo из tests/conftest.py здесь не срабатывает
(он ищет extracted/ относительно корня проекта). Используется локальный
детектор: переменная окружения OPAL_LBO_DIR либо путь по умолчанию.

Сам сканер пишет параллельный агент (SA-1). Пока scripts/corpus_scan.py нет,
все тесты честно скипаются: без этой защиты CLI-тесты прошли бы ЛОЖНО —
`py` на отсутствующем файле тоже возвращает код 2.
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Пути и детекторы ресурсов
# --------------------------------------------------------------------------- #

#: Корень проекта — cwd subprocess'ов и база для пути к сканеру.
BASE_DIR = Path(__file__).resolve().parent.parent
SCAN_SCRIPT = BASE_DIR / 'scripts' / 'corpus_scan.py'

#: Реальные .LBO — абсолютный путь в основной папке (в worktree данных нет).
LBO_DIR = Path(os.environ.get(
    'OPAL_LBO_DIR',
    r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib'))
LENS_LBO = LBO_DIR / 'LENS.LBO'
LENS_SPC_LBO = LBO_DIR / 'LENS_SPC.LBO'

HAS_DATA = LENS_LBO.is_file()
requires_data = pytest.mark.skipif(
    not HAS_DATA,
    reason='нет Lib/LENS.LBO (данные не в git; задай OPAL_LBO_DIR)')

#: Сканер — соседняя подзадача SA-1; без него честный skip.
HAS_SCRIPT = SCAN_SCRIPT.is_file()
requires_script = pytest.mark.skipif(
    not HAS_SCRIPT,
    reason='нет scripts/corpus_scan.py — сканер (SA-1) ещё не готов')

#: Читатель обоих schema (v1/v2) — соседняя подзадача SA-2; без него skip.
STATS_SCRIPT = BASE_DIR / 'scripts' / 'corpus_stats.py'
HAS_STATS = STATS_SCRIPT.is_file()
requires_stats = pytest.mark.skipif(
    not HAS_STATS,
    reason='нет scripts/corpus_stats.py — статистика (SA-2) ещё не готова')

# --------------------------------------------------------------------------- #
# Контракт JSON (schema_version 2) — точные наборы ключей из CORPUS_PLAN.md
# (разделы «Контракт JSON» и «Контракт v2»)
# --------------------------------------------------------------------------- #

#: 6 базовых операций волны 1: load → parse → paraxial → seidel → taboc1 →
#: pupils (полный конвейер --ops all — см. OPS_ALL_KEYS).
OPS_KEYS = {'load', 'parse', 'paraxial', 'seidel', 'taboc1', 'pupils'}

#: 4 новые операции волны 2 (v2-хвост конвейера).
OPS_V2_KEYS = {'vignette', 'chief', 'spot', 'mtf_geo'}

#: Полный конвейер --ops all (дефолт): 6 базовых + 4 новых.
OPS_ALL_KEYS = OPS_KEYS | OPS_V2_KEYS

#: Точный набор ключей системы (14 полей, ops — одно поле с 6 булевыми).
SYSTEM_KEYS = {
    'lib', 'index', 'name', 'filename', 'n_surfaces', 'n_wavelengths',
    'glasses', 'has_mirror', 'status', 'error', 'ops', 'metrics', 'f_check',
}

#: Точный набор метрик волны 1 (15 полей; числа — float или null, не строки).
METRICS_KEYS = {
    'efl', 'bfd', 'f_number', 'L',
    'entrance_pupil', 'exit_pupil', 'entrance_pupil_diameter',
    'seidel_SI', 'seidel_SII', 'seidel_SIII', 'seidel_SIV', 'seidel_SV',
    'taboc1_rows', 'taboc1_ok', 'taboc1_max_abs_longitudinal_mm',
}

#: 13 новых ключей metrics волны 2 (float | null; null при отказе операции,
#: у безполевой системы null валиден для полевых ключей).
V2_METRICS_KEYS = {
    'vignette_max_field', 'vignette_up_pct', 'vignette_down_pct',
    'chief_max_field', 'distortion_pct', 'astig_Zm_mm', 'astig_Zs_mm',
    'spot_rms_axis_um', 'spot_rms_max_field_um',
    'mtf30_axis', 'mtf50_axis', 'mtf30_max_field', 'mtf50_max_field',
}

#: Новая операция → её ключи metrics (зеркало _V2_METRICS сканера).
V2_METRICS_BY_OP = {
    'vignette': {'vignette_max_field', 'vignette_up_pct',
                 'vignette_down_pct'},
    'chief': {'chief_max_field', 'distortion_pct', 'astig_Zm_mm',
              'astig_Zs_mm'},
    'spot': {'spot_rms_axis_um', 'spot_rms_max_field_um'},
    'mtf_geo': {'mtf30_axis', 'mtf50_axis', 'mtf30_max_field',
                'mtf50_max_field'},
}

#: Полный набор metrics полного прогона: 15 базовых + 13 новых.
FULL_METRICS_KEYS = METRICS_KEYS | V2_METRICS_KEYS

#: Обязательные верхние ключи JSON (кроме них есть tool/schema_version/limit).
TOP_KEYS = {
    'total', 'ok', 'fail', 'ops_summary', 'systems', 'source', 'generated',
}

#: Поля f_check (null, если в имени нет f= / f'= / ф'=).
F_CHECK_KEYS = {'name_f', 'calc_f', 'err_pct', 'category'}

#: Категории f_check из контракта («no_f» нет — без f в имени f_check = null).
F_CATEGORIES = {'ok', 'sign_flip', 'hydro', 'truncated', 'diverge'}


# --------------------------------------------------------------------------- #
# Хелперы запуска
# --------------------------------------------------------------------------- #

def run_scan(args, timeout=300):
    """``<python> scripts/corpus_scan.py <args>`` → CompletedProcess.

    cwd — корень проекта (сканер обязан работать из любого cwd); вывод в
    UTF-8: консоль здесь cp1251, без PYTHONIOENCODING печать кириллицы
    (имена систем!) может упасть с UnicodeEncodeError.
    Интерпретатор — текущий (sys.executable), а не лаунчер `py`:
    на CI py-лаунчер резолвится в системный Python без пакетов
    (numpy и пр.), отличного от окружения pytest (setup-python).
    """
    return subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), *args],
        capture_output=True, text=True,
        encoding='utf-8', errors='replace',
        cwd=str(BASE_DIR), timeout=timeout,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )


def run_scan_args(lib, out_path, limit=None, quiet=True):
    """Сборка аргументов прогона и сам прогон → CompletedProcess."""
    args = ['--lib', str(lib), '--out', str(out_path)]
    if limit is not None:
        args += ['--limit', str(limit)]
    if quiet:
        args.append('--quiet')
    return run_scan(args)


def run_scan_ops(lib, out_path, ops, limit=None, quiet=True):
    """Как run_scan_args, но с явным --ops (контракт v2: all|base|v2|список)."""
    args = ['--lib', str(lib), '--out', str(out_path), '--ops', ops]
    if limit is not None:
        args += ['--limit', str(limit)]
    if quiet:
        args.append('--quiet')
    return run_scan(args)


def run_stats(args, timeout=120):
    """``<python> scripts/corpus_stats.py <args>`` → CompletedProcess.

    Тот же стиль окружения, что run_scan: cwd — корень проекта, UTF-8,
    интерпретатор — текущий (sys.executable), а не лаунчер `py`.
    """
    return subprocess.run(
        [sys.executable, str(STATS_SCRIPT), *args],
        capture_output=True, text=True,
        encoding='utf-8', errors='replace',
        cwd=str(BASE_DIR), timeout=timeout,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )


def _proc_msg(proc):
    """Читаемая диагностика для assert'а по CompletedProcess."""
    return (f'rc={proc.returncode}\n--- stdout ---\n{proc.stdout[-2000:]}'
            f'\n--- stderr ---\n{proc.stderr[-2000:]}')


def _num_equal(a, b):
    """Точное равенство чисел из JSON: None совпадает только с None,
    NaN (нестандартный, но возможный литерал json) — с таким же NaN."""
    if a is None or b is None:
        return a is None and b is None
    if (isinstance(a, float) and isinstance(b, float)
            and math.isnan(a) and math.isnan(b)):
        return True
    return a == b


# --------------------------------------------------------------------------- #
# Fixture'ы: один subprocess на модуль, tmp — вне репозитория
# --------------------------------------------------------------------------- #

@pytest.fixture(scope='module')
def lens5_run(tmp_path_factory):
    """Прогон сканера на LENS.LBO --limit 5 → (CompletedProcess, путь JSON).

    Дублирующая skip-защита fixture — маркеры может кто-то снять при рефакторе.
    """
    if not HAS_DATA:
        pytest.skip('нет Lib/LENS.LBO (данные не в git; задай OPAL_LBO_DIR)')
    if not HAS_SCRIPT:
        pytest.skip('нет scripts/corpus_scan.py — сканер (SA-1) ещё не готов')
    out = tmp_path_factory.mktemp('corpus_scan') / 'lens5.json'
    proc = run_scan_args(LENS_LBO, out, limit=5)
    return proc, out


@pytest.fixture(scope='module')
def lens20_run(tmp_path_factory):
    """Прогон сканера на LENS.LBO --limit 20 → (CompletedProcess, путь JSON).

    20 систем хватает, чтобы гарантированно встретить f_check != null
    (уже LENS[0] — Индустар-7 f'=104). Полный корпус не гоняем.
    """
    if not HAS_DATA:
        pytest.skip('нет Lib/LENS.LBO (данные не в git; задай OPAL_LBO_DIR)')
    if not HAS_SCRIPT:
        pytest.skip('нет scripts/corpus_scan.py — сканер (SA-1) ещё не готов')
    out = tmp_path_factory.mktemp('corpus_scan') / 'lens20.json'
    proc = run_scan_args(LENS_LBO, out, limit=20)
    return proc, out


def _load_json(path):
    """JSON из файла сканера, строго UTF-8 (контракт: ensure_ascii=False)."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


# --------------------------------------------------------------------------- #
# 1. Smoke: LENS --limit 5
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_smoke_lens_limit_5(lens5_run):
    """Smoke: LENS.LBO --limit 5 — rc 0, валидный UTF-8 JSON, schema 2,
    5 систем с точным набором ключей контракта, status/ops/efl правильных
    типов (полный прогон --ops all — 10 булевых полей ops)."""
    proc, out = lens5_run
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)  # упадёт, если файл не UTF-8 / не JSON

    assert data['schema_version'] == 2, (
        f"schema_version={data['schema_version']!r}, ожидали 2")
    assert data['total'] == 5, f"total={data['total']}, ожидали 5"
    systems = data['systems']
    assert isinstance(systems, list), 'systems должен быть списком'
    assert len(systems) == 5, f'len(systems)={len(systems)}, ожидали 5'

    for i, s in enumerate(systems):
        assert set(s) == SYSTEM_KEYS, (
            f'система {i}: ключи {set(s) ^ SYSTEM_KEYS} расходятся с контрактом')
        assert s['status'] in ('ok', 'fail'), f'система {i}: status={s["status"]!r}'
        ops = s['ops']
        assert set(ops) == OPS_ALL_KEYS, (
            f'система {i}: ops-ключи {set(ops) ^ OPS_ALL_KEYS} расходятся')
        assert all(isinstance(v, bool) for v in ops.values()), (
            f'система {i}: ops должен быть 10 булевых полей, got {ops!r}')
        efl = s['metrics']['efl']
        assert efl is None or isinstance(efl, float), (
            f'система {i}: metrics.efl={efl!r} — должен быть float или null')


# --------------------------------------------------------------------------- #
# 2. Стабильность схемы JSON
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_json_schema_stable(lens5_run):
    """Схема стабильна: schema_version==2, tool, верхние ключи контракта,
    ops_summary по всем 10 стадиям, metrics — РОВНО 15 базовых + 13 новых
    ключей контракта v2."""
    _, out = lens5_run
    data = _load_json(out)

    assert data['schema_version'] == 2, (
        f"schema_version={data['schema_version']!r}, ожидали 2")
    assert data['tool'] == 'corpus_scan.py', f"tool={data['tool']!r}"

    missing = TOP_KEYS - set(data)
    assert not missing, f'нет верхних ключей контракта: {missing}'
    assert isinstance(data['generated'], str) and data['generated'], (
        'generated должен быть непустой ISO-датой')

    ops_summary = data['ops_summary']
    missing_ops = OPS_ALL_KEYS - set(ops_summary)
    assert not missing_ops, f'ops_summary не содержит стадии: {missing_ops}'
    for stage in OPS_ALL_KEYS:
        entry = ops_summary[stage]
        assert {'ok', 'fail'} <= set(entry), (
            f'ops_summary[{stage}] без ok/fail: {entry!r}')

    for i, s in enumerate(data['systems']):
        extra = set(s['metrics']) - FULL_METRICS_KEYS
        gone = FULL_METRICS_KEYS - set(s['metrics'])
        assert not extra and not gone, (
            f'система {i}: metrics расходится с контрактом '
            f'(лишние {extra}, отсутствуют {gone})')
        assert set(s['ops']) == OPS_ALL_KEYS, f'система {i}: ops не 10 стадий'


# --------------------------------------------------------------------------- #
# 3. Консистентность итогов
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_totals_consistency(lens5_run):
    """Итоги сходятся: ok+fail==total==len(systems); ok-системы — все 6 ops
    true и error is None; ok не больше paraxial.ok (ok строгое подмножество)."""
    _, out = lens5_run
    data = _load_json(out)

    total, ok, fail = data['total'], data['ok'], data['fail']
    assert ok + fail == total, f'ok({ok}) + fail({fail}) != total({total})'
    assert total == len(data['systems']), (
        f'total({total}) != len(systems)({len(data["systems"])})')

    paraxial_ok = data['ops_summary']['paraxial']['ok']
    assert ok <= paraxial_ok, (
        f'ok({ok}) > ops_summary.paraxial.ok({paraxial_ok}) — '
        f'ok-система обязана пройти paraxial')

    for i, s in enumerate(data['systems']):
        if s['status'] == 'ok':
            failed_ops = [k for k, v in s['ops'].items() if not v]
            assert not failed_ops, (
                f'система {i} ok, но ops false: {failed_ops}')
            assert s['error'] is None, (
                f'система {i} ok, но error={s["error"]!r}')


# --------------------------------------------------------------------------- #
# 4. Детерминизм: два прогона --limit 3
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_determinism_limit_3(tmp_path):
    """Два прогона LENS_SPC.LBO (6 систем; нет файла — LENS.LBO) --limit 3:
    metrics.efl попарно равны точно (float ==), имена равны."""
    lib = LENS_SPC_LBO if LENS_SPC_LBO.is_file() else LENS_LBO
    out1, out2 = tmp_path / 'det1.json', tmp_path / 'det2.json'

    proc1 = run_scan_args(lib, out1, limit=3)
    proc2 = run_scan_args(lib, out2, limit=3)
    assert proc1.returncode == 0, _proc_msg(proc1)
    assert proc2.returncode == 0, _proc_msg(proc2)

    d1, d2 = _load_json(out1), _load_json(out2)
    s1, s2 = d1['systems'], d2['systems']
    assert len(s1) == len(s2) == 3, f'{len(s1)} vs {len(s2)}, ожидали по 3'

    for i, (a, b) in enumerate(zip(s1, s2)):
        assert a['name'] == b['name'], (
            f'#{i}: имена разошлись: {a["name"]!r} vs {b["name"]!r}')
        efl_a, efl_b = a['metrics']['efl'], b['metrics']['efl']
        assert _num_equal(efl_a, efl_b), (
            f'#{i} ({a["name"]!r}): efl недетерминирован: {efl_a!r} vs {efl_b!r}')


# --------------------------------------------------------------------------- #
# 5. CLI-парсер и коды возврата (данные не нужны, нужен сканер)
# --------------------------------------------------------------------------- #

@requires_script
class TestCLICodes:
    """Коды возврата CLI: 2 — неверный путь/аргументы (контракт CORPUS_PLAN)."""

    def test_lib_not_found_rc2(self, tmp_path):
        """--lib с несуществующим путём → rc 2, сообщение в stderr."""
        missing = tmp_path / 'no_such_lib.LBO'
        assert not missing.exists()
        proc = run_scan(['--lib', str(missing), '--out',
                         str(tmp_path / 'out.json')])
        assert proc.returncode == 2, _proc_msg(proc)
        assert proc.stderr.strip(), 'ожидали сообщение об ошибке в stderr'

    def test_limit_without_lib_rc2(self, tmp_path):
        """--limit без обязательного --lib → rc 2 (argparse required)."""
        proc = run_scan(['--limit', '5', '--out', str(tmp_path / 'out.json')])
        assert proc.returncode == 2, _proc_msg(proc)
        assert proc.stderr.strip(), 'ожидали сообщение об ошибке в stderr'

    def test_lib_dir_without_lbo_rc2(self, tmp_path):
        """--lib на каталоге без .LBO → rc 2 (нечего сканировать)."""
        empty = tmp_path / 'empty_lib'
        empty.mkdir()
        proc = run_scan(['--lib', str(empty), '--out',
                         str(tmp_path / 'out.json')])
        assert proc.returncode == 2, _proc_msg(proc)


# --------------------------------------------------------------------------- #
# 6. f_check: категории и арифметика err_pct
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_f_check_categories(lens20_run):
    """f_check sanity: категории из контракта; для ok — 0 <= err_pct <= 5;
    при равных знаках name_f/calc_f err_pct == |calc-name|/|name|*100
    (точность 0.01 п.п.; hydro исключён — там |calc*1.331| по контракту)."""
    proc, out = lens20_run
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)

    checked = [s for s in data['systems'] if s.get('f_check') is not None]
    assert checked, (
        "в LENS --limit 20 не нашлось систем с f_check != null "
        "(уже LENS[0] Индустар-7 должен давать f'=104)")

    for s in checked:
        fc = s['f_check']
        assert isinstance(fc, dict), f'{s["name"]!r}: f_check не dict'
        missing = F_CHECK_KEYS - set(fc)
        assert not missing, f'{s["name"]!r}: f_check без ключей {missing}'
        assert fc['category'] in F_CATEGORIES, (
            f'{s["name"]!r}: category={fc["category"]!r} не из контракта')

        if fc['category'] == 'ok' and fc['err_pct'] is not None:
            assert 0.0 <= fc['err_pct'] <= 5.0, (
                f'{s["name"]!r}: category ok, но err_pct={fc["err_pct"]}')

        name_f, calc_f, err = fc['name_f'], fc['calc_f'], fc['err_pct']
        # Формула err_pct = |calc-name|/|name|*100 верна для всех категорий,
        # кроме hydro (там фокус в воде: |calc*1.331|) — его пропускаем.
        if (err is not None and name_f and calc_f
                and (name_f > 0) == (calc_f > 0)
                and fc['category'] != 'hydro'):
            expected = abs(calc_f - name_f) / abs(name_f) * 100.0
            assert abs(err - expected) <= 0.01, (
                f'{s["name"]!r}: err_pct={err}, а по формуле {expected:.4f}')


# --------------------------------------------------------------------------- #
# 7. Smoke v2-операций: новые метрики на LENS --limit 5 (--ops all)
# --------------------------------------------------------------------------- #

def _is_number(v):
    """Конечное число (не bool) — «разумный» тип метрики из JSON."""
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v))


@requires_data
@requires_script
def test_v2_metrics_lens5(lens5_run):
    """Smoke v2-операций (LENS --limit 5, полный конвейер): все 5 систем
    проходят базовые ops; у ok-систем все 13 новых метрик — конечные числа
    (контрасты в [0..1], осевой RMS > 0); у fail-систем (если есть) error
    начинается с имени нового этапа, а его v2-метрики null."""
    _, out = lens5_run
    data = _load_json(out)

    base_fails = [s for s in data['systems']
                  if not all(s['ops'][op] for op in OPS_KEYS)]
    assert not base_fails, (
        'LENS --limit 5: отказ базовых ops у систем '
        f'{[s["name"] for s in base_fails]}')

    for s in data['systems']:
        if s['status'] == 'ok':
            m = s['metrics']
            for key in V2_METRICS_KEYS:
                assert _is_number(m[key]), (
                    f'{s["name"]!r}: metrics.{key}={m[key]!r} — у ok-системы '
                    'ожидалось конечное число')
            assert m['spot_rms_axis_um'] > 0, (
                f'{s["name"]!r}: spot_rms_axis_um={m["spot_rms_axis_um"]!r} '
                '— ожидали положительный осевой RMS')
            for key in ('mtf30_axis', 'mtf50_axis'):
                assert 0.0 <= m[key] <= 1.0, (
                    f'{s["name"]!r}: {key}={m[key]!r} — контраст вне [0..1]')
        else:
            prefix = (s['error'] or '').split(':', 1)[0].strip()
            if prefix in OPS_V2_KEYS:
                for key in V2_METRICS_BY_OP[prefix]:
                    assert s['metrics'][key] is None, (
                        f'{s["name"]!r}: отказ {prefix}, но metrics.{key} '
                        f'={s["metrics"][key]!r} — ожидали null')


# --------------------------------------------------------------------------- #
# 8. CLI --ops: base / v2 / список / неизвестное имя / дефолт == all
# --------------------------------------------------------------------------- #

@pytest.fixture(scope='module')
def lens5_ops_runs(tmp_path_factory):
    """Прогоны CLI --ops на LENS.LBO --limit 5 → {режим: (proc, путь JSON)}.

    По одному subprocess на модуль для режимов base/v2/spot/all — тесты
    CLI --ops переиспользуют одни и те же JSON. Режим 'all' нужен тесту
    сравнения с дефолтным прогоном (lens5_run — всегда без --ops).
    """
    if not HAS_DATA:
        pytest.skip('нет Lib/LENS.LBO (данные не в git; задай OPAL_LBO_DIR)')
    if not HAS_SCRIPT:
        pytest.skip('нет scripts/corpus_scan.py — сканер (SA-1) ещё не готов')
    out_dir = tmp_path_factory.mktemp('corpus_ops')
    runs = {}
    for ops in ('base', 'v2', 'spot', 'all'):
        out = out_dir / f'lens5_{ops}.json'
        runs[ops] = (run_scan_ops(LENS_LBO, out, ops=ops, limit=5), out)
    return runs


@requires_data
@requires_script
def test_cli_ops_base(lens5_ops_runs):
    """--ops base: ровно 6 базовых стадий в ops/ops_summary и ровно 15
    базовых метрик без v2-ключей (побитово набор волны 1)."""
    proc, out = lens5_ops_runs['base']
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)

    assert set(data['ops_summary']) == OPS_KEYS, (
        f"ops_summary: {set(data['ops_summary']) ^ OPS_KEYS} расходятся")
    for i, s in enumerate(data['systems']):
        assert set(s['ops']) == OPS_KEYS, (
            f'система {i}: ops-ключи {set(s["ops"]) ^ OPS_KEYS} расходятся')
        assert set(s['metrics']) == METRICS_KEYS, (
            f'система {i}: --ops base должен давать ровно 15 базовых метрик, '
            f'расхождение {set(s["metrics"]) ^ METRICS_KEYS}')


@requires_data
@requires_script
def test_cli_ops_v2(lens5_ops_runs):
    """--ops v2: ops = load/parse + 4 новые стадии; из новых метрик есть
    только 13 v2-ключей (15 базовых всегда на месте по контракту)."""
    proc, out = lens5_ops_runs['v2']
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)

    v2_ops = {'load', 'parse'} | OPS_V2_KEYS
    full_metrics = METRICS_KEYS | V2_METRICS_KEYS
    assert set(data['ops_summary']) == v2_ops, (
        f"ops_summary: {set(data['ops_summary']) ^ v2_ops} расходятся")
    for i, s in enumerate(data['systems']):
        assert set(s['ops']) == v2_ops, (
            f'система {i}: ops-ключи {set(s["ops"]) ^ v2_ops} расходятся')
        assert set(s['metrics']) == full_metrics, (
            f'система {i}: --ops v2 — metrics {set(s["metrics"]) ^ full_metrics} '
            'расходятся с 15 базовыми + 13 v2')


@requires_data
@requires_script
def test_cli_ops_list_spot(lens5_ops_runs):
    """--ops spot (список имён): ops = load/parse/spot; из новых метрик —
    только две spot-метрики (базовые 15 всегда на месте)."""
    proc, out = lens5_ops_runs['spot']
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)

    spot_ops = {'load', 'parse', 'spot'}
    spot_metrics = METRICS_KEYS | V2_METRICS_BY_OP['spot']
    assert set(data['ops_summary']) == spot_ops, (
        f"ops_summary: {set(data['ops_summary']) ^ spot_ops} расходятся")
    for i, s in enumerate(data['systems']):
        assert set(s['ops']) == spot_ops, (
            f'система {i}: ops-ключи {set(s["ops"]) ^ spot_ops} расходятся')
        assert set(s['metrics']) == spot_metrics, (
            f'система {i}: --ops spot — metrics '
            f'{set(s["metrics"]) ^ spot_metrics} расходятся')


@requires_data
@requires_script
def test_cli_ops_default_eq_all(lens5_ops_runs, lens5_run):
    """Дефолт (без --ops; lens5_run всегда запускается без флага) и явный
    --ops all дают одинаковые наборы ключей ops/metrics/ops_summary."""
    proc_all, out_all = lens5_ops_runs['all']
    assert proc_all.returncode == 0, _proc_msg(proc_all)
    d_def = _load_json(lens5_run[1])
    d_all = _load_json(out_all)

    assert set(d_all['ops_summary']) == set(d_def['ops_summary']), (
        'ops_summary дефолта и --ops all различаются')
    assert len(d_all['systems']) == len(d_def['systems']) == 5
    for i, (a, b) in enumerate(zip(d_all['systems'], d_def['systems'])):
        assert set(a['ops']) == set(b['ops']), f'система {i}: ops'
        assert set(a['metrics']) == set(b['metrics']), f'система {i}: metrics'


@requires_script
def test_cli_ops_unknown_rc2(tmp_path):
    """--ops с неизвестным именем → код возврата 2 (контракт v2) и сообщение
    в stderr; --ops проверяется до чтения --lib, данные не нужны."""
    proc = run_scan(['--lib', str(tmp_path / 'no_such.LBO'), '--out',
                     str(tmp_path / 'out.json'), '--ops', 'bogus'])
    assert proc.returncode == 2, _proc_msg(proc)
    assert '--ops' in proc.stderr, (
        f'в stderr нет упоминания --ops: {proc.stderr[-500:]!r}')


# --------------------------------------------------------------------------- #
# 9. corpus_stats.py — читатель JSON schema 1 и 2 (backwards-compat)
# --------------------------------------------------------------------------- #

#: Заголовки секций волны 2 отчёта — выводятся только для schema_version 2.
V2_SECTION_HEADERS = (
    '## RMS пятна (spot)',
    '## Дисторсия (chief)',
    '## Астигматизм (chief)',
    '## ЧКХ (mtf_geo)',
    '## Корреляция «RMS поле/ось» (spot)',
    '## Аномалии v2',
    '## Отказы v2 (базовый конвейер прошёл)',
)

#: Реалистичные v2-значения (Индустар-7 из фактического прогона --limit 5).
_SYNTH_V2_VALUES = {
    'vignette_max_field': 21.6, 'vignette_up_pct': 2.923,
    'vignette_down_pct': 45.963,
    'chief_max_field': 21.6, 'distortion_pct': -0.572,
    'astig_Zm_mm': -0.248, 'astig_Zs_mm': -0.934,
    'spot_rms_axis_um': 49.149, 'spot_rms_max_field_um': 65.286,
    'mtf30_axis': 0.103, 'mtf50_axis': 0.074,
    'mtf30_max_field': 0.0095, 'mtf50_max_field': 0.0013,
}


def _synth_system(index, name, with_v2):
    """Синтетическая система контракта: базовые ключи всегда; v2-ключи
    в metrics и 10 ops — только для schema 2 (with_v2)."""
    metrics = dict.fromkeys(METRICS_KEYS)
    metrics['efl'] = 103.84 if index == 0 else 80.445
    ops = OPS_KEYS
    if with_v2:
        metrics.update(dict.fromkeys(V2_METRICS_KEYS))
        metrics.update(_SYNTH_V2_VALUES)
        ops = OPS_ALL_KEYS
    fc = {'name_f': 104.0 if index == 0 else 80.0,
          'calc_f': metrics['efl'],
          'err_pct': 0.154 if index == 0 else 0.55,
          'category': 'ok' if index == 0 else 'hydro'}
    return {
        'lib': 'LENS', 'index': index, 'name': name,
        'filename': f'IND{index}.OPJ',
        'n_surfaces': 8, 'n_wavelengths': 3,
        'glasses': ['К8', 'Ф1'], 'has_mirror': False,
        'status': 'ok', 'error': None,
        'ops': dict.fromkeys(ops, True),
        'metrics': metrics, 'f_check': fc,
    }


def _synth_scan_json(schema_version):
    """Минимальный валидный JSON сканера schema 1|2 — вход corpus_stats."""
    with_v2 = schema_version == 2
    ops = OPS_ALL_KEYS if with_v2 else OPS_KEYS
    systems = [
        _synth_system(0, "Индустар-7   f'=104  2w=24 1:3.5 4линзы", with_v2),
        _synth_system(1, 'Гидро-объектив  f=80', with_v2),
    ]
    return {
        'tool': 'corpus_scan.py', 'schema_version': schema_version,
        'generated': '2026-10-24T00:00:00+03:00',
        'source': ['X:/Lib/LENS.LBO'], 'limit': None,
        'total': 2, 'ok': 2, 'fail': 0,
        'ops_summary': {op: {'ok': 2, 'fail': 0} for op in ops},
        'systems': systems,
    }


@requires_stats
def test_stats_reads_v1_json(tmp_path):
    """corpus_stats читает v1-JSON (schema 1): rc 0; v1-секции («Обзор»,
    «Сверка f'») есть, v2-секций нет — поведение волны 1 без изменений."""
    src = tmp_path / 'synth_v1.json'
    src.write_text(json.dumps(_synth_scan_json(1), ensure_ascii=False),
                   encoding='utf-8')
    out = tmp_path / 'synth_v1.md'
    proc = run_stats(['--json', str(src), '--out', str(out)])
    assert proc.returncode == 0, _proc_msg(proc)

    text = out.read_text(encoding='utf-8')
    assert '## Обзор' in text, 'v1-отчёт без секции «Обзор»'
    assert "## Сверка f'" in text, "v1-отчёт без секции «Сверка f'»"
    for header in V2_SECTION_HEADERS:
        assert header not in text, (
            f'v1-отчёт не должен содержать v2-секцию {header!r}')


@requires_stats
def test_stats_reads_v2_json(tmp_path):
    """corpus_stats читает v2-JSON (schema 2): rc 0; все v2-секции на месте
    (и базовые v1-секции тоже)."""
    src = tmp_path / 'synth_v2.json'
    src.write_text(json.dumps(_synth_scan_json(2), ensure_ascii=False),
                   encoding='utf-8')
    out = tmp_path / 'synth_v2.md'
    proc = run_stats(['--json', str(src), '--out', str(out)])
    assert proc.returncode == 0, _proc_msg(proc)

    text = out.read_text(encoding='utf-8')
    assert '## Обзор' in text, 'v2-отчёт без секции «Обзор»'
    assert "## Сверка f'" in text, "v2-отчёт без секции «Сверка f'»"
    for header in V2_SECTION_HEADERS:
        assert header in text, f'v2-отчёт без секции {header!r}'
