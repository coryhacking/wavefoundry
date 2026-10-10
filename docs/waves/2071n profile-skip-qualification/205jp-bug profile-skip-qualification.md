# Make packaging profile qualification independent of local graph state

Change ID: `205jp-bug profile-skip-qualification`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 2071n profile-skip-qualification

## Rationale

Finish the requested local 1.29.0 pack without weakening its profile qualification. The default receipt proves 12030 tests with 20 skips. The full second-profile run passes all 177 files but reports 53 skips. Its temporary checkout intentionally omits the local index, causing live-graph tests to skip independently of vocabulary. One repository-corpus test also skips whenever WAVEFOUNDRY_TEST_PROFILE exists, including the declared-tools profile whose vocabulary is unchanged. Neither reason satisfies the packaging rule for extra skips. The operator subsequently waived the additional skips for local pack 1.29.0+pviw only, then authorized this repair after that build. The local pack is built and inspected; no release qualification is claimed.

## Requirements

1. Tests whose contract is graph classification, evidence partitioning or evidence lookup use an isolated published graph fixture with realistic production and evidence nodes, sufficient ranked communities and explicit indexed classification controls. Their assertions run without a pre-existing local index under both packaging profiles.
2. The admitted-ID corpus test uses the existing default_profile_only marker based on loaded vocabulary/layout differences, rather than the presence of the run-mode environment variable. It runs under the declared-tools profile and keeps its existing non-vacuous corpus assertions.
3. Retain existing public response and publication paths, presence assertions, classification oracles and precise ranking/lookup checks. Do not turn executed coverage into allowed skips or copy a mutable operator index into fixtures.
4. Historical upgrade/review-policy tests use committed byte-exact fixtures from the three historical revisions they exercise, with provenance and SHA-256 verification, instead of skipping when a copied checkout lacks those Git refs. Preserve old-code execution and exact migration/refusal assertions. Missing or corrupt fixtures fail clearly; do not silently substitute current source.
5. Keep the packaging skip contract and production behavior unchanged. Qualification must enumerate skip identities/reasons against the same source tree rather than relying only on aggregate counts.

## Scope

**Problem statement:** Successful profile exit codes conceal extra skips caused by checkout state and an overly broad run-mode skip predicate.

**In scope:** The graph-quality and retrieval test cases that read the running checkout's graph, shared test fixture support, the admitted-ID corpus marker, historical review-policy/storage tests and bounded pinned-source fixtures, and verification documentation.

**Out of scope:** Graph extraction/resolution/ranking behavior, release policy changes, waiving checks, dependency/bootstrap pin updates, downstream deployment, publishing, commits and wave closure.

## Acceptance Criteria

- [x] AC-1: Each affected graph test executes its existing load-bearing assertions against an isolated published fixture when no local index exists, with independently checked production/evidence and indexed-control presence.
- [x] AC-2: The corpus test runs with the declared-tools profile and retains its assertions; a genuinely renamed layout skips only through default_profile_only with its explicit reason.
- [x] AC-3: Known-bad evidence classification, partition/lookup or corpus acceptance is detected by the affected tests; empty graph or empty evidence cannot satisfy them.
- [x] AC-4: The four historical tests execute their original old-code paths without historical Git refs using byte-exact provenance-verified fixtures; missing/corrupt fixtures fail clearly and substituted current source is detected.

## Tasks

