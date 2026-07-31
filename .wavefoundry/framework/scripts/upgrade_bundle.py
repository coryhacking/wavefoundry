#!/usr/bin/env python3
"""Run the protocol bridge and selected feature upgrade from one release zipapp."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import zipfile
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
                }
                allowed_feature = {
                    name
                    for name in names
                    if name.startswith(FEATURE_MEMBER_PREFIX)
                    or name in FEATURE_ROOT_MEMBERS
                }
                allowed_payload = {
                    name for name in names if name.startswith(PAYLOAD_PREFIX)
                }
                if len(names) != len(set(names)) or set(names) != (
                    allowed_runner | allowed_feature | allowed_payload
                ):
                    raise upgrade_bridge_bootstrap.BridgeError(
                        "upgrade_protocol_invalid: bundle contains an unexpected member"
                    )
                payload = [name for name in names if name.startswith(PAYLOAD_PREFIX)]
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
                    target.write_bytes(archive.read(name))
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
                    "memory_backfill_run_id",
                    "memory_backfill_state",
                    "memory_backfill_pending",
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


def _recovery(root: Path, bridge: dict, feature_state: str) -> dict:
    runner = root / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"
    if feature_state == "awaiting_memory_validation":
        return {
            "kind": "restart_then_resume_memory",
            "instruction": (
                "Restart every attached agent/MCP host, complete the reported memory work, "
                "then call wf_upgrade(phase='resume_after_memory')."
            ),
        }
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
    if failed == "docs_gate":
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


def run(bundle: Path, root: Path, *, hosts_stopped: bool) -> tuple[int, dict]:
    if not hosts_stopped:
        raise upgrade_bridge_bootstrap.BridgeError(
            "host_quiescence_required: fully stop dashboard and attached agent/MCP hosts, "
            "then retry with --confirm-hosts-stopped"
        )
    bridge = upgrade_bridge_bootstrap.install(
        root,
        None,
        hosts_stopped=True,
        materialize=_materializer(bundle),
    )
    try:
        result = subprocess_util.isolated_run(
            bridge["next_argv"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
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
    args = parser.parse_args(argv)
    try:
        code, payload = run(
            Path(sys.argv[0]).resolve(),
            Path(args.root),
            hosts_stopped=args.confirm_hosts_stopped,
        )
    except upgrade_bridge_bootstrap.BridgeError as exc:
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
