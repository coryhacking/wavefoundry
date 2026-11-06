# Preserve review and hook checks across renamed profiles

Change ID: `22llh-bug renamed-profile-review-and-hook-parity`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-06
Wave: 22lli renamed-profile-review-parity

## Rationale

Local package qualification passed the default and declared-extension profiles but failed the renamed profile with 11 assertions across three test files. Production diagnostics and hook prose correctly use configured item and container names; several tests still expect the default words. These failures prevent a clean compatibility qualification for downstream distributions.

A focused reproduction ran nine test methods and reproduced all 11 failures. Correcting only their expectations in an isolated copy exposed one additional production wording defect: `review_evidence._review_authority_path_error` reports that an escaping record leaves its “wave directory” even when the container has another name. The path is still refused. Correcting that single diagnostic in the copy made all nine methods pass. This is bounded diagnostic evidence, not a repaired source tree or a qualifying test receipt.

## Product Intent

Maintainers of renamed distributions should retain meaningful review, authority-path and generated-hook checks without false failures caused by default vocabulary. The change supports [VISION.md](../../../VISION.md), Horizon 1's dependable delivery on the existing foundation. It preserves lifecycle authority and scanner behavior.

## Requirements

1. Review-attribution and lifecycle-action assertions must use the effective item and container vocabulary while still checking identifiers, statuses, finding attribution and authority requirements. Machine keys and historical approval compatibility remain unchanged.
2. Preserve the historical default council-text byte/hash oracle under an explicit default vocabulary. Also verify the effective profile's council instructions and next action. Do not weaken comparisons through unrestricted word replacement, revised expected hashes without cause, or profile-specific skips.
3. Preserve byte-exact committed-hook parity for the default profile. In the renamed-profile fixture, permit only the known item-noun substitution in the modernization briefing, alongside existing declared-extension allowances. Unrelated prose, permissions and executable differences must still fail. Do not regenerate the fixture's committed hooks before comparison and thereby erase drift.
4. The record-escape diagnostic must use the configured container noun consistently with the existing directory-symlink and ledger-escape diagnostics. Symlink and containment refusal behavior, path disclosure limits and ownership checks remain unchanged.
5. Keep coverage in the default, renamed and declared-extension profiles. Document why vocabulary-sensitive expectations differ and which comparisons remain exact. No new release exception, skip allowance or relaxed compatibility threshold is part of this repair.

## Scope

**Problem statement:** Tests conflate default vocabulary with behavior, and one refusal message still hard-codes the default container name.

**In scope:**

- Six lifecycle attribution assertions, three council-brief subtest comparisons and the subsequent next-action assertion in `test_server_tools_lifecycle.py`.
- Hook parity in `test_render_platform_surfaces.py`.
- Authority-path assertions in `test_review_evidence.py` and the one record-escape diagnostic in `review_evidence.py`.
- A focused clarification in the testing architecture and a CHANGELOG entry.

**Out of scope:**

- Scanner rules, scanning scope, classification records, upgrade behavior and scan scheduling.
- Seeds, lifecycle policy, machine schemas, review gates, profile definitions, the profile runner and generated hook behavior.
- Blanket profile skips, whole-suite golden rebaselining, or weakening authority checks.
- Unrelated website edits, local package version stamps and existing handoff changes.
- Native Windows qualification or a claim that an actual Waveforge distribution was tested.

## Acceptance Criteria

- [x] AC-1: The nine reproduced methods pass in the default, renamed and declared-extension profiles without new skips. Assertions still verify receipt attribution, typed authority and next-action behavior; configured names appear where appropriate. This establishes the intended compatibility outcome together with AC-2 through AC-4.
- [x] AC-2: The original default council-text oracle remains exact. Effective-profile checks detect an incorrect item/container label and a material non-vocabulary change to the council instructions or lifecycle action; passing a renamed profile cannot conceal those regressions.
- [x] AC-3: Hook parity accepts the intended noun substitution and existing declared-extension differences, while a focused negative control confirms that an unrelated changed hook byte is rejected. Default committed-hook parity remains exact.
- [x] AC-4: Existing symlink and escaping-record/ledger controls still refuse the same unsafe paths across the three profiles. Messages use the configured names and retain the existing limits on path disclosure.

## Tasks

