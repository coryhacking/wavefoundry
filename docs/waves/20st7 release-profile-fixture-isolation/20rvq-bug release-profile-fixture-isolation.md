# Release profile fixture isolation

Change ID: `20rvq-bug release-profile-fixture-isolation`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-16
Wave: `20st7 release-profile-fixture-isolation`

## Rationale

The operator authorized official 1.32.0 after committing the completed Tensorwell work. Default qualification passed 11,867 tests, but the compatibility matrix exposed fixture assumptions in recently added portability and hook tests. Repair the tests' environments and expectations while retaining production guards and meaningful negative coverage. This is release preparation, with no consumer upgrade work or public API change.

The earlier explicitly approved release repair in test_archive_ownership_portability.py is already committed as 667cfbd0 and is not reopened here. The pending single-file waiver question for test_mcp_tool_extensions.py is not authority for the other files: normal admission and readiness govern this consolidated change.

## Requirements

1. Verified-pack ownership tests stage under an owned private temporary parent. Legacy aliases must still exercise canonical-parent cleanup, exact original path binding, missing files, final links/replacements and positive cleanup. Preserve the test worker's protected-ancestor checks unchanged.
2. Legacy-hook declaration tests use a valid core/runner roster when validating an otherwise valid distribution declaration. Preserve malformed-entry and reject-before-render controls; no production declaration validation is relaxed.
3. Core-read hook tests own their explicit declaration fixtures, using existing declaration test support rather than partially overwriting an ambient distribution declaration. Preserve ordinary core-read exemptions, writer refusal, overridden/aliased/hidden read refusal, stale/missing/nonregular source refusal and no server/model imports during rendering. Keep a real positive core-read control.
4. Hook-parity verification remains byte-exact for the shipped default. Under a changed distribution declaration, verify the fresh pre-edit hook's declaration-dependent permission names and source digests against the effective roster and actual source bytes; permit differences in only those two policy-data assignments when comparing its template with the committed default hook. Every other byte and every other host hook remains checked. Do not add profile skips or rewrite committed hooks as test setup.
5. Changes stay in the four declared test files. Production guards, renderers, profile/declaration modules, runner deadlines, qualification reader and packed sources are read-only. No test is deleted, skipped or converted to a pass without its assertions.

## Scope

**In scope:** the four declared test files and existing wave/change documentation; isolated regression and negative controls; focused qualification under default/second/declared, one fresh canonical default qualification after all material edits, and sequential full compatibility qualification for the release.

**Out of scope:** Tensorwell behavior, production hooks or filesystem policy, tests' execution deadlines, model loading, native Windows qualification, dependency updates, automatic closure, and timing investigation. The 600-second indexer cutoffs and TechDocs errors following two-second child calls remain explicit incomplete/failed observations, not silently accepted timing exceptions or proven product defects. Requalify the final tree without overlapping full suites; escalate remaining failures without unbounded unchanged retries.

## Acceptance Criteria

- [ ] AC-1: The verified-pack fixture's existing positive and refusal cases run under each profile without protected-ancestor cleanup errors; removing private staging reproduces the alias cleanup refusal in an isolated protected profile.
- [ ] AC-2: Valid legacy hook entries pass and malformed entries fail for their own declaration errors under shipped and declared profiles, preserving placeholder expansion and pre-render refusal.
- [ ] AC-3: Explicit core-read fixtures retain allowed core reads and refuse writers, aliases, overridden/hidden reads and invalid source contracts under every profile, without server/model imports.
- [ ] AC-4: Default hook parity remains byte-exact; declaration-aware parity verifies actual permission data, refuses an incorrect permission contract and an unrelated template edit, and adds no skips.
- [ ] AC-5: This change's touched test suites and controls pass, its edited documents validate, and no failure elsewhere is attributable to it.

## Tasks

- [ ] Isolate private pack parents and declaration fixture state.
- [ ] Make hook-parity expectations explicitly declaration-aware without weakening default parity.
- [ ] Execute the four affected suites under all three profiles and bounded known-bad controls before final qualification.
- [ ] Freeze material edits, run canonical default once, then the two compatibility profiles sequentially; retain exact reports and disclose any incomplete workers or remaining failures.
- [ ] Obtain independent code, QA, security and release delivery reviews; consolidate durable results in wave.md.

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
| 2026-10-16 | Planned after complete compatibility results: second failed verified-pack alias cleanup, two TechDocs child-result reads and an incomplete indexer; declared additionally failed partial declaration fixtures and pre-edit hook parity. Default 11,867/200/12 passed in 779.246s. No production defect is inferred from the child/worker timing observations. | /private/tmp/release-1.32.0-{second,declared}-final.log; ignored release-1.32.0 reports |
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
