"""
OPAL-OKB — Пакет R500-11: текстовые отчёты для печати (report).

ГОТОВЫЙ ФОРМАТИРОВАННЫЙ ТЕКСТ (многострочная строка ``text`` в ответе,
стиль fileio/protocol.py / ANALIZE.txt §2.9) — не сырые словари:
расчёт выполняют сестринские команды того же реестра через
``registry.execute`` (живая система передаётся служебным именем в
контексте), таблицы порта — их штатные форматтеры ``format_tab*``.
Логика расчёта не дублируется; ``export.*`` пишет таблицы в файлы,
``report.*`` собирает печатный лист в ответе (``out`` — опция записи
.txt через :func:`commands.exportio.write_text`).

- ``report.system / surfaces / fields / glasses`` — структурные
  перечни: паспорт системы, таблица поверхностей, точки поля, стёкла
  (n из каталога через ``catalog.glass.get``);
- ``report.paraxial / seidel / chromatism`` — параксиальные
  характеристики (``calc.paraxial``), суммы Зейделя (``seidel.sums``),
  хроматизм по λ (``calc.paraxial.multi_wl``);
- ``report.aberrations / spot / ee / mtf / strehl / wavefront`` —
  внеосевые аберрации по полям (``analyze.field_aberrations``), RMS
  кружка (``quality.spot.summary``), зоны энергии
  (``quality.ee.diameters``), матрица ЧКХ (``quality.mtf.matrix``),
  Штрель (``quality.strehl.summary``), СКВ волнового фронта
  (``quality.wavefront.summary``);
- ``report.quality`` — свод качества (``quality.passport`` +
  ``quality.regime``);
- ``report.tables`` — стандартные таблицы порта текстом: TABOC1/
  TABOC2/TABGL/TABPR2/TABAX3/TABBEA/TABESB/TABEAP (селектор; секции
  строятся независимо, сбой одной не роняет отчёт);
- ``report.full`` — полный свод всех секций.
"""
from commands.base import (
    ERR_INVALID_PARAM,
    ERR_UNSUPPORTED,
    CommandError,
    Param,
)
from commands.exportio import write_text
from commands.registry import Registry
from commands.systemio import (
    resolve_system,
    system_source_params,
    system_to_dict,
)
from optics_utils import get_primary_wl

# Общие хелперы пакетов R500 (правило №1): TINY, сестринские вызовы.
from commands.builtin._r500_common import TINY
from commands.builtin._r500_common import run_sibling

#: Ширина листа отчёта (как fileio/protocol.py).
REPORT_WIDTH = 72

#: Ширина линии-заголовка секции.
SECTION_WIDTH = 40

#: Ширина числовой колонки таблиц.
NUM_WIDTH = 12

#: Прочерк в колонке (величина не посчитана / луч не дошёл).
NO_VALUE = "—"

#: Ширины строки «метка = значение» (как protocol.py).
KV_LABEL_WIDTH = 34
KV_VALUE_WIDTH = 14

#: Частоты ЧКХ по умолчанию в матрице, лин/мм.
MTF_FREQS_DEFAULT = (20.0, 50.0, 100.0)

#: Частота ЧКХ по умолчанию в своде качества, лин/мм.
MTF_FREQ_DEFAULT = 50.0

#: Лучей сетки зрачка по умолчанию (своды пятна/качества).
SPOT_RAYS_DEFAULT = 20

#: Лучей веера по умолчанию (внеосевые аберрации).
FAN_RAYS_DEFAULT = 15

#: Лучей точечной диаграммы по умолчанию (зоны энергии).
EE_RAYS_DEFAULT = 100

#: Доли задержанной энергии по умолчанию (диаметры зон 50/80/90 %).
EE_FRACTIONS_DEFAULT = (0.5, 0.8, 0.9)

#: Селекторы таблиц порта: имя → (команда-источник, заголовок секции).
PORT_TABLES = {
    "taboc1": ("tables.taboc1",
               "TABOC1 — остаточные аберрации осевого пучка (§11.3)"),
    "taboc2": ("tables.taboc2",
               "TABOC2 — волновые аберрации осевого пучка (§11.3)"),
    "tabgl": ("analyze.tables.tabgl",
              "TABGL — характеристики главных лучей (§15.1)"),
    "tabpr2": ("analyze.tables.tabpr2",
               "TABPR2 — хроматизм увеличения/положения (§15.2)"),
    "tabax3": ("chrom.opal",
               "TABAX3 — OPAL-режим хроматизма (§16)"),
    "tabbea": ("vign.tabbea",
               "TABBEA — апертурные характеристики пучков (§14)"),
    "tabesb": ("beam.heights",
               "TABESB — световые высоты пучков (§14.1)"),
    "tabeap": ("beam.screen_zones",
               "TABEAP — экраны/зоны экранирования (§14.1)"),
}

#: Таблицы по умолчанию (стандартный набор осевого пучка + поля).
PORT_TABLES_DEFAULT = ("taboc1", "taboc2", "tabgl", "tabpr2")

#: Таблицы с параметром числа зон (зрачок/поле).
ZONED_TABLES = frozenset(("taboc1", "taboc2", "tabgl", "tabpr2"))

#: Таблицы, где длина волны задаётся параметром wl_main (пара λ).
WL_MAIN_TABLES = frozenset(("tabpr2", "tabax3"))

#: Метки сумм Зейделя для секции отчёта.
SEIDEL_LABELS = (
    ("SI", "сферическая аберрация"),
    ("SII", "кома"),
    ("SIII", "астигматизм"),
    ("SIV", "кривизна поля (Петцваль)"),
    ("SV", "дисторсия"),
)

