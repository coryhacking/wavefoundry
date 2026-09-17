# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-09-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1y0gz record-layout-roots`
Title: Record Layout Roots

## Objective

When this wave closes, a target repository can relocate its wave and plan roots and group wave records at bounded depth through committed `record_layout` configuration, with the default reproducing today's `docs/waves` and `docs/plans` layout byte for byte. This is the first of the two waves that unblock Waveforge's adoption.

## Changes

Change ID: `1y042-enh record-roots-config-and-resolver`
Change Status: `planned`

Change ID: `1y043-enh nested-record-lookup`
Change Status: `planned`

## Participants

- Coordinator: Engineering
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

## Wave Summary

Config-driven replacement for the RFC's auto-discovered `PathResolver`: one stdlib resolver module, fail-closed validation, routing of every hardcoded layout site across the server, docs-lint, indexer, memory backfill, and dashboard, a census test that forbids new literals, and opt-in nested wave discovery with deterministic ambiguity handling.

## Watchpoints

- `1y042` must land before `1y043`; the nested discovery builds on the resolver module.
- The existing `wave_implement.wave_root` key is written by installs but read by nothing today; the legacy fallback and lint hint keep those configs working.
- Rendered prose in seeds, `AGENTS.md`, and prompt docs still names `docs/waves` as the conventional home; a one-sentence seed follow-up under the seed gate is deferred, not forgotten.
- Waveforge's exact tree is unstated; the nested option is generic and bounded. Confirm their layout before Prepare so the fixture in `1y043` mirrors it.
- Golden tool-surface fixture from `1y0do` must remain unchanged; no tool parameter is added in this wave.

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
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| code-reviewer | pending | no current executed approval | record approval evidence for code-reviewer |
| qa-reviewer | pending | no current executed approval | record approval evidence for qa-reviewer |
| operator-signoff | pending | no current executed approval | record approval evidence for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- `1y0do tool-surface-snapshot` should close first so both changes can assert an unchanged public surface.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 7 | 0 |
| **Total** | **7** | **0** |

<!-- wave:context-efficiency-state {"generation":7,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":7,"content_source_credit":3567,"derived_artifact_credit":273,"direct_net":-1685,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1429,"response_debit":7703,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607}},"store_instance_id":"33652402c1924592b478c511b0100138","totals":{"calls":7,"content_source_credit":3567,"derived_artifact_credit":273,"direct_net":-1685,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1429,"response_debit":7703,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3607},"wave_id":"1y0gz record-layout-roots"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->

## Review checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: 1y042's own success criterion was transitively coupled to an unrelated maintainer-only wave; strongest-alternative: a self-contained schema-pin test for the eight touched lifecycle tools, applied in-session).
