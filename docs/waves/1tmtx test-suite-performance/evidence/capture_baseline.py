#!/usr/bin/env python3
"""Requirement 1 checkpoint capture for wave 1tmtx (change 1tm6d).

Freezes the original-source inventory and captures the external
invocation-to-exit baseline BEFORE any runner edit.

Phases:
  A  freeze  - framework input digest, per-file sha256 digests, per-class
               normalized-AST fingerprints, static (class, test_method)
               identities, environment record
  B  census  - executed per-file test identities and skip counts via one
               6-worker verbose unittest pass (evidence only; not a
               baseline sample)
  C  baseline- one uncounted warm-up plus three timed `--no-cache`
               complete runs of the canonical runner, external
               monotonic invocation-to-exit timing

Outputs (this directory): freeze.json, census.json, baseline.json,
logs/*.log. Invocation: python3 capture_baseline.py  (from any cwd).
"""

import ast
import concurrent.futures
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
SCRIPTS = REPO / ".wavefoundry" / "framework" / "scripts"
TESTS = SCRIPTS / "tests"
LOGS = EVIDENCE / "logs"

sys.path.insert(0, str(SCRIPTS))
import run_tests as rt  # noqa: E402
import subprocess_util  # noqa: E402


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight() -> dict:
    held, holder = rt._probe_index_build_lock()
    if held:
        raise SystemExit(f"ABORT: index build lock held by {holder}")
    dash = subprocess.run(["pgrep", "-f", "dashboard_server"], capture_output=True, text=True)
    if dash.stdout.strip():
        raise SystemExit(f"ABORT: dashboard process running: {dash.stdout.strip()}")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", ".wavefoundry/framework"],
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        raise SystemExit(f"ABORT: framework tree not clean:\n{dirty}")
    return {"git_head": head, "framework_tree_clean": True,
            "index_build_lock_held": False, "dashboard_running": False}


def phase_a_freeze(pre: dict) -> dict:
    test_files = sorted(TESTS.glob("test_*.py"))
    tracked = test_files + [SCRIPTS / "run_tests.py", TESTS / "__init__.py"]
    file_digests = {str(p.relative_to(REPO)): sha256_file(p) for p in tracked}

    fingerprints = {}
    static_identities = []
    for tf in test_files:
        tree = ast.parse(tf.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                dump = ast.dump(node, include_attributes=False)
                fingerprints[f"{tf.name}::{node.name}"] = hashlib.sha256(dump.encode("utf-8")).hexdigest()
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                        static_identities.append([tf.name, node.name, item.name])

    cpu = os.cpu_count() or 4
    freeze = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "preflight": pre,
        "framework_inputs_hash": rt._hash_inputs(),
        "file_digests": file_digests,
        "test_file_count": len(test_files),
        "class_fingerprint_count": len(fingerprints),
        "class_fingerprints": fingerprints,
        "static_identity_count": len(static_identities),
        "static_identities": sorted(static_identities),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "worker_python": rt._test_runner_python(),
            "cpu_count": cpu,
            "workers": min(len(test_files), min(cpu, 6)),
            "wavefoundry_env": {k: v for k, v in os.environ.items() if k.startswith("WAVEFOUNDRY_")},
        },
    }
    (EVIDENCE / "freeze.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"phase A: froze {len(test_files)} files, {len(fingerprints)} class fingerprints, "
        f"{len(static_identities)} static identities, inputs_hash={freeze['framework_inputs_hash'][:16]}...")
    return freeze


