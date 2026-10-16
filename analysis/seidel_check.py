# -*- coding: utf-8 -*-
"""
OPAL-OKB — сверка сумм Зейделя порта с OPAL (TASK_SEIDEL, A5).

Порт считает суммы Зейделя в ``domain.calculations.seidel_aberrations``
(SI–SV на параксиальных базисах y₀=1, nu₀=0 / главного луча от стопа).
Здесь — независимая реализация тех же формул (контроль паритета),
хроматические суммы SIхр/SIIхр (ANALIZE.DOC:434–448 — между крайними
рабочими λ; в порте их нет) и две сверки:

1. **Против трассировки** (:func:`compare_with_tracing`) — численное
   выделение аберраций 3-го порядка из точного трейсера ``ray_native``
   (веера на параксиальном фокусе, МНК): знаки и порядок величин
   коэффициентов против знаков сумм. Соответствие (проверено на 6
   демо-системах):

   ============  ==================================================
   сумма          коэффициент трассировки
   ============  ==================================================
   SI             c₃ — кубический член осевого веера ε(ρ)
   SII            a₂ — квадратичный член полевого веера
   SIII           (a₁ − b₁) — астигматизм (танг./саг. наклоны)
   SV             a₀ — постоянный член (дисторсия)
   SIхр           +δf′ = f′(λmax) − f′(λmin) — хроматический сдвиг
                  фокуса (2 λ)
   ============  ==================================================

   Абсолютные константы связки (классические −SI/(2n′u′) и т.п.) имеют
   несовместимую с базисом порта нормировку вспомогательных лучей —
   сверяются знаки и порядок величин (``orders``), не константы.

2. **Против golden .PRN** (:func:`seidel_vs_golden`) — парсинг секции
   сумм Зейделя OPAL (подпрограмма sumsed, формат
   ``(' ',I3,5(F11.5),2F10.5)`` — S1..S5 + S1хр/S2хр, REVERSE_TRACE
   §14.4): знаки всех сумм + отношения Sₖ/S1 (инвариант нормировки
   вспомогательных лучей OPAL — EDIT нормирует их иначе, чем порт;
   допуск ~5 % — float32 OPAL). Секция sumsed ни в одном эталоне
   репозитория (RT__2236/2250, PROTOCOL, LEXA22) не встречается —
   сверка возвращает ``skipped`` с пояснением.

Хроматические суммы — Δ(1/n) от дисперсии δn = n(λmax) − n(λmin)
между крайними рабочими λ системы (одна λ — нули); для зеркал
δn₂ = −δn₁ (отражение меняет знак показателя).

Параксиальные вспомогательные лучи (базис порта, §14.4):

* маргинальный: y[0]=1, nu[0]=0 (на первой поверхности);
* главный: yb[stop]=0, nub[stop]=1 (стоп — 0-based, зажат в списке),
  вперёд и назад от стопа;
* инвариант A = nu + n·y/R (угол падения × n), Ā — главного луча.
"""
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ray_native
from domain.calculations import paraxial_trace, refractive_index
from domain.models import ObjectType
from optics_utils import get_effective_aperture, get_primary_wl

from analysis.aberrations import _compute_ray_start, _pupil_field_ray

#: Узлов осевого веера для МНК ε(ρ)/ρ = c₁ + c₃ρ² + c₅ρ⁴.
AXIAL_FAN_RHOS = (0.1, 0.2, 0.3, 0.4, 0.5)

#: Узлов полевого веера ε(ρ) = a₀ + a₁ρ + a₂ρ² + a₃ρ³.
FIELD_FAN_RHOS = (-0.4, -0.25, -0.12, 0.12, 0.25, 0.4)

#: Узлов сагиттального веера для наклона b₁ = εx(ρ)/ρ.
SAGITTAL_RHOS = (0.2, 0.35)


