# Harnessability Assessment

Change ID: `12ed1-feat harnessability-assessment`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Böckeler's "ambient affordances" concept identifies structural properties of a codebase — type system strength, module boundary clarity, debt density — as the primary determinant of how governable it is by agent harnesses. Wavefoundry's `070-quality-and-debt.prompt.md` guides a human through this assessment, but the result is never machine-readable, never periodic, and never fed back into the wave lifecycle. Without a harnessability signal, operators have no objective baseline for how much to trust agent outputs in a given repo, and no way to track whether interventions (refactors, type coverage improvements) are improving agent tractability over time.

## Requirements

1. A `wave_harnessability` MCP tool (or a `harnessability` section in `wave_audit`) must produce a scored assessment of the repo's agent-operability across at least three dimensions: type coverage, module boundary clarity, and debt density.
2. Each dimension must produce a rating (`high`, `medium`, `low`) with a brief evidence summary (e.g. file count, % typed, detected boundary violations).
3. The overall harnessability score must be included in `wave_audit` as a top-level field alongside wave, validation, and index health.
4. Scores must be computed from observable repo signals (file structure, config files, index metadata) — not from LLM inference, keeping this a computational sensor.
5. Assessment results must be stored to `.wavefoundry/harnessability.json` for trend tracking across sessions.

## Scope

**Problem statement:** Wavefoundry has no machine-readable signal for how tractable a repo is to agent operation — the assessment exists only as a seed prompt for human inspection.

**In scope:**

- Harnessability scoring helpers for type coverage (tsconfig, mypy.ini, pyproject.toml presence + strictness flags), module boundaries (presence of domain boundary docs, import graph depth proxy), debt density (TODO/FIXME density, avg file length proxy)
- `wave_harnessability_response` or integration into `wave_audit_response`
- Persistence to `.wavefoundry/harnessability.json` with timestamp
- Seed documentation explaining the harnessability concept and how to act on low scores

**Out of scope:**

- LLM-based quality assessment — computational signals only
- Full static analysis (import graph tracing, cyclomatic complexity) — proxies are sufficient for v1
- Trend visualisation

## Acceptance Criteria

- AC-1: `wave_audit` includes a `harnessability` section with per-dimension ratings and an overall score.
- AC-2: Type coverage dimension correctly detects typed/untyped projects based on config presence and strictness.
- AC-3: Results are written to `.wavefoundry/harnessability.json` after each assessment.
- AC-4: Seed documentation explains harnessability, how scores are computed, and how to improve a low score.
- AC-5: Assessment completes on any repo regardless of language or structure — unknown dimensions return `unknown` rather than erroring.

## Tasks

- [ ] Design harnessability scoring schema and dimension list
- [ ] Implement type coverage scorer (tsconfig, mypy, pyright, ruff config detection)
- [ ] Implement module boundary clarity scorer (domain boundary doc presence, avg directory depth)
- [ ] Implement debt density scorer (TODO/FIXME count, avg file length)
- [ ] Integrate into `wave_audit_response` as `harnessability` section
- [ ] Implement persistence to `.wavefoundry/harnessability.json`
- [ ] Add seed documentation
- [ ] Add tests for each scorer and graceful handling of unknown project types

## Agent Execution Graph

| Workstream       | Owner       | Depends On     | Notes |
| ---------------- | ----------- | -------------- | ----- |
| scorers          | implementer | —              | can be parallelized |
| audit integration| implementer | scorers        |       |
| persistence      | implementer | scorers        |       |
| seed + tests     | implementer | audit integration |    |

## Serialization Points

- Scoring schema must be finalized before audit integration

## Affected Architecture Docs

N/A — additive new tool; no boundary or data-flow impact beyond `wave_audit`.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Audit integration makes the score visible in the primary governance tool |
| AC-2 | required   | Type coverage is the most universal and actionable dimension |
| AC-3 | important  | Persistence enables trend tracking; not required for v1 value |
| AC-4 | important  | Seed doc is how operators act on a low score |
| AC-5 | required   | Must not break on non-standard project layouts |

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
| Proxy metrics are imprecise — score may not reflect true harnessability | Frame as directional signal, not ground truth; document limitations in seed |
| Many project types (Go, Rust, Ruby) have different conventions | Unknown dimension → `unknown` rating; expand coverage over time |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
