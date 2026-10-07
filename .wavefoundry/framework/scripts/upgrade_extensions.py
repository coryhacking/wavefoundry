"""Framework-side upgrade extension hooks.

This module is loaded directly from inside the upgrade zip by
``upgrade_wavefoundry.py`` *before* extraction, so hooks fire at the right
phase boundaries without requiring a pre-existing copy on disk.

Hook functions
--------------
Define any of the functions below.  Each receives an ``UpgradeContext``
and should return ``None`` on success.  Raising any exception (or calling
``sys.exit()``) aborts the upgrade with exit code 3.

Available hooks (in call order):

    post_preflight(ctx)         after pre-flight checks, before zip extraction
    pre_extract(ctx)            immediately before zip extraction
    post_extract(ctx)           immediately after zip extraction
    pre_surface_rendering(ctx)  before render_platform_surfaces.py
    post_surface_rendering(ctx) after  render_platform_surfaces.py
    pre_pruning(ctx)            before prune_framework.py
    post_pruning(ctx)           after  prune_framework.py
    pre_docs_gate(ctx)          before docs-gardener && docs-lint
    post_docs_gate(ctx)         after  docs-gardener && docs-lint
    pre_index_update(ctx)       before setup_index.py (--update-index path, incremental)
    post_index_update(ctx)      after  setup_index.py (--update-index path)
    pre_index_rebuild(ctx)      before setup_index.py (--rebuild-index path, full)
    post_index_rebuild(ctx)     after  setup_index.py (--rebuild-index path)
    pre_cleanup(ctx)            before lock removal and operator summary
    post_cleanup(ctx)           after  lock removal and operator summary

UpgradeContext attributes
-------------------------
    ctx.root          Path  — repository root
    ctx.from_version  str | None — installed revision before upgrade
    ctx.to_version    str | None — target version from zip or pack
    ctx.zip_path      Path | None — path to the zip being applied
    ctx.yes           bool — True when running non-interactively (--yes / MCP)

Version-gated example
---------------------
    def post_pruning(ctx):
        # Only needed when upgrading from before the config schema change.
        if ctx.from_version and ctx.from_version >= "2026-06-01a":
            return
        _migrate_workflow_config(ctx.root)

Convention hooks
----------------
Project operators can also place executable scripts at:

    .wavefoundry/hooks/<hook-name-with-dashes>

e.g. ``.wavefoundry/hooks/post-surface-rendering``

They receive the same version info via environment variables:

    WF_FROM_VERSION   installed revision (empty string if unknown)
    WF_TO_VERSION     target version (empty string if unknown)
    WF_ROOT           absolute path to the repository root
    WF_YES            "1" if non-interactive, "0" otherwise

Convention hooks run after the extension module hook for the same phase.

Security note
-------------
The extension module is loaded from the zip by ``exec()``-ing its source into a
fresh ``types.ModuleType`` before any files are extracted.  It runs with the
operator's full user privileges — treat the zip as trusted input and verify its
provenance before running the upgrade.  The ``--dry-run`` flag surfaces the
extension module source and all convention hook scripts for review before any
disk writes occur.
"""
from __future__ import annotations

import errno
import json
import hashlib
import importlib.util
import os
import re
import shlex
import subprocess
import stat
import tempfile
import sys
import traceback
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath


_LEGACY_RUNTIME_LOCKS = (
    ("review-evidence-adoptions.lock", 0),
    ("dashboard-start.lock", 1 << 30),
    ("dashboard-server.lock", 1 << 30),
)

_PROTOCOL_METADATA_ARC = ".wavefoundry/framework/UPGRADE-PROTOCOL.json"
_GRAPH_BUILDER_DOC_CLAIM_RE = re.compile(r"graph builder version `([^`\r\n]+)`")
_GRAPH_BUILDER_DOC_SNAPSHOT_KEY = "graph_builder_doc_claim_pre_extract"
_GRAPH_BUILDER_DOC_PACK_SHA_KEY = "graph_builder_doc_claim_pack_sha256"
_DOC_SCALAR_SNAPSHOT_KEY = "docs_scalar_claims_pre_extract"
_DOC_SCALAR_PACK_SHA_KEY = "docs_scalar_claims_pack_sha256"

# Keep this registry aligned with the scalar module-constant claims in
# wave_lint_lib/docs_constants_validators.py.  Vocabulary claims owned by
# public_contract are intentionally excluded: they are not scalar assignments
# and should remain an explicit docs-gate repair.
_DOC_SCALAR_CLAIMS = (
    (
        "docs embedding model",
        "docs/architecture/performance-budget.md",
        re.compile(r"docs embedding model `([^`\r\n]+)`"),
        ".wavefoundry/framework/scripts/indexer.py",
        "DOCS_MODEL",
    ),
    (
        "code embedding model",
        "docs/architecture/performance-budget.md",
        re.compile(r"code embedding model `([^`\r\n]+)`"),
        ".wavefoundry/framework/scripts/indexer.py",
        "CODE_MODEL",
    ),
    (
        "reranker model",
        "docs/architecture/performance-budget.md",
        re.compile(r"reranker model `([^`\r\n]+)`"),
        ".wavefoundry/framework/scripts/indexer.py",
        "RERANKER_MODEL",
    ),
    (
        "state-store schema version",
        "docs/RELIABILITY.md",
        re.compile(r"state-store schema version `([^`\r\n]+)`"),
        ".wavefoundry/framework/scripts/index_state_store.py",
        "STATE_STORE_SCHEMA_VERSION",
    ),
    (
        "graph builder version",
        "docs/RELIABILITY.md",
        _GRAPH_BUILDER_DOC_CLAIM_RE,
        ".wavefoundry/framework/scripts/graph_indexer.py",
        "GRAPH_BUILDER_VERSION",
    ),
    (
        "chunker version",
        "docs/architecture/performance-budget.md",
        re.compile(r"chunker version `([^`\r\n]+)`"),
        ".wavefoundry/framework/scripts/chunker.py",
        "CHUNKER_VERSION",
    ),
)


def _render_command(argv: list[str], *, platform_name: str | None = None) -> str:
    """Render human guidance; callers execute the original argv list."""

    selected = platform_name or os.name
    return subprocess.list2cmdline(argv) if selected == "nt" else shlex.join(argv)


def _operator_python(executable: str, *, platform_name: str | None = None) -> str:
    """Return a console interpreter for the human-run package command."""

    selected = platform_name or os.name
    if selected == "nt":
        path = PureWindowsPath(executable)
        if path.stem.lower() == "pythonw" and path.suffix.lower() == ".exe":
            return str(path.with_name(path.stem[:-1] + path.suffix))
    return executable


def post_preflight(ctx):
    """Stop a protocol-1 runner before it can enter extraction.

    The supported-floor runner already invokes this incoming hook but has no
    native protocol vocabulary. Absence of ``runner_protocol`` therefore
    identifies that legacy ABI; protocol-2 runners set it explicitly.
    """

    zip_path = getattr(ctx, "zip_path", None)
    if zip_path is None:
        return
    runner_protocol = getattr(ctx, "runner_protocol", 1)
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            metadata = json.loads(
                archive.read(_PROTOCOL_METADATA_ARC).decode("utf-8")
            )
        minimum = metadata.get("minimum_runner_protocol")
    except (OSError, KeyError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "code": "upgrade_protocol_invalid",
                    "message": f"feature-pack protocol metadata is unavailable: {exc}",
                },
                sort_keys=True,
            )
        )
        raise SystemExit(3)
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        print(json.dumps({"status": "error", "code": "upgrade_protocol_invalid"}))
        raise SystemExit(3)
    if int(runner_protocol) >= minimum:
        return
    package = Path(zip_path)
    root = Path(getattr(ctx, "root", Path.cwd())).resolve()
    command_argv = [
        _operator_python(sys.executable),
        str(package),
        "--root",
        str(root),
        "--confirm-hosts-stopped",
    ]
    command = _render_command(command_argv)
    print(
        json.dumps(
            {
                "status": "error",
                "code": "bridge_release_required",
                "runner_protocol": int(runner_protocol),
                "minimum_runner_protocol": minimum,
                "why": (
                    "the attached protocol-1 runner cannot replace itself or extract "
                    "a protocol-2 feature pack"
                ),
                "package": str(package),
                "package_present": package.is_file(),
                "command_argv": command_argv if package.is_file() else None,
                "command": command if package.is_file() else None,
                "hosts_to_stop": (
                    "Wavefoundry dashboard and MCP server processes for this repository; "
                    "keep the agent session idle while the shell command runs"
                ),
                "restart_guidance": (
                    "The agent runs command_argv through its ordinary non-MCP shell after "
                    "Wavefoundry services stop. After the package finishes or pauses, fully "
                    "restart every attached host and follow the structured recovery result."
                ),
                "legacy_wrapper_limitation": (
                    "The already-loaded protocol-1 MCP wrapper predates the current response "
                    "cap and cannot be changed by this incoming pack; this compact JSON record "
                    "is emitted last. If the host rejects or truncates it, the agent uses its "
                    "ordinary shell to detect and execute the single installed package after "
                    "Wavefoundry services stop; the operator does not enter a command."
                ),
                "acquisition": (
                    "Download the single matching wavefoundry-<version>.zip release "
                    "package when it is not present."
                ),
            },
            sort_keys=True,
        )
    )
    raise SystemExit(3)


def _read_json_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _update_upgrade_state(root: Path, **fields) -> None:
    path = root / ".wavefoundry" / "upgrade-in-progress.json"
    data = _read_json_object(path)
    if not path.exists():
        raise RuntimeError("upgrade-in-progress.json is missing during lock cutover")
    data.update(fields)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _legacy_lock_is_held(path: Path, offset: int) -> bool:
    """Probe a pre-cutover lock without importing not-yet-extracted code."""

    if not path.exists():
        return False
    handle = path.open("r+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(offset)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return True
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError):
                return True
        acquired = True
        return False
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(offset)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
        else:
            handle.close()


def _stop_dashboard_for_lock_cutover(root: Path) -> tuple[bool, int | None]:
    """Stop the old-path dashboard through the installed lifecycle implementation."""

    meta_paths = (
        root / ".wavefoundry" / "locks" / "dashboard-server.lock",
        root / ".wavefoundry" / "dashboard-server.lock",
    )
    meta = next(
        (_read_json_object(path) for path in meta_paths if path.exists()),
        {},
    )
    port = meta.get("port")
    restart_port = port if isinstance(port, int) and port > 0 else None
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        try:
            import dashboard_handlers
        except ImportError:
            # The new archive hook runs before extraction against an old tree.
            import server_impl

            stop_dashboard = getattr(
                server_impl, "wf_stop_dashboard_response", None
            ) or getattr(server_impl, "wave_dashboard_stop_response", None)
            if stop_dashboard is None:
                raise RuntimeError(
                    "installed server implementation exposes neither "
                    "wf_stop_dashboard_response nor wave_dashboard_stop_response"
                )
        else:
            stop_dashboard = dashboard_handlers.wf_stop_dashboard_response
        response = stop_dashboard(root)
    except Exception as exc:
        raise RuntimeError(f"unable to stop dashboard before lock cutover: {exc}") from exc
    if response.get("status") != "ok":
        raise RuntimeError("dashboard stop failed before runtime-lock cutover")
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    stopped = bool(data.get("stopped"))
    already_stopped = bool(data.get("already_stopped"))
    if not (stopped or already_stopped):
        raise RuntimeError("dashboard could not be verified stopped before lock cutover")
    return stopped, restart_port


def _cut_over_runtime_locks(root: Path) -> None:
    """Perform the one-way old-path cleanup before new runtime code is extracted."""

    was_running, restart_port = _stop_dashboard_for_lock_cutover(root)
    _update_upgrade_state(
        root,
        dashboard_restart_pending=was_running,
        dashboard_restart_port=restart_port,
        runtime_lock_cutover_complete=False,
    )
    old_root = root / ".wavefoundry"
    held = [
        name
        for name, offset in _LEGACY_RUNTIME_LOCKS
        if _legacy_lock_is_held(old_root / name, offset)
    ]
    legacy_producers = old_root / "logs" / "context-efficiency-producers"
    legacy_producer_leases = (
        list(legacy_producers.glob("*.lock"))
        if legacy_producers.exists()
        else []
    )
    producer_held = [
        lease.name
        for lease in legacy_producer_leases
        if _legacy_lock_is_held(lease, 0)
    ]
    if held:
        raise RuntimeError(
            "old runtime lock still held; quiesce/reload lifecycle writers before upgrade: "
            + ", ".join(held)
        )
    if producer_held:
        raise RuntimeError(
            "old context-efficiency producer lease is still held; reload active agents before upgrade: "
            + ", ".join(producer_held)
        )
    # The migration is deliberately check-then-delete: no old carrier is
    # removed until every carrier has been proven unlocked.
    for name, _offset in _LEGACY_RUNTIME_LOCKS:
        try:
            (old_root / name).unlink()
        except FileNotFoundError:
            pass
    if legacy_producers.exists():
        for lease in legacy_producer_leases:
            lease.unlink(missing_ok=True)
        try:
            legacy_producers.rmdir()
        except OSError:
            pass
    _update_upgrade_state(root, runtime_lock_cutover_complete=True)


def _read_scalar_constant(root: Path, relative: str, name: str) -> str:
    path = root / relative
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(
        rf"^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE
    )
    return match.group(1) if match else ""


def _pack_sha256(path: Path | None) -> str:
    if not isinstance(path, Path) or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_docs_scalar_claims(ctx) -> None:
    """Remember exact pre-extract matches for scalar docs-vs-code claims."""

    state = _read_json_object(ctx.root / ".wavefoundry" / "upgrade-in-progress.json")
    persisted = state.get(_DOC_SCALAR_SNAPSHOT_KEY)
    if isinstance(persisted, dict):
        snapshots = {
            str(key): str(value)
            for key, value in persisted.items()
            if isinstance(key, str) and isinstance(value, str) and value
        }
    else:
        snapshots = {}
        for label, relative_doc, pattern, script, constant in _DOC_SCALAR_CLAIMS:
            path = ctx.root / relative_doc
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            claims = list(pattern.finditer(text))
            installed = _read_scalar_constant(ctx.root, script, constant)
            if len(claims) == 1 and installed and claims[0].group(1) == installed:
                snapshots[label] = installed

    ctx.pre_extract_docs_scalar_claims = snapshots
    graph_snapshot = snapshots.get("graph builder version", "")
    ctx.pre_extract_graph_builder_doc_claim = graph_snapshot
    _update_upgrade_state(
        ctx.root,
        **{
            _DOC_SCALAR_SNAPSHOT_KEY: snapshots,
            _DOC_SCALAR_PACK_SHA_KEY: (
                _pack_sha256(getattr(ctx, "zip_path", None)) if snapshots else ""
            ),
            # Preserve the legacy graph keys for older recovery code and tests.
            _GRAPH_BUILDER_DOC_SNAPSHOT_KEY: graph_snapshot,
            _GRAPH_BUILDER_DOC_PACK_SHA_KEY: (
                _pack_sha256(getattr(ctx, "zip_path", None)) if graph_snapshot else ""
            ),
        },
    )


