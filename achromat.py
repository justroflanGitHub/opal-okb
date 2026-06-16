"""
OPAL-OKB — Автоматический расчёт ахроматического дублета

Классический ахромат: два склеенных элемента (крон + флинт).
Условие ахроматизма: φ₁/ν₁ + φ₂/ν₂ = 0
Оптическая сила:     φ₁ + φ₂ = φ_total

Решение:
    φ₁ = φ_total * ν₁ / (ν₁ - ν₂)
    φ₂ = -φ_total * ν₂ / (ν₁ - ν₂)

Для тонкой линзы: φ = (n-1)(1/R₁ - 1/R₂)
"""
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optics_engine import (
    OpticalSystem, Surface, Wavelength, FieldPoint,
    ObjectType, ApertureType, SurfaceType, paraxial_trace,
)
from glass_catalog import compute_refractive_index, GLASS_CATALOG


# Длины волн: F(486 нм), d(588 нм), C(656 нм)
LAMBDA_F = 0.48613   # мкм
LAMBDA_d = 0.58756   # мкм
LAMBDA_C = 0.65627   # мкм

# Предопределённые пары стёкол для комбобокса
GLASS_PAIRS = [
    ("К8",  "ТФ5"),
    ("БК10", "ТФ3"),
    ("К8",  "Ф4"),
]


def _get_glass_props(glass_name: str):
    """Вернуть (nd, vd) для стекла из каталога."""
    entry = GLASS_CATALOG.get(glass_name)
    if entry is None:
        # case-insensitive fallback
        for key, val in GLASS_CATALOG.items():
            if key.upper() == glass_name.upper():
                entry = val
                break
    if entry is None:
        raise ValueError(f"Стекло '{glass_name}' не найдено в каталоге")
    nd, vd = entry[0], entry[1]
    return nd, vd


