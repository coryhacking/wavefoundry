#!/usr/bin/env python3
"""Build/apply the narrowly scoped local ppol memory-staging repair.

This source-repository utility is not an upgrade entrypoint. Its generated kit
repairs two pinned runtime files, then hands control back to the retained CLI
checkpoint. It never edits the migration receipt, checkpoint, or any database.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
import zipfile

VERSION = "1.24.0+ppol"
PACK_SHA256 = "77ca918696b3e481a4287eb253596dee4e84dbef46c98f70eda990eb7287b82a"
FEATURE_SHA256 = "a1b1c8cf99f3e73bda380a791ff169f0586bd01f0a8405ae11369890659552b6"
OLD_HASHES = {
    "sqlite_storage_migration.py": "a42563cc1af4f38a88305ebab3052437e46f75dcc40fdca44d09af3278e65dee",
    "index_state_store.py": "dd08cc7541c3f3da2d00eb7fb87495e850523cb60007d31e8dffd9958faa85c0",
}
RUNNER_HASH = "4f3653a4ed4dfa93229e745ba477ef6f77cc35e3f27bf370f881c7451243afc4"
SCRIPTS = ".wavefoundry/framework/scripts"


class Refused(ValueError):
    """Preconditions did not prove this exact repair safe."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe(path: Path, boundary: Path | None = None) -> Path:
    """Reject redirects inside an owned boundary; allow redirected host ancestors."""
    path = Path(os.path.abspath(path))
    if boundary is None:
        # Explicit locators may live under /tmp aliases or redirected profiles.
        path = path.parent.resolve() / path.name
        boundary = path.parent
    boundary = Path(boundary).resolve()
    try:
        relative = path.relative_to(boundary)
    except ValueError as exc:
        raise Refused(f"Path escapes its ownership boundary: {path}") from exc
    parts = [boundary]
    for name in relative.parts:
        parts.append(parts[-1] / name)
    for part in parts:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise Refused(f"Redirected path is not supported: {part}")
    return path


def identity(path: Path) -> dict:
    info = safe(path).stat()
    return {"device": info.st_dev, "inode": info.st_ino}


def read_json(path: Path, boundary: Path | None = None) -> dict:
    value = json.loads(safe(path, boundary).read_text("utf-8"))
    if not isinstance(value, dict):
        raise Refused(f"Expected a JSON object: {path}")
    return value


def original_files(pack: Path) -> dict[str, bytes]:
    data = safe(pack).read_bytes()
    if digest(data) != PACK_SHA256:
        raise Refused("Package differs from the pinned original ppol archive")
    with zipfile.ZipFile(io.BytesIO(data)) as outer:
        candidates = [name for name in outer.namelist() if name.endswith("wavefoundry-1.24.0.ppol.zip")]
        if len(candidates) != 1:
            raise Refused("Expected exactly one ppol feature archive")
        feature = outer.read(candidates[0])
    if digest(feature) != FEATURE_SHA256:
        raise Refused("Feature archive identity differs")
    with zipfile.ZipFile(io.BytesIO(feature)) as inner:
        result = {name: inner.read(f"{SCRIPTS}/{name}") for name in OLD_HASHES}
    if any(digest(result[name]) != expected for name, expected in OLD_HASHES.items()):
        raise Refused("Original runtime files differ")
    return result


