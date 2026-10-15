"""
OPAL-OKB — Оптимизация оптических систем: решатель «ЛАП» (волна 9)

Порт модели оптимизатора OPALLAP.EXE / задания OPALOPT.DOC по реверс-досье
[REVERSE_LAP.md] (§9 — ТЗ) и [REVERSE_OPTDOC.md] (§5 — выводы, §1 — язык
OPALOPT):

- **многоцелевая постановка**: N целей (функции отклика «оф(I)») × M
  варьируемых параметров («PAR») одновременно — f′, BFD, аберрации, суммы
  Зейделя, RMS пятна;
- **оф(I) = (офт − офз)/офн × офв** — текущее, заданное, норма, вес
  (OPALOPT:701–713); умолчания норм — по типу характеристики (продольные
  0.1 мм, поперечные 0.01 мм; OPALOPT:167–172);
- **критерий качества F = Σ оф(I)² + Σ шф²** — штрафы границ/связей
  (PENIP0/PENSS, шф = min(0; (нр − t)·g)) — часть objective;
- **якобиан центральными разностями P ± DP0** (GTISL, цикл 0x67BC
  OPALLAP) с масштабированием столбцов GTIMAS;
- **шаг — демпфированные нормальные уравнения Марквардта**
  (JᵀJ + λ·diag(JᵀJ))·ΔP = −Jᵀ·оф; численное ядро — ``numpy.linalg.solve``
  (Гаусс с частичным выбором ведущего элемента): в OPALLAP СЛАУ ≤5×5
  решалась явными развёрнутыми формулами на скалярах COMMON (REVERSE_LAP
  §6) — воспроизводить «аутентичный» решатель не нужно, поведение то же,
  стабильность выше; сингулярность → ISTOP = −1 (аналог FCOM [0x4dac]);
- **лимитеры шага** |ΔPᵢ| ≤ 10·DP0ᵢ и **границы-штрафы вместо молчаливого
  clamp**: якобиан считается на невозмущенных границами значениях P±DP0;
- **статусы останова ISTOP**: 0 — допуски целей, 1 — максимум NSTEP,
  2 — нет улучшения, −1 — вырождение; протокол итераций — ЛАП-трейсы
  (``nstep, FMIN, λ, ΔP`` + финал ``ISTOP,NSTEP``);
- **solve-режим 1×1** (``solve_single``) — Ньютон по чувствительности
  dF/dP из центральной разности с обязательной пробой чувствительности
  (закрывает отказы «толщина последней поверхности не влияет на f′»);
- **связи** PGL/CC: линейные «элементарные преобразования»
  Δведомый = k·Δведущий (симметрия радиусов и т.п.);
- ``parse_opt_file`` — разбор задания оптимизации во входном языке
  OPAL-PC: операторы ``PAR/MF/EQF + pmin/pmax + D<…`` (грамматика —
  OPALANG.DOC §3, живые примеры — ``extracted/opal_okb/PLIOPT.OPT``).

Существующее не дублируется: параксиальные характеристики —
``domain/calculations.paraxial_trace``, аберрационные вычислители —
``analysis/aberrations``, суммы Зейделя — ``seidel_aberrations``.
Legacy-движок ``optimizer.py`` (одношаговый DLS по скалярному RMS,
бисекция fit_*) остаётся для совместимости; GUI-подгонка переводится
на этот модуль.
"""
from __future__ import annotations

import copy
import logging
import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from optics_engine import (OpticalSystem, paraxial_trace, refractive_index,
                           seidel_aberrations)
from optics_utils import get_primary_wl
from analysis.aberrations import (compute_field_aberrations, compute_rms_spot,
                                  compute_spot_diagram, trace_aberration_fan)

__all__ = [
    'OptVariable', 'OptGoal', 'Penalty', 'OptResult',
    'PARAM_TYPES', 'GOAL_KINDS', 'DEFAULT_NORMS',
    'get_param', 'set_param', 'bounds_penalties', 'penalty_residual',
    'evaluate_goal', 'merit_vector', 'build_jacobian',
    'optimize', 'solve_single',
    'parse_opt_task', 'parse_opt_file',
    'ISTOP_TOLERANCES', 'ISTOP_MAX_ITER', 'ISTOP_NO_IMPROVE',
    'ISTOP_DEGENERATE', 'ISTOP_MESSAGES',
]

_log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Коды останова ISTOP (REVERSE_LAP §9.2; трассы «ISTOP,NSTEP,IPOD» OPALLAP)
# --------------------------------------------------------------------------- #

ISTOP_TOLERANCES = 0     # все |оф(I)| < tol(I) — цели достигнуты
ISTOP_MAX_ITER = 1       # исчерпан максимум итераций NSTEP
ISTOP_NO_IMPROVE = 2     # нет улучшения два шага подряд
ISTOP_DEGENERATE = -1    # вырождение: якобиан/делитель ≈ 0, трассировка не идёт

ISTOP_MESSAGES = {
    ISTOP_TOLERANCES: 'все цели в допусках',
    ISTOP_MAX_ITER: 'исчерпан максимум итераций (NSTEP)',
    ISTOP_NO_IMPROVE: 'нет улучшения критерия два шага подряд',
    ISTOP_DEGENERATE: 'вырождение задачи (якобиан ≈ 0 / трассировка не сходится)',
}


# --------------------------------------------------------------------------- #
# Модель данных (REVERSE_OPTDOC §5.1: OptTask/Operand → переменные/цели/штрафы)
# --------------------------------------------------------------------------- #

@dataclass
class OptVariable:
    """Варьируемый параметр «PAR».

    Attributes:
        surface: 0-based индекс поверхности.
        param: тип параметра — ``'radius'`` | ``'thickness'`` | ``'conic'``
            | ``'semi_diameter'`` | ``'glass_index'`` (сдвиг показателя
            преломления через ``n_override`` на всех λ — дисперсия
            сохраняется).
        pmin/pmax: границы → штрафы PENIP0 (не молчаливый clamp).
        dp0: шаг центральных разностей DP0 (единицы параметра);
            ``None`` → авто = max(1e-4, 1e-3·|P|).
        link: связь PGL/CC — тройка ``(surface, param, k)`` ведущей
            переменной: ведомый движется как Δведомый = k·Δведущий
            (коэффициент CC; ведущий обязан быть свободным).
    """
    surface: int
    param: str = 'radius'
    pmin: Optional[float] = None
    pmax: Optional[float] = None
    dp0: Optional[float] = None
    link: Optional[Tuple[int, str, float]] = None


