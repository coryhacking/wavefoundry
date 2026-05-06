# Hotfix Bypass Detection

Change ID: `12ed1-feat hotfix-bypass-detection`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Commits that land outside the wave/change-doc lifecycle bypass every harness control Wavefoundry provides — no stage gate, no AC tracking, no operator review lane. SPDD explicitly identifies "firefighting hotfixes that bypass governance permanently" as a risk. Currently `wave_audit` has no awareness of recent git commits; an operator has no way to know whether a period of activity was fully governed or included out-of-band edits.

## Requirements

1. `wave_audit` must include a `commit_governance` section that lists recent commits (configurable window, default 30 days) and flags any that cannot be associated with a known wave or change ID.
2. Association is determined by scanning commit messages for a wave ID pattern (e.g. `12abc`, `12abc-feat slug`) or a known change ID.
3. Unassociated commits must be surfaced as an advisory diagnostic, not a blocking error — hotfixes are sometimes legitimate.
4. The window and any permanent exclusion patterns (e.g. "chore:", "deps:") must be configurable in `workflow-config.json`.
5. The feature must degrade gracefully when git history is unavailable (shallow clone, no git, etc.).

## Scope

**Problem statement:** Commits that bypass the wave lifecycle are invisible to governance — there is no audit signal that out-of-band edits occurred.

**In scope:**

- Git log scan in `wave_audit_response` (or a dedicated helper) to identify recent commits
- Pattern matching against known wave/change IDs extracted from wave docs
- `commit_governance` field in `wave_audit` response with `governed`, `unassociated`, and `excluded` commit lists
- Advisory diagnostic for unassociated commits
- Config for window length and exclusion patterns in `workflow-config.json`

**Out of scope:**

- Blocking pushes or commits (no pre-push hook enforcement)
- Attribution of commits to specific ACs
- Cross-repo audit

## Acceptance Criteria

- AC-1: `wave_audit` response includes a `commit_governance` section listing governed and unassociated commits within the configured window.
- AC-2: Commits whose messages reference a known wave or change ID are classified `governed`.
- AC-3: Unassociated commits produce an advisory diagnostic — not an error.
- AC-4: Exclusion patterns in config suppress expected unassociated commits (e.g. dependency updates).
- AC-5: Feature degrades gracefully when git is unavailable — section is omitted, no error raised.

## Tasks

- [ ] Implement git log scanner helper — returns commits with message + hash in window
- [ ] Implement wave/change ID extraction from `docs/waves/` for matching
- [ ] Add `commit_governance` section to `wave_audit_response`
- [ ] Add advisory diagnostic for unassociated commits
- [ ] Add config support for window and exclusion patterns in `workflow-config.json`
- [ ] Add tests: governed commits matched, unassociated flagged, exclusions respected, git-unavailable graceful

## Agent Execution Graph

| Workstream       | Owner       | Depends On | Notes |
| ---------------- | ----------- | ---------- | ----- |
| git scanner      | implementer | —          |       |
| audit integration| implementer | git scanner|       |
| tests            | implementer | audit integration |  |

## Serialization Points

- `workflow-config.json` schema for exclusion patterns must be finalized before config reader is implemented

## Affected Architecture Docs

N/A — additive to `wave_audit` response; no boundary or data-flow impact.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The commit governance section is the core deliverable |
| AC-2 | required   | Correct classification is the minimum viable feature |
| AC-3 | required   | Advisory-only is essential — blocking on unassociated commits would break legitimate hotfix workflows |
| AC-4 | important  | Without exclusions, noise from dependency bots makes the signal useless |
| AC-5 | required   | Must not break in CI shallow clones or non-git environments |

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
| Commit message conventions vary — matching may miss valid governed commits | Make matching lenient (substring, case-insensitive); document the pattern |
| Large repos with long histories are slow to scan | Window-based scan limits to recent commits; default 30 days |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
