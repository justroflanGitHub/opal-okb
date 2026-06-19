"""
OPAL-OKB — Библиотека оптических систем
Предустановленные системы (генераторы) + OPJ файлы из архива + LBO библиотеки.
"""
import os
import glob

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
        return _create_from_opj_bytes(entry["opj_data"])
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
    """Загрузить систему из OPJ файла."""
    from opj_reader import load_opj
    sys, _info = load_opj(filepath)
    return sys


def _create_from_opj_bytes(opj_data):
    """Загрузить систему из OPJ данных в памяти."""
    import tempfile
    from opj_reader import load_opj
    
    # First try standalone OPJ parser
    tmpfd, tmppath = tempfile.mkstemp(suffix='.OPJ')
    try:
        os.write(tmpfd, opj_data)
        os.close(tmpfd)
        try:
            sys_obj, _info = load_opj(tmppath)
            # Validate: check if surfaces have real R values
            if sys_obj.surfaces and any(abs(s.radius) > 0.5 for s in sys_obj.surfaces):
                return sys_obj
        except Exception:
            pass
    finally:
        try:
            os.unlink(tmppath)
        except Exception:
            pass
    
    # Fallback: use LBO decoder (handles compact OPJ format)
    from decode_lbo_opj import decode_lbo_opj
    return decode_lbo_opj(opj_data)


def _create_from_lbo(lbo_path, filename):
    """Загрузить конкретную систему из LBO файла по имени файла."""
    from lbo_reader import load_lbo_fast
    
    systems = load_lbo_fast(lbo_path)
    for s in systems:
        if s['filename'].upper() == filename.upper():
            return _create_from_opj_bytes(s['opj_data'])
    
    raise ValueError(f"Система {filename} не найдена в {lbo_path}")


def expand_lbo(lbo_path):
    """
    Раскрыть LBO библиотеку — получить список систем.
    
    Returns:
        Список записей: [{"name": str, "lbo_path": str, "lbo_filename": str, "opj_data": bytes}, ...]
    """
    return _load_lbo_systems(lbo_path)
