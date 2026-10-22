"""
OPAL-OKB — Команды Волны 3, домен «Оптимизация и визуализация»:
``opt.*`` (решатель ЛАП + legacy-RMS), ``plot.*`` (headless-графики PNG),
``diagram.*`` (карта стёкол n–V).

Оборачиваются только вычислители без Qt:

- ``opt.*`` — analysis/optimization.py (ЛАП: OptVariable/OptGoal/optimize/
  solve_single/parse_opt_task) и legacy optimizer.py (DLS/Simplex по RMS);
- ``plot.*`` — данные analysis/aberrations (пятно, веер, поле, фокус,
  топограмма) и analysis/psf_mtf (ФРТ/ОПФ/ФКЭ); рендер — matplotlib
  backend Agg, окно не показывается, файл пишется в ``output`` (PNG);
- ``diagram.*`` — glass_catalog.GLASS_CATALOG + чистые хелперы
  glass_diagram (цвет/тип по марке); рендер — Agg.

Пропущено (жёсткая привязка к Qt, см. отчёт Волны 3): visualization.py
(виджет OpticalSystemView — QPainter/paintEvent), visualization3d.py
(QOpenGLWidget + PyOpenGL), glass_diagram.plot_glass_diagram/GlassDiagramWindow
(Qt5Agg) — команда diagram.render воспроизводит карту стёкол headless на
тех же данных/цветах.
"""
import os

from commands.base import (
    ERR_BAD_REQUEST,
    ERR_INVALID_PARAM,
    ERR_IO_ERROR,
    ERR_UNSUPPORTED,
    CommandError,
    Param,
)
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    save_system,
    system_source_params,
)

# ============================================================
# Константы рендера (общие для plot.*/diagram.*)
# ============================================================

#: Backend matplotlib для headless-рендера (без окон и без Qt).
PNG_BACKEND = "Agg"
PNG_DPI = 120
#: Размеры фигур, дюймы: двухпанельные и одиночные графики.
FIGSIZE_WIDE = (10.0, 5.0)
FIGSIZE_SQUARE = (7.0, 6.0)

#: Конвенции карты стёкол — как в glass_diagram.plot_glass_diagram.
DIAGRAM_FIGSIZE = (10.0, 7.0)
DIAGRAM_XLIM = (20.0, 80.0)
DIAGRAM_YLIM = (1.45, 1.85)

#: Параметры вывода оптимизированной системы (как system.new).
_RESULT_OUTPUT_PARAMS = [
    Param("name", help="сохранить результат в контекст REPL под именем"),
    Param("save", help="записать результат в файл (.opj/.json)"),
]


# ============================================================
# Хелперы: headless-рендер PNG
# ============================================================

def _pyplot():
    """matplotlib.pyplot с backend Agg (headless, без Qt).

    Вызывается внутри обработчиков: импорт тяжёлый, а backend нужно
    выставить до первого pyplot в процессе.
    """
    import matplotlib
    matplotlib.use(PNG_BACKEND, force=True)
    import matplotlib.pyplot as plt
    return plt


def _save_png(fig, output: str) -> dict:
    """Сохранить фигуру в PNG и закрыть её; метаданные файла для ответа."""
    if not output:
        raise CommandError(ERR_INVALID_PARAM,
                           "output: путь к PNG-файлу обязателен")
    try:
        fig.savefig(output, dpi=PNG_DPI, bbox_inches="tight")
    except OSError as exc:
        raise CommandError(ERR_IO_ERROR,
                           f"не удалось записать {output!r}: {exc}") from exc
    finally:
        import matplotlib.pyplot as plt
        plt.close(fig)
    return {"output": os.path.abspath(output),
            "size_bytes": os.path.getsize(output)}


def _wl_effective(system, wl):
    """λ команды (None → основная λ системы), как analyze.* Волны 1."""
    if wl is not None:
        return float(wl)
    from optics_utils import get_primary_wl
    return get_primary_wl(system)


# ============================================================
# Хелперы: разбор спецификаций переменных/целей (JSON → объекты ЛАП)
# ============================================================

def _opt_float(value):
    """Число из JSON или None (границы/норма не заданы)."""
    return None if value is None else float(value)


def _spec_error(message: str) -> CommandError:
    """Ошибка спецификации переменной/цели — invalid_param."""
    return CommandError(ERR_INVALID_PARAM, message)


