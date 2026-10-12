# Distribution-independent Upgrade and Qualification Fixtures

Change ID: `20gfi-bug distribution-independent-upgrade-fixtures`
Change Status: `implemented`
Owner: implementer
Status: implementing
Last verified: 2026-10-12
Wave: `20gx1 distribution-test-fixtures`

## Rationale

Distribution maintainers edit framework declarations, identity/path text and record roots at merge time. Three regression fixtures currently inherit unrelated live configuration, so valid distribution changes can break tests without a runtime defect. This change makes those fixtures explicit while preserving the real historical upgrade and qualification paths, integrity checks, and exact skip evidence.

Current-source discovery: `_JournalDeclarationFixture._declare` copies the live `mcp_tool_extensions.py` but replaces only helpers, templates and hook; it leaves the journal trigger and other declarations ambient. `QualificationCLITests.setUp` applies `shipped_default_profile()`, which includes vocabulary and layout but excludes declarations, before nested declared-profile runs. `StorageUpgradeProcessResumeTests` writes the hash-verified `v122-upgrade` bytes unchanged. That runner contains framework-root, project-index, extraction-prefix, bootstrap and home-pack path literals as well as two fixed wave-root expressions; the encoded historical bundle intentionally cannot receive a distribution's text localization. The existing `fixtures/upgrade_old_runner/*.py.txt` convention already makes historical source reviewable and text-rename compatible. Supported profile constants describe record vocabulary/layout and declarations; they do not describe framework identity/path text.

## Requirements

1. Journal declaration fixtures start with every constant in the existing `SHIPPED_DECLARATION` baseline, then apply only the case's explicit overrides. The baseline includes `EXTENSION_JOURNAL_PRE_MIGRATION_TRIGGER = "legacy_cutover"`; trigger-policy tests may opt into their intended policy explicitly. Keep real current declaration validators and upgrade hooks.
2. Move the v1.22.0 runner used by this process-resume fixture to `fixtures/upgrade_old_runner/upgrade_runner_v1_22_0.py.txt`, using the existing plaintext historical-runner convention. Extract its executable source from the currently verified `v122-upgrade` entry without rewriting historical logic; document origin revision `feaef9ac0e5bffe3bed46498340eaf5e7d191583`, source path and original SHA256 `ae18d63246bc55f398bb6ae10303044f7701b68dbbf7ecff8e8e54230df0fb24` as provenance. Read the plaintext fixture directly so a distribution's same text identity/layout rename applies to it and current fixture/source naturally. Do not enforce that original digest against intentionally renamed plaintext. Preserve historical pause, installed-runner handoff, pack identity, bootstrap preservation and rollback behavior. Do not build a general path-localization adapter. A narrowly bounded record-root adjustment may remain necessary for independently edited record-profile constants; that is separate from framework text renames.
3. Qualification CLI control fixtures explicitly reset the copied declaration module to the existing shipped baseline along with shipped vocabulary/layout, then let the nested runner apply its real second/declared profile asset. Live distribution declarations must neither leak into this control nor be weakened in actual profile validation.
4. Remove the duplicate encoded `v122-upgrade` entry after checking all consumers, update the bundle hash and exact inventory expectations intentionally, and retarget encoded integrity controls to a remaining immutable entry. Preserve strict bundle/entry size, hash, encoding, schema, missing-entry and historical-absence checks for every remaining encoded fixture. Include the new plaintext file in framework text-ownership expectations where the existing fixture policy requires it.
5. Use the real subprocess runners and exact report comparator. Preserve executed skip IDs/reasons, default-profile-only markers, incomplete/mutated-report refusals, source identity and default receipt preservation. Add focused regression controls that fail with the former fixture coupling; do not introduce new skips.

## Scope

**Problem statement:** Test-owned synthetic configurations inherit ambient distribution declarations and an encoded historical runner that cannot receive framework identity/layout text renames.

**In scope:**

- `_JournalDeclarationFixture` and its affected migration/preview/trigger-policy cases in `test_upgrade_wavefoundry.py`.
- Plaintext v1.22.0 historical runner, its process-resume consumer and deterministic generic framework-identity/layout rename regression control.
- Removal of the duplicate encoded v122 entry, intentional bundle hash/inventory updates and preserved remaining encoded integrity controls.
- Copied control declaration setup and regression cases in `test_qualification_report.py`.
- Existing test support may be reused; a helper edit is permitted only if needed to express the same baseline/localization once.

