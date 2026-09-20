"""Receipt-owned conversion of legacy vector stores through standard Upgrade.

Importing this module is bootstrap-safe: native bindings and the legacy reader
are imported only after the explicit restart checkpoint. The separate receipt
survives old upgrade finalizers removing their ordinary checkpoint on retry.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import stat
import time
import uuid
import re
import sys
import shlex
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar

try:  # normal import: the scripts directory is on sys.path
    import index_paths
except ImportError:  # pragma: no cover - exercised by the explicit-path load test
    # ``upgrade_extensions.post_extract`` loads THIS module by absolute path,
    # from an old runner whose sys.path need not contain the scripts directory.
    # Resolve the sibling the same way rather than re-spelling a filename here.
    import importlib.util as _util
    _spec = _util.spec_from_file_location(
        "index_paths", Path(__file__).resolve().parent / "index_paths.py")
    index_paths = _util.module_from_spec(_spec)
    _spec.loader.exec_module(index_paths)

try:
    import storage_identity
except ImportError:  # incoming upgrade hook can load this file before extraction
    import importlib.util as _identity_util
    _identity_spec = _identity_util.spec_from_file_location(
        "storage_identity", Path(__file__).resolve().parent / "storage_identity.py")
    storage_identity = _identity_util.module_from_spec(_identity_spec)
    _identity_spec.loader.exec_module(storage_identity)


RECEIPT = "sqlite-migration.json"
LEGACY_NAMES = ("docs.lance", "code.lance", "__manifest")
STATES = {"restart_required", "quiesced", "staged", "validated", "cutover_pending",
          "published", "verified", "cleanup_pending", "complete"}
READABLE_STATES = {"published", "verified", "cleanup_pending", "complete"}
SCHEMA_VERSION = "8"
# Shipped historical formats: schema 4 at a62d612a; schema 5 adds
# layer_path_state at 2952df8f; schema 6 adds build_state at 6bcac5f1;
# schema 7 adds canonical chunks/vectors and external-content FTS at
# 884f46bb. Existing auxiliary table definitions are identical across 4-6.
# A schema-7 source DISPATCHES here (instead of raising
# storage_schema_unsupported) and takes index_state_store's ADDITIVE 7 -> 8
# arm, which preserves its FTS tables, digests and lexical statistics.
LEGACY_SCHEMA_VERSIONS = frozenset({"4", "5", "6", "7"})
# The schemas the VERSION-1 conversion owns: they predate the canonical-chunk
# FTS contract and may still carry Lance artifacts beside them. A schema-7
# source has nothing left for that conversion to do, so it dispatches straight
# to the schema-8 kind.
LEGACY_CONVERSION_SCHEMAS = frozenset({"4", "5", "6"})
assert LEGACY_CONVERSION_SCHEMAS < LEGACY_SCHEMA_VERSIONS
# Receipt versions. v1 is the LanceDB-era record; v2 is the schema-8 rename
# record. v1 code's ``read_receipt`` rejects an unknown version outright, which
# is exactly the old-code fence: once a v2 record exists, a v1 runner refuses
# before it can open (or create) any database.
RECEIPT_VERSION_LEGACY = 1
RECEIPT_VERSION_CURRENT = 2
SUPPORTED_RECEIPT_VERSIONS = frozenset({RECEIPT_VERSION_LEGACY, RECEIPT_VERSION_CURRENT})
# The one migration kind a v2 record may declare.
KIND_SCHEMA8 = "index_sqlite_schema8"
KINDS = frozenset({KIND_SCHEMA8})
# Protocol floor per record: the legacy conversion is protocol 1, the schema-8
# kind requires a coordinator that declares 2. A coordinator declaring 1 (or
# nothing) receives the restart handoff and the installed CLI resumes it.
PROTOCOL_LEGACY = 1
PROTOCOL_SCHEMA8 = 2
# Roles, not strings: `source` is whichever owned name the record converts FROM,
# `published` is always the current name after the schema-8 cutover.
SOURCE_ROLE_LEGACY = "legacy"
SOURCE_ROLE_CURRENT = "current"
SOURCE_ROLES = (SOURCE_ROLE_LEGACY, SOURCE_ROLE_CURRENT)
KIND_WORK_PREFIX = "index-migration-"
LEGACY_WORK_PREFIX = "sqlite-migration-"
STAGING_ROLLBACK_STEM = "rollback.sqlite"
PREPARED_SPOOL_PREFIX = "wavefoundry-sqlite-prepared-"
PREPARED_SPOOL_STEM = "prepared.sqlite"
# The RETIRED graph-output folder under the index directory. Mirrors
# graph_indexer.GRAPH_DIRNAME, spelled here so cleanup never imports the heavy
# extractor module. Wave 1xny6 retired the derived writers that kept it alive,
# so nothing recreates it and procedure step 6 removes it under the
# pre-deletion inventory in `_inventory_retired_graph_directory`.
GRAPH_OUTPUT_DIRNAME = "graph"
# Derived-output directories the staged build writes beside the staged store.
# They are framework-owned staging output, never published, and never seeded
# from the source. The scan folder holds the secret-scan state the ordinary
# build refreshes; it is the ONLY one left now that the transitional derived
# graph writers are retired. Any OTHER directory under the staging index is an
# unknown staging artifact. The staged-build production test named in
# `_staging_allowlist` drives a REAL staged build and fails when the build
# produces a directory this set does not cover.
STAGING_DERIVED_DIRNAMES = frozenset({"scan"})
# Receipt cleanup state when the retired graph folder held something this
# migration does not own: the WHOLE folder is preserved and its entries are
# reported (procedure step 6).
RETAINED_UNOWNED_CONTENTS = "retained_unowned_contents"
AUTHORITY_AMBIGUOUS = "storage_authority_ambiguous"
SPURIOUS_LEGACY_GUIDANCE = (
    "A database under the retired name reappeared beside the published index. It was NOT "
    "adopted as authority and is preserved. An old Wavefoundry host (MCP server, dashboard "
    "or a pre-upgrade CLI) is still running against this repository: stop it, then remove "
    "the reappeared file only after confirming the published index is current."
)
INVOCATION_ENV = "WAVEFOUNDRY_STORAGE_INVOCATION"
CONFIRM_ENV = "WAVEFOUNDRY_STORAGE_HOSTS_STOPPED"
OLD_MCP_PID_ENV = "WAVEFOUNDRY_STORAGE_OLD_MCP_PID"
LEGACY_RECOVERY_GUIDANCE = (
    "Original storage, receipt and checkpoint are retained. Stop Wavefoundry hosts; "
    "recover a duplicate with a verified compatible older framework/runtime and its canonical "
    "wf setup --full before retrying the owning setup or upgrade operation. Keep the original index and "
    "receipts archived, preserve auxiliary state, and never open schema7 with an old runner. "
    "Current wf setup --full cannot bypass this migration receipt. See the Upgrade Wavefoundry "
    "legacy-source recovery instructions; if the compatible recovery inputs are unavailable, leave this paused."
)


class MigrationRequired(RuntimeError):
    """An actionable, non-destructive migration refusal."""


REBUILD_PROOF_KEY = "storage_rebuild_proof"


def rebuild_requested(receipt: dict | None) -> bool:
    """Old receipts retain transfer semantics; an explicit choice survives retries."""
    strategy = (receipt or {}).get("strategy", "transfer")
    if strategy not in {"transfer", "rebuild"}:
        raise MigrationRequired("storage_strategy_invalid")
    return strategy == "rebuild"


def _select_strategy(ctx, index_dir: Path, receipt: dict) -> None:
    selected = rebuild_requested(receipt)
    if getattr(ctx, "rebuild_storage", False) and not selected:
        if receipt["state"] not in {"restart_required", "quiesced"}:
            raise MigrationRequired("storage_strategy_changed_after_staging: retain the recorded strategy and resume")
        receipt.update(strategy="rebuild", rebuild_id=uuid.uuid4().hex)
        receipt.pop("upgrade_publication", None)
        _write(index_dir, receipt)
    if rebuild_requested(receipt) and not re.fullmatch(r"[0-9a-f]{32}", str(receipt.get("rebuild_id", ""))):
        raise MigrationRequired("storage_rebuild_identity_missing")


def _is_reparse(metadata) -> bool:
    """Windows lstat metadata works on Python 3.11, before is_junction exists."""
    return bool(getattr(metadata, "st_file_attributes", 0)
                & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _is_link_or_reparse(metadata) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata)


def _safe(path: Path) -> Path:
    """Refuse symlinks/junctions in every existing path component."""
    path = Path(path).absolute()
    # System aliases such as macOS /tmp are outside the project-owned tree.
    # Resolve the repository at entry; inspect every .wavefoundry descendant.
    parts = (path, *path.parents)
    stop = next((i for i, p in enumerate(parts) if p.name == ".wavefoundry"), 0)
    for part in parts[:stop + 1]:
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            continue
        if _is_link_or_reparse(metadata):
            raise MigrationRequired(f"storage_path_unowned: {part}")
    return path


def _safe_sqlite(path: Path) -> Path:
    """Validate a SQLite main path and both possible sidecars before opening."""
    path = _safe(path)
    for suffix in ("-wal", "-shm"):
        _safe(Path(str(path) + suffix))
    return path


def _identity(path: Path) -> dict:
    st = _safe(path).stat()
    return {"device": st.st_dev, "inode": st.st_ino}


def _write(index_dir: Path, receipt: dict) -> None:
    from upgrade_lib import _durable_json_replace
    path = _safe(index_dir / RECEIPT)
    receipt["updated_at"] = time.time()
    _durable_json_replace(path, receipt)


def is_kind_receipt(receipt: dict | None) -> bool:
    """A version-2 record: the schema-8 kind, and the old-code fence."""
    return bool(receipt) and receipt.get("receipt_version") == RECEIPT_VERSION_CURRENT


def _source_role(receipt: dict | None) -> str:
    """Which owned name a record converts FROM, by role and never by string."""
    role = (receipt or {}).get("source_database", SOURCE_ROLE_LEGACY)
    if role not in SOURCE_ROLES:
        raise MigrationRequired("storage_receipt_source_role_invalid")
    return role


def _role_path(index_dir, role: str) -> Path:
    if role == SOURCE_ROLE_CURRENT:
        return index_paths.index_database_path(index_dir)
    return index_paths.legacy_index_database_path(index_dir)


def source_database_path(index_dir, receipt: dict | None) -> Path:
    """The database a record reads FROM."""
    return _role_path(index_dir, _source_role(receipt))


def published_database_path(index_dir, receipt: dict | None) -> Path:
    """The database a record's cutover publishes TO.

    The schema-8 kind always publishes the CURRENT name; that rename is the
    whole point of the kind. A version-1 record publishes onto the name
    runtime consumers open, which is what it has always done — before the
    rename that was the retired name, after it the current one.
    """
    if is_kind_receipt(receipt):
        return index_paths.index_database_path(index_dir)
    return index_paths.runtime_database_path(index_dir)


def staged_database_path(work_index_dir) -> Path:
    """The staged file, named for the store module that will OPEN it.

    Staging is opened by ``IndexStateStore``/``sqlite_vector_store``, so its
    name is the runtime binding, not the record's publication target.
    """
    return index_paths.runtime_database_path(work_index_dir)


def _owned_database_names() -> frozenset:
    return frozenset({index_paths.INDEX_DATABASE_FILENAME,
                      index_paths.LEGACY_INDEX_DATABASE_FILENAME})


def _family_names(stem: str) -> tuple:
    base = Path(stem)
    return (base.name, *(path.name for path in index_paths.sidecar_paths(base)))


def _memory_state_filename() -> str:
    """The memory database's name, read from the module that CREATES it.

    Lazy because ``index_state_store`` imports this module; taking the name
    from its owner rather than copying the string is what keeps the staging
    allowlist derived instead of hand-maintained.
    """
    import index_state_store

    return index_state_store.MEMORY_STATE_FILENAME


def _staging_allowlist() -> frozenset:
    """Every FILE the staged build legitimately leaves under the staging index.

    Composed from the producing modules' own canonical names, never a copied
    literal: both owned database names and the rollback copy (``index_paths``),
    and the memory state database (``index_state_store``).

    Both database names are listed because a record staged before the runtime
    rename resumes under code that stages after it; either name inside a
    receipt-owned work directory is ours.

    ``memory-state.sqlite`` is listed because the staged rebuild runs the REAL
    coordinator, which invalidates memory state whenever the walk touches an
    agent-memory record, and the memory reader-writer creates its database in
    whatever index directory it is handed -- so on any repository carrying
    memory records the staged build DOES produce it beside the staged store.
    It is staging output that is never published: a freshly minted epoch at
    generation 1 with no writer token, so discarding it discards nothing. The
    live repository's own memory state is a different file in a different
    directory and is never touched.

    ``SchemaEightKindTests.test_the_staged_build_produces_nothing_the_staging_``
    ``classifier_refuses`` drives a REAL staged build over a corpus that
    includes a memory record and fails when the build starts producing
    something this function does not cover.
    """
    names = set()
    for stem in _owned_database_names() | {STAGING_ROLLBACK_STEM, _memory_state_filename()}:
        names.update(_family_names(stem))
    return frozenset(names)


def _retired_graph_allowlist() -> frozenset:
    """Owned names inside the RETIRED ``<index>/graph/`` folder.

    Procedure step 6's owned-name allowlist, exactly as written: the current
    project artifacts, the standalone graph state store with its sidecars, the
    legacy JSON state file, the framework-owned map fingerprint marker, and the
    retired framework-layer files some installs still carry. The atomic
    writers' ``<owned name>.*.tmp`` siblings are matched by
    :func:`_is_owned_graph_entry`, not listed here.

    Cleanup is the only code that still needs to NAME these files -- wave
    1xny6 retired ``index_state_store.GRAPH_STATE_STORE_RELPATH`` with its last
    reader -- so the list lives with the arm that deletes them.
    """
    return frozenset({"project-graph.json", "project-graph-clusters.json",
                      "project-graph-state.json", ".codebase-map.fingerprint",
                      "framework-graph.json", "framework-graph-state.json",
                      "framework-graph-clusters.json",
                      *_family_names("project-graph-state.sqlite")})


def _is_owned_graph_entry(name: str) -> bool:
    """An owned name, or one of the atomic writers' ``<owned>.*.tmp`` siblings.

    ``graph_indexer._write_json`` and ``graph_cluster._write_json`` promote
    through ``tempfile.mkstemp(prefix=<owned name> + ".", suffix=".tmp")``, so a
    crash between create and ``os.replace`` leaves exactly that shape behind.
    """
    owned = _retired_graph_allowlist()
    if name in owned:
        return True
    if not name.endswith(".tmp"):
        return False
    return any(name.startswith(stem + ".") for stem in owned)


def _work_prefix(receipt: dict | None) -> str:
    """A distinct work-dir prefix per record kind.

    Version-1 and version-2 staging never adopt each other's directory, so a
    resumed record cannot inherit a candidate built under the other contract.
    """
    return KIND_WORK_PREFIX if is_kind_receipt(receipt) else LEGACY_WORK_PREFIX


def read_receipt(index_dir: Path) -> dict | None:
    path = _safe(Path(index_dir) / RECEIPT)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise MigrationRequired("storage_receipt_unreadable") from exc
    if (not isinstance(value, dict) or value.get("receipt_version") not in SUPPORTED_RECEIPT_VERSIONS
            or value.get("state") not in STATES
            or not re.fullmatch(r"[0-9a-f]{32}", str(value.get("migration_id", "")))
            or not storage_identity.same_path(value.get("index_dir"), Path(index_dir).resolve())
            or not storage_identity.compare_identity(value.get("root_identity"), _identity(Path(index_dir).parent.parent))["matches"]):
        raise MigrationRequired("storage_receipt_identity_mismatch")
    if value["receipt_version"] == RECEIPT_VERSION_CURRENT:
        if value.get("kind") not in KINDS:
            raise MigrationRequired("storage_receipt_kind_unsupported")
        _source_role(value)
        superseded = value.get("supersedes")
        if superseded is not None and (not isinstance(superseded, dict)
                or superseded.get("receipt_version") != RECEIPT_VERSION_LEGACY):
            raise MigrationRequired("storage_receipt_supersedes_invalid")
    elif value.get("kind") is not None:
        # A version-1 record carrying a kind marker is rejected outright: old
        # code tolerates the unknown field and would NOT fence on it, so the
        # marker would advertise a migration the fence cannot enforce.
        raise MigrationRequired("storage_receipt_kind_unsupported")
    return value


def _database_schema(path: Path) -> str:
    """Read one database's schema through a qualified WAL-aware snapshot.

    Bootstrap hosts may lack the incoming runtime. An existing file then needs
    a restart checkpoint and a qualified probe after normal dependency setup.
    File headers are never schema authority: committed metadata may be in WAL.
    """
    path = _safe_sqlite(Path(path))
    if not path.exists():
        if any(sidecar.exists() for sidecar in index_paths.sidecar_paths(path)):
            raise MigrationRequired("storage_schema_unreadable: orphan SQLite sidecars retained; recover before setup")
        return "absent"
    identity = _identity(path)
    from importlib.metadata import PackageNotFoundError
    try:
        import sqlite_runtime as runtime
    except ImportError:
        return "runtime_unavailable"
    try:
        conn = runtime.connect(path, read_only=True)
    except (runtime.RuntimeUnavailable, PackageNotFoundError):
        return "runtime_unavailable"
    except Exception as exc:
        raise MigrationRequired("storage_schema_unreadable: preserve the shared database and resume after recovery") from exc
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone()
        if _identity(path) != identity:
            raise MigrationRequired(f"storage_source_identity_changed: {path.name}")
        return str(row[0]) if row else "unknown"
    except MigrationRequired:
        raise
    except Exception as exc:
        raise MigrationRequired("storage_schema_unreadable: preserve the shared database and resume after recovery") from exc
    finally:
        conn.close()


def _identity_if_present(path: Path) -> dict | None:
    path = _safe(Path(path))
    return _identity(path) if path.exists() else None


def _resolve_authority(resolution: dict, receipt: dict | None) -> tuple:
    """Decide which of two owned names is authority, or refuse to decide.

    Never mtime, never size, never "newest schema": only one name present, or
    a version-2 receipt whose recorded identities still match what is on disk.
    """
    state = resolution["state"]
    if state == index_paths.ABSENT:
        return None, None, None
    if state == index_paths.CURRENT:
        return SOURCE_ROLE_CURRENT, None, None
    if state == index_paths.LEGACY:
        return SOURCE_ROLE_LEGACY, None, None
    if (receipt and receipt["state"] in READABLE_STATES | {"cutover_pending"}
            and receipt.get("published_sqlite_identity")
            and storage_identity.compare_identity(receipt["published_sqlite_identity"], _identity_if_present(resolution["current_path"]))["matches"]):
        # The recorded cutover identity landed on the current name: that file is
        # authority. `cutover_pending` counts because the intent was recorded
        # durably BEFORE the replace, so an interruption on either side of it is
        # decidable by identity alone. The retained source stays until cleanup;
        # anything else under the retired name is spurious.
        retained = receipt.get("source_sqlite_identity")
        reappeared = (receipt["state"] == "complete" or retained is None
                      or not storage_identity.compare_identity(retained, _identity_if_present(resolution["legacy_path"]))["matches"])
        return SOURCE_ROLE_CURRENT, None, (SPURIOUS_LEGACY_GUIDANCE if reappeared else None)
    return None, AUTHORITY_AMBIGUOUS, None


def detect(index_dir: Path) -> dict:
    index_dir = _safe(Path(index_dir))
    receipt = read_receipt(index_dir)
    legacy = [name for name in LEGACY_NAMES if (index_dir / name).exists()
              or (index_dir / name).is_symlink()]
    resolution = index_paths.resolve_index_database(index_dir)
    # Authority comes from presence plus the receipt, never from a schema
    # comparison: "newest schema wins" is exactly the destructive guess.
    authority_role, diagnostic, spurious = _resolve_authority(resolution, receipt)
    # ALWAYS probe BOTH owned names. Receipt presence never short-circuits the
    # probe: the durable once-marker is meta.store_schema_version in the
    # published database, not a state word in a JSON file. A probe failure on
    # the name that is NOT authority is recorded, not raised — a file an old
    # host dropped beside the published index must be reported and preserved,
    # never allowed to take the repository down.
    schemas = {}
    for role in SOURCE_ROLES:
        path = resolution["current_path"] if role == SOURCE_ROLE_CURRENT else resolution["legacy_path"]
        try:
            schemas[role] = _database_schema(path)
        except MigrationRequired:
            # Tolerate ONLY when a different name is the proven authority. With
            # no proven authority the undecidable probe must raise: `absent` is
            # the one state that authorizes creating a database, so an orphan
            # sidecar or an unreadable file may never read as a fresh index.
            if authority_role is None or role == authority_role:
                raise
            schemas[role] = "unreadable"
    authority_schema = schemas[authority_role] if authority_role else "absent"
    if authority_schema not in {"absent", "runtime_unavailable", SCHEMA_VERSION} | LEGACY_SCHEMA_VERSIONS:
        raise MigrationRequired(f"storage_schema_unsupported: {authority_schema}; preserve the shared database")
    # The once-marker: schema 8 under the CURRENT name, nothing else.
    marker_satisfied = (authority_role == SOURCE_ROLE_CURRENT
                        and authority_schema == SCHEMA_VERSION)
    # A COMPLETED version-1 record that published the current name satisfies the
    # marker but installs no fence: a version-1 runner reads "complete", finds
    # nothing under the retired name and creates a fresh empty database beside
    # the published index. The kind's version-2 record is that fence.
    fence_required = bool(receipt and not is_kind_receipt(receipt)
                          and receipt["state"] == "complete"
                          and receipt.get("published_sqlite_identity")
                          and marker_satisfied)
    kind_required = (bool(authority_role) and not marker_satisfied) or fence_required
    active_pending = receipt is not None and receipt["state"] not in READABLE_STATES
    # A record whose own state reads "done" does NOT clear a still-unsatisfied
    # once-marker: a published version-1 conversion still owes the rename.
    kind_can_start = kind_required and (receipt is None or receipt["state"] in READABLE_STATES)
    return {"legacy": legacy, "receipt": receipt,
            "identity_comparison": storage_identity.compare_identity(
                receipt.get("root_identity"), _identity(index_dir.parent.parent)) if receipt else None,
            "sqlite_schema": "ambiguous" if diagnostic else authority_schema,
            "resolution": resolution["state"], "schemas": schemas,
            "authority_role": authority_role,
            "authority_path": _role_path(index_dir, authority_role) if authority_role else None,
            "kind_required": kind_required, "fence_required": fence_required,
            "authority_diagnostic": diagnostic,
            "spurious_legacy": spurious,
            "migration_required": bool(
                active_pending or kind_can_start or diagnostic
                or (receipt is None and (legacy or authority_schema == "runtime_unavailable")))}


def require_ready(index_dir: Path, allow_migration: bool = False) -> None:
    # The publication fence runs BEFORE any schema probe: when the receipt-owned
    # cutover file has been replaced, that is the accurate diagnostic, and a
    # probe of the replaced file would report an unreadable schema instead.
    receipt = read_receipt(Path(index_dir))
    if receipt and receipt["state"] in READABLE_STATES - {"complete"}:
        _published_identity(Path(index_dir), receipt)
    state = detect(index_dir)
    if allow_migration:
        return
    if state["authority_diagnostic"]:
        raise MigrationRequired(
            state["authority_diagnostic"] + ": both index database names exist and no version-2 "
            "receipt proves which is authority. Both files are preserved; recover the intended "
            "one through its owning recovery records rather than deleting either.")
    if state["migration_required"]:
        command = "wf_upgrade" if receipt and receipt.get("entry_path") != "setup" else "wf setup"
        raise MigrationRequired(f"storage_migration_required: run {command}; restart old hosts and resume the retained checkpoint")


def restore_checkpoint(root: Path) -> dict | None:
    """Run before generic dead-PID checkpoint cleanup or overwrite."""
    import upgrade_lib
    index_dir = Path(root) / ".wavefoundry" / "index"
    receipt = read_receipt(index_dir)
    if receipt is None or receipt["state"] == "complete":
        return receipt
    if receipt.get("entry_path") == "setup":
        from setup_reconciliation import validate_source_binding
        validate_source_binding(root, receipt)
        checkpoint = upgrade_lib.read_upgrade_lock(root)
        if checkpoint is not None and checkpoint.get("entry_path") != "setup":
            raise MigrationRequired("storage_setup_foreign_upgrade: checkpoint retained")
    if upgrade_lib.read_upgrade_lock(root) is None:
        upgrade_lib.write_upgrade_lock(root, receipt.get("source_version"),
                                       receipt.get("target_version") or "unknown",
                                       Path(receipt["pack_path"]) if receipt.get("pack_path") else None)
    if not upgrade_lib.update_upgrade_lock(root, storage_migration_id=receipt["migration_id"],
                                           storage_migration_state=receipt["state"],
                                           **({key: receipt.get(key) for key in
                                               ("entry_path", "installed_framework_sha256", "setup_args", "root_identity")}
                                              if receipt.get("entry_path") == "setup" else {})):
        raise MigrationRequired("storage_checkpoint_write_failed")
    return receipt


def _host_is_running(pid: int) -> bool:
    if os.name == "nt":
        # os.kill(pid, 0) is not a portable Windows liveness operation. Open a
        # synchronization-only handle and poll it; never terminate an old host.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER: absent PID
                return False
            raise MigrationRequired(f"storage_host_exit_unproven: {pid}")
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            if result == 0:
                return False
            if result == 258:
                return True
            raise MigrationRequired(f"storage_host_exit_unproven: {pid}")
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError as exc:
        raise MigrationRequired(f"storage_host_exit_unproven: {pid}") from exc
    return True


def _hosts_gone(receipt: dict) -> None:
    # Only explicitly identified framework hosts belong here. In particular,
    # os.getppid() may be a terminal/shell and is never inferred to be an MCP host.
    blockers = []
    for host in receipt.get("old_hosts", []):
        pid = host.get("pid")
        if type(pid) is not int or pid <= 0 or host.get("kind") not in {"mcp", "dashboard"}:
            raise MigrationRequired("storage_host_identity_invalid")
        if not _host_is_running(pid):
            continue
        # A reused PID is conservatively retained, never killed. Birth metadata
        # is diagnostic until a host-specific provider can verify replacement.
        blockers.append(host)
    if blockers:
        raise MigrationRequired("storage_old_host_alive: " + ", ".join(str(h["pid"]) + " (" + h["kind"] + "; " + h.get("association", h.get("source", "recorded host")) + ")" for h in blockers))


def _process_cwds(pids: list[int]) -> dict[int, Path]:
    """One bounded observation for relative framework entry-point candidates."""
    paths = {}
    if not pids:
        return paths
    if sys.platform.startswith("linux"):
        for pid in pids:
            try:
                paths[pid] = Path(os.readlink(f"/proc/{pid}/cwd")).resolve()
            except OSError:
                pass
    elif sys.platform == "darwin":
        import subprocess_util
        try:
            result = subprocess_util.isolated_run(["lsof", "-a", "-p", ",".join(map(str, pids)), "-d", "cwd", "-Fn"], capture_output=True, text=True, timeout=5, check=True)
            pid = None
            for line in result.stdout.splitlines():
                if line.startswith("p") and line[1:].isdigit():
                    pid = int(line[1:])
                elif line.startswith("n/") and pid in pids:
                    paths[pid] = Path(line[1:]).resolve()
        except (OSError, subprocess.SubprocessError):
            pass
    return paths


def discover_hosts(root: Path) -> tuple[list[dict], list[str]]:
    """Inventory positively associated hosts, without guessing from cwd."""
    import subprocess_util
    root = Path(root).resolve()
    limits = ["Process visibility is limited to accessible command lines; hidden, remote and unregistered hosts require operator confirmation."]
    try:
        if os.name == "nt":
            script = "Get-CimInstance Win32_Process | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
            result = subprocess_util.isolated_run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, text=True, timeout=10, check=True)
            rows = json.loads(result.stdout or "[]")
            if isinstance(rows, dict):
                rows = [rows]
            processes = [(int(row["ProcessId"]), row.get("CommandLine") or "") for row in rows]
        else:
            result = subprocess_util.isolated_run(["ps", "-axww", "-o", "pid=,command="], capture_output=True, text=True, timeout=10, check=True)
            if not isinstance(result.stdout, str):
                raise ValueError("process command output unavailable")
            processes = [(int(parts[0]), parts[1]) for line in result.stdout.splitlines() if len(parts := line.strip().split(None, 1)) == 2 and parts[0].isdigit()]
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return [], limits + ["Process discovery failed: " + type(exc).__name__ + "; absence of hosts is unproven."]
    hosts = []
    relative_pids = [pid for pid, command in processes if re.search(r"(?:^|[\s\"\'])\.?/?\.wavefoundry/framework/scripts/(?:server|dashboard_server)\.py(?:[\s\"\']|$)", command)]
    process_cwds = _process_cwds(relative_pids)
    for pid, command in processes:
        if pid == os.getpid():
            continue
        candidates = [command]
        if os.name != "nt":
            # ps loses argv quoting. Try its original representation first,
            # then protect this known root (and verified macOS alias) only.
            roots = [str(root)]
            alias = str(root).removeprefix("/private")
            if alias != str(root) and Path(alias).resolve() == root:
                roots.append(alias)
            for candidate_root in roots:
                candidates.append(command.replace(candidate_root, shlex.quote(candidate_root)))
        for parse_command in candidates:
            try:
                tokens = shlex.split(parse_command, posix=os.name != "nt")
                tokens = [token.strip('"') for token in tokens]
            except ValueError:
                continue
            executable = Path(tokens[0].replace("\\", "/")).name.lower() if tokens else ""
            if not re.fullmatch(r"python(?:w|3(?:\.\d+)?)?(?:\.exe)?", executable):
                continue
            # Script must be the interpreter entry point, never a -c string or an
            # argument to an unrelated Python program.
            arguments = tokens[1:]
            while arguments and arguments[0] in {"-B", "-u", "-E", "-s", "-S", "-I"}:
                arguments = arguments[1:]
            scripts = [(token, Path(token.replace("\\", "/")).name) for token in arguments[:1]]
            selected = next(((token, "dashboard" if name == "dashboard_server.py" else "mcp") for token, name in scripts if name in {"server.py", "dashboard_server.py"}), None)
            if not selected:
                continue
            script_path, kind = selected
            explicit_root = next((token.split("=", 1)[1] for token in tokens if token.startswith("--root=")), None)
            if "--root" in tokens and tokens.index("--root") + 1 < len(tokens):
                explicit_root = tokens[tokens.index("--root") + 1]
            expected_script = root / ".wavefoundry/framework/scripts" / ("dashboard_server.py" if kind == "dashboard" else "server.py")
            # A shared framework script is associated by an explicit absolute root;
            # a repo-local absolute script is evidence only absent a different root.
            if explicit_root is not None:
                associated = Path(explicit_root).is_absolute() and Path(explicit_root).resolve() == root
                framework_script = ".wavefoundry/framework/scripts/" in script_path.replace("\\", "/")
                associated = associated and framework_script
                association = "explicit --root and Wavefoundry entry point"
            else:
                associated = Path(script_path).is_absolute() and Path(script_path).resolve() == expected_script
                association = "absolute repository-local Wavefoundry entry point"
                if not Path(script_path).is_absolute() and script_path.replace("\\", "/").startswith((".wavefoundry/framework/scripts/", "./.wavefoundry/framework/scripts/")):
                    cwd = process_cwds.get(pid)
                    associated = cwd is not None and (cwd / script_path).resolve() == expected_script
                    association = "relative Wavefoundry entry point resolved against observed process cwd"
                    if cwd is None:
                        limit = f"PID {pid} is a relative Wavefoundry {kind} entry point but its cwd/root is unobservable; confirm its repository manually."
                        if limit not in limits:
                            limits.append(limit)
            if associated:
                hosts.append({"pid": pid, "kind": kind, "association": association, "source": "process_command_line"})
                break
    return hosts, limits


def _refresh_hosts(root: Path, receipt: dict) -> None:
    hosts, limits = discover_hosts(root)
    existing = {(host["pid"], host["kind"]): host for host in receipt.get("old_hosts", [])}
    existing.update({(host["pid"], host["kind"]): host for host in hosts})
    receipt.update(old_hosts=list(existing.values()), discovery_limits=limits, hosts_observed_at=time.time())
    _write(Path(root) / ".wavefoundry/index", receipt)


def restart_command(root: Path, pack_path: str | None, rebuild_storage: bool = False,
                    *, entry_path: str = "upgrade", setup_args: list[str] | None = None) -> dict:
    executable = sys.executable
    console = Path(executable)
    if os.name == "nt" and console.stem.lower() == "pythonw" and console.suffix.lower() == ".exe":
        executable = str(console.with_name(console.stem[:-1] + console.suffix))
    script = "setup_wavefoundry.py" if entry_path == "setup" else "upgrade_wavefoundry.py"
    argv = [executable, str(Path(root).resolve() / ".wavefoundry/framework/scripts" / script)]
    if entry_path == "setup":
        args = iter(setup_args or [])
        for arg in args:
            if arg == "--root":
                next(args, None)
            elif not arg.startswith("--root=") and arg not in {"--confirm-hosts-stopped", "--rebuild-storage"}:
                argv.append(arg)
    argv += ["--root", str(Path(root).resolve())]
    if pack_path:
        argv += ["--pack", pack_path]
    argv += (["--confirm-hosts-stopped"] if entry_path == "setup"
             else ["--yes", "--confirm-hosts-stopped"])
    if rebuild_storage:
        argv.append("--rebuild-storage")
    if os.name == "nt":
        command = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in argv)
        shell = "PowerShell"
    else:
        command, shell = shlex.join(argv), "POSIX shell"
    return {"command_argv": argv, "command": command, "command_shell": shell}


def read_restart_action(root: Path, exit_code: int, invocation_token: str) -> dict | None:
    """Recognize only this invocation's durable, receipt/checkpoint-bound pause."""
    if exit_code != 3 or not invocation_token:
        return None
    # An already-running pre-guard MCP wrapper loads this installed reader after
    # extraction. Its final response also needs adaptation: returning a guard
    # action alone would make that wrapper mislabel it as a storage migration.
    try:
        import upgrade_extensions
        reader = getattr(upgrade_extensions, "legacy_index_guard_restart_action", None)
    except ImportError:
        reader = None
    guard_action = reader(root, exit_code, invocation_token, sys._getframe(1)) if callable(reader) else None
    if guard_action is not None:
        return guard_action
    import upgrade_lib
    try:
        root = Path(root).resolve()
        receipt = read_receipt(root / ".wavefoundry/index")
        lock = upgrade_lib.read_upgrade_lock(root) or {}
        action = lock.get("action_required")
        if not receipt or receipt["state"] in READABLE_STATES or not isinstance(action, dict) or action != receipt.get("restart_action"):
            return None
        if receipt.get("entry_path") == "setup":
            from setup_reconciliation import validate_source_binding
            validate_source_binding(root, receipt)
            if (lock.get("entry_path") != "setup"
                    or action.get("installed_framework_sha256") != receipt.get("installed_framework_sha256")
                    or lock.get("installed_framework_sha256") != receipt.get("installed_framework_sha256")):
                return None
        if (action.get("kind") != "storage_migration" or action.get("state") != "restart_required"
                or action.get("invocation_token") != invocation_token or not storage_identity.same_path(action.get("root"), root)
                or action.get("migration_id") != receipt["migration_id"]
                or action.get("root_identity") != receipt["root_identity"]
                or action.get("target_version") != receipt.get("target_version")
                or action.get("pack_path") != receipt.get("pack_path")
                or action.get("pack_sha256") != receipt.get("pack_sha256")
                or lock.get("storage_migration_id") != receipt["migration_id"]
                or lock.get("to_version") != receipt.get("target_version")
                or lock.get("zip_path") != action.get("consumed_pack_path")
                or lock.get("current_phase") != "storage_restart_required"
                or action.get("checkpoint_started_at") != lock.get("started_at")):
            return None
        if receipt.get("pack_path"):
            if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("pack_sha256", ""))):
                return None
            for path in (receipt["pack_path"], action.get("consumed_pack_path")):
                if not path or _file_hash(Path(path)) != receipt["pack_sha256"]:
                    return None
        elif action.get("consumed_pack_path") or receipt.get("pack_sha256"):
            return None
        return action
    except (OSError, ValueError, KeyError, MigrationRequired):
        return None