#: Метки скаляров паспорта качества (quality.passport → строки свода).
PASSPORT_LABELS = (
    ("num_surfaces", "Поверхностей"),
    ("efl_mm", "Фокусное расстояние f', мм"),
    ("f_number", "Диафрагменное число F/#"),
    ("epd_mm", "Диаметр входного зрачка, мм"),
    ("bfd_mm", "Задний фокальный отрезок sF', мм"),
    ("max_field", "Максимальное поле"),
    ("num_wavelengths", "Рабочих λ"),
    ("rms_axis_mm", "RMS кружка на оси (полихром), мм"),
    ("rms_worst_mm", "RMS кружка, худшее поле (полихром), мм"),
    ("rms_worst_field", "RMS: худшее поле"),
    ("strehl_exact", "Штрель на оси (точный)"),
    ("mtf_t", "ЧКХ на частоте, меридиан."),
    ("mtf_s", "ЧКХ на частоте, сагиттал."),
    ("cutoff_lpmm", "Частота среза ЧКХ, лин/мм"),
    ("airy_diameter_um", "Диаметр диска Эйри, мкм"),
)

#: Префикс служебных имён систем в контексте (живой объект →
#: сестринская команда). Разные суффиксы исключают коллизии при
#: вложенных вызовах (report.full → секции → quality.* → mtf.curve).
_PROBE_PREFIX = "_report_"


# ============================================================
# Хелперы композиции и форматирования
# ============================================================

def _run_sibling(registry: Registry, ctx, system, tag: str, name: str,
                 args: dict = None) -> dict:
    """Выполнить сестринскую команду с живой системой в контексте
    (движок — _r500_common.run_sibling; служебный ключ ``_report_<tag>``)."""
    return run_sibling(registry, ctx, system, _PROBE_PREFIX + tag,
                       name, args)


def _num(value, decimals: int = 4, width: int = NUM_WIDTH) -> str:
    """Число в колонке отчёта; ``None`` → прочерк."""
    if value is None:
        return NO_VALUE.rjust(width)
    return f"{float(value):{width}.{decimals}f}"


def _kv(label: str, value, decimals: int = 4) -> str:
    """Строка «метка = значение» (стиль protocol.py)."""
    if isinstance(value, str):
        text = value
    elif value is None:
        text = NO_VALUE
    else:
        text = f"{float(value):{KV_VALUE_WIDTH}.{decimals}f}"
    return f"  {label:<{KV_LABEL_WIDTH}} = {text}".rstrip()


def _section(title: str) -> list:
    """Заголовок секции отчёта."""
    return ["", "─" * SECTION_WIDTH, f"  {title}", "─" * SECTION_WIDTH]


def _report(title: str, body: list) -> str:
    """Собрать печатный лист отчёта (рамка + тело)."""
    lines = ["=" * REPORT_WIDTH, f"  ОТЧЁТ: {title}", "=" * REPORT_WIDTH]
    lines.extend(body)
    lines += ["", "=" * REPORT_WIDTH, "  Конец отчёта", "=" * REPORT_WIDTH]
    return "\n".join(lines)


def _out_param() -> Param:
    """Общий хвост «куда писать» (опциональная запись .txt)."""
    return Param("out", help="файл .txt для записи отчёта (опционально)")


def _finish(payload: dict, text: str, out) -> dict:
    """Ответ отчётной команды: текст целиком (+ файл при out)."""
    payload["text"] = text
    if out:
        payload.update(write_text(text, out))
    return payload


def _wl_tag_args(wl, extra: dict = None) -> dict:
    """Аргументы сестре: λ только если задана явно."""
    args = dict(extra or {})
    if wl is not None:
        args["wl"] = wl
    return args


# ============================================================
# Секции отчёта (каждая — список строк)
# ============================================================

def _sec_system(system) -> list:
    """Паспорт системы: структура, апертура, λ, поля."""
    data = system_to_dict(system)
    lines = _section("ПАСПОРТ СИСТЕМЫ")
    lines.append(_kv("Система", data["name"] or NO_VALUE))
    if data["comment"]:
        lines.append(_kv("Комментарий", data["comment"]))
    if data["object_type"] == "FINITE":
        lines.append(_kv("Предмет", f"FINITE: s={data['object_distance']:g} мм, "
                                    f"h={data['object_height']:g} мм"))
    else:
        lines.append(_kv("Предмет", "INFINITE (дальний)"))
    lines.append(_kv("Изображение", data["image_type"]))
    lines.append(_kv("Апертура",
                     f"{data['aperture_type']} = {data['aperture_value']:g}"))
    stop = f"поверхность {data['stop_surface']}, тип {data['stop_type']}"
    if data["stop_offset"]:
        stop += f", смещение {data['stop_offset']:g} мм"
    lines.append(_kv("Диафрагма", stop))
    if data["obscuration_ratio"] > 0:
        lines.append(_kv("Экранирование",
                         f"{data['obscuration_ratio'] * 100.0:.1f} %"))
    lines.append(_kv("Режим пучка", str(data["beam_mode"])))
    lines.append(_kv("Поверхностей", str(data["num_surfaces"])))
    lines.append(_kv("Длина хода, мм", data["track_length"], decimals=3))
    wavelengths = data["wavelengths"]
    if wavelengths:
        parts = []
        for w in wavelengths:
            name = f", {w['name']}" if w["name"] else ""
            parts.append(f"{w['value']:.5f} мкм (вес {w['weight']:g}{name})")
        lines.append(_kv(f"Рабочие λ ({len(wavelengths)})", "; ".join(parts)))
    else:
        lines.append(_kv("Рабочие λ", "нет (монохромный расчёт)"))
    fields = data["field_points"]
    if fields:
        parts = [f"Y={fp['y']:g}" + (f"/X={fp['x']:g}" if fp["x"] else "")
                 + f" (вес {fp['weight']:g})" for fp in fields]
        lines.append(_kv(f"Точки поля ({len(fields)})", "; ".join(parts)))
    else:
        lines.append(_kv("Точки поля", "нет (осевая система)"))
    return lines


