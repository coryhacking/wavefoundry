# Keep the AC-Locality Sensor Advisory by Recorded Decision

Change ID: `1yzj8-maint ac-locality-sensor-stays-advisory`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-24
Wave: `1yzj9 sensor-advisory-decisions`

## Rationale

Wave `1wur7` introduced the AC-locality docs-lint sensor (`_check_ac_asserts_repository_state`), which flags an acceptance criterion that asserts repository-wide state ("the full suite is green") instead of an outcome the change controls. Wave `1wuju` (change `1wujs`, Requirement 2) registered it `advisory` and recorded that a flip to `blocking` would be a separate change once field data existed. The 1.27.0 release checklist listed it as still advisory with no decision.

Field data (2026-09-24, the sensor run over the final text of every change document; `evidence/field_data.py` and `evidence/field_data.out`):

- Waves before the sensor (247 waves, 880 change docs): 431 findings in 424 change docs (48%). All 12 randomly sampled findings are true positives.
- Waves since `1wur7` (55 waves, 85 change docs, excluding this wave): 1 finding, a true positive (`1yd25-debt` AC-4, "the full suite is green"), which closed with the warning noted.
- No false positive observed; only final text is measured, so in-flight hits reworded during readiness leave no trace.

Decision (operator, 2026-09-24): the sensor stays advisory permanently. Guidance plus the warning reduced the pattern from 48% to about 1%. The one miss carried no verification gap, because whole-suite health is enforced at close by the framework test receipt. Blocking would turn a phrase-matching heuristic into a hard stop in consumer repositories, including at the upgrade docs gate, for little remaining benefit.

Two mechanisms still describe this sensor as awaiting a flip: the advisory warning suffix ("a flip to blocking is a recorded change") and the release checklist, which lists every advisory sensor for a flip decision. A recorded standing decision needs a place in the registry so both stop re-raising it. `inert_record_layout_config` (wave `1yyoj`) is in the same position: advisory by design under ADR `1yb8v`.

## Requirements

