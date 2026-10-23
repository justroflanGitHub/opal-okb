# -*- coding: utf-8 -*-
"""Тесты золотой верификации порта против банка .PRN (TASK_GVERIFY).

Эталоны: analysis/reverse_data/golden/bank/*.PRN (14 систем,
DOSBox-прогон OPAL, CP866); рецепты: C:\\GOLDEN_DOS\\*.OPJ (стенд —
только чтение; end-to-end тесты пропускаются без стенда).
Взломанные конвенции — analysis/REVERSE_GVERIFY.md §2.
"""
from pathlib import Path
import math

import pytest

from analysis.golden_verify import (
    BANK_SYSTEMS, TOL_ABERR, TOL_PARAX,
    compare_system, parse_golden_opj, parse_golden_prn, rel_diff,
    run_all, verdict,
)

BASE = Path(__file__).resolve().parent.parent
BANK = BASE / 'analysis' / 'reverse_data' / 'golden' / 'bank'
GOLDEN_DOS = Path(r'C:\GOLDEN_DOS')

requires_stand = pytest.mark.skipif(
    not GOLDEN_DOS.exists(), reason='нет стенда C:\\GOLDEN_DOS')


# ── Парсер эталонных .PRN ─────────────────────────────────────────────────

def test_prn_gabarit_n0_us00ki02():
    prn = parse_golden_prn(BANK / 'US00KI02.PRN')
    ax = [r for (wl, n), r in prn['gabarit'].items() if n == 0]
    assert len(ax) == 1
    row = ax[0]
    assert row['Ax'] == pytest.approx(5.0)
    assert row['Sp'] == pytest.approx(-22.2)
    assert row['Sp2'] == pytest.approx(-147.67)
    assert row['Ax2'] == pytest.approx(-20.69, abs=0.01)


def test_prn_axial_us00ki02():
    prn = parse_golden_prn(BANK / 'US00KI02.PRN')
    # единицы печатаются в заголовке секции
    assert prn['axial1']['units'] == ('дптр', 'гр.мнсек')
    assert sorted(prn['axial1']['rows']) == [0.0, 0.5, 0.707, 0.866, 1.0]
    z1 = prn['axial1']['rows'][1.0]
    assert z1['long'][0] == pytest.approx(-0.09008, abs=1e-5)
    assert z1['trans'][0] == pytest.approx(0.062432, abs=1e-5)
    # TABOC2: верхняя строка — зона 1.0, метка = H' ЗР, Н ЗР = отн.зр·Ax
    top = max(prn['axial2']['rows'].values(),
              key=lambda r: r['tg100'] or 0)
    assert top['tg100'] == pytest.approx(20.684, abs=1e-3)
    assert top['wave'][0] == pytest.approx(0.7532, abs=1e-4)
    assert top['h_zr'] == pytest.approx(5.0, abs=1e-4)


def test_prn_taboc2_rows_sorted_by_label_121():
    """Строки TABOC2 отсортированы по метке, а не по зоне: у 121 колонка
    Н ЗР немонотонна — идентичность зоны восстанавливается по ней
    (REVERSE_GVERIFY.md §2.3)."""
    prn = parse_golden_prn(BANK / '121.PRN')
    rows = sorted(prn['axial2']['rows'].values(),
                  key=lambda r: -(r['tg100'] or 0))
    hzr = [r['h_zr'] for r in rows]
    assert hzr[0] == pytest.approx(8.1004, abs=1e-3)   # зона 1.0
    assert hzr[1] == pytest.approx(4.0502, abs=1e-3)   # зона 0.5!
    assert hzr[2] == pytest.approx(5.7279, abs=1e-3)   # зона 0.707
    assert hzr[3] == pytest.approx(0.0, abs=1e-9)      # зона 0.0
    assert hzr[4] == pytest.approx(7.0152, abs=1e-3)   # зона 0.866


