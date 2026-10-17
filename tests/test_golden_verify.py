# -*- coding: utf-8 -*-
"""Тесты золотой верификации порта против банка .PRN (TASK_GVERIFY).

Эталоны: analysis/reverse_data/golden/bank/*.PRN (14 систем,
DOSBox-прогон OPAL, CP866); рецепты: C:\\GOLDEN_DOS\\*.OPJ (стенд —
только чтение; end-to-end тесты пропускаются без стенда).
Взломанные конвенции — analysis/REVERSE_GVERIFY.md §2.
"""
from pathlib import Path

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
    """Опорная система: все развёрнутые конвенции зелёные; RED — только
    волновые зоны 1.0/0.866 с остатком ~2–3 % (опорная сфера, досье
    §2.4)."""
    res = compare_system('US00KI02')
    reds = [r for r in res['rows'] if r[7] == 'RED']
    assert len(reds) == 2
    assert all(r[1] == 'волновые' for r in reds)
    assert all(r[5] < 0.05 for r in reds)
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
    # поперечные — конвенция не сведена (досье §2.5): SKIP
    trans = [r for r in res['rows'] if r[1].startswith('попер')]
    assert trans and all(r[7] == 'SKIP' for r in trans)


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
def test_near_object_systems_skipped_with_note():
    """obj=1: конвенции не реверсированы (досье §3) — строки пропущены с
    заметкой вместо ложного RED."""
    for name in ('ST4', 'OKULAR', 'S_KOND1'):
        res = compare_system(name)
        assert res['counts']['RED'] == 0
        assert any('ближний предмет' in n for n in res['notes'])


@requires_stand
def test_run_all_fourteen_systems():
    results = run_all()
    names = {r['name'] for r in results}
    assert names == set(BANK_SYSTEMS)
    by_name = {r['name']: r for r in results}
    # ГОЭ-голограмма: standalone-раскладка отличается (досье §6)
    assert any('ОШИБКА' in n for n in by_name['GTIE00']['notes'])
    # опорная система — в банке и со строками
    assert by_name['US00KI02']['counts']['GREEN'] >= 15