@dataclass
class OptGoal:
    """Цель-функция отклика «оф(I)»: характеристика + заданное/норма/вес.

    kind — вид характеристики (реестр :data:`GOAL_KINDS`):

    - параксиальные: ``'efl'`` (f′), ``'bfd'`` (задний фокальный отрезок),
      ``'magnification'`` (обобщённое увеличение VG0);
    - аберрационные: ``'longitudinal'`` (продольная сферическая, зона),
      ``'transverse'`` (поперечная аберрация луча, зона/поле),
      ``'rms_spot'`` (RMS пятна рассеяния), ``'seidel'`` (суммы SI..SV),
      ``'field'`` (внеосевые: astigmatism/z_m/z_s/coma/distortion).

    refs — зона/поле/λ/лучи: ``zone`` (0..1), ``field`` (град),
    ``wl`` (мкм), ``num_rays``, ``term`` (для seidel), ``metric``
    (для field).
    """
    kind: str
    target: Optional[float] = 0.0   # офз; None = «зафиксировать текущее»
    weight: float = 1.0             # офв
    norm: Optional[float] = None    # офн; None → авто по типу
    tol: float = 1e-4               # допуск |оф| (критерий ISTOP=0)
    refs: dict = field(default_factory=dict)


@dataclass
class Penalty:
    """Штраф «шф» границы/связи: шф = min(0; (нр − t)·g) (OPALOPT:945–987).

    Нормированное нарушение нр = (P − граница)/scale для нижней границы и
    (граница − P)/scale для верхней, scale = 1 % от max(1, |граница|) —
    выход за границу на 1 % даёт |шф| ≈ g, т.е. штраф сопоставим с оф(I).
    Вклад в критерий — шф² (REVERSE_LAP §7).
    """
    surface: int
    param: str
    bound: str = 'min'          # 'min' | 'max'
    value: float = 0.0          # граница (в единицах параметра)
    t: float = 0.0              # сдвиг t< (допуск, в единицах нр)
    g: float = 1.0              # вес g<


@dataclass
class OptResult:
    """Результат решения (аналог FitResult REVERSE_LAP §9.2)."""
    system: Optional[OpticalSystem] = None   # оптимизированная копия
    converged: bool = False                  # istop == 0
    istop: int = ISTOP_MAX_ITER
    nstep: int = 0
    fmin: float = math.inf
    residuals: List[float] = field(default_factory=list)  # оф(I) по целям
    history: List[dict] = field(default_factory=list)     # nstep, fmin, x, λ
    protocol: List[str] = field(default_factory=list)     # ЛАП-трейсы
    message: str = ''


# --------------------------------------------------------------------------- #
# Доступ к параметрам поверхностей
# --------------------------------------------------------------------------- #

_PARAM_ATTRS = {
    'radius': 'radius',
    'thickness': 'thickness',
    'conic': 'conic_constant',
    'semi_diameter': 'semi_diameter',
}
#: Типы варьируемых параметров (табл. 1 OPALOPT:1122–1137: C/D/ES/SD/N).
PARAM_TYPES = tuple(_PARAM_ATTRS) + ('glass_index',)


def get_param(system: OpticalSystem, surface_idx: int, param: str) -> float:
    """Текущее значение параметра поверхности (для glass_index — n основной λ)."""
    s = system.surfaces[surface_idx]
    if param in _PARAM_ATTRS:
        return float(getattr(s, _PARAM_ATTRS[param]))
    if param == 'glass_index':
        return float(refractive_index(s.glass, get_primary_wl(system),
                                      None, s.n_override or None))
    raise ValueError(f"Неизвестный тип параметра: {param!r} "
                     f"(допустимо: {', '.join(PARAM_TYPES)})")


def set_param(system: OpticalSystem, surface_idx: int, param: str,
              value: float) -> None:
    """Установить параметр (glass_index — сдвиг n на всех λ, дисперсия
    сохраняется; радиус 0 интерпретируется трассировщиком как плоскость)."""
    s = system.surfaces[surface_idx]
    if param in _PARAM_ATTRS:
        setattr(s, _PARAM_ATTRS[param], float(value))
        return
    if param == 'glass_index':
        if not s.glass:
            raise ValueError(
                f"glass_index: поверхность {surface_idx + 1} без стекла")
        wls = sorted({w.value for w in system.wavelengths} |
                     {get_primary_wl(system)})
        wl0 = get_primary_wl(system)
        base0 = refractive_index(s.glass, wl0, None, s.n_override or None)
        delta = float(value) - base0
        s.n_override = {wl: refractive_index(s.glass, wl, None,
                                             s.n_override or None) + delta
                        for wl in wls}
        return
    raise ValueError(f"Неизвестный тип параметра: {param!r}")


# --------------------------------------------------------------------------- #
# Вычислители целей (существующее: paraxial_trace, analysis/aberrations)
# --------------------------------------------------------------------------- #

class _EvalError(RuntimeError):
    """Трассировка/расчёт цели не сошёлся (аналог статуса es:[0x1950] = −1)."""


def _goal_wl(system: OpticalSystem, goal: OptGoal) -> float:
    wl = (goal.refs or {}).get('wl')
    return float(wl) if wl is not None else float(get_primary_wl(system))


def _interp_fan(fan: Sequence[dict], key: str, zone: float) -> float:
    """Линейная интерполяция величины луча по зрачковой координате 0..1
    (верхняя половина веера — сглаживание для конечных разностей)."""
    xs: List[float] = []
    ys: List[float] = []
    for row in fan:
        v = row.get(key)
        if not row.get('success') or v is None:
            continue
        if row['pupil_y'] >= -1e-9:
            xs.append(float(row['pupil_y']))
            ys.append(float(v))
    if len(xs) < 2:
        raise _EvalError(f"веер лучей пуст ({key})")
    return float(np.interp(max(0.0, min(1.0, zone)), xs, ys))


def _eval_paraxial(system: OpticalSystem, goal: OptGoal, key: str) -> float:
    px = paraxial_trace(system)
    v = px.get(key)
    if v is None or not math.isfinite(float(v)):
        raise _EvalError(f"параксиальный расчёт: {key} = {v}")
    return float(v)


def _eval_longitudinal(system: OpticalSystem, goal: OptGoal) -> float:
    """Продольная сферическая аберрация DSA: LSA(зона) = ds(зона) − ds(0)."""
    refs = goal.refs or {}
    fan = trace_aberration_fan(system, _goal_wl(system, goal),
                               num_rays=int(refs.get('num_rays', 15)),
                               field_y=0.0)
    zone = float(refs.get('zone', 1.0))
    return _interp_fan(fan, 'ds', zone) - _interp_fan(fan, 'ds', 0.0)


def _eval_transverse(system: OpticalSystem, goal: OptGoal) -> float:
    """Поперечная аберрация луча (зона, поле): dy(зона) − dy(главный)."""
    refs = goal.refs or {}
    fan = trace_aberration_fan(system, _goal_wl(system, goal),
                               num_rays=int(refs.get('num_rays', 15)),
                               field_y=float(refs.get('field', 0.0)))
    zone = float(refs.get('zone', 1.0))
    return _interp_fan(fan, 'dy', zone) - _interp_fan(fan, 'dy', 0.0)


