"""TASK_TABAX3 — OPAL-режим хроматизма (парные волны, таблица TABAX3).

Реверс §9 REVERSE_TRACE.md: хроматизм = повторная трассировка того же
луча с показателями преломления другой λ у помеченных поверхностей
(wl-флаги записи, выбор трейсера f344/f359 по [0x50c2]); при отсутствии
флагов — fallback-пары по system.wavelengths. Осевые величины обязаны
совпадать с разностями paraxial_trace (одна формула двумя путями).
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint, ObjectType,
)
from domain.calculations import paraxial_trace
from achromat import design_achromat
from analysis.chromatism import (
    ANGLE_RAY_ZONE, TABAX3_FIELD_WIDTHS, ChromatismResult,
    compute_chromatism_opal, format_tabax3, tabax3_rows,
)

L_d, L_F, L_C = 0.58756, 0.48613, 0.65627


def build_singlet(focal=100.0):
    """Синглет К8 f'≈100 — нормальная дисперсия без компенсации."""
    s = OpticalSystem(name='Синглет К8', object_type=ObjectType.INFINITE)
    s.wavelengths = [Wavelength(L_d, 1.0, 'd'), Wavelength(L_F, 1.0, 'F'),
                     Wavelength(L_C, 1.0, 'C')]
    s.field_points = [FieldPoint(0.0)]
    s.aperture_value = 20.0
    R = 2 * 0.5163 * focal  # (n-1)·2/R = 1/f → R = 2(n-1)f
    s.surfaces = [
        Surface(radius=R, thickness=4, glass='К8', semi_diameter=10),
        Surface(radius=-R, thickness=focal * 0.9, glass='', semi_diameter=10),
    ]
    return s


def build_two_lens():
    """К8 — воздушный зазор — ТФ5: 4 поверхности, среда 1 — воздух."""
    s = OpticalSystem(name='Двухлинзовая', object_type=ObjectType.INFINITE)
    s.wavelengths = [Wavelength(L_d, 1.0, 'd'), Wavelength(L_F, 1.0, 'F'),
                     Wavelength(L_C, 1.0, 'C')]
    s.field_points = [FieldPoint(0.0)]
    s.aperture_value = 10.0
    s.surfaces = [
        Surface(radius=80, thickness=5, glass='К8', semi_diameter=12),
        Surface(radius=-60, thickness=0.2, glass='', semi_diameter=12),
        Surface(radius=-70, thickness=4, glass='ТФ5', semi_diameter=12),
        Surface(radius=-250, thickness=90, glass='', semi_diameter=12),
    ]
    return s


def row_by_wl(result, wl):
    """Строка результата для λ пары (допуск 0.002 мкм)."""
    return next(r for r in result['rows'] if abs(r['wl'] - wl) < 0.002)


# --------------------------------------------------------------------------- #
# 1. Ахромат К8/ТФ1 из каталога
# --------------------------------------------------------------------------- #

class TestAchromat:

    def test_d_to_f_finite_and_small(self):
        """Осевой хроматизм d→F у ахромата конечен и мал: на порядок
        меньше синглета той же силы (подгонка design_achromat)."""
        ach = design_achromat(100.0, 'К8', 'ТФ1')
        sing = build_singlet(100.0)
        dsF_ach = row_by_wl(compute_chromatism_opal(ach), L_F)['dsF_prime_mm']
        dsF_sing = row_by_wl(compute_chromatism_opal(sing), L_F)['dsF_prime_mm']
        assert abs(dsF_ach) < 0.2          # конечен и мал (мм)
        assert abs(dsF_ach) < 0.2 * abs(dsF_sing)

    def test_f_to_c_corrected_vs_singlet(self):
        """Пара F→C сведена ахроматом: |ΔsF'| < 10% от синглета."""
        ach = design_achromat(100.0, 'К8', 'ТФ1')
        sing = build_singlet(100.0)
        dsF_ach = row_by_wl(compute_chromatism_opal(ach, wl_main=L_F),
                            L_C)['dsF_prime_mm']
        dsF_sing = row_by_wl(compute_chromatism_opal(sing, wl_main=L_F),
                             L_C)['dsF_prime_mm']
        assert abs(dsF_ach) < 0.1 * abs(dsF_sing)

    def test_achromat_rows_for_all_system_wavelengths(self):
        """Fallback даёт по строке на каждую λ системы, кроме основной."""
        res = compute_chromatism_opal(design_achromat(100.0, 'К8', 'ТФ1'))
        assert res['mode'] == 'fallback'
        assert [r['wl'] for r in res['rows']] == pytest.approx([L_F, L_C])


# --------------------------------------------------------------------------- #
# 2. Парность: per-surface флаги
# --------------------------------------------------------------------------- #