def _parse_lap_variables(spec, num_surfaces: int) -> list:
    """Список dict → [OptVariable] (ЛАП-решатель).

    Формат элемента: ``{"surface": 0, "param": "radius", "pmin": 40,
    "pmax": 200, "dp0": 1.0, "link": [1, "radius", -1.0]}`` (surface —
    0-based, как в system.surface.*).
    """
    from analysis.optimization import PARAM_TYPES, OptVariable
    if not isinstance(spec, list) or not spec:
        raise _spec_error(
            "variables — непустой список объектов "
            "{surface, param, pmin, pmax, dp0, link}")
    out = []
    for i, item in enumerate(spec):
        if not isinstance(item, dict):
            raise _spec_error(f"variables[{i}]: ожидается объект, "
                              f"получено {type(item).__name__}")
        if "surface" not in item:
            raise _spec_error(f"variables[{i}]: обязательное поле surface")
        try:
            surface = int(item["surface"])
        except (TypeError, ValueError) as exc:
            raise _spec_error(f"variables[{i}].surface: {item['surface']!r} "
                              f"не целое ({exc})") from exc
        param = str(item.get("param", "radius"))
        if param not in PARAM_TYPES:
            raise _spec_error(
                f"variables[{i}].param={param!r}: допустимо "
                f"{list(PARAM_TYPES)}")
        if not 0 <= surface < num_surfaces:
            raise _spec_error(
                f"variables[{i}].surface={surface} вне диапазона "
                f"0..{num_surfaces - 1}")
        link = item.get("link")
        if link is not None:
            if not isinstance(link, (list, tuple)) or len(link) != 3:
                raise _spec_error(
                    f"variables[{i}].link: тройка "
                    "[surface, param, коэффициент]")
            link = (int(link[0]), str(link[1]), float(link[2]))
        out.append(OptVariable(
            surface=surface, param=param,
            pmin=_opt_float(item.get("pmin")),
            pmax=_opt_float(item.get("pmax")),
            dp0=_opt_float(item.get("dp0")), link=link))
    return out


def _parse_goals(spec) -> list:
    """Список dict → [OptGoal].

    Формат элемента: ``{"kind": "efl", "target": 100.0, "weight": 1.0,
    "norm": 1.0, "tol": 1e-4, "refs": {"zone": 0.7, "field": 3.0}}``.
    """
    from analysis.optimization import GOAL_KINDS, OptGoal
    if not isinstance(spec, list) or not spec:
        raise _spec_error(
            "goals — непустой список объектов {kind, target, weight, "
            "norm, tol, refs}")
    out = []
    for i, item in enumerate(spec):
        if not isinstance(item, dict):
            raise _spec_error(f"goals[{i}]: ожидается объект, получено "
                              f"{type(item).__name__}")
        kind = str(item.get("kind", ""))
        if kind not in GOAL_KINDS:
            raise _spec_error(f"goals[{i}].kind={kind!r}: допустимо "
                              f"{sorted(GOAL_KINDS)}")
        refs = item.get("refs") or {}
        if not isinstance(refs, dict):
            raise _spec_error(f"goals[{i}].refs: ожидается объект")
        try:
            weight = float(item.get("weight", 1.0))
            tol = float(item.get("tol", 1e-4))
        except (TypeError, ValueError) as exc:
            raise _spec_error(f"goals[{i}]: weight/tol не число ({exc})")
        target = item.get("target", 0.0)
        if target is not None:
            try:
                target = float(target)
            except (TypeError, ValueError) as exc:
                raise _spec_error(f"goals[{i}].target: {target!r} не число "
                                  f"({exc})") from exc
        out.append(OptGoal(kind=kind, target=target, weight=weight,
                           norm=_opt_float(item.get("norm")), tol=tol,
                           refs=dict(refs)))
    return out


def _variable_to_dict(variable) -> dict:
    """OptVariable → JSON-словарь (link — списком)."""
    link = (list(variable.link) if variable.link is not None else None)
    return {"surface": variable.surface, "param": variable.param,
            "pmin": variable.pmin, "pmax": variable.pmax,
            "dp0": variable.dp0, "link": link}


def _goal_to_dict(goal) -> dict:
    """OptGoal → JSON-словарь."""
    return {"kind": goal.kind, "target": goal.target, "weight": goal.weight,
            "norm": goal.norm, "tol": goal.tol, "refs": dict(goal.refs or {})}


def _store_system(ctx, system, name, save, result: dict) -> None:
    """Результат-систему — в контекст (name) и/или файл (save)."""
    if name:
        ctx.put_system(name, system)
        result["system"] = name
    if save:
        result["saved"] = save_system(system, save)


