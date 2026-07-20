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
- **architectural decisions** — why an approach was chosen, not just what was done; capture when the reasoning is non-obvious and not recoverable from git history or change docs
- **validated approaches** — positive confirmations of non-obvious choices that worked well; auto-memory should capture these equally with corrections, not only save when something went wrong
- **wave-close retrospective findings** — non-obvious learnings surfaced at closure and promoted to auto-memory or `docs/references/project-context-memory.md`

## Shared Model

- A wave should always have enough recorded state that another agent or future session can understand its scope, status, dependencies, and next decision point.
- Wave state should show whether readiness has passed, failed, or needs to be rerun before the next lifecycle action.
- Completed work, remaining work, and deferred work should be reconciled explicitly at wave closure.
- Carry-forward work should stay attached to the same feature thread unless there is a deliberate re-scope.
- Short-lived execution state belongs in wave artifacts and handoffs; reusable lessons belong in workflow memory or canonical docs.
- **Auto-memory captures both corrections and confirmations.** If only corrections are saved, the memory skews toward avoidance and loses the positive signal of validated patterns. Record non-obvious approaches that worked, not just things that went wrong.
- **Wave close is the primary knowledge-capture moment.** A retrospective step at closure — "what was non-obvious in this wave that a future session should know?" — is the most reliable trigger for surfacing architectural decisions, validated patterns, and workflow discoveries into durable memory.
- **Idle handoff preserves recent history.** When no wave is active, `docs/agents/session-handoff.md` must record the last-closed wave ID and a one-line summary of what shipped so the next session has recent history without running `wf_list_waves`.
- **Session-end capture is a safety net, not a substitute.** The rendered session-end hook (`.claude/hooks/session-capture`, Claude `Stop`) writes a capture summary to `.wavefoundry/logs/last-session-capture.md` — open wave + AC progress, uncommitted-work and handoff-staleness signals, and a nudge to record new quirks/decisions as **memory candidates**. It captures and nudges only: it never writes memory or commits, so the agent/operator still curates handoff and memory deliberately.

## Relationship To The Agent Memory Layer

“Wave Memory” (this doc) is the CONTINUITY model: wave records, session handoff, journals, and project-context
memory — prose surfaces that carry working state and durable narrative across sessions. The **agent memory
layer** is a separate, typed system: evidence-backed records under `docs/agents/memory/` (kinds like
`fragile_file`, `failed_attempt`, `operator_preference`) served at action time through the `memory_*` MCP
tools and as capped advisories on read/impact tools. The two link but do not replace each other: journals stay
role retrospectives, handoff stays session state, and memory records stay retrieval/action artifacts distilled
from them at lifecycle checkpoints.

At review and close, do not start the typed memory layer from an empty corpus: `memory_propose(wave_id)`
drafts `candidate` records from the wave's own typed review evidence (change-doc Decision Logs and repaired
real-defect findings), so the durable lessons the wave already produced become records instead of being
re-derived. It is conservative and agent-validated: drafts are `candidate` only, carry a stable source-event
identity, and a focused agent uses `memory_validate` to promote, retain, reject, or rewrite each draft after
checking its evidence, current target, future-action delta, durability, canonical overlap, target accuracy,
duplicates/contradictions, and confidence. Rejected and superseded source events are durable dispositions, so
re-running does not regenerate them. This is a bounded memory-quality checkpoint, not a new full review council;
many waves should correctly produce no memory. Operator authoring still covers the conversational kinds the typed
ledger cannot supply.

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
