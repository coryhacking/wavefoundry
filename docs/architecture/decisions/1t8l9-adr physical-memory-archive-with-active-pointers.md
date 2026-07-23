# 1t8l9-adr — Physical Memory Archive with Active Pointers

Owner: Engineering
Status: accepted
Last verified: 2026-07-22

## Context

Status filtering kept retired memories out of normal memory briefings, but their
full bodies remained in the active memory directory and ordinary semantic and
graph corpora. As project memory grows, that makes historical material easier
to retrieve accidentally and leaves no project-visible retention boundary.

## Decision

Archive only through an explicit `memory_reconcile(status="archived")`
decision. The operation runs under the shared cross-process mutation lock and a
writer-owned memory fence, renames the retired body into the index-excluded
`docs/agents/memory/archive/`, atomically marks it with archive
date/reason/path, and atomically publishes a compact pointer under
`docs/agents/memory/pointers/`.

Default memory briefings, advisory reads, semantic indexing, and graph
extraction exclude archive bodies. Targeted normal memory search may return a
pointer; `memory_search(include_history=True)` or `status="archived"` resolves
the body. Proposal/backfill still scan archived source dispositions so history
is not regenerated. Decisions, operator preferences, and fragile-file records
require an additional explicit eligibility confirmation.

The transaction is state-derived: retries inspect the active body, archive body,
and pointer on disk and converge after interruption. The body move uses a
filesystem rename, never copy/delete.

## Consequences

- Git records a move of the canonical body while active retrieval carries only
  compact discovery metadata.
- Setup and upgrade rebuild from a non-mixed corpus boundary: archive bodies are
  excluded by both normal walking and explicit incremental-file seams.
- An archived body remains version-controlled and explicitly retrievable; this
  feature does not delete history or change ranking/decay formulas.
- Protected memories require current semantic judgment before archival; age
  alone is never archive authority.

## Alternatives Considered

- **Status-only archival:** rejected because the full body remains in normal
  docs and graph traversal.
- **Copy then delete:** rejected because rename better preserves filesystem/Git
  intent and has fewer interruption states.
- **Automatic age-based archival:** rejected because age does not prove that a
  decision, preference, or fragile-file warning is no longer operational.