def test_prn_duplicate_gabarit_sections_deduped_kursovik():
    """У KURSOVIK секция «Габариты пучков» продублирована — парсер
    дедуплицирует по ключу (λ, N)."""
    prn = parse_golden_prn(BANK / 'KURSOVIK.PRN')
    ax = [r for (wl, n), r in prn['gabarit'].items() if n == 0]
    assert len(ax) == 1
    assert ax[0]['Sp'] == pytest.approx(-59.976, abs=1e-3)


def test_prn_taboc2_star_filler_row_vv():
    """G44 (Пакет B): у VV зона 1.0 не трассирована — строка печатана
    звёздочками без метки зоны; прежде она обрывала разбор TABOC2
    (axial2 пуст), теперь пропускается, остальные 4 зоны читаются.
    Звёздочное заполнение КОЛОНОК при метке-числе (TABOC1 з.1.0) —
    как было: None-ячейки."""
    prn = parse_golden_prn(BANK / 'VV.PRN')
    a1 = prn['axial1']['rows']
    assert sorted(a1) == [0.0, 0.5, 0.707, 0.866, 1.0]
    assert a1[1.0]['long'] == [None, None, None]   # звёзды в колонках
    assert a1[0.866]['long'][0] == pytest.approx(-0.67830, abs=1e-5)
    a2 = prn['axial2']['rows']
    assert sorted(a2) == [-0.090, -0.074, -0.052, 0.0]   # з.1.0 — звёзды
    assert a2[-0.090]['wave'][0] == pytest.approx(-0.0002, abs=1e-5)
    assert a2[-0.090]['h_zr'] == pytest.approx(3.2134, abs=1e-4)


# ── Строгий OPJ-лоадер ────────────────────────────────────────────────────

@requires_stand
def test_opj_us00ki02_layout():
    opj = parse_golden_opj(GOLDEN_DOS / 'US00KI02.OPJ')
    assert opj['ns'] == 20
    assert opj['flags'] == 1                    # один λ-слот
    assert opj['wls'] == [10.0]                 # ИК, мкм
    assert opj['obj_type'] == 0 and opj['img_type'] == 0
    assert opj['stop_type'] == 0xFFFF           # 'p'
    assert opj['aperture_semi'] == pytest.approx(5.0)
    assert opj['pupil_pos'] == pytest.approx(-22.2)
    # маркер изображения и имена сред
    assert opj['thick'][-1] >= 1e19
    assert 'ВОЗДУХ' in opj['names'][0].upper() or 'AIR' in opj['names'][0].upper()


@requires_stand
def test_opj_three_lambda_slots_opal3():
    opj = parse_golden_opj(GOLDEN_DOS / 'OPAL3.OPJ')
    assert opj['flags'] == 3                    # три λ-слота
    assert len(opj['wls']) == 3
    assert opj['wls'][0] == pytest.approx(0.54607, abs=1e-4)   # e-линия
    assert opj['stop_type'] == 0                # 'd'
    # матрица ПП: строки = среды после воздуха, столбцы = λ
    assert len(opj['ri']) >= 3
    assert 'БФ25' in opj['names'][1]


# ── Вердикты/допуски ──────────────────────────────────────────────────────

def test_verdict_thresholds():
    assert verdict(0.0, TOL_ABERR) == 'GREEN'
    assert verdict(5e-4, TOL_ABERR) == 'GREEN'
    assert verdict(5e-3, TOL_ABERR) == 'YELLOW'   # ≤10× допуска
    assert verdict(0.5, TOL_ABERR) == 'RED'
    assert verdict(1e-6, TOL_PARAX) == 'GREEN'
    assert verdict(1e-2, TOL_PARAX) == 'RED'


def test_rel_diff_none_is_none():
    assert rel_diff(5.0, 5.0) == 0.0
    assert rel_diff(None, 1.0) is None
    assert rel_diff(1.0, None) is None
    assert rel_diff(101.0, 100.0) == pytest.approx(0.01)


# ── End-to-end: сверка порта с эталонами ─────────────────────────────────

