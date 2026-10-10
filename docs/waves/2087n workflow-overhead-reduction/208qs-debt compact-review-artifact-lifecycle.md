# Keep durable wave evidence compact

Change ID: `208qs-debt compact-review-artifact-lifecycle`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: `2087n workflow-overhead-reduction`

## Rationale

The ten-wave audit found 1495 evidence files (21.9 MiB), including per-seat packets and routine green worker transcripts. Existing seed209 already discourages this. Make final decisions and results live in wave.md, keep machine authority and unique proof, and stop creating disposable files under the repository.

Evidence: the recent-ten-wave audit and final cleanup are summarized in `docs/waves/2071p bounded-reconciliation-reporting/wave.md` and `docs/waves/2071n profile-skip-qualification/wave.md`. Existing unique proof and ledger citations remain available. This plan does not claim future implementation tests passed.

## Requirements

1. Keep routine briefings, per-seat reports, probe captures, source baselines and green logs in task context or temporary storage. Retain a repository artifact only for unique long-run evidence that canonical tests, exact Git history and the wave summary cannot preserve; explain retained exceptions inline in wave.md.
2. Before close, consolidate final outcomes, review disagreements, source/profile identities, reproducible commands, limits, memory disposition and evidence index in wave.md. Reconcile mutable watchpoints and handoff notes; preserve historical conclusions, admitted change docs and immutable events.jsonl without rewriting ledger history.
3. Prune only wave-owned, verified redundant material without live references. Keep cited originals and unreconstructable dirty-tree baselines. No age expiry, reference resolver, blanket deletion or new cleanup sidecar/gate is introduced.
4. Use successful typed-write continuation actions instead of extra list/full-review calls. Batch bookkeeping before the final quiet canonical suite, reuse current matching receipts, and run one authorized close mutation when current review authority already proves readiness. Use dry-run for unresolved checks, not as a compulsory extra close gate.
5. Keep current specialist authority and readiness Council. Use the existing risk-selected primer depth for narrow work; readiness checks plan feasibility rather than requiring future delivery execution. Preserve final full docs validation, exact test qualification and focused independent repair review. Do not cache hard-gate validation results or change mandatory review rosters. The separately admitted advisory-lint change is limited to scoped feedback.
6. Consuming-repository upgrades do not gain source-suite/profile qualification, extra evidence generation or broad memory maintenance. Preserve render -> docs gate -> incremental index ordering; reports are reused only when their inputs are unchanged.

## Scope

**Problem statement:** The ten-wave audit found 1495 evidence files (21.9 MiB), including per-seat packets and routine green worker transcripts. Existing seed209 already discourages this. Make final decisions and results live in wave.md, keep machine authority and unique proof, and stop creating disposable files under the repository.

**In scope:** the named behavior, its existing module owners, finite contract regressions and affected documentation. Canonical seeds are edited first; generated lifecycle/role surfaces are regenerated from those seeds, not patched as a substitute.

The policy change adds no deletion tool or automatic cleanup gate. An operator-authorized manual cleanup checks containment, identity, uniqueness and references before unlink. Cited originals stay unless their consumers are explicitly migrated; immutable ledgers never change.

**Out of scope:** graph-query provenance wave2071o, unrelated scanner repairs, mandatory-lane removal, weakening full lifecycle gates, rewriting ledger history, release/tag/publish, new broad maintenance during consumer upgrades and product-wide refactoring. No implementation is authorized by this planning pass.

## Acceptance Criteria

- [x] AC-1: Generated instructions place routine review working material outside the repository and specify the durable wave.md/ledger/unique-proof boundary. Oracle: seed/render contract tests and a finite representative review packet.
- [x] AC-2: The close workflow preserves cited and unique evidence while removing an owned uncited redundant capture, and final mutable notes agree with closure. Oracle: a reference/uniqueness cleanup matrix and rendered workflow review; no automatic deletion is claimed.
- [x] AC-3: A representative review/repair/close trace consumes typed continuation actions and reuses a matching receipt without additional full-suite or compulsory dry-run work, while changed/red inputs still stop qualification. Oracle: bounded recorded workflow traces and existing gate negative controls.
- [x] AC-4: Required specialist/Council authority, final docs gates and consumer upgrade ordering remain unchanged; narrow readiness uses an existing appropriate primer depth. Oracle: policy/render assertions and a finite upgrade workflow trace showing no newly added consumer suite or evidence pass.

## Tasks

- [x] Implement the scoped requirements in the existing owning modules and canonical instructions.
- [x] Execute the finite positive and known-bad controls named in the ACs through actual public/registered paths; record observations and limits in wave.md.
- [x] Update affected architecture and operator contracts; regenerate affected local surfaces from canonical seeds.
- [x] Run required independent delivery review and fresh framework qualification after source edits; consolidate useful long-run evidence and current handoff without routine per-seat files.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| implementation | implementer | readied wave and later operator activation | Existing module owners; no code edit during readiness. |
| focused verification | qa-reviewer | implementation | AC-scoped real controls; preserve independent judgment. |
| delivery lanes | required specialists | verified implementation | Existing selected authority, no new roster. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
- `docs/contributing/build-and-verification.md`
- `docs/contributing/agent-team-workflow.md`
- `docs/prompts/`
- `docs/agents/`

