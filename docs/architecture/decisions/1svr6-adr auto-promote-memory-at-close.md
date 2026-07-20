# 1svr6-adr — Auto-Promote Evidence-Derived Memory at Close (Auto-Supersede Still Rejected)

Owner: Engineering
Status: superseded
Last verified: 2026-07-18
Superseded by: `1syle-enh agent-validated-memory-curation-and-backfill`

## Supersession

Evaluation during the same wave showed that deterministic structural proxies
could draft plausible candidates but could not establish semantic usefulness.
Change `1syle` therefore replaced this decision before release: evidence-derived
records are always written as `candidate`, a focused agent verifies the evidence
and current target, and only the typed validation path may promote, retain,
reject, or rewrite. The no-auto-supersede invariant remains in force. The text
below is retained as the historical decision that was implemented and then
reversed.

## Context

The typed agent memory layer (ADR `1sk58`) shipped with a deliberate invariant:
status and supersession are the only lifecycle mechanisms, nothing auto-rewrites
history, and promotion of a `candidate` to `active` is human-gated (an explicit
`wave_memory_reconcile`). That human gate, together with a manual supply step,
made the whole loop inert in practice: nobody remembered to propose candidates
after a close and then reconcile each one, so the corpus stayed empty and the
(already-automatic) surfacing had nothing to surface. The value only exists if
supply and promotion happen as part of normal work.

Separately, the review of `agentmemory` established the danger we must not
reintroduce: auto-*supersede* on similarity (flipping an older record to
non-latest above a Jaccard threshold), which silently rewrites history.

## Decision

Relax the human-gated-promotion posture, but only in the direction that does not
rewrite history:

- `wave_close` **automatically drafts** memory records from the closing wave's
  own typed evidence (change-doc Decision Logs + repaired real-defect findings),
  always on, bounded, idempotent (exact/normalized dedup), and fail-isolated so
  it never affects the close.
- A **deterministic importance criteria** (a pure function of the draft's kind,
  evidence-ref count, code-anchor target, source-signal class; no LLM, no clock,
  no randomness) sets each fresh draft's starting status: repaired real-defect
  signals and code-anchored decisions-with-a-rationale are written `active`;
  thinner drafts are written `candidate`. The close output reports the change.

Auto-promotion is a starting-status choice on a **new** record. It writes an
`active` record; it never touches any existing record. The `1sk58` invariant
stays firm: nothing auto-supersedes, merges, or deletes, and duplicates /
contradictions are still only surfaced (1stwl detection), never auto-resolved.

## Consequences

- The memory loop runs with no manual step: closing a wave populates the corpus
  and the durable records surface on the next `code_read` / `wave_prepare`.
- "Importance" is approximated by deterministic structural proxies, so the
  promotion set is auditable and reproducible, and it is guarded by the 1sufm
  memory-retrieval eval (a widening of the drafting must be shown to add signal,
  not flood).
- The distinction that mattered in the agentmemory review is preserved:
  auto-*promote* (a status choice on a new record) yes; auto-*supersede* (a
  rewrite of an existing record) never.

## Alternatives Considered

- **Keep promotion human-gated.** Rejected: the manual step is precisely the
  adoption killer this change exists to remove.
- **An LLM "is this important?" judge.** Rejected: non-deterministic and
  unauditable; the whole point is a reproducible, testable criteria.
- **Copy agentmemory auto-supersede on similarity.** Rejected: rewrites history
  and detects similarity, not opposition.
