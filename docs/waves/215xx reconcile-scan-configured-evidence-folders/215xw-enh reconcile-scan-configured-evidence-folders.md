# Reconcile scan skips folders a project declares as evidence

Change ID: `215xw-enh reconcile-scan-configured-evidence-folders`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-20
Wave: 215xx reconcile-scan-configured-evidence-folders

## Rationale

Waveforge's note against `7ab3963d` reports 4,541 retired-surface findings from `reconcile_scan.scan_repo_channels` on their tree, 4,154 of them under `tools/upstream-sync/baselines/`, merge evidence that quotes old names on purpose. Verified at `6a1f228b`: the scan's exclusions are the fixed `_STATIC_EXCLUDED_DIRS` plus the wave and archive roots (`excluded_dirs_for`), and the only per-project control is `docs/reconcile-dispositions.json`, one `historical-record` entry per finding. Thousands of per-line entries for a folder that is historical as a whole is the wrong tool, and every rewrite of the evidence mints new keys.

## Product Intent

- **A project or distribution with an evidence folder:** declares the folder once in `docs/workflow-config.json`, and the scan (upgrade reconciliation and any direct caller) stops reporting it, while the upgrade summary names the excluded folder so the skip stays visible.
- **Everyone else:** nothing changes without the key.
- **Boundary:** a declaration can never hide a carrier the scan is required to inspect (seed 160 "Reconciliation scope and limits"): the root and per-folder instruction files, host surfaces, prompts, agents, plans and the rest of `docs/`. A refused entry excludes nothing.

## Requirements

1. `docs/workflow-config.json` accepts `"reconcile_scan": {"excluded_dirs": ["<repo-relative folder>", ...]}`. One helper in `reconcile_scan.py` reads it with `contained_files.read_contained_bytes` (size cap `DEFAULT_SCAN_FILE_BYTES`) and returns the accepted folders plus one diagnostic per entry. A missing, unreadable, refused or non-JSON file, or a missing key, means no configured exclusions and no diagnostic, as other workflow-config readers behave.
2. Accepted folders are kept apart from `_STATIC_EXCLUDED_DIRS` and matched by prefix only: a path is under a configured folder `d` when `rel == d` or `rel.startswith(d + "/")`. The bare-component clause of `_directory_excluded` never applies to them.
3. Under a configured folder, a file whose basename is `AGENTS.md`, `CLAUDE.md` or `WARP.md` is still scanned. Every other file under it is skipped by both the walk and the mandatory-path branch of `_iter_scannable_files`. Directories under it are still descended so those instruction files are found.
4. After one trailing `/` is dropped, an entry is refused, excluding nothing, with exactly one reason code, checked in this order:
   1. `not_a_string`;
   2. `backslash`: contains `\`;
   3. `absolute`: starts with `/`, or with a drive letter and `:` (such as `C:`);
   4. `bad_component`: any empty, `.` or `..` component;
   5. `dot_directory`: the first component starts with `.`;
   6. `under_docs`: is `docs` or starts with `docs/`;
   7. `protected_carrier`: equals, contains, or lies inside a path in `_MANDATORY_FILES`, `HOST_PERMISSION_FILES` or `_MANDATORY_DIRECTORIES`, or the configured plans or waves root (`record_paths.load_record_roots`);
   8. `not_a_directory`: the path exists in the repository and is not a plain directory (a file, or a link, checked with `lstat`).
   A value of `excluded_dirs` that is not a list, or a `reconcile_scan` value that is not an object, is one `not_a_list` refusal. A repeated accepted entry is accepted once, with one diagnostic.
5. `reconcile_scan.disposition_diagnostics(root)` also returns one entry per configured entry: `{"excluded_directory": <entry as written, JSON-encoded when not a string>, "disposition_state": "excluded-directory"}`, or `"excluded-directory-refused"` with `"reason": <code>`. The upgrade summary's "Disposition-store diagnostics" section prints such an entry as `excluded directory <entry> [<state>]`, followed by `reason=<code>` when refused, instead of the `(missing key)` line.
6. With no `reconcile_scan` key, the scan's findings, exclusion set and diagnostics are unchanged.
7. Seed 160 "Reconciliation scope and limits" and `docs/prompts/upgrade-wavefoundry.prompt.md` (a project-owned baseline, not a render, so both are edited by hand) gain one identical sentence naming the key, the protected carriers, the instruction-file carve-out and where the skip is reported, and noting it as the folder-level alternative to per-finding dispositions. `docs/contributing/build-and-verification.md` gains one sentence beside `indexing.project_include_prefixes`. Existing targets get the prompt sentence only through their own baseline reconciliation; the scanner behaviour ships with the framework.

## Scope

**Problem statement:** a project cannot exclude a folder of evidence from the reconcile scan without one disposition per finding.

**In scope:**

- `reconcile_scan.py`: config helper, validation, matching, the instruction-file carve-out, `disposition_diagnostics`.
- `upgrade_wavefoundry.py`: the summary line for the new diagnostic entries.
- Tests in `tests/test_reconcile_scan.py` and `tests/test_upgrade_wavefoundry.py`.
- Seed 160, `docs/prompts/upgrade-wavefoundry.prompt.md` and `docs/contributing/build-and-verification.md`: one sentence each.
- One CHANGELOG bullet under a new `### Added` heading in `[Unreleased]`.

