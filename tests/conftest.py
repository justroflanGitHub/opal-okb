"""Shared pytest fixtures and path configuration for OPAL-OKB tests."""
import sys
import os
from pathlib import Path

import pytest

# Ensure project root is on sys.path so imports like `from lbo_reader import ...` work
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Common library directory — prefer extracted/opal_okb/Lib (used by legacy tests),
# fall back to Lib/ at project root.
_LIB_CANDIDATES = [
    BASE_DIR / "extracted" / "opal_okb" / "Lib",
    BASE_DIR / "Lib",
]
LIB_DIR = next((p for p in _LIB_CANDIDATES if p.is_dir()), BASE_DIR / "Lib")


# --------------------------------------------------------------------------- #
# Resource detectors — single source of truth for skipif markers.
#
# extracted/ (библиотека OPAL-PC: .FIL-каталоги стёкол, .OPJ-системы,
# .LBO-библиотеки, .PRN-эталоны) осознанно не в git (.gitignore: сотни MB),
# поэтому на CI эти ресурсы недоступны по определению. Тесты, которым они
# нужны, помечаются маркерами requires_* из этого модуля:
#
#     from tests.conftest import requires_opj
#
#     @requires_opj
#     def test_...
# --------------------------------------------------------------------------- #

EXTRACTED_DIR = BASE_DIR / "extracted"
EXTRACTED_OPAL_DIR = EXTRACTED_DIR / "opal_okb"   # *.FIL, *.OPJ, RT__*.PRN
EXTRACTED_LIB_DIR = EXTRACTED_OPAL_DIR / "Lib"    # *.LBO

HAS_EXTRACTED = EXTRACTED_DIR.is_dir()
HAS_OPAL_DIR = HAS_EXTRACTED and EXTRACTED_OPAL_DIR.is_dir()

# FIL-каталоги стёкол: без них glass_catalog_full возвращает 16 встроенных
# ГОСТ-стёкол вместо 889 (см. catalog/glass_catalog_full.py::_load_catalog)
_FIL_CATALOGS = ("GCTG.FIL", "FCTG.FIL", "GCNG.FIL", "HCTG.FIL")
HAS_FIL = HAS_OPAL_DIR and all(
    (EXTRACTED_OPAL_DIR / name).is_file() for name in _FIL_CATALOGS)

# .OPJ-системы в extracted/opal_okb (81 файл)
HAS_OPJ = HAS_OPAL_DIR and any(EXTRACTED_OPAL_DIR.glob("*.OPJ"))

# .LBO-библиотеки в extracted/opal_okb/Lib
HAS_LBO = HAS_OPAL_DIR and EXTRACTED_LIB_DIR.is_dir() and any(
    EXTRACTED_LIB_DIR.glob("*.LBO"))


def has_lbo(*names: str) -> bool:
    """Есть ли конкретные .LBO в extracted/opal_okb/Lib («LENS» → LENS.LBO)."""
    return all((EXTRACTED_LIB_DIR / f"{name}.LBO").is_file() for name in names)


# .PRN-эталоны (печатки OPAL, CP866): RT__2250 (TABGL), RT__2236 (TABOC1/2)
HAS_PRN_RT2250 = HAS_OPAL_DIR and (EXTRACTED_OPAL_DIR / "RT__2250.PRN").is_file()
HAS_PRN_RT2236 = HAS_OPAL_DIR and (EXTRACTED_OPAL_DIR / "RT__2236.PRN").is_file()

# PyOpenGL: без него visualization3d не создаёт gl_widget (заглушка-лейбл,
# gl_widget = None) — GL-стаб тестов рендерит через настоящий paintGL
try:
    import OpenGL  # noqa: F401
    HAS_PYOPENGL = True
except ImportError:
    HAS_PYOPENGL = False


# Причины скипов — общий текст для маркеров и fixture-guard'ов
REASON_NO_EXTRACTED = "нет extracted/ (локальные данные, не в git)"
REASON_NO_FIL = "нет extracted/opal_okb/*.FIL — каталоги стёкол (локальные данные, не в git)"
REASON_NO_OPJ = "нет extracted/opal_okb/*.OPJ — системы (локальные данные, не в git)"
REASON_NO_LBO = "нет extracted/opal_okb/Lib/*.LBO — библиотеки (локальные данные, не в git)"
REASON_NO_PRN_RT2250 = "нет extracted/opal_okb/RT__2250.PRN — эталон TABGL (локальные данные, не в git)"
REASON_NO_PRN_RT2236 = "нет extracted/opal_okb/RT__2236.PRN — эталон TABOC1/2 (локальные данные, не в git)"
REASON_NO_PYOPENGL = "PyOpenGL не установлен — visualization3d.gl_widget = None"


