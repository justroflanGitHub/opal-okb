"""
OPAL-OKB — Библиотека оптических систем
Предустановленные системы (генераторы) + OPJ файлы из архива.
"""
import os
import glob

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPJ_DIR = os.path.join(BASE_DIR, "extracted", "opal_okb")


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


def build_library():
    """Построить библиотеку оптических систем."""
    library = {
        "Ахроматические дублеты": [
            {"name": "Дублет К8+ТФ5 f'=100", "file": None, "generator": "achromat_100"},
            {"name": "Дублет К8+ТФ5 f'=200", "file": None, "generator": "achromat_200"},
        ],
        "OPAL системы": _scan_opj_files(),
    }
    return library


def create_system_from_entry(entry):
    """
    Создать OpticalSystem из записи библиотеки.
    entry: {"name": str, "file": str|None, "generator": str|None}
    """
    if entry.get("generator"):
        return _create_from_generator(entry["generator"])
    elif entry.get("file"):
        return _create_from_opj(entry["file"])
    else:
        raise ValueError(f"Запись '{entry['name']}' не имеет ни файла, ни генератора")


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
