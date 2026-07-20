# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1stwm memory-supply`
Title: Memory Supply

## Objective

Fix the binding constraint on the 1.13.0 agent-memory layer: an empty corpus. Add a tool that drafts candidate memory records from a wave's canonical `events.jsonl` review evidence (human-gated, never auto-promoted, conservative durable-signal selection per the council re-scope), the exact-duplicate detection that makes supply idempotent, and — grounded in the measured cost of the exploration each record captures — a separate, honestly-labeled "estimated exploration avoided" wave-metric category so the memory layer's largest value is visible without faking a measurement. Supply-first: retrieval quality (Wave B) is moot until records exist.

## Changes

Change ID: `1stwk-feat evidence-derived-memory-candidates`
Change Status: `implemented`

Change ID: `1stwl-enh memory-exact-duplicate-diagnostics`
Change Status: `implemented`

Change ID: `1svuk-enh estimated-exploration-avoided-category`
Change Status: `implemented`

Completed At: 2026-07-17

## Wave Summary

Wave `1stwm` (Memory Supply) delivered 3 changes: Evidence-derived memory candidates from the review ledger, Memory exact-duplicate diagnostics (detection only), and Estimated exploration-avoided — a separate, grounded wave-metric category. Notable adjustments during implementation: Estimated exploration-avoided — a separate, grounded wave-metric category: Implemented `exploration_avoided.py` (grounded formula `source_cost × bounded ATTRIBUTION_BASE × match_confidence`, disposable JSON sidecar, fail-isolated `credit_surface`), credit hooked at `wave_memory_brief` (telemetry-only, never alters advisory output), separate labeled block on `wave_current`/`wave_audit` with the causal caveat, reference doc. `wave.md` marker-block deferred (renderer out of scope; surfaced via tools). Full suite 5788 OK; docs-lint clean.

**Changes delivered:**

- **Evidence-derived memory candidates from the review ledger** (`1stwk-feat evidence-derived-memory-candidates`) — 10 ACs completed. Key decisions: Draft from `events.jsonl` heads + Decision Logs only; Write `candidate` only; operator reconcile to promote
- **Memory exact-duplicate diagnostics (detection only)** (`1stwl-enh memory-exact-duplicate-diagnostics`) — 5 ACs completed. Key decisions: Detection only, surfaced to operator; Exact/normalized signals, no similarity model
- **Estimated exploration-avoided — a separate, grounded wave-metric category** (`1svuk-enh estimated-exploration-avoided-category`) — 7 ACs completed. Key decisions: Ground the estimate in measured `source_exploration_cost`; Separate labeled category, never summed into measured tokens
## Journal Watchpoints

