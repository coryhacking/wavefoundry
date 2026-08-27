#!/usr/bin/env python3
"""Instrumented pre-optimization series for wave 1tmtx (change 1tm6d).

Runs AFTER the telemetry-only runner edit (Task 2) and BEFORE any scheduling
or shard edit. Freezes the instrumented source digests, then executes one
uncounted warm-up plus three timed `--no-cache` complete runs, parsing each
run's per-file telemetry to establish the pre-optimization distribution
(Requirement 11) that feeds the Requirement 12 feasibility gate.

Outputs (this directory): instrumented.json, logs/instrumented-*.log.
"""

import datetime
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
SCRIPTS = REPO / ".wavefoundry" / "framework" / "scripts"
LOGS = EVIDENCE / "logs"

sys.path.insert(0, str(SCRIPTS))
import run_tests as rt  # noqa: E402

_PROGRESS = re.compile(r"^\s*\[\d+/\d+\] (\S+) — (\d+) tests (ok|FAIL) \(([\d.]+)s\)")
_RAN = re.compile(r"Ran (\d+) tests across (\d+) files in ([\d.]+)s")
_SERVICE = re.compile(r"Worker service time: ([\d.]+)s across (\d+) files; skipped (\d+) tests")


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def main() -> int:
    held, holder = rt._probe_index_build_lock()
    if held:
        raise SystemExit(f"ABORT: index build lock held by {holder}")
    LOGS.mkdir(exist_ok=True)

    source_digests = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [SCRIPTS / "run_tests.py", SCRIPTS / "tests" / "test_run_tests_cache.py"]
    }
    inputs_hash = rt._hash_inputs()
    log(f"instrumented source frozen: inputs_hash={inputs_hash[:16]}...")

    runs = []
    for label in ["warmup", "sample1", "sample2", "sample3"]:
        log(f"starting {label}")
        t0 = time.monotonic()
        proc = subprocess.run(
            ["python3", str(SCRIPTS / "run_tests.py"), "--no-cache"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO),
        )
        dt = time.monotonic() - t0
        out = (proc.stdout or "") + (proc.stderr or "")
        (LOGS / f"instrumented-{label}.log").write_text(out, encoding="utf-8")
        per_file = {m.group(1): float(m.group(4))
                    for m in map(_PROGRESS.match, out.splitlines()) if m}
        ran = _RAN.search(out)
        svc = _SERVICE.search(out)
        runs.append({
            "label": label,
            "external_s": round(dt, 3),
            "returncode": proc.returncode,
            "ok": bool(re.search(r"^OK$", out, re.MULTILINE)),
            "tests": int(ran.group(1)) if ran else None,
            "files": int(ran.group(2)) if ran else None,
            "internal_worker_phase_s": float(ran.group(3)) if ran else None,
            "service_time_s": float(svc.group(1)) if svc else None,
            "skipped": int(svc.group(3)) if svc else None,
            "per_file_s": per_file,
        })
        log(f"{label}: external={dt:.1f}s rc={proc.returncode} "
            f"service={runs[-1]['service_time_s']} files_parsed={len(per_file)}")

    samples = [r for r in runs if r["label"] != "warmup"]
    names = set()
    for r in samples:
        names.update(r["per_file_s"])
    per_file_median = {
        n: round(statistics.median([r["per_file_s"][n] for r in samples if n in r["per_file_s"]]), 3)
        for n in sorted(names)
    }
    ext = [r["external_s"] for r in samples]
    result = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "command": "python3 .wavefoundry/framework/scripts/run_tests.py --no-cache",
        "framework_inputs_hash": inputs_hash,
        "source_digests": source_digests,
        "runs": runs,
        "sample_external_s": ext,
        "median_external_s": sorted(ext)[len(ext) // 2],
        "median_service_time_s": round(statistics.median(
            [r["service_time_s"] for r in samples if r["service_time_s"] is not None]), 3),
        "per_file_median_s": per_file_median,
        "slowest_10_median": sorted(per_file_median.items(), key=lambda kv: -kv[1])[:10],
    }
    (EVIDENCE / "instrumented.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bad = [r["label"] for r in runs if r["returncode"] != 0 or not r["ok"]]
    log(f"samples={ext} median={result['median_external_s']}s "
        f"service_median={result['median_service_time_s']}s bad={bad}")
    log("slowest10=" + json.dumps(result["slowest_10_median"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