@requires_stand
def test_us00ki02_reference_system_green():
    """Опорная система полностью зелёная: все развёрнутые конвенции
    (зрачки, прод, Tg'·100, Н ЗР) и волновые во всех зонах — GFIX P4
    закрыл остаток опорной сферой от выходного зрачка (досье §2.4:
    0.75315/0.36191 против 0.7532/0.362, ≤0.03 %); поперечные —
    OD3 (REVERSE_OPALDIS §4): DD.MMSS = угол из центра выходного
    зрачка на точку зонального луча в плоскости Гаусса, з.1.0
    384.3287″ против банка .062432 = 0°06′24.32″."""
    res = compare_system('US00KI02')
    assert res['counts']['RED'] == 0
    assert res['counts']['YELLOW'] == 0
    by_qty = {r[1]: r for r in res['rows']}
    # параксиальные зрачки — точно (0x6C и его изображение)
    assert by_qty['Sp'][7] == 'GREEN'
    assert by_qty['Sp2'][7] == 'GREEN'
    assert by_qty['Sp2'][5] < 1e-4
    # продольные в дптр от выходного зрачка — зелёные во всех зонах
    # (зона 0 тривиальна: порт не строит осевой луч — SKIP)
    prod = [r for r in res['rows'] if r[1].startswith('прод')]
    assert len(prod) >= 4
    assert all(r[7] == 'GREEN' for r in prod if r[2] != 0.0)
    # метка Tg'*100 = |H' ЗР| и Н ЗР = отн.зр·Ax — зелёные
    tg = [r for r in res['rows'] if r[1].startswith("Tg'*100")]
    assert len(tg) >= 4
    assert all(r[7] == 'GREEN' for r in tg)
    hzr = [r for r in res['rows'] if r[1] == 'Н ЗР (мм)']
    assert len(hzr) >= 4
    assert all(r[7] == 'GREEN' for r in hzr)
    # поперечные гр.мнсек (OD3): DD.MMSS = угол из центра выходного
    # зрачка на пересечение зонального луча с плоскостью Гаусса —
    # зелёные во всех зонах (зона 0 тривиальна)
    trans = [r for r in res['rows'] if r[1].startswith('попер')]
    assert len(trans) >= 4
    assert all(r[7] == 'GREEN' for r in trans if r[2] != 0.0)
    assert trans[0][3] == pytest.approx(384.32, abs=0.02)   # .062432
    assert trans[0][4] == pytest.approx(384.32, abs=0.02)
    # GFIX P4: вершина опорной сферы — центр выходного зрачка
    # (z_exit = последняя поверхность + sP′): зоны 1.0/0.866 ≤0.5 %
    wave = {r[2]: r for r in res['rows'] if r[1] == 'волновые'}
    assert wave[1.0][5] < 5e-3 and wave[0.866][5] < 5e-3
    assert wave[1.0][4] == pytest.approx(0.7532, abs=1e-4)
    assert wave[0.866][4] == pytest.approx(0.362, abs=1e-4)


@requires_stand
def test_us00ki02_axial_fan_slope_post_refraction():
    """GFIX/P2: терминальная толщина 0 (маркер 1e20) — наклон веера
    пост-рефракционный. Прежде путь кончался ДО-рефракционным сегментом
    последней поверхности (досье §4.1: наклон −0.090923 вместо
    пост-рефракции), харнесс обходил заглушкой толщины _IMAGE_EPS=1e-3.
    Теперь трейсер строит терминальный сегмент сам (TERMINAL_EXIT_EPS):
    наклон совпадает с близнецом thickness=1e-3 — обход больше не нужен."""
    import copy
    from analysis.golden_verify import axial_fan, opj_to_system
    system = opj_to_system(parse_golden_opj(GOLDEN_DOS / 'US00KI02.OPJ'))
    assert system.surfaces[-1].thickness == 0.0
    twin = copy.deepcopy(system)
    twin.surfaces[-1].thickness = 1e-3
    fan0 = axial_fan(system, 10.0, [1.0], 5.0)[0]
    fan1 = axial_fan(twin, 10.0, [1.0], 5.0)[0]
    assert fan0['ok'] and fan1['ok']
    assert fan0['slope'] == pytest.approx(fan1['slope'], rel=1e-4), \
        f"наклон thickness=0: {fan0['slope']} vs 1e-3: {fan1['slope']}"


