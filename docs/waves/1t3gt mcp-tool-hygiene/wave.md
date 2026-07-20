# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-20
review-evidence-source: events.jsonl

wave-id: `1t3gt mcp-tool-hygiene`
Title: Mcp Tool Hygiene

## Objective

Clean up MCP tool-surface hygiene: rename the `wave_*` tool prefix so it splits by what a tool
actually operates on (`wf_` general/lifecycle, `memory_`, `index_`), and fix the CLI `--root`
default in `memory_backfill.py`/`memory_cli.py` that let a stray index artifact get created
outside the repo root.

## Changes

Change ID: `1t1b3-bug memory-cli-root-default-cwd-not-repo`
Change Status: `complete`

Change ID: `1t3gs-ref mcp-tool-prefix-rename`
Change Status: `complete`

Change ID: `1t3gu-bug wave-scaffold-lint-valid-from-creation`
Change Status: `complete`

Change ID: `1t3ld-enh context-efficiency-three-stage-model`
Change Status: `complete`

Completed At: 2026-07-20

## Wave Summary

Wave `1t3gt` (Mcp Tool Hygiene) delivered 4 changes: Memory CLI Root Defaults to CWD, Not Repo Root, MCP Tool Prefix Rename: wave_ → wf_ / memory_ / index_, Wave Scaffold Must Be Lint-Valid From Creation, and Context Efficiency Three-Stage Model.

**Changes delivered:**

- **Memory CLI Root Defaults to CWD, Not Repo Root** (`1t1b3-bug memory-cli-root-default-cwd-not-repo`) — 4 ACs completed
- **MCP Tool Prefix Rename: wave_ → wf_ / memory_ / index_** (`1t3gs-ref mcp-tool-prefix-rename`) — 7 ACs completed. Key decisions: Council readiness fix: AC-5 sweep scope aligned to Requirement 10 (repo-wide minus historical archives); named surfaces corrected after code-grounded verification found `workflow-config.json`, rendered hooks, and the memory README carry old-name references while `.claude/agents` allowlists do not.; Implementer must re-derive the live `@mcp.tool` registration list and diff it against this doc's rename table before editing.
- **Wave Scaffold Must Be Lint-Valid From Creation** (`1t3gu-bug wave-scaffold-lint-valid-from-creation`) — 5 ACs completed. Key decisions: Audit result: the `wf_new_*` change-doc template and the co-created journal stub are clean — all four change-doc creations this session returned `lint.clean: true` at creation, and the new creation-lint regression test exercises the journal stub through docs-lint `--changed` on the create path. No fix needed (audit-and-skip).; Baking the review-status block into the scaffold surfaced a latent contract interaction: the 1t3dm freshness contract requires the projection to be re-rendered whenever a wave.md edit changes the derived signoff keys (e.g. adding a Participants table or prose signoffs), and one legacy prose-flow test relied on the block being absent. Kept 1t3dm's strict contract; fixed the test to reconcile via `_project_current_review_status` after its text mutations. An empty-ledger staleness tolerance was prototyped and REVERTED: 1t3dm's own tests assert strictness with an empty ledger, and weakening a two-day-old shipped contract inside a hygiene wave is silent scope expansion.
- **Context Efficiency Three-Stage Model** (`1t3ld-enh context-efficiency-three-stage-model`) — 5 ACs completed. Key decisions: Manual history cleanup executed as: one-time SQL canonicalization of the live store (telemetry_event/source_credit stage+phase_id: pre-wave/prepare to plan, close to review; 8 waves affected) plus re-rendering each affected wave.md checkpoint block through the canonical normalizer/renderer with merged stage sums.
## Journal Watchpoints

- Watchpoint: `1t3gs` must land as a single coordinated pass over `server_impl.py`/`server.py`
  — both files are shared and carry most of the 47 renames plus dozens of internal
  cross-references; do not split the rename across parallel editors.
- `1t3gs` docs/seed/allowlist updates are a follow-up step that comes after the finalized code
  rename, not run concurrently against it.
- After `1t3gs` lands, the MCP server needs a reload and this session (and any other live agent
  session) needs to reconnect to pick up the renamed tools — do not treat a stale tool list as a
  blocking failure, just reconnect.
- `1t1b3` is independent of `1t3gs` (different files, different subsystem) and has no ordering
  dependency on it.
