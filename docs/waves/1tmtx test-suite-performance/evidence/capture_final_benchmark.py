#!/usr/bin/env python3
"""Post-change benchmark series for wave 1tmtx / 1tm6d (Requirement 11 / AC-6).

Frozen final source: one uncounted warm-up plus three timed `--no-cache`
complete runs of the unchanged canonical invocation, external
invocation-to-exit monotonic seconds. Compares the median against the
original-source baseline (baseline.json, median 216.665 s) for the
Requirement 12 verdict. Output: benchmark_final.json, logs/final-*.log.
"""

import datetime
import hashlib
import json
import re
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


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def main() -> int:
    held, holder = rt._probe_index_build_lock()
    if held:
        raise SystemExit(f"ABORT: index build lock held by {holder}")
    LOGS.mkdir(exist_ok=True)
    digest = rt._hash_inputs()
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
        (LOGS / f"final-{label}.log").write_text(out, encoding="utf-8")
        ran = re.search(r"Ran (\d+) tests across (\d+) files in ([\d.]+)s", out)
        svc = re.search(r"Worker service time: ([\d.]+)s across (\d+) files; skipped (\d+) tests", out)
        runs.append({
            "label": label, "external_s": round(dt, 3), "returncode": proc.returncode,
            "ok": bool(re.search(r"^OK$", out, re.MULTILINE)),
            "tests": int(ran.group(1)) if ran else None,
            "files": int(ran.group(2)) if ran else None,
            "internal_worker_phase_s": float(ran.group(3)) if ran else None,
            "service_time_s": float(svc.group(1)) if svc else None,
            "skipped": int(svc.group(3)) if svc else None,
        })
        log(f"{label}: external={dt:.1f}s rc={proc.returncode} tests={runs[-1]['tests']} "
            f"skipped={runs[-1]['skipped']}")
    if rt._hash_inputs() != digest:
        log("SOURCE DIGEST CHANGED during series — invalid")
        return 1
    samples = [r["external_s"] for r in runs if r["label"] != "warmup"]
    baseline = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8"))
    base_median = baseline["median_external_s"]
    median = sorted(samples)[len(samples) // 2]
    improvement = (base_median - median) / base_median * 100.0
    result = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "command": "python3 .wavefoundry/framework/scripts/run_tests.py --no-cache",
        "framework_inputs_hash": digest,
        "runner_sha256": hashlib.sha256((SCRIPTS / "run_tests.py").read_bytes()).hexdigest(),
        "runs": runs,
        "sample_external_s": samples,
        "median_external_s": median,
        "baseline_median_external_s": base_median,
        "improvement_percent": round(improvement, 1),
        "meets_25_percent_target": improvement >= 25.0,
        "all_green": all(r["ok"] and r["returncode"] == 0 for r in runs),
        "new_skips": any((r["skipped"] or 0) > 3 for r in runs),
    }
    (EVIDENCE / "benchmark_final.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    log(f"samples={samples} median={median}s baseline={base_median}s "
        f"improvement={result['improvement_percent']}% "
        f"target_met={result['meets_25_percent_target']} all_green={result['all_green']} "
        f"new_skips={result['new_skips']}")
    return 0 if result["all_green"] and not result["new_skips"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
