# Drop Lifecycle IDs From Tool Descriptions

Change ID: `237el-enh drop-lifecycle-ids-from-tool-descriptions`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-12
Wave: `237ei tool-reference-and-guru-description-follow-ups`

## Rationale

The MCP server sends every registered tool's description to the model, so these descriptions are instruction text loaded into every session of every project. Change `237eg` removed wave and change IDs from `AGENTS.md` and seed 050 because a reading agent cannot act on them and the history already lives in git and `docs/waves/`. The registered tool descriptions still carry them. The `237ef` ledger recorded this as INDEXSUMMARY-DEL-1, because Tool Index summaries copy the registered first sentence.

A census of the live base registration finds 87 ID-shaped tokens in 27 of the 92 tool descriptions. One is legitimate: `wf_get_change`'s example argument `"12ahv"`. That leaves 86 lifecycle references in 26 descriptions, for example:

1. "Wave 1p3dk adds …";
2. "(wave 1t59p)";
3. "Secrets gate (wave 1p3rm, updated 1p5pz)";
4. "Degrades per the 1seaq st…".

The heaviest are `wf_graph_report` (23), `index_build` (6), `index_health` (6), `code_graph_community` (5) and `wf_close_wave` (5). The `wf_new_feature` reference is in its first sentence, so it also appears in its Tool Index row.

The descriptions live in handler docstrings, 25 in `wf_server/server_impl.py` and one in `server.py`. Docstring edits change the handler digests pinned in `tests/fixtures/register-surface-handler-digests.json` and checked by `test_mcp_tool_registry.py`.

## Product Intent

Agents in every project read tool descriptions that state current behavior without history pointers they cannot act on. Before: 26 descriptions carry 86 wave or change IDs. After: none carry one, a test keeps it that way, and each description still states the same behavior. Boundary: description text only; no parameter, schema, tier or behavior changes. AC-1 tests the intent.

## Requirements

1. **Remove the references.** In each affected registered description, remove the lifecycle ID and keep the behavior it annotated, for example "Wave 1p3dk adds X" becomes a statement that the tool does X. Where an ID names a contract or design, state the behavior inline, or give a path and a heading with no ID in the cited text. Many architecture headings carry wave IDs, and the `1seaq` state table exists only in a closed wave's change doc, so pointing at them would bring the IDs back. Also remove sentences that only narrate history, with or without an ID (for example "before that wave" or "pre-… acknowledged_for_wave").
2. **Keep example values.** An ID used as an example argument value, such as `wf_get_change`'s `"12ahv"`, is not a lifecycle reference and stays. The guard's allowlist is exactly `{"12ahv"}`. A later addition must be an example argument value or a unit token (such as `100ms`), with a comment justifying it.
3. **Preserve meaning.** Every description keeps its parameters, modes, side effects, refusals and diagnostic names. Contract tests that compare a description with an exported registry (for example the `wf_review_event` vocabularies) still pass.
4. **A guard test.** Add a test that boots the shipped base declaration and fails when any registered tool description contains a lifecycle ID. It uses the same pattern as the `237eg` `LIFECYCLE_ID` test in `test_render_agent_surfaces.py` (bare, backticked, parenthesized and slash-joined IDs; digit-only tokens are not flagged), and uses the allowlist defined in Requirement 2. It runs, not skips, in the default, declared and second profiles.
5. **Follow-on surfaces.**
   1. Refresh the handler-digest pins in `tests/fixtures/register-surface-handler-digests.json`, which `test_mcp_tool_registry.py` checks, for the edited handlers.
   2. Update the Tool Index rows whose summary changes so the index test still passes: `wf_new_feature` and `wf_techdocs_baseline`.
   3. Update any test that asserts on removed description text.

## Scope

**Problem statement:** Registered tool descriptions, loaded into every session, carry wave and change IDs that agents cannot act on.

**In scope:**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py` and `.wavefoundry/framework/scripts/server.py`: description docstrings
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` (guard test) and `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json` (digest pins), plus any test asserting on removed text (the code reviewer found none)
- `docs/specs/mcp-tool-surface.md`: changed Tool Index summaries
- `CHANGELOG.md` `[Unreleased]`

**Out of scope:**

- IDs in code comments, test docstrings, the changelog or wave records
- IDs in spec prose that is not a registered description, such as detail bullets and the `wf_new_<kind>` family row in `docs/specs/mcp-tool-surface.md`
- Any tool behavior, schema or registration change
- Extension tool descriptions not on the base declaration

## Acceptance Criteria

