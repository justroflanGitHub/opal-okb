"""
OPAL-OKB — Пакет R500-12: расширенные headless-графики ``plot.*``
(matplotlib backend Agg → PNG), дополнительные к Волне 3 (opt_cmds).

Новые графики (данные — только существующие движки analysis/domain,
новых вычислительных ядер нет; сагитта — общий хелпер calc_ext_cmds):

- ``plot.layout``     — 2D-схема системы: поверхности (дуги по сагиттам),
  стоп, оптическая ось, F′ и меридиональные веера лучей по полям
  (ANALIZE.txt §4.8 «Рисунок оптической системы с трассировкой лучей»);
- ``plot.caustic``    — каустика: выходящие лучи веера за последнюю
  поверхность + ширина пучка RMS(z) (перетяжка/положение фокуса);
- ``plot.vignetting`` — виньетирование по полям: верх/низ (TABBEA §14.1,
  analysis/vignetting.compute_vignetting) + светораспределение
  (compute_light_distribution);
- ``plot.chromatism`` — хроматизм: f′(λ) и осевой Δf′(λ) по сетке λ
  (domain.calculations.paraxial_trace);
- ``plot.wavefront``  — карта волнового фронта на зрачке W(x, y), λ
  (analysis/zernike.compute_wavefront_map_2d);
- ``plot.glassmap``   — стёкла системы на карте nd–vd с ломаной
  «траектории коррекции» (данные — команда diagram.glasses);
- ``plot.seidel``     — бар-чарт сумм Зейделя SI..SV (+ хроматические,
  данные — команда seidel.sums);
- ``plot.fields``     — карта точек поля системы с весами;
- ``plot.mtf.family`` — семейство ЧКХ (танг./саг.) по полям;
- ``plot.ee.family``  — семейство ФКЭ по полям с r₈₀;
- ``plot.spot.grid``  — сетка пятен рассеяния по полям;
- ``plot.fan.fields`` — веера поперечных аберраций dy по полям;
- ``plot.dof``        — глубина фокуса: RMS/геометрический радиус пятна
  против дефокуса с порогом круга нерезкости;
- ``plot.pupil.vign`` — маска зрачка: узлы гексаполярной сетки
  «прошёл/срезан» на поле (данные — команда trace.grid3d);
- ``plot.psf.slice``  — срезы ФРТ через центр (x/y) с FWHM.

Общие конвенции PNG (backend/DPI/сохранение) — opt_cmds._save_png.
"""
import math

from commands.base import (
    ERR_BAD_REQUEST,
    ERR_INVALID_PARAM,
    ERR_UNSUPPORTED,
    CommandError,
    Param,
)
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
)
from optics_utils import get_primary_wl

# Рендер и палитра — общие с Волной 3 (opt_cmds), дублирования нет.
from commands.builtin.opt_cmds import (
    DIAGRAM_FIGSIZE,
    DIAGRAM_XLIM,
    DIAGRAM_YLIM,
    FIGSIZE_SQUARE,
    FIGSIZE_WIDE,
    _pyplot,
    _save_png,
    _wl_effective,
)
# Подписи сумм Зейделя и FWHM-хелпер — общий код R500-7 (sweep).
from commands.builtin.sweep_cmds import SEIDEL_LABELS, _fwhm_um
# Общие хелперы пакетов R500 (правило №1): поля, TINY, сестринские вызовы.
from commands.builtin._r500_common import TINY
from commands.builtin._r500_common import fields_arg as _fields_arg
from commands.builtin._r500_common import run_sibling

#: Служебный префикс имён систем в контексте для композиции сестринских
#: команд (система кладётся под уникальным именем и удаляется после).
_PROBE_PREFIX = "_plotx_"

#: Палитра (как у plot.* Волны 3: цвета табл. matplotlib).
COLOR_MAIN = "#1f77b4"
COLOR_ALT = "#d62728"
COLOR_OK = "#2ca02c"
COLOR_BLOCKED = "#7f7f7f"
COLOR_LENS_FILL = "#a6cee3"
COLOR_MIRROR = "#b8860b"

#: Палитра семейств кривых (по полям; табличный цикл matplotlib).
COLOR_CYCLE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")

# ── plot.layout ────────────────────────────────────────────────────────────

#: Фигура схемы системы, дюймы (широкая — под 2D-разрез с лучами).
LAYOUT_FIGSIZE = (12.5, 6.0)
#: Точек в дуге поверхности.
LAYOUT_ARC_POINTS = 61
#: Лучей в меридиональном веере на поле.
LAYOUT_RAYS_DEFAULT = 7
#: Запас по |y| < |R| при построении дуги (защита дискриминанта сагитты).
ARC_MARGIN = 0.999

# ── plot.caustic ───────────────────────────────────────────────────────────

#: Лучей веера каустики.
CAUSTIC_RAYS_DEFAULT = 15
#: Продление за плоскость изображения, мм.
CAUSTIC_RANGE_DEFAULT = 2.0
#: Точек сетки z для ширины пучка.
CAUSTIC_POINTS_DEFAULT = 60

# ── plot.chromatism ────────────────────────────────────────────────────────

#: Точек сетки λ.
CHROMATISM_STEPS_DEFAULT = 21
#: Расширение диапазона λ за пределы рабочих λ системы (доля диапазона).
CHROMATISM_PAD_FRACTION = 0.1
#: Минимальное расширение, мкм (одна рабочая λ в системе).
CHROMATISM_MIN_PAD_UM = 0.05

# ── plot.wavefront ─────────────────────────────────────────────────────────

#: Решётка карты волнового фронта (N×N).
WAVEFRONT_GRID_DEFAULT = 64

# ── plot.spot.grid / plot.fan.fields ───────────────────────────────────────

#: Лучей на пятно в сетке пятен.
SPOT_GRID_RAYS_DEFAULT = 40
#: Максимум колонок сетки пятен.
SPOT_GRID_MAX_COLS = 3
#: Размер ячейки сетки пятен, дюймы.
SPOT_GRID_CELL = (4.5, 4.2)
#: Лучей в веере на поле.
FAN_FIELDS_RAYS_DEFAULT = 15

# ── plot.dof ───────────────────────────────────────────────────────────────

#: Круг нерезкости по умолчанию, мкм.
DOF_COC_UM_DEFAULT = 20.0
#: ±мм развёртки дефокуса.
DOF_RANGE_DEFAULT = 1.0
#: Точек кривой.
DOF_POINTS_DEFAULT = 21
#: Лучей сетки зрачка на точку.
DOF_RAYS_DEFAULT = 20

# ── plot.pupil.vign ────────────────────────────────────────────────────────

#: Кольца/азимуты гексаполярной сетки зрачка.
PUPIL_RINGS_DEFAULT = 5
PUPIL_AZIMUTHS_DEFAULT = 24

# ── plot.mtf.family / plot.ee.family ───────────────────────────────────────

#: Уровень ФКЭ для метрики r₈₀.
EE_LEVEL = 0.8


# ============================================================
# Хелперы
# ============================================================

