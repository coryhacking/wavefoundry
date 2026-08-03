# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-03
review-evidence-source: events.jsonl

wave-id: `1tis8 memory-eval-mcp-tool-and-decision-log-target`
Title: Memory Eval Mcp Tool And Decision Log Target

## Objective

Make the framework's own affordances stop tripping agents: promote the memory retrieval eval from stranded test infrastructure to a shippable, MCP-exposed measurement; close the second (decision-log) vector of the harness-token target misattribution; and complete the repair-chain guidance so driving a review repair no longer costs dead-end tool calls.

## Changes

Change ID: `1tgws-enh memory-eval-shippable-mcp-tool`
Change Status: `implemented`

Change ID: `1tis7-bug memory-propose-decision-log-harness-target`
Change Status: `implemented`

Change ID: `1tis9-enh repair-chain-recipe-and-review-evidence-errors`
Change Status: `implemented`


Completed At: 2026-07-25

## Wave Summary

Wave `1tis8` (Memory Eval Mcp Tool And Decision Log Target) delivered 3 changes: Memory retrieval eval as a shippable MCP measurement tool, memory-propose decision-log path extracts harness and prose tokens as targets, and Rename wf_review_evidence to wf_review_event and complete the repair-chain guidance. Notable adjustments during implementation: Memory retrieval eval as a shippable MCP measurement tool: SECOND REPAIR (blocking P2 on the GUARD, independent code-reviewer): the concurrency regression added by the first repair could not fail. `threading.Thread` swallows worker exceptions so `join()` returned normally after a crash; the behavioural half exercised hermetic `run()` rather than the MCP-exposed `run_curated()` where the corruption occurred; and its "unrelated lookup" assertion passed an EMPTY path list, which `file_commit_times` short-circuits to `{}` before touching the store — true whether or not the global was corrupted. Rebuilt: drives the real `run_curated` through a stubbed `srv.WaveIndex` with a `threading.Barrier` forcing genuine overlap, runs both calls through `ThreadPoolExecutor` so `future.result()` re-raises worker failures, asserts both reports are `available` with a non-zero sample, and probes a path deliberately seeded OUTSIDE the sampled records' targets so a leftover frozen subset answers `{}`. Structural source pin retained.; memory-propose decision-log path extracts harness and prose tokens as targets: SCOPE NARROWED (live-caught): the planned "not resolving to a tracked path" guard was implemented, then withdrawn. An existence check dropped legitimate targets and failed 12 existing tests (fixtures and real decision docs name paths absent at drafting time). The placeholder + runner screens fully fix the observed defect; the existence guard was net-negative. AC-2 marked `[~]` with rationale.; Rename wf_review_evidence to wf_review_event and complete the repair-chain guidance: Implemented the clean rename: 103 `wf_review_evidence` occurrences renamed across 18 live files, plus 41 `wf_review_evidence_response` occurrences (the `\b` word boundary skipped the `_response` suffix — caught by the residual census, not assumed). Extractor maps (`_STATE_SOURCE_EXTRACTORS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`) key on the new name; upgrade reconciliation gained `wf_review_evidence -> wf_review_event`. FRESH-PROCESS verification: 83 tools register, `wf_review_event` present, `wf_review_evidence` absent, no alias. Historical wave records, prior telemetry rows, and the 1.14.0 CHANGELOG entry retain the old name; a new 1.15.0 section documents the rename.

**Changes delivered:**

- **Memory retrieval eval as a shippable MCP measurement tool** (`1tgws-enh memory-eval-shippable-mcp-tool`) — 5 ACs completed. Key decisions: `wf_memory_eval` takes no target-root argument; it measures the configured repository.; Split the eval into a shipped MCP-exposed measurement plus a test-owned invariant check.
- **memory-propose decision-log path extracts harness and prose tokens as targets** (`1tis7-bug memory-propose-decision-log-harness-target`) — 3 ACs completed. Key decisions: Extend the harness-token exclusion to the decision-log path and reject non-file placeholder tokens.; Do NOT screen prose targets by on-disk existence; keep the angle-bracket placeholder and runner-entry screens only.
- **Rename wf_review_evidence to wf_review_event and complete the repair-chain guidance** (`1tis9-enh repair-chain-recipe-and-review-evidence-errors`) — 8 ACs completed. Key decisions: Rename `wf_review_evidence` → `wf_review_event`, clean, no alias, folded into this change.; Fix guidance in both the seed AND the tool docstring; sharpen (not re-document) field placement; correct the actor model.
## Watchpoints

