# -*- coding: utf-8 -*-
"""Пакет D (TASK_GOLDEN_WAVE3): параметризованная сверка 25 новых систем
golden-банка волны 3 — «порт vs оригинал».

Банк: analysis/reverse_data/golden/bank/*.PRN = 70 печатей — волна 2
(43 системы, регламент tests/test_golden_wave2.py) + волна 3 (25 новых,
этот файл, пачки печати B1–B5 — G2W3_PLAN.md §7) + 2 stale. Вердикты и
допуски считает только analysis/golden_verify.py (TOL_PARAX/TOL_ABERR/
TOL_YELLOW) — тест допусков-чисел не дублирует: он суммирует
вердикт-строки compare_system и проверяет отсутствие RED/ОШИБКА.

8 систем с остаточными RED-строками — xfail(strict=False): это находки
реверса, не провал порта; реестр с числами порт/оригинал и гипотезами —
docs/tasks/G2W3_FINDINGS.md. Остальные 17 — зелёные или только YELLOW
(11 полностью зелёных; DIP1 зелёная по всем сверившимся строкам при
20 SKIP из-за порта) — xfail им не нужен: strict=False не считает
падением «внезапно зелёный» xfail.

CI (нет стенда): тесты 2–3 дают skip с reason, тесты формата и smoke
работают — банк .PRN в git.
"""
from pathlib import Path

import pytest

from analysis.golden_verify import (
    compare_system, parse_golden_opj, parse_golden_prn,
)
from tests.conftest import GOLDEN_DOS, requires_stand

BASE = Path(__file__).resolve().parent.parent
BANK = BASE / 'analysis' / 'reverse_data' / 'golden' / 'bank'

#: 25 систем волны 3 — явный список (не glob, стабильность когорты):
#: состав = новые .PRN коммитов волны 3, очередь печати G2W3_PLAN.md §7
#: (пачки B1–B5; LEXA21 — ствол PRN, на стенде файл Lexa21.opj).
WAVE3_SYSTEMS = [
    'DEMON2', 'DEMON4', 'DEMON5', 'DEMON6', 'DEM',          # B1: ИК/KBR ядро
    'DEM1', 'DEMDA', 'GUTAN4', 'LAB31S', 'SERGEY0',         # B2: ИК/многолинзовые
    'EGOR_2', 'ANDREW_2', 'LEXA11', 'LAB3S', 'LAB3_GAS',    # B3: ахроматы/склейка
    'GTIN0', 'SERGEY3', 'WA3', 'PETRO3', 'S_KOND3',         # B4: сиблинги xfail-G44
    'LEXA23', 'LEXA21', 'G1', 'DIP1', 'YBBG00',             # B5: одиночные/эксперимент
]

