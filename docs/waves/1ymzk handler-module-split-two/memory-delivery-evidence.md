# Memory extraction checkpoint

Status: current
Owner: Engineering
Last verified: 2026-09-21

## Delivered boundary

The independently reviewed [memory inventory](memory-inventory.md) governs the move: 29 functions and 14 objects relocated, five lifecycle/crediting compositions retained. All 43 moved names are explicitly re-exported and tested for object identity; mutable caches remain shared through those aliases. The loader indirection for memory records remains intact. `memory_cli.py` reaches the new owner directly, while `memory_eval.py` retains its existing handle. Registration bytes and the prior TechDocs source remain unchanged.

The four inventoried mock targets now address the actual owner. Added mock-call assertions ensure the failure-path injection executes. Two-server-instance tests retain their existing behavior assertions and gain an explicit distinct-cache assertion; docstrings now acknowledge the canonical per-call loader and distinguish these fixtures from the retained real child-process tests. No existing assertion was removed or weakened.

The new structure checks pin the five stayers, every re-exported identity, absence of moved source definitions/assignments from the composition root, and absence of forbidden module-top imports. Actual scratch reload now invokes graph, TechDocs and memory through the public registry. The evaluator membership test follows the bounded direct-call closure, verifies meaningful reached methods, checks evaluator attribute reads, and scans every golden corpus anchor.

## Executed verification

All current commands use `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests` and `/Users/coryhacking/.wavefoundry/venv/bin/python -B`. The seven named existing modules run in separate subprocesses, matching the canonical framework runner's isolation model.

| Invocation after `-m unittest` | Result | Transcript |
| --- | --- | --- |
| `test_memory_records` | 217 passed, 7.935 seconds | `/private/tmp/1ymzk-memory-records.log` |
| `test_memory_backfill` | 46 passed, 5.165 seconds | `/private/tmp/1ymzk-memory-backfill.log` |
| `test_handler_modules test_lifecycle_gates_structure test_mcp_tool_registry test_tool_surface_golden` | 61 passed, 24.479 seconds | `/private/tmp/1ymzk-memory-contracts.log` |
| `test_memory_eval` | 25 passed, 4.209 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_storage_upgrade_resume` | 14 passed, 44.738 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_upgrade_wavefoundry` | 530 run, one skipped, 28.442 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_graph_snapshot_readers` | 51 passed, 15.604 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_record_layout_nested` | 18 passed, 6.808 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_lifecycle_golden` | 5 passed, 8.352 seconds | `/private/tmp/1ymzk-memory-remaining.log` |
| `test_phase_gates` | 20 passed, 17.335 seconds | `/private/tmp/1ymzk-memory-remaining.log` |

The seven named memory modules ran 901 tests with one skip and no failures; lifecycle seam suites added 25 passes, and the shared contract group added 61 passes.

All 29 moved function ASTs equal the immutable wave baseline after normalizing only approved qualification and local imports. The complete `register_mcp_surface` source segment is byte-identical (SHA-256 `0a8ed546ca1eb46dfc06967d1994f064612531c61cffd626dffa627ef6486c62`). `git diff --check` passed. Full framework receipt and after-evaluation remain coordinator-owned and pending.

The retained pre-change `/private/tmp/1ymzk-memory-before-canonical.log` reports 217 tests passed in 10.023 seconds, filesystem timestamp 2026-09-21 15:16:44 MDT. The transcript itself has no command/interpreter header, so that historical file alone does not establish its interpreter; the current 217-test run above has an observed canonical-interpreter invocation.

## Failed exploratory run, retained

The first invocation combined `test_handler_modules.HandlerStructureTests`, `test_memory_records`, and `test_memory_backfill` in one interpreter: 264 tests, three failures, 12.526 seconds (`/private/tmp/1ymzk-memory-first.log`). `test_response_size_is_bounded_even_when_failure_text_is_huge` failed the new mock-call assertion: prior reload/second-server fixtures replaced the handler module while the backfill test module retained its earlier imported server object. The two other failures were publication fault-injection tests (`test_receipt_does_not_alias_a_later_unrelated_generation` and `test_setup_retry_recovers_memory_publication_and_refreshes_changed_core`), likewise in the mixed-module run. All three passed with the complete backfill module isolated. No product repair or assertion relaxation was used to turn that run green; its transcript remains evidence of the mixed-process test-harness limitation, not a successful suite receipt. The pre-change mixed invocation was not rerun, so no claim is made that every mixed-run failure predates this extraction.

## Reproduce equivalence and hashes

The following command body reads the immutable baseline and the delivered tree; it can be run using `python -B` from the repository root. File hashes below use `hashlib.sha256(path.read_bytes()).hexdigest()`.

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
moved = (scripts / "memory_handlers.py").read_text()
def definitions(source):
    return {n.name: n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
class Normalize(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if (isinstance(node.value, ast.Name) and node.value.id == "server_impl"
                and node.attr in {"_load_script", "_response", "_graph_snapshot_module",
                                  "_trigger_background_index_refresh_for_paths", "WaveIndex",
                                  "project_state_publication_lock", "list_waves"}):
            return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return self.generic_visit(node)
    def visit_Import(self, node):
        if len(node.names) == 1 and node.names[0].name == "server_impl":
            return None
        return node
before, after = definitions(old), definitions(moved)
assert len(after) == 29
assert not set(after) & set(definitions(current))
for name, node in after.items():
    assert ast.dump(before[name]) == ast.dump(Normalize().visit(node)), name
registration = ast.get_source_segment(old, before["register_mcp_surface"])
assert registration == ast.get_source_segment(current, definitions(current)["register_mcp_surface"])
print(hashlib.sha256(registration.encode()).hexdigest())
```

