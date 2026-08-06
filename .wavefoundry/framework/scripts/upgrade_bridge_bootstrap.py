#!/usr/bin/env python3
"""Standalone stdlib-only protocol-1 -> protocol-2 framework bridge installer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath


PROTOCOL = 2
MINIMUM_SOURCE_VERSION = "1.8.0"
FRAMEWORK_PREFIX = ".wavefoundry/framework/"
PROTOCOL_ARC = FRAMEWORK_PREFIX + "UPGRADE-PROTOCOL.json"
VERSION_ARC = FRAMEWORK_PREFIX + "VERSION"
LIFECYCLE_LOCK = Path(".wavefoundry/lifecycle-mutation.lock")
PUBLICATION_LOCK = Path(".wavefoundry/locks/review-evidence-adoptions.lock")
DASHBOARD_LOCK = Path(".wavefoundry/locks/dashboard-server.lock")
LIFECYCLE_OFFSET = 1 << 30
_SAFE_BUILD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class BridgeError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _lock_owner_hint(path: Path) -> str:
    """Return actionable service metadata for a strict-lock refusal."""

    if path.name != "dashboard-server.lock":
        return ""
    pid: int | None = None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_pid = data.get("pid") if isinstance(data, dict) else None
        pid = raw_pid if isinstance(raw_pid, int) and raw_pid > 0 else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    root = path.parents[2] if len(path.parents) >= 3 else path.parent
    owner = f" (pid {pid})" if pid is not None else ""
    return (
        f"; Wavefoundry dashboard{owner} owns the lifetime lock for {root}. "
        "Run wf_stop_dashboard() for this repository, disconnect/stop its "
        "Wavefoundry MCP hosts, then retry this exact package command"
    )


class _StrictLock:
    def __init__(self, path: Path, offset: int, *, style: str) -> None:
        if style not in {"record", "flock"}:
            raise ValueError(f"unknown lock style: {style}")
        self.path = path
        self.offset = offset
        self.style = style
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                # Match RuntimeFileLock exactly: byte-zero locks need one
                # carrier byte only when the file is empty. High sentinel
                # offsets remain beyond EOF, and a busy-lock probe must never
                # mutate the active owner's persistent metadata.
                if self.offset == 0:
                    self.handle.seek(0)
                    if self.handle.read(1) == b"":
                        self.handle.seek(0)
                        self.handle.write(b"\0")
                        self.handle.flush()
                self.handle.seek(self.offset)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                if self.style == "record":
                    fcntl.lockf(
                        self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB,
                        1, self.offset,
                    )
                else:
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ImportError) as exc:
            self.handle.close()
            self.handle = None
            raise BridgeError(
                f"cannot acquire strict lock {self.path}: {exc}"
                + _lock_owner_hint(self.path)
            ) from exc
        return self

    def __exit__(self, _kind, _value, _traceback):
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(self.offset)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                if self.style == "record":
                    fcntl.lockf(self.handle.fileno(), fcntl.LOCK_UN, 1, self.offset)
                else:
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        name.startswith(FRAMEWORK_PREFIX)
        and not path.is_absolute()
        and ".." not in path.parts
        and name != FRAMEWORK_PREFIX
    )


def _load_selection(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BridgeError(f"upgrade_protocol_invalid: selection metadata unreadable: {exc}") from exc
    required = {
        "schema_version", "bridge_build_id", "upgrade_protocol_version",
        "minimum_runner_protocol", "bridge_archive", "bridge_sha256",
        "feature_archive", "feature_sha256", "minimum_source_version",
        "supported_source_protocol", "feature_release_version",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise BridgeError("upgrade_protocol_invalid: selection metadata has the wrong fields")
    if value["schema_version"] != 1 or value["upgrade_protocol_version"] != PROTOCOL:
        raise BridgeError("upgrade_protocol_invalid: unsupported bridge protocol")
    if value["minimum_runner_protocol"] != PROTOCOL:
        raise BridgeError("upgrade_protocol_invalid: decreasing or malformed protocol floor")
    if value["minimum_source_version"] != MINIMUM_SOURCE_VERSION:
        raise BridgeError("upgrade_protocol_invalid: unsupported bridge minimum source version")
    if value["supported_source_protocol"] != 1:
        raise BridgeError("upgrade_protocol_invalid: unsupported bridge source protocol")
    build_id = value["bridge_build_id"]
    if not isinstance(build_id, str) or _SAFE_BUILD_ID_RE.fullmatch(build_id) is None:
        raise BridgeError(
            "upgrade_protocol_invalid: bridge_build_id must be a bounded ASCII identifier"
        )
    _version_tuple(value["feature_release_version"], field="feature release")
    return value


def _version_tuple(value: object, *, field: str) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise BridgeError(f"upgrade_protocol_invalid: {field} version is missing")
    base = value.split("+", 1)[0].split("-", 1)[0]
    parts = base.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise BridgeError(f"upgrade_protocol_invalid: {field} version is malformed")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _validate_installed_source(current: Path, selection: dict) -> bytes:
    version_path = current / "VERSION"
    try:
        raw_version = version_path.read_bytes()
        installed_version = raw_version.decode("utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise BridgeError(
            f"upgrade_protocol_invalid: installed source version is unavailable: {exc}"
        ) from exc
    installed = _version_tuple(installed_version, field="installed source")
    minimum = _version_tuple(
        selection["minimum_source_version"], field="minimum source"
    )
    feature = _version_tuple(
        selection["feature_release_version"], field="feature release"
    )
    if installed < minimum:
        raise BridgeError(
            "upgrade_protocol_invalid: bridge requires installed source version at least "
            f"{selection['minimum_source_version']}, found {installed_version}; "
            "upgrade to the minimum supported release first"
        )
    if feature <= installed:
        raise BridgeError("upgrade_protocol_invalid: feature release must advance the source")
    protocol_path = current / "UPGRADE-PROTOCOL.json"
    if protocol_path.exists():
        try:
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
            installed_protocol = protocol["upgrade_protocol_version"]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise BridgeError(
                f"upgrade_protocol_invalid: installed protocol metadata is malformed: {exc}"
            ) from exc
        if not isinstance(installed_protocol, int) or isinstance(installed_protocol, bool):
            raise BridgeError("upgrade_protocol_invalid: installed protocol is malformed")
        if installed_protocol >= PROTOCOL:
            raise BridgeError("upgrade_protocol_invalid: source already uses protocol 2")
        if installed_protocol != selection["supported_source_protocol"]:
            raise BridgeError("upgrade_protocol_invalid: unsupported installed source protocol")
    return raw_version


def _resolve_artifact(selection_path: Path, name: object) -> Path:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise BridgeError("upgrade_protocol_invalid: artifact names must be local basenames")
    return selection_path.parent / name


def _safe_wavefoundry_dir(root: Path) -> Path:
    state = root / ".wavefoundry"
    if state.is_symlink() or not state.is_dir():
        raise BridgeError(
            "root_containment_failed: .wavefoundry must be a real directory under the repository root"
        )
    if state.resolve(strict=True).parent != root:
        raise BridgeError("root_containment_failed: .wavefoundry escapes the repository root")
    return state


def _render_command(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _verify_bridge_archive(path: Path, expected_hash: str) -> dict:
    if _sha256(path) != expected_hash:
        raise BridgeError("bridge_integrity_failed: bridge archive hash mismatch")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if not infos or any(not _safe_member(info.filename) for info in infos):
                raise BridgeError("bridge_integrity_failed: bridge contains a project-surface member")
            if any((info.external_attr >> 16) & 0o170000 == 0o120000 for info in infos):
                raise BridgeError("bridge_integrity_failed: bridge may not contain symlinks")
            metadata = json.loads(archive.read(PROTOCOL_ARC).decode("utf-8"))
            if metadata.get("artifact_type") != "bridge" or metadata.get("upgrade_protocol_version") != PROTOCOL:
                raise BridgeError("upgrade_protocol_invalid: bridge metadata mismatch")
            manifest = archive.read(FRAMEWORK_PREFIX + "MANIFEST").decode("utf-8").splitlines()
            actual = {
                info.filename.removeprefix(FRAMEWORK_PREFIX)
                for info in infos
                if info.filename.startswith(FRAMEWORK_PREFIX)
            }
            if set(manifest) != actual:
                raise BridgeError("bridge_integrity_failed: framework MANIFEST is incomplete")
            return metadata
    except (OSError, KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        if isinstance(exc, BridgeError):
            raise
        raise BridgeError(f"bridge_integrity_failed: {exc}") from exc


def _retain_feature_archive(
    wavefoundry_dir: Path,
    feature: Path,
    expected_hash: str,
) -> Path:
    """Keep the selected feature pack available to retained recovery state."""

    assets = wavefoundry_dir / "upgrade-assets"
    if assets.is_symlink() or (assets.exists() and not assets.is_dir()):
        raise BridgeError("root_containment_failed: upgrade-assets must be a real directory")
    assets.mkdir(parents=True, exist_ok=True)
    if assets.resolve(strict=True).parent != wavefoundry_dir:
        raise BridgeError("root_containment_failed: upgrade-assets escapes .wavefoundry")
    retained = assets / feature.name
    if retained.exists():
        if retained.is_symlink() or not retained.is_file() or _sha256(retained) != expected_hash:
            raise BridgeError("bridge_integrity_failed: retained feature archive conflicts")
        return retained
    staged_fd, staged_name = tempfile.mkstemp(
        prefix=f".{feature.name}.tmp-", dir=str(assets)
    )
    staged = Path(staged_name)
    try:
        with os.fdopen(staged_fd, "wb") as target, feature.open("rb") as source:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        if (
            staged.is_symlink()
            or not staged.is_file()
            or staged.resolve(strict=True).parent != assets
            or _sha256(staged) != expected_hash
        ):
            raise BridgeError("bridge_integrity_failed: retained feature archive hash mismatch")
        os.replace(staged, retained)
        if (
            retained.is_symlink()
            or not retained.is_file()
            or retained.resolve(strict=True).parent != assets
            or _sha256(retained) != expected_hash
        ):
            raise BridgeError("bridge_integrity_failed: retained feature archive is not regular and contained")
    finally:
        staged.unlink(missing_ok=True)
    return retained


def install(
    root: Path,
    selection_path: Path | None,
    *,
    hosts_stopped: bool,
    materialize: Callable[[Path], Path] | None = None,
) -> dict:
    if not hosts_stopped:
        raise BridgeError(
            "host_quiescence_required: fully stop dashboard and attached agent/MCP hosts, "
            "then retry with --confirm-hosts-stopped"
        )
    root = root.resolve(strict=True)
    wavefoundry_dir = _safe_wavefoundry_dir(root)
    if (wavefoundry_dir / "upgrade-in-progress.json").exists():
        raise BridgeError("upgrade_in_progress: recover or finish the retained upgrade first")
    with (
        _StrictLock(root / LIFECYCLE_LOCK, LIFECYCLE_OFFSET, style="record"),
        _StrictLock(root / PUBLICATION_LOCK, 0, style="flock"),
        _StrictLock(root / DASHBOARD_LOCK, LIFECYCLE_OFFSET, style="flock"),
    ):
        # Resolve and consume the exact selection/artifacts only after every
        # quiescence/serialization lock is held. A bundle materializer therefore
        # cannot extract its nested payload until the same locks are engaged.
        materialized_root: Path | None = None
        if materialize is not None:
            materialized_root = Path(
                tempfile.mkdtemp(prefix="bridge-payload-", dir=str(wavefoundry_dir))
            )
            try:
                selection_path = materialize(materialized_root)
            except BaseException:
                shutil.rmtree(materialized_root, ignore_errors=True)
                raise
        if selection_path is None:
            raise BridgeError("upgrade_protocol_invalid: selection metadata is missing")
        try:
            selection = _load_selection(selection_path)
            current = wavefoundry_dir / "framework"
            current_version = _validate_installed_source(current, selection)
            bridge = _resolve_artifact(selection_path, selection["bridge_archive"])
            feature = _resolve_artifact(selection_path, selection["feature_archive"])
            if _sha256(feature) != selection["feature_sha256"]:
                raise BridgeError("bridge_integrity_failed: feature archive hash mismatch")
            rollback = wavefoundry_dir / f"framework.rollback-{selection['bridge_build_id']}"
            if rollback.exists():
                raise BridgeError(f"rollback target already exists: {rollback}")
            stage_root = Path(tempfile.mkdtemp(prefix="bridge-stage-", dir=str(wavefoundry_dir)))
        except BaseException:
            if materialized_root is not None:
                shutil.rmtree(materialized_root, ignore_errors=True)
            raise
        moved = False
        try:
            staged_bridge = stage_root / "bridge.zip"
            shutil.copyfile(bridge, staged_bridge)
            metadata = _verify_bridge_archive(
                staged_bridge, str(selection["bridge_sha256"])
            )
            if metadata.get("build_id") != selection["bridge_build_id"]:
                raise BridgeError("upgrade_protocol_invalid: bridge build identity mismatch")
            retained_feature = _retain_feature_archive(
                wavefoundry_dir, feature, str(selection["feature_sha256"])
            )
            incoming = stage_root / ".wavefoundry/framework"
            with zipfile.ZipFile(staged_bridge, "r") as archive:
                for info in archive.infolist():
                    archive.extract(info, stage_root)
            if not incoming.is_dir():
                raise BridgeError("bridge_integrity_failed: framework tree missing after staging")
            (incoming / "VERSION").write_bytes(current_version)
            os.replace(current, rollback)
            moved = True
            os.replace(incoming, current)
            installed = json.loads((current / "UPGRADE-PROTOCOL.json").read_text("utf-8"))
            if installed.get("upgrade_protocol_version") != PROTOCOL:
                raise BridgeError("upgrade_protocol_invalid: installed runner protocol mismatch")
            (current / "BRIDGE-ROLLBACK.json").write_text(
                json.dumps(
                    {
                        "bridge_build_id": selection["bridge_build_id"],
                        "rollback": str(rollback),
                        "hosts_stopped_confirmed": True,
                        "confirmed_at_unix": time.time(),
                        "quiescence_locks": [
                            str(LIFECYCLE_LOCK),
                            str(PUBLICATION_LOCK),
                            str(DASHBOARD_LOCK),
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except BaseException:
            if moved:
                failed = wavefoundry_dir / f"framework.failed-{selection['bridge_build_id']}"
                if current.exists():
                    os.replace(current, failed)
                os.replace(rollback, current)
            raise
        finally:
            shutil.rmtree(stage_root, ignore_errors=True)
            if materialized_root is not None:
                shutil.rmtree(materialized_root, ignore_errors=True)
    next_argv = [
        sys.executable,
        str(root / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"),
        "--root",
        str(root),
        "--pack",
        str(retained_feature),
        "--expected-pack-sha256",
        str(selection["feature_sha256"]),
        "--yes",
    ]
    return {
        "status": "bridge_installed",
        "bridge_build_id": selection["bridge_build_id"],
        "rollback": str(rollback),
        "hosts_stopped_confirmed": True,
        "source_version": current_version.decode("utf-8").strip(),
        "source_protocol": selection["supported_source_protocol"],
        "target_version": selection["feature_release_version"],
        "target_protocol": selection["upgrade_protocol_version"],
        "feature_archive": str(retained_feature),
        "next_argv": next_argv,
        "next_command": _render_command(next_argv),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--confirm-hosts-stopped", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = install(
            Path(args.root), Path(args.selection).resolve(),
            hosts_stopped=args.confirm_hosts_stopped,
        )
    except BridgeError as exc:
        print(json.dumps({"status": "error", "code": str(exc).split(":", 1)[0], "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
