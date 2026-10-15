# Make release verification and qualification provenance explicit

Change ID: `20qvs-enh release-provenance-verification`
Change Status: `deferred`
Owner: Engineering
Status: deferred
Last verified: 2026-10-15
Wave: TBD

## Disposition

Deferred by operator scope direction on 2026-10-15; removed from wave 20qvq. The proposal below is retained for later triage, not admitted release requirements. Existing qualification reporting and build identity should be checked before proposing new machinery. No signing authority decision is required for the narrowed provider wave.

## Rationale

Consumers need to verify distribution artifacts before executing their bootstrap and distinguish official releases from later source builds. Qualification exceptions must be visible rather than implied green.

## Requirements

1. Publish independently verifiable artifact digests bound to release tag/source commit using an approved signing or attestation authority. A checksum embedded in its own pack is only self-consistency.
2. Install and upgrade guidance verifies published provenance and digest before executing or extracting either lean or combined pack, including bootstrap bridges. Document offline trusted-verification inputs and failure handling.
3. Build artifacts record source commit and unique build identity; official combined and lean artifacts are attached to their deliberate release tag. Do not require a VERSION-only commit after every source commit.
4. Qualification reporting identifies each profile, result and explicit operator-approved exception in release-facing metadata and notes. Functional renamed-profile failures block release.
5. Keep existing timing investigations deferred. Previously accepted timing exceptions remain named exceptions, not passing tests or permanent threshold changes.

## Scope

In scope: the requirements above, registered entry-point regressions, canonical guidance and necessary generated surfaces.
Out of scope: unrelated refactoring, timing investigation, production-target mutation, external publication and release execution.

## Acceptance Criteria

- [ ] AC-1: Tampered, wrong-tag and untrusted provenance fixtures fail before pack execution/extraction; valid trusted release artifacts pass the documented verification path.
- [ ] AC-2: Lean and combined pack metadata distinguish artifacts built from different source commits and identify the release tag when applicable.
- [ ] AC-3: Release-summary fixtures expose profile failures and named approved exceptions; unapproved functional failures prevent release.
- [ ] AC-4: Updated packaging/install/upgrade instructions explain trust bootstrap, offline verification and post-release build identity without changing deferred timing thresholds.

## Tasks

- [ ] Inventory release automation and choose an available signing/attestation authority before readiness.
- [ ] Implement artifact provenance and pre-execution verification contract with local bounded fixtures.
- [ ] Expose source identity and profile/exception summaries for lean and combined artifacts.
- [ ] Update canonical install, upgrade and packaging guidance; qualify verification on the supported consumer paths.
- [ ] Complete readiness before code edits and required delivery review; retain durable results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and guidance | Implementer | Readiness | Single write owner; serialize shared files |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/pack_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/`
- `docs/architecture/testing-architecture.md`

Write ownership: implementer owns admitted behavior and its derived callers/tests. Canonical seed edits precede regeneration; do not hand-patch generated surfaces. Reviewers are read-only. Protect publication guards, recovery checkpoints, unrelated user hooks/docs, secrets and existing evidence; no historical ledger rewrites. Confirm exact seed/config edits during Prepare before opening gates.

## Affected Architecture Docs

Update `docs/architecture/testing-architecture.md` and applicable canonical setup, extension, lifecycle or release guidance.

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

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Choose artifact provenance tied to source and explicit release qualification. | Coherent contract with focused regression coverage | Self-hashing archives alone: no independent authenticity. Per-commit VERSION churn alone: does not authenticate artifacts or explain exceptions. |

## Open Decisions

Before readiness, select signing/attestation authority and offline trust/bootstrap mechanism from actual release infrastructure.

## Risks

| Risk | Mitigation |
| --- | --- |
| Verification must bootstrap outside the untrusted archive; authority and offline trust distribution must be chosen before implementation. | Use public-path positive and negative controls; preserve contracts outside scope. |
| Review overhead | Keep durable conclusions in wave.md and temporary probes outside tracked evidence folders; reuse valid qualification. |
