# Warn on Inert Record-Layout Config Keys

Change ID: `1yygb-maint warn-inert-record-layout-config`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-25

## Rationale

Waveforge feedback (modularity RFC section 10.2): configuration keys that look like the record-layout surface are inert, and a new fork could reasonably but wrongly edit them. ADR `1yb8v` already decides that record roots are the `record_paths` module constants and that a `record_layout` block in `docs/workflow-config.json` and a `wave_implement.wave_root` key are inert, but nothing tells an operator who edits them. This repository's own `docs/workflow-config.json` still carries `wave_implement.wave_root`, and no framework install default writes it (older installs do).

Brief: add an advisory docs-lint warning when `docs/workflow-config.json` contains a `record_layout` block or a `wave_implement.wave_root` key, naming `record_paths` as the live surface; remove the inert key from this repository's config. The warning never fails validation and never rewrites a target's config.

## Requirements

1. Docs-lint emits an advisory `WARNING:` (never an error) for each of: a top-level `record_layout` key, a `wave_implement.wave_root` key, and a legacy `wave_execution.wave_root` key, in `docs/workflow-config.json`. The message says the key has no effect and that record roots are the constants in `.wavefoundry/framework/scripts/record_paths.py` (ADR `1yb8v`).
2. The check is registered as an advisory sensor in `SENSOR_POLARITY_REGISTRY` and routed through the existing advisory channel (`_route_sensor_findings`), so its findings are warnings, never entries in `check_workflow_config`'s failure list. `check_workflow_config` keeps its current signature and return value (existing callers and tests expect `[]` for valid configs); the advisory findings come from a separate function that `cli.py` routes at its call sites, introducing no import cycle between `core_validators` and `wave_validators`.
3. Remove `wave_implement.wave_root` from this repository's `docs/workflow-config.json`. No install, setup or upgrade path rewrites or deletes the key in a target repository.
4. The `wave_root` key in `prompt-surface-manifest.json` is out of scope: `docs_gardener` deliberately preserves it for target-side consumers.

## Scope

In scope: the lint check and sensor registration, tests, this repository's config edit, a changelog bullet.

Out of scope: automatic removal from target configs, the manifest `wave_root` key, any change to `record_paths` behavior, RFC items 10.1 (change `1yxl8`) and 10.3 (already documented in the upgrade prompt and seed 160).

## Acceptance Criteria

- [x] AC-1: A fixture config with `record_layout`, and one with `wave_implement.wave_root`, each produce the advisory warning naming the key and `record_paths`, and docs-lint still passes; a config with neither produces no warning.
- [x] AC-2: The sensor appears in `SENSOR_POLARITY_REGISTRY` as advisory, and a mutant that removes the check fails the new tests.
- [x] AC-3: This repository's `docs/workflow-config.json` no longer carries `wave_implement.wave_root`, and the change's own suites and every test it adds pass; the documents this change authors or edits validate.

## Tasks

- [x] Add the advisory check to the workflow-config validation path and register the sensor.
- [x] Add positive and negative fixture tests through the real docs-lint entry point.
- [x] Remove the key from this repository's config; add a changelog bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Lint check and tests | implementer | readiness | Single write owner |
| Verification | code, qa, docs-contract reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `docs/architecture/decisions/1yb8v-adr record-layout-config-over-resolver-protocol.md`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

ADR `docs/architecture/decisions/1yb8v-adr record-layout-config-over-resolver-protocol.md`: add an amendment line. Its Decision says there is no migration hint; a docs-lint advisory warning now names `record_paths` for these inert keys. There is still no fallback, no runtime read and no rewrite of target config.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested warning |
| AC-2 | required | Advisory sensors are tracked for a later polarity decision |
| AC-3 | required | This repository should not carry the inert key it warns about |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Planned from Waveforge RFC section 10.2 at operator request | Operator request; ADR 1yb8v |
| 2026-09-25 | Operator-approved second bounded repair: ADR 1yb8v amendment (DOCS-READY-3), unchanged check_workflow_config signature with separate advisory function routed by cli.py, legacy wave_execution.wave_root warned | readiness-review.md |
| 2026-09-25 | Readiness primer (no blockers): named the advisory routing (warnings sink through _route_sensor_findings, no import cycle) and added cli.py and wave_validators.py to serialization points | readiness-review.md |
| 2026-09-25 | Implemented: `inert_record_layout_findings` in core_validators routed by cli.py through `_route_sensor_findings` as advisory sensor `inert_record_layout_config`; check_workflow_config unchanged; legacy wave_execution.wave_root covered; key removed from this repo's config; ADR 1yb8v amendment; InertRecordLayoutConfigTests (6) OK; mutants killed | test_docs_lint.py InertRecordLayoutConfigTests; evidence/mutants.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | Advisory warning, no automatic removal from targets | Warns forks without rewriting project-owned config | Blocking error: breaks existing installs that carry the key. Auto-remove on upgrade: rewrites project-owned config without consent. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Warning noise on older installs | Advisory only; the message names the fix |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
