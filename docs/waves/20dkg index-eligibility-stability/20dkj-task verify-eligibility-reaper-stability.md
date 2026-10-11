# Verify Eligibility Reaper Stability

Change ID: `20dkj-task verify-eligibility-reaper-stability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-11
Wave: 20dkg index-eligibility-stability

## Rationale

Verify the historical eligibility-reaper flapping report against the current framework and reconcile the remaining backlog entry, using scratch repositories and the existing launch/corpus regression tests. Do not redesign a reaper when a later repair already removed the reported cause.

The follow-up in `docs/agents/session-handoff.md` cites wave `1ymzk`: repeated removal of about 187 policy-ineligible framework test paths. Its historical before/after retrieval improvement measured corpus cleanup, not handler extraction. Wave `204jj` subsequently closed change `2038p`, which stopped setup from forwarding workflow code prefixes as an all-layer override. Current `setup_index._run_indexer` launches the indexer bare (`setup_index.py:2256–2282`), and the indexer resolves layer-specific prefixes itself (`indexer.py:1569–1610`). The existing corpus-parity tests exercise the exact former re-add/reap loop and migration cleanup.

Discovery executed three unchanged focused tests in scratch fixtures: two `SetupLaunchedCorpusParityTests` and the six-mode setup launcher test, all passing in 2.331 seconds. A runtime-only historical-prefix-forward control was detected by the unchanged corpus oracle as framework test rows in `chunks_docs`. This disproves an unrepaired instance of the historical default-policy launch defect on this fixture; it does not establish the state of the operator's live index or every possible eligibility defect. This wave is therefore verification and record reconciliation, with no admitted production repair.

## Requirements

1. Inspect the current launch route census and shared prefix reader, including foreground setup (all/docs/code/graph), background docs/code setup children, and the bare incremental shape used by hooks/MCP refresh. Verify no automatic route supplies `--project-include-prefix`. Explicit manual overrides remain supported and are not automatic-launch parity claims.
2. Execute existing deterministic scratch corpus tests showing setup → bare incremental → setup convergence under unchanged default flags, including preservation of folded framework docs, eligible non-test script docstrings and code. Verify previously leaked framework test rows are removed once by normal setup and do not return or cause further embedding.
3. Confirm the corpus oracle detects the historical prefix-forward fault without changing repository source or writing the live index. Use temporary fixture state and report the observed failure honestly; do not count a known-bad failure as a green qualification result.
4. At delivery, replace the stale unresolved flapping entry in the current handoff with the verified disposition and the `204jj` repair reference. Preserve the historical `1ymzk` caveat and invalid receipt dispositions; do not relabel old measurements as extraction benefits or qualify a live store without inspecting it.
5. Keep commands, concise results, covered routes and limitations in the existing change/wave records. Use temporary logs/probes only; no new permanent evidence folder, model download, live setup/rebuild or broad benchmark is required. A newly reproduced defect must return to planning and readiness before source edits.

## Scope

**Problem statement:** A durable backlog entry still describes a historically recurring re-add/reap loop after a later closed wave repaired that launch-policy inconsistency. Reconfirmation and truthful backlog reconciliation remain unfinished.

**In scope:** Existing scratch launch/corpus/migration tests; current automatic launcher census; runtime-only historical control; minimal handoff reconciliation at delivery; independent code/QA review of the evidence and Council readiness.

**Out of scope:** Production source, framework seeds, workflow config, generated surfaces, policy changes, reaper algorithm or safety-guard changes; live index inspection or mutation; rebuild or disabled-reaping workarounds; new benchmarks or receipt relabeling; persisting manual `--include-tests`/`--include-generated` flags (an explicit separate `204jj` watchpoint); proving every OS or external consumer environment.

## Acceptance Criteria

- [x] AC-1: Current automatic foreground/background launch routes use the same layer-prefix authority without an explicit project-prefix override; source census and existing launcher assertions identify the covered routes.
- [x] AC-2: Existing scratch corpus/migration oracles demonstrate unchanged setup/incremental convergence, one-time cleanup of historical leaked test rows, no repeated embedding after cleanup, and retention of eligible framework docs/docstrings/code.
- [x] AC-3: The unchanged scratch corpus oracle rejects the historical forwarded-prefix fault, with the exact failing condition and the control's temporary-only scope recorded separately from passing qualification.
- [x] AC-4: The delivered handoff and wave summary identify `204jj` as the completed historical repair and this wave as its verification, preserve the historical measurement caveat, and explicitly limit claims to the checked routes/fixture rather than the live index.

## Tasks

- [x] Reconfirm current automatic-launch and shared-reader census before delivery evidence freezes.
- [x] Execute existing focused launcher/corpus tests and the temporary historical control; record concise actual results and limitations.
- [x] Reconcile the stale handoff item and record the disposition in wave.md, preserving historical wave/receipt records.
- [x] Obtain independent code/QA review and the configured Council verdict; validate the documents edited by this change. Leave closure operator-owned.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Verify current mechanism and fixture evidence | implementer / Guru | — | Read-only source; scratch-only stores and controls. |
| Reconcile current backlog | wave-coordinator | Verification | Writes only current handoff and this wave's records. |
| Independent verification review | code-reviewer, qa-reviewer | Verification and reconciliation | Review current proof and claim boundaries; no new production repair. |

## Serialization Points

The coordinator owns wave records and the handoff. Verification reads source and tests; it must not write shared framework surfaces. Handoff reconciliation occurs only after verification; preserve concurrently updated unrelated handoff material.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/workflow_include_prefixes.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/agents/session-handoff.md`

