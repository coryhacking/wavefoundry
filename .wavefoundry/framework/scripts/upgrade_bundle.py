#!/usr/bin/env python3
"""Run the protocol bridge and selected feature upgrade from one release zipapp."""

from __future__ import annotations

# Change 1zyv1: no bytecode beside the sources. This file also runs as a member of the
# release upgrade zipapp and as a standalone copied bridge, where ``bytecode_cache`` is not
# importable, so it only disables writes, before any other import, and never caches.
import sys

sys.dont_write_bytecode = True

import argparse
import json
import os
import subprocess
import sys
import zipfile
import tempfile
import hashlib
import shutil
import embedded_model_bundle as envelope
from pathlib import Path, PurePosixPath, PureWindowsPath

import upgrade_bridge_bootstrap
import subprocess_util


PAYLOAD_PREFIX = "payload/"
SELECTION_SUFFIX = ".json"
OUTPUT_LIMIT = 16 * 1024
FEATURE_MEMBER_PREFIX = ".wavefoundry/"
FEATURE_ROOT_MEMBERS = {"install-wavefoundry.md"}


def _safe_artifact_basename(name: object) -> bool:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        return False
    return PurePosixPath(name).name == name and PureWindowsPath(name).name == name


def _safe_payload_name(name: str) -> bool:
    path = PurePosixPath(name)
    leaf = path.name
    return (
        name.startswith(PAYLOAD_PREFIX)
        and not path.is_absolute()
        and ".." not in path.parts
        and len(path.parts) == 2
        and _safe_artifact_basename(leaf)
    )


def _materializer(bundle: Path):
    def materialize(destination: Path) -> Path:
        try:
            with zipfile.ZipFile(bundle, "r") as archive:
                names = [info.filename for info in archive.infolist()]
                allowed_runner = {
                    "__main__.py",
                    "upgrade_bridge_bootstrap.py",
                    "subprocess_util.py",
                    *({"embedded_model_bundle.py"} if "embedded_model_bundle.py" in names else set()),
                }
                allowed_feature = {
                    name
                    for name in names
                    if name.startswith(FEATURE_MEMBER_PREFIX)
                    or name in FEATURE_ROOT_MEMBERS
                }
                declaration = envelope.inspect(archive)
                model_members = {envelope.DESCRIPTOR, declaration["member"]} if declaration else set()
                allowed_payload = {
                    name for name in names if name.startswith(PAYLOAD_PREFIX)
                }
                if len(names) != len(set(names)) or set(names) != (
                    allowed_runner | allowed_feature | allowed_payload
                ):
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle contains an unexpected member"
                    )
                payload = [name for name in names if name.startswith(PAYLOAD_PREFIX) and name not in model_members]
                if (
                    not payload
                    or len(payload) != len(set(payload))
                    or any(not _safe_payload_name(name) for name in payload)
                ):
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle payload paths are malformed"
                    )
                selections = [name for name in payload if name.endswith(SELECTION_SUFFIX)]
                if len(selections) != 1:
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle must contain one selection"
                    )
                selection = json.loads(archive.read(selections[0]).decode("utf-8"))
                if not isinstance(selection, dict):
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle selection must be an object"
                    )
                bridge_name = selection.get("bridge_archive")
                feature_name = selection.get("feature_archive")
                if not all(
                    _safe_artifact_basename(value)
                    for value in (bridge_name, feature_name)
                ):
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: selected artifact names are not local basenames"
                    )
                expected = {
                    selections[0],
                    PAYLOAD_PREFIX + str(bridge_name),
                    PAYLOAD_PREFIX + str(feature_name),
                }
                if set(payload) != expected:
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle payload does not match selection"
                    )
                for name in sorted(expected):
                    target = destination / PurePosixPath(name).name
                    with target.open("xb") as output:
                        envelope.copy_member(archive, archive.getinfo(name), output, limit=envelope.MAX_BUNDLE_BYTES)
                return destination / PurePosixPath(selections[0]).name
        except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
            if isinstance(exc, upgrade_bridge_bootstrap.BridgeError):
                raise
            raise upgrade_bridge_bootstrap.BridgeError(
                f"upgrade_protocol_invalid: bundle is unreadable: {exc}"
            ) from exc

    return materialize