- Watchpoint: `1t3gu` also edits `server_impl.py` (`create_wave` scaffold) — sequence it fully
  before or fully after the `1t3gs` rename pass, never concurrently.
- Watchpoint: `1t3ld` is the third change touching `server_impl.py` (the five `focus_stage`
  stamp sites) — all `server_impl.py`-touching changes in this wave sequence one at a time,
  never concurrently.

## Participants

Review lanes assigned at Prepare (tier 1 triggers: framework script changes, AC priority tables, MCP tool contract change; policy: qa-reviewer required for bug fixes):

- code-reviewer (framework scripts: `server_impl.py`, `server.py`, `memory_backfill.py`, `memory_cli.py`)
- qa-reviewer (required: two bug-fix changes admitted; AC priority tables on all three docs)
- architecture-reviewer (MCP tool contract change: 47-tool rename plus prefix invariant)
- docs-contract-reviewer (seed and prompt surfaces: 23 seed files, 16 prompt docs reference renamed tools)
- security-reviewer (council fixed seat; 1t1b3 touches path resolution)
- reality-checker (council fixed seat)
- red-team (council adversarial primer)
- wave-council (moderator)

## Prepare Review Evidence

Council readiness pass, 2026-07-20, primer depth full. Per-seat evidence:

- red-team (primer): strongest challenge is sweep completeness; the stale-listing phantom tool (`wave_setup_resume_after_memory`) proves reference lists drift. Three primer questions issued (sweep scope, table-vs-registration authority, `server_impl.py` ordering between 1t3gs and 1t3gu).
- architecture-reviewer: one moderate finding, AC-5 directory allowlist contradicted Requirement 10 repo-wide sweep, and named surfaces were wrong in both directions (`workflow-config.json`, rendered hooks, and memory README carry old names; `.claude/agents` allowlists do not). Fixed in-session in the 1t3gs doc (see its Decision Log). Prefix guard and reload-survivor sites verified at `server_impl.py:213`, `server_impl.py:2700`, `server.py:446`, `server.py:83`.
- security-reviewer: no findings. 1t3gs is a pure rename with no trust-boundary change; 1t1b3's containment/symlink checks in `memory_backfill._connect` verified independent of root resolution; watchpoint recorded that the shared root helper must keep the workflow-config marker check before trusting env vars.
- qa-reviewer: no findings. Both 1t3gu defects reproduced from this session's own tool output; recommends implementer re-derive the live registration list before editing (adopted into 1t3gs Decision Log).
- reality-checker: no findings. 61-tool census independently reconciled against live registrations; change ordering for the two `server_impl.py`-touching changes confirmed present as a wave watchpoint.
- docs-contract-reviewer (rotating seat): no findings. Strongest alternative not taken is a two-release alias transition; rejected because alias machinery cost exceeds benefit for a local-only tool surface whose consumers reconnect. Seeds-first update path confirmed in scope.

Delta readiness pass for late-admitted `1t3ld` (context-efficiency three-stage model), 2026-07-20:

- All five `focus_stage` stamp sites verified against the tree (`server_impl.py:23009/23104/23164/23338/23418`), the adoption-path stamp at `context_efficiency.py:1415-1440`, the `general` fallback at `context_efficiency.py:1004/1017`, and `_STAGE_KEYS` at `context_efficiency.py:1520` confirmed to name metric fields, not stage names.
- Scope was deliberately narrowed by operator direction during this pass: no historical-data migration or read-side legacy mapping; write-time vocabulary plus stamp-site updates only.
- Seats concur no new trust boundary, no contract change beyond the stage vocabulary, and the only cross-change coupling is the shared `server_impl.py` file, covered by the sequencing watchpoint. No findings.

## Delivery Review Evidence

Delivery review pass, 2026-07-20, primer depth full. Per-seat evidence:

- red-team (primer): strongest challenge is approving a deterministic transformation on the implementer's own audit; answered by oracle-diverse executed evidence (canonical suite 5,990, fresh-process exact-set tools/list oracle, repo-wide sweep, store census). Three primer questions issued (old-name reachability, config-key preservation, history-cleanup consistency).
- code-reviewer: no findings. Exact-set oracle matched all three namespaces; `repo_root.py` is the single discovery source; the reverted empty-ledger tolerance left no residue (strict-contract tests green).
- qa-reviewer: no findings on delivered behavior. All required AC rows carry executed evidence; no `[~]` markers. Observation (dispositioned): implement-stage retrieval posture was near zero; operator caught it live; framework response drafted as `1t22z`/`1t230` in docs/plans. Not a defect of the delivered changes.
- security-reviewer: no findings. `wave_review`/`wave_implement` survive only as workflow-config keys (verified by residual census); no trust-boundary change; `repo_root.py` keeps the marker check before honoring env vars.
- reality-checker: no findings. Store census shows only canonical stages plus internal `general`; the 8 re-rendered wave records pass docs-lint with totals preserved; the lone full-suite `test_indexer` failure reproduced as concurrency interference (passes isolated and on the final uncontended run).
- docs-contract-reviewer (rotating seat): no findings. Seeds, prompts, install templates, and shipped/canonical parity all updated (byte-parity test green). Strongest alternative not taken: re-render host surfaces via `wf_sync_surfaces` instead of direct edits; moot since render-parity tests pass.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-20: PASS WITH NOTES** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: sweep completeness is the load-bearing risk, a stale listing already produced one phantom tool, so the live registration set rather than the doc table is the rename authority; strongest-alternative: two-release alias transition for target-repo operators, rejected because alias machinery cost exceeds benefit for a local-only surface whose consumers reconnect)
- Notes: verdict was pass-with-conditions with a single condition (AC-5 sweep-scope fix in 1t3gs), applied in-session before the readiness signoff was recorded. Seat agreement unanimous, severity ceiling medium.
- Notes (delta, 2026-07-20): late-admitted `1t3ld` reviewed in a delta pass (see Prepare Review Evidence); no findings, verdict unchanged. Readiness run and approval re-recorded to cover all four changes.
- **Delivery-phase Wave Council [delivery-council] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, code-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; material-disagreements: none, seat agreement unanimous, severity ceiling none; strongest-challenge: deterministic-transformation delivery must not rest on the implementer's own audit, answered with executed oracle-diverse evidence; strongest-alternative: host-surface re-render via wf_sync_surfaces instead of direct edits, moot under green render-parity tests). Prior prepare-council verdict confirmed structured and machine-readable. AC scope gap check: no important/nice-to-have items outside admitted scope surfaced; no not-this-scope deferrals recorded. `wave-council-delivery` recorded in the evidence ledger.
- Observation (dispositioned, not a finding): implement-stage retrieval posture near zero during this wave's implementation; operator-caught; framework response drafted as `1t22z` (review-boundary checkpoint flush) and `1t230` (retrieval-posture sensor) in docs/plans for a future wave.
- Docs-contract review: performed — `docs/specs/mcp-tool-surface.md` changed during the wave; docs-contract-reviewer ran as the rotating seat in both council passes (readiness and delivery) with no findings; shipped/canonical template byte-parity test green.
- pre-implementation-review: passed (2026-07-20) — highest risk is sweep completeness on the 47-tool rename; addressed by re-deriving the live registration list before editing, renaming internal `*_response` helpers so no old-name substrings survive, and the repo-wide AC-5 grep. Implementation order: 1t1b3, then 1t3gs, then 1t3gu, then 1t3ld (single builder lane, sequenced over the shared `server_impl.py`). Builder lane: coordinator-implemented inline; parallel lanes rejected because every change but 1t1b3 serializes on `server_impl.py`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 7 records; 3 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
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

- operator-signoff: approved 2026-07-20 (operator requested closure in-session)

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 234 | 2,078,570 |
| implement | 1 | 939 |
| review | 4 | 0 |
| **Total** | **239** | **2,079,509** |

<!-- wave:context-efficiency-state {"generation":14,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":1,"content_source_credit":0,"direct_net":939,"estimated_tokens_saved":939,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9,"response_debit":477,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1425},"plan":{"calls":234,"content_source_credit":2656991,"direct_net":2078570,"estimated_tokens_saved":2078570,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7886,"response_debit":575784,"source_credit_count":159,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5249},"review":{"calls":4,"content_source_credit":0,"direct_net":-2109,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":40,"response_debit":3104,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1035}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":239,"content_source_credit":2656991,"direct_net":2077400,"estimated_tokens_saved":2079509,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7935,"response_debit":579365,"source_credit_count":159,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7709},"wave_id":"1t3gt mcp-tool-hygiene"} -->
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