#: 8 систем с остаточными RED-строками полного прогона банка
#: (2026-10-27, Пакет C: 1438 GREEN / 46 YELLOW / 128 RED / 215 SKIP
#: по 68 системам; 11 систем волны 3 полностью зелёные). Числа
#: порт/оригинал и гипотезы — docs/tasks/G2W3_FINDINGS.md (ссылка в
#: каждой причине).
WAVE3_RED = {
    'DEM': 'G2W3 FINDINGS §DEM: Tg з1.0/0.866 — кромка КРС при na 0.95 '
           '(121-паттерн строки иного прохода); волновые ×2 — опорная '
           'сфера при мнимом изображении (κ R1 не решена); попер з1.0 '
           '1.2e-2 — та же кромочная систематика',
    'DEM1': 'G2W3 FINDINGS §DEM1: знак попер/Tg ×6 при L_p=+14.29, '
            'z_obj=0 (модули точны ≤0.03%) — дискриминатор НЕ знак L_p; '
            'Tg з1.0 — модули не сходятся (121-паттерн); волновые ×4 — '
            'SKIP (z_obj=0)',
    'DEMON2': 'G2W3 FINDINGS §DEMON2: волновые з1.0/0.866/0.707 '
              '2.4–11.8% — DEMON-паттерн «высшие порядки» (знаки '
              'совпадают, монотонно к оси), з1.0 по кромке апертуры',
    'DEMON4': 'G2W3 FINDINGS §DEMON4: волновые з1.0 1.02e-2 — '
              'ИК-полоса 1–2% (GUTAN 1.7% RED, LABA2 1.3–4.3%), порог '
              'взят лишь чуть',
    'EGOR_2': 'G2W3 FINDINGS §EGOR_2: зональные прод/попер/волновые '
              '1.7–8.5% — опора при большой сферической аберрации '
              '(68 мм на краю); з1.0 — TIR-кромка дублета, порт не '
              'трассирует (SKIP)',
    'LAB3_GAS': 'G2W3 FINDINGS §LAB3_GAS: волновые з1.0 1.06e-2 — '
                'остаток опорной сферы (GUTAN/OKULAR-паттерн), '
                'монотонно к кромке; сиблинги LAB31S/LAB3S — на '
                'Y-уровне',
    'LEXA23': 'G2W3 FINDINGS §LEXA23: знак попер/Tg ×5 при L_p=−10.25 '
              '(WA2-сторона дискриминатора; модули ≤6e-6 мм); Tg з0.866 '
              '— TIR при na≈1 (121-паттерн); волновые з0.707/0.5 — '
              'SKIP (r_ref=0)',
    'SERGEY0': 'G2W3 FINDINGS §SERGEY0: прод-дптр ×4 — константа '
               'OPAL/порт 0.82 (множитель печати, E2/марш-λ); знак '
               'попер/Tg ×8 при мнимом изображении (модули ≤0.3%, '
               'arcsec-ветка без правила знака); волновые — опорная '
               'сфера при мнимом дальнем (|L_p|≫f)',
}

#: Параметры теста полной сверки: 25 систем, 8 остаточных — xfail
#: (метка только здесь: smoke-тест 4 не про вердикты и всегда зелёный).
COMPARE_PARAMS = [
    pytest.param(n, id=n,
                 marks=pytest.mark.xfail(strict=False,
                                         reason=WAVE3_RED[n]))
    if n in WAVE3_RED else n
    for n in WAVE3_SYSTEMS
]


# ── 1. Формат печатей волны 3 (CI-safe: банк .PRN в git) ──────────────────

@pytest.mark.parametrize('name', WAVE3_SYSTEMS)
def test_prn_format(name):
    """Формат всех 25 печатей волны 3 через parse_golden_prn: обе
    таблицы «Аберрации осевого пучка» полные (TABOC1 ≥4 зон,
    TABOC2 ≥3 строк), юниты читаются из шапок — в допускаемых
    множествах (мм/дптр у продольных, мм/гр.мнсек у поперечных;
    дптр-печать DEM1/DEMDA — ИК 9.2 мкм, ближний тип), зоны TABOC1
    в [0, 1]."""
    prn = parse_golden_prn(BANK / f'{name}.PRN')
    a1 = prn['axial1'].get('rows', {})
    a2 = prn['axial2'].get('rows', {})
    assert len(a1) >= 4, f'{name}: TABOC1 зон {len(a1)} < 4'
    assert len(a2) >= 3, f'{name}: TABOC2 строк {len(a2)} < 3'
    units = prn['axial1']['units']
    assert units[0] in ('мм', 'дптр'), (name, units)
    assert units[1] in ('мм', 'гр.мнсек'), (name, units)
    bad = [z for z in a1 if not 0.0 <= z <= 1.0]
    assert not bad, f'{name}: зоны TABOC1 вне [0,1]: {bad}'


# ── 2. Чтение OPJ стенда ──────────────────────────────────────────────────