- [x] Identify every live-graph skip contributing to the copied-tree difference and implement bounded isolated fixtures.
- [x] Replace the environment-only corpus skip and add targeted marker regression coverage.
- [x] Capture bounded historical source fixtures and verify provenance/digests; retain all four historical behavior checks without checkout history.
- [x] Run affected tests, independently review the frozen diff, reconcile AC evidence and document qualification commands/results.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Qualification repair | implementer | Readiness | Tests and test support only |
| Independent verification | code-reviewer, qa-reviewer, release-reviewer | Frozen implementation | Execute realistic controls and mutation probes |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.wavefoundry/framework/scripts/tests/test_change_id_path_guard.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py`
- `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` and `docs/contributing/build-and-verification.md`: describe isolated graph fixtures and exact skip accounting. No production module ownership changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes executed coverage independent of operator state |
| AC-2 | required | Preserves declared-tool coverage and intentional vocabulary pins |
| AC-3 | required | Prevents empty fixtures or permissive assertions from hiding defects |
| AC-4 | required | Retains old-code compatibility coverage without operator history |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-09 | Reflect: independent code, QA, architecture and release approve finaldelivery; full seven-role council approves withnotes after its own17baseline checks,3detectedmutants and independent534capture audit. AllACs/tasks have evidence; both findings remain real/do_now with completed independent lane clearance. Docsvalidation passes0errors/warnings and gitdiffcheck passes. Implementation/review complete; leave paused for operatorclosuredecision, with no commit/push/newpack. | Typed delivery approvals; evidence/delivery/wf-2071n-final-*; qualification-evidence.md |
| 2026-10-09 | Observe: finalqualification runs all178 files perprofile without failures: default12040 tests/13skips/626.634s; second12032/28/629.215s; declared12040/13/644.729s. Exact534-worker capture audit passes: declared skips identical to default; second15extraidentities all explicitdefault_profile_only, one shared-baseline markedreason change retained. Source15 remains c7bd807a8edbe7878841b4e2971e6405f5bc7418e60ed86658125e770bc039d0; receipt168eafe7d59e87c2acf0ab232ae3ac0a418b3aeec0a6972fef0fad78b9e1c22d unchanged by profile diagnostics. | evidence/delivery/final/skip-inventory.json; lossless534worker captures and capture-manifest.json; canonical-receipt.json; all three full logs |
| 2026-10-09 | Observe: fresh independent QA/code/release verify the actual corpus correction; architecture/release verify measured scratch-query provenance matches repaired prose. All five typed lane reverifications clear the two original real findings in cycle1. The final canonical full default passes12040 tests/178 files/13 skips in626.634s; current receipt168eafe7d59e87c2acf0ab232ae3ac0a418b3aeec0a6972fef0fad78b9e1c22d. Full copied second and declared qualification and final approvals remain pending. | evidence/delivery/wf-2071n-reverify-*; typed findings QA-2071N-01 and ARCH-2071N-02; /private/tmp/wf-2071n-final-default.log |
| 2026-10-09 | Observe: two-item cycle1 repair landed; actualsecond focused test_profile_support runs76 tests,0skips,green. Derived-pattern deletion in scratch is the named guard pin; finalfixedsource packet changes only test_profile_support and testing-architecture,13 other reviewedpaths exact. Finalall-profile qualification and fresh lane clearance remain pending. | [consolidated evidence](wave.md#evidence-retention) |
| 2026-10-09 | Reflect: initial default full suite green12040/178/13, but fullsecond12032/178 has one failure introduced in the new marker regression: simulatedstock editable constants omitted the derived MEMBER_ID_LABEL_RE. QA single-property correction recovers1105 accepted IDs. Architecture/release also caught false current live-partition coverage prose. Both are bounded admitted test/doc repairs, not production or scope changes. All initial frozen-round findings were collected and deduplicated before mutation; typed repair_start cycle1 recorded. | QA-2071N-01; ARCH-2071N-02; evidence/delivery/initial |
| 2026-10-09 | Thought: repair the declared marker meta-test by synchronizing its derived label regex with its intentionally restored base label; update only the false architecture coverage sentence. Preserve real corpus >100/zero-rejected assertions and intentional renamed-profile skip. Then run actualprofile-focused repro and a guard-deletion control, freeze once and obtain fresh independent affected-lane reverification. | Current actual source and QA adjacent-control evidence |
| 2026-10-09 | Observe: graph writer final21 affected cases pass with0 skips; broader1149-case two-module run green before final lookup guards, which final targeted rerun covers. Twelve classification/partition/identity/empty/ignored-path/crossing/presence mutants detected. Historical writer12 cases pass in default/second/declared one-commit copies missing all old refs;13 present entries match trustedGit and one optional absence is verified. Three source/bundle/size mutants detected. All writer source is frozen. | evidence/implementation logs and scoped patches; old-beforebytes match readiness Gitblobs |
| 2026-10-09 | Thought: qualify frozen integrated source through the full canonical suite and both packaging profiles; capture unchanged per-file unittest output externally for exact skip identities/reasons. Independent delivery reviewers receive the same frozen tree, distinct contexts and read-only probes. No source/repository writes during canonical artifact-guard runs. | Output-only capture adapter tested on real pass/skip subprocess output; source pack fingerprint |
| 2026-10-09 | Coordinator marker checks: six actual corpus/marker tests pass, including declared environment with loaded stock constants and explicit renamed-layout skip. An in-memory is_change_id=False mutant makes the actual corpus assertion fail (one failure, no errors/skips), proving retained non-vacuity. | DefaultProfileOnlyMarkerTests.test_repository_corpus_runs_under_declared_tools; test_repository_corpus_names_its_renamed_layout_skip; IsChangeIdTests |
| 2026-10-09 | Readback: AC1–4 preserve existing graph classification, partition, lookup, corpus and cross-version assertions while replacing operator-index/Git-ref preconditions with test-owned published graphs and immutable historical bytes. Declared-tools corpus runs; renamed layout alone uses default_profile_only. The two v1.14 cases use old carrier documents with the current reconciler; the v1.22 entry and pinned reader run with current siblings, exactly as before. No production behavior, package policy, commit or closure changes. | Six named test modules; graph_fixture_support and historical fixture support |
| 2026-10-09 | Thought: implement graph and historical fixtures concurrently with separate file ownership; coordinator owns corpus marker, docs and inventory integration. Current request authorizes this readied implementation sequence. After integration run focused checks and default/second/declared qualification, then fresh independent delivery lanes and council. | Successful typed readiness and Prepare; implementation allocation |
| 2026-10-09 | Operator explicitly waived additional profile skips for the current local test pack, then requested Prepare, Implement and Review of this plan after the pack. No release waiver, commit or closure authority inferred. | Current operator messages |
| 2026-10-09 | Inventory identifies14 newly skipped retrieval cases, one corpus case and four missing-history cases. Historical revisions: v1.14.0, v1.22.0, pinned5e798daa. Plan scope/Requirements/AC-4 extended before readiness. | /private/tmp/wf-205jp-historical-skip-inventory.log; exact22-case profile/default skip probes |
| 2026-10-09 | Planned only; source unchanged, no admission/readiness or repair claimed. Full second profile is green by exit code but its skip contract is not proven. Declared run survived daemon restart and remains running. | /private/tmp/wf-package-129-second.log; /private/tmp/wf-package-129-declared.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-09 | Prefer isolated published graph fixtures and a vocabulary-aware corpus marker. | Exercises real behavior in copied checkouts and retains the declared-tools corpus check. | Mark all live-graph tests default-only: suppresses relevant distribution coverage and still loses declared coverage. Copy the operator index: inherits mutable/stale state and makes qualification checkout-dependent. Waive skips for this local build: possible only by explicit operator exception, with the limitation disclosed. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A tiny synthetic graph makes ranking assertions vacuous | Include enough distinct production/evidence communities to fill independent limits and keep negative controls |
| Fixture data encodes expected results directly | Publish through the actual graph paths; verify source controls and mutant detection separately |
| Scope grows into a graph algorithm change | Keep behavior unchanged and escalate an actual production defect separately |

## Session Handoff

Implemented in this closed wave; final qualification, review outcomes, retained evidence and limits are recorded in wave.md.
