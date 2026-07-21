# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1t72b ce-hardening-and-paired-eval`
Title: Context-Efficiency Hardening and Paired Evaluation

## Objective

Harden the residue the 1t3ek arc exposed and open the counterfactual half of the accounting: serialize the test suite against the background indexer (three false FAILEDs in one day), stop memory_propose drafting wrong-target advisories, give wf_sync_surfaces a structured written-file manifest (closing the recorded 1t15a credit deferral), and make the paired-evaluation gate reachable with a scorer-derived scaffold and protocol guide.

## Changes

Change ID: `1t727-bug suite-indexer-interference`
Change Status: `implemented`

Change ID: `1t728-bug memory-propose-target-misattribution`
Change Status: `implemented`

Change ID: `1t729-enh sync-surfaces-written-manifest`
Change Status: `implemented`

Change ID: `1t72a-enh paired-evaluation-scaffold`
Change Status: `implemented`

Change ID: `1t67p-enh posture-loop-full-coverage`
Change Status: `implemented`

Change ID: `1t6p8-enh upgrade-reconciliation-tool-renames`
Change Status: `implemented`

Completed At: 2026-07-20

## Wave Summary

Wave `1t72b` (Context-Efficiency Hardening and Paired Evaluation) delivered 6 changes: Test Suite vs Background Indexer Interference, Memory Propose Draws Targets From the Verification Command, Sync Surfaces Reports a Structured Written-File Manifest, Paired-Evaluation Scaffold: Making the Counterfactual Measurable, Retrieval-Posture Loop: Full Activation Coverage and Honest Counting, and Upgrade Reconciliation Covers the MCP Tool Renames. Notable adjustments during implementation: Upgrade Reconciliation Covers the MCP Tool Renames: The pre-channels self-host guard (`NoLiveReferenceToRetiredWrapperTests`) failed the suite on the two operator-owned allow-rule flags — it asserted BOTH channels empty. Scoped it to the editable channel per the channel design (host findings surface at upgrade time, never gate the suite on operator-owned files) and fixed its formatting to use the `matched` field.

**Changes delivered:**

- **Test Suite vs Background Indexer Interference** (`1t727-bug suite-indexer-interference`) — 3 ACs completed. Key decisions: Both exclusion directions implemented as defense-in-depth after a dry bounded reproduction (3 configurations, all green); Build-side deferral lives INSIDE `_index_build_lock` (the chokepoint), covering every build caller; timeout PROCEEDS rather than cancels
- **Memory Propose Draws Targets From the Verification Command** (`1t728-bug memory-propose-target-misattribution`) — 4 ACs completed. Key decisions: Targets come from `public_path` + `artifact_or_test_id` only; `command_or_fixture` dropped from target extraction
- **Sync Surfaces Reports a Structured Written-File Manifest** (`1t729-enh sync-surfaces-written-manifest`) — 4 ACs completed. Key decisions: Manifest records only NEW-OR-CHANGED content (byte comparison inside the write chokepoint); writes still always happen; `render_agent_surfaces`' changed-only return value merges into the manifest rather than instrumenting its writers
- **Paired-Evaluation Scaffold: Making the Counterfactual Measurable** (`1t72a-enh paired-evaluation-scaffold`) — 4 ACs completed. Key decisions: Arm/pair field sets lifted to scorer module constants (`ARM_KEYS`, `PAIR_KEYS`) used by BOTH the validator and the scaffold generator; Placeholders are deliberately invalid (empty ids, negative token counts, incomplete arms) so score_pairs REJECTS an unfilled scaffold
- **Retrieval-Posture Loop: Full Activation Coverage and Honest Counting** (`1t67p-enh posture-loop-full-coverage`) — 4 ACs completed. Key decisions: The gap DECISION counts only the code-retrieval census; the telemetry summary keeps unfiltered totals; `implement_stage_retrieval_calls` gains an optional `tool_names` filter rather than a second function
- **Upgrade Reconciliation Covers the MCP Tool Renames** (`1t6p8-enh upgrade-reconciliation-tool-renames`) — 6 ACs completed. Key decisions: The map holds 61 renames, not the 47 the 1t3gs header claimed; Bare-token matching skips `wave_review`/`wave_implement`; only their `mcp__wavefoundry__` form flags
## Journal Watchpoints

