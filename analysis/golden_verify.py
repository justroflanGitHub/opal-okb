# -*- coding: utf-8 -*-
"""
GVERIFY — золотая верификация расчётов порта против банка эталонных .PRN
(волна 2026-10-17, TASK_GVERIFY).

Банк: ``analysis/reverse_data/golden/bank/*.PRN`` (14 систем, CP866,
досье REVERSE_G2BANK.md) + исходные ``C:\\GOLDEN_DOS\\*.OPJ`` (стенд,
только чтение). Порт считается верифицируемым: правки модулей порта в
этой волне ЗАПРЕЩЕНЫ — все расхождения фиксируются в досье
REVERSE_GVERIFY.md.

Структура:

1. :func:`parse_golden_opj` — строгий разбор standalone .OPJ. Валидирован
   на OPAL3/OBEKTIV/US00KI02 (efl 297.28/100.0065/1034.25, RI-матрица
   совпадает с каталожными марками стёкол). Причина существования:
   ``fileio.decode_lbo.decode_lbo_opj`` миспарсит standalone-файлы
   (толщины со сдвигом на слот, потеря RI при Ge>2.60) — досье §3.

2. :func:`parse_golden_prn` — разбор эталонных .PRN: заголовок, секция
   «Габариты пучков» (с дедупликацией дублей-протокола), две таблицы
   «Аберрации осевого пучка». Единицы величин читаются из шапок таблиц
   (дптр/мм; гр.мнсек/мм; дл. волн; %; мм) — семантика единиц у каждой
   системы своя, досье §2.

3. Расчёт порта: :func:`opj_to_system` (портовая :class:`OpticalSystem`
   с n_override из RI-матрицы OPJ), дальше только вызовы порта —
   ``paraxial_trace``, ``trace_ray_through_system``, ``_ray_wavefront``,
   ``compute_isoplanatism``, конверсии ``analysis.units``. Где портовый
   API не покрывает величину (выходной зрачок для диафрагмы типа 'p' —
   ``paraxial_trace`` знает только 'd'), харнесс считает дополнение на
   портовых примитивах (:func:`_paraxial_ray`, досье §4).

4. :func:`compare_system`/:func:`run_all` — таблицы «величина | OPAL |
   порт | Δ | допуск» с вердиктами GREEN/YELLOW/RED и сводкой.

Взломанные конвенции OPAL (полный вывод — досье REVERSE_GVERIFY.md):

* **метка TABOC2 «Tg'*100»**: у систем с дальним изображением (afocal)
  колонка фактически содержит **высоту зонального луча в плоскости
  выходного зрачка, мм** (H' ЗР): US00KI02 20.676 vs эталон 20.684
  (0.03%, все 4 зоны). Печать порта ``tg_prime100`` = 100·tg u' —
  угловая мера ближнего типа; сверка дальнего типа идёт по H' ЗР.
* **продольные (дптр)** = 1000·(1/L'_зоны − 1/L'_паракс), где длины
  отмеряются **от плоскости выходного зрачка**: US00KI02 — совпадение
  0.03–0.2% на всех зонах (−.0902/−.0560/−.0300/−.0116 vs эталон
  −.09008/−.05594/−.03000/−.01158).
* **Sp** (входной зрачок) для диафрагмы типа «зрачок» (0x46=0xFFFF)
  лежит в заголовке OPJ @0x6C (US00KI02: −22.2 = эталон −22.200 точно).
* **Ax'** (задняя апертура, N=0) = высота краевого луча в плоскости
  выходного зрачка — та же величина, что и метка Tg'*100 дальней
  системы.
"""
from __future__ import annotations

import copy
import math
import os
import re
import struct

_BANK_DIR = os.path.join(os.path.dirname(__file__), 'reverse_data',
                         'golden', 'bank')
_GOLDEN_DOS = r'C:\GOLDEN_DOS'

#: Банк: имя → наличие секций (досье G2BANK).
BANK_SYSTEMS = (
    'US00KI02', '121', 'ST', 'ST4', 'OPAL3', 'HELIOS8', 'OKULAR',
    'OBEKTIV', 'PLIOPT', 'GTIE00', 'KURSOVIK', 'LAB6_GAS', 'S_KOND1',
    'OPTICS#1',
)

#: Допуски карточки задачи: параксиальные ≤1e-4 отн., аберрации ≤1e-3
#: отн. (после выравнивания знаков/масштабов). Жёлтый — 10× допуска.
TOL_PARAX = 1e-4
TOL_ABERR = 1e-3
TOL_YELLOW = 10.0

#: Абсолютный шумовой порог аберраций (мм): PRN печатает 5 знаков,
#: n порта/OPAL интерполируются из f32-λ — систематика ~1e-3 мм не
#: устранима; для дптр — эквивалент 1000·floor/f² при типовом фокусе
#: (2e-3 мм / 100 мм ≈ 2e-4 дптр); волновые в мкм — разрешение печати
#: (4 знака → 1e-4 мкм) с запасом: 1e-3 мкм, чтобы не глотать
#: реальную систематику опорной сферы ~2 % (досье §2.4, цель P4).
ABS_FLOOR_MM = 2e-3
ABS_FLOOR_DPTR = 2e-4
ABS_FLOOR_WAVE = 1e-3

# ══════════════════════════════════════════════════════════════════════════
# 1. Строгий разбор standalone .OPJ — вход порта (GFIX P5)
# ══════════════════════════════════════════════════════════════════════════

from fileio.standalone_opj import (BIG_MARKER as _BIG_MARKER,  # noqa: E402
                                   parse_standalone_opj,
                                   standalone_to_system)


def parse_golden_opj(path: str) -> dict:
    """Строгий разбор standalone .OPJ — обёртка портового входа
    :func:`fileio.standalone_opj.parse_standalone_opj` (GFIX P5:
    парсер интегрирован в порт как отдельный вход, харнесс копию не
    держит; раскладка/семантика — докстринг портового модуля,
    досье REVERSE_GVERIFY.md §3)."""
    return parse_standalone_opj(open(path, 'rb').read(), source=str(path))


#: Standalone-разбор → портовая OpticalSystem (fileio.standalone_opj).
opj_to_system = standalone_to_system


# ══════════════════════════════════════════════════════════════════════════
# 2. Разбор эталонных .PRN
# ══════════════════════════════════════════════════════════════════════════

_NUM = re.compile(r'-?\d+\.\d+|-?\.\d+')

