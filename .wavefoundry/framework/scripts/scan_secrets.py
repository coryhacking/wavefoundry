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

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)  # noqa: E402

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
        result = subprocess_util.isolated_run(
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


# Wave 1rsh9 (1rsha): the framework ruleset lives at
# `.wavefoundry/framework/scan-rules.toml` (see wave_lint_lib.constants
# SCAN_RULES_FRAMEWORK_PATH) — the previous first entry
# (`.wavefoundry/scan-rules.toml`) pointed at a path that never exists, so a
# framework-rules change silently failed to trigger the promised full
# re-scan. Fixed alongside the cache's rules fingerprint, which must cover
# the real ruleset. (One-time effect on upgrade: the hash changes → one full
# re-scan.)
_RULES_RELPATHS = (".wavefoundry/framework/scan-rules.toml", "docs/scan-rules.toml")


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


_state_store_mod = None


def _load_state_store():
    """Load index_state_store (wave 1rsh9) — cached, optional (None if absent)."""
    global _state_store_mod
    if _state_store_mod is None:
        import importlib.util
        store_path = Path(__file__).resolve().parent / "index_state_store.py"
        if not store_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("index_state_store", store_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("index_state_store", mod)
        spec.loader.exec_module(mod)
        _state_store_mod = mod
    return _state_store_mod


def _rule_catalog(root: Path) -> dict:
    """Tier-2-ready per-rule hash catalog, derived by parse/hash only (1rsha Req 4).

    Uses the same merged ruleset the scanner runs (framework + project merge,
    disabled-rule filtering) so rule identity matches execution; each rule's
    hash is the SHA-256 of its canonical-JSON dict. No per-rule execution.
    """
    try:
        from wave_lint_lib.secrets_validators import load_merged_ruleset
        rules, _policy, errors = load_merged_ruleset(root)
        if errors:
            return {}
        catalog = {}
        for rule in rules:
            rid = str(rule.get("id") or "")
            if not rid:
                continue
            payload = json.dumps(rule, sort_keys=True, separators=(",", ":"), default=str)
            catalog[rid] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return catalog
    except Exception:
        return {}


def _findings_by_file(root: Path) -> dict:
    """Group current scan-findings.json entries by file (derived refs for cache rows)."""
    try:
        from wave_lint_lib.constants import SCAN_FINDINGS_PATH
        path = root / SCAN_FINDINGS_PATH
        if not path.exists():
            return {}
        entries = json.loads(path.read_text(encoding="utf-8"))
        result: dict = {}
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict) and e.get("file"):
                    ref = {k: e.get(k) for k in ("rule_id", "line", "status") if k in e}
                    result.setdefault(str(e["file"]), []).append(ref)
        return result
    except Exception:
        return {}


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

    # Wave 1rsh9 (1rsha): per-file content+rules scan cache on the index-state
    # store. A skip optimization only — a file is skipped when its content
    # hash AND the rules fingerprint both match its cached row; any cache
    # problem fails toward scanning. mode=full / rules-change / scanner-version
    # escalations bypass the skip (real full scan) and repopulate the cache.
    iss = _load_state_store()
    index_dir = scan_dir.parent if scan_dir.name == "scan" else root / ".wavefoundry" / "index"
    files_skipped = 0
    scanned_rel: list[str] = []
    content_hashes: dict = {}

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
        if iss is not None:
            from wave_lint_lib.secrets_validators import get_scan_files
            scanned_rel = [
                str(p.relative_to(root)).replace("\\", "/")
                for p in get_scan_files(root, True)
            ]
    else:
        if not changed and not removed:
            if verbose:
                print("build_index: secrets scan — nothing changed", flush=True)
            return {"files_scanned": 0, "files_skipped": 0, "failures": 0, "up_to_date": True}
        candidate_rel = [p for p in sorted(changed) if (root / p).is_file()]
        if iss is not None:
            try:
                candidate_rel, files_skipped, content_hashes = iss.secret_scan_filter(
                    index_dir, root, candidate_rel, current_rules_hash
                )
            except Exception as exc:  # noqa: BLE001 - fail toward scanning
                print(f"build_index: secrets scan cache filter skipped ({exc})",
                      file=sys.stderr)
        if verbose:
            print(
                f"build_index: secrets scan — incremental "
                f"({len(candidate_rel)} to scan, {files_skipped} cache-skipped, "
                f"{len(removed)} removed)",
                flush=True,
            )
        # Pass the specific changed-file set. Removed files are handled by the
        # deleted-file sweep inside check_hardcoded_secrets.
        files = [root / p for p in candidate_rel]
        max_workers = _auto_max_workers(len(files))
        failures = check_hardcoded_secrets(root, files=files, max_workers=max_workers)
        scan_type = "incremental"
        files_scanned = len(files)
        scanned_rel = candidate_rel

    if iss is not None and scanned_rel:
        iss.secret_scan_record(
            index_dir,
            root,
            scanned_rel_paths=scanned_rel,
            rules_fingerprint=current_rules_hash,
            findings_by_file=_findings_by_file(root),
            content_hashes=content_hashes,
            removed_rel_paths=sorted(removed or ()),
            rule_catalog=_rule_catalog(root),
        )

    elapsed = time.monotonic() - t0
    print(
        f"build_index: secrets scan complete ({scan_type}) — "
        f"{len(failures)} finding(s), {files_skipped} cache-skipped, in {elapsed:.1f}s",
        flush=True,
    )

    _save_scan_state(scan_dir, {
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scanner_version": SCANNER_VERSION,
        "scan_type": scan_type,
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "rules_change_escalation": rules_changed,
        "rules_hash": current_rules_hash,
    })

    return {
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "rules_change_escalation": rules_changed,
        "failures": len(failures),
        "up_to_date": False,
    }