def _paraxial_auxiliary(system, wl: float):
    """Параксиальные базисы порта: ``(n, y, nu, yb, nub)``.

    Маргинальный луч y[0]=1, nu[0]=0; главный — от стопа
    (yb[stop]=0, nub[stop]=1, стоп 0-based, зажат в список), вперёд и
    назад. Отражение — смена знака показателя (n → −n). Копия схемы
    трейсера порта (``domain.calculations``, §14.4) — независимая
    реализация для контроля паритета сумм.
    """
    ns = len(system.surfaces)
    n = [1.0]
    for s in system.surfaces:
        n.append(-n[-1] if s.is_reflective
                 else refractive_index(s.glass, wl, None,
                                       getattr(s, 'n_override', None)))
    y = [0.0] * (ns + 1)
    nu = [0.0] * (ns + 1)
    y[0], nu[0] = 1.0, 0.0
    for i, s in enumerate(system.surfaces):
        R = s.radius if s.radius != 0 else math.inf
        nu[i + 1] = nu[i] - (y[i] * (n[i + 1] - n[i]) / R
                             if R != math.inf else 0.0)
        y[i + 1] = y[i] + nu[i + 1] * s.thickness / n[i + 1]
    yb = [0.0] * (ns + 1)
    nub = [0.0] * (ns + 1)
    k = max(0, min(system.stop_surface - 1, ns - 1))
    yb[k], nub[k] = 0.0, 1.0
    for i in range(k - 1, -1, -1):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else math.inf
        yb[i] = yb[i + 1] - nub[i + 1] * s.thickness / n[i + 1]
        nub[i] = nub[i + 1] + (yb[i] * (n[i + 1] - n[i]) / R
                               if R != math.inf else 0.0)
    for i in range(k, ns):
        s = system.surfaces[i]
        R = s.radius if s.radius != 0 else math.inf
        nub[i + 1] = nub[i] - (yb[i] * (n[i + 1] - n[i]) / R
                               if R != math.inf else 0.0)
        yb[i + 1] = yb[i] + nub[i + 1] * s.thickness / n[i + 1]
    return n, y, nu, yb, nub


def chief_field_scale(system, field_y: float,
                      nub0: Optional[float] = None) -> float:
    """Масштаб главного луча s для поля ``field_y`` (базис nub=1).

    INFINITE — поле в градусах: s = tan(ω)/nub[0]; FINITE — высота
    предмета (мм): s = (−field_y/d)/nub[0], d — расстояние до первой
    поверхности (знак OPAL: предмет отрицательный).
    """
    if nub0 is None:
        wl = get_primary_wl(system)
        nub0 = _paraxial_auxiliary(system, wl)[4][0]
    if system.object_type == ObjectType.INFINITE:
        return math.tan(math.radians(field_y)) / nub0
    d = abs(system.surfaces[0].thickness) if system.surfaces else 50.0
    return (-field_y / d) / nub0


# ── Суммы Зейделя (независимая реализация формул порта) ─────────────────────

