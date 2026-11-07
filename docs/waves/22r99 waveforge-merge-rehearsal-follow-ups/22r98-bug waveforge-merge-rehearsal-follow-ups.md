# Waveforge merge rehearsal follow-ups

Change ID: `22r98-bug waveforge-merge-rehearsal-follow-ups`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22r99 waveforge-merge-rehearsal-follow-ups

## Rationale

Waveforge rehearsed their full merge of `2b6b985a` under their rebrand and vocabulary profile, in which the container tier is called "Set". They reported five items. Their four 2026-11-06 items are already delivered in `1f7e5907` (wave 22r97). Each new item was confirmed against the current tree:

1. **`review_policy` cannot be imported from a zip.** `scripts/review_policy.py` computes `_NORMALIZER_SIGNATURE` at import with `Path(gardener_metadata.__file__).read_bytes()`. Under zipimport that path lies inside the archive, so the import raises `NotADirectoryError`. Anything importing `review_policy` from a zipped framework fails, including Waveforge's zipped upgrade launcher through `lifecycle_gate_support`.
2. **PowerShell recovery commands double only the ASCII quote.** `scripts/setup_commands.format_command` quotes each argument for PowerShell by doubling `'`. PowerShell also ends a single-quoted string at U+2018, U+2019, U+201A and U+201B, so a repository path containing `’` (for example in a user folder name) yields a recovery command that splits at that character.
3. **The work area's name carries the container noun.** "Disposable wave work" and "the lifecycle-reported disposable wave work area" name the wrong tier in a renamed distribution. The phrase appears in the five lifecycle templates, seeds 050, 160, 180 and 209, the rendered `.gitignore` comment (`render_platform_surfaces._GITIGNORE_BLOCK`), and the phrase pinned in `tests/test_compact_review_artifacts.py`. Waveforge plans to use "Disposable work" and "disposable work area"; adopting the same words lets them carry no divergence. An uncommitted prose sweep from 2026-11-07 already renamed the headings to "Disposable work area"; this change settles the final wording.
4. **The Betterleaks baseline cannot satisfy both of its tests in a renamed tree.** `tests/test_secrets_prefix_collapse.py` pins `tests/fixtures/betterleaks/baseline.toml` by the SHA-256 of its whole bytes. `tests/test_betterleaks_engine.py` compares that file's `allowlist` with the shipped `scan-rules.toml`, whose runtime-path entries (`.wavefoundry/` paths) a renamed distribution rewrites. The fixture cannot keep its bytes and match the renamed rules at once.
5. **Container fixture setup assumes Wavefoundry's served signatures.** `tests/test_wave_work_lifecycle.py` and `test_server_tools_lifecycle.ReceiptSnapshotPublicIntegrationTests` call the served `wf_create_wave` with only a slug and `wf_close_wave` with only a wave id. A distribution whose served tools require more arguments (Waveforge's need a parent `feature` and `kind` on creation, and `scope="set"` to close a whole container) fails about 21 tests on fixture setup rather than on the behavior they check.

## Product Intent

Downstream distributions can merge Wavefoundry's tree without carrying local divergences for these five points: the lifecycle and upgrade import path loads from a zipped framework, and the work-area wording, the baseline pin and the container fixture setup survive a renamed vocabulary. Windows operators get setup and upgrade recovery commands that paste correctly whatever their path contains. Wavefoundry's own behavior and tool signatures are unchanged. Loading the indexer, server or dashboard from a zip is not part of this intent.

## Requirements

