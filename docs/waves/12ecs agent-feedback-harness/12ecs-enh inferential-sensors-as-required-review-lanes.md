# Inferential Sensors as Required Review Lanes

Change ID: `12ecs-enh inferential-sensors-as-required-review-lanes`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Wavefoundry already ships `212-performance-reviewer.prompt.md` and `213-security-reviewer.prompt.md` as inferential sensors — LLM-run agents that assess semantic quality. However, they are invoked ad hoc; there is no mechanism that requires them before a wave closes. High-impact semantic issues (security vulnerabilities, performance regressions, misunderstood requirements) are only caught if an operator explicitly asks. Promoting inferential sensors to first-class review lanes — wired into the same `wave_review` / `wave_close` gate system that enforces operator signoff — makes them structurally unavoidable for projects that declare them.

## Requirements

1. Projects must be able to declare a set of required review lanes in project config (e.g. `"required_review_lanes": ["security", "performance"]`).
2. `wave_review` must check for project-declared lanes and include them in `required_lanes`, alongside the always-required operator lane.
3. A missing project-declared lane signoff must emit a `missing_required_lane` diagnostic and block `wave_close` (same pattern as `missing_operator_signoff`).
4. `007-review-system-overview.md` must document inferential sensor lanes alongside the operator lane, including how to record signoff and how lanes are declared.
5. `190-finalize-feature.prompt.md` must instruct agents to run declared inferential sensors and record their signoff before requesting operator review.

## Scope

**Problem statement:** Performance and security reviewers exist but are never required — they run only if explicitly invoked, so their value is opt-in and inconsistent.

**In scope:**

- `required_review_lanes` config key in `workflow-config.json` (project-level)
- `wave_review_response` reads project config and appends declared lanes to `required_lanes`
- `wave_close_response` blocks on missing declared-lane signoffs (reuses `_lane_has_signoff_in_evidence`)
- Updates to `007-review-system-overview.md` documenting inferential sensor lanes
- Updates to `190-finalize-feature.prompt.md` to invoke and record declared sensor lanes
- Standard signoff format: `- security-review: approved` / `- performance-review: approved`

**Out of scope:**

- Automatically running sensor agents (agents invoke them manually per seed guidance)
- Computational sensors — covered by `12ecs-feat post-edit-computational-sensors`
- Hardcoding specific lanes in framework — all non-operator lanes are project-declared

## Acceptance Criteria

- AC-1: A project declaring `"required_review_lanes": ["security"]` causes `wave_review` to include `security` in `required_lanes`.
- AC-2: Missing a declared lane signoff blocks `wave_close` with a `missing_required_lane` diagnostic.
- AC-3: Projects with no declared lanes behave identically to today — only operator lane required.
- AC-4: `007-review-system-overview.md` documents inferential lanes with signoff format and declaration instructions.
- AC-5: `190-finalize-feature.prompt.md` instructs agents to run and record declared sensor lanes before operator review.

## Tasks

- [ ] Add `required_review_lanes` to `workflow-config.json` schema and config reader
- [ ] Update `wave_review_response` to append project-declared lanes to `required_lanes`
- [ ] Update `wave_close_response` to check all declared lanes (reuse `_lane_has_signoff_in_evidence` pattern)
- [ ] Update `007-review-system-overview.md` to document inferential sensor lanes
- [ ] Update `190-finalize-feature.prompt.md` to invoke and record declared lanes
- [ ] Add tests: declared lane blocks close, no declared lanes unchanged, signoff recorded passes

## Agent Execution Graph

| Workstream   | Owner       | Depends On  | Notes |
| ------------ | ----------- | ----------- | ----- |
| server impl  | implementer | —           |       |
| seed updates | implementer | server impl |       |
| tests        | implementer | server impl |       |

## Serialization Points

- `workflow-config.json` schema for `required_review_lanes` should align with sensors config from `12ecs-feat post-edit-computational-sensors`

## Affected Architecture Docs

N/A — confined to MCP tool surface and seed guidance; no boundary or data-flow impact beyond existing review lane infrastructure.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority         | Rationale |
| ---- | ---------------- | --------- |
| AC-1 | required         | Config → required_lanes wiring is the core deliverable |
| AC-2 | required         | Blocking wave_close is what makes the lane structurally unavoidable |
| AC-3 | required         | Backwards compatibility — projects not opting in must see no change |
| AC-4 | required         | Docs are how agents discover the pattern; undocumented lanes won't be used |
| AC-5 | required         | finalize-feature is where agents act; without it the config is never exercised |

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
| Inferential sensor results are probabilistic — a "passed" signoff may be wrong | Goal is structural coverage, not perfect detection; document this limitation |
| Config drift — project declares lanes that don't match available sensor seeds | Document canonical lane names in seed; emit advisory for unknown lane names |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