def _protocol_tail(protocol, lines: int = 3) -> list:
    """Последние строки протокола ЛАП для ответа."""
    return list(protocol[-lines:])


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать все команды opt.*/plot.*/diagram.*."""

    # ----------------------------------------------------------
    # opt.* — решатель ЛАП (analysis/optimization.py)
    # ----------------------------------------------------------

    @registry.command(
        "opt.goals", category="opt",
        description="Справочник критериев оптимизации ЛАП: виды целей, "
                    "нормы, типы параметров, коды останова",
        returns="kinds/param_types/istop — константы решателя",
        params=[])
    def opt_goals(ctx):
        from analysis.optimization import (
            DEFAULT_NORMS,
            GOAL_KINDS,
            ISTOP_MESSAGES,
            PARAM_TYPES,
        )
        return {
            "kinds": sorted(GOAL_KINDS),
            "default_norms": dict(DEFAULT_NORMS),
            "param_types": list(PARAM_TYPES),
            "istop": {str(code): msg
                      for code, msg in ISTOP_MESSAGES.items()},
        }

    @registry.command(
        "opt.variables", category="opt",
        description="Варьируемые параметры системы: текущие значения "
                    "radius/thickness/conic/semi_diameter/glass_index",
        returns="список {surface, param, value} по всем поверхностям",
        params=system_source_params())
    def opt_variables(ctx, file, system, lbo_index, lbo_name):
        from analysis.optimization import PARAM_TYPES, get_param
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        variables = [{"surface": i, "param": param,
                      "value": get_param(sys_obj, i, param)}
                     for i in range(sys_obj.num_surfaces)
                     for param in PARAM_TYPES]
        return {"num_surfaces": sys_obj.num_surfaces,
                "param_types": list(PARAM_TYPES),
                "variables": variables}

    @registry.command(
        "opt.merit", category="opt",
        description="Оценить цели на системе без оптимизации: значения "
                    "характеристик и остатки оф(I) = (офт−офз)/офн×офв",
        returns="values/residuals по целям + критерий F",
        params=system_source_params([
            Param("goals", type="list", required=True,
                  help="список целей {kind, target, weight, norm, refs} "
                       "(формат — opt.goals)"),
        ]))
    def opt_merit(ctx, file, system, lbo_index, lbo_name, goals):
        from analysis.optimization import evaluate_goal, merit_vector
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        goal_objs = _parse_goals(goals)
        values = [evaluate_goal(sys_obj, g) for g in goal_objs]
        out = {"goals": [_goal_to_dict(g) for g in goal_objs],
               "values": values}
        if all(g.target is not None for g in goal_objs):
            residuals = merit_vector(sys_obj, goal_objs)
            out["residuals"] = residuals
            out["F"] = sum(r * r for r in residuals)
        return out

    @registry.command(
        "opt.run", category="opt",
        description="Многоцелевая оптимизация ЛАП (аналог OPALLAP): "
                    "N целей × M переменных, шаг Марквардта, границы-штрафы",
        returns="istop/fmin/остатки + новые значения переменных "
                "(+system/saved при name/save)",
        params=system_source_params([
            Param("variables", type="list", required=True,
                  help="[{surface, param, pmin, pmax, dp0, link}, ...]"),
            Param("goals", type="list", required=True,
                  help="[{kind, target, weight, norm, tol, refs}, ...]"),
            Param("mode", choices=["linear", "gradient"], default="linear",
                  help="linear — нормальные уравнения Марквардта, "
                       "gradient — наискорейший спуск"),
            Param("max_iter", type="int", default=50,
                  help="максимум итераций NSTEP"),
            Param("num_rays", type="int", default=20,
                  help="лучей веера для трассируемых целей"),
            Param("include_history", type="bool", default=False,
                  help="полная история итераций (nstep/fmin/x/λ)"),
        ] + _RESULT_OUTPUT_PARAMS))
    def opt_run(ctx, file, system, lbo_index, lbo_name, variables, goals,
                mode, max_iter, num_rays, include_history, name, save):
        from analysis.optimization import get_param, optimize
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        var_objs = _parse_lap_variables(variables, sys_obj.num_surfaces)
        goal_objs = _parse_goals(goals)
        before = {id(v): get_param(sys_obj, v.surface, v.param)
                  for v in var_objs}
        res = optimize(sys_obj, var_objs, goal_objs, mode=mode,
                       max_iter=max_iter, num_rays=num_rays)
        out = {
            "istop": res.istop,
            "message": res.message,
            "converged": res.converged,
            "nstep": res.nstep,
            "fmin": res.fmin,
            "residuals": res.residuals,
            "variables": [
                {"surface": v.surface, "param": v.param,
                 "from": before[id(v)],
                 "to": get_param(res.system, v.surface, v.param),
                 "pmin": v.pmin, "pmax": v.pmax}
                for v in var_objs],
            "fmin_curve": [h["fmin"] for h in res.history],
            "protocol_tail": _protocol_tail(res.protocol),
        }
        if include_history:
            out["history"] = res.history
        _store_system(ctx, res.system, name, save, out)
        return out

    @registry.command(
        "opt.solve", category="opt",
        description="Подогнать один параметр под одну цель (Ньютон по "
                    "чувствительности; цели — efl/bfd/аберрации/RMS)",
        returns="значение параметра + достигнутое значение характеристики",
        params=system_source_params([
            Param("kind", required=True,
                  help="вид цели (opt.goals), например efl/bfd/rms_spot"),
            Param("target", type="float", required=True,
                  help="целевое значение характеристики"),
            Param("surface", type="int", required=True,
                  help="индекс поверхности (0-based)"),
            Param("param", default="radius",
                  help="тип параметра (radius/thickness/conic/...)"),
            Param("pmin", type="float", help="нижняя граница поиска"),
            Param("pmax", type="float", help="верхняя граница поиска"),
            Param("tol", type="float", default=1e-6,
                  help="допуск на характеристику"),
            Param("max_iter", type="int", default=60,
                  help="максимум итераций"),
        ] + _RESULT_OUTPUT_PARAMS))
    def opt_solve(ctx, file, system, lbo_index, lbo_name, kind, target,
                  surface, param, pmin, pmax, tol, max_iter, name, save):
        from analysis.optimization import (
            GOAL_KINDS,
            PARAM_TYPES,
            OptGoal,
            evaluate_goal,
            get_param,
            solve_single,
        )
        if kind not in GOAL_KINDS:
            raise _spec_error(f"kind={kind!r}: допустимо {sorted(GOAL_KINDS)}")
        if param not in PARAM_TYPES:
            raise _spec_error(f"param={param!r}: допустимо "
                              f"{list(PARAM_TYPES)}")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if not 0 <= surface < sys_obj.num_surfaces:
            raise _spec_error(f"surface={surface} вне диапазона "
                              f"0..{sys_obj.num_surfaces - 1}")
        res = solve_single(sys_obj, kind, target, surface, param,
                           tol=tol, max_iter=max_iter, pmin=pmin, pmax=pmax)
        achieved = evaluate_goal(res.system, OptGoal(kind=kind))
        out = {
            "kind": kind,
            "target": target,
            "achieved": achieved,
            "surface": surface,
            "param": param,
            "value": get_param(res.system, surface, param),
            "nstep": res.nstep,
            "protocol_tail": _protocol_tail(res.protocol),
        }
        _store_system(ctx, res.system, name, save, out)
        return out

    @registry.command(
        "opt.parse", category="opt",
        description="Разобрать задание оптимизации во входном языке OPAL "
                    "(PAR/MF/EQF + pmin/pmax, формат OPALANG §3)",
        returns="variables/goals/warnings — готовые spec для opt.run",
        params=system_source_params([
            Param("task",
                  help="текст задания (например 'PAR(1)=C/1,D/1; MF(1)=DSA;')"),
            Param("task_file", help="путь к файлу задания (.OPT)"),
        ]))
    def opt_parse(ctx, file, system, lbo_index, lbo_name, task, task_file):
        if not task and not task_file:
            raise CommandError(ERR_BAD_REQUEST,
                               "задайте task (текст) или task_file (путь)")
        sys_obj = (resolve_system(ctx, file, system, lbo_index, lbo_name)
                   if (file or system or ctx.current is not None) else None)
        num_surfaces = sys_obj.num_surfaces if sys_obj is not None else None
        warnings_out = []
        if task_file:
            # parse_opt_file отдаёт предупреждения в лог, а не возвращением —
            # собираем записи логгера, чтобы файл-режим не молчал ярче текста.
            import logging

            from analysis.optimization import parse_opt_file

            class _Collector(logging.Handler):
                def emit(self, record):
                    warnings_out.append(record.getMessage())

            module_log = logging.getLogger("analysis.optimization")
            collector = _Collector(level=logging.WARNING)
            module_log.addHandler(collector)
            try:
                variables, goals = parse_opt_file(
                    task_file, num_surfaces=num_surfaces)
            finally:
                module_log.removeHandler(collector)
        else:
            from analysis.optimization import parse_opt_task
            variables, goals, warnings_out = parse_opt_task(
                task, num_surfaces=num_surfaces)
        return {
            "num_surfaces": num_surfaces,
            "variables": [_variable_to_dict(v) for v in variables],
            "goals": [_goal_to_dict(g) for g in goals],
            "warnings": warnings_out,
        }

    # ----------------------------------------------------------
    # opt.* — legacy optimizer.py (DLS / Nelder-Mead по RMS пятна)
    # ----------------------------------------------------------

    @registry.command(
        "opt.rms", category="opt",
        description="Legacy-оптимизация по RMS пятна рассеяния: DLS "
                    "(демпфированные НК) или Nelder-Mead Simplex",
        returns="мерит RMS до/после + новые значения переменных "
                "(+system/saved при name/save)",
        params=system_source_params([
            Param("variables", type="list", required=True,
                  help="[{surface, param, min, max}, ...] — param только "
                       "radius/thickness"),
            Param("method", choices=["dls", "simplex"], default="dls",
                  help="метод оптимизации"),
            Param("max_iter", type="int", default=50,
                  help="максимум итераций"),
            Param("num_rays", type="int", default=30,
                  help="лучей на сторону для spot diagram"),
        ] + _RESULT_OUTPUT_PARAMS))
    def opt_rms(ctx, file, system, lbo_index, lbo_name, variables, method,
                max_iter, num_rays, name, save):
        import optimizer
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        var_tuples = _parse_legacy_variables(variables,
                                             sys_obj.num_surfaces)
        history = []
        result = optimizer.optimize(
            sys_obj, var_tuples, method=method, max_iter=max_iter,
            num_rays=num_rays,
            callback=lambda it, merit, x: history.append(
                {"iteration": it, "merit": merit}))
        out = {
            "method": method,
            "merit_initial": history[0]["merit"] if history else None,
            "merit_final": (history[-1]["merit"] if history else None),
            "iterations": len(history) - 1 if history else 0,
            "variables": [
                {"surface": s_idx, "param": p_type,
                 "from": _legacy_get(sys_obj, s_idx, p_type),
                 "to": _legacy_get(result, s_idx, p_type),
                 "min": vmin, "max": vmax}
                for s_idx, p_type, vmin, vmax in var_tuples],
        }
        _store_system(ctx, result, name, save, out)
        return out

    def _parse_legacy_variables(spec, num_surfaces: int) -> list:
        """Список dict → кортежи legacy-оптимизатора (radius/thickness)."""
        if not isinstance(spec, list) or not spec:
            raise _spec_error(
                "variables — непустой список объектов "
                "{surface, param, min, max}")
        out = []
        for i, item in enumerate(spec):
            if not isinstance(item, dict):
                raise _spec_error(f"variables[{i}]: ожидается объект")
            try:
                surface = int(item["surface"])
                p_type = str(item.get("param", "radius"))
                vmin = float(item["min"])
                vmax = float(item["max"])
            except KeyError as exc:
                raise _spec_error(
                    f"variables[{i}]: обязательное поле {exc} отсутствует")
            except (TypeError, ValueError) as exc:
                raise _spec_error(f"variables[{i}]: {exc}") from exc
            if p_type not in ("radius", "thickness"):
                raise _spec_error(
                    f"variables[{i}].param={p_type!r}: legacy-движок "
                    f"умеет только radius/thickness")
            if not 0 <= surface < num_surfaces:
                raise _spec_error(f"variables[{i}].surface={surface} вне "
                                  f"диапазона 0..{num_surfaces - 1}")
            if vmin > vmax:
                raise _spec_error(f"variables[{i}]: min > max")
            out.append((surface, p_type, vmin, vmax))
        return out

    def _legacy_get(system, surface_idx: int, param_type: str) -> float:
        """Текущее значение переменной legacy-оптимизатора."""
        surface = system.surfaces[surface_idx]
        return float(getattr(surface, param_type))

    # ----------------------------------------------------------
    # plot.* — headless-графики (Agg → PNG)
    # ----------------------------------------------------------

    @registry.command(
        "plot.spot", category="plot",
        description="Точечная диаграмма пятна рассеяния (PNG): точки + "
                    "окружность RMS",
        returns="{output, size_bytes, num_points, rms}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("num_rays", type="int", default=50,
                  help="лучей по стороне сетки / колец гексаполярной сетки"),
            Param("sampling", choices=["grid", "hexapolar"], default="grid",
                  help="способ выборки зрачка"),
        ]))
    def plot_spot(ctx, file, system, lbo_index, lbo_name, output, wl,
                  field_y, num_rays, sampling):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        spots = compute_spot_diagram(sys_obj, wl=wl_eff, num_rays=num_rays,
                                     field_y=field_y, sampling=sampling)
        if not spots:
            raise CommandError(ERR_UNSUPPORTED,
                               "трассировка не дала точек пятна")
        rms = compute_rms_spot(spots)
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.plot([p[0] for p in spots], [p[1] for p in spots], ".",
                color="#1f77b4", markersize=4)
        ax.add_patch(plt.Circle((0.0, 0.0), rms, fill=False,
                                color="#d62728", linestyle="--",
                                label=f"RMS = {rms:.4f} мм"))
        ax.set_aspect("equal")
        ax.set_xlabel("dx, мм")
        ax.set_ylabel("dy, мм")
        ax.set_title(f"Пятно рассеяния: λ={wl_eff} мкм, поле {field_y}")
        ax.grid(True, alpha=0.3)
        ax.legend()
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y,
                    "num_points": len(spots), "rms": rms})
        return out

    @registry.command(
        "plot.fan", category="plot",
        description="Веер лучей (PNG): поперечная dy и продольная ds "
                    "аберрации против зрачковой координаты",
        returns="{output, size_bytes, num_rays, num_ok}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("num_rays", type="int", default=21,
                  help="лучей в веере"),
        ]))
    def plot_fan(ctx, file, system, lbo_index, lbo_name, output, wl,
                 field_y, num_rays):
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fan = trace_aberration_fan(sys_obj, wl_eff, num_rays=num_rays,
                                   field_y=field_y)
        ok = [row for row in fan if row.get("success")]
        if not ok:
            raise CommandError(ERR_UNSUPPORTED, "веер лучей пуст")
        plt = _pyplot()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        for ax, key, label in ((ax1, "dy", "dy, мм (поперечная)"),
                               (ax2, "ds", "ds, мм (продольная)")):
            xs = [row["pupil_y"] for row in ok]
            ys = [row[key] for row in ok]
            ax.plot(xs, ys, ".-", color="#1f77b4", markersize=4)
            ax.axhline(0.0, color="gray", linewidth=0.8)
            ax.set_xlabel("Зрачковая координата")
            ax.set_ylabel(label)
            ax.grid(True, alpha=0.3)
        fig.suptitle(f"Веер лучей: λ={wl_eff} мкм, поле {field_y}")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y,
                    "num_rays": len(fan), "num_ok": len(ok)})
        return out

    @registry.command(
        "plot.field", category="plot",
        description="Внеосевые аберрации по полю (PNG): астигматизм Z'm/Z's "
                    "и дисторсия",
        returns="{output, size_bytes, fields}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("fields", type="list",
                  help="список полей (град); по умолчанию — поля системы"),
            Param("num_fan_rays", type="int", default=15,
                  help="лучей в веере на поле"),
        ]))
    def plot_field(ctx, file, system, lbo_index, lbo_name, output, wl,
                   fields, num_fan_rays):
        from analysis.aberrations import compute_field_aberrations
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        if fields is None:
            field_points = None           # поля системы
        elif fields:
            field_points = [(float(f),) for f in fields]
        else:
            raise CommandError(ERR_BAD_REQUEST,
                               "fields: список полей пуст (не задан — "
                               "используются поля системы)")
        rows = compute_field_aberrations(
            sys_obj, wl=wl_eff, field_points=field_points,
            num_fan_rays=num_fan_rays)
        if not rows:
            raise CommandError(
                ERR_BAD_REQUEST,
                "нет точек поля: задайте fields или добавьте поля системе "
                "(system.fields.add)")
        xs = [row["field_y"] for row in rows]
        plt = _pyplot()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        ax1.plot(xs, [row["z_m"] for row in rows], ".-",
                 color="#1f77b4", label="Z'm (меридиональная)")
        ax1.plot(xs, [row["z_s"] for row in rows], ".-",
                 color="#d62728", label="Z's (сагиттальная)")
        ax1.set_xlabel("Поле, град")
        ax1.set_ylabel("Z', мм")
        ax1.set_title("Астигматизм / кривизна поля")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax2.plot(xs, [row["distortion"] for row in rows], ".-",
                 color="#2ca02c")
        ax2.axhline(0.0, color="gray", linewidth=0.8)
        ax2.set_xlabel("Поле, град")
        ax2.set_ylabel("Дисторсия, %")
        ax2.set_title("Дисторсия")
        ax2.grid(True, alpha=0.3)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "fields": xs})
        return out

    @registry.command(
        "plot.psf", category="plot",
        description="Функция рассеяния точки (PNG): карта интенсивности "
                    "в плоскости изображения",
        returns="{output, size_bytes, strehl, pitch_um}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def plot_psf(ctx, file, system, lbo_index, lbo_name, output, field_y,
                 wl, defocus):
        from analysis.psf_mtf import psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = psf_grid(sys_obj, field_y=field_y, wl=wl, defocus=defocus)
        psf = res.get("psf")
        if psf is None:
            raise CommandError(ERR_UNSUPPORTED,
                               f"ФРТ не рассчитана: {res.get('reason')}")
        import numpy as np
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        y_um = res["y_um"]
        x_um = res["x_um"]
        extent = (min(x_um), max(x_um), min(y_um), max(y_um))
        im = ax.imshow(psf, extent=extent, origin="lower", cmap="viridis")
        fig.colorbar(im, ax=ax, label="Интенсивность (норм.)")
        ax.set_xlabel("x, мкм")
        ax.set_ylabel("y, мкм")
        ax.set_title(f"ФРТ: поле {field_y}, λ={res.get('wl')} мкм, "
                     f"Штрель={res.get('strehl'):.3f}"
                     if res.get("strehl") is not None else "ФРТ")
        out = _save_png(fig, output)
        out.update({"strehl": res.get("strehl"),
                    "pitch_um": res.get("pitch_um"),
                    "grid": res.get("grid")})
        return out

    @registry.command(
        "plot.mtf", category="plot",
        description="Оптическая передаточная функция (PNG): сечения "
                    "тангенциальное/сагиттальное из ФРТ",
        returns="{output, size_bytes, cutoff_lpmm, nyquist_lpmm}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_mtf(ctx, file, system, lbo_index, lbo_name, output, field_y,
                 wl):
        from analysis.psf_mtf import mtf_from_psf, psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = psf_grid(sys_obj, field_y=field_y, wl=wl)
        psf = res.get("psf")
        if psf is None:
            raise CommandError(ERR_UNSUPPORTED,
                               f"ОПФ не рассчитана: {res.get('reason')}")
        mtf = mtf_from_psf(psf, res["pitch_um"])
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.plot(mtf["freq_lpmm"], mtf["tan"], "-",
                color="#1f77b4", label="Тангенциальное")
        ax.plot(mtf["freq_lpmm"], mtf["sag"], "--",
                color="#d62728", label="Сагиттальное")
        ax.axhline(0.0, color="gray", linewidth=0.8)
        ax.set_xlabel("Пространственная частота, лин/мм")
        ax.set_ylabel("MTF")
        ax.set_title(f"ОПФ: поле {field_y}, λ={res.get('wl')} мкм")
        ax.set_xlim(0.0, float(mtf["nyquist_lpmm"]))
        ax.grid(True, alpha=0.3)
        ax.legend()
        out = _save_png(fig, output)
        out.update({"cutoff_lpmm": res.get("cutoff_lpmm"),
                    "nyquist_lpmm": float(mtf["nyquist_lpmm"])})
        return out

    @registry.command(
        "plot.ee", category="plot",
        description="Функция концентрации энергии (PNG): доля энергии ФРТ "
                    "в круге радиуса r",
        returns="{output, size_bytes, r80_um}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_ee(ctx, file, system, lbo_index, lbo_name, output, field_y,
                wl):
        import numpy as np
        from analysis.psf_mtf import encircled_energy, psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        res = psf_grid(sys_obj, field_y=field_y, wl=wl)
        psf = res.get("psf")
        if psf is None:
            raise CommandError(ERR_UNSUPPORTED,
                               f"ФКЭ не рассчитана: {res.get('reason')}")
        r_um, ee = encircled_energy(psf, res["pitch_um"])
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.plot(r_um, ee, "-", color="#1f77b4")
        ax.axhline(0.8, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Радиус кружка, мкм")
        ax.set_ylabel("Доля энергии")
        ax.set_title(f"ФКЭ: поле {field_y}, λ={res.get('wl')} мкм")
        ax.grid(True, alpha=0.3)
        out = _save_png(fig, output)
        # Радиус, вмещающий 80 % энергии (для контроля качества).
        ee_level = 0.8
        r80 = float(np.interp(ee_level, ee, r_um))
        out.update({"r80_um": r80})
        return out

    @registry.command(
        "plot.focus", category="plot",
        description="Фокусировочная кривая (PNG): MTF на заданной частоте "
                    "против смещения плоскости изображения",
        returns="{output, size_bytes, best_defocus_mm, num_points}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("defocus_range", type="float", default=2.0,
                  help="±мм от лучшей фокальной плоскости"),
            Param("freq_lpmm", type="float", default=50.0,
                  help="частота оценки MTF, лин/мм"),
            Param("num_points", type="int", default=40,
                  help="точек кривой"),
            Param("num_rays", type="int", default=30,
                  help="лучей сетки для оценки пятна"),
        ]))
    def plot_focus(ctx, file, system, lbo_index, lbo_name, output, wl,
                   field_y, defocus_range, freq_lpmm, num_points, num_rays):
        from analysis.aberrations import compute_focus_curve
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        curve = compute_focus_curve(sys_obj, wl=wl_eff,
                                    num_points=num_points,
                                    defocus_range=defocus_range,
                                    freq_lpmm=freq_lpmm,
                                    num_rays=num_rays,
                                    field_y=field_y)
        if not curve:
            raise CommandError(ERR_UNSUPPORTED,
                               "фокусировочная кривая не рассчитана")
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.plot([p[0] for p in curve], [p[1] for p in curve], ".-",
                color="#1f77b4")
        ax.set_xlabel("Дефокусировка, мм")
        ax.set_ylabel(f"MTF @ {freq_lpmm} лин/мм")
        ax.set_title(f"Фокусировочная кривая: λ={wl_eff} мкм, "
                     f"поле {field_y}")
        ax.grid(True, alpha=0.3)
        best = max(curve, key=lambda p: p[1])
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "best_defocus_mm": best[0],
                    "best_mtf": best[1], "num_points": len(curve)})
        return out

    @registry.command(
        "plot.heatmap", category="plot",
        description="Топограмма плотности пятна рассеяния (PNG): "
                    "гистограмма точек в плоскости изображения",
        returns="{output, size_bytes, x_range, y_range}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE)"),
            Param("num_rays", type="int", default=500,
                  help="лучей для гистограммы"),
            Param("grid_size", type="int", default=100,
                  help="сетка гистограммы (N×N)"),
        ]))
    def plot_heatmap(ctx, file, system, lbo_index, lbo_name, output, wl,
                     field_y, num_rays, grid_size):
        from analysis.aberrations import compute_spot_heatmap
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        heatmap, x_range, y_range = compute_spot_heatmap(
            sys_obj, wl=wl_eff, num_rays=num_rays, field_y=field_y,
            grid_size=grid_size)
        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        im = ax.imshow(heatmap, extent=(x_range[0], x_range[1],
                                        y_range[0], y_range[1]),
                       origin="lower", cmap="magma")
        fig.colorbar(im, ax=ax, label="Плотность (норм.)")
        ax.set_xlabel("x, мм")
        ax.set_ylabel("y, мм")
        ax.set_title(f"Топограмма пятна: λ={wl_eff} мкм, поле {field_y}")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "x_range": list(x_range),
                    "y_range": list(y_range)})
        return out

    # ----------------------------------------------------------
    # diagram.* — карта стёкол n–V
    # ----------------------------------------------------------

    @registry.command(
        "diagram.render", category="diagram",
        description="Диаграмма стёкол n–V (PNG): nd против vd по каталогу "
                    "ГОСТ, стекла системы — подсветкой",
        returns="{output, size_bytes, num_glasses, highlighted}",
        params=[
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("highlight", type="list",
                  help="марки стёкол для подсветки (список имён)"),
        ] + system_source_params())
    def diagram_render(ctx, output, highlight, file, system, lbo_index,
                       lbo_name):
        from glass_catalog import GLASS_CATALOG
        from glass_diagram import get_glass_color, get_glass_type_label
        highlighted = list(highlight or [])
        if not highlighted and (file or system or ctx.current is not None):
            sys_obj = resolve_system(ctx, file, system, lbo_index,
                                     lbo_name)
            highlighted = [s.glass for s in sys_obj.surfaces if s.glass]
        highlighted = [h.upper() for h in highlighted]

        types = {}
        num_points = 0
        for name, entry in GLASS_CATALOG.items():
            if name in ("ВОЗДУХ", "AIR"):
                continue
            nd, vd = float(entry[0]), float(entry[1])
            if vd <= 0:
                continue
            label = get_glass_type_label(name)
            bucket = types.setdefault(
                label or "Другие",
                {"x": [], "y": [], "color": get_glass_color(name)})
            bucket["x"].append(vd)
            bucket["y"].append(nd)
            num_points += 1

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=DIAGRAM_FIGSIZE)
        marks = []
        for label, data in sorted(types.items()):
            ax.scatter(data["x"], data["y"], c=data["color"], s=50,
                       alpha=0.7, label=label, edgecolors="gray",
                       linewidths=0.5)
        for name, entry in GLASS_CATALOG.items():
            if name.upper() in highlighted and name not in ("ВОЗДУХ", "AIR"):
                nd, vd = float(entry[0]), float(entry[1])
                if vd <= 0:
                    continue
                ax.plot(vd, nd, "o", color="gold", markersize=14,
                        markeredgecolor="black", markeredgewidth=2,
                        zorder=10)
                ax.annotate(name, (vd, nd), fontsize=9, fontweight="bold",
                            ha="left", va="bottom", xytext=(5, 5),
                            textcoords="offset points")
                marks.append(name)
        ax.set_xlabel("Коэффициент дисперсии $v_d$ (Аббе)")
        ax.set_ylabel("Показатель преломления $n_d$")
        ax.set_title("Диаграмма стёкол (ГОСТ 13658-78)")
        ax.legend(loc="upper right", fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(*DIAGRAM_XLIM)
        ax.set_ylim(*DIAGRAM_YLIM)
        ax.invert_xaxis()  # vd убывает вправо — как в glass_diagram
        out = _save_png(fig, output)
        out.update({"num_glasses": num_points, "highlighted": marks})
        return out

    @registry.command(
        "diagram.glasses", category="diagram",
        description="Данные карты стёкол: марки каталога ГОСТ с nd/vd, "
                    "типом и цветом диаграммы",
        returns="список {name, nd, vd, type, color}",
        params=[
            Param("type",
                  help="фильтр по типу (префикс марки: К, ТФ, БК, ...)"),
        ])
    def diagram_glasses(ctx, type):
        from glass_catalog import GLASS_CATALOG
        from glass_diagram import get_glass_color, get_glass_type_label
        rows = []
        for name, entry in sorted(GLASS_CATALOG.items()):
            if name in ("ВОЗДУХ", "AIR"):
                continue
            nd, vd = float(entry[0]), float(entry[1])
            if vd <= 0:
                continue
            label = get_glass_type_label(name)
            if type and label != type:
                continue
            rows.append({"name": name, "nd": nd, "vd": vd, "type": label,
                         "color": get_glass_color(name)})
        return {"num_glasses": len(rows), "glasses": rows,
                "types": sorted({r["type"] for r in rows})}
