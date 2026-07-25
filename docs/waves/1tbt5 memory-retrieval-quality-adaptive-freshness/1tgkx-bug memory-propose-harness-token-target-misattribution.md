# Memory-Propose Harness-Token Target Misattribution

Change ID: `1tgkx-bug memory-propose-harness-token-target-misattribution`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-23
Wave: `1tbt5 memory-retrieval-quality-adaptive-freshness`

## Rationale

`memory_propose`'s repaired-finding drafter has produced a wrong-target `Fragile: run_tests.py` candidate on three waves (1t3ek, 1tbvp, 1tg55), each requiring a manual `memory_validate` rewrite to point the lesson at the surface actually repaired. Wave 1t72b (`1t728-bug memory-propose-target-misattribution`) fixed the first-known path by dropping `command_or_fixture` from target extraction (decision recorded as memory `1t21l-mem`): targets now come from `artifact_or_test_id` and `public_path` only. The 1tg55 recurrence proves that fix incomplete: in real ledgers, agents record the suite run inside `artifact_or_test_id` too (observed verbatim: `run_tests.py quiet 6,181 OK; test_zero_measured_cost_omits_the_stamp`), so harness file tokens still become targets. Any two findings in a wave verified by the full suite then share the `run_tests.py` token, the >= 2 repeated-repairs heuristic fires, and a false `fragile_file` draft is minted against the test runner instead of the repaired module. The defect is systematic, not a one-off authoring mistake: full-suite verification is the required norm, so the collision is the common case.

## Requirements

1. **The verification harness never becomes a target.** File tokens that name the repository's test-runner entry points (at minimum `run_tests.py`; when the workflow config's `test_runner` key names a runner entry, its file token as well, with graceful absence) must never be extracted as draft targets from any evidence field, including `artifact_or_test_id`.
2. **Targets prefer the repaired surface.** Target extraction from repaired findings must favor tokens that name what was repaired. Design options to settle at Prepare (pick the simplest that passes the regression corpus): (a) filter harness-entry tokens from `artifact_or_test_id`; (b) additionally exclude any file token that also appears in the same record's `command_or_fixture` (it is verification context by construction); (c) map `test_<module>.py` tokens to their covered module only when unambiguous. The existing conservative rule stands: if no qualifying target survives, draft nothing.
3. **Regression corpus from canonical producers.** Tests replay the real 1tg55-shaped ledger content (repair evidence citing `run_tests.py quiet ...; test_x` in `artifact_or_test_id` across two findings) and assert no harness-targeted draft is produced, while a genuine repeated-repair signal (two findings whose evidence anchors the same product module, as on 1t9w8/`memory_records.py`) still drafts its `fragile_file` candidate. No hand-invented field shapes; fixture content derives from the recorded ledgers.
4. **`1t21l-mem` reconciled.** The prior decision memory is updated (supersede or validate-rewrite) so its action delta covers the widened rule; the corpus's existing wrong-target rewrites (`1t0z2-mem`, `1tage-mem`, `1tdm6-mem` lineage) are left as history.

## Scope

**Problem statement:** the repaired-finding drafter in `memory_supply.py` still extracts verification-harness file tokens as targets via `artifact_or_test_id`, minting false `fragile_file` drafts against `run_tests.py`.

**In scope:**

- `draft_candidates` target extraction in `.wavefoundry/framework/scripts/memory_supply.py`
- Regression tests in `test_memory_records.py` built from real ledger shapes
- Reconciling decision memory `1t21l-mem`
- Validation-schema compatibility for an already-promoted record later
  superseded through the ordinary memory lifecycle

**Out of scope:**

- Decision-Log-sourced drafting (path (A)); its `1t72b` backtick-refs behavior is unchanged
- Retrieval/ranking behavior (`1sufn`) and freshness policy (`1t7ab`)
- Rewriting historical superseded draft records

## Acceptance Criteria

- [x] AC-1: replaying the 1tg55-shaped ledger (two findings, both with `artifact_or_test_id` citing the suite run plus specific tests) produces no draft targeting `run_tests.py` or any configured test-runner entry.
- [x] AC-2: a genuine repeated-repair signal (two findings anchored to the same product module) still produces its `fragile_file` draft, and single-repair findings still produce `failed_attempt` drafts with repaired-surface targets.
- [x] AC-3: `1t21l-mem` is reconciled to the widened rule via the memory lifecycle (no hand edit of the record body outside the tools).
- [x] AC-4: docs gate and full framework suite green.

