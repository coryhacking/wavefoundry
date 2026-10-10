# Keep readiness approval separate from delivery findings

Change ID: `206oh-bug readiness-delivery-phase-isolation`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-08
Wave: `207lx readiness-phase-isolation`

## Rationale

A downstream diagnostic demonstrates a repair-plan deadlock: current independent readiness approvals for code, QA, architecture and security are withheld by unresolved delivery-origin findings, while council readiness remains approved. Readiness authorizes a plan for implementation; delivery verifies the resulting work. This change gives every readiness lane that same phase boundary and makes gate diagnostics distinguish absent approval from an existing approval that is withheld. Deliverable: a narrowly scoped evaluator/diagnostic fix, executable phase controls and updated review-contract documentation. The real downstream ledger remains untouched; reproduce with generic scratch records rather than importing its finding details.

Current source grounding: review_evidence._finding_affects_signoff protects only COUNCIL_READINESS_SIGNOFF_KEY from delivery-origin findings. review_authority_projection builds affected_signoff_keys before selecting each approval's effective phase. Origin authority already comes from the finding's sealed root synthesis and review run through _finding_origin_phases, rather than mutable evidence text. lifecycle_gates.prepare_review_lanes_gate reduces all non-current approvals to missing and recommends recording an approval.

## Requirements

1. Derive the finding-to-approval relation using the effective approval phase for every required or requested readiness lane, including specialist, custom and council lanes. A canonically delivery-origin finding must not withhold, stale or require delivery reverification for a readiness approval, whether that delivery head is unresolved or repaired later.
2. Preserve delivery authority: unresolved applicable delivery findings continue withholding delivery approval, terminal repairs continue requiring fresh affected delivery approval, and operator closure remains blocked until its existing requirements are satisfied. Do not erase, filter or rewrite ledger history to accomplish phase isolation.
3. Preserve readiness authority: applicable readiness-origin findings, stale receipt bindings, missing/invalid actors and missing independence continue blocking readiness under existing rules. Preserve conservative handling of unknown-origin historical/synthetic rows and existing default/mixed-phase presentation compatibility; do not relabel a sealed finding using a mutable phase field.
4. Keep one structured authority for status rows, guided review actions, prepare/implementation admission and delivery/close evaluation. Readiness guidance must not route a plan approval through repair of delivery-only findings. Do not add parallel signoff-affect rules or parse human status prose in gate callers.
5. Preserve the existing diagnostic code contract while making the readiness-lane message and structured outcome distinguish absent, stale and withheld approval using canonical authority facts. An existing withheld approval must receive its actual phase-appropriate remedy rather than an instruction to record a supposedly missing approval. Apply the same truthful distinction to shared delivery diagnostics where directly affected, without weakening their gate. Update the direct lifecycle-envelope golden only for these declared diagnostics/structured observation fields, with explicit delta assertions preserving prior codes, outcomes and unrelated fields; do not relax its overwrite refusal or oracle.

## Scope

In scope: this reported readiness/delivery phase collision, its direct gate presentations and named verification consumers. All reviewer lanes are derived from the current policy; four reported lanes are examples, not a hardcoded exception set.

Out of scope: closing waves, committing/pushing, changing delivery-finding dispositions, waiving independence or operator authority, rewriting historical ledgers, the separate graph-community qualification issue, C6 journal relocation and private security drafts.

## Acceptance Criteria

- [x] AC-1: With current typed readiness approvals and unresolved delivery findings affecting specialist and council roles, the real readiness projection and implementation admission accept the approved repair plan without changing ledger bytes. The same fixture's delivery projection remains withheld.
- [x] AC-2: Every policy-selected readiness lane, including a custom reviewer and existing legacy council aliases, follows the phase distinction; mixed/default projections retain their documented phase selection.
- [x] AC-3: Unresolved readiness-origin findings, stale receipts, invalid actors and non-independent approvals still reject readiness. Unknown-origin compatibility remains conservative, and mutable finding phase fields cannot bypass the sealed run's origin.
- [x] AC-4: Delivery approval, terminal-repair chronology, independent reverification and close/operator checks retain their blocking behavior on the same typed records that permit readiness.
- [x] AC-5: Guided readiness actions and gate diagnostics report the actual absent/stale/withheld state and its correct remedy; they never demand completion of delivery-only repairs as a prerequisite for implementation of their approved plan.

## Tasks