def design_achromat(
    focal_length: float,
    crown_glass: str = "К8",
    flint_glass: str = "ТФ5",
    aperture: float = 0.0,
    catalog=None,
) -> OpticalSystem:
    """
    Рассчитать ахроматический дублет.

    Возвращает OpticalSystem с 3 поверхностями:
      - S1: R1 (крон, передняя)
      - S2: R2 = R3 (склейка, крон→флинт)  — одинаковый радиус
      - S3: R3 (флинт, задняя) → воздух

    Параметры
    ---------
    focal_length : float
        Фокусное расстояние f' (мм), f' > 0.
    crown_glass : str
        Марка крона (по умолчанию К8).
    flint_glass : str
        Марка флинта (по умолчанию ТФ5).
    aperture : float
        Диаметр входного зрачка (мм). Если 0 — вычисляется как f'/5.
    catalog : dict, optional
        Каталог стёкол (не используется, берётся из glass_catalog).

    Возвращает
    ----------
    OpticalSystem — система с тремя поверхностями.
    """
    if focal_length <= 0:
        raise ValueError(f"f' должно быть > 0, получено {focal_length}")

    # --- Свойства стёкол ---
    nd_crown, vd_crown = _get_glass_props(crown_glass)
    nd_flint, vd_flint = _get_glass_props(flint_glass)

    nF_crown = compute_refractive_index(crown_glass, LAMBDA_F)
    nd_crown_calc = compute_refractive_index(crown_glass, LAMBDA_d)
    nC_crown = compute_refractive_index(crown_glass, LAMBDA_C)

    nF_flint = compute_refractive_index(flint_glass, LAMBDA_F)
    nd_flint_calc = compute_refractive_index(flint_glass, LAMBDA_d)
    nC_flint = compute_refractive_index(flint_glass, LAMBDA_C)

    # Пересчитаем ν по F и C для точности
    # ν = (nd - 1) / (nF - nC)
    delta_n_crown = nF_crown - nC_crown
    delta_n_flint = nF_flint - nC_flint

    nu_crown = (nd_crown_calc - 1.0) / delta_n_crown if abs(delta_n_crown) > 1e-12 else vd_crown
    nu_flint = (nd_flint_calc - 1.0) / delta_n_flint if abs(delta_n_flint) > 1e-12 else vd_flint

    # --- Оптические силы ---
    phi_total = 1.0 / focal_length   # 1/мм

    d_nu = nu_crown - nu_flint
    if abs(d_nu) < 1e-6:
        raise ValueError(
            f"ν₁ ≈ ν₂ ({nu_crown:.2f} vs {nu_flint:.2f}): "
            f"невозможно ахроматизировать пару {crown_glass} + {flint_glass}"
        )

    phi_crown = phi_total * nu_crown / d_nu
    phi_flint = -phi_total * nu_flint / d_nu

    # --- Радиусы (метод: bended к равнопрочной форме) ---
    # Для тонкой линзы: φ = (n-1)(1/R₁ - 1/R₂)
    #
    # Схема:  R1 → crown → R2 == R3 → flint → R4
    # R2 = R3 (склейка), R4 = ∞ (плоская задняя) — простейший вариант.
    #
    # Тогда для крона:  φ_crown = (n_crown - 1) * (1/R1 - 1/R2)
    #          для флинта: φ_flint = (n_flint - 1) * (1/R3 - 1/R4)
    #                         = (n_flint - 1) * (1/R2 - 0)   при R4 = ∞
    #                         = (n_flint - 1) / R2
    #  => R2 = (n_flint - 1) / φ_flint
    #  => R1 из φ_crown

    # Сначала R2 (склейка) из флинта при R4 = ∞:
    if abs(phi_flint) < 1e-15:
        raise ValueError("Оптическая сила флинта ≈ 0, невозможно рассчитать R2")

    R2 = (nd_flint_calc - 1.0) / phi_flint   # мм

    # Теперь R1 из крона:
    # phi_crown = (n_crown - 1) * (1/R1 - 1/R2)
    # 1/R1 = phi_crown / (n_crown - 1) + 1/R2
    inv_R1 = phi_crown / (nd_crown_calc - 1.0) + 1.0 / R2
    if abs(inv_R1) < 1e-15:
        R1 = 0.0  # плоскость
    else:
        R1 = 1.0 / inv_R1

    # --- Толщины ---
    d_crown = max(0.03 * abs(focal_length), 1.0)
    d_flint = max(0.02 * abs(focal_length), 0.5)

    # --- Апертура ---
    if aperture <= 0:
        aperture = focal_length / 5.0
    semi_d = aperture / 2.0

    # --- Задний отрезок (приближённо) ---
    # Для тонкого дублета BFD ≈ f', но с толщинами чуть меньше.
    # Уточним через параксиальный расчёт ниже.
    bfd_approx = focal_length - d_crown - d_flint
    if bfd_approx < 1.0:
        bfd_approx = focal_length * 0.9

    # --- Сборка системы ---
    sys = OpticalSystem(
        name=f"Ахромат f'={focal_length:.1f} {crown_glass}+{flint_glass}",
        object_type=ObjectType.INFINITE,
        object_height=5.0,
    )

    sys.wavelengths = [
        Wavelength(LAMBDA_d, 1.0, "d"),
        Wavelength(LAMBDA_F, 1.0, "F"),
        Wavelength(LAMBDA_C, 1.0, "C"),
    ]
    sys.field_points = [
        FieldPoint(0.0),
        FieldPoint(3.0),
    ]
    sys.aperture_type = ApertureType.ENTRANCE_PUPIL
    sys.aperture_value = aperture
    sys.stop_surface = 1

    # S1: передняя поверхность крона
    # S2: склейка (крон → флинт), R2 = R3
    # S3: задняя поверхность флинта → воздух (R4 = ∞)
    sys.surfaces = [
        Surface(
            radius=R1,
            thickness=d_crown,
            glass=crown_glass,
            semi_diameter=semi_d,
            surface_type=SurfaceType.SPHERE,
        ),
        Surface(
            radius=R2,
            thickness=d_flint,
            glass=flint_glass,
            semi_diameter=semi_d,
            surface_type=SurfaceType.SPHERE,
        ),
        Surface(
            radius=0.0,     # плоскость (R4 = ∞)
            thickness=bfd_approx,
            glass="",
            semi_diameter=semi_d,
            surface_type=SurfaceType.SPHERE,
        ),
    ]

    # --- Итеративная подгонка f' и заднего отрезка ---
    # paraxial_trace возвращает BFD как расстояние от плоскости изображения
    # до фокуса (BFD_code). Истинный BFD от последней поверхности = BFD_code + d_last.
    for _iteration in range(20):
        parax = paraxial_trace(sys)
        if not parax or 'focal_length' not in parax:
            break
        actual_f = parax['focal_length']
        bfd_offset = parax.get('back_focal_distance', 0)
        d_last = sys.surfaces[-1].thickness

        # Истинный BFD от последней поверхности до фокуса
        bfd_true = bfd_offset + d_last
        sys.surfaces[-1].thickness = max(bfd_true, 0.1)

        # Подправить радиусы если f' не совпадает
        rel_err = abs(actual_f - focal_length) / focal_length
        if rel_err < 0.0005:  # < 0.05% — достаточно
            break

        scale = focal_length / actual_f
        for s in sys.surfaces:
            if s.radius != 0.0:
                s.radius *= scale

    return sys