def _eval_rms_spot(system: OpticalSystem, goal: OptGoal) -> float:
    refs = goal.refs or {}
    spots = compute_spot_diagram(system, wl=_goal_wl(system, goal),
                                 num_rays=int(refs.get('num_rays', 20)),
                                 field_y=float(refs.get('field', 0.0)))
    if not spots:
        raise _EvalError("точечная диаграмма пуста")
    return float(compute_rms_spot(spots))


def _eval_seidel(system: OpticalSystem, goal: OptGoal) -> float:
    term = (goal.refs or {}).get('term', 'SI')
    sums = seidel_aberrations(system)
    if term not in sums:
        raise ValueError(f"Неизвестная сумма Зейделя: {term!r} "
                         "(допустимо SI..SV)")
    return float(sums[term])


def _eval_field(system: OpticalSystem, goal: OptGoal) -> float:
    refs = goal.refs or {}
    metric = refs.get('metric', 'astigmatism')
    field_y = refs.get('field')
    if field_y is None:
        raise ValueError("цель 'field' требует refs['field'] (град)")
    rows = compute_field_aberrations(system, wl=_goal_wl(system, goal),
                                     field_points=[(float(field_y),)])
    if not rows or rows[0].get(metric) is None:
        raise _EvalError(f"внеосевые характеристики (поле {field_y}°) "
                         "не рассчитаны")
    return float(rows[0][metric])


#: Реестр вычислимых характеристик (kind → вычислитель).
GOAL_KINDS: Dict[str, Callable] = {
    'efl': lambda s, g: _eval_paraxial(s, g, 'focal_length'),
    'bfd': lambda s, g: _eval_paraxial(s, g, 'back_focal_distance'),
    'magnification': lambda s, g: _eval_paraxial(s, g, 'magnification'),
    'longitudinal': _eval_longitudinal,
    'transverse': _eval_transverse,
    'rms_spot': _eval_rms_spot,
    'seidel': _eval_seidel,
    'field': _eval_field,
}

#: Умолчания норм офн (OPALOPT:167–172: продольные 0.1 мм, поперечные 0.01).
DEFAULT_NORMS: Dict[str, float] = {
    'longitudinal': 0.1,
    'transverse': 0.01,
    'rms_spot': 0.01,
    'seidel': 0.1,
    'field': 0.01,
}
# Параксиальные/габаритные: норма = 1 % от |цели|, но не меньше пола.
_MIN_NORMS: Dict[str, float] = {
    'efl': 1.0, 'bfd': 1.0, 'magnification': 0.01,
}


def _resolve_norm(goal: OptGoal) -> float:
    """офн: явная → умолчание по типу → 1 % |target| (не меньше пола)."""
    if goal.norm is not None and goal.norm > 0:
        return float(goal.norm)
    if goal.kind in DEFAULT_NORMS:
        return DEFAULT_NORMS[goal.kind]
    floor = _MIN_NORMS.get(goal.kind, 1.0)
    t = goal.target if goal.target is not None else 0.0
    return max(floor, abs(t) * 0.01)


def evaluate_goal(system: OpticalSystem, goal: OptGoal) -> float:
    """Сырое значение характеристики цели офт(I) на системе."""
    fn = GOAL_KINDS.get(goal.kind)
    if fn is None:
        raise ValueError(f"Неизвестный вид цели: {goal.kind!r} "
                         f"(допустимо: {', '.join(GOAL_KINDS)})")
    return float(fn(system, goal))


def merit_vector(system: OpticalSystem, goals: Sequence[OptGoal]
                 ) -> List[float]:
    """Вектор остатков оф(I) = (офт − офз)/офн × офв по всем целям.

    Raises:
        _EvalError: трассировка одной из целей не сошлась.
    """
    out: List[float] = []
    for g in goals:
        if g.target is None:
            raise ValueError("target=None разрешим только внутри optimize()")
        out.append((evaluate_goal(system, g) - g.target) / _resolve_norm(g)
                   * g.weight)
    return out


# --------------------------------------------------------------------------- #
# Штрафы (PENIP0/PENSS)
# --------------------------------------------------------------------------- #

def penalty_residual(value: float, pen: Penalty) -> float:
    """шф = min(0; (нр − t)·g) — активен только за границей."""
    scale = 0.01 * max(1.0, abs(pen.value))
    if pen.bound == 'min':
        u = (value - pen.value) / scale
    elif pen.bound == 'max':
        u = (pen.value - value) / scale
    else:
        raise ValueError(f"bound должен быть 'min' или 'max': {pen.bound!r}")
    return min(0.0, u - pen.t) * pen.g


def bounds_penalties(variables: Sequence[OptVariable]) -> List[Penalty]:
    """Границы pmin/pmax переменных → штрафы PENIP0 (метод модифицированных
    штрафных функций, OPALOPT §1.7-2 — вместо молчаливого clamp)."""
    out: List[Penalty] = []
    for v in variables:
        if v.pmin is not None:
            out.append(Penalty(v.surface, v.param, 'min', float(v.pmin)))
        if v.pmax is not None:
            out.append(Penalty(v.surface, v.param, 'max', float(v.pmax)))
    return out


# --------------------------------------------------------------------------- #
# Валидация и применение вектора переменных (со связями PGL/CC)
# --------------------------------------------------------------------------- #

def _validate_task(system: OpticalSystem, variables: Sequence[OptVariable],
                   goals: Sequence[OptGoal]) -> None:
    if not variables:
        raise ValueError("Список переменных пуст")
    if not goals:
        raise ValueError("Список целей пуст")
    ns = len(system.surfaces)
    seen = set()
    for v in variables:
        if v.param not in PARAM_TYPES:
            raise ValueError(f"Неизвестный тип параметра: {v.param!r}")
        if not (0 <= v.surface < ns):
            raise ValueError(f"Индекс поверхности вне диапазона: {v.surface}")
        key = (v.surface, v.param)
        if key in seen:
            raise ValueError(f"Дублирующаяся переменная: поверхность "
                             f"{v.surface + 1}, {v.param}")
        seen.add(key)
        if v.pmin is not None and v.pmax is not None and v.pmin > v.pmax:
            raise ValueError(f"pmin > pmax: поверхность {v.surface + 1}, "
                             f"{v.param}")
    for v in variables:
        if v.link is None:
            continue
        ms, mp, _k = v.link
        master = next((u for u in variables
                       if (u.surface, u.param) == (ms, mp)), None)
        if master is None:
            raise ValueError(f"Связь ссылается на отсутствующую переменную: "
                             f"поверхность {ms + 1}, {mp}")
        if master.link is not None:
            raise ValueError("Цепочки связей не поддерживаются: ведущий "
                             f"({ms + 1}, {mp}) сам является ведомым")
    for g in goals:
        if g.kind not in GOAL_KINDS:
            raise ValueError(f"Неизвестный вид цели: {g.kind!r}")
        if g.weight < 0:
            raise ValueError(f"Вес цели отрицателен: {g.kind}")
        if g.tol <= 0:
            raise ValueError(f"Допуск цели должен быть > 0: {g.kind}")