def _pause_for_restart(ctx, receipt: dict) -> None:
    import upgrade_lib
    root = Path(ctx.root).resolve()
    token = os.environ.get(INVOCATION_ENV) or uuid.uuid4().hex
    lock = upgrade_lib.read_upgrade_lock(root) or {}
    action = {"kind": "storage_migration", "state": "restart_required", "code": "storage_restart_required",
              "invocation_token": token, "migration_id": receipt["migration_id"], "root": str(root),
              "root_identity": receipt["root_identity"], "target_version": receipt.get("target_version"),
              "pack_path": receipt.get("pack_path"), "pack_sha256": receipt.get("pack_sha256"),
              "consumed_pack_path": str(Path(ctx.zip_path).resolve()) if getattr(ctx, "zip_path", None) else None,
              "checkpoint_started_at": lock.get("started_at"), "old_hosts": receipt.get("old_hosts", []),
              "discovery_limits": receipt.get("discovery_limits", []),
              "message": "Save this command, fully stop the listed Wavefoundry MCP/dashboard hosts and confirm any hosts discovery cannot observe, then run it in an external terminal. No storage format change has occurred; extracted framework files and the upgrade checkpoint are retained. Keep the recorded archive until completion. If its path disappears, supply a relocated byte-identical archive with --pack; its recorded SHA-256 must match. Do not edit the receipt.",
              **restart_command(root, receipt.get("pack_path"), rebuild_requested(receipt),
                                entry_path=receipt.get("entry_path", "upgrade"),
                                setup_args=receipt.get("setup_args"))}
    if receipt.get("entry_path") == "setup":
        action.update(entry_path="setup", installed_framework_sha256=receipt["installed_framework_sha256"],
                      message="Save this setup continuation, stop the listed Wavefoundry MCP/dashboard hosts and confirm any hosts discovery cannot observe, then run it in an external terminal. The installed framework, receipt and source storage are retained; restore the recorded framework if its bytes change before retry. Do not edit the receipt.")
    receipt["restart_action"] = action
    _write(root / ".wavefoundry/index", receipt)
    if not upgrade_lib.update_upgrade_lock(root, action_required=action, zip_path=action["consumed_pack_path"], current_phase="storage_restart_required", failed_phase=None, failed_at=None):
        raise MigrationRequired("storage_checkpoint_write_failed")
    pause = SystemExit(3)
    # The delivering OLD runner owns the outer exception handler. Bridge its
    # finalizer once, and restore it before any match check or delegated call.
    parent = sys.modules.get(type(ctx).__module__)
    original = getattr(parent, "_finalize_failed_upgrade", None)
    if callable(original):
        def finalizer(final_root, tree_mutated, current_phase):
            parent._finalize_failed_upgrade = original
            exc = sys.exc_info()[1]
            if (exc is pause and Path(final_root).resolve() == root
                    and current_phase in {"extract", "storage_migration", "storage_restart_required", "runtime_lock_cutover"}
                    and read_restart_action(root, exc.code, token) is not None):
                return
            return original(final_root, tree_mutated, current_phase)
        parent._finalize_failed_upgrade = finalizer
    print(json.dumps({"status": "action_required", **action}), flush=True)
    print(action["command_shell"] + ": " + action["command"], flush=True)
    raise pause


