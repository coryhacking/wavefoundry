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

RECEIPT = "sqlite-migration.json"
LEGACY_NAMES = ("docs.lance", "code.lance", "__manifest")
STATES = {"restart_required", "quiesced", "staged", "validated", "cutover_pending",
          "published", "verified", "cleanup_pending", "complete"}
READABLE_STATES = {"published", "verified", "cleanup_pending", "complete"}
SCHEMA_VERSION = "7"
# Shipped historical formats: schema 4 at a62d612a; schema 5 adds
# layer_path_state at 2952df8f; schema 6 adds build_state at 6bcac5f1.
# Existing auxiliary table definitions are identical across these versions.
LEGACY_SCHEMA_VERSIONS = frozenset({"4", "5", "6"})
INVOCATION_ENV = "WAVEFOUNDRY_STORAGE_INVOCATION"
CONFIRM_ENV = "WAVEFOUNDRY_STORAGE_HOSTS_STOPPED"
OLD_MCP_PID_ENV = "WAVEFOUNDRY_STORAGE_OLD_MCP_PID"
LEGACY_RECOVERY_GUIDANCE = (
    "Original storage, receipt and checkpoint are retained. Stop Wavefoundry hosts; "
    "recover a duplicate with a verified compatible older framework/runtime and its canonical "
    "wf setup --full before retrying a fresh standard upgrade. Keep the original index and "
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


def read_receipt(index_dir: Path) -> dict | None:
    path = _safe(Path(index_dir) / RECEIPT)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise MigrationRequired("storage_receipt_unreadable") from exc
    if (not isinstance(value, dict) or value.get("receipt_version") != 1
            or value.get("state") not in STATES
            or not re.fullmatch(r"[0-9a-f]{32}", str(value.get("migration_id", "")))
            or value.get("index_dir") != str(Path(index_dir).resolve())
            or value.get("root_identity") != _identity(Path(index_dir).parent.parent)):
        raise MigrationRequired("storage_receipt_identity_mismatch")
    return value


def _sqlite_schema(index_dir: Path) -> str:
    """Read the single schema authority through a qualified WAL-aware snapshot.

    Bootstrap hosts may lack the incoming runtime. An existing file then needs
    a restart checkpoint and a qualified probe after normal dependency setup.
    File headers are never schema authority: committed metadata may be in WAL.
    """
    path = _safe_sqlite(index_dir / "index-state.sqlite")
    if not path.exists():
        if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm")):
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
            raise MigrationRequired("storage_source_identity_changed: index-state.sqlite")
        return str(row[0]) if row else "unknown"
    except MigrationRequired:
        raise
    except Exception as exc:
        raise MigrationRequired("storage_schema_unreadable: preserve the shared database and resume after recovery") from exc
    finally:
        conn.close()


def detect(index_dir: Path) -> dict:
    index_dir = _safe(Path(index_dir))
    receipt = read_receipt(index_dir)
    legacy = [name for name in LEGACY_NAMES if (index_dir / name).exists()
              or (index_dir / name).is_symlink()]
    schema = _sqlite_schema(index_dir) if receipt is None else "receipt_owned"
    if schema not in {"absent", "runtime_unavailable", "receipt_owned", SCHEMA_VERSION} | LEGACY_SCHEMA_VERSIONS:
        raise MigrationRequired(f"storage_schema_unsupported: {schema}; preserve the shared database")
    return {"legacy": legacy, "receipt": receipt, "sqlite_schema": schema,
            "migration_required": bool((legacy or schema in LEGACY_SCHEMA_VERSIONS | {"runtime_unavailable"}) and not receipt
                                       or receipt and receipt["state"] not in READABLE_STATES)}


def require_ready(index_dir: Path, allow_migration: bool = False) -> None:
    state = detect(index_dir)
    receipt = state["receipt"]
    if receipt and receipt["state"] in READABLE_STATES - {"complete"}:
        _published_identity(Path(index_dir), receipt)
    if allow_migration:
        return
    if state["migration_required"]:
        raise MigrationRequired("storage_migration_required: run wf_upgrade; restart old hosts and resume the retained checkpoint")


def restore_checkpoint(root: Path) -> dict | None:
    """Run before generic dead-PID checkpoint cleanup or overwrite."""
    import upgrade_lib
    index_dir = Path(root) / ".wavefoundry" / "index"
    receipt = read_receipt(index_dir)
    if receipt is None or receipt["state"] == "complete":
        return receipt
    if upgrade_lib.read_upgrade_lock(root) is None:
        upgrade_lib.write_upgrade_lock(root, receipt.get("source_version"),
                                       receipt.get("target_version") or "unknown",
                                       Path(receipt["pack_path"]) if receipt.get("pack_path") else None)
    if not upgrade_lib.update_upgrade_lock(root, storage_migration_id=receipt["migration_id"],
                                           storage_migration_state=receipt["state"]):
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


def restart_command(root: Path, pack_path: str | None, rebuild_storage: bool = False) -> dict:
    executable = sys.executable
    console = Path(executable)
    if os.name == "nt" and console.stem.lower() == "pythonw" and console.suffix.lower() == ".exe":
        executable = str(console.with_name(console.stem[:-1] + console.suffix))
    argv = [executable, str(Path(root).resolve() / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"), "--root", str(Path(root).resolve())]
    if pack_path:
        argv += ["--pack", pack_path]
    argv += ["--yes", "--confirm-hosts-stopped"]
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
    import upgrade_lib
    try:
        root = Path(root).resolve()
        receipt = read_receipt(root / ".wavefoundry/index")
        lock = upgrade_lib.read_upgrade_lock(root) or {}
        action = lock.get("action_required")
        if not receipt or receipt["state"] in READABLE_STATES or not isinstance(action, dict) or action != receipt.get("restart_action"):
            return None
        if (action.get("kind") != "storage_migration" or action.get("state") != "restart_required"
                or action.get("invocation_token") != invocation_token or action.get("root") != str(root)
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
              **restart_command(root, receipt.get("pack_path"), rebuild_requested(receipt))}
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


def prepare_upgrade(ctx) -> dict | None:
    root = Path(ctx.root).resolve()
    index_dir = root / ".wavefoundry" / "index"
    state = detect(index_dir)
    receipt = state["receipt"]
    if getattr(ctx, "rebuild_storage", False) and (
            (receipt is None and not state["migration_required"])
            or (receipt is not None and receipt["state"] == "complete")):
        raise MigrationRequired("storage_rebuild_not_applicable: no pending legacy storage conversion")
    # An existing framework can have a loaded old MCP writer even before its
    # first index exists. Fence that upgrade before setup creates schema 7.
    # from_version is the coordinator's installed-version context; a genuine
    # fresh installer has none. Conservatively this also restarts a current,
    # never-indexed target once, without introducing a second capability marker.
    upgrading_without_index = (bool(getattr(ctx, "from_version", None))
                               and state["sqlite_schema"] == "absent")
    if not state["migration_required"] and receipt is None and not upgrading_without_index:
        return None
    if getattr(ctx, "dry_run", False):
        return {"state": "restart_required", "legacy": state["legacy"]}
    if receipt is None:
        old_hosts = list(getattr(ctx, "storage_old_hosts", []))
        identified_mcp_pid = os.environ.get(OLD_MCP_PID_ENV)
        if identified_mcp_pid:
            if not identified_mcp_pid.isdecimal() or int(identified_mcp_pid) <= 0:
                raise MigrationRequired("storage_host_identity_invalid")
            old_hosts.append({"kind": "mcp", "pid": int(identified_mcp_pid),
                              "source": "initiating_mcp_wrapper"})
        receipt = {"receipt_version": 1, "migration_id": uuid.uuid4().hex,
                   "index_dir": str(index_dir.resolve()), "root_identity": _identity(root),
                   "source_version": getattr(ctx, "from_version", None),
                   "target_version": getattr(ctx, "to_version", None),
                   "pack_path": str(Path(ctx.zip_path).resolve()) if getattr(ctx, "zip_path", None) else None,
                   "pack_sha256": _file_hash(Path(ctx.zip_path)) if getattr(ctx, "zip_path", None) else None,
                   "state": "restart_required", "old_hosts": old_hosts,
                   "reason": "existing_framework_without_index" if upgrading_without_index else "legacy_storage",
                   "source_sqlite_identity": (_identity(index_dir / "index-state.sqlite")
                                              if (index_dir / "index-state.sqlite").exists() else None),
                   "artifacts": {name: _identity(index_dir / name) for name in state["legacy"]}}
        _write(index_dir, receipt)
    if receipt["state"] == "complete":
        return receipt
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
    if receipt["state"] in READABLE_STATES and getattr(ctx, "storage_migration_protocol", 0) == 1:
        return receipt
    if receipt["state"] in READABLE_STATES:
        raise MigrationRequired("storage_current_runner_required: resume using the installed upgrade CLI; storage was already published")
    _refresh_hosts(root, receipt)
    restore_checkpoint(root)
    # Old archive dispatchers cannot honor new storage guards; always unwind
    # their installing invocation before running any native conversion.
    confirmed = os.environ.get(CONFIRM_ENV) == "1"
    if getattr(ctx, "storage_migration_protocol", 0) != 1 or not confirmed:
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
        if name not in LEGACY_NAMES or _identity(index_dir / name) != identity:
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
    rebuild = rebuild_requested(receipt)
    if not state["migration_required"] and receipt is None:
        return {"state": "not_applicable"}
    if receipt is None:
        raise MigrationRequired("storage_restart_required: run the primary upgrade phase first")
    restore_checkpoint(root)
    if receipt["state"] in READABLE_STATES:
        if receipt["state"] != "complete":
            _published_identity(index_dir, receipt)
        return receipt
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
                "standard wf_upgrade with confirm_hosts_stopped=True (CLI --confirm-hosts-stopped). "
                "Migration paused before staging or cutover; original stores and receipt are retained.") from exc
        except runtime.StorageRecoveryRequired as exc:
            raise MigrationRequired(
                f"{exc}; storage migration paused before staging or cutover. "
                "Original stores, candidate and receipt are retained; correct the runtime or "
                "filesystem requirement and resume standard wf_upgrade.") from exc
        if receipt["state"] != "cutover_pending":
            source_identity = receipt.get("source_sqlite_identity")
            if source_identity is not None and _identity(index_dir / "index-state.sqlite") != source_identity:
                raise MigrationRequired("storage_source_identity_changed: index-state.sqlite")
            if ("source_sqlite_identity" in receipt and source_identity is None
                    and (index_dir / "index-state.sqlite").exists()):
                raise MigrationRequired("storage_source_identity_changed: unexpected index-state.sqlite")
            schema = _sqlite_schema(index_dir)
            if schema == "runtime_unavailable":
                raise MigrationRequired(
                    "storage_runtime_restart_required: run wf setup to provision the pinned native runtime; "
                    "then start a fresh process and resume ordinary wf_upgrade with confirm_hosts_stopped=True "
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
        live_size = (index_dir / "index-state.sqlite").stat().st_size if (index_dir / "index-state.sqlite").exists() else 0
        if shutil.disk_usage(index_dir).free < source_size * 2 + live_size * 2 + 64 * 1024 * 1024:
            raise MigrationRequired("storage_disk_space_insufficient: retain original stores and free staging space")
        work = _safe(index_dir / ("sqlite-migration-" + receipt["migration_id"]))
        if work.exists() and receipt.get("work_identity") != _identity(work):
            raise MigrationRequired("storage_staging_identity_changed")
        work.mkdir(exist_ok=True)
        live = _safe_sqlite(index_dir / "index-state.sqlite")
        staged = _safe_sqlite(work / "index-state.sqlite")
        backup = _safe_sqlite(work / "rollback.sqlite")
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
                    and (not live.exists() and receipt.get("original_sha256") is None
                         or live.exists() and _file_hash(live) == receipt.get("original_sha256"))):
                return _publish_candidate(root, receipt, staged, live)
            raise MigrationRequired("storage_cutover_recovery_required: retained candidate and rollback need verification")
        for candidate in (staged, Path(str(staged) + "-wal"), Path(str(staged) + "-shm")):
            _safe(candidate).unlink(missing_ok=True)
        if live.exists():
            runtime.backup(_safe_sqlite(live), _safe_sqlite(staged))
            if not backup.exists():
                runtime.backup(_safe_sqlite(live), _safe_sqlite(backup))
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
                                raise MigrationRequired("storage_duplicate_or_missing_chunk_id: retain the receipt and original archive; "
                                    "if current project sources are available, resume the standard upgrade with --rebuild-storage "
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
        if live.exists():
            conn = runtime.connect(_safe_sqlite(live))
            try:
                checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                if checkpoint and checkpoint[0]:
                    raise MigrationRequired("storage_handles_busy")
            finally:
                conn.close()
        receipt.update(state="cutover_pending", candidate_sha256=_file_hash(staged),
                       published_sqlite_identity=_identity(staged),
                       original_sha256=_file_hash(live) if live.exists() else None)
        _write(index_dir, receipt)
        return _publish_candidate(root, receipt, staged, live)


def _published_identity(index_dir: Path, receipt: dict) -> Path:
    """Fence the cutover file, not its mutable generation or sidecar identities."""
    live = _safe_sqlite(index_dir / "index-state.sqlite")
    expected = receipt.get("published_sqlite_identity")
    if not expected:
        raise MigrationRequired(
            "storage_publication_identity_missing: retained receipt cannot prove the cutover file; "
            "preserve original stores and staging/rollback files for recovery before resuming upgrade")
    if not live.exists() or _identity(live) != expected:
        raise MigrationRequired("storage_publication_identity_changed: preserve original stores and recover the receipt-owned cutover file")
    return live


def _publish_candidate(root: Path, receipt: dict, staged: Path, live: Path) -> dict:
    _hosts_gone(receipt)
    if not receipt.get("published_sqlite_identity") or _identity(staged) != receipt["published_sqlite_identity"]:
        raise MigrationRequired("storage_cutover_candidate_identity_changed")
    _safe_sqlite(live)
    try:
        for suffix in ("-wal", "-shm"):
            sidecar = _safe(Path(str(live) + suffix))
            if sidecar.exists() and suffix == "-wal" and sidecar.stat().st_size:
                raise MigrationRequired("storage_cutover_live_wal_changed")
            sidecar.unlink(missing_ok=True)
        os.replace(staged, live)
    except OSError as exc:
        raise MigrationRequired(
            "storage_cutover_io_failed: cannot remove a SQLite sidecar or replace the live database. "
            "Close programs holding the index files, allow transient scanner activity to finish, "
            "and check filesystem permissions. Candidate, rollback and cutover_pending receipt "
            "are retained; resume standard wf_upgrade after releasing handles or fixing access.") from exc
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
    publication = receipt.get("upgrade_publication", {})
    if publication.get("semantic_exit") != 0 or publication.get("graph_exit") != 0:
        raise MigrationRequired("storage_all_layer_publication_unverified: resume standard wf_upgrade")
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
    receipt["state"] = "cleanup_pending"
    _write(index_dir, receipt)
    removed = set(receipt.get("removed", []))
    reclaimed = receipt.get("reclaimed_bytes", 0)
    for name, identity in receipt["artifacts"].items():
        _published_identity(index_dir, receipt)
        if name not in LEGACY_NAMES:
            raise MigrationRequired("storage_cleanup_path_unowned")
        path = _safe(index_dir / name)
        if name in removed or not path.exists():
            removed.add(name)
            continue
        if _identity(path) != identity:
            raise MigrationRequired(f"storage_cleanup_identity_changed: {name}")
        size = 0
        for base, dirs, files in os.walk(path, followlinks=False):
            _safe(Path(base))
            for child in dirs + files:
                node = _safe(Path(base) / child)
                if node.is_file():
                    size += node.stat().st_size
        if path.is_dir():
            # Reuse the existing upgrade cleanup's fd-anchored POSIX deletion
            # and explicitly narrower, revalidated Windows no-follow fallback.
            from upgrade_wavefoundry import _remove_retired_component
            outcome = _remove_retired_component(index_dir, name, custom=False, ownership_root=root)
            if outcome == "unowned":
                raise MigrationRequired(
                    "storage_cleanup_path_unowned: an owned index path changed or contains a "
                    "symlink/junction. Restore the receipt-owned directory inside the repository "
                    "and resume standard wf_upgrade; receipt and remaining sources are retained.")
            if outcome != "removed":
                raise MigrationRequired(
                    "storage_cleanup_removal_failed: release handles or correct permissions and "
                    "resume standard wf_upgrade; receipt and remaining sources are retained.")
        elif name == "__manifest" and path.is_file():
            size = path.stat().st_size
            _safe(path).unlink()
        else:
            raise MigrationRequired("storage_cleanup_artifact_type_invalid")
        reclaimed += size
        removed.add(name)
        receipt.update(removed=sorted(removed), reclaimed_bytes=reclaimed)
        _write(index_dir, receipt)
    work_name = receipt.get("work_dir")
    if work_name:
        if work_name != "sqlite-migration-" + receipt["migration_id"]:
            raise MigrationRequired("storage_cleanup_work_identity_invalid")
        work = _safe(index_dir / work_name)
        if work.exists():
            if receipt.get("work_identity") != _identity(work):
                raise MigrationRequired("storage_cleanup_work_identity_changed")
            for path in work.iterdir():
                _safe(path)
                if not path.is_file() or path.name not in {"index-state.sqlite", "index-state.sqlite-wal", "index-state.sqlite-shm", "rollback.sqlite", "rollback.sqlite-wal", "rollback.sqlite-shm"}:
                    raise MigrationRequired("storage_cleanup_unknown_staging_artifact")
                reclaimed += path.stat().st_size
                path.unlink()
            work.rmdir()
    receipt.update(state="complete", removed=sorted(removed), reclaimed_bytes=reclaimed,
                   dependency_disposition="retained: shared/unregistered consumers not proven absent")
    _write(index_dir, receipt)
    return receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_migration(args.verify), sort_keys=True))