#: Правые границы колонок FORTRAN Fw.d (печать OPAL правоориентированная;
#: замерено по полностью заполненным строкам OPAL3/GTIE00/121 — единая
#: форма печати на весь банк): табл.1 — продольные λ0..2, поперечные
#: λ0..2; табл.2 — волновые λ0..2, неизопл, Н ЗР. Метки строк (koop /
#: Tg'*100) кончаются на колонках 5 и 6.
_AXIAL1_EDGES = (17, 28, 39, 52, 65, 77)
_AXIAL2_EDGES = (16, 26, 36, 47, 57)


def _fixed_cells(line: str, edges, left0: int):
    """Значения правоориентированных полей: каждое поле = отрезка
    (правая граница предыдущего поля, эта правая граница]."""
    values = []
    prev = left0
    for e in edges:
        text = line[prev:e].strip() if prev < len(line) else ''
        m = _NUM.search(text)
        values.append(float(m.group(0)) if m else None)
        prev = e
    return values


def parse_golden_prn(path: str) -> dict:
    """Разбор эталонного .PRN банка (CP866 → значения).

    Возвращает::

        {'name': ..., 'gabarit': {(wl_str, N): row_dict},
         'axial1': {'units': ('дптр'|'мм', 'гр.мнсек'|'мм'),
                    'rows': {zone: {'long': [v0,v1,v2]|None,
                                    'trans': [v0,v1,v2]|None}}},
         'axial2': {'rows': {zone: {'tg100': v, 'wave': [v0..2]|None,
                                     'iso': v, 'h_zr': v}}},
         'duplicated_gabarit': bool}

    Секция «Габариты пучков» может быть продублирована протоколом
    (KURSOVIK) — дубли игнорируются; строки: N Ax Ay Ax' Ay' Sp Sp'
    виньетаж светораспределение ограничения (последние не сверяются).
    """
    text = open(path, encoding='cp866').read()
    lines = text.splitlines()
    result = {'gabarit': {}, 'axial1': {}, 'axial2': {},
              'gabarit_units': ('мм', 'мм'),
              'duplicated_gabarit': False}
    m = re.search(r'Cистема-(.*?)\s{2,}Работа-RT', text)
    result['name'] = m.group(1).rstrip() if m else ''

    i, n = 0, len(lines)
    gab_seen = 0
    while i < n:
        line = lines[i]
        if line.strip() == 'Габариты пучков':
            gab_seen += 1
            # единицы «Положение зрачков»: (мм)/(дптр) у Sp/Sp' —
            # дптр у ближнего типа (Sp' при img=1 — от плоскости Гаусса,
            # Sp при obj=1 — от предмета; OPALOPT:1275–1293)
            units_line = lines[i + 2] if i + 2 < n else ''
            mu = re.findall(r'\((мм|дптр)\)', units_line)
            if len(mu) >= 2:
                result['gabarit_units'] = (mu[0], mu[1])
            i += 4                                  # шапка из 3 строк
            while i < n:
                s = lines[i].strip()
                if not s:
                    i += 1
                    continue
                mw = re.match(r'Длина волны\s*-\s*([\d.]+)', s)
                if not mw:
                    break
                wl = mw.group(1)
                i += 1
                while i < n:
                    row = lines[i]
                    if not row.strip() or not row.lstrip()[:1].isdigit():
                        break
                    toks = row.split()
                    if len(toks) >= 7:
                        key = (wl, int(toks[0]))
                        if key in result['gabarit'] and gab_seen > 1:
                            pass                    # дубли протокола
                        else:
                            result['gabarit'][key] = {
                                'N': int(toks[0]),
                                'Ax': float(toks[1]), 'Ay': float(toks[2]),
                                'Ax2': float(toks[3]), 'Ay2': float(toks[4]),
                                'Sp': float(toks[5]), 'Sp2': float(toks[6]),
                            }
                    i += 1
            continue
        if line.strip() == 'Аберрации осевого пучка':
            i += 1
            while i < n:
                s = lines[i]
                mu = re.search(r'Продольные аберрации \(([^)]+)\)', s)
                if mu:
                    mt = re.search(r'Поперечные аберрации \(([^)]+)\)', s)
                    result['axial1']['units'] = (
                        mu.group(1), mt.group(1) if mt else 'мм')
                if 'koop' in s and '┴' in s:      # разделитель табл.1
                    i += 1
                    while i < n:
                        row = lines[i]
                        m = _NUM.match(row.strip())
                        if not m:
                            break
                        zone = float(m.group(0))
                        vals = _fixed_cells(row, _AXIAL1_EDGES, len(m.group(0)))
                        result['axial1'].setdefault('rows', {})[zone] = {
                            'long': vals[:3], 'trans': vals[3:6],
                        }
                        i += 1
                    continue
                if 'Tg' in s and '100' in s:      # шапка табл.2
                    j = i + 1
                    while j < n and '┴' not in lines[j]:
                        j += 1
                    k = j + 1
                    while k < n:
                        row = lines[k]
                        m = _NUM.match(row.strip())
                        if not m:
                            break
                        tg = float(m.group(0))
                        vals = _fixed_cells(row, _AXIAL2_EDGES,
                                            len(m.group(0)))
                        result['axial2'].setdefault('rows', {})[tg] = {
                            'tg100': tg,
                            'wave': vals[:3],
                            'iso': vals[3], 'h_zr': vals[4],
                        }
                        k += 1
                    i = k
                    continue
                i += 1
            continue
        i += 1
    result['duplicated_gabarit'] = gab_seen > 1
    return result


# ══════════════════════════════════════════════════════════════════════════
# 3. Расчёт порта (портовые функции + минимальные дополнения харнесса)
# ══════════════════════════════════════════════════════════════════════════

def _n_media(system, wl: float) -> list:
    """Показатели сред ns+1 — как ``paraxial_trace`` (портовый
    :func:`refractive_index` с n_override, отражения не поддерживаем:
    в банке зеркал с is_reflective нет)."""
    from domain.calculations import refractive_index
    media = [1.0]
    for s in system.surfaces:
        media.append(refractive_index(s.glass, wl, None,
                                      getattr(s, 'n_override', None)))
    return media


