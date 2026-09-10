"""Qualified SQLite binding for the shared semantic index.

Never open this file with another SQLite library in the same process. Graph
and memory stores are separate files and may retain their existing binding.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

APSW_VERSION = "3.53.4.0"
SQLITE_VERSION = "3.53.4"
SQLITE_VEC_VERSION = "0.1.9"
BINARY_SUPPORT_GUIDANCE = (
    "sqlite-vec==0.1.9 publishes wheels for macOS arm64/x86_64, Linux glibc "
    "x86_64/aarch64, and Windows x64; no sdist or wheels for Linux musl, "
    "Windows ARM64 or Windows 32-bit. APSW also requires glibc >=2.28 on Linux. "
    "Wheel availability is not native platform qualification. Use a compatible "
    "Python environment and rerun wf setup; do not remove the existing index."
)

try:
    import apsw
except ImportError:
    apsw = None


class RuntimeUnavailable(RuntimeError):
    """The pinned native runtime must be installed by the normal setup path."""
    code = "storage_runtime_unavailable"


class StorageRecoveryRequired(RuntimeError):
    """Preserve the index and require an explicit migration or rebuild."""
    code = "storage_recovery_required"


# These categories intentionally do not classify busy/I/O/full as corruption.
Error = apsw.Error if apsw is not None else RuntimeUnavailable
OperationalError = (apsw.SQLError, apsw.BusyError, apsw.LockedError,
                    apsw.IOError, apsw.FullError, apsw.CantOpenError,
                    apsw.ReadOnlyError) if apsw is not None else (RuntimeUnavailable,)
CorruptionError = (apsw.CorruptError, apsw.NotADBError) if apsw is not None else ()


def connect(path: Path, *, read_only: bool = False,
            full_durability: bool = False):
    """Open a native connection; transactions and changes() belong to callers."""
    if apsw is None:
        raise RuntimeUnavailable(
            f"SQLite index runtime missing; run wf setup to install apsw=={APSW_VERSION} "
            f"and sqlite-vec=={SQLITE_VEC_VERSION} in the Wavefoundry tool environment. "
            "After installation, restart the process and resume the ordinary command.")
    from importlib.metadata import version
    if apsw.apswversion() != APSW_VERSION or apsw.sqlitelibversion() != SQLITE_VERSION:
        raise RuntimeUnavailable("SQLite index runtime version mismatch; run wf setup.")
    try:
        import sqlite_vec
        if version("sqlite-vec") != SQLITE_VEC_VERSION:
            raise RuntimeUnavailable("sqlite-vec version mismatch; run wf setup.")
    except ImportError as exc:
        raise RuntimeUnavailable("sqlite-vec missing; run wf setup.") from exc
    path = Path(path)
    creating = not path.exists() or path.stat().st_size == 0
    flags = apsw.SQLITE_OPEN_READONLY if read_only else (
        apsw.SQLITE_OPEN_READWRITE | apsw.SQLITE_OPEN_CREATE)
    conn = apsw.Connection(str(path), flags=flags)
    try:
        conn.set_busy_timeout(5000)
        conn.enable_load_extension(True)
        try:
            try:
                conn.load_extension(sqlite_vec.loadable_path())
            except Exception as exc:
                raise RuntimeUnavailable(
                    "SQLite vector extension could not load; run wf setup with a compatible "
                    "native Python/runtime, then restart the host. " + BINARY_SUPPORT_GUIDANCE
                ) from exc
        finally:
            conn.enable_load_extension(False)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA case_sensitive_like=ON")
        conn.execute("PRAGMA mmap_size=268435456")
        if not read_only:
            if creating:
                conn.execute("PRAGMA page_size=4096")
                conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
            mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(mode).lower() != "wal":
                raise StorageRecoveryRequired(
                    f"WAL unavailable for semantic index: {path}. The index requires a local "
                    "WAL-capable filesystem. Move the checkout to local storage (in WSL2, "
                    "prefer the Linux filesystem), then rerun the ordinary setup/upgrade "
                    "command. Preserve the existing index and migration receipt; a rebuild "
                    "on the same unsupported filesystem cannot repair this condition."
                )
            conn.execute("PRAGMA synchronous=" + ("FULL" if full_durability else "NORMAL"))
        return conn
    except BaseException:
        conn.close()
        raise


def preflight(index_dir: Path) -> dict:
    """Qualify native WAL creation on the destination filesystem without changing its index.

    Callers validate ownership and quiesce migration hosts first. The disposable
    probe is owned by this invocation; it never opens the existing main database.
    """
    index_dir = Path(index_dir)
    try:
        index_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sqlite-preflight-", dir=index_dir) as directory:
            conn = connect(Path(directory) / "probe.sqlite", full_durability=True)
            try:
                with conn:
                    conn.execute("CREATE TABLE probe(value INTEGER)")
                    conn.execute("INSERT INTO probe VALUES(1)")
                if conn.execute("SELECT value FROM probe").fetchone() != (1,):
                    raise StorageRecoveryRequired("SQLite filesystem preflight write/read failed.")
                return {"sqlite": SQLITE_VERSION, "sqlite_vec": SQLITE_VEC_VERSION,
                        "journal_mode": "wal"}
            finally:
                conn.close()
    except (RuntimeUnavailable, StorageRecoveryRequired):
        raise
    except Exception as exc:
        raise StorageRecoveryRequired(
            f"SQLite filesystem preflight failed at {index_dir}: {exc}. "
            "Check local-filesystem support, permissions and free space; preserve the "
            "index and receipt and retry the ordinary setup/upgrade command."
        ) from exc


def backup(source_path: Path, destination_path: Path) -> None:
    """Copy a consistent live database, including its committed WAL content."""
    source = connect(source_path, read_only=True)
    try:
        destination = connect(destination_path, full_durability=True)
        try:
            with destination.backup("main", source, "main") as copier:
                while not copier.done:
                    copier.step(1024)
        finally:
            destination.close()
    finally:
        source.close()
