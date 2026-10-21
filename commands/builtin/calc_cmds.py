"""
OPAL-OKB — Команды calc.*: параксиальный расчёт, апертура, габариты,
суммы Зейделя (обёртки над domain/calculations.py).
"""
from domain.calculations import (
    BEAM_SEMI_MODES,
    compute_beam_geometry,
    paraxial_trace,
    paraxial_trace_all_wavelengths,
    real_beam_aperture,
    seidel_aberrations,
)

from commands.base import Param
from commands.registry import Registry
from commands.systemio import resolve_system, system_source_params

#: Режимы габаритов пучков — из domain (единственный источник).
SEMI_MODE_CHOICES = tuple(key for key, _ in BEAM_SEMI_MODES)


def register(registry: Registry) -> None:
    """Зарегистрировать все команды calc.*."""

    @registry.command(
        "calc.paraxial", category="calc",
        description="Параксиальный расчёт: кардинальные отрезки, зрачки, f/#",
        returns="словарь paraxial_trace (focal_length, sF/sF', sP/sP', ...)",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ системы)"),
        ]))
    def calc_paraxial(ctx, file, system, lbo_index, lbo_name, wl):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return paraxial_trace(sys_obj, wl=wl)

    @registry.command(
        "calc.paraxial.multi_wl", category="calc",
        description="Параксиальный расчёт для каждой рабочей λ системы",
        returns="список результатов paraxial_trace (ключ 'wl' в каждом)",
        params=system_source_params())
    def calc_paraxial_multi_wl(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"results": paraxial_trace_all_wavelengths(sys_obj),
                "num_wavelengths": len(sys_obj.wavelengths)}

    @registry.command(
        "calc.aperture.real", category="calc",
        description="Реальный диаметр осевого пучка по полудиаметрам поверхностей",
        returns="диаметр (мм) или null — если полудиаметры не заданы",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("sharp_edge", type="bool", default=True,
                  help="виньетирование по острому краю (без скругления)"),
        ]))
    def calc_aperture_real(ctx, file, system, lbo_index, lbo_name, wl,
                           sharp_edge):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        diameter = real_beam_aperture(sys_obj, wl=wl,
                                      sharp_edge=sharp_edge)
        return {"diameter": diameter,
                "sharp_edge": sharp_edge}

    @registry.command(
        "calc.beam_geometry", category="calc",
        description="Габариты пучков по полям: апертуры, виньетирование, "
                    "светораспределение",
        returns="список результатов по точкам поля",
        params=system_source_params([
            Param("wl", type="float",
                  help="длина волны, мкм (по умолчанию — основная λ)"),
            Param("semi_mode", choices=list(SEMI_MODE_CHOICES),
                  default="given",
                  help="режим: given — по заданной апертуре, real — по "
                       "полудиаметрам поверхностей"),
            Param("sharp_edge", type="bool", default=True,
                  help="виньетирование по острому краю"),
        ]))
    def calc_beam_geometry(ctx, file, system, lbo_index, lbo_name, wl,
                           semi_mode, sharp_edge):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return {"fields": compute_beam_geometry(
                    sys_obj, wl=wl, semi_mode=semi_mode,
                    sharp_edge=sharp_edge),
                "semi_mode": semi_mode}

    @registry.command(
        "calc.seidel", category="calc",
        description="Суммы Зейделя 3-го порядка: SI..SV",
        returns="словарь {SI, SII, SIII, SIV, SV}",
        params=system_source_params())
    def calc_seidel(ctx, file, system, lbo_index, lbo_name):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        return seidel_aberrations(sys_obj)