def _run_sibling(registry: Registry, ctx, system, tag: str, name: str,
                 args: dict = None) -> dict:
    """Выполнить сестринскую команду с живой системой в контексте
    (движок — _r500_common.run_sibling; служебный ключ ``_plotx_<tag>``)."""
    return run_sibling(registry, ctx, system, _PROBE_PREFIX + tag,
                       name, args)


def _sagitta(surface, height: float) -> float:
    """Сагитта поверхности (сфера/коника) — общий движок calc.sagitta."""
    from commands.builtin.calc_ext_cmds import _sagitta as sag
    return sag(surface.radius, height, surface.conic_constant)


def _surface_sd(surface, default_sd: float) -> float:
    """Полудиаметр поверхности с фолбэком (как visualization.py)."""
    return surface.semi_diameter if surface.semi_diameter > 0.0 else default_sd


def _arc_points(surface, z_vertex: float, default_sd: float,
                num_points: int) -> tuple:
    """Точки дуги поверхности (zs, ys) для 2D-схемы.

    Высота ограничена полудиаметром и |R|·ARC_MARGIN (сагитта определена
    только внутри апертуры кривизны); точки вне — отбрасываются.
    """
    ymax = _surface_sd(surface, default_sd)
    if surface.radius:
        ymax = min(ymax, abs(surface.radius) * ARC_MARGIN)
    if num_points < 2 or ymax <= 0.0:
        return [z_vertex], [0.0]
    ys = [-ymax + 2.0 * ymax * i / (num_points - 1)
          for i in range(num_points)]
    zs, ys_ok = [], []
    for y in ys:
        try:
            sag = _sagitta(surface, y)
        except CommandError:
            continue                      # вне апертуры кривизны
        zs.append(z_vertex + sag)
        ys_ok.append(y)
    return zs, ys_ok


def _exit_line(result) -> tuple:
    """Выходящий участок луча (y0, z0, dy/dz) по последним точкам пути.

    ``None`` — луч не дошёл или вырожден (последний сегмент ∥ оси y).
    """
    if len(result.path) < 2 or result.error == "OBSCURED":
        return None
    p_prev, p_last = result.path[-2], result.path[-1]
    dz = p_last[2] - p_prev[2]
    if abs(dz) < TINY:
        return None
    return (p_last[1], p_last[2], (p_last[1] - p_prev[1]) / dz)