- **Watchpoint (1tgws):** the relocated eval engine must stay importable without a `server_impl` import cycle. `run_memory_eval` already lazy-imports `server_impl` inside functions; preserve that so the MCP tool in `server_impl` can call the engine without a circular import.
- **Watchpoint (1tgws):** assert the hermetic fixture fingerprint is byte-identical before and after relocation; the invariant test must not lose coverage or change its fingerprint.
- **Watchpoint (1tgws):** the `wf_memory_eval` envelope stays aggregate-only (no record bodies, summaries, or ids), mirroring the existing curated-report privacy boundary.
- **Watchpoint (1tis7):** the non-file-token guard keys on angle-bracket placeholders and unresolved-to-tracked-file tokens; keep a genuine module resolvable so real decision targets are not dropped.
- **Watchpoint (1tis9):** the `wf_review_evidence`->`wf_review_event` rename is clean with no alias; verify completeness with a case-insensitive rename-gate census and a fresh-process/reload tool-list check (only the new name registers). Historical wave records, prior telemetry rows, and past CHANGELOG entries retain the old name.
- **Watchpoint (1tis9):** rename the tool-name-keyed CE extractor maps (`_STATE_SOURCE_EXTRACTORS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`) so new invocations attribute; update the explicit-wave-attribution and repeat-list-neutrality tests. Add the rename to the upgrade tool-rename map.
- **Watchpoint (1tis9):** fix the lane-clearing recipe in BOTH seed 209 and the registered tool docstring (same omission in both), with the implementer-records-repair_start / blocking-lane-reverifies actor split; do not claim field placement undocumented (the docstring already assigns judgment vs evidence).
- **Watchpoint (1tis9):** implementation needs `seed_edit_allowed` (seed 209) and `framework_edit_allowed`; regenerate the rendered prompt surface via the canonical renderer, never hand-edit the render. Error-message tests assert the corrective concept, not a verbatim string.
- **Watchpoint:** the three changes are independent (no serialization point); they may be implemented in any order.

## Prepare Review Evidence

- **red-team — no blocking finding:** the strongest failure modes are (1tgws) the relocation silently breaking the fixture fingerprint or introducing a `server_impl` import cycle, (1tis7) over-filtering dropping a genuine decision target, and (1tis9) brittle verbatim error-string tests. Each is bounded by an explicit plan mitigation (byte-identical fingerprint assertion, preserved lazy import, preservation test, semantic error-content tests) and captured as a watchpoint.
- **reality-checker — no blocking finding:** all three are grounded, not speculative. `build_pack.py` `EXCLUDED_REL_PATHS` excludes `scripts/tests` and `run_curated(root)` is a real cross-project pass (1tgws); the path-A misattribution was reproduced live at 1tbt5 close (`memory_propose` drafted `run_tests.py`/`test_<module>.py` targets) (1tis7); the repair-chain dead-ends were hit this session (1tis9).
- **qa-reviewer — no blocking finding:** the ACs are falsifiable and checkable — pack inclusion and fingerprint parity (1tgws), producer-derived harness/placeholder exclusion with a preservation counter-case (1tis7), and semantic assertions on the two self-correcting errors (1tis9). Coverage matches the changed surfaces.
- **docs-contract-reviewer — no blocking finding:** the seed-209 edit regenerates the render rather than hand-editing it; the `wf_memory_eval` registration (census/`public_contract`, tool-surface spec, docs-constants) and the field-placement note are enumerated; reference/testing-architecture updates are named. State machine, run kinds, and evidence schema are explicitly unchanged.

## Review Checkpoints