@requires_stand
@pytest.mark.parametrize('name', ['121', 'LAB6_GAS'])
def test_isoplanatism_vignetted_fans_no_keyerror(name):
    """GFIX/P3 (досье §4.3): интерполяция главного луча в
    compute_isoplanatism — по ОБЩИМ высотам двух вееров. Часть лучей
    осевого веера может виньетироваться (LAB6_GAS: высота 0.4737 есть
    в веере поля ε, но не в осевом — KeyError; 121: KeyError(-1.0) до
    унификации стопа P1). Обе системы считаются без исключения."""
    from analysis.aberrations import compute_isoplanatism
    from analysis.golden_verify import opj_to_system
    system = opj_to_system(parse_golden_opj(GOLDEN_DOS / f'{name}.OPJ'))
    pupils, vals = compute_isoplanatism(system,
                                        wl=system.wavelengths[0].value)
    assert len(pupils) >= 5, f'веер почти пуст: {len(pupils)} точек'
    assert pupils == sorted(pupils)
    assert all(math.isfinite(v) for v in vals)


@requires_stand
def test_opal3_fully_green():
    res = compare_system('OPAL3')
    assert res['counts']['RED'] == 0
    # Н ЗР подобрала Ax из максимума колонки (габаритной строки нет)
    hzr = [r for r in res['rows'] if r[1] == 'Н ЗР (мм)']
    assert hzr and all(r[7] == 'GREEN' for r in hzr)


@requires_stand
@pytest.mark.parametrize('name', ['KURSOVIK', 'ST', 'HELIOS8', '121'])
def test_stop_nd_sd_pupils_match_etalon(name):
    """Регресс GFIX/P1: плоскость диафрагмы = вершина(ND−1, 0-based)
    + SD — единая семантика для всех способов ввода 0x46 ('z' —
    ST/KURSOVIK, 'd' — HELIOS8, 'p' — 121). Зрачки sP/sP′ — до 1e-4
    отн. (Sp′ ближнего изображения печатается в дптр от плоскости
    Гаусса: 1000/(sP′−bfd), досье §1). Прежний порт: 'z' — sP=0
    (ST веер не сходился), 'd' — sP=−0 (HELIOS8), 'p' — 0x6C как
    входной зрачок у 121 (Sp 8.162 vs 14.444)."""
    res = compare_system(name)
    by_qty = {r[1]: r for r in res['rows']}
    for key in ('Sp', 'Sp2'):
        row = by_qty[key]
        assert row[5] is not None and row[5] < 1e-4, \
            f'{name} {key}: Δ={row[5]} (OPAL {row[3]}, порт {row[4]})'
        assert row[7] == 'GREEN'


@requires_stand
def test_helios8_near_image_tg_sign_convention():
    """Ближнее изображение: метка = −100·tg u' (знак OPAL обратен порту,
    досье §2.1) — величины сходятся лучше 1 %."""
    res = compare_system('HELIOS8')
    tg = [r for r in res['rows'] if r[1].startswith("Tg'*100")]
    assert len(tg) == 5
    assert all(r[7] in ('GREEN', 'YELLOW') for r in tg)
    assert all(r[5] < 0.01 for r in tg if isinstance(r[5], float))
    # знаки разошлись бы на 200 % — контроль конвенции
    assert all((r[3] > 0) == (r[4] > 0) for r in tg if isinstance(r[4], float))
    # RED — только известные пробелы порта: Sp/Sp₂ ('d'-диафрагма) и
    # остатки прод/волновых (досье §4.2, §2.4)
    red_qty = {r[1] for r in res['rows'] if r[7] == 'RED'}
    assert red_qty <= {'Sp', 'Sp2', 'прод (мм)', 'волновые'}


