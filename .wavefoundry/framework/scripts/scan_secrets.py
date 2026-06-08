#!/usr/bin/env python3
"""Incremental secrets scan module — loaded by indexer.py via importlib.

update_secrets_scan() is the entry point:
  - On full: delegates to check_hardcoded_secrets(scan_all=True, max_workers=N)
  - On incremental: calls check_hardcoded_secrets(files=changed, max_workers=N)
  - Maintains scan-state.json in scan_dir to track scan completeness
  - Forces full re-scan when scan-findings.json is missing (regeneration)
  - Forces full re-scan when scan-rules.toml (framework or project) changes
    (SHA-256 hash stored in scan-state.json; auto-detects rule additions/edits)

Parallelism:
  File scanning uses ProcessPoolExecutor (spawn + initializer) inside
  check_hardcoded_secrets for phase 1 (regex matching). Worker count
  auto-scales by file count, mirroring the graph indexer's tiered scaling
  with P-core awareness on macOS. Override via WAVEFOUNDRY_SCAN_PARALLEL_WORKERS
  (any positive int; 1 disables parallel).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

SCANNER_VERSION = "1"

# Minimum file count before the parallel scan path is engaged (matches
# _PARALLEL_SCAN_THRESHOLD in secrets_validators.py).
_PARALLEL_THRESHOLD = 50
_WORKERS_ENV = "WAVEFOUNDRY_SCAN_PARALLEL_WORKERS"

_PERF_CORE_COUNT_CACHE: int | None = None


def _physical_perf_core_count() -> int | None:
    """Return performance-core count on macOS Apple Silicon, or None elsewhere."""
    global _PERF_CORE_COUNT_CACHE
    if _PERF_CORE_COUNT_CACHE is not None:
        return _PERF_CORE_COUNT_CACHE
    if sys.platform != "darwin":
        return None
    try:
        import subprocess as _sp
        result = _sp.run(
            ["sysctl", "-n", "hw.perflevel0.physicalcpu"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            count = int(result.stdout.strip())
            if count > 0:
                _PERF_CORE_COUNT_CACHE = count
                return count
    except Exception:
        pass
    return None


def _cpu_cap() -> int:
    """Worker cap: P-core count on macOS Apple Silicon, cpu//2 on Linux/Windows."""
    p_cores = _physical_perf_core_count()
    if p_cores is not None and p_cores > 0:
        return p_cores
    total = os.cpu_count() or 1
    return max(2, total // 2)


def _auto_max_workers(file_count: int) -> int:
    """Auto-scale worker count by file count, matching graph indexer tiers.

    Tiers (matching graph_indexer._auto_scale_worker_count):
      file_count <  200 → 2 workers
      file_count <  500 → 3 workers
      file_count >= 500 → cpu_cap (P-cores on macOS, cpu//2 on Linux)
    Override via WAVEFOUNDRY_SCAN_PARALLEL_WORKERS (any positive int; 1 disables parallel).
    """
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


_RULES_RELPATHS = (".wavefoundry/scan-rules.toml", "docs/scan-rules.toml")


def _compute_rules_hash(root: Path) -> str:
    """SHA-256 of framework + project scan-rules.toml content (in order).

    A null-byte separator between files prevents collisions where the
    concatenated bytes of two different splits would be identical.
    Missing files contribute nothing (empty bytes + separator).
    """
    h = hashlib.sha256()
    for rel in _RULES_RELPATHS:
        p = root / rel
        h.update(p.read_bytes() if p.exists() else b"")
        h.update(b"\x00")
    return h.hexdigest()


def _scan_state_path(scan_dir: Path) -> Path:
    return scan_dir / "scan-state.json"


def _load_scan_state(scan_dir: Path) -> dict:
    path = _scan_state_path(scan_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_scan_state(scan_dir: Path, state: dict) -> None:
    scan_dir.mkdir(parents=True, exist_ok=True)
    _scan_state_path(scan_dir).write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_secrets_scan(
    *,
    root: Path,
    scan_dir: Path,
    changed: set[str],
    removed: set[str],
    full: bool = False,
    verbose: bool = False,
) -> dict:
    """Incremental secrets scan piggybacking on the indexer's change detection.

    root        — repository root
    scan_dir    — directory for scan-state.json (e.g. .wavefoundry/index/scan/)
    changed     — rel-path set of changed files (from indexer's _detect_changes)
    removed     — rel-path set of removed files
    full        — True when the indexer is doing a full rebuild
    verbose     — emit progress to stdout

    Returns a summary dict.
    """
    scripts_dir = Path(__file__).parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from wave_lint_lib.secrets_validators import check_hardcoded_secrets
    from wave_lint_lib.constants import SCAN_FINDINGS_PATH

    scan_state = _load_scan_state(scan_dir)
    findings_path = root / SCAN_FINDINGS_PATH
    current_rules_hash = _compute_rules_hash(root)
    rules_changed = scan_state.get("rules_hash") != current_rules_hash

    # Force full scan if findings were deleted, scanner version changed, or
    # scan-rules.toml changed (framework or project rules). The hash covers
    # both files so any edit — including a framework upgrade — triggers a
    # full re-scan automatically without any manual intervention.
    if not findings_path.exists() or scan_state.get("scanner_version") != SCANNER_VERSION or rules_changed:
        full = True

    t0 = time.monotonic()

    if full:
        if verbose:
            reason = "rules changed" if rules_changed else "full rebuild"
            print(f"build_index: secrets scan — full ({reason})", flush=True)
        # Use all git-tracked files; auto-scale workers.
        # Pre-counting files for worker scaling not worth the stat overhead on
        # full rebuild — use a conservative default of 4 (capped by cpu_count).
        max_workers = _auto_max_workers(500)  # assume large enough to parallelise
        failures = check_hardcoded_secrets(root, scan_all=True, max_workers=max_workers)
        scan_type = "full"
        files_scanned = -1
    else:
        if not changed and not removed:
            if verbose:
                print("build_index: secrets scan — nothing changed", flush=True)
            return {"files_scanned": 0, "failures": 0, "up_to_date": True}
        if verbose:
            print(
                f"build_index: secrets scan — incremental "
                f"({len(changed)} changed, {len(removed)} removed)",
                flush=True,
            )
        # Pass the specific changed-file set. Removed files are handled by the
        # deleted-file sweep inside check_hardcoded_secrets.
        files = [root / p for p in sorted(changed) if (root / p).is_file()]
        max_workers = _auto_max_workers(len(files))
        failures = check_hardcoded_secrets(root, files=files, max_workers=max_workers)
        scan_type = "incremental"
        files_scanned = len(files)

    elapsed = time.monotonic() - t0
    print(
        f"build_index: secrets scan complete ({scan_type}) — "
        f"{len(failures)} finding(s) in {elapsed:.1f}s",
        flush=True,
    )

    _save_scan_state(scan_dir, {
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scanner_version": SCANNER_VERSION,
        "scan_type": scan_type,
        "files_scanned": files_scanned,
        "rules_hash": current_rules_hash,
    })

    return {
        "files_scanned": files_scanned,
        "failures": len(failures),
        "up_to_date": False,
    }