def seidel_sums(system, wl: Optional[float] = None) -> Dict:
    """Суммы Зейделя SI–SV + хроматические SIхр/SIIхр «как порт».

    Формулы порта (``domain.calculations.seidel_aberrations``, §14.4)
    на базисе маргинального y₀=1 и главного nub=1 (масштаб апертуры и
    поля — единица):

    * SI  = Σ A²hΔ(1/n) — сферическая;
    * SII = Σ ĀAhΔ(1/n) — кома;
    * SIII= Σ Ā²hΔ(1/n) — астигматизм;
    * SIV = Σ (n₂−n₁)/(R·n₁·n₂) — Петцваль;
    * SV  = Σ (Ā³/A)hΔ(1/n) + 3ΣĀ²hΔ(1/n) — дисторсия;

    A = nu + n·y/R (инвариант угла падения), h = y, Δ(1/n) — скачок
    на поверхности (плоские поверхности вклада не дают). Хроматические
    (в порте отсутствуют): SIхр = ΣAh·δ(−1/n), SIIхр = ΣĀh·δ(−1/n),
    δn = n(λmax) − n(λmin) между крайними рабочими λ системы (одна λ —
    нули, флаг ``chromatic``); зеркала: δn₂ = −δn₁.

    Args:
        system: Оптическая система.
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        ``{'SI'..'SV', 'SIxp', 'SIIxp', 'wl', 'wl_lo', 'wl_hi',
        'chromatic': bool}`` — суммы на базисе порта (ср. тест паритета
        с ``domain.calculations.seidel_aberrations``).
    """
    if wl is None:
        wl = get_primary_wl(system)
    wls = sorted(float(w.value) for w in system.wavelengths)
    wl_lo, wl_hi = (wls[0], wls[-1]) if len(wls) >= 2 else (wl, wl)
    chromatic = len(wls) >= 2 and abs(wl_hi - wl_lo) > 1e-12

    def dn(glass: str, n_ov) -> float:
        if glass == '' and not n_ov:
            return 0.0
        return (refractive_index(glass, wl_hi, None, n_ov)
                - refractive_index(glass, wl_lo, None, n_ov))

    n, y, nu, yb, nub = _paraxial_auxiliary(system, wl)
    S = dict(SI=0.0, SII=0.0, SIII=0.0, SIV=0.0, SV=0.0,
             SIxp=0.0, SIIxp=0.0)
    for i, surf in enumerate(system.surfaces):
        R = surf.radius
        if R == 0:
            continue                          # плоская: вклада нет
        dinv = 1.0 / n[i + 1] - 1.0 / n[i]
        h = y[i]
        A = nu[i] + n[i] * y[i] / R
        Ab = nub[i] + n[i] * yb[i] / R
        S['SI'] += A * A * h * dinv
        S['SII'] += Ab * A * h * dinv
        S['SIII'] += Ab * Ab * h * dinv
        S['SIV'] += (n[i + 1] - n[i]) / (R * n[i] * n[i + 1])
        a_safe = A if abs(A) > 1e-12 else 1e-12
        S['SV'] += (Ab ** 3 / a_safe) * h * dinv + 3.0 * Ab * Ab * h * dinv
        if chromatic:
            if surf.is_reflective:
                dn1 = dn(system.surfaces[i - 1].glass if i else '',
                         getattr(system.surfaces[i - 1], 'n_override', None)
                         if i else None)
                dn2 = -dn1
            else:
                n_ov1 = (getattr(system.surfaces[i - 1], 'n_override', None)
                         if i else None)
                dn1 = dn(system.surfaces[i - 1].glass if i else '', n_ov1)
                dn2 = dn(surf.glass, getattr(surf, 'n_override', None))
            dchrom = -(dn2 / n[i + 1] ** 2 - dn1 / n[i] ** 2)   # δ(−1/n)
            S['SIxp'] += A * h * dchrom
            S['SIIxp'] += Ab * h * dchrom
    S.update(wl=wl, wl_lo=wl_lo, wl_hi=wl_hi, chromatic=chromatic)
    return S


# ── Численная сверка против трассировки ─────────────────────────────────────

def _paraxial_focus_z(system, n, y, nu) -> float:
    """Z параксиального фокуса (пересечение маргинального луча с осью)."""
    ns = len(system.surfaces)
    z_pos = [0.0]
    for s in system.surfaces:
        z_pos.append(z_pos[-1] + s.thickness)
    slope = nu[ns] / n[ns]
    if abs(slope) < 1e-15:
        return z_pos[ns]
    return z_pos[ns] - y[ns] / slope


