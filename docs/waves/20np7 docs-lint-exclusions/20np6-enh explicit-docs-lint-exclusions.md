# Explicit project documentation lint exclusions

Change ID: `20np6-enh explicit-docs-lint-exclusions`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-14
Wave: `20np7 docs-lint-exclusions`

## Rationale

Existing product documentation must stay at its current paths when Wavefoundry is installed. The first install audit currently applies generic metadata and link checks before the existing-document inventory, so unrelated documentation debt blocks adoption. The operator requested an explicit file/folder list in TOML, following the scan-rules naming convention, with exclusion only for now. Use docs/lint-rules.toml; the spelling line-rules is treated as a typo for lint-rules.

## Requirements

1. Read optional docs/lint-rules.toml with only an optional [exclude] table containing paths, an array of literal repository-relative POSIX paths. Exact paths match files; a trailing slash matches descendants by path components. Missing or empty rules preserve current behavior. No globs, regexes, implicit Git-ignore reuse, history classification or JSON duplicate source.
2. Apply matches only to generic Markdown metadata and outgoing relative-link checks in both full and incremental lint. Excluded documents remain on disk, searchable and valid link targets. Corpus, required-artifact presence, lifecycle/review, secrets and safe-read refusal checks remain active; this is not an all-validator bypass.
3. Protected contract surfaces retain generic checks despite broad exclusions. Derive protected files from the existing required-doc and renderer policy/protocol carrier registries, and protected trees from resolved wave/plan/archive roots plus the canonical agent/prompt roots. docs/README.md is a deliberate presence-only exception: it may exclude generic checks while its existence remains required. Invalid record layouts still fail closed.
4. Parse the rules once per lint invocation with a bounded contained no-link read, stdlib TOML and deterministic validation. Invalid TOML/schema/types/paths, unsupported keys, oversized or refused rules yield actionable blocking lint errors and grant no exclusions. Limit file size to 64 KiB, entries to 512 and each path to 4096 characters. Reject absolute/drive/backslash/dot/parent/glob/control-containing paths; do not resolve names through links to grant matches.
5. A changed rules file invalidates advisory lint reuse and triggers full lint through the shared incremental trigger inventory. Fresh invocations observe changed rules; no persistent rules cache or new upgrade phase.
6. Document exclusion setup before the first install audit, including resumed installations, without renumbering install-log rows. Preserve existing docs/README.md and other project documents; excluded paths are no instruction to move, overwrite or adopt them. Install and upgrade audits consume the common lint behavior. No new config is generated automatically, and no extra permanent evidence artifacts.

## Scope

In scope: one narrow TOML reader/matcher, full/incremental lint integration and trigger identity, focused tests, install/use guidance and architecture contract. Root changelog receives a concise entry. Root coordinator owns integration; implementation follows readiness.

Out of scope: history folders, migration/quarantine/adoption machinery, general document ownership database, per-rule severities, glob/regex syntax, index/search exclusions, format conversion of workflow-config.json, timing investigation or threshold changes, closure, commits and releases.

## Acceptance Criteria

- [x] AC-1: Exact file and recursive folder exclusions suppress only generic metadata/outgoing-link findings; near-miss names remain checked, and incoming links still validate the actual target.
- [x] AC-2: Broad exclusions cannot disable protected record/contract checks, required artifact presence or other corpus/secrets/refusal validation; docs/README.md can retain its original content with generic checks excluded.
- [x] AC-3: Missing/empty rules preserve behavior; malformed, unsupported, unsafe, linked, special and oversized rules fail without hanging or granting partial exemptions, with bounded diagnostics.
- [x] AC-4: Full and incremental public lint paths agree, and rules edits invalidate reuse/force full evaluation. The install audit accepts excluded preexisting guide debt while still rejecting required-artifact defects.
- [x] AC-5: Shipped install instructions establish the list before the first audit and preserve existing documents; current docs and tests describe the same literal-path and protected-surface contract without new upgrade work.

## Tasks

- [x] Implement the bounded TOML reader and protected literal-path matcher.
- [x] Integrate generic full/incremental checks and shared lint trigger identity.
- [x] Add focused public-path, malformed-input and negative-control regression coverage.
- [x] Update install seeds and canonical documentation; reconcile focused reviews and qualification limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Discovery and plan | coordinator with read-only implementer discovery | Request | MCP-first source validation |
| Readiness | independent council and specialist reviewers | Admitted plan | Isolated primer before fixed seats and rotating docs remit |
| Implementation | implementer | Current readiness | Single source writer; coordinator integrates |
| Delivery | fresh independent reviewers | Frozen implementation and tests | Required remits; qualification limits explicit |

## Serialization Points

