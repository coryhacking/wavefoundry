# Isolate qualification fixtures from the outer profile

Change ID: `2080b-bug qualification-fixture-default-profile`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-10
Wave: 2080c qualification-fixture-default-profile

## Rationale

The requested local package is blocked by two reproducible qualification-report test failures under the second profile. QualificationCLITests copies edited outer modules, clears only the profile environment variable, and assumes the copied constants are shipped defaults. Its nested default run therefore has three skips rather than one and the nested second run has no additional skips. Repair this test fixture without changing qualification policy, skip markers, expected counts or production code.

## Requirements

1. Initialize the copied fixture modules from the existing shipped-default profile helper before executing its nested runner. Mutate only the scratch copy; retain explicit nested second/declared runs.
2. Keep exact count, skip ID/reason, default-only marker, execution-origin and receipt assertions unchanged. The test must still detect a real reporting/count defect.
3. Verify this test file under default, second and declared profiles; retain all existing tests without newly marking or skipping them.

## Scope

**Problem statement:** An outer distribution profile leaks into a nested known-default qualification fixture.

**In scope:** `.wavefoundry/framework/scripts/tests/test_qualification_report.py` only.

**Out of scope:** Runner/report behavior, profile policy, new skips, weakened assertions, performance budget changes or package gate waivers.

## Acceptance Criteria

- [x] AC-1: The nested default control reports four tests and one real skip, with exact skip identity/reason, under each outer profile. Oracle: existing real CLI worker test in default/second/declared runs.
- [x] AC-2: Nested second controls retain exactly two marked default-only skips and nested declared controls match default; receipt and source identity remain valid. Oracle: existing profile CLI comparison assertions under each outer profile.
- [x] AC-3: Removing scratch default initialization recreates the second-profile failures, while the canonical modules remain unchanged. Oracle: temporary known-bad copy and canonical source hashes.

## Tasks

- [x] Initialize the scratch fixture through the existing helper.
- [x] Verify all three profile workers and the known-bad control.
- [x] Independently review and record delivery evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture repair | implementer/root | Current typed readiness | One source file; serialize before 2071o activation |
| Independent verification | code-reviewer, qa-reviewer | Frozen repair | Real CLI/profile controls |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`

## Affected Architecture Docs

N/A: test-only fixture initialization uses existing helper and preserves the runner/report contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Restore an honest known-default control under distribution runs |
| AC-2 | required | Preserve exact profile differences and receipt invariants |
| AC-3 | required | Prove fixture repair rather than weakening reporting checks |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | AC-1–AC-3 implemented: selected default19/0skip14.506s, second19/0skip15.652s, declared19/0skip15.640s pass. Removing the single scratch-default call in a disposable copy returns1 with exact original failures(3,3)!=(4,1), default_only0!=2; canonical SHA25674fe2fbe7913921f77e2185a8ad6d41ce943703134be76731c41d23c8952453a unchanged. No assertions changed. | QualificationCLITests; /private/tmp/wf-local-pack-2087n/fixture-*.log |
| 2026-10-10 | Readback: initialize only copied vocabulary/layout from existing shipped_default_profile/apply_profile before nested runners. Previously copied second constants yield(3tests,3skips); afterwards known-default expects(4tests,1skip) and nested second adds2marked skips. Preserve production and every exact assertion. AC-1–AC-3; only test_qualification_report.py. | Current typed readiness; independent helper/canonical refusal and public pre-fix controls |
| 2026-10-10 | Plan created from actual second-profile failures; no source edit. Independent timing-only worker rerun passes unchanged. | Temporary second.log and timing-recheck.log under /private/tmp/wf-local-pack-2087n |

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-10 | Use existing shipped-default helper on scratch modules | Removes inherited distribution constants while preserving exact oracles. Rejected marking these tests default-only because that loses distribution qualification. Rejected adapting expected counts to inherited constants because the fixture intentionally measures default-to-profile transitions. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Scratch helper accidentally targets canonical files | Existing apply_profile refuses canonical directory; check source hashes |

## Session Handoff

Prepare and independently review before source edit; leave ready to close after delivery. Local package awaits this repair and 2071o.
