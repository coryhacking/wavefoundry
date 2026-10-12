# Refresh the uv bootstrap pin for release

Change ID: `20gz2-maint refresh-uv-release-bootstrap`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12
Wave: 20gz3 uv-release-bootstrap

## Rationale

The operator approved updating the official 1.29.0 release bootstrap from uv 0.12.4 to 0.12.17 after reviewing its integrity, signed-binary and installer fixes. The new version satisfies the 21-day release-age policy. Keep the existing bootstrap-only contract: a usable uv in the tool environment or trusted PATH remains untouched.

## Requirements

1. Bootstrap uv 0.12.17 only when setup finds no usable existing uv, using the complete exact wheel filename/SHA256 table published by PyPI for that version.
2. Preserve wheel-only, hash-required installation, age policy, bounded subprocess execution and existing-uv selection without changing setup control flow.
3. Verify the approved release inventory and existing regression controls, exercise the new binary in a disposable environment, and requalify the framework and both distribution profiles before packaging.

## Scope

**Problem statement:** The tested bootstrap pin predates eligible installer and integrity fixes needed for the official release baseline.

**In scope:** The two bootstrap constants in `.wavefoundry/framework/scripts/setup_index.py`; release changelog entry; existing setup tests and finite disposable installation/CLI controls; release qualification and artifact verification.

**Out of scope:** Automatically replacing existing uv; dependency-resolution policy, model changes, setup algorithms, new configuration or broad test infrastructure; native Windows execution; commit/tag/push/publication without the applicable operator authority.

## Acceptance Criteria

- [x] AC-1: The bootstrap requirement is exactly uv 0.12.17 and its wheel table equals the complete non-yanked PyPI release inventory, including supported Windows, macOS and Linux wheels older than the package-age cutoff.
- [x] AC-2: Existing usable uv is retained and missing-uv bootstrap remains wheel-only and hash-required; refusal and timeout controls stay effective.
- [~] AC-3: The approved uv binary installs and runs in a disposable environment; canonical default, second and declared qualification pass with valid exact skip comparisons before the official feature/model artifacts are built. *Operator authorized release on 2026-10-12 with alternate-profile exceptions deferred: second-profile warm-estimator timing is inconclusive during concurrent reviews; declared-profile combined log-tail assertion is tracked in planned wave 20h6q/change 20gz6. Default 12,402-test qualification is green, both profile executions are complete, and exact skip audits match; the two red reports and canonical comparison refusals are preserved. Disposable uv installation and CLI controls passed. This defers the all-green profile requirement for this release only.*

## Tasks

- [x] T-1: Replace the pin and full hash table from the official release metadata; document the bootstrap-only change in CHANGELOG.md.
- [x] T-2: Run existing bootstrap/trusted-lookup/refusal tests, an invalid inventory control and a disposable real bootstrap/CLI smoke check; obtain independent delivery review.
- [x] T-3: Run canonical qualification and both package profiles, reconcile evidence and verify feature/model release artifacts.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Pin and inventory | implementer | readiness | One source writer; no control-flow change |
| Independent verification | code-reviewer, qa-reviewer, security-reviewer, release-reviewer | implementation | Exact registry comparison, existing-uv preservation and package evidence |
| Qualification and packaging | wave-coordinator | source frozen | Sequential profile suites; current artifacts only |

## Serialization Points

Only the coordinator edits source, changelog and lifecycle state. Reviewers are read-only and use disposable temporary fixtures.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

Root CHANGELOG.md and release-generated VERSION/manifest stamps are also reviewed. The test file is a read-only verification target; no test-source change is planned.

## Affected Architecture Docs

N/A: one version/hash inventory refresh; bootstrap selection, boundaries and documented behavior remain unchanged. The changelog states that existing uv installations are not automatically upgraded.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The release must install the approved, verified artifact set |
| AC-2 | required | Preserve the existing-user contract and integrity checks |
| AC-3 | required | The pin changes executable dependencies and must be qualified before shipping |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Final default qualification passed 12,402 tests/185 files/12 skips and wrote a green receipt for source 7ed6f72bf5f7df9eb7940d2f5039f915634c10d145f54598c409b960b6dcabac. Second profile completed 12,394 tests with one warm-estimator timing failure; declared completed 12,402 tests with one missing stdout marker in the nonzero-exit bounded-log fixture. Both reports are complete but red. Read-only skip audits match the required 16 marked second-profile extras and exact declared/default skips; canonical comparisons correctly refuse the red reports. Operator said concurrent reviews prevent timing conclusions: no further timing-only retries or repairs. Packaging confirmation is pending for the separate log-content assertion. | Qualification cache reports; test_server_context_efficiency.test_repeated_warm_estimator_and_projection_budgets; test_child_tee.test_large_two_pipe_logs_finalize_on_nonzero_exit_and_timeout |
| 2026-10-12 | Release qualification waits for test-only repair wave 20gz5. First default run passed all 12,402 tests but concurrent reviewer telemetry created an untracked artifact; it was identified and quarantined. Retry exposed the separate large child-log timeout fixture assertion. UV checks and reviewed source remain valid; no fresh full-suite receipt is claimed. | test_child_tee.ChildTeeTests.test_large_two_pipe_logs_finalize_on_nonzero_exit_and_timeout; wave 20gz5 |
| 2026-10-12 | Pin/hash table and changelog updated. Exact 18-wheel registry comparison passes; omitted-wheel and wrong-hash controls reject. Disposable real bootstrap refuses an incorrect hash, installs uv 0.12.17, installs a local fixture dependency, reports an unsatisfiable dependency and retains an existing uv. All 203 setup tests passed with zero skips. Operator separately authorized and received the local tool-venv uv update to 0.12.17. | setup_index bootstrap constants; test_setup_index.py; temporary real-install and inventory probes |
| 2026-10-12 | Operator approved update. Current source confirms existing uv is preferred; the pin is bootstrap-only. Official registry review found 18 eligible wheels for 0.12.17. | setup_index._uv_bin; setup_index._install_deps; PyPI uv 0.12.17 release JSON |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Refresh only the exact bootstrap pin and its full wheel hashes | Follows the release-age policy and incorporates installer/integrity fixes without changing existing installations | Retain 0.12.4: preserves prior qualification but delays eligible fixes and needs a workflow exception. Force-upgrade every existing uv: changes the established operator contract and exceeds the requested scope. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Incorrect/missing wheel hashes or unaged release | Independent exact PyPI inventory comparison, platform and date checks, existing inventory test and invalid control |
| Changed upstream exit codes/install behavior | Real disposable bootstrap and CLI smoke, existing refusal tests, full qualification |
| Implied universal upgrade or native-platform proof | Explicit bootstrap-only scope; retain existing uv; disclose macOS-only real execution |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