One implementer owns shared server_impl.py, seed190, build-and-verification and generated outputs. Qualification, memory and advisory changes settle their APIs before the compact-workflow instructions describe them. Index work may be isolated; final integration and canonical receipt run are serialized after all framework edits. Reviewer contexts do not edit source or plans.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Four required ACs protect retention, authority and bounded work; each is necessary to demonstrate the requested reduction without weakening quality. |
| AC-2 | required | Four required ACs protect retention, authority and bounded work; each is necessary to demonstrate the requested reduction without weakening quality. |
| AC-3 | required | Four required ACs protect retention, authority and bounded work; each is necessary to demonstrate the requested reduction without weakening quality. |
| AC-4 | required | Four required ACs protect retention, authority and bounded work; each is necessary to demonstrate the requested reduction without weakening quality. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Consolidated plan; implementation and delivery ACs remain unmet. | Current requirements and named AC oracles; operator requested create/prepare/review. |

| 2026-10-09 | Readback: Routine working packets stay temporary; wave.md and immutable ledgers retain conclusions, with cited or unique proof kept. Update seeds180/190/209/215 and workflow contracts, preserving full gates and existing upgrade ordering (AC-1–4). Before: routine worker log forest; after: inline synthesis plus justified exceptions. | Operator implementation request; admitted ACs unchanged. |
| 2026-10-09 | Observe: Implemented seed180/209/215 and the canonical/authored Implement wave carrier. Routine captures stay outside the repository; final synthesis is inline, cited/unique proof is preserved, and manual pruning checks containment/identity/uniqueness/references. Current continuation/receipt guidance preserves required specialist/Council and final docs authority. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_compact_review_artifacts.py`: 4 passed, including actual template-render deletion/reversal controls. `CompactReviewArtifactContractTests.test_each_seed_and_deleted_or_reversed_obligation_controls` detects each deleted/reversed obligation; `test_implement_wave_template_and_authored_carrier_match_and_render` detects six real temporary-template mutants. Contract transport proves availability, not agent adherence. |
| 2026-10-09 | Observe: Finite continuation/qualification and manual cleanup controls passed. The temporary cleanup matrix removed only the nominated owned uncited reconstructable green capture; kept cited same-byte original, unique proof, dirty baseline, wave summary and ledger byte-identical. Replaced identity, final symlink and outside containment were refused by existing contained-file APIs. | With `PYTHONPATH=..`, nine selected `test_server_tools_lifecycle` tests passed: `ReviewEvidenceListEventTests` guided single-lane/frozen-equivalence/continuation-only cases and `FrameworkTestReceiptGateTests` green/stale/red/no-subprocess/public-close/absent-runner cases. A temporary legacy `wf_close_wave_response(mode='create')` fixture consumed its matching real-runner receipt unchanged in one mutation without prior dry-run; one docs call, docs/garden stubbed green, no self-hosted closure. Cleanup used `judge_contained_file` → `unlink_contained` with carried identity; no new selector/tool/gate. |
| 2026-10-09 | Observe: Consumer recovery still respects docs → bounded historical-memory checkpoint → index and refuses bypassing failed review/docs. No new source suite/profile/evidence or broad memory pass is added to consumer code. | Three selected `test_upgrade_wavefoundry` controls passed: `ResumeAfterGateTests.test_resume_runs_only_the_docs_gate_and_clears_marker_on_pass`, `HistoricalMemoryUpgradeGateTests.test_docs_gate_resume_establishes_memory_checkpoint_and_composes`, and `test_resume_after_memory_cannot_bypass_failed_review_or_docs_gate`. Public `main` recovery boundaries execute with index/docs phase stubs; no full installed consumer upgrade or Windows qualification claimed. Root owns seed190/shared contracts, generated-surface sync, final review and canonical suite. |

| 2026-10-09 | Integration repair: raw canonical seed record-name pin derives from shared shipped vocabulary rather than a default-layout literal. Exact exception obligation and deletion/reversal mutants remain active; no default-only skip added. | `PYTHONPATH=.. python3 -B -m unittest test_compact_review_artifacts test_profile_literal_census` from `scripts/tests`: compact 4 plus census 8 passed (12 tests, 4.565 s); scoped diff check passed. Canonical seed expectation uses `record_layout_support.SHIPPED_DEFAULTS`; active-profile names do not rewrite the raw pointer-target source. |

| 2026-10-10 | Implementation complete; all tasks and ACs met. Required independent delivery lanes approved and current canonical qualification passed. | wave.md retains consolidated proof and limits; events.jsonl holds typed authority. Fresh source receipt bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af; 12,108 tests/181 files/13 skips; no closure or commit authorized. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Adopt the scoped approach above for readiness review. | Concrete ten-wave waste and current source owners support a bounded repair; retain quality and authority boundaries. | Selected clearer canonical workflow discipline and inline close synthesis. Rejected automatic TTL deletion because it can destroy cited or unique evidence. Rejected a new hard-gate full-lint cache and reduced review roster because they add unproven invalidation/authority risk; the audited waste can first be removed through existing continuation and receipt contracts. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Saving work conceals missing proof or stale authority. | Required negative controls, exact input identities, retained unique evidence and unchanged full gates. |
| Cross-change source ownership causes conflicting edits. | Shared-file serialization; canonical seeds first; focused independent integration review. |
| Upgrade performs unrelated maintenance. | Consumer upgrade trace and explicit no-source-suite/no-extra-evidence boundary in every applicable contract. |

## Session Handoff

Planned for readiness review only. See `docs/agents/session-handoff.md`; no code edited under this wave, no AC marked complete and no OPEN slot taken.
