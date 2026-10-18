"""
OPAL-OKB — Библиотека оптических систем
Предустановленные системы (генераторы) + OPJ файлы из архива + LBO библиотеки.
"""
import os
import sys
import glob


def _resolve_base_dir():
    """Каталог с данными extracted/opal_okb: dev-репо, каталог рядом с exe
    (портативный режим) или бандл PyInstaller (_MEIPASS)."""
    dev_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if getattr(sys, 'frozen', False):  # PyInstaller: рядом с exe → бандл → dev
        candidates = [os.path.dirname(sys.executable)]
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(meipass)
        candidates.append(dev_base)
    else:
        candidates = [dev_base]
    for base in candidates:
        if os.path.isdir(os.path.join(base, 'extracted', 'opal_okb')):
            return base
    return candidates[0]


# Базовая директория проекта — catalog/ is one level ниже корня
BASE_DIR = _resolve_base_dir()
OPJ_DIR = os.path.join(BASE_DIR, "extracted", "opal_okb")
LBO_DIR = os.path.join(BASE_DIR, "extracted", "opal_okb", "Lib")


def _scan_opj_files():
    """Сканировать директорию extracted/opal_okb/ на наличие .OPJ файлов."""
    opj_files = []
    if not os.path.isdir(OPJ_DIR):
        return opj_files
    for path in sorted(glob.glob(os.path.join(OPJ_DIR, "*.OPJ"))):
        name = os.path.splitext(os.path.basename(path))[0]
        opj_files.append({"name": name, "file": path, "generator": None})
    # Также .opj (lowercase)
    for path in sorted(glob.glob(os.path.join(OPJ_DIR, "*.opj"))):
        name = os.path.splitext(os.path.basename(path))[0]
        # Avoid duplicates
        if not any(f["name"] == name for f in opj_files):
            opj_files.append({"name": name, "file": path, "generator": None})
    return opj_files


def _scan_lbo_files():
    """Сканировать директорию Lib/ на наличие .LBO файлов (без загрузки систем)."""
    from lbo_reader import scan_lbo_directory
    lbo_entries = []
    for info in scan_lbo_directory(LBO_DIR):
        lbo_entries.append({
            "name": f"{info['name']} ({info['num_systems']})",
            "file": None,
            "lbo_path": info['path'],
            "lbo_name": info['name'],
            "num_systems": info['num_systems'],
            "generator": None,
        })
    return lbo_entries


def _load_lbo_systems(lbo_path):
    """Загрузить системы из .LBO файла (быстро, без парсинга OPJ)."""
    from lbo_reader import load_lbo_fast
    systems = load_lbo_fast(lbo_path)
    result = []
    for s in systems:
        result.append({
            "name": s['name'],
            "file": None,
            "lbo_path": lbo_path,
            "lbo_filename": s['filename'],
            "opj_data": s['opj_data'],
            "generator": None,
        })
    return result


def build_library():
    """
    Построить библиотеку оптических систем.
    
    Возвращает словарь категорий:
    {
        "Ахроматические дублеты": [...],
        "OPAL системы (.OPJ)": [...],
        "LBO библиотеки": [
            {"name": "LENS (116)", "lbo_path": "...", "is_lbo": True},
            ...
        ],
    }
    """
    library = {
        "Ахроматические дублеты": [
            {"name": "Дублет К8+ТФ5 f'=100", "file": None, "generator": "achromat_100"},
            {"name": "Дублет К8+ТФ5 f'=200", "file": None, "generator": "achromat_200"},
        ],
        "OPAL системы (.OPJ)": _scan_opj_files(),
        "LBO библиотеки": _scan_lbo_files(),
    }
    return library


def create_system_from_entry(entry):
    """
    Создать OpticalSystem из записи библиотеки.
    
    entry может быть:
    - {"generator": "achromat_100"} — генератор
    - {"file": "path/to/file.OPJ"} — standalone OPJ файл
    - {"lbo_path": "...", "opj_data": bytes} — система из LBO
    - {"lbo_path": "...", "lbo_filename": "ST01FA01.OPJ"} — загрузка из LBO по имени
    """
    if entry.get("generator"):
        return _create_from_generator(entry["generator"])
    elif entry.get("opj_data"):
        is_lbo = bool(entry.get("lbo_path"))
        return _create_from_opj_bytes(entry["opj_data"], is_lbo=is_lbo)
    elif entry.get("lbo_path") and entry.get("lbo_filename"):
        return _create_from_lbo(entry["lbo_path"], entry["lbo_filename"])
    elif entry.get("file"):
        return _create_from_opj(entry["file"])
    else:
        raise ValueError(f"Запись '{entry.get('name', '?')}' не имеет ни файла, ни генератора")


