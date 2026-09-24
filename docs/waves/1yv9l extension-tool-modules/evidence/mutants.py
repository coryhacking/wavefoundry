"""Mutation check for test_extension_tool_modules (wave 1yv9l). Usage: python -B mutants.py .wavefoundry/framework/scripts (scratch copies only)."""
import shutil, subprocess, sys, tempfile, os
from pathlib import Path
SRC = Path(sys.argv[1])
MUTANTS = {
 "no_strip": ("server_impl.py", "        _EXTENSION_PROVENANCE = None\n        _strip_to_runner_tools(mcp)\n        raise", "        _EXTENSION_PROVENANCE = None\n        raise"),
 "no_attempt_record": ("server_impl.py", "            self.wf_attempts.append(name or getattr(fn, \"__name__\", repr(fn)))\n", ""),
 "no_compat": ("server_impl.py", "            if problem:\n                problems.append(problem)", "            pass"),
 "no_ext_guard": ("server_impl.py", "    guarded |= extension_writers\n", ""),
 "roster_no_validate": ("mcp_tool_roster.py", "    mcp_tool_extensions.validate_declaration(\n        core_tools=set(TOOL_TIERS) - RUNNER_TOOLS,\n        runner_tools=RUNNER_TOOLS,\n    )\n", ""),
 "no_location_check": ("server_impl.py", "    if source_path.parent != scripts_dir or source_path.stem != module_name:", "    if False:"),
 "no_async_refusal": ("server_impl.py", "        if getattr(tool, \"is_async\", False) or inspect.iscoroutinefunction(getattr(tool, \"fn\", None)):", "        if False:"),
 "no_unrecorded_check": ("server_impl.py", "        if unrecorded:\n", "        if False:\n"),
 "no_withdrawn_check": ("server_impl.py", "        if withdrawn:\n", "        if False:\n"),
 "no_served_table_check": ("server_impl.py", "        if served_changed:\n", "        if False:\n"),
 "no_schema_preservation": ("server_impl.py", "    if changed:\n        return f\"override {name!r} changes the schema", "    if False:\n        return f\"override {name!r} changes the schema"),
 "title_significant": ("server_impl.py", "_SCHEMA_ANNOTATION_KEYS = frozenset({\"title\", \"description\", \"default\", \"examples\"})", "_SCHEMA_ANNOTATION_KEYS = frozenset({\"description\", \"default\", \"examples\"})"),
 "no_relative_path": ("server_impl.py", "            return Path(path).resolve().relative_to(root.resolve()).as_posix()", "            return path"),
}
for label, (fname, old, new) in MUTANTS.items():
    with tempfile.TemporaryDirectory() as t:
        scr = Path(t)/"scripts"; shutil.copytree(SRC, scr, ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
        p = scr/fname; s = p.read_text(); assert s.count(old)==1, label; p.write_text(s.replace(old,new))
        r = subprocess.run([sys.executable,"-B","-m","unittest","test_extension_tool_modules"], cwd=scr/"tests",
            env=dict(os.environ, PYTHONPATH=f"{scr}:{scr/'tests'}", PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True, timeout=600)
        tail = r.stderr.strip().splitlines()[-1]
        print(f"{label}: rc={r.returncode} {tail}")