1. `review_policy._NORMALIZER_SIGNATURE` hashes the bytes returned by `gardener_metadata.__loader__.get_data(gardener_metadata.__file__)`. The value is identical for a filesystem import, and `review_policy` and `lifecycle_gate_support` import from a zip archive carrying the framework's `.py` sources (a sources-only zip; a bytecode-only zip would hash bytecode and is not supported).
2. One shared PowerShell quoting helper in `setup_commands` doubles each of the five single quotes `'`, U+2018, U+2019, U+201A and U+201B inside an argument, using `str.translate` (no `re`, so the module stays stdlib-only and import-cheap). Both PowerShell quoters use it: `setup_commands.format_command` and `sqlite_storage_migration._quote_argument` (which builds the upgrade restart and resume commands and the repository-root text in the accounting-gap guidance). POSIX output is unchanged.
3. The work area is named without the container noun everywhere it ships, with these exact forms. Every section heading reads `## Disposable work` or `### Disposable work` (the lifecycle templates, seed 180, the `docs/prompts/` copies, `docs/architecture/threat-model.md`, `docs/contributing/build-and-verification.md` and `docs/specs/mcp-tool-surface.md`). The bold lead-in reads `**Disposable work.**` (seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md`). Every cross-reference reads `seed 180’s **Disposable work**` (seeds 160 and 209, the templates and the `docs/prompts/` copies). The `docs/architecture/domain-map.md` term reads `**Disposable Work**`. The running phrase reads "disposable work area" (implement-wave, `wave_work.py`'s module docstring, `run_tests.py`'s comment, `docs/references/native-windows-support.md`). The `docs/prompts/` copies are authored locally and carry the same wording as their seed or template. The managed `.gitignore` comment changes together in `render_platform_surfaces._GITIGNORE_BLOCK` and seed 050 (a test requires the two to match) to `# Wavefoundry disposable work (local review aids and scratch — never commit)`, and this repository's tracked `.gitignore` is re-rendered through the supported renderer, not hand-edited. The previous comment text is kept in a separate legacy set used only by the loose-line drop check, never in `_GITIGNORE_BLOCK`, whose lines also feed the tracked-runtime patterns. Re-rendering an existing `.gitignore` then leaves exactly one copy of the new comment and none of the old. The `.wavefoundry/work/<wave-id>/` path, identifiers and rule content are unchanged; in particular the `generic-api-key` stopword `wave` is not vocabulary.
4. The baseline pin in `test_secrets_prefix_collapse._legacy_ruleset` covers the fixture's parsed `rules` table, every field of every rule, as the SHA-256 of a canonical JSON serialization. That table carries no brand or runtime-path token, and the frozen prefix-collapse oracle consumes only it. The allowlist and policy stay guarded by the existing comparison in `test_betterleaks_engine`.
5. A new test-only module, `tests/container_fixture_profile.py`, marked fork-editable like `vocabulary_profile.py`, defines `container_fixture_args(tool_name, root) -> dict`, which returns `{}` by default for both `wf_create_wave` and `wf_close_wave`. Upstream never changes it beyond its defaults. `tests/server_tools_support.py` gains `create_container(call, root, slug, **kwargs)` and `close_container(call, root, wave_id, **kwargs)`, which merge the profile's arguments into the served call and raise when a profile key collides with an argument the test passes. All 18 container fixture calls Waveforge reported use the helpers: the 4 `wf_create_wave` and 13 `wf_close_wave` calls in `test_wave_work_lifecycle.py` and the 1 `wf_create_wave` call in `test_server_tools_lifecycle.ReceiptSnapshotPublicIntegrationTests`. A distribution supplies its arguments, including any it must create in the fixture repository first, by editing only that module. The direct served-tool calls in `test_server_tools_lifecycle.RetainedUpgradePreviewTests` stay as they are: Waveforge did not report them, and converting them is a follow-up if a distribution needs it. `docs/architecture/testing-architecture.md` (Profile-Aware Fixtures) names the new module.

## Scope

**In scope:** the five items above, their tests, the changelog, and the 2026-11-07 wording sweep. The sweep's files are the five lifecycle templates, seeds 160, 180 and 209, `docs/prompts/{close-wave,create-wave,implement-change,implement-wave,install-wavefoundry,pause-wave,prepare-wave,review-wave,upgrade-wavefoundry}.prompt.md`, `docs/architecture/{domain-map,threat-model}.md`, `docs/contributing/build-and-verification.md`, `docs/references/native-windows-support.md` and `docs/specs/mcp-tool-surface.md`; also seed 050, `.wavefoundry/framework/scripts/wave_work.py`, `.wavefoundry/framework/scripts/run_tests.py`, this repository's `.gitignore` (re-rendered), `docs/architecture/testing-architecture.md` and `CHANGELOG.md`. `docs/prompts/prompt-surface-manifest.json` records no per-prompt hash, so it needs no refresh. Pre-existing operator edits to `README.md`, `docs/index.md`, `docs/references/wavefoundry-overview.md`, `.wavefoundry/framework/VERSION` and `docs/prompts/prompt-surface-manifest.json` are not part of this change.

**Out of scope:** renaming identifiers, tool names, paths or record markers; changing served tool signatures. Other modules that read source bytes at import remain zip-incompatible and are known blockers outside this intent: `index_compatibility._SOURCE_BYTES` (reached by the indexer, graph, memory supply and model bundle paths), the server's and `wf_server/server_impl.py`'s module-level reads, and the evaluation scripts `ann_reference_eval.py` and `retrieval_eval.py`.

## Acceptance Criteria

- [x] AC-1: In a subprocess run with `-B` and `PYTHONPYCACHEPREFIX` unset, importing `review_policy` and `lifecycle_gate_support` from a zip of the framework scripts' `.py` sources succeeds, and `normalizer_signature()` equals the value from a filesystem import. On the current code the zip import raises `NotADirectoryError`.
- [x] AC-2: For an argument containing each of the five quote characters, both `setup_commands.format_command` (PowerShell dialect) and `sqlite_storage_migration._quote_argument` (PowerShell branch) double every one, and an exact expected string is asserted for each; POSIX output is unchanged. On the current code the four typographic quotes are not doubled.
- [x] AC-3: A census over the files named in Requirement 3 and Scope finds: every work-area heading line is exactly `## Disposable work` or `### Disposable work`; every lead-in, cross-reference and the domain-map term match their exact Requirement 3 forms; no file contains "Disposable work area" or "Disposable Work Area" (case-sensitive; the lowercase running phrase is allowed) or "disposable wave work" (any case). These assertions fail on the current tree, which carries the 2026-11-07 "Disposable work area" sweep. Rendering a `.gitignore` that holds the previous managed block, or a loose copy of the previous comment outside it, yields exactly one new comment line and no old one; this repository's `.gitignore` carries the new comment. On the current code the old comment is rendered.
- [x] AC-4: The baseline pin passes when the fixture's runtime-path allowlist entries and brand comments are rewritten, and fails when any rule's regex changes and when any rule's filter or other field changes. On the current code a rewrite of those entries fails the pin.
- [x] AC-5: With `call` replaced by a recording fake and `container_fixture_args` patched to return an extra argument for each tool, every converted call passes it to the served tool, and a key collision raises. With the default profile, the converted tests pass unchanged. A guard test parses `test_wave_work_lifecycle.py` (whole file) and the `ReceiptSnapshotPublicIntegrationTests` class of `test_server_tools_lifecycle.py`, excluding the helpers in `server_tools_support.py`. It counts as a direct call any call whose first positional argument or `name=` keyword is the string `"wf_create_wave"` or `"wf_close_wave"`, and any call through `_tool_manager._tools["wf_create_wave"]` or `["wf_close_wave"]`, and finds none. On the pre-conversion source the same guard reports 17 sites and 1 site.
- [x] AC-6: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Read the normalizer bytes through the module loader.
- [x] Add the shared five-quote PowerShell helper and use it in both quoters.
- [x] Settle the work-area wording in its exact forms, including the `.gitignore` comment, its legacy line, seed 050, `wave_work.py` and `run_tests.py`.
- [x] Re-render this repository's `.gitignore` through the supported renderer.
- [x] Pin the baseline's full rules table rather than its bytes.
- [x] Add the container fixture profile and helpers, and convert all 18 fixture calls.
- [x] Add regression tests with known-bad controls.
- [x] Update the changelog: revise the uncommitted 22r97 bullet that says the `.gitignore` comment is unchanged (it now reads "disposable work", and existing blocks and loose old comments are rewritten once), and add Unreleased bullets for the zip import, PowerShell quoting, the baseline pin and the fixture profile, stating that served tool signatures are unchanged.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| followups  | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/setup_commands.py`, `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/wave_work.py`, `.wavefoundry/framework/scripts/run_tests.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/install/lifecycle-prompts/`, `.wavefoundry/framework/seeds/`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/domain-map.md`, `docs/architecture/threat-model.md`: section and term names only. `docs/architecture/testing-architecture.md`: the new fork-editable test module. No boundary or flow change.

## Platform Behavior

The quoting fix applies to the PowerShell dialect, which native Windows uses by default; POSIX output on macOS, Linux and WSL2 is unchanged. The zip import, wording and test changes are platform-neutral. Verification runs on macOS only; the PowerShell behavior is asserted on the formatted string, not executed in PowerShell.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Import failure for zipped distributions. |
| AC-2 | required  | Broken recovery command on Windows. |
| AC-3 | important | Removes a downstream divergence. |
| AC-4 | important | Removes a downstream divergence. |
| AC-5 | important | Lets the downstream container-fixture tests run unchanged. |
| AC-6 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-07 | Planned from Waveforge's merge rehearsal on `2b6b985a`; all five claims confirmed against the tree. The operator chose all five items for one wave before the 1.40.0 tag. | Waveforge follow-up 2026-11-07; reads of `review_policy.py:24`, `setup_commands.format_command`, `render_platform_surfaces` `.gitignore` merge, `test_secrets_prefix_collapse._legacy_ruleset`, `test_wave_work_lifecycle` fixture calls |
| 2026-11-07 | R1: `review_policy._NORMALIZER_SIGNATURE` hashes `gardener_metadata.__loader__.get_data(gardener_metadata.__file__)`. | `scripts/review_policy.py`; new `tests/test_review_policy_zip_import.py` (subprocess `-B`, `PYTHONPYCACHEPREFIX` unset, zip path via argv; asserts both modules load from the zip, signature equals the filesystem value, and the old `Path(...).read_bytes()` form raises `NotADirectoryError` from the zip) |
| 2026-11-07 | R2: `setup_commands.powershell_quote` doubles `'`, U+2018, U+2019, U+201A and U+201B through `str.translate`; `format_command` uses it, and `sqlite_storage_migration._quote_argument` resolves it at call time with a `getattr` fallback to the ASCII form. | `scripts/setup_commands.py`, `scripts/sqlite_storage_migration.py`; `test_setup_commands.PowerShellQuoteTests` (exact string per quote, all five in one argument, POSIX `shlex.join` unchanged, `setup_recovery` end to end); `test_sqlite_storage_migration` `test_powershell_quoting_doubles_all_five_single_quotes` (exact per quote, `restart_command` `--pack` and `accounting_gap_guidance` end to end, POSIX unchanged) and `test_quote_argument_falls_back_when_an_older_setup_commands_is_loaded` |
| 2026-11-07 | R3: headings `## Disposable work` / `### Disposable work`, lead-in `**Disposable work.**`, cross-references `seed 180’s **Disposable work**` (the install prompt's "Seed 180’s" sentence and seed 209's "(seed 180, " form normalized), domain-map `**Disposable Work**`, running phrase in `wave_work.py` and `run_tests.py`. `_GITIGNORE_BLOCK` and seed 050 carry the new comment; `_GITIGNORE_LEGACY_LINES` holds the previous one for the loose-line drop only. `.gitignore` re-rendered with `wf_sync_surfaces(mode='run')` (wrote only `.gitignore`). | New `tests/test_work_area_wording.py` (census marked default-profile-only; `render_platform_surfaces.py` excluded from the census because it must hold the legacy line, covered by its own tests); three new `RenderGitignoreBlockTests` (previous block, loose previous comment, legacy set disjoint from the block plus tracked `.gitignore`). `test_compact_review_artifacts` pins needed no change. Gapfill: the sweep used `perl -pi` over a fixed file list for mechanical substitutions. |
| 2026-11-07 | R4: `_legacy_ruleset` pins SHA-256 `efa742f0…` of canonical JSON over the parsed `rules` table. | `tests/test_secrets_prefix_collapse.py` `LegacyRulesPinTests`: rebranded fixture text (runtime paths and brand strings) keeps the pin; regex, filter, keywords, `required`, `validate`, an added and a removed rule each fail it; a regex edit in the fixture text fails the parse |
| 2026-11-07 | R5: `tests/container_fixture_profile.py` (fork-editable, `{}` default); `create_container` / `close_container` in `tests/server_tools_support.py` resolve the profile at call time and raise on collision; 4 + 13 calls in `test_wave_work_lifecycle.py` and 1 in `ReceiptSnapshotPublicIntegrationTests` converted; `RetainedUpgradePreviewTests` unchanged. `docs/architecture/testing-architecture.md` names the module; CHANGELOG 22r97 bullet revised and four 22r99 bullets added. | New `tests/test_container_fixture_profile.py`: recording fake with patched profile, collision raises, call-time resolution; AST guard finds 0 direct calls and 17 / 1 helper calls in the scoped sources |
| 2026-11-07 | Known-bad controls, all in a `git archive HEAD` scratch copy, never the working tree. | AC-1: HEAD zip import raises `NotADirectoryError`; new test fails. AC-2: new tests fail for U+2018..U+201B in both quoters. AC-3: census fails on HEAD (40 failures) and on a reconstructed "Disposable work area" sweep copy (73 problems over 22 files); HEAD renderer fails the three `.gitignore` tests; current renderer with the legacy check removed fails the loose-comment test. AC-4: HEAD byte pin raises "historical ruleset fixture changed" on the rebranded fixture. AC-5: guard on HEAD sources reports 17 and 1 sites. |
| 2026-11-07 | AC-6: focused suites green after inputs settled; docs validate; no `__pycache__` under `.wavefoundry/framework/`. A first run was flagged only by the repository-change guard because CHANGELOG and testing-architecture were edited mid-run; all its tests passed. Full suite left to the coordinator. | `run_tests.py --file` over 17 files (setup_commands, sqlite_storage_migration, render_platform_surfaces, secrets_prefix_collapse, betterleaks_engine, wave_work_lifecycle, server_tools_lifecycle, compact_review_artifacts, review_policy, review_policy_zip_import, work_area_wording, container_fixture_profile, profile_literal_census, vocabulary_prompt_names, bytecode_cache, render_agent_surfaces, docs_lint): 1849 tests OK; `wf_validate_docs` passed |
| 2026-11-07 | Coordinator fix after the first full run: `test_server_package.TestCensusTests.test_no_flat_enumeration_of_the_scripts_root_outside_the_helper` refused the new zip test's `SCRIPTS.glob("*.py")`. The test now builds the zip from `framework_files.framework_source_files(include_aliases=True)` with scripts-relative arcnames, so the `wf_server` package and the flat aliases are inside it too. | First full run 12,590 tests, 1 failure in `test_server_package.py`; after the fix `test_review_policy_zip_import` and `test_server_package` 32 OK |
| 2026-11-07 | Delivery repair cycle 2 (QA findings `22r99-qa-del-posix-asserts-unguarded-on-windows`, `22r99-qa-del-zip-signature-content-unpinned`, by the coordinator): the two POSIX `_quote_argument` assertions in `test_powershell_quoting_doubles_all_five_single_quotes` now run under a patched POSIX `os`, so the test holds on native Windows; the zip test also asserts the signature equals the SHA-256 of `gardener_metadata.py`'s source bytes, killing QA mutant M13. Test-only. | `test_review_policy_zip_import` and `test_sqlite_storage_migration` focused runs OK |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Readiness repair cycle 1 for lane findings DC-1, DC-2, QA-1, QA-2 and CR-1: exact wording forms and an anchored census for AC-3; the tracked `.gitignore` re-render and authored prompt copies in Scope; the AC-5 guard predicate, scope and known-bad counts; `RetainedUpgradePreviewTests` left direct; `testing-architecture.md` and the changelog bullets named. | Ledger findings `22r99-docs-dc1-final-wording-unpinned`, `22r99-docs-dc2-self-hosted-gitignore`, `22r99-qa-1-ac3-heading-check-vacuous`, `22r99-qa-2-ac5-ast-check-underspecified`, `22r99-code-cr1-ac5-guard-scope` | Convert `RetainedUpgradePreviewTests` too |
| 2026-11-07 | Readiness repairs F1-F11 from the red-team primer, before any approval: the second PowerShell quoter through a shared helper; a test-only fixture profile module with a callable hook and collision check; all 18 fixture calls converted with an AST guard; the 22r97 changelog contradiction; the zip intent narrowed to the lifecycle and upgrade import path with the other import-time readers named; the docstring and comment included in the sweep; a legacy set separate from the block; every rule field pinned; the sweep's files listed; a sources-only zip. | Red-team primer `.wavefoundry/work/22r99/readiness/primer.json` | Keep the hook location open between the vocabulary profile and the extension module |
| 2026-11-07 | Use Waveforge's exact wording ("Disposable work", "disposable work area"). | A shared wording removes the divergence; "Disposable work area" headings would leave one. | Keep the "Disposable work area" headings from the 2026-11-07 sweep. |
| 2026-11-07 | Keep the previous `.gitignore` comment as a recognized legacy line. | Existing installs may hold a loose copy outside the fenced block. | Rename without a legacy line. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A rules-only pin misses a change to the fixture's allowlist or policy | `test_betterleaks_engine` already compares those sections with the shipped rules. |
| The fixture profile becomes a second, drifting configuration point | One test-only module, empty by default, never edited upstream beyond its defaults, with a test that drives it. |
| A vocabulary sweep rewrites rule content | The `generic-api-key` stopword `wave` and all rule content are out of scope. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