def _pack_locator(ctx, consumed_pack: Path, digest: str) -> str:
    """Prefer a verified original archive over the dispatcher's private copy."""
    selected = getattr(ctx, "selected_feature_zip", None)
    if selected is None:
        # Incoming hooks can run in a previously shipped UpgradeContext. Reuse
        # that runner's discovery policy; never infer authority from a filename.
        parent = sys.modules.get(type(ctx).__module__)
        finder = getattr(parent, "_find_zip", None)
        if callable(finder):
            try:
                selected = finder(Path(ctx.root).resolve())
            except (OSError, ValueError):
                selected = None
    if selected is not None:
        try:
            candidate = Path(selected).resolve()
            if _file_hash(candidate) == digest:
                return str(candidate)
        except (OSError, ValueError, MigrationRequired):
            pass
    return str(consumed_pack)


def _kind_dispatch(state: dict) -> bool:
    """Is the NEXT record the schema-8 kind, or the legacy conversion first?

    A Lance-era source (artifacts present, or a schema this module's version-1
    conversion owns) takes the version-1 conversion first, unchanged. The kind
    then runs on its result.
    """
    if not state["kind_required"]:
        return False
    if state["legacy"]:
        return False
    return state["schemas"][state["authority_role"]] not in LEGACY_CONVERSION_SCHEMAS


