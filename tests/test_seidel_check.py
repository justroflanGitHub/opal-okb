# -*- coding: utf-8 -*-
"""A5 (TASK_SEIDEL): сверка сумм Зейделя порта — паритет независимой
реализации, знаки против трассировки 3-го порядка, golden .PRN
(sumsed): эталоны репозитория секции не содержат (skip), синтетическая
секция (масштаб ×1000 — отношения Sₖ/S1 инвариантны нормировке) —
числовая сверка.
"""
from pathlib import Path

import pytest

from analysis.seidel_check import (compare_with_tracing, parse_prn_seidel,
                                   seidel_sums, seidel_vs_golden)
from domain.calculations import seidel_aberrations
from domain.models import create_demo_system_by_name

GOLDEN_PRN = (Path(__file__).resolve().parents[1] / 'extracted'
              / 'opal_okb' / 'RT__2236.PRN')


def _sumsed_line(values, n=0):
    """Строка sumsed ``(' ',I3,5(F11.5),2F10.5)`` (переполнение — звёзды)."""
    def fw(v, w, d):
        s = f'{v:.{d}f}'
        return ('*' * w) if len(s) > w else s.rjust(w)
    line = ' ' + f'{n:3d}'
    line += ''.join(fw(v, 11, 5) for v in values[:5])
    line += ''.join(fw(v, 10, 5) for v in values[5:7])
    return line


# ── паритет независимой реализации с портом (зрачковые переносы) ────────────

@pytest.mark.parametrize('name', ['plano_convex', 'achromat',
                                  'cook_doublet', 'telephoto'])
def test_seidel_sums_parity_with_port(name):
    """Независимая реализация формул SI–SV (базисы порта: маргинальный
    y₀=1 + главный от стопа с переносами назад/вперёд) совпадает с
    ``domain.calculations.seidel_aberrations`` до 1e-9."""
    system = create_demo_system_by_name(name)
    port = seidel_aberrations(system)
    mine = seidel_sums(system)
    for key in ('SI', 'SII', 'SIII', 'SIV', 'SV'):
        assert mine[key] == pytest.approx(port[key], abs=1e-9), key


def test_chromatic_sums_present():
    """Хроматические суммы считаются между крайними рабочими λ; одна λ —
    нули и флаг chromatic=False."""
    system = create_demo_system_by_name('achromat')
    S = seidel_sums(system)
    assert S['chromatic']
    assert abs(S['SIxp']) > 1e-7
    assert S['wl_lo'] < S['wl_hi']


# ── тест 4: дублет — SI<0, знаки согласованы с трассировкой ─────────────────

@pytest.mark.parametrize('name', ['achromat', 'cook_doublet'])
def test_doublet_si_negative_and_signs_agree(name):
    """Дублет: SI<0 (положительная линза корректирует сферическую);
    знаки устойчивых пар (SIII-астигматизм, SV-дисторсия, SIхр-хроматизм)
    согласованы с трассировкой; порядок величин — мкм-аберрации при
    суммах 1e-4, линейный член осевого веера ~0 (контроль фокуса)."""
    system = create_demo_system_by_name(name)
    S = seidel_sums(system)
    assert S['SI'] < 0
    report = compare_with_tracing(system, field_y=2.0)
    assert 'error' not in report
    assert report['signs']['SIII_astig']
    assert report['signs']['SV_a0']
    assert report['signs']['SIxp_df']
    assert abs(report['axial']['c1_mm']) < 0.05 * abs(
        report['axial']['c3_mm'])
    assert 1e-3 < abs(report['axial']['c3_mm']) < 1e-1
    assert 1e-5 < abs(S['SI']) < 1e-2


# ── тест 5: golden .PRN ─────────────────────────────────────────────────────

def test_seidel_vs_golden_real_prn_skipped():
    """RT__2236.PRN секции сумм sumsed не содержит — сверка честно
    скипается с пояснением (парсер не находит строк формата)."""
    assert parse_prn_seidel(GOLDEN_PRN) == []
    system = create_demo_system_by_name('achromat')
    report = seidel_vs_golden(system, GOLDEN_PRN)
    assert report['status'] == 'skipped'
    assert 'sumsed' in report['reason']
    assert report['golden_rows'] == []


def test_parse_prn_seidel_synthetic(tmp_path):
    """Позиционный разбор строки sumsed: значения, переполнение
    (звёздочки → None), мусорные строки игнорируются."""
    line = _sumsed_line([-0.12345, 0.98765, -0.5, 0.25, -38.79583,
                         0.00012, 0.00035])
    prn = tmp_path / 'SYNTH.PRN'
    prn.write_text('СУММЫ ЗАБЕРРАЦИЙ ЗЕЙДЕЛЯ\n'
                   'мусорная строка без чисел\n'
                   + line + '\n', encoding='cp866')
    rows = parse_prn_seidel(prn)
    assert len(rows) == 1
    row = rows[0]
    assert row['n'] == 0
    assert row['S1'] == pytest.approx(-0.12345)
    assert row['S5'] == pytest.approx(-38.79583)


def test_seidel_vs_golden_synthetic_matched(tmp_path):
    """Синтетическая секция (суммы системы ×1000 — нормировка OPAL
    неизвестна, отношения Sₖ/S1 инвариантны): знаки всех сумм и
    отношения совпадают — matched (S5×1000 переполняет F11.5 —
    звёздочки, колонка пропускается)."""
    system = create_demo_system_by_name('achromat')
    S = seidel_sums(system)
    keys = ('SI', 'SII', 'SIII', 'SIV', 'SV', 'SIxp', 'SIIxp')
    line = _sumsed_line([1000.0 * S[k] for k in keys])
    prn = tmp_path / 'SYNTH.PRN'
    prn.write_text(line + '\n', encoding='cp866')
    report = seidel_vs_golden(system, prn)
    assert report['status'] == 'matched'
    assert all(report['signs'].values())
    assert report['ratios']['SII']['rel_dev'] < 0.05
    assert 'SV' not in report['ratios']       # переполнение F11.5
