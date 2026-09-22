# TechDocs extraction checkpoint

Status: current
Owner: Engineering
Last verified: 2026-09-21

## Scope and result

The approved [inventory](techdocs-inventory.md) moved exactly three functions and two constants. The two public responses use function-local composition-root lookup for retained helpers; the bounded payload helper remains independent. Public reexports, the plain-name reload purge entry, and the named test-owner migrations are implemented. The renderer caller census replaces the former owner exemption instead of retaining both owners, keeping its two-entry contract exact. Memory source and inventory publication remain pending the independent TechDocs checkpoint.

The three moved definitions are AST-identical to baseline commit `f7f95d5ec63a1e30f166f17eebed5d8e95797a54` after normalizing only the approved four qualifications and the inserted local imports. `register_mcp_surface` is byte-identical. The ninety-tool golden and eighty-nine-handler digest fixtures are unchanged. `retrieval_eval.py` is unchanged; no TechDocs definition is reachable from the four measured tools or named by a corpus anchor, per the inventory and readiness closure.

## Verification

Canonical interpreter: `/Users/coryhacking/.wavefoundry/venv/bin/python -B`. All commands use `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`.

- `-m unittest test_handler_modules test_lifecycle_gates_structure test_mcp_tool_registry test_server_tools.TechdocsAuditToolTests test_server_tools.TechdocsBaselineToolTests`: **70 tests passed**, 25.435 seconds. Includes actual scratch reload through registered graph and TechDocs tools, import-derived purge coverage, manifest membership, real audit/renderer producers, exact dry-run byte maps, name-resolution mutants and registry digest parity. Transcript: `/private/tmp/1ymzk-techdocs-focused.log`.
- Complete `test_server_tools`, `test_server_tools_lifecycle`, `test_render_agent_surfaces`, and `test_tool_surface_golden`: **1,031 tests passed**, 178.487 seconds. Transcript: `/private/tmp/1ymzk-techdocs-existing.log`. The actual ninety-tool golden and the sanctioned advisory-site/caller censuses passed unchanged apart from their approved owner migrations.
- `git diff --check`: clean.
- Full framework receipt, combined-wave after evaluation and required delivery review remain coordinator-owned and pending; no closure claim is made here.

## Reproducible equivalence check

Run from the repository root after the TechDocs move and before the memory move. This check uses the immutable Git baseline; only the explicitly permitted qualification and local-import edits are normalized.

```python
import ast
import hashlib
import subprocess
from pathlib import Path

scripts = Path(".wavefoundry/framework/scripts")
old = subprocess.check_output([
    "git", "show", "f7f95d5ec63a1e30f166f17eebed5d8e95797a54:" + str(scripts / "server_impl.py")
]).decode()
current = (scripts / "server_impl.py").read_text()
moved = (scripts / "techdocs_handlers.py").read_text()
def definitions(source):
    return {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
class Normalize(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if (isinstance(node.value, ast.Name) and node.value.id == "server_impl"
                and node.attr in {"_response", "_attach_lint_to_response",
                                  "_trigger_background_index_refresh_for_paths", "McpRepoCache"}):
            return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return self.generic_visit(node)
    def visit_Import(self, node):
        if len(node.names) == 1 and node.names[0].name == "server_impl":
            return None
        return node
before, after = definitions(old), definitions(moved)
assert set(after) == {"_bounded_techdocs_payload", "wf_techdocs_audit_response",
                      "wf_techdocs_baseline_response"}
assert not set(after) & set(definitions(current))
for name, node in after.items():
    assert ast.dump(before[name]) == ast.dump(Normalize().visit(node)), name
registration = ast.get_source_segment(old, before["register_mcp_surface"])
assert registration == ast.get_source_segment(current, definitions(current)["register_mcp_surface"])
print(hashlib.sha256(registration.encode()).hexdigest())
```

SHA-256 values below are reproducible with `hashlib.sha256(path.read_bytes()).hexdigest()`, except registration, which uses the exact UTF-8 source segment in the recipe above.

| Artifact at TechDocs checkpoint | SHA-256 |
| --- | --- |
| Baseline `server_impl.py` | `2ab7e97732dc7491471c4a5c77b3c2b846f684ca8107ecef8ccbad07e0c5c651` |
| Checkpoint `server_impl.py` | `60af022de1c36cea6170e9140aa8215f84f511ba9e282de9ef83f559f4abff13` |
| `techdocs_handlers.py` | `a77d31ec9ece75ced097b5d95425b116e3f5110edf4a1dc5f33767a4acdefed7` |
| Registration segment, before and after | `0a8ed546ca1eb46dfc06967d1994f064612531c61cffd626dffa627ef6486c62` |
| `retrieval_eval.py`, unchanged | `c0ed5e897f874c0b2ff2a447f68bbf0bab1d4b35ca0ed1c6ffc106603f90eb99` |
| `tests/fixtures/tool-surface-golden.json`, unchanged | `2d8dad0a2e4230e856e8b65c2624d78d444e0531780d00ef694d1bf8147f7e4c` |
| `tests/fixtures/register-surface-handler-digests.json`, unchanged | `21c2b156b7461c84d9d63692c1de253832a82069e115547bc3443759e83197d4` |