- [x] Confirm the scoped baseline using the existing reproduction and current source; retain a concise durable account of the failure classes.
- [x] Repair vocabulary-aware lifecycle assertions and isolate the historical default oracle without broad normalization.
- [x] Repair the narrow hook parity expectation, preserving unrelated-byte detection.
- [x] Correct the record-escape diagnostic and its authority-path assertions.
- [x] Run the affected methods and files in all three profiles, including the focused negative controls; record actual outcomes against ACs.
- [x] Update testing architecture and CHANGELOG, complete required delivery reviews and documentation validation.
- [x] After source freezes, run the framework suite and normal default/renamed/declared-extension compatibility qualification. Report any unrelated failures separately; do not broaden this change's ACs to promise that every repository test passes.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Scoped repair | Implementer | Readied and opened wave | One small sequential implementation; use existing profile fixtures. |
| Verification | QA reviewer | Scoped repair | Check the three profiles and meaningful negative controls before expensive full qualification. |
| Delivery | Coordinator and required review lanes | Verification | Preserve all gate and receipt requirements; no additional experimental review process. |

## Serialization Points

Freeze the affected source before full compatibility qualification. Any subsequent behavior or assertion change requires the relevant checks to run again. Keep unrelated working-tree edits outside the repair.

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `docs/architecture/testing-architecture.md`

The root CHANGELOG.md is also in scope. Do not change profile-runner or shared-helper behavior merely to make these assertions pass; widen the plan first if a new mechanism proves necessary.

## Affected Architecture Docs