| Frozen source file | SHA-256 |
| --- | --- |
| `server_impl.py` | `f9ba2a24a5b77e77d8ca0d9aa8ce7a76577435721f6359ef01925b298a8f78f8` |
| `memory_handlers.py` | `e160012ebe7fc7047afeed4c58c5147b2f130bc7b7954451b896d103c3945cd4` |
| `memory_cli.py` | `c8280dd6e4ac1f3ce123182904ac7d1f81056ab4aeb4397bb114a345ae13751f` |
| `techdocs_handlers.py` | `a77d31ec9ece75ced097b5d95425b116e3f5110edf4a1dc5f33767a4acdefed7` |
| `tests/test_handler_modules.py` | `a5573b14f2b956f41d2e152c1770ab8b885de5fdbd03bf60f7bb39a246a2413e` |
| `tests/test_memory_records.py` | `54a916bdb44ddd90de59defb5eca9bc99afe7e31f158f909120a0812aaeccaae` |
| `tests/test_memory_backfill.py` | `ea3c49920b88a11a8601d5976d8be0209f21a6f23caf72d8efbc42daccba7c10` |

## Delivery cycle-1 repair

The first canonical full-suite attempt exposed two additional source-owner migrations, recorded as `CODE-DEL-1` and `QA-DEL-1`. The implementer reproduced the same three assertions failing in six focused tests before repair (`/private/tmp/1ymzk-repair-before.log`), recorded typed `repair_start` for both findings in cycle 1, then changed only the two tests named below.

The record-layout allowlist now locates its exact recovery-message exemption in `memory_handlers.py`. The lock-order census now scans both actual owners and recognizes bare and `server_impl`-qualified lock calls. Its coverage threshold remains `>= 8`; no assertion was weakened. The existing visitor additionally rejects synthetic nested lifecycle locks, both bare and qualified, under the moved owner's qualified publication call.

Reverification command: `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest test_record_layout_census test_server_tools_lifecycle.PublicTypedEventProcessRaceTests.test_lock_order_is_lifecycle_then_publication_structurally`. Result: **6 tests passed in 0.712 seconds**, `/private/tmp/1ymzk-repair-after.log`; `git diff --check` clean. Independent lane reverification and the new full-suite receipt remain separate coordinator-owned steps.

| Repaired test file | SHA-256 via `shasum -a 256` |
| --- | --- |
| `tests/test_record_layout_census.py` | `ed6c7e46ed076a0b0bbce8c69b8ceb17033ecca9969862958b13e61fdca3fc76` |
| `tests/test_server_tools_lifecycle.py` | `77b07bb61745b1e817eade15fd5820c1c11d509c3c563960d903e5796ffefa23` |

The product-file SHA-256 values above are unchanged. The first full-suite attempt is retained at `/private/tmp/1ymzk-full-suite.log`; it is not a green receipt. Its separate dashboard host-permission failures are being handled by the coordinator without product changes.