def _resolve_dp0(var: OptVariable, value: float) -> float:
    """DP0 — шаг центральных разностей (в единицах параметра)."""
    if var.dp0 is not None and var.dp0 > 0:
        return float(var.dp0)
    return max(1e-4, 1e-3 * abs(value))


def _master_pos(variables: Sequence[OptVariable],
                link: Tuple[int, str, float]) -> int:
    ms, mp, _k = link
    for j, u in enumerate(variables):
        if (u.surface, u.param) == (ms, mp):
            return j
    raise ValueError("ведущий связи не найден")  # прикрытие — проверено выше


def _apply_vector(system: OpticalSystem, variables: Sequence[OptVariable],
                  free: Sequence[int], base: Sequence[float],
                  x: np.ndarray) -> None:
    """Применить значения свободных переменных + пересчитать ведомые связи."""
    for k, i in enumerate(free):
        v = variables[i]
        set_param(system, v.surface, v.param, float(x[k]))
    for i, v in enumerate(variables):
        if v.link is None:
            continue
        j = _master_pos(variables, v.link)
        k_coef = v.link[2]
        jx = float(x[free.index(j)]) if j in free else base[j]
        set_param(system, v.surface, v.param,
                  base[i] + k_coef * (jx - base[j]))


# --------------------------------------------------------------------------- #
# Якобиан (GTISL 0x67BC: центральные разности P ± DP0)
# --------------------------------------------------------------------------- #

def build_jacobian(system: OpticalSystem, variables: Sequence[OptVariable],
                   goals: Sequence[OptGoal], central: bool = True
                   ) -> np.ndarray:
    """Якобиан J[m×n] = d(оф)/dP по свободным переменным.

    ``central=True`` — центральные разности (F(P+DP0)−F(P−DP0))/(2·DP0),
    точность O(DP0²); ``False`` — forward O(DP0). Штрафы в J не входят —
    optimize() собирает расширенную систему с аналитическими штрафами
    конечными разностями того же шага.
    """
    _validate_task(system, variables, goals)
    work = copy.deepcopy(system)
    free = [i for i, v in enumerate(variables) if v.link is None]
    base = [get_param(work, v.surface, v.param) for v in variables]
    x = np.array([base[i] for i in free], dtype=float)
    dp0 = np.array([_resolve_dp0(variables[i], base[i]) for i in free])

    goals_r = _resolve_targets(work, list(goals))

    def res_at(xv: np.ndarray) -> Optional[np.ndarray]:
        _apply_vector(work, variables, free, base, xv)
        try:
            return np.array(merit_vector(work, goals_r), dtype=float)
        except _EvalError:
            return None

    r0 = res_at(x)
    if r0 is None:
        raise _EvalError("начальная точка: трассировка не сходится")
    m = len(r0)
    n = len(free)
    J = np.zeros((m, n))
    for i in range(n):
        xp = x.copy()
        xp[i] += dp0[i]
        rp = res_at(xp)
        if central:
            xm = x.copy()
            xm[i] -= dp0[i]
            rm = res_at(xm)
            if rp is None or rm is None:
                continue
            J[:, i] = (rp - rm) / (2.0 * dp0[i])
        else:
            if rp is None:
                continue
            J[:, i] = (rp - r0) / dp0[i]
    return J


def _resolve_targets(system: OpticalSystem,
                     goals: List[OptGoal]) -> List[OptGoal]:
    """target=None → «зафиксировать текущее» (умолчание EQF#, OPALOPT:869)."""
    out = []
    for g in goals:
        if g.target is None:
            out.append(replace(g, target=evaluate_goal(system, g)))
        else:
            out.append(g)
    return out


# --------------------------------------------------------------------------- #
# Решатель ЛАП (GTISL / GTISGR)
# --------------------------------------------------------------------------- #

#: Лимитер шага: |ΔPᵢ| ≤ K_LIMIT·DP0ᵢ (REVERSE_LAP §9.3е).
K_LIMIT = 10.0
#: Максимум бисекций α в линейном поиске шага (§9.3з).
MAX_BISECTIONS = 15


