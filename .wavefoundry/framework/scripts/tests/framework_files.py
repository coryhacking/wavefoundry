"""Where tests find framework source files (wave 1yzd0).

The server-owned modules live in the ``wf_server`` package. Each keeps a flat
file beside the package whose whole body is a three-line ``sys.modules`` alias,
so a test that reads or enumerates flat files by name would read or count the
alias instead of the implementation. Tests locate sources through this module;
``test_server_package`` refuses a flat ``glob("*.py")`` of the scripts root and
a source read of a moved module's flat path anywhere else.
"""
from __future__ import annotations

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DIR = SCRIPTS_DIR / "wf_server"


def package_module_names() -> frozenset[str]:
    """Flat names of the modules that live in the package (``server_impl``, ...)."""
    return frozenset(path.stem for path in PACKAGE_DIR.glob("*.py") if path.name != "__init__.py")


def source_path(name: str, scripts_dir: Path = SCRIPTS_DIR) -> Path:
    """The file under the scripts root for ``name``, resolving moved modules.

    ``name`` is a module (``server_impl`` or ``server_impl.py``) or any other
    scripts-relative path. A moved module resolves to its package file, another
    module to its flat file, and any other path (``benchmarks/x.json``,
    ``wave_lint_lib/cli.py``, ``VERSION``) to itself under ``scripts_dir``. An
    extensionless name is a module stem only when that module exists.

    The moved set is read from this checkout's package, so a ``scripts_dir``
    other than the live one must be a copy with the same layout.
    """
    if name.endswith(".py"):
        stem = name[:-3]
    elif "/" in name or "." in name:
        return scripts_dir / name
    else:
        stem = name
        if stem not in package_module_names() and not (scripts_dir / (stem + ".py")).exists():
            return scripts_dir / name
    if stem in package_module_names():
        return scripts_dir / PACKAGE_DIR.name / (stem + ".py")
    return scripts_dir / (stem + ".py")


def shipped_path(relpath: str, scripts_dir: Path = SCRIPTS_DIR) -> Path:
    """The file a pack ships at ``scripts/<relpath>``, with no resolution.

    For a moved module's flat name this is the three-line alias, which is what
    a test building a shippable tree wants (older upgrade runners require it).
    Use ``source_path`` to read an implementation.
    """
    return scripts_dir / relpath


def framework_source_files(*, include_aliases: bool = False) -> list[Path]:
    """Every implementing ``.py`` file of the scripts root and the package.

    Flat alias files are excluded (they implement nothing) unless
    ``include_aliases`` is set, which a test that builds a shippable tree needs:
    a pack carries the aliases and older upgrade runners require them. The
    package initializer is included. Subpackages other than ``wf_server`` (for
    example ``wave_lint_lib``) are left to the caller.
    """
    aliases = set() if include_aliases else package_module_names()
    flat = [path for path in SCRIPTS_DIR.glob("*.py") if path.stem not in aliases]
    return sorted(flat + list(PACKAGE_DIR.glob("*.py")))