- Watchpoint: `1t729` and `1t72a` both edit `server_impl.py` — sequence their edits; the file carries an active fragile-file advisory for the credit instrumentation (four repairs in 1t3ek), so every extractor/census claim needs a canonical-producer test and a live post-reload probe.
- Blocking note: `1t727` accepts no fix without an identified mechanism (the 1t231 precedent); if reproduction stays dry after a bounded effort, that outcome is recorded honestly and the exclusion justified as defense-in-depth.
- Watchpoint: `1t72a` must not weaken the scorer's gate — the scaffold's placeholders must FAIL scoring until genuinely filled, asserted by test.
- Watchpoint: `1t727` edits `run_tests.py`, which carries the 1t231 stray-artifact guard; its snapshot semantics must remain intact.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| agent-surfaces-report-unchanged-files-as-written | do_now | no | completed | — |
| suite-indexer-exclusion-toctou-race | do_now | no | completed | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 28 records; 8 runs; 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Participants

Review lanes assigned at Prepare (framework script changes; policy: qa-reviewer required for bug fixes):

- code-reviewer (framework scripts: `run_tests.py`, `indexer` spawn path, `memory_supply.py`, `render_platform_surfaces.py`, `server_impl.py`, tests)
- qa-reviewer (required: bug fixes `1t727`/`1t728` admitted; hermetic-testability of the exclusion and the canonical-producer fixtures)
- architecture-reviewer (response-shape change in `run_sync_surfaces`; eval-tool mode addition)
- docs-contract-reviewer (`1t72a` protocol reference doc + cross-links)
- security-reviewer (council fixed seat)
- reality-checker (council fixed seat)
- red-team (council adversarial primer)
- wave-council (moderator)

## Prepare Review Evidence

Council readiness pass, 2026-07-20, primer depth standard. Per-seat evidence:

- red-team (primer): strongest challenge is `1t727` fixing by serialization without understanding — masking a real indexer defect behind an exclusion; countered by AC-1's root-cause-first requirement (no fix without a named mechanism, honest defense-in-depth fallback recorded if reproduction stays dry). Second challenge: `1t72a`'s scaffold weakening the scorer gate via placeholders that accidentally qualify; countered by AC-2 asserting the unfilled scaffold is REJECTED by the real scorer. Deadlock probe on 1t727 answered: deferral is spawn-time, waits are bounded with holder-naming diagnostics, no lock cycle exists.
- architecture-reviewer: no findings. Verified `files_written` has exactly one producer and zero consumers (code_keyword census), so retiring it for `written` is a safe shape change; `mode='scaffold'` slots into the existing eval-mode dispatch without touching attach/revoke semantics.
- security-reviewer: no findings. No trust boundary changes; the scaffold writes only repo-contained files through the existing containment-checked path; renderer manifest carries repo-relative paths only.
- qa-reviewer: no findings. `1t727` has the `test_run_tests_lock.py` seam precedent for hermetic lock simulation; `1t728`/`1t729` ACs mandate canonical-producer fixtures (the 1t3ek fixture-echo lesson, four instances); `server_impl.py` carries an active fragile-file advisory requiring live post-reload probes for extractor claims.
- reality-checker: no findings. Motivating evidence is concrete and same-day: three false FAILED (test_indexer) runs on 2026-07-20; the wrong `run_tests.py` fragile-file draft live-corrected via memory_validate rewrite; the 1t15a Decision Log deferral naming the missing file list; a scorer with validation but no production path.
- docs-contract-reviewer (rotating seat): no findings. `1t72a` adds one reference doc with cross-links from the context-efficiency contract doc; the protocol doc must state the residual is the only sanctioned counterfactual channel, matching the shipped ledger language.

Delta readiness pass for late-admitted `1t67p` (posture-loop full coverage), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is directive fatigue — serving the posture block on every open path could train agents to skim it; answered: it already ships on wf_implement_wave and the bypass paths are the anomaly, not the directive. Second challenge: filtering the sensor count could hide legitimate non-code retrieval work; answered: the telemetry summary keeps overall totals — only the gap DECISION uses the census filter.
- architecture-reviewer: no findings. The directive constant is shared (no duplication); the census filter references `_CONTEXT_RETRIEVAL_TOOLS`, which the registration census test already pins against drift.
- qa-reviewer: no findings. AC-2 mandates reproducing the exact live masking scenario (a stage whose only retrieval row is wf_sync_surfaces).
- reality-checker: no findings. Both holes are live-demonstrated on this wave's own store (implement stage: 1 call, wf_sync_surfaces, sensor silent).
- security-reviewer / docs-contract-reviewer: no findings (no boundary change; one reference-doc counting note).