- **Product-owner acknowledgment — 2026-07-24:** the operator directed this wave from the 1tbt5 close discussion and explicitly asked to add the repair-chain-guidance change and prepare the wave.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-24: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the 1tgws relocation could break the hermetic fixture fingerprint or introduce a server_impl import cycle — bounded by a byte-identical fingerprint assertion and preserving the existing lazy import, both recorded as watchpoints; strongest-alternative: split the three changes into separate single-change waves — rejected because they share the "framework affordances that trip agents" theme, carry no serialization point, and are cheaper to review and land together)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-24: PASS (delta: 1tis9 expanded to a wf_review_evidence->wf_review_event rename)** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: an incomplete clean rename could leave a dangling reference or, worse, silently drop CE telemetry credit if a tool-name-keyed extractor map is missed — bounded by a case-insensitive rename-gate census AC, the extractor-key AC with explicit-wave attribution + repeat-list-neutrality tests, and a fresh-process reload tool-list verification; strongest-alternative: register a backward-compatible alias for `wf_review_evidence` — rejected per operator direction because the tool is not broadly distributed and an alias is permanent surface debt; historical wave records, prior telemetry rows, and past CHANGELOG entries retain the old name as point-in-time history)

- **Independent implementation review — 2026-07-25: APPROVED, no additional findings.** The operator independently verified: focused memory-eval suite 14/14; the injected worker failure propagated through `future.result()` as required; the corrupted-store simulation failed on the unrelated-path assertion as designed; both finding chains terminal with the cycle-2 convergence checkpoint covering both; delivery approval current and postdating the repairs; close dry-run passing lint and garden. This clears the review lane; the operator close signoff remains outstanding and is recorded separately when given.

## Implementation Progress Log

