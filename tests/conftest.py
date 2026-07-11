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