- `server_impl.py` / `memory_records.py` edited under `framework_edit_allowed`; open before editing, close immediately after.
- Sequencing: `1stwl` (dedup detector) is a dependency of `1stwk`'s idempotency (AC-5); land the detector or its interface first.
- Invariant watchpoint: both changes are strictly additive to the memory lifecycle — never auto-promote, supersede, merge, or delete (the `memory_records.py:8` never-auto-rewrite invariant); proposal writes `candidate` only, dedup is detection-only.
- Watchpoint: drafts source ONLY from the typed ledger + Decision Logs; no raw transcript/conversational ingestion (the explicit non-goal).
- Re-scope watchpoint (`1stwk`): draft CONSERVATIVELY — only durable-shaped signals (fragile_file/successful_pattern/lasting decision/real-defect repair), NOT every material finding; the conversational kinds (operator_preference/environment_gotcha) are structurally unavailable and left to native memory.
- `1svuk` watchpoint: the estimated-exploration-avoided category must stay a SEPARATE labeled estimate, grounded in the measured `source_exploration_cost` (never a constant), event-triggered on advisory surface (never accrues by existence), and NEVER summed into the measured `## Context Efficiency` total. Depends on `1stwk`'s source-cost stamping + the 1stwj telemetry store.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| exploration-estimate-repeat-and-match-inflation | do_now | yes | pending | wave-council-delivery |
| exploration-telemetry-authority-and-coverage | do_now | yes | pending | wave-council-delivery |
| memory-duplicate-idempotency-and-identity | do_now | yes | pending | wave-council-delivery |
| memory-supply-derivation-not-conservative-or-live | do_now | yes | pending | wave-council-delivery |
| memory-supply-response-honesty | do_now | yes | pending | wave-council-delivery |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 35 records; 12 runs; 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: re-prepared after the council review — the original `1stwk` could flood the corpus with low-value per-wave findings and could only feed the least-durable kinds; resolved by the conservative durable-signal re-scope (AC-7) + the explicit taxonomy limitation (conversational kinds ceded to native memory), and the memory arc's value is now visible via the grounded `1svuk` estimated-exploration-avoided category; strongest-alternative: passive transcript capture — rejected as the explicit non-goal, an injection surface, and a duplicate of native memory.)
- prepare-council seat — red-team: the re-scope answers the flood/low-value critique — drafting is now conservative (durable-shaped signals only) with the ledger-only taxonomy limitation stated. Write path stays candidate-only (`create_memory_record`/`write_memory_record`, atomic `open(...,"x")`) with reconcile as the only transition (never-auto-rewrite invariant `memory_records.py:8` holds). `1svuk` is honest by construction: grounded in the MEASURED `source_exploration_cost` (not a constant), event-triggered on advisory surface (never accrues by existence), a SEPARATE labeled estimate never summed into the measured token total, with a mandatory causal caveat and a telemetry-only invariance AC. Residual (not blocking): the attribution factor is a bounded judgment and surface≠use — both explicitly bounded/recorded.
- prepare-council seat — code-reviewer: verified the reuse surface — `current_synthesis_heads` (review_evidence.py:888), `MEMORY_KINDS`/`MEMORY_STATUSES`/`create_memory_record`/`load_memory_records`/`match_targets` present; `wave_memory_add_response` (server_impl.py:7790) is the pattern to follow; `1svuk` reuses the 1stwj telemetry store + the advisory surface + `search_docs` semantic-match. Dependency chain 1stwj (telemetry, implemented) → `1stwk` (stamps source cost) → `1svuk` (credits on surface) is sound. Precision for implementation: the 1stwj `## Context Efficiency` telemetry measures context-AVOIDED, not exploration-COST — so `source_exploration_cost` must pick a defined measured proxy from that telemetry (e.g. the source wave's total returned/consumed tokens), an implementation choice the doc should pin, not a missing foundation.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | withheld | blocking findings: memory-supply-derivation-not-conservative-or-live, memory-duplicate-idempotency-and-identity, memory-supply-response-honesty, exploration-estimate-repeat-and-match-inflation, exploration-telemetry-authority-and-coverage; unresolved lanes: code-reviewer, qa-reviewer | record independent reverification for code-reviewer, qa-reviewer, then re-approve wave-council-delivery |
| operator-signoff | withheld | blocking findings: memory-supply-derivation-not-conservative-or-live, memory-duplicate-idempotency-and-identity, memory-supply-response-honesty, exploration-estimate-repeat-and-match-inflation, exploration-telemetry-authority-and-coverage; unresolved lanes: code-reviewer, qa-reviewer | record independent reverification for code-reviewer, qa-reviewer, then re-approve operator-signoff |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-17 — supply-first, additive to the memory lifecycle (candidate-only writes, detection-only dedup, no auto-promote/supersede/delete), sourced only from the typed `events.jsonl` ledger + Decision Logs. The foundation exists in 1.13.0 (ledger, `review_evidence.py` reader, `memory_records.py` write path, `candidate` status). Internal dependency `1stwl → 1stwk` sequenced. No blocking concerns.
- operator-signoff: pending operator closure confirmation

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| implement | 15 | 336,956 |
| review | 5 | 0 |
| **Total** | **20** | **336,956** |

<!-- wave:context-efficiency-state {"generation":20,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":360253,"direct_net":336956,"estimated_tokens_saved":336956,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":453,"response_debit":24269,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"review":{"calls":5,"content_source_credit":0,"direct_net":-1005,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":49,"response_debit":1953,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":997}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":20,"content_source_credit":360253,"direct_net":335951,"estimated_tokens_saved":336956,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":502,"response_debit":26222,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2422},"wave_id":"1stwm memory-supply"} -->
<!-- wave:context-efficiency end -->
