# Receipt section attribution and focused re-review

Change ID: `21lug-enh receipt-section-attribution-and-focused-rereview`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-25
Wave: `21luh wave-work-and-focused-rereview`

## Rationale

21j63 repeatedly renewed readiness judgments while diagnostics identified changed documents but not sections or exact deltas. Reduce reconstruction effort without preserving approvals on a changed contract. Existing normalization already excludes routine tracking; AC deferrals remain acceptance decisions.

## Product Intent

A reviewer can see every material change since their last approval, access the complete amended plan and prior evidence, and decide whether their verdict changes without reconstructing uncommitted history. AC-2/3 test this across intervening receipts; AC-4 proves honest fallback. Better information does not establish lower real-world effort until later waves are measured.

## Requirements

1. Add optional section fingerprints to newly published receipts without changing receipt identity, input digest, supersession, approval validity or lane selection. Reuse existing canonical normalization. Cover preamble and all sections; respect fenced headings and report duplicate/ambiguous boundaries conservatively. Report changed/added/removed sections without discarding unmatched content. Section metadata does not classify semantic impact or map sections to lanes.
2. Capture exact reviewed admitted-document text once per newly published receipt in `.wavefoundry/work/<wave-id>/receipts/`. Bind immutable snapshots to receipt and document identity; verify canonical digest and exact-byte integrity before use. Never recreate an old baseline from current text. Integrate at the shared receipt-publication boundary, including automatic deferral publication. Failed/rolled-back publication never makes orphaned snapshots valid. Missing/I/O-failed snapshots are advisory and do not fail readiness publication.
3. For each stale readiness lane, existing guided review actions show changed sections, its prior approval/evidence, baseline/target receipt identities, verified before/after delta when available, and access to full amended plans. Compare against the receipt that lane last approved, not just the latest two receipts. Newly required lanes with no prior approval receive normal initial review. Ask whether the cumulative change alters the verdict, with access to dependency context.
4. Diff normalized reviewable text to suppress tracking noise; retain exact raw snapshots for inspection and label normalization. Bound output using existing conventions, visibly report truncation and offer access to omitted/full text. Missing legacy metadata, missing/corrupt/cleaned snapshots, stale current inputs or incompatible normalization produce explicit limitations and normal full-review fallback, never false no-change. Read-only review never creates or changes snapshots.
5. Preserve all existing approval recording, invalidation, deferral and reviewer-selection rules. No approval transfer, selective invalidation, new role, universal Council or post-implementation deferral exemption. Old ledgers validate without rewriting. Attribution is optional; cleanup removes only review aids, not durable authority.
6. Preserve the 21j63 baseline now: distinguish receipt transitions, approval submissions and actual reviewer rounds; record unavailable effort rather than inventing it. For the first three later waves needing re-readiness, use the same definitions and note decision changes, attributable extra retrieval and measured reviewer effort where available. Capture future per-round observations before ordinary close compaction; no telemetry-retention redesign.
7. Run one bounded matched reconstruction exercise: compare the structured brief against an independently determined cumulative material delta and the existing full-plan review route. Record completeness and calls/content as proxies, not billed tokens or causal savings. Include normalized tracking and an earlier material change a latest-two-only diff would miss. Later-wave benefit remains a post-release observation.
8. Reconcile Prepare/Review instructions, MCP response docs and their canonical install/upgrade carriers to explain focused review, full-plan access and fallback. No host-specific feature or new approval authority.

## Scope

Implementation follows 21luf's work-area helper; the machine-readable dependency is declared in this wave's Changes section.

In scope: section attribution, receipt-bound scratch snapshots, cumulative per-lane context, bounded baseline/comparison and guidance.

Out of scope: new canonicalization or receipt identity; historical backfills; selective invalidation; changed deferral authority; full plan bodies in durable ledgers; Git commits/stashes; telemetry redesign; semantic impact classifier; 21lue's test receipt allowance.

Source-inspected premises: `review_policy.policy_input_snapshot` stores per-change hashes; `lifecycle_gate_support.receipt_supersession_attribution` lacks section attribution; `_publish_prepare_policy_state` publishes receipts transactionally; `_guided_review_actions` and `wf_review_wave_response` serve review guidance. New mechanism feasibility remains to be executed at readiness/implementation. Baseline counts come from the live read-only typed ledger listing, not prose round estimates.

## Acceptance Criteria

- [x] AC-1: Section attribution identifies changed/added/removed and ambiguous regions while receipt ids/digests and approval decisions remain identical with or without optional metadata. Normalized tracking adds no substantive section delta.
- [x] AC-2: Public receipt publication produces immutable verified snapshots of reviewed uncommitted text, including deferral publication; retry, concurrent edit and publication failure never associate the wrong text with a receipt.
- [x] AC-3: Reviewers last approving different receipts receive their complete cumulative material delta, prior evidence and full-plan access. A matched reconstruction exercise agrees with an independent expected delta; a latest-two-only implementation fails.
- [x] AC-4: Legacy, missing, corrupt, cleaned, truncated/oversized or stale baseline cases report limitations and retain a usable full-review path, without restoring stale approvals or adding gates.
- [x] AC-5: Compatibility cases preserve existing validation/approval semantics across old/new metadata, absent scratch and closure/reopening; controls detect accidental approval transfer or identity churn.
- [x] AC-6: A reproducible 21j63 baseline separates exact counts from unavailable effort; a bounded prospective comparison uses the same definitions. Guidance accurately explains brief/fallback behavior without claiming demonstrated savings.