- **Observe — ordered lanes:** 1tis7 (smallest, independent) → 1tgws (relocation + tool) → 1tis9 (rename, widest blast radius) last, because the rename removes the very tool this session uses to record review evidence.
- **Verify — 1tis7:** `_code_targets` rejects angle-bracket placeholders for every caller; `_prose_targets` applies the runner filter to the Decision Log path. Live-verified against the real producer: `memory_propose(1tbt5)` no longer drafts the mis-targeted decision. `1tdmn-mem` superseded by `1tj3j-mem` covering both drafting paths.
- **Deviation — 1tis7 scope narrowed:** the planned on-disk existence guard was implemented, proved net-negative (dropped legitimate targets, 12 test failures), and withdrawn. AC-2 carries `[~]` with rationale; recorded in the change's Decision Log.
- **Verify — 1tgws:** engine relocated via `git mv` (history preserved) to shippable `memory_eval.py`; hermetic fixture fingerprint byte-identical (`72ead292…d23f4a4`); pack probe confirms engine included / fixture excluded; new read-only `wf_memory_eval` registered live with a `tools/list_changed` notification.
- **Deviation — 1tgws tool shape:** `wf_memory_eval` takes no target-root argument. No other tool accepts one and the allowed-roots safety rule forbids caller-named directories; cross-project use comes from the engine shipping. Recorded in the change's Decision Log.
- **Verify — 1tis9:** clean rename with no alias — 103 `wf_review_evidence` + 41 `wf_review_evidence_response` occurrences across 18 live files; extractor maps, renderer, and upgrade reconciliation updated; recipe fixed in BOTH seed 209 and the registered docstring; both sequence errors self-correct. Fresh-subprocess probe: 83 tools, `wf_review_event` present, `wf_review_evidence` absent.
- **Observe — history preserved:** closed wave records, prior telemetry rows, and the 1.14.0 CHANGELOG entry retain `wf_review_evidence` as point-in-time history; a new 1.15.0 CHANGELOG section documents the rename.
- **Gapfill:** the rename pass itself was scripted over an explicit file list rather than driven through MCP retrieval — bulk-mechanical token replacement where the raw residual census IS the verification artifact. Discovery, call-site reads, and all recipe/error edits used `code_keyword`/`code_read`.
- **Verify — gates:** full framework suite 6,200 tests across 59 files OK; `wf_validate_docs` clean; `framework_edit_allowed` and `seed_edit_allowed` opened only for their edits and closed immediately after.
- **Verify — post-restart live check (2026-07-25):** the operator restarted the MCP host and the client re-fetched the tool list. `wf_review_event` is callable and operated on wave 1tis8's real ledger (5 records, correct approval currency, `next_tools` emitting the new name); `wf_review_evidence` is gone from the client surface. This resolves the connected-client limitation recorded in the delivery approval, which had only been proven in a fresh subprocess.
- **Observe — `wf_memory_eval` unlocked a previously impossible measurement:** its first live call returned `available: true`. The curated real-corpus pass had never run before (wave 1tbt5 recorded "curated semantic scoring unavailable to the standalone interpreter"), because the standalone CLI could not load the semantic backend; the MCP server can. On the real 38-record corpus (12 sampled): baseline recall@3 1.0 / MRR 0.9167, semantic-only identical, candidate fusion 0.25 / 0.2586 exactly matching lexical-only. This is direct real-corpus evidence CONFIRMING the `1sufn` adoption-gate rejection: the lexical stream drags fusion far below the shipped order. Aggregate-only privacy held (no ids, summaries, or bodies).
- **Repair — delivery-review blocking P2 (2026-07-25):** an independent reviewer found that `run_curated` rebound the shared `index_state_store.file_commit_times` global and restored it in a `finally`. Harmless in the old single-shot CLI process; corrupting once relocated into the long-lived server — two overlapping `wf_memory_eval` calls restore out of order, leaving one call's frozen-subset lambda installed permanently, while unrelated concurrent `memory_search` readers observe the replacement. A tool-level lock would NOT have sufficed because the corruption is visible to readers that never take the lock, so the shared mutation was removed outright: `_memory_ranked` gained `commit_times_override`, threaded through the eval's ranking helpers, and the hermetic `run()` now seeds its throwaway store through the canonical `apply_freshness` writer instead of patching. Re-running the reviewer's own probe against the fixed code passes (both overlapping calls `available: true`, `restored_original: true`, 1,569,397,696 clean watcher samples, unrelated lookup non-empty — it returned `{}` before). Hermetic fingerprint and all four comparison metric sets byte-identical; full suite 6,202 OK. Chain terminal via repair_start + fresh independent code-reviewer reverification; delivery re-approved post-repair.
- **Observe — documentation reconciled with the shipped behaviour:** 1tgws Requirement 2 no longer claims the tool accepts a `root` argument, and 1tis7's Requirement 2 and risk row now describe the shipped placeholder-only guard rather than the withdrawn tracked-file screen.
- **Watchpoint for close:** the rename removes `wf_review_evidence` from the registered surface. A host restart (or client re-fetch of `tools/list`) is required before `wf_review_event` is callable. This session deliberately did NOT reload after the rename so the delivery evidence below could still be recorded; the operator-signoff and close steps will need the restarted host.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| concurrency-regression-vacuous-and-wrong-path | do_now | no | completed | wave-council-delivery |
| memory-eval-global-monkeypatch-concurrency | do_now | no | completed | wave-council-delivery |

*Machine review evidence — 31 records; 10 runs; 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 21 | 40,490 |
| implement | 14 | 350,453 |
| review | 140 | 3,745,496 |
| **Total** | **175** | **4,136,439** |

<!-- wave:context-efficiency-state {"generation":169,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":370023,"derived_artifact_credit":26,"direct_net":350453,"estimated_tokens_saved":350453,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":556,"response_debit":20613,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":21,"content_source_credit":52764,"derived_artifact_credit":1989,"direct_net":40490,"estimated_tokens_saved":40490,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1693,"response_debit":17835,"source_credit_count":8,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5265},"review":{"calls":140,"content_source_credit":3986848,"derived_artifact_credit":1789,"direct_net":3745496,"estimated_tokens_saved":3745496,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14451,"response_debit":231114,"source_credit_count":134,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2424}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":175,"content_source_credit":4409635,"derived_artifact_credit":3804,"direct_net":4136439,"estimated_tokens_saved":4136439,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16700,"response_debit":269562,"source_credit_count":146,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9262},"wave_id":"1tis8 memory-eval-mcp-tool-and-decision-log-target"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 2 | 539,240 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":539240,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
