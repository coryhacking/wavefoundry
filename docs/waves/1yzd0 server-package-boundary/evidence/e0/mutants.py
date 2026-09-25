"""Wave 1yzd0 E0 mutation probe: each mutant must fail an assertion (failures=),
not an import (errors=). Runs against a scratch copy of the scripts tree."""
import shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
SCRIPTS = REPO / ".wavefoundry/framework/scripts"
PY = Path.home() / ".wavefoundry/venv/bin/python"
MUTANTS = [
    ("no package resolution",
     '    return f"{SERVER_PACKAGE_DIR}/{name}"\n',
     '    return name\n'),
    ("partial package falls back to the alias",
     '    _require((scripts_dir / SERVER_PACKAGE_DIR / name).is_file(), "incomplete_server_package",',
     '    if not (scripts_dir / SERVER_PACKAGE_DIR / name).is_file(): return name\n    _require(True, "incomplete_server_package",'),
    ("digest keyed by implementing path",
     'f"{name}:{modules[name]}" for name in sorted(modules)',
     'f"{paths[name]}:{modules[name]}" for name in sorted(modules)'),
    ("scripts root is server_impl's parent",
     '    return parent.parent if parent.name == SERVER_PACKAGE_DIR else parent\n',
     '    return parent\n'),
    ("match ignores remap",
     'if _normal_path(result.get("path")) != (relevance_paths or {}).get(expected["path"], expected["path"]):',
     'if _normal_path(result.get("path")) != expected["path"]:'),
    ("runner scores without remap",
     'score = score_response(tool, fixture, response, declarations, relevance_paths)',
     'score = score_response(tool, fixture, response, declarations)'),
    ("anchor resolution ignores remap",
     '            path = (relevance_paths or {}).get(target["path"], target["path"])\n',
     '            path = target["path"]\n'),
    ("git binding ignores paths",
     '        relpath = (paths or {}).get(name, name)\n',
     '        relpath = name\n'),
    ("moved table missing a module",
     '    "context_efficiency_handlers.py",\n})',
     '})'),
    ("retained module remapped",
     '    if name not in SERVER_PACKAGE_MODULES or not (scripts_dir / SERVER_PACKAGE_DIR / "__init__.py").is_file():',
     '    if not (scripts_dir / SERVER_PACKAGE_DIR / "__init__.py").is_file():'),
    ("package recognised by its directory",
     'not (scripts_dir / SERVER_PACKAGE_DIR / "__init__.py").is_file():',
     'not (scripts_dir / SERVER_PACKAGE_DIR).is_dir():'),
]

def main() -> int:
    source = (SCRIPTS / "retrieval_eval.py").read_text(encoding="utf-8")
    ok = True
    for label, old, new in MUTANTS:
        assert source.count(old) == 1, f"{label}: anchor not unique"
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / "scripts"
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("__pycache__", "index"))
            (scratch / "retrieval_eval.py").write_text(source.replace(old, new), encoding="utf-8")
            run = subprocess.run([str(PY), "-B", "-m", "unittest", "tests.test_retrieval_eval"],
                                 cwd=scratch, capture_output=True, text=True)
            tail = run.stderr.strip().splitlines()[-1]
            killed = run.returncode != 0 and "failures=" in tail
            ok &= killed
            print(f"{'KILLED' if killed else 'SURVIVED'}: {label}: {tail}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