def _trace_at_focus(system, wl: float, field_y: float, rho: float,
                    sagittal: bool = False):
    """Поперечная аберрация луча (ρ) на параксиальном фокусе, мм.

    Луч — через зрачковую координату (ρ по y, сагиттальный — по x);
    на поле из высоты вычитается параксиальный главный луч (масштаб
    :func:`chief_field_scale`). ``None`` — луч не дошёл.
    """
    aperture = get_effective_aperture(system, default=10.0)
    parax = paraxial_trace(system)
    z_start, z_pupil = _compute_ray_start(system, parax)
    px, py = (rho, 0.0) if sagittal else (0.0, rho)
    ray = _pupil_field_ray(system, px * aperture / 2, py * aperture / 2,
                           field_y, z_start, z_pupil)
    res = ray_native.trace_batch(
        system, [(ray.x, ray.y, ray.z, ray.k, ray.l, ray.m)], wl)[0]
    if not res.success or len(res.path) < 2:
        return None
    n, y, nu, yb, nub = _paraxial_auxiliary(system, wl)
    ns = len(system.surfaces)
    z_img = sum(s.thickness for s in system.surfaces)
    z_focus = _paraxial_focus_z(system, n, y, nu)
    (x0, y0, z0), (x1, y1, z1) = res.path[-2], res.path[-1]
    dz = z1 - z0
    t = (z_focus - z0) / dz if abs(dz) > 1e-12 else 0.0
    x, yv = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    if field_y == 0.0:
        return x if sagittal else yv
    s = chief_field_scale(system, field_y, nub[0])
    y_par_chief = s * (yb[ns] + nub[ns] * (z_focus - z_img) / n[ns])
    return x if sagittal else yv - y_par_chief


def _lstsq(rows, rhs):
    import numpy as np
    coeffs, *_ = np.linalg.lstsq(np.array(rows, dtype=float),
                                 np.array(rhs, dtype=float), rcond=None)
    return [float(c) for c in coeffs]


def compare_with_tracing(system, field_y: float,
                         wl: Optional[float] = None) -> Dict:
    """Численная сверка сумм Зейделя с трассировкой 3-го порядка.

    Из точного трейсера выделяются коэффициенты аберраций 3-го
    порядка (МНК по веерам на параксиальном фокусе, мм):

    * осевой веер ε(ρ)/ρ = c₁ + c₃ρ² + c₅ρ⁴ (c₁ ≈ 0 — контроль фокуса);
    * полевой меридиональный ε(ρ) = a₀ + a₁ρ + a₂ρ² + a₃ρ³;
    * сагиттальный наклон b₁ = εx(ρ)/ρ;
    * хроматический сдвиг фокуса δf′ = f′(λmax) − f′(λmin).

    Знаки коэффициентов сверяются со знаками сумм (таблица в докстринге
    модуля), отношения — порядок величин (``orders``; константы связки
    зависят от нормировки вспомогательных лучей — не сверяются).

    Args:
        system: Оптическая система.
        field_y: Поле (град / мм) полевого веера.
        wl: Длина волны (мкм); None → основная λ системы.

    Returns:
        ``{'sums', 'axial': {c1_mm, c3_mm, c5_mm}, 'field': {a0_mm,
        a1_mm, a2_mm, a3_mm, b1_mm}, 'chromatic': {delta_f_mm,
        wl_lo, wl_hi}, 'signs': {SI_c3, SII_a2, SIII_astig, SV_a0,
        SIxp_df}, 'orders': {..}}``; ``None`` — веер не дотянулся
        (например, сильное виньетирование поля).
    """
    if wl is None:
        wl = get_primary_wl(system)
    S = seidel_sums(system, wl=wl)
    sums = {k: S[k] for k in ('SI', 'SII', 'SIII', 'SIV', 'SV',
                              'SIxp', 'SIIxp')}

    axial_pairs = [(rho, _trace_at_focus(system, wl, 0.0, rho))
                   for rho in AXIAL_FAN_RHOS]
    axial_pairs = [(rho, e) for rho, e in axial_pairs if e is not None]
    if len(axial_pairs) < 3:
        return {'system': getattr(system, 'name', ''), 'field_y': field_y,
                'wl': wl, 'sums': sums, 'error': 'осевой веер не дошёл'}
    c1, c3, c5 = _lstsq([[1.0, rho * rho, rho ** 4]
                         for rho, _ in axial_pairs],
                        [e / rho for rho, e in axial_pairs])

    fan = [(rho, _trace_at_focus(system, wl, field_y, rho))
           for rho in FIELD_FAN_RHOS]
    if any(e is None for _, e in fan):
        return {'system': getattr(system, 'name', ''), 'field_y': field_y,
                'wl': wl, 'sums': sums, 'error': 'полевой веер не дошёл'}
    a0, a1, a2, a3 = _lstsq([[1.0, rho, rho * rho, rho ** 3]
                             for rho, _ in fan],
                            [e for _, e in fan])
    sag = [(rho, _trace_at_focus(system, wl, field_y, rho, sagittal=True))
           for rho in SAGITTAL_RHOS]
    if any(e is None for _, e in sag):
        return {'system': getattr(system, 'name', ''), 'field_y': field_y,
                'wl': wl, 'sums': sums, 'error': 'сагиттальный веер не дошёл'}
    b1 = sum(e / rho for rho, e in sag) / len(sag)

    delta_f = None
    if S['chromatic']:
        f1 = paraxial_trace(system, wl=S['wl_lo'])['back_focal_distance']
        f2 = paraxial_trace(system, wl=S['wl_hi'])['back_focal_distance']
        delta_f = f2 - f1

    def sign(v):
        return (v > 0) - (v < 0)

    pairs = {'SI_c3': (S['SI'], c3), 'SII_a2': (S['SII'], a2),
             'SIII_astig': (S['SIII'], a1 - b1), 'SV_a0': (S['SV'], a0),
             'SIxp_df': (S['SIxp'],
                         delta_f if delta_f is not None else 0.0)}
    signs = {key: sign(sv) == sign(tv) and sign(sv) != 0
             for key, (sv, tv) in pairs.items()}
    orders = {key: (abs(tv) / abs(sv) if abs(sv) > 1e-15 else None)
              for key, (sv, tv) in pairs.items()}
    return {
        'system': getattr(system, 'name', ''), 'field_y': field_y,
        'wl': wl, 'sums': sums,
        'axial': {'c1_mm': c1, 'c3_mm': c3, 'c5_mm': c5},
        'field': {'a0_mm': a0, 'a1_mm': a1, 'a2_mm': a2, 'a3_mm': a3,
                  'b1_mm': b1},
        'chromatic': {'delta_f_mm': delta_f, 'wl_lo': S['wl_lo'],
                      'wl_hi': S['wl_hi']},
        'signs': signs, 'orders': orders,
    }


