"""Критерии оптимального фокуса OPAL (TASK_FOCUS / B4, REVERSE_PLAN).

Плоскости оптимальной установки для системы с волновой аберрацией W:
min RMS(W), max Штрель, min RMS геометрического пятна, зональный баланс
0.7 и EQF — «равнофокусность» (марка OPALOW, REVERSE_OPALO §1/§8).

Соглашения
----------
* Все функции возвращают сдвиг фокальной плоскости Δz, мм, относительно
  плоскости Гаусса z_G (параксиальный фокус); Δz > 0 — дальше от системы
  (в сторону изображения), как ``defocus_mm`` в
  ``aberrations.compute_spot_diagram_at_defocus``.
* Связь с волновым дефокусом d (волны на краю зрачка, член d·ρ²):
  калибровка по сдвигу центра опорной сферы даёт
  W(Δz) = W(0) − Δz/(8·F#²·λ)·ρ², т.е. d = −Δz/(8·F#²·λ_мм) и
  Δz_мм = −8·F#²·λ_мм·d (λ в мм; F# = |f'|/D_эфф).
* Волновой фронт снимается гексаполярной сеткой зрачка
  (``aberrations.trace_wavefront_hexapolar``) с FOCUS_RINGS кольцами,
  кратными 10, чтобы кольца 0.3/0.7/1.0 существовали точно.

EQF (гипотеза)
--------------
Код OPALO для EQF не разобран (REVERSE_OPALO §8, п.3 — пробел). В досье
марка EQF таблицы OPALOW растолкована как «равнофокусность» — критерий
оптимального фокуса. Здесь EQF реализован как итеративный зонный паритет:
подбирается дефокус, при котором СКВ волновой аберрации внутренней рабочей
зоны [0.3, 0.7] равна СКВ внешней зоны [0.7, 1.0] — «одинаковое качество»
по зонам зрачка. Корень ищется бисекцией вокруг плоскости min RMS(W);
при отсутствии корня EQF вырождается в min RMS(W) (converged=False).
В OPALOPT.DOC (REVERSE_OPTDOC §1.5) «EQF» — оператор ограничений-равенств
оптимизатора (фр = (рвз−рвт)/рвн), это ДРУГОЙ смысл того же имени.

Штрель
------
Для max Штреля используется квадратура интеграла |∫e^{i2πW}dA|²/A² прямо
по гексаполярным точкам (пистон и глобальная фаза выпадают из |·|).
Сетка ``strehl._pupil_grid_from_points`` не годится для фокусировки:
её IDW-интерполяция (веса 1/(d²+soft), soft=(2/(N−1))²) при ~330 точках
даёт фону дальних сэмплов ~12 % веса — центр зрачка подтягивается к
среднему по зрачку (в пробах: W(r=0.1): −0.0001λ истинное против −0.027λ
на решётке), и оптимум на решётке смещается до ~0.67× истинного.
``strehl.py`` — эталон волны 6 (REVERSE_OPALO §9.7) и не правится;
смещение устраняется локальной квадратурой. На осесимметричном поле
квадратура точна по кольцам (W постоянна на кольце) и сходится по числу
колец: на дублете с умеренной сферической согласие с min RMS(W) < 1 %.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from optics_engine import OpticalSystem, paraxial_trace
from optics_utils import get_effective_aperture, make_field_ray
from analysis import aberrations as ab

# Число колец гексаполярной сетки: кратно 10 (кольца 0.3/0.7/1.0 точные)
# и достаточно для квадратурного Штреля при |W| ~ 1–3λ (пробы: сходимость
# argmax при rings≥30 лучше 1 %).
FOCUS_RINGS = 30

# Геометрическое пятно: сетка лучей и скан фокуса
SPOT_GRID = 25
SPOT_SPAN_MM = 3.0
SPOT_STEPS = 361

# Штрель: скан волнового дефокуса вокруг плоскости min RMS(W)
STREHL_SPAN_WAVES = 4.0
STREHL_STEPS = 801

# EQF: границы рабочей зоны (внутренняя) и внешней зоны зрачка
EQF_INNER = 0.3
EQF_OUTER = 0.7

# Зональный баланс классической плоскости наилучшей установки
ZONE_RING = 0.7

_RING_TOL = 1e-9


# ── Волновой уровень: (ρ², W)-массивы, тестируются на синтетике ──────────

def _defocus_min_rms(rho2: np.ndarray, W: np.ndarray) -> float:
    """Дефокус d (волны на краю), минимизирующий RMS(W + d·ρ²).

    Наименьшие квадраты: d = −Cov(W, ρ²)/Var(ρ²).
    """
    var = float(np.var(rho2))
    if var < 1e-15:
        return 0.0
    return -float(np.cov(W, rho2, bias=True)[0, 1]) / var


def _ring_stats(points: List[Tuple[float, float, float]],
                num_rings: int) -> Dict[float, Tuple[float, float]]:
    """Кольца гексагональной сетки: r → (среднее ρ², среднее W)."""
    by_ring: Dict[int, list] = {}
    for px, py, w in points:
        r = math.hypot(px, py)
        ring = round(r * num_rings)
        by_ring.setdefault(ring, []).append((px * px + py * py, w))
    stats = {}
    for ring, vals in by_ring.items():
        arr = np.asarray(vals)
        stats[ring / num_rings] = (float(arr[:, 0].mean()),
                                   float(arr[:, 1].mean()))
    return stats


def _nearest_ring(stats: Dict[float, Tuple[float, float]],
                  target: float) -> float:
    """Ближайшее доступное кольцо к радиусу target."""
    return min(stats, key=lambda r: abs(r - target))


def _defocus_zone_balance(points: List[Tuple[float, float, float]],
                          num_rings: int, zone: float = ZONE_RING) -> float:
    """Дефокус d: W(zone) = W(1.0) после добавления d·ρ².

    Классический зональный баланс — плоскость посередине между краевым
    и зональным фокусами (для сферической совпадает с «наилучшей
    установкой» учебника).
    """
    stats = _ring_stats(points, num_rings)
    r_z = _nearest_ring(stats, zone)
    r_e = _nearest_ring(stats, 1.0)
    m_z, k_z = stats[r_z][1], stats[r_z][0]
    m_e, k_e = stats[r_e][1], stats[r_e][0]
    if abs(k_e - k_z) < 1e-12:
        return 0.0
    return (m_z - m_e) / (k_e - k_z)


def _strehl_quadrature(W: np.ndarray, rho2: np.ndarray, d: float) -> float:
    """Штрель квадратурой по точкам зрачка при дефокусе d·ρ².

    S = |Σ e^{i2π(W+d·ρ²)}|² / (Σ 1)² — точки гексагональной сетки
    площадно-равномерны, пистон выпадает из модуля суммы.
    """
    phase = np.exp(2j * np.pi * (W + d * rho2))
    total = phase.sum()
    return float((total.real ** 2 + total.imag ** 2) / len(phase) ** 2)


def _parabolic_extremum(y0: float, y1: float, y2: float) -> float:
    """Смещение вершины параболы по трём точкам (в единицах шага, [−1, 1])."""
    den = y0 - 2.0 * y1 + y2
    if den == 0.0:
        return 0.0
    off = 0.5 * (y0 - y2) / den
    return max(-1.0, min(1.0, off))


def _defocus_max_strehl(rho2: np.ndarray, W: np.ndarray,
                        d_center: float,
                        span: float = STREHL_SPAN_WAVES,
                        steps: int = STREHL_STEPS) -> Tuple[float, float]:
    """Дефокус d максимума Штреля (скан + параболическое уточнение)."""
    ds = np.linspace(d_center - span, d_center + span, steps)
    ss = np.array([_strehl_quadrature(W, rho2, d) for d in ds])
    j = int(ss.argmax())
    d_best = ds[j]
    if 0 < j < steps - 1:
        d_best += _parabolic_extremum(ss[j - 1], ss[j], ss[j + 1]) * (ds[1] - ds[0])
    return float(d_best), float(ss[j])


def _zone_rms(W: np.ndarray, rho2: np.ndarray, d: float,
              sel: np.ndarray) -> float:
    """СКВ волновой аберрации W + d·ρ² на выбранной зоне зрачка."""
    v = W[sel] + d * rho2[sel]
    return float(v.std())


def _eqf_defocus(points: List[Tuple[float, float, float]],
                 num_rings: int, d_center: float,
                 inner: float = EQF_INNER,
                 outer: float = EQF_OUTER) -> Dict:
    """EQF: итеративный паритет СКВ зон [inner, outer] и [outer, 1].

    f(d) = RMS(W+d·ρ² | r∈[inner,outer]) − RMS(W+dρ² | r∈[outer,1]) = 0.
    Сканируется брекет вокруг d_center, корни уточняются бисекцией;
    выбирается ближайший к d_center. Возвращает словарь с d, остатком
    и признаком сходимости (при отсутствии корня — d_center, False).
    """
    rho = np.array([math.hypot(px, py) for px, py, _ in points])
    rho2 = np.array([px * px + py * py for px, py, _ in points])
    W = np.array([w for _, _, w in points])
    sel_in = (rho >= inner - _RING_TOL) & (rho <= outer + _RING_TOL)
    sel_out = (rho >= outer - _RING_TOL) & (rho <= 1.0 + _RING_TOL)
    if sel_in.sum() < 3 or sel_out.sum() < 3:
        return {'d': d_center, 'residual': float('nan'), 'converged': False,
                'n_points_in': int(sel_in.sum()), 'n_points_out': int(sel_out.sum())}

    def f(d: float) -> float:
        return _zone_rms(W, rho2, d, sel_in) - _zone_rms(W, rho2, d, sel_out)

    # грубый скан брекета, корни — перемены знака f
    lo, hi = d_center - STREHL_SPAN_WAVES, d_center + STREHL_SPAN_WAVES
    ds = np.linspace(lo, hi, 401)
    fs = np.array([f(d) for d in ds])
    brackets = []
    for i in range(len(ds) - 1):
        if fs[i] == 0.0 or fs[i] * fs[i + 1] < 0:
            brackets.append((ds[i], ds[i + 1]))
    if not brackets:
        return {'d': d_center, 'residual': float(f(d_center)),
                'converged': False, 'n_points_in': int(sel_in.sum()),
                'n_points_out': int(sel_out.sum())}

    # бисекция ближайшего к d_center корня
    a, b = min(brackets, key=lambda ab: abs(0.5 * (ab[0] + ab[1]) - d_center))
    fa = f(a)
    for _ in range(60):
        m = 0.5 * (a + b)
        fm = f(m)
        if fm == 0.0 or (b - a) < 1e-10:
            break
        if fa * fm < 0:
            b = m
        else:
            a, fa = m, fm
    root = 0.5 * (a + b)
    return {'d': float(root), 'residual': float(f(root)), 'converged': True,
            'n_points_in': int(sel_in.sum()), 'n_points_out': int(sel_out.sum())}


# ── Контекст: одна трассировка на все критерии ───────────────────────────

def _resolve_wl(system: OpticalSystem, wl: Optional[float]) -> float:
    """Рабочая длина волны, мкм (None → максимум веса системы)."""
    if wl is not None:
        return float(wl)
    waves = sorted(system.wavelengths, key=lambda w: -w.weight)
    if waves:
        return float(waves[0].value)
    return 0.58756


def _focus_context(system: OpticalSystem, field: float,
                   wl: Optional[float], num_rings: int) -> Dict:
    """Трассировка волнового фронта + масштабы фокуса.

    Возвращает ρ²/W-массивы, F#, цену волны дефокуса в мм (K = 8·F#²·λ_мм),
    z_G и точки гексасетки.
    """
    wl_um = _resolve_wl(system, wl)
    points = ab.trace_wavefront_hexapolar(system, wl=wl_um, field_y=field,
                                          num_rings=num_rings)
    rho2 = np.array([px * px + py * py for px, py, _ in points])
    W = np.array([w for _, _, w in points])

    parax = paraxial_trace(system)
    efl = abs(parax.get('focal_length', 0.0) or 0.0)
    D = get_effective_aperture(system, default=10.0)
    if efl <= 1e-9 or D <= 1e-9:
        raise ValueError('система без фокусного расстояния/апертуры — '
                         'критерии фокуса не определены')
    fnum = efl / D
    mm_per_wave = 8.0 * fnum * fnum * wl_um * 1e-3
    z_G = ab._paraxial_focus_z(system)
    return {'points': points, 'rho2': rho2, 'W': W, 'wl_um': wl_um,
            'field': field, 'efl': efl, 'D': D, 'f_number': fnum,
            'mm_per_wave': mm_per_wave, 'z_G': z_G, 'num_rings': num_rings}


def _waves_to_mm(d: float, ctx: Dict) -> float:
    """Волновой дефокус d (волны на краю) → сдвиг плоскости, мм."""
    return -ctx['mm_per_wave'] * d


# ── Публичные критерии (все возвращают Δz, мм, от плоскости Гаусса) ──────

def focus_min_rms_wavefront(system: OpticalSystem, field: float = 0.0,
                            wl: Optional[float] = None) -> float:
    """Плоскость min RMS(W): наименьшие квадраты по W и ρ².

    Классика (и «наименьшие квадраты» OPALOPT.DOC): при умеренных
    аберрациях совпадает с max Штреля (Марешаль).
    """
    ctx = _focus_context(system, field, wl, FOCUS_RINGS)
    return _waves_to_mm(_defocus_min_rms(ctx['rho2'], ctx['W']), ctx)


def focus_max_strehl(system: OpticalSystem, field: float = 0.0,
                     wl: Optional[float] = None) -> float:
    """Плоскость max Штреля (квадратура по гексаполярным точкам).

    При |W| ≳ 2λ максимумы Штреля и min RMS физически расходятся
    (многолепестковое PSF) — расхождение отражает реальную оптику,
    а не счёт (см. докстринг модуля).
    """
    ctx = _focus_context(system, field, wl, FOCUS_RINGS)
    d_center = _defocus_min_rms(ctx['rho2'], ctx['W'])
    d_best, _s = _defocus_max_strehl(ctx['rho2'], ctx['W'], d_center)
    return _waves_to_mm(d_best, ctx)


def focus_zone_best(system: OpticalSystem, field: float = 0.0,
                    wl: Optional[float] = None) -> float:
    """Зональный баланс: W(0.7) = W(1) — плоскость наилучшей установки."""
    ctx = _focus_context(system, field, wl, FOCUS_RINGS)
    return _waves_to_mm(_defocus_zone_balance(ctx['points'], FOCUS_RINGS), ctx)


def _exit_ray_fan(system: OpticalSystem, field: float,
                  wl_um: float, n_grid: int) -> List[Tuple[float, ...]]:
    """Выходные лучи пучка: (x, y, z, dx/dz, dy/dz) в пространстве изображений.

    Направления берутся из ``_air_exit_direction`` (нормировка спасает
    при вырожденном последнем сегменте трассировки).
    """
    parax = paraxial_trace(system)
    z_start, z_pupil = ab._compute_ray_start(system, parax)
    D = get_effective_aperture(system, default=10.0)
    rays = []
    for i in range(n_grid):
        for j in range(n_grid):
            px = -1.0 + 2.0 * i / (n_grid - 1)
            py = -1.0 + 2.0 * j / (n_grid - 1)
            if px * px + py * py <= 1.0:
                rays.append(make_field_ray(system, px * D / 2, py * D / 2,
                                           field, z_start, z_pupil))
    out = []
    for res in ab._trace_ray_list(system, rays, wl_um):
        if not res.success or len(res.path) < 2:
            continue
        u = ab._air_exit_direction(system, res, wl_um)
        if u is None or u[2] < 1e-6:
            continue
        p = res.path[-1]
        out.append((p[0], p[1], p[2], u[0] / u[2], u[1] / u[2]))
    return out


def _min_spot_rms_mm(exit_rays: List[Tuple[float, ...]], z_G: float,
                     span: float, steps: int) -> Tuple[float, float]:
    """Минимум RMS пятна (относительно центроида) сканом вокруг z_G."""
    if not exit_rays:
        return 0.0, float('nan')
    arr = np.asarray(exit_rays)

    def rms_at(z_t: float) -> float:
        t = z_t - arr[:, 2]
        xs = arr[:, 0] + arr[:, 3] * t
        ys = arr[:, 1] + arr[:, 4] * t
        xs = xs - xs.mean()
        ys = ys - ys.mean()
        return float(math.sqrt((xs * xs + ys * ys).mean()))

    zs = np.linspace(z_G - span, z_G + span, steps)
    rms = np.array([rms_at(z) for z in zs])
    j = int(rms.argmin())
    z_best = float(zs[j])
    if 0 < j < steps - 1:
        z_best += _parabolic_extremum(rms[j - 1], rms[j], rms[j + 1]) * (zs[1] - zs[0])
    return z_best - z_G, rms_at(z_best)


def focus_min_spot_rms(system: OpticalSystem, field: float = 0.0,
                       wl: Optional[float] = None) -> float:
    """Плоскость min RMS геометрического пятна (без дифракции).

    Для сферической аберрации лежит между краевым и зональным фокусами
    (круг наименьшего рассеяния) и не совпадает с min RMS(W).
    """
    wl_um = _resolve_wl(system, wl)
    rays = _exit_ray_fan(system, field, wl_um, SPOT_GRID)
    dz, _rms = _min_spot_rms_mm(rays, ab._paraxial_focus_z(system),
                                SPOT_SPAN_MM, SPOT_STEPS)
    return dz


def eqf(system: OpticalSystem, field: float = 0.0,
        wl: Optional[float] = None) -> Dict:
    """EQF — «равнофокусность» OPAL (гипотеза: паритет СКВ зон 0.3/0.7).

    Словарь: dz_mm, d_waves, converged, residual (разность СКВ зон),
    rms_in/rms_out — сами СКВ зон в найденной плоскости, hypothesis.
    """
    ctx = _focus_context(system, field, wl, FOCUS_RINGS)
    d_center = _defocus_min_rms(ctx['rho2'], ctx['W'])
    root = _eqf_defocus(ctx['points'], FOCUS_RINGS, d_center)
    rho = np.array([math.hypot(px, py) for px, py, _ in ctx['points']])
    sel_in = (rho >= EQF_INNER - _RING_TOL) & (rho <= EQF_OUTER + _RING_TOL)
    sel_out = (rho >= EQF_OUTER - _RING_TOL) & (rho <= 1.0 + _RING_TOL)
    d = root['d']
    rms_in = _zone_rms(ctx['W'], ctx['rho2'], d, sel_in)
    rms_out = _zone_rms(ctx['W'], ctx['rho2'], d, sel_out)
    return {
        'dz_mm': _waves_to_mm(d, ctx),
        'd_waves': d,
        'converged': root['converged'],
        'residual': root['residual'],
        'rms_in': rms_in,
        'rms_out': rms_out,
        'n_points_in': root.get('n_points_in'),
        'n_points_out': root.get('n_points_out'),
        'hypothesis': ('EQF = Equal Quality Focus: паритет СКВ W зон '
                       '[0.3, 0.7] и [0.7, 1.0]; код OPALO не разобран '
                       '(REVERSE_OPALO §8 п.3), в OPALOPT.DOC EQF — '
                       'ограничения-равенства оптимизатора (другой смысл)'),
    }


def all_focus_criteria(system: OpticalSystem, field: float = 0.0,
                       wl: Optional[float] = None) -> Dict:
    """Сводка всех критериев фокуса + лучшая плоскость по OPAL.

    Одна трассировка на все волновые критерии; геометрическое пятно
    трассируется отдельно. Плоскость OPAL (марка EQF «равнофокусность»)
    — результат :func:`eqf`; при несходимости используется min RMS(W).
    """
    ctx = _focus_context(system, field, wl, FOCUS_RINGS)
    rho2, W, points = ctx['rho2'], ctx['W'], ctx['points']

    d_rms = _defocus_min_rms(rho2, W)
    d_strehl, s_max = _defocus_max_strehl(rho2, W, d_rms)
    d_zone = _defocus_zone_balance(points, FOCUS_RINGS)
    eqf_res = eqf(system, field, ctx['wl_um'])

    wl_um = _resolve_wl(system, wl)
    rays = _exit_ray_fan(system, field, wl_um, SPOT_GRID)
    dz_spot, rms_spot = _min_spot_rms_mm(rays, ctx['z_G'], SPOT_SPAN_MM, SPOT_STEPS)

    sigma_best = float((W + d_rms * rho2).std())
    best_opal = eqf_res['dz_mm'] if eqf_res['converged'] else \
        _waves_to_mm(d_rms, ctx)
    return {
        'min_rms_wavefront_mm': _waves_to_mm(d_rms, ctx),
        'max_strehl_mm': _waves_to_mm(d_strehl, ctx),
        'min_spot_rms_mm': dz_spot,
        'zone_best_mm': _waves_to_mm(d_zone, ctx),
        'eqf_mm': eqf_res['dz_mm'],
        'eqf': eqf_res,
        'best_opal_mm': best_opal,
        'best_opal_source': 'eqf' if eqf_res['converged'] else 'min_rms_wavefront',
        'strehl_at_max': s_max,
        'rms_wavefront_at_min': sigma_best,
        'spot_rms_mm_at_min': rms_spot,
        'meta': {
            'wl_um': ctx['wl_um'], 'field': field, 'f_number': ctx['f_number'],
            'D_mm': ctx['D'], 'efl_mm': ctx['efl'], 'z_G_mm': ctx['z_G'],
            'num_rings': FOCUS_RINGS, 'num_points': len(points),
            'mm_per_edge_wave': ctx['mm_per_wave'],
        },
    }