def required_protocol(receipt: dict | None) -> int:
    """The coordinator protocol a record needs to convert in-process."""
    return PROTOCOL_SCHEMA8 if is_kind_receipt(receipt) else PROTOCOL_LEGACY


def _new_receipt(ctx, root: Path, index_dir: Path, state: dict,
                 superseded: dict | None = None) -> dict:
    """Create the next record. One receipt file; one active record."""
    old_hosts = list(getattr(ctx, "storage_old_hosts", []) if ctx is not None else [])
    identified_mcp_pid = os.environ.get(OLD_MCP_PID_ENV)
    if identified_mcp_pid:
        if not identified_mcp_pid.isdecimal() or int(identified_mcp_pid) <= 0:
            raise MigrationRequired("storage_host_identity_invalid")
        old_hosts.append({"kind": "mcp", "pid": int(identified_mcp_pid),
                          "source": "initiating_mcp_wrapper"})
    upgrading_without_index = (bool(getattr(ctx, "from_version", None) if ctx is not None else None)
                               and state["authority_role"] is None)
    kind = _kind_dispatch(state)
    role = state["authority_role"] or SOURCE_ROLE_LEGACY
    source = _role_path(index_dir, role)
    receipt = {"receipt_version": RECEIPT_VERSION_CURRENT if kind else RECEIPT_VERSION_LEGACY,
               "migration_id": uuid.uuid4().hex,
               "index_dir": str(index_dir.resolve()), "root_identity": _identity(root),
               "source_version": getattr(ctx, "from_version", None) if ctx is not None else None,
               "target_version": getattr(ctx, "to_version", None) if ctx is not None else None,
               "pack_path": str(Path(ctx.zip_path).resolve()) if getattr(ctx, "zip_path", None) else None,
               "pack_sha256": _file_hash(Path(ctx.zip_path)) if getattr(ctx, "zip_path", None) else None,
               "state": "restart_required", "old_hosts": old_hosts,
               "reason": ("index_database_rename" if kind
                          else "existing_framework_without_index" if upgrading_without_index
                          else "legacy_storage"),
               "source_database": role,
               "source_sqlite_identity": _identity_if_present(source),
               "artifacts": {name: _identity(index_dir / name) for name in state["legacy"]}}
    if getattr(ctx, "entry_path", None) == "setup":
        receipt.update(entry_path="setup", installed_framework_sha256=ctx.installed_framework_sha256,
                       setup_args=list(ctx.setup_args))
    if kind:
        receipt["kind"] = KIND_SCHEMA8
        if superseded is not None:
            receipt["supersedes"] = superseded
        # The kind inherits the completed record's retired artifacts so one
        # cleanup arm owns everything the chained conversion left behind.
        if superseded is not None and superseded.get("artifacts"):
            receipt["artifacts"] = {name: identity for name, identity
                                    in superseded["artifacts"].items()
                                    if (index_dir / name).exists()}
    elif superseded is not None:
        raise MigrationRequired("storage_receipt_supersedes_invalid")
    return receipt


def prepare_upgrade(ctx) -> dict | None:
    root = Path(ctx.root).resolve()
    index_dir = root / ".wavefoundry" / "index"
    state = detect(index_dir)
    receipt = state["receipt"]
    if receipt and receipt["state"] != "complete" and receipt.get("entry_path") == "setup":
        if getattr(ctx, "entry_path", None) != "setup":
            raise MigrationRequired("storage_setup_resume_required: resume the recorded wf setup continuation")
        from setup_reconciliation import validate_source_binding
        validate_source_binding(root, receipt)
    if state["authority_diagnostic"]:
        raise MigrationRequired(
            state["authority_diagnostic"] + ": both index database names exist and no version-2 "
            "receipt proves which is authority. Both files are preserved; stop every Wavefoundry "
            "host and recover the intended database before resuming the upgrade.")
    if getattr(ctx, "rebuild_storage", False) and (
            is_kind_receipt(receipt) or _kind_dispatch(state)
            or (receipt is None and not state["migration_required"])
            or (receipt is not None and receipt["state"] == "complete"
                and not state["kind_required"])):
        raise MigrationRequired("storage_rebuild_not_applicable: no pending legacy storage conversion")
    # An existing framework can have a loaded old MCP writer even before its
    # first index exists. Fence that upgrade before setup creates schema 7.
    # from_version is the coordinator's installed-version context; a genuine
    # fresh installer has none. Conservatively this also restarts a current,
    # never-indexed target once, without introducing a second capability marker.
    upgrading_without_index = (bool(getattr(ctx, "from_version", None))
                               and state["authority_role"] is None)
    if not state["migration_required"] and receipt is None and not upgrading_without_index:
        return None
    if getattr(ctx, "dry_run", False):
        return {"state": "restart_required", "legacy": state["legacy"],
                "kind": KIND_SCHEMA8 if _kind_dispatch(state) else None}
    if receipt is None:
        receipt = _new_receipt(ctx, root, index_dir, state)
        _write(index_dir, receipt)
    elif receipt["state"] == "complete":
        if not state["kind_required"]:
            return receipt
        # The completed record's once-marker is satisfied; the next one is the
        # schema-8 kind, which supersedes it in the same receipt file.
        receipt = _new_receipt(ctx, root, index_dir, state, superseded=receipt)
        _write(index_dir, receipt)
    if (getattr(ctx, "to_version", None) and receipt.get("target_version")
            and ctx.to_version != receipt["target_version"]):
        raise MigrationRequired("storage_target_changed: recover the recorded upgrade first")
    consumed_pack = Path(ctx.zip_path).resolve() if getattr(ctx, "zip_path", None) else None
    if consumed_pack is None:
        if receipt.get("pack_path") or receipt.get("pack_sha256"):
            raise MigrationRequired("storage_pack_changed: supply the recorded package with --pack")
    else:
        expected = receipt.get("pack_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise MigrationRequired("storage_pack_changed: recorded package SHA-256 is missing or invalid; retain the receipt and original archive for recovery")
        if _file_hash(consumed_pack) != expected:
            raise MigrationRequired("storage_pack_changed: recorded package content changed")
        # A locator can move; only the recorded digest authorizes replacement.
        receipt["pack_path"] = _pack_locator(ctx, consumed_pack, expected)
        _write(index_dir, receipt)
    _select_strategy(ctx, index_dir, receipt)
    # The kind needs a coordinator that declares protocol 2; the version-1
    # conversion needs only 1. A coordinator declaring less receives the
    # existing restart handoff and the installed CLI resumes it.
    protocol = int(getattr(ctx, "storage_migration_protocol", 0) or 0)
    qualified = protocol >= required_protocol(receipt)
    if receipt["state"] in READABLE_STATES and qualified:
        return receipt
    if receipt["state"] in READABLE_STATES:
        raise MigrationRequired("storage_current_runner_required: resume using the installed upgrade CLI; storage was already published")
    _refresh_hosts(root, receipt)
    restore_checkpoint(root)
    # Old archive dispatchers cannot honor new storage guards; always unwind
    # their installing invocation before running any native conversion.
    confirmed = os.environ.get(CONFIRM_ENV) == "1"
    if not qualified or not confirmed:
        _pause_for_restart(ctx, receipt)
    _hosts_gone(receipt)
    receipt["hosts_stopped_confirmed"] = True
    receipt["confirmed_at"] = time.time()
    if receipt["state"] == "restart_required":
        receipt["state"] = "quiesced"
    _write(index_dir, receipt)
    restore_checkpoint(root)
    return receipt


def _assert_sources(index_dir: Path, receipt: dict) -> None:
    for name, identity in receipt["artifacts"].items():
        if name not in LEGACY_NAMES or not storage_identity.compare_identity(identity, _identity(index_dir / name))["matches"]:
            raise MigrationRequired(f"storage_source_identity_changed: {name}")


def _row_digest(row: dict) -> str:
    row = dict(row)
    row.pop("_distance", None)
    import math
    error = ("storage_vector_invalid: source vector is not qualified finite 384D. "
             + LEGACY_RECOVERY_GUIDANCE)
    try:
        values = [float(v) for v in row.pop("vector")]
        if len(values) != 384 or not all(math.isfinite(v) for v in values):
            raise MigrationRequired(error)
        packed = struct.pack("<384f", *values)
    except (KeyError, TypeError, ValueError, OverflowError, struct.error) as exc:
        raise MigrationRequired(error) from exc
    return hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode() + packed).hexdigest()


def _source_fingerprint(index_dir: Path, receipt: dict) -> dict:
    result = {}
    for name in receipt["artifacts"]:
        base = _safe(index_dir / name)
        if base.is_file():
            result[name] = _file_hash(base)
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            _safe(Path(directory))
            for child in dirs:
                _safe(Path(directory) / child)
            for child in sorted(files):
                path = _safe(Path(directory) / child)
                result[str(path.relative_to(index_dir))] = _file_hash(path)
    return result


def _legacy_table(index_dir: Path, layer: str):
    """The sole legacy import; no normal-runtime import or auto-install."""
    try:
        import lancedb
    except ImportError as exc:
        raise MigrationRequired("storage_legacy_reader_missing: provision pinned migration-only lancedb==0.33.0 through setup") from exc
    if lancedb.__version__ != "0.33.0":
        raise MigrationRequired("storage_legacy_reader_version: require migration-only lancedb==0.33.0")
    try:
        db = lancedb.connect(str(index_dir))
        table = db.open_table(layer)
        # Pin the table and stream Arrow batches through the bundled reader.
        # to_lance() would introduce a second optional native package (pylance).
        table.checkout(table.version)
        return table
    except Exception as exc:
        raise MigrationRequired(f"storage_legacy_source_unreadable: {layer}. "
                                + LEGACY_RECOVERY_GUIDANCE) from exc


def _legacy_counts(index_dir: Path, artifacts: dict) -> dict:
    try:
        return {layer: _legacy_table(index_dir, layer).count_rows()
                if layer + ".lance" in artifacts else 0 for layer in ("docs", "code")}
    except MigrationRequired:
        raise
    except Exception as exc:
        raise MigrationRequired("storage_legacy_source_unreadable: row-count preflight. "
                                + LEGACY_RECOVERY_GUIDANCE) from exc


def _legacy_batches(index_dir: Path, layer: str):
    """Stream pinned Arrow batches without the optional pylance dependency."""
    table = _legacy_table(index_dir, layer)
    try:
        for batch in table.search().limit(None).to_batches(batch_size=512):
            yield batch.to_pylist()
    except Exception as exc:
        raise MigrationRequired(f"storage_legacy_source_unreadable: {layer} scan. "
                                + LEGACY_RECOVERY_GUIDANCE) from exc


def _sync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        if os.name == "nt":
            return
        raise
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _clear_rebuild_candidate(conn) -> None:
    """Clear only known derived semantics on an unpublished backup copy."""
    import index_state_store as state_store
    with conn:
        for layer in ("docs", "code"):
            conn.execute(f"DELETE FROM chunks_{layer}")
            conn.execute(f"DELETE FROM vectors_{layer}")
            for prefix in (state_store.META_FTS_CHURN_PREFIX, state_store.META_FTS_FINGERPRINT_PREFIX,
                           state_store.META_FTS_HEAL_ATTEMPT_PREFIX, state_store.META_CHUNK_SYNC_RAW_PREFIX,
                           state_store.META_CHUNK_SYNC_UNIQUE_PREFIX, state_store.META_CHUNK_ID_COLLISIONS_PREFIX,
                           state_store.META_CHUNK_ID_COLLISION_SAMPLE_PREFIX):
                conn.execute("DELETE FROM meta WHERE key=?", (prefix + layer,))
            state_store._write_fts_digest_meta(conn, layer, 0)
        for table in ("chunk_registry", "layer_path_state", "build_file_meta", "build_layer_meta"):
            conn.execute(f"DELETE FROM {table}")
        conn.executemany("DELETE FROM meta WHERE key=?", [(key,) for key in
            (state_store.META_LEXICAL_STATISTICS, state_store.META_REAP_STATE, REBUILD_PROOF_KEY)])
        conn.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (state_store.META_CHUNK_INDEX_COLD,"1"))
        conn.execute("UPDATE build_state SET status='building',attempt_id=?,scope='all',started_at=?,completed_at=NULL WHERE id=1",
                     (uuid.uuid4().hex, time.time()))


def _rebuild_metadata(meta: dict) -> dict:
    return {key: meta.get(key) for key in ("model_versions", "chunker_versions", "walker_version", "content")}


def record_rebuild_proof(conn, receipt: dict, inventory: dict, options: dict, meta: dict, attempt: str) -> None:
    """Written only by a strict full docs+code build, in its data transaction."""
    from sqlite_vector_store import capacity_qualification
    counts = {layer: conn.execute(f"SELECT count(*) FROM chunks_{layer}").fetchone()[0] for layer in ("docs", "code")}
    qualification = capacity_qualification(counts)
    if not qualification["qualified"]:
        raise MigrationRequired("storage_capacity_unqualified: current rebuilt corpus exceeds qualification; original storage retained")
    proof = {"migration_id": receipt["migration_id"], "rebuild_id": receipt["rebuild_id"],
             "semantic_attempt": attempt, "layers": ["docs", "code"], "counts": counts,
             "inventory": inventory, "options": options, "metadata": _rebuild_metadata(meta),
             "capacity_qualification": qualification}
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                 (REBUILD_PROOF_KEY, json.dumps(proof, sort_keys=True, separators=(",", ":"))))