def achromat_report(sys: OpticalSystem) -> str:
    """Вернуть текстовый отчёт о системе-ахромате."""
    lines = []
    lines.append(f"Система: {sys.name}")
    lines.append(f"Поверхностей: {sys.num_surfaces}")
    lines.append("")

    # Параксиальный расчёт (d-линия)
    wl_orig = sys.wavelengths[:]
    sys.wavelengths = [Wavelength(LAMBDA_d, 1.0, "d")]
    parax = paraxial_trace(sys)
    f_prime = parax.get('focal_length', 0)
    bfd_val = parax.get('back_focal_distance', 0) + sys.surfaces[-1].thickness
    lines.append(f"Фокусное расстояние f' = {f_prime:.4f} мм")
    lines.append(f"Задний фок. отрезок    = {bfd_val:.4f} мм")
    lines.append("")

    # Ахроматизм: f'_F - f'_C
    sys.wavelengths = [Wavelength(LAMBDA_F, 1.0, "F")]
    parax_F = paraxial_trace(sys)
    f_F = parax_F.get('focal_length', 0)

    sys.wavelengths = [Wavelength(LAMBDA_C, 1.0, "C")]
    parax_C = paraxial_trace(sys)
    f_C = parax_C.get('focal_length', 0)

    sys.wavelengths = wl_orig[:]  # восстановить

    delta_f = f_F - f_C
    lines.append(f"f'_F = {f_F:.4f} мм")
    lines.append(f"f'_C = {f_C:.4f} мм")
    lines.append(f"Δf'_F-C = {delta_f:.4f} мм  ({abs(delta_f)/f_prime*100:.4f}% от f')")
    lines.append("")

    lines.append("Поверхности:")
    lines.append(f"{'№':>3}  {'R (мм)':>12}  {'d (мм)':>10}  {'Стекло':>8}  {'D/2':>8}")
    lines.append("-" * 55)
    for i, s in enumerate(sys.surfaces):
        r_str = f"{s.radius:.4f}" if s.radius != 0 else "∞"
        lines.append(f"{i+1:>3}  {r_str:>12}  {s.thickness:>10.4f}  {s.glass:>8}  {s.semi_diameter:>8.2f}")

    return "\n".join(lines)


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("Расчёт ахроматического дублета")
    print("=" * 60)

    for crown, flint in GLASS_PAIRS:
        print(f"\n--- Пара: {crown} + {flint} ---")
        system = design_achromat(100.0, crown, flint)
        print(achromat_report(system))
