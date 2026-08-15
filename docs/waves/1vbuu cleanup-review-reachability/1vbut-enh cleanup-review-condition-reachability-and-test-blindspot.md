# Cleanup review: condition-reachability rule and the test-coverage blind spot

Change ID: `1vbut-enh cleanup-review-condition-reachability-and-test-blindspot`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: 1vbuu cleanup-review-reachability

## Rationale

The first real `/wf-code-cleanup` run (2026-08-15) produced an operator-approved `remove` verdict against `accel_embedder`'s resident-model fallback, and only plan-time verification (wave `1ve3e`) falsified it. The post-mortem isolates two distinct causes, both fixable cheaply and neither a graph defect:

1. **The safety rule covers the wrong reachability class.** Seed 221's `## Maintainability & Dead-Code` block says "Zero static references does NOT mean dead" and lists surfaces invisible to static analysis (registration, reflection, string references, test fixtures, public API). Every item on that list is a **node-reachability** miss: a caller the graph cannot see. The accel branch failed a different way: it HAD a visible caller (the graph reported one, high-confidence), and the removal argument was about **condition reachability**: "the guard `_resolve_clean_onnx() is None` is always false for shipped models." A call graph models node reachability transitively and correctly, but a branch guarded by a sentinel is reachable iff some producer of that sentinel fires, which is a control-flow and data-flow question no `calls` edge carries. The reviewer trusted a docstring's "unreachable" claim over reading `_resolve_clean_onnx`'s two `return None` sites (one for unregistered models, one for a FAILED fetch). The rule needs a second class with its own probe: for a fallback or degradation branch, read every producer of the sentinel that routes into it and grep the module's own tests for fixtures that exercise it; a docstring or comment asserting unreachability is a hypothesis to falsify, not corroboration.

2. **`code_impact(include_tests=true)` returned zero test callers silently, and the reason is not what it looks like.** Probed 2026-08-15: the project graph holds 10,719 test-path nodes (fixture repos, the multi-language pack), but **zero nodes for `scripts/tests/test_accel_embedder.py`**, because the framework's own test tree under `.wavefoundry/framework/scripts/tests/` is never indexed (AGENTS.md contract). Additionally, the two tests that exercise the branch reach it through `patch.object` and a call to the parent function, so even an indexed test would not produce a `calls` edge to the branch's helper. So on this repository, `include_tests=true` disables a query-time filter (`_is_test_path`) over data that was excluded at build time, and the empty `affected` list reads as "no test coverage" when the truth is "no test coverage VISIBLE to this instrument." That is the same silent-empty class already logged for `code_keyword` on index-excluded files.

## Requirements

1. **Seed 221 rule (canonical), under `seed_edit_allowed`.** In `## Maintainability & Dead-Code`, after the "Zero static references does NOT mean dead" block, add a second, clearly separate rule for **conditionally-guarded branches** (fallback, degradation, retry, cold-cache paths): a visible caller does not make the branch live and a guard does not make it dead; the reviewer must (a) enumerate every producer of the sentinel or predicate that routes into the branch (every `return None`, every raised-then-caught exception, every default), (b) grep the module's tests for fixtures naming the branch or its helper, and (c) treat any prose claim of unreachability (docstring, comment, plan, prior sweep) as a hypothesis to falsify against (a) and (b). State the two-class distinction explicitly (node reachability, answered by `code_references` + `code_callhierarchy`; condition reachability, answered by reading sentinel producers plus tests) so the sweep picks the right probe.
2. **Mirror the rule in the repo-local prompt.** `docs/prompts/codebase-cleanup-review.prompt.md` `## Aggressive but SAFE` gains the same two-class rule in its own compact voice (this doc is hand-authored, not seed-rendered; verified 2026-08-15).
3. **`code_impact` test-visibility diagnostic.** When `include_tests=true` and the traversal yields zero affected nodes classified as test paths, attach a non-error diagnostic (e.g. `test_callers_not_visible`) stating that the empty result does not prove absence of test coverage, naming the two reasons: the repository's index-excluded test trees (this repository excludes `.wavefoundry/framework/scripts/tests/`), and mock- or fixture-driven coverage that produces no `calls` edge. Recovery pointer: `code_keyword` over the test tree for the symbol name. Response shape otherwise unchanged; `include_tests=false` behavior untouched.
4. **Tests.** A `code_impact` fixture proving the diagnostic appears exactly when `include_tests=true` AND zero test-path nodes are affected, and is absent both when `include_tests=false` and when a test-path node IS affected (positive control on a fixture repo whose test file is indexed). Seed 221 content covered by the existing shipped-reference/carrier tests. Full suite green; docs-lint clean.

## Scope

**Problem statement:** The cleanup review's safety rule addresses only node reachability, and `code_impact` reports "no test callers" silently where test coverage is merely invisible; together they produced a false removal verdict against a live fallback.

**In scope:** Requirements 1 through 4.

**Out of scope (evaluated 2026-08-15, recorded so nobody re-derives them):**

- **Path predicates on call edges** (a `RETURNS_NONE_ON`-style extractor annotating edges with early-return conditions). Would move condition reachability partly into the graph, but: Python-only at first, an ADR, a `GRAPH_BUILDER_VERSION` bump forcing a full re-extract on every install, for a class of finding observed exactly once, and it would not have prevented today's failure, which was a reviewer overriding a correct graph answer on the strength of a docstring. Revisit only if condition-reachability misfires recur; measure first.
- Indexing the framework's own `scripts/tests/` tree (a deliberate self-hosting exclusion with its own rationale; this change makes the exclusion visible, not undone).
- Changing `_is_test_path` or the `include_tests` semantics.