def optimize(system: OpticalSystem,
             variables: Sequence[OptVariable],
             goals: Sequence[OptGoal],
             penalties: Sequence[Penalty] = (),
             *,
             mode: str = 'linear',
             max_iter: int = 50,
             damping: float = 1.0,
             tol: float = 1e-8,
             num_rays: int = 20,
             callback: Optional[Callable] = None) -> OptResult:
    """Многоцелевая оптимизация ЛАП (GTISL-эквивалент, REVERSE_LAP §9.3).

    Args:
        system: исходная система (не изменяется — работает копия).
        variables: список OptVariable (свободные + связанные).
        goals: список OptGoal.
        penalties: дополнительные штрафы (границы переменных pmin/pmax
            добавляются автоматически).
        mode: ``'linear'`` (GTISL — нормальные уравнения Марквардта) или
            ``'gradient'`` (GTISGR — наискорейший спуск).
        max_iter: максимум итераций NSTEP.
        damping: начальное λ демпфирования.
        tol: порог стагнации |ΔF| < tol·max(1, |F|).
        num_rays: число лучей веера для трассируемых целей (умножается на
            refs['num_rays'] целей, если задан).
        callback: callable(nstep, fmin, x) после каждой итерации.

    Returns:
        OptResult с оптимизированной копией системы, историей и протоколом
        (формат ЛАП: ``nstep, FMIN, λ, ΔP`` + финал ``ISTOP,NSTEP``).
    """
    if mode not in ('linear', 'gradient'):
        raise ValueError(f"Неизвестный режим: {mode!r} ('linear'|'gradient')")
    _validate_task(system, variables, goals)

    variables = list(variables)
    goals = list(goals)
    pens = bounds_penalties(variables) + [Penalty(*p) if isinstance(p, tuple)
                                          else p for p in penalties]
    # num_rays по умолчанию для трассируемых целей (refs перекрывают)
    def _with_rays(g: OptGoal) -> OptGoal:
        refs = dict(g.refs or {})
        if refs.get('num_rays') is None and g.kind in ('longitudinal',
                                                       'transverse',
                                                       'rms_spot'):
            refs['num_rays'] = int(num_rays)
        return replace(g, refs=refs)
    goals = [_with_rays(g) for g in goals]

    work = copy.deepcopy(system)
    free = [i for i, v in enumerate(variables) if v.link is None]
    base = [get_param(work, v.surface, v.param) for v in variables]
    x = np.array([base[i] for i in free], dtype=float)
    dp0 = np.array([_resolve_dp0(variables[i], base[i]) for i in free])
    # Границы свободных переменных: принимаемая точка отражается в границы
    # (§9.3е); якобиан ниже считается на невозмущённых границами P ± DP0.
    lo = np.array([variables[i].pmin if variables[i].pmin is not None
                   else -np.inf for i in free])
    hi = np.array([variables[i].pmax if variables[i].pmax is not None
                   else np.inf for i in free])
    goals_r = _resolve_targets(work, goals)
    m = len(goals_r)

    def res_at(xv: np.ndarray) -> Optional[np.ndarray]:
        """оф(I) по целям + шф по штрафам (единый вектор остатков)."""
        _apply_vector(work, variables, free, base, xv)
        out: List[float] = []
        try:
            for g in goals_r:
                F = evaluate_goal(work, g)
                out.append((F - g.target) / _resolve_norm(g) * g.weight)
        except _EvalError:
            return None
        for p in pens:
            out.append(penalty_residual(
                get_param(work, p.surface, p.param), p))
        arr = np.array(out, dtype=float)
        return arr if np.all(np.isfinite(arr)) else None

    protocol: List[str] = []
    history: List[dict] = []

    def record(nstep: int, fmin: float, lam: float) -> None:
        history.append({'nstep': nstep, 'fmin': float(fmin),
                        'x': x.tolist(), 'lambda': float(lam)})

    r0 = res_at(x)
    if r0 is None:
        return _finish(work, variables, free, base, x, ISTOP_DEGENERATE,
                       math.inf, r0=None, goals=goals_r,
                       history=history, protocol=protocol,
                       note='начальная точка: трассировка не сходится')
    F = float(r0 @ r0)
    lam = float(damping)
    record(0, F, lam)
    protocol.append(f'GTISL: NBFO= {len(r0)} FMIN(0)= {F:.6g}')
    if callback is not None:
        callback(0, F, x.tolist())

    istop = ISTOP_MAX_ITER
    nstep = 0
    stagnation = 0     # |ΔF| < tol два шага подряд
    rejected = 0       # отклонённые шаги подряд

    while True:
        # (ж) критерий останова по целям — как в коде 0x74E87
        if all(abs(float(r0[k])) < goals_r[k].tol for k in range(m)):
            istop = ISTOP_TOLERANCES
            break
        if nstep >= max_iter:
            istop = ISTOP_MAX_ITER
            break

        # (б) якобиан центральными разностями P ± DP0
        n = len(free)
        J = np.zeros((len(r0), n))
        for i in range(n):
            xp = x.copy()
            xp[i] += dp0[i]
            rp = res_at(xp)
            xm = x.copy()
            xm[i] -= dp0[i]
            rm = res_at(xm)
            if rp is None or rm is None:
                continue    # возмущение не трассируется → столбец нечувствителен
            J[:, i] = (rp - rm) / (2.0 * dp0[i])
        if not np.any(J):
            istop = ISTOP_DEGENERATE
            protocol.append('GTISL: якобиан ≈ 0 — вырождение')
            break

        # (г) масштабирование GTIMAS: столбцы на max|J[:,i]|
        sc = np.maximum(np.abs(J).max(axis=0), 1e-300)
        Js = J / sc
        if mode == 'gradient':
            g_vec = Js.T @ r0
            gn = float(np.linalg.norm(g_vec))
            ds = -g_vec / max(gn, 1e-300)
        else:
            # (д) (JᵀJ + λ·diag(JᵀJ))·ΔP = −Jᵀ·оф (Марквардт). Диагональ
            # зазубривается снизу (столбцы уже масштабированы GTIMAS,
            # единица шкалы = max|J[:,i]|): без пола нулевые направления
            # недоопределённой задачи (M < N) усиливают шум округления и
            # «съедают» лимитер шага.
            A = Js.T @ Js
            diag = np.maximum(np.diag(A).copy(), 1e-6)
            A = A + lam * np.diag(diag)
            try:
                ds = np.linalg.solve(A, -(Js.T @ r0))
            except np.linalg.LinAlgError:
                istop = ISTOP_DEGENERATE
                protocol.append('GTISL: сингулярные нормальные уравнения')
                break
            if not np.all(np.isfinite(ds)):
                istop = ISTOP_DEGENERATE
                break
        # Обратный переход из масштабированных GTIMAS-единиц: Js[:,j] =
        # J[:,j]/sc[j] — якобиан по p̃ = sc·p, значит ΔP = Δp̃/sc
        # (умножение вместо деления искажает направление шага и даёт
        # линейное сползание вместо квадратичной сходимости)
        dx = ds / sc

        # (е) лимитер |ΔPᵢ| ≤ K_LIMIT·DP0ᵢ — направленный: шаг уменьшается
        # целиком (направление LM сохраняется, компоненты не «прилипают»
        # к границе независимо друг от друга)
        lim = K_LIMIT * dp0
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = np.where(np.abs(dx) > 0, lim / np.abs(dx), np.inf)
        scale = float(np.min(ratio))
        if math.isfinite(scale) and scale < 1.0:
            dx = dx * scale

        # (з) линейный поиск: ≤ MAX_BISECTIONS бисекций α; принимаемая
        # точка отражается в границы (штрафы при этом остаются активными)
        alpha = 1.0
        accepted = False
        xt = x
        rt = None
        Ft = math.inf
        for _ in range(MAX_BISECTIONS):
            xt = np.clip(x + alpha * dx, lo, hi)
            rt = res_at(xt)
            Ft = float(rt @ rt) if rt is not None else math.inf
            if Ft < F - 1e-15 * max(1.0, abs(F)):
                accepted = True
                break
            alpha *= 0.5

        nstep += 1
        if accepted:
            F_prev = F
            x, r0, F = xt, rt, Ft
            # (з) λ-адаптация: λ/2 при полном шаге (α = 1); шаг, который
            # пришлось укорачивать бисекциями, — признак переоптимистичной
            # линеаризации → λ растёт (демпфирование Марквардта гасит именно
            # околонулевое направление, раздувающее шаг; иначе сползание
            # λ→0, α→0 и линейная сходимость с фактором ~0.7)
            lam = max(lam * 0.5, 1e-6) if alpha >= 1.0 else lam * 2.0
            rejected = 0
            record(nstep, F, lam)
            protocol.append(
                f'GTISL шаг {nstep}: FMIN= {F:.6g} LAM= {lam:.3g} '
                f'DP= [' + ', '.join(f'{d:+.3g}' for d in dx) + ']')
            if abs(F_prev - F) < tol * max(1.0, abs(F)):
                stagnation += 1
                if stagnation >= 2:
                    istop = ISTOP_NO_IMPROVE
                    break
            else:
                stagnation = 0
        else:
            lam *= 3.0
            rejected += 1
            record(nstep, F, lam)
            protocol.append(f'GTISL шаг {nstep}: отклонён, LAM= {lam:.3g}')
            if rejected >= 2:
                istop = ISTOP_NO_IMPROVE
                break
        if callback is not None:
            callback(nstep, F, x.tolist())

    return _finish(work, variables, free, base, x, istop, F, r0=r0,
                   goals=goals_r, history=history, protocol=protocol)