def _validated_rebuild_proof(root: Path, receipt: dict):
    import sqlite_runtime
    import indexer
    index_dir = Path(root) / ".wavefoundry/index"
    conn = sqlite_runtime.connect(_published_identity(index_dir, receipt), read_only=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (REBUILD_PROOF_KEY,)).fetchone()
        try:
            proof = json.loads(row[0]) if row else None
        except (ValueError, TypeError) as exc:
            raise MigrationRequired("storage_rebuild_proof_invalid") from exc
        if (not isinstance(proof, dict) or proof.get("migration_id") != receipt["migration_id"]
                or proof.get("rebuild_id") != receipt.get("rebuild_id") or proof.get("layers") != ["docs", "code"]):
            raise MigrationRequired("storage_rebuild_proof_missing: complete both semantic layers from current source")
        counts = {layer: conn.execute(f"SELECT count(*) FROM chunks_{layer}").fetchone()[0] for layer in ("docs", "code")}
        from sqlite_vector_store import capacity_qualification
        qualification = capacity_qualification(counts)
        if not qualification["qualified"] or proof.get("counts") != counts:
            raise MigrationRequired("storage_rebuild_counts_unverified")
        layer_meta = dict(conn.execute("SELECT key,value FROM build_layer_meta"))
        metadata = {key: json.loads(layer_meta.get(key, "null")) for key in ("model_versions", "chunker_versions", "content")}
        metadata["walker_version"] = layer_meta.get("walker_version")
        if metadata != proof.get("metadata"):
            raise MigrationRequired("storage_rebuild_metadata_changed")
        current_chunker = getattr(indexer._get_chunker(), "CHUNKER_VERSION", "")
        if (metadata["walker_version"] != indexer.WALKER_VERSION
                or metadata["chunker_versions"] != {"docs": current_chunker, "code": current_chunker}
                or metadata["content"] != ["code", "docs"]):
            raise MigrationRequired("storage_rebuild_metadata_stale: repeat the full source rebuild")
        for layer, model in (("docs", indexer.DOCS_MODEL), ("code", indexer.CODE_MODEL)):
            version = (metadata["model_versions"] or {}).get(layer, "")
            precision = indexer._precision_class_from_version(version)
            if version != f"{model}@{precision}@{indexer._identity_fingerprint_for_class(precision)}":
                raise MigrationRequired("storage_rebuild_metadata_stale: embedding identity changed")
        stored_inventory = {layer: dict(conn.execute("SELECT path,hash FROM layer_path_state WHERE layer=?", (layer,)))
                            for layer in ("docs", "code")}
        if stored_inventory != proof.get("inventory"):
            raise MigrationRequired("storage_rebuild_inventory_unverified")
        if indexer.preflight_rebuild_sources(root, index_dir, **proof.get("options", {})) != stored_inventory:
            raise MigrationRequired("storage_rebuild_source_changed: repeat the full source rebuild")
        epoch = conn.execute("SELECT attempt_id,generation,status FROM build_state WHERE id=1").fetchone()
        if epoch is None or epoch[2] not in {"building", "complete"}:
            raise MigrationRequired("storage_rebuild_epoch_unverified")
        return proof, epoch, hashlib.sha256(row[0].encode()).hexdigest()
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise MigrationRequired("storage_rebuild_proof_invalid") from exc
    finally:
        conn.close()


def validate_rebuild_publication(root: Path, staging_receipt: dict | None = None) -> dict | None:
    receipt = read_receipt(Path(root) / ".wavefoundry/index")
    if not rebuild_requested(receipt) or receipt["state"] == "complete":
        return None
    proof, epoch, digest = _validated_rebuild_proof(root, receipt)
    binding = receipt.get("upgrade_publication", {}).get("rebuild")
    generation = epoch[1] + (1 if staging_receipt is not None else 0)
    if (not isinstance(binding, dict) or binding.get("proof_sha256") != digest
            or binding.get("attempt_id") != epoch[0] or binding.get("generation") != generation
            or (staging_receipt is None and epoch[2] != "complete")
            or (staging_receipt is not None and (epoch[2] != "building"
                or staging_receipt.get("attempt_id") != epoch[0]
                or staging_receipt.get("expected_generation") != generation))):
        raise MigrationRequired("storage_rebuild_publication_unverified: complete the current parent-owned rebuild")
    return proof


def migrate_legacy(root: Path, hosts_stopped: bool = False) -> dict:
    """Stage and switch under the caller's upgrade/publication ownership.

    The old stores remain until new-process verification; source reconciliation
    and final publication run through the ordinary subsequent index build.
    """
    root = Path(root)
    index_dir = root / ".wavefoundry" / "index"
    state = detect(index_dir)
    receipt = state["receipt"]
    if state["authority_diagnostic"]:
        raise MigrationRequired(
            state["authority_diagnostic"] + ": both index database names exist and no version-2 "
            "receipt proves which is authority; both files are preserved")
    rebuild = rebuild_requested(receipt)
    if not state["migration_required"] and receipt is None:
        return {"state": "not_applicable"}
    if receipt is None:
        raise MigrationRequired("storage_restart_required: run the primary upgrade phase first")
    restore_checkpoint(root)
    if receipt["state"] in READABLE_STATES:
        if receipt["state"] != "complete":
            _published_identity(index_dir, receipt)
        if not (state["kind_required"] and not is_kind_receipt(receipt)):
            return receipt
        # The version-1 conversion finished its package-bound recovery; the
        # schema-8 kind now runs on its result, in this same upgrade.
        receipt = _begin_chained_kind(root, index_dir, receipt, state, hosts_stopped)
    if not (hosts_stopped or receipt.get("hosts_stopped_confirmed")) or receipt["state"] == "restart_required":
        raise MigrationRequired("storage_restart_required")
    _refresh_hosts(root, receipt)
    _hosts_gone(receipt)
    _assert_sources(index_dir, receipt)
    import sqlite_runtime as runtime
    import index_state_store as state_store
    from indexer import _index_build_lock
    with _index_build_lock(index_dir):
        try:
            runtime.preflight(index_dir)
        except runtime.RuntimeUnavailable as exc:
            raise MigrationRequired(
                f"storage_runtime_restart_required: {exc}; start a fresh process and resume "
                "the recorded owning setup or upgrade continuation with confirm_hosts_stopped=True (CLI --confirm-hosts-stopped). "
                "Migration paused before staging or cutover; original stores and receipt are retained.") from exc
        except runtime.StorageRecoveryRequired as exc:
            raise MigrationRequired(
                f"{exc}; storage migration paused before staging or cutover. "
                "Original stores, candidate and receipt are retained; correct the runtime or "
                "filesystem requirement and resume the recorded owning setup or upgrade continuation.") from exc
        if is_kind_receipt(receipt):
            return _migrate_schema8(root, index_dir, receipt, runtime, state_store)
        source_path = source_database_path(index_dir, receipt)
        if receipt["state"] != "cutover_pending":
            source_identity = receipt.get("source_sqlite_identity")
            if source_identity is not None and not storage_identity.compare_identity(source_identity, _identity(source_path))["matches"]:
                raise MigrationRequired(f"storage_source_identity_changed: {source_path.name}")
            if ("source_sqlite_identity" in receipt and source_identity is None
                    and source_path.exists()):
                raise MigrationRequired(f"storage_source_identity_changed: unexpected {source_path.name}")
            schema = _database_schema(source_path)
            if schema == "runtime_unavailable":
                raise MigrationRequired(
                    "storage_runtime_restart_required: provision the pinned native runtime through the owning operation; "
                    "then start a fresh process and resume the recorded owning setup or upgrade continuation with confirm_hosts_stopped=True "
                    "(CLI --confirm-hosts-stopped). Installed bindings cannot replace this process's cached "
                    "runtime. The migration receipt and original database are retained.")
            if schema == SCHEMA_VERSION and not receipt["artifacts"]:
                receipt.update(state="complete", disposition="already_current", reclaimed_bytes=0)
                _write(index_dir, receipt)
                return receipt
            if schema not in {"absent"} | LEGACY_SCHEMA_VERSIONS:
                raise MigrationRequired(f"storage_schema_unsupported: {schema}; original database retained")
            from sqlite_vector_store import capacity_qualification
            if rebuild:
                from indexer import preflight_rebuild_sources
                preflight_rebuild_sources(root, index_dir)
                receipt.pop("source_preflight_counts", None)
                receipt["capacity_qualification"] = {"status": "pending_current_rebuild", "qualified": None}
                qualification = None
            else:
                preflight_counts = _legacy_counts(index_dir, receipt["artifacts"])
                qualification = capacity_qualification(preflight_counts)
                receipt["capacity_qualification"] = qualification
                receipt["source_preflight_counts"] = preflight_counts
            if qualification is not None and not qualification["qualified"]:
                receipt["last_failure"] = {"code": "storage_capacity_unqualified", "at": time.time()}
                _write(index_dir, receipt)
                raise MigrationRequired(
                    "storage_capacity_unqualified: source exceeds the measured conversion envelope; "
                    "original stores and checkpoint retained. Qualify this larger corpus before resuming: "
                    + json.dumps(qualification, sort_keys=True))
            if receipt.get("last_failure", {}).get("code") == "storage_capacity_unqualified":
                receipt.pop("last_failure")
            _write(index_dir, receipt)
        fingerprint = _source_fingerprint(index_dir, receipt)
        source_size = sum((index_dir / name).stat().st_size for name in fingerprint)
        live_size = source_path.stat().st_size if source_path.exists() else 0
        if shutil.disk_usage(index_dir).free < source_size * 2 + live_size * 2 + 64 * 1024 * 1024:
            raise MigrationRequired("storage_disk_space_insufficient: retain original stores and free staging space")
        work = _safe(index_dir / (LEGACY_WORK_PREFIX + receipt["migration_id"]))
        if work.exists() and not storage_identity.compare_identity(receipt.get("work_identity"), _identity(work))["matches"]:
            raise MigrationRequired("storage_staging_identity_changed")
        work.mkdir(exist_ok=True)
        live = _safe_sqlite(published_database_path(index_dir, receipt))
        # Staging is named for the store module that OPENS it, not for the
        # record's publication target.
        staged = _safe_sqlite(staged_database_path(work))
        backup = _safe_sqlite(work / STAGING_ROLLBACK_STEM)
        receipt["work_dir"] = work.name
        receipt["work_identity"] = _identity(work)
        _write(index_dir, receipt)
        if receipt["state"] == "cutover_pending":
            # No blind repeat: the file identity determines whether replacement
            # landed before an interrupted receipt write.
            if live.exists() and _file_hash(live) == receipt.get("candidate_sha256"):
                _published_identity(index_dir, receipt)
                receipt["state"] = "published"
                receipt["cutover_pid"] = receipt.get("staging_pid")
                _write(index_dir, receipt)
                return receipt
            if (staged.exists() and _file_hash(staged) == receipt.get("candidate_sha256")
                    and (not source_path.exists() and receipt.get("original_sha256") is None
                         or source_path.exists() and _file_hash(source_path) == receipt.get("original_sha256"))
                    and (live == source_path or not live.exists())):
                return _publish_candidate(root, receipt, staged, live)
            raise MigrationRequired("storage_cutover_recovery_required: retained candidate and rollback need verification")
        for candidate in (staged, *index_paths.sidecar_paths(staged)):
            _safe(candidate).unlink(missing_ok=True)
        if source_path.exists():
            runtime.backup(_safe_sqlite(source_path), _safe_sqlite(staged))
            if not backup.exists():
                runtime.backup(_safe_sqlite(source_path), _safe_sqlite(backup))
            staging_conn = runtime.connect(_safe_sqlite(staged), full_durability=True)
            try:
                if staging_conn.execute("PRAGMA auto_vacuum").fetchone() != (2,):
                    staging_conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
                    staging_conn.execute("VACUUM")
            finally:
                staging_conn.close()
        store = state_store.IndexStateStore(work, migration=True)
        counts = {}
        try:
            conn = store._conn
            if rebuild:
                _clear_rebuild_candidate(conn)
            for layer in ("docs", "code"):
                count = 0
                seen = set()
                if not rebuild and layer + ".lance" in receipt["artifacts"]:
                    for rows in _legacy_batches(index_dir, layer):
                        for row in rows:
                            _row_digest(row)
                            if not row.get("id") or row["id"] in seen:
                                raise MigrationRequired("storage_duplicate_or_missing_chunk_id: retain the receipt, original sources and any recorded archive; "
                                    "if current project sources are available, resume the owning setup or upgrade continuation with --rebuild-storage "
                                    "to regenerate both semantic layers instead of transferring legacy rows")
                            seen.add(row["id"])
                        state_store._apply_chunk_deltas_locked(store, layer, add_rows=rows)
                        for row in rows:
                            actual = conn.execute(f"SELECT c.payload,c.text,c.text_present,v.embedding FROM chunks_{layer} c JOIN vectors_{layer} v ON c.id=v.chunk_id WHERE c.chunk_id=?", (row["id"],)).fetchone()
                            if actual is None:
                                raise MigrationRequired("storage_transfer_missing_row")
                            payload = json.loads(actual[0])
                            if actual[2]:
                                payload["text"] = actual[1]
                            payload["vector"] = struct.unpack("<384f", actual[3])
                            if _row_digest(payload) != _row_digest(row):
                                raise MigrationRequired("storage_transfer_payload_mismatch")
                        count += len(rows)
                if conn.execute(f"SELECT count(*) FROM chunks_{layer}").fetchone()[0] != count:
                    raise MigrationRequired("storage_transfer_count_mismatch")
                conn.execute(f"INSERT INTO fts_{layer}(fts_{layer}, rank) VALUES('integrity-check',1)")
                counts[layer] = count
            if not rebuild and counts != receipt["source_preflight_counts"]:
                raise MigrationRequired("storage_source_counts_changed_during_transfer")
            with conn:
                conn.execute("UPDATE build_state SET status='building' WHERE id=1")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            store.close()
        _assert_sources(index_dir, receipt)
        if fingerprint != _source_fingerprint(index_dir, receipt):
            raise MigrationRequired("storage_source_changed_during_transfer")
        if rebuild:
            from indexer import preflight_rebuild_sources
            preflight_rebuild_sources(root, index_dir)
            receipt.pop("source_counts", None)
            receipt["candidate_counts"] = counts
        else:
            receipt["source_counts"] = counts
        receipt.update(state="validated", staging_pid=os.getpid())
        _write(index_dir, receipt)
        # All handles are closed. Flush the staging file before atomic replace.
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        _quiesce_source(runtime, source_path)
        receipt.update(state="cutover_pending", candidate_sha256=_file_hash(staged),
                       published_sqlite_identity=_identity(staged),
                       original_sha256=_file_hash(source_path) if source_path.exists() else None)
        _write(index_dir, receipt)
        return _publish_candidate(root, receipt, staged, live)