**Out of scope:**

- Production upgrade, declaration, profile runner or qualification validation behavior.
- Changes to remaining encoded historical source bytes or entry hashes, arbitrary weakening of their integrity checks, or replacing historical upgrade logic with current code.
- Generalizing record layout APIs, adding report/evidence folders, changing skip policy, or downstream integration.

## Acceptance Criteria

- [x] AC-1: Journal fixture behavior is independent of a valid ambient declaration with a non-default trigger and unrelated tool/skill state. Real migration and preview cases use their explicit declarations, and explicit trigger-policy cases retain their expected scheduling; regression controls detect ambient leakage.
- [x] AC-2: The plaintext historical runner preserves its original executable source and documented provenance, receives the same deterministic generic framework-identity/layout text rename as the copied current tree, and executes the real pause/fresh-installed-runner handoff. Existing relocated-pack retry, altered-pack rejection, preserved bootstrap/memory/manifest and rollback assertions pass in that renamed copy and the ordinary supported profiles; the old encoded fixture fails the rename control. The control covers framework internal root/path text, project index and installer identity rather than only WAVES_ROOT.
- [x] AC-5: The encoded bundle has no duplicate v122 runner; every remaining source entry retains its previous bytes and per-entry digest. Updated exact inventory and bundle hash checks pass, and existing malformed, tampered, oversized, missing and recorded-absence controls still refuse or accept exactly their intended inputs. The plaintext fixture is classified by the existing framework text-ownership policy and intentional text renames do not fail an original-byte digest gate.
- [x] AC-3: Qualification CLI controls run successfully when copied from a valid custom declaration tree. Their nested default, second and declared runs retain exact skip IDs/reasons and the expected two second-profile-only skips, exact declared/default equality, unchanged default receipt and source identity, and existing incomplete/mutated-report refusals.
- [x] AC-4: The changed files' suites and regression controls pass under default, second and declared profiles with no new skips; no failure elsewhere is attributable to this change. Edited documents validate.

## Tasks

