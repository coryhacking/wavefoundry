# Define Cross-Platform Support Policy

Change ID: `12t9a-change define-cross-platform-support-policy`
Change Status: `implemented`
Owner: planner
Status: implemented
Last verified: 2026-05-22
Wave: `12t9b public-rollout-readiness-decisions`

## Rationale

Wavefoundry already contains cross-platform-aware code paths, but its operator-facing install and upgrade contract is not explicit. macOS and Linux appear to be first-class paths, while Windows still depends on POSIX-centric flows and documentation that points operators to Git Bash or WSL. Before broader rollout, the project should define an explicit support policy so maintainers do not over-promise native Windows behavior that the repository does not consistently provide.

## Requirements

1. Define a clear support-tier policy for macOS, Linux, and Windows.
2. Decide whether Windows support is native, WSL2-only, or explicitly unsupported for the current rollout phase.
3. Identify scripts, prompts, and launchers that currently depend on POSIX shell semantics versus Python/native Windows entry points.
4. Update operator guidance and verification expectations to match the chosen platform policy.
5. Record the follow-on work required to raise Windows support beyond the initial policy.

## Scope

**Problem statement:** The codebase shows partial Windows handling, but the public support boundary is ambiguous and risks confusing downstream operators.

**In scope:**

- Define support tiers for macOS, Linux, and Windows for the next rollout stage.
- Audit current POSIX assumptions in upgrade, launcher, and registration flows.
- Decide whether WSL2 is the required Windows path for now.
- Update platform-facing docs and rollout guidance to match the decision.
- Identify the engineering backlog needed for full native Windows support if that remains a future goal.

**Out of scope:**

- Delivering full native Windows parity in this planning change.
- Rewriting all shell launchers immediately.
- Expanding support to additional environments such as BSD variants or container-only workflows unless required by the platform policy.

## Acceptance Criteria

- [x] AC-1: The change doc defines the rollout support policy for macOS, Linux, and Windows, including whether Windows requires WSL2.
- [x] AC-2: The plan names the known Windows-sensitive or POSIX-sensitive surfaces that must align with the chosen policy.
- [x] AC-3: The plan states the required documentation and verification updates for operators and maintainers.
- [x] AC-4: The plan distinguishes immediate rollout policy from future native-Windows improvement work.

## Tasks

- [x] Review install, upgrade, launcher, hook, and Codex-registration surfaces for OS-specific assumptions.
- [x] Define the support-tier recommendation for the next rollout.
- [x] Capture the doc, prompt, and test surfaces that must be updated once the policy is approved.
- [x] Record future backlog items required for native Windows support beyond WSL2.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| platform-audit | planner | — | Enumerate platform-specific assumptions in code and prompts |
| policy-definition | planner | platform-audit | Choose support tiers and Windows stance |
| rollout-alignment | planner | policy-definition | Name required doc and verification updates |

## Serialization Points

- Public install and upgrade docs must not promise native Windows support until the policy is explicit.
- Registration and launcher guidance should align with the chosen Windows stance before broader distribution.

## Affected Architecture Docs

`docs/architecture/current-state.md`, `docs/architecture/cross-cutting-concerns.md`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/testing-architecture.md`, and likely `docs/architecture/decisions/` for the support policy ADR.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Rollout messaging needs an explicit platform contract before broader distribution |
| AC-2 | required | The policy must be grounded in actual code and workflow constraints, not assumptions |
| AC-3 | required | Operator docs and verification must match the chosen support boundary to avoid false promises |
| AC-4 | important | Future-native-Windows work should stay visible but is secondary to the immediate support stance |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Change scaffolded from rollout-readiness evaluation. | Repository inspection of upgrade prompts, launcher generation, Windows launchers, and shell-based registration flows. |
| 2026-05-22 | Published the rollout support policy as macOS native, Linux native, and Windows via WSL2, then aligned operator-facing install, upgrade, README, and architecture docs to that boundary. | `README.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, and `docs/architecture/current-state.md`; verification: `python3 .wavefoundry/framework/scripts/docs_lint.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-22 | Track platform policy as a dedicated change rather than burying it inside release notes. | The support boundary affects docs, operator expectations, and future engineering scope. | Leave platform support implicit; promise native Windows now. |
| 2026-05-22 | Support Windows through WSL2 for the current rollout rather than claiming native Windows parity. | The repository already contains targeted Windows-aware code, but install, upgrade, and Codex bootstrap still rely on POSIX-shell workflows. | Promise native Windows support immediately; mark Windows unsupported. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Platform language in docs drifts from actual implementation constraints. | Tie the support policy to an explicit audit of shell-dependent and Windows-dependent surfaces. |
| Pressure to promise native Windows support exceeds current implementation reality. | Treat WSL2 as the likely short-term Windows contract unless the audit proves native parity. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