# ============================================================
# Регистрация
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать расширенные plot.* (R500-12)."""

    # ----------------------------------------------------------
    # plot.layout — 2D-схема системы с трассировкой лучей
    # ----------------------------------------------------------

    @registry.command(
        "plot.layout", category="plot",
        description="Схема оптической системы с трассировкой лучей "
                    "(PNG, 2D-разрез): поверхности-дуги, стёкла, стоп, "
                    "ось, F′ и веера лучей по полям (ANALIZE §4.8)",
        returns="{output, size_bytes, num_surfaces, fields, num_rays, "
                "num_ok, focal_z_mm}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("fields", type="list",
                  help="поля вееров, град; по умолчанию — 0 и максимальное "
                       "поле системы"),
            Param("num_rays", type="int", default=LAYOUT_RAYS_DEFAULT,
                  help="лучей в веере на поле"),
        ]))
    def plot_layout(ctx, file, system, lbo_index, lbo_name, output, wl,
                    fields, num_rays):
        from analysis.ray_tracing import trace_fan
        from domain.calculations import paraxial_trace
        from optics_utils import compute_z_positions, get_effective_aperture
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        if not sys_obj.surfaces:
            raise CommandError(ERR_BAD_REQUEST,
                               "в системе нет поверхностей")
        if fields:
            fields_list = [float(f) for f in fields]
        else:
            max_field = max((abs(fp.y) for fp in sys_obj.field_points),
                            default=0.0)
            fields_list = [0.0, max_field] if max_field > 0.0 else [0.0]

        # Данные до создания фигуры (фигура не течёт при отказе).
        z_pos = compute_z_positions(sys_obj)
        parax = paraxial_trace(sys_obj)
        aperture = get_effective_aperture(sys_obj, default=20.0)
        default_sd = aperture / 2.0
        fans = []
        for field in fields_list:
            results = trace_fan(sys_obj, num_rays=num_rays, wl=wl_eff,
                                field_y=field)
            fans.append((field, [r for r in results
                                 if r.error != "OBSCURED" and r.path]))
        num_ok = sum(1 for _, results in fans for r in results
                     if r.success)
        if num_ok == 0:
            raise CommandError(ERR_UNSUPPORTED,
                               "трассировка не дала ни одного луча")

        sfp = parax.get("sF_prime", 0.0)
        focal_z = z_pos[-2] + sfp if sfp else None

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=LAYOUT_FIGSIZE)

        # Стёкла: заливка между последовательными дугами (среда после
        # поверхности i — стекло до вершины i+1).
        for i, surf in enumerate(sys_obj.surfaces[:-1]):
            if not surf.glass or surf.glass.upper() in ("ВОЗДУХ", "AIR"):
                continue
            next_surf = sys_obj.surfaces[i + 1]
            ymax = min(_surface_sd(surf, default_sd),
                       _surface_sd(next_surf, default_sd))
            if surf.radius:
                ymax = min(ymax, abs(surf.radius) * ARC_MARGIN)
            if next_surf.radius:
                ymax = min(ymax, abs(next_surf.radius) * ARC_MARGIN)
            ys = [-ymax + 2.0 * ymax * j / (LAYOUT_ARC_POINTS - 1)
                  for j in range(LAYOUT_ARC_POINTS)]
            zs_a, zs_b, ys_ok = [], [], []
            for y in ys:
                try:
                    za = z_pos[i] + _sagitta(surf, y)
                    zb = z_pos[i + 1] + _sagitta(next_surf, y)
                except CommandError:
                    continue
                zs_a.append(za)
                zs_b.append(zb)
                ys_ok.append(y)
            if ys_ok:
                ax.fill_betweenx(ys_ok, zs_a, zs_b, color=COLOR_LENS_FILL,
                                 alpha=0.35, linewidth=0)

        # Контуры поверхностей (зеркала — толстой линией).
        for i, surf in enumerate(sys_obj.surfaces):
            zs, ys = _arc_points(surf, z_pos[i], default_sd,
                                 LAYOUT_ARC_POINTS)
            if surf.is_reflective:
                ax.plot(zs, ys, color=COLOR_MIRROR, linewidth=2.5)
            elif surf.glass and surf.glass.upper() not in ("ВОЗДУХ", "AIR"):
                ax.plot(zs, ys, color="#3182bd", linewidth=1.5)
            else:
                ax.plot(zs, ys, color="#606070", linewidth=1.2)

        # Плоскость изображения.
        ax.axvline(z_pos[-1], color="gray", linewidth=0.8, linestyle=":")

        # Апертурная диафрагма (1-индексация, как в системе).
        stop_idx = sys_obj.stop_surface - 1
        if 0 <= stop_idx < len(sys_obj.surfaces):
            z_stop = z_pos[stop_idx] + sys_obj.stop_offset
            ax.plot([z_stop, z_stop], [aperture / 2.0, -aperture / 2.0],
                    color=COLOR_ALT, linewidth=1.2, linestyle="--",
                    label="апертурная диафрагма")

        # Оптическая ось.
        ax.axhline(0.0, color="black", linewidth=0.8)

        # Веера лучей: осевой — синим, полевые — зелёным; срезанные —
        # серым (до точки среза видно, где пучок виньетируется).
        labeled = {"axial": False, "field": False, "blocked": False}
        for field, results in fans:
            color = COLOR_MAIN if field == 0.0 else COLOR_OK
            for r in results:
                zs = [p[2] for p in r.path]
                ys = [p[1] for p in r.path]
                if r.success:
                    key = "axial" if field == 0.0 else "field"
                    label = (f"{'осевой' if key == 'axial' else 'полевой'}"
                             f" пучок") if not labeled[key] else None
                    labeled[key] = True
                    ax.plot(zs, ys, color=color, linewidth=0.8, alpha=0.85,
                            label=label)
                else:
                    label = ("срезанные лучи"
                             if not labeled["blocked"] else None)
                    labeled["blocked"] = True
                    ax.plot(zs, ys, color=COLOR_BLOCKED, linewidth=0.6,
                            alpha=0.5, label=label)

        # Задний фокус F′.
        if focal_z is not None:
            ax.axvline(focal_z, color=COLOR_ALT, linewidth=1.0,
                       linestyle="--", alpha=0.8)
            ax.annotate("F'", xy=(focal_z, 0.0), xytext=(focal_z,
                                                         aperture * 0.55),
                        color=COLOR_ALT, ha="center", fontsize=10)

        # Границы по данным (лучи стартуют до первой поверхности).
        z_min = min([p[2] for _, results in fans for r in results
                     for p in r.path] + [0.0])
        z_max = max(z_pos[-1], focal_z if focal_z is not None else z_pos[-1])
        pad = max(0.05 * (z_max - z_min), 1.0)
        ax.set_xlim(z_min - pad, z_max + pad)
        y_top = max(_surface_sd(s, default_sd)
                    for s in sys_obj.surfaces)
        ax.set_ylim(-y_top * 1.15, y_top * 1.15)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("z, мм")
        ax.set_ylabel("y, мм")
        ax.set_title(f"Схема системы: {len(sys_obj.surfaces)} поверхностей, "
                     f"λ={wl_eff} мкм, поля {fields_list}")
        ax.grid(True, alpha=0.2)
        ax.legend(fontsize=8, loc="upper right")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "num_surfaces": len(sys_obj.surfaces),
                    "fields": fields_list, "num_rays": num_rays,
                    "num_ok": num_ok, "focal_z_mm": focal_z})
        return out

    # ----------------------------------------------------------
    # plot.caustic — каустика пучка за последней поверхностью
    # ----------------------------------------------------------

    @registry.command(
        "plot.caustic", category="plot",
        description="Каустика (PNG): выходящие участки лучей веера за "
                    "последней поверхностью до z(изображение)+range и "
                    "ширина пучка RMS(z) — перетяжка/положение фокуса",
        returns="{output, size_bytes, wl, field_y, num_rays, num_ok, "
                "paraxial_focus_mm, waist_z_mm, min_rms_mm}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("num_rays", type="int", default=CAUSTIC_RAYS_DEFAULT,
                  help="лучей в меридиональном веере"),
            Param("defocus_range", type="float",
                  default=CAUSTIC_RANGE_DEFAULT,
                  help="продление за плоскость изображения, мм (> 0)"),
            Param("num_points", type="int", default=CAUSTIC_POINTS_DEFAULT,
                  help="точек сетки z кривой ширины"),
        ]))
    def plot_caustic(ctx, file, system, lbo_index, lbo_name, output, wl,
                    field_y, num_rays, defocus_range, num_points):
        from analysis.ray_tracing import trace_fan
        from domain.calculations import paraxial_trace
        from optics_utils import compute_z_positions
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if defocus_range <= 0.0:
            raise CommandError(ERR_INVALID_PARAM,
                               "defocus_range должен быть > 0")
        wl_eff = _wl_effective(sys_obj, wl)
        z_pos = compute_z_positions(sys_obj)
        fan = trace_fan(sys_obj, num_rays=num_rays, wl=wl_eff,
                        field_y=field_y)
        lines = []
        for r in fan:
            line = _exit_line(r)
            if line is not None and r.success:
                lines.append(line)
        if not lines:
            raise CommandError(ERR_UNSUPPORTED,
                               "трассировка не дала лучей для каустики")

        z_img = z_pos[-1]
        z_lo = min(min(z0 for _, z0, _ in lines), z_pos[-2])
        z_hi = z_img + defocus_range
        if num_points < 2:
            raise CommandError(ERR_INVALID_PARAM, "num_points ≥ 2")
        zs_grid = [z_lo + (z_hi - z_lo) * i / (num_points - 1)
                   for i in range(num_points)]
        widths = []
        for z in zs_grid:
            ys = [y0 + slope * (z - z0) for y0, z0, slope in lines]
            mean_y = sum(ys) / len(ys)
            widths.append(math.sqrt(sum((y - mean_y) ** 2 for y in ys)
                                    / len(ys)))
        waist_idx = widths.index(min(widths))
        waist_z = zs_grid[waist_idx]
        min_rms = widths[waist_idx]

        sfp = paraxial_trace(sys_obj).get("sF_prime", 0.0)
        paraxial_focus = (z_pos[-2] + sfp) if sfp else None

        plt = _pyplot()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        # Полные пути — контекст (тонко), выходящие лучи — каустика.
        for r in fan:
            if r.error != "OBSCURED" and len(r.path) >= 2:
                ax1.plot([p[2] for p in r.path],
                         [p[1] for p in r.path],
                         color=COLOR_BLOCKED, linewidth=0.5, alpha=0.4)
        for y0, z0, slope in lines:
            ax1.plot([z0, z_hi], [y0, y0 + slope * (z_hi - z0)],
                     color=COLOR_MAIN, linewidth=0.9)
        ax1.axvline(z_img, color="gray", linewidth=0.8, linestyle=":")
        if paraxial_focus is not None:
            ax1.axvline(paraxial_focus, color=COLOR_ALT, linewidth=1.0,
                        linestyle="--")
            y_top = ax1.get_ylim()[1]
            ax1.text(paraxial_focus, 0.9 * y_top, "F' (параксиальный)",
                     color=COLOR_ALT, fontsize=8, ha="center", va="top")
        ax1.set_xlabel("z, мм")
        ax1.set_ylabel("y, мм")
        ax1.set_title(f"Каустика: λ={wl_eff} мкм, поле {field_y}")
        ax1.grid(True, alpha=0.3)

        ax2.plot(zs_grid, widths, ".-", color=COLOR_MAIN, markersize=4)
        ax2.plot(waist_z, min_rms, "o", color=COLOR_ALT,
                 label=f"перетяжка z={waist_z:.3f} мм")
        ax2.set_xlabel("z, мм")
        ax2.set_ylabel("Ширина пучка RMS, мм")
        ax2.set_title("Ширина пучка по z")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y, "num_rays": num_rays,
                    "num_ok": len(lines),
                    "paraxial_focus_mm": paraxial_focus,
                    "waist_z_mm": waist_z, "min_rms_mm": min_rms})
        return out

    # ----------------------------------------------------------
    # plot.vignetting — виньетирование и светораспределение по полям
    # ----------------------------------------------------------

    @registry.command(
        "plot.vignetting", category="plot",
        description="Виньетирование по полям (PNG): срезание верх/низ "
                    "пучка, % (TABBEA §14.1) и светораспределение "
                    "(доли площади зрачка верх/низ/всего)",
        returns="{output, size_bytes, wl, rows: [{field_y, vignet_up, "
                "vignet_down, light_up, light_down, light_total}], "
                "max_vignet_percent}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_vignetting(ctx, file, system, lbo_index, lbo_name, output,
                        fields, wl):
        from analysis.vignetting import (
            compute_light_distribution,
            compute_vignetting,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fields_list = _fields_arg(sys_obj, fields)
        vign = {f: compute_vignetting(sys_obj, f, wl=wl_eff)
                for f in fields_list}
        light_rows = compute_light_distribution(sys_obj, fields_list,
                                                wl=wl_eff)
        light = {row["field_y"]: row for row in light_rows}
        rows = []
        for f in fields_list:
            v, l = vign[f], light.get(f, {})
            rows.append({
                "field_y": f,
                "vignet_up": float(v["vignet_up"]),
                "vignet_down": float(v["vignet_down"]),
                "light_up": l.get("light_up"),
                "light_down": l.get("light_down"),
                "light_total": l.get("light_total"),
            })

        xs = [r["field_y"] for r in rows]
        plt = _pyplot()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        ax1.plot(xs, [r["vignet_up"] for r in rows], ".-", color=COLOR_MAIN,
                 label="верх пучка")
        ax1.plot(xs, [r["vignet_down"] for r in rows], ".-", color=COLOR_ALT,
                 label="низ пучка")
        ax1.set_xlabel("Поле, град")
        ax1.set_ylabel("Виньетирование, %")
        ax1.set_title("Срезание пучка (TABBEA)")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax2.plot(xs, [r["light_total"] for r in rows], ".-", color="black",
                 label="всего")
        ax2.plot(xs, [r["light_up"] for r in rows], ".-", color=COLOR_MAIN,
                 label="верх")
        ax2.plot(xs, [r["light_down"] for r in rows], ".-", color=COLOR_ALT,
                 label="низ")
        ax2.set_xlabel("Поле, град")
        ax2.set_ylabel("Доля светораспределения")
        ax2.set_title("Светораспределение по полям")
        ax2.set_ylim(0.0, 1.05)
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "rows": rows,
                    "max_vignet_percent": max(
                        max(r["vignet_up"], r["vignet_down"])
                        for r in rows)})
        return out

    # ----------------------------------------------------------
    # plot.chromatism — f'(λ) и осевой хроматизм
    # ----------------------------------------------------------

    @registry.command(
        "plot.chromatism", category="plot",
        description="Хроматизм (PNG): f′(λ) по сетке длин волн и осевой "
                    "хроматизм Δf′(λ) относительно основной λ; рабочие λ "
                    "системы — метками",
        returns="{output, size_bytes, primary_wl, fprime_primary_mm, "
                "wl_grid, fprimes_mm, dfprime_at_system_wl}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("steps", type="int", default=CHROMATISM_STEPS_DEFAULT,
                  help="точек сетки λ (≥ 2)"),
        ]))
    def plot_chromatism(ctx, file, system, lbo_index, lbo_name, output,
                        steps):
        from domain.calculations import paraxial_trace
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if steps < 2:
            raise CommandError(ERR_INVALID_PARAM, "steps ≥ 2")
        wls_sys = [float(w.value) for w in sys_obj.wavelengths]
        if not wls_sys:
            wls_sys = [get_primary_wl(sys_obj)]
        wl_primary = get_primary_wl(sys_obj)
        lo, hi = min(wls_sys), max(wls_sys)
        pad = max((hi - lo) * CHROMATISM_PAD_FRACTION,
                  CHROMATISM_MIN_PAD_UM)
        grid = [lo - pad + (hi - lo + 2.0 * pad) * i / (steps - 1)
                for i in range(steps)]
        fprimes = [float(paraxial_trace(sys_obj, wl=lam)["focal_length"])
                   for lam in grid]
        f_primary = float(paraxial_trace(sys_obj,
                                         wl=wl_primary)["focal_length"])
        if f_primary == 0.0:
            raise CommandError(ERR_UNSUPPORTED,
                               "система афокальна: f′ = 0, хроматизм f′(λ) "
                               "не строится")

        plt = _pyplot()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        ax1.plot(grid, fprimes, "-", color=COLOR_MAIN)
        for wl_sys in wls_sys:
            ax1.axvline(wl_sys, color="gray", linewidth=0.8,
                        linestyle=":")
        ax1.set_xlabel("λ, мкм")
        ax1.set_ylabel("f′, мм")
        ax1.set_title("Фокусное расстояние по λ")
        ax1.grid(True, alpha=0.3)
        ax2.plot(grid, [f - f_primary for f in fprimes], "-",
                 color=COLOR_MAIN)
        ax2.axhline(0.0, color="gray", linewidth=0.8)
        for wl_sys in wls_sys:
            ax2.axvline(wl_sys, color="gray", linewidth=0.8,
                        linestyle=":")
        ax2.set_xlabel("λ, мкм")
        ax2.set_ylabel("Δf′, мм")
        ax2.set_title(f"Осевой хроматизм (отн. λ={wl_primary} мкм)")
        ax2.grid(True, alpha=0.3)
        out = _save_png(fig, output)
        out.update({
            "primary_wl": wl_primary,
            "fprime_primary_mm": f_primary,
            "wl_grid": grid,
            "fprimes_mm": fprimes,
            "dfprime_at_system_wl": {
                str(wl_sys): float(
                    paraxial_trace(sys_obj, wl=wl_sys)["focal_length"]
                    - f_primary)
                for wl_sys in sorted(set(wls_sys))},
        })
        return out

    # ----------------------------------------------------------
    # plot.wavefront — карта волнового фронта
    # ----------------------------------------------------------

    @registry.command(
        "plot.wavefront", category="plot",
        description="Карта волнового фронта W(x, y) на зрачке (PNG, λ), "
                    "с СКВ и размахом PV",
        returns="{output, size_bytes, wl, field_y, grid_size, rms_wl, "
                "pv_wl, fill}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("grid_size", type="int", default=WAVEFRONT_GRID_DEFAULT,
                  help="решётка карты N×N (≥ 8)"),
        ]))
    def plot_wavefront(ctx, file, system, lbo_index, lbo_name, output, wl,
                       field_y, grid_size):
        import numpy as np
        from analysis.zernike import compute_wavefront_map_2d
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if grid_size < 8:
            raise CommandError(ERR_INVALID_PARAM, "grid_size ≥ 8")
        wl_eff = _wl_effective(sys_obj, wl)
        wavefront, coords, mask = compute_wavefront_map_2d(
            sys_obj, wl=wl_eff, field_y=field_y, grid_size=grid_size)
        inside = mask > 0.5
        n_inside = int(inside.sum())
        if n_inside == 0:
            raise CommandError(ERR_UNSUPPORTED,
                               "карта волнового фронта пуста (зрачок не "
                               "заполнен)")
        values = wavefront[inside]
        rms_wl = float(np.sqrt(np.mean(values ** 2)))
        pv_wl = float(values.max() - values.min())
        masked = np.ma.masked_array(wavefront, mask=~inside)

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        im = ax.imshow(masked, extent=(-1.0, 1.0, -1.0, 1.0),
                       origin="lower", cmap="RdBu_r")
        fig.colorbar(im, ax=ax, label="W, λ")
        ax.set_xlabel("Зрачковая координата px")
        ax.set_ylabel("Зрачковая координата py")
        ax.set_title(f"Волновой фронт: λ={wl_eff} мкм, поле {field_y}, "
                     f"СКВ={rms_wl:.3f}λ, PV={pv_wl:.3f}λ")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y,
                    "grid_size": grid_size, "rms_wl": rms_wl,
                    "pv_wl": pv_wl,
                    "fill": n_inside / float(mask.size)})
        return out

    # ----------------------------------------------------------
    # plot.glassmap — стёкла системы на карте nd–vd
    # ----------------------------------------------------------

    @registry.command(
        "plot.glassmap", category="plot",
        description="Стёкла системы на карте стёкол nd–vd (PNG): каталог "
                    "ГОСТ фоном, стёкла системы — ломаной «траектории "
                    "коррекции» по ходу поверхностей (данные — "
                    "diagram.glasses)",
        returns="{output, size_bytes, glasses, skipped, num_catalog}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
        ]))
    def plot_glassmap(ctx, file, system, lbo_index, lbo_name, output):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        catalog_res = registry.execute("diagram.glasses", ctx, {})
        if not catalog_res.ok:
            raise CommandError(catalog_res.error["code"],
                               catalog_res.error["message"])
        catalog = catalog_res.data
        by_name = {row["name"]: row for row in catalog["glasses"]}

        # Стёкла системы по ходу поверхностей (без воздуха, с повторами —
        # ломаная показывает порядок линз).
        names = [s.glass for s in sys_obj.surfaces
                 if s.glass and s.glass.upper() not in ("ВОЗДУХ", "AIR")]
        if not names:
            raise CommandError(ERR_BAD_REQUEST,
                               "в системе нет стёкол (только воздух/зеркала)")
        skipped = sorted({n for n in names if n not in by_name})
        points = [by_name[n] for n in names if n in by_name]
        if not points:
            raise CommandError(ERR_BAD_REQUEST,
                               f"стёкла системы {skipped} отсутствуют в "
                               f"каталоге")

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=DIAGRAM_FIGSIZE)
        ax.scatter([row["vd"] for row in catalog["glasses"]],
                   [row["nd"] for row in catalog["glasses"]],
                   c="#b0b0b0", s=12, alpha=0.5, linewidths=0,
                   label=f"каталог ГОСТ ({catalog['num_glasses']})")
        ax.plot([row["vd"] for row in points],
                [row["nd"] for row in points], "-o",
                color=COLOR_MAIN, markersize=9, markeredgecolor="black",
                markeredgewidth=1.2, linewidth=1.6,
                label="стёкла системы (по ходу)")
        for row, name in zip(points, [n for n in names if n in by_name]):
            ax.annotate(name, (row["vd"], row["nd"]), fontsize=10,
                        fontweight="bold", ha="left", va="bottom",
                        xytext=(6, 5), textcoords="offset points")
        ax.set_xlabel("Коэффициент дисперсии $v_d$ (Аббе)")
        ax.set_ylabel("Показатель преломления $n_d$")
        ax.set_title("Стёкла системы на карте nd–vd")
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(*DIAGRAM_XLIM)
        ax.set_ylim(*DIAGRAM_YLIM)
        ax.invert_xaxis()                # vd убывает вправо (как diagram)
        out = _save_png(fig, output)
        out.update({"glasses": [n for n in names if n in by_name],
                    "skipped": skipped,
                    "num_catalog": catalog["num_glasses"]})
        return out

    # ----------------------------------------------------------
    # plot.seidel — бар-чарт сумм Зейделя
    # ----------------------------------------------------------

    @registry.command(
        "plot.seidel", category="plot",
        description="Суммы Зейделя 3-го порядка — бар-чарт (PNG): "
                    "SI..SV, при наличии хроматизма — SIхр/SIIхр (данные — "
                    "seidel.sums)",
        returns="{output, size_bytes, wl, sums, chromatic}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_seidel(ctx, file, system, lbo_index, lbo_name, output, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        args = {"wl": wl} if wl is not None else {}
        sums = _run_sibling(registry, ctx, sys_obj, "seidel", "seidel.sums",
                            args)
        keys = ["SI", "SII", "SIII", "SIV", "SV"]
        if sums.get("chromatic"):
            keys += ["SIxp", "SIIxp"]
        labels = [f"{key}\n{SEIDEL_LABELS.get(key, 'хроматическая')}"
                  for key in keys]
        values = [float(sums[key]) for key in keys]

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
        colors = [COLOR_MAIN if v >= 0.0 else COLOR_ALT for v in values]
        bars = ax.bar(labels, values, color=colors, alpha=0.85)
        for bar, value in zip(bars, values):
            y_text = value + 0.02 * max(abs(v) for v in values)
            ax.text(bar.get_x() + bar.get_width() / 2.0, y_text,
                    f"{value:.4g}", ha="center", va="bottom", fontsize=9)
        ax.axhline(0.0, color="black", linewidth=0.8)
        ax.set_ylabel("Сумма Зейделя (базис порта)")
        ax.set_title(f"Суммы Зейделя 3-го порядка: λ={sums['wl']} мкм")
        ax.grid(True, axis="y", alpha=0.3)
        out = _save_png(fig, output)
        out.update({"wl": sums["wl"], "sums": {k: float(sums[k])
                                               for k in keys},
                    "chromatic": bool(sums.get("chromatic"))})
        return out

    # ----------------------------------------------------------
    # plot.fields — карта точек поля
    # ----------------------------------------------------------

    @registry.command(
        "plot.fields", category="plot",
        description="Карта точек поля системы (PNG): (x, y) с весами и "
                    "окружностью максимального поля",
        returns="{output, size_bytes, num_fields, max_field, fields}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
        ]))
    def plot_fields(ctx, file, system, lbo_index, lbo_name, output):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        fields = [(float(fp.x), float(fp.y), float(fp.weight))
                  for fp in sys_obj.field_points]
        if not fields:
            raise CommandError(
                ERR_BAD_REQUEST,
                "у системы нет точек поля; добавьте system.fields.add")
        max_field = max(math.hypot(x, y) for x, y, _ in fields)
        if max_field <= 0.0:
            raise CommandError(ERR_BAD_REQUEST,
                               "все точки поля в центре (0, 0) — карта "
                               "вырождена")

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        theta = [2.0 * math.pi * i / 60 for i in range(61)]
        ax.plot([max_field * math.cos(t) for t in theta],
                [max_field * math.sin(t) for t in theta],
                color=COLOR_BLOCKED, linewidth=0.8, linestyle="--",
                label=f"макс. поле {max_field:g}")
        ax.scatter([x for x, _, _ in fields], [y for _, y, _ in fields],
                   s=[80.0 * w for _, _, w in fields], c=COLOR_MAIN,
                   alpha=0.75, edgecolors="black", linewidths=0.8,
                   zorder=3)
        for x, y, w in fields:
            ax.annotate(f"w={w:g}", (x, y), ha="left", va="bottom",
                        xytext=(6, 4), textcoords="offset points",
                        fontsize=9)
        ax.axhline(0.0, color="gray", linewidth=0.6)
        ax.axvline(0.0, color="gray", linewidth=0.6)
        ax.set_aspect("equal")
        pad = max_field * 0.15
        ax.set_xlim(-max_field - pad, max_field + pad)
        ax.set_ylim(-max_field - pad, max_field + pad)
        ax.set_xlabel("x поля")
        ax.set_ylabel("y поля (град / мм)")
        ax.set_title(f"Точки поля системы ({len(fields)} шт.)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        out = _save_png(fig, output)
        out.update({"num_fields": len(fields), "max_field": max_field,
                    "fields": [{"x": x, "y": y, "weight": w}
                               for x, y, w in fields]})
        return out

    # ----------------------------------------------------------
    # plot.mtf.family — семейство ЧКХ по полям
    # ----------------------------------------------------------

    @registry.command(
        "plot.mtf.family", category="plot",
        description="Семейство ЧКХ по полям (PNG): тангенциальное "
                    "(сплошная) и сагиттальное (пунктир) сечения из ФРТ "
                    "на одном поле графика",
        returns="{output, size_bytes, wl, fields, cutoff_lpmm, "
                "nyquist_lpmm}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("max_freq", type="float",
                  help="правая граница частоты, лин/мм (по умолчанию — "
                       "Найквист ФРТ)"),
        ]))
    def plot_mtf_family(ctx, file, system, lbo_index, lbo_name, output,
                        fields, wl, max_freq):
        from analysis.psf_mtf import mtf_from_psf, psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fields_list = _fields_arg(sys_obj, fields)
        curves = []
        cutoff = nyquist = None
        for field in fields_list:
            res = psf_grid(sys_obj, field_y=field, wl=wl_eff)
            psf = res.get("psf")
            if psf is None:
                raise CommandError(ERR_UNSUPPORTED,
                                   f"ЧКХ не рассчитана на поле {field}: "
                                   f"{res.get('reason')}")
            mtf = mtf_from_psf(psf, res["pitch_um"])
            curves.append((field, mtf["freq_lpmm"], mtf["tan"], mtf["sag"],
                           float(mtf["nyquist_lpmm"])))
            cutoff = res.get("cutoff_lpmm")
        if not curves:
            raise CommandError(ERR_UNSUPPORTED, "семейство ЧКХ пусто")
        nyquist = min(c[4] for c in curves)
        x_max = min(max_freq, nyquist) if max_freq else nyquist

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        for idx, (field, freqs, tan, sag, _) in enumerate(curves):
            color = COLOR_CYCLE[idx % len(COLOR_CYCLE)]
            ax.plot(freqs, tan, "-", color=color, linewidth=1.2,
                    label=f"поле {field:g}: танг.")
            ax.plot(freqs, sag, "--", color=color, linewidth=1.2,
                    label=f"поле {field:g}: саг.")
        ax.axhline(0.0, color="gray", linewidth=0.8)
        ax.set_xlabel("Пространственная частота, лин/мм")
        ax.set_ylabel("MTF")
        ax.set_title(f"Семейство ЧКХ по полям: λ={wl_eff} мкм")
        ax.set_xlim(0.0, x_max)
        ax.set_ylim(0.0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "fields": fields_list,
                    "cutoff_lpmm": cutoff, "nyquist_lpmm": nyquist})
        return out

    # ----------------------------------------------------------
    # plot.ee.family — семейство ФКЭ по полям
    # ----------------------------------------------------------

    @registry.command(
        "plot.ee.family", category="plot",
        description="Семейство функций концентрации энергии по полям "
                    "(PNG) с метрикой r₈₀",
        returns="{output, size_bytes, wl, rows: [{field_y, r80_um}]}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_ee_family(ctx, file, system, lbo_index, lbo_name, output,
                       fields, wl):
        import numpy as np
        from analysis.psf_mtf import encircled_energy, psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fields_list = _fields_arg(sys_obj, fields)
        curves = []
        for field in fields_list:
            res = psf_grid(sys_obj, field_y=field, wl=wl_eff)
            psf = res.get("psf")
            if psf is None:
                raise CommandError(ERR_UNSUPPORTED,
                                   f"ФКЭ не рассчитана на поле {field}: "
                                   f"{res.get('reason')}")
            r_um, ee = encircled_energy(psf, res["pitch_um"])
            r80 = float(np.interp(EE_LEVEL, ee, r_um))
            curves.append((field, list(r_um), list(ee), r80))

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        for field, r_um, ee, r80 in curves:
            ax.plot(r_um, ee, "-", linewidth=1.2,
                    label=f"поле {field:g} (r₈₀={r80:.1f} мкм)")
        ax.axhline(EE_LEVEL, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Радиус кружка, мкм")
        ax.set_ylabel("Доля энергии")
        ax.set_title(f"ФКЭ по полям: λ={wl_eff} мкм")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff,
                    "rows": [{"field_y": f, "r80_um": r80}
                             for f, _, _, r80 in curves]})
        return out

    # ----------------------------------------------------------
    # plot.spot.grid — сетка пятен рассеяния по полям
    # ----------------------------------------------------------

    @registry.command(
        "plot.spot.grid", category="plot",
        description="Сетка пятен рассеяния по полям (PNG): подпанель на "
                    "поле, точки и окружность RMS",
        returns="{output, size_bytes, wl, rows: [{field_y, rms, "
                "num_points}]}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_rays", type="int", default=SPOT_GRID_RAYS_DEFAULT,
                  help="лучей по стороне сетки зрачка"),
        ]))
    def plot_spot_grid(ctx, file, system, lbo_index, lbo_name, output,
                       fields, wl, num_rays):
        import numpy as np
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fields_list = _fields_arg(sys_obj, fields)
        spots_by_field = []
        for field in fields_list:
            spots = compute_spot_diagram(sys_obj, wl=wl_eff,
                                         num_rays=num_rays, field_y=field)
            if not spots:
                raise CommandError(ERR_UNSUPPORTED,
                                   f"пятно пусто на поле {field}")
            spots_by_field.append((field, spots, compute_rms_spot(spots)))

        ncols = min(SPOT_GRID_MAX_COLS, len(spots_by_field))
        nrows = math.ceil(len(spots_by_field) / ncols)
        plt = _pyplot()
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(SPOT_GRID_CELL[0] * ncols,
                     SPOT_GRID_CELL[1] * nrows))
        axes = np.atleast_1d(axes).ravel()
        for ax in axes[len(spots_by_field):]:
            ax.axis("off")
        for ax, (field, spots, rms) in zip(axes, spots_by_field):
            ax.plot([p[0] for p in spots], [p[1] for p in spots], ".",
                    color=COLOR_MAIN, markersize=3)
            ax.add_patch(plt.Circle((0.0, 0.0), rms, fill=False,
                                    color=COLOR_ALT, linestyle="--"))
            ax.set_aspect("equal")
            ax.set_title(f"поле {field:g}, RMS={rms:.4f} мм", fontsize=10)
            ax.grid(True, alpha=0.3)
        fig.suptitle(f"Пятна рассеяния по полям: λ={wl_eff} мкм, "
                     f"{num_rays}×{num_rays} лучей")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff,
                    "rows": [{"field_y": f, "rms": rms,
                              "num_points": len(spots)}
                             for f, spots, rms in spots_by_field]})
        return out

    # ----------------------------------------------------------
    # plot.fan.fields — веера поперечных аберраций по полям
    # ----------------------------------------------------------

    @registry.command(
        "plot.fan.fields", category="plot",
        description="Веера поперечных аберраций dy по полям (PNG): "
                    "кривые dy(зрачковая координата) всех полей на одном "
                    "поле графика",
        returns="{output, size_bytes, wl, num_fan_rays, fields, num_ok}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("num_fan_rays", type="int",
                  default=FAN_FIELDS_RAYS_DEFAULT,
                  help="лучей в веере на поле"),
        ]))
    def plot_fan_fields(ctx, file, system, lbo_index, lbo_name, output,
                        fields, wl, num_fan_rays):
        from analysis.aberrations import trace_aberration_fan
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        fields_list = _fields_arg(sys_obj, fields)
        fans = []
        num_ok_total = 0
        for field in fields_list:
            fan = trace_aberration_fan(sys_obj, wl_eff,
                                       num_rays=num_fan_rays,
                                       field_y=field)
            ok = [row for row in fan if row.get("success")]
            num_ok_total += len(ok)
            if ok:
                fans.append((field, ok))
        if not fans:
            raise CommandError(ERR_UNSUPPORTED,
                               "веера лучей пусты на всех полях")

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        for field, ok in fans:
            ax.plot([row["pupil_y"] for row in ok],
                    [row["dy"] for row in ok], ".-",
                    markersize=4, linewidth=1.1,
                    label=f"поле {field:g}")
        ax.axhline(0.0, color="gray", linewidth=0.8)
        ax.set_xlabel("Зрачковая координата")
        ax.set_ylabel("dy, мм (поперечная аберрация)")
        ax.set_title(f"Веера аберраций по полям: λ={wl_eff} мкм")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "num_fan_rays": num_fan_rays,
                    "fields": fields_list, "num_ok": num_ok_total})
        return out

    # ----------------------------------------------------------
    # plot.dof — глубина фокуса по дефокусу
    # ----------------------------------------------------------

    @registry.command(
        "plot.dof", category="plot",
        description="Глубина фокуса (PNG): RMS и геометрический радиус "
                    "пятна против смещения плоскости изображения; зона, "
                    "где радиус ≤ круга нерезкости, — глубина резкости",
        returns="{output, size_bytes, wl, field_y, coc_um, "
                "best_defocus_mm, best_rms_mm, near_mm, far_mm, "
                "depth_mm}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("coc_um", type="float", default=DOF_COC_UM_DEFAULT,
                  help="круг нерезкости, мкм (> 0)"),
            Param("defocus_range", type="float", default=DOF_RANGE_DEFAULT,
                  help="±мм развёртки дефокуса (> 0)"),
            Param("num_points", type="int", default=DOF_POINTS_DEFAULT,
                  help="точек кривой (≥ 3)"),
            Param("num_rays", type="int", default=DOF_RAYS_DEFAULT,
                  help="лучей по стороне сетки зрачка"),
        ]))
    def plot_dof(ctx, file, system, lbo_index, lbo_name, output, wl,
                 field_y, coc_um, defocus_range, num_points, num_rays):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram_at_defocus,
        )
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if coc_um <= 0.0:
            raise CommandError(ERR_INVALID_PARAM, "coc_um должен быть > 0")
        if defocus_range <= 0.0:
            raise CommandError(ERR_INVALID_PARAM,
                               "defocus_range должен быть > 0")
        if num_points < 3:
            raise CommandError(ERR_INVALID_PARAM, "num_points ≥ 3")
        wl_eff = _wl_effective(sys_obj, wl)
        threshold = coc_um * 1e-3 / 2.0        # радиус круга нерезкости, мм

        defoci, rms_curve, geo_curve = [], [], []
        for i in range(num_points):
            dz = -defocus_range + 2.0 * defocus_range * i / (num_points - 1)
            spots = compute_spot_diagram_at_defocus(
                sys_obj, wl=wl_eff, num_rays=num_rays, field_y=field_y,
                defocus_mm=dz)
            if not spots:
                raise CommandError(ERR_UNSUPPORTED,
                                   f"пятно пусто при дефокусе {dz} мм")
            defoci.append(dz)
            rms_curve.append(compute_rms_spot(spots))
            geo_curve.append(max(math.hypot(dx, dy) for dx, dy in spots))
        best_idx = rms_curve.index(min(rms_curve))

        # Границы зоны резкости: первый/последний узел, где геометрический
        # радиус ≤ допуска; края — линейной интерполяцией пересечения.
        inside_idx = [i for i, geo in enumerate(geo_curve)
                      if geo <= threshold]
        if inside_idx:
            i0, i1 = inside_idx[0], inside_idx[-1]

            def _cross(i_lo: int, i_hi: int) -> float:
                """Пересечение geo(z)=threshold между соседними узлами."""
                g_lo, g_hi = geo_curve[i_lo], geo_curve[i_hi]
                z_lo, z_hi = defoci[i_lo], defoci[i_hi]
                if g_lo == g_hi:
                    return z_lo
                return z_lo + (z_hi - z_lo) * (threshold - g_lo) / \
                    (g_hi - g_lo)

            near = (_cross(i0 - 1, i0) if i0 > 0 else defoci[0])
            far = (_cross(i1, i1 + 1) if i1 < num_points - 1
                   else defoci[-1])
            near, far = min(near, far), max(near, far)
            depth = far - near
        else:
            near = far = None
            depth = 0.0              # пятно превышает допуск во всём range

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        if near is not None and far is not None and far > near:
            ax.axvspan(near, far, color=COLOR_OK, alpha=0.15,
                       label=f"глубина резкости {depth:.3f} мм")
        ax.plot(defoci, rms_curve, ".-", color=COLOR_MAIN, markersize=4,
                label="RMS радиус")
        ax.plot(defoci, geo_curve, ".-", color=COLOR_ALT, markersize=4,
                label="геометр. радиус")
        ax.axhline(threshold, color="black", linewidth=0.9,
                   linestyle="--",
                   label=f"круг нерезкости R={threshold:.4f} мм")
        ax.set_xlabel("Дефокусировка, мм")
        ax.set_ylabel("Радиус пятна, мм")
        ax.set_title(f"Глубина фокуса: λ={wl_eff} мкм, поле {field_y}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y, "coc_um": coc_um,
                    "best_defocus_mm": defoci[best_idx],
                    "best_rms_mm": rms_curve[best_idx],
                    "near_mm": near, "far_mm": far, "depth_mm": depth})
        return out

    # ----------------------------------------------------------
    # plot.pupil.vign — маска зрачка (виньетирование узлов сетки)
    # ----------------------------------------------------------

    @registry.command(
        "plot.pupil.vign", category="plot",
        description="Маска зрачка на поле (PNG): узлы гексаполярной сетки "
                    "зрачка «прошёл/срезан» (данные — trace.grid3d), "
                    "границы зрачка и экранирования",
        returns="{output, size_bytes, wl, field_y, num_passed, "
                "num_blocked, pass_fraction, obscuration_ratio}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("num_rings", type="int", default=PUPIL_RINGS_DEFAULT,
                  help="колец зрачка (≥ 2)"),
            Param("num_azimuths", type="int",
                  default=PUPIL_AZIMUTHS_DEFAULT,
                  help="азимутов на кольцо (≥ 4)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
        ]))
    def plot_pupil_vign(ctx, file, system, lbo_index, lbo_name, output,
                        field_y, num_rings, num_azimuths, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        if num_rings < 2:
            raise CommandError(ERR_INVALID_PARAM, "num_rings ≥ 2")
        if num_azimuths < 4:
            raise CommandError(ERR_INVALID_PARAM, "num_azimuths ≥ 4")
        wl_eff = _wl_effective(sys_obj, wl)
        args = {"field_y": field_y, "num_rings": num_rings,
                "num_azimuths": num_azimuths, "wl": wl_eff}
        data = _run_sibling(registry, ctx, sys_obj, "pupil",
                            "trace.grid3d", args)
        nodes = []
        for ring in data["rings"]:
            for ray in ring:
                phi = math.radians(ray["phi_deg"])
                nodes.append((ray["rho"] * math.cos(phi),
                              ray["rho"] * math.sin(phi),
                              bool(ray["success"])))
        num_passed = sum(1 for _, _, ok in nodes if ok)
        num_blocked = len(nodes) - num_passed
        if num_passed == 0:
            raise CommandError(ERR_UNSUPPORTED,
                               "все узлы зрачка срезаны на поле "
                               f"{field_y}")
        obscuration = float(getattr(sys_obj, "obscuration_ratio", 0.0))

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        theta = [2.0 * math.pi * i / 60 for i in range(61)]
        ax.plot([math.cos(t) for t in theta], [math.sin(t) for t in theta],
                color=COLOR_BLOCKED, linewidth=1.0)
        if obscuration > 0.0:
            ax.plot([obscuration * math.cos(t) for t in theta],
                    [obscuration * math.sin(t) for t in theta],
                    color=COLOR_ALT, linewidth=1.0, linestyle="--",
                    label=f"экранирование {obscuration:g}")
        ax.scatter([px for px, _, ok in nodes if ok],
                   [py for _, py, ok in nodes if ok],
                   c=COLOR_OK, s=28, label=f"прошли ({num_passed})")
        if num_blocked:
            ax.scatter([px for px, _, ok in nodes if not ok],
                       [py for _, py, ok in nodes if not ok],
                       c=COLOR_ALT, marker="x", s=42,
                       label=f"срезаны ({num_blocked})")
        ax.set_aspect("equal")
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.set_xlabel("Зрачковая координата px")
        ax.set_ylabel("Зрачковая координата py")
        ax.set_title(f"Маска зрачка: поле {field_y}, λ={wl_eff} мкм, "
                     f"проходят {num_passed / len(nodes):.0%}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9, loc="upper right")
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y,
                    "num_passed": num_passed, "num_blocked": num_blocked,
                    "pass_fraction": num_passed / len(nodes),
                    "obscuration_ratio": obscuration})
        return out

    # ----------------------------------------------------------
    # plot.psf.slice — срезы ФРТ через центр
    # ----------------------------------------------------------

    @registry.command(
        "plot.psf.slice", category="plot",
        description="Срезы ФРТ через центр (PNG): горизонтальный I(x) и "
                    "вертикальный I(y) профили с шириной FWHM",
        returns="{output, size_bytes, wl, field_y, defocus, strehl, "
                "fwhm_x_um, fwhm_y_um}",
        params=system_source_params([
            Param("output", required=True, help="путь к PNG-файлу"),
            Param("field_y", type="float", default=0.0,
                  help="поле (град для INFINITE / мм для FINITE)"),
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("defocus", type="float", default=0.0,
                  help="дефокусировка в длинах волн на краю зрачка"),
        ]))
    def plot_psf_slice(ctx, file, system, lbo_index, lbo_name, output,
                       field_y, wl, defocus):
        import numpy as np
        from analysis.psf_mtf import psf_grid
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        wl_eff = _wl_effective(sys_obj, wl)
        res = psf_grid(sys_obj, field_y=field_y, wl=wl_eff,
                       defocus=defocus)
        psf = res.get("psf")
        if psf is None:
            raise CommandError(ERR_UNSUPPORTED,
                               f"ФРТ не рассчитана: {res.get('reason')}")
        psf_arr = np.asarray(psf, dtype=float)
        center = psf_arr.shape[0] // 2
        x_um, y_um = np.asarray(res["x_um"]), np.asarray(res["y_um"])
        i_x = psf_arr[center, :]
        i_y = psf_arr[:, center]
        peak = float(psf_arr[center, center])
        if peak <= 0.0:
            raise CommandError(ERR_UNSUPPORTED,
                               "ФРТ вырождена (нулевой центр)")
        fwhm_x = _fwhm_um(i_x, x_um)
        fwhm_y = _fwhm_um(i_y, y_um)

        plt = _pyplot()
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.plot(x_um, i_x / peak, "-", color=COLOR_MAIN,
                label=f"I(x): FWHM={fwhm_x:.2f} мкм")
        ax.plot(y_um, i_y / peak, "--", color=COLOR_ALT,
                label=f"I(y): FWHM={fwhm_y:.2f} мкм")
        ax.axhline(0.5, color="gray", linewidth=0.8, linestyle=":")
        ax.set_xlabel("Координата в плоскости изображения, мкм")
        ax.set_ylabel("Интенсивность (норм.)")
        ax.set_title(f"Срезы ФРТ: поле {field_y}, λ={wl_eff} мкм")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        out = _save_png(fig, output)
        out.update({"wl": wl_eff, "field_y": field_y,
                    "defocus": defocus, "strehl": res.get("strehl"),
                    "fwhm_x_um": fwhm_x, "fwhm_y_um": fwhm_y})
        return out