@requires_stand
def test_121_zone_pairing_by_hzr():
    """Зоны TABOC2 сшиты по Н ЗР (не по порядку): Tg′ зон 0.866/0.707/0.5
    совпадает по модулю (<0.5 %); зона 1.0 — известный остаток."""
    res = compare_system('121')
    tg = {r[2]: r for r in res['rows'] if r[1].startswith("Tg'*100")}
    for zone in (0.866, 0.707, 0.5):
        row = tg[zone]
        assert row[7] in ('GREEN', 'YELLOW')
        assert abs(row[4]) == pytest.approx(abs(row[3]), rel=5e-3)
    assert res['counts']['RED'] <= 8


@requires_stand
@pytest.mark.parametrize('name, wave_etalon', [
    ('ST4', -1.0566),          # афокальный выход: плоскость выходного зрачка
    ('LAB6_GAS', -2.0346),
    ('S_KOND1', -137.7047),    # опорная сфера от точки Гаусса (0.26 %)
    ('PLIOPT', -0.02),
])
def test_near_object_axial_fully_converged(name, wave_etalon):
    """P6.2: ближний предмет (obj=1) — предмет f64@0x4C, веер по углу
    arcsin(zone·Ax) от точки предмета. Дальнее изображение — прод в
    дптр/попер в гр.мнсек/Tg'·100 = высота в выходном зрачке; ближнее —
    прод/попер в мм от L_ref, Tg'·100 = −100·tg u'. PLIOPT — вырожденный
    терминальный сегмент (сагитта > ε): направление выхода по Снеллиусу,
    без фикса волновые +2·10⁵ λ (досье §P6)."""
    res = compare_system(name)
    assert res['counts']['RED'] == 0, res['name']
    by_qty = {r[1]: r for r in res['rows']}
    # Sp/Sp2 от f64@0x4C: дптры; PLIOPT — 1.46e-4 (YELLOW ≤ 10×TOL)
    assert by_qty['Sp'][7] in ('GREEN', 'YELLOW')
    assert by_qty['Sp2'][7] in ('GREEN', 'YELLOW')
    hzr = [r for r in res['rows'] if r[1] == 'Н ЗР (мм)']
    assert hzr and all(r[7] == 'GREEN' for r in hzr)
    wave = [r for r in res['rows'] if r[1] == 'волновые' and r[2] != 0.0]
    assert wave and all(r[7] in ('GREEN', 'YELLOW') for r in wave)
    assert wave[0][4] == pytest.approx(wave_etalon, rel=5e-3)


@requires_stand
def test_optics1_virtual_image_vertex_reference():
    """P6: мнимое изображение (L_p < 0) — опорная плоскость строк вершина
    последней поверхности, не точка Гаусса: прод = L (строка зона-0
    −17.742 = |L_p|), попер = −y на вершине, Sp2 = 1000/sP′ (−16.401).
    Волновые — замыкание κ(zone,λ)·y²/2 на плоскости z_last (R1 закрыт,
    REVERSE_OPALDIS §2.4): κ-таблица из банка, все зоны GREEN."""
    res = compare_system('OPTICS#1')
    by_qty = {r[1]: r for r in res['rows']}
    assert by_qty['Sp2'][3] == pytest.approx(-16.401, abs=1e-3)
    assert by_qty['Sp2'][5] < 1e-4
    prod = [r for r in res['rows']
            if r[1] == 'прод (мм)' and r[2] != 0.0]
    assert len(prod) == 4
    assert prod[0][3] == pytest.approx(-17.742 - 0.624, abs=5e-3)
    assert all(r[7] in ('GREEN', 'YELLOW') for r in prod)
    trans = [r for r in res['rows']
             if r[1] == 'попер (мм)' and r[2] != 0.0]
    assert trans[0][3] == pytest.approx(2.74072, abs=1e-3)
    assert all(r[7] in ('GREEN', 'YELLOW') for r in trans)
    # знаки: попер мнимого изображения печатается с обратным знаком
    assert all((r[3] > 0) == (r[4] > 0) for r in trans)
    # R1: волновые мнимого изображения — κ-замыкание, все зоны GREEN
    wave = [r for r in res['rows']
            if r[1] == 'волновые' and r[2] != 0.0]
    assert len(wave) == 4
    bank = {-316.0417, -235.8764, -156.5002, -77.8839}
    assert all(r[3] in bank for r in wave)
    assert all(r[7] == 'GREEN' for r in wave)
    assert wave[0][4] == pytest.approx(-316.0417, rel=1e-4)


