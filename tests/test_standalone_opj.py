# -*- coding: utf-8 -*-
"""GFIX/P5: строгий парсер standalone .OPJ как отдельный вход порта.

fileio/standalone_opj — раскладка, валидированная банком .PRN (досье
REVERSE_GVERIFY.md §3). До P5 парсер жил только в харнессе
(analysis/golden_verify) и падал голым struct.error на зеркальных
маркерах gidx (0xFFFE/0xFFFF раздували n_glass = max(gidx)). Теперь:
харнесс алиасит портовый вход, библиотека (catalog/library) пробует
строгий разбор первым, lbo-путь не тронут.
"""
import math
from pathlib import Path

import pytest

from fileio.standalone_opj import (
    BIG_MARKER, MIRROR_MARKERS, StandaloneOpjError,
    parse_standalone_opj, standalone_to_system,
)

GOLDEN_DOS = Path(r'C:\GOLDEN_DOS')

requires_stand = pytest.mark.skipif(
    not GOLDEN_DOS.exists(), reason='нет стенда C:\\GOLDEN_DOS')

#: Записи стенда/архива, не соответствующие standalone-раскладке:
#: ГОЭ GTIE00 пишет мусорный индекс среды 0xFFFD и RI за пределами
#: файла (досье §6) — строгий вход обязан падать ЧИСТОЙ ошибкой.
NOT_STANDALONE = {'GTIE00'}


def _opj_files(root: Path):
    """*.OPJ обоих регистров (Path.glob чувствителен к регистру на POSIX)."""
    return sorted(set(root.glob('*.OPJ')) | set(root.glob('*.opj')))


@requires_stand
def test_all_stand_files_strict_parse():
    """Все ~85 записей стенда: строгий разбор либо succeeds с инвариантами
    раскладки, либо ЧИСТАЯ StandaloneOpjError — и такие ровно одна
    (GTIE00, ГОЭ). Прежде парсер харнесса валился struct.error ещё и на
    зеркальных YBBS77_/GTIN05."""
    files = _opj_files(GOLDEN_DOS)
    assert len(files) >= 80                      # стенд целиком
    rejected = []
    for p in files:
        try:
            opj = parse_standalone_opj(p.read_bytes(), source=p.name)
        except StandaloneOpjError:
            rejected.append(p.stem)
            continue
        # инварианты раскладки
        assert opj['ns'] == len(opj['curv']) == len(opj['thick'])
        assert len(opj['gidx']) == opj['ns'] + 1
        assert len(opj['ri']) == max(g for g in opj['gidx']
                                     if g not in MIRROR_MARKERS)
        assert all(len(row) == len(opj['wls']) for row in opj['ri'])
        assert 1 <= len(opj['wls']) <= 3
        assert all(0.1 < wl < 30.0 for wl in opj['wls'])
        assert all(math.isfinite(v) for row in opj['ri'] for v in row)
        assert all(m < opj['ns'] for m in opj['mirrors'])
        system = standalone_to_system(opj)
        assert len(system.surfaces) == opj['ns']
    assert set(rejected) == NOT_STANDALONE, rejected


@requires_stand
@pytest.mark.parametrize('name, field, expected', [
    ('US00KI02', 'ns', 20),
    ('US00KI02', 'wls', [10.0]),                 # ИК, мкм
    ('US00KI02', 'stop_type', 0xFFFF),           # 'p'
    ('US00KI02', 'pupil_pos', -22.2),
    ('US00KI02', 'aperture_semi', 5.0),
    ('OPAL3', 'flags', 3),                       # три λ-слота
    ('OPAL3', 'stop_type', 0),                   # 'd'
    ('121', 'stop_nd', 4),                       # ND 1-индексация (GFIX P1)
    ('121', 'pupil_pos', 8.162),                 # SD от вершины ND−1
    ('YBBS77_', 'mirrors', [0, 1]),              # зеркальные маркеры gidx
])
def test_layout_pins(name, field, expected):
    opj = parse_standalone_opj((GOLDEN_DOS / f'{name}.OPJ').read_bytes())
    assert opj[field] == pytest.approx(expected, abs=1e-3) \
        if isinstance(expected, float) else opj[field] == expected


@requires_stand
def test_opal3_first_wavelength_e_line():
    opj = parse_standalone_opj((GOLDEN_DOS / 'OPAL3.OPJ').read_bytes())
    assert opj['wls'][0] == pytest.approx(0.54607, abs=1e-4)


