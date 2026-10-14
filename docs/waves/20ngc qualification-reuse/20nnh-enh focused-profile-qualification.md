# Focus compatibility profile qualification

Change ID: `20nnh-enh focused-profile-qualification`
Change Status: `active`
Owner: Engineering
Status: active
Last verified: 2026-10-14
Wave: `20ngc qualification-reuse`

## Rationale

The current release workflow runs all discovered test files under default, renamed vocabulary/layout and declared tool profiles. run_tests._profile_run_in already accepts selectors, but qualification_report.compare requires equal worker inventories. A smaller run needs explicit completeness semantics and a reviewed coverage rule before it may satisfy packaging.

## Requirements

1. Keep one full default canonical suite. Define profile qualification scope at test-file granularity from the customization contracts each profile changes and their affected consumers, including fixture construction, dynamic declarations and served-tool behavior. Changes-only selection and name matching alone are insufficient.
2. Classify discovered test files as requiring a profile or demonstrably independent of that profile, with concise rationale tied to contracts. Unknown/unclassified files, an invalid inventory, unknown profile extensions or a changed coverage contract default to the full affected profile rather than silently skipping work.
3. Execute the selected compatibility inventory through existing profile application, worker isolation, cleanup and guards. Full-profile execution remains available. Keep selectors diagnostic until the explicit compatibility-qualification path validates coverage.
4. Compare selected profile observations with the same worker subset of a complete matching default report; verify exact expected/observed membership, source/applied-profile identity and existing skip-ID/reason rules. A focused report must never pass as a full-suite report.
5. Qualify the initial selection against a full reference matrix and finite negative controls at affected seams; record retained coverage and worker count savings. No timing pass threshold, permanent raw artifacts, additional ordinary wave gate or consumer-upgrade work.
6. Repair the operator-approved child-timeout fixture completion-marker race: write and close a sibling temporary marker before atomically publishing the final marker. Preserve the existing timeout, held-pipe, reader/thread cleanup and completion assertions; make no production child-output change.

## Scope

Runner/profile support, compact report coverage identity/comparison, test-file coverage inventory and packaging documentation. No removal of unique assertions, weakening of default-only skip rules, model benchmark, scheduler change or general changed-test planner.

The bounded qualification-fixture repair additionally covers only completion-marker publication in ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers. It does not change timing budgets or resolve the separately deferred performance gate.

## Acceptance Criteria

- [ ] AC-1: The qualification selector includes every discovered file with an affected or unknown customization contract, and safely expands to full-profile work on incomplete or invalid classification.
- [ ] AC-2: Partial, omitted, duplicated, mismatched-profile and stale-inventory reports refuse; valid selected reports compare against the corresponding complete default subset using unchanged skip rules.
- [ ] AC-3: At least one proven independent test file avoids repeat execution, while affected contract regressions are still caught by selected profile runs; observed file counts and qualification limits are recorded.
- [ ] AC-4: Full default and explicit full-profile behavior and worker protection remain intact, and no ordinary upgrade invokes compatibility tests.
- [x] AC-5: The child-timeout fixture publishes a complete final marker atomically; a controlled delay before its payload write cannot expose an empty final marker. Existing timeout and cleanup assertions remain unchanged, and reverting atomic publication reproduces the failure.

## Tasks

- [x] Derive and review a small file-level coverage inventory from the current profile definitions and consumers; classify uncertainty conservatively.
- [x] Implement explicit compatibility selection and report scope validation without reclassifying existing diagnostic selectors.
- [ ] Use a reference full matrix plus contract regression controls once to qualify the selection, then document the smaller release workflow.
- [x] Publish the child fixture completion marker atomically and independently verify the ordinary, delayed-write and reverted-publication controls.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/qualification_report.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/scripts/tests/test_child_tee.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

docs/architecture/testing-architecture.md, docs/contributing/build-and-verification.md and docs/prompts/package-wavefoundry.prompt.md: explicit profile coverage and fallback rules.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-5 | required | Removes a reproduced fixture race without weakening its child timeout or cleanup oracle. |

