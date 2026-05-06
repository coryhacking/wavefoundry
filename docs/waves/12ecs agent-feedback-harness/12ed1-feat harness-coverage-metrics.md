# Harness Coverage Metrics

Change ID: `12ed1-feat harness-coverage-metrics`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Böckeler asks: "how do you know your harness has adequate coverage?" — analogous to code coverage but for sensors. Wavefoundry currently has no answer: there is no way to know which change types, AC categories, or workflow stages have sensor coverage and which are exercised only by human review. Adding harness coverage metrics to `wave_audit` gives operators a concrete signal of where the harness is thin and where human review is carrying all the weight.

## Requirements

1. `wave_audit` must include a `harness_coverage` section reporting which of the three harness dimensions (maintainability, architecture, behaviour) have at least one active sensor configured for the project.
2. Coverage is determined by inspecting project config (`workflow-config.json`): registered sensors map to the maintainability dimension; declared review lanes map to the architecture/behaviour dimensions.
3. Uncovered dimensions must be surfaced as advisory diagnostics with a suggested next step.
4. The section must report a simple coverage ratio (e.g. `2/3 dimensions covered`) alongside per-dimension status.
5. After wave 12ecs ships, the coverage check must also count the behaviour harness test-generation loop as a behaviour-dimension signal when a test runner is configured.

## Scope

**Problem statement:** No signal exists for which harness dimensions are covered by sensors vs. relying entirely on human review — operators fly blind when assessing harness adequacy.

**In scope:**

- `harness_coverage` section in `wave_audit_response`
- Dimension mapping: maintainability ← computational sensors; architecture ← `architecture-review` lane; behaviour ← `security`/`performance` lanes + test runner
- Advisory diagnostics for uncovered dimensions
- Coverage ratio summary field

**Out of scope:**

- Sensor fire-rate tracking (how often sensors actually trigger) — future wave
- Coverage of individual ACs or change types (too granular for v1)
- Integration with non-Wavefoundry CI tools

## Acceptance Criteria

- AC-1: `wave_audit` includes `harness_coverage` with per-dimension status and a coverage ratio.
- AC-2: A project with no sensors and no declared review lanes shows `0/3` coverage with advisory diagnostics for each gap.
- AC-3: A project with sensors registered and `architecture-review` declared shows the correct covered dimensions.
- AC-4: Advisory diagnostics point to actionable next steps (e.g. "add `required_review_lanes: [architecture-review]` to workflow-config.json").
- AC-5: Coverage check is backwards-compatible — projects without `workflow-config.json` return `0/3` without error.

## Tasks

- [ ] Design `harness_coverage` schema and dimension-to-config mapping
- [ ] Implement coverage checker reading from `workflow-config.json`
- [ ] Add `harness_coverage` section to `wave_audit_response`
- [ ] Add advisory diagnostics for uncovered dimensions
- [ ] Add tests: zero coverage, partial coverage, full coverage, missing config

## Agent Execution Graph

| Workstream       | Owner       | Depends On        | Notes |
| ---------------- | ----------- | ----------------- | ----- |
| coverage checker | implementer | —                 | depends on 12ecs config schema |
| audit integration| implementer | coverage checker  |       |
| tests            | implementer | audit integration |       |

## Serialization Points

- Must align with `workflow-config.json` schema from wave 12ecs (`sensors`, `required_review_lanes`)

## Affected Architecture Docs

N/A — additive to `wave_audit`; no boundary impact.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The coverage section is the core deliverable |
| AC-2 | required   | Zero-coverage baseline is the most important case to detect and report |
| AC-3 | required   | Must correctly credit configured sensors and lanes |
| AC-4 | important  | Actionable diagnostics are what make the metric useful rather than decorative |
| AC-5 | required   | Backwards compatibility — must not break existing projects |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Coverage metric may create false confidence if sensors are registered but never fire | v1 reports configuration coverage, not fire-rate coverage; document this distinction |
| Depends on 12ecs config schema being stable | Sequence after 12ecs ships or implement against a draft schema with a migration path |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
