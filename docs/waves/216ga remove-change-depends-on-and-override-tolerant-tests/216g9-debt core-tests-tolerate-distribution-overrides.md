# Core-behaviour tests keep running where a distribution overrides the tool they drive

Change ID: `216g9-debt core-tests-tolerate-distribution-overrides`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-20
Wave: 216ga remove-change-depends-on-and-override-tolerant-tests

## Rationale

Waveforge merged `7ab3963d` into their tree and three tests that change 2134w made portable still fail there (X1, X2, X3). Each test drives a core tool that their distribution overrides through `EXTENSION_OVERRIDES` (`mcp_tool_extensions.py`), and the override has different, legitimate rules. Verified at `cd3d2043`:

- **X1** `test_render_agent_surfaces.ChangePromptSkillAndContractTests.test_close_change_states_the_implemented_wf_close_change_contract` compares the rendered prompt's closable statuses with `server_impl._close_change_closable_statuses()`, the core rule. Their `wf_close_change` override closes `active` or `review` only, and their prompt says so.
- **X2** `test_memory_records.MemoryProposeTests.test_registered_manual_pending_candidate_blocks_close_without_source_event` resolves only `EXTENSION_REPLACEMENTS`. Their `wf_close_wave` override requires a container id and refuses the call before the memory gate runs.
- **X3** `test_indexer.OperationalEvidencePolicyTests.test_registered_review_read_and_typed_history_retain_evidence` creates its wave with `parent="group"`. Their `wf_create_wave` override refuses a caller-supplied parent.

Under an override the registered core handler is not reachable from a test (`mcp.core_handler` works only while an extension module registers, and the core close takes no container id), but the core response functions are: `wf_close_wave_response` holds the memory gate X2 asserts, and `wf_create_wave_response` builds X3's fixture.

## Product Intent

- **Distribution maintainers:** a distribution that overrides `wf_close_change`, `wf_close_wave` or `wf_create_wave` gets a green framework suite without editing our tests, and X2 and X3 still check the core memory gate and evidence policy on their tree; the override's own behaviour stays the distribution's to test.
- **This repository:** with no overrides declared, all three tests run and assert exactly what they assert today.

## Requirements

1. Each of the three tests checks `override_targets()` on `sys.modules["mcp_tool_extensions"]`, read at call time after the server module is loaded (the server import evicts and re-imports that module), for the tool it drives:
   - X1: only the rendered-prompt `closable statuses` subtest is skipped when `wf_close_change` is overridden, and the skip message names the tool. The seed and template subtests, and every other clause on the rendered prompt, still run. Waveforge reported the seed and template subtests passing; a distribution that also narrows its template is a stated limit.
   - X2: when `wf_close_wave` is overridden, the close dry run goes through `server_impl.wf_close_wave_response(root, wave_id, mode="dry_run")` instead of the registered tool, with the same `run_validate` patch and the same assertions. The existing `EXTENSION_REPLACEMENTS` resolution stays.
   - X3: when `wf_create_wave` is overridden, the fixture wave is created through `server_impl.wf_create_wave_response(root, "retained-proof", "create", parent="group")` instead of the registered tool. Everything after creation is unchanged.
2. With `EXTENSION_OVERRIDES` empty, as shipped and in every shipped profile, no test skips, the registered tools are used, and each test's assertions are unchanged.

## Scope

**Problem statement:** three core-behaviour tests fail on a distribution whose override of the tool they drive has its own rules.

**In scope:**

- The three tests in `tests/test_render_agent_surfaces.py`, `tests/test_memory_records.py` and `tests/test_indexer.py`.
- One CHANGELOG bullet in the new `[Unreleased]` section.

**Out of scope:**

- Product code, `mcp_tool_extensions.py`, and new extension constants (for example a declared closable set).
- Waveforge's X6 docs failures and the repository scan, which they own.
- Any other test that drives an overridable tool; none has been reported.

**Platform behaviour:** test-only. The same on Windows, macOS, Linux and WSL2.

## Acceptance Criteria

- [x] AC-1: Under the default profile all three tests run with no skip and pass, and each still fails on the known-bad its earlier change named: X1 when the rendered prompt drops `review`; X2 when the memory gate is removed from close; X3 when `is_operational_evidence_path` returns False. Oracle: scratch mutants.
- [x] AC-2: In a scratch copy, with `override_targets()` on the loaded `mcp_tool_extensions` patched to name the driven tool, the registered tool swapped for one that refuses every call, and (for X1) the rendered close-change prompt narrowed to `active` and `review`: X1 skips only the rendered `closable statuses` subtest while its other subtests run and pass; X2 and X3 pass through the core response functions; and X2 still fails when the memory gate is removed from close. Before the fix, the same setup fails X1, X2 and X3. Oracle: the scratch run before and after.
- [x] AC-3: The change's own suites and every test it adds pass, including under `run_tests.py --profile second`; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the override check to the three tests.
- [x] Run the default mutants and the patched-override probe in a scratch copy.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tests      | implementer | —          | three test files |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `.wavefoundry/framework/scripts/tests/test_indexer.py`

## Affected Architecture Docs

N/A. Test-only; no boundary, flow or verification seam changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | No coverage lost in this repository. |
| AC-2 | required | The distribution-facing outcome. |
| AC-3 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-20 | Planned on operator request after the Waveforge note against `7ab3963d`. | Tests and `mcp_tool_extensions.override_targets` read at `cd3d2043`. |
| 2026-10-20 | Readiness round 1: code-reviewer, qa-reviewer, red-team and docs-contract-reviewer PASS, no blockers. Folded in before readying: red-team's alternative (core response functions for X2 and X3, after confirming the memory gate lives in `wf_close_wave_response`); QA's module-identity note (read `override_targets()` on the post-load module); the X1 template limit; the CHANGELOG bullet opens `[Unreleased]`. AC-2 reworded to match. | Readiness lane and seat reports. |
| 2026-10-20 | Implemented. X1: the rendered `closable statuses` subtest calls `skipTest` when `sys.modules["mcp_tool_extensions"].override_targets()` names `wf_close_change`. X2: a local `dry_close()` uses `wf_close_wave_response` when `wf_close_wave` is overridden, for every close call in the test (the AC-2 probe caught a second call after `memory_reconcile` that the first edit missed). X3: the fixture wave is created through `wf_create_wave_response(..., parent="group")` when `wf_create_wave` is overridden. Scratch evidence: default baseline 4 tests OK, no skips; AC-1 mutants (rendered prompt drops `review`, memory gate returns no diagnostics, `is_operational_evidence_path` returns False) each fail their test; AC-2 with the branch forced, registered tools replaced by `None`, and the rendered prompt narrowed to `active`/`review`: 3 tests OK with exactly one skip (the rendered closable subtest), X2 still fails with the gate removed, and the HEAD tests fail under the same setup (X1 failure, X2 and X3 errors). Gapfill: Python mutation driver for scratch edits. | Scratch logs `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/216ga/mutants.log` and `probes2.log`. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-20 | X2 and X3 call the core response function when the driven tool is overridden; X1 skips only its rendered closable subtest. | Red-team readiness: a skip drops core coverage on the distribution for no reason tied to what X2 and X3 test, and the response functions are as cheap. X1's rendered prompt legitimately states the override's rule. | Skip all three (loses coverage); declare the closable set in an extension constant (new mechanism); pass a container id (core close takes none); call `mcp.core_handler` (only works during registration); write X3's fixture records by hand (more code). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The X1 skip hides a real core regression. | It fires only when a distribution declares an override of `wf_close_change`; no shipped profile does, and AC-1 proves the tests still catch their known-bads here. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