def _begin_chained_kind(root: Path, index_dir: Path, superseded: dict,
                        state: dict, hosts_stopped: bool) -> dict:
    """Supersede a finished version-1 record with the schema-8 kind.

    Same upgrade, same stopped hosts, same package binding. The version-1
    record is embedded verbatim under ``supersedes`` as historical evidence;
    its retired artifacts and any explicit rebuild strategy carry forward so
    ONE cleanup arm owns everything the chained conversion leaves behind.
    """
    if not (hosts_stopped or superseded.get("hosts_stopped_confirmed")):
        raise MigrationRequired("storage_restart_required")
    receipt = dict(superseded)
    receipt.pop("restart_action", None)
    receipt.pop("upgrade_publication", None)
    for key in ("work_dir", "work_identity", "candidate_sha256", "original_sha256",
                "published_sqlite_identity", "cutover_pid", "staging_pid", "verification",
                "removed", "reclaimed_bytes", "disposition", "source_counts",
                "candidate_counts", "source_preflight_counts", "last_failure"):
        receipt.pop(key, None)
    role = state["authority_role"] or SOURCE_ROLE_LEGACY
    receipt.update(receipt_version=RECEIPT_VERSION_CURRENT, kind=KIND_SCHEMA8,
                   migration_id=uuid.uuid4().hex, state="quiesced",
                   reason="index_database_rename", source_database=role,
                   source_sqlite_identity=_identity_if_present(_role_path(index_dir, role)),
                   artifacts={name: identity for name, identity in superseded.get("artifacts", {}).items()
                              if (index_dir / name).exists()},
                   supersedes=superseded, hosts_stopped_confirmed=True)
    _write(index_dir, receipt)
    restore_checkpoint(root)
    return receipt


def _staging_index_dir(work: Path) -> Path:
    """``<work>/.wavefoundry/index`` — the nested layout the entry needs.

    The lock-free coordinator entry derives its repository root and its
    test-run fence from the index directory's parents. Staging under a nested
    ``.wavefoundry/index`` keeps every derived path inside the staging tree,
    while the source walk still receives the real repository root explicitly.
    """
    return work / ".wavefoundry" / "index"


def _clear_staging_tree(staging_index: Path) -> None:
    """Forward-only restaging: discard any earlier candidate under this record."""
    for child in sorted(staging_index.iterdir()) if staging_index.exists() else ():
        _safe(child)
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _reset_staged_graph(conn) -> None:
    """Start empty graph/extraction/community tables before the full rebuild.

    Never seeded from the old graph folder: the transition is a rebuild from
    current sources, not a conversion of old graph artifacts.
    """
    import graph_store
    import graph_indexer
    with conn:
        for table in graph_store.GRAPH_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM meta WHERE key LIKE ?",
                     (graph_indexer.GRAPH_META_PREFIX + "%",))


def _layer_chunk_counts(conn) -> dict:
    return {layer: conn.execute(f"SELECT count(*) FROM chunks_{layer}").fetchone()[0]
            for layer in ("docs", "code")}


def _validate_staged_candidate(runtime, staged: Path, source_counts: dict) -> dict:
    """Procedure step 4's staged participant validation, before any cutover."""
    import sqlite_vector_store as vectors
    # Read-write: the FTS integrity-check is a write statement, and this is an
    # UNPUBLISHED staging copy the migration exclusively owns.
    conn = runtime.connect(_safe_sqlite(staged))
    try:
        version = conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone()
        if version != (SCHEMA_VERSION,):
            raise MigrationRequired("storage_staged_schema_unverified: original database retained")
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise MigrationRequired("storage_staged_integrity_failed: original database retained")
        counts = _layer_chunk_counts(conn)
        if counts != source_counts:
            raise MigrationRequired("storage_staged_counts_changed: original database retained")
        for layer in ("docs", "code"):
            integrity = vectors.vector_integrity(conn, layer)
            if (integrity["missing_vectors"] or integrity["orphan_vectors"]
                    or integrity["canonical"] != integrity["vectors"]):
                raise MigrationRequired("storage_staged_vector_integrity_failed: original database retained")
            conn.execute(f"INSERT INTO fts_{layer}(fts_{layer}, rank) VALUES('integrity-check',1)")
        epoch = conn.execute("SELECT attempt_id,generation,status FROM build_state WHERE id=1").fetchone()
        if epoch is None or epoch[2] != "complete":
            raise MigrationRequired("storage_staged_epoch_unverified: original database retained")
        import graph_indexer
        graph = {"nodes": conn.execute("SELECT count(*) FROM graph_nodes").fetchone()[0],
                 "edges": conn.execute("SELECT count(*) FROM graph_edges").fetchone()[0],
                 "files": conn.execute("SELECT count(*) FROM graph_file_state").fetchone()[0]}
        builder = conn.execute("SELECT value FROM meta WHERE key=?",
                               (graph_indexer.GRAPH_META_PREFIX + "builder_version",)).fetchone()
        if not builder or not str(builder[0]):
            raise MigrationRequired("storage_staged_graph_unverified: rebuilt graph recorded no builder version")
        return {"counts": counts, "graph": graph, "builder_version": str(builder[0]),
                "attempt_id": epoch[0], "generation": epoch[1],
                "rebuilt_at": time.time(), "pid": os.getpid()}
    except MigrationRequired:
        raise
    except Exception as exc:
        raise MigrationRequired("storage_staged_validation_failed: original database retained") from exc
    finally:
        conn.close()


def _quiesce_source(runtime, source: Path) -> None:
    """Truncate the source WAL so no committed frame is left behind on rename."""
    if not source.exists():
        return
    conn = runtime.connect(_safe_sqlite(source))
    try:
        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and checkpoint[0]:
            raise MigrationRequired("storage_handles_busy")
    finally:
        conn.close()


def _forward_recovery(source: Path) -> str:
    return ("Recovery is FORWARD: resume the recorded owning setup or upgrade continuation from the retained "
            f"{source.name}; the rollback copy is retained as evidence and is never "
            "returned to service. No backward rollback to the old runner is offered.")


def _resume_schema8_cutover(root: Path, index_dir: Path, receipt: dict,
                            staged: Path, live: Path, source: Path) -> dict:
    """Interruption before/after filesystem publication, by identity only."""
    if live.exists() and _file_hash(live) == receipt.get("candidate_sha256"):
        # Published before the receipt advanced; adopt it, never republish.
        _published_identity(index_dir, receipt)
        receipt["state"] = "published"
        receipt["cutover_pid"] = receipt.get("staging_pid")
        _write(index_dir, receipt)
        restore_checkpoint(root)
        return receipt
    # The accepted schema-7 population includes the current filename. In that
    # case the destination is still the original source before replacement;
    # require both its recorded identity and checkpointed bytes before retrying.
    if (staged.exists() and _file_hash(staged) == receipt.get("candidate_sha256")
            and (not live.exists() or live == source)
            and source.exists()
            and storage_identity.compare_identity(receipt.get("source_sqlite_identity"), _identity(source))["matches"]
            and _file_hash(source) == receipt.get("original_sha256")):
        return _publish_candidate(root, receipt, staged, live)
    raise MigrationRequired("storage_cutover_recovery_required: retained candidate and source "
                            "need verification. " + _forward_recovery(source))


_candidate_build = ContextVar("sqlite_migration_candidate_build", default=None)


@contextmanager
def _candidate_build_scope(index_dir: Path, receipt: dict, staging_index: Path):
    """Complete an owned unpublished candidate without authorizing live memory.

    This is deliberately not an environment override: sibling threads and live
    index producers retain their ordinary publication context.
    """
    index_dir = Path(index_dir).resolve()
    work = _safe(index_dir / (KIND_WORK_PREFIX + receipt["migration_id"]))
    expected = _safe(_staging_index_dir(work))
    candidate = _safe_sqlite(staged_database_path(expected))
    current = read_receipt(index_dir)
    if (current != receipt or receipt.get("kind") != KIND_SCHEMA8
            or receipt.get("state") != "staged"
            or receipt.get("staging_pid") != os.getpid()
            or receipt.get("work_dir") != work.name
            or receipt.get("work_identity") != _identity(work)
            or Path(staging_index).absolute() != expected
            or not candidate.is_file()):
        raise MigrationRequired("storage_staging_identity_changed")
    binding = (index_dir, receipt["migration_id"], expected, _identity(expected),
               candidate, _identity(candidate), work, _identity(work))
    token = _candidate_build.set(binding)
    try:
        yield
    finally:
        _candidate_build.reset(token)


def is_unpublished_candidate(index_dir: Path) -> bool:
    """True only inside this migration's exact, still-owned candidate build."""
    binding = _candidate_build.get()
    if binding is None or Path(index_dir).absolute() != binding[2]:
        return False
    live_index, migration_id, staging, staging_id, candidate, candidate_id, work, work_id = binding
    receipt = read_receipt(live_index)
    if (not receipt or receipt.get("migration_id") != migration_id
            or receipt.get("state") != "staged" or receipt.get("kind") != KIND_SCHEMA8
            or receipt.get("staging_pid") != os.getpid()
            or receipt.get("work_identity") != work_id
            or _identity(staging) != staging_id or _identity(work) != work_id
            or _identity(_safe_sqlite(candidate)) != candidate_id):
        raise MigrationRequired("storage_staging_identity_changed")
    return True


def _migrate_schema8(root: Path, index_dir: Path, receipt: dict, runtime, state_store) -> dict:
    """Stage, rebuild the graph from current sources, then publish the rename."""
    source = _safe_sqlite(source_database_path(index_dir, receipt))
    live = _safe_sqlite(published_database_path(index_dir, receipt))
    work = _safe(index_dir / (KIND_WORK_PREFIX + receipt["migration_id"]))
    if work.exists() and not storage_identity.compare_identity(receipt.get("work_identity"), _identity(work))["matches"]:
        raise MigrationRequired("storage_staging_identity_changed")
    work.mkdir(exist_ok=True)
    staging_index = _safe(_staging_index_dir(work))
    staging_index.mkdir(parents=True, exist_ok=True)
    staged = _safe_sqlite(staged_database_path(staging_index))
    backup = _safe_sqlite(staging_index / STAGING_ROLLBACK_STEM)
    receipt["work_dir"] = work.name
    receipt["work_identity"] = _identity(work)
    _write(index_dir, receipt)

    if receipt["state"] == "cutover_pending":
        return _resume_schema8_cutover(root, index_dir, receipt, staged, live, source)

    source_identity = receipt.get("source_sqlite_identity")
    if source_identity is None or not source.exists() or not storage_identity.compare_identity(source_identity, _identity(source))["matches"]:
        raise MigrationRequired(f"storage_source_identity_changed: {source.name}. "
                                + _forward_recovery(source))
    # Retain a strict same-run race check after accepting persisted continuity.
    source_snapshot = _identity(source)
    if live.exists() and live != source:
        raise MigrationRequired(
            AUTHORITY_AMBIGUOUS + f": {live.name} already exists before this record's cutover; "
            "both files are preserved. " + _forward_recovery(source))
    schema = _database_schema(source)
    if schema == "runtime_unavailable":
        raise MigrationRequired(
            "storage_runtime_restart_required: provision the pinned native runtime through the owning operation, "
            "then resume the recorded owning setup or upgrade continuation with confirm_hosts_stopped=True. The migration receipt "
            "and original database are retained.")
    if schema == SCHEMA_VERSION and live == source:
        receipt.update(state="complete", disposition="already_current", reclaimed_bytes=0)
        _write(index_dir, receipt)
        return receipt
    if schema not in LEGACY_SCHEMA_VERSIONS | {SCHEMA_VERSION}:
        raise MigrationRequired(f"storage_schema_unsupported: {schema}; original database retained")
    source_size = source.stat().st_size
    if shutil.disk_usage(index_dir).free < source_size * 3 + 64 * 1024 * 1024:
        raise MigrationRequired("storage_disk_space_insufficient: retain original stores and free staging space")

    # Forward-only restaging: an interrupted earlier candidate is discarded and
    # rebuilt from the retained source, never resumed in place.
    _clear_staging_tree(staging_index)
    runtime.backup(source, staged)
    runtime.backup(source, backup)
    # Precondition 2: pre-open the staged store ONCE in migration mode, so the
    # legacy-to-current arm has run and the entry's non-migration open sees the
    # current schema.
    store = state_store.IndexStateStore(staging_index, migration=True)
    try:
        source_counts = _layer_chunk_counts(store._conn)
        _reset_staged_graph(store._conn)
        store._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        store.close()
    receipt.update(state="staged", staging_pid=os.getpid(),
                   rollback={"name": backup.name, "identity": _identity(backup),
                             "sha256": _file_hash(backup)})
    _write(index_dir, receipt)

    import indexer
    import sqlite_vector_store as vector_store
    # The entry always consumes prepared updates. Empty graph-only preparation
    # stays in memory; any overflow belongs to the staging tree.
    with _candidate_build_scope(index_dir, receipt, staging_index), \
            vector_store.PreparedUpdates(staging_index) as prepared:
        summary = indexer._build_index_locked(
            Path(root), content="graph", full=True, index_dir=staging_index,
            prepared=prepared)
    if summary.get("failed"):
        raise MigrationRequired(
            "storage_staged_graph_rebuild_failed: " + str(summary.get("failure", "")) + ". "
            "Original database and graph are retained. " + _forward_recovery(source))
    receipt["staged_rebuild"] = _validate_staged_candidate(runtime, staged, source_counts)
    receipt["state"] = "validated"
    _write(index_dir, receipt)
    # Committed rebuild output must live in the staged MAIN file: only that file
    # is published, so a surviving staged WAL would silently drop rows.
    _quiesce_source(runtime, staged)
    for sidecar in index_paths.sidecar_paths(staged):
        _safe(sidecar).unlink(missing_ok=True)

    _assert_sources(index_dir, receipt)
    _hosts_gone(receipt)
    with staged.open("rb") as handle:
        os.fsync(handle.fileno())
    _quiesce_source(runtime, source)
    if _identity(source) != source_snapshot:
        raise MigrationRequired(f"storage_source_identity_changed: {source.name}. "
                                + _forward_recovery(source))
    # Cutover intent recorded durably BEFORE the atomic publish, so an
    # interruption on either side of os.replace is decidable by identity.
    receipt.update(state="cutover_pending", candidate_sha256=_file_hash(staged),
                   published_sqlite_identity=_identity(staged),
                   original_sha256=_file_hash(source),
                   cutover={"source_role": _source_role(receipt), "source": source.name,
                            "published": live.name, "intent_at": time.time()})
    _write(index_dir, receipt)
    return _publish_candidate(root, receipt, staged, live)