These are read-only source/test review targets plus the handoff write target. No source edit is admitted. Root AGENTS, seeds, workflow config, rendered prompts/hooks and existing historical waves/receipts are protected.

## Affected Architecture Docs

No architecture change is admitted. `docs/architecture/data-and-control-flow.md` item 9 already documents the shared reader and bare automatic launches; read it for consistency. `docs/architecture/graph-index-system.md` needs no change because publication, eligibility, reaping and safety boundaries stay unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Grounds parity in actual launch routes rather than a historical hypothesis. |
| AC-2 | required | Shows the observed re-add/reap cycle has converged without losing eligible content. |
| AC-3 | required | Prevents a vacuous green fixture from dismissing the original defect. |
| AC-4 | required | Removes a stale actionable backlog claim without rewriting historical evidence. |

## Progress Log

Readback: Verify the already shipped 204jj launch correction using the current automatic-route census, existing scratch convergence/migration tests and a runtime-only historical prefix-forward fault. AC1–4 cover route parity, one-time cleanup, oracle sensitivity and truthful handoff disposition. Only this wave/change and current session handoff will be written; no production source, live index, downloads, benchmarks or historical receipt rewrite.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | Planning discovery: default-policy historical loop already repaired by 204jj. Three current scratch tests pass; historical forwarded-prefix control fails on test rows in chunks_docs. ACs remain pending delivery reconfirmation/reconciliation and independent review. | `tests/test_indexer.py:2554–2726`, `tests/test_setup_index.py:491–545`; reproduction below. |

### Reproduction

From `.wavefoundry/framework/scripts/tests/`, execute:

```sh
env -u PYTHONPYCACHEPREFIX -u WAVEFOUNDRY_TOOL_VENV PYTHONDONTWRITEBYTECODE=1 WAVEFOUNDRY_DISABLE_BYTECODE_CACHE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TMPDIR=/private/tmp /Users/coryhacking/.wavefoundry/venv/bin/python3 -B -m unittest test_indexer.SetupLaunchedCorpusParityTests test_setup_index.SetupIndexTests.test_main_never_forwards_project_include_prefixes_in_any_mode
```

Use the approved tool interpreter on other hosts. These fixtures create their own temporary repositories; dependency/model/GPU/process boundaries are substituted, while actual indexer, graph/store, drift and reap logic run in the corpus tests. No model download or current repository index build occurs.

The historical control initializes `SetupLaunchedCorpusParityTests('test_setup_and_incremental_builds_agree_on_the_corpus')`, calls `setUp`, saves `case.bi.main`, and within `unittest.mock.patch.object(case.bi, 'main', side_effect=...)` calls the saved function with `[*args, '--project-include-prefix', case.SCRIPTS]`. The unchanged test method must fail with `setup build: framework test rows in chunks_docs`; always call `tearDown`. Discovery observed `.wavefoundry/framework/scripts/tests/test_tools.py` as the leaked path. This control mutates only runtime dispatch, not repository files.

