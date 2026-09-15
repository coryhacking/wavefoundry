# First-hop index restart envelope

Change ID: `1xxca-bug first-hop-index-restart-envelope`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-14

## Rationale

The ppjy-to-ppm0 consumer upgrade correctly paused for an unprotected host but its already-loaded MCP wrapper returned error/isError and pre-flight failure around a valid index_guard_restart_required action. Make that expected checkpoint visibly actionable on the current wrapper and the older wrapper's installed action-reader seam, while preserving exact continuation and genuine failure semantics. No storage, index, ranking or version-constant change is intended.

## Requirements

1. A validated invocation-bound index guard pause returns outer status action_required, no true isError, failed_phase null and the correct index_guard_restart_required code; retain exact command_argv and checkpoint/package guidance.
2. Cover the first installing hop through the pre-guard wrapper, not only a current wrapper calling a simulated old coordinator. Reuse its installed restart-action reader and response boundary; do not create a fake storage receipt, relabel the action as a storage migration, reload producer modules, or weaken host confirmation.
3. Plain exit 3, stale/mismatched invocation, malformed/foreign checkpoint and dry-run remain errors. Existing real storage pauses retain their behavior. Response bounds and host inventory limits remain effective.
4. Compatibility adaptation is narrow and validated; unrelated/concurrent responses are unchanged. Older hosts that already cached an older action reader cannot acquire incoming behavior; document this limit rather than claiming universal retroactive replacement.
5. The change's focused tests and new regressions pass; edited guidance describes the actual supported boundary.

## Scope

In scope: guard pause response formatting, installed-reader compatibility for pre-guard wrappers, regression fixtures and a real ppjy-wrapper local replay; concise 1.24.0 changelog and upgrade guidance.

Out of scope: publication/host-stop policy, storage conversion, producer versions, general MCP reload, commits, package/publication and wave closure.

## Acceptance Criteria

- [x] AC-1: Current wrapper surfaces a validated guard pause as action_required with correct code, exact command and no failure framing.
- [x] AC-2: A pre-guard wrapper replay reaches the same safe public envelope through newly installed code, without a storage receipt or index mutation; cached-reader limitations are explicit.
- [x] AC-3: Invalid/stale/plain failures and dry-runs do not become pauses; real storage and unrelated responses remain correct, including concurrent response handling and bounded output.
- [x] AC-4: Focused regressions detect omitted normalization; edited guidance and changelog align with observed first-hop behavior.

## Tasks

- [x] Implement narrow current and legacy-wrapper envelope handling.
- [x] Add positive/negative/concurrency regression controls and execute the ppjy-wrapper replay.
- [x] Update operator guidance and changelog; record focused and full verification evidence.

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — current response owner.
- `.wavefoundry/framework/scripts/sqlite_storage_migration.py` — pre-guard wrapper's installed restart-action reader.
- `.wavefoundry/framework/scripts/upgrade_extensions.py` — validated guard checkpoint and bounded compatibility adaptation, if needed.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_index_upgrade_guard.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `CHANGELOG.md`

Read-only review roles inspect these seams. Implementer owns writes after readiness; all other framework, product and renderer-managed surfaces are protected.

## Affected Architecture Docs

MCP tool surface and upgrade prompt document the response contract. Existing publication/storage architecture remains unchanged; no ADR or new schema is required.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Honest operator-visible result |
| AC-2 | required | Fix the reported installing hop |
| AC-3 | required | Do not disguise real failures |
| AC-4 | required | Durable regression evidence |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-13 | Reuse validated installed action-reader and bounded response seams for the pre-guard wrapper, plus direct current-wrapper normalization. | Addresses the reported installing hop without pretending an old executing wrapper reloads itself. | Current-wrapper-only fix misses ppjy; forcing a restart before every upgrade adds unnecessary operator work and avoids the defect rather than handling the expected checkpoint. Compatibility uses one idempotent adapter at the old wrapper's final bounded-envelope function, preserving its original bounds. A nonserialized per-action capability carries the validated root, invocation and immutable action snapshot across the old wrapper's dict copy; no temporary next-response hook or accumulating registry. Install successfully before returning the marked action, check unchanged identity/command fields, remove the internal marker and synthetic receipt path before serialization, and leave unrelated responses untouched. Current wrappers format directly; cached old readers remain an explicit first-hop limitation. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-14 | Observe: all four ACs remain verified in released 1.24.0. Luna passed 32 focused tests; independent Astra passed 12 controls including actual archived ppjy wrapper and killed two in-memory mutants. No source changes or findings. Status reconciled to complete; prior council remains applicable to unchanged boundary. | delivery-review.json closure_verification_20260914; current green 9,008-test receipt. |
| 2026-09-14 | Readback: resume shipped AC-1–4 for closure verification only. Thought: Luna owns bounded QA checks; independent Astra owns compatibility and docs-contract review; coordinator owns lifecycle bookkeeping. No production edits planned. Operator authorized reopening, review and closure of this wave followed by 1xtnr. | Current operator request; public release 1.24.0+ppq7; framework receipt 9,008 tests, current input hash. |
| 2026-09-13 | Trace: current wf_upgrade_response recognizes guard action; pre-guard wrapper has only sqlite_storage_migration.read_restart_action and hardcoded storage envelope. The current test exercises the new wrapper, not the reported ppjy wrapper. | server_impl.wf_upgrade_response; sqlite_storage_migration.read_restart_action; WaveUpgradeMcpToolTests.test_index_guard_pause_is_bound_to_invocation_and_uses_external_cli |

| 2026-09-13 | Readback: expected index restart becomes action_required in current and newly loaded ppjy reader paths, preserving exact CLI and genuine errors (AC-1–4). Thought: implement response/reader adapter, run historical and negative controls, then update guidance and full verification. Generic implementer owns scoped writes. Prepare/create opened after clean readiness; wf_implement_wave still requests obsolete extra prepare lanes, so the documented prepare-and-open path was used. | Current typed council approval and successful wf_prepare_wave(mode=create) |
| 2026-09-13 | Observe: current public wrapper controls pass; actual ppjy archive wf_upgrade_response plus original bounder pass guard/storage/plain-exit/dry-run replay (3 tests). MacOS path alias mismatch found in the adapter and repaired by retaining validated caller locator spelling. | /tmp/1xxcb-ppjy-replay.json; test_index_guard_pause_is_bound_to_invocation_and_uses_external_cli |
| 2026-09-13 | Observe: 192 focused tests pass (one existing platform skip); latest public wrapper and guard suite 24/24 pass. Both removed-reader and removed-final-normalizer mutants fail the positive legacy-wrapper test for the expected wrong status. Oversized child output remains bounded while exact argv survives the archived original bounder. Thought: freeze scoped source for independent delivery review and full suite. | implementation-evidence.json; test_legacy_wrapper_corrects_outer_status_and_retains_exact_continuation |
| 2026-09-13 | Observe: full framework suite passes 8,984 tests across 90 files (12 existing skips); green receipt hash independently recomputed. Code, QA, docs and targeted delivery council approve with no findings. Memory proposal returned zero candidates; canonical guidance owns the lesson. | implementation-evidence.json; delivery-review.json; current typed approvals |
