# -*- coding: utf-8 -*-
"""Тесты сканера корпуса (scripts/corpus_scan.py) — TASK_CORPUS_SCAN, SA-4.

Тестируем строго против контрактов из docs/tasks/CORPUS_PLAN.md: «Контракт CLI
сканера» (--lib/--out/--limit/--quiet, коды возврата 0/2) и «Контракт JSON»
(schema_version 1). Полный корпус (612 систем) в тестах НЕ гоняется — только
--limit на маленьких выборках реальных библиотек.

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

# --------------------------------------------------------------------------- #
# Контракт JSON (schema_version 1) — точные наборы ключей из CORPUS_PLAN.md
# --------------------------------------------------------------------------- #

#: 6 операций конвейера: load → parse → paraxial → seidel → taboc1 → pupils.
OPS_KEYS = {'load', 'parse', 'paraxial', 'seidel', 'taboc1', 'pupils'}

#: Точный набор ключей системы (14 полей, ops — одно поле с 6 булевыми).
SYSTEM_KEYS = {
    'lib', 'index', 'name', 'filename', 'n_surfaces', 'n_wavelengths',
    'glasses', 'has_mirror', 'status', 'error', 'ops', 'metrics', 'f_check',
}

#: Точный набор метрик (15 полей; числа — float или null, не строки).
METRICS_KEYS = {
    'efl', 'bfd', 'f_number', 'L',
    'entrance_pupil', 'exit_pupil', 'entrance_pupil_diameter',
    'seidel_SI', 'seidel_SII', 'seidel_SIII', 'seidel_SIV', 'seidel_SV',
    'taboc1_rows', 'taboc1_ok', 'taboc1_max_abs_longitudinal_mm',
}

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
    """``py scripts/corpus_scan.py <args>`` → CompletedProcess.

    cwd — корень проекта (сканер обязан работать из любого cwd); вывод в
    UTF-8: консоль здесь cp1251, без PYTHONIOENCODING печать кириллицы
    (имена систем!) может упасть с UnicodeEncodeError.
    """
    return subprocess.run(
        ['py', str(SCAN_SCRIPT), *args],
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
    """Smoke: LENS.LBO --limit 5 — rc 0, валидный UTF-8 JSON, 5 систем
    с точным набором ключей контракта, status/ops/efl правильных типов."""
    proc, out = lens5_run
    assert proc.returncode == 0, _proc_msg(proc)
    data = _load_json(out)  # упадёт, если файл не UTF-8 / не JSON

    assert data['total'] == 5, f"total={data['total']}, ожидали 5"
    systems = data['systems']
    assert isinstance(systems, list), 'systems должен быть списком'
    assert len(systems) == 5, f'len(systems)={len(systems)}, ожидали 5'

    for i, s in enumerate(systems):
        assert set(s) == SYSTEM_KEYS, (
            f'система {i}: ключи {set(s) ^ SYSTEM_KEYS} расходятся с контрактом')
        assert s['status'] in ('ok', 'fail'), f'система {i}: status={s["status"]!r}'
        ops = s['ops']
        assert set(ops) == OPS_KEYS, (
            f'система {i}: ops-ключи {set(ops) ^ OPS_KEYS} расходятся')
        assert all(isinstance(v, bool) for v in ops.values()), (
            f'система {i}: ops должен быть 6 булевых полей, got {ops!r}')
        efl = s['metrics']['efl']
        assert efl is None or isinstance(efl, float), (
            f'система {i}: metrics.efl={efl!r} — должен быть float или null')


# --------------------------------------------------------------------------- #
# 2. Стабильность схемы JSON
# --------------------------------------------------------------------------- #

@requires_data
@requires_script
def test_json_schema_stable(lens5_run):
    """Схема стабильна: schema_version==1, tool, верхние ключи контракта,
    ops_summary по 6 стадиям, metrics — РОВНО 15 ключей контракта."""
    _, out = lens5_run
    data = _load_json(out)

    assert data['schema_version'] == 1, (
        f"schema_version={data['schema_version']!r}, ожидали 1")
    assert data['tool'] == 'corpus_scan.py', f"tool={data['tool']!r}"

    missing = TOP_KEYS - set(data)
    assert not missing, f'нет верхних ключей контракта: {missing}'
    assert isinstance(data['generated'], str) and data['generated'], (
        'generated должен быть непустой ISO-датой')

    ops_summary = data['ops_summary']
    missing_ops = OPS_KEYS - set(ops_summary)
    assert not missing_ops, f'ops_summary не содержит стадии: {missing_ops}'
    for stage in OPS_KEYS:
        entry = ops_summary[stage]
        assert {'ok', 'fail'} <= set(entry), (
            f'ops_summary[{stage}] без ok/fail: {entry!r}')

    for i, s in enumerate(data['systems']):
        extra = set(s['metrics']) - METRICS_KEYS
        gone = METRICS_KEYS - set(s['metrics'])
        assert not extra and not gone, (
            f'система {i}: metrics расходится с контрактом '
            f'(лишние {extra}, отсутствуют {gone})')
        assert set(s['ops']) == OPS_KEYS, f'система {i}: ops не 6 стадий'


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