def _sec_surfaces(system) -> list:
    """Таблица поверхностей (как protocol.py, + коника/асферика)."""
    lines = _section("ТАБЛИЦА ПОВЕРХНОСТЕЙ")
    lines.append(f"  {'№':>3}  {'R, мм':>12}  {'d, мм':>10}  "
                 f"{'Стекло':>10}  {'D/2, мм':>9}  {'Тип':>8}")
    lines.append("  " + "-" * (REPORT_WIDTH - 4))
    for i, s in enumerate(system.surfaces):
        radius = f"{s.radius:.4f}" if s.radius != 0 else "∞"
        glass = s.glass if s.glass else "ВОЗДУХ"
        lines.append(f"  {i:>3}  {radius:>12}  {s.thickness:>10.4f}  "
                     f"{glass:>10}  {s.semi_diameter:>9.2f}  "
                     f"{s.surface_type.name:>8}")
        extras = []
        if s.conic_constant:
            extras.append(f"коника K={s.conic_constant:g}")
        if s.aspheric_coeffs:
            extras.append(f"асферика: {len(s.aspheric_coeffs)} коэфф.")
        if s.tilt_x or s.tilt_y or s.tilt_z:
            extras.append("наклон")
        if s.decenter_x or s.decenter_y:
            extras.append("децентр")
        if extras:
            lines.append(f"      пов.{i}: " + ", ".join(extras))
    return lines


def _sec_fields(system) -> list:
    """Перечень точек поля."""
    lines = _section("ТОЧКИ ПОЛЯ")
    fields = list(system.field_points or [])
    if not fields:
        lines.append("  точек поля нет — система осевая")
        return lines
    lines.append(f"  {'№':>3}  {'Y':>10}  {'X':>10}  {'вес':>8}")
    lines.append("  " + "-" * 46)
    for i, fp in enumerate(fields):
        lines.append(f"  {i:>3}  {fp.y:>10.4f}  {fp.x:>10.4f}  "
                     f"{fp.weight:>8.3f}")
    lines.append(f"  максимальное поле: "
                 f"{max(abs(fp.y) for fp in fields):.4f}")
    return lines


def _sec_glasses(registry: Registry, ctx, system) -> list:
    """Перечень стёкол: где используются + n из каталога (сестра)."""
    wl = get_primary_wl(system)
    where = {}
    for i, s in enumerate(system.surfaces):
        if s.glass:
            where.setdefault(s.glass, []).append(i)
    lines = _section("СТЁКЛА СИСТЕМЫ")
    if not where:
        lines.append("  поверхности без стёкол (воздушный канал)")
        return lines
    lines.append(_kv("λ расчёта n, мкм", wl, decimals=5))
    lines.append(f"  {'Марка':>10}  {'Поверхности':<14}  {'n(λ)':>10}  "
                 f"{'nd':>10}  Источник")
    lines.append("  " + "-" * (REPORT_WIDTH - 4))
    for glass, indexes in sorted(where.items()):
        surf_text = ",".join(str(i) for i in indexes)
        result = registry.execute(
            "catalog.glass.get", ctx, {"name": glass, "wl": wl})
        if result.ok:
            info = result.data
            lines.append(f"  {glass:>10}  {surf_text:<14}  "
                         f"{_num(info.get('n'), 6, 10)}  "
                         f"{_num(info.get('nd'), 6, 10)}  "
                         f"{info.get('source', NO_VALUE)}")
        else:
            lines.append(f"  {glass:>10}  {surf_text:<14}  "
                         f"{NO_VALUE:>10}  {NO_VALUE:>10}  "
                         f"нет в каталоге ({result.error['code']})")
    return lines


def _sec_paraxial(registry: Registry, ctx, system, wl) -> list:
    """Параксиальные характеристики (calc.paraxial, как protocol.py)."""
    data = _run_sibling(registry, ctx, system, "parax", "calc.paraxial",
                        _wl_tag_args(wl))
    lines = _section("ПАРАКСИАЛЬНЫЕ ХАРАКТЕРИСТИКИ")
    lines.append(_kv("λ расчёта, мкм", data.get("wl"), decimals=5))
    focal = data.get("focal_length")
    lines.append(_kv("Задний фокус F', мм", focal))
    lines.append(_kv("Передний фокус F, мм",
                     -focal if focal is not None else None))
    lines.append(_kv("Передний фокальный отрезок sF, мм",
                     data.get("sF")))
    lines.append(_kv("Задний фокальный отрезок sF', мм",
                     data.get("sF_prime")))
    lines.append(_kv("Передняя главная плоскость sH, мм",
                     data.get("sH")))
    lines.append(_kv("Задняя главная плоскость sH', мм",
                     data.get("sH_prime")))
    lines.append(_kv("Задний фокальный отрезок (BFD), мм",
                     data.get("back_focal_distance")))
    lines.append(_kv("Длина системы L, мм", data.get("L"), decimals=2))
    lines.append(_kv("Входной зрачок sP, мм", data.get("sP")))
    lines.append(_kv("Выходной зрачок sP', мм", data.get("sP_prime")))
    lines.append(_kv("Увеличение V", data.get("V")))
    lines.append(_kv("Диафрагменное число F/#", data.get("f_number"),
                     decimals=2))
    lines.append(_kv("Диаметр входного зрачка, мм",
                     data.get("entrance_pupil_diameter"), decimals=2))
    lines.append(_kv("Увеличение зрачков", data.get("pupil_magnification")))
    return lines