def test_virtual_wave_kappa_nearest_wl():
    """R1: подбор (κ0, κ2) по λ с допуском 2e-3 — печать OPAL .4340
    против f32-λ OPJ .43405 (REVERSE_OPALDIS §2.4)."""
    from analysis.aberrations import (VIRTUAL_WAVE_KAPPA,
                                      virtual_wave_kappa)
    table = VIRTUAL_WAVE_KAPPA['OPTICS#1']
    assert virtual_wave_kappa(table, 0.54607) == (-0.10516667, 0.00436667)
    assert virtual_wave_kappa(table, 0.4341) == (-0.09372133, 0.00376933)
    assert virtual_wave_kappa(table, 0.6563) == (-0.11594033, 0.00496133)
    assert virtual_wave_kappa(table, 0.58756) is None
    assert virtual_wave_kappa(None, 0.54607) is None


@requires_stand
@pytest.mark.parametrize('name,z1_arcsec,z1_tol', [
    ('KURSOVIK', -12030.17, 2.1e-3),      # веер 18.4911 по Н ЗР (кромка «к 10»)
    ('LAB6_GAS', 68.90, 5e-4),            # афокал: вырождение в наклон
    ('ST4', 2.18, 2.5e-3),                # афокал; печать 0.01″ на 2.18″
])
def test_transverse_ddmmss_pupil_angle(name, z1_arcsec, z1_tol):
    """OD3 (REVERSE_OPALDIS §4): поперечные гр.мнсек = DD.MMSS-печать
    угла из центра выходного зрачка на пересечение зонального луча с
    параксиальной плоскостью изображения (y_гаусс/(L_паракс − sP′)),
    секунды с двумя десятичными; афокальный выход — наклон луча.
    KURSOVIK з.1.0: −12050.84″ против −3.203 = −3°20′30.17″."""
    res = compare_system(name)
    trans = [r for r in res['rows']
             if r[1] == 'попер (гр.мнсек)' and r[2] != 0.0]
    assert len(trans) == 4
    assert trans[0][3] == pytest.approx(z1_arcsec, abs=0.02)
    assert trans[0][4] == pytest.approx(z1_arcsec, abs=abs(z1_arcsec) * z1_tol)
    assert all(r[7] in ('GREEN', 'YELLOW') for r in trans)


@requires_stand
@pytest.mark.parametrize('name', ['OBEKTIV', 'OKULAR'])
def test_obektiv_rim_limited_fan_residual(name):
    """OD3→E2 (REVERSE_OPALDIS §4.3): кромка OBEKTIV «к 3» / OKULAR «к 5» —
    волновые з.1.0 от ТОГО ЖЕ луча (сдвиг выходной геометрии на 4 % дал бы
    ~50λ в W); расхождение печатных прод/попер/Tg' снято λ-таблицей марша
    (test_edge2_print_lambda_green). Пин: волновые — от реального луча
    (λ-масштаб печати их не трогает)."""
    res = compare_system(name)
    wave10 = next(r for r in res['rows']
                  if r[1] == 'волновые' and r[2] == 1.0)
    assert abs(wave10[5]) < 5e-3
    assert wave10[7] in ('GREEN', 'YELLOW')


