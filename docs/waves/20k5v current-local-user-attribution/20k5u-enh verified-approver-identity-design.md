# Current local user attribution

Change ID: `20k5u-enh verified-approver-identity-design`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-13
Wave: `20k5v current-local-user-attribution`

## Rationale

The operator clarified that the desired identity is simply the current user. Record the local operating-system account automatically when a new review event is authored, independently of configured contributor handles and self-attested names. This supplies useful provenance without signatures, external identity services or another approval step. It identifies the process account, not a separately authenticated human; shared accounts and delegated agent processes remain explicit limits.

## Requirements

1. Resolve the current process account through the operating system: effective-user account lookup on POSIX and the native current-account API on Windows. Do not accept a caller-supplied local-account name or trust username environment variables as verified account data. No network, shell identity command, password, key or extra dependency.
2. Store optional bounded local-user attribution in the existing verification_context of newly authored review evidence, separately from contributor operator metadata and attested_by. A canonical source label distinguishes local operating-system account data. Capture account name only, not hostname, home directory, email or credentials. Unsafe/unavailable lookup yields omitted attribution plus bounded advisory, never a new approval gate.
3. Preserve original attribution on replay; read/list and historical records require no account lookup or backfill. Keep account data outside semantic event/review-policy identity so ordinary attribution does not rotate approvals or require another review.
4. Display local-account attribution with an explicit label, keeping configured handles and self-attested names distinguishable. It does not enforce approver-versus-owner separation, prove review independence or authenticate the human driving the process.
5. Extend canonical builder/validator/registered review paths and their tests without creating another evidence file or rewriting existing ledgers. Document upgrade compatibility: old readers may require the ordinary framework update to understand new optional metadata; no mandatory user enrollment.

## Scope

In scope: source-derived local account metadata, canonical event authoring/replay/display validation, focused platform-adapter controls and documentation. Out of scope: signed approvals, identity providers, passwords/keys, owner separation enforcement, environment-name authentication, automatic ledger backfill and new lifecycle gates.

## Acceptance Criteria

- [x] AC-1: Controlled account adapters resolve the process account on supported platform paths and ignore contradictory username environment variables; unavailable/unsafe names produce a bounded nonblocking advisory.
- [x] AC-2: A registered new review event contains separately labeled local-account metadata alongside existing contributor/self-attested metadata; historical records validate without it, and replay preserves the original value without lookup.
- [x] AC-3: Display/validation controls distinguish local account from self-attestation, escape unsafe presentation, and reject malformed metadata; changing the current account does not alter an existing operation identity or readiness receipt.
- [x] AC-4: Focused tests and edited docs validate; documentation describes process-account provenance and shared-account limits without person-authentication claims or new approval requirements.

## Tasks

- [x] Implement bounded platform-specific local-account lookup and canonical metadata propagation.
- [x] Extend validation, rendering and registered-path replay tests.
- [x] Update the review-event contract, threat model and changelog with narrow attribution semantics.
- [x] Run focused controls and independent review; pause the completed wave.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | Independent council and required lanes | Admitted plan | Verify identity claims and compatibility |
| Implementation | implementer | readiness and earlier review_evidence edits | Single writer |
| Delivery | Independent required reviewers | frozen implementation | Native-platform execution limits explicit |

## Serialization Points

Run after earlier parser/publication repairs; serialize review_evidence.py, server_impl.py and shared docs. Reviewers read only; coordinator owns ledgers and integration.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/operator_identity.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_operator_identity.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/threat-model.md`

Root CHANGELOG.md records the additive attribution behavior. Protected role authority, policy canonicalization and existing ledgers remain unchanged.

The miniature packaging fixture must include the existing `operator_identity` and `subprocess_util` dependencies now imported by the reviewed code. Keep its isolated extracted import and inert worker-guard assertions unchanged; this does not change production packaging or introduce a new shipped dependency.

## Affected Architecture Docs

`docs/architecture/threat-model.md` distinguishes process-account attribution from human authentication. The MCP review-event spec and seed209 document new optional metadata and first-write/replay behavior. No new trust authority is introduced.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Record the actual local account instead of a supplied label |
| AC-2 | required | Preserve event history and existing attribution |
| AC-3 | required | Do not turn metadata into approval authority or repeat reviews |
| AC-4 | required | Bound claims and verify intended behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | After focused readiness currency and recorded repair start, added only operator_identity and subprocess_util to the miniature packaging fixture. The unchanged isolated import/inert-guard test passes. Production packaging and source unchanged; fresh QA/release reverification and final qualification pending. | Canonical targeted controls; recorded cycle-1 repair; no release/closure claim |
| 2026-10-13 | Final focused integration is green. The broad lifecycle run exposed four outdated expectations and one mock signature; eight targeted controls now pass with original historical digests preserved, deterministic account attribution, the exact callback advisory site and the original replacement-refusal oracle. No production repair was needed. All five implementations are paused; canonical combined qualification and independent delivery are next. | test_server_tools_lifecycle named failed methods and LocalUserReviewEventTests; git diff --check clean |
| 2026-10-13 | Implemented bounded native local-account lookup, optional canonical metadata, escaped labeled projection and new-event-only attribution. All 232 focused tests pass; 65 council-policy controls pass. A real readiness receipt and approval stay identical across account changes. Known-bad unsafe-name, omitted-propagation and caller-injection controls fail as intended. Full docs validation passes; final combined qualification and independent delivery remain pending. | test_operator_identity; test_review_evidence; LocalUserReviewEventTests; test_review_operator_integration; WaveCouncilPolicyTests; native Windows API mocked, native execution unrun |
| 2026-10-13 | Opened after independent readiness. Readback: capture bounded native current-account metadata only on new event construction, preserve replay and semantic identity, and label local-account provenance without human-authentication claims. Source implementer and coordinator documentation writes serialize. | Current typed readiness; operator_identity, review_evidence and registered first-write/replay branch; pre-implementation memory brief |
| 2026-10-13 | Operator clarified current user only; narrowed the earlier identity-design draft before admission. No implementation yet. | Current operator direction; operator_identity.resolve_operator and registered wf_review_event first-write/replay branch |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Record current local OS account as separate optional provenance. | Meets operator direction without signatures or enrollment. | Signed approval adds unnecessary authority infrastructure; Git handles or username environment values alone do not identify the process account. |
| 2026-10-13 | Preserve attribution on replay and keep it outside semantic identity. | Recording metadata must not cause repeated approval or review work. | Backfilling old events changes historical claims; making lookup a gate adds unnecessary failure modes. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Local account mistaken for verified person | Explicit source label and shared/delegated-account limitation |
| Platform APIs unavailable | Nonblocking omitted attribution and bounded advisory; native qualification limits disclosed |
| Unsafe account name leaks into display | Bounded validation and escaped output; no paths or environment dumps |

## Session Handoff

Implementation follows the earlier repair waves and current readiness authority; no closure or commit authorized.