## Progress Log

- 2026-10-14: QA-FINAL-MARKER-PUBLICATION cycle 2 is terminal after fresh independent verification; convergence checkpoint recorded. Reviewer independently executed ordinary/delayed-write positives and the reverting-publication mutant: two passes and the exact expected empty-read failure, zero errors/skips. Only the three-line fixture publication hunk differs from its original source; all assertions/deadlines remain intact. Code delivery approval is current; full QA/release remains pending qualification. AC-5 and the marker task are complete. Canonical evidence: .wavefoundry/framework/scripts/tests/test_child_tee.py::ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers. Timing stays deferred, all waves paused, no new permanent evidence artifact or separate memory record needed.

Repair verification: the named child-timeout fixture passes normally and with a 250 ms pause between opening the sibling temporary marker and writing its payload; the final marker is absent during that gap. Reverting only atomic publication in the in-memory child command reproduces exactly one empty-string assertion failure. All three controls execute the actual fixture with zero errors/skips; production child_tee.py and every existing assertion are unchanged. Canonical reference: .wavefoundry/framework/scripts/tests/test_child_tee.py::ChildTeeTests.test_explicit_timeout_includes_withheld_descendant_pipes_and_closes_readers. Source SHA-256 b594624f17597eb1022b28276ad89ff0561bb90dce8a3bd5dc82a3afebda3e8f. Fresh independent verification follows; full qualification and timing remain deferred.

The operator explicitly approved this bounded fixture repair on 2026-10-14 after its preexisting empty-marker failure was independently reproduced. Timing remains deferred; this addition grants no full qualification waiver. Readback: change only final marker publication in the named fixture, then prove delayed publication and a reverting mutant through that same test.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |
| 2026-10-14 | Readback: after default-detail reuse, explicit compatibility qualification will run all affected or uncertain workers and omit only a small reviewed independent set. Unknown files or changed coverage inputs restore full-profile execution; comparison validates the selected inventory against a complete default baseline. Existing full-profile and diagnostic selectors retain their meanings. | Same sole implementer owns runner, report, profile support, tests and packaging guidance; reference full matrix and finite negative controls precede delivery approval. |

| 2026-10-14 | Observe: Explicit compatibility selection and report scope validation implemented. Focused report/profile-support/cache modules passed 41/80/97 tests. A real two-worker fixture executed only the selected worker, retained exact skip comparison, detected failure in an affected worker and exercised the excluded worker trap through the full path. | test_qualification_report.py, test_profile_support.py, test_run_tests_cache.py. Current inventory excludes only test_check_version.py with a pinned independence rationale; other 186 workers remain affected or uncertain. Unknown/changed contracts fall back to full. Guard-removal controls, full reference matrix and delivery review remain pending. |

