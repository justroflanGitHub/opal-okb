"""
OPAL-OKB — Protocol export

Export analysis results (paraxial + Seidel) to formatted text file.

Extracted from io_utils.py during package restructuring.
"""
from optics_engine import OpticalSystem


def export_protocol(system: OpticalSystem, paraxial: dict, seidel: dict, filepath: str):
    """
    Экспортировать результаты анализа в текстовый файл (.txt).
    Формат: таблицы с параксиальными характеристиками, суммами Зейделя,
    таблица поверхностей.
    """
    lines = []
    lines.append("=" * 72)
    lines.append(f"  ПРОТОКОЛ РАСЧЁТА ОПТИЧЕСКОЙ СИСТЕМЫ")
    lines.append(f"  {system.name}")
    lines.append("=" * 72)
    lines.append("")

    # Параксиальные характеристики
    lines.append("─" * 40)
    lines.append("  ПАРАКСИАЛЬНЫЕ ХАРАКТЕРИСТИКИ")
    lines.append("─" * 40)
    f_val = paraxial.get('focal_length', 0)
    lines.append(f"  Передний фокус F                 = {-f_val:>12.4f} мм")
    lines.append(f"  Задний фокус F'                  = {f_val:>12.4f} мм")
    lines.append(f"  sF (передний фокальный отрезок)  = {paraxial.get('sF', 0):>12.4f} мм")
    lines.append(f"  sF' (задний фокальный отрезок)   = {paraxial.get('sF_prime', 0):>12.4f} мм")
    lines.append(f"  sH (перед. главная плоскость)    = {paraxial.get('sH', 0):>12.4f} мм")
    lines.append(f"  sH' (задн. главная плоскость)    = {paraxial.get('sH_prime', 0):>12.4f} мм")
    lines.append(f"  L (длина системы)                = {paraxial.get('L', 0):>12.2f} мм")
    lines.append(f"  sP (входной зрачок)              = {paraxial.get('sP', 0):>12.4f} мм")
    lines.append(f"  sP' (выходной зрачок)            = {paraxial.get('sP_prime', 0):>12.4f} мм")
    lines.append(f"  Увеличение V                     = {paraxial.get('V', 0):>12.4f}")
    lines.append(f"  f'/# (диафрагменное число)        = {paraxial.get('f_number', 0):>12.2f}")
    lines.append(f"  D входного зрачка                = {paraxial.get('entrance_pupil_diameter', 0):>12.2f} мм")
    lines.append("")

    # Суммы Зейделя
    lines.append("─" * 40)
    lines.append("  СУММЫ ЗЕЙДЕЛЯ (3-й порядок)")
    lines.append("─" * 40)
    lines.append(f"  SI   — сферическая аберрация    = {seidel.get('SI', 0):>14.6f}")
    lines.append(f"  SII  — кома                     = {seidel.get('SII', 0):>14.6f}")
    lines.append(f"  SIII — астигматизм              = {seidel.get('SIII', 0):>14.6f}")
    lines.append(f"  SIV  — кривизна поля (Петцваль) = {seidel.get('SIV', 0):>14.6f}")
    lines.append(f"  SV   — дисторсия                = {seidel.get('SV', 0):>14.6f}")
    lines.append("")

    # Таблица поверхностей
    lines.append("─" * 72)
    lines.append("  ТАБЛИЦА ПОВЕРХНОСТЕЙ")
    lines.append("─" * 72)
    header = f"  {'№':>3}  {'R (мм)':>12}  {'d (мм)':>10}  {'Стекло':>10}  {'D/2 (мм)':>9}  {'Тип':>8}"
    lines.append(header)
    lines.append("  " + "-" * 66)

    for i, s in enumerate(system.surfaces):
        r_str = f"{s.radius:.4f}" if s.radius != 0 else "∞"
        glass_str = s.glass if s.glass else "ВОЗДУХ"
        lines.append(
            f"  {i+1:>3}  {r_str:>12}  {s.thickness:>10.4f}  {glass_str:>10}  {s.semi_diameter:>9.2f}  {s.surface_type.name:>8}"
        )

    # Экранирование
    if system.obscuration_ratio > 0:
        lines.append("")
        lines.append(f"  Экранирование: {system.obscuration_ratio*100:.1f}%")

    lines.append("")
    lines.append("=" * 72)
    lines.append("  Конец протокола")
    lines.append("=" * 72)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