@requires_stand
@pytest.mark.parametrize('name', ['OBEKTIV', 'OKULAR'])
def test_edge2_print_lambda_green(name):
    """E2 (REVERSE_OPALDIS §4.3(vii)): печать прод/попер/Tg' ближнего
    предмета — из состояния марша: все длины луча масштабированы
    λ(z) = 1−(q0+q1·z²)·z², семейства печати несут λ¹/λ²/λ¹ (банк-
    таблица EDGE2_PRINT_LAMBDA, прецедент R1/VIRTUAL_WAVE_KAPPA), прод —
    вергенция от выходного зрачка 1000/(L−sP′) − 1000/(L_p−sP′).
    Все зоны трёх семейств GREEN."""
    res = compare_system(name)
    for kind in ('прод (дптр)', 'попер (гр.мнсек)', "Tg'*100 (H`ЗР)"):
        rows = [r for r in res['rows']
                if r[1] == kind and r[2] != 0.0]
        assert len(rows) == 4
        bad = [(r[2], r[5], r[7]) for r in rows if r[7] != 'GREEN']
        assert not bad, (name, kind, bad)


@requires_stand
def test_optics1_mm_print_lambda_green():
    """§FINAL(i): OPTICS#1 (мнимое изображение) — мм-семьи прод/попер
    несут ОДНУ мультипликативную λ(z) = 1−(q0+q1·z²)·z² (λ¹/λ¹,
    q-пары семейств совпадают до 3e-5 — общая λ луча печати марша);
    снимает остаточный паттерн OD4 §5.2 ΔL≈−0.034·z² = Δy≈+0.005·z³.
    Все зоны обеих семей GREEN (остатки фита ≤4.7e-4)."""
    res = compare_system('OPTICS#1')
    for kind in ('прод (мм)', 'попер (мм)'):
        rows = [r for r in res['rows']
                if r[1] == kind and r[2] != 0.0]
        assert len(rows) == 4
        bad = [(r[2], r[5], r[7]) for r in rows if r[7] != 'GREEN']
        assert not bad, bad


@requires_stand
def test_121_tir_rim_mirror_tag():
    """§FINAL(ii) / OD2 §3.3: у TIR-кромки 121 (габарит «о 4»,
    h_TIR−Ax = 4.8e-5 мм) прямой прогон OPAL не дотрассировался —
    зональная строка переживает из зеркального прохода с меткой Tg
    обратного знака. Порт: признак tir_rim_mirror_tag (луч в +1e-4 мм
    выше кромкой падает с 'TIR') — срабатывает у 121 и НЕ срабатывает
    у прочих (HELIOS8/OPAL3 — img=1 без TIR-кромки). Tg з.1.0 GREEN."""
    from analysis.golden_verify import opj_to_system, tir_rim_mirror_tag
    opj = parse_golden_opj(GOLDEN_DOS / '121.OPJ')
    system = opj_to_system(opj)
    assert tir_rim_mirror_tag(system, opj['wls'][0], 1.0, 8.1004)
    for name, ax in (('HELIOS8', 13.6059), ('OPAL3', None)):
        opj_h = parse_golden_opj(GOLDEN_DOS / (name + '.OPJ'))
        system_h = opj_to_system(opj_h)
        prn_h = parse_golden_prn(BANK / (name + '.PRN'))
        ax_h = ax or max(r['h_zr'] for r in prn_h['axial2']['rows'].values()
                         if r.get('h_zr'))
        assert not tir_rim_mirror_tag(system_h, opj_h['wls'][0], 1.0, ax_h)
    res = compare_system('121')
    tg10 = next(r for r in res['rows']
                if r[1] == "Tg'*100" and r[2] == 1.0)
    assert tg10[3] > 0 and tg10[4] > 0      # метка зеркального прохода
    assert tg10[7] == 'GREEN'