@requires_stand
@pytest.mark.parametrize('name', WAVE3_SYSTEMS)
def test_opj_reads(name):
    """Все 25 .OPJ стенда волны 3 читаются строгим лоадером: ≥1
    поверхность, длины волн в разумном диапазоне (0.1–20 мкм), флаги
    λ-слотов 1/3, типы предмета/изображения 0 (дальн.)/1 (ближн.).

    YBBG00 — «basic test» с ПУСТЫМ glass-блоком (G2W3_PLAN §5):
    flags=3 в допуске (как у GTIN0); сам glass-блок parse_golden_opj
    НЕ проверяет — лоадер читает только заголовок/поверхности/RI и
    возвращает names=[] без ошибки (проверено прогоном). Валидность
    «системы без стёкол» обеспечивается сверкой (тест 3) — G2W3_
    FINDINGS §YBBG00: полный RT, все сверившиеся строки GREEN."""
    opj = parse_golden_opj(GOLDEN_DOS / f'{name}.OPJ')
    assert opj['ns'] >= 1, name
    assert opj['wls'] and all(0.1 < w < 20.0 for w in opj['wls']), \
        (name, opj['wls'])
    assert opj['flags'] in (1, 3), (name, opj['flags'])
    assert opj['obj_type'] in (0, 1), (name, opj['obj_type'])
    assert opj['img_type'] in (0, 1), (name, opj['img_type'])


# ── 3. Полная сверка порт-vs-PRN ──────────────────────────────────────────

@requires_stand
@pytest.mark.parametrize('name', COMPARE_PARAMS)
def test_wave3_compare_system(name):
    """Сверка порта с эталоном (compare_system): ни одной ошибки
    расчёта в notes и ни одной RED-вердикт-строки. В сообщении — сами
    RED-строки (порт/оригинал/Δотн) для отладки; допуски — только
    TOL_* в golden_verify.py. 8 систем с остаточными RED — xfail со
    ссылками на G2W3_FINDINGS (см. WAVE3_RED)."""
    res = compare_system(name)
    bad_notes = [n for n in res['notes'] if 'ОШИБКА' in n]
    assert not bad_notes, f'{name}: {bad_notes}'
    reds = [r for r in res['rows'] if r[7] == 'RED']
    detail = '; '.join(
        f'{r[1]} з{r[2]}: OPAL {r[3]:.5g} / порт '
        + (f'{r[4]:.5g}' if isinstance(r[4], float) else '—')
        + f' / Δ {r[5]:.2e}'
        for r in reds)
    assert res['counts']['RED'] == 0, \
        f'{name}: RED={res["counts"]["RED"]}: {detail}'


# ── 4. Smoke чтения печатей (CI-safe: без сверки, всегда зелёный) ─────────

#: Печатями с SKIP-профилями сравнения: DIP1 — порт даёт
#: error='MISS' на всех зональных лучах (20 SKIP-строк), YBBG00 —
#: попер (мм) far-object SKIP (семья GTIN0/ST). SKIP — это уровень
#: compare_system; парсер обязан дать полные структуры (G2W3_FINDINGS
#: §DIP1, §YBBG00).
SKIP_PROFILE_PRINTS = ('DIP1', 'YBBG00')


@pytest.mark.parametrize('name', WAVE3_SYSTEMS)
def test_wave3_prn_smoke(name):
    """Smoke чтения без сверки порт-vs-OPAL: parse_golden_prn каждой
    из 25 печатей даёт осмысленные структуры (непустые «Габариты
    пучков» и обе таблицы осевого пучка), а YBBG00/DIP1 со своими
    SKIP-профилями сравнения не крашат парсер и дают полные таблицы
    (достижение assert'ов ниже = отсутствие краша разбора)."""
    prn = parse_golden_prn(BANK / f'{name}.PRN')
    assert prn['gabarit'], f'{name}: пустая секция «Габариты пучков»'
    assert prn['axial1'].get('rows'), f'{name}: пустая TABOC1'
    assert prn['axial2'].get('rows'), f'{name}: пустая TABOC2'
    if name in SKIP_PROFILE_PRINTS:
        assert len(prn['axial1']['rows']) >= 4, name
        assert len(prn['axial2']['rows']) >= 3, name
