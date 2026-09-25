"""Wave 1yzd0 move (M) mutation probe (AC-7).

Each mutant changes one mechanism in a scratch copy of the scripts tree and
must be killed by an assertion (``failures=``), not only by an import error.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
SCRIPTS = REPO / ".wavefoundry/framework/scripts"
PY = Path.home() / ".wavefoundry/venv/bin/python"
IMPL = "wf_server/server_impl.py"
MUTANTS = [
    # (label, file, old, new, test modules)
    ("scripts root is the package directory", IMPL,
     "SCRIPTS_DIR = Path(__file__).resolve().parent.parent", "SCRIPTS_DIR = Path(__file__).resolve().parent",
     ["test_server_package"]),
    ("harness coherence reads the flat alias", IMPL,
     'for src_path in (SCRIPTS_DIR / "server.py", Path(__file__).resolve()):',
     'for src_path in (SCRIPTS_DIR / "server.py", SCRIPTS_DIR / "server_impl.py"):',
     ["test_server_package"]),
    ("harness coherence drops server.py", IMPL,
     'for src_path in (SCRIPTS_DIR / "server.py", Path(__file__).resolve()):',
     'for src_path in (Path(__file__).resolve(),):',
     ["test_server_package"]),
    ("purge skips the package keys", IMPL,
     "        or _wll_key in _PACKAGE_PURGE_KEYS\n", "",
     ["test_lifecycle_gates_structure"]),
    ("purge evicts server_impl too", IMPL,
     '    if flat != "server_impl"\n', "",
     ["test_lifecycle_gates_structure"]),
    ("purge keys only the flat spelling", IMPL,
     "    for key in (flat, canonical)\n", "    for key in (flat,)\n",
     ["test_lifecycle_gates_structure"]),
    ("no eager alias registration", IMPL,
     "        sys.modules[_flat_name] = importlib.import_module(_canonical_name)\n",
     "        pass\n",
     ["test_server_package"]),
    ("eager registration unguarded", IMPL,
     'if __name__ == "wf_server.server_impl":\n    for _flat_name', 'if True:\n    for _flat_name',
     ["test_server_package"]),
    ("registry imported with the stale from-form", IMPL,
     "import wf_server.mcp_tool_registry as mcp_tool_registry  # tool registry",
     "from wf_server import mcp_tool_registry  # tool registry",
     ["test_mcp_tool_registry"]),
    ("version read beside the package", IMPL,
     "    scripts_dir = scripts_dir or SCRIPTS_DIR\n    version_path",
     "    scripts_dir = scripts_dir or Path(__file__).resolve().parent\n    version_path",
     ["test_server_package"]),
    ("default template read beside the package", IMPL,
     'candidates.append(SCRIPTS_DIR.parent / "install" / "plan-template.md")',
     'candidates.append(Path(__file__).resolve().parent.parent / "install" / "plan-template.md")',
     ["test_server_package"]),
    ("chunker version read beside the package", IMPL,
     '    chunker_path = SCRIPTS_DIR / "chunker.py"\n    try:',
     '    chunker_path = Path(__file__).resolve().parent / "chunker.py"\n    try:',
     ["test_server_package"]),
    ("upgrade sentinel inserts the package directory", "wf_server/upgrade_handlers.py",
     "    _scripts_dir = str(server_impl.SCRIPTS_DIR)\n    if _scripts_dir not in sys.path:\n        sys.path.insert(0, _scripts_dir)\n    try:\n        import upgrade_wavefoundry as _uw",
     "    _scripts_dir = str(Path(server_impl.__file__).resolve().parent)\n    if _scripts_dir not in sys.path:\n        sys.path.insert(0, _scripts_dir)\n    try:\n        import upgrade_wavefoundry as _uw",
     ["test_server_package"]),
    ("sync surfaces reads its renderer beside the package", "wf_server/docs_handlers.py",
     'script = server_impl.SCRIPTS_DIR / "render_platform_surfaces.py"',
     'script = Path(server_impl.__file__).resolve().parent / "render_platform_surfaces.py"',
     ["test_install_resume_integration"]),
    ("setup identity misses the implementation", "setup_readiness.py",
     "'wf_server/server_impl.py', ", "",
     ["test_server_package"]),
    ("package name not reserved for extensions", "mcp_tool_extensions.py",
     '    "wf_server",\n', "",
     ["test_server_package"]),
    ("helper enumerates aliases as sources", "tests/framework_files.py",
     "    aliases = set() if include_aliases else package_module_names()",
     "    aliases = set()",
     ["test_server_package"]),
    ("helper resolves moved modules to the flat alias", "tests/framework_files.py",
     "        return scripts_dir / PACKAGE_DIR.name / (stem + \".py\")",
     "        return scripts_dir / (stem + \".py\")",
     ["test_server_package"]),
    ("loader returns the hollow module", "tests/test_graph_snapshot_readers.py",
     "    return sys.modules[name]\n", "    return mod\n",
     ["test_server_package"]),
    # Delivery-review round 1 repairs (CODE-DEL-1, RT-DEL-1, RT-DEL-2 / SEC-DEL-1, QA-DEL-1, QA-DEL-3).
    ("dashboard start resolves beside the package", "wf_server/dashboard_handlers.py",
     "        scripts_dir = server_impl.SCRIPTS_DIR\n", "        scripts_dir = Path(server_impl.__file__).resolve().parent\n",
     ["test_server_package"]),
    ("gardener resolves beside the package", "wf_server/docs_handlers.py",
     'script = server_impl.SCRIPTS_DIR / "docs_gardener.py"', 'script = Path(server_impl.__file__).resolve().parent / "docs_gardener.py"',
     ["test_server_package"]),
    ("index build spawn resolves beside the package", "wf_server/index_handlers.py",
     "    scripts_dir = server_impl.SCRIPTS_DIR\n    python_exec", "    scripts_dir = Path(server_impl.__file__).resolve().parent\n    python_exec",
     ["test_server_package"]),
    ("lock-owner indexer path beside the package", "wf_server/index_handlers.py",
     'server_impl.SCRIPTS_DIR / "indexer.py",', 'Path(server_impl.__file__).resolve().parent / "indexer.py",',
     ["test_server_package"]),
    ("upgrade script beside the package", "wf_server/upgrade_handlers.py",
     'upgrade_script = server_impl.SCRIPTS_DIR / "upgrade_wavefoundry.py"',
     'upgrade_script = Path(server_impl.__file__).resolve().parent / "upgrade_wavefoundry.py"',
     ["test_server_package"]),
    ("restored full flat copy accepted", IMPL,
     "        if _flat_file.is_file() and _flat_file.read_text(encoding=\"utf-8\") != (",
     "        if False and _flat_file.read_text(encoding=\"utf-8\") != (",
     ["test_server_package"]),
    ("handler name not reserved for extensions", "mcp_tool_extensions.py",
     '    "graph_handlers",\n', "",
     ["test_server_package"]),
    ("census bypass: renderer pin reads the flat alias", "tests/test_render_platform_surfaces.py",
     '            source = source_path(name).read_text(encoding="utf-8")\n            for symbol in (',
     '            source = self.SCRIPTS.joinpath(name).read_text(encoding="utf-8")\n            for symbol in (',
     ["test_server_package"]),
    ("hollow loader regression", "tests/test_fts_lexical_layer.py",
     "    return sys.modules[name]\n", "    return mod\n",
     ["test_server_package"]),
]


def main() -> int:
    ok = True
    for label, rel, old, new, modules in MUTANTS:
        source = (SCRIPTS / rel).read_text(encoding="utf-8")
        assert source.count(old) == 1, f"{label}: anchor count {source.count(old)}"
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / "framework" / "scripts"
            shutil.copytree(SCRIPTS.parent, scratch.parent,
                            ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json"))
            (scratch / rel).write_text(source.replace(old, new), encoding="utf-8")
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
