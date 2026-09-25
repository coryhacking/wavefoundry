"""Wave 1yzd0 move/body equivalence (Requirement 10, AC-7).

Compares every top-level definition of each moved module against the E0
commit's flat file. The base source is first rewritten with the documented
mechanical import and scripts-root rewrites; any remaining difference must be
an inventoried adaptation (ALLOWED) or it is reported as UNEXPECTED.
"""
import ast, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
BASE = "2ce2e953"
PREFIX = ".wavefoundry/framework/scripts/"
MOVED = ["server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
         "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
         "dashboard_handlers", "docs_handlers", "context_efficiency_handlers"]
# Inventoried adaptations (readiness inventory A3), by module and definition.
ALLOWED = {
    "server_impl": {"_read_chunker_version", "_load_script", "run_validate", "run_validate_changed",
                    "_audit_harness_coherence", "_default_template", "_indexer_module",
                    "_get_chunker_module", "_read_framework_pack_version",
                    # module-level statements: purge block, alias table, SCRIPTS_DIR,
                    # canonical imports, eager registration
                    "<module statements>"},
}
MECHANICAL = [
    (re.compile(r"^(\s*)import server_impl\s*$", re.M), r"\1from wf_server import server_impl"),
    (re.compile(r"^(\s*)from server_impl import ", re.M), r"\1from wf_server.server_impl import "),
    (re.compile(r"Path\(server_impl\.__file__\)\.resolve\(\)\.parent"), "server_impl.SCRIPTS_DIR"),
]


def definitions(source: str) -> dict[str, str]:
    result, module_statements = {}, []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
        else:
            module_statements.append(ast.dump(node, include_attributes=False))
    result["<module statements>"] = "\n".join(module_statements)
    return result


def main() -> int:
    unexpected = 0
    for name in MOVED:
        base = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:{PREFIX}{name}.py"],
                              capture_output=True, text=True, check=True).stdout
        for pattern, replacement in MECHANICAL:
            base = pattern.sub(replacement, base)
        current = (REPO / PREFIX / "wf_server" / f"{name}.py").read_text(encoding="utf-8")
        before, after = definitions(base), definitions(current)
        changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
        added, removed = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
        allowed = ALLOWED.get(name, set())
        bad = [k for k in changed if k not in allowed] + added + removed
        unexpected += len(bad)
        print(f"{name}: {len(after) - 1} definitions; changed={changed} added={added} removed={removed}"
              + (f" UNEXPECTED={bad}" if bad else ""))
    print("RESULT:", "OK" if unexpected == 0 else f"{unexpected} unexpected differences")
    return 0 if unexpected == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
