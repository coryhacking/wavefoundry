"""Mutation check for wave 1yyoj. Usage: python -B mutants.py .wavefoundry/framework/scripts (scratch copies only)."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
SRC = Path(sys.argv[1])
MUTANTS = {
 "no_reserved_check": ("server_impl.py", "                if name in reserved_names:\n", "                if False:\n", ["test_extension_tool_modules"]),
 "reserved_missing_extractors": ("server_impl.py", '        "_COST_FOCUS_EXTRACTORS": frozenset(_COST_FOCUS_EXTRACTORS),\n', "", ["test_extension_tool_modules"]),
 "overlap_rule_restored": ("mcp_tool_extensions.py", '            problems.append(f"extension prefix {prefix!r} must be a non-empty string")\n', '            problems.append(f"extension prefix {prefix!r} must be a non-empty string")\n        elif any(prefix.startswith(c) or c.startswith(prefix) for c in CORE_TOOL_PREFIXES):\n            problems.append(f"extension prefix {prefix!r} overlaps core prefix")\n', ["test_extension_tool_modules"]),
 "inert_warning_not_routed": ("wave_lint_lib/cli.py", '        _route_sensor_findings("inert_record_layout_config", inert_record_layout_findings(root),\n                               failures, warnings)\n', "", ["test_docs_lint.InertRecordLayoutConfigTests"]),
 "census_derived_collection": ("server_impl.py", None, "\n_MUTANT_DERIVED = frozenset(_COST_EXEMPT_TOOLS) | frozenset(_ARTIFACT_EXTRACTORS)\n", ["test_extension_tool_modules.ReservedNameCensusTests"]),
 "reserved_gains_unserved_name": ("server_impl.py", '_COST_EXEMPT_TOOLS = frozenset({\n', '_COST_EXEMPT_TOOLS = frozenset({\n    "wf_planned_tool",\n', ["test_extension_tool_modules.ReservedNameCensusTests"]),
 # Expected SURVIVOR, documented in the spec and testing architecture: a new collection naming only unserved tools is outside the census.
 "census_unserved_only_collection": ("server_impl.py", None, '\n_MUTANT_PLANNED = frozenset({"wf_planned_tool"})\n', ["test_extension_tool_modules.ReservedNameCensusTests"]),
 "inert_legacy_key_ignored": ("wave_lint_lib/core_validators.py", '    for section in ("wave_implement", "wave_execution"):', '    for section in ("wave_implement",):', ["test_docs_lint.InertRecordLayoutConfigTests"]),
}
for label, (fname, old, new, targets) in MUTANTS.items():
    with tempfile.TemporaryDirectory() as t:
        scr = Path(t) / "scripts"; shutil.copytree(SRC, scr, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        p = scr / fname; s = p.read_text()
        if old is None:
            p.write_text(s + new)
        else:
            assert s.count(old) == 1, label; p.write_text(s.replace(old, new))
        r = subprocess.run([sys.executable, "-B", "-m", "unittest", *targets], cwd=scr / "tests",
            env=dict(os.environ, PYTHONPATH=f"{scr}:{scr/'tests'}", PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True, timeout=900)
        print(f"{label}: rc={r.returncode} {r.stderr.strip().splitlines()[-1]}")
