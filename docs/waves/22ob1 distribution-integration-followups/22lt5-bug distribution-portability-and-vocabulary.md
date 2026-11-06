# Make distribution verification portable and vocabulary-aware

Change ID: `22lt5-bug distribution-portability-and-vocabulary`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22ob1 distribution-integration-followups

## Rationale

The distribution's 1.39 review reports source-project assumptions in tests and fixed vocabulary in user-facing responses. Current source confirms the carrier assertions, the ledger census requiring more than 100 checkout ledgers, root metadata checks, report-path assumptions and literal wording. A complete downstream suite replay has not run. Two offered test-isolation fixes, home-directory discovery and SQLite WAL snapshots, remain reported rather than locally reproduced.

## Product Intent

A distribution should verify shared framework behavior without copying Wavefoundry's project prose, record corpus, package metadata or vocabulary. Portable tests must still detect broken framework behavior. AC-1 through AC-3 test that outcome. This is delivery maintenance supporting the adopted vision; it does not introduce a new product direction.

## Requirements

1. Separate source-repository carrier assertions from portable seed/renderer contracts in EfficacyCheckCarrierTests, IntentFitCarrierTests, IntentFitApprovalCarrierTests and the writing-guide invocation test. Gate only source-specific checks with the established source-repository/fixture helpers. Keep meaningful canonical and temporary-target checks running downstream.
2. Route the shipped ledger corpus through upstream_fixture and configured record roots via load_record_roots. An absent upstream corpus skips its corpus check rather than failing a count. Keep portable synthetic validation and corruption detection. Do not use an arbitrary consuming checkout's in-progress ledgers as a unit-test prerequisite; retain an explicit route to audit those records.
3. Treat Wavefoundry's metadata-only wheel assertions as source-specific. Separate the shipped graph-report .aiignore assertions from generic report self-contamination prevention, which remains tested in a controlled target. Change rendered ignore policy only if a generic installed-report contract actually requires it.
4. Derive user-facing item/container wording in lifecycle_gate_support and review_evidence from the vocabulary profile, including golden expectations. Use profile-resolved prompt paths in initiative-planning tests. Preserve wire keys, ledger kinds, historical aliases and intentional fixed physical paths.
5. Audit the reported SubagentStart briefing literals and duplicated arc reserved-token sets against their intended profile and compatibility contracts. Replace bypasses of supported customization; retain and explain necessary fixed tokens or framework paths. Do not infer that every product name or arc token is renamable.
6. Isolate every archive-discovery search root in DryRunTests, including home roots. Review the offered test-only SQLite snapshot approach against explicit WAL/SHM states: absent, SHM-only, empty WAL and populated WAL with/without SHM. Snapshot assertions must see committed WAL rows without creating side files. Do not apply immutable reads indiscriminately to live runtime databases.

## Scope

In scope: affected test modules and their fixture support, lifecycle_gate_support.py, review_evidence.py, vocabulary_profile.py and the briefing renderer where supported customization is verified. Out of scope: skipping entire mixed test classes, changing persisted schemas, renaming installed trees or repairing arbitrary downstream records.

## Acceptance Criteria

- [x] AC-1: A controlled non-source target with customized project docs, no upstream corpus and a non-Wavefoundry root manifest can run the portable checks; their known-bad framework controls still fail.
- [x] AC-2: An alternate vocabulary and renamed Plan arc prompt exercise the affected responses, briefing and prompt lookup without stale display nouns or broken fixed contracts; reserved-token decisions have a compatibility rationale.
- [x] AC-3: Archive discovery is independent of real home folders, and SQLite snapshot controls cover the stated file states, preserve rows and leave directory entries unchanged.
- [x] AC-4: Source-project carrier/corpus checks remain available and meaningful; documentation distinguishes source-only fixtures from portable contracts.

## Tasks

- [x] Reproduce each reported assumption in bounded fixtures before changing it.
- [x] Separate test contracts, apply profile routing and repair test isolation.
- [x] Run affected suites in source and temporary distribution shapes; document boundaries.

## Agent Execution Graph

Keep fixture isolation and vocabulary changes in one coordinated stream to avoid conflicting golden updates. Reviewers inspect both source and distribution outcomes.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_writing_guide_delivery.py`
- `.wavefoundry/framework/scripts/tests/test_intent_fit_approvals.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`
- `.wavefoundry/framework/scripts/tests/test_initiative_planning_delivery.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `docs/architecture/testing-architecture.md`

Existing test-support helpers and the lifecycle golden fixture may change where required by these tests. CHANGELOG.md records the bounded result.

## Affected Architecture Docs

Update docs/architecture/testing-architecture.md for portable versus source-corpus coverage; update profile/briefing documentation only where its contract changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Downstream verification remains useful. |
| AC-2 | required | Profile routing reaches visible behavior. |
| AC-3 | required | Tests do not depend on developer state. |
| AC-4 | required | Portability must not erase verification. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Separate contracts and use existing fixture/profile mechanisms. | Controlled distribution fixtures can test the reported failures without requiring copied project text. | Broad class skips lose portable coverage; requiring downstream prose to match defeats customization. |

## Risks

A broad skip could hide a real defect. Require a portable negative control beside each separated source assertion. Native platform results must be reported as tested, simulated or unverified.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented explicit source-opt-in carrier/corpus separation with portable negative controls, supported display/profile routing and isolated home/WAL fixtures. Development suites and alternate-profile293-test selected run pass (one reported skip). Closed source corpus is separate from active lifecycle audit; fixed wire/history tokens retained. | delivery-evidence.json; named production tests and guard mutants; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: separate source-project corpus/carrier assertions from portable behavior, use supported vocabulary routing and isolate home/WAL test fixtures. AC-1–4; portable-negative controls must keep failing on bad framework behavior. Implementer owns named portability tests and lifecycle/vocabulary display producers, except shared platform briefing is coordinated with setup implementer. | Current receipt review-policy-9f3ca64efa19fe8cfee4; Implement wave activation succeeded. |
| 2026-11-05 | Staged from the distribution report and targeted source checks; offered WAL/home fixes await execution. | Named test classes and production vocabulary sites; no downstream suite claim. |
| 2026-11-05 | Final delivery passed: canonical suite 12,369 tests / 217 files / 12 reported skips; full docs validation and independent required lanes plus Council approve. Four supporting test-fixture repairs were independently verified in cycle 1; no product repair or scope change was needed. | delivery-evidence.json and typed events.jsonl; current receipt 92ad0645. Wave remains open for operator signoff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