## Acceptance Criteria

- [x] AC-1: seed 221 carries the two-class reachability rule with the three-step condition-reachability probe (sentinel producers, module tests, prose-as-hypothesis); the existing node-reachability block is unchanged.
- [x] AC-2: `docs/prompts/codebase-cleanup-review.prompt.md` mirrors the two-class rule.
- [x] AC-3: `code_impact` attaches the `test_callers_not_visible` diagnostic exactly under the specified condition, naming both invisibility reasons and the recovery pointer; `include_tests=false` responses are byte-identical to before.
- [x] AC-4: fixture tests cover the diagnostic present/absent in all three states; full suite green; docs-lint clean; seed edits under `seed_edit_allowed`.

## Tasks

- [x] Author the seed 221 rule (one `seed_edit_allowed` cycle); mirror into the cleanup prompt.
- [x] Add the `code_impact` diagnostic in `server_impl.py` (read the fragile-file playbook memory first: identify the response-envelope seam and its paired consumer).
- [x] Tests: three-state diagnostic fixture; suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| rule       | implementer | —          | Goal: seed 221 + prompt mirror carry the two-class rule; lint clean |
| diag       | implementer | —          | Goal: diagnostic emitted only in the specified state; three-state fixture green |


## Serialization Points

- `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`
- `docs/prompts/codebase-cleanup-review.prompt.md`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

`N/A`: a review-rule refinement and one advisory diagnostic on an existing tool; no boundary, flow, or verification-architecture change. `docs/specs/mcp-tool-surface.md` may gain one line for the new diagnostic code if it enumerates `code_impact` diagnostics (check at implement).

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The rule is what would have prevented the false verdict. |
| AC-2 | important | The repo-local prompt is what `/wf-code-cleanup` actually loads. |
| AC-3 | required  | Silent-empty is the tool defect; the diagnostic is the fix. |
| AC-4 | required  | Three-state proof that the diagnostic is neither vacuous nor noisy. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-15 | Planned from the wave 1ve3e post-mortem. Two premises verified before writing: (a) `code_impact(symbol=_ensure_fastembed_model_cached, include_tests=true)` returned 3 non-test affected nodes and zero test callers while the graph holds 10,719 test-path nodes but 0 for `test_accel_embedder.py`; (b) the branch's callers in tests use `patch.object` + the parent function, so no `calls` edge exists even in principle. The safety rule lives canonically in seed 221 `## Maintainability & Dead-Code`; the repo-local prompt is hand-authored (no seed renders it). | Graph probe 2026-08-15 (`gq.get_query_index`: 17,058 nodes, 10,719 test-path, 0 for the accel test file); `code_impact`/`code_callhierarchy` outputs; seed 221 lines 82-108 |
| 2026-08-15 | Implemented. Seed 221 gained the two-class reachability rule (node vs condition, three-step probe, prose-as-hypothesis, the accel case as the recorded example) under one `seed_edit_allowed` cycle; the repo-local cleanup prompt mirrors it. `code_impact` now attaches the advisory `test_callers_not_visible` exactly when `include_tests=true` and zero affected nodes are test-path (pure function of already-computed data, no extra traversal; `include_tests=false` path untouched). Three-state tests added to `TestCodeImpactIncludeTests` and passing. `docs/specs/mcp-tool-surface.md` gained one clause. Live find during implementation: the full suite's `test_advisory_tags_appear_only_at_the_sanctioned_sites` guard (1uugg AC-10c) correctly rejected the new `advisory=True` site, since the sanctioned set is a security control preventing silent softening of lifecycle gates; extended the sanctioned set with the new read-only site (`_code_impact_graph_response`, `test_callers_not_visible`) as a reviewed, deliberate addition with a comment stating why it can soften nothing. Full suite 7244 across 62 files OK; docs-lint clean. | `server_impl.py` `_code_impact_graph_response`; `TestCodeImpactIncludeTests` (`t1vbuu.log`); `suite-1vbuu.log` (guard failure) and `suite-1vbuu-2.log` (7244 OK); seed 221 rule; `docs/specs/mcp-tool-surface.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-15 | Fix the RULE (two reachability classes) plus a visibility DIAGNOSTIC; do not extend the graph with path predicates. | The graph answered node reachability correctly; the failure was a reviewer applying a node-reachability rule to a condition-reachability question and trusting prose. Path predicates would add a third fact the same reviewer could override; a rule that names the right probe addresses the actual failure at near-zero cost. | Path-predicate extractor (deferred: high cost, single occurrence, does not address the override); do nothing and rely on the new memory record (rejected: memories advise the target file, the rule must live where every sweep reads it). |
| 2026-08-15 | Make the empty test-caller result a diagnostic, not a filled-in answer. | The instrument cannot know about mock-driven coverage or index-excluded trees; honesty about the blind spot is the correct contract, matching the `code_keyword` index-exclusion precedent. | Auto-fall-back to a `code_keyword` sweep inside `code_impact` (rejected: changes response semantics and cost for every caller). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The diagnostic fires on every `include_tests=true` call in repos with excluded test trees and becomes noise. | Scoped to the zero-test-affected state only; a repo whose tests are indexed and hit gets no diagnostic (positive-control fixture proves it). |
| The seed rule reads as generic caution and gets skimmed. | It names the exact three-step probe and the exact two classes with their instruments; the accel case is the recorded example. |
| `server_impl.py` is a fragile file. | Follow the fragile-file playbook memory: identify the envelope seam and paired consumer, forward the diagnostic code to any enumeration that lists `code_impact` diagnostics. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