- [x] Reproduce the central evaluator and public implementation gate using generic canonical scratch ledgers; record readiness and delivery outputs before changes.
- [x] Make the canonical approval-affect relation phase-aware, preserving sealed origin and unknown-origin compatibility.
- [x] Derive truthful lane diagnostics and guided actions from structured authority without duplicate rules.
- [x] Add phase, lane, chronology, legacy and authority controls with known-bad detection; run the change's affected suites.
- [x] Update the review contract and obtain independent code, QA, architecture, docs-contract and security review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Evaluator and direct gate consumers | Implementer | Readiness | One source writer; preserve C4 alias implementation |
| Contract documentation | Technical writer | Phase contract | Serialize shared specification with public wave |
| Independent verification | Reviewers | Frozen implementation | Fresh contexts; paired readiness/delivery public gate probes |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates.py`
- `.wavefoundry/framework/scripts/tests/test_phase_gates.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/review-and-evals.md`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/contributing/review-and-evals.md: readiness authorizes an approved implementation plan; delivery findings continue governing delivery authority and truthful phase-specific remediation. No ledger format or new authority store is proposed.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Remove the reproduced circular admission gate |
| AC-2 | required | Apply the rule to the derived lane set |
| AC-3 | required | Preserve readiness authority and conservative compatibility |
| AC-4 | required | Prevent a delivery or operator-authority bypass |
| AC-5 | required | Keep tools and operator remediation consistent |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Readback: plan a phase-isolation fix separately from C1–C5. Before, a delivery finding can withhold a specialist's current repair-plan readiness approval. After, readiness follows its own finding phase while delivery still rejects unfinished repairs. No implementation edits are authorized before admission and successful Prepare. | Live code_read of canonical relation/projection and prepare gate; downstream diagnostic inspected without ledger mutation |

| 2026-10-08 | Generic real-producer scratch reproduction reaches the evaluator, prepare gate and implementation-admission dry run: four reported specialist lanes plus a custom reviewer are withheld; council readiness is approved; every delivery lane remains withheld. Ledger bytes stay unchanged. Direct Req-4/5 consumer census also identifies wf_server/server_impl.py (_prepare_lane_review_state, _attach_prepare_readiness_advisories, wf_implement_wave_response) and its test_readiness_convergence.py owner. These existing direct presentations are intended implementation targets under the admitted gate/diagnostic scope, sharing canonical projection facts rather than new signoff rules. | /tmp/wf-207lx-phase-probe.py, baseline log; live code_read and code_keyword of all _prepare_lane_review_state callers |

| 2026-10-08 | Queue update: public 204mp was temporarily paused with its C5 finding still open to free the OPEN slot for this requested phase repair. Its earlier OPEN references describe the planning snapshot; no public source edits run concurrently. The operator also approved separate graph repair 207t4. | wf_pause_wave(204mp) successful implementing-to-paused transition; current central handoff |

| 2026-10-08 | Readback: implement the approved phase-aware finding relation for every policy lane and use its structured absence/staleness/withholding facts in direct prepare, admission and delivery diagnostics. Before, a delivery finding withholds a current repair-plan readiness approval; after, readiness remains current both before and after delivery repair, while delivery keeps its blocking/chronology rules. Intended source edits: review_evidence.py, lifecycle_gates.py, direct server_impl.py presentations, their phase/gate/golden tests and hand-authored MCP spec. The existing generated review-and-evals carrier already states same-phase repair; preserve its canonical seed rather than edit it as a substitute. No ledger rewrite, actor/independence change or operator waiver. | Successful Prepare-ready receipt3ee7280c80ff0820a2dc; memory briefing and current caller census |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Select a central phase-aware approval-affect relation with structured diagnostics. | Smallest change that covers every lane while preserving delivery authority and one source of truth. | Dropping delivery findings from ledger/evaluation globally would weaken delivery. Hardcoding the four reported specialist exceptions misses custom and additional policy-selected lanes. Patching each gate separately duplicates authority and risks divergent remedies. |
| 2026-10-08 | Keep the diagnostic code compatible and make state/reason/remedy explicit. | Existing consumers rely on missing_required_lane; actual authority state can distinguish absence from withheld approval without an unrelated API break. | Renaming every diagnostic broadens consumer changes; retaining inaccurate missing-approval instructions leaves the operator stuck. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Filtering too broadly permits readiness-origin or unknown-origin findings to bypass admission. | Paired sealed-origin, unknown-origin and mutable-phase controls. |
| A readiness exemption accidentally weakens delivery or repair chronology. | Same-ledger readiness/delivery comparison, fresh repair chronology and operator close controls. |
| Shared source or specification changes invalidate active public delivery review. | Plan/readiness only while C1–C5 reviewers run; serialize implementation after their frozen round. |

## Session Handoff

Planning only. Public 204mp remains OPEN with its independent delivery review in progress; this wave consumes no OPEN slot until readied and deliberately activated. See docs/agents/session-handoff.md.