def _finish(work: OpticalSystem, variables: Sequence[OptVariable],
            free: Sequence[int], base: Sequence[float], x: np.ndarray,
            istop: int, F: float, *, r0: Optional[np.ndarray],
            goals: Sequence[OptGoal],
            history: List[dict], protocol: List[str],
            note: str = '') -> OptResult:
    """Собрать OptResult: применить лучший x, дописать протокол."""
    _apply_vector(work, variables, free, base, x)
    residuals = ([float(v) for v in r0[:len(goals)]]
                 if r0 is not None else
                 [math.nan] * len(goals))
    fmin = F if math.isfinite(F) else float('inf')
    protocol = list(protocol)
    tail = f'GTISL ВЫХОД: ISTOP= {istop} NSTEP= {len(history) - 1} ' \
           f'FMIN= {fmin:.6g}'
    if note:
        protocol.append(f'GTISL: {note}')
    protocol.append(tail)
    msg = ISTOP_MESSAGES.get(istop, '')
    if note:
        msg = f'{msg}: {note}' if msg else note
    return OptResult(system=work, converged=(istop == ISTOP_TOLERANCES),
                     istop=istop, nstep=max(0, len(history) - 1),
                     fmin=fmin, residuals=residuals, history=history,
                     protocol=protocol, message=msg)


# --------------------------------------------------------------------------- #
# Solve-режим 1×1 (замена бисекции fit_*, REVERSE_LAP §9.4)
# --------------------------------------------------------------------------- #

#: Порог пробы чувствительности |dF/dP| (закрывает отказ «не влияет»).
SENSITIVITY_EPS = 1e-9


def solve_single(system: OpticalSystem, kind: str, target: float,
                 surface_idx: int, param: str, *,
                 tol: float = 1e-6, max_iter: int = 60,
                 pmin: Optional[float] = None,
                 pmax: Optional[float] = None) -> OptResult:
    """Подогнать один параметр под одну цель (Ньютон по чувствительности).

    Чувствительность dF/dP — центральная разность пары P ± h; при
    |dF/dP| < :data:`SENSITIVITY_EPS` — явная ошибка «параметр не влияет
    на целевую характеристику» (толщина до плоскости изображения и f′ и
    т.п.). Границы поиска — pmin/pmax (не эвристика [0.01x..100x]).

    Raises:
        ValueError: цель некорректна / параметр не влияет / цель не
            достигнута (в т.ч. недостижима в границах).
    """
    if not math.isfinite(float(target)):
        raise ValueError(f"Целевое значение некорректно: {target}")
    goal = OptGoal(kind=kind, target=float(target))
    if kind not in GOAL_KINDS:
        raise ValueError(f"Неизвестный вид цели: {kind!r}")
    if param not in PARAM_TYPES:
        raise ValueError(f"Неизвестный тип параметра: {param!r}")
    if not (0 <= surface_idx < len(system.surfaces)):
        raise ValueError(f"Индекс поверхности вне диапазона: {surface_idx}")

    work = copy.deepcopy(system)
    x = get_param(work, surface_idx, param)
    h = max(1e-4, 1e-3 * abs(x))       # шаг центральной разности
    protocol: List[str] = [f'SOLVE: {kind} = {target:.6g}; '
                           f'поверхность {surface_idx + 1}, {param}']

    def f_at(v: float) -> float:
        set_param(work, surface_idx, param, v)
        try:
            F = evaluate_goal(work, goal)
        except _EvalError as e:
            raise ValueError(
                f"Расчёт характеристики «{kind}» не сходится при "
                f"{param} = {v:.6g}: {e}") from e
        if not math.isfinite(F):
            raise ValueError(f"Характеристика «{kind}» выродилась "
                             f"({F}) при {param} = {v:.6g}")
        return F

    F = f_at(x)
    norm = _resolve_norm(goal)
    pinned = 0
    for it in range(1, max_iter + 1):
        if abs(F - target) < tol:
            r = (F - target) / norm
            protocol.append(f'SOLVE ВЫХОД: ISTOP= 0 NSTEP= {it} '
                            f'оф= {r:.3g}')
            return OptResult(system=work, converged=True,
                             istop=ISTOP_TOLERANCES, nstep=it, fmin=r * r,
                             residuals=[r], history=[], protocol=protocol,
                             message=ISTOP_MESSAGES[ISTOP_TOLERANCES])
        # обязательная проба чувствительности (§9.4)
        dF = (f_at(x + h) - f_at(x - h)) / (2.0 * h)
        if abs(dF) < SENSITIVITY_EPS:
            raise ValueError(
                f"Параметр {param} поверхности {surface_idx + 1} не влияет "
                f"на характеристику «{kind}» (|dF/dP| = {abs(dF):.3g}). "
                f"Выберите другой параметр или поверхность.")
        dx = (target - F) / dF
        dx = math.copysign(min(abs(dx), 5.0 * max(1.0, abs(x))), dx)
        xn = x + dx
        if pmin is not None or pmax is not None:
            xc = min(max(xn, pmin if pmin is not None else -math.inf),
                     pmax if pmax is not None else math.inf)
            if abs(xc - xn) > 1e-12:
                pinned += 1
            xn = xc
        x = xn
        F = f_at(x)
        protocol.append(f'SOLVE шаг {it}: {param}= {x:.6g} {kind}= {F:.6g}')
        if pinned >= 3 and abs(F - target) > tol:
            raise ValueError(
                f"Цель {kind} = {target:.6g} недостижима в границах "
                f"[{pmin}, {pmax}]; достигнуто {F:.6g} при {param} = "
                f"{x:.6g}")
    raise ValueError(
        f"Цель {kind} = {target:.6g} не достигнута за {max_iter} итераций "
        f"(достигнуто {F:.6g} при {param} = {x:.6g}). Возможно, цель вне "
        f"физически достижимого диапазона для этого параметра.")


# --------------------------------------------------------------------------- #
# Парсер входного языка OPAL (PAR/EQF/MF + pmin/pmax, OPALANG §3)
# --------------------------------------------------------------------------- #

# Типы параметров: буквы маркировки OPALOPT (табл. 1) → имена порта.
_PAR_LETTERS = {
    'C': 'radius',
    'D': 'thickness',
    'ES': 'conic',
    'SD': 'semi_diameter',
    'N': 'glass_index',
}
# Границы параметров: операторы X< / X> (OPALOPT:323–358). DE</DE> —
# толщины «по краю», AS</AS> — световые высоты (REVERSE_OPTDOC §1.5);
# в модели порта крайняя толщина ≈ осевая (стрелка не вычитается).
_BOUND_LETTERS = dict(_PAR_LETTERS)
_BOUND_LETTERS.update({'DE': 'thickness', 'AS': 'semi_diameter'})

