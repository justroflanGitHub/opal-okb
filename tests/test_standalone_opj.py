# -*- coding: utf-8 -*-
"""GFIX/P5: строгий парсер standalone .OPJ как отдельный вход порта.

fileio/standalone_opj — раскладка, валидированная банком .PRN (досье
REVERSE_GVERIFY.md §3). До P5 парсер жил только в харнессе
(analysis/golden_verify) и падал голым struct.error на зеркальных
маркерах gidx (0xFFFE/0xFFFF раздували n_glass = max(gidx)). Теперь:
харнесс алиасит портовый вход, библиотека (catalog/library) пробует
строгий разбор первым, lbo-путь не тронут.

GTIE (REVERSE_GTIE.md): ГОЭ-маркер 0xFFFD в gidx принят — GTIE00
разбирается (заглушка ГОЭ-поверхности, λ записи HeNe в ключе goe),
отказов на стенде больше нет.
"""
import math
from pathlib import Path

import pytest

from fileio.standalone_opj import (
    BIG_MARKER, GOE_MARKER, MIRROR_MARKERS, StandaloneOpjError,
    parse_standalone_opj, standalone_to_system,
)

GOLDEN_DOS = Path(r'C:\GOLDEN_DOS')

requires_stand = pytest.mark.skipif(
    not GOLDEN_DOS.exists(), reason='нет стенда C:\\GOLDEN_DOS')


def _opj_files(root: Path):
    """*.OPJ обоих регистров (Path.glob чувствителен к регистру на POSIX)."""
    return sorted(set(root.glob('*.OPJ')) | set(root.glob('*.opj')))


@requires_stand
def test_all_stand_files_strict_parse():
    """Все ~85 записей стенда: строгий разбор succeeds с инвариантами
    раскладки, чистых отказов нет. Прежде парсер харнесса валился
    struct.error на зеркальных YBBS77_/GTIN05, затем единственным
    отказом оставался ГОЭ GTIE00 (0xFFFD раздувал n_glass, досье §6)."""
    files = _opj_files(GOLDEN_DOS)
    assert len(files) >= 80                      # стенд целиком
    for p in files:
        opj = parse_standalone_opj(p.read_bytes(), source=p.name)
        # инварианты раскладки
        assert opj['ns'] == len(opj['curv']) == len(opj['thick'])
        assert len(opj['gidx']) == opj['ns'] + 1
        assert len(opj['ri']) == max(g for g in opj['gidx'] if g < GOE_MARKER)
        assert all(len(row) == len(opj['wls']) for row in opj['ri'])
        assert 1 <= len(opj['wls']) <= 3
        assert all(0.1 < wl < 30.0 for wl in opj['wls'])
        assert all(math.isfinite(v) for row in opj['ri'] for v in row)
        assert all(m < opj['ns'] for m in opj['mirrors'])
        assert all(g < opj['ns'] for g in opj['goe']['surfaces'])
        system = standalone_to_system(opj)
        assert len(system.surfaces) == opj['ns']


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
    # GTIE (REVERSE_GTIE.md): заголовок канонический, ИК-ГОЭ 3-5 мкм
    ('GTIE00', 'ns', 10),
    ('GTIE00', 'wls', [4.25, 3.5, 5.0]),         # эталон GTIE00.PRN
    ('GTIE00', 'stop_nd', 3),
    ('GTIE00', 'aperture_semi', 26.0),           # Ax эталона 26.17
    ('GTIE00', 'mirrors', [2, 3, 4, 5]),         # зеркальный сэндвич ГОЭ
    # P6.1: положение предмета — f64@0x4C (мм от первой поверхности):
    # <0 действительный слева, >0 мнимый справа; 1000/(sP − z_obj) = Sp
    ('ST4', 'object_pos', -96.2046),             # Sp 9.717 дптр
    ('S_KOND1', 'object_pos', -30.0),            # Sp 33.333 дптр
    ('PLIOPT', 'object_pos', -280.5),
    ('OPTICS#1', 'object_pos', 85.1495),         # мнимый предмет
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
def test_goe_marker_stub_surface():
    """GTIE00 (ЭКРАН - ГОЭ, досье REVERSE_GTIE.md): маркер 0xFFFD в
    gidx[4] = среда после S3 — ГОЭ в зеркальном сэндвиче S2/S4. До GTIE
    0xFFFD раздувал n_glass (65533) и RI уходил за пределы файла;
    теперь поверхность = заглушка (отражение, дифракция записи не
    смоделирована), параметры записи — в ключе goe (λ HeNe 0.6328).
    Прочие поверхности честные: R/d из OPJ, RI-матрица 3 сред ИК
    (CaF2-подобная 1.407 / 1.664 / Ge 4.022 при 4.25 мкм)."""
    opj = parse_standalone_opj((GOLDEN_DOS / 'GTIE00.OPJ').read_bytes())
    assert opj['gidx'][4] == GOE_MARKER
    assert opj['goe']['surfaces'] == [3]
    assert opj['goe']['wlh'] == pytest.approx(0.6328, abs=1e-4)
    assert opj['goe']['rec'][4] == pytest.approx(0.6328, abs=1e-4)
    # толщина изображения 0 вместо 1e20 — допустимое отклонение (§6)
    assert opj['thick'][-1] == 0.0
    assert any('ГОЭ' in w for w in opj['warnings'])
    # кривизны: R = [36.98, 34.04, −71.82, −17.06, −15.70, ∞×5]
    radii = [1.0 / c if c else 0.0 for c in opj['curv']]
    assert radii[0] == pytest.approx(36.98, abs=1e-2)   # = Sp эталона
    assert radii[2] == pytest.approx(-71.8165, abs=1e-2)
    assert radii[3] == pytest.approx(-17.061, abs=1e-3)  # сама ГОЭ
    assert opj['thick'][2:5] == [-17.0, -2.0, -8.0]
    system = standalone_to_system(opj)
    goe_s = system.surfaces[3]
    assert goe_s.glass == 'ГОЭ' and goe_s.is_reflective
    assert not goe_s.n_override                       # RI-строку не берёт
    assert goe_s.radius == pytest.approx(-17.061, abs=1e-3)
    # окружение честное: S2/S4 — зеркала, S6 — окно Ge по RI-матрице
    assert system.surfaces[2].glass == 'ЗЕРКАЛО'
    assert system.surfaces[4].glass == 'ЗЕРКАЛО'
    n_ov = system.surfaces[6].n_override
    assert n_ov[4.25] == pytest.approx(4.02166, abs=1e-4)


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