def _create_from_generator(gen_name):
    """Создать систему через генератор (achromat)."""
    from achromat import design_achromat

    if gen_name == "achromat_100":
        return design_achromat(100.0, "К8", "ТФ5")
    elif gen_name == "achromat_200":
        return design_achromat(200.0, "К8", "ТФ5")
    else:
        raise ValueError(f"Неизвестный генератор: {gen_name}")


def _create_from_opj(filepath):
    """Загрузить систему из OPJ файла.

    Standalone .OPJ встречаются в двух раскладках: «standalone» (R,d
    интерливом, fileio/opj_io.load_opj) и компактной LBO (fileio/decode_lbo).
    Пробуем оба декодера и выбираем лучший по объективным критериям
    (число поверхностей, стёкла, совпадение f' с именем системы).
    GFIX P5: первым — строгий вход fileio/standalone_opj (валидированная
    банком .PRN раскладка: точные ND/SD диафрагмы, поле, λ, RI-матрица);
    успех строгого разбора = prescription достоверен, скоринг эвристик не
    нужен. При несоответствии раскладки (StandaloneOpjError) — эвристики
    как прежде.
    """
    try:
        from fileio.standalone_opj import (StandaloneOpjError,
                                           load_standalone_opj)
        return load_standalone_opj(filepath)[0]
    except StandaloneOpjError:
        pass                                            # не standalone — эвристики
    from opj_reader import load_opj
    sys_opj, _info = load_opj(filepath)
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        from decode_lbo_opj import decode_lbo_opj
        sys_lbo = decode_lbo_opj(data)
    except Exception:
        sys_lbo = None
    return _pick_better_system(sys_opj, sys_lbo, filepath)


# Совпадение f' из имени системы (f'=104, F'=100, ...)
import re as _re
_F_NAME_RE = _re.compile(r"[fF]['\u2032]?=\s*(-?\d+(?:\.\d+)?)")


def _system_score(sys_obj, name_hint=None):
    """Оценка качества декодирования: больше — лучше."""
    if sys_obj is None or not getattr(sys_obj, 'surfaces', None):
        return -1e9
    from optics_engine import paraxial_trace
    n = len(sys_obj.surfaces)
    n_glass = sum(1 for s in sys_obj.surfaces if s.glass)
    score = float(n) + 3.0 * n_glass
    try:
        f = paraxial_trace(sys_obj).get('focal_length', 0) or 0
    except Exception:
        f = 0
    if f and abs(f) > 1e-6:
        score += 5.0                      # непустой параксиал — уже хорошо
        m = _F_NAME_RE.search(name_hint or sys_obj.name or '')
        if m:
            target = abs(float(m.group(1)))
            if target > 0:
                ratio = abs(abs(f) - target) / target
                if ratio < 0.08:
                    score += 50.0         # f' совпал с именем — сильный сигнал
                elif ratio < 0.25:
                    score += 10.0
    return score


def _pick_better_system(a, b, name_hint=None):
    """Вернуть систему с большей оценкой декодирования."""
    if a is None:
        return b
    if b is None:
        return a
    return a if _system_score(a, name_hint) >= _system_score(b, name_hint) else b


def _create_from_opj_bytes(opj_data, is_lbo=False):
    """Загрузить систему из OPJ данных в памяти."""
    # LBO data uses compact format — always use LBO decoder
    if is_lbo:
        from decode_lbo_opj import decode_lbo_opj
        return decode_lbo_opj(opj_data)

    # Standalone OPJ: строгий вход первым (GFIX P5), откат на эвристики
    try:
        from fileio.standalone_opj import (StandaloneOpjError,
                                           parse_standalone_opj,
                                           standalone_to_system)
        return standalone_to_system(parse_standalone_opj(opj_data))
    except StandaloneOpjError:
        pass

    import tempfile
    from opj_reader import load_opj

    # Standalone OPJ file
    tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
    try:
        os.write(tmpfd, opj_data)
        os.close(tmpfd)
        sys_obj, _info = load_opj(tmppath)
        return sys_obj
    except Exception:
        from decode_lbo_opj import decode_lbo_opj
        return decode_lbo_opj(opj_data)
    finally:
        try:
            os.unlink(tmppath)
        except Exception:
            pass


def _create_from_lbo(lbo_path, filename):
    """Загрузить конкретную систему из LBO файла по имени файла."""
    from lbo_reader import load_lbo_fast
    
    systems = load_lbo_fast(lbo_path)
    for s in systems:
        if s['filename'].upper() == filename.upper():
            return _create_from_opj_bytes(s['opj_data'], is_lbo=True)
    
    raise ValueError(f"Система {filename} не найдена в {lbo_path}")


def expand_lbo(lbo_path):
    """
    Раскрыть LBO библиотеку — получить список систем.
    
    Returns:
        Список записей: [{"name": str, "lbo_path": str, "lbo_filename": str, "opj_data": bytes}, ...]
    """
    return _load_lbo_systems(lbo_path)