- [x] AC-1: No registered base-declaration tool description contains a lifecycle ID other than the allowlisted example values. The guard test fails on the current descriptions and passes after the change, in the default, declared and second profiles without skipping, and fails on a known-bad control that adds one ID back.
- [x] AC-2: The code-reviewer compares each edited description before and after (the git diff of the handler docstrings) and records one line per tool in the Progress Log. Each line confirms that no parameter, mode, side effect, refusal or diagnostic name was lost, and that no history narration remains, with or without an ID.
- [x] AC-3: The Tool Index test, the description contract tests and the refreshed handler-digest pins pass.
- [x] AC-4: The changelog describes the change; the edited documents validate; the change's tests pass in the default and declared profiles.

## Tasks

- [x] Open `framework_edit_allowed`; edit the 26 descriptions; add the guard test; refresh digest pins and affected tests; close the gate.
- [x] Update the changed Tool Index summaries.
- [x] Add the changelog bullet.
- [x] Run focused tests in the default, declared and second profiles and full docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| descriptions | implementer | `237ek-enh signatures-for-every-tool-entry` | Shares `test_server_tools.py` and the spec with 237ek; run after it |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: description text only, with no boundary, flow or verification-architecture impact.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The intent |
| AC-2 | required | Descriptions are the model's tool contract; nothing may be lost |
| AC-3 | required | Existing enforcement stays green |
| AC-4 | required | Release notes and validation |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-12 | Planned from `237ef` follow-up INDEXSUMMARY-DEL-1. Census over the live base registration with the ID pattern: 87 tokens in 27 descriptions, one of them the `wf_get_change` example value. | Scratch census over `build_server` tool descriptions |
| 2026-11-12 | Readiness review round 1 amendments. Code, QA and red-team each reproduced the census (86 references in 26 descriptions, 25 in `server_impl.py` and `wf_reload_mcp` in `server.py`) and confirmed no description is composed elsewhere. Added: the digest fixture path and the `server.py` restart note (CR-EL-2); the `wf_techdocs_baseline` index row (CR-EL-3, DOC-6); spec prose out of scope (DOC-6); the bounded allowlist (QA-RDY-5); inline behavior or ID-free path and heading instead of ID-bearing headings (RT-2); history narration without IDs in AC-2 (RT-7). | `.wavefoundry/work/237ei/code-readiness.md`, `qa-readiness.md`, `docs-readiness.md`, `redteam-readiness.md` |
| 2026-11-12 | Implemented. An implementer subagent rewrote the 26 descriptions (25 in `server_impl.py`, `wf_reload_mcp` in `server.py`); its per-tool record is `.wavefoundry/work/237ei/237el-description-diff.md`. It also removed three all-digit wave references in `wf_graph_report` ("wave 13129") that the pattern cannot see. An AST comparison against HEAD with docstrings blanked shows both files' code is unchanged, and no comment line changed. The guard `test_tool_descriptions_carry_no_lifecycle_ids` reuses `RoutingGuidanceTextTests.LIFECYCLE_ID`, allows exactly `{"12ahv"}`, fails on an added ID, and checks the allowlisted value is really present. The 25 changed handler digests were refreshed in the fixture (no other entry changed). The `wf_new_feature` and `wf_techdocs_baseline` Tool Index rows follow the new first sentences. Focused run of six files: default 950 tests OK; declared and second profiles 0 of 6 files failed. | `run_tests.py`, six files, three profiles |
| 2026-11-12 | AC-2 code-reviewer before-and-after review (delivery, HEAD against the working tree): exactly 26 docstrings changed (25 in `server_impl.py`, `wf_reload_mcp` in `server.py`); for each of code_ask, code_callgraph, code_callhierarchy, code_constants, code_graph_community, code_graph_path, code_impact, code_keyword, code_lexical, code_pattern, code_read, code_risk_score, code_search, docs_search, index_build, index_build_status, index_health, wf_audit, wf_close_wave, wf_graph_report, wf_new_feature, wf_pause_wave, wf_prepare_wave, wf_reload_mcp, wf_review_event and wf_techdocs_baseline, no parameter, mode, side effect, refusal or diagnostic name was lost and no history-only narration remains (per-tool table in the artifact). Red-team's word-level diff agrees. Three time-relative phrases that state current behavior or a deprecation remain by design: `code_impact` "no longer reads as", `wf_graph_report` "in this release" and "removed after one release" (CODE-DEL-A2). QA confirmed the guard fails with the HEAD descriptions swapped in. | `.wavefoundry/work/237ei/code-delivery.md`, `redteam-delivery.md`, `qa-delivery.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-12 | Clean every description, not only Tool Index summaries | The full descriptions are what the model reads each session; the summaries follow from them | Fix only `wf_new_feature` (leaves 85 references) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Rewording drops a behavior detail an agent relied on | Per-tool before and after review (AC-2) |
| The ID pattern flags a legitimate token | Allowlist is exactly `{"12ahv"}`, and each later entry is justified in the test (Requirement 2) |
| Editing `server.py` changes the runner identity | A live session reports `runner_stale` and needs a host restart, not `wf_reload_mcp`; note it in the handoff |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
