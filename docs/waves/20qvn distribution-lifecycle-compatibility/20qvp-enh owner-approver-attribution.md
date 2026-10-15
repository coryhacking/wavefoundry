# Record owner and approver attribution with explicit review states

Change ID: `20qvp-enh owner-approver-attribution`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qvn distribution-lifecycle-compatibility`

## Rationale

Keep useful owner and approver attribution without pretending local account metadata authenticates a human review. Support deliberate migration from legacy prose and keep refusal diagnostics free of local filesystem identity.

## Requirements

1. Reuse existing identity fields where possible for owner and approver, supporting configured Git identity and local OS identity with an explicit source label. Do not require GitHub, online lookup, credentials or separate owner and approver.
2. Preserve privacy opt-out and optional account capture. Do not silently publish Git email or OS identifiers beyond the selected attribution policy; distinguish configured/observed attribution from authentication.
3. Document and support explicit operator attestation or conversion of migrated prose evidence through the typed path. Do not fabricate historical review execution or silently turn prose into approval.
4. Make legacy review signoff interpretation fail closed for negated, pending or ambiguous free prose. Retain the existing explicit lane/state first-token grammar and current-state table contract; keep explanatory prose without approval authority and document compatibility/migration.
5. Keep publication-refusal messages, structured details and displayed chained tracebacks free of the protected absolute root.

## Scope

In scope: the requirements above, registered entry-point regressions, canonical guidance and necessary generated surfaces.
Out of scope: unrelated refactoring, timing investigation, production-target mutation, external publication and release execution.

## Acceptance Criteria

- [x] AC-1: Owner and approver may be the same configured Git or OS identity; offline operation and privacy opt-out work and source labels never claim authenticated human approval.
- [x] AC-2: Migration tests preserve legacy text and record only explicitly supplied typed attestation, with no invented reviewer execution.
- [x] AC-3: Negated/pending/ambiguous free prose does not satisfy approval; supported explicit approved states retain the existing first-token grammar, and typed approvals remain valid.
- [x] AC-4: Public refusal and formatted traceback tests show a path-free error without the underlying sensitive cause being displayed.

## Tasks

- [x] Map existing owner/approval fields and reuse them before adding schema.
- [x] Implement minimum attribution and privacy changes; document Git identity terminology.
- [x] Define explicit migration attestation and strict approval parsing with compatibility controls.
- [x] Sanitize refusal chaining and add public-path regressions; update review guidance.
- [x] Complete readiness before code edits and required delivery review; retain durable results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and guidance | Implementer | Readiness | Single write owner; serialize shared files |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/operator_identity.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/architecture/cross-cutting-concerns.md`

Write ownership: implementer owns admitted behavior and its derived callers/tests. Canonical seed edits precede regeneration; do not hand-patch generated surfaces. Reviewers are read-only. Protect publication guards, recovery checkpoints, unrelated user hooks/docs, secrets and existing evidence; no historical ledger rewrites. Confirm exact seed/config edits during Prepare before opening gates.

## Affected Architecture Docs

Update `docs/architecture/cross-cutting-concerns.md` and applicable canonical setup, extension, lifecycle or release guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core observable contract |
| AC-2 | required | Core observable contract |
| AC-3 | required | Core observable contract |
| AC-4 | required | Core observable contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned only; implementation and approvals pending | This plan and wave record |
| 2026-10-15 | Readback: reuse operator-authored Owner and existing source-labelled Git/local attribution with privacy opt-out; remove free-prose approval authority while retaining explicit latest lane states and typed authority. Preserve historical prose during documented explicit current attestation; suppress sensitive publication exception chaining. Before: negated prose can approve a reviewer; after: only explicit current state can approve. AC-1–4; review_evidence, identity regression tests, lifecycle tests and review guidance. | Admitted requirements and current source inventory |