# ── Golden .PRN: парсинг секции sumsed ──────────────────────────────────────

#: Соответствие колонок sumsed (позиции в строке после ' ' + I3).
_SUMSED_SPANS = ((4, 15), (15, 26), (26, 37), (37, 48), (48, 59),
                 (59, 69), (69, 79))

#: Ключи сумм в порядке колонок sumsed.
_SUMSED_KEYS = ('S1', 'S2', 'S3', 'S4', 'S5', 'S1xp', 'S2xp')


def parse_prn_seidel(prn_path) -> List[Dict]:
    """Строки секции сумм Зейделя из .PRN OPAL (sumsed, cp866).

    Строка sumsed — формат ``(' ',I3,5(F11.5),2F10.5)``: номер (0 —
    итог, 1..n — поверхности) и 7 сумм S1..S5, S1хр, S2хр. Позиционный
    разбор по границам полей формата; переполнение FORTRAN (звёздочки)
    и пустые поля — ``None``. Строка засчитывается при ≥5 распознанных
    числах. Возвращает список словарей (возможно пустой — секции в
    эталонах репозитория нет).
    """
    try:
        text = Path(prn_path).read_text(encoding='cp866', errors='replace')
    except OSError:
        return []
    rows: List[Dict] = []
    for line in text.splitlines():
        if len(line) < 69 or not line[0].isspace():
            continue
        try:
            num = int(line[1:4])
        except ValueError:
            continue
        values = []
        for lo, hi in _SUMSED_SPANS:
            try:
                values.append(float(line[lo:hi]))
            except ValueError:
                values.append(None)
        if sum(v is not None for v in values) >= 5:
            row = {'n': num}
            row.update(dict(zip(_SUMSED_KEYS, values)))
            rows.append(row)
    return rows