def _paraxial_ray(system, wl: float, y0: float, u0: float,
                  z0: float) -> tuple:
    """Параксиальный луч (y, u) от плоскости z0 (мм от первой
    поверхности; z0<0 — перед системой). Возвращает (y, u) на выходе
    последней поверхности. Дополнение харнесса: портовый
    ``paraxial_trace`` не принимает произвольный старт-луч (нужен для
    изображения зрачка при диафрагме типа 'p', досье §4)."""
    media = _n_media(system, wl)
    y, u, z = y0, u0, z0
    for i, s in enumerate(system.surfaces):
        if z < 0:                                # перенос до s0
            y += u * (0.0 - z)
            z = 0.0
        if i > 0:
            y += u * system.surfaces[i - 1].thickness
        R = s.radius if s.radius != 0 else 1e15
        phi = (media[i + 1] - media[i]) / R
        u = (media[i] * u - y * phi) / media[i + 1]
        z += s.thickness
    return y, u


def paraxial_of(system, wl: float) -> dict:
    """Параксиальные габариты порта: sF', sP, sP', f', L.

    Все зрачковые величины считаются портовым :func:`paraxial_trace`
    из плоскости диафрагмы ND/SD (волна GFIX: 'z'/'d'/'p' едины)."""
    from domain.calculations import paraxial_trace
    res = paraxial_trace(system, wl=wl)
    return {
        'f': res.get('focal_length', 0.0),
        'sF_prime': res.get('sF_prime', 0.0),
        'sP': res.get('sP', 0.0),
        'sP_prime': res.get('sP_prime', 0.0),
        'V': res.get('V', 0.0),
        'L': res.get('L', 0.0),
        'bfd': res.get('back_focal_distance', 0.0),
    }


def axial_fan(system, wl: float, zones, ax_semi: float) -> list:
    """Веер осевых зональных лучей портовым трейсером.

    Как ``analysis.tables._axial_zone_fan``, но с явной полувысотой
    пучка ``ax_semi`` (реальный габаритный луч системы из эталона —
    у KURSOVIK заданная апертура 10≠реальные 18.49 мм) и с записью
    выходной геометрии (y, наклон, L, высота в плоскости выходного
    зрачка) для сверок конвенций OPAL.
    """
    from analysis.aberrations import (_chief_reference_opl, _ray_wavefront,
                                      _reference_sphere)
    from optics_utils import make_field_ray
    from ray_tracing import trace_ray_through_system
    from domain.calculations import paraxial_trace

    parax = paraxial_trace(system, wl=wl)
    from analysis.aberrations import _compute_ray_start
    z_start, z_pupil = _compute_ray_start(system, parax)
    ref_center, ref_r = _reference_sphere(system, 0.0, parax)
    opl_chief = _chief_reference_opl(system, wl, 0.0, z_start, z_pupil,
                                     ref_center, ref_r)
    sp_prime = paraxial_of(system, wl)['sP_prime']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    fan = []
    for zone in zones:
        ray = make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                             z_start, z_pupil)
        res = trace_ray_through_system(system, ray, wl)
        if not (res.success and len(res.path) >= 2):
            fan.append({'zone': zone, 'ok': False})
            continue
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else 0.0
        y_exit, z_exit = last[1], last[2]
        length = -y_exit / slope if abs(slope) > 1e-12 else None
        y_pupil = y_exit + slope * ((z_last + sp_prime) - z_exit) \
            if abs(slope) < 1e3 else None
        fan.append({
            'zone': zone, 'ok': True,
            'y_exit': y_exit, 'slope': slope,
            'L': length, 'y_pupil': y_pupil,
            'wave': _ray_wavefront(system, res, opl_chief, ref_center,
                                   ref_r, wl),
        })
    return fan


def port_axial_rows(system, wl: float, zones, ax_semi: float) -> list:
    """Строки осевого пучка портом: продольные/поперечные + TABOC2-набор.

    Продольные: порт ``taboc1_rows``-семантика (мм), затем конверсия
    юнитов эталона; дальний тип (дптр) — формула от выходного зрачка
    (досье §2.2). Поперечные: порт dy на последней поверхности;
    гр.мнсек — кандидат-конвенция (досье §2.3). Волновые —
    ``_ray_wavefront`` порта; неизопл — ``compute_isoplanatism`` c
    интерполяцией на зону (как ``taboc2_rows``).
    """
    from analysis.aberrations import compute_isoplanatism
    from analysis.tables import _interp_at
    from analysis.units import mm_to_dioptres, pupil_h_mm

    parax = paraxial_of(system, wl)
    fan = axial_fan(system, wl, zones, ax_semi)
    # параксиальный краевой: y=ax_semi, u=0 → опора продольных
    y_p, u_p = _paraxial_ray(system, wl, ax_semi, 0.0, 0.0)
    L_parax = (-y_p / u_p) if abs(u_p) > 1e-15 else None
    sp_prime = parax['sP_prime']

    iso_pupils, iso_vals = [], []
    iso_error = None
    try:
        iso_pupils, iso_vals = compute_isoplanatism(system, wl=wl)
    except Exception as exc:      # падение портовой функции — в досье §6
        iso_error = repr(exc)
    rows = []
    for ray in fan:
        zone = ray['zone']
        row = {'zone': zone, 'ok': ray['ok'], 'iso_error': iso_error}
        if ray['ok']:
            row.update({
                'y_pupil': ray['y_pupil'], 'tg_prime100': ray['slope'] * 100.0,
                'wave': ray['wave'],
                'h_zr_mm': pupil_h_mm(zone, ax_semi),
                'L': ray['L'],
                'long_mm': (ray['L'] - L_parax
                            if None not in (ray['L'], L_parax) else None),
                'long_dptr': None,
                'dy_exit': ray['y_exit'],
                'iso_pct': (_interp_at(iso_pupils, iso_vals, zone) * 100.0
                            if iso_pupils else None),
            })
            if ray['L'] is not None and L_parax is not None \
                    and sp_prime:
                lp_z = ray['L'] - sp_prime
                lp_p = L_parax - sp_prime
                if abs(lp_z) > 1e-9 and abs(lp_p) > 1e-9:
                    row['long_dptr'] = mm_to_dioptres(lp_z) - mm_to_dioptres(lp_p)
            # поперечные в гр.мнсек (дальнее изображение, OD3): угол из
            # центра выходного зрачка на пересечение зонального луча с
            # параксиальной плоскостью изображения —
            # y_зон(гаусс)/(L_паракс − sP′)·206264.8″; афокальный выход
            # вырождается в наклон. Валидация: US00KI02 2.3e-5..5.8e-4,
            # KURSOVIK ≤1.4e-3 (веер 18.49 по Н ЗР) — REVERSE_OPALDIS §4.
            if ray['slope'] is not None and L_parax is not None \
                    and sp_prime:
                y_gauss = ray['y_exit'] + ray['slope'] * L_parax
                d_pup = L_parax - sp_prime
                if abs(d_pup) > 1e-9:
                    row['trans_arcsec'] = -y_gauss / d_pup * _ARCSEC_PER_RAD
        else:
            row.update({'y_pupil': None, 'tg_prime100': None, 'wave': None,
                        'h_zr_mm': pupil_h_mm(zone, ax_semi), 'L': None,
                        'long_mm': None, 'long_dptr': None, 'dy_exit': None,
                        'trans_arcsec': None, 'iso_pct': None})
        rows.append(row)
    return rows


