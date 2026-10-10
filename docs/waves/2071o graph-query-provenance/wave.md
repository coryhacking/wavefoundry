# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-10-09
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2071o graph-query-provenance`
Title: Graph Query Provenance

## Objective

Make graph hierarchy locations reflect persisted call expressions and restore non-exact symbol lookup in Rust-containing graphs. Readiness only in this session; implementation waits for a later instruction.

## Changes

Change ID: `2073s-bug hierarchy-call-site-provenance`
Change Status: `planned`
Depends On: `2073t-bug rust-symbol-lookup-name-error`

Change ID: `2073t-bug rust-symbol-lookup-name-error`
Change Status: `planned`

## Participants

- Coordinator: root
- Write-owning roles: implementer for code, wave-coordinator for lifecycle/docs integration
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer
- Council: isolated red-team primer; architecture, security, QA and reality fixed seats; performance rotating fifth; independent council-chair synthesis

## Wave Summary

Two admitted bug repairs: hierarchy call-site provenance and the shared Rust symbol-lookup regex binding. Plans preserve outgoing definition-line fields, edge counts, legacy Java filtering and existing resolver ambiguity semantics.

## Watchpoints

- Watchpoint: no implementation/opening/closure/commit/push/package authorization in the current request. Existing paused2071n and unrelated dirty work are preserved.
- Graph callgraph provenance was fixed earlier; hierarchy remains a distinct defective query path.
- Indexed coordinates are source-version provenance; snippets require proven freshness, otherwise null. Legacy missing sites never justify name-only guesses.
- Do not confuse caller edge counts with invocation occurrence counts.
- Source and baseline captures are under evidence/readiness; probe source is a non-executed archival text capture, not a shipped test.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| council-delivery | pending | no current executed approval | record approval evidence for council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| architecture-reviewer | pending | no current executed approval | record approval evidence for architecture-reviewer |
| docs-contract-reviewer | pending | no current executed approval | record approval evidence for docs-contract-reviewer |
| performance-reviewer | pending | no current executed approval | record approval evidence for performance-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Hierarchy repair follows the resolver repair so bare-symbol impact analysis can operate during implementation. Shared retrieval tests have one write owner.
- No external wave dependency; wave2071p can be readied independently. Only one wave is opened at implementation time.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 361 | 1,009,627 |
| review | 3 | 0 |
| **Total** | **364** | **1,009,627** |

<!-- wave:context-efficiency-state {"generation":20,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":361,"content_source_credit":2399323,"derived_artifact_credit":1149,"direct_net":1009627,"estimated_tokens_saved":1009627,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19429,"response_debit":1375221,"source_credit_count":77,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":3,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-8270,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":45,"response_debit":8225,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":364,"content_source_credit":2399323,"derived_artifact_credit":1149,"direct_net":1001357,"estimated_tokens_saved":1009627,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19474,"response_debit":1383446,"source_credit_count":77,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"wave_id":"2071o graph-query-provenance"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

- Current source packet has14 content hashes; no source repair has been made. Exact node IDs work while the confirmed non-exact Rust scan fails.
- Existing stored call_sites suffice; no extraction/schema migration is admitted.

## Outputs produced or expected

- Two wave-owned complete plans with required/justified ACs and unchanged unchecked delivery tasks.
- Typed current readiness approvals and successful Prepare-ready; implementation and delivery evidence come later.

## Review checkpoints

### Planning and review scope — 2026-10-09

Optional Review plan: self-answered location authority from current stored graph and served-handler probe; preserve outgoing definition fields from the MCP spec; use nullable snippets when source identity is unavailable; retain exact-ID/ambiguity semantics. Operator questions: none. Stop condition: all Requirements/Scope/AC decision branches resolved.

Chair declares FULL primer depth for public graph data-path/source-version boundary: five stances, three questions. First isolated primer precedes all fixed seats; rotating performance seat proposes the best alternative before final fixed-seat weighing and anonymized chair synthesis. All judgments are readiness-phase only.

Allocation: root drafts/admits docs; independent reviewers use focused fresh contexts with source fingerprints. Requested gpt-6.1-sol/high for bounded source-contract review; chair retains its separate inherited context for synthesis, selected for complex boundary judgment and continuity. Observed runtime model/effort unknown where not exposed. Readiness work budget15min per seat, selected finite controls only; no full suite or downstream scan. No separate artifact per seat. One bounded plan-repair pass and one focused verification round maximum before operator escalation.

## Completion criteria

- Implement both admitted repairs and prove all ACs with meaningful independent delivery evidence.
- Pass applicable framework/profile qualification, docs validation and close dry-run; operator controls closure.

## Handoff or next-wave notes

Leave planned/readied after current approvals; do not activate. Implement resolver first, then hierarchy provenance, then independent delivery review and full qualification. Paused2071n remains ready for a separate operator closure decision.

### Independent readiness reviews — 2026-10-09

FULL isolated primer applied adversarial, constructive, simplicity, first-principles and analogical stances, with three questions per wave. Graph challenge: relationship confidence cannot authenticate guessed name-only locations; indexed coordinates do not prove current snippets. Scanner challenge: cooperative checks cannot enforce blocked I/O timeouts, and empty error channels cannot establish clean scans. Every fixed seat answered the primer questions independently before the performance rotating seat ran.

Architecture, security, QA and reality fixed seats approved with notes; required code and docs-contract reviews also approved with notes. Performance proposed shared callgraph/hierarchy projection and staged anchor mitigation before broader scanner work. All four fixed seats explicitly weighed those alternatives and retained the narrow graph repair and coherent scanner/reporting wave. Shared projection expands qualification; partial staging leaves candidate/other-pattern/corpus exposure and transitional contracts. Urgent partial release needs separate scope. No typed plan-blocking finding was demonstrated; current product defects remain the admitted repair rationale.

Finite evidence is current-tree/readiness-only: canonical served handler negatives and exact-ID controls, actual scanner/emitter boundaries, compatible/malformed summary controls and owned-child timeout controls. No implementation, full suite, downstream scan or whole-upgrade deadline is proved. Independent raw results and non-executed probe captures are retained under evidence/readiness, indexed by review-artifact-manifest.json; exact approval inputs are lane-approval-inputs.json. Source packet14 paths remained unchanged.

Implementation notes: bind any source freshness proof to the indexed graph generation; preserve null snippets when unavailable. Explicitly screen lexical symlinks before contained reads. Test candidate-dense and cumulative workloads, every work/retention cap, and positive/negative old/current summary compatibility. Compact summary status must survive old collection bounds. Reporting work and owned cleanup must respect remaining budget; unchanged old-parent fallback remains disclosed.

### Prepare council — final independent synthesis

Phase: readiness. Verdict: approved with notes. Primer depth: full; all five stances and three questions addressed. Architecture, security, QA and reality fixed seats; performance rotating fifth; code/docs-contract additional independent specialist inputs. Chair first weighed randomized anonymized outputs, then reattached identities while preserving required-lane authority. All four fixed seats explicitly weighed the rotating alternatives. Seat agreement: unanimous; max severity: none. No material disagreement or challenge round. Detailed synthesis and honest readiness-only execution limits: evidence/readiness/chair-synthesis.json.

| Recommendation | Reason |
| --- | --- |
| G-N1 | Normalize/deduplicate edge-site copies rather than mutating shared query snapshots; assert relationship counts separately from occurrence counts. |
| G-N2 | Treat any optional session-hash freshness mechanism as graph-generation bound. If existing artifacts cannot establish that binding, retain null snippets. |
| G-N3 | Pin outgoing definition fields and legacy Java filter-only authority beside collision, macro, adjacent function and same-line provenance controls. |

Recommendations are implementation notes, not additional scope or delivered proof. Keep current receipt and planned status; activate only under a later instruction.

### Prepare-ready succeeded — 2026-10-09

Canonical wf_prepare_wave(mode=ready) returned status ok, readied true, no activation, clean garden/full lint and no pending readiness lanes. All required lane approvals and council-readiness are current on the unchanged receipt. Durable result: evidence/readiness/prepare-ready-result.json. Status remains planned; delivery ACs/tasks remain unchecked.