def _golden_totals(rows: List[Dict], n_surfaces: int) -> Optional[Dict]:
    """Итоговые суммы из строк sumsed: строка N=0, иначе сумма 1..n.

    [РЕКОНСТРУКЦИЯ]: нумерация итоговой строки sumsed в реверсе не
    подтверждена (§14.4) — берётся строка N=0; если её нет, а строки
    1..n идут подряд по всем поверхностям, итог = их сумма.
    """
    for row in rows:
        if row['n'] == 0:
            return row
    per_surface = {row['n']: row for row in rows if row['n'] >= 1}
    if set(per_surface) == set(range(1, n_surfaces + 1)):
        totals = {'n': 0}
        for key in _SUMSED_KEYS:
            vals = [per_surface[i].get(key) for i in range(1, n_surfaces + 1)]
            if any(v is None for v in vals):
                totals[key] = None
            else:
                totals[key] = sum(vals)
        return totals
    return None


def seidel_vs_golden(system, prn_path, tol: float = 0.05) -> Dict:
    """Сверка сумм Зейделя порта с секцией golden .PRN OPAL.

    Парсинг секции — :func:`parse_prn_seidel`; итоговые суммы —
    :func:`_golden_totals`. Сверка двухуровневая (нормировка
    вспомогательных лучей OPAL EDIT неизвестна — абсолютные значения
    не сравниваются):

    * **знаки** SI..SV, SIхр/SIIхр (где golden имеет число);
    * **отношения** Sₖ/S1 и SIхр/SI (инвариант нормировки) —
      относительное расхождение ≤ ``tol`` (по умолчанию 5 % — float32
      OPAL).

    Args:
        system: Оптическая система (должна соответствовать .PRN).
        prn_path: Путь к .PRN OPAL (cp866).
        tol: Допуск относительного расхождения отношений, доли.

    Returns:
        ``{'status': 'matched'|'mismatch'|'skipped', 'reason'?,
        'golden', 'sums', 'signs', 'ratios', 'tol', 'golden_rows'}``.
        ``skipped`` — секции сумм в .PRN нет (все эталоны репозитория)
        либо итоговая строка не восстановима; ``reason`` поясняет.
    """
    S = seidel_sums(system)
    sums = {k: S[k] for k in ('SI', 'SII', 'SIII', 'SIV', 'SV',
                              'SIxp', 'SIIxp')}
    rows = parse_prn_seidel(prn_path)
    out = {'status': 'skipped', 'sums': sums, 'tol': tol,
           'golden_rows': rows}
    if not rows:
        out['reason'] = ('секция сумм Зейделя (sumsed) в PRN не найдена —'
                         ' числовая сверка невозможна')
        return out
    totals = _golden_totals(rows, len(system.surfaces))
    if totals is None:
        out['reason'] = ('итоговая строка сумм не восстановима (нет N=0 и'
                         ' строк 1..n по числу поверхностей)')
        return out
    out['golden'] = totals

    key_map = dict(zip(_SUMSED_KEYS,
                       ('SI', 'SII', 'SIII', 'SIV', 'SV', 'SIxp', 'SIIxp')))

    def sign(v):
        return (v > 0) - (v < 0)

    signs = {}
    for gk, sk in key_map.items():
        gv = totals.get(gk)
        if gv is None:
            continue
        signs[sk] = sign(gv) == sign(sums[sk])
    out['signs'] = signs

    ratios = {}
    ok = all(signs.values())
    for gk, sk in (('S2', 'SII'), ('S3', 'SIII'), ('S4', 'SIV'),
                   ('S5', 'SV')):
        gv, g1 = totals.get(gk), totals.get('S1')
        if gv is None or g1 is None or abs(g1) < 1e-12:
            continue
        gr, pr = gv / g1, sums[sk] / sums['SI']
        rel = abs(gr - pr) / max(abs(pr), 1e-12)
        # квант печати F11.5: у |S1| ~ 1e-4 половина младшего разряда
        # даёт единицы процентов — такие отношения не засчитываются
        quantum = 5e-6 / abs(g1)
        low_prec = quantum > tol
        ratios[sk] = {'golden': gr, 'port': pr, 'rel_dev': rel,
                      'low_precision': low_prec}
        if rel > tol and not low_prec:
            ok = False
    out['ratios'] = ratios
    out['status'] = 'matched' if ok else 'mismatch'
    return out