@requires_stand
def test_to_system_uses_ri_matrix_and_marker():
    """Среды — n_override из RI-матрицы OPAL (не каталог порта):
    US00KI02 — германий n(10 мкм) ≈ 4.00324 в строке 1. Маркер 1e20 →
    терминальная толщина 0 (терминальный сегмент строит трейсер,
    GFIX P2)."""
    opj = parse_standalone_opj((GOLDEN_DOS / 'US00KI02.OPJ').read_bytes())
    assert opj['thick'][-1] >= BIG_MARKER
    system = standalone_to_system(opj)
    assert system.surfaces[-1].thickness == 0.0
    n_ov = system.surfaces[0].n_override           # gidx[1] = 2 → строка 1
    assert 10.0 in n_ov and n_ov[10.0] == pytest.approx(4.00324, abs=1e-4)
    assert system.stop_surface == 1 and system.stop_offset == -22.2


@requires_stand
def test_mirror_markers_flag_reflective():
    """0xFFFE/0xFFFF в gidx — зеркало: поверхность reflective, среда не
    меняется (n_override не назначается). До P5 такие файлы падали
    struct.error (n_glass = max(gidx) без исключения маркеров)."""
    opj = parse_standalone_opj((GOLDEN_DOS / 'YBBS77_.OPJ').read_bytes())
    system = standalone_to_system(opj)
    assert all(s.is_reflective for s in system.surfaces)
    assert all(s.glass == 'ЗЕРКАЛО' for s in system.surfaces)
    assert all(not s.n_override for s in system.surfaces)


@requires_stand
def test_marker_deviant_files_warn_not_fail():
    """OPAL иногда пишет вместо маркера 1e20 нулевой хвост толщин
    (KURSOV/LAB3) или фактический BFD (PETRO1 493.56) — допустимое
    отклонение: warning, разбор продолжается."""
    for name, tail in (('KURSOV', 0.0), ('PETRO1', 493.56)):
        opj = parse_standalone_opj((GOLDEN_DOS / f'{name}.OPJ').read_bytes())
        assert opj['warnings'], name
        assert opj['thick'][-1] == pytest.approx(tail, abs=1e-3), name


def test_harness_aliases_port_entry():
    """Харнесс больше не держит копию парсера (GFIX P5): его входы —
    портовый модуль (обёртка parse_golden_opj читает файл и вызывает
    порт; равенство значений — тестом ниже)."""
    import analysis.golden_verify as gv
    import fileio.standalone_opj as so
    assert gv.opj_to_system is so.standalone_to_system
    assert gv._BIG_MARKER is so.BIG_MARKER
    assert 'parse_standalone_opj' in gv.parse_golden_opj.__globals__


@requires_stand
def test_harness_parse_equals_port_entry():
    opj = parse_standalone_opj((GOLDEN_DOS / '121.OPJ').read_bytes())
    from analysis.golden_verify import parse_golden_opj
    gold = parse_golden_opj(str(GOLDEN_DOS / '121.OPJ'))
    for key in ('ns', 'flags', 'wls', 'curv', 'thick', 'gidx', 'ri',
                'stop_nd', 'pupil_pos', 'names', 'mirrors'):
        assert gold[key] == opj[key], key


@requires_stand
def test_library_prefers_strict_entry():
    """catalog._create_from_opj: успех строгого разбора = prescription
    достоверен (ND/SD, λ, RI) — эвристики не соревнуются. Дискриминатор:
    λ=10.0 и SD=−22.2 US00KI02 недоступны эвристикам (OPAL_WL не знает
    10.0, стоп-плоскость — семантика GFIX P1)."""
    from catalog.library import _create_from_opj
    system = _create_from_opj(str(GOLDEN_DOS / 'US00KI02.OPJ'))
    assert [w.value for w in system.wavelengths] == [10.0]
    assert system.stop_offset == pytest.approx(-22.2)
    assert system.stop_type == 'p'
    assert len(system.surfaces) == 20
    # не-standalone запись (ГОЭ) — откат на эвристики без исключения
    fallback = _create_from_opj(str(GOLDEN_DOS / 'GTIE00.OPJ'))
    assert fallback is not None and len(fallback.surfaces) >= 1