def _published_identity(index_dir: Path, receipt: dict) -> Path:
    """Fence the cutover file, not its mutable generation or sidecar identities."""
    live = _safe_sqlite(published_database_path(index_dir, receipt))
    expected = receipt.get("published_sqlite_identity")
    if not expected:
        raise MigrationRequired(
            "storage_publication_identity_missing: retained receipt cannot prove the cutover file; "
            "preserve original stores and staging/rollback files for recovery before resuming the recorded owning continuation")
    if not live.exists() or not storage_identity.compare_identity(expected, _identity(live))["matches"]:
        raise MigrationRequired("storage_publication_identity_changed: preserve original stores and recover the receipt-owned cutover file")
    return live


def _publish_candidate(root: Path, receipt: dict, staged: Path, live: Path) -> dict:
    _hosts_gone(receipt)
    if not receipt.get("published_sqlite_identity") or not storage_identity.compare_identity(receipt["published_sqlite_identity"], _identity(staged))["matches"]:
        raise MigrationRequired("storage_cutover_candidate_identity_changed")
    _safe_sqlite(live)
    try:
        for index, sidecar in enumerate(index_paths.sidecar_paths(live)):
            sidecar = _safe(sidecar)
            if sidecar.exists() and index == 0 and sidecar.stat().st_size:
                raise MigrationRequired("storage_cutover_live_wal_changed")
            sidecar.unlink(missing_ok=True)
        os.replace(staged, live)
    except OSError as exc:
        raise MigrationRequired(
            "storage_cutover_io_failed: cannot remove a SQLite sidecar or replace the live database. "
            "Close programs holding the index files, allow transient scanner activity to finish, "
            "and check filesystem permissions. Candidate, rollback and cutover_pending receipt "
            "are retained; resume the recorded owning setup or upgrade continuation after releasing handles or fixing access.") from exc
    _sync_directory(live.parent)
    _published_identity(live.parent, receipt)
    receipt.update(state="published", cutover_pid=os.getpid())
    _write(live.parent, receipt)
    restore_checkpoint(root)
    return receipt


def record_upgrade_publication(root: Path) -> None:
    """Receipt for the coordinator's observed successful semantic AND graph children."""
    index_dir = Path(root) / ".wavefoundry/index"
    receipt = read_receipt(index_dir)
    if receipt is None or receipt["state"] == "complete":
        return
    receipt["upgrade_publication"] = {"semantic_exit": 0, "graph_exit": 0,
                                      "coordinator_pid": os.getpid(), "completed_at": time.time()}
    if rebuild_requested(receipt):
        proof, epoch, digest = _validated_rebuild_proof(root, receipt)
        receipt["capacity_qualification"] = proof["capacity_qualification"]
        receipt["upgrade_publication"]["rebuild"] = {"proof_sha256": digest,
            "attempt_id": epoch[0], "generation": epoch[1] + (epoch[2] == "building")}
    _write(index_dir, receipt)


def begin_upgrade_publication(root: Path) -> None:
    """A retry must not inherit a previous successful all-layer observation."""
    index_dir = Path(root) / ".wavefoundry/index"
    receipt = read_receipt(index_dir)
    if receipt is None or receipt["state"] == "complete":
        return
    if receipt["state"] in READABLE_STATES:
        _published_identity(index_dir, receipt)
    receipt.pop("upgrade_publication", None)
    _write(index_dir, receipt)
    if rebuild_requested(receipt):
        import sqlite_runtime
        conn = sqlite_runtime.connect(_published_identity(index_dir, receipt))
        try:
            with conn:
                conn.execute("DELETE FROM meta WHERE key=?", (REBUILD_PROOF_KEY,))
        finally:
            conn.close()


