# Review and Evaluations

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Review Lane Summary

| Lane | When Required | Gating |
|------|--------------|--------|
| `code-reviewer` | Non-trivial implementation changes | Yes — blocking findings return to implementation |
| `architecture-reviewer` | Cross-boundary or integration-contract changes | Yes |
| `qa-reviewer` | Bug fixes (always); acceptance criteria requiring coverage | Yes |
| `security-reviewer` | Trust boundary, guard mechanism, or allowed-roots changes | Yes |
| `docs-contract-reviewer` | `docs/specs/*.md` behavioral contract changes | Yes at wave closure |
| `performance-reviewer` | Indexing, search, or MCP response path changes | Advisory |
| `release-reviewer` | Packaging, VERSION, or distribution format changes | Yes |

## Readiness Checklist (Prepare Wave)

Before implementation begins, the wave-coordinator confirms:
- [ ] All admitted changes have consolidated change docs at `docs/waves/<wave-id>/`
- [ ] Required review lanes identified for each admitted change
- [ ] AC priority recorded on each change doc (`## AC priority`)
- [ ] product-owner acknowledgment recorded for product-impacting waves
- [ ] `qa-reviewer` confirmed for any bug fix (per `review_policies.require_qa_reviewer_for_bug_fixes`)

## Wave Closure

**Closure requires all of the following:**

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness are reconciled in `## Review checkpoints` (including deferred with rationale when applicable)
3. Docs-contract review: recorded as performed (findings in `## Review checkpoints`) or `not applicable` with rationale, when any `docs/specs/*.md` changed during the wave
4. Journal distillation complete: any important implementation/review lessons added to relevant role or persona journals
5. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
6. `docs/agents/session-handoff.md` cleared or refreshed to reflect post-closure state
7. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized

**Closure is blocked until all seven items above are explicitly recorded in the wave record.**

## Code Review Requirements

When `code-reviewer` is required:
- Check branch completeness and re-entrant safety for any per-key mutable state the change touches
- Verify dominant patterns from `docs/repo-profile.json` `code_patterns` are followed (when patterns exist)
- Verify `.wavefoundry/framework/scripts/tests/` coverage for any new script behavior
- All blocking findings must be fixed before the wave proceeds to close

## QA Review Requirements

When `qa-reviewer` is required:
- Confirm each required AC row in `## AC priority` has verification evidence (automated test, manual matrix, or documented exception)
- Multi-step verification for any stateful behavior (state across repeated calls or routine steps)
- AC scope gap check: surface important/nice-to-have items not in admitted scope after confirming required ACs

## Docs-Contract Review

At wave closure: if any `docs/specs/*.md` behavioral contract changed during the wave, record a docs-contract review with findings in `## Review checkpoints`. If no specs changed, record `Docs-contract review: not applicable` with a one-line rationale.
