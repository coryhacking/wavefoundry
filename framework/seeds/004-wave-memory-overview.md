# Wave Memory Overview

## Purpose

Explain the shared Wave Framework memory model that keeps wave state, handoffs, and durable workflow lessons synchronized across sessions.

## What “Wave Memory” Covers

Wave memory is the low-noise operational context that lets a feature continue safely across waves, reviews, pauses, and handoffs.

It typically includes:

- active and completed wave records under the project's wave root in the repository
- next-wave or paused-work handoff notes
- readiness-evaluation state, including which reviewer and persona lanes were selected and whether the gate is still valid
- carry-forward decisions for unfinished scope under the same `change-id`
- durable workflow lessons promoted into long-lived memory docs when they are likely to recur

## Shared Model

- A wave should always have enough recorded state that another agent or future session can understand its scope, status, dependencies, and next decision point.
- Wave state should show whether readiness has passed, failed, or needs to be rerun before the next lifecycle action.
- Completed work, remaining work, and deferred work should be reconciled explicitly at wave closure.
- Carry-forward work should stay attached to the same feature thread unless there is a deliberate re-scope.
- Short-lived execution state belongs in wave artifacts and handoffs; reusable lessons belong in workflow memory or canonical docs.

## Relationship To Other Framework Systems

- Wave artifacts capture the current execution slice.
- Journals capture lessons learned by roles or personas while working that slice.
- Persona docs explain who should participate when domain-specific review or planning help is needed.
- Review outputs validate whether a wave is ready to implement, ready to close, or should carry forward.

## Seeded Repository Expectations

Init and upgrade should seed or refresh the topical homes in the repository that implement this model, typically including:

- `docs/waves/`
- `docs/agents/session-handoff.md`
- `docs/references/project-context-memory.md`

Exact schemas and local routing belong in the seeded project docs in the repository, especially `docs/waves/README.md` and the local lifecycle overview.

## Related Docs

- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/200-wave-reconciliation.prompt.md`
- `docs/waves/README.md`
- `docs/references/project-context-memory.md`