**Out of scope:**

- Excluding single files or globs; excluding anything under `docs/` or a dot-directory.
- Any other scanner (secrets, docs-lint, indexing).
- Declaring this repository's own folders.
- Reporting excluded folders when the upgrade's reporting budget runs out before `disposition_diagnostics` (the scan is then already reported incomplete).

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. Entries are matched against the scan's `/`-separated repo-relative paths (`as_posix`), so a backslash entry is refused rather than reinterpreted, and a drive-letter entry is refused on every platform. Matching is by exact spelling everywhere, so on a case-insensitive file system (Windows, macOS) an entry spelled with different case excludes nothing and the files stay reported, which fails toward reporting; for the same reason `Docs/x` is not refused by `under_docs` but also excludes nothing under `docs/`. The `not_a_directory` check uses `lstat`, and a Windows junction or symlink is refused as a link. The config is read as UTF-8 JSON.

## Acceptance Criteria

- [x] AC-1: In a fixture repository with the same retired reference in `tools/evidence/old.md`, `tools/evidence/sub/deep.md`, `tools/evidence/AGENTS.md`, `tools/evidence-notes.md` and `docs/runbook.md`, `scan_repo` reports all five with no config; with `excluded_dirs: ["tools/evidence"]` (and again with `"tools/evidence/"`) it reports only `tools/evidence/AGENTS.md`, `tools/evidence-notes.md` and `docs/runbook.md`. Oracle: scratch mutants that (a) drop the configured folders from matching, (b) drop the instruction-file carve-out, each fail the test.
- [x] AC-2: Each refusal reason has a case that only it refuses, the file under it stays reported, and the diagnostic carries that reason: `not_a_string` (`7`), `backslash` (`tools\evidence`), `absolute` (`/tools/x` and `C:/tools`), `bad_component` (`tools/./x`, `tools/../x`, `tools//x`), `dot_directory` (`.vscode/x`), `under_docs` (`docs/specs`), `protected_carrier` (`AGENTS.md`, and a moved plans root outside `docs/`), `not_a_directory` (`tools/evidence/old.md`), `not_a_list` (a string value, and a non-object `reconcile_scan`). A bare-component entry `prompts` excludes nothing under `docs/prompts/`. Oracle: removing any one rule makes its case fail (scratch mutants, one per rule), and a mutant that matches configured folders as bare components fails the `prompts` case.
- [x] AC-3: `disposition_diagnostics` lists accepted and refused entries as Requirement 5 states (a duplicate once), and the upgrade summary text contains `excluded directory tools/evidence [excluded-directory]` and, for a refused entry, its reason, with no `(missing key)` line for them. With no key (and with an unreadable config), `disposition_diagnostics` returns exactly what it returns today and the existing `ExclusionTests` and disposition tests pass. Oracle: renderer and diagnostics tests.
- [x] AC-4: The seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` "Reconciliation scope and limits" paragraphs remain byte-identical after the edit (a test or a scratch diff recorded in the Progress Log), and the contributing doc names the key.
- [x] AC-5: The change's own suites and every test it adds pass, including under `run_tests.py --profile second`; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the config helper, validation, prefix matching and carve-out in `reconcile_scan.py`, and report entries in `disposition_diagnostics`.
- [x] Print the new diagnostic entries in the upgrade summary.
- [x] Add the tests and run the scratch mutants.
- [x] Add the seed 160, upgrade prompt and contributing sentences and the CHANGELOG bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scan       | implementer | —          | reconcile_scan.py and tests |
| summary    | implementer | scan       | upgrade_wavefoundry.py summary line and test |
| docs       | implementer | scan       | seed 160, upgrade prompt, contributing, CHANGELOG |


## Serialization Points

- `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`, `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

