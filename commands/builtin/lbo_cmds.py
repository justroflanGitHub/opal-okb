"""
OPAL-OKB — Пакет R500-3: библиотеки систем и сравнение файлов.

- ``file.lbo.*`` — работа с .LBO-библиотеками OPAL-PC (записи .OPJ):
  список/поиск/выборка/извлечение (движок ``fileio/lbo_io.py``,
  выбор записи — ``commands.systemio._pick_lbo_entry``);
- ``library.*`` — единая библиотека проекта (``catalog/library.py``):
  категории, записи, поиск, загрузка в контекст, пакетные прогоны по
  LBO с фильтром (ТЗ TASK_REGISTRY_500 §2.4) и метриками поверх
  существующих движков;
- ``file.diff`` / ``file.compare.*`` — сравнение двух систем
  (структура, параксиал, Зейдель, пятно); ``file.checksum``.

LBO-данные локальны (extracted/, в git не входят) — тесты пакета
маркируются ``requires_lbo`` (конвенция conftest).
"""
import hashlib
import os

from commands.base import (
    ERR_INVALID_PARAM,
    ERR_IO_ERROR,
    ERR_NOT_FOUND,
    Param,
    CommandError,
)
from commands.registry import Registry
from commands.systemio import (
    _pick_lbo_entry,
    _load_lbo_entries,
    lbo_entry_info,
    resolve_system,
    save_system,
    system_source_params,
    system_to_dict,
)

#: Метрики library.batch → (поля строк, вычислитель системы).
BATCH_METRIC_FIELDS = {
    "surfaces": ("num_surfaces", "track_length"),
    "paraxial": ("efl", "f_number", "track_length"),
    "seidel": ("SI", "SII", "SIII", "SIV", "SV"),
    "spot_rms": ("rms",),
}
BATCH_METRIC_CHOICES = tuple(BATCH_METRIC_FIELDS)

#: Лимит строк пакетного прогона по умолчанию.
BATCH_LIMIT_DEFAULT = 50

#: Максимум различий в ответе file.diff.
DIFF_MAX_REPORTED = 50

#: Алгоритмы file.checksum.
CHECKSUM_ALGOS = ("md5", "sha1", "sha256")


def _load_batch_systems(path: str, name_filter, limit):
    """Разобранные записи LBO → [(имя, OpticalSystem|None, warnings)]."""
    entries = _load_lbo_entries(path)
    rows = []
    for entry in entries:
        name = entry.get("filename", "") or entry.get("name", "")
        if name_filter and name_filter.lower() not in name.lower():
            continue
        system = entry.get("system")
        rows.append((name, system, entry.get("warnings") or []))
        if limit and len(rows) >= limit:
            break
    if not rows:
        raise CommandError(
            ERR_NOT_FOUND,
            f"в {path!r} не найдено записей"
            + (f" по фильтру {name_filter!r}" if name_filter else ""))
    return rows


def _metric_row(name, system, warnings, metric: str) -> dict:
    """Строка библиотечного прогона: метрика поверх существующего движка."""
    row = {"name": name,
           "ok": system is not None and bool(system.surfaces),
           "warnings": warnings[:3]}
    if not row["ok"]:
        return row
    if metric == "surfaces":
        row["num_surfaces"] = system.num_surfaces
        row["track_length"] = sum(s.thickness for s in system.surfaces)
    elif metric == "paraxial":
        from domain.calculations import paraxial_trace
        parax = paraxial_trace(system)
        row["efl"] = parax.get("focal_length")
        row["f_number"] = parax.get("f_number")
        row["track_length"] = sum(s.thickness for s in system.surfaces)
    elif metric == "seidel":
        from domain.calculations import seidel_aberrations
        sums = seidel_aberrations(system)
        for key in ("SI", "SII", "SIII", "SIV", "SV"):
            row[key] = sums.get(key)
    elif metric == "spot_rms":
        from analysis.aberrations import compute_rms_spot, compute_spot_diagram
        spots = compute_spot_diagram(system, num_rays=20)
        row["rms"] = compute_rms_spot(spots)
    return row