# Марки характеристик → (kind, refs-умолчания). Вычислимое портом
# подмножество полного каталога REVERSE_OPTDOC §1.9 (DSA/DYA/DYM/ZM/ZS/
# AST/DIS/VG0…); CWZ/MTF/DPA и прочее — предупреждение, не ошибка.
_MF_MARKS = {
    'DSA': ('longitudinal', {'zone': 1.0}),
    'DYA': ('transverse', {'zone': 1.0, 'field': 0.0}),
    'DYM': ('transverse', {'zone': 1.0}),          # меридиональное сечение
    'DXS': ('transverse', {'zone': 1.0}),          # сагиттальное сечение
    'DYS': ('transverse', {'zone': 1.0}),
    'DYT': ('transverse', {'zone': 1.0}),          # косое сечение
    'DXT': ('transverse', {'zone': 1.0}),
    'ZM': ('field', {'metric': 'z_m'}),
    'ZS': ('field', {'metric': 'z_s'}),
    'AST': ('field', {'metric': 'astigmatism'}),
    'DIS': ('field', {'metric': 'distortion'}),
    'DIS%': ('field', {'metric': 'distortion'}),
    'DVL': ('field', {'metric': 'distortion'}),
    'DVL%': ('field', {'metric': 'distortion'}),
    'VG0': ('magnification', {}),
    'V0': ('magnification', {}),
}
#: Вес операндов-равенств EQF (мягкие равенства — большим весом,
#: REVERSE_OPTDOC §5.7).
EQF_DEFAULT_WEIGHT = 10.0
#: Допуск EQF в нормах (умолчание VG0 ±2 %, OPALOPT:248–250).
EQF_DEFAULT_TOL = 0.02

_COMMENT_RE = re.compile(r'!.*?!', re.S)
_STMT_RE = re.compile(
    r'^\s*([A-Za-zА-Яа-яЁё][\w#<>\'"]*)\s*(?:\(([^)]*)\))?\s*=\s*(.+?)\s*$')
_MARK_RE = re.compile(r'^(-?)([A-Za-z][A-Za-z0-9%]*)\s*(?:/\s*([^\s,]+))?$')

# Операторы-счётчики (пороги лимитов задачи — порту не нужны).
_COUNTER_OPS = {'NPAR', 'NPFC', 'NOF', 'NMF', 'NINF', 'NEQF',
                'NGP', 'NGB'}
# Операторы лучевой конфигурации → refs['ray'] целей (OPALOPT:1381–1412).
_RAY_OPS = {'RAYA', 'RAYM', 'RAYS', 'RAYT', 'PCA', 'PCM', 'PCS',
            'PCT', 'SECT', 'FRQ', 'NFRQ'}


def _parse_indices(spec):
    """Индекс-список OPALANG §3.2: ``(3,7,9,15-19,*)``; ``*`` → «все» (None)."""
    if spec is None:
        return None
    spec = spec.strip()
    if not spec or spec == '*':
        return None
    out = []
    for item in spec.split(','):
        item = item.strip()
        if not item:
            continue
        if '-' in item[1:]:
            a, b = item.split('-', 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(item))
    return out


def _parse_numbers(rhs):
    """Числовые выражения правой части: список float (допускает ``.05``)."""
    return [float(tok) for tok in rhs.split(',') if tok.strip()]


def _parse_marks(rhs):
    """Правая часть из марок → [(minus, имя, указатель)]; порядок сохранён."""
    out = []
    for item in rhs.split(','):
        item = item.strip()
        if not item:
            continue
        m = _MARK_RE.match(item)
        if m is None:
            raise ValueError(f'марка не разобрана: {item!r}')
        out.append((m.group(1) == '-', m.group(2).upper(), m.group(3)))
    return out


def _broadcast(values, n):
    """Размножение последнего значения до n элементов (OPALANG §3.2)."""
    if not values or n <= 0:
        return []
    if len(values) >= n:
        return list(values[:n])
    return list(values) + [values[-1]] * (n - len(values))


def parse_opt_task(text, num_surfaces=None):
    """Разобрать текст задания оптимизации (входной язык OPAL).

    Поддерживаемые операторы (живые примеры — ``extracted/opal_okb/
    PLIOPT.OPT``, ``FORM.OPT``; грамматика — OPALANG.DOC §3.2):

    - ``PAR(1-3)=C,D/1-9,-C/5;`` — переменные: буквы C/D/ES/SD/N, указатели
      поверхностей ``C/3`` и диапазоны ``D/1-9``, минус-марки — исключение;
      индексы в скобках — номера мест (для pmin/pmax); марка без указателя
      поверхности означает «все поверхности» и раскрывается только при
      заданном ``num_surfaces`` (иначе — предупреждение);
    - ``MF(1-4)=DYA,DYM,…;`` + ``MF#`` (заданные), ``MFW`` (веса), ``MFS``
      (нормы) — цели (вычислимое подмножество марок, остальные — в
      warnings);
    - ``EQF(1)=VG0; EQF#(1)=-50;`` — мягкие равенства: target = текущее
      значение, если EQF# нет (OPALOPT:869), вес :data:`EQF_DEFAULT_WEIGHT`;
    - ``pmin(1-3)=30,-200,2;`` / ``pmax(…)`` — границы по местам PAR;
    - ``D<(1-11)=0.01;`` и родственные ``C< C> D> ES< SD< …`` — границы по
      типу параметра и поверхностям;
    - ``RAYA=2; PCA(1-2)=1.0,0.707; SECT=45;`` — лучевая конфигурация →
      ``refs['ray']`` всех целей;
    - комментарии ``! … !``.

    Args:
        text: текст задания (может содержать переводы строк).
        num_surfaces: число поверхностей системы — для раскрытия марок без
            указателя поверхности (``PAR(*)=C`` → все радиусы).

    Returns:
        (variables, goals, warnings).
    """

    variables = []
    goals = []
    warnings = []
    ray_cfg = {}
    slot_vars = {}    # место PAR → индексы переменных (для pmin/pmax)
    # отложенные операторы значений по местам: (op, indices, values)
    pending = []
    # отложенные границы по типам: (param, surfaces|None, сторона, значения)
    pending_bounds = []

    body = _COMMENT_RE.sub(' ', text)
    for raw_stmt in body.split(';'):
        stmt = raw_stmt.strip()
        if not stmt:
            continue
        m = _STMT_RE.match(stmt)
        if m is None:
            warnings.append(f'оператор не разобран: {stmt!r}')
            continue
        op = m.group(1).upper()
        idx = _parse_indices(m.group(2))
        rhs = m.group(3)

        try:
            if op == 'PAR':
                _parse_par(rhs, idx, num_surfaces, variables, slot_vars,
                           warnings)
            elif op in ('MF', 'OF'):
                _parse_goals(rhs, idx, goals, warnings, eq=False)
            elif op == 'EQF':
                _parse_goals(rhs, idx, goals, warnings, eq=True)
            elif op in ('MF#', 'OF#', 'MFW', 'OFW', 'MFS', 'OFS',
                        'EQF#', 'EQFW', 'EQFS', 'PMIN', 'PMAX'):
                pending.append((op, idx, _parse_numbers(rhs)))
            elif len(op) > 1 and op[-1] in '<>':
                base = op[:-1]
                param = _BOUND_LETTERS.get(base)
                if param is None:
                    warnings.append(f'оператор границ не поддерживается: '
                                    f'{op}')
                else:
                    pending_bounds.append(
                        (param, idx, 'min' if op[-1] == '<' else 'max',
                         _parse_numbers(rhs)))
            elif op in _RAY_OPS:
                vals = _parse_numbers(rhs)
                if vals:
                    ray_cfg[op] = vals[0]
                    if len(vals) > 1:
                        warnings.append(f'{op}: взято первое из {rhs!r}')
            elif op in _COUNTER_OPS:
                pass
            else:
                warnings.append(f'оператор не поддерживается: {op}')
        except ValueError as e:
            warnings.append(str(e))

    _apply_pending(pending, slot_vars, variables, goals)
    _apply_param_bounds(pending_bounds, variables, warnings)
    if ray_cfg:
        goals = [replace(g, refs={**dict(g.refs or {}), 'ray': dict(ray_cfg)})
                 for g in goals]
    return variables, goals, warnings


