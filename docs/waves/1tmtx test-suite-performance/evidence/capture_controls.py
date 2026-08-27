#!/usr/bin/env python3
"""Schedule-control comparison for wave 1tmtx / 1tm6d (Requirement 4 / AC-7).

On the frozen final file layout: one uncounted `bootstrap` run writes the
digest-bound timing manifest; then counterbalanced candidates run A-T-T-A
(alphabetical, timing, timing, alphabetical) against the byte-identical
manifest on unchanged runner source. External invocation-to-exit monotonic
seconds decide the winner. Output: schedule_controls.json, logs/control-*.log.
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
MANIFEST = EVIDENCE / "timings-manifest.json"

sys.path.insert(0, str(SCRIPTS))
import run_tests as rt  # noqa: E402


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def run_mode(label: str, mode: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        ["python3", str(SCRIPTS / "run_tests.py"),
         "--schedule-control", mode, "--timings-file", str(MANIFEST)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO),
    )
    dt = time.monotonic() - t0
    out = (proc.stdout or "") + (proc.stderr or "")
    (LOGS / f"control-{label}.log").write_text(out, encoding="utf-8")
    ran = re.search(r"Ran (\d+) tests across (\d+) files in ([\d.]+)s", out)
    svc = re.search(r"Worker service time: ([\d.]+)s", out)
    rec = {
        "label": label, "mode": mode, "external_s": round(dt, 3),
        "returncode": proc.returncode, "ok": bool(re.search(r"^OK$", out, re.MULTILINE)),
        "tests": int(ran.group(1)) if ran else None,
        "files": int(ran.group(2)) if ran else None,
        "internal_worker_phase_s": float(ran.group(3)) if ran else None,
        "service_time_s": float(svc.group(1)) if svc else None,
    }
    log(f"{label} ({mode}): external={dt:.1f}s rc={proc.returncode} internal={rec['internal_worker_phase_s']}")
    return rec


def main() -> int:
    held, holder = rt._probe_index_build_lock()
    if held:
        raise SystemExit(f"ABORT: index build lock held by {holder}")
    LOGS.mkdir(exist_ok=True)
    source_digest_before = rt._hash_inputs()
    runner_sha = hashlib.sha256((SCRIPTS / "run_tests.py").read_bytes()).hexdigest()

    boot = run_mode("bootstrap", "bootstrap")
    if boot["returncode"] != 0 or not boot["ok"]:
        log("bootstrap not green; aborting controls")
        return 1
    manifest_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    sequence = [("A1", "alphabetical"), ("T1", "timing"), ("T2", "timing"), ("A2", "alphabetical")]
    runs = [run_mode(label, mode) for label, mode in sequence]
    if hashlib.sha256(MANIFEST.read_bytes()).hexdigest() != manifest_sha:
        log("MANIFEST CHANGED during candidate runs — comparison invalid")
        return 1
    if rt._hash_inputs() != source_digest_before:
        log("SOURCE DIGEST CHANGED during controls — comparison invalid")
        return 1

    alpha = [r["external_s"] for r in runs if r["mode"] == "alphabetical"]
    timing = [r["external_s"] for r in runs if r["mode"] == "timing"]
    winner = "timing" if statistics.mean(timing) < statistics.mean(alpha) else "alphabetical"
    result = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source_digest": source_digest_before,
        "runner_sha256": runner_sha,
        "manifest_sha256": manifest_sha,
        "bootstrap": boot,
        "runs": runs,
        "alphabetical_external_s": alpha,
        "timing_external_s": timing,
        "alphabetical_mean_s": round(statistics.mean(alpha), 3),
        "timing_mean_s": round(statistics.mean(timing), 3),
        "winner": winner,
        "all_green": all(r["ok"] and r["returncode"] == 0 for r in runs),
    }
    (EVIDENCE / "schedule_controls.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    log(f"alphabetical={alpha} mean={result['alphabetical_mean_s']}s | "
        f"timing={timing} mean={result['timing_mean_s']}s | WINNER={winner} "
        f"all_green={result['all_green']}")
    return 0 if result["all_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
