# Release profile fixture isolation

Change ID: `20rvq-bug release-profile-fixture-isolation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-17
Wave: `20st7 release-profile-fixture-isolation`

## Rationale

The operator authorized official 1.32.0 after committing the completed Tensorwell work. Default qualification passed 11,867 tests, but the compatibility matrix exposed fixture assumptions in recently added portability and hook tests. Repair the tests' environments and expectations while retaining production guards and meaningful negative coverage. This is release preparation, with no consumer upgrade work or public API change.

The earlier explicitly approved release repair in test_archive_ownership_portability.py is already committed as 667cfbd0 and is not reopened here. The pending single-file waiver question for test_mcp_tool_extensions.py is not authority for the other files: normal admission and readiness govern this consolidated change.

## Requirements

1. Verified-pack ownership tests stage under an owned private temporary parent. Legacy aliases must still exercise canonical-parent cleanup, exact original path binding, missing files, final links/replacements and positive cleanup. Preserve the test worker's protected-ancestor checks unchanged. Staging (`_stage_pack_for_consumption`) has no directory parameter and legacy proofs pass only when the staged parent equals `tempfile.gettempdir()`, so the private parent is a fresh subdirectory of the test root (distinct from the root itself and from the existing `private-tmp` fixture) installed by patching `tempfile.tempdir` for the whole test including cleanup, never only during setup.
2. Legacy-hook declaration tests use a valid core/runner roster when validating an otherwise valid distribution declaration. Preserve malformed-entry and reject-before-render controls; no production declaration validation is relaxed. Malformed cases assert their own legacy-hook problem text (the `_legacy_claude_hook_problems` messages), not mere truthiness, so an ambient declaration problem cannot satisfy the assertion; the valid case asserts an empty problem list with the real roster, and the reject-before-render test also asserts the legacy-hook message on stderr.
3. Core-read hook tests own their explicit declaration fixtures, using existing declaration test support rather than partially overwriting an ambient distribution declaration. Preserve ordinary core-read exemptions, writer refusal, overridden/aliased/hidden read refusal, stale/missing/nonregular source refusal and no server/model imports during rendering. Keep a real positive core-read control on the same hook instance in every refusal test, so a digest mismatch cannot make refusals pass vacuously. The copied `mcp_tool_roster.py` and `mcp_tool_extensions.py` stay byte copies (no declaration source appended), because `CORE_READ_CONTRACT` digests the on-disk bytes. Add one explicit hidden-name fixture (a hidden canonical name with a plain alias and no parameter mapping) so hidden-read refusal is covered without relying on the ambient profile; that test first proves the fixture is a valid declaration (`roster.all_tool_tiers()` succeeds and the contract has two entries) and a plain read passes on the same hook, so the hidden refusal cannot pass through a fail-closed contract.
4. Hook-parity verification remains byte-exact for the shipped default. Under a changed distribution declaration, verify the fresh pre-edit hook's declaration-dependent permission names and source digests against the effective roster and actual source bytes; permit differences in only those two policy-data assignments when comparing its template with the committed default hook. Every other byte and every other host hook remains checked. Do not add profile skips or rewrite committed hooks as test setup. The declaration-aware branch is selected only by the loaded declaration differing from the shipped one (`expected_profile().declaration()` against `SHIPPED_DECLARATION`), never by an observed byte difference, so the default and `second` profiles stay on the byte-exact path; the comparison is JSON-normalized (`declaration_support._normalized`) and `declaration_profile_mismatch(expected)` must be `None` before the relaxed branch is taken. Declaration-aware parity requires the fresh contract to have exactly two entries, the fresh `CORE_READ_TOOLS` to equal an independent derivation that shares no code with the renderer (the committed default hook's names, which the default run proves byte-exact, minus the prefixed names in the profile asset's `EXTENSION_HIDDEN_TOOLS`, override targets and `EXTENSION_REPLACEMENTS` keys taken from `expected_profile().declaration()`), with the literal anchor that `wf_gpu_doctor` is absent under `declared`, the `mcp_tool_roster.py` digest to stay byte-exact, and exactly one occurrence of each assignment line; only the `mcp_tool_extensions.py` digest value and the names line may differ. The comparison lives in a pure helper whose refusals are asserted in-test under every profile, including default: a names line with one name added or removed, a changed roster digest, one changed byte outside the two lines, a duplicated assignment line, and the fail-closed empty render. The committed extensions digest is checked only on the byte-exact path, so stale-digest drift is caught by the default run; wave.md states this.
5. Changes stay in the four declared test files. Production guards, renderers, profile/declaration modules, runner deadlines, qualification reader and packed sources are read-only. No test is deleted, skipped or converted to a pass without its assertions.

## Scope

**In scope:** the four declared test files and existing wave/change documentation; isolated regression and negative controls; focused qualification under default/second/declared, one fresh canonical default qualification after all material edits, and sequential full compatibility qualification for the release.

**Out of scope:** CHANGELOG (test-only change, no bullet; the release owner may add one under `[1.32.0]` during release preparation, as the earlier waived fixture repair did), Tensorwell behavior, production hooks or filesystem policy, tests' execution deadlines, model loading, native Windows qualification, dependency updates, automatic closure, and timing investigation. The 600-second indexer cutoffs and TechDocs errors following two-second child calls remain explicit incomplete/failed observations, not silently accepted timing exceptions or proven product defects. Requalify the final tree without overlapping full suites; escalate remaining failures without unbounded unchanged retries.

## Acceptance Criteria

- [x] AC-1: The verified-pack fixture's existing positive and refusal cases run under each profile without protected-ancestor cleanup errors; removing private staging reproduces the alias cleanup refusal in an isolated protected profile (a scratch clone with the edit reverted, run through `run_tests.py --profile second --file`, never the live tree; the expected signature is three ERRORs, each a `PermissionError` naming `temporary-parent-alias` as a protected record path during `TemporaryDirectory` cleanup).
- [x] AC-2: Valid legacy hook entries pass and malformed entries fail for their own declaration errors under shipped and declared profiles, preserving placeholder expansion and pre-render refusal.
- [x] AC-3: Explicit core-read fixtures retain allowed core reads and refuse writers, aliases, overridden/hidden reads and invalid source contracts under every profile, without server/model imports.
- [x] AC-4: Default hook parity remains byte-exact; declaration-aware parity verifies actual permission data, refuses an incorrect permission contract and an unrelated template edit, and adds no skips.
- [x] AC-5: This change's touched test suites and controls pass, its edited documents validate, and no failure elsewhere is attributable to it (no other test imports the four files; the diff touches only the four paths; a per-file test-ID inventory from `-v` output under default, `second` and `declared` shows every pre-edit test ID still present and the skip count unchanged, and a diff grep finds no new skip, expectedFailure, early return or exception swallowing around assertions). A pass here does not qualify 1.32.0: the indexer 600 s cutoffs and TechDocs child-result errors remain separate blockers.

## Tasks

- [x] Isolate private pack parents and declaration fixture state.
- [x] Make hook-parity expectations explicitly declaration-aware without weakening default parity.
- [x] Execute the four affected suites under all three profiles and bounded known-bad controls before final qualification.
- [x] Freeze material edits, run canonical default once, then the two compatibility profiles sequentially; retain exact reports and disclose any incomplete workers or remaining failures. Commands: focused `run_tests.py --file <name>` and `run_tests.py --profile second|declared --file <name>` for the four files (no receipt); canonical `run_tests.py` with `WAVEFOUNDRY_TEST_PROFILE` unset (writes the receipt only when the whole suite is green, so it runs last and nothing under `.wavefoundry/framework/` changes after it); then `run_tests.py --qualify-profile second --qualification-report <path>` and the same for `declared`, one at a time. The inventory in `fixtures/profiles/qualification/coverage.json` does not classify three of the four files, so the reports will show scope `full (coverage unproven)`; that is expected and the inventory is not edited.
- [x] Obtain independent code, QA, security and release delivery reviews; consolidate durable results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture repairs | Coordinator implementer | Current readiness | One writer for all four coupled tests |
| Independent reviews | Fresh reviewer contexts | Frozen plan/source | Required specialist and targeted council authority |
| Qualification | Coordinator | Final material edits | Sequential whole-suite runs; existing compact ignored reports |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_verified_pack_portability.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_core_read_hook.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`

