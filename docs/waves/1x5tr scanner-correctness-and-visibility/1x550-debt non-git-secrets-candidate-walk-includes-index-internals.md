# The Secrets Scanner's Candidate Walk Includes Index Internals in Non-Git Repositories

Change ID: `1x550-debt non-git-secrets-candidate-walk-includes-index-internals`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-05
Wave: 1x5tr scanner-correctness-and-visibility

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
   This means the existing canonical/legacy index prefixes, logs/locks prefixes,
   exact authority paths and four authority predicate families (semantic walk
   layers 2–4). Arbitrary custom index directories are outside this bounded fix;
   semantic walking itself does not dynamically exclude them today.
2. The exclusion SHALL not narrow the git-tracked candidate set, which is
   intentionally wider than the index corpus (wave `1rsha`).
3. A test SHALL pin that a non-git fixture's `secret_scan_cache` holds no
   `.wavefoundry/index/` path after a full build, and that the sidecar
   breaker's denominator for that store is deterministic across two builds.
   The fixture starts with a fresh cache. This is prevention of new pollution,
   not migration: previously cached machine rows may remain until the separate
   existing cache reset/reconciliation path removes them. No cleanup guarantee
   or change to orphan reconciliation is included.

## Scope

**Problem statement:** the non-git candidate walk scans the index's own
files, which pollutes the secret-scan cache and makes the sidecar breaker's
denominator timing-dependent.

**In scope:**

- The non-git candidate walk in the secrets scanner.
- Extract those existing exclusions to a lightweight shared owner used by the
  semantic walker and non-git fallback. Keep semantic eligibility unchanged.
- Preserve ordinary `.env`, lockfiles, generated assets, and noncanonical
  same-named files; do not reuse the semantic walk's extension/name/size filters.
- A determinism pin on the `secret_scan_cache` denominator in a non-git fixture.

**Out of scope:**

- The git-tracked candidate set and its content-addressed skip semantics.
- The Lance eligibility reap and the orphan-store reconciliation (wave `1x54z`).

## Acceptance Criteria

- [x] AC-1: Starting with a fresh cache, after a full scanner/cache pass of a non-git fixture, `secret_scan_cache` holds no path under `.wavefoundry/index/`; every machine-authority class is excluded from fallback candidates.
- [x] AC-2: Two consecutive full scanner/cache passes of that unchanged non-git fixture produce identical `secret_scan_cache` membership and row count. Historical polluted caches are not covered by this prevention guarantee.
- [x] AC-3: The git-tracked candidate set is unchanged, pinned by the existing `1rsha` tests.

## Tasks

- [x] Locate the non-git fallback walk in the scanner and apply the machine-authority exclusions.
- [x] Add the determinism pin.
- [x] Record the mutation (exclusion removed) before review.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| exclusion  | implementer | —          | The walk fallback only.                |
| pin        | implementer | exclusion  | Non-git fixture, two builds, one count. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` (candidate owner)
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/machine_authority.py` (shared exclusion owner)
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
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
| 2026-09-05 | Reproduced before admission using the real scanner and SQLite in a disposable non-git tree: 4 then 8 cache rows on unchanged full scans. Git control preserves machine paths and ordinary secret-bearing candidates. | Discovery probe under `/tmp/scanner-scope`; `_get_all_files` owns fallback, `update_secrets_scan` enumerates the same candidates for cache recording. |
| 2026-09-05 | Observe: shared policy extraction and fallback wiring complete. All 11 authority examples excluded, 13 ordinary/lookalike paths preserved; Git tracked and untracked sets unchanged. Two real fresh-cache scans retain identical 14-path membership. | `test_secret_scan_cache.py`: 22 tests pass (2.130s); `FileWalkerTests` + `CorpusExclusionCensusTests`: 19 pass (0.735s). |
| 2026-09-05 | Mutation: replace scanner `is_machine_authority_path` with a predicate returning False. Named determinism test fails exactly one assertion; clean and restored controls pass. | `NonGitMachineAuthorityTests.test_two_full_scans_keep_exact_cache_membership_without_index_internals`. No source mutant left on disk. |
| 2026-09-05 | Observe: preserve wider fallback when Git ls-files fails inside a real Git worktree. Only genuinely non-git fallback applies authority exclusions. | New real-Git transient-failure control preserves 11 tracked authority paths; final cache suite 23 plus walker/census 19 = 42 green (2.930s). |
| 2026-09-05 | Delivery review: the security and red-team seats (SEC-DEL-1, RED-DEL-4) note that the memory-archive, pointer and event-ledger families are excluded only on the non-git walk while their git-tracked copies stay scanned; the CHANGELOG entry discloses the trade for operator acknowledgement, no code change. | `CHANGELOG.md` Unreleased; events ledger. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-05 | Limit exclusion to existing semantic machine-authority classes. | Shares a known policy without broadening semantic eligibility or adding custom-directory plumbing. | Full semantic walker would suppress legitimate scanner candidates; duplicate predicates would drift. |


## Risks


| Risk                                                        | Mitigation                                                    |
| ----------------------------------------------------------- | ------------------------------------------------------------- |
| Narrowing the non-git walk hides a real secret under an excluded path. | The exclusions are the index directory and machine-authority paths only. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