class TestPerSurfaceFlags:

    def test_air_surface_contributes_nothing(self):
        """Флаг на поверхности без дисперсии (воздушный зазор): воздух
        n≡1 на всех λ → разности нулевые — в паре участвуют только
        помеченные среды."""
        res = compute_chromatism_opal(
            build_two_lens(), wl_flags=[0, L_F, 0, 0])
        assert res['mode'] == 'per_surface'
        assert len(res['rows']) == 1
        row = res['rows'][0]
        assert row['surface'] == 1
        for key in ('dsF_prime_mm', 'dfocal_mm', 'dy_prime_mm',
                    'du_prime_rad', 'dsF_prime_pct'):
            assert row[key] == 0.0, key

    def test_glass_surface_contributes(self):
        """Изоляция вкладов: К8 и ТФ5 по отдельности дают ΔsF' разных
        знаков (положительный крон / отрицательный флинт), вместе —
        частичная компенсация (|полного| меньше каждого из вкладов)."""
        sys2 = build_two_lens()
        res_crown = compute_chromatism_opal(sys2, wl_flags=[2, 0, 0, 0])
        res_flint = compute_chromatism_opal(sys2, wl_flags=[0, 0, 2, 0])
        res_full = compute_chromatism_opal(sys2)
        ds_crown = row_by_wl(res_crown, L_F)['dsF_prime_mm']
        ds_flint = row_by_wl(res_flint, L_F)['dsF_prime_mm']
        ds_full = row_by_wl(res_full, L_F)['dsF_prime_mm']
        assert res_crown['mode'] == 'per_surface'
        assert res_full['mode'] == 'fallback'
        assert abs(ds_crown) > 1e-9 and abs(ds_flint) > 1e-9
        assert ds_crown * ds_flint < 0.0
        assert abs(ds_full) < min(abs(ds_crown), abs(ds_flint))

    def test_flag_int_index_equals_direct_lambda(self):
        """Флаг-int (1-основной индекс system.wavelengths) и прямая λ
        дают одну и ту же строку."""
        by_idx = compute_chromatism_opal(build_two_lens(), wl_flags=[2, 0, 0, 0])
        by_lam = compute_chromatism_opal(build_two_lens(), wl_flags=[L_F, 0, 0, 0])
        r1 = row_by_wl(by_idx, L_F)
        r2 = row_by_wl(by_lam, L_F)
        for key in ('dsF_prime_mm', 'dfocal_mm', 'du_prime_rad'):
            assert r1[key] == pytest.approx(r2[key], abs=1e-12), key

    def test_surface_attribute_channel(self):
        """Флаг можно вешать атрибутом Surface.wl_flag (канал OPJ-записи)."""
        sys2 = build_two_lens()
        sys2.surfaces[0].wl_flag = 2  # int → wavelengths[1] = F
        res = compute_chromatism_opal(sys2)
        assert res['mode'] == 'per_surface'
        assert res['rows'][0]['surface'] == 0
        assert res['rows'][0]['wl'] == pytest.approx(L_F)

    def test_row_per_flagged_surface(self):
        """Каждая помеченная поверхность даёт свою строку (изоляция
        вклада поверхности)."""
        res = compute_chromatism_opal(
            build_two_lens(), wl_flags=[L_F, 0, L_F, 0])
        assert [r['surface'] for r in res['rows']] == [0, 2]
        # вклады двух разных стёкол различаются
        assert res['rows'][0]['dsF_prime_mm'] != pytest.approx(
            res['rows'][1]['dsF_prime_mm'])

    def test_invalid_flag_raises(self):
        sys2 = build_two_lens()
        with pytest.raises(ValueError):
            compute_chromatism_opal(sys2, wl_flags=[5, 0, 0, 0])
        with pytest.raises(ValueError):
            compute_chromatism_opal(sys2, wl_flags=[True, 0, 0, 0])
        with pytest.raises(ValueError):
            compute_chromatism_opal(sys2, wl_flags=[0, 0])  # короче списка

    def test_system_not_mutated(self):
        """Временное расширение полудиаметров восстанавливается; записи
        поверхностей (n_override, радиусы) не меняются."""
        sys2 = build_two_lens()
        before = [(s.radius, s.thickness, s.glass, s.semi_diameter,
                   dict(s.n_override)) for s in sys2.surfaces]
        compute_chromatism_opal(sys2, wl_flags=[L_F, 0, L_F, 0])
        after = [(s.radius, s.thickness, s.glass, s.semi_diameter,
                  dict(s.n_override)) for s in sys2.surfaces]
        assert after == before


# --------------------------------------------------------------------------- #
# 3. Формат TABAX3: 7 колонок, ширины полей
# --------------------------------------------------------------------------- #

