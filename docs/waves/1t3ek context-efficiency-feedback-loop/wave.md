# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1t3ek context-efficiency-feedback-loop`
Title: Context Efficiency Feedback Loop

## Objective

Close the context-efficiency feedback loop: publish the implement-stage numbers at the review boundary so the delivery council reads current accounting, add the retrieval-posture sensor so MCP-first drift is caught by the framework instead of the operator, and fix the test that litters the working tree with cwd-relative memory-state artifacts.

## Changes

Change ID: `1t22z-enh context-efficiency-review-boundary-flush`
Change Status: `implemented`

Change ID: `1t230-enh implement-wave-retrieval-posture-sensor`
Change Status: `implemented`

Change ID: `1t231-bug test-writes-memory-state-outside-fixture`
Change Status: `implemented`

Change ID: `1t3el-enh multi-agent-open-wave-attribution`
Change Status: `implemented`

Change ID: `1t3s7-enh derived-artifact-credit-full-surface-debits`
Change Status: `implemented`

Change ID: `1t2zq-enh state-file-source-credit-artifact-tools`
Change Status: `implemented`

Change ID: `1t15a-enh digest-tool-credit-completion`
Change Status: `implemented`

Completed At: 2026-07-20

## Wave Summary

Wave `1t3ek` (Context Efficiency Feedback Loop) delivered 7 changes: Context Efficiency Review-Boundary Checkpoint Flush, Implement Wave Retrieval-Posture Sensor, Test Writes memory-state.sqlite Outside Its Fixture, Multi-Agent Open-Wave Attribution, Derived-Artifact Credit and Full-Surface Debits, State-File Source Credit for Artifact Tools, and Digest-Tool Credit Completion. Notable adjustments during implementation: Derived-Artifact Credit and Full-Surface Debits: Operator static review (two P1s against this change's wrapper): (1) credit floored once on the artifact aggregate instead of per artifact as this doc requires — repaired: extractors return per-artifact token lists, wrapper sums per-artifact floors, boundary-case regression test added; (2) artifact tools without an operation digest got uuid4 event ids so identical replays re-credited — repaired: stable sha256(tool+request+response) identity, replay/different-outcome regression test added. Typed chains cycle 4.

**Changes delivered:**

- **Context Efficiency Review-Boundary Checkpoint Flush** (`1t22z-enh context-efficiency-review-boundary-flush`) — 5 ACs completed. Key decisions: Requirement 4 resolved: keep the `_OBSERVATIONAL_TOOL` annotation unchanged and publish without a `flush` parameter — the annotation already declares `readOnlyHint: False`, so the checkpoint-block write is annotation-compatible.; AC-2/Requirement 3 refined: the publish boundary is "review ran" (`reached_review`: structured lane summary present), not "status ok" — a review reporting pending operator signoff is the NORMAL pre-close state and is exactly when the council reads the table.
- **Implement Wave Retrieval-Posture Sensor** (`1t230-enh implement-wave-retrieval-posture-sensor`) — 6 ACs completed
- **Test Writes memory-state.sqlite Outside Its Fixture** (`1t231-bug test-writes-memory-state-outside-fixture`) — 4 ACs completed. Key decisions: Root cause identified by per-test bisection: four `test_setup_wavefoundry` tests call `setup_wavefoundry.main([])` (cwd-default root) with render/index/dry-run mocked but `memory_backfill.ensure_run` UNMOCKED — the real gate call created `.wavefoundry/index/memory-state.sqlite` under whatever cwd the suite ran from (the scripts dir under `run_tests.py`), matching the observed stray row (`entry_path='setup'`, `inventory_pending`).; Fix is two layers: patch `ensure_run` in the class setUp AND sandbox the class cwd into a tempdir, so any future unmocked cwd-relative write lands in the sandbox rather than the repository. Recurrence guard added at the runner level (`run_tests.py` `stray_artifact_paths`/`_stray_artifact_failure`): a run that creates a nested `.wavefoundry` under the scripts dir fails with the offending paths listed; pre-existing artifacts are snapshotted so only run-created ones fail. Guard demonstrated against a seeded artifact by unit test.
- **Multi-Agent Open-Wave Attribution** (`1t3el-enh multi-agent-open-wave-attribution`) — 6 ACs completed. Key decisions: Provenance is an additive `attribution` column on telemetry_event ('focus'/'open_wave'/'adopted'), following the `source_credits_dropped` ALTER-migration precedent; no schema-version bump needed.; Stage derivation reads only wave-owned files (wave.md Status line, sibling events.jsonl delivery-run markers) with a 10s TTL cache keyed per root and an explicit test reset seam; any failure resolves to None and keeps general-bucket behavior.
- **Derived-Artifact Credit and Full-Surface Debits** (`1t3s7-enh derived-artifact-credit-full-surface-debits`) — 7 ACs completed. Key decisions: Instrumentation is a generic post-registration wrapping pass over the FastMCP registry (`_wrap_first_party_tool_costs`), not per-tool call-site edits: uninstrumented first-party tools get a debit recorder, artifact extractors are a small named map, lifecycle/retrieval tools are exempt by name, and every failure path is observational (the tool result is never altered).; `wf_create_wave` keeps only its lifecycle workflow proxy this pass; its generated wave.md/journal bodies are not artifact-credited yet. The `wf_new_*` scaffolds (no proxy) carry the artifact credit.
- **State-File Source Credit for Artifact Tools** (`1t2zq-enh state-file-source-credit-artifact-tools`) — 6 ACs completed
- **Digest-Tool Credit Completion** (`1t15a-enh digest-tool-credit-completion`) — 4 ACs completed. Key decisions: Listings and views credit the BOUNDED LIVE SET they enumerate: `wf_current_wave`/`wf_list_waves` credit non-closed listed waves, `wf_list_plans` its listed pending plans, `wf_map` its one resolved doc, `memory_search`/`memory_brief` the capped record files they surface (three-step operator refinement); `wf_get_change` bulk rows gained a structural `truncated` boolean; the extractor gates credit on `content and not truncated`
## Journal Watchpoints

- Watchpoint: `1t22z` and `1t230` both touch `server_impl.py` lifecycle call sites — sequence them, `1t22z` first so review-time wave.md numbers and the `1t230` envelope summary agree.
- Follow-up: `1t231`'s root cause is unknown until reproduced; if it lands in `server_impl.py`, it joins the sequencing constraint above.
- Blocking note: `1t230` thresholds must ship conservative defaults; advisory noise on legitimate bulk-mechanical waves would erode trust in the sensor.
- Watchpoint: `1t3el` (late-admitted) adds an additive store column and an open-wave resolver on the retrieval hot path; any resolver failure must fall back to today's general-bucket behavior, and adoption must reuse the existing once-only credit keys. Implemented after `1t22z`/`1t230` landed, so no sequencing race.
- Watchpoint: `1t3s7` (late-admitted post-delivery-review) changes the stage metric key set — every published checkpoint block needs the one-time re-render (the 1t3ld cleanup pattern), the new column must join the schema_ready fast-path check (the recorded 1t3ek gotcha), and a FRESH delivery cycle with a superseding council approval must follow implementation before close.
- Watchpoint: `1t2zq` (third late admission) builds on the landed 1t3s7 wrapper; credits ride the existing `_source_credits` commit path only (no new storage), containment and failure paths credit nothing, and a second superseding delivery approval must follow its implementation before close.
- Watchpoint: `1t15a` (fourth late admission) was refined three times mid-implementation by operator direction, settling on the bounded-enumeration boundary — wave/plan listings credit only the non-closed rows they enumerate (bounded by work in flight, never the closed-history tail), `wf_map` credits its one resolved doc, `wf_get_change` conveyed-content rows, `memory_search`/`memory_brief` the capped record files they surface, `memory_backfill` written records; `wf_sync_surfaces` is deferred for response enrichment. A fourth superseding delivery approval must follow before close.

## Participants

Review lanes assigned at Prepare (framework script changes, AC priority tables; policy: qa-reviewer required for bug fixes):

- code-reviewer (framework scripts: `server_impl.py`, `context_efficiency.py`, tests)
- qa-reviewer (required: bug fix `1t231` admitted; AC priority tables on all three docs)
- architecture-reviewer (lifecycle response-envelope and publication-timing changes)
- docs-contract-reviewer (implement-wave prompt/seed wording changes in `1t230`)
- security-reviewer (council fixed seat)
- reality-checker (council fixed seat)
- red-team (council adversarial primer)
- wave-council (moderator)

## Prepare Review Evidence

Council readiness pass, 2026-07-20, primer depth standard. Per-seat evidence:

- red-team (primer): strongest challenge is advisory noise killing the sensor's signal (rote Gapfill notes); best alternative hard-blocking, rejected for legitimate near-zero cases. Two primer questions issued (hermetic footprint census; observational-annotation tension).
- architecture-reviewer: no findings. Verified `wf_review_wave`'s call site passes no `flush` and carries the observational annotation, confirming both load-bearing `1t22z` claims; the annotation-vs-write tension is honestly deferred with named resolutions (Requirement 4).
- security-reviewer: no findings. No trust boundary; sensor reads existing store data only; footprint census local-only by requirement.
- qa-reviewer: no findings. `1t230` risk table mandates the injectable file-list seam for hermetic tests; `1t231` AC-1 refuses a fix without identifying the writer and AC-3 demands a demonstrated guard failure.
- reality-checker: no findings. Stray-artifact reproduction evidence concrete (one entry_path='setup' row timestamped mid-suite); motivating telemetry (implement stage: 1 call on 1t3gt) is in the sealed wave record.
- docs-contract-reviewer (rotating seat): no findings. Envelope text correctly forbids internal artifact IDs. Strongest alternative not taken: carry the directive in the MCP tool description instead of the response; rejected because descriptions inform tool selection, not agent reasoning at activation.

Delta readiness pass for late-admitted `1t3el` (multi-agent open-wave attribution), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is a hot-path resolver failure or latency regression on every retrieval call; answered by TTL caching plus unconditional fall-through to today's general-bucket behavior on any failure. Best alternative (per-agent focus handshake tools) rejected: requires every helper session to run lifecycle calls, which is the exact behavior that does not happen in practice.
- architecture-reviewer: no findings. Verified `_commit_event`'s focus fallback (`stage = focus.stage or "general"`), the sealed-wave redirect, and the `source_credits_dropped` additive-column migration precedent the provenance column will follow.
- security-reviewer: no findings. Resolver reads only repo-contained wave records and ledgers; no new trust boundary.
- qa-reviewer: no findings. Hermetic multi-producer scenarios enumerated in ACs (live peer, exited peer, none/ambiguous OPEN, replay dedup); cache needs an explicit test reset seam.
- reality-checker: no findings. The gap is operator-observed and store-confirmed (1t3gt implement: 1 call while multiple sessions worked; 227 adopted pre-wave events on the next wave's plan bucket).
- docs-contract-reviewer (rotating): no findings. `docs/references/context-efficiency.md` attribution section update is in-task; honest-labeling note stays.
- Verdict: PASS, unanimous, severity ceiling none. Readiness run and approval re-recorded to cover all four changes.

Delta readiness pass for late-admitted `1t3s7` (derived-artifact credit + full-surface debits), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is credit-type inflation drifting into the counterfactual overclaim the subsystem was designed to refuse; answered by the bright line (persisted textual artifacts only, verification tools debit-only) written into Requirement 4 and the reference-doc framing. Two primer questions (checkpoint key-set compatibility; replay identity) both pre-answered in the doc.
- architecture-reviewer: no findings. Verified against the tree: the checkpoint validator enforces an exact stage key set (so the one-time re-render is mandatory, per the 1t3ld pattern); `workflow_prompt_tokens` is the established per-event credit-column pattern the new column follows; `wf_review_evidence` responses carry a `request_digest` usable as replay-safe artifact identity.
- qa-reviewer: no findings. AC-5 mandates the stripped-current-store migration regression (the recorded schema_ready gotcha applied to its next customer); known-size fixtures make the credit arithmetic exactly assertable.
- reality-checker: no findings. The motivating gap is this wave's own ledger: the review phase made dozens of calls and the table noted three.
- security-reviewer / docs-contract-reviewer: no findings; no trust boundary; reference-doc taxonomy update is in-task.
- Verdict: PASS, unanimous, severity ceiling none. Readiness approval re-recorded to cover all five changes.

Delta readiness pass for late-admitted `1t2zq` (state-file source credit), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is self-dealing optics (each ledger write mints a new creditable version); answered in the risk table — each event genuinely obviates a fresh read of the grown authoritative ledger, the once-only key bounds it, and the semantics are documented plainly. Best alternative (counterfactual retry/schema credit) correctly stays behind paired evaluations.
- architecture-reviewer: no findings. The `_source_credits` commit path, once-only `(wave, phase, source, version)` key, and stat-signature versioning all exist and were verified against the tree; the change adds extractors, not storage.
- qa-reviewer: no findings. Dedup semantics (same version once, grown version again), no-read tools crediting nothing, and failure paths are each pinned as ACs with hermetic tests.
- reality-checker: no findings. The motivating measurement is grounded on this wave's own store (337 credited vs 7,400-token ledger reads performed by the tool).
- security-reviewer / docs-contract-reviewer: no findings; containment reuses the 1t3s7 pattern; taxonomy doc update in-task.
- Verdict: PASS, unanimous, severity ceiling none. Readiness approval re-recorded to cover all six changes.

Delta readiness pass for late-admitted `1t15a` (digest-tool credit completion), 2026-07-20:

- red-team (primer, standard depth): strongest challenge is the fixture-echo class recurring in the nine new extractors (an extractor assuming a response field that does not exist); answered by the task ordering — every response shape is verified against the real response builders before its extractor is written, and absent fields credit nothing.
- architecture-reviewer: no findings. The native path for the two code tools reuses `_record_retrieval_context`'s existing family routing (structural for risk_score, current-size for hover); the digest extractors reuse the landed 1t2zq machinery; no new storage or equation change.
- qa-reviewer: no findings. Exemption double-count risk pinned by extending the existing exemption test; dedup semantics inherited from the once-only key.
- reality-checker / security-reviewer / docs-contract-reviewer: no findings; the census update (18 to 20) and the digest boundary go to the reference doc.
- Verdict: PASS, unanimous, severity ceiling none. Readiness approval re-recorded to cover all seven changes.

## Delivery Review Evidence

Delivery review pass, 2026-07-20, primer depth full. Per-seat evidence:

- red-team (primer): strongest challenge is that accounting-layer changes verified only against fresh fixtures prove nothing about production stores; VINDICATED in-wave by the schema_ready finding, which exactly this kind of live-state probe caught. Primer questions (attribution correctness under multi-producer concurrency; migration safety on current stores) both answered with executed evidence.
- code-reviewer: ONE real finding, recorded through the typed ledger and repaired in-cycle: `schema-ready-fast-path-skips-additive-migration` (the fast path skipped additive-column migration on already-current stores; first attributed INSERT poisoned the live store). Fix bounded to the schema_ready column check with an inline invariant comment; regression test reconstructs the exact pre-fix state. Full chain: finding, repair_start (cycle 1), independent reverification (completed).
- qa-reviewer: reverified the repair independently against both the regression fixture and the real migrated store (durable persistence, open_wave provenance row, no gap marker). All ACs across the four changes carry executed evidence; no `[~]` markers; suite 6,008/6,008 on the final uncontended run.
- security-reviewer: no findings. The resolver reads only repo-contained files; attribution and adoption change no trust boundary; the manual poison repair touched only this repository's own sidecar store and is recorded in the Decision Log.
- reality-checker: no findings beyond the recorded one. Live verifications executed for every change: review-boundary publish (implement 16/606,849 appeared in wave.md mid-review), sensor silence with 15 retrieval calls on this MCP-first wave, stray-artifact guard green across three full-suite runs, helper-session attribution row on the live store. The shipped/canonical template parity break recurred via the gardener and was re-synced; flagged in the handoff as a candidate future change, not a defect of this wave's scope.
- docs-contract-reviewer (rotating seat): no findings. `docs/references/context-efficiency.md` now documents symmetric publication, the posture sensor, and open-wave/adoption attribution semantics with the honest-labeling caveat; seed 180 and the implement-wave prompt state the measured rule. Strongest alternative not taken: a store schema-version bump for the attribution column; rejected because the additive-ALTER precedent is the established migration pattern and the real defect was the fast-path check, not versioning.

Delta delivery pass for late-admitted `1t3s7`, 2026-07-20 (fresh cycle after the first delivery review):

- code-reviewer: no findings. The generic wrapper is observational end-to-end (every failure path returns the unaltered tool result); exemption set verified against the instrumented lifecycle/retrieval names; the new column joined the schema_ready check per the recorded gotcha, and the stripped-current-store regression covers both new columns.
- qa-reviewer: no findings. Known-size fixtures assert the credit arithmetic exactly (artifact minus request, floored); replay dedup proven via the stable `artifact:{digest}` identity; debit-only and no-double-count paths each pinned by test; suite 6,012/6,012 on the final uncontended run (one test_indexer interference flake excluded by isolated pass plus clean rerun, the documented pattern).
- reality-checker: no findings. All nine published checkpoint blocks re-rendered through the canonical renderer, docs-lint clean corpus-wide; the wave.md two-column projection is unchanged, with the new credit folded into estimated savings.
- security-reviewer / docs-contract-reviewer: no findings. Artifact-size reads are containment-checked under the repo root; the reference doc states the non-counterfactual bright line explicitly.
- Verdict: PASS, unanimous, severity ceiling none. A superseding `wave-council-delivery` approval covering all five changes follows this pass.

Delta delivery pass for late-admitted `1t2zq`, 2026-07-20 (second superseding cycle):

- code-reviewer: no findings. Credits ride the canonical source-proof machinery unchanged (live proofs, stat-signature versions, opaque ids); the wrapper stays observational; no new storage.
- qa-reviewer: no findings. The dedup test proves once-per-version semantics including the grown-ledger fresh credit; no-read tools and escape paths pinned credit-free; suite 6,014/6,014.
- reality-checker / security-reviewer / docs-contract-reviewer: no findings. Containment reuses the established checks; the reference doc states the avoided-reading bright line.
- Verdict: PASS, unanimous, severity ceiling none. A second superseding `wave-council-delivery` approval covering all six changes follows.

## Review Checkpoints

- pre-implementation-review: passed (2026-07-20) — highest risks: (1) the `1t22z` observational-annotation vs projection-write decision, resolved during implementation with rationale in the Decision Log; (2) `1t230` threshold noise, mitigated by fire-only-on-zero-retrieval conservative defaults; (3) `1t231` unknown root cause, time-boxed reproduction first; (4) this wave IS the retrieval-posture wave, so implementation itself follows MCP-first exploration and records a Gapfill note for any bulk-mechanical fallback. Order: 1t22z, then 1t230, then 1t231 (single builder lane; shared `server_impl.py`).
- **Prepare-phase Wave Council [prepare-council] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: advisory noise on legitimate bulk-mechanical waves would teach agents rote Gapfill notes and kill the sensor signal, answered with conservative defaults and explain-or-fix framing; strongest-alternative: carry the retrieval directive in the MCP tool description instead of the response envelope, rejected because descriptions inform tool selection rather than agent reasoning at activation)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| artifact-credit-floors-aggregate-not-per-artifact | do_now | no | completed | — |
| artifact-replay-uuid-event-ids-recredit | do_now | no | completed | — |
| hover-census-keys-path-but-envelope-names-file | do_now | no | completed | — |
| risk-score-request-arguments-incomplete | do_now | no | completed | — |
| schema-ready-fast-path-skips-additive-migration | do_now | no | completed | — |
| stage-derivation-marker-never-matches-compact-json | do_now | no | completed | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 71 records; 23 runs; 6 findings; current: do_now 6, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

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
| plan | 3 | 2,268 |
| implement | 32 | 651,254 |
| review | 60 | 819,720 |
| **Total** | **95** | **1,473,242** |

<!-- wave:context-efficiency-state {"generation":95,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":32,"content_source_credit":676129,"derived_artifact_credit":1851,"direct_net":651254,"estimated_tokens_saved":651254,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2924,"response_debit":25229,"source_credit_count":9,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1427},"plan":{"calls":3,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":2268,"estimated_tokens_saved":2268,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":33,"response_debit":896,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3197},"review":{"calls":60,"content_source_credit":880048,"derived_artifact_credit":6981,"direct_net":819720,"estimated_tokens_saved":819720,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14766,"response_debit":53578,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1035}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":95,"content_source_credit":1556177,"derived_artifact_credit":8832,"direct_net":1473242,"estimated_tokens_saved":1473242,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17723,"response_debit":79703,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5659},"wave_id":"1t3ek context-efficiency-feedback-loop"} -->
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
