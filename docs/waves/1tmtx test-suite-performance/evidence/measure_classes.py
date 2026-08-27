#!/usr/bin/env python3
"""Per-class timing measurement for the test_server_tools.py shard design (1tm6d).

Runs every top-level TestCase class of test_server_tools.py as its own
subprocess (``python -m unittest tests.test_server_tools.<Class>``, the
per-class invocation the tests package documents), six at a time, and
records elapsed wall seconds per class. The minimum observed elapsed
approximates the constant per-process import/startup floor; shard balance
uses net = elapsed - floor. Output: class_timings.json.
"""

import ast
import concurrent.futures
import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[3]
SCRIPTS = REPO / ".wavefoundry" / "framework" / "scripts"
TESTS = SCRIPTS / "tests"

sys.path.insert(0, str(SCRIPTS))
import run_tests as rt  # noqa: E402
import subprocess_util  # noqa: E402


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}] {msg}", flush=True)


def class_names() -> list[str]:
    tree = ast.parse((TESTS / "test_server_tools.py").read_text(encoding="utf-8"))
    return [n.name for n in tree.body if isinstance(n, ast.ClassDef)]


def _env() -> dict:
    env = os.environ.copy()
    env["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
    env.setdefault("WAVEFOUNDRY_EMBED_PROVIDER", "cpu")
    env.setdefault("WAVEFOUNDRY_DISABLE_RERANKER", "1")
    return subprocess_util.utf8_child_env(env)


def measure(cls: str) -> dict:
    t0 = time.monotonic()
    proc = subprocess.run(
        [rt._test_runner_python(), "-B", "-m", "unittest", "-v", f"tests.test_server_tools.{cls}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(SCRIPTS), env=_env(), timeout=600,
    )
    elapsed = time.monotonic() - t0
    out = (proc.stdout or "") + (proc.stderr or "")
    ran = re.search(r"Ran (\d+) tests?", out)
    return {
        "cls": cls,
        "elapsed_s": round(elapsed, 3),
        "returncode": proc.returncode,
        "ran": int(ran.group(1)) if ran else 0,
        "ok": bool(re.search(r"^OK", out, re.MULTILINE)),
    }


def main() -> int:
    held, holder = rt._probe_index_build_lock()
    if held:
        raise SystemExit(f"ABORT: index build lock held by {holder}")
    names = class_names()
    log(f"measuring {len(names)} classes, 6 workers")
    results = []
    t0 = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(measure, c): c for c in names}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            results.append(r)
            done += 1
            if r["returncode"] != 0 or not r["ok"]:
                log(f"  RED {r['cls']} rc={r['returncode']} ran={r['ran']} {r['elapsed_s']}s")
            if done % 40 == 0:
                log(f"  {done}/{len(names)} done")
    wall = time.monotonic() - t0
    results.sort(key=lambda r: -r["elapsed_s"])
    floor = min(r["elapsed_s"] for r in results)
    data = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "wall_s": round(wall, 3),
        "class_count": len(results),
        "total_ran": sum(r["ran"] for r in results),
        "red": [r["cls"] for r in results if r["returncode"] != 0 or not r["ok"]],
        "startup_floor_s": floor,
        "median_elapsed_s": round(statistics.median(r["elapsed_s"] for r in results), 3),
        "sum_net_s": round(sum(max(0.0, r["elapsed_s"] - floor) for r in results), 3),
        "classes": results,
    }
    (EVIDENCE / "class_timings.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    log(f"done: wall={wall:.1f}s total_ran={data['total_ran']} floor={floor}s "
        f"sum_net={data['sum_net_s']}s red={data['red']}")
    for r in results[:12]:
        log(f"  top: {r['cls']} {r['elapsed_s']}s ({r['ran']} tests)")
    return 1 if data["red"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
