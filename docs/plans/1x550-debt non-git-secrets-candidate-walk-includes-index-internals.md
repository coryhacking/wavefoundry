# The Secrets Scanner's Candidate Walk Includes Index Internals in Non-Git Repositories

Change ID: `1x550-debt non-git-secrets-candidate-walk-includes-index-internals`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: TBD

## Rationale

Recorded during the delivery review of wave `1x54z` (finding QA-DEL-7, rejected
as outside that wave's scope). In a repository without git, the secrets
scanner's candidate set falls back to a walk that can include files under
`.wavefoundry/index/` (the SQLite state store, the build lock, and, depending
on timing against the Lance writer, Lance transaction and manifest files).
Those rows land in `secret_scan_cache`, which inflates the store's row count
and therefore the denominator of the `1u8nz` mass-removal breaker for that
store, so the same fixture defers or reconciles depending on a race. The
effect is confined to non-git targets and to the sidecar's own breaker
arithmetic; the scanner still finds what it finds. The `1x54z` test that
asserts on the reap alone neutralises the sidecar plan for this reason.

## Requirements

1. The scanner's non-git candidate walk SHALL exclude the index directory and
   every other path the semantic walk excludes as machine authority, so the
   candidate set is a subset of repository content.
2. The exclusion SHALL not narrow the git-tracked candidate set, which is
   intentionally wider than the index corpus (wave `1rsha`).
3. A test SHALL pin that a non-git fixture's `secret_scan_cache` holds no
   `.wavefoundry/index/` path after a full build, and that the sidecar
   breaker's denominator for that store is deterministic across two builds.

## Scope

**Problem statement:** the non-git candidate walk scans the index's own
files, which pollutes the secret-scan cache and makes the sidecar breaker's
denominator timing-dependent.

**In scope:**

- The non-git candidate walk in the secrets scanner.
- A determinism pin on the `secret_scan_cache` denominator in a non-git fixture.

**Out of scope:**

- The git-tracked candidate set and its content-addressed skip semantics.
- The Lance eligibility reap and the orphan-store reconciliation (wave `1x54z`).

## Acceptance Criteria

- [ ] AC-1: After a full build of a non-git fixture, `secret_scan_cache` holds no path under `.wavefoundry/index/`.
- [ ] AC-2: Two consecutive full builds of the same non-git fixture produce the same `secret_scan_cache` row count.
- [ ] AC-3: The git-tracked candidate set is unchanged, pinned by the existing `1rsha` tests.

## Tasks

- [ ] Locate the non-git fallback walk in the scanner and apply the machine-authority exclusions.
- [ ] Add the determinism pin.
- [ ] Record the mutation (exclusion removed) before review.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| exclusion  | implementer | —          | The walk fallback only.                |
| pin        | implementer | exclusion  | Non-git fixture, two builds, one count. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secret_scan_cache.py`

## Affected Architecture Docs

`N/A`: confined to the scanner's candidate selection; no boundary, flow, or
verification-architecture change.

## AC Priority


| AC   | Priority  | Rationale                                             |
| ---- | --------- | ----------------------------------------------------- |
| AC-1 | required  | The defect itself.                                    |
| AC-2 | required  | The observable consequence (a timing-dependent breaker). |
| AC-3 | required  | The `1rsha` candidate semantics must not narrow.        |


## Progress Log


| Date       | Update                                                                                                  | Evidence                                   |
| ---------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| 2026-09-04 | Filed from the `1x54z` delivery review (QA-DEL-7, probe P10: 14 cache rows for 12 repository files). | Wave `1x54z` events ledger, finding QA-DEL-7. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                        | Mitigation                                                    |
| ----------------------------------------------------------- | ------------------------------------------------------------- |
| Narrowing the non-git walk hides a real secret under an excluded path. | The exclusions are the index directory and machine-authority paths only. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