## Affected Architecture Docs

N/A: no shipped module, trust boundary, runner contract or consumer flow changes. Existing declaration_support.py and the existing production hook contract remain authoritative; final test limitations and release evidence belong in wave.md, not a new permanent evidence folder.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserve real legacy ownership tests without aliasing a protected ancestor |
| AC-2 | required | A valid ambient declaration must not invalidate a hook fixture |
| AC-3 | required | Security checks must remain sensitive after fixture isolation |
| AC-4 | required | Profile-aware parity must not mask template or permission-policy regressions |
| AC-5 | required | Verify the owned repair without claiming control over unrelated machine timing |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-17 | Qualification on the frozen tree, sequential: canonical default passed 11,857 tests / 200 files / 12 existing skips in 620.219s, exit 0, receipt inputs_hash `ea4a928052921c825aa182b78cf0a75b976009fbbd8b0ddb296446a347b64065`; `--qualify-profile second` passed 11,849 tests / 200 files, complete, scope `200 of 200 files (full fallback: coverage unproven)`; `--qualify-profile declared` passed 11,857 tests / 200 files, complete, same scope. The indexer 600 s cutoffs and the TechDocs child-result errors seen in the earlier concurrent runs did not recur in these sequential runs; their timing cause remains uninvestigated and no threshold was changed. AC-5 met. Council-delivery approved after four lane approvals. Not a 1.32.0 release qualification by itself: the operator owns the release decision. | scratchpad 20st7-canonical-default.log, 20st7-qualify-second.log, 20st7-qualify-declared.log; `.wavefoundry/cache/qualification/20st7-second.json` and `20st7-declared.json` (ignored cache); `.wavefoundry/framework/test-cache.json` |
| 2026-10-17 | Delivery lanes: code, QA, release and docs-contract PASS; code and QA independently reverified DEL-1 (resolve mutant fails exactly the three legacy tests, unmutated 15/15). QA non-blocking note applied: `test_known_bad_shapes_are_refused` now keeps equal line counts where the shape allows and asserts each case's own reason substring (render file 147/147 after the edit). Release note applied: a default focused run of all four files is logged (170/170, 0 skips). Windows note from code: on `nt` the temp root is the plain owned parent, so the gettempdir-side resolve is uncovered there, as before the wave; native Windows qualification stays out of scope. | scratchpad 20st7-default-focused-r1.log, cr-del1-mutant.log, qa20st7/mutant.log; events.jsonl DEL-1 reverifications |
| 2026-10-17 | Delivery red-team primer: one blocking finding DEL-1 (the private parent was canonical, so a mutant dropping the gettempdir-side `.resolve(strict=True)` in `_cleanup_verified_pack` passed every file; before the wave three tests caught it) plus two non-blocking notes (the parity helper let the two assignment lines move; the real parity run lacked the `wf_gpu_doctor` anchor). Repair cycle 1, after the typed `repair_start`: the temp root is now a link `owned-pack-parent-link` to the owned parent (plain parent on Windows, where the alias tests already skip); the parity helper requires each assignment to keep its committed line position, with `moved assignment` and `swapped assignments` known-bad cases; the declared run asserts `wf_gpu_doctor` absent from the fresh names. Focused runs after repair: default 162/162 (two files), second 170/170, declared 170/170, zero skips. Scratch-clone mutant: the resolve mutant now fails the same three legacy tests; unmutated 15/15. | scratchpad 20st7-second-focused-r1.log, 20st7-declared-focused-r1.log, 20st7-del1-mutant.log; events.jsonl DEL-1 |
| 2026-10-17 | Implemented the four repairs: verified-pack tests stage under an owned private parent (`tempfile.tempdir` patched for the whole test); legacy-hook tests use the production roster arguments and assert each case's exact message, with the renderer refusal asserted on stderr; core-read tests own their declaration through `apply_base_declaration`/`base_declaration` with byte-copied modules, a paired positive read in every refusal test and a new explicit hidden-name test; hook parity selects the declaration-aware branch only from the JSON-normalized loaded declaration and compares through `_declaration_aware_pre_edit_parity` with an independent names derivation and byte-exact roster digest, plus `DeclarationAwareHookParityTests` running the known-bad shapes in every profile. Focused runs: default 23/23 and 147/147, second 170/170, declared 170/170, zero skips. Controls in a scratch clone: AC-1 unrepaired test under `second` gave 3 ERRORs naming `temporary-parent-alias`; AC-4 one unrelated hook byte under `declared` failed with `bytes differ outside the declaration data`, a comment edit to `mcp_tool_extensions.py` without resync failed the default byte-exact path, and a renderer mutant that stops dropping hidden names failed with `fresh CORE_READ_TOOLS does not equal the expected names`. Test-ID inventory: 166 before, 170 after, none removed, four added; no new skip, expectedFailure, early return or exception swallowing in the diff. Gapfill: file reads during implementation used the shell because the four target files and their anchors were already named by readiness. | `git diff --stat` four test files; scratchpad logs 20st7-second-focused.log, 20st7-declared-focused.log, 20st7-ac1-control.log, 20st7-ac4-control-{a,b,c}.log, 20st7-testids-{before,after}.txt |
| 2026-10-16 | Planned after complete compatibility results: second failed verified-pack alias cleanup, two TechDocs child-result reads and an incomplete indexer; declared additionally failed partial declaration fixtures and pre-edit hook parity. Default 11,867/200/12 passed in 779.246s. No production defect is inferred from the child/worker timing observations. | /private/tmp/release-1.32.0-{second,declared}-final.log; ignored release-1.32.0 reports |
| 2026-10-16 | Readiness primer (red-team) PASS with six plan corrections folded into Requirements 1 to 4 and AC-1/AC-5 before readiness was recorded: private parent via `tempfile.tempdir` for the whole test; legacy-hook assertions on message text; byte-copied modules, paired positive reads and an explicit hidden-name fixture; parity mode selected by loaded declaration with exact-equality oracles. | Primer report in session; `_cleanup_verified_pack`, `_claude_core_read_contract`, `test_worker_guard._check` |
| 2026-10-16 | A scratch-only candidate supplying the real roster to the legacy-hook checks passed 3/3 declared tests; unmodified source failed one assertion. No repository code edit yet. | /private/tmp/release-1.32.0-declaration-{diagnostic,candidate}.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-16 | Select targeted fixture isolation and declaration-aware parity. | Repairs test assumptions while retaining production behavior and negative controls. | Relax guards or skip profile tests: hides defects and loses coverage. Regenerate every profile surface or redesign the runner: broadens scope and adds unnecessary work. |
| 2026-10-16 | Full release qualification remains mandatory and sequential after final edits. | Current failed/incomplete profile reports cannot qualify a release; the earlier default source identity must not be relabelled after test edits. | Reuse mismatched reports or silently accept worker timeouts: false evidence. Timing investigation stays deferred. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Over-normalizing hook parity hides a real change | Default raw equality; only two declaration-data assignments may differ; independent current-data and unrelated-byte negative controls |
| Fixture reset masks missing security behavior | Keep real positive and denied writer/override/alias/hidden/source controls |
| Shared host load prevents qualification | Run full suites sequentially; disclose and escalate remaining failed/incomplete work; do not tune thresholds |

## Session Handoff

See docs/agents/session-handoff.md. 20tpp remains paused and is not reopened or closed by this repair.