def _bounded(text: str) -> str:
    if len(text) <= OUTPUT_LIMIT:
        return text
    return "…[truncated]…\n" + text[-OUTPUT_LIMIT:]


def _feature_state(root: Path, returncode: int) -> tuple[str, dict]:
    checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
    state: dict = {}
    try:
        parsed = json.loads(checkpoint.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            state = {
                key: parsed[key]
                for key in (
                    "from_version",
                    "to_version",
                    "current_phase",
                    "failed_phase",
                )
                if key in parsed
            }
    except (OSError, UnicodeError, ValueError):
        pass
    if returncode == 0:
        return "primary_phase_complete", state
    if returncode == 4:
        return "awaiting_memory_validation", state
    failed = str(state.get("failed_phase") or "").strip()
    return (f"failed:{failed}" if failed else "failed"), state


def _post_docs_gate_failure(state: object) -> bool:
    """A retained checkpoint whose upgrade failed after the docs gate passed.

    Mirrors ``upgrade_wavefoundry._is_post_docs_gate_failure`` (wave 1zeyo);
    the bundle reads the checkpoint JSON without importing the runner, and a
    parity test pins the two together. Such a lock is recovered by
    ``--resume-after-gate`` rather than a full rerun.
    """
    if not isinstance(state, dict):
        return False
    failed = state.get("failed_phase")
    if failed == "post_docs_gate":
        return True
    return (
        failed == "awaiting_memory_validation"
        and state.get("current_phase") == "docs_gate_complete"
        and not state.get("action_required")
    )


def _recovery(root: Path, bridge: dict, feature_state: str) -> dict:
    runner = root / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"
    if feature_state == "awaiting_memory_validation":
        return {"kind": "continue_index_then_cleanup",
                "instruction": "Continue with wf_upgrade(phase='update_index'), then wf_upgrade(phase='cleanup')."}
    if feature_state == "primary_phase_complete":
        return {
            "kind": "restart_reconcile_then_cleanup",
            "instruction": (
                "Restart every attached agent/MCP host, complete the "
                "reconciliation/editing pass reported by the upgrade, then call "
                "wf_upgrade(phase='cleanup'). After cleanup succeeds, call "
                "wf_upgrade_status and wf_audit."
            ),
        }
    if feature_state == "spawn_failed":
        argv = list(bridge["next_argv"])
        return {
            "kind": "retry_feature_runner",
            "argv": argv,
            "command": upgrade_bridge_bootstrap._render_command(argv),
            "instruction": (
                "Keep every attached host stopped, resolve the process-launch failure, "
                "then have the agent execute the exact recovery argv through its ordinary "
                "non-MCP shell; the operator does not copy or type it. Restart every "
                "attached host only after it completes or returns a retained checkpoint."
            ),
        }
    checkpoint = root / ".wavefoundry" / "upgrade-in-progress.json"
    try:
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        state = {}
    failed = state.get("failed_phase") if isinstance(state, dict) else None
    if failed == "docs_gate" or _post_docs_gate_failure(state):
        argv = [sys.executable, str(runner), "--root", str(root), "--resume-after-gate", "--yes"]
    else:
        argv = list(bridge["next_argv"])
    return {
        "kind": "retained_checkpoint",
        "argv": argv,
        "command": upgrade_bridge_bootstrap._render_command(argv),
        "instruction": (
            "Keep every attached host stopped, resolve the reported failure, then have "
            "the agent execute the exact recovery argv through its ordinary non-MCP "
            "shell; the operator does not copy or type it. Restart every attached host "
            "only after the command completes or returns another retained checkpoint."
        ),
    }


def _incoming_runner(bundle: Path, root: Path, *, dry_run=False):
    """Run current pack code without swapping a protocol-2 installed framework."""
    root = root.resolve(strict=True)
    if (root / ".wavefoundry/upgrade-in-progress.json").exists():
        raise upgrade_bridge_bootstrap.BridgeError("upgrade_in_progress: resume the retained upgrade first")
    retained = None
    stage = Path(tempfile.mkdtemp(prefix="wf-incoming-runner-"))
    try:
        # A preview owns only temporary system storage; no target locks or files.
        if not dry_run:
            from contextlib import ExitStack
            with ExitStack() as locks:
                for relative, offset, style in (
                    (upgrade_bridge_bootstrap.LIFECYCLE_LOCK, upgrade_bridge_bootstrap.LIFECYCLE_OFFSET, "record"),
                    (upgrade_bridge_bootstrap.PUBLICATION_LOCK, 0, "flock"),
                    (upgrade_bridge_bootstrap.DASHBOARD_LOCK, upgrade_bridge_bootstrap.LIFECYCLE_OFFSET, "flock")):
                    locks.enter_context(upgrade_bridge_bootstrap._StrictLock(root / relative, offset, style=style))
                retained = envelope.retain(root, bundle)
            selected = Path(retained["path"])
            expected = retained["sha256"]
        else:
            selected = stage / "preview.zip"
            shutil.copyfile(bundle, selected)
            expected = upgrade_bridge_bootstrap._sha256(selected)
        payload = stage / "payload"
        payload.mkdir()
        selection_path = _materializer(selected)(payload)
        selection = upgrade_bridge_bootstrap._load_selection(selection_path)
        feature = payload / selection["feature_archive"]
        if upgrade_bridge_bootstrap._sha256(feature) != selection["feature_sha256"]:
            raise ValueError("selected feature hash mismatch")
        upgrade_bridge_bootstrap._verify_bridge_archive(payload / selection["bridge_archive"], selection["bridge_sha256"])
        with zipfile.ZipFile(feature) as archive:
            infos = [i for i in archive.infolist() if i.filename.startswith(".wavefoundry/framework/")]
            if sum(i.file_size for i in infos) > envelope.MAX_MEMBER_BYTES:
                raise ValueError("incoming runner exceeds extraction budget")
            for info in infos:
                if not envelope.regular_member(info):
                    raise ValueError("incoming runner contains unsafe member")
                target = stage / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    envelope.copy_member(archive, info, output, limit=64 * 1024 * 1024)
        argv = [sys.executable, "-B", str(stage / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"),
                "--root", str(root), "--pack", str(selected), "--expected-pack-sha256", expected, "--yes"]
        if dry_run:
            argv.append("--dry-run")
        return ({"status": "incoming_runner_ready", "source_version": (root / ".wavefoundry/framework/VERSION").read_text().strip(),
                 "source_protocol": 2, "target_version": selection["feature_release_version"], "target_protocol": 2,
                 "rollback": None, "next_argv": argv, "feature_archive": str(selected)}, stage, retained)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        if retained:
            envelope.cleanup(root, retained)
        raise


def run(bundle: Path, root: Path, *, hosts_stopped: bool, dry_run: bool = False) -> tuple[int, dict]:
    if not hosts_stopped:
        raise upgrade_bridge_bootstrap.BridgeError(
            "host_quiescence_required: fully stop dashboard and attached agent/MCP hosts, "
            "then retry with --confirm-hosts-stopped"
        )
    protocol_path = root / ".wavefoundry/framework/UPGRADE-PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text())["upgrade_protocol_version"] if protocol_path.exists() else 1
    declaration = None
    if bundle.is_file():
        with zipfile.ZipFile(bundle) as archive:
            declaration = envelope.inspect(archive)
    retained = None
    runner_stage = None
    if protocol == 2 or dry_run:
        bridge, runner_stage, retained = _incoming_runner(bundle, root, dry_run=dry_run)
    else:
        bridge = upgrade_bridge_bootstrap.install(
            root, None, hosts_stopped=True, materialize=_materializer(bundle))
        if declaration is not None:
            retained = envelope.retain(root, bundle)
            argv = bridge["next_argv"]
            argv[argv.index("--pack") + 1] = retained["path"]
            argv[argv.index("--expected-pack-sha256") + 1] = retained["sha256"]
    child_env = dict(os.environ)
    child_env.pop(envelope.SOURCE_PROOF_ENV, None)
    if retained is not None:
        child_env[envelope.SOURCE_PROOF_ENV] = json.dumps(retained, sort_keys=True)
    try:
        result = subprocess_util.isolated_run(
            bridge["next_argv"],
            cwd=str(root),
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        if retained is not None:
            bridge["next_argv"] = [sys.executable, "-B", retained["path"], "--root", str(root), "--confirm-hosts-stopped"]
        if runner_stage is not None:
            shutil.rmtree(runner_stage, ignore_errors=True)
        feature_state = "spawn_failed"
        payload = {
            "status": "action_required",
            "source_version": bridge["source_version"],
            "source_protocol": bridge["source_protocol"],
            "target_version": bridge["target_version"],
            "target_protocol": bridge["target_protocol"],
            "bridge_state": bridge["status"],
            "feature_state": feature_state,
            "feature_exit_code": None,
            "rollback": bridge["rollback"],
            "upgrade_log": str(root / ".wavefoundry/logs/upgrade.log"),
            "restart_required": True,
            "checkpoint": {},
            "recovery": _recovery(root, bridge, feature_state),
            "stdout": "",
            "stderr": _bounded(str(exc)),
        }
        return 2, payload
    if runner_stage is not None:
        shutil.rmtree(runner_stage, ignore_errors=True)
        if retained is not None:
            bridge["next_argv"] = [sys.executable, "-B", retained["path"], "--root", str(root), "--confirm-hosts-stopped"]
    if retained is not None:
        checkpoint_path = root / ".wavefoundry/upgrade-in-progress.json"
        try:
            state = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
        except (OSError, ValueError, RecursionError):
            state = {}  # Unreadable recovery authority never authorizes deletion.
        if state is None and result.returncode == 0:
            envelope.cleanup(root, retained)
        elif isinstance(state, dict):
            child_proof = state.get("embedded_source_proof")
            if isinstance(child_proof, dict) and child_proof.get("path") != retained["path"]:
                try:
                    envelope.validate_retained(root, child_proof)
                except (OSError, ValueError):
                    pass
                else:
                    envelope.cleanup(root, retained)
    feature_state, checkpoint = _feature_state(root, result.returncode)
    payload = {
        "status": "ok" if result.returncode == 0 else "action_required",
        "source_version": bridge["source_version"],
        "source_protocol": bridge["source_protocol"],
        "target_version": bridge["target_version"],
        "target_protocol": bridge["target_protocol"],
        "bridge_state": bridge["status"],
        "feature_state": feature_state,
        "feature_exit_code": result.returncode,
        "rollback": bridge["rollback"],
        "upgrade_log": str(root / ".wavefoundry/logs/upgrade.log"),
        "restart_required": True,
        "checkpoint": checkpoint,
        "recovery": _recovery(root, bridge, feature_state),
        "stdout": _bounded(result.stdout or ""),
        "stderr": _bounded(result.stderr or ""),
    }
    return result.returncode, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--confirm-hosts-stopped", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, payload = run(
            Path(sys.argv[0]).resolve(),
            Path(args.root),
            hosts_stopped=args.confirm_hosts_stopped,
            dry_run=args.dry_run,
        )
    except (upgrade_bridge_bootstrap.BridgeError, ValueError, OSError, zipfile.BadZipFile) as exc:
        code = 2
        payload = {
            "status": "error",
            "code": str(exc).split(":", 1)[0],
            "message": str(exc),
            "restart_required": False,
        }
    print(json.dumps(payload, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