## Tasks

- [x] Confirm receipt publication/validation and guided action seams; design optional metadata with identity parity.
- [x] Implement section attribution and verified snapshots on 21luf's owned workspace.
- [x] Integrate per-lane cumulative deltas, prior evidence and full-plan fallback.
- [x] Reconcile canonical/local/install/upgrade instructions and MCP documentation.
- [x] Independently verify bounded failure, compatibility and matched reconstruction cases.
- [x] Preserve baseline and future comparison instructions in durable wave evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Attribution and snapshots | implementer | 21luf; readiness | Serialize shared publication integration |
| Guided review | implementer | verified baseline | Read-only advice, existing approval writes |
| Verification | code/QA/docs/security reviewers | frozen source | Verify completeness and cache distrust |

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wave_work.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Derive carrier edits from Prepare/re-review instructions and receipt guidance, preserving unrelated text. Fix canonical sources before local reconciliation. Protect canonical normalization, ledger history, approval authority and host permissions. Implementer/coordinator owns writes; reviewers are read-only. Amend scope before touching newly discovered source owners.

## Affected Architecture Docs

Update data-and-control-flow and MCP tool surface for authoritative receipts versus disposable snapshots and new advisory output. Existing review-policy authority remains unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Useful attribution without identity churn |
| AC-2 | required | Correct reviewed baseline |
| AC-3 | required | Complete practical re-review context |
| AC-4 | required | Disposable cache stays optional |
| AC-5 | required | Approval safety and legacy compatibility |
| AC-6 | required | Honest measurable outcome and limitations |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-25 | Independent delivery verification completed; required lanes and Council support the admitted mechanisms. Final canonical qualification passed 12,195 tests across 211 files, 12 skips, 592.190s; no reviewed source changed during the run. | Maintained helper/lifecycle/publication/review controls and typed delivery evidence; receipt inputs_hash db4065ce546931c670d6378ed45f79af78c256fe64aec17cfda145e214335a87; see wave Review Checkpoints for limits |
| 2026-10-25 | Implemented optional section metadata, captured immutable snapshots and per-lane cumulative briefs with full-review fallback. 120 policy and 211 evidence tests pass; six registered publication/deferral/re-review tests pass. Latest-two-only, Prepare-only and live-reread mutants fail; exact CRLF and rollback controls pass. Matched reconstruction and its proxy limits retained in baseline evidence. Independent delivery review and canonical qualification remain pending. | Maintained helper and ReceiptSnapshotPublicIntegrationTests controls; evidence/readiness-baseline-21j63.md |
| 2026-10-25 | Readback: current receipts identify changed documents but not exact cumulative changes. Add optional section metadata and immutable reviewed-byte snapshots; show each stale lane its own approved baseline, complete amended plan and bounded normalized delta. Example: a lane on R1 reviewing R3 sees both R1→R2 and R2→R3 changes; missing scratch falls back to full review. AC-1–6; shared publisher, review helpers and guidance only, no approval transfer or identity changes. 21luf helper and public lifecycle tests now pass. | Current readiness receipt; 18 helper and 10 public lifecycle tests; baseline evidence |
| 2026-10-25 | Planned and baseline captured. No implementation/readiness performed. | evidence/readiness-baseline-21j63.md; typed ledger census; read-only telemetry query |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-25 | Section metadata plus disposable text snapshots | Hashes locate change; text explains uncommitted change | Git-only misses reviewed uncommitted states; committed snapshots add permanent volume; hashes alone cannot show deltas |
| 2026-10-25 | Compare to each lane's approved receipt | Intervening receipts must not hide unseen changes | Latest-pair-only diff is incomplete |
| 2026-10-25 | Advisory mechanism, unchanged approval authority | Replays reconstruction burden through explicit context; reviewer still judges | Section-to-lane mapping misses semantic impacts; authority changes deferred |
| 2026-10-25 | Completeness now, effort prospectively | Baseline counts observable, per-round effort compacted; fewer rounds not promised | Approval counts/context estimates do not establish saved reviewer effort |
| 2026-10-25 | Keep canonicalization unchanged | Existing tracking exclusions already reduce churn | Changing normalization is a separate policy change |

## Risks

| Risk | Mitigation |
| --- | --- |
| Cache mistaken for authority | Verify binding/integrity and fall back; durable ledger remains sole review authority |
| Snapshot races publication | Capture inspected inputs at existing publication boundary; exercise failure/mutation |
| Brief hides ambiguous or large changes | Explicit limits and full text access |
| More output increases effort | Bounded response, optional expansion and measured follow-up |
| Guidance fails to improve judgment | Claim completeness only now; measure later decisions and cost |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