def _sec_seidel(registry: Registry, ctx, system, wl) -> list:
    """Суммы Зейделя + хроматические (seidel.sums)."""
    data = _run_sibling(registry, ctx, system, "seidel", "seidel.sums",
                        _wl_tag_args(wl))
    lines = _section("СУММЫ ЗЕЙДЕЛЯ (3-Й ПОРЯДОК)")
    lines.append(_kv("λ расчёта, мкм", data.get("wl"), decimals=5))
    for key, name in SEIDEL_LABELS:
        lines.append(_kv(f"{key} — {name}", data.get(key), decimals=6))
    lines.append(_kv("SIхр — хроматизм положения", data.get("SIxp"),
                     decimals=6))
    lines.append(_kv("SIIхр — хроматизм увеличения", data.get("SIIxp"),
                     decimals=6))
    if data.get("wl_lo") is not None and data.get("wl_hi") is not None:
        lines.append(_kv("Пара λ хроматизма, мкм",
                         f"{data['wl_lo']:.5f} … {data['wl_hi']:.5f}"))
    return lines


def _sec_chromatism(registry: Registry, ctx, system) -> list:
    """Хроматизм положения по рабочим λ (calc.paraxial.multi_wl)."""
    data = _run_sibling(registry, ctx, system, "chrom",
                        "calc.paraxial.multi_wl")
    results = data.get("results") or []
    lines = _section("ХРОМАТИЗМ ПО РАБОЧИМ λ")
    if not results:
        lines.append("  рабочие λ не заданы")
        return lines
    lines.append(f"  {'λ, мкм':>10}  {'f\', мм':>12}  {'sF\', мм':>12}  "
                 f"{'F/#':>10}  {'BFD, мм':>12}")
    lines.append("  " + "-" * 62)
    for row in results:
        f_number = row.get("f_number")
        lines.append(f"  {row.get('wl', 0.0):>10.5f}  "
                     f"{_num(row.get('focal_length'))}  "
                     f"{_num(row.get('sF_prime'))}  "
                     f"{_num(f_number, 3, 10)}  "
                     f"{_num(row.get('back_focal_distance'))}")
    if len(results) >= 2:
        focals = [float(r["focal_length"]) for r in results
                  if r.get("focal_length") is not None]
        if len(focals) >= 2:
            spread = max(focals) - min(focals)
            denom = min(abs(v) for v in focals)
            lines.append("")
            lines.append(_kv("Разброс f' между крайними λ, мм", spread))
            if denom > TINY:
                lines.append(_kv("Относительный хроматизм f', %",
                                 spread / denom * 100.0, decimals=3))
    return lines


def _sec_aberrations(registry: Registry, ctx, system, wl, fields,
                     num_fan_rays) -> list:
    """Внеосевые аберрации по полям (analyze.field_aberrations)."""
    args = {"num_fan_rays": num_fan_rays}
    if fields:
        args["fields"] = fields
    data = _run_sibling(registry, ctx, system, "aber",
                        "analyze.field_aberrations", _wl_tag_args(wl, args))
    lines = _section("ВНЕОСЕВЫЕ АБЕРРАЦИИ ПО ПОЛЯМ")
    lines.append(_kv("λ, мкм", data.get("wl"), decimals=5))
    lines.append(f"  {'поле':>8}  {'дист, %':>10}  {'Z\'m, мм':>11}  "
                 f"{'Z\'s, мм':>11}  {'астигм, мм':>11}  {'кома':>10}")
    lines.append("  " + "-" * 66)
    for row in data.get("fields") or []:
        lines.append(f"  {row['field_y']:>8.3f}  "
                     f"{_num(row.get('distortion'), 3, 10)}  "
                     f"{_num(row.get('z_m'))}  "
                     f"{_num(row.get('z_s'))}  "
                     f"{_num(row.get('astigmatism'))}  "
                     f"{_num(row.get('coma'), 5, 10)}")
    return lines


def _sec_spot(registry: Registry, ctx, system, fields, num_rays) -> list:
    """RMS кружка рассеяния по полям и λ (quality.spot.summary)."""
    args = {"num_rays": num_rays}
    if fields:
        args["fields"] = fields
    data = _run_sibling(registry, ctx, system, "spot",
                        "quality.spot.summary", args)
    rows = data.get("rows") or []
    lines = _section("RMS КРУЖКА РАССЕЯНИЯ ПО ПОЛЯМ И λ (ММ)")
    if not rows:
        lines.append("  нет полей расчёта")
        return lines
    wavelengths = [entry["wl"] for entry in rows[0].get("by_wl") or []]
    head = f"  {'поле':>8}" + "".join(f"{f'λ={wl:.4g}':>13}"
                                      for wl in wavelengths) \
        + f"{'полихром':>13}"
    lines.append(head)
    lines.append("  " + "-" * (len(head) - 2))
    for row in rows:
        cells = "".join(f"{_num(entry.get('rms')):>13}"
                        for entry in row.get("by_wl") or [])
        lines.append(f"  {row['field_y']:>8.3f}{cells}"
                     f"{_num(row.get('rms_poly')):>13}")
    summary = data.get("summary") or {}
    lines.append("")
    lines.append(_kv("Худшее поле (полихром)", summary.get("max_field"),
                     decimals=3))
    lines.append(_kv("Максимальный RMS (полихром), мм",
                     summary.get("max_rms")))
    return lines