def _census_env() -> dict:
    env = os.environ.copy()
    env["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
    env.setdefault("WAVEFOUNDRY_EMBED_PROVIDER", "cpu")
    env.setdefault("WAVEFOUNDRY_DISABLE_RERANKER", "1")
    return subprocess_util.utf8_child_env(env)


_RESULT_LINE = re.compile(r"^(\w+) \(([\w.]+)\)")
_RAN_LINE = re.compile(r"Ran (\d+) tests? in ([\d.]+)s")
_TAIL_LINE = re.compile(r"^(OK|FAILED)\s*(?:\((.*)\))?\s*$", re.MULTILINE)


def _census_one(tf: Path) -> dict:
    env = _census_env()
    t0 = time.monotonic()
    proc = subprocess.run(
        [rt._test_runner_python(), "-B", "-m", "unittest", "discover",
         "-s", str(TESTS), "-p", tf.name, "-v"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(SCRIPTS), env=env, timeout=600,
    )
    elapsed = time.monotonic() - t0
    out = (proc.stdout or "") + (proc.stderr or "")
    ids = sorted({f"{m.group(2)}.{m.group(1)}" for m in map(_RESULT_LINE.match, out.splitlines()) if m})
    ran = _RAN_LINE.search(out)
    tail = _TAIL_LINE.search(out)
    detail = {}
    if tail and tail.group(2):
        for part in tail.group(2).split(","):
            k, _, v = part.strip().partition("=")
            detail[k.strip()] = int(v) if v.isdigit() else v
    return {
        "file": tf.name,
        "returncode": proc.returncode,
        "ran": int(ran.group(1)) if ran else None,
        "unittest_internal_s": float(ran.group(2)) if ran else None,
        "status": tail.group(1) if tail else None,
        "status_detail": detail,
        "skipped": detail.get("skipped", 0),
        "elapsed_s": round(elapsed, 3),
        "id_count": len(ids),
        "ids": ids,
        "output_bytes": len(out),
    }


def phase_b_census() -> dict:
    strays_before = rt.stray_artifact_paths()
    test_files = sorted(TESTS.glob("test_*.py"))
    results = []
    t0 = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, 6)) as ex:
        futures = {ex.submit(_census_one, tf): tf for tf in test_files}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            results.append(r)
            log(f"phase B: {r['file']} ran={r['ran']} skipped={r['skipped']} "
                f"rc={r['returncode']} elapsed={r['elapsed_s']}s")
    wall = time.monotonic() - t0
    results.sort(key=lambda r: r["file"])
    strays_after = rt.stray_artifact_paths()
    new_strays = [p for p in strays_after if p not in strays_before]
    rt._clean_pycache()
    census = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wall_s": round(wall, 3),
        "total_ran": sum(r["ran"] or 0 for r in results),
        "total_skipped": sum(r["skipped"] for r in results),
        "failed_files": [r["file"] for r in results if r["returncode"] != 0],
        "new_stray_artifacts": new_strays,
        "files": results,
    }
    (EVIDENCE / "census.json").write_text(json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"phase B: total ran={census['total_ran']} skipped={census['total_skipped']} "
        f"failed_files={census['failed_files']} wall={census['wall_s']}s new_strays={new_strays}")
    return census


def phase_c_baseline() -> dict:
    LOGS.mkdir(exist_ok=True)
    runs = []
    for label in ["warmup", "sample1", "sample2", "sample3"]:
        log(f"phase C: starting {label}")
        t0 = time.monotonic()
        proc = subprocess.run(
            ["python3", str(SCRIPTS / "run_tests.py"), "--no-cache"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO),
        )
        dt = time.monotonic() - t0
        out = (proc.stdout or "") + (proc.stderr or "")
        (LOGS / f"baseline-{label}.log").write_text(out, encoding="utf-8")
        m = re.search(r"Ran (\d+) tests across (\d+) files in ([\d.]+)s", out)
        runs.append({
            "label": label,
            "external_s": round(dt, 3),
            "returncode": proc.returncode,
            "tests": int(m.group(1)) if m else None,
            "files": int(m.group(2)) if m else None,
            "internal_worker_phase_s": float(m.group(3)) if m else None,
            "ok": bool(re.search(r"^OK$", out, re.MULTILINE)),
        })
        log(f"phase C: {label} external={dt:.1f}s rc={proc.returncode} "
            f"internal={runs[-1]['internal_worker_phase_s']}")
    samples = [r["external_s"] for r in runs if r["label"] != "warmup"]
    baseline = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "command": "python3 .wavefoundry/framework/scripts/run_tests.py --no-cache",
        "metric": "external invocation-to-exit monotonic seconds",
        "runs": runs,
        "sample_external_s": samples,
        "median_external_s": sorted(samples)[len(samples) // 2],
    }
    (EVIDENCE / "baseline.json").write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(f"phase C: samples={samples} median={baseline['median_external_s']}s")
    return baseline


def main() -> int:
    pre = preflight()
    log(f"preflight ok: HEAD={pre['git_head'][:12]}, framework tree clean")
    phase_a_freeze(pre)
    census = phase_b_census()
    if census["failed_files"] or census["new_stray_artifacts"]:
        log("ABORT before baseline: census had failures or stray artifacts")
        return 1
    baseline = phase_c_baseline()
    bad = [r for r in baseline["runs"] if r["returncode"] != 0 or not r["ok"]]
    if bad:
        log(f"BASELINE NOT GREEN: {[r['label'] for r in bad]}")
        return 1
    log("checkpoint capture complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