Update `docs/architecture/testing-architecture.md` with the distinction between the historical default-byte oracle, effective-vocabulary assertions and the narrow hook-fixture allowance. No runtime ownership or workflow architecture changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the reproduced compatibility failures while retaining coverage. |
| AC-2 | required | Prevents compatibility fixes from hiding changed review behavior. |
| AC-3 | required | Keeps generated-hook drift detection meaningful. |
| AC-4 | required | Repairs downstream wording without weakening containment. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Delivered the admitted scope: all ACs and tasks have evidence; required delivery approvals are current and no findings remain. Full docs validation and diff checks pass. All six reviewed paths still match the frozen candidate, and all edit gates are closed. Wave remains open and uncommitted. | Independent execution, mutation table and profile totals are retained inline in wave.md; typed approvals remain in events.jsonl. No source changes followed review or qualification. The existing local package predates this repair and was not rebuilt. |
| 2026-11-06 | Observe: the complete qualification matrix passes with frozen source. Declared-extension qualification passes 12,485 tests / 221 files / 12 existing skips in 705.813 seconds. Its exact comparison to default passes with zero default-only cases. No allowance, profile definition or baseline oracle changed. | Default 12,485 / 12 skips / 716.508 seconds; renamed 12,467 / 30 skips / 700.315 seconds, with 18 permitted default-only cases; declared 12,485 / 12 skips / 705.813 seconds. Both qualification_report.py comparisons return equal=true. Reports: .wavefoundry/cache/qualification/22lli-{default,second,declared}.json. All three commands and both comparisons exit zero. Alternate profile copies do not replace the canonical default receipt. |
| 2026-11-06 | Observe: full default qualification passes 12,485 tests / 221 files / 12 existing skips in 716.508 seconds. Full renamed qualification passes 12,467 tests / 221 files / 30 existing skips in 700.315 seconds. Exact comparison passes with 18 existing default-only cases; no skip allowance changed. Independent delivery lanes and Council approve with no findings. Declared-extension qualification is running. | run_tests.py --qualification-report .wavefoundry/cache/qualification/22lli-default.json; same command with --profile second and its own report. qualification_report.py --compare default-report second-report --profile second returns equal=true. Default receipt input hash 67a67641b3d521a84201c9d318c66ab5d99255154c35956e47d613cd4709cb63. Typed approvals and independently executed controls are in the wave record and events.jsonl. |
| 2026-11-06 | Observe: all scoped ACs have positive and negative evidence. Declared affected-file run passes 1,057 tests / three files / two existing skips in 181.432 seconds; renamed passes 1,054 / three / six. Default workers passed 1,057 / three / two, with the disclosed concurrent gate-change guard refusal. Thought: freeze the six-path candidate and run the already-planned complete default, second and declared matrix sequentially, with exact comparisons. | Commands: run_tests.py --file test_server_tools_lifecycle.py --file test_review_evidence.py --file test_render_platform_surfaces.py, also with --profile second and --profile declared. Six scoped mutants detected; candidate e9b746357d882960c29f12e35feeb398ccd5cce8d86a8db16f07f2f9b783726a unchanged. No claim of full qualification yet. |
| 2026-11-06 | Observe: renamed affected-file run passes 1,054 tests / three files / six existing skips in 180.835 seconds. AC-2, AC-3 and AC-4 are supported by the positive runs and targeted assertion-failing mutants; no error or unintended skip supplies mutant detection. | Historical digest values unchanged; wrong item/container, typed-authority and grounding mutants fail the council test. Changing MAX_INPUT_BYTES in the copied committed hook fails byte parity outside the allowed noun. Restoring the record-escape literal fails the renamed authority test, whose symlink/escape refusals continue to pass. Default affected tests also passed, with its separate gate-movement refusal disclosed above. |
| 2026-11-06 | Observe: all 1,057 affected-file default tests passed (two existing skips), but the focused runner refused the overall run because the coordinator closed the framework edit gate during execution. No failed test is being waived; no green receipt was produced. Thought: keep gates/source fixed, finish focused renamed/declared checks, then use the required full default suite for a fresh guarded result. | Focused default log: 665 lifecycle, 223 authority and 169 hook tests; 172.341 seconds. The changed path was only .wavefoundry/guard-overrides.json. Both edit gates are now closed. |
| 2026-11-06 | Observe: implemented the four-file repair and updated testing architecture/CHANGELOG. Initial nine-method default and renamed positives pass; declared nine-method positive passes after the final assertion refinement. Six scoped mutants are now detected without errors/skips. A typed-authority mutant initially survived, so the existing assertion was strengthened to cover the complete gate-authority sentence before rerunning that control. Thought: run affected files in all profiles before full qualification. | Mutants: wrong item label, wrong next-action container, narrative substituted for typed authority, changed legacy grounding, unrelated hook input-limit byte and restored record-escape literal. Current results are in disposable work; final qualification is pending. No production control flow, seeds, profile runner or committed hooks changed. |
| 2026-11-06 | Readback: preserve strict default council/hash and hook checks while testing configured names; correct only the record-escape noun. For example a Set distribution must report set directory, while rejecting the same escape. AC-1 through AC-4 cover three test files and one production expression, plus testing architecture and CHANGELOG. Thought: implement this small coupled repair sequentially, then run focused profile controls before full qualification. | Readiness passed on review-policy-08bce7906989f3824f48 with code, QA, architecture and targeted Council approvals; wave opened through wf_implement_wave. Baseline nine-method reproduction and six scoped preimages remain in disposable work. MCP source navigation and pre-implementation memory brief completed; no authority or permission changes. |
| 2026-11-06 | Planned the targeted repair after read-only investigation. No source edits, wave admission or readiness performed. | Package qualification: default and declared-extension profiles green; renamed profile 11 failed assertions in three files. Isolated nine-method reproduction: 11 failures; expectation-only correction: one remaining failure; expectation plus diagnostic correction: zero failures. |

The diagnostic scripts and reports under `/private/tmp/wf-renamed-*` are temporary aids, not durable acceptance evidence. Implementation must record commands and results in the wave before relying on them for delivery. The existing qualification summaries are under `.wavefoundry/cache/qualification/`; they describe the pre-repair tree.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-06 | Select profile-aware assertions, preserved default oracles and one production wording correction. | The failures arise from display vocabulary, while independent control-flow checks remain valuable. | Reverting localized production wording would restore wrong downstream names. Skipping renamed checks, broadly normalizing text or regenerating hooks before comparison would conceal regressions. |
| 2026-11-06 | Run cheap affected checks first, then normal full qualification once the repair is stable. | The previous full renamed run took about 800 seconds; the targeted reproduction already isolates the defects. | Repeated full-suite runs during assertion editing add cost without better diagnosis. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Normalization hides changed review instructions. | Keep the historical default oracle exact and use narrow, explicit effective-profile assertions with a negative control. |
| Hook fixture preparation masks committed drift. | Preserve the copied committed hooks and allow only the known noun difference plus existing extension allowances. |
| A wording repair accidentally weakens path checks. | Run the existing rejection cases through the production authority helper in each profile. |
| Focused success is mistaken for release qualification. | Separate nine-method diagnostic evidence, affected-file tests and final compatibility receipts. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