def _sec_ee(registry: Registry, ctx, system, fields, fractions,
            num_rays, wl) -> list:
    """Диаметры зон задержанной энергии (quality.ee.diameters)."""
    args = {"num_rays": num_rays}
    if fields:
        args["fields"] = fields
    if fractions:
        args["fractions"] = fractions
    data = _run_sibling(registry, ctx, system, "ee",
                        "quality.ee.diameters", _wl_tag_args(wl, args))
    rows = data.get("rows") or []
    lines = _section("ДИАМЕТРЫ ЗОН ЗАДЕРЖАННОЙ ЭНЕРГИИ (МКМ)")
    lines.append(_kv("λ, мкм", data.get("wl"), decimals=5))
    if not rows:
        lines.append("  нет полей расчёта")
        return lines
    parts = [entry["fraction"] for entry in rows[0].get("diameters") or []]
    head = f"  {'поле':>8}" + "".join(f"D{f * 100:g}%".rjust(14)
                                      for f in parts)
    lines.append(head)
    lines.append("  " + "-" * (len(head) - 2))
    for row in rows:
        cells = "".join(f"{_num(entry.get('diameter_um'), 1, 14)}"
                        for entry in row.get("diameters") or [])
        lines.append(f"  {row['field_y']:>8.3f}{cells}")
    return lines


def _sec_mtf(registry: Registry, ctx, system, fields, freqs, wl) -> list:
    """Матрица дифракционной ЧКХ (quality.mtf.matrix)."""
    args = {"freqs": freqs}
    if fields:
        args["fields"] = fields
    data = _run_sibling(registry, ctx, system, "mtf",
                        "quality.mtf.matrix", _wl_tag_args(wl, args))
    rows = data.get("rows") or []
    freq_list = [float(f) for f in data.get("freqs") or []]
    lines = _section("МАТРИЦА ДИФРАКЦИОННОЙ ЧКХ")
    lines.append(_kv("λ, мкм", data.get("wl"), decimals=5))
    lines.append(_kv("Частота среза, лин/мм", data.get("cutoff_lpmm"),
                     decimals=1))
    lines.append("  " + "".join(f"{f'ν={f:.6g}':>24}" for f in freq_list))
    head = f"  {'поле,°':>9}" + "".join(f"{'мер':>12}{'саг':>12}"
                                        for _ in freq_list)
    lines.append(head)
    lines.append("  " + "-" * (len(head) - 2))
    for row in rows:
        cells = "".join(f"{_num(entry.get('mtf_t')):>12}"
                        f"{_num(entry.get('mtf_s')):>12}"
                        for entry in row.get("mtf") or [])
        lines.append(f"  {row['field_y']:>9.3f}{cells}")
    return lines


def _sec_strehl(registry: Registry, ctx, system, fields) -> list:
    """Число Штреля по полям (quality.strehl.summary)."""
    args = {"fields": fields} if fields else {}
    data = _run_sibling(registry, ctx, system, "strehl",
                        "quality.strehl.summary", args)
    lines = _section("ЧИСЛО ШТРЕЛЯ ПО ПОЛЯМ")
    lines.append(f"  {'поле':>8}  {'точный':>12}  {'Марешаль':>12}  "
                 f"{'σ, λ':>12}")
    lines.append("  " + "-" * 50)
    for row in data.get("rows") or []:
        lines.append(f"  {row['field_y']:>8.3f}  "
                     f"{_num(row.get('strehl_exact'), 5)}  "
                     f"{_num(row.get('strehl_marechal'), 5)}  "
                     f"{_num(row.get('sigma_w'), 5)}")
    worst = data.get("worst") or {}
    lines.append("")
    lines.append(_kv("Худшее поле", worst.get("field_y"), decimals=3))
    lines.append(_kv("Штрель на худшем поле",
                     worst.get("strehl_exact"), decimals=5))
    lines.append(_kv("Средний Штрель (точный)", data.get("mean_exact"),
                     decimals=5))
    return lines


def _sec_wavefront(registry: Registry, ctx, system, wl) -> list:
    """СКВ волнового фронта по полю (quality.wavefront.summary)."""
    data = _run_sibling(registry, ctx, system, "wf",
                        "quality.wavefront.summary", _wl_tag_args(wl))
    lines = _section("СКВ ВОЛНОВОГО ФРОНТА ПО ПОЛЯМ")
    lines.append(_kv("λ, мкм", data.get("wl"), decimals=5))
    lines.append(f"  {'поле':>8}  {'СКВ, λ':>12}")
    lines.append("  " + "-" * 24)
    for row in data.get("rows") or []:
        lines.append(f"  {row['field_y']:>8.3f}  "
                     f"{_num(row.get('rms_wl'), 5)}")
    lines.append("")
    lines.append(_kv("Максимум СКВ, λ", data.get("max_rms_wl"), decimals=5))
    lines.append(_kv("Поле максимума", data.get("max_field"), decimals=3))
    lines.append(_kv("Штрель Марешаля в максимуме",
                     data.get("strehl_marechal_max"), decimals=5))
    return lines