| 2026-10-15 | Reused existing Owner, operator, attested_by and optional local_user attribution without a schema or authentication change. Legacy prose remains narrative; explicit current lane states and last table rows govern, and typed authority remains separate. Explicit current migration attestation preserves prose without inventing reviewer execution. Publication protection suppresses sensitive chaining; preview publication refusal precedes locks. | Source and focused fixtures |
| 2026-10-15 | Identity14 and review-evidence206 passed. Lifecycle637 had one intended old positive prose fixture failure (architecture/code-reviewer sign-off spelling), repaired to canonical lane states and targeted green; two pre-existing Guru seed/render path skips remain disclosed. Final target10 passed including registered migration, privacy opt-out and path-free refusal. Four worker mutants detected restored prose approval, first-row table authority, sensitive exception chaining and removed preview refusal; /private/tmp/20qvp-mutants.py. Full combined suite and required delivery review remain coordinator-owned and pending. | Focused validation; no whole-suite claim |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Choose source-labelled attribution and explicit approval states. | Coherent contract with focused regression coverage | Mandatory signed identity/separation policy: exceeds the requested owner/approver purpose. Keep permissive prose approval: ambiguous language remains authoritative. |

## Open Decisions

No unresolved operator scope decision. Prepare must verify exact API/schema compatibility and source-derived affected paths.

## Risks

| Risk | Mitigation |
| --- | --- |
| Existing prose users need actionable migration guidance; do not invent approvals or require separate people. | Use public-path positive and negative controls; preserve contracts outside scope. |
| Review overhead | Keep durable conclusions in wave.md and temporary probes outside tracked evidence folders; reuse valid qualification. |

## Source-derived implementation contract

- Reuse the document's existing `Owner` field and approval event `verification_context.operator`, `attested_by` and optional `local_user`. `operator_identity.resolve_operator` already resolves an explicit configured handle or maps local Git `user.email` to a contributor handle, retaining source `explicit` or `git_email` without recording the email in the event. Local account capture already has a privacy policy. Treat this portion as guidance and regression coverage unless a demonstrated display gap requires a minimal change; do not add an identity registry, network authentication, mandatory account capture or an owner/approver inequality gate.
- Describe Git attribution independently of hosting vendor. An owner may use the same configured handle or chosen local account label as the approver; the document owner is operator-authored text. A local account or configured Git handle identifies recorded provenance, not a verified human review. Preserve unresolved identity and opt-out behavior.
- Migration guidance must preserve legacy prose and explain the existing typed declaration/event path, dry-run first. Record newly executed review runs and explicit current approvals with current context; never synthesize historical runs from prose or import prose as typed authority. If a migrated record remains legacy, document exact canonical lane-state lines for finishing it. An operator attestation is labelled as such and does not substitute for required executed reviewer evidence.
- Remove free-prose signoff authority from `lane_has_signoff_in_evidence`; keep the existing explicit lane/state and current-state table contracts and their last-state semantics. Explanatory prose stays in the record. Cover negation, token-bearing lane names, pending/ambiguous prose, exact positive and negative states, superseded evidence and typed-wave noninterference. Update legacy-fixture text only where it intentionally expresses an approval, not to hide refused cases.
- Change the test-worker protection translation in `project_state_publication_lock` to suppress its sensitive exception cause (`from None`) while retaining the existing path-free message/detail. Assert formatted traceback output and the public response, not merely the top-level string; keep failure closed and retain its exception type.
- Focused coverage belongs in `test_operator_identity.py`, `test_review_evidence.py` and `test_server_tools_lifecycle.py`; documentation belongs in the canonical review/legacy migration guidance and `docs/architecture/cross-cutting-concerns.md`. No historical event ledger rewrites or automatically populated owner fields are in scope.

Source inspection: `operator_identity.resolve_operator`, `review_evidence._identity_context`, `review_evidence.lane_has_signoff_in_evidence` and `review_evidence.project_state_publication_lock` establish these existing contracts and the two narrow behavior repairs. This is readiness design evidence, not an executed approval.

QVN-D1 repair clarification: the owning Requirement 4 and AC-3 now distinguish free prose from the explicit-state grammar already required by the source-derived implementation contract. No parser expansion or new authority boundary is admitted; canonical guidance will be aligned and independently rechecked.