N/A. The change adds an optional config input to an existing report-only scanner and one summary line; no module boundary, flow or verification seam changes.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The requested outcome, without hiding instruction files. |
| AC-2 | required | The declaration must not hide the live surface. |
| AC-3 | required | The skip stays visible; nothing changes without the key. |
| AC-4 | required | Operators can find the key; the two prompt copies stay aligned. |
| AC-5 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-20 | Planned on operator request, for the Waveforge reply on `tools/upstream-sync/baselines/`. | `reconcile_scan.excluded_dirs_for`, `disposition_diagnostics` and the upgrade summary read at `6a1f228b`. |
| 2026-10-20 | Readiness round 1: release-reviewer and docs-contract-reviewer PASS; code-reviewer, qa-reviewer and red-team BLOCK on one shared gap: shape rules alone let `AGENTS.md` (a root carrier) or `agents`/`prompts` (matched as a bare component anywhere by `_directory_excluded`) hide the live surface, and excluding a folder hid per-folder instruction files. Rewritten before readying: separate prefix-only matching (Req 2), the instruction-file carve-out (Req 3), ordered single-reason refusals including `protected_carrier` from the scanner's own registries plus the plans and waves roots, and `not_a_directory` (Req 4), the summary line format (Req 5), the contributing doc and identical-paragraph check (Req 7, AC-4), `### Added` for the CHANGELOG, and isolated mutant cases per rule (AC-2). | Readiness lane and seat reports. |
| 2026-10-20 | Readiness confirmation pass: all five PASS. Folded in: the bare-component mutant moves to AC-2's `prompts` case (QA: AC-1's only entry has a `/`, so it could not catch it). Implementation notes: pair `lstat` with `contained_files._is_windows_link` for rule 8 (code-reviewer); add a test asserting every `_mandatory_paths` carrier lies under `docs/` or a dot-directory, so a future carrier outside both fails loudly (red-team, code-reviewer). | Confirmation reports. |
| 2026-10-20 | Implemented. `reconcile_scan.configured_excluded_dirs(root)` reads `docs/workflow-config.json` with `read_contained_bytes` (cap `DEFAULT_SCAN_FILE_BYTES`) and returns accepted folders plus diagnostics; `_excluded_dir_refusal` applies the eight ordered rules (rule 8 pairs `lstat` with `contained_files._is_windows_link`); `_configured_excluded` is prefix-only with the `AGENTS.md`/`CLAUDE.md`/`WARP.md` carve-out and is added to `eligible()` in `_iter_scannable_files`, so both the mandatory-path branch and the walk honour it while directories are still descended; `disposition_diagnostics` appends the entries. `upgrade_wavefoundry._reconciliation_recommendation_lines` prints `excluded directory <entry> [<state>]` plus `reason=`. Tests: `ConfiguredEvidenceFolderTests` (6) and `test_store_diagnostics_render_configured_excluded_directories`, including the registered-carrier guard test (every `_mandatory_paths` carrier and mandatory directory is listed, under `docs/`, or under a dot-directory). Seed 160 and the upgrade prompt copy gained the same sentence (paragraphs diffed identical); contributing doc and CHANGELOG `### Added` bullet added. Scratch mutants, each detected: (a) configured matching dropped, (b) carve-out dropped, (c) bare-component matching, each of the eight refusal rules, record roots dropped from `protected_carrier`, both `not_a_list` branches, duplicates kept, diagnostics not reported, and the summary renderer branch disabled. Gapfill: shell reads, a Python edit script for the two identical prompt paragraphs, and a mutation driver; MCP used for review claims. | Scratch `/private/tmp/claude-502/-Users-coryhacking-Developer-wavefoundry/64d2b992-b50d-423e-985d-22b0c59dd1ac/scratchpad/215xx/mutants.log`. |
| 2026-10-20 | Delivery review: docs-contract, release, QA and red-team PASS; code-reviewer BLOCK, recorded as CODE-DEL-1: `record_paths.load_record_roots` raises `RecordLayoutInvalid` (not an `OSError`) from inside `_excluded_dir_refusal`, so with a configured entry and an invalid layout `disposition_diagnostics` raised and the upgrade report child (which calls it unguarded) would die. Repair: `configured_excluded_dirs` loads the roots once and returns `((), [])` on `RecordLayoutInvalid`, and passes the protected set to `_excluded_dir_refusal`; `json.loads` also treats `RecursionError` as unreadable. Also: the instruction-file carve-out compares case-insensitively (red-team: on Windows and macOS a host asking for `CLAUDE.md` can open `Claude.md`). New tests: invalid layout, symlinked folder refused, case-insensitive carve-out. Mutants: removing the layout guard and making the carve-out case-sensitive each fail; `lstat` to `stat` alone survives because `contained_files._is_windows_link` (itself `lstat`-based, POSIX symlinks included) still refuses the link, and removing both guards fails the symlink test, so rule 8 is pinned as a pair. Dispositioned, no change: red-team's medium note that host folders nested inside an excluded folder (`pkg/.claude/agents/`, `pkg/.github/...`) are skipped; hosts load those only at the repository root, nested copies in an evidence folder are exactly the evidence being excluded, and the files hosts read at any depth (`AGENTS.md`, `CLAUDE.md`, `WARP.md`) stay scanned. Red-team's low note that a missing or unparseable config produces no diagnostic: it then excludes nothing, so there is no folder to list. `--profile second` over the six touched files: 0 of 6 failed. | `ConfiguredEvidenceFolderTests` 9 OK; scratch mutant runs. |
| 2026-10-20 | Confirmations on the repaired tree: code-reviewer reverified CODE-DEL-1 (resolved); QA PASS (10 tests, 10 mutants killed, AC-4 paragraphs still identical); red-team PASS, accepting the nested-folder disposition. Decision recorded: Requirement 3's carve-out names `AGENTS.md`, `CLAUDE.md` and `WARP.md`; the code compares them case-insensitively, which can only scan more files, never fewer (code-reviewer note). Residual lows recorded, no change: a nested `.claude/skills` inside an excluded folder that a monorepo-aware host might load, and `CLAUDE.local.md`, are not carved out (neither is a registered carrier at the root either); an unparseable config is ignored without a diagnostic, which excludes nothing. | Confirmation reports. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-20 | A workflow-config list of folders, prefix-matched, refused where it overlaps a carrier the scan must inspect, with instruction files still scanned inside. | Smallest addition that keeps the seed 160 promise; a project-owned file targets edit, unlike framework constants. | A framework constant (distributions only, overwritten for targets); per-finding dispositions (thousands of entries); glob patterns (more surface, easier to over-exclude); a shape-only refusal list (red-team and code-reviewer showed it hides carriers). |
| 2026-10-20 | Report entries through `disposition_diagnostics`. | The upgrade summary already prints that section; no new report key. | A new `ScanResult` field and report key (more plumbing). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A project excludes a folder that holds live instructions. | Overlap with any registered carrier, the plans and waves roots or `docs/` is refused; instruction files inside an excluded folder are still scanned; the summary lists every excluded folder. |
| A malformed config silently changes the scan. | A refused entry excludes nothing and is listed with its reason. |
| The config changes between the scan and the diagnostics read. | Both read the same helper; a change mid-upgrade is an operator edit during an upgrade and shows on the next run. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