1. `SENSOR_POLARITY_REGISTRY` entries accept an optional `decided_wave` naming the wave whose recorded decision keeps the sensor advisory. Both current advisory entries get `decided_wave: 1yzj9`: `ac_asserts_repository_state` on this change's field data, and `inert_record_layout_config` by the standing decision recorded in this change's Decision Log (ADR `1yb8v`'s amendment already says its warning never fails lint). Polarity stays `advisory` for both; detection logic and scope are unchanged.
2. `_route_sensor_findings` validates `decided_wave` at the same point it validates polarity, before any branch on findings or the warning sink, so a misregistration raises even when there are no findings. A `decided_wave` that is not a non-empty string, or that is set on a `blocking` entry, raises `ValueError` naming the sensor. For an advisory entry with `decided_wave`, the suffix is exactly `[advisory sensor \`<id>\`, introduced in wave \`<X>\`; advisory by recorded decision in wave \`<Y>\`]`. Entries without it keep today's suffix `[advisory sensor \`<id>\`, introduced in wave \`<X>\`; a flip to blocking is a recorded change]`. The `WARNING:` prefix and finding text are unchanged.
3. The release checklist in `docs/prompts/package-wavefoundry.prompt.md` (not seed-rendered; edited directly) lists only advisory sensors without a `decided_wave` for a flip decision, and names the decided ones as settled.
4. Every statement that this sensor will flip, or that the checklist lists every advisory sensor, is updated. Seed edits happen under the `seed_edit_allowed` gate, and the seed-rendered prompt is mirrored by hand, because `wf render-surfaces` does not carry seed prose into existing prompts.
   - Seed `170-plan-feature`: the AC-locality paragraph states the sensor is advisory by recorded decision (wave `1yzj9`), dropping "a flip to `blocking` is a separate recorded change made on field data" and the "meant to block one day" wording. In the "New docs-lint sensors ship advisory" paragraph, "every entry still advisory" becomes "every advisory entry without a recorded decision", and one sentence adds that a recorded decision may keep a sensor advisory permanently.
   - `docs/prompts/plan-feature.prompt.md`: the AC bullet's sensor clause and its "(the release checklist lists every sensor still advisory ...)" parenthetical, mirroring seed 170.
   - `docs/contributing/change-workflow.md`: the matching sentence.
   - `docs/architecture/testing-architecture.md`: the polarity paragraph records the decision and the `decided_wave` field.
   - Code text: the comment above `SENSOR_POLARITIES`/`SENSOR_POLARITY_REGISTRY` in `constants.py`, and the `_check_ac_asserts_repository_state` docstring in `wave_validators.py`.
   - Checked and unchanged, because they state only the general rule, which stays true for undecided sensors: seed `190` and its mirror `close-wave.prompt.md`, `docs/specs/mcp-tool-surface.md`, seed `160`, `AGENTS.md`. The dated `1wujs` `CHANGELOG.md` bullet is history and is not edited.
5. `CHANGELOG.md` `[Unreleased]` gains a Changed bullet: the AC-locality sensor stays advisory by recorded decision, with the field data in one sentence, and the release checklist no longer asks about decided sensors.

## Scope

**Problem statement:** the AC-locality sensor's intended flip was never decided, so the warning text and the release checklist keep describing a pending flip that the field data does not justify.

**In scope:** the `decided_wave` registry field and its validation, the warning suffix, the release-checklist wording, guidance, code-comment and changelog updates, field-data evidence.

**Out of scope:** changing either sensor's detection or scope; changing any sensor's polarity; rewriting historical closed-wave criteria or released changelog history.

## Acceptance Criteria

- [ ] AC-1: Through the real `docs_lint.py` CLI, an in-scope (readied or active) scratch wave with a repository-wide AC passes lint and its `WARNING:` line carries the exact decided suffix for wave `1yzj9`, without "a flip to blocking is a recorded change"; in-process with a patched entry lacking `decided_wave`, the existing suffix is unchanged.
- [ ] AC-2: A `decided_wave` that is empty, not a string, or on a blocking entry raises `ValueError` even when called with no findings and no warning sink; the evidence mutants (decided branch dropped, suffix applied unconditionally, flip text left in the decided suffix, each validation removed, validation moved after the findings branch, a registry entry's `decided_wave` removed) each fail a test.
- [ ] AC-3: Both registry entries carry `decided_wave: 1yzj9`. The release checklist, seed 170, `plan-feature.prompt.md`, `change-workflow.md`, `testing-architecture.md`, the `constants.py` comment, the sensor docstring and the changelog state the decision, pinned by `AdvisoryFirstRulePinTests` (removed clauses asserted absent, new sentences asserted present). The documents this change edits validate, and this change's own suites and new tests pass.

## Tasks

- [ ] Add `decided_wave` validation and the decided suffix in `_route_sensor_findings`; set both registry entries; update the `constants.py` comment and the sensor docstring.
- [ ] Update the tests that pin the advisory suffix and the guidance prose (`AdvisoryFirstRulePinTests`: seed 170, prompt surfaces and contributing docs, release checklist; `SensorPolarityRegistryTests`); add the decided-suffix CLI assertion and the validation tests; record the mutants in wave evidence.
- [ ] Update seed 170 (gate), mirror it into `plan-feature.prompt.md`, and update the release checklist, contribution workflow, testing architecture and changelog.
- [ ] Keep the field-data script and output in wave evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Registry, routing, tests, docs | implementer | readiness | Single write owner |
| Verification | code, qa, docs-contract reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/contributing/change-workflow.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: the sensor-polarity paragraph records the standing decision and the `decided_wave` field.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The warning must stop describing a flip that will not happen |
| AC-2 | required | A decision field on a blocking sensor is a misregistration |
| AC-3 | required | Guidance and the release checklist must agree with the decision |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-24 | Readiness round 1: red-team, code, architecture and QA approve; docs-contract blocked on the seed 170 and plan-feature prompt clause claiming the checklist lists every advisory sensor. One repair: that clause, the prompt mirror, code comment and docstring, validation placement and empty-string rule, exact suffix text, both entries recorded under `1yzj9`, test census widened to `AdvisoryFirstRulePinTests`, superseded `1wujs` condition recorded, field-data script now prints every Rationale figure | readiness-review.md; evidence/field_data.out |
| 2026-09-24 | Planned first as a flip to blocking; operator decided after reviewing the field data that advisory is enough, so the change records a standing advisory decision instead | evidence/field_data.py over 966 change docs |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-24 | Keep the AC-locality sensor advisory permanently | Pattern fell from 48% to about 1% of change docs under the warning; the one miss had no verification gap because the close-time test receipt enforces suite health; blocking would hard-stop consumers on a heuristic | Flip to blocking (consumer upgrade friction for marginal gain); leave undecided (the release checklist keeps re-raising it) |
| 2026-09-24 | Supersede the flip condition recorded by `1wujs` (field data from at least one release with no false-positive report, decided at the release checklist) | The condition is met and the flip is deliberately declined on the data above | Flip now that the condition is met |
| 2026-09-24 | Keep `inert_record_layout_config` advisory permanently, recorded here | It reports config keys that do nothing; ADR `1yb8v`'s amendment says the warning never fails lint and `1yygb` rejected blocking because it breaks existing installs; recording it here gives the decision one wave of record | Credit `1yyoj`, whose own change left the polarity for a later decision |
| 2026-09-24 | Record standing decisions in the registry (`decided_wave`) | One source both the warning suffix and the release checklist can read | Prose-only decision (the suffix would keep promising a flip) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Warning fatigue lets repository-wide criteria creep back | The release checklist still lists undecided sensors; a later wave can revisit with new field data |
| Tests pinning the old suffix text | Updated in the same change; suffix prefix and sensor naming unchanged |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