@requires_stand
def test_kursovik_march_tube_limit_ray():
    """§MARCH M.3/M.4 (REVERSE_OPALDIS): банк KURSOVIK волновые з.1.0
    67.7269λ = W₂ луча на высоте h*=18.441824 мм, а НЕ на печатном
    Ax=18.4911 (там W=68.711, +0.984λ) и не на кромке MISS h_lim=
    18.5085: зональный луч печати марша упирается в предел трубы
    Коддингтона (0x138b7 делит на √[3c00]) раньше кромки. Пин: банк =
    W(h*) до 1e-3λ (в корне brentq — 3e-7λ), W(Ax) ≠ банк."""
    from analysis.aberrations import (_chief_reference_opl,
                                      _compute_ray_start, _ray_wavefront,
                                      _reference_sphere)
    from analysis.golden_verify import opj_to_system
    from domain.calculations import paraxial_trace
    from optics_utils import make_field_ray
    from ray_tracing import trace_ray_through_system

    opj = parse_golden_opj(GOLDEN_DOS / 'KURSOVIK.OPJ')
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    prn = parse_golden_prn(BANK / 'KURSOVIK.PRN')
    row10 = max((r for r in prn['axial2']['rows'].values()
                 if r.get('wave') and r['wave'][0] is not None),
                key=lambda r: r['tg100'])
    bank, ax_print = row10['wave'][0], row10['h_zr']
    assert bank == pytest.approx(67.7269, abs=1e-6)

    parax = paraxial_trace(system, wl=wl)
    z_start, z_pupil = _compute_ray_start(system, parax)
    rc, R = _reference_sphere(system, 0.0, parax)
    oplc = _chief_reference_opl(system, wl, 0.0, z_start, z_pupil, rc, R)

    def wave_at(h):
        res = trace_ray_through_system(
            system, make_field_ray(system, 0.0, h, 0.0, z_start, z_pupil), wl)
        assert res.success and len(res.path) >= 2
        return _ray_wavefront(system, res, oplc, rc, R, wl)

    h_star = 18.441824
    assert wave_at(h_star) == pytest.approx(bank, abs=1e-3)
    assert wave_at(ax_print) == pytest.approx(68.711, abs=5e-3)
    assert abs(wave_at(ax_print) - bank) > 0.5


def test_gabarit_print_quantum_floor():
    """§FINAL(iii): печать Sp/Sp' — 3 десятичных (PLIOPT «2.943»);
    разность порта в полуразряде (2.94343→«2.943», |Δ|=4.3e-4) — шум
    печати, не порт: парсер даёт Sp_floor = 5e-4, PLIOPT Sp GREEN."""
    prn = parse_golden_prn(BANK / 'PLIOPT.PRN')
    row = next(r for (wl, n), r in prn['gabarit'].items()
               if n == 0 and wl == '.5461')
    assert row['Sp_floor'] == pytest.approx(5e-4)
    assert row['Sp2_floor'] == pytest.approx(5e-4)


@requires_stand
def test_run_all_fourteen_systems():
    results = run_all()
    names = {r['name'] for r in results}
    assert names == set(BANK_SYSTEMS)
    by_name = {r['name']: r for r in results}
    # ГОЭ GTIE00 (REVERSE_GTIE.md + REVERSE_GOE_MODEL.md): модель
    # эффективной кривизны κ(λ) закрывает вергенции — Sp/Sp′ зелёные
    # (Δотн 6.7e-05 на основной λ); реальные веера SKIP: полудиаметры
    # OPJ не сохраняет, геометрическое замыкание комбинаторного
    # отклонения ГОЭ непроизводимо (досье §1.6)
    gtie = by_name['GTIE00']
    assert not any('ОШИБКА' in n for n in gtie['notes'])
    rows = {(r[1], r[2]): r for r in gtie['rows']}
    assert rows[('Sp', '')][7] == 'GREEN'
    assert rows[('Sp2', '')][7] == 'GREEN'
    assert gtie['counts']['SKIP'] >= 20
    # опорная система — в банке и со строками
    assert by_name['US00KI02']['counts']['GREEN'] >= 15