def build_kit(output: Path, pack: Path) -> None:
    original_files(pack)
    source = Path(__file__).resolve()
    payload = {name: (source.parent / name).read_bytes() for name in OLD_HASHES}
    if any(digest(payload[name]) == OLD_HASHES[name] for name in OLD_HASHES):
        raise Refused("Both fixed canonical runtime files must be present before building")
    manifest = {name: digest(data) for name, data in payload.items()}
    output = safe(output)
    # Exclusive creation prevents silently replacing an already distributed kit.
    with output.open("xb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(source.name, source.read_bytes())
        archive.writestr("repair-manifest.json", json.dumps(manifest, indent=2) + "\n")
        for name, data in payload.items():
            archive.writestr(f"fixed/{name}", data)
        archive.writestr("README.txt", "Run with Python 3.11+ outside the target repository.\n"
            "First: python3 -B repair_ppol_memory_staging.py --root TARGET --pack ORIGINAL_PPOL.zip\n"
            "Stop every repository host; an empty discovery list is not proof.\n"
            "Then add --apply --confirm-hosts-stopped. Review the returned exact CLI command.\n"
            "Do not switch packages, delete receipts, copy databases, or restart MCP before recovery.\n"
            "The kit only patches two runtime files and retains original source backups.\n"
            "Resume through the returned --resume-after-memory command (no extraction).\n"
            "Complete the project upgrade-prompt editing pass and docs gate before --cleanup.\n"
            "Retain this kit, original archive, and backups until recovery is verified.\n")


def query(path: Path, sql: str, params: tuple = (), *, boundary: Path | None = None) -> list:
    for suffix in ("", "-wal", "-shm", "-journal"):
        safe(Path(str(path) + suffix), boundary)
    if not path.is_file():
        raise Refused(f"Required database is absent: {path}")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def hosts(root: Path, recorded_pids: list[int]) -> tuple[list, list]:
    scripts = root / SCRIPTS
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("_ppol_repair_migration", scripts / "sqlite_storage_migration.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        running, limits = module.discover_hosts(root)
        for pid in recorded_pids:
            if module._host_is_running(pid):
                running.append({"pid": pid, "kind": "retained coordinator/staging process"})
        return running, limits
    finally:
        sys.path.remove(str(scripts))


def inspect(root: Path, pack: Path, kit: Path) -> dict:
    root = Path(root).resolve()
    kit = Path(kit).resolve()
    originals = original_files(pack)
    manifest = read_json(kit / "repair-manifest.json", kit)
    if set(manifest) != set(OLD_HASHES):
        raise Refused("Repair manifest contains an unexpected file set")
    fixed = {name: safe(kit / "fixed" / name, kit).read_bytes() for name in OLD_HASHES}
    if any(digest(data) != manifest[name] or manifest[name] == OLD_HASHES[name] for name, data in fixed.items()):
        raise Refused("Fixed runtime payload identity differs")
    scripts = root / SCRIPTS
    if safe(scripts.parent / "VERSION", root).read_text("utf-8").strip() != VERSION:
        raise Refused("Only an extracted 1.24.0+ppol installation is supported")
    if digest(safe(scripts / "upgrade_wavefoundry.py", root).read_bytes()) != RUNNER_HASH:
        raise Refused("Installed upgrade runner differs from ppol")
    for name in OLD_HASHES:
        if digest(safe(scripts / name, root).read_bytes()) not in {OLD_HASHES[name], manifest[name]}:
            raise Refused(f"Installed runtime file differs: {name}")
    index = root / ".wavefoundry/index"
    receipt = read_json(index / "sqlite-migration.json", root)
    checkpoint = read_json(root / ".wavefoundry/upgrade-in-progress.json", root)
    migration_id = receipt.get("migration_id", "")
    if (receipt.get("receipt_version") != 2 or receipt.get("kind") != "index_sqlite_schema8"
            or receipt.get("state") != "staged" or not re.fullmatch("[0-9a-f]{32}", str(migration_id))
            or receipt.get("index_dir") != str(index) or receipt.get("root_identity") != identity(root)
            or receipt.get("target_version") != VERSION or receipt.get("pack_sha256") not in {PACK_SHA256, FEATURE_SHA256}
            or receipt.get("source_database") != "legacy"):
        raise Refused("Receipt does not identify the supported staged schema-7 conversion")
    work = safe(index / ("index-migration-" + migration_id), root)
    if receipt.get("work_dir") != work.name or receipt.get("work_identity") != identity(work):
        raise Refused("Owned migration work directory differs")
    source = safe(index / "index-state.sqlite", root)
    if receipt.get("source_sqlite_identity") != identity(source) or (index / "index.sqlite").exists():
        raise Refused("Retained source is not the sole pre-cutover database")
    if query(source, "SELECT value FROM meta WHERE key='store_schema_version'", boundary=root) != [("7",)]:
        raise Refused("Retained source is not schema 7")
    if (checkpoint.get("to_version") != VERSION or checkpoint.get("storage_migration_id") != migration_id
            or checkpoint.get("failed_phase") != "index_update"
            or checkpoint.get("current_phase") not in {"memory_resume_preflight", "awaiting_memory_validation"}):
        raise Refused("Checkpoint is outside this narrowly supported memory repair")
    run_id = checkpoint.get("memory_backfill_run_id")
    if not isinstance(run_id, str) or not run_id or query(index / "memory-state.sqlite",
            "SELECT state FROM memory_backfill_runs WHERE run_id=?", (run_id,), boundary=root) != [("ready_for_index",)]:
        raise Refused("Live memory backfill run is not ready_for_index")
    recorded_pack = checkpoint.get("zip_path")
    if not isinstance(recorded_pack, str) or not Path(recorded_pack).is_absolute():
        raise Refused("Retained checkpoint has no absolute package locator; preserve it for supported recovery")
    # The ordinary MCP path can retain the outer distribution; the CLI
    # path can retain its feature payload. Both are immutable, pinned inputs.
    if digest(safe(Path(recorded_pack)).read_bytes()) not in {PACK_SHA256, FEATURE_SHA256}:
        raise Refused("Retained checkpoint package must still exist and match the original ppol distribution or feature archive")
    recorded_pids = []
    for value in (checkpoint.get("pid"), receipt.get("staging_pid")):
        if type(value) is not int or value <= 0:
            raise Refused("Retained coordinator/staging PID is missing or invalid")
        if value not in recorded_pids:
            recorded_pids.append(value)
    running, limitations = hosts(root, recorded_pids)
    return dict(root=root, originals=originals, fixed=fixed, hosts=running, limitations=limitations,
                migration_id=migration_id, run_id=run_id)


def apply_repair(root: Path, pack: Path, kit: Path, *, apply: bool = False,
                 confirm_hosts_stopped: bool = False) -> dict:
    if apply and not confirm_hosts_stopped:
        raise Refused("Apply requires --confirm-hosts-stopped after stopping all repository hosts")
    checked = inspect(root, pack, kit)
    root = checked["root"]
    if apply and checked["hosts"]:
        raise Refused("Repository hosts are still running: " + json.dumps(checked["hosts"]))
    backup = safe(root / ".wavefoundry/repair-backups/ppol-memory-staging", root)
    if apply:
        backup.mkdir(parents=True, exist_ok=True)
        # Validate all retained backups before the first source replacement.
        for name, data in checked["originals"].items():
            dest = safe(backup / name, root)
            if dest.exists() and dest.read_bytes() != data:
                raise Refused(f"Existing repair backup differs: {name}")
        for name, data in checked["originals"].items():
            dest = safe(backup / name, root)
            if not dest.exists():
                with dest.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
        for name, data in checked["fixed"].items():
            dest = safe(root / SCRIPTS / name, root)
            if dest.read_bytes() == data:
                continue
            fd, temporary = tempfile.mkstemp(prefix=name + ".repair-", dir=dest.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, stat.S_IMODE(dest.stat().st_mode))
                os.replace(temporary, dest)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    base = [sys.executable, "-B", str(root / SCRIPTS / "upgrade_wavefoundry.py"), "--root", str(root)]
    return {"status": "applied" if apply else "dry_run", "migration_id": checked["migration_id"],
            "memory_run_id": checked["run_id"], "hosts": checked["hosts"],
            "discovery_limits": checked["limitations"], "backups": str(backup),
            "command_argv": base + ["--resume-after-memory", "--confirm-hosts-stopped"],
            "cleanup_after_editing_and_docs_gate_argv": base + ["--cleanup", "--confirm-hosts-stopped"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--build-kit", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-hosts-stopped", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.build_kit:
            if args.root or args.apply or args.confirm_hosts_stopped:
                raise Refused("Kit generation cannot also apply a repair")
            build_kit(args.build_kit, args.pack)
            result = {"status": "built", "path": str(args.build_kit), "sha256": digest(args.build_kit.read_bytes())}
        else:
            if args.root is None:
                raise Refused("--root is required for repair inspection/application")
            result = apply_repair(args.root, args.pack, Path(__file__).resolve().parent,
                                  apply=args.apply, confirm_hosts_stopped=args.confirm_hosts_stopped)
        print(json.dumps(result, indent=2))
        return 0
    except (Refused, OSError, ValueError, sqlite3.Error, zipfile.BadZipFile, KeyError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