class TestTabax3Format:

    def test_row_widths_and_columns(self):
        """Строка TABAX3 — 77 символов: f8.3 + f9.2 + 5×f12.6."""
        res = compute_chromatism_opal(design_achromat(100.0, 'К8', 'ТФ1'))
        rows = tabax3_rows(res)
        assert len(rows) == 2
        for text in rows:
            assert len(text) == sum(TABAX3_FIELD_WIDTHS) == 77
        # первая колонка — λ пары, вторая — осевой отрезок sF'
        assert float(rows[0][0:8]) == pytest.approx(L_F, abs=5e-4)
        assert float(rows[1][0:8]) == pytest.approx(L_C, abs=5e-4)
        seg = res['rows'][0]['segment_mm']
        assert float(rows[0][8:17]) == pytest.approx(seg, abs=5e-3)
        # остальные 5 полей — фиксированной ширины 12 и парсятся как float
        pos = 17
        for width, value in zip((12, 12, 12, 12, 12), (
                res['rows'][0]['dsF_prime_mm'], res['rows'][0]['dfocal_mm'],
                res['rows'][0]['dy_prime_mm'], res['rows'][0]['du_prime_rad'],
                res['rows'][0]['dsF_prime_pct'])):
            field = rows[0][pos:pos + width]
            assert len(field) == width
            assert float(field) == pytest.approx(value, abs=5e-6)
            pos += width

    def test_method_and_function_agree(self):
        """ChromatismResult.formatTabax3() == format_tabax3(result):
        подписи колонок + строки данных."""
        res = compute_chromatism_opal(build_two_lens(), wl_flags=[2, 0, 0, 0])
        assert isinstance(res, ChromatismResult) and isinstance(res, dict)
        text = res.formatTabax3()
        assert text == format_tabax3(res)
        lines = text.split('\n')
        assert len(lines) == 2  # заголовок + 1 строка per_surface
        assert len(lines[1]) == 77

    def test_none_printed_as_blanks(self):
        """Луч не дошёл → поле из пробелов ширины колонки (не NaN)."""
        row = {'wl': L_F, 'surface': None, 'segment_mm': 100.0,
               'dsF_prime_mm': -0.1, 'dfocal_mm': -0.1,
               'dy_prime_mm': None, 'du_prime_rad': None,
               'dsF_prime_pct': -0.1}
        (text,) = tabax3_rows({'rows': [row]})
        assert text[17 + 24:17 + 48] == ' ' * 24  # колонки Δy', Δu'
        assert len(text) == 77


# --------------------------------------------------------------------------- #
# 4. Сверка с paraxial_trace: одна формула двумя путями (≤1e-6)
# --------------------------------------------------------------------------- #

class TestParaxialConsistency:

    def test_achromat_d_f_pair(self):
        """Явная пара d→F: ΔsF' из прогона B == разности
        paraxial_trace(wl=F) − paraxial_trace(wl=d)."""
        ach = design_achromat(100.0, 'К8', 'ТФ1')
        row = row_by_wl(compute_chromatism_opal(ach, wl_main=L_d), L_F)
        ref = (paraxial_trace(ach, wl=L_F)['sF_prime']
               - paraxial_trace(ach, wl=L_d)['sF_prime'])
        assert row['dsF_prime_mm'] == pytest.approx(ref, abs=1e-6)

    def test_lens_lbo_systems(self, lens_systems):
        """2-3 системы LENS.LBO: осевой хроматизм основной пары λ
        совпадает с paraxial-разностью в пределах 1e-6."""
        from decode_lbo_opj import decode_lbo_opj
        checked = 0
        for idx in (0, 3, 5):  # Индустар-7, -23у, -37
            sys_obj = decode_lbo_opj(lens_systems[idx]['opj_data'])
            wl0 = sys_obj.wavelengths[0].value
            wl1 = sys_obj.wavelengths[1].value
            row = row_by_wl(compute_chromatism_opal(sys_obj), wl1)
            ref = (paraxial_trace(sys_obj, wl=wl1)['sF_prime']
                   - paraxial_trace(sys_obj, wl=wl0)['sF_prime'])
            assert abs(row['dsF_prime_mm'] - ref) < 1e-6, (idx, sys_obj.name)
            checked += 1
        assert checked == 3

    def test_transverse_chief_difference_present(self, lens_systems):
        """Поперечная величина Δy' (хроматизм увеличения) на краевом поле
        LENS.LBO-системы конечна и ненулевая."""
        from decode_lbo_opj import decode_lbo_opj
        sys_obj = decode_lbo_opj(lens_systems[0]['opj_data'])
        res = compute_chromatism_opal(sys_obj)
        dy = [r['dy_prime_mm'] for r in res['rows']]
        assert all(v is not None for v in dy)
        assert any(abs(v) > 1e-6 for v in dy)


# --------------------------------------------------------------------------- #
# 5. Прочее: пустая система, пустые λ
# --------------------------------------------------------------------------- #

class TestDegenerate:

    def test_empty_system(self):
        res = compute_chromatism_opal(OpticalSystem(name='empty'))
        assert res['rows'] == []
        assert res['mode'] == 'fallback'
        assert res.formatTabax3().split('\n')[1:] == []

    def test_single_wavelength_no_pairs(self):
        """Единственная λ == основная: пар нет, таблица пуста."""
        sys2 = build_two_lens()
        sys2.wavelengths = [Wavelength(L_d, 1.0, 'd')]
        res = compute_chromatism_opal(sys2)
        assert res['rows'] == []

    def test_angle_ray_zone_sane(self):
        """Зона луча Δu' — внутри зрачка (край виньетируется полем)."""
        assert 0.0 < ANGLE_RAY_ZONE < 1.0
