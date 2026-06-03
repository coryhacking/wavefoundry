# Review and Evaluations

Owner: Engineering
Status: active
Last verified: 2026-06-03

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
| `wave-council-readiness` | Every wave before implementation (`wave_review.enabled`) | Yes |
| `wave-council-delivery` | Every wave after implementation and before closure (`wave_review.enabled`) | Yes |

## Readiness Checklist (Prepare Wave)

Before implementation begins, the wave-coordinator confirms:
- [ ] All admitted changes have consolidated change docs at `docs/waves/<wave-id>/`
- [ ] Required review lanes identified for each admitted change
- [ ] AC priority recorded on each change doc (`## AC priority`)
- [ ] product-owner acknowledgment recorded for product-impacting waves
- [ ] `qa-reviewer` confirmed for any bug fix (per `review_policies.require_qa_reviewer_for_bug_fixes`)
- [ ] `wave-council-readiness` signoff recorded in `## Review Evidence` when `wave_review.enabled`

## Wave Closure

**Closure requires all of the following:**

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness are reconciled in `## Review checkpoints` (including deferred with rationale when applicable)
3. `wave-council-readiness` and `wave-council-delivery` signoffs are present in `## Review Evidence` when `wave_review.enabled`
4. Docs-contract review: recorded as performed (findings in `## Review checkpoints`) or `not applicable` with rationale, when any `docs/specs/*.md` changed during the wave
5. Journal distillation complete: any important implementation/review lessons added to relevant role or persona journals
6. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
7. `docs/agents/session-handoff.md` cleared or refreshed to reflect post-closure state
8. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized

**Closure is blocked until all eight items above are explicitly recorded in the wave record.**

## Wave Council

The framework ships `wave_review.enabled: true` by default (formerly `wave_council_policy`) so the council surface is available without operator action. When `required_for_all_waves: true` (operator opt-in for enforcement), Wavefoundry requires a universal two-phase council pass for every wave:

- `wave-council-readiness` before implementation
- `wave-council-delivery` before closure

Wave Council runs a red-team adversarial primer (Phase 1) before fixed seats (Phase 2), then synthesizes. The full protocol — depth tiers, seat responsibilities, output shape — is in `docs/agents/specialists/wave-council.md`.

Fixed Phase 2 seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, plus one rotating domain seat from wave evidence.

The `wave-council` owns the protocol and verdict. The `wave-coordinator` routes lanes and enforces the gate.

Record machine-readable council signoffs in `## Review Evidence`. Record the narrative synthesis in `## Review checkpoints`.

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
