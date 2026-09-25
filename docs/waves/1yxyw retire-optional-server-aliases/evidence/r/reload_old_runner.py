"""Wave 1yxyw in-process reload from an older host (AC-3).

A process running an older runner (v1.26.0 and 902f7edc carry full flat
modules; 599039d9 carries the twelve 1yzd0 aliases) builds its server, then the
tree is replaced with the current framework and the ten retired flat files are
removed (what a proven prune leaves), and a probe edit is appended to the
package graph handler. The OLD runner's ``perform_mcp_reload`` must then serve
the edit, and every moved module must have exactly one live module object:
retired flat keys are gone, the package keys are fresh, the two retained flat
keys name the package module, and no separate flat module object the host
loaded (a full flat copy) is still in ``sys.modules``.
"""
import io, json, os, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
PY = str(Path.home() / ".wavefoundry/venv/bin/python")
SOURCES = [a for a in sys.argv[1:]] or ["v1.26.0", "902f7edc", "599039d9"]

_PROCESS = r'''
import json, shutil, sys
from pathlib import Path
scripts, new_scripts, root = (Path(a) for a in sys.argv[1:4])
RETIRED = ("mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
           "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
           "docs_handlers", "context_efficiency_handlers")
RETAINED = ("server_impl", "dashboard_handlers")
sys.path.insert(0, str(scripts))
sys.path.insert(0, str(scripts / "tests"))
from server_tools_support import _make_repo
repo = _make_repo(root)
import server
server.build_server(repo)
# Separate flat module objects (a full flat copy, __name__ == the flat name),
# held by reference so no id can be reused. An alias already names the package
# module, which server_impl's in-place reload keeps by design.
old_flat = {n: sys.modules[n] for n in RETIRED + RETAINED
            if n in sys.modules and sys.modules[n].__name__ == n}
# The upgrade: overwrite with the new tree, prune the retired flat files.
for src in new_scripts.rglob("*"):
    rel = src.relative_to(new_scripts)
    if src.is_file() and "__pycache__" not in rel.parts and rel.parts[0] != "tests":
        (scripts / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, scripts / rel)
for name in RETIRED:
    (scripts / f"{name}.py").unlink(missing_ok=True)
graph = scripts / "wf_server" / "graph_handlers.py"
graph.write_text(graph.read_text() + "\ndef wf_graph_report_response(root, *a, **k):\n"
                 "    return {'status': 'ok', 'data': {'reload_probe': 'served'}}\n")
result = server.perform_mcp_reload()
tool = server._mcp._tool_manager._tools["wf_graph_report"].fn
served = tool()
if isinstance(served, str):
    served = json.loads(served)
package_dir = (scripts / "wf_server").resolve()
live = {}
for name in RETIRED + RETAINED:
    objects = {id(sys.modules[k]) for k in (name, "wf_server." + name) if k in sys.modules}
    module = sys.modules.get("wf_server." + name)
    live[name] = {
        "objects": len(objects),
        "flat_key": name in sys.modules,
        "package_file": bool(module) and Path(module.__file__).resolve().parent == package_dir,
        "old_flat_object_live": name in old_flat and any(m is old_flat[name] for m in sys.modules.values()),
    }
print(json.dumps({"reload_status": result.get("status"), "served": (served.get("data") or {}).get("reload_probe"),
                  "live": live}))
server._get_handler().close()
'''


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory(prefix="wf 1yxyw reload ") as temp:
        work = Path(temp)
        new_scripts = work / "new framework" / "scripts"
        shutil.copytree(REPO / ".wavefoundry/framework/scripts", new_scripts,
                        ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json"))
        for source in SOURCES:
            host = work / f"host {source}"
            host.mkdir()
            archive = subprocess.run(["git", "-C", str(REPO), "archive", source, ".wavefoundry/framework"],
                                     capture_output=True, check=True).stdout
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(host, filter="data")
            scripts = host / ".wavefoundry/framework/scripts"
            repo = work / f"repo {source}"
            repo.mkdir()
            run = subprocess.run([PY, "-B", "-c", _PROCESS, str(scripts), str(new_scripts), str(repo)],
                                 cwd=scripts, capture_output=True, text=True, timeout=900,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            if run.returncode != 0:
                entry = {"error": run.stderr[-3000:]}
                good = False
            else:
                entry = json.loads(run.stdout.strip().splitlines()[-1])
                live = entry["live"]
                good = (entry["reload_status"] == "ok" and entry["served"] == "served"
                        and all(v["objects"] == 1 and v["package_file"] and not v["old_flat_object_live"]
                                for v in live.values())
                        and not any(live[n]["flat_key"] for n in live if n not in ("server_impl", "dashboard_handlers"))
                        and all(live[n]["flat_key"] for n in ("server_impl", "dashboard_handlers")))
            entry["verdict"] = "ok" if good else "FAILED"
            ok &= good
            print(json.dumps({source: entry}, indent=1), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