Delta readiness pass for late-admitted `1t6p8` (upgrade reconciliation tool renames), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is bare-token over-flagging — prose that legitimately mentions old names (migration guides, historical notes) becoming false edit instructions; answered by the existing exclusion set (CHANGELOG/waves/journals plus the new memory-dir exclusion) and the config-key carve-out for `wave_review`/`wave_implement` whose false flagging would actively break target configs (AC-3 pins it). Second challenge: a hand-copied rename map drifting from the shipped tool surface — the same fixture-echo class that bit this arc four times; answered by AC-1's two-directional oracle against the live registration census.
- architecture-reviewer: no findings. The map co-locates with the existing retired-surface table (the one-map convention the scan already imports); channel semantics (editable vs host-permission) reuse the existing partition unchanged.
- qa-reviewer: no findings. AC-3 pins the sharpest boundary pair (`wave_index_build` inside `wave_index_build_status`); AC-4 requires the live self-repo scan as the end-to-end oracle.
- security-reviewer: no findings. Report-only scan, no new write paths; host permission files remain operator-flag-only.
- reality-checker: no findings. The hazard is same-day live-demonstrated: the self-repo sweep found two live agent surfaces still naming old tools despite the 1t3gs rename claiming full coverage.
- docs-contract-reviewer (rotating): no findings. The seed restart callout states the boundary generically with the public 1.14.0 version reference (no internal artifact IDs).

## Review Checkpoints

- **Delivery-phase Wave Council [wave-council-delivery] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the live-caught manifest defect showed the Guru-less hermetic fixture was blind to the agent-surfaces path — answered by the strengthened Guru-enabled fixture that now reproduces the find hermetically, the net-change repair, and the post-reload double-probe returning written: [] with zero credit; strongest-alternative: retroactively repair the one pre-repair overstated credit row (2,220 tokens) — rejected per the no-retroactive-edit precedent, disclosed in the reverification instead. Per-seat: code-reviewer verified all four changes' sites against the tree (exclusion both directions with bounded waits, target-source narrowing, manifest chokepoint recording, scorer-constant-derived scaffold), no findings; qa-reviewer confirmed canonical-producer fixtures throughout and suite 6,036/6,036 on the final tree; reality-checker executed the live probes (sync double-run empty manifest + zero credit; memory_propose on this wave's own repaired finding drafts nothing false — the honest no-anchor gap; run_tests exercised its own build-wait guard on every suite run); security-reviewer: no trust-boundary changes, scaffold and manifest paths containment-checked; red-team: exclusion-masking challenge answered by the recorded dry-reproduction evidence and the honest defense-in-depth AC-1 disposition; docs-contract-reviewer: protocol doc cross-linked both ways, census updated for the sync manifest credit)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1t727 could fix by serialization without understanding, masking a real indexer defect — countered by the AC-1 root-cause-first requirement with an honest defense-in-depth fallback; strongest-alternative: fold the paired-eval scaffold into documentation only (no mode) — rejected because a hand-authored artifact against a validator-only schema is exactly the parallel-schema drift the scorer-derived scaffold eliminates)

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 29 | 830,593 |
| implement | 1 | 2,122 |
| review | 63 | 451,959 |
| **Total** | **93** | **1,284,674** |

<!-- wave:context-efficiency-state {"generation":85,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"derived_artifact_credit":2220,"direct_net":2122,"estimated_tokens_saved":2122,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4,"response_debit":94,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":29,"content_source_credit":840885,"derived_artifact_credit":2265,"direct_net":830593,"estimated_tokens_saved":830593,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1073,"response_debit":14681,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3197},"review":{"calls":63,"content_source_credit":496413,"derived_artifact_credit":2319,"direct_net":451959,"estimated_tokens_saved":451959,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10132,"response_debit":37676,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1035}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":93,"content_source_credit":1337298,"derived_artifact_credit":6804,"direct_net":1284674,"estimated_tokens_saved":1284674,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11209,"response_debit":52451,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4232},"wave_id":"1t72b ce-hardening-and-paired-eval"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