def lbo_missing(*names: str) -> list:
    """Список отсутствующих .LBO из запрошенных («LENS» → LENS.LBO)."""
    return [n for n in names if not (EXTRACTED_LIB_DIR / f"{n}.LBO").is_file()]


# --------------------------------------------------------------------------- #
# Skip markers (импорт в тестах: from tests.conftest import requires_*)
# --------------------------------------------------------------------------- #

requires_extracted = pytest.mark.skipif(
    not HAS_EXTRACTED, reason=REASON_NO_EXTRACTED)
requires_opal_dir = pytest.mark.skipif(
    not HAS_OPAL_DIR, reason=REASON_NO_EXTRACTED)
requires_fil = pytest.mark.skipif(not HAS_FIL, reason=REASON_NO_FIL)
requires_opj = pytest.mark.skipif(not HAS_OPJ, reason=REASON_NO_OPJ)
requires_lbo = pytest.mark.skipif(not HAS_LBO, reason=REASON_NO_LBO)
requires_prn_rt2250 = pytest.mark.skipif(
    not HAS_PRN_RT2250, reason=REASON_NO_PRN_RT2250)
requires_prn_rt2236 = pytest.mark.skipif(
    not HAS_PRN_RT2236, reason=REASON_NO_PRN_RT2236)
requires_pyopengl = pytest.mark.skipif(
    not HAS_PYOPENGL, reason=REASON_NO_PYOPENGL)


def requires_lbo_of(*names: str):
    """Маркер под конкретные .LBO-каталоги: @requires_lbo_of("LENS", "LENS_SPC")."""
    missing = lbo_missing(*names)
    reason = ("нет extracted/opal_okb/Lib: "
              + ", ".join(f"{n}.LBO" for n in missing)
              + " (локальные данные, не в git)")
    return pytest.mark.skipif(bool(missing), reason=reason)


# --------------------------------------------------------------------------- #
# Path fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def lbo_dir():
    """Directory containing all .LBO catalog files."""
    return LIB_DIR


@pytest.fixture(scope="session")
def lens_lbo_path(lbo_dir):
    """Path to LENS.LBO."""
    return lbo_dir / "LENS.LBO"


@pytest.fixture(scope="session")
def lens_spc_lbo_path(lbo_dir):
    """Path to LENS_SPC.LBO (special / catadioptric systems)."""
    return lbo_dir / "LENS_SPC.LBO"


@pytest.fixture(scope="session")
def microlen_lbo_path(lbo_dir):
    """Path to MICROLEN.LBO."""
    return lbo_dir / "MICROLEN.LBO"


@pytest.fixture(scope="session")
def ocular_lbo_path(lbo_dir):
    """Path to OCULAR.LBO."""
    return lbo_dir / "OCULAR.LBO"


@pytest.fixture(scope="session")
def repro_lbo_path(lbo_dir):
    """Path to REPROD.LBO."""
    return lbo_dir / "REPROD.LBO"


# --------------------------------------------------------------------------- #
# Data-loading fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def lens_systems(lens_lbo_path):
    """All systems from LENS.LBO."""
    from lbo_reader import load_lbo_fast
    return load_lbo_fast(str(lens_lbo_path))


@pytest.fixture(scope="session")
def lens_spc_systems(lens_spc_lbo_path):
    """All systems from LENS_SPC.LBO."""
    from lbo_reader import load_lbo_fast
    return load_lbo_fast(str(lens_spc_lbo_path))


@pytest.fixture(scope="session")
def industar23u(lens_systems):
    """Декодированная система Индустар-23у (index 3 in LENS.LBO) — golden reference."""
    from decode_lbo_opj import decode_lbo_opj
    return decode_lbo_opj(lens_systems[3]['opj_data'])


@pytest.fixture(scope="session")
def mirror_lens_450(lens_spc_systems):
    """Декодированная зеркально-линзовая система f'=450 (index 1 in LENS_SPC.LBO)."""
    from decode_lbo_opj import decode_lbo_opj
    return decode_lbo_opj(lens_spc_systems[1]['opj_data'])


@pytest.fixture(scope="session")
def all_lbo_paths(lbo_dir):
    """Paths to every .LBO file in the library directory."""
    return sorted(lbo_dir.glob("*.LBO"))


# --------------------------------------------------------------------------- #
# Helper — make all .LBO libraries available as a dict
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session")
def all_lbo_systems(all_lbo_paths):
    """Dict mapping library filename → list of decoded entries (raw, not decoded).

    Each value is the list returned by ``load_lbo_fast``.
    """
    from lbo_reader import load_lbo_fast
    result = {}
    for path in all_lbo_paths:
        try:
            result[path.name] = load_lbo_fast(str(path))
        except Exception:
            result[path.name] = []
    return result
