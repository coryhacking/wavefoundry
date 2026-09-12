"""One definition of the shared index database's filename and its legacy name.

Deliberately import-light (``pathlib`` only, no project imports): every runtime
consumer of the shared semantic/graph database resolves its filename here, and
``upgrade_wavefoundry``'s stdlib-only probes can mirror these constants without
importing the module at all. Adding a heavy import here would pull it into
every store consumer and into the bootstrap-safe upgrade path.

The module answers exactly two questions:

* what is the current database called, and what was it called before the
  schema-8 rename (``index-state.sqlite``); and
* for a given index directory, which of the two names is actually present.

It deliberately does NOT decide authority when both names exist. That is the
migration receipt's job (see ``sqlite_storage_migration``): a resolver that
guessed here would authorize a destructive choice between two real databases.
"""
from __future__ import annotations

from pathlib import Path

# The current shared semantic + graph database (resident schema 8 onward).
INDEX_DATABASE_FILENAME = "index.sqlite"

# The pre-schema-8 name. Retained as the explicit legacy locator for
# migration detection, fixtures and historical evidence — never as a fallback
# a runtime consumer may silently open.
LEGACY_INDEX_DATABASE_FILENAME = "index-state.sqlite"

# The name runtime consumers open, and the single place the schema-8 rename is
# activated. ACTIVATED: every behavioral site in `sqlite_storage_migration`
# (schema probe, receipt source identity, identity revalidation, staging copy,
# `_published_identity`, the cleanup allowlists) now resolves a name through
# this module by ROLE — source, published, staged — so the migration publishes
# exactly the file store consumers open. Rebinding this to the legacy name
# would restore the pre-rename layout without reintroducing any literal.
RUNTIME_DATABASE_FILENAME = INDEX_DATABASE_FILENAME

# SQLite's WAL sidecars, in the order recovery code inspects them.
SIDECAR_SUFFIXES = ("-wal", "-shm")

# Resolution states. `both` is ambiguous by construction, `absent` is the only
# state that authorizes creating a database.
CURRENT = "current"
LEGACY = "legacy"
BOTH = "both"
ABSENT = "absent"
RESOLUTIONS = (CURRENT, LEGACY, BOTH, ABSENT)


def runtime_database_path(index_dir) -> Path:
    """The database path runtime consumers open inside ``index_dir``."""
    return Path(index_dir) / RUNTIME_DATABASE_FILENAME


def index_database_path(index_dir) -> Path:
    """The current (post-rename) database path inside ``index_dir``."""
    return Path(index_dir) / INDEX_DATABASE_FILENAME


def legacy_index_database_path(index_dir) -> Path:
    """The pre-rename database path inside ``index_dir``."""
    return Path(index_dir) / LEGACY_INDEX_DATABASE_FILENAME


def sidecar_paths(database_path) -> tuple[Path, ...]:
    """The ``-wal``/``-shm`` companions of one database path."""
    text = str(database_path)
    return tuple(Path(text + suffix) for suffix in SIDECAR_SUFFIXES)


def _present(path: Path) -> bool:
    """Fail CLOSED: an undecidable probe reads as present, never as absent.

    ``Path.is_file`` raises ``OSError`` (EACCES on an unreadable parent, and
    on Python 3.13 for the path itself) rather than returning False. Reading
    that as absence is the destructive direction — ``absent`` is the one state
    that authorizes creating a fresh database over a file we could not read.
    """
    try:
        return path.is_file()
    except OSError:
        return True


def resolve_index_database(index_dir) -> dict:
    """Which database names exist under ``index_dir``, without guessing.

    Returns ``{"state", "current_path", "legacy_path", "path"}`` where
    ``state`` is one of :data:`RESOLUTIONS` and ``path`` is the single
    unambiguous database — ``None`` for both ``both`` and ``absent``, so a
    caller cannot accidentally treat an ambiguous pair as authority.
    """
    current = index_database_path(index_dir)
    legacy = legacy_index_database_path(index_dir)
    has_current = _present(current)
    has_legacy = _present(legacy)
    if has_current and has_legacy:
        state = BOTH
    elif has_current:
        state = CURRENT
    elif has_legacy:
        state = LEGACY
    else:
        state = ABSENT
    return {
        "state": state,
        "current_path": current,
        "legacy_path": legacy,
        "path": {CURRENT: current, LEGACY: legacy}.get(state),
    }