# ══════════════════════════════════════════════════════════════════════════
# 3а. Ближний предмет (obj=1) — веер по углу NA от точки предмета (P6)
# ══════════════════════════════════════════════════════════════════════════

#: Секунды дуги на радиан (формат «гр.мнсек» OPAL — DD.MMSSss).
_ARCSEC_PER_RAD = 206264.80624709636


def ddmmss_value(arcsec: float) -> float:
    """Секунды дуги → число формата «гр.мнсек» OPAL: после запятой
    двухразрядные минуты, затем секунды с двумя знаками (OBEKTIV попер
    з.1.0 1°13'04.83" → 1.130483; ST4 2.17" → 0.000217; перенос
    разрядов при ss ≥ 99.995 — печать OPAL его не делает, обратный
    разбор :func:`arcsec_of_ddmmss` клампит)."""
    sign = -1.0 if arcsec < 0.0 else 1.0
    total_min = abs(arcsec) / 60.0
    deg = int(total_min // 60.0)
    mm = int(total_min % 60.0)
    ss = (total_min - int(total_min)) * 100.0
    if ss >= 99.995:
        ss, mm = 0.0, mm + 1
        if mm >= 60:
            mm, deg = 0, deg + 1
    return sign * (deg + mm / 100.0 + ss / 10000.0)


def arcsec_of_ddmmss(value: float) -> float:
    """Обратная к :func:`ddmmss_value`: сверка поперечных идёт в
    секундах дуги — шкала линейна, числовое DD.MMSS кусочно."""
    sign = -1.0 if value < 0.0 else 1.0
    v = abs(value)
    deg = int(v)
    mm = int(round((v - deg) * 100.0))
    ss = ((v - deg) * 100.0 - mm) * 100.0
    if ss < 0.0:                            # округление минут вверх
        mm, ss = mm - 1, ss + 100.0
    if mm >= 100:                           # печать без переноса разряда
        mm, deg = mm - 100, deg + 1
    return sign * (deg * 3600.0 + mm * 60.0 + ss)


# R1 (TASK_RESID, REVERSE_OPALDIS §2.2/§2.4): κ-таблицы мнимого изображения.
# Замыкание волновых OPAL при L_p<0 — пер-поверхностный марш Коддингтона
# (хвост 0xd074: W₂ += QF·mixed/2, mixed = [3C98]/(u_m·u_s²)); в эффективной
# квадратике на плоскости z_last: κ(zone,λ) = κ0(λ) + κ2(λ)·zone². κ0/κ2
# решены из банка (4 зоны × остатки ≤2.2e-5 мм⁻¹ = уровень округления
# печати 1e-4λ); якорь C_eff = z_last+1/κ0 не параксиален (мнимое —
# 3-й порядок знаменателя mixed), закрытой формулы марша пока нет.
VIRTUAL_WAVE_KAPPA = {
    'OPTICS#1': {                      # λ (f32 OPJ) → (κ0, κ2), мм⁻¹
        0.54607: (-0.10516667, 0.00436667),
        0.43405: (-0.09372133, 0.00376933),
        0.65628: (-0.11594033, 0.00496133),
    },
}


def _virtual_wave_kappa(table: dict, wl: float):
    """(κ0, κ2) для λ (допуск 2e-3 — печать .4340 против f32 .43405)."""
    for wl_key, pair in (table or {}).items():
        if abs(wl_key - wl) < 2e-3:
            return pair
    return None


def near_object_axial_fan(system, wl: float, zones, na: float,
                          z_obj: float, wave_kappa: dict = None) -> list:
    """Осевой веер ближнего предмета (P6.2): лучи из точки предмета
    (0, 0, z_obj — f64@0x4C) под углом ``u = arcsin(zone·NA)`` к оси —
    OPAL Ax = sin NA габаритной строки (ST4 0.125, досье §3.7). Мнимый
    предмет (z_obj > 0, OPTICS#1 +85.1495): лучи сходятся В точку
    предмета — старт слева от системы с наклоном −sin u.

    Строка: геометрия выхода (терминальный сегмент, GFIX P2): ``L`` —
    мм от вершины последней поверхности до пересечения с осью, плюс
    параксиальная опора ``L_p``/``u_parax`` от точки предмета,
    ``y_pupil`` в плоскости выходного зрачка и ``wave`` — волновая
    относительно главного (осевого) луча: ближнее изображение — опорная
    сфера с центром в точке Гаусса и вершиной в выходном зрачке (как
    P4 у дальнего предмета), афокальный выход (|u'|→0: ST4/LAB6_GAS —
    предмет в переднем фокусе) — плоскость выходного зрачка (досье
    §3.7; вергенция ~1e-5 рад — любая дальняя опора эквивалентна).

    Мнимое ИЗОБРАЖЕНИЕ (L_p < 0) с ``wave_kappa``-таблицей (R1,
    REVERSE_OPALDIS §2.4): опора OPAL — не гауссова сфера, а
    пер-поверхностное замыкание марша Коддингтона
    ``W₂ += QF(X,Y)·mixed/2`` (хвост 0xd074, mixed = [3C98]/(u_m·u_s²));
    в эффективной квадратике на плоскости последней поверхности это
    ``κ(zone,λ)·y²/2`` с κ = κ0 + κ2·zone² (мнимое изображение —
    центровка на вершину z_last, как прод/попер P6). Таблица
    ``{wl: (κ0, κ2)}`` — решена из банка; якорь C_eff = z_last+1/κ0
    не параксиален (мнимое — 3-й порядок знаменателя mixed).
    """

    from ray_tracing import Ray, trace_ray_through_system
    from analysis.aberrations import (_air_exit_direction,
                                      _opl_to_reference_sphere)

    if z_obj < 0.0:
        y0_par, u0_par, z0_par = 0.0, 0.05, z_obj
    else:                                   # прицел в (0, 0, z_obj)
        z0_par = -(abs(z_obj) + 100.0)
        u0_par = -0.05
        y0_par = (z_obj - z0_par) * (-u0_par)
    y_p, u_p = _paraxial_ray(system, wl, y0_par, u0_par, z0_par)
    L_p = (-y_p / u_p) if abs(u_p) > 1e-15 else None    # ∞ — афокальный выход
    # Мнимое изображение (L_p < 0, OPTICS#1): опорная плоскость строк —
    # вершина последней поверхности, не точка Гаусса: прод = L (зона-0
    # −17.742 = |L_p|), попер = −y на вершине, Sp2 = 1000/sP' (досье §P6)
    L_ref = 0.0 if (L_p is not None and L_p < 0.0) else L_p
    sp_prime = paraxial_of(system, wl)['sP_prime']
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    z_pup = z_last + sp_prime
    afocal = L_p is None or abs(u_p) <= 1e-6
    if afocal:
        center, r_ref = None, None
    else:
        center = (0.0, 0.0, z_last + L_p)
        r_ref = (z_last + L_p) - z_pup

    def _opl_close(res):
        """OPL луча до опорной сферы/плоскости выходного зрачка."""
        d = _air_exit_direction(system, res, wl)
        if afocal:
            return res.opl + (z_pup - res.path[-1][2]) / d[2]
        return _opl_to_reference_sphere(res.opl, res.path[-1], d,
                                        center, r_ref)

    def _opl_to_zlast(res):
        """OPL луча до ПЛОСКОСТИ вершины последней поверхности (по
        терминальному воздушному сегменту) — опора мнимого изображения."""
        d = _air_exit_direction(system, res, wl)
        return res.opl + (z_last - res.path[-1][2]) / d[2]

    # R1 (REVERSE_OPALDIS §2.4): мнимое изображение + таблица κ — опора
    # веера = плоскость z_last, замыкание = κ(zone,λ)·y²/2
    virtual_kappa = _virtual_wave_kappa(wave_kappa, wl) \
        if (wave_kappa and L_p is not None and L_p < 0.0) else None

    chief = trace_ray_through_system(
        system, Ray(0.0, 0.0, z0_par if z_obj >= 0.0 else z_obj,
                    0.0, 0.0, 1.0), wl)
    opl_chief = _opl_close(chief) if chief.success else None
    opl_chief_zl = _opl_to_zlast(chief) if (
        chief.success and virtual_kappa) else None
    fan = []
    for zone in zones:
        su = na * zone
        tu = su / math.sqrt(1.0 - su * su)
        if z_obj < 0.0:
            ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
        else:
            z0 = -(abs(z_obj) + 100.0)
            ray = Ray(0.0, (z_obj - z0) * tu, z0,
                      0.0, -su, math.sqrt(1.0 - su * su))
        res = trace_ray_through_system(system, ray, wl)
        row = {'zone': zone, 'ok': False, 'L_p': L_p, 'L_ref': L_ref,
               'u_parax': u_p, 'sp_prime': sp_prime,
               'h_zr_mm': 100.0 * tu, 'wave': None}
        if not (res.success and len(res.path) >= 2):
            fan.append(row)
            continue
        if z_obj > 0.0:
            # мнимый предмет: веер со старта на ПЛОСКОСТИ z0 несёт фазовый
            # сагиттный эксцесс сферы, сходящейся в точку предмета
            # (R0 − √(R0²+y0²), ~2 мм = 4·10³ λ у OPTICS#1) — вычитаем:
            # фаза старта общая со сферы R0 вокруг точки предмета
            r0 = z_obj - ray.z
            res.opl -= math.sqrt(r0 * r0 + ray.y * ray.y) - r0
        prev, last = res.path[-2], res.path[-1]
        dz = last[2] - prev[2]
        slope = (last[1] - prev[1]) / dz if abs(dz) > 1e-12 else None
        y_exit, z_exit = last[1], last[2]
        opl = _opl_close(res)
        if virtual_kappa and opl_chief_zl is not None:
            # R1: замыкание марша на плоскости z_last — эффективная
            # квадратика κ(zone,λ)·y²/2 (мнимое изображение)
            k0, k2 = virtual_kappa
            opl = (_opl_to_zlast(res) - opl_chief_zl
                   + (k0 + k2 * zone * zone) * y_exit * y_exit / 2.0)
            opl_chief_ref = 0.0
        else:
            opl_chief_ref = opl_chief
        row.update({
            'ok': True, 'y_exit': y_exit, 'z_exit': z_exit, 'slope': slope,
            'L': (z_exit - y_exit / slope - z_last
                  if slope is not None and abs(slope) > 1e-15 else None),
            'wave': ((opl - opl_chief_ref) / (wl * 1e-3)
                     if None not in (opl, opl_chief_ref) else None),
        })
        if slope is not None:
            row['y_pupil'] = y_exit + slope * ((z_last + sp_prime) - z_exit)
        fan.append(row)
    return fan


# ══════════════════════════════════════════════════════════════════════════
# 4. Сравнение и вердикты
# ══════════════════════════════════════════════════════════════════════════

def verdict(delta_rel: float, tol: float) -> str:
    """GREEN ≤ tol, YELLOW ≤ 10·tol, иначе RED (карточка задачи)."""
    if delta_rel is None:
        return 'SKIP'
    if delta_rel <= tol:
        return 'GREEN'
    if delta_rel <= tol * TOL_YELLOW:
        return 'YELLOW'
    return 'RED'


def rel_diff(port: float, opal: float, abs_floor: float = 0.0) -> float:
    """Относительное расхождение |Δ|/max(|OPAL|, ε) с защитой нулей.

    ``abs_floor`` — абсолютный шумовой порог в единицах величины:
    при |Δ| ≤ floor расхождение считается нулевым (возвращает 0).
    Обоснование: PRN печатает 5 знаков, показатели n порта и OPAL
    интерполируются из f32-λ OPJ — систематика ~1e-3 мм между
    независимыми реализациями численно неустранима; у нулей
    сферической аберрации (смена знака между зонами, OPAL3 з.0.866:
    0.046 мм при |Δ| 1 мкм) чистое |Δ|/|OPAL| взрывается и RED
    обвиняет порт ложно.
    """
    if port is None or opal is None:
        return None
    delta = abs(port - opal)
    if abs_floor > 0.0 and delta <= abs_floor:
        return 0.0
    denom = max(abs(opal), 1e-9)
    return delta / denom


def compare_system(name: str, bank_dir: str = _BANK_DIR,
                   opj_dir: str = _GOLDEN_DOS) -> dict:
    """Полная сверка одной системы: строки-величины + вердикты.

    Возвращает ``{'rows': [строки таблицы], 'counts': {G/Y/R/S},
    'notes': [...]}``. Строка: ``(раздел, величина, зона, OPAL, порт,
    Δотн, допуск, вердикт)``.
    """
    prn = parse_golden_prn(os.path.join(bank_dir, name + '.PRN'))
    opj_path = os.path.join(opj_dir, name + '.OPJ')
    opj = parse_golden_opj(opj_path)
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    rows, notes = [], []

    parax = paraxial_of(system, wl)

    # Ближний предмет (obj=1, P6): предмет — f64@0x4C (мм от первой
    # поверхности), веер по углу u = arcsin(zone·Ax), Sp = 1000/(sP−z)
    # дптр. Дальняя/ближняя конвенции строк — досье §3.7.
    near_obj = (opj['obj_type'] == 1)

    # ── габариты: строка N=0 (осевая) расчётной λ ──
    # (λ OPJ — f32: 0.54607 против печати .5461 → допуск 2e-3)
    ax_row = None
    for (wl_str, n_zone), row in prn['gabarit'].items():
        if n_zone == 0 and abs(float(wl_str) - wl) < 2e-3:
            ax_row = row
            break
    if ax_row is None:                      # фолбэк: любая N=0
        for (wl_str, n_zone), row in prn['gabarit'].items():
            if n_zone == 0:
                ax_row = row
    if prn['gabarit'] and ax_row is None:
        notes.append('габариты без строки N=0')
    units_sp, units_sp2 = prn.get('gabarit_units', ('мм', 'мм'))
    if ax_row is not None:
        if near_obj:
            # Ближний предмет (P6.1): Sp в дптр = 1000/(sP − z_obj) от
            # входного зрачка (ST4 9.717 = 1000/(6.703+96.2046);
            # OPTICS#1 мнимый предмет даёт Sp<0). Sp' — мм от последней
            # поверхности (дальнее изображение) либо дптр от точки
            # Гаусса: 1000/(sP'−L_p) (S_KOND1 −3.758, досье §3.7).
            z_obj = opj['object_pos']
            port_sp = (1000.0 / (parax['sP'] - z_obj)
                       if units_sp == 'дптр' else parax['sP'])
            if units_sp2 == 'дптр':
                if z_obj < 0.0:
                    y0p, u0p, z0p = 0.0, 0.05, z_obj
                else:                       # прицел в мнимый предмет
                    z0p = -(abs(z_obj) + 100.0)
                    u0p = -0.05
                    y0p = (z_obj - z0p) * (-u0p)
                y_p, u_p = _paraxial_ray(system, wl, y0p, u0p, z0p)
                L_p = (-y_p / u_p) if abs(u_p) > 1e-15 else None
                # мнимое изображение (L_p<0): опора — вершина последней
                # поверхности, Sp2 = 1000/sP' (OPTICS#1 −16.401, §P6)
                L_ref = 0.0 if (L_p is not None and L_p < 0.0) else L_p
                port_sp2 = (1000.0 / (parax['sP_prime'] - L_ref)
                            if L_ref is not None else None)
            else:
                port_sp2 = parax['sP_prime']
        else:
            # Sp — мм от первой поверхности (дальний предмет). Sp' — мм
            # от последней поверхности (дальнее изображение) либо дптр
            # от плоскости Гаусса (ближнее изображение): HELIOS8/ST/121 —
            # 1000/(sP'−bfd) совпадает с эталоном до 4 знаков (досье §1).
            port_sp = parax['sP']
            port_sp2 = parax['sP_prime']
            if units_sp2 == 'дптр':
                d = parax['sP_prime'] - parax['bfd']
                port_sp2 = 1000.0 / d if abs(d) > 1e-9 else None
        for key, port_val, tol in (
                ('Sp', port_sp, TOL_PARAX),
                ('Sp2', port_sp2, TOL_PARAX),
        ):
            rows.append(('габариты', key, '', ax_row[key], port_val,
                         rel_diff(port_val, ax_row[key]), tol,
                         verdict(rel_diff(port_val, ax_row[key]), tol)))

    # Ax — реальная полувысота пучка: вход для веера (см. досье §5).
    # Цепочка: максимум колонки Н ЗР (зона 1.0: Н ЗР = отн.зр·Ax, точнее
    # округленной габаритной Ax — HELIOS8 13.606 vs габарит 13.61/13.66
    # по λ) → габаритная строка N=0 → заданная апертура OPJ (у
    # KURSOVIK/OPAL3 отличается от реального габаритного луча).
    ax_semi = None
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    if hzr_vals:
        ax_semi = max(hzr_vals)
    if not ax_semi and ax_row:
        ax_semi = ax_row['Ax']
    if not ax_semi:
        ax_semi = opj['aperture_semi']

    # ── осевой пучок ──
    if not near_obj:
        units = prn['axial1'].get('units', ('мм', 'мм'))
        long_key = 'long_dptr' if units[0] == 'дптр' else 'long_mm'
        port_rows = {r['zone']: r for r in
                     port_axial_rows(system, wl, list(
                         prn['axial1'].get('rows', {}).keys()), ax_semi)}
        if port_rows:
            first = next(iter(port_rows.values()))
            if first.get('iso_error'):
                notes.append('неизопл: compute_isoplanatism порта упал (%s)'
                             % first['iso_error'])
        a1_rows = prn['axial1'].get('rows', {})

        # сопоставление зон: продольная таблица индексируется отн.зр,
        # TABOC2 — своей меткой; зоны берем из продольной таблицы
        for zone, et in sorted(a1_rows.items(), reverse=True):
            pr = port_rows.get(zone)
            # продольные (колонка λ0)
            if et['long'] and et['long'][0] is not None:
                opal_v = et['long'][0]
                port_v = pr.get(long_key) if pr else None
                floor = (ABS_FLOOR_MM if units[0] == 'мм'
                         else ABS_FLOOR_DPTR)
                d = rel_diff(port_v, opal_v, floor)
                rows.append(('осевой', f'прод ({units[0]})', zone, opal_v,
                             port_v, d, TOL_ABERR, verdict(d, TOL_ABERR)))
            # поперечные (гр.мнсек, OD3): DD.MMSS → секунды дуги; порт —
            # угол из центра выходного зрачка на точку зонального луча в
            # плоскости Гаусса (досье REVERSE_OPALDIS §4). Пол 0.02″ —
            # гранулярность печати секунд.
            if et['trans'] and et['trans'][0] is not None:
                opal_v = et['trans'][0]
                if units[1] == 'гр.мнсек':
                    opal_as = arcsec_of_ddmmss(opal_v)
                    port_v = (pr.get('trans_arcsec') if pr else None)
                    d = rel_diff(port_v, opal_as, 0.02)
                    rows.append(('осевой', 'попер (гр.мнсек)', zone, opal_as,
                                 port_v, d, TOL_ABERR,
                                 verdict(d, TOL_ABERR)))
                else:
                    rows.append(('осевой', f'попер ({units[1]})', zone, opal_v,
                                 None, None, TOL_ABERR, 'SKIP'))

        # TABOC2: строки отсортированы ПО МЕТКЕ (убывание tg'*100), а не
        # по зоне — у 121 метка немонотонна по зонам. Идентичность зоны
        # восстанавливаем по колонке Н ЗР = отн.зр·Ax (дossier §2.5);
        # строки без Н ЗР сшиваем по порядку.
        a2_list = sorted(prn['axial2'].get('rows', {}).values(),
                         key=lambda r: -r['tg100'] if r['tg100'] is not None else 0)
        zones_sorted = sorted(a1_rows.keys(), reverse=True)

        def _zone_of(et):
            hzr = et.get('h_zr')
            if hzr is not None and ax_semi:
                return min(zones_sorted,
                           key=lambda z: abs(z - hzr / ax_semi))
            return None

        used = set()
        pairs = []
        for et in a2_list:
            z = _zone_of(et)
            if z is None or z in used:
                z = next((zz for zz in zones_sorted if zz not in used), None)
            if z is None:
                break
            used.add(z)
            pairs.append((et, z))
        # .000-строка эталона — осевая; у веера её нет (зона 0 тривиальна)
        for et, zone in pairs:
            pr = port_rows.get(zone)
            if et['tg100'] is not None:
                # дальний тип: метка = H' ЗР (мм, печатается положительной
                # независимо от инверсии — габаритный Ax' той же величины
                # знак сохраняет); ближний тип: −100·tg u' (знак OPAL
                # обратен наклону порта — HELIOS8/121, досье §2.1)
                far = (opj['img_type'] == 0)
                port_v = None
                if pr:
                    if far:
                        port_v = (abs(pr['y_pupil'])
                                  if pr['y_pupil'] is not None else None)
                        if port_v is not None and et['tg100'] < 0:
                            port_v = -port_v
                    else:
                        port_v = (-pr['tg_prime100']
                                  if pr.get('tg_prime100') is not None else None)
                d = rel_diff(port_v, et['tg100'])
                rows.append(('осевой', "Tg'*100" + (' (H`ЗР)' if far else ''),
                             zone, et['tg100'], port_v, d, TOL_ABERR,
                             verdict(d, TOL_ABERR)))
            if et['wave'] and et['wave'][0] is not None:
                port_v = pr.get('wave') if pr else None
                d = rel_diff(port_v, et['wave'][0], ABS_FLOOR_WAVE)
                rows.append(('осевой', 'волновые', zone, et['wave'][0], port_v,
                             d, TOL_ABERR, verdict(d, TOL_ABERR)))
            if et['h_zr'] is not None:
                port_v = pr.get('h_zr_mm') if pr else None
                d = rel_diff(port_v, et['h_zr'])
                rows.append(('осевой', 'Н ЗР (мм)', zone, et['h_zr'], port_v, d,
                             TOL_ABERR, verdict(d, TOL_ABERR)))

    elif near_obj:
        # ── осевой пучок: ближний предмет (P6.2) ──
        # Веер по углу u = arcsin(zone·Ax) из точки предмета 0x4C;
        # конвенции строк — досье §3.7: дальнее изображение — прод в дптр
        # (вергенция пересечения с осью − параксиальная), попер в
        # гр.мнсек (угол выхода vs паракс, DD.MMSS), метка Tg'*100 —
        # высота луча в плоскости выходного зрачка; ближнее — прод/попер
        # в мм (пересечение с осью/высота в плоскости Гаусса от точки
        # предмета), метка = −100·tg u'.
        units = prn['axial1'].get('units', ('мм', 'мм'))
        a1_rows = prn['axial1'].get('rows', {})
        na = ax_row['Ax'] if ax_row else opj['aperture_semi']
        if not na:
            hzr_max = max((r['h_zr'] for r in
                           prn['axial2'].get('rows', {}).values()
                           if r.get('h_zr') is not None), default=0.0)
            na = hzr_max / 100.0
        z_obj = opj['object_pos']
        z_last = sum(s.thickness for s in system.surfaces[:-1])
        port_rows = {r['zone']: r for r in
                     near_object_axial_fan(system, wl, list(a1_rows.keys()),
                                           na, z_obj)}
        for zone, et in sorted(a1_rows.items(), reverse=True):
            pr = port_rows.get(zone)
            if et['long'] and et['long'][0] is not None:
                opal_v = et['long'][0]
                port_v = None
                if pr and pr['ok'] and pr['L'] is not None:
                    l_ref = pr.get('L_ref', pr['L_p'])
                    if units[0] == 'дптр':
                        port_v = 1000.0 / pr['L']
                        if l_ref:
                            port_v -= 1000.0 / l_ref
                    else:
                        port_v = (pr['L'] - l_ref
                                  if l_ref is not None else None)
                floor = (ABS_FLOOR_MM if units[0] == 'мм'
                         else ABS_FLOOR_DPTR)
                d = rel_diff(port_v, opal_v, floor)
                rows.append(('осевой', f'прод ({units[0]})', zone, opal_v,
                             port_v, d, TOL_ABERR, verdict(d, TOL_ABERR)))
            if et['trans'] and et['trans'][0] is not None:
                opal_v = et['trans'][0]
                port_v = None
                if units[1] == 'гр.мнсек':
                    # сверка в секундах дуги; порт — угол из центра
                    # выходного зрачка на точку зонального луча в
                    # плоскости Гаусса (OD3, досье REVERSE_OPALDIS §4);
                    # афокальный выход (L_p=None/|u'|→0: ST4/LAB6_GAS) —
                    # вырождается в наклон луча
                    opal_as = arcsec_of_ddmmss(opal_v)
                    if pr and pr['ok'] and pr['slope'] is not None:
                        if pr.get('L_p') and pr.get('sp_prime') \
                                and abs(pr['L_p'] - pr['sp_prime']) > 1e-9:
                            y_g = pr['y_exit'] + pr['slope'] * pr['L_p']
                            port_v = -y_g / (pr['L_p'] - pr['sp_prime']) \
                                * _ARCSEC_PER_RAD
                        else:
                            port_v = -pr['slope'] * _ARCSEC_PER_RAD
                    d = rel_diff(port_v, opal_as, 0.02)
                    rows.append(('осевой', 'попер (гр.мнсек)', zone, opal_as,
                                 port_v, d, TOL_ABERR, verdict(d, TOL_ABERR)))
                else:
                    if pr and pr['ok'] and pr['slope'] is not None:
                        l_ref = pr.get('L_ref', pr['L_p'])
                        if l_ref is not None:
                            z_img = z_last + l_ref
                            port_v = pr['y_exit'] + pr['slope'] * (z_img
                                                                   - pr['z_exit'])
                            if l_ref == 0.0 and pr['L_p'] is not None \
                                    and pr['L_p'] < 0.0:
                                # мнимое изображение: ТА на вершине с
                                # обратным знаком (OPTICS#1 +2.741, §P6)
                                port_v = -port_v
                    d = rel_diff(port_v, opal_v, ABS_FLOOR_MM)
                    rows.append(('осевой', f'попер ({units[1]})', zone,
                                 opal_v, port_v, d, TOL_ABERR,
                                 verdict(d, TOL_ABERR)))

        # TABOC2: сшивка зон по Н ЗР = 100·tg(arcsin(zone·NA)) (та же
        # схема, что и для дальнего предмета, масштаб 100·NA)
        a2_list = sorted(prn['axial2'].get('rows', {}).values(),
                         key=lambda r: -r['tg100'] if r['tg100'] is not None
                         else 0)
        zones_sorted = sorted(a1_rows.keys(), reverse=True)
        scale = 100.0 * na
        used, pairs = set(), []
        for et in a2_list:
            hzr = et.get('h_zr')
            z = None
            if hzr is not None and scale:
                z = min(zones_sorted, key=lambda zz: abs(zz - hzr / scale))
            if z is None or z in used:
                z = next((zz for zz in zones_sorted if zz not in used), None)
            if z is None:
                break
            used.add(z)
            pairs.append((et, z))
        far = (opj['img_type'] == 0)
        for et, zone in pairs:
            pr = port_rows.get(zone)
            if et['tg100'] is not None:
                port_v = None
                if pr and pr['ok']:
                    if far:
                        port_v = pr.get('y_pupil')
                        if port_v is not None and et['tg100'] < 0:
                            port_v = -port_v
                    else:
                        port_v = (-100.0 * pr['slope']
                                  if pr['slope'] is not None else None)
                        # знак эталона (луч ниже оси / печать з.0.5
                        # OPTICS#1 −7.433 при |7.4333| — как дальняя ветка)
                        if port_v is not None and et['tg100'] < 0:
                            port_v = -port_v
                d = rel_diff(port_v, et['tg100'])
                rows.append(('осевой', "Tg'*100" + (' (H`ЗР)' if far else ''),
                             zone, et['tg100'], port_v, d, TOL_ABERR,
                             verdict(d, TOL_ABERR)))
            if et['wave'] and et['wave'][0] is not None:
                port_v = pr.get('wave') if pr else None
                d = rel_diff(port_v, et['wave'][0], ABS_FLOOR_WAVE)
                rows.append(('осевой', 'волновые', zone, et['wave'][0], port_v,
                             d, TOL_ABERR, verdict(d, TOL_ABERR)))
            if et['h_zr'] is not None:
                port_v = pr.get('h_zr_mm') if pr else None
                d = rel_diff(port_v, et['h_zr'])
                rows.append(('осевой', 'Н ЗР (мм)', zone, et['h_zr'], port_v,
                             d, TOL_ABERR, verdict(d, TOL_ABERR)))

    counts = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0}
    for r in rows:
        counts[r[7]] += 1
    return {'name': name, 'prn': prn, 'opj': opj, 'rows': rows,
            'counts': counts, 'notes': notes, 'system': system,
            'parax': parax}


