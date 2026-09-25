"""Exercise the REAL build_pack.collect_files/write_manifest and upgrade_protocol
module-availability logic against a disposable framework tree with a package.

Nothing in the repository is written: the framework tree is a temp dir; the
repo's scripts are only imported (python -B).
"""
import ast
import json
import sys
import tempfile
from pathlib import Path

REPO_SCRIPTS = Path("/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts")
sys.path.insert(0, str(REPO_SCRIPTS))
import build_pack  # noqa: E402
import upgrade_protocol  # noqa: E402

out = {}
with tempfile.TemporaryDirectory(prefix="wf1yzd0-pack-") as tmp:
    fw = Path(tmp) / "framework with space"
    s = fw / "scripts"
    (s / "wavefoundry_server" / "__pycache__").mkdir(parents=True)
    (s / "tests").mkdir()
    for rel in ("server.py", "server_impl.py", "graph_handlers.py", "upgrade_wavefoundry.py",
                "wavefoundry_server/__init__.py", "wavefoundry_server/server_impl.py",
                "wavefoundry_server/graph_handlers.py", "wavefoundry_server/__pycache__/x.cpython-313.pyc",
                "tests/test_x.py"):
        (s / rel).write_text("# demo\n", encoding="utf-8")
    entries = build_pack.collect_files(fw)
    manifest = build_pack.write_manifest(fw, entries)
    out["collect_files_arcnames"] = sorted(a for _, a in entries)
    out["manifest"] = manifest.read_text().splitlines()
    names = {a for _, a in entries}
    out["upgrade_protocol._pack_module_names"] = sorted(upgrade_protocol._pack_module_names(names))

    def check(src):
        try:
            upgrade_protocol._validate_imports(ast.parse(src), "upgrade_wavefoundry.py",
                                               upgrade_protocol._pack_module_names(names))
            return "accepted"
        except upgrade_protocol.UpgradeProtocolError as exc:
            return f"refused: {exc}"

    out["mandatory_module_function_local_import_server_impl(flat shim present)"] = check(
        "def f():\n    import server_impl\n")
    out["mandatory_module_import_wavefoundry_server_package"] = check(
        "def f():\n    import wavefoundry_server.server_impl\n")
    names_without_shim = {n for n in names if not n.endswith("scripts/server_impl.py")}
    try:
        upgrade_protocol._validate_imports(ast.parse("def f():\n    import server_impl\n"), "upgrade_wavefoundry.py",
                                           upgrade_protocol._pack_module_names(names_without_shim))
        out["mandatory_module_import_server_impl(flat shim ABSENT)"] = "accepted"
    except upgrade_protocol.UpgradeProtocolError as exc:
        out["mandatory_module_import_server_impl(flat shim ABSENT)"] = f"refused: {exc}"
print(json.dumps(out, indent=1))
