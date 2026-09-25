"""Wave 1yzj9 (1yzj8 AC-2) mutation probe: each mutant must fail a test by assertion."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SCRIPTS = REPO / ".wavefoundry/framework/scripts"
PY = Path.home() / ".wavefoundry/venv/bin/python"
V = "wave_lint_lib/wave_validators.py"
C = "wave_lint_lib/constants.py"
TESTS = ["test_docs_lint.SensorPolarityRegistryTests", "test_docs_lint.AdvisoryFirstRulePinTests"]
MUTANTS = [
    ("decided branch dropped", V,
     "            tail = (f\"advisory by recorded decision in wave `{decided}`\" if decided is not None\n"
     "                    else \"a flip to blocking is a recorded change\")",
     "            tail = \"a flip to blocking is a recorded change\""),
    ("decided suffix applied unconditionally", V,
     "            tail = (f\"advisory by recorded decision in wave `{decided}`\" if decided is not None\n"
     "                    else \"a flip to blocking is a recorded change\")",
     "            tail = f\"advisory by recorded decision in wave `{decided}`\""),
    ("flip text left in the decided suffix", V,
     "            tail = (f\"advisory by recorded decision in wave `{decided}`\" if decided is not None",
     "            tail = (f\"advisory by recorded decision in wave `{decided}`; a flip to blocking is a recorded change\" if decided is not None"),
    ("empty-string validation removed", V,
     "        if not isinstance(decided, str) or not decided.strip():",
     "        if not isinstance(decided, str):"),
    ("type validation removed", V,
     "        if not isinstance(decided, str) or not decided.strip():",
     "        if isinstance(decided, str) and not decided.strip():"),
    ("blocking validation removed", V,
     "        if polarity != \"advisory\":\n            raise ValueError(f\"sensor `{sensor_id}` is blocking",
     "        if False:\n            raise ValueError(f\"sensor `{sensor_id}` is blocking"),
    ("validation moved after the findings branch", V,
     "    if \"decided_wave\" in entry:",
     "    if \"decided_wave\" in entry and findings and warnings is not None:"),
    ("registry decided_wave removed", C,
     "    \"ac_asserts_repository_state\": {\"polarity\": \"advisory\", \"introduced_wave\": \"1wur7\",\n"
     "                                    \"decided_wave\": \"1yzj9\"},",
     "    \"ac_asserts_repository_state\": {\"polarity\": \"advisory\", \"introduced_wave\": \"1wur7\"},"),
]


def main() -> int:
    ok = True
    for label, rel, old, new in MUTANTS:
        source = (SCRIPTS / rel).read_text(encoding="utf-8")
        assert source.count(old) == 1, f"{label}: anchor count {source.count(old)}"
        with tempfile.TemporaryDirectory() as temp:
            framework = Path(temp) / "repo copy" / ".wavefoundry" / "framework"
            shutil.copytree(SCRIPTS.parent, framework, ignore=shutil.ignore_patterns("__pycache__", "index", "test-cache.json"))
            shutil.copytree(REPO / "docs", framework.parent.parent / "docs", ignore=shutil.ignore_patterns("waves", "reports"))
            shutil.copy2(REPO / "CHANGELOG.md", framework.parent.parent / "CHANGELOG.md")
            scratch = framework / "scripts"
            (scratch / rel).write_text(source.replace(old, new), encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(scratch), str(scratch / "tests")]), PYTHONDONTWRITEBYTECODE="1")
            run = subprocess.run([str(PY), "-B", "-m", "unittest", *TESTS], cwd=scratch / "tests", env=env,
                                 capture_output=True, text=True, timeout=900)
            tail = [l for l in run.stderr.strip().splitlines() if l.startswith(("FAILED", "OK"))]
            tail = tail[-1] if tail else run.stderr.strip().splitlines()[-1]
            killed = run.returncode != 0 and "failures=" in tail
            ok &= killed
            print(f"{'KILLED' if killed else 'SURVIVED'}: {label}: {tail}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