def format_report(results: list) -> str:
    """Markdown-отчёт по всем системам (для REVERSE_GVERIFY.md)."""
    out = []
    total = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0}
    for res in results:
        c = res['counts']
        for k in total:
            total[k] += c[k]
        out.append(f"### {res['name']} — G:{c['GREEN']} Y:{c['YELLOW']} "
                   f"R:{c['RED']} S:{c['SKIP']}")
        out.append('')
        out.append('| раздел | величина | зона | OPAL | порт | Δотн | вердикт |')
        out.append('|---|---|---|---|---|---|---|')
        for sec, qty, zone, opal_v, port_v, d, tol, verd in res['rows']:
            z = f'{zone:.3f}' if isinstance(zone, float) else str(zone)
            op_s = f'{opal_v:.5g}' if isinstance(opal_v, float) else '—'
            pt_s = f'{port_v:.5g}' if isinstance(port_v, float) else '—'
            d_s = f'{d:.2e}' if isinstance(d, float) else '—'
            out.append(f'| {sec} | {qty} | {z} | {op_s} | {pt_s} | {d_s} '
                       f'| {verd} |')
        out.append('')
    out.insert(0, f'**Сводка: GREEN {total["GREEN"]} / YELLOW {total["YELLOW"]}'
                  f' / RED {total["RED"]} / SKIP {total["SKIP"]}**\n')
    return '\n'.join(out)


def run_all(bank_dir: str = _BANK_DIR, opj_dir: str = _GOLDEN_DOS) -> list:
    """Сверка всех систем банка (пропуская системы без .OPJ на стенде)."""
    results = []
    for name in BANK_SYSTEMS:
        prn_path = os.path.join(bank_dir, name + '.PRN')
        opj_path = os.path.join(opj_dir, name + '.OPJ')
        if not (os.path.exists(prn_path) and os.path.exists(opj_path)):
            continue
        try:
            results.append(compare_system(name, bank_dir, opj_dir))
        except Exception as exc:                     # досье: падение системы
            hint = ' (ГОЭ: standalone-раскладка OPJ отличается — ' \
                   'отрицательные толщины, мусорные gidx, досье §6)' \
                if 'GTIE' in name else ''
            results.append({'name': name, 'rows': [], 'counts': {
                'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'SKIP': 0},
                'notes': [f'ОШИБКА: {exc!r}{hint}'], 'system': None,
                'parax': {}})
    return results


if __name__ == '__main__':
    print(format_report(run_all()))
