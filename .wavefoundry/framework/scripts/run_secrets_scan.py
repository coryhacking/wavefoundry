#!/usr/bin/env python3
"""Standalone secrets scan entry point — launched as a subprocess by the MCP server.

Running as a subprocess keeps all ProcessPoolExecutor workers and the
multiprocessing resource_tracker out of the long-running MCP server process.
They exit when this process exits, matching the graph indexer's architecture.

Usage:
    python3 run_secrets_scan.py --root /path/to/repo [--mode full|incremental]

Output: single JSON line on stdout: {"failures": [...]}
Exit code: 0 on success, non-zero on error (stderr gets the traceback).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)  # noqa: E402
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)  # noqa: E402

# Wave 1p8gv: this entry emits a JSON line on stdout the MCP server parses; UTF-8 stdout/stderr (no
# newline translation — cli_stdio only fixes the encoding) keeps non-ASCII from raising on a cp1252
# console without disturbing the JSON framing.
cli_stdio.configure_utf8_stdio()

_PARALLEL_THRESHOLD = 50
_WORKERS_ENV = "WAVEFOUNDRY_SCAN_PARALLEL_WORKERS"
_SCAN_STATE_RELPATH = ".wavefoundry/index/scan/scan-state.json"
# Wave 1rsh9 (1rsha): framework rules live at `.wavefoundry/framework/scan-rules.toml`
# (the previous first entry pointed at a never-existing path, so framework-rules
# changes silently missed the full-re-scan escalation). Kept in sync with
# scan_secrets._RULES_RELPATHS.
_RULES_RELPATHS = (".wavefoundry/framework/scan-rules.toml", "docs/scan-rules.toml")


def _physical_perf_core_count() -> int | None:
    if sys.platform != "darwin":
        return None
    try:
        r = subprocess_util.isolated_run(
            ["sysctl", "-n", "hw.perflevel0.physicalcpu"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            n = int(r.stdout.strip())
            return n if n > 0 else None
    except Exception:
        pass
    return None


def _cpu_cap() -> int:
    p = _physical_perf_core_count()
    if p:
        return p
    return max(2, (os.cpu_count() or 1) // 2)


def _compute_rules_hash(root: Path) -> str:
    h = hashlib.sha256()
    for rel in _RULES_RELPATHS:
        p = root / rel
        h.update(p.read_bytes() if p.exists() else b"")
        h.update(b"\x00")
    return h.hexdigest()


def _load_scan_state(root: Path) -> dict:
    path = root / _SCAN_STATE_RELPATH
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_rules_hash(root: Path, rules_hash: str) -> None:
    """Merge rules_hash into existing scan-state.json without disturbing other fields."""
    path = root / _SCAN_STATE_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        state = {}
    state["rules_hash"] = rules_hash
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _auto_max_workers(file_count: int) -> int:
    env_val = os.environ.get(_WORKERS_ENV)
    if env_val:
        try:
            return max(1, int(env_val))
        except ValueError:
            pass
    if file_count < _PARALLEL_THRESHOLD:
        return 1
    cap = _cpu_cap()
    if file_count < 200:
        return min(2, cap)
    if file_count < 500:
        return min(3, cap)
    return cap


def main() -> int:
    parser = argparse.ArgumentParser(description="Wavefoundry secrets scan subprocess")
    parser.add_argument("--root", required=True, help="Repository root path")
    parser.add_argument(
        "--mode", choices=["full", "incremental"], default="incremental",
        help="full = all tracked files; incremental = git-changed files only",
    )
    args = parser.parse_args()

    root = Path(args.root)
    scripts_dir = Path(__file__).parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from wave_lint_lib.secrets_validators import check_hardcoded_secrets, get_scan_files
    except ImportError as exc:
        print(json.dumps({"error": str(exc), "failures": []}), flush=True)
        return 1

    current_rules_hash = _compute_rules_hash(root)
    scan_state = _load_scan_state(root)
    rules_changed = scan_state.get("rules_hash") != current_rules_hash

    # Wave 1rsh9 (1rsha): the per-file content+rules cache replaces the
    # git-changed-only gate for incremental scans — candidates are ALL tracked
    # files, and the cache's content-addressed skip decides what actually
    # scans (precise across branch switches, whitespace-only touches, and
    # touch-and-revert; decoupled from git status). A rules change makes every
    # cached fingerprint mismatch, preserving the full re-scan escalation by
    # construction (and instrumenting it). --mode full bypasses the skip
    # entirely. Any cache problem fails toward scanning everything.
    scan_all = args.mode == "full" or rules_changed
    files = get_scan_files(root, True)
    rel_paths = [str(p.relative_to(root)).replace("\\", "/") for p in files]
    files_skipped = 0
    content_hashes: dict = {}
    index_dir = root / ".wavefoundry" / "index"
    iss = None
    try:
        import scan_secrets
        iss = scan_secrets._load_state_store()
    except Exception:
        iss = None
    if iss is not None and not scan_all:
        try:
            rel_paths, files_skipped, content_hashes = iss.secret_scan_filter(
                index_dir, root, rel_paths, current_rules_hash
            )
        except Exception as exc:  # noqa: BLE001 - fail toward scanning
            print(f"secrets scan cache filter skipped ({exc})", file=sys.stderr)
    scan_files = [root / p for p in rel_paths]
    max_workers = _auto_max_workers(len(scan_files))
    t0 = time.monotonic()
    failures = check_hardcoded_secrets(root, files=scan_files, max_workers=max_workers)
    if iss is not None and rel_paths:
        try:
            iss.secret_scan_record(
                index_dir,
                root,
                scanned_rel_paths=rel_paths,
                rules_fingerprint=current_rules_hash,
                findings_by_file=scan_secrets._findings_by_file(root),
                content_hashes=content_hashes,
                rule_catalog=scan_secrets._rule_catalog(root),
            )
        except Exception as exc:  # noqa: BLE001 - record failure = re-scan next time
            print(f"secrets scan cache record skipped ({exc})", file=sys.stderr)
    _save_rules_hash(root, current_rules_hash)
    print(json.dumps({
        "failures": failures,
        "files_scanned": len(scan_files),
        "files_skipped": files_skipped,
        "rules_hash_changed": rules_changed,
        "escalated_to_full": rules_changed and args.mode != "full",
        "elapsed_s": round(time.monotonic() - t0, 3),
    }), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