- [x] Implement complete journal fixture baseline plus explicit trigger overrides and an ambient-declaration regression control.
- [x] Extract the verified historical runner into the existing plaintext fixture convention; document provenance and switch its consumer without changing historical executable logic.
- [x] Remove only the redundant encoded v122 entry, update bundle hash/inventory and retarget integrity controls to a remaining encoded entry; update framework text-ownership fixture expectations.
- [x] Add a deterministic generic framework-identity/layout text-rename scratch control that transforms both current sources/fixture setup and plaintext historical input, then runs the real process-resume assertions; retain supported record-profile execution.
- [x] Reset the qualification copied declaration baseline; add a custom-ambient-declaration control while retaining the real nested profile/comparator assertions.
- [x] Run the three focused files in default, second and declared modes; run historical fixture/profile support guards and relevant server-package census when helper/source access changes warrant them.
- [x] Record change-local execution and known-bad evidence, update task/AC status as completed, and return for required delivery reviews and pause.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fixture repairs | implementer | readiness and activation | Serialize shared test-file edits; scratch probes may precede activation. |
| delivery review | code-reviewer, qa-reviewer | fixture repairs | Inspect historical source preservation and remaining encoded integrity; exercise generic renamed process/report paths. |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/historical_fixture_support.py`
- `.wavefoundry/framework/scripts/tests/test_historical_fixture_support.py`
- `.wavefoundry/framework/scripts/tests/fixtures/historical_sources.json`
- `.wavefoundry/framework/scripts/tests/fixtures/upgrade_old_runner/upgrade_runner_v1_22_0.py.txt`
- `.wavefoundry/framework/scripts/tests/fixtures/framework-text-ownership.json`

`record_layout_support.py` is a conditional helper review target; prefer existing support without edits. Production source and the remaining encoded historical source bytes/per-entry hashes are protected. The v122 representation move, bundle-level digest, encoded inventory/integrity-test sample keys and plaintext ownership entry are the named intentional changes. Only implementers write test source after readiness and activation; reviewers are read-only apart from coordinator-recorded findings.

## Affected Architecture Docs

N/A: this repairs test-owned configuration at an existing test/release seam; production ownership, contracts, profile application and upgrade control flow remain unchanged. Existing testing architecture remains accurate.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Journal fixture isolation is one reported failure source. |
| AC-2 | required | Historical resume remains meaningful in renamed distributions. |
| AC-3 | required | Qualification must retain real exact-evidence validation. |
| AC-4 | required | Change-local delivery evidence proves all three repairs. |
| AC-5 | required | Representation change retains strict integrity of remaining encoded history. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-11 | Authored from current on-disk test/support reads; no code edited. | MCP `code_read` of three test owners and baseline/profile support. |
| 2026-10-11 | Coordinator-directed pre-readiness correction covers framework identity/path text through the established plaintext historical fixture convention. | Historical path census includes framework/index/bootstrap/extraction/home paths; profile modules do not expose those constants. |
| 2026-10-11 | Readback: synthetic declarations reset every shipped field before case overrides; original v122 executable source moves verbatim to plaintext so framework identity/layout text renames reach old and current paths together. Production validation stays protected. AC-1/2/3/5 use real gate/resume/comparator and encoded tamper controls; AC-4 uses focused default/second/declared runs. | Current MCP owner reads, memory brief and accepted 20gx1 readiness notes; before: encoded old paths survive rename, after: plaintext fixture receives that same rename. |
| 2026-10-11 | Implemented synthetic full baselines, verbatim plaintext history and generic identity/layout rename control. New positive gate/qualification/renamed old-current resume controls pass. Every remaining encoded entry including metadata/body equals its prior value. | Original plaintext 269025 bytes / SHA256 ae18d63246bc55f398bb6ae10303044f7701b68dbbf7ecff8e8e54230df0fb24; 13 unchanged encoded entries; bundle SHA256 54c36b3b6110917954bb720490be9824758f04ea51fabde2ded7d39839350537. |
| 2026-10-11 | Disposable known-bad controls detect journal baseline removal, qualification reset removal with valid custom lifecycle/tool/artifact declarations, and exclusion of plaintext from the generic rename. Historical mutant reaches actual old-runner pause and fails; qualification mutant reaches the real declared profile refusal. An earlier alias-only ambient control was insufficient and replaced. | Temporary mutant captures outside repository; new positive controls rerun after the stronger ambient fixture. |
| 2026-10-12 | Focused matrix passed: default 926 tests / 6 files; second and declared each 810 tests / owning 3 files. All had two existing Windows junction skips; new controls executed without unintended skips. Full docs validation and diff check passed. No production edits. | Canonical focused runner; temporary implementation summary `/private/tmp/wf-followup-distribution-implementation.json`. Combined whole-suite qualification and required delivery approvals remain coordinator-owned and pending. |

| 2026-10-12 | Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster. | Canonical final qualification: 12,402 tests / 185 files / 12 unchanged existing skips, 798.065 seconds, exit 0; matching receipt `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Exact report worker/skip comparison and all reviewed source fingerprints verified. Full documentation validation passed with zero errors and warnings. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-11 | Select explicit declaration baselines and move only the v122 runner into the established plaintext historical fixture convention; remove its encoded duplicate. | Same text rename naturally reaches current and historical source; preserves old control flow without a large path adapter. Remaining encoded integrity remains strict and provenance records the original runner. | Localize only two wave-root expressions: misses framework identity/layout renames. Build an extensive path adapter: duplicates distribution rewrite policy and increases fragile maintenance. Preserve ambient declarations and derive every synthetic profile dynamically: unnecessary complexity for known-baseline controls. Replace historical runner with current source or relax declared-profile/report validation: loses regression meaning and is rejected. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Historical representation move changes old logic or weakens unrelated integrity. | Extract source from verified bytes, compare executable source before/after, document revision/digest, remove only v122 and retain every remaining entry byte/digest and rejection control. |
| Plaintext origin digest rejects intentional distribution rename. | Treat original digest as provenance, not runtime authority over renamed plaintext; execute a deterministic generic text-rename control. |
| Baseline reset hides actual distribution errors. | Limit reset to synthetic scratch controls; production profile validation remains real and unchanged. Include valid ambient declaration controls and existing invalid declaration/report tests. |
| New baseline fields silently escape fixtures later. | Derive fixture reset from existing `SHIPPED_DECLARATION`, with explicit case overrides; retain assignment-count checks and test-support guards. |

## Session Handoff

Planning complete; no unresolved design decision. Admitted; await readiness and root coordinator activation before source edits. See `docs/agents/session-handoff.md` for session state.
