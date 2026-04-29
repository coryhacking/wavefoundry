# Review System Overview

## Purpose

Explain the shared Wave Framework review model: what review is for, how it fits into a wave, and where project-specific gate logic belongs.

## Shared Review Model

- Review begins with a readiness evaluation before implementation and continues with implementation-time and final review passes as the wave progresses.
- Required review depth depends on change type, risk, and project policy.
- The shared framework supplies generic review lanes and expects seeded repositories to define exact triggers and local reviewer surfaces.
- A wave is not complete until required review outputs are collected and addressed.
- The same readiness evaluation used before implementation should be rerun during final review before closure.

## Generic Review Lanes

The framework commonly expects some combination of these lanes in seeded repositories:

- code correctness and maintainability review
- QA / verification review
- architecture and boundary review
- security review
- performance review
- docs-contract review
- release / packaging review

## Stateful Logic And Re-Entrant Review (Shared Heuristic)

Seeded closure and review prompts (`190-finalize-feature.prompt.md`, `docs/prompts/review-wave.md`) should steer `code-reviewer` and `qa-reviewer` toward bugs that only appear across **repeated calls** or **incomplete branches**:

- **Per-key mutable state** (dictionaries, caches, grace timestamps): reviewers should verify **set / clear / leave unchanged** on **every** exit from the control-flow region that references the state, including `else` arms when a boolean gate (for example `powerStateChanged`) splits mismatch vs match paths.
- **Re-entrancy**: if a function runs every step, tick, or timer fire, reviewers should ask what happens to that state when the **same** external condition holds on consecutive calls (stale timestamps, leaked entries).
- **Parallel helpers**: when two functions implement the same policy (for example `*WithDelays` vs a simpler checker), reviewers should compare them for **symmetry** unless the change doc records an intentional difference.

This complements **docs-contract review** (spec vs code): contract review catches documented invariants; **code review** catches branch gaps the spec did not yet encode.

## Relationship To Personas

- Personas may add specialized domain context to a review, but they do not replace the repository's generic review gates.
- Repo-local policy should decide when persona participation is selected during readiness evaluation and whether those persona findings are gating.
- Shared framework guidance assumes persona lanes can be required both before implementation and again at final review when the delivered behavior warrants it.

## Seeded Repository Expectations

Init and upgrade should generate or refresh review docs in the repository that define:

- the actual reviewer roles available in the repository
- which change types trigger which review lanes
- how the readiness evaluation selects implementer lanes, reviewer lanes, and persona lanes before implementation begins
- what evidence each reviewer should inspect
- which reviewer and persona outputs are gating for readiness and closure

In a seeded project, that local source of truth lives in `docs/contributing/review-and-evals.md` plus related agent-role docs.

## Related Docs

- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `docs/contributing/review-and-evals.md`
- `docs/contributing/agent-team-workflow.md`
