# 1t8l9-adr — Physical Memory Archive with Searchable Register

Owner: Engineering
Status: accepted
Last verified: 2026-08-03
Amended: 2026-08-02 — wave `1u8r2`, change `1u8r1`

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
date/reason/path, and atomically rebuilds the compact register at
`docs/agents/memory-archive.md`. The register remains indexed and searchable;
the archive bodies do not.

Default memory briefings, advisory reads, semantic indexing, and graph
extraction exclude archive bodies. Targeted normal memory search may return a
register entry; `memory_search(include_history=True)` or `status="archived"` resolves
the body. Proposal/backfill still scan archived source dispositions so history
is not regenerated. Decisions, operator preferences, and fragile-file records
require an additional explicit eligibility confirmation.

The transaction is state-derived: retries inspect the active body, archive body,
and register on disk and converge after interruption. The body move uses a
filesystem rename, never copy/delete.

Wave `1u8r2` adds two explicit curation operations without changing that
authority boundary. `memory_consolidate` previews a capped same-kind/same-target
group, validates the reviewed replacement through the canonical safety seam,
and rolls a failed multi-source apply back to its pre-apply snapshot.
`memory_purge` irreversibly removes only an individually reviewed retired record
and is advertised as destructive; any evidence-derived source identity is
persisted as a SHA-256 value in the repo-visible, non-indexed
`.wavefoundry/memory-purge-dispositions.json` before deletion so it cannot
regenerate after an index reset or fresh clone.

## Consequences

- Git records a move of the canonical body while ordinary retrieval carries only
  the compact register metadata.
- Setup and upgrade rebuild from a non-mixed corpus boundary: archive bodies are
  excluded by both normal walking and explicit incremental-file seams. They
  also migrate the retired generated pointer directory into the compact
  register before index publication; walkers exclude any residue and lint
  refuses the old schema.
- An archived body remains version-controlled and explicitly retrievable; this
  feature does not delete history or change ranking/decay formulas.
- Protected memories require current semantic judgment before archival; age
  alone is never archive authority.
- The compact register is intentionally searchable, while archive bodies remain
  an explicit-history storage class. There is no pointer directory.

## Alternatives Considered

- **Status-only archival:** rejected because the full body remains in normal
  docs and graph traversal.
- **Copy then delete:** rejected because rename better preserves filesystem/Git
  intent and has fewer interruption states.
- **Automatic age-based archival:** rejected because age does not prove that a
  decision, preference, or fragile-file warning is no longer operational.