### Delivery reconfirmation — 2026-10-11

The original final Session Handoff paragraph is retained as the planning-time snapshot; current status, completed verification, approvals and next actions are recorded in metadata, this Progress Log and wave.md. A non-boilerplate handoff replacement would be digested; routine execution narration stays here rather than rotating unchanged plan authority.

- Executed the exact existing three-test reproduction above: exit 0, three tests in 2.259 seconds, no skips. The corpus assertions retain folded framework README/seed rows and non-test script docs/code, prove no bare incremental reap and no settled setup embedding, and prove one-time migration cleanup. No new production/test source or live index write.
- Runtime-only historical forward appended `--project-include-prefix` to the real indexer main arguments inside the existing fixture. The unchanged oracle raised `AssertionError`: `setup build: framework test rows in chunks_docs`, with fixture `tests/test_tools.py`. This expected negative-control failure is distinct from passing qualification; teardown removed scratch storage.
- MCP current-file census: setup `_run_indexer` and foreground all/docs/code/graph callers; `_spawn_background_semantic_build` docs/code children reenter bare setup; MCP `run_index_rebuild`, `_index_is_up_to_date`, `_start_background_index_refresh`; rendered hook `_spawn_reindex`; indexer `_effective_project_include_prefixes` and shared `read_project_include_prefixes`. All automatic argv shapes inspected use no explicit project-prefix override; refresh passes content all. Manual parser override remains supported. Existing six-mode test asserts final indexer and detached-child argv. This is a bounded named-route census, not proof about every external launcher.
- Current handoff now identifies 204jj/2038p as the completed historical repair and this wave as verification, retaining 1ymzk's cleanup-only measurement caveat and invalid receipt dispositions. Existing historical records were not edited.
- Fresh canonical-hash check matches the genuine 20cw2 whole-suite receipt: inputs `67dd374e5de81888d47f41034de951993d69a8bc0760c46abadacb792c8111db`, result ok, 12,282 tests / 185 files / 12 aggregate skips, ran `2026-10-11T07:38:09.547707+00:00`, receipt SHA256 `ccbb0439b849e9694cdcf5494efc8a5d08dbe7925e2417ed215ac3b83dbd30c2`. No framework input changed; no redundant whole-suite rerun, new gate or manually minted receipt. Logs/probes stay outside the repository.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-10 | Select a verification/reconciliation task, not a production bug repair. | Later closed wave 204jj and executed current convergence tests already address the historical fault. | Redesign eligibility/reaper logic: risks data loss and new overhead without a remaining reproducer. Dismiss the stale item by document reading alone: cannot establish fixture convergence or oracle sensitivity. |
| 2026-10-10 | Use existing focused tests and one temporary historical control. | They exercise the former inconsistency, migration cleanup and all six setup mode argv shapes. | Add duplicate tests/permanent evidence files: little additional coverage or durable benefit. Run live setup/rebuild: mutates the operator's index and could conceal the relevant state. |
| 2026-10-10 | Keep explicit opt-in flag persistence outside scope. | 204jj records it as a separate policy watchpoint; it is not the historical default-policy prefix-forward defect. | Silently expand scope: introduces an unresolved corpus-policy change under a verification task. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Passing scratch tests are mistaken for live-index or every-platform qualification. | Name substituted boundaries and checked launch routes; make no live-store, network or native-Windows claim. |
| Historical benchmarks get reinterpreted as handler improvements. | Preserve 1ymzk's corpus-pollution caveat and invalid receipt dispositions unchanged. |
| An unobserved different eligibility fault is dismissed. | Treat any new reproduced defect as fresh scoped work; this conclusion addresses the recorded historical prefix-forward cycle only. |
| Concurrent handoff edits are lost. | Coordinator serializes minimal targeted reconciliation after rereading the current handoff. |

## Session Handoff

This task is planned and not implemented. Readiness discovery is not delivery approval. All ACs/tasks remain unchecked; reconciliation and independent delivery checks await implementation. No unresolved operator decision is required: source evidence resolved the defect-versus-verification branch. Runtime model identity is not exposed to this planner; inherited capable model is appropriate for bounded code-grounded planning, and no model override is claimed.
