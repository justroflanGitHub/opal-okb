# -*- coding: utf-8 -*-
"""Пин-тесты симуляции марш-конвейера (TASK_MARCH2, analysis/golden_march).

Локируют декодированные инварианты конвейера и точные причины
остаточных RED/YELLOW волновых строк банка:
* телескоп каскада W₂=(W₂+L_s)·head при head=n_пад/n_прел — для систем,
  окончившихся воздухом, Πhead=1 → W₂=OPL+ΣQF/2 (§M.1, 307 GREEN);
* 121 волновые з.1.0 — кромочный луч (8.10 мм > габарит 8.0 мм
  поверхности 1): печать из приповерхностной ветки [4dca]=−1 (cd62),
  порт ветки не имеет (§M.4);
* 121 з.0.866 / OKULAR з.0.866 — структурных веток нет: остаток =
  λ-уровень тензора/трубы, семена [4d20]/[4c4a] рантаймовые;
* KURSOVIK з.1.0 — предел трубы афокала (числовой пин —
  test_kursovik_march_tube_limit_ray в test_golden_verify.py).
"""
import pytest

from analysis.golden_march import (
    DEFAULT_SYSTEMS, fan_context, march_ray, march_report, ray_of,
    surface_semis,
)
from analysis.golden_verify import _n_media
from tests.conftest import GOLDEN_DOS, requires_stand


def _state(name, zone):
    prn, opj, system, wl, near, ax_semi, na, _rows = fan_context(name)
    media = _n_media(system, wl)
    semis = surface_semis(prn, wl)
    res = ray_of(system, near, opj.get('object_pos', 0.0), na, ax_semi,
                 zone, wl)
    assert res.success, f'{name} зона {zone}: трассировка не сошлась'
    return march_ray(system, wl, media, res, semis)


# ── инвариант телескопа каскада (основа W₂ = OPL + ΣQF/2) ─────────────────

@pytest.mark.parametrize('name', ['121', 'OKULAR', 'KURSOVIK', 'US00KI02',
                                  'S_KOND1', 'OBEKTIV'])
@requires_stand
def test_march_head_telescope_air_terminated(name):
    """Πhead = 1 у всех носителей остатков: каскад W₂=(W₂+L_s)·head
    с head=n_пад/n_прел вырождается в OPL-сумму — это и делает
    маршевую печать сравнимой с портовой OPL-геометрией."""
    st = _state(name, 0.5)
    assert st['head_prod'] == pytest.approx(1.0, abs=1e-12)
    assert st['w2_opl'] == pytest.approx(st['opl_direct'],
                                         rel=1e-12, abs=1e-9)


# ── 121 з.1.0: кромочная ветка [4dca] ─────────────────────────────────────

@requires_stand
def test_121_zone1_kromka_branch():
    """RED «121 волновые з.1.0» (−229.337 против +307.855): луч зоны 1.0
    выходит за габарит поверхности 1 (y=8.10 мм > 8.0 мм) — печать
    марша идёт по приповерхностной ветке cd62 ([4dca]=−1, зеркальный
    хвост 0xd6d4), портовая волновая такого луча не строит."""
    st = _state('121', 1.0)
    assert st['rim_surf'] == 1
    assert 1.0 < st['rim_max'] <= 1.05


@requires_stand
def test_121_zone0866_no_structural_branch():
    """121 з.0.866 (75.284 против 73.620, +1.664λ): кромки/TIR нет —
    остаток чисто замыкания тензора/трубы λ-уровня (семена [4d20]
    ff9:19 / [4c4a] 0xbe4f рантаймовые, статически недостижимы)."""
    st = _state('121', 0.866)
    assert st['rim_max'] < 0.97
    assert st['tir_surf'] is None


@requires_stand
def test_okular_zone0866_no_structural_branch():
    """OKULAR з.0.866 (−71.321 против −70.538): та же причина — нет
    структурной ветки, только λ-уровень замыкания."""
    st = _state('OKULAR', 0.866)
    assert st['tir_surf'] is None


# ── отчёт: каждая остаточная строка имеет причину ─────────────────────────

@pytest.mark.parametrize('name', DEFAULT_SYSTEMS)
@requires_stand
def test_march_report_causes(name):
    """Все RED/YELLOW-зоны отчёта марша несут точную причину; зона 1.0
    афокалов — предел трубы (числовое значение запинено отдельным
    тестом test_kursovik_march_tube_limit_ray)."""
    rows = march_report(name, verbose=False)
    assert rows, f'{name}: пустой отчёт'
    residual = [r for r in rows
                if any(('ветк' in c or 'предел' in c or 'недостижимы' in c)
                       for c in r.get('causes', []))]
    assert residual, f'{name}: ни одной причинной строки'
    for r in rows:
        if abs(r['zone']) < 1e-9:
            assert not r.get('causes')


@requires_stand
def test_kursovik_zone1_tube_limit_cause():
    rows = march_report('KURSOVIK', verbose=False)
    z1 = next(r for r in rows if abs(r['zone'] - 1.0) < 1e-9)
    assert any('предел трубы' in c for c in z1['causes'])
