# Builder mutant evidence — index extraction

Owner: Engineering
Status: active
Last verified: 2026-09-21

Wave: `1ymzq handler-module-split-three`

This is implementer verification by the same worker that built containment and prepared index test changes. It is **not independent delivery review**.

## Identity omission control

Executed with `/Users/coryhacking/.wavefoundry/venv/bin/python -B` in an isolated temporary copy of the scripts tree. Both runs used `python -B -m unittest discover -s <scratch>/tests -p test_index_handler_identity.py -v`, with `PYTHONPATH=<scratch>` and bytecode disabled. Only the scratch evaluator tuple was mutated; live source and index state were untouched.

| Mechanism | Control or mutation | Observation |
| --- | --- | --- |
| Index handler bytes participate in production identity | Current copied source; test edits its independently copied `index_handlers.py` | One named test passed in 0.036 s; exit 0. |
| Evaluator membership cannot silently disappear | Removed only `"index_handlers.py"` from scratch `PRODUCTION_RETRIEVAL_MODULES`; reran the same test | `IndexHandlerIdentityTests.test_index_handler_edit_moves_production_identity` failed its membership assertion; one failure, zero errors, no skips, exit 1 (0.030 s). |

The normal control additionally verifies that changing the independently copied module changes the production digest. The mutant proves omission is caught rather than dropping the target from the test fixture. Neither run executes a production retrieval benchmark.

## Integration checks

Read current source through MCP first, then used the documented bulk AST/symbol-table inventory fallback. The 53 index function definitions exactly match the settled inventory. At the initial integration check, all eight applied test-patch files AST-matched the intended staging, including preserved optimize-contract assertions and the strengthened public no-build guard covering both namespaces. The timeout constant is read as `server_impl._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS` at call time.

A symbol-table check over index, context-efficiency, docs, dashboard, edit-gate and upgrade handler modules found no unresolved global names or missing referenced server attributes. The index module references 32 existing server attributes. This is static binding evidence, not proof of every runtime branch; parent-owned targeted suites and independent delivery review remain necessary.

## Reviewed bytes

- `index_handlers.py`: SHA256 `b209e36967fe142d66596574da4834b6160d861293f966f85ec2d88afb642fbc`
- `retrieval_eval.py`: SHA256 `25bb941502b84a29c9e8899640dfa2e31e1776218e2554ac881491c1f8d16832`
- `tests/test_index_handler_identity.py`: SHA256 `6c433265d24392ec0b2abb0a54b7aa90247143e28447400c7b9c1b28501799ff`
## Retrieval fixture corrections

The parent-owned focused run exposed eight retrieval failures: three source anchors still scanned the former owner, and five graph tests shared a fixture that patched only the root namespace. The graph fixture now binds the same mock in both namespaces: `_graph_refresh_then_recheck` resolves the index handler owner, while `_graph_refresh_and_resolve` retains the root seam. Its original combined exactly-once assertion remains intact. The three source anchors follow moved definitions; the obsolete-lock-message negative assertion still scans both root and index sources.

The eight tests in `TestGraphToolRefreshOnMiss` plus the three corrected source-anchor tests passed in 1.409 s with cached Python and `-B` (11 total tests, exit 0). Evidence log: `/private/tmp/1ymzq-retrieval-fixed.log`. The temporary extraction census records these four fixture/source-anchor corrections. Production source was unchanged by this repair.
