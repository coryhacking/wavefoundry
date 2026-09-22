# Implement tool inventory

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Ordered work and readback

1. Dependency parser and activation hints in `server_impl.wf_implement_wave_response`; preserve admission order and parse only anchored declaration lines, exact ids in wave records and unique-prefix compatibility in legacy change docs. Current activation reproduced prose fragments as dependencies and no serialization points.
2. Retained-context helper in `review_evidence`; append boundary judges the candidate against preceding repair evidence. Existing own-chain diagnostics retain their precedence. Both close paths already consume `repair_independence_violations`: `lifecycle_gates` facade and `server_impl.wf_close_wave_response`. Delivery review adds only a firing advisory; golden envelopes remain unchanged otherwise.
3. List context summary reports the full ledger, including historical superseded claims. Approval audit uses current per-phase authority and event-prefix chronology, so later repairs never invalidate earlier approvals retroactively.
4. Seeds, then local surfaces follow the tool implementation. Renderer constants are explicitly not propagated; no renderer edits are planned.

## Verified seams

- `review_evidence._reverification_independence_defect` currently checks exact finding/cycle only; `build_compact_review_event` calls it before constructing terminal synthesis. Its approval branch independently checks declared freshness.
- `server_impl._identified_review_event_bundle` decides identical replay before the builder; preserve this ordering.
- `review_evidence._approval_rows`, `ReviewAuthority.signoff_current`, and `review_authority_projection` own phase and receipt currency. Reuse rather than invent new currency rules.
- `server_impl._review_evidence_list_response` derives listing from validated records; add context summaries without replacing existing projections.
- `wf_review_wave_response` attaches retrieval-posture diagnostics without changing blocking status; use the same conditional advisory pattern.

## Producer-built fixtures

Use `server_tools_support.make_declared_wave` with real create/admit/prepare/review producers, plus `declared_wave_doc_gates` for unrelated doc execution. Do not copy the private receipt construction in legacy `WaveImplementTests`.

`RepairIndependenceBoundaryTests` supplies public writer helpers; `RepairReverificationIndependenceTests` supplies component event builders and the established guard-patched historical-row technique. Existing cross-finding/earlier-cycle acceptance tests must be revised under the admitted contract.

## Initial verification

`python3 -B -m unittest test_review_evidence.RepairReverificationIndependenceTests` from the tests directory: 21 passed before changes.

Read-only live-ledger census by `/root/efficiency_readiness_verify`: 1ypxw planned and 1ypy6 implementing, 26 rows at the final census snapshot, zero repair-start evidence rows, zero earlier-repair-context fresh claims, zero parse errors. Closed archives excluded and untouched. Therefore only injected producer-built cases can prove the new guard.

## Allocation and limitations

Coordinator owns implementation; inherited model settings suit cross-cutting lifecycle contracts, runtime identity unknown. One fresh context verified revised readiness, then became read-only implementation support. It is not eligible as a fresh delivery reviewer. Host rejected another inventory worker at its thread limit. Before receipt: docs/reports/retrieval-quality-1ypy6-before.json, verdict baseline, no invalidation or operator-review reasons, end digest verified, 335.771 seconds. The index was already current; no update/rebuild ran. Two public producer-built parser/hint tests now pass. Source implementation is underway.