def _reconcile_docs_scalar_claims(ctx) -> bool:
    """Advance only exact code-matched scalar claims captured before extraction."""

    snapshots = getattr(ctx, "pre_extract_docs_scalar_claims", None)
    state = _read_json_object(ctx.root / ".wavefoundry" / "upgrade-in-progress.json")
    if not isinstance(snapshots, dict):
        persisted = state.get(_DOC_SCALAR_SNAPSHOT_KEY)
        snapshots = persisted if isinstance(persisted, dict) else {}
    if not snapshots:
        legacy = getattr(ctx, "pre_extract_graph_builder_doc_claim", "")
        if not isinstance(legacy, str) or not legacy:
            legacy = state.get(_GRAPH_BUILDER_DOC_SNAPSHOT_KEY, "")
        if isinstance(legacy, str) and legacy:
            snapshots = {"graph builder version": legacy}

    changed = False
    remaining = dict(snapshots)
    for label, relative_doc, pattern, script, constant in _DOC_SCALAR_CLAIMS:
        old = remaining.get(label, "")
        if not old:
            continue
        new = _read_scalar_constant(ctx.root, script, constant)
        if not new or new == old:
            if new == old:
                remaining.pop(label, None)
            continue
        path = ctx.root / relative_doc
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        claims = list(pattern.finditer(text))
        if len(claims) == 1 and claims[0].group(1) == new:
            remaining.pop(label, None)
            continue
        if len(claims) != 1 or claims[0].group(1) != old:
            continue
        claim = claims[0]
        path.write_text(text[: claim.start(1)] + new + text[claim.end(1) :], encoding="utf-8")
        remaining.pop(label, None)
        changed = True
        print(f"upgrade docs reconciliation: {label} {old} -> {new}", flush=True)

    ctx.pre_extract_docs_scalar_claims = remaining
    ctx.pre_extract_graph_builder_doc_claim = remaining.get("graph builder version", "")
    _update_upgrade_state(
        ctx.root,
        **{
            _DOC_SCALAR_SNAPSHOT_KEY: remaining,
            _DOC_SCALAR_PACK_SHA_KEY: state.get(_DOC_SCALAR_PACK_SHA_KEY, "")
            if remaining
            else "",
            _GRAPH_BUILDER_DOC_SNAPSHOT_KEY: ctx.pre_extract_graph_builder_doc_claim,
            _GRAPH_BUILDER_DOC_PACK_SHA_KEY: state.get(_GRAPH_BUILDER_DOC_PACK_SHA_KEY, "")
            if ctx.pre_extract_graph_builder_doc_claim
            else "",
        },
    )
    return changed


def _snapshot_graph_builder_doc_claim(ctx) -> None:
    """Backward-compatible wrapper for the generalized scalar snapshot."""

    _snapshot_docs_scalar_claims(ctx)


def _reconcile_graph_builder_doc_claim(ctx) -> bool:
    """Backward-compatible wrapper for the generalized scalar reconcile."""

    return _reconcile_docs_scalar_claims(ctx)