def _parse_par(rhs, idx, num_surfaces, variables, slot_vars, warnings):
    """PAR: марки параметров → OptVariable; минус-марки исключают."""
    marks = _parse_marks(rhs)
    if not marks:
        return
    slots = idx if idx is not None else list(range(1, len(marks) + 1))
    if len(slots) > len(marks):        # размножение последней марки
        marks = _broadcast(marks, len(slots))

    excluded = set()                   # (param, поверхность 1-based | None)
    for minus, name, ptr in marks:
        param = _PAR_LETTERS.get(name)
        if param is None:
            warnings.append(f'тип параметра не поддерживается: {name}')
            continue
        surfaces = _parse_indices(ptr)
        if minus:
            excluded.update((param, s) for s in
                            (surfaces if surfaces is not None else [None]))

    for slot, (_minus, name, ptr) in zip(slots, marks):
        param = _PAR_LETTERS.get(name)
        if param is None:
            continue
        surfaces = _parse_indices(ptr)
        if surfaces is None:
            if num_surfaces:
                surfaces = list(range(1, num_surfaces + 1))
            else:
                warnings.append(
                    f'марка {name} без указателя поверхности («все '
                    f'поверхности») — задайте num_surfaces для раскрытия')
                continue
        for s in surfaces:
            if (param, s) in excluded:
                continue
            variables.append(OptVariable(surface=s - 1, param=param))
            slot_vars.setdefault(slot, []).append(len(variables) - 1)


def _parse_goals(rhs, idx, goals, warnings, eq):
    """MF/OF (eq=False) и EQF (eq=True): марки характеристик → OptGoal."""
    marks = _parse_marks(rhs)
    if not marks:
        return
    slots = idx if idx is not None else list(range(1, len(marks) + 1))
    if len(slots) > len(marks):
        marks = _broadcast(marks, len(slots))

    for slot, (_minus, name, ptr) in zip(slots, marks):
        kind_refs = _MF_MARKS.get(name)
        if kind_refs is None:
            warnings.append(f'марка не поддерживается портом: {name}')
            continue
        kind, refs = kind_refs
        refs = dict(refs)
        refs['slot'] = slot
        refs['src'] = 'eq' if eq else 'mf'   # пространства мест MF и EQF
        if ptr:
            refs['ptr'] = ptr      # указатели LJIS сохраняются сырыми
        if eq:
            goals.append(OptGoal(kind=kind, target=None,   # сохранить текущее
                                 weight=EQF_DEFAULT_WEIGHT,
                                 tol=EQF_DEFAULT_TOL, refs=refs))
        else:
            goals.append(OptGoal(kind=kind, target=0.0, refs=refs))


def _apply_pending(pending, slot_vars, variables, goals):
    """Применить отложенные MF#/MFW/MFS/EQF#/pmin/pmax по местам.

    Места MF и EQF — независимые пространства (MF#(1) и EQF#(1) задают
    разные цели), pmin/pmax — по местам PAR.
    """
    by_slot = {}
    for op, idx, vals in pending:
        group = 'eq' if op.startswith('EQF') else 'mf'
        slots = idx if idx is not None else []
        for slot, val in zip(slots, _broadcast(vals, len(slots))):
            by_slot[(group, op, slot)] = val

    for g in goals:
        refs = g.refs or {}
        slot = refs.get('slot')
        group = refs.get('src')
        if slot is None or group is None:
            continue
        for op, attr in (('MF#', 'target'), ('OF#', 'target'),
                         ('EQF#', 'target'), ('MFW', 'weight'),
                         ('OFW', 'weight'), ('EQFW', 'weight'),
                         ('MFS', 'norm'), ('OFS', 'norm'),
                         ('EQFS', 'norm')):
            op_group = 'eq' if op.startswith('EQF') else 'mf'
            if op_group != group:
                continue        # места MF и EQF — разные пространства
            key = (op_group, op, slot)
            if key in by_slot:
                setattr(g, attr, by_slot[key])

    for op, idx, vals in pending:
        if op not in ('PMIN', 'PMAX'):
            continue
        slots = idx if idx is not None else sorted(slot_vars)
        for slot, val in zip(slots, _broadcast(vals, len(slots))):
            for vi in slot_vars.get(slot, ()):
                v = variables[vi]
                if op == 'PMIN':
                    v.pmin = val if v.pmin is None else max(v.pmin, val)
                else:
                    v.pmax = val if v.pmax is None else min(v.pmax, val)


def _apply_param_bounds(pending_bounds, variables, warnings):
    """Границы по операторам типов: ``D<(1-11)=0.01`` → pmin толщин 1..11."""
    for param, surfaces, side, vals in pending_bounds:
        if not vals:
            continue
        if surfaces is None:
            warnings.append(f'границы {param} без списка поверхностей — '
                            f'пропущены')
            continue
        values = _broadcast(vals, len(surfaces))
        for s, val in zip(surfaces, values):
            for v in variables:
                if v.param != param or (v.surface + 1) != s:
                    continue
                if side == 'min':
                    v.pmin = val if v.pmin is None else max(v.pmin, val)
                else:
                    v.pmax = val if v.pmax is None else min(v.pmax, val)


def parse_opt_file(path, num_surfaces=None):
    """Прочитать файл задания оптимизации (формат OPAL: PAR/EQF/MF).

    Кодировка — UTF-8, при неудаче CP866 (оригинальные файлы пакета).
    Возвращает ``(variables, goals)``; неподдерживаемые марки/операторы —
    предупреждения в лог (:data:`_log`), разбор не прерывают (живые файлы
    содержат марки вне вычислимого подмножества порта).

    Args:
        path: путь к файлу задания (PLIOPT.OPT, FORM.OPT, …).
        num_surfaces: число поверхностей системы — для раскрытия марок без
            указателя поверхности (``PAR(*)=C`` → все радиусы).

    Raises:
        OSError: файл не читается.
    """
    p = Path(path)
    raw = p.read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('cp866', errors='replace')
    variables, goals, warnings = parse_opt_task(text, num_surfaces)
    for w in warnings:
        _log.warning('parse_opt_file(%s): %s', p.name, w)
    return variables, goals
