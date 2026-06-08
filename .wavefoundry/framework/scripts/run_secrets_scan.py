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

_PARALLEL_THRESHOLD = 50
_WORKERS_ENV = "WAVEFOUNDRY_SCAN_PARALLEL_WORKERS"
_SCAN_STATE_RELPATH = ".wavefoundry/index/scan/scan-state.json"
_RULES_RELPATHS = (".wavefoundry/scan-rules.toml", "docs/scan-rules.toml")


def _physical_perf_core_count() -> int | None:
    if sys.platform != "darwin":
        return None
    try:
        import subprocess as _sp
        r = _sp.run(
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

    scan_all = args.mode == "full" or rules_changed
    files = get_scan_files(root, scan_all)
    max_workers = _auto_max_workers(len(files))
    t0 = time.monotonic()
    failures = check_hardcoded_secrets(root, files=files, max_workers=max_workers)
    _save_rules_hash(root, current_rules_hash)
    print(json.dumps({
        "failures": failures,
        "rules_hash_changed": rules_changed,
        "escalated_to_full": rules_changed and args.mode != "full",
        "elapsed_s": round(time.monotonic() - t0, 3),
    }), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