def _find_library_entry(query: str, category):
    """Запись библиотеки по подстроке (имя/генератор/файл); категория
    опциональна."""
    from catalog.library import build_library
    library = build_library()
    matches = []
    q = query.lower()
    for cat_name, entries in library.items():
        if category and cat_name != category:
            continue
        for e in entries:
            hay = " ".join(filter(None, (
                e.get("name"), e.get("generator"),
                os.path.basename(e.get("file") or ""),
                e.get("lbo_name") or ""))).lower()
            if q in hay:
                matches.append((cat_name, e))
    if not matches:
        raise CommandError(
            ERR_NOT_FOUND,
            f"запись {query!r} не найдена в библиотеке"
            + (f" (категория {category!r})" if category else ""))
    return matches


def register(registry: Registry) -> None:
    """Зарегистрировать команды LBO/библиотеки/сравнения (R500-3)."""

    # ============================================================
    # file.lbo.* — записи .LBO-библиотек
    # ============================================================

    @registry.command(
        "file.lbo.info", category="lbo",
        description="Метаданные .LBO-файла: размер, число записей",
        returns="{path, name, size, num_systems}",
        params=[Param("file", required=True, help="путь к .lbo")])
    def file_lbo_info(ctx, file):
        from fileio.lbo_io import get_lbo_info
        try:
            return get_lbo_info(file)
        except OSError as exc:
            raise CommandError(ERR_IO_ERROR, f"{file}: {exc}") from exc

    @registry.command(
        "file.lbo.list", category="lbo",
        description="Записи .LBO-библиотеки: имена файлов, описания, "
                    "поверхности, предупреждения парсера",
        returns="{count, ok, entries: [...]}",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("limit", type="int",
                  help="максимум записей (по умолчанию — все)"),
        ])
    def file_lbo_list(ctx, file, limit):
        entries = _load_lbo_entries(file)
        infos = [dict(index=i, **lbo_entry_info(e))
                 for i, e in enumerate(entries)]
        if limit:
            infos = infos[:max(0, limit)]
        return {"count": len(entries),
                "ok": sum(1 for e in entries if e.get("system")),
                "entries": infos}

    @registry.command(
        "file.lbo.count", category="lbo",
        description="Число записей .LBO и сколько разобрано в системы",
        returns="{count, ok, broken}",
        params=[Param("file", required=True, help="путь к .lbo")])
    def file_lbo_count(ctx, file):
        entries = _load_lbo_entries(file)
        ok = sum(1 for e in entries if e.get("system"))
        return {"count": len(entries), "ok": ok,
                "broken": len(entries) - ok}

    @registry.command(
        "file.lbo.get", category="lbo",
        description="Система из записи .LBO (по имени записи или индексу)",
        returns="полная сериализация системы + метаданные записи",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("index", type="int", default=0,
                  help="индекс записи (0-based)"),
            Param("name", help="имя .OPJ-записи (приоритетнее index)"),
        ])
    def file_lbo_get(ctx, file, index, name):
        entry = _pick_lbo_entry(_load_lbo_entries(file), name, index, file)
        result = {"entry": lbo_entry_info(entry)}
        if entry.get("system") is not None:
            result["system"] = system_to_dict(entry["system"])
        return result

    @registry.command(
        "file.lbo.search", category="lbo",
        description="Поиск записей .LBO по подстроке (имя файла/описание)",
        returns="{total, entries: [...]}",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("query", required=True, help="подстрока поиска"),
            Param("limit", type="int", default=50,
                  help="максимум записей в ответе"),
        ])
    def file_lbo_search(ctx, file, query, limit):
        q = query.lower()
        entries = _load_lbo_entries(file)
        found = []
        for i, e in enumerate(entries):
            info = lbo_entry_info(e)
            if q in info["filename"].lower() or q in info["name"].lower() \
                    or q in info["description"].lower():
                found.append(dict(index=i, **info))
        return {"total": len(found),
                "entries": found[:max(0, limit)]}

    @registry.command(
        "file.lbo.save", category="lbo",
        description="Извлечь запись .LBO в файл .opj/.json",
        returns="{out, format, name}",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("out", required=True, help="куда сохранить"),
            Param("index", type="int", default=0, help="индекс записи"),
            Param("name", help="имя .OPJ-записи (приоритетнее index)"),
        ])
    def file_lbo_save(ctx, file, out, index, name):
        entry = _pick_lbo_entry(_load_lbo_entries(file), name, index, file)
        return {"out": save_system(entry["system"], out),
                "format": os.path.splitext(out)[1].lstrip(".").lower(),
                "name": entry.get("filename", "")}

    @registry.command(
        "file.lbo.save_all", category="lbo",
        description="Распаковать все записи .LBO в каталог (.opj)",
        returns="{dir, saved, broken, names: [...]}",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("dir", required=True, help="каталог назначения"),
        ])
    def file_lbo_save_all(ctx, file, dir):
        os.makedirs(dir, exist_ok=True)
        saved, broken = [], []
        for entry in _load_lbo_entries(file):
            system = entry.get("system")
            filename = entry.get("filename") or f"entry_{len(saved) + len(broken)}.OPJ"
            if system is None or not getattr(system, "surfaces", None):
                broken.append(filename)
                continue
            stem = os.path.splitext(os.path.basename(filename))[0]
            out = os.path.join(dir, stem + ".opj")
            save_system(system, out)
            saved.append(out)
        return {"dir": os.path.abspath(dir), "saved": len(saved),
                "broken": len(broken), "names": saved[:BATCH_LIMIT_DEFAULT]}

    @registry.command(
        "file.lbo.scan", category="lbo",
        description="Сканировать каталог с .LBO-библиотеками (без разбора "
                    "записей)",
        returns="{count, libraries: [{name, num_systems, size, path}]}",
        params=[Param("dir", required=True, help="каталог с .lbo")])
    def file_lbo_scan(ctx, dir):
        from fileio.lbo_io import scan_lbo_directory
        libs = scan_lbo_directory(dir)
        if not libs and not os.path.isdir(dir):
            raise CommandError(ERR_IO_ERROR, f"каталог {dir!r} не найден")
        return {"count": len(libs), "libraries": libs}

    # ============================================================
    # library.* — единая библиотека проекта
    # ============================================================

    @registry.command(
        "library.summary", category="library",
        description="Библиотека систем: категории, счётчики, итог",
        returns="{categories: [{name, count}], total}",
        params=[])
    def library_summary(ctx):
        from commands.builtin.catalog_cmds import _library_summary
        return _library_summary()

    @registry.command(
        "library.categories", category="library",
        description="Категории библиотеки с числом записей",
        returns="список {name, count}",
        params=[])
    def library_categories(ctx):
        from commands.builtin.catalog_cmds import _library_summary
        return {"categories": [
            {"name": c["name"], "count": c["count"]}
            for c in _library_summary()["categories"]]}

    @registry.command(
        "library.entries", category="library",
        description="Записи категории библиотеки (генераторы/OPJ/LBO)",
        returns="{category, entries: [{name, file|generator|lbo_path}]}",
        params=[
            Param("category", required=True,
                  help="имя категории (см. library.categories)"),
        ])
    def library_entries(ctx, category):
        from catalog.library import build_library
        library = build_library()
        if category not in library:
            raise CommandError(
                ERR_NOT_FOUND,
                f"категории {category!r} нет; доступны: {list(library)}")
        entries = [{k: v for k, v in e.items() if k != "opj_data"}
                   for e in library[category]]
        return {"category": category, "count": len(entries),
                "entries": entries}

    @registry.command(
        "library.search", category="library",
        description="Поиск по всем категориям библиотеки (подстрока имени)",
        returns="{total, matches: [{category, name, file?, generator?}]}",
        params=[
            Param("query", required=True, help="подстрока имени"),
            Param("limit", type="int", default=50, help="максимум строк"),
        ])
    def library_search(ctx, query, limit):
        matches = [{"category": cat, **{k: v for k, v in e.items()
                                        if k != "opj_data"}}
                   for cat, e in _find_library_entry(query, None)]
        return {"total": len(matches),
                "matches": matches[:max(0, limit)]}

    @registry.command(
        "library.generators", category="library",
        description="Генераторы систем в библиотеке (параметрические)",
        returns="список {name, generator}",
        params=[])
    def library_generators(ctx):
        from catalog.library import build_library
        gens = []
        for cat, entries in build_library().items():
            for e in entries:
                if e.get("generator"):
                    gens.append({"name": e["name"],
                                 "generator": e["generator"],
                                 "category": cat})
        return {"generators": gens, "count": len(gens)}

    @registry.command(
        "library.dirs", category="library",
        description="Каталоги данных библиотеки (OPJ/LBO): пути и наличие",
        returns="{base_dir, opj_dir, lbo_dir, opj_count, lbo_count}",
        params=[])
    def library_dirs(ctx):
        from catalog.library import LBO_DIR, OPJ_DIR
        opj = ([f for f in os.listdir(OPJ_DIR)
                if f.upper().endswith(".OPJ")]
               if os.path.isdir(OPJ_DIR) else [])
        lbo = ([f for f in os.listdir(LBO_DIR)
                if f.upper().endswith(".LBO")]
               if os.path.isdir(LBO_DIR) else [])
        return {"base_dir": os.path.dirname(OPJ_DIR),
                "opj_dir": OPJ_DIR, "lbo_dir": LBO_DIR,
                "opj_count": len(opj), "lbo_count": len(lbo),
                "opj_exists": os.path.isdir(OPJ_DIR),
                "lbo_exists": os.path.isdir(LBO_DIR)}

    @registry.command(
        "library.load", category="library",
        description="Загрузить систему из библиотеки в контекст REPL "
                    "(по имени записи: генератор/.OPJ/LBO)",
        returns="{name, system} — система в контексте",
        params=[
            Param("name", required=True,
                  help="имя записи (подстрока; см. library.search)"),
            Param("category", help="ограничить категорию"),
            Param("as_name",
                  help="ключ в контексте (по умолчанию — имя записи)"),
        ])
    def library_load(ctx, name, category, as_name):
        from catalog.library import create_system_from_entry
        matches = _find_library_entry(name, category)
        cat, entry = matches[0]
        try:
            system = create_system_from_entry(entry)
        except Exception as exc:
            raise CommandError(
                ERR_NOT_FOUND,
                f"запись {entry.get('name')!r} ({cat}) не создаётся: {exc}"
            ) from exc
        key = as_name or entry.get("name") or "library_system"
        ctx.put_system(key, system)
        return {"name": key, "category": cat,
                "system": system_to_dict(system)}

    @registry.command(
        "library.batch", category="library",
        description="Пакетный прогон по записям .LBO с фильтром: метрика "
                    "поверх существующих движков (ТЗ §2.4)",
        returns="{metric, count, rows: [{name, ok, <метрики>}]}",
        params=[
            Param("file", required=True, help="путь к .lbo"),
            Param("metric", choices=list(BATCH_METRIC_CHOICES),
                  default="paraxial", help="surfaces|paraxial|seidel|spot_rms"),
            Param("filter", help="подстрока имени записи"),
            Param("limit", type="int", default=BATCH_LIMIT_DEFAULT,
                  help="максимум записей"),
        ])
    def library_batch(ctx, file, metric, filter, limit):
        rows = [_metric_row(name, system, warnings, metric)
                for name, system, warnings
                in _load_batch_systems(file, filter, limit)]
        return {"metric": metric, "count": len(rows), "rows": rows}

    # ============================================================
    # file.diff / file.compare.* / file.checksum
    # ============================================================

    @registry.command(
        "file.diff", category="file",
        description="Структурное сравнение двух систем: поверхности "
                    "(R/d/стекло), поля, λ",
        returns="{identical, differences: [{surface?, field, a, b}], count}",
        params=[
            Param("file_a", required=True, help="файл первой системы"),
            Param("file_b", required=True, help="файл второй системы"),
        ])
    def file_diff(ctx, file_a, file_b):
        from commands.systemio import load_system
        a = system_to_dict(load_system(file_a))
        b = system_to_dict(load_system(file_b))
        diffs = []
        for key in ("object_type", "aperture_type", "aperture_value",
                    "stop_surface", "obscuration_ratio", "beam_mode"):
            if a[key] != b[key]:
                diffs.append({"field": key, "a": a[key], "b": b[key]})
        for arr_name in ("wavelengths", "field_points"):
            if a[arr_name] != b[arr_name]:
                diffs.append({"field": arr_name,
                              "a": len(a[arr_name]), "b": len(b[arr_name])})
        for i in range(max(a["num_surfaces"], b["num_surfaces"])):
            sa = a["surfaces"][i] if i < a["num_surfaces"] else None
            sb = b["surfaces"][i] if i < b["num_surfaces"] else None
            for field in ("radius", "thickness", "glass", "semi_diameter",
                          "surface_type", "conic_constant"):
                va = sa[field] if sa else None
                vb = sb[field] if sb else None
                if va != vb:
                    diffs.append({"surface": i, "field": field,
                                  "a": va, "b": vb})
        return {"identical": not diffs, "count": len(diffs),
                "differences": diffs[:DIFF_MAX_REPORTED],
                "truncated": len(diffs) > DIFF_MAX_REPORTED}

    @registry.command(
        "file.compare.paraxial", category="file",
        description="Сравнение параксиальных характеристик двух систем",
        returns="строки {metric, a, b, delta}",
        params=[
            Param("file_a", required=True, help="файл первой системы"),
            Param("file_b", required=True, help="файл второй системы"),
        ])
    def file_compare_paraxial(ctx, file_a, file_b):
        from domain.calculations import paraxial_trace
        from commands.systemio import load_system
        pa = paraxial_trace(load_system(file_a))
        pb = paraxial_trace(load_system(file_b))
        rows = []
        for key in sorted(set(pa) & set(pb)):
            va, vb = pa[key], pb[key]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                rows.append({"metric": key, "a": va, "b": vb,
                             "delta": vb - va})
        return {"rows": rows, "count": len(rows)}

    @registry.command(
        "file.compare.seidel", category="file",
        description="Сравнение сумм Зейделя двух систем",
        returns="строки {sum, a, b, delta}",
        params=[
            Param("file_a", required=True, help="файл первой системы"),
            Param("file_b", required=True, help="файл второй системы"),
        ])
    def file_compare_seidel(ctx, file_a, file_b):
        from domain.calculations import seidel_aberrations
        from commands.systemio import load_system
        sa = seidel_aberrations(load_system(file_a))
        sb = seidel_aberrations(load_system(file_b))
        rows = []
        for key in sorted(set(sa) & set(sb)):
            va, vb = sa[key], sb[key]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                rows.append({"sum": key, "a": va, "b": vb,
                             "delta": vb - va})
        return {"rows": rows, "count": len(rows)}

    @registry.command(
        "file.compare.spot", category="file",
        description="Сравнение пятна рассеяния двух систем (RMS, мм)",
        returns="{a: {rms, num_points}, b: {rms, num_points}, delta_rms}",
        params=[
            Param("file_a", required=True, help="файл первой системы"),
            Param("file_b", required=True, help="файл второй системы"),
            Param("num_rays", type="int", default=30,
                  help="лучей точечной диаграммы"),
        ])
    def file_compare_spot(ctx, file_a, file_b, num_rays):
        from analysis.aberrations import (
            compute_rms_spot,
            compute_spot_diagram,
        )
        from commands.systemio import load_system
        out = {}
        for tag, path in (("a", file_a), ("b", file_b)):
            spots = compute_spot_diagram(load_system(path), num_rays=num_rays)
            out[tag] = {"rms": compute_rms_spot(spots),
                        "num_points": len(spots)}
        out["delta_rms"] = out["b"]["rms"] - out["a"]["rms"]
        return out

    @registry.command(
        "file.checksum", category="file",
        description="Контрольная сумма файла (md5/sha1/sha256)",
        returns="{file, algo, hex, size_bytes}",
        params=[
            Param("file", required=True, help="путь к файлу"),
            Param("algo", choices=list(CHECKSUM_ALGOS), default="sha256",
                  help="алгоритм хеша"),
        ])
    def file_checksum(ctx, file, algo):
        try:
            with open(file, "rb") as f:
                data = f.read()
        except OSError as exc:
            raise CommandError(ERR_IO_ERROR, f"{file}: {exc}") from exc
        digest = hashlib.new(algo, data).hexdigest()
        return {"file": os.path.abspath(file), "algo": algo,
                "hex": digest, "size_bytes": len(data)}