## Tasks

- [x] Settle the extraction design (Requirement 2 options) and implement in `draft_candidates`.
- [x] Producer-derived regression tests: harness-token exclusion + genuine-signal preservation.
- [x] Reconcile `1t21l-mem`; docs gate; full suite. *(Lifecycle reconciliation complete via superseding `1tdmn-mem`; docs/full-suite evidence is recorded at the wave gate.)*

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| extraction | implementer | —          | memory_supply.py target derivation |
| regression | qa-reviewer | extraction | Real-ledger-derived corpus, both directions |


## Serialization Points

- None; single-module change with its tests.

## Affected Architecture Docs

N/A — confined to the `memory_supply.py` drafter and its tests; no boundary, flow, or verification-architecture impact. `docs/agents/memory/README.md` gains a note only if the extraction rule becomes operator-visible.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The defect being fixed: harness tokens must never be drafted as targets. |
| AC-2 | required  | The guard must not suppress genuine repeated-repair and failed-attempt signals. |
| AC-3 | important | Keeps the decision-memory lineage truthful; uses the lifecycle tools, not hand edits. |
| AC-4 | required  | Standard gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-23 | Drafted from the 1tg55 recurrence: confirmed via the 1tg55 ledger that `artifact_or_test_id` carried `run_tests.py quiet 6,181 OK; ...` on two findings, tripping the repeated-repairs heuristic post-1t72b-fix. | 1tg55 events.jsonl; `memory_supply.py` `draft_candidates` lines 388-427; `1t21l-mem` |
| 2026-07-23 | Implemented canonical/configured runner-entry exclusion and producer-derived regressions in both directions. | `MemoryProposeTests.test_artifact_harness_tokens_never_become_targets`; `test_configured_runner_is_filtered_but_product_signal_survives` |
| 2026-07-23 | Superseded the narrower decision memory through the typed lifecycle with a widened rule covering every evidence-derived target source, including `artifact_or_test_id`. | `1tdmn-mem decision-memory-supply-targets-exclude-verification-harness-` supersedes `1t21l-mem`. |
| 2026-07-24 | The live supersession exposed a schema mismatch: lifecycle supersession preserved the historical `Validation: promote` verdict but lint required every promoted record to remain active. The lint contract now accepts promoted-then-superseded records only with `Superseded by:`, preserving validation provenance without confusing lifecycle supersession with validation rewrite. | `MemoryRecordLintTests.test_evidence_derived_validation_contract`; live `wf_validate_docs`; full suite 6,193/6,193. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-23 | Filter the canonical `run_tests.py` entry token plus implementation-file tokens named by optional workflow-config `test_runner`; do not add cross-field suppression or test-module inference. | This directly excludes known verification entry points while preserving product modules that may legitimately appear in both a fixture command and repaired-surface evidence. It is deterministic, bounded to one optional config read per draft call, and degrades to the canonical token when config is absent or invalid. | Exclude every token also present in `command_or_fixture`: rejected as over-broad; map `test_<module>.py` to product modules: rejected as speculative inference. |
| 2026-07-24 | Preserve a promoted validation verdict when ordinary lifecycle supersession later retires the record; require the successor link. | `Validation:` records the original agent judgment, while `Status:` records current lifecycle state. Relabeling a promoted record as `Validation: rewrite` would falsify its history. | Clear validation metadata or hand-edit the record: rejected as provenance loss and lifecycle bypass. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-filtering suppresses genuine fragile_file signals on test infrastructure itself | The exclusion names harness ENTRY points, not test modules. If a wave genuinely repairs the runner itself twice, the conservative outcome (draft nothing) is acceptable by the drafter's standing philosophy: a suppressed true signal costs less than a minted false one, and the corpus test pins whichever behavior the settled design produces |
| Token heuristics drift again as evidence-authoring habits change | Regression corpus derives from real recorded ledgers, so the guard tracks actual producer behavior |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