def verify_migration(root: Path) -> dict:
    """Reopen published storage in a new process and exercise native readers."""
    root = Path(root)
    index_dir = root / ".wavefoundry/index"
    receipt = read_receipt(index_dir)
    if receipt is None:
        return {"state": "not_applicable"}
    if receipt["state"] == "complete":
        return receipt
    if receipt.get("entry_path") == "setup":
        from setup_reconciliation import validate_source_binding
        validate_source_binding(root, receipt)
    if is_kind_receipt(receipt):
        # The kind's proof is its OWN validated staged rebuild, not a later
        # coordinator child: the graph was rebuilt and validated before cutover.
        if not isinstance(receipt.get("staged_rebuild"), dict):
            raise MigrationRequired("storage_staged_rebuild_unverified: resume the recorded owning setup or upgrade continuation")
        if rebuild_requested(receipt):
            validate_rebuild_publication(root)
    else:
        publication = receipt.get("upgrade_publication", {})
        if publication.get("semantic_exit") != 0 or publication.get("graph_exit") != 0:
            raise MigrationRequired("storage_all_layer_publication_unverified: resume the recorded owning setup or upgrade continuation")
        validate_rebuild_publication(root)
    prior_verification = receipt.get("verification", {})
    independently_opened = (prior_verification.get("pid") is not None
                            and prior_verification["pid"] != receipt.get("cutover_pid"))
    if (receipt["state"] not in READABLE_STATES
            or receipt.get("cutover_pid") == os.getpid() and not independently_opened):
        raise MigrationRequired("storage_new_process_verification_required")
    _hosts_gone(receipt)
    import sqlite_runtime as runtime
    import sqlite_vector_store as vectors
    live = _published_identity(index_dir, receipt)
    conn = runtime.connect(live)
    try:
        _published_identity(index_dir, receipt)
        version = conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone()
        epoch = conn.execute("SELECT attempt_id,generation,status FROM build_state WHERE id=1").fetchone()
        if version != (SCHEMA_VERSION,) or epoch is None or epoch[2] != "complete":
            raise MigrationRequired("storage_publication_unverified")
        if is_kind_receipt(receipt):
            # Kind-aware: the rename only counts when the rebuilt graph actually
            # survived the cutover into the published file.
            staged_graph = receipt["staged_rebuild"].get("graph", {})
            published_nodes = conn.execute("SELECT count(*) FROM graph_nodes").fetchone()[0]
            if staged_graph.get("nodes") and not published_nodes:
                raise MigrationRequired("storage_publication_graph_missing")
        if conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise MigrationRequired("storage_integrity_failed")
        for layer in ("docs", "code"):
            integrity = vectors.vector_integrity(conn, layer)
            if (integrity["missing_vectors"] or integrity["orphan_vectors"]
                    or integrity["canonical"] != integrity["vectors"]):
                raise MigrationRequired("storage_vector_integrity_failed")
            conn.execute(f"INSERT INTO fts_{layer}(fts_{layer},rank) VALUES('integrity-check',1)")
            row = conn.execute(f"SELECT embedding FROM vectors_{layer} LIMIT 1").fetchone()
            if row is not None and not vectors.dense_rows(index_dir, layer, row[0], 1):
                raise MigrationRequired("storage_vector_query_failed")
            text = conn.execute(f"SELECT text FROM chunks_{layer} WHERE text<>'' LIMIT 1").fetchone()
            if text is not None:
                token = re.search(r"\w+", text[0], re.UNICODE)
                if token and conn.execute(f"SELECT count(*) FROM fts_{layer} WHERE fts_{layer} MATCH ?", ('"' + token.group() + '"',)).fetchone()[0] == 0:
                    raise MigrationRequired("storage_fts_query_failed")
    finally:
        conn.close()
    _published_identity(index_dir, receipt)
    receipt.update(state="verified", verification={"pid": prior_verification.get("pid", os.getpid()),
                    "last_check_pid": os.getpid(), "attempt_id": epoch[0],
                    "generation": epoch[1], "schema": SCHEMA_VERSION,
                    "counts": vectors.layer_counts(index_dir), "verified_at": time.time()})
    _write(index_dir, receipt)
    return receipt


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with _safe(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _install_kind_fence(root: Path, index_dir: Path, superseded: dict) -> dict:
    """Run the schema-8 kind on a store the completed conversion published.

    The version-1 conversion publishes onto the name runtime consumers open,
    so the once-marker (``meta.store_schema_version = 8`` in the current
    database) is already satisfied and there is nothing to restage. What is
    missing is the version-2 record: without it a version-1 runner reads a
    "complete" version-1 receipt, finds nothing under the retired name and
    creates a fresh empty database beside the published index. Installing the
    record IS the fence, and it also retires any database the conversion left
    behind under the retired name.
    """
    live = _safe_sqlite(index_paths.index_database_path(index_dir))
    published = _identity_if_present(live)
    if published is None or not storage_identity.compare_identity(superseded.get("published_sqlite_identity"), published)["matches"]:
        raise MigrationRequired(
            "storage_publication_identity_changed: the completed conversion's published database "
            "is not the current index database; preserve both files and resume the recorded owning setup or upgrade continuation")
    legacy = _safe_sqlite(index_paths.legacy_index_database_path(index_dir))
    role = SOURCE_ROLE_LEGACY if legacy.exists() else SOURCE_ROLE_CURRENT
    receipt = dict(superseded)
    receipt.pop("restart_action", None)
    for key in ("work_dir", "work_identity", "candidate_sha256", "original_sha256"):
        receipt.pop(key, None)
    receipt.update(receipt_version=RECEIPT_VERSION_CURRENT, kind=KIND_SCHEMA8,
                   migration_id=uuid.uuid4().hex, state="verified",
                   reason="index_database_fence", source_database=role,
                   source_sqlite_identity=_identity_if_present(legacy) if role == SOURCE_ROLE_LEGACY else None,
                   published_sqlite_identity=published,
                   staged_rebuild={"inherited_from": superseded["migration_id"],
                                   "at": time.time(), "restaged": False},
                   supersedes=superseded)
    _write(index_dir, receipt)
    if receipt.get("entry_path") == "setup":
        # The fence is a new record in the same setup operation. Persist its
        # identity before retirement so a crash resumes the exact new record.
        restore_checkpoint(root)
    reclaimed = receipt.get("reclaimed_bytes", 0)
    retired = _retire_source_database(index_dir, receipt) if role == SOURCE_ROLE_LEGACY else 0
    receipt.update(state="complete", reclaimed_bytes=reclaimed + retired,
                   retired_source_bytes=retired)
    _write(index_dir, receipt)
    restore_checkpoint(root)
    return receipt


def _plan_retire_source_database(index_dir: Path, receipt: dict) -> dict:
    """VALIDATE the receipt-owned source retirement. Deletes nothing.

    Every refusal this arm can raise -- ownership, identity, and a non-empty
    ``-wal`` whose committed frames exist nowhere else -- lives here, so
    :func:`cleanup_legacy` reaches all of them while the source is still
    intact. Returns ``{"paths": [...], "bytes": n}``; an absent source plans
    zero work, which is what makes a retry after a partial cleanup converge.
    """
    source = _safe_sqlite(source_database_path(index_dir, receipt))
    identity = receipt.get("source_sqlite_identity")
    if not source.exists():
        return {"paths": [], "bytes": 0}
    if source == published_database_path(index_dir, receipt):
        # Same-name cutover already replaced the original. Its rollback copy
        # is retired by the staging inventory, never by deleting the live file.
        _published_identity(index_dir, receipt)
        return {"paths": [], "bytes": 0}
    if identity is None or not storage_identity.compare_identity(identity, _identity(source))["matches"]:
        raise MigrationRequired(f"storage_cleanup_identity_changed: {source}. "
                                + SPURIOUS_LEGACY_GUIDANCE)
    reclaimed = source.stat().st_size
    sidecars = []
    for index, sidecar in enumerate(index_paths.sidecar_paths(source)):
        sidecar = _safe(sidecar)
        if not sidecar.exists():
            continue
        if index == 0 and sidecar.stat().st_size:
            raise MigrationRequired("storage_cleanup_live_wal_changed: preserve the retired database "
                                    f"until its write-ahead log is checkpointed: {sidecar}")
        reclaimed += sidecar.stat().st_size
        sidecars.append(sidecar)
    return {"paths": [*sidecars, source], "bytes": reclaimed}


def _apply_retire_source_database(plan: dict) -> int:
    """Execute a validated retirement plan: sidecars first, main file last."""
    parent = None
    for path in plan["paths"]:
        parent = path.parent
        path.unlink()
    if parent is not None:
        _sync_directory(parent)
    return plan["bytes"]


def _retire_source_database(index_dir: Path, receipt: dict) -> int:
    """Validate then delete, for the fence arm that has no staging to inventory."""
    return _apply_retire_source_database(_plan_retire_source_database(index_dir, receipt))


def _unknown_staging(path: Path) -> MigrationRequired:
    """The staging refusal, NAMING the entry that caused it.

    The refusal is only actionable if the operator can see which path to
    remove; the message used to name nothing, so the recovery instruction was
    "read the source".
    """
    return MigrationRequired(
        f"storage_cleanup_unknown_staging_artifact: {path}. This entry is inside the "
        "migration's own staging directory but is not something the staged build "
        "produces. Nothing has been deleted. Remove or move the named entry, then "
        "resume the recorded owning setup or upgrade continuation; the retired source database and the receipt are "
        "retained.")


def _inventory_kind_staging(work: Path) -> dict:
    """CLASSIFY exactly the nested staging structure. Deletes nothing.

    ``<work>/.wavefoundry/index/`` holds the staged database family, the
    rollback family, the memory state database the staged build's coordinator
    creates, the prepared-updates spool, and the derived ``scan`` output. Any
    other entry is an unknown staging artifact and refuses HERE -- before
    :func:`cleanup_legacy` has deleted anything at all, so the operator can fix
    the named path and retry.

    Returns ``{"trees": [...], "files": [...], "dirs": [...], "bytes": n}``:
    subtrees to remove wholesale, individual files to unlink, and the
    directories to ``rmdir`` afterwards in the returned order.
    """
    reclaimed = 0
    trees: list[Path] = []
    files: list[Path] = []

    def entries(directory: Path):
        return sorted(directory.iterdir()) if directory.exists() else []

    def tree_bytes(path: Path) -> int:
        total = 0
        for base, dirs, names in os.walk(path, followlinks=False):
            _safe(Path(base))
            for child in dirs + names:
                node = _safe(Path(base) / child)
                if node.is_file():
                    total += node.stat().st_size
        return total

    for child in entries(work):
        _safe(child)
        if child.name != ".wavefoundry" or not child.is_dir():
            raise _unknown_staging(child)
    nested = work / ".wavefoundry"
    for child in entries(nested):
        _safe(child)
        if not child.is_dir() or child.name not in {"index", "locks"}:
            raise _unknown_staging(child)
        if child.name == "locks":
            reclaimed += tree_bytes(child)
            trees.append(child)
    staging_index = _staging_index_dir(work)
    allowed = _staging_allowlist()
    spool = frozenset(_family_names(PREPARED_SPOOL_STEM))
    spool_dirs: list[Path] = []
    for child in entries(staging_index):
        _safe(child)
        if child.is_dir():
            if child.name in STAGING_DERIVED_DIRNAMES:
                reclaimed += tree_bytes(child)
                trees.append(child)
                continue
            if not child.name.startswith(PREPARED_SPOOL_PREFIX):
                raise _unknown_staging(child)
            for member in entries(child):
                _safe(member)
                if not member.is_file() or member.name not in spool:
                    raise _unknown_staging(member)
                reclaimed += member.stat().st_size
                files.append(member)
            spool_dirs.append(child)
            continue
        if not child.is_file() or child.name not in allowed:
            raise _unknown_staging(child)
        reclaimed += child.stat().st_size
        files.append(child)
    return {"trees": trees, "files": files,
            "dirs": [*spool_dirs, staging_index, nested, work], "bytes": reclaimed}


def _apply_kind_staging(plan: dict) -> int:
    """Execute a validated staging plan. Every refusal already happened."""
    for tree in plan["trees"]:
        shutil.rmtree(tree)
    for path in plan["files"]:
        path.unlink()
    for directory in plan["dirs"]:
        if directory.exists():
            directory.rmdir()
    return plan["bytes"]


def _inventory_retired_graph_directory(index_dir: Path) -> dict:
    """Procedure step 6's pre-deletion inventory of ``<index>/graph/``.

    ``lstat`` every entry WITHOUT following links and classify it against the
    owned-name allowlist. Any unknown name, any nested directory, or any
    symlink/reparse node at any depth preserves the WHOLE folder, reports the
    entries, and records cleanup state ``retained_unowned_contents``. The
    whole-tree primitive ``_remove_retired_component`` is the final delete step
    only -- never the classifier -- so it is reached only when the inventory
    says every entry is owned.

    Returns ``{"state": ..., "path": ..., "entries": [...], "bytes": n}`` with
    ``state`` one of ``absent``, ``removable`` or ``retained_unowned_contents``.
    """
    # ``_safe`` the ANCESTORS only. The folder itself is classified by lstat
    # here, because a folder that IS a link must be PRESERVED (procedure step
    # 6's rule) rather than refused -- and it is never followed either way.
    graph_dir = _safe(index_dir) / GRAPH_OUTPUT_DIRNAME
    try:
        metadata = graph_dir.lstat()
    except FileNotFoundError:
        return {"state": "absent", "path": str(graph_dir), "entries": [], "bytes": 0}
    if _is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
        # Not the framework-owned folder at all: never delete through a link,
        # and never unlink a stray file under the folder's name.
        return {"state": RETAINED_UNOWNED_CONTENTS, "path": str(graph_dir),
                "entries": [graph_dir.name], "bytes": 0,
                "reason": "the retired graph path is not a real directory"}
    unowned: list[str] = []
    reclaimed = 0
    with os.scandir(graph_dir) as scan:
        children = sorted(scan, key=lambda entry: entry.name)
    for entry in children:
        child_metadata = os.lstat(entry.path)
        if _is_link_or_reparse(child_metadata):
            unowned.append(entry.name)
        elif stat.S_ISDIR(child_metadata.st_mode):
            unowned.append(entry.name)
        elif not _is_owned_graph_entry(entry.name):
            unowned.append(entry.name)
        else:
            reclaimed += child_metadata.st_size
    if unowned:
        return {"state": RETAINED_UNOWNED_CONTENTS, "path": str(graph_dir),
                "entries": unowned, "bytes": 0,
                "reason": "unknown names, nested directories or link nodes are preserved "
                          "with the whole folder"}
    return {"state": "removable", "path": str(graph_dir),
            "entries": [entry.name for entry in children], "bytes": reclaimed}


def _apply_retired_graph_directory(root: Path, index_dir: Path, plan: dict) -> int:
    """Delete the all-owned retired graph folder. The inventory already ruled."""
    if plan["state"] != "removable":
        return 0
    from upgrade_wavefoundry import _remove_retired_component
    outcome = _remove_retired_component(index_dir, GRAPH_OUTPUT_DIRNAME,
                                        custom=False, ownership_root=root)
    if outcome == "absent":
        return 0
    if outcome != "removed":
        raise MigrationRequired(
            f"storage_cleanup_removal_failed: {plan['path']} ({outcome}). Release handles or "
            "correct permissions and resume the recorded owning setup or upgrade continuation; receipt and remaining "
            "sources are retained.")
    return plan["bytes"]


def _plan_legacy_artifacts(index_dir: Path, receipt: dict, removed: set) -> list:
    """CLASSIFY the receipt's inherited Lance artifacts. Deletes nothing.

    Ownership, identity and artifact-type refusals all live here so they fire
    before any deletion, and the recorded byte counts come from the same walk.
    """
    plan = []
    for name, identity in receipt["artifacts"].items():
        _published_identity(index_dir, receipt)
        if name not in LEGACY_NAMES:
            raise MigrationRequired(f"storage_cleanup_path_unowned: {index_dir / name}")
        path = _safe(index_dir / name)
        if name in removed or not path.exists():
            plan.append({"name": name, "kind": "absent", "path": str(path), "bytes": 0})
            continue
        if not storage_identity.compare_identity(identity, _identity(path))["matches"]:
            raise MigrationRequired(f"storage_cleanup_identity_changed: {path}")
        size = 0
        for base, dirs, files in os.walk(path, followlinks=False):
            _safe(Path(base))
            for child in dirs + files:
                node = _safe(Path(base) / child)
                if node.is_file():
                    size += node.stat().st_size
        if path.is_dir():
            plan.append({"name": name, "kind": "directory", "path": str(path), "bytes": size})
        elif name == "__manifest" and path.is_file():
            plan.append({"name": name, "kind": "file", "path": str(path),
                         "bytes": path.stat().st_size})
        else:
            raise MigrationRequired(f"storage_cleanup_artifact_type_invalid: {path}")
    return plan


def _plan_staging(index_dir: Path, receipt: dict):
    """CLASSIFY this record's staging directory, by kind. Deletes nothing."""
    work_name = receipt.get("work_dir")
    if not work_name:
        return None
    if work_name != _work_prefix(receipt) + receipt["migration_id"]:
        raise MigrationRequired(f"storage_cleanup_work_identity_invalid: {index_dir / work_name}")
    work = _safe(index_dir / work_name)
    if not work.exists():
        return None
    if not storage_identity.compare_identity(receipt.get("work_identity"), _identity(work))["matches"]:
        raise MigrationRequired(f"storage_cleanup_work_identity_changed: {work}")
    if is_kind_receipt(receipt):
        return _inventory_kind_staging(work)
    allowed = _staging_allowlist()
    files = []
    total = 0
    for path in sorted(work.iterdir()):
        _safe(path)
        if not path.is_file() or path.name not in allowed:
            raise _unknown_staging(path)
        total += path.stat().st_size
        files.append(path)
    return {"trees": [], "files": files, "dirs": [work], "bytes": total}


def _apply_legacy_staging(plan: dict) -> int:
    """The version-1 record's flat staging directory. Validation already ran."""
    return _apply_kind_staging(plan)


def cleanup_legacy(root: Path) -> dict:
    """Delete only identity-bound obsolete project artifacts after verification."""
    root = Path(root).resolve()
    index_dir = root / ".wavefoundry" / "index"
    receipt = read_receipt(index_dir)
    if receipt is None:
        if detect(index_dir)["legacy"]:
            raise MigrationRequired("storage_cleanup_unverified")
        return {"state": "not_applicable", "reclaimed_bytes": 0}
    if receipt["state"] == "complete":
        return receipt
    if receipt["state"] not in {"verified", "cleanup_pending"}:
        raise MigrationRequired("storage_cleanup_unverified")
    # Revalidate the current coherent generation, not an obsolete exact epoch.
    receipt = verify_migration(root)
    _hosts_gone(receipt)
    removed = set(receipt.get("removed", []))
    reclaimed = receipt.get("reclaimed_bytes", 0)

    # --- PLAN. Nothing below this comment mutates the filesystem. -----------
    # Every refusal this function can raise is reachable HERE, while the
    # operator's only index is still on disk. Source retirement used to run
    # before the staging walk, so a staging refusal arrived after the source
    # had been deleted and recorded as retired -- and the retry then skipped
    # retirement, re-entered the same walk and refused again, permanently.
    # Inventory first, refuse first, delete last.
    artifact_plan = _plan_legacy_artifacts(index_dir, receipt, removed)
    source_plan = None
    if is_kind_receipt(receipt) and "retired_source_bytes" not in receipt:
        _published_identity(index_dir, receipt)
        source_plan = _plan_retire_source_database(index_dir, receipt)
    staging_plan = _plan_staging(index_dir, receipt)
    graph_plan = (_inventory_retired_graph_directory(index_dir)
                  if is_kind_receipt(receipt) else None)

    # --- APPLY. Validation is finished; from here the work is irreversible. -
    receipt["state"] = "cleanup_pending"
    _write(index_dir, receipt)
    for entry in artifact_plan:
        name = entry["name"]
        if entry["kind"] == "absent":
            removed.add(name)
            continue
        if entry["kind"] == "directory":
            # Reuse the existing upgrade cleanup's fd-anchored POSIX deletion
            # and explicitly narrower, revalidated Windows no-follow fallback.
            from upgrade_wavefoundry import _remove_retired_component
            outcome = _remove_retired_component(index_dir, name, custom=False, ownership_root=root)
            if outcome == "unowned":
                raise MigrationRequired(
                    "storage_cleanup_path_unowned: an owned index path changed or contains a "
                    f"symlink/junction: {entry['path']}. Restore the receipt-owned directory "
                    "inside the repository and resume the recorded owning setup or upgrade continuation; receipt and remaining "
                    "sources are retained.")
            if outcome != "removed":
                raise MigrationRequired(
                    f"storage_cleanup_removal_failed: {entry['path']} ({outcome}). Release handles "
                    "or correct permissions and resume the recorded owning setup or upgrade continuation; receipt and remaining "
                    "sources are retained.")
        else:
            _safe(Path(entry["path"])).unlink()
        reclaimed += entry["bytes"]
        removed.add(name)
        receipt.update(removed=sorted(removed), reclaimed_bytes=reclaimed)
        _write(index_dir, receipt)
    if source_plan is not None:
        retired = _apply_retire_source_database(source_plan)
        reclaimed += retired
        receipt.update(retired_source_bytes=retired, reclaimed_bytes=reclaimed)
        _write(index_dir, receipt)
    if staging_plan is not None:
        reclaimed += (_apply_kind_staging(staging_plan) if is_kind_receipt(receipt)
                      else _apply_legacy_staging(staging_plan))
    if graph_plan is not None and graph_plan["state"] != "absent":
        reclaimed += _apply_retired_graph_directory(root, index_dir, graph_plan)
        receipt["graph_directory_cleanup"] = {
            "state": "removed" if graph_plan["state"] == "removable" else graph_plan["state"],
            "path": graph_plan["path"], "entries": graph_plan["entries"],
            **({"reason": graph_plan["reason"]} if "reason" in graph_plan else {}),
        }
    receipt.update(state="complete", removed=sorted(removed), reclaimed_bytes=reclaimed,
                   dependency_disposition="retained: shared/unregistered consumers not proven absent")
    _write(index_dir, receipt)
    # Same upgrade: the schema-8 kind runs on the store the conversion just
    # finished, installing the version-2 fence the version-1 record cannot.
    if detect(index_dir)["fence_required"]:
        return _install_kind_fence(root, index_dir, receipt)
    return receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_migration(args.verify), sort_keys=True))
