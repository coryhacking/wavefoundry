"""Wave 1yxyw removal (R) mutation probe (AC-1, AC-2, AC-3).

Each mutant changes one mechanism in a scratch copy of the framework tree and
must be killed by an assertion (``failures=``), not only by an import error.
A mutant whose ``old`` is None writes ``new`` as a new file at ``rel``.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
SCRIPTS = REPO / ".wavefoundry/framework/scripts"
PY = Path.home() / ".wavefoundry/venv/bin/python"
IMPL = "wf_server/server_impl.py"
EXT = "upgrade_extensions.py"
PKG = ["test_server_package"]
ALIAS = 'import importlib\nimport sys\n\nsys.modules[__name__] = importlib.import_module("wf_server.mcp_tool_registry")\n'
MUTANTS = [
    # (label, file, old, new, test modules)
    ("purge omits the retired flat keys", IMPL,
     "    for flat in (set(_FLAT_ALIASES) | _RETIRED_FLAT_NAMES)\n", "    for flat in set(_FLAT_ALIASES)\n",
     ["test_lifecycle_gates_structure"]),
    ("retired table drops a name", IMPL,
     '"mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",',
     '"mcp_tool_registry", "codenav_handlers", "techdocs_handlers",', PKG),
    ("wf_server_info omits the leftover diagnostic", IMPL,
     "    if leftovers:\n        diagnostics.append(", "    if False:\n        diagnostics.append(", PKG),
    ("server start omits the stderr warning", IMPL,
     'print(f"wavefoundry: WARNING, {_retired_flat_leftover_warning(leftovers)}", file=sys.stderr)', "pass", PKG),
    ("leftover check always reports", IMPL,
     '            if (base / f"{name}.py").is_file():\n', "            if True:\n", PKG),
    ("upgrade hook raises on an unreadable directory", EXT,
     "    except Exception as exc:  # noqa: BLE001 - reporting must never abort the upgrade",
     "    except ValueError as exc:  # noqa: BLE001 - reporting must never abort the upgrade", PKG),
    ("upgrade hook deletes leftovers", EXT,
     "        if leftovers:\n            print(\n                f\"WARNING: retired flat",
     "        for name in leftovers:\n            (scripts / name).unlink()\n"
     "        if leftovers:\n            print(\n                f\"WARNING: retired flat", PKG),
    ("upgrade hook list drops a name", EXT,
     '    "docs_handlers", "context_efficiency_handlers",\n)', '    "docs_handlers",\n)', PKG),
    ("reserved extension names drop a retired name", "mcp_tool_extensions.py",
     '    "graph_handlers",\n', "", PKG),
    ("flat import restored in production", "memory_cli.py",
     "import wf_server.memory_handlers as memory_handlers", "import memory_handlers", PKG),
    ("stale from-form import in production", "memory_cli.py",
     "import wf_server.memory_handlers as memory_handlers", "from wf_server import memory_handlers", PKG),
    ("swallowed hook import reverted", "project_context_efficiency.py",
     "import wf_server.context_efficiency_handlers as context_efficiency_handlers",
     "import context_efficiency_handlers", PKG),
    ("flat patch target restored in a test", "tests/test_sqlite_serving.py",
     '"wf_server.index_handlers._index_build_lock_info"', '"index_handlers._index_build_lock_info"', PKG),
    ("a retired alias file restored", "mcp_tool_registry.py", None, ALIAS, PKG),
]


def main() -> int:
    ok = True
    for label, rel, old, new, modules in MUTANTS:
        if old is not None:
            source = (SCRIPTS / rel).read_text(encoding="utf-8")
            assert source.count(old) == 1, f"{label}: anchor count {source.count(old)}"
        else:
            assert not (SCRIPTS / rel).exists(), f"{label}: {rel} already exists"
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / "framework copy" / "scripts"
            shutil.copytree(SCRIPTS.parent, scratch.parent,
                            ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json"))
            (scratch / rel).write_text(new if old is None else source.replace(old, new), encoding="utf-8")
            # The project runner puts both the scripts root and tests/ on the path.
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(scratch), str(scratch / "tests")]),
                       PYTHONDONTWRITEBYTECODE="1")
            run = subprocess.run([str(PY), "-B", "-m", "unittest", *modules],
                                 cwd=scratch / "tests", env=env, capture_output=True, text=True, timeout=900)
            tail = [l for l in run.stderr.strip().splitlines() if l.startswith(("FAILED", "OK"))]
            tail = tail[-1] if tail else run.stderr.strip().splitlines()[-1]
            killed = run.returncode != 0 and "failures=" in tail
            ok &= killed
            print(f"{'KILLED' if killed else 'SURVIVED'}: {label}: {tail}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