def _preserve_original_manifest(ctx) -> None:
    """Carry root-owned pruning authority across an old runner's fatal restart.

    Old runners erase their process-global temp copy when post_extract pauses.
    This incoming hook therefore writes the existing new-runner recovery format
    before extraction, using only stdlib APIs available in the old process.
    """
    if getattr(ctx, "dry_run", False):
        return
    target = str(getattr(ctx, "to_version", "") or "")
    if not target:
        return
    parent = Path(ctx.root) / ".wavefoundry"
    snapshot = parent / "upgrade-manifest-old.json"
    manifest = parent / "framework/MANIFEST"
    version = parent / "framework/VERSION"
    for path in (parent, parent / "framework", manifest, version, snapshot):
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(metadata.st_mode) or
                getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("upgrade MANIFEST recovery paths may not use links or reparse points")
    installed = version.read_text(encoding="utf-8").strip() if version.exists() else ""
    # Match the coordinator's byte-preserving snapshot, including CRLF from
    # Windows checkouts; universal-newline reads would reject the same manifest.
    original = manifest.read_bytes().decode("utf-8") if manifest.exists() else None
    if snapshot.exists():
        value = json.loads(snapshot.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or set(value) != {"target_version", "manifest"}
                or value.get("target_version") != target or not isinstance(value.get("manifest"), str)):
            raise ValueError("divergent upgrade MANIFEST recovery snapshot; preserve it and retry its original target")
        if installed != target and original is not None and value["manifest"] != original:
            raise ValueError("original MANIFEST differs from its retained recovery snapshot")
        return
    if original is None or installed == target:
        return
    # The upgrade lifecycle lock owns this write. Stage and fsync before the
    # atomic replace, matching the new coordinator's existing snapshot format.
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=parent, prefix=".manifest-", delete=False) as stream:
            staged = Path(stream.name)
            json.dump({"target_version": target, "manifest": original}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if snapshot.exists() or snapshot.is_symlink():
            raise ValueError("upgrade MANIFEST recovery appeared during capture; preserve both copies")
        os.replace(staged, snapshot)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    try:
        fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return  # Windows does not expose directory fsync through this API.
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _protect_existing_root_bootstrap(ctx) -> None:
    """Exclude the fresh-install bootstrap from the already-running extractor."""
    if getattr(ctx, "dry_run", False) or getattr(ctx, "zip_path", None) is None:
        return
    root = Path(ctx.root).resolve()
    path = root / "install-wavefoundry.md"
    parent = sys.modules.get(type(ctx).__module__)
    members = getattr(parent, "_EXTRACT_ROOT_MEMBERS", None)
    if parent is None or members is None:
        raise RuntimeError("upgrade_root_installer_unowned: cannot exclude install-wavefoundry.md from the old runner before extraction")
    parent._EXTRACT_ROOT_MEMBERS = frozenset(members) - {path.name}
    original = getattr(parent, "_remove_root_bootstrap_file", None)
    if callable(original):
        def preserve_existing(candidate_root):
            # Older runners may call cleanup more than once. Keep protection
            # for this root throughout the invocation; never infer ownership.
            if Path(candidate_root).resolve() != root:
                return original(candidate_root)
        parent._remove_root_bootstrap_file = preserve_existing



_INDEX_GUARD_HANDOFF = "index_guard_handoff"


def _guard_owned_path(root: Path, path: Path) -> Path:
    """Stdlib-only incoming hook: refuse links before reading checkpoint/source."""
    path.relative_to(root)
    for part in (path, *path.parents):
        if part == root:
            break
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("index_guard_checkpoint_invalid: linked recovery/source path")
    return path


def _storage_identity_helper(package, expected_sha256):
    """Use the incoming helper before extraction, with the existing zip-source loader.

    The extension loader gives archive modules a relative member filename;
    installed modules have an absolute filename. Never import the old target's
    missing or stale helper when running incoming source.
    """
    if Path(__file__).is_absolute():
        import storage_identity
        return storage_identity
    from types import ModuleType
    import io
    member = str(Path(__file__).with_name("storage_identity.py")).replace("\\", "/")
    # Execute only the bytes whose digest was checked, never reopen the path
    # after validating it: the archive can be replaced between those operations.
    package_bytes = Path(package).read_bytes()
    if hashlib.sha256(package_bytes).hexdigest() != expected_sha256:
        raise ValueError("index_guard_package_changed: resume with the recorded byte-identical --pack")
    with zipfile.ZipFile(io.BytesIO(package_bytes), "r") as archive:
        source = archive.read(member).decode("utf-8")
    helper = ModuleType("_incoming_storage_identity")
    helper.__file__ = member
    exec(compile(source, member, "exec"), helper.__dict__)
    return helper


def _validate_index_guard_handoff(root, lock, record, package=..., target=None):
    root = Path(root).resolve()
    identity = root.stat()
    package = lock.get("zip_path") if package is ... else package
    if (not isinstance(record, dict) or type(record.get("version")) is not int or record.get("version") != 1
            or type(record.get("required")) is not bool
            or any(type(record.get(key)) is not bool for key in ("prior_runtime_present", "prior_capability", "prior_coordinator_capable"))
            or record.get("required") != (record.get("prior_runtime_present") and (not record.get("prior_capability") or not record.get("prior_coordinator_capable")))
            or record.get("target_version") != (target if target is not None else lock.get("to_version"))
            or not isinstance(record.get("token"), str) or not record["token"]):
        raise ValueError("index_guard_checkpoint_invalid: preserve checkpoint and original package")
    expected = record.get("pack_sha256")
    if expected is not None:
        if (not re.fullmatch(r"[0-9a-f]{64}", str(expected)) or not package
                or _pack_sha256(Path(package)) != expected):
            raise ValueError("index_guard_package_changed: resume with the recorded byte-identical --pack")
    elif package is not None:
        raise ValueError("index_guard_package_changed: checkpoint belongs to a current-tree upgrade")
    storage_identity = _storage_identity_helper(package, expected)
    if (not storage_identity.same_path(record.get("root"), root)
            or not storage_identity.compare_identity(record.get("root_identity"), {"device": identity.st_dev, "inode": identity.st_ino})["matches"]):
        raise ValueError("index_guard_checkpoint_invalid: preserve checkpoint and original package")
    if expected is not None:
        locator = record.get("pack_path")
        if not locator or _pack_sha256(Path(locator)) != expected:
            record["pack_path"] = str(Path(package).resolve())
    return record


def _capture_index_guard_handoff(ctx):
    """Capture old capability BEFORE replacement; never recalculate on retry."""
    if getattr(ctx, "dry_run", False):
        return
    root = Path(ctx.root).resolve()
    checkpoint = _guard_owned_path(root, root / ".wavefoundry/upgrade-in-progress.json")
    if not checkpoint.exists():
        # The upgrade coordinator creates this before invoking incoming hooks.
        # Standalone hook previews without an upgrade are not publishers.
        return
    lock = json.loads(checkpoint.read_text(encoding="utf-8"))
    if _INDEX_GUARD_HANDOFF in lock:
        _validate_index_guard_handoff(root, lock, lock[_INDEX_GUARD_HANDOFF],
                                     getattr(ctx, "zip_path", None), getattr(ctx, "to_version", None))
        return
    source = _guard_owned_path(root, root / ".wavefoundry/framework/scripts/index_compatibility.py")
    import ast
    capable = False
    if source.is_file():
        try:
            module = ast.parse(source.read_text(encoding="utf-8"))
            capable = any(isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INDEX_GUARD_CAPABILITY" for t in node.targets)
                          and isinstance(node.value, ast.Constant) and type(node.value.value) is int and node.value.value >= 1
                          for node in module.body)
        except (SyntaxError, UnicodeError):
            capable = False
    package = getattr(ctx, "zip_path", None)
    digest = _pack_sha256(Path(package)) if package is not None else None
    locator = package
    selected = getattr(ctx, "selected_feature_zip", None)
    if selected is None:
        parent = sys.modules.get(type(ctx).__module__)
        finder = getattr(parent, "_find_zip", None)
        if callable(finder):
            try:
                selected = finder(root)
            except (OSError, ValueError):
                selected = None
    if selected is not None and _pack_sha256(Path(selected)) == digest:
        locator = selected
    identity = root.stat()
    record = {"version": 1, "token": uuid.uuid4().hex,
              "required": bool(getattr(ctx, "from_version", None)) and (not capable or getattr(ctx, "index_guard_coordinator_capability", 0) != 1),
              "root": str(root), "root_identity": {"device": identity.st_dev, "inode": identity.st_ino},
              "target_version": getattr(ctx, "to_version", None), "pack_sha256": digest,
              "pack_path": str(Path(locator).resolve()) if locator is not None else None,
              "prior_capability": capable, "prior_runtime_present": bool(getattr(ctx, "from_version", None)),
              "prior_coordinator_capable": getattr(ctx, "index_guard_coordinator_capability", 0) == 1}
    import upgrade_lib
    if not upgrade_lib.update_upgrade_lock(root, **{_INDEX_GUARD_HANDOFF: record}):
        raise ValueError("index_guard_checkpoint_write_failed")


def enforce_index_guard_handoff(ctx):
    """First-hop host quiescence, independent of storage conversion receipts."""
    if getattr(ctx, "dry_run", False):
        return
    root = Path(ctx.root).resolve()
    checkpoint = _guard_owned_path(root, root / ".wavefoundry/upgrade-in-progress.json")
    if not checkpoint.exists():
        return
    lock = json.loads(checkpoint.read_text(encoding="utf-8"))
    if _INDEX_GUARD_HANDOFF not in lock:
        # Already-extracted legacy checkpoints cannot prove old capability.
        # Conservatively retain an obligation rather than trusting new files.
        if not lock.get("from_version"):
            return
        identity = root.stat()
        package = lock.get("zip_path")
        record = {"version": 1, "token": uuid.uuid4().hex, "required": True,
                  "root": str(root), "root_identity": {"device": identity.st_dev, "inode": identity.st_ino},
                  "target_version": lock.get("to_version"), "pack_path": package,
                  "pack_sha256": _pack_sha256(Path(package)) if package else None,
                  "prior_capability": False, "prior_runtime_present": True, "prior_coordinator_capable": False}
    else:
        record = lock[_INDEX_GUARD_HANDOFF]
    _validate_index_guard_handoff(root, lock, record)
    if not record["required"]:
        return
    migration = getattr(ctx, "_index_guard_migration_module", None)
    if migration is None and getattr(ctx, "index_guard_coordinator_capability", 0) != 1:
        path = _guard_owned_path(root, root / ".wavefoundry/framework/scripts/sqlite_storage_migration.py")
        if path.is_file():
            spec = importlib.util.spec_from_file_location("_index_guard_installed_migration", path)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
    if migration is None:
        import sqlite_storage_migration as migration
    import upgrade_lib
    hosts, limits = migration.discover_hosts(root)
    prior_hosts = {(h["pid"], h["kind"]): h for h in record.get("old_hosts", [])}
    prior_hosts.update({(h["pid"], h["kind"]): h for h in hosts})
    record.update(old_hosts=list(prior_hosts.values()), discovery_limits=limits)
    reason = None
    if getattr(ctx, "index_guard_coordinator_capability", 0) != 1:
        reason = "index_guard_fresh_coordinator_required"
    elif os.environ.get(migration.CONFIRM_ENV) != "1":
        reason = "index_guard_hosts_confirmation_required"
    else:
        try:
            migration._hosts_gone(record)
        except migration.MigrationRequired as exc:
            reason = str(exc)
    # Keep this separate from action_required: storage/memory own that field.
    if reason:
        storage_receipt = migration.read_receipt(root / ".wavefoundry/index")
        rebuild = bool(getattr(ctx, "rebuild_storage", False)) or migration.rebuild_requested(storage_receipt)
        command = migration.restart_command(root, record.get("pack_path"), rebuild)
        record["action"] = {"status": "action_required", "code": "index_guard_restart_required",
                            "reason": reason, "kind": "index_guard_handoff", "token": record["token"],
                            "invocation_token": os.environ.get(migration.INVOCATION_ENV), **command,
                            "old_hosts": record["old_hosts"], "discovery_limits": limits,
                            "message": "Stop this repository's Wavefoundry hosts, including hosts discovery cannot observe, then run the retained command in an external terminal. Keep the checkpoint and original package. No index publication is permitted before confirmation."}
    else:
        record.pop("action", None)
        record["hosts_stopped_confirmed"] = True
    if not upgrade_lib.update_upgrade_lock(root, **{_INDEX_GUARD_HANDOFF: record}):
        raise ValueError("index_guard_checkpoint_write_failed")
    if reason:
        print(json.dumps(record["action"], sort_keys=True), flush=True)
        pause = SystemExit(3)
        pause.index_guard_token = record["token"]
        parent = sys.modules.get(type(ctx).__module__)
        original = getattr(parent, "_finalize_failed_upgrade", None)
        if callable(original) and getattr(ctx, "index_guard_coordinator_capability", 0) != 1:
            def preserve_pause(final_root, tree_mutated, current_phase):
                parent._finalize_failed_upgrade = original
                if sys.exc_info()[1] is pause and Path(final_root).resolve() == root:
                    current = upgrade_lib.read_upgrade_lock(root) or {}
                    if current.get(_INDEX_GUARD_HANDOFF, {}).get("token") == record["token"]:
                        return
                return original(final_root, tree_mutated, current_phase)
            parent._finalize_failed_upgrade = preserve_pause
        raise pause


def read_index_guard_action(root: Path, exit_code: int, invocation_token: str | None = None) -> dict | None:
    """Read the root/package-bound handoff for the invoking upgrade wrapper."""
    if exit_code != 3:
        return None
    root = Path(root).resolve()
    try:
        path = _guard_owned_path(root, root / ".wavefoundry/upgrade-in-progress.json")
        lock = json.loads(path.read_text(encoding="utf-8"))
        record = _validate_index_guard_handoff(root, lock, lock.get(_INDEX_GUARD_HANDOFF))
        action = record.get("action")
        if (not isinstance(action, dict) or action.get("token") != record["token"]
                or action.get("kind") != "index_guard_handoff"
                or action.get("code") != "index_guard_restart_required"
                or (invocation_token is not None and action.get("invocation_token") != invocation_token)):
            return None
        return action
    except (OSError, ValueError, TypeError, KeyError):
        return None


INDEX_GUARD_NEXT_STEP = (
    "Save action_required.command_argv before stopping MCP. Stop this repository's "
    "Wavefoundry hosts, including other editors and this server, then run that exact "
    "command through the ordinary non-MCP shell. Preserve the upgrade checkpoint "
    "and selected package. Follow the CLI recovery instructions before restarting hosts."
)
_INDEX_GUARD_ENVELOPE_PROOF = "_index_guard_envelope_proof"
_INDEX_GUARD_ADAPTER_LOCK = threading.Lock()


class _IndexGuardEnvelopeProof(tuple):
    """Immutable, process-local capability; never part of a serialized response."""


def _normalize_legacy_index_guard_envelope(response: dict) -> dict:
    data = response.get("data")
    action = data.get("action_required") if isinstance(data, dict) else None
    if not isinstance(action, dict) or _INDEX_GUARD_ENVELOPE_PROOF not in action:
        return response
    # The old wrapper copies the dict, caps hosts and injects storage fields.
    # Compare that exact transformation, rather than trusting kind/code alone.
    action = dict(action)
    proof = action.pop(_INDEX_GUARD_ENVELOPE_PROOF)
    valid = isinstance(proof, _IndexGuardEnvelopeProof) and len(proof) == 2
    if valid:
        root, serialized = proof
        expected = json.loads(serialized)
        hosts = expected.get("old_hosts", [])
        expected.update(old_hosts=hosts[:50], old_hosts_total=len(hosts),
                        old_hosts_omitted=max(0, len(hosts) - 50))
        expected["receipt_path"] = str(Path(root) / ".wavefoundry/index/sqlite-migration.json")
        valid = (action == expected and response.get("status") == "ok"
                 and not response.get("isError") and data.get("exit_code") == 3
                 and data.get("code") == "storage_restart_required"
                 and data.get("state") == "restart_required"
                 and data.get("restart_required") is True
                 and data.get("failed_phase") is None)
    if not valid:
        # Never serialize an internal capability or bless an altered envelope.
        return {"status": "error", "isError": True,
                "data": {"code": "index_guard_envelope_unproven", "exit_code": 3,
                         "log_path": data.get("log_path")},
                "diagnostics": [{"code": "index_guard_envelope_unproven",
                                 "message": "Restart response changed after checkpoint validation. "
                                            "Preserve the upgrade checkpoint and selected package; "
                                            "inspect the recorded continuation before resuming."}],
                "next_tools": ["wf_upgrade_status"]}
    action.pop("receipt_path")
    return {**response, "status": "action_required", "isError": False,
            "data": {**data, "code": "index_guard_restart_required",
                     "action_required": action, "failed_phase": None},
            "diagnostics": [], "next_step": INDEX_GUARD_NEXT_STEP}


def legacy_index_guard_restart_action(root: Path, exit_code: int,
                                     invocation_token: str, caller) -> dict | None:
    """Bridge the ppjy wrapper's installed reader to its final response boundary.

    This does not reload a runner or producers. Already-cached old readers cannot
    call this seam. No pending-response registry is used: each validated action
    carries its own immutable capability across the old wrapper's dict copy.
    """
    namespace = caller.f_globals
    wrapper = namespace.get("wf_upgrade_response")
    if (exit_code != 3 or not invocation_token
            or namespace.get("INDEX_GUARD_RESPONSE_VERSION", 0) >= 1
            or caller.f_code.co_name != "wf_upgrade_response"
            or getattr(wrapper, "__code__", None) is not caller.f_code):
        return None
    action = read_index_guard_action(root, exit_code, invocation_token)
    if action is None:
        return None
    with _INDEX_GUARD_ADAPTER_LOCK:
        original = namespace.get("_bounded_upgrade_response_envelope")
        if not callable(original):
            return None
        if not getattr(original, "_index_guard_envelope_adapter", False):
            def bounded(response):
                return original(_normalize_legacy_index_guard_envelope(response))
            bounded._index_guard_envelope_adapter = True
            namespace["_bounded_upgrade_response_envelope"] = bounded
    # Installation must succeed BEFORE the old storage branch sees this action.
    # Retain the caller's spelling for the synthetic receipt field comparison
    # (e.g. macOS /var -> /private/var). The reader already validated its resolved
    # ownership; normalizing this locator would reject a legitimate old wrapper.
    return {**action, _INDEX_GUARD_ENVELOPE_PROOF: _IndexGuardEnvelopeProof(
        (str(Path(root)), json.dumps(action, ensure_ascii=False)))}


def pre_index_rebuild(ctx):
    enforce_index_guard_handoff(ctx)


# Wave 1yxyw: the moved server modules whose flat aliases are retired. This is
# an upgrade-mandatory module, which older runners validate against flat module
# stems only, so it keeps its own copy instead of importing wf_server;
# test_server_package pins it to server_impl._RETIRED_FLAT_NAMES.
RETIRED_FLAT_SERVER_MODULES = (
    "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
    "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
    "docs_handlers", "context_efficiency_handlers",
)


def post_pruning(ctx):
    """Report retired flat server files the MANIFEST-diff prune left behind.

    Report only: the prune is the sole deletion authority. A leftover means the
    prune did not run or could not be proven. Never raises, because an older
    runner turns a hook exception into exit 3 after pruning changed the tree.
    """
    try:
        scripts = Path(ctx.root) / ".wavefoundry" / "framework" / "scripts"
        leftovers = [f"{name}.py" for name in RETIRED_FLAT_SERVER_MODULES
                     if (scripts / f"{name}.py").is_file()]
        if leftovers:
            print(
                f"WARNING: retired flat server module file(s) remain in {scripts}: "
                f"{', '.join(leftovers)}. Delete them: the implementations now live in "
                "wf_server/, and while a file remains an 'import <name>' of that flat "
                "name loads the stale copy instead of failing.",
                flush=True,
            )
    except Exception as exc:  # noqa: BLE001 - reporting must never abort the upgrade
        print(f"note: could not check for retired flat server module files: {exc}", flush=True)


def pre_extract(ctx):
    """Snapshot lint-bound facts, then quiesce old dedicated lock carriers."""

    _capture_index_guard_handoff(ctx)
    _protect_existing_root_bootstrap(ctx)
    _preserve_original_manifest(ctx)
    _snapshot_graph_builder_doc_claim(ctx)
    _cut_over_runtime_locks(ctx.root)


# Wave 1zeyo (1zesi): the pure framework modules the memory bootstrap
# (``ensure_run``, ``sync_inventory``, ``reconcile_index_publication``) reaches
# at runtime, leaf-first. A pre-upgrade runner holds its own copies in
# ``sys.modules``; refreshing only ``memory_backfill`` left it calling new code
# against an old ``record_paths`` (a 1.27 ``RecordRoots`` has no ``archive``).
# The v1.27.0 runner also imports ``memory_backfill`` itself after this hook,
# so the refresh happens in this process rather than in a subprocess.
_MEMORY_BOOTSTRAP_MODULES = (
    "vocabulary_profile",
    "path_containment",
    "repo_root",
    "record_paths",
    "memory_records",
    "memory_backfill",
)
# Framework modules the bootstrap reaches that are never reloaded, and why.
_MEMORY_BOOTSTRAP_EXCLUDED = {
    "index_state_store": (
        "holds build-state locks and context variables; the bootstrap calls only "
        "read_build_state, whose definition is unchanged since v1.27.0"
    ),
    "lifecycle_id": (
        "activates the tool venv when imported; memory_records calls only "
        "build_prefix and load_lifecycle_policy, both unchanged since v1.27.0"
    ),
}


def _reload_in_place(module) -> None:
    """Re-execute a cached module from the extracted source, keeping its exception classes.

    ``importlib.reload`` updates the module's namespace in place, so functions
    that other modules imported by name (``from record_paths import
    load_record_roots``) raise the NEW exception class, while those modules'
    ``except`` clauses still name the OLD one they imported. Rebinding each
    exception class that survives the reload to its original object keeps
    those holders catching what the reloaded code raises. The exception classes
    in the reloaded modules carry the same definition as in v1.27.0.

    The rebinding runs in a ``finally`` (wave 1zqe4, 1zrah): a reload that
    raises part-way has already re-executed every statement before the failing
    one, so a class it re-defined would otherwise stay split from the holders.
    """

    name = module.__name__
    kept = {
        attr: value
        for attr, value in vars(module).items()
        if isinstance(value, type)
        and issubclass(value, BaseException)
        and value.__module__ == name
    }
    try:
        importlib.reload(module)
    finally:
        for attr, old in kept.items():
            new = getattr(module, attr, None)
            if isinstance(new, type) and issubclass(new, BaseException):
                setattr(module, attr, old)


def _installed_memory_backfill(root: Path):
    """Load the just-extracted coordinator, even under a pre-upgrade runner."""

    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    # Same cross-extraction seam as ``_reload_cached_review_evidence``: a
    # pre-upgrade runner's cached modules would shadow the extracted ones.
    for name in _MEMORY_BOOTSTRAP_MODULES:
        cached = sys.modules.get(name)
        if cached is not None:
            _reload_in_place(cached)
        else:
            importlib.import_module(name)
    return sys.modules["memory_backfill"]


def _installed_upgrade_module(root: Path):
    """Load the just-extracted upgrader without reusing the old runner module."""

    scripts = root / ".wavefoundry" / "framework" / "scripts"
    path = scripts / "upgrade_wavefoundry.py"
    if not path.is_file():
        raise RuntimeError(f"newly extracted upgrader is missing: {path}")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(
        "_wavefoundry_installed_upgrade_projection",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load newly extracted upgrader: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reload_cached_review_evidence() -> None:
    """Re-execute a pre-extraction ``review_evidence`` module in place.

    The installed upgrader loaded by :func:`_installed_upgrade_module` resolves
    its function-local ``from review_evidence import ...`` through
    ``sys.modules``.  A pre-upgrade runner that already imported the module
    would hand the new projection the OLD implementation; reloading in place
    re-executes the freshly extracted source while preserving module identity
    for any existing holders.
    """

    _refresh_record_layout_modules()
    cached = sys.modules.get("review_evidence")
    if cached is not None:
        importlib.reload(cached)


# Wave 1zeyo (1zesi): pure record-layout leaves that the reloaded review and
# memory modules import. A reloaded module must not run against the old
# runner's copies of these (a 1.27 ``RecordRoots`` has no ``archive``). The
# functions 1.27 code calls on them keep compatible signatures, so refreshing
# them in place is safe for the old runner too.
_RECORD_LAYOUT_MODULES = ("vocabulary_profile", "path_containment", "record_paths")


def _refresh_record_layout_modules() -> None:
    for name in _RECORD_LAYOUT_MODULES:
        cached = sys.modules.get(name)
        if cached is not None:
            _reload_in_place(cached)


def _refresh_record_layout_modules_at_extraction(root: Path) -> None:
    """Refresh a pre-upgrade runner's cached record-layout leaves after extraction.

    Wave 1zqe4 (1zrah): a 1.28.0 runner imports ``vocabulary_profile`` before
    extraction, then imports the new ``lifecycle_id`` in Phase 2c, whose
    module-level ``KIND_CHOICES`` reads ``CHANGE_KINDS`` from the cached old
    copy. ``post_extract`` is the first new-tree code the runner calls after
    extraction, so the leaves are refreshed here, leaf-first. A failed reload
    leaves a namespace that mixes old and new names (or, for
    ``vocabulary_profile``, the full namespace that failed its own import-time
    validation), so the first failure stops the upgrade and no later module is
    reloaded.
    """

    scripts = Path(root) / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    for name in _RECORD_LAYOUT_MODULES:
        cached = sys.modules.get(name)
        if cached is None:
            continue
        try:
            _reload_in_place(cached)
        except Exception as exc:
            reason = type(exc).__name__
            print(
                f"upgrade: refreshing the cached {name} module failed ({reason}); "
                "no later module was refreshed",
                flush=True,
            )
            raise RuntimeError(
                f"could not refresh the cached {name} module after extraction "
                f"({reason}); rerun the same upgrade command"
            ) from exc


def _fresh_installed_module(name: str):
    """Import a just-extracted scripts module, refreshing a pre-upgrade cache.

    Same cross-extraction seam as ``_reload_cached_review_evidence``: a
    pre-upgrade runner's cached module would shadow the extracted one, so a
    cached entry is re-executed in place (preserving module identity) and a
    cold entry imports normally from the installed scripts directory.
    """

    _refresh_record_layout_modules()
    cached = sys.modules.get(name)
    if cached is not None:
        importlib.reload(cached)
        return cached
    return importlib.import_module(name)


def _migrate_memory_naming(root: Path) -> None:
    """Rename legacy memory records to lifecycle naming (wave 1t9w7).

    Deterministic and idempotent (prefixes backdate from each record's own
    Created date), so re-running on an interrupted upgrade converges. The
    mapping is reported in the upgrade output; a repo with no memory records
    is a silent no-op.
    """

    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    memory_records = _fresh_installed_module("memory_records")
    _fresh_installed_module("lifecycle_id")
    result = memory_records.migrate_memory_ids_to_lifecycle_naming(root)
    if result.get("renamed"):
        print(
            f"memory-naming migration: renamed {result['renamed']} record(s) "
            f"to lifecycle ids ({result['skipped']} already current or "
            "unparsable):",
            flush=True,
        )
        for old_id, new_id in sorted(result["mapping"].items()):
            print(f"  {old_id} -> {new_id}", flush=True)
    if result.get("references_repaired"):
        print(
            f"memory-naming migration: repaired {result['references_repaired']} "
            "live reference(s) to migrated records.",
            flush=True,
        )
    for residue in result.get("residual_references", ()):
        print(
            "memory-naming migration WARNING: stale memory reference "
            f"`{residue['token']}` in {residue['path']} could not be resolved "
            "to a migrated record — review it manually.",
            flush=True,
        )


def _pristine_journal_template(wave_id: str, title: str, date: str) -> str:
    """The retired wave-journal scaffold, frozen as a migration oracle.

    Byte-identical to what ``wf_create_wave`` generated before wave 1t9w9
    retired journals. A journal file that EQUALS this rendering (with its own
    wave-id, title, and creation date substituted back in) provably carries
    zero operator content, so deleting it loses nothing.
    """

    return (
        f"# Journal - {title}\n\n"
        "Owner: Engineering\n"
        "Status: active\n"
        "Role: wave-coordinator\n"
        f"Last verified: {date}\n\n"
        "Actor: wave-coordinator\n"
        "Schema version: 1.0\n"
        f"Last distilled: {date}\n\n"
        f"wave-id: `{wave_id}`\n\n"
        "## Operating Identity\n\n"
        f"- **Role:** wave-coordinator for wave `{wave_id}`. **Responsibility:** "
        "coordinate the wave's admitted changes through prepare → implement → "
        "review → close per the lifecycle contract.\n\n"
        "## Salience Triggers\n\n"
        "- **critical** — operator directives that change wave scope, admitted "
        "changes, or close authorization\n"
        "- **high** — review-time findings that block close, dependency changes "
        "between admitted changes\n"
        "- **medium** — implementation-time observations about scope drift or "
        "unexpected blockers\n"
        "- **low** — routine coordination notes, status updates, lint pass/fail "
        "signals\n\n"
        "## Default Stance\n\n"
        "Maintain the wave's load-bearing invariants throughout implementation. "
        "Preserve the change-doc contracts admitted at prepare time; surface drift "
        "from operator immediately rather than silently absorbing scope.\n\n"
        "## Memory Responsibilities\n\n"
        "- Track per-change implementation state (gate-open/close pairs, AC "
        "completion, follow-up findings)\n"
        "- Record decisions made during implementation that affected scope, "
        "AC formulation, or test strategy\n\n"
        "## Active Signals\n\n"
        f"- Pending: wave `{wave_id}` opened {date}; populate as admitted "
        "changes move through implementation.\n\n"
        "## Distillation\n\n"
        "- Pending: distilled lessons emerge as the wave delivers; promote durable "
        "findings to `docs/agents/journals/README.md` at close.\n\n"
        "## Promotion Evidence\n\n"
        "- Pending: promotion candidates against `docs/agents/journals/README.md` "
        "emerge as the wave delivers and durable lessons are identified.\n\n"
        "## Retirement And Supersession\n\n"
        "- Pending: retirement happens at wave close per the closure contract in "
        "`docs/agents/journals/README.md`.\n\n"
        "## Governance\n\n"
        "- This journal follows the operating-memory contract in "
        "`docs/agents/journals/README.md`. Critical/high signals may be journaled "
        "during planning, implementation, review, handoff, reindex, or closure — "
        "not only at close. Distillation, promotion, and retirement happen at "
        "close.\n"
    )


_JOURNALS_REL = Path("docs", "agents", "journals")


def _journal_lstat(path: "Path | None"):
    """``os.lstat`` of ``path``, or ``None`` when it is absent or uninspectable."""
    if path is None:
        return None
    try:
        return os.lstat(path)
    except OSError:
        return None


def _journal_source_ok(st) -> bool:
    """Wave 1zv87 (1zuq5): a journal is touched only while it is a regular,
    singly linked file. A FIFO or device named ``*.md`` is never opened, and a
    hard-linked journal is neither copied (it is shared with another path) nor
    removed (removal would not remove the content)."""
    return st is not None and stat.S_ISREG(st.st_mode) and st.st_nlink == 1


def _same_journal_file(a, b) -> bool:
    """Whether two stats name the same file. Compared on POSIX only: Windows
    fills ``st_dev``/``st_ino`` differently across stat calls and Python
    versions, so there the regular-file and link-count checks stand alone."""
    if os.name == "nt":
        return True
    return os.path.samestat(a, b)


def _read_journal_bytes(path, expected, dir_fd: "int | None" = None) -> "bytes | None":
    """The bytes of a vetted journal, or ``None``. The open refuses a final
    link where the platform can, and the open file must still be the regular,
    singly linked file ``expected`` described (a swap between the ``lstat`` and
    the open is refused, not followed). With ``dir_fd`` (wave 1zxo0, 1zxns),
    ``path`` is a name opened relative to that directory handle."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(path, flags, dir_fd=dir_fd)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if not _journal_source_ok(st) or not _same_journal_file(st, expected):
            return None
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError:
        return None
    finally:
        os.close(fd)


def _write_journal_exclusive(destination, data: bytes, dir_fd: "int | None" = None) -> bool:
    """Wave 1zv87 (1zuq5): create ``destination`` and write ``data``, or return
    ``False``. ``O_CREAT | O_EXCL`` refuses any existing name, a dangling link
    included, so nothing is followed or replaced; ``O_NOFOLLOW`` is kept as
    defense in depth where it exists (not on Windows). Without ``dir_fd`` the
    path is absolute (the Windows branch: ``dir_fd`` is unsupported there).
    With ``dir_fd`` (wave 1zxo0, 1zxns), ``destination`` is a name created and,
    on a failed write, removed relative to the destination folder's handle."""
    flags = (
        os.O_CREAT
        | os.O_EXCL
        | os.O_WRONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(destination, flags, 0o666, dir_fd=dir_fd)
    except OSError:
        return False
    ok = False
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        ok = True
    except OSError:
        pass
    finally:
        os.close(fd)
    if not ok:
        # This run created the name exclusively; drop the partial copy.
        try:
            os.unlink(destination, dir_fd=dir_fd)
        except OSError:
            pass
    return ok


def _remove_journal_source(path_containment, root: Path, rel: Path, original) -> bool:
    """Wave 1zv87 (1zuq5): remove a journal only when a fresh containment check
    and ``lstat`` show it is still the regular, singly linked file first seen
    inside the contained journals folder; otherwise leave it."""
    current = path_containment.contained_path(root, rel, refuse_symlink_components=True)
    st = _journal_lstat(current)
    if current is None or not _journal_source_ok(st) or not _same_journal_file(st, original):
        return False
    try:
        os.unlink(current)
    except OSError:
        return False
    return True


def _journal_dir_fd_supported() -> bool:
    """Wave 1zxo0 (1zxns): whether the descriptor-bound journal migration can
    run. It needs ``open``, ``unlink`` and ``stat`` relative to a directory
    handle, ``scandir`` of a handle, and ``O_DIRECTORY``/``O_NOFOLLOW``. All
    are present on Linux, macOS and WSL2; ``os.supports_dir_fd`` is empty on
    Windows, which keeps the path branch."""
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and {os.open, os.unlink, os.stat} <= os.supports_dir_fd
        and os.scandir in os.supports_fd
    )


def _journal_walk_checkpoint(stage: str) -> None:
    """A no-op seam between a containment check and the descriptor work that
    follows it (wave 1zxo0, 1zxns). ``stage`` is ``"journals"`` (after the
    journals folder check, before its walk) or ``"destination"`` (after the
    destination folder check, before its walk and the write). Tests patch it
    to substitute a link at that point; the descriptor walk must refuse it."""
    return None


class _JournalWalkRefused(OSError):
    """A link met by the descriptor walk (wave 1zxo0, 1zxns). Carries no path."""


def _journal_open_dir(root: Path, parts) -> int:
    """A handle on ``root / parts`` opened one component at a time with
    ``O_RDONLY | O_DIRECTORY | O_NOFOLLOW`` relative to the previous handle, so
    no component below ``root`` is a link at the moment it is used.

    The pattern of ``runtime_lock._open_lock_carrier``, kept local because the
    upgrade extension runs pack-loaded: macOS reports a symlinked directory as
    ``ENOTDIR`` and Linux as ``ELOOP``, and either is confirmed to be a link by
    ``os.stat(..., follow_symlinks=False)`` before ``_JournalWalkRefused`` is
    raised. Any other failure raises its own ``OSError``. The caller closes
    the returned handle."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in parts:
            if name in ("", os.curdir, os.pardir) or os.sep in name or (
                os.altsep and os.altsep in name
            ):
                raise _JournalWalkRefused(errno.EINVAL, "unsafe path component")
            try:
                child = os.open(name, flags, dir_fd=fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    try:
                        is_link = stat.S_ISLNK(
                            os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
                        )
                    except OSError:
                        is_link = False
                    if is_link:
                        raise _JournalWalkRefused(errno.ELOOP, "link component") from exc
                raise
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _journal_dir_unchanged(root: Path, parts, fd: int) -> bool:
    """Whether a fresh no-follow walk to ``root / parts`` still reaches the
    directory ``fd`` holds, so a folder replaced after it was opened (by a link
    or another directory) is never written into or removed from."""
    try:
        current = _journal_open_dir(root, parts)
    except OSError:
        return False
    try:
        return os.path.samestat(os.fstat(current), os.fstat(fd))
    except OSError:
        return False
    finally:
        os.close(current)


def _remove_journal_source_at(root: Path, journals_fd: int, name: str, original) -> bool:
    """Descriptor-bound :func:`_remove_journal_source` (wave 1zxo0, 1zxns): the
    journals folder must still be the one ``journals_fd`` holds, and a re-stat
    relative to that handle must show the regular, singly linked file first
    seen; the name is then removed relative to the same handle."""
    if not _journal_dir_unchanged(root, _JOURNALS_REL.parts, journals_fd):
        return False
    try:
        st = os.stat(name, dir_fd=journals_fd, follow_symlinks=False)
    except OSError:
        return False
    if not _journal_source_ok(st) or not _same_journal_file(st, original):
        return False
    try:
        os.unlink(name, dir_fd=journals_fd)
    except OSError:
        return False
    return True


def _journal_exception_text(exc: BaseException, root: Path) -> str:
    """An exception for a journal migration warning, with no absolute path
    (wave 1zxo0, 1zxns): ``lifecycle_lock.path_free_exception_text`` from the
    extracted tree, or the class name alone when that import fails."""
    try:
        import lifecycle_lock  # noqa: PLC0415

        return lifecycle_lock.path_free_exception_text(exc, Path(root))
    except Exception:  # noqa: BLE001 - never fatal to an upgrade
        return type(exc).__name__


def _journal_rel(resolved_root: Path, path: Path) -> str:
    """``path`` relative to ``resolved_root`` as POSIX text; outside it, only
    ``<parent name>/<file name>`` (wave 1zxo0, 1zxns), never an absolute path."""
    try:
        return path.relative_to(resolved_root).as_posix()
    except ValueError:
        return f"{path.parent.name}/{path.name}"


def _journal_wave_dirs(root: Path) -> "tuple[dict[str, list[tuple[Path, bool]]] | None, re.Pattern | None, str | None]":
    """Wave 1zv87 (1zuq6): the wave folders by lower-cased id token over the
    waves and archive roots, each with whether it is archived, the profile's
    journal identity reader, and a skip reason. Both roots feed one map so an
    id found in both (or twice anywhere) is ambiguous; an archived folder is
    never a relocation target (the archive root is read-only, wave 1z8ts).

    The reader matches the active vocabulary profile's id key line, read at
    call time from the module the extracted tree provides; the caller falls
    back to the frozen scaffold's legacy key (journals predate profiles). Any
    discovery error (``RecordRootUnreadable``, ``RecordLayoutInvalid``, an
    import failure) returns ``None`` for the map, so relocation is skipped and
    the journals are listed."""
    profile_re = None
    try:
        import vocabulary_profile  # noqa: PLC0415
        import record_paths  # noqa: PLC0415

        profile_re = re.compile(rf"(?m)^{vocabulary_profile.ID_KEY_RE}: `(.+)`$")
        record_roots = record_paths.load_record_roots(root)
        folders = [(f, False) for f in record_paths.discover_wave_dirs(root, record_roots)]
        folders += [(f, True) for f in record_paths.discover_archive_dirs(root, record_roots)]
        by_token: dict[str, list[tuple[Path, bool]]] = {}
        for folder, archived in folders:
            by_token.setdefault(record_paths.wave_id_of(folder), []).append((folder, archived))
        return by_token, profile_re, None
    except Exception as exc:  # noqa: BLE001 - never fatal to an upgrade
        return None, profile_re, (
            f"record discovery unavailable: {_journal_exception_text(exc, root)}"
        )


def _journal_destination(path_containment, root: Path, name: str, wave_id: str,
                         by_token: "dict[str, list[tuple[Path, bool]]]") -> "tuple[Path | None, str | None]":
    """The destination for a wave journal, or ``(None, reason)`` to leave it
    in place (``reason`` is ``None`` when the plain left-in-place listing
    suffices).

    Wave 1zv87 (1zuq6): the folder is the one discovered for the id token; a
    token found in more than one folder is never guessed. The discovered
    folder is re-checked for link components and containment, and an archived
    folder is never written (the archive root is read-only)."""
    # A WAVE journal is identified by its filename equalling its wave id
    # (the generator's contract); a ROLE journal merely REFERENCES wave ids
    # in its content and must be left in place (live-caught
    # on this repository's own migration: guru.md carried a wave-id
    # reference and was mis-relocated before this filename check).
    if name != f"{wave_id.replace(' ', '-')}.md":
        return None, None
    folders = by_token.get(wave_id.split(" ", 1)[0].lower(), [])
    if len(folders) != 1:
        return None, None
    found, archived = folders[0]
    if archived:
        return None, "wave is archived (read-only archive root)"
    folder = path_containment.contained_path(root, found, refuse_symlink_components=True)
    folder_st = _journal_lstat(folder)
    if folder is None or folder_st is None or not stat.S_ISDIR(folder_st.st_mode):
        return None, None
    # Wave 1t76w: the relocated artifact carries the lifecycle type suffix
    # like every other typed artifact in a wave folder (`<prefix>-jrnl
    # <slug>.md`, space form).
    prefix, _, slug = wave_id.partition(" ")
    destination_name = f"{prefix}-jrnl {slug}.md" if slug else f"{prefix}-jrnl.md"
    if "/" in destination_name or "\\" in destination_name:
        return None, None
    return folder / destination_name, None


class JournalDeclarationError(RuntimeError):
    """An invalid journal migration declaration (wave 1zyb3, change 1zxnv):
    refuses the upgrade before any journal is touched."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("invalid journal migration declaration: " + "; ".join(self.problems))


# Private module names, so a stale ``mcp_tool_extensions`` (or helper) in
# ``sys.modules`` never answers and nothing loaded here is left registered.
_JOURNAL_DECLARATION_MODULE = "_wf_upgrade_journal_declaration"
_JOURNAL_HOOK_MODULE_PREFIX = "_wf_upgrade_journal_hook_"
# Each free-text placeholder matches 1 to _JOURNAL_PLACEHOLDER_MAX characters
# of one line. A real wave id or title is far shorter; the bound keeps a
# template with two free-text placeholders on one line from backtracking
# quadratically over a very long journal line (wave 1zyb3 delivery repair).
_JOURNAL_PLACEHOLDER_MAX = 512
_JOURNAL_PLACEHOLDER_PATTERNS = {
    "wave_id": rf"[^\n]{{1,{_JOURNAL_PLACEHOLDER_MAX}}}",
    "title": rf"[^\n]{{1,{_JOURNAL_PLACEHOLDER_MAX}}}",
    "date": r"\d{4}-\d{2}-\d{2}",
}
_JOURNAL_PLACEHOLDER_MAX_LENGTHS = {
    "wave_id": _JOURNAL_PLACEHOLDER_MAX,
    "title": _JOURNAL_PLACEHOLDER_MAX,
    "date": 10,
}
_JOURNAL_PLACEHOLDER_SPLIT = re.compile(r"\{\{(wave_id|title|date)\}\}")
_UNSET = object()


def _journal_scripts_dir(root: Path) -> Path:
    return Path(root) / ".wavefoundry" / "framework" / "scripts"


def _exec_module_from_file(name: str, path: Path):
    """Execute the ``.py`` file at ``path`` as a fresh module called ``name``,
    never registered in ``sys.modules``."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_journal_hook(scripts: Path, hook: str):
    """The declared ``module:function`` hook, loaded by file path from
    ``scripts``: the module must be a ``.py`` file listed directly there
    (exact name, as the server's extension loader requires) whose resolved
    parent is that directory and whose resolved name is that file name.
    Returns the callable; raises :class:`JournalDeclarationError` with
    path-free problems otherwise."""
    import inspect  # noqa: PLC0415

    module_name, function_name = hook.split(":")
    label = f"journal pre-migration hook {hook!r}"
    file_name = f"{module_name}.py"
    try:
        listed = os.listdir(scripts)
    except OSError as exc:
        raise JournalDeclarationError(
            [f"{label}: the framework scripts directory cannot be listed ({type(exc).__name__})"]
        ) from None
    path = scripts / file_name
    try:
        resolved_scripts = scripts.resolve()
        resolved = path.resolve()
        regular = stat.S_ISREG(os.stat(resolved).st_mode)
    except OSError:
        regular = False
        resolved = resolved_scripts = None
    # The resolved file must also carry the module's own name, as the
    # server's extension loader requires ``source_path.stem == module_name``:
    # a same-directory link to a sibling script is refused.
    if (file_name not in listed or not regular or resolved.parent != resolved_scripts
            or resolved.name != file_name):
        raise JournalDeclarationError(
            [f"{label}: module {module_name!r} has no {file_name} file directly in the framework scripts directory"]
        )
    # A helper may import helpers declared before it, as on the server.
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        module = _exec_module_from_file(_JOURNAL_HOOK_MODULE_PREFIX + module_name, resolved)
    except Exception as exc:  # noqa: BLE001 - refused, never raised raw
        raise JournalDeclarationError(
            [f"{label}: module {module_name!r} could not be imported ({type(exc).__name__})"]
        ) from None
    function = getattr(module, function_name, None)
    if function is None:
        raise JournalDeclarationError([f"{label}: module {module_name!r} defines no {function_name!r}"])
    if not callable(function):
        raise JournalDeclarationError([f"{label}: {function_name!r} is not callable"])
    try:
        inspect.signature(function).bind(Path(scripts))
    except (TypeError, ValueError):
        raise JournalDeclarationError(
            [f"{label}: {function_name!r} cannot be called with one positional argument (the repository root)"]
        ) from None
    return function


def _load_journal_declaration(root, *, load_hook: bool = True) -> "tuple[tuple[str, ...], str, object]":
    """The journal migration declaration from the EXTRACTED tree (wave 1zyb3,
    change 1zxnv): ``(templates, hook_name, hook_callable_or_None)``.

    ``mcp_tool_extensions.py`` is loaded by file path under a private module
    name. A missing file, or a module that predates the constants, reads as
    the empty declaration. An import failure, an invalid declaration or (with
    ``load_hook``) a hook that cannot be loaded raises :class:`JournalDeclarationError`, whose
    problems carry no path and no exception text."""
    scripts = _journal_scripts_dir(root)
    path = scripts / "mcp_tool_extensions.py"
    if not path.is_file():
        return (), "", None
    try:
        module = _exec_module_from_file(_JOURNAL_DECLARATION_MODULE, path)
    except Exception as exc:  # noqa: BLE001 - refused, never raised raw
        raise JournalDeclarationError(
            [f"mcp_tool_extensions could not be imported ({type(exc).__name__})"]
        ) from None
    templates = getattr(module, "EXTENSION_JOURNAL_TEMPLATES", ())
    hook = getattr(module, "EXTENSION_JOURNAL_PRE_MIGRATION_HOOK", "")
    check = getattr(module, "journal_declaration_problems", None)
    if callable(check):
        problems = list(check())
    elif templates or hook:
        problems = ["mcp_tool_extensions declares journal migration entries but has no journal_declaration_problems"]
    else:
        problems = []
    if problems:
        raise JournalDeclarationError(problems)
    function = _load_journal_hook(scripts, hook) if hook and load_hook else None
    return tuple(templates), hook, function


def _compile_journal_template(template: str) -> "re.Pattern[str]":
    """A declared template as one full-match pattern: literal text escaped,
    the first occurrence of each placeholder a named one-line group and every
    later one a backreference to it. No nested quantifiers."""
    parts = _JOURNAL_PLACEHOLDER_SPLIT.split(template)
    pattern: list[str] = []
    seen: set[str] = set()
    for index, part in enumerate(parts):
        if index % 2 == 0:
            pattern.append(re.escape(part))
        elif part in seen:
            pattern.append(f"(?P={part})")
        else:
            seen.add(part)
            pattern.append(f"(?P<{part}>{_JOURNAL_PLACEHOLDER_PATTERNS[part]})")
    return re.compile("".join(pattern))


def _journal_template_max_length(template: str) -> int:
    """The longest text :func:`_compile_journal_template`'s pattern can match:
    the literal text plus each placeholder occurrence at its bound. A journal
    longer than this is never matched against the template at all."""
    parts = _JOURNAL_PLACEHOLDER_SPLIT.split(template)
    return sum(
        len(part) if index % 2 == 0 else _JOURNAL_PLACEHOLDER_MAX_LENGTHS[part]
        for index, part in enumerate(parts)
    )


def migrate_journals(root, *, apply: bool = False, templates=_UNSET) -> dict:
    """Mechanically migrate the retired journal directory (wave 1t9w9).

    Fail-safe by construction: (a) a journal that provably equals the pristine
    rendered scaffold (its own wave-id/title/date substituted into the frozen
    template, so zero information loss) is deleted; (b) a content-bearing WAVE
    journal is moved, byte-exact, into its discovered wave folder; (c)
    everything else (role journals, template drift, unknown shapes, an
    ambiguous, missing or archived wave folder, a path the migration will not
    follow) is
    left in place and listed for the operator-invoked Migrate journals prompt.
    Idempotent: deleted and moved files are gone from the source on rerun.

    Wave 1zv87 (1zuq6): public so an operator or distribution can preview the
    migration. Returns ``{"deleted": [...], "moved": [{"source", "destination"}],
    "left": [...], "warnings": [...]}`` with repository-relative POSIX paths;
    with ``apply`` False nothing on disk changes.

    Wave 1zv87 (1zuq5): the repository decides whether this runs, so no file
    operation follows a link. The journals folder, each journal and each wave
    folder resolve through ``path_containment.contained_path(...,
    refuse_symlink_components=True)``; a journal must be a regular, singly
    linked file; the destination is created only by an exclusive, no-follow
    open; and the source is re-checked right before it is removed. A refused
    journals folder ends the migration with nothing touched.

    Wave 1zxo0 (1zxns): where :func:`_journal_dir_fd_supported` holds (Linux,
    macOS, WSL2) the journals folder and each destination folder are opened by
    a no-follow walk from the repository root, and every enumeration, read,
    create, re-stat and removal is relative to those handles, so a directory
    component swapped after the checks above is refused rather than followed;
    a refusal leaves the journal in place under ``left``. Windows keeps the
    path branch, whose check-to-use window is a documented limit. Warnings and
    report entries carry no absolute path.

    Wave 1zyb3 (1zxnv): a journal that fully matches a declared template
    (``EXTENSION_JOURNAL_TEMPLATES``) is deleted too. ``templates`` defaults to
    the declaration loaded from the extracted tree, so a preview sees the same
    oracle; an invalid declaration raises :class:`JournalDeclarationError`.
    The pre-migration hook is never called here.
    """

    root = Path(root)
    if templates is _UNSET:
        templates = _load_journal_declaration(root, load_hook=False)[0]
    patterns = tuple(
        (_compile_journal_template(template), _journal_template_max_length(template))
        for template in templates
    )
    report: dict = {"deleted": [], "moved": [], "left": [], "warnings": []}
    try:
        os.lstat(root / _JOURNALS_REL)
    except OSError:
        return report
    # Wave 1y0gz: the record layout comes from the resolver in the EXTRACTED
    # tree, guarded like the other sibling imports in this module.
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    journals_rel = _JOURNALS_REL.as_posix()
    try:
        import path_containment  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - never fatal to an upgrade
        report["left"].append(journals_rel)
        report["warnings"].append(
            "journal migration: skipped (path containment unavailable: "
            f"{_journal_exception_text(exc, root)})"
        )
        return report
    journals_dir = path_containment.contained_path(
        root, _JOURNALS_REL, refuse_symlink_components=True
    )
    refused_warning = (
        f"journal migration: skipped ({journals_rel} is a link or leaves the repository)"
    )
    if journals_dir is None:
        report["left"].append(journals_rel)
        report["warnings"].append(refused_warning)
        return report
    journals_st = _journal_lstat(journals_dir)
    if journals_st is None or not stat.S_ISDIR(journals_st.st_mode):
        return report
    resolved_root = root.resolve()

    def _rel(path: Path) -> str:
        return _journal_rel(resolved_root, path)

    # Wave 1zxo0 (1zxns): on POSIX every journal operation is bound to a
    # directory handle from a no-follow walk; Windows keeps the path branch.
    journals_fd = None
    if _journal_dir_fd_supported():
        _journal_walk_checkpoint("journals")
        try:
            journals_fd = _journal_open_dir(root, _JOURNALS_REL.parts)
        except OSError:
            report["left"].append(journals_rel)
            report["warnings"].append(refused_warning)
            return report
    try:
        _migrate_journal_entries(
            root, resolved_root, journals_dir, journals_fd, path_containment,
            apply, report, _rel, patterns,
        )
    finally:
        if journals_fd is not None:
            os.close(journals_fd)
    return report


def _move_journal_at(root: Path, resolved_root: Path, journals_fd: int, name: str,
                     source_st, destination: Path, data: bytes) -> bool:
    """Write a vetted journal into its destination through directory handles
    (wave 1zxo0, 1zxns): the destination folder is opened by a no-follow walk
    from the resolved root, the journals folder must still be the one
    ``journals_fd`` holds, and the source must still be the file first seen,
    all before the exclusive create relative to the destination handle."""
    _journal_walk_checkpoint("destination")
    try:
        parts = destination.parent.relative_to(resolved_root).parts
        dest_fd = _journal_open_dir(resolved_root, parts)
    except (OSError, ValueError):
        return False
    try:
        if not _journal_dir_unchanged(root, _JOURNALS_REL.parts, journals_fd):
            return False
        try:
            st = os.stat(name, dir_fd=journals_fd, follow_symlinks=False)
        except OSError:
            return False
        if not _journal_source_ok(st) or not _same_journal_file(st, source_st):
            return False
        return _write_journal_exclusive(destination.name, data, dir_fd=dest_fd)
    finally:
        os.close(dest_fd)


def _migrate_journal_entries(root: Path, resolved_root: Path, journals_dir: Path,
                             journals_fd: "int | None", path_containment, apply: bool,
                             report: dict, _rel, patterns=()) -> None:
    """The per-journal loop of :func:`migrate_journals`. With ``journals_fd``
    (wave 1zxo0, 1zxns) journals are enumerated, inspected, read and removed
    relative to that handle, so no source path is reopened by name; without it
    the path branch (Windows) runs as before."""
    journals_rel = _JOURNALS_REL.as_posix()
    by_token, profile_re, skipped = _journal_wave_dirs(root)
    if skipped is not None:
        report["warnings"].append(
            f"journal migration: wave-journal relocation skipped ({skipped})"
        )
    if journals_fd is not None:
        try:
            with os.scandir(journals_fd) as entries:
                names = sorted(entry.name for entry in entries if entry.name.endswith(".md"))
        except OSError:
            report["left"].append(journals_rel)
            return
    else:
        names = [path.name for path in sorted(journals_dir.glob("*.md"))]

    def _remove(name: str, original) -> bool:
        if journals_fd is not None:
            return _remove_journal_source_at(root, journals_fd, name, original)
        return _remove_journal_source(path_containment, root, _JOURNALS_REL / name, original)

    for name in names:
        if name == "README.md":
            continue
        source_rel = f"{journals_rel}/{name}"
        if journals_fd is not None:
            try:
                source_st = os.stat(name, dir_fd=journals_fd, follow_symlinks=False)
            except OSError:
                source_st = None
            if not _journal_source_ok(source_st):
                report["left"].append(source_rel)
                continue
            data = _read_journal_bytes(name, source_st, dir_fd=journals_fd)
        else:
            source = path_containment.contained_path(
                root, _JOURNALS_REL / name, refuse_symlink_components=True
            )
            source_st = _journal_lstat(source)
            if source is None or not _journal_source_ok(source_st):
                report["left"].append(source_rel)
                continue
            data = _read_journal_bytes(source, source_st)
        try:
            text = data.decode("utf-8") if data is not None else None
        except UnicodeDecodeError:
            text = None
        if text is None:
            report["left"].append(source_rel)
            continue
        # A CRLF checkout of a scaffold is still the scaffold; the move below
        # writes the original bytes, so newlines are preserved.
        text = text.replace("\r\n", "\n")
        wave_m = re.search(r"^wave-id: `(.+)`$", text, re.MULTILINE)
        title_m = re.search(r"^# Journal - (.+)$", text, re.MULTILINE)
        date_m = re.search(r"^Last verified: (\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
        pristine = bool(wave_m and title_m and date_m) and text == _pristine_journal_template(
            wave_m.group(1), title_m.group(1), date_m.group(1)
        )
        # Wave 1zyb3 (1zxnv): then each declared template, as one full match.
        if pristine or any(
            len(text) <= max_length and pattern.fullmatch(text)
            for pattern, max_length in patterns
        ):
            if not apply or _remove(name, source_st):
                report["deleted"].append(source_rel)
            else:
                report["left"].append(source_rel)
            continue
        # Relocation needs only the wave identity: older journals may lack
        # template fields and must still move, never delete. The profile's id
        # key comes first; the scaffold's legacy key (``wave_m``) is the
        # fallback, since journals predate vocabulary profiles.
        id_m = (profile_re.search(text) if profile_re is not None else None) or wave_m
        destination = None
        if id_m and by_token is not None:
            destination, reason = _journal_destination(
                path_containment, root, name, id_m.group(1), by_token
            )
            if reason is not None:
                report["warnings"].append(
                    f"journal migration: left {name} in place: {reason}"
                )
        if destination is None:
            report["left"].append(source_rel)
            continue
        entry = {"source": source_rel, "destination": _rel(destination)}
        if not apply:
            if _journal_lstat(destination) is None:
                report["moved"].append(entry)
            else:
                report["left"].append(source_rel)
            continue
        if journals_fd is not None:
            written = _move_journal_at(
                root, resolved_root, journals_fd, name, source_st, destination, data
            )
        else:
            written = _write_journal_exclusive(destination, data)
        if not written:
            report["left"].append(source_rel)
            continue
        if _remove(name, source_st):
            report["moved"].append(entry)
        else:
            report["left"].append(source_rel)


def _migrate_journals(root: Path, templates=_UNSET) -> None:
    """The applying caller, run by :func:`pre_docs_gate` before the docs gate:
    :func:`migrate_journals` with ``apply=True`` plus its printed summary (wave
    1zv87, 1zuq6). ``templates`` is the declaration ``pre_docs_gate`` already
    loaded (wave 1zyb3, 1zxnv); by default it is loaded here."""

    report = migrate_journals(root, apply=True, templates=templates)
    for warning in report["warnings"]:
        print(warning, flush=True)
    deleted, moved = report["deleted"], report["moved"]
    if deleted or moved:
        print(
            f"journal migration: deleted {len(deleted)} pristine scaffold(s); "
            f"moved {len(moved)} wave journal(s) into their wave directories.",
            flush=True,
        )
        for entry in moved:
            print(f"  {Path(entry['source']).name} -> {entry['destination']}", flush=True)
    for rel in report["left"]:
        print(
            f"journal migration: left {Path(rel).name} in place (role journal, "
            "template drift, missing or ambiguous wave directory, or a path the "
            "migration will not follow); run the Migrate journals prompt to "
            "finish by hand.",
            flush=True,
        )


def _run_journal_pre_migration_hook(root: Path, hook_name: str, hook) -> bool:
    """Call the declared pre-migration hook once with the repository root
    (wave 1zyb3, 1zxnv). True when the migration may run: no hook, or the
    hook returned. A hook that raises skips the migration for this upgrade
    with one warning naming the hook and the exception class, never the
    exception text, which may carry an absolute path."""
    if hook is None:
        return True
    try:
        hook(Path(root))
    except Exception as exc:  # noqa: BLE001 - never fatal to an upgrade
        print(
            f"journal migration WARNING: skipped; the pre-migration hook {hook_name} "
            f"raised {type(exc).__name__}. Journals were left in place; a later "
            "upgrade or the Migrate journals prompt finishes the work.",
            flush=True,
        )
        return False
    return True


def repair_declaring_scaffold(root) -> list[str]:
    """Fence a scaffold's example block so it stops declaring review targets.

    1.15.6 ships a docs-lint ERROR for a scaffold that declares review
    targets, because a declaring template hands every change doc created from
    it a roster its author never chose. (1.15.5 is the release the field
    report came from, not the release carrying the rule.) That rule is class-a: the docs gate
    subprocesses the freshly extracted ``docs_lint.py``, so it fires on the
    upgrade that installs it. A repository whose template was already
    contaminated would therefore halt at ``failed_phase == "docs_gate"`` —
    exactly the population the rule exists to protect.

    This repair runs from the pack-loaded extension immediately before that
    gate, so it is class-a too and clears the contamination on the same run.
    It is safe in a scaffold and only in a scaffold: every declaration in a
    template is by definition an example, so fencing cannot destroy a real
    target. Authored change docs are never touched.

    Returns the repaired paths so the caller can report what it changed;
    reporting from the repair is the only option, because the reconciliation
    scan runs after the gate and is skipped entirely when the gate fails.
    """

    from pathlib import Path as _Path

    root = _Path(root)
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        # Resolve against the EXTRACTED tree: a pre-upgrade runner's cached
        # module would be the old parser, which is the version that did not
        # know the marker block at all.
        _refresh_record_layout_modules()
        cached = sys.modules.get("review_policy")
        if cached is not None:
            importlib.reload(cached)
            review_policy = cached
        else:
            import review_policy  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 — never fatal to an upgrade
        print(f"scaffold repair: skipped (parser unavailable: {exc})", flush=True)
        return []

    repaired: list[str] = []
    # The SAME constant the docs-lint rule blocks on. Two independent literals
    # would let the blocking set grow past the repairable set, stranding a
    # repository at the docs gate with nothing the upgrade can fix.
    # getattr, not attribute access: the loop header sits OUTSIDE the per-file
    # guard below, so a parser without the constant would raise straight past
    # every "never fatal" promise into _run_hook's sys.exit(3) and abort the
    # upgrade. No shipped launcher reaches that, but the cost of not finding
    # out the hard way is one word.
    for rel in getattr(review_policy, "SCAFFOLD_DOCS", ()):
        path = root / rel
        # Every step below is guarded: a repair that cannot complete must
        # REPORT, never abort the upgrade. An unguarded write on a read-only
        # template escaped into the hook dispatcher's `sys.exit(3)`, which
        # reports itself as a pre-flight failure for a phase-3 problem.
        try:
            # ``os.stat`` rather than ``is_file()``, which reads any
            # ``OSError`` as absent from Python 3.14 (wave 1zrak) and would
            # skip a template it cannot inspect instead of reporting it.
            try:
                if not stat.S_ISREG(os.stat(path).st_mode):
                    continue
            except (FileNotFoundError, NotADirectoryError):
                continue
            # newline="" on BOTH sides. Reading without it translates a CRLF
            # checkout to LF in memory, so writing it back rewrites every line
            # in the operator's repo even though the repair touched one block.
            with path.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read()
            if not review_policy.serialization_point_paths(text):
                continue
            fenced = _fence_serialization_examples(
                text, review_policy.serialization_point_paths, review_policy
            )
            if fenced is None or review_policy.serialization_point_paths(fenced):
                print(
                    f"scaffold repair: {rel} declares review targets and could "
                    "not be repaired automatically — fence its example block by "
                    "hand, then re-run with --resume-after-gate.",
                    flush=True,
                )
                continue
            # Write to a sibling temp file and rename. `open("w")` truncates
            # BEFORE writing, so an I/O error between those two points would
            # leave the operator's template truncated while the handler below
            # reported "could not be repaired" — false, and destructively so.
            # This is the one place the change writes to an operator's file,
            # and the whole fencing-over-re-rendering decision rests on
            # preserving their prose.
            #
            # newline="" preserves the file's own line endings. Without it a
            # CRLF checkout comes back all-LF (and the reverse on Windows),
            # producing a whole-file spurious diff in the operator's repo.
            # A rename only needs write permission on the DIRECTORY, so an
            # atomic write would silently override a template the operator
            # deliberately marked read-only. Refuse and report instead: it is
            # their file, and they still get the message naming it and the fix.
            if not os.access(path, os.W_OK):
                raise PermissionError(f"{path} is not writable")
            staged = path.with_name(path.name + ".wf-scaffold-repair")
            try:
                with staged.open("w", encoding="utf-8", newline="") as handle:
                    handle.write(fenced)
                # The staged file gets the process umask, not the template's
                # mode; carry the original across so a group-writable checkout
                # stays group-writable.
                os.chmod(staged, path.stat().st_mode & 0o7777)
                os.replace(staged, path)
            finally:
                if staged.exists():
                    staged.unlink()
        except Exception as exc:  # noqa: BLE001 — never fatal to an upgrade
            print(
                f"scaffold repair: {rel} could not be repaired ({exc}) — fence "
                "its example block by hand, then re-run with "
                "--resume-after-gate.",
                flush=True,
            )
            continue
        repaired.append(rel)
        print(f"scaffold repair: fenced the example block in {rel}.", flush=True)
    return repaired


def _fence_serialization_examples(text, declares, parser=None):
    """Fence the declaring example(s) in a scaffold's Serialization Points.

    Handles BOTH declaration tiers, because both are shapes the framework
    itself teaches. Tier 2 is the ``**Review targets (repo-relative paths):**``
    block. Tier 1 is a bullet whose content is entirely repo-relative paths,
    which is the literal example seed 040 hands a bootstrap agent, so a
    freshly installed template can carry it and a marker-only repair would
    leave that repository halted at the docs gate with nothing to do but edit
    by hand.

    Only bullet runs that actually DECLARE are fenced, decided by the shipped
    parser rather than by shape, so instructional prose bullets are left
    alone. Returns ``None`` when nothing is recognized, so the caller reports
    rather than mangling an unfamiliar template.
    """

    if parser is None:
        import review_policy as parser  # noqa: PLC0415

    lines = text.split("\n")

    # EVERY predicate below comes from the parser, never from a local
    # restatement. Requirement 2 forbids re-implementing extraction because a
    # second implementation drifts; the same argument holds for the fence
    # scanner and the boundary tests, and all of them had drifted. A local
    # "## " section-end test missed the tab form the parser accepts, so the
    # scan ran past a real boundary and spliced fences into the NEXT section
    # while the post-verify stayed silent (fencing a non-declaring section
    # does not change what the parser extracts). A local bullet test missed
    # the tab separator, so a template that declares to the parser was
    # invisible here and halted the upgrade.
    fenced = parser._fenced_line_flags(lines)

    section_start = None
    for index, line in enumerate(lines):
        if not fenced[index] and parser._SERIALIZATION_POINTS_HEADING_RE.match(line):
            section_start = index + 1
            break
    if section_start is None:
        return None
    section_end = len(lines)
    for index in range(section_start, len(lines)):
        # A heading inside a fenced example is sample text, not the next
        # section; treating it as one truncates the scan and leaves a real
        # declaring run beyond the false boundary unfenced.
        if not fenced[index] and parser._SECTION_HEADING_RE.match(lines[index]):
            section_end = index
            break

    def _bullet(index: int) -> bool:
        # An already-fenced bullet is an example that is ALREADY safe; it
        # declares nothing and must not be re-fenced.
        return not fenced[index] and bool(parser._BULLET_RE.match(lines[index]))

    # Collect the runs to fence, then splice from the bottom up so earlier
    # indices stay valid.
    runs: list[tuple[int, int]] = []
    index = section_start
    while index < section_end:
        marker = not fenced[index] and bool(
            parser._REVIEW_TARGETS_MARKER_RE.match(lines[index])
        )
        if not marker and not _bullet(index):
            index += 1
            continue
        start = index
        end = index + 1
        saw_bullet = _bullet(index)
        while end < section_end:
            if not lines[end].strip():
                # A blank line ends a plain bullet run, so an instructional
                # bullet group separated from the example by a blank is a
                # DIFFERENT run and is judged on its own. Only the marker
                # form spans its blank, because the marker and the bullets
                # beneath it are one construct.
                if marker and not saw_bullet:
                    end += 1
                    continue
                break
            if _bullet(end):
                saw_bullet = True
                end += 1
                continue
            break
        while end > start and not lines[end - 1].strip():
            end -= 1
        if saw_bullet and declares("## Serialization Points\n\n" + "\n".join(lines[start:end])):
            runs.append((start, end))
        index = max(end, index + 1)

    if not runs:
        return None
    # Match the file's own line ending. The split is on "\n", so a CRLF file's
    # lines carry a trailing "\r"; an inserted bare fence would leave the file
    # with mixed endings.
    fence = "```\r" if "\r\n" in text else "```"
    for start, end in reversed(runs):
        lines[start:end] = [fence] + lines[start:end] + [fence]
    repaired = "\n".join(lines)
    # A run reaching EOF puts the closing fence on the last line, dropping the
    # file's trailing newline. Restore it so the repair is insertion-only.
    if text.endswith("\n") and not repaired.endswith("\n"):
        repaired += "\r\n" if "\r\n" in text else "\n"
    return repaired


def pre_docs_gate(ctx):
    """Run the retired-sidecar cutover before the docs gate validates the tree.

    A pre-upgrade runner has already loaded its old ``upgrade_wavefoundry``
    module, but it executes this extension from the new archive.  Loading the
    installed module by file path avoids the old ``sys.modules`` entry and
    gives that runner the new one-way sidecar cleanup before docs-lint runs.
    """

    # 1.15.6's scaffold rule is class-a, so a repository whose template already
    # declares would halt at the docs gate on the very upgrade that installs
    # the rule. Repair first, from this pack-loaded module, so it clears on the
    # same run rather than one upgrade later.
    repair_declaring_scaffold(ctx.root)

    # A graph extraction change may advance the framework-owned version while
    # leaving an exact project-local reliability claim behind. The incoming
    # extension captured a code/doc match before extraction, so this can repair
    # the installing upgrade without overwriting a customized or ambiguous doc.
    _reconcile_graph_builder_doc_claim(ctx)

    # Wave 1t9w7 — runs before docs-lint so renamed memory records are what
    # the gate validates. Version-gated as a cheap skip; the migration itself
    # is idempotent either way. Non-string from_version falls to the module's
    # unknown-means-old safe default.
    from_version = ctx.from_version if isinstance(ctx.from_version, str) else ""
    if _from_version_predates(from_version, "1.15.0"):
        # Wave 1zyb3 (1zxnv): the distribution's journal declaration, loaded
        # by path from the extracted tree only when the migration runs, and
        # FIRST, so an invalid one (or a hook that cannot be loaded) raises
        # before the memory-naming or journal migration changes anything. The
        # loaded templates are always passed on, so the declaration module is
        # executed once; the hook runs right before the journal migration, and
        # a hook that raises skips it.
        templates, hook_name, hook = _load_journal_declaration(ctx.root)
        _migrate_memory_naming(ctx.root)
        if _run_journal_pre_migration_hook(ctx.root, hook_name, hook):
            _migrate_journals(ctx.root, templates)

    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    if "review_sidecar_cleanup" in lock:
        return
    _reload_cached_review_evidence()
    installed = _installed_upgrade_module(ctx.root)
    # Thread the pre-upgrade installed version into the cutover so the
    # installed cleanup can scope restart_required; a non-string
    # ctx.from_version falls to the cleanup's fail-safe pre-1.15 default.
    counts = installed.phase_review_evidence_sidecar_cleanup(
        ctx.root,
        from_version=from_version or None,
    )
    _update_upgrade_state(ctx.root, review_sidecar_cleanup=counts)


def post_docs_gate(ctx):
    """Bootstrap the memory pause under both old and new upgrade runners."""

    backfill = _installed_memory_backfill(ctx.root)
    run_id = backfill.ensure_run(ctx.root, "upgrade")
    summary = backfill.sync_inventory(ctx.root, run_id)
    _update_upgrade_state(
        ctx.root,
        memory_backfill_run_id=run_id,
        memory_backfill_state=summary["state"],
        memory_backfill_pending=(
            summary["remaining_waves"]
            + summary["candidates_pending"]
            + summary["failures"]
        ),
        memory_backfill_last_failure=summary["last_failure"],
    )
    # Protocol-2 runners own the canonical bounded extraction attempt after
    # this hook returns.  A protocol-1 runner cannot safely continue through
    # the new memory state machine, so it retains the compatibility pause.
    if int(getattr(ctx, "runner_protocol", 1) or 1) >= 2:
        return
    if summary["state"] == "awaiting_validation":
        _pause_for_memory_action(
            ctx,
            state="awaiting_memory_validation",
            run_id=run_id,
            message=(
                "Historical memory requires bounded extraction and agent validation "
                "before index publication. Reload MCP, run memory_backfill and "
                "memory_validate, then call wf_upgrade(phase='resume_after_memory')."
            ),
        )


def _bridge_index_publisher_grant(root, lock) -> None:
    """Establish the value-bound Phase 4 publisher grant (wave 1u44n).

    The parent runner executing Phase 4 may still be OLD code that spawns the
    ``setup_index.py`` children with no authorized-publisher status, so the
    installed ``index_state_store.begin_build_epoch`` refuses them on
    checkpoint presence and the build epoch is left incomplete. This bridge
    runs NEW pack code inside that old parent, immediately before the Phase 4
    dispatch: it records a random token as ``publisher_grant`` in the upgrade
    checkpoint and exports the matching
    ``WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN`` into the parent environment the
    children inherit. The installed store admits a publisher only when the two
    MATCH, so a copy leaked into the old parent's detached background code
    child dies with this checkpoint (a later upgrade mints a fresh token).
    Idempotent, and a no-op when the grant is already in place.
    """
    if not lock:
        return
    token = str(lock.get("publisher_grant") or "").strip()
    if not token:
        import uuid

        token = uuid.uuid4().hex
        _update_upgrade_state(root, publisher_grant=token)
    if os.environ.get("WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN") != token:
        os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"] = token


def _arm_memory_action_required(ctx, *, state: str, run_id: str) -> None:
    """Persist an intentional memory pause and bridge only legacy finalizers.

    The incoming extension is the sole new code running in pghn/pgi7 while
    they own the outer ``SystemExit`` handler.  Their dashboards also retain a
    dead-PID lock only when ``failed_phase`` is truthy, so that field is a
    short-lived compatibility lease, not a public failure claim.
    """
    token = uuid.uuid4().hex
    _update_upgrade_state(
        ctx.root,
        current_phase=state,
        action_required={
            "kind": "historical_memory",
            "state": state,
            "resume_phase": "resume_after_memory",
            "run_id": run_id,
            "token": token,
        },
        failed_phase="awaiting_memory_validation",
        failed_at=None,
    )
    parent = sys.modules.get(type(ctx).__module__)
    legacy_build = str(getattr(ctx, "from_version", "") or "")
    if legacy_build not in {"1.15.0+pghn", "1.15.0+pgi7"}:
        return
    if parent is None or getattr(parent, "_wf_memory_action_bridge", False):
        return
    original = getattr(parent, "_finalize_failed_upgrade", None)
    if not callable(original):
        return

    def _legacy_finalizer(root, tree_mutated, current_phase):
        # Restore before inspecting state: any mismatch must use the original
        # finalizer and no later failure may inherit this one-shot exception.
        parent._finalize_failed_upgrade = original
        parent._wf_memory_action_bridge = False
        exc = sys.exc_info()[1]
        lock = _read_json_object(root / ".wavefoundry" / "upgrade-in-progress.json")
        action = lock.get("action_required") if isinstance(lock, dict) else None
        if (
            tree_mutated
            and current_phase in {"index_update", "awaiting_memory_validation"}
            and isinstance(exc, SystemExit)
            and exc.code == 4
            and root == ctx.root
            and isinstance(action, dict)
            and action.get("kind") == "historical_memory"
            and action.get("token") == token
            and action.get("run_id") == run_id
        ):
            return
        return original(root, tree_mutated, current_phase)

    parent._finalize_failed_upgrade = _legacy_finalizer
    parent._wf_memory_action_bridge = True


def _pause_for_memory_action(ctx, *, state: str, run_id: str, message: str) -> None:
    _arm_memory_action_required(ctx, state=state, run_id=run_id)
    print(message, flush=True)
    raise SystemExit(4)


def pre_index_update(ctx):
    """Keep candidate publication on the newly installed runner."""

    enforce_index_guard_handoff(ctx)
    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    # 1u44n: authorize the Phase 4 children BEFORE the no-memory early return
    # below — the non-memory case is exactly the one that needs the bridge
    # most. Fail-safety lives HERE, inside the hook body: the dispatcher
    # re-raises SystemExit and converts any other hook exception into a fatal
    # exit 3 that RETAINS the lock, so an unexpected bridge bug must be
    # absorbed rather than convert every zip-borne upgrade into a
    # retained-lock failure. An ungranted child degrades to the pre-existing
    # refusal, never worse.
    try:
        _bridge_index_publisher_grant(ctx.root, lock)
    except Exception:
        pass
    run_id = str(lock.get("memory_backfill_run_id") or "").strip()
    if not run_id:
        return
    backfill = _installed_memory_backfill(ctx.root)
    summary = backfill.reconcile_index_publication(ctx.root, run_id)
    if summary["state"] == "awaiting_validation":
        _pause_for_memory_action(
            ctx, state="awaiting_memory_validation", run_id=run_id,
            message="Historical memory requires validation. Reload the installed MCP/runtime, run memory_validate, then call wf_upgrade(phase='resume_after_memory').",
        )
    if (
        summary["state"] == "ready_for_index"
        and int(summary.get("candidates_drafted") or 0) > 0
    ):
        _pause_for_memory_action(
            ctx, state="awaiting_memory_publication", run_id=run_id,
            message="Historical memory is ready for receipt-owned publication. Reload the installed MCP/runtime and call wf_upgrade(phase='resume_after_memory').",
        )
    _update_upgrade_state(
        ctx.root,
        memory_backfill_state=summary["state"],
        memory_backfill_pending=(
            summary["remaining_waves"]
            + summary["candidates_pending"]
            + summary["failures"]
        ),
    )


def post_index_update(ctx):
    """Seal an old runner's zero-candidate/no-source historical run."""

    lock = _read_json_object(
        ctx.root / ".wavefoundry" / "upgrade-in-progress.json"
    )
    run_id = str(lock.get("memory_backfill_run_id") or "").strip()
    if not run_id:
        return
    backfill = _installed_memory_backfill(ctx.root)
    summary = backfill.reconcile_index_publication(ctx.root, run_id)
    if (
        summary["state"] == "ready_for_index"
        and int(summary.get("candidates_drafted") or 0) == 0
    ):
        backfill.mark_indexed(ctx.root, run_id)
        summary = backfill.run_summary(ctx.root, run_id)
    if summary["state"] != "indexed":
        raise RuntimeError(
            "candidate-bearing historical-memory publication requires the "
            "newly installed resume_after_memory runner"
        )
    _update_upgrade_state(ctx.root, memory_backfill_state="indexed")

# ---------------------------------------------------------------------------
# 1.4.x → 1.5.0 migration (wave 1p35d / 1p3ay)
# ---------------------------------------------------------------------------
#
# Wave 1p35d introduced three changes that break in-place on existing consumer
# installs running ``Upgrade wave framework`` from 1.4.x:
#
#   1. C4 (1p35l): docs-lint enforces ``Role:`` on every ``docs/agents/*.md``.
#      Custom agent docs added by operators after their last install fail lint
#      on the first post-upgrade docs gate run.
#
#   2. C5 (1p35n): ``.claude/hooks/pycache-cleanup*`` launcher files become
#      orphans — the framework no longer renders them but they remain in
#      consumer repos.
#
#   3. C5 (1p35n): ``.claude/settings.json`` ``PostToolUse`` Bash hook row
#      pointing at the retired ``pycache-cleanup`` launcher persists because
#      ``render_platform_surfaces.py`` merges settings rather than overwriting.
#      Claude Code invokes a deleted launcher on every Bash tool call.
#
# Each migration below is idempotent: re-running ``Upgrade wave framework``
# performs zero work after the migrations have already run. Version-gated by
# ``_from_version_predates(from_version, "1.5.0")``; from 1.5.0 onward the
# migrations skip entirely.

_PRE_1_5_0_CUTOFF: tuple[int, int, int] = (1, 5, 0)

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def _parse_semver_prefix(version: str) -> tuple[int, int, int] | None:
    """Return (major, minor, patch) when ``version`` starts with a semver
    triple. Returns None for unparseable inputs (date-style or empty)."""
    if not version:
        return None
    match = _SEMVER_RE.match(version)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _from_version_predates(from_version: str | None, cutoff: str) -> bool:
    """True when ``from_version`` is older than ``cutoff`` (or unparseable).

    Unknown / unparseable inputs return True so we treat them as "old" — the
    migrations are idempotent, so re-running them on an already-migrated state
    is safe; missing a needed migration is not.
    """
    cutoff_parsed = _parse_semver_prefix(cutoff)
    if cutoff_parsed is None:
        return True
    parsed = _parse_semver_prefix(from_version or "")
    if parsed is None:
        return True
    return parsed < cutoff_parsed


# --- Migration 1: Role: backfill ---------------------------------------------

_AGENT_DOC_ROLE_EXEMPT_NAMES = frozenset({
    "README.md", "session-handoff.md", "platform-mapping.md",
})
_ROLE_LINE_RE = re.compile(r"^Role:\s+", re.MULTILINE)
_STATUS_LINE_RE = re.compile(r"^(Status:\s+.*)$", re.MULTILINE)
_OWNER_LINE_RE = re.compile(r"^(Owner:\s+.*)$", re.MULTILINE)


def _backfill_role_field_on_agent_docs(root: Path) -> list[str]:
    """Insert ``Role: <slug>`` into agent docs missing the field.

    Returns the list of repository-relative paths modified. Empty list when
    no modifications were needed.

    Walks ``docs/agents/*.md``, ``docs/agents/specialists/*.md``, and
    ``docs/agents/personas/*.md``. Skips:
    - Exempt filenames (README.md, session-handoff.md, platform-mapping.md)
    - Anything under ``docs/agents/journals/`` (journal docs)
    - Files that already declare ``Role:``

    Inserts ``Role: <stem>`` immediately after the ``Status:`` line, falling
    back to insertion after ``Owner:`` if no ``Status:`` line exists.
    """
    modified: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return modified

    # Wave 1p3b9 (1p3b7 F6): recursive walk replaces the previous fixed-subdir
    # iteration so enterprise nested layouts (e.g.,
    # `docs/agents/teams/<team>/<role>.md`) are covered. A history directory
    # at any depth is skipped; the exempt-filename list still applies.
    # Wave 1zyb2 (1zxnt): the shared history predicate is imported here, after
    # the target's scripts directory is on sys.path, and tests the
    # root-relative path so an ancestor of the checkout never decides it.
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from history_paths import is_history_path

    try:
        candidates = sorted(agents_root.rglob("*.md"))
    except OSError:
        return modified
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in _AGENT_DOC_ROLE_EXEMPT_NAMES:
            continue
        if is_history_path(path.relative_to(root)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _ROLE_LINE_RE.search(text):
            continue  # already has Role:, no work needed
        stem = path.stem
        replacement = lambda m, s=stem: f"{m.group(1)}\nRole: {s}"
        new_text, count = _STATUS_LINE_RE.subn(replacement, text, count=1)
        if count == 0:
            new_text, count = _OWNER_LINE_RE.subn(replacement, text, count=1)
        if count == 0:
            # No anchor line — skip rather than corrupt the file
            continue
        try:
            path.write_text(new_text, encoding="utf-8")
        except OSError:
            continue
        try:
            modified.append(str(path.relative_to(root)).replace("\\", "/"))  # wave 1p9hm: forward-slash
        except ValueError:
            modified.append(str(path))
    return modified


# --- Migration 2: Pycache launcher cleanup -----------------------------------

_PYCACHE_LAUNCHER_NAMES = ("pycache-cleanup", "pycache-cleanup.py", "pycache-cleanup.cmd")


def _delete_pycache_hook_launchers(root: Path) -> list[str]:
    """Delete orphan ``.claude/hooks/pycache-cleanup*`` files.

    Returns the list of repository-relative paths deleted. Empty list when
    none existed.
    """
    deleted: list[str] = []
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return deleted
    for name in _PYCACHE_LAUNCHER_NAMES:
        path = hooks_dir / name
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            continue
        try:
            deleted.append(str(path.relative_to(root)).replace("\\", "/"))  # wave 1p9hm: forward-slash
        except ValueError:
            deleted.append(str(path))
    return deleted


# --- Migration 3: settings.json pycache row strip ----------------------------


def _is_retired_pycache_row(entry) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("matcher") != "Bash":
        return False
    nested = entry.get("hooks")
    if not isinstance(nested, list) or not nested:
        return False
    first = nested[0]
    if not isinstance(first, dict):
        return False
    command = first.get("command")
    if not isinstance(command, str):
        return False
    normalized = command.lower().rstrip()
    return (normalized.endswith("pycache-cleanup")
            or normalized.endswith("pycache-cleanup.cmd"))


def _strip_pycache_row_from_settings_file(settings_path: Path, root: Path) -> str | None:
    """Strip the retired pycache row from a single settings.json-shaped file.

    Returns the repo-relative path when modified, else None. Used to handle
    both ``.claude/settings.json`` and the personal-override
    ``.claude/settings.local.json`` (wave 1p3b9 / 1p3b7 F4).
    """
    if not settings_path.is_file():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    hooks_block = data.get("hooks")
    if not isinstance(hooks_block, dict):
        return None
    post_tool = hooks_block.get("PostToolUse")
    if not isinstance(post_tool, list):
        return None
    original_len = len(post_tool)
    post_tool_filtered = [e for e in post_tool if not _is_retired_pycache_row(e)]
    if len(post_tool_filtered) == original_len:
        return None
    hooks_block["PostToolUse"] = post_tool_filtered
    try:
        settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        return None
    try:
        return str(settings_path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
    except ValueError:
        return str(settings_path)


def _strip_pycache_row_from_claude_settings(root: Path) -> list[str]:
    """Remove the retired ``PostToolUse`` Bash → pycache-cleanup hook row from
    both ``.claude/settings.json`` AND ``.claude/settings.local.json``.

    Returns a list of relative paths modified (possibly empty, one, or two
    entries). Preserves all other hook rows including operator-added customs.

    Wave 1p3b9 (1p3b7 F4): added the personal-override settings.local.json to
    the strip set so enterprise consumers with shared local-overrides don't
    leave the orphan row behind. The original 1p35d C7 migration only touched
    the committed `settings.json`.

    Matches a hook block whose ``matcher == "Bash"`` AND whose nested
    ``hooks[0].command`` ends with ``pycache-cleanup`` or
    ``pycache-cleanup.cmd``. Does not touch any other matcher value or any
    hook command.
    """
    modified: list[str] = []
    for fname in ("settings.json", "settings.local.json"):
        result = _strip_pycache_row_from_settings_file(
            root / ".claude" / fname, root
        )
        if result:
            modified.append(result)
    return modified


def _strip_pycache_row_legacy_single_path(root: Path) -> str | None:
    """Backward-compat shim. Returns the relative path of the first file
    modified by `_strip_pycache_row_from_claude_settings`, or None.

    The C7 (1p3ay) migration code called `_strip_pycache_row_from_claude_settings`
    expecting a `str | None` return shape. C5 (1p3b7 F4) changed the signature
    to return a list. The shim preserves the old shape for any external caller
    that imported the old name. Internal callers use the new list-returning
    form.
    """
    result = _strip_pycache_row_from_claude_settings(root)
    if not result:
        return None
    return result[0]


# --- Migration report writer -------------------------------------------------


def _write_migration_report(root: Path, sections: list[tuple[str, list[str]]]) -> Path | None:
    """Write a consolidated migration report to .wavefoundry/logs/.

    ``sections`` is a list of (migration-name, action-records) tuples. An
    action-records list may include normal action descriptions and
    exception-trace strings (prefixed ``ERROR:`` by callers).

    Returns the report path when a report was written; None when no section
    had any records.
    """
    if not any(records for _name, records in sections):
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "upgrade-migration-1.5.0.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"# Upgrade migration 1.4.x → 1.5.0",
        f"# Run timestamp: {timestamp}",
        "",
    ]
    for name, records in sections:
        if not records:
            continue
        lines.append(f"## {name}")
        for rec in records:
            lines.append(f"- {rec}")
        lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


# --- Preview helpers (Wave 1p3b9 / 1p3b6: --dry-run support) -----------------
#
# Each preview helper has the same signature and contract as its action
# companion, EXCEPT it performs ZERO filesystem mutations and returns the
# planned-action list instead. Used by `post_extract` when `ctx.dry_run` is
# True so operators can review what the migration WOULD do before committing.


def _preview_role_field_backfill(root: Path) -> list[str]:
    """Preview variant of `_backfill_role_field_on_agent_docs`. Returns the
    list of repository-relative paths that WOULD have `Role: <slug>` inserted,
    formatted as ``<path>: would insert Role: <slug>``. Zero filesystem
    mutations."""
    planned: list[str] = []
    agents_root = root / "docs" / "agents"
    if not agents_root.is_dir():
        return planned
    # Wave 1p3b9 (1p3b7 F6): recursive walk parallels the action helper,
    # including the shared history predicate (wave 1zyb2, 1zxnt).
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from history_paths import is_history_path

    try:
        candidates = sorted(agents_root.rglob("*.md"))
    except OSError:
        return planned
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in _AGENT_DOC_ROLE_EXEMPT_NAMES:
            continue
        if is_history_path(path.relative_to(root)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _ROLE_LINE_RE.search(text):
            continue
        # Detect whether either anchor (Status:/Owner:) is present so the
        # preview matches the action helper's would-skip-no-anchor logic.
        if not (_STATUS_LINE_RE.search(text) or _OWNER_LINE_RE.search(text)):
            continue
        stem = path.stem
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
        except ValueError:
            rel = str(path)
        planned.append(f"{rel}: would insert `Role: {stem}`")
    return planned


def _preview_pycache_launcher_deletion(root: Path) -> list[str]:
    """Preview variant of `_delete_pycache_hook_launchers`. Returns the list
    of launcher files that WOULD be deleted. Zero filesystem mutations."""
    planned: list[str] = []
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return planned
    for name in _PYCACHE_LAUNCHER_NAMES:
        path = hooks_dir / name
        if path.exists():
            try:
                rel = str(path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
            except ValueError:
                rel = str(path)
            planned.append(f"would delete {rel}")
    return planned


def _preview_settings_pycache_strip(root: Path) -> dict | None:
    """Preview variant of `_strip_pycache_row_from_claude_settings`. Returns
    a description of the FIRST row that WOULD be stripped (across both
    `settings.json` and `settings.local.json` per wave 1p3b9 / 1p3b7 F4),
    or None when no row matches in either file. Zero filesystem mutations."""
    for fname in ("settings.json", "settings.local.json"):
        settings_path = root / ".claude" / fname
        if not settings_path.is_file():
            continue
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        hooks_block = data.get("hooks")
        if not isinstance(hooks_block, dict):
            continue
        post_tool = hooks_block.get("PostToolUse")
        if not isinstance(post_tool, list):
            continue
        for entry in post_tool:
            if not _is_retired_pycache_row(entry):
                continue
            command = entry["hooks"][0]["command"]
            try:
                rel = str(settings_path.relative_to(root)).replace("\\", "/")  # wave 1p9hm: forward-slash
            except ValueError:
                rel = str(settings_path)
            return {
                "file": rel,
                "matcher": entry.get("matcher"),
                "command": command,
                "note": "would strip this PostToolUse Bash row",
            }
    return None


def _write_migration_preview_report(
    root: Path, sections: list[tuple[str, list[str]]],
) -> Path | None:
    """Wave 1p3b9 (1p3b6): write the preview-log to a DISTINCT filename so a
    dry-run report doesn't shadow a subsequent real-run report. Mirrors
    `_write_migration_report` shape but lands at `.preview.log`."""
    if not any(records for _name, records in sections):
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "upgrade-migration-1.5.0.preview.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade migration 1.4.x → 1.5.0 — PREVIEW (--dry-run; zero mutations performed)",
        f"# Run timestamp: {timestamp}",
        "",
    ]
    for name, records in sections:
        if not records:
            continue
        lines.append(f"## {name}")
        for rec in records:
            lines.append(f"- {rec}")
        lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


# --- Convergence migration (wave 1p3iv / 1p3j7; self-contained as of 1p5b4) -------
#
# Rewrites legacy config keys to their canonical names in `docs/workflow-config.json`.
# Runs on EVERY upgrade (no version gate) — idempotent because already-canonical configs
# no-op. Operators on legacy spellings (`wave_council_policy`, `wave_execution`) get
# auto-converted at upgrade time so the deprecation window closes.
#
# Wave 1p5b4: the canonical-names manifest was retired; this convergence is now the only
# remaining piece — a self-contained hardcoded table, kept as the one-shot safety net for
# skip-version operators. Slated for removal at 2.0.0 (by then every maintained project has
# converged on upgrade).
_CONFIG_KEY_RENAMES = {
    "wave_execution": "wave_implement",
    "wave_council_policy": "wave_review",
}


def _load_config_key_renames(repo_root):
    """Return {legacy: canonical} for the config-key convergence migration.
    Self-contained (no manifest) as of wave 1p5b4; the whole migration is removed at 2.0.0.
    ``repo_root`` is accepted for call-site compatibility and unused."""
    return dict(_CONFIG_KEY_RENAMES)


def _preview_legacy_config_key_rewrite(repo_root):
    """Plan the rewrite without touching disk. Returns a list of human-readable
    planned-action strings; empty list when no work would be done."""
    workflow_config = repo_root / "docs/workflow-config.json"
    if not workflow_config.exists():
        return []
    try:
        data = json.loads(workflow_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    renames = _load_config_key_renames(repo_root)
    planned = []
    for legacy, canonical in renames.items():
        if legacy in data and canonical not in data:
            planned.append(
                f"would rename `{legacy}` → `{canonical}` in docs/workflow-config.json"
            )
        elif legacy in data and canonical in data:
            planned.append(
                f"would drop legacy `{legacy}` (canonical `{canonical}` already present) "
                f"in docs/workflow-config.json"
            )
    return planned


def _rewrite_legacy_config_keys(repo_root):
    """Rewrite legacy keys to canonical in workflow-config.json. Returns a
    list of (legacy, canonical, action, dropped_value) tuples for the renames
    performed. `action` is ``"rename"`` (legacy → canonical) or ``"drop"``
    (canonical already present; legacy entry removed). `dropped_value` is
    the JSON value the legacy key held (only populated when action == "drop",
    None otherwise) — included so operators recovering from the migration log
    can see what was dropped without consulting git history. Idempotent —
    no-op when no legacy keys are present."""
    workflow_config = repo_root / "docs/workflow-config.json"
    if not workflow_config.exists():
        return []
    try:
        data = json.loads(workflow_config.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        # 1p5do: do not no-op silently — a malformed config that can't be rewritten will later fail
        # the docs gate with no migration-side signal, making the gate failure baffling. Warn here so
        # the operator can connect the gate failure to the un-migrated config.
        print(
            f"  WARNING: convergence migration could not read/parse {workflow_config} ({exc}); "
            "legacy config keys were NOT rewritten — the docs gate may fail until this is fixed.",
            file=sys.stderr,
        )
        return []
    if not isinstance(data, dict):
        print(
            f"  WARNING: convergence migration found {workflow_config} is not a JSON object; "
            "legacy config keys were NOT rewritten.",
            file=sys.stderr,
        )
        return []
    renames = _load_config_key_renames(repo_root)
    performed = []
    # Build a new dict preserving original key order with renames applied,
    # so the on-disk file remains diffable across upgrades.
    new_data = {}
    for key, value in data.items():
        if key in renames:
            canonical = renames[key]
            if canonical in data:
                # Canonical already present: drop the legacy entry. Record
                # the dropped value so operators recovering from the log can
                # see what was thrown away.
                performed.append((key, canonical, "drop", value))
                continue
            new_data[canonical] = value
            performed.append((key, canonical, "rename", None))
        else:
            new_data[key] = value
    if not performed:
        return []
    workflow_config.write_text(
        json.dumps(new_data, indent=2) + "\n",
        encoding="utf-8",
    )
    return performed


def _write_convergence_preview_report(root, planned):
    """Wave 1p3iv (1p3j7): write the convergence dry-run preview to a
    distinct log file for parity with `_write_migration_preview_report`.
    Operators running `--dry-run` get a written record to review before
    committing to the real upgrade."""
    if not planned:
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    report_path = logs_dir / "upgrade-convergence-migration.preview.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade convergence migration — PREVIEW (--dry-run; zero mutations performed)",
        f"# Run timestamp: {timestamp}",
        "",
        "## Legacy config-key rewrite (1p3j7 — convergence half)",
    ]
    for record in planned:
        lines.append(f"- {record}")
    lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


def _write_convergence_report(root, performed):
    """Wave 1p3iv (1p3j7): write the convergence real-run log alongside the
    1.5.0 migration report for parity. Records each rename / drop with the
    dropped value (when applicable) so operators recovering from a surprise
    can read the log instead of consulting git."""
    if not performed:
        return None
    logs_dir = root / ".wavefoundry" / "logs"
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    report_path = logs_dir / "upgrade-convergence-migration.log"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Upgrade convergence migration — REAL RUN",
        f"# Run timestamp: {timestamp}",
        "",
        "## Legacy config-key rewrite (1p3j7 — convergence half)",
    ]
    for legacy, canonical, action, dropped_value in performed:
        if action == "rename":
            lines.append(
                f"- renamed `{legacy}` → `{canonical}` in docs/workflow-config.json"
            )
        else:  # drop
            value_repr = json.dumps(dropped_value)
            lines.append(
                f"- dropped legacy `{legacy}` (canonical `{canonical}` already "
                f"present in docs/workflow-config.json); dropped value was: "
                f"`{value_repr}`"
            )
    lines.append("")
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        return None
    return report_path


def _run_convergence_migration(ctx):
    """Top-level convergence migration. Always runs (no version gate).
    Records to a dedicated log file and stderr; silent no-op when no renames
    apply. Dry-run writes to `.preview.log`; real-run writes to `.log`."""
    try:
        if getattr(ctx, "dry_run", False):
            planned = _preview_legacy_config_key_rewrite(ctx.root)
            if planned:
                report_path = _write_convergence_preview_report(ctx.root, planned)
                tail = f" — see {report_path}" if report_path else ""
                print(
                    f"upgrade-convergence preview: {len(planned)} legacy "
                    f"config-key rewrite(s) planned in docs/workflow-config.json{tail}",
                    file=sys.stderr,
                )
                for record in planned:
                    print(f"  - {record}", file=sys.stderr)
        else:
            performed = _rewrite_legacy_config_keys(ctx.root)
            if performed:
                # Build a compact summary that distinguishes rename from drop
                # so the stderr line isn't misleading on the both-present case.
                renames = [
                    f"`{l}`→`{c}`" for l, c, action, _v in performed
                    if action == "rename"
                ]
                drops = [
                    f"`{l}` (canonical `{c}` already present)"
                    for l, c, action, _v in performed
                    if action == "drop"
                ]
                report_path = _write_convergence_report(ctx.root, performed)
                tail = f" — see {report_path} for the dropped values" if report_path else ""
                parts = []
                if renames:
                    parts.append(f"renamed {len(renames)} ({', '.join(renames)})")
                if drops:
                    parts.append(f"dropped {len(drops)} ({', '.join(drops)})")
                print(
                    f"upgrade-convergence: {'; '.join(parts)} in "
                    f"docs/workflow-config.json{tail}",
                    file=sys.stderr,
                )
    except Exception:  # pragma: no cover — defensive isolation
        print(
            f"upgrade-convergence: ERROR: {traceback.format_exc()}",
            file=sys.stderr,
        )


# --- Wired hook --------------------------------------------------------------


def post_extract(ctx):
    """1.4.x → 1.5.0 migration hook.

    Runs only when ``ctx.from_version`` predates 1.5.0. Each migration is
    isolated in its own try/except so a failure in one does not abort the
    others; failures are recorded in the report rather than raised.

    Wave 1p3b9 (1p3b6): when ``ctx.dry_run`` is True, the preview helpers
    fire instead of the action helpers — zero filesystem mutations, preview
    output written to a DISTINCT filename
    (``upgrade-migration-1.5.0.preview.log``) so it does not shadow a
    subsequent real-run report. Operators can review the planned actions
    before committing to the real upgrade.

    Wave 1p3iv (1p3j7): the convergence migration runs FIRST, before the
    1.4 → 1.5 version gate, on every upgrade. It rewrites legacy config keys to
    canonical in ``docs/workflow-config.json``. Idempotent — no-op when no legacy
    keys are present. (Wave 1p5b4: the rename map is now a self-contained hardcoded
    table — the canonical-names manifest was retired; this convergence is removed at 2.0.0.)
    """
    # Storage conversion must stop the old installing coordinator before it
    # can call an old indexer or cleanup. Load the newly extracted, stdlib-only
    # helper explicitly; never hide this safety failure in migration reports.
    if not getattr(ctx, "dry_run", False):
        # Wave 1zqe4 (1zrah): before any new-tree module is imported in this
        # process, so an older runner's cached leaves never feed it.
        _refresh_record_layout_modules_at_extraction(ctx.root)
        migration_path = Path(ctx.root) / ".wavefoundry/framework/scripts/sqlite_storage_migration.py"
        if migration_path.is_file():
            spec = importlib.util.spec_from_file_location("_installed_storage_migration", migration_path)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            migration.prepare_upgrade(ctx)
            ctx._index_guard_migration_module = migration
        enforce_index_guard_handoff(ctx)

    # Wave 1p3iv (1p3j7): convergence half — runs on every upgrade.
    _run_convergence_migration(ctx)

    if not _from_version_predates(ctx.from_version, "1.5.0"):
        return

    # Wave 1p3b9 (1p3b6): dry-run branch. UpgradeContext gained `dry_run` so
    # we can preview without touching disk. Fall back to False for older
    # contexts (`getattr` default) — the field is new in 1.5.0.
    if getattr(ctx, "dry_run", False):
        preview_sections: list[tuple[str, list[str]]] = []
        try:
            planned = _preview_role_field_backfill(ctx.root)
            preview_sections.append((
                "Role: backfill on docs/agents/*.md "
                "(C4 / 1p35l: docs-lint now enforces Role: on every agent doc)",
                planned,
            ))
        except Exception:
            preview_sections.append((
                "Role: backfill on docs/agents/*.md",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        try:
            planned = _preview_pycache_launcher_deletion(ctx.root)
            preview_sections.append((
                "Pycache launcher cleanup "
                "(C5 / 1p35n: .claude/hooks/pycache-cleanup* retired)",
                planned,
            ))
        except Exception:
            preview_sections.append((
                "Pycache launcher cleanup",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        try:
            row = _preview_settings_pycache_strip(ctx.root)
            preview_sections.append((
                "Claude Code settings.json pycache row removal "
                "(C5 / 1p35n: PostToolUse Bash → pycache-cleanup row retired)",
                [f"would strip from {row['file']}: matcher={row['matcher']!r} "
                 f"command={row['command']!r}"] if row else [],
            ))
        except Exception:
            preview_sections.append((
                "Claude Code settings.json pycache row removal",
                [f"ERROR (preview): {traceback.format_exc()}"],
            ))
        report_path = _write_migration_preview_report(ctx.root, preview_sections)
        total = sum(len(recs) for _name, recs in preview_sections)
        if total > 0:
            print(
                f"upgrade-migration preview: {total} planned action(s); "
                f"see {report_path} for details (no files modified)",
                file=sys.stderr,
                flush=True,
            )
        return

    sections: list[tuple[str, list[str]]] = []

    # Migration 1: Role: backfill
    try:
        modified = _backfill_role_field_on_agent_docs(ctx.root)
        sections.append((
            "Role: backfill on docs/agents/*.md "
            "(C4 / 1p35l: docs-lint now enforces Role: on every agent doc)",
            [f"inserted `Role: <slug>` into {rel}" for rel in modified],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Role: backfill on docs/agents/*.md",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    # Migration 2: Pycache launcher cleanup
    try:
        deleted = _delete_pycache_hook_launchers(ctx.root)
        sections.append((
            "Pycache launcher cleanup "
            "(C5 / 1p35n: .claude/hooks/pycache-cleanup* retired)",
            [f"deleted {rel}" for rel in deleted],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Pycache launcher cleanup",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    # Migration 3: settings.json pycache row strip (covers both committed
    # `.claude/settings.json` AND personal-override `.claude/settings.local.json`
    # per wave 1p3b9 / 1p3b7 F4).
    try:
        modified_settings = _strip_pycache_row_from_claude_settings(ctx.root)
        sections.append((
            "Claude Code settings.json pycache row removal "
            "(C5 / 1p35n: PostToolUse Bash → pycache-cleanup row retired; "
            "1p3b7 F4 added settings.local.json coverage)",
            [f"stripped PostToolUse Bash → pycache-cleanup row from {rel}"
             for rel in modified_settings],
        ))
    except Exception:  # pragma: no cover — defensive isolation
        sections.append((
            "Claude Code settings.json pycache row removal",
            [f"ERROR: {traceback.format_exc()}"],
        ))

    _write_migration_report(ctx.root, sections)