def _sec_quality(registry: Registry, ctx, system, freq_lpmm,
                 num_rays) -> list:
    """Свод качества: паспорт + режим ограничения (quality.*)."""
    passport = _run_sibling(registry, ctx, system, "qpass",
                            "quality.passport",
                            {"freq_lpmm": freq_lpmm,
                             "num_rays": num_rays})
    regime = _run_sibling(registry, ctx, system, "qregime",
                          "quality.regime", {"num_rays": num_rays})
    lines = _section("СВОД КАЧЕСТВА")
    for key, label in PASSPORT_LABELS:
        lines.append(_kv(label, passport.get(key)))
    lines.append(_kv("Частота ЧКХ свода, лин/мм", freq_lpmm, decimals=1))
    lines.append("")
    regime_labels = {
        "diffraction_limited": "ограничена дифракцией",
        "aberration_limited": "ограничена аберрациями",
        "comparable": "сопоставимо (дифракция ~ аберрации)",
    }
    label = regime_labels.get(regime.get("regime"), regime.get("regime"))
    lines.append(_kv("Пятно на оси", label))
    lines.append(_kv("Радиус диска Эйри, мкм",
                     regime.get("airy_radius_um"), decimals=2))
    lines.append(_kv("RMS пятна (полихром), мкм", regime.get("rms_um"),
                     decimals=2))
    lines.append(_kv("Отношение RMS/Эйри", regime.get("ratio"),
                     decimals=2))
    return lines


def _table_args(table: str, wl, n_zones) -> dict:
    """Аргументы команды-источника таблицы порта."""
    args = {}
    if wl is not None:
        key = "wl_main" if table in WL_MAIN_TABLES else "wl"
        args[key] = wl
    if n_zones is not None and table in ZONED_TABLES:
        args["n_zones"] = int(n_zones)
    return args


def _sec_tables(registry: Registry, ctx, system, tables, wl,
                n_zones) -> tuple:
    """Таблицы порта текстом; возврат (строки, включённые, сбойные)."""
    lines = _section("СТАНДАРТНЫЕ ТАБЛИЦЫ ПОРТА")
    included, failed = [], []
    for name in tables:
        command, title = PORT_TABLES[name]
        lines.append("")
        lines.append(f"  ── {title}")
        try:
            data = _run_sibling(registry, ctx, system, f"tbl_{name}",
                                command, _table_args(name, wl, n_zones))
            text = data.get("text")
            if text is None:
                raise CommandError(
                    ERR_UNSUPPORTED,
                    f"{command} не имеет текстового формата")
            lines.extend(str(text).splitlines())
        except CommandError as exc:
            lines.append(f"  [таблица не построена: {exc.message}]")
            failed.append({"table": name, "error": exc.message})
            continue
        included.append(name)
    return lines, included, failed


# ============================================================
# Регистрация команд
# ============================================================