Only the implementation owner edits source after readiness; root coordinates documents and typed evidence. New module, CLI, shared trigger and test changes serialize with existing paused work. No changes to other waves or deferred timing. Seed and framework gates must be opened only for admitted edits and closed at handoff.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/lint_rules.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/advisory_lint_identity.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_advisory_lint_reuse.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_install_log_lib.py`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md for generic lint filtering and retained guards; docs/contributing/build-and-verification.md documents the optional TOML file and literal matching. Install seeds own initial/resumed workflow guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Solves the requested in-place exclusion behavior. |
| AC-2 | required | Preserves lifecycle and security gate authority. |
| AC-3 | required | Rules are untrusted repository input consumed by every lint caller. |
| AC-4 | required | Avoids inconsistent gate outcomes and stale advisory acceptance. |
| AC-5 | required | Makes the setting usable before the observed install block. |

## Progress Log

- 2026-10-14: Fresh independent repair review passed the exact three regressions, relocated-root case and two census polarity controls: six tests in 8.083s, zero failures/errors/skips. All 14 final source/test/doc blob hashes matched fingerprint e03da1f4783085fa711e6d073b7fc1579c3d707a581070a2713faff0defa3a4f (SHA-256 of sorted JSON mapping of path to git hash-object). QA-20NP7-COMPAT-01 is terminal after typed reverification. Code/architecture/performance and security/docs-contract delivery approvals are recorded with honest grouped contexts; final QA is withheld because canonical qualification remains red. No source timing change, waiver, repeated unchanged suite, close, commit or package was performed. Finish final docs validation and pause; resume qualification when the deferred timing issue is addressed or explicitly waived for a named purpose.
- 2026-10-14: Compatibility repair now passes 75 tests in 12.545s, zero skips: full test_install_log_lib and test_profile_literal_census modules, all seven DocsLintExclusionTests, and PostWriteLintFreshGitTests. The latter uses valid TOML for the new trigger while preserving real Git/CLI scope and timeout assertions. Updated step-2.3a assertions retain preservation and operator-confirmation checks; relocated-root coverage uses vocabulary_profile.RECORD_FILENAME. A transient indentation error in the repair was caught before execution and corrected before this green run. No production code or seed behavior changed in repair. Gates closed; fresh QA reverification requested. The canonical run remains red; focused repair is not a replacement green receipt or timing waiver.
- 2026-10-14: Canonical run completed 11,671 tests / 187 files / 12 skips in 1017.741s, red in four files. QA-20NP7-COMPAT-01 records the install-wording and new literal-filename fixture failures; repair_start is recorded before edits. The same compatibility sweep also found test_server_tools.py::PostWriteLintFreshGitTests writes JSON into every trigger, including the new TOML file. Its fixture-format repair is necessary verification follow-through for AC-4, with the same QA/code remits and no new behavior or authority scope. Repair only these three tests; preserve assertions, no census exception or skip. The fourth failure is the deferred lifecycle projection timing check, 38.197ms against 37.333ms effective budget; do not investigate or relax it. No green receipt was written. Log: /private/tmp/20np7-default.log.
- 2026-10-14: Implemented and integrated. All 10 new tests passed in 9.049s with zero skips: DocsLintExclusionTests (7), AdvisoryLintReuseTests.test_lint_exclusion_creation_edit_and_deletion_invalidate_identity, WaveInstallAuditTests.test_real_install_audit_excludes_existing_guides_but_keeps_required_artifacts, and FreshInstallContractParityTests.test_existing_docs_rules_precede_first_audit_without_new_rows. Ten adjacent cases passed in 14.155s; the final current-date fixture correction passed its affected test in 0.960s. Real full/changed CLI and install-audit paths were exercised; guide/README bytes remained unchanged and damaged required artifacts still blocked. Broad exclusions retained protected/relocated roots, secrets and safe-read diagnostics. Full wf_validate_docs passed with zero errors/warnings.
- 2026-10-14: Guard falsification before delivery: in-memory protected-path bypass caused six failures in DocsLintExclusionTests.test_protected_paths_and_safe_read_refusals_survive_broad_exclusion; removing the excluded-document safe read caused one failure in that test. Both mutants had zero errors/skips. Initial probe import order targeted a stale class; corrected order made the mutations observable. Probe and source hashes remain in temporary storage; source/test names and results are retained here. Source/tests are frozen and edit gates closed for one canonical qualification run; timing remains deferred.
- 2026-10-14: Readiness passed with six lane approvals and council on receipt review-policy-b13250b912547db1c433; Prepare readied and Implement opened the wave. Both edit gates opened for the admitted scope. Implementation readback surfaced before edits: optional literal TOML filters generic loops only; before/after guide metadata/link debt is excluded while operating contracts still validate. Root owns seeds/docs/changelog; one implementer owns source/tests. Retain bounded safe reads for excluded regular documents so unreadability cannot disappear with the generic validators. No speedup is claimed.
- 2026-10-14: Seed guidance now introduces the optional list before the first or resumed audit, preserves existing README content and reuses the inventory without new rows or evidence files. Gapfill: shell ranged reads and apply_patch used for mechanical prose editing after MCP source reads; indexed setup remains unchanged.
- 2026-10-14: Readback: excluded user guides remain unchanged and no longer produce metadata/outgoing-link errors; lifecycle records and required artifacts still validate. Narrow TOML exclusion only. Existing three waves stay paused and timing stays deferred. Discovery used live MCP reads after indexed retrieval reported stale/not-ready context; no setup/index/model operation was initiated for recovery.
- 2026-10-14: Thought: independent discovery checks protected surfaces and trigger reuse before the readiness packet. Root retains single-writer coordination. Current model/default effort is used for bounded code/contract work; runtime model identity is not independently reported. Required reviewers will be fresh contexts.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Literal [exclude] paths in docs/lint-rules.toml, filtered only at generic lint loops | Matches operator preference, supports comments and preserves existing locations with a small contract | JSON exclusion list duplicates the requested format; automatic ownership/history classification adds persistence and migration complexity; regex/glob lists add ambiguity and excess scope. |
| 2026-10-14 | Protected contract checks override broad matches; README keeps presence validation | Prevents blanket exclusions weakening lifecycle authority while supporting a project-authored landing page | Excluding every validator hides real gate failures; forbidding README exclusions reproduces the reported install collision. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Exclusions hide lifecycle failures | Protect existing registry surfaces and keep corpus checks unchanged. |
| Malformed rules silently appear clean | Bounded no-link parsing, strict schema, no partial exemptions. |
| Install agent overwrites project content | Pre-audit guidance and explicit collision preservation; no automatic rewrite. |
| Deferred timing gate blocks final qualification | Report separately; no threshold change, waiver or repeated unchanged run. |

## Session Handoff

See docs/agents/session-handoff.md for current session state.
