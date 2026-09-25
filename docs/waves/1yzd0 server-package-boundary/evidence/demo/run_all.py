"""Run the alias-strategy matrix; write demo/results.json and print a compact table."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_tree  # noqa: E402

PY = sys.executable
RUNS = []
for strategy in ("a", "b", "b2", "c"):
    RUNS.append((strategy, "static", "both", "root", "wavefoundry_server.graph_handlers", "new"))
    RUNS.append((strategy, "reload", "both", "root", "wavefoundry_server.graph_handlers", "new"))
    RUNS.append((strategy, "reload", "flat_only", "root", "wavefoundry_server.graph_handlers", "new"))
    RUNS.append((strategy, "old_runner", "both", "root", "wavefoundry_server.graph_handlers", "old"))
    RUNS.append((strategy, "spec_load", "both", "root", "wavefoundry_server.graph_handlers", "new"))
    RUNS.append((strategy, "consumer", "both", "root", "wavefoundry_server.graph_handlers", "new"))
# strategy (a) with the package-internal import spelled by FLAT name (today's spelling)
RUNS.append(("a", "reload", "flat_only", "root", "graph_handlers", "new"))
RUNS.append(("a", "reload", "both", "root", "graph_handlers", "new"))
# naive root: SCRIPTS_DIR = Path(__file__).parent inside the package
RUNS.append(("a", "naive_root", "both", "naive", "graph_handlers", "new"))
RUNS.append(("a", "naive_root", "both", "naive", "wavefoundry_server.graph_handlers", "new"))

results = []
for strategy, scenario, purge, sdir, himp, initial in RUNS:
    with tempfile.TemporaryDirectory(prefix="wf1yzd0-") as tmp:
        dest = Path(tmp) / "tree with space"
        if initial == "old":
            scripts = build_tree.build(dest, strategy="old", version="v0")
        else:
            scripts = build_tree.build(dest, strategy=strategy, purge=purge, scripts_dir=sdir, version="v1",
                                       handler_import=himp, flat_files=(strategy != "c"))
        proc = subprocess.run([PY, "-B", str(HERE / "probe.py"), str(scripts), scenario, strategy, purge, himp],
                              capture_output=True, text=True, timeout=120, cwd=str(scripts))
        entry = {"strategy": strategy, "scenario": scenario, "purge": purge, "scripts_dir": sdir,
                 "handler_import": himp, "returncode": proc.returncode}
        if proc.returncode == 0 and proc.stdout.strip():
            entry["obs"] = json.loads(proc.stdout.strip().splitlines()[-1])
        else:
            entry["stderr_tail"] = proc.stderr[-2500:]
        results.append(entry)

(HERE / f"results-py{sys.version_info[0]}{sys.version_info[1]}.json").write_text(json.dumps(results, indent=1, sort_keys=True), encoding="utf-8")
for e in results:
    print(f"\n=== strategy={e['strategy']} scenario={e['scenario']} purge={e['purge']} root={e['scripts_dir']} internal_import={e['handler_import']} rc={e['returncode']}")
    if "obs" in e:
        for k, v in e["obs"].items():
            if k in ("scenario", "strategy", "purge"):
                continue
            print(f"   {k}: {v}")
    else:
        print(e["stderr_tail"])