def register(registry: Registry) -> None:
    """Зарегистрировать команды отчётов (R500-11)."""

    # ============================================================
    # Структурные перечни системы
    # ============================================================

    @registry.command(
        "report.system", category="report",
        description="Паспорт системы текстом: предмет/изображение, "
                    "апертура, диафрагма, экранирование, рабочие λ, "
                    "точки поля, габарит",
        returns="{name, num_surfaces, text, out?}",
        params=system_source_params() + [_out_param()])
    def report_system(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ПАСПОРТ СИСТЕМЫ", _sec_system(sys_obj))
        return _finish({"name": getattr(sys_obj, "name", None),
                        "num_surfaces": sys_obj.num_surfaces},
                       text, out)

    @registry.command(
        "report.surfaces", category="report",
        description="Таблица поверхностей текстом: №, R, d, стекло, "
                    "полудиаметр, тип (+ коника/асферика/наклоны)",
        returns="{num_surfaces, text, out?}",
        params=system_source_params() + [_out_param()])
    def report_surfaces(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ТАБЛИЦА ПОВЕРХНОСТЕЙ", _sec_surfaces(sys_obj))
        return _finish({"num_surfaces": sys_obj.num_surfaces},
                       text, out)

    @registry.command(
        "report.fields", category="report",
        description="Перечень точек поля текстом: №, Y, X, вес + "
                    "максимальное поле",
        returns="{count, text, out?}",
        params=system_source_params() + [_out_param()])
    def report_fields(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ТОЧКИ ПОЛЯ", _sec_fields(sys_obj))
        return _finish(
            {"count": len(sys_obj.field_points or [])}, text, out)

    @registry.command(
        "report.glasses", category="report",
        description="Перечень стёкол системы текстом: марки, "
                    "поверхности использования, n(λ) и nd из каталога",
        returns="{count, wl, text, out?}",
        params=system_source_params() + [_out_param()])
    def report_glasses(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("СТЁКЛА СИСТЕМЫ",
                       _sec_glasses(registry, ctx, sys_obj))
        glasses = {s.glass for s in sys_obj.surfaces if s.glass}
        return _finish({"count": len(glasses),
                        "wl": get_primary_wl(sys_obj)}, text, out)

    # ============================================================
    # Параксиал / Зейдель / хроматизм
    # ============================================================

    @registry.command(
        "report.paraxial", category="report",
        description="Параксиальные характеристики текстом (calc.paraxial): "
                    "фокусы, кардинальные отрезки, зрачки, F/#, увеличение",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            _out_param(),
        ])
    def report_paraxial(ctx, file, system, lbo_index, lbo_name, wl, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ПАРАКСИАЛЬНЫЕ ХАРАКТЕРИСТИКИ",
                       _sec_paraxial(registry, ctx, sys_obj, wl))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj)}, text, out)

    @registry.command(
        "report.seidel", category="report",
        description="Суммы Зейделя текстом (seidel.sums): SI..SV + "
                    "хроматические SIхр/SIIхр и пара λ",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            _out_param(),
        ])
    def report_seidel(ctx, file, system, lbo_index, lbo_name, wl, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("СУММЫ ЗЕЙДЕЛЯ",
                       _sec_seidel(registry, ctx, sys_obj, wl))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj)}, text, out)

    @registry.command(
        "report.chromatism", category="report",
        description="Хроматизм положения по рабочим λ текстом "
                    "(calc.paraxial.multi_wl): f'/sF'/F/#/BFD по λ + "
                    "разброс f'",
        returns="{num_wavelengths, text, out?}",
        params=system_source_params() + [_out_param()])
    def report_chromatism(ctx, file, system, lbo_index, lbo_name, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ХРОМАТИЗМ ПО РАБОЧИМ λ",
                       _sec_chromatism(registry, ctx, sys_obj))
        return _finish({"num_wavelengths": len(sys_obj.wavelengths)},
                       text, out)

    # ============================================================
    # Аберрации и качество по полям
    # ============================================================

    @registry.command(
        "report.aberrations", category="report",
        description="Внеосевые аберрации по полям текстом "
                    "(analyze.field_aberrations): дисторсия, Z'm/Z's, "
                    "астигматизм, кома",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            Param("num_fan_rays", type="int", default=FAN_RAYS_DEFAULT,
                  help="лучей веера на поле"),
            _out_param(),
        ])
    def report_aberrations(ctx, file, system, lbo_index, lbo_name,
                           fields, wl, num_fan_rays, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ВНЕОСЕВЫЕ АБЕРРАЦИИ",
                       _sec_aberrations(registry, ctx, sys_obj, wl,
                                        fields, num_fan_rays))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj)}, text, out)

    @registry.command(
        "report.spot", category="report",
        description="RMS кружка рассеяния по полям и λ текстом "
                    "(quality.spot.summary) + худшее поле",
        returns="{text, out?}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
            _out_param(),
        ])
    def report_spot(ctx, file, system, lbo_index, lbo_name, fields,
                    num_rays, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("RMS КРУЖКА РАССЕЯНИЯ",
                       _sec_spot(registry, ctx, sys_obj, fields, num_rays))
        return _finish({}, text, out)

    @registry.command(
        "report.ee", category="report",
        description="Диаметры зон задержанной энергии по полям текстом "
                    "(quality.ee.diameters): 50/80/90 % геометрически",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("fractions", type="list",
                  help="доли энергии; по умолчанию [0.5, 0.8, 0.9]"),
            Param("num_rays", type="int", default=EE_RAYS_DEFAULT,
                  help="лучей точечной диаграммы"),
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            _out_param(),
        ])
    def report_ee(ctx, file, system, lbo_index, lbo_name, fields,
                  fractions, num_rays, wl, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ЗОНЫ ЗАДЕРЖАННОЙ ЭНЕРГИИ",
                       _sec_ee(registry, ctx, sys_obj, fields, fractions,
                               num_rays, wl))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj)}, text, out)

    @registry.command(
        "report.mtf", category="report",
        description="Матрица дифракционной ЧКХ текстом "
                    "(quality.mtf.matrix): частоты × поля, сечения "
                    "мер/саг, частота среза",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("freqs", type="list",
                  help="частоты, лин/мм; по умолчанию [20, 50, 100]"),
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            _out_param(),
        ])
    def report_mtf(ctx, file, system, lbo_index, lbo_name, freqs,
                   fields, wl, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        freq_list = [float(f) for f in freqs] if freqs \
            else list(MTF_FREQS_DEFAULT)
        text = _report("МАТРИЦА ЧКХ",
                       _sec_mtf(registry, ctx, sys_obj, fields, freq_list,
                                wl))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj),
                        "freqs": freq_list}, text, out)

    @registry.command(
        "report.strehl", category="report",
        description="Число Штреля по полям текстом "
                    "(quality.strehl.summary): точный/Марешаль/σ + "
                    "худшее поле и средний",
        returns="{text, out?}",
        params=system_source_params() + [
            Param("fields", type="list",
                  help="список полей; по умолчанию — поля системы"),
            _out_param(),
        ])
    def report_strehl(ctx, file, system, lbo_index, lbo_name, fields, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("ЧИСЛО ШТРЕЛЯ",
                       _sec_strehl(registry, ctx, sys_obj, fields))
        return _finish({}, text, out)

    @registry.command(
        "report.wavefront", category="report",
        description="СКВ волнового фронта по полям текстом "
                    "(quality.wavefront.summary) + Марешаль в максимуме",
        returns="{wl, text, out?}",
        params=system_source_params() + [
            Param("wl", type="float",
                  help="λ, мкм (по умолчанию — основная λ системы)"),
            _out_param(),
        ])
    def report_wavefront(ctx, file, system, lbo_index, lbo_name, wl, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("СКВ ВОЛНОВОГО ФРОНТА",
                       _sec_wavefront(registry, ctx, sys_obj, wl))
        return _finish({"wl": wl if wl is not None
                        else get_primary_wl(sys_obj)}, text, out)

    @registry.command(
        "report.quality", category="report",
        description="Свод качества текстом: паспорт системы "
                    "(quality.passport: f', F/#, RMS, Штрель, ЧКХ, Эйри) "
                    "+ режим ограничения пятна (quality.regime)",
        returns="{freq_lpmm, text, out?}",
        params=system_source_params() + [
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ свода, лин/мм"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка"),
            _out_param(),
        ])
    def report_quality(ctx, file, system, lbo_index, lbo_name,
                       freq_lpmm, num_rays, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        text = _report("СВОД КАЧЕСТВА",
                       _sec_quality(registry, ctx, sys_obj, freq_lpmm,
                                    num_rays))
        return _finish({"freq_lpmm": freq_lpmm}, text, out)

    # ============================================================
    # Таблицы порта и полный свод
    # ============================================================

    @registry.command(
        "report.tables", category="report",
        description="Стандартные таблицы порта текстом: TABOC1/TABOC2/"
                    "TABGL/TABPR2/TABAX3/TABBEA/TABESB/TABEAP (селектор; "
                    "сбой секции не роняет отчёт)",
        returns="{tables, included, failed?, text, out?}",
        params=system_source_params() + [
            Param("tables", type="list",
                  help=f"селектор таблиц; по умолчанию "
                       f"{list(PORT_TABLES_DEFAULT)}; допустимо "
                       f"{list(PORT_TABLES)}"),
            Param("wl", type="float",
                  help="λ, мкм для всех таблиц (по умолчанию — каждая "
                       "берёт свою основную λ)"),
            Param("n_zones", type="int",
                  help="число зон зрачка/поля (TABOC1/2, TABGL, TABPR2)"),
            _out_param(),
        ])
    def report_tables(ctx, file, system, lbo_index, lbo_name, tables, wl,
                      n_zones, out):
        names = [str(t).strip().lower() for t in tables] if tables \
            else list(PORT_TABLES_DEFAULT)
        unknown = [t for t in names if t not in PORT_TABLES]
        if unknown:
            raise CommandError(
                ERR_INVALID_PARAM,
                f"неизвестные таблицы {unknown}; допустимо: "
                f"{list(PORT_TABLES)}")
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        body, included, failed = _sec_tables(registry, ctx, sys_obj,
                                             names, wl, n_zones)
        text = _report("ТАБЛИЦЫ ПОРТА", body)
        payload = {"tables": names, "included": included}
        if failed:
            payload["failed"] = failed
        return _finish(payload, text, out)

    @registry.command(
        "report.full", category="report",
        description="Полный свод текстом: паспорт, поверхности, поля, "
                    "стёкла, параксиал, Зейдель, хроматизм, аберрации, "
                    "RMS пятна, зоны энергии, ЧКХ, Штрель, волновой "
                    "фронт, качество, таблицы порта",
        returns="{sections, failed?, text, out?}",
        params=system_source_params() + [
            Param("freq_lpmm", type="float", default=MTF_FREQ_DEFAULT,
                  help="частота ЧКХ свода, лин/мм"),
            Param("num_rays", type="int", default=SPOT_RAYS_DEFAULT,
                  help="лучей сетки зрачка (своды пятна/качества)"),
            _out_param(),
        ])
    def report_full(ctx, file, system, lbo_index, lbo_name, freq_lpmm,
                    num_rays, out):
        sys_obj = resolve_system(ctx, file, system, lbo_index, lbo_name)
        plan = (
            ("паспорт", lambda: _sec_system(sys_obj)),
            ("поверхности", lambda: _sec_surfaces(sys_obj)),
            ("поля", lambda: _sec_fields(sys_obj)),
            ("стёкла", lambda: _sec_glasses(registry, ctx, sys_obj)),
            ("параксиал", lambda: _sec_paraxial(registry, ctx, sys_obj,
                                                None)),
            ("зейдель", lambda: _sec_seidel(registry, ctx, sys_obj,
                                            None)),
            ("хроматизм", lambda: _sec_chromatism(registry, ctx,
                                                  sys_obj)),
            ("аберрации", lambda: _sec_aberrations(
                registry, ctx, sys_obj, None, None, FAN_RAYS_DEFAULT)),
            ("пятно", lambda: _sec_spot(registry, ctx, sys_obj, None,
                                        num_rays)),
            ("зоны энергии", lambda: _sec_ee(
                registry, ctx, sys_obj, None, None, num_rays, None)),
            ("чкх", lambda: _sec_mtf(registry, ctx, sys_obj, None,
                                     list(MTF_FREQS_DEFAULT), None)),
            ("штрель", lambda: _sec_strehl(registry, ctx, sys_obj,
                                           None)),
            ("волновой фронт", lambda: _sec_wavefront(registry, ctx,
                                                      sys_obj, None)),
            ("качество", lambda: _sec_quality(registry, ctx, sys_obj,
                                              freq_lpmm, num_rays)),
            ("таблицы", lambda: _sec_tables(
                registry, ctx, sys_obj, PORT_TABLES_DEFAULT, None,
                None)[0]),
        )
        body, sections, failed = [], [], []
        for title, build in plan:
            try:
                body.extend(build())
                sections.append(title)
            except CommandError as exc:
                body.append(f"  [секция «{title}» не построена: "
                            f"{exc.message}]")
                failed.append({"section": title, "error": exc.message})
        text = _report("ПОЛНЫЙ СВОД СИСТЕМЫ", body)
        payload = {"sections": sections}
        if failed:
            payload["failed"] = failed
        return _finish(payload, text, out)