| 2026-10-14 | Observe: Final focused canonical run passed 218 tests, zero skips; final parser-control addition then passed its 98-test file, zero skips. Framework source frozen at 476f7794c9adbbe1808ce6278e8fa56451520a642bb679506d5b983357bfb217; coverage f089d951b33e624a48f1f6e843a64934159d88e33dbdf6492273d31f58d3b008. | Full default qualification started. Actual selected dispatch was tested with a two-worker fixture; the full reference matrix will check coverage without fabricating selected execution or repeating 186 workers. |
| 2026-10-14 | Guard-removal evidence: isolated removal of coverage contract hash checking caused 32 assertion failures in CompatibilityCoverageTests.test_every_changed_contract_forces_full_profile; removal of trusted scope equality caused four assertion failures in QualificationCLITests.test_selected_report_cannot_authorize_its_own_coverage_or_applied_identity. No errors or skips in either mutant control. | Mutations were confined to compiled temporary module copies; live source remained unchanged. These failures pin changed-dependency fallback and refusal of self-asserted coverage. |
| 2026-10-14 | Observe: First full default run executed 11,621 tests across 187 files with 12 skips; its sole failure was the existing warm lifecycle projection timing assertion (36.336 ms versus effective 28.911 ms). The same 120-test file passed unchanged in an isolated guarded worker. The failed run wrote no green receipt; an unchanged canonical retry is running. | Original failure retained in temporary qualification log; no assertion was weakened and no timing conclusion is claimed under concurrent host work. |
| 2026-10-14 | Observe: Unchanged canonical retry passed 11,621 tests across 187 files with 12 skips. Independent delivery review found QUAL-DEL-1: actual full compatibility fallback accepted an empty self-consistently hashed applied profile. The same defect was independently reproduced by the implementer through the public comparator before recorded repair-start cycle 1. | qualification_report.compare; QualificationCLITests fixture, --qualify-profile declared full fallback. Required AC-2 remains unmet pending common validation and fresh review. Original full renamed-profile reference was deliberately stopped through its cleanup handler with exit 130 before source repair; it is not qualification evidence. |
| 2026-10-14 | Observe: QUAL-DEL-1 repaired with common source-profile, applied-digest and applied-value validation across selected, full and fallback reports. All 42 report tests passed with zero skips. Removing the common check in the new real CLI regression caused 20 assertion failures and no errors/skips, while all four valid profile/route controls remained successful. | QualificationCLITests.test_all_profile_scopes_refuse_wrong_applied_provenance_through_public_cli; both second/declared profiles and --profile/--qualify-profile full fallback. Fresh independent reverification and full qualification remain pending. |
| 2026-10-14 | Observe: Explicitly reviewed and refreshed only the changed comparator coverage pin. The omitted version test, check_version.py and bytecode_cache.py were byte-identical, and every other contract pin matched; the repair adds no dependency to that independent worker. | Coverage remains 186/187 workers for each profile. Frozen framework inputs 5778d54023eebcbcaa18469cd95ffc9bf13e21bcff34c3a22a348e49049c2cbd; coverage fd8b51d431c3d26cc719bad85a6863364ad51060363893bf15235360da2d9668. |

| 2026-10-14 | Observe: Repaired-tree full default executed 11,622 tests across all 187 files with 12 existing skips; its sole failure was the unchanged lifecycle warm projection timing assertion, 42.784 ms against effective 33.242 ms. No green receipt was written and the sequential profile matrix did not start. QUAL-DEL-1 is terminal after fresh independent reverification; code, architecture and docs approvals are current. | Source remains 5778d54023eebcbcaa18469cd95ffc9bf13e21bcff34c3a22a348e49049c2cbd. Timing investigation stays deferred under operator direction; park qualification pending and continue the next admitted wave instead of repeating unchanged suites. QA/release approval and AC completion remain pending. |

| 2026-10-14 | Observe: Independent coverage follow-up during the next wave found only test_worker_guard.py stale among 16 coverage pins; both profiles correctly fall back to all 187 workers. Live-pin freshness is not required by the fixture-owned coverage tests, and the two focused independence/changed-contract controls passed. | Omitted version-test footprint remains unchanged; guard changes add profile-neutral prelaunch carrier checks. Do not refresh during moving source. After later waves settle and the guard review passes, recheck every pin and explicitly refresh only justified changes before final matrix qualification. |

| 2026-10-14 | Combined default completed 11,658 tests / 187 files / 12 skips in 775.265 seconds and was red in ten files. No receipt/export/profile run followed. Distribution integration and provider diagnostic repairs are being collected before one revised-tree qualification. | Full failure report remains temporary. Existing timing assertion also failed at 40.156 ms against 30.375 ms; no timing threshold changed or timing waiver inferred. Sole reviewed guard pin refresh leaves both compatibility scopes at 186/187. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select explicit file-level compatibility scope with conservative full-profile fallback and one reference qualification. | Run customization-sensitive compatibility checks under alternative profiles without repeating demonstrably profile-independent work. | Keep three whole suites forever: simple but repeats unrelated work. Select only changed files/import matches: cheap but misses ambient vocabulary, fixture and dynamic extension effects. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | A mistaken independence claim hides a distribution regression. Require a reviewed consumer rationale, unknown-file full fallback and representative fault controls; keep the full matrix runnable. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
