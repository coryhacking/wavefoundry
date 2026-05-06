# Sensor Finding Severity Triage

Change ID: `12ed1-enh sensor-finding-severity-triage`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Böckeler frames the strategic goal of a harness as directing human review to where it matters most — not eliminating it. Wavefoundry's operator review lane is currently a single undifferentiated queue: every wave looks equally urgent regardless of what sensors fired. A security reviewer finding a critical vulnerability and a performance reviewer noting a minor inefficiency both result in the same operator review prompt with no priority signal. Adding severity triage to sensor findings — and surfacing that triage in the operator review request — routes human attention more effectively.

## Requirements

1. Inferential sensor reviewers (`212`, `213`, `214`) must include a `severity` field in their structured verdicts: `critical`, `high`, `medium`, `low`, or `none`.
2. `wave_review_response` must aggregate sensor severities and include a `max_severity` field in its response.
3. When `max_severity` is `critical` or `high`, `wave_review` must emit an advisory diagnostic flagging the finding for priority operator attention.
4. The operator review request in `190-finalize-feature.prompt.md` must include the severity summary so the operator can triage before reading the full diff.
5. `critical` severity findings from any sensor must be explicitly noted in the Review Evidence section — the agent must not record `approved` without acknowledging the finding.

## Scope

**Problem statement:** All sensor findings look the same to the operator — there is no triage signal to direct human attention to what matters most.

**In scope:**

- `severity` field in structured verdict format for seeds `212`, `213`, `214`
- `max_severity` aggregation in `wave_review_response`
- Advisory diagnostic for critical/high severity findings
- Updates to `190-finalize-feature.prompt.md` to surface severity in operator review request
- Guidance in `007-review-system-overview.md` on severity levels and escalation

**Out of scope:**

- Automated escalation or blocking on critical findings (operator decides)
- Severity for computational sensor findings (linter errors are binary pass/fail)
- SLA or deadline enforcement based on severity

## Acceptance Criteria

- AC-1: Seeds `212`, `213`, `214` verdicts include a `severity` field with one of the defined levels.
- AC-2: `wave_review_response` includes `max_severity` aggregated across all declared lane signoffs.
- AC-3: `critical` or `high` max severity emits an advisory diagnostic in `wave_review`.
- AC-4: `190-finalize-feature.prompt.md` includes severity summary in the operator review request.
- AC-5: `007-review-system-overview.md` documents severity levels and the escalation pattern.

## Tasks

- [ ] Add `severity` field to verdict format in seeds `212`, `213`, `214`
- [ ] Implement severity aggregation in `wave_review_response`
- [ ] Add advisory diagnostic for critical/high severity in `wave_review_response`
- [ ] Update `190-finalize-feature.prompt.md` to surface severity in review request
- [ ] Update `007-review-system-overview.md` with severity documentation
- [ ] Add tests: severity aggregation, advisory on critical/high, no advisory on low/none

## Agent Execution Graph

| Workstream       | Owner       | Depends On               | Notes |
| ---------------- | ----------- | ------------------------ | ----- |
| seed updates     | implementer | —                        | 212, 213, 214 verdict format |
| server impl      | implementer | verdict format defined   | wave_review_response changes |
| tests            | implementer | server impl              |       |

## Serialization Points

- Verdict format (including `severity` field) must be agreed before seed updates and server impl proceed in parallel

## Affected Architecture Docs

N/A — confined to seed surface and MCP tool response shape; no boundary impact.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Severity field in verdicts is the foundation everything else depends on |
| AC-2 | required   | Aggregation in wave_review is what makes severity visible at the governance layer |
| AC-3 | important  | Advisory on critical/high is the primary human-routing mechanism |
| AC-4 | important  | Surfacing in the operator review request is where operators actually see it |
| AC-5 | important  | Documentation embeds the pattern in agent memory for future waves |

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
| Inferential severity ratings are subjective — two runs may give different results | Severity is a triage signal, not ground truth; document this in seed |
| Agents may inflate severity to trigger escalation | Severity criteria must be concrete in seed prompt (e.g. "critical = exploitable vulnerability or data loss") |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
