# Agent Memory Records

Owner: Engineering
Status: active
Last verified: 2026-08-03

Typed, evidence-backed memory records for the agent memory layer: prior failed
attempts, operator preferences, fragile files, review findings, environment
gotchas, and decisions — captured so prior learning surfaces at action time
(before an edit, a review, or a lifecycle step), not only when an agent
happens to search the right prose.

This layer is **not** generic chat memory, and it is distinct from the wave
continuity model (wave records, session handoff, journals): records here are
retrieval/action artifacts that link to and distill from those surfaces.
Journals remain role retrospectives; `docs/references/` remains curated
narrative.

## Record schema

One record per file: `docs/agents/memory/<memory-id>.md`. The docs-lint rules
(`check_memory_docs`) are the schema contract — a record that fails lint must
never surface as an advisory.

Required lines (in the header block):

| Line | Form | Meaning |
| ---- | ---- | ------- |
| `Owner:` / `Status:` / `Last verified:` | standard doc metadata | `Status:` carries the MEMORY status: `candidate`, `active`, `stale`, `superseded`, `rejected`, or `archived` |
| `Memory ID:` | `` `<lifecycleId>-mem <slug>` `` (must equal the filename stem; legacy bare-slug ids from before wave 1t9w7 remain valid) | stable identity for supersession links |
| `Kind:` | `` `one of the eight kinds` `` | drives decay policy and advisory routing |
| `Confidence:` | number in `[0.0, 1.0]` | advisory ranking input; decays kind-awarely, never deletes |
| `Created:` / `Updated:` | `YYYY-MM-DD` | `Created` anchors churn-based decay |
| `Supersedes:` / `Superseded by:` | `` `memory-id` `` (optional; `Superseded by:` REQUIRED when status is `superseded`) | history is preserved through supersession, never deletion |

An evidence-derived record keeps its original finalized `Validation:` verdict
as provenance when the ordinary lifecycle later supersedes it. A promoted
record may therefore be `Status: superseded` only when it carries the required
`Superseded by:` successor link; lifecycle supersession is not relabeled as an
agent-validation rewrite.

Required sections:

- `## Summary` — the lesson, one short paragraph, phrased as what changes the
  next action.
- `## Evidence` — bullets with backticked refs (wave/change ids, commit SHAs,
  file paths, test names). Memory without evidence is opinion; lint rejects
  records whose evidence bullets carry no refs.
- `## Targets` — bullets with backticked target refs the advisory attaches to:
  - `` `path/to/file.py` `` — a file
  - `` `symbol:Class.method` `` — a symbol
  - `` `community:hub:<node-id>` `` — a graph community, referenced by its
    **hub node id** (the stable cross-rebuild anchor; raw community ids are
    renumbered by re-clustering)

Optional: `## Notes`.

## Physical archive and searchable register

Retired records may be archived only through
`memory_reconcile(memory_id, status="archived", archive_reason=..., retain_for_history=true)`. Eligible
statuses are `stale`, `superseded`, and `rejected`; decisions, operator
preferences, and fragile-file records additionally require
`eligibility_confirmed=true` after a current review confirms the knowledge is no
longer operational.

The operation first renames the retired body into the index-excluded
`docs/agents/memory/archive/`, then atomically marks it with `Archived:`,
`Archive reason:`, and `Archive path:`. It leaves a compact record-shaped
entry in `docs/agents/memory-archive.md`. The register carries only stable ID,
title, kind, targets, archive date, successor, and archive path. Full archive
bodies are excluded from ordinary semantic indexing; the compact register
remains indexed and searchable.
Setup and upgrade detect the retired generated `memory/pointers/` directory,
derive this register from archive bodies, and remove the pointer copies before
index publication. The index walker also excludes that legacy path during the
transition, so an interrupted or older repository cannot keep indexing it.

Archive only material that remains important to project history. For a reviewed
retired record that is not history-worthy, use `memory_purge(memory_id=..., reviewed=true)`;
it permanently removes the body and register entry and cannot be undone by Wavefoundry.
The body is first renamed into an index-excluded purge-staging path. Register
publication must succeed before final deletion; a publication failure rolls the
body back, while an interruption after staging is completed by retrying the same
`memory_purge` call.
For evidence-derived memories, purge first records only the SHA-256 source-event
identity in `.wavefoundry/memory-purge-dispositions.json`. This compact,
repo-visible authority is outside the indexed memory corpus and survives index
rebuilds and fresh clones, so removal cannot regenerate the same proposal.
Setup and upgrade preserve an existing authority file byte-for-byte.
The rename, metadata rewrite, and manifest publication are
state-derived and retry-safe under the cross-process mutation lock and memory
fence; no copy/delete move is used.

Archive bodies are excluded from ordinary semantic indexing, graph extraction,
briefings, and action-time advisories. A targeted normal `memory_search` may
return the compact register entry. Use `memory_search(include_history=true)` or
`memory_search(status="archived")` to retrieve the archived body. Archived
source-event dispositions remain part of proposal/backfill duplicate history,
so archival never regenerates old candidates.

If a process stops after the rename but before metadata/manifest publication, the
retired-status body is a **pending archive**. It stays excluded from every
default advisory and index path, but unfiltered/history reads retain it so its
source disposition cannot be regenerated. Docs lint fails loudly with the exact
`memory_reconcile(memory_id=..., status="archived", archive_reason=...)` retry
needed to finish the transaction.

For related active lessons, use `memory_consolidate(mode="dry_run")` first.
It only proposes same-kind records with identical canonical targets. Applying
one returned group requires an explicit reviewed title and summary; the new
playbook is created only after every source passes a locked read-only preflight,
then every source is superseded and archived. Consolidation has no bulk retired-
record cleanup path; age alone never authorizes archival.

## Kinds and decay

| Kind | Decays on | Notes |
| ---- | --------- | ----- |
| `failed_attempt` | target-file churn since `Created` | the failure may no longer reproduce |
| `successful_pattern` | target-file churn (slow) | pattern may have been refactored away |
| `review_finding` | target-file churn | finding may be fixed or moot |
| `operator_preference` | never (code churn) | preferences outlive refactors |
| `environment_gotcha` | elapsed time | tool versions move on |
| `fragile_file` | **never auto-decays** | churn sets a needs-reverification flag instead — churn on a fragile file is ambiguous evidence (refactored away vs actively unstable); only reconciliation retires it |
| `decision` | never (code churn) | decisions are superseded explicitly |
| `dependency_gotcha` | elapsed time | ecosystem moves on |

Decay affects advisory ranking and briefing inclusion only. Status and
supersession are the ONLY lifecycle mechanisms — decay never deletes,
auto-supersedes, or rewrites a record.

Tactical and time-sensitive decay adapts to the target's observed change
cadence. The read path fetches commit timestamps for every surfaced file target
in one state-store query, derives each target's median commit interval, applies
named multiplier/minimum/maximum clamps, and uses the most conservative
half-life for a multi-target record. A target with fewer than two timestamps,
or an unreadable freshness store, uses the established fixed half-life.
Decisions and operator preferences remain immune to automatic age penalties;
fragile-file churn continues to set `needs_reverification` without attenuation.

Ordering keeps policy separate from relevance. Records compare first by exact
target class, base-confidence band, surfaced status, and kind family
(`protected`, `fragile`, `tactical`, `time_sensitive`); adaptive freshness,
semantic query rank, centrality, and memory id order only within those policy
boundaries. `memory_brief` remains queryless. Wave `1tbt5` evaluated an
in-process BM25 + semantic RRF candidate, but did not wire it into
`memory_search`: the curated semantic pass was unavailable in the implementation
environment and the hermetic candidate did not improve the shipped baseline.

## Duplicate detection

Adding a record runs a deterministic, DETECTION-ONLY duplicate check against
existing `active`/`candidate` records (retired history is never a duplicate).
Two independent signals are reported:

- `evidence_ref`: the new record shares at least one `## Evidence` ref (an
  originating event id, a wave/change id, or a path) with an existing record.
- `normalized_content`: the `(kind, sorted targets, summary)` identities match,
  where the summary is compared after a fixed normalization (lowercased, every
  run of non-alphanumeric characters collapsed to one space, trimmed).

`memory_add` still writes the record and attaches a `possible_duplicate`
advisory naming the matched ids and signals; pass `abort_if_duplicate=True` to
refuse the write instead (no mutation). This detection is what keeps evidence
derived candidate supply idempotent. It NEVER marks a record superseded, merges,
or deletes: reconciliation stays an explicit operator action. Semantic
contradiction detection (conflicting but not duplicate claims) is deliberately
not attempted here.

## Proposing candidates from review evidence

### Historical install/upgrade backfill

Established projects use `memory_backfill(mode='create',
entry_path='setup|upgrade')` after the newly installed MCP is reloaded. The
tool inventories closed waves without Git and processes bounded,
server-selected batches. It checkpoints per-wave fingerprints and short random
claims in `.wavefoundry/index/memory-state.sqlite`; there is no fallback state
file. Every created record remains `candidate` / `Validation: pending` until a
focused agent follows its evidence and current target and calls
`memory_validate`.

Repeat backfill and validation until the response reports
`ready_for_index`. Setup and migration resume by rerunning ordinary `wf setup`;
upgrade uses `wf_upgrade(phase='resume_after_memory')`. The owning lifecycle
command publishes through a durable `publishing_index` receipt: the index
finalizer rechecks source fingerprints and zero pending work immediately before
its epoch CAS, then records the exact attempt, expected generation, and
inventory digest. If the process stops after index publication but before the
backfill checkpoint, the next ordinary retry reconciles the completed
generation and does not repeat the index pass. Changed history requeues its
wave instead of publishing stale candidates; unchanged indexed history reuses
the completed run without another validation ceremony. Receipt-authorized
publication is a foreground, synchronous convergence of both semantic layers;
detached index jobs do not inherit publication authority. While paused,
backfill mutations update durable files/seqlock state but do not start
background indexing. A zero-source wave, unsupported legacy source, and
mechanical failure are reported separately; none is represented as an empty
successful candidate set.
Each create response carries a run-scoped `validation_worklist` with the exact
pending `memory_id` values for the next bounded page, its total count, and the
remaining count. Validate that page, then call backfill again; older unrelated
candidates cannot hide the current run. The no-MCP `wf memory-validate`
fallback accepts the same rewrite fields as the MCP tool (`--rewrite-kind`,
`--rewrite-title`, `--rewrite-summary`, repeatable `--rewrite-evidence` and
`--rewrite-target`, and `--rewrite-confidence`).

Concurrent setup/upgrade callers converge on one active SQLite run per entry
path. The lookup and creation are one `BEGIN IMMEDIATE` transaction backed by a
partial uniqueness invariant, so separate processes cannot split the pending
census. An upgrade whose parent process loaded older Wavefoundry code may first
discover this gate when the newly extracted `--update-index` runs. Exit 4 in
that handoff is action-required: reload the MCP implementation, use the
run-scoped worklist, and resume. Index/rebuild/cleanup never fall through an
old-shaped retained lock.

`memory_propose(wave_id, mode)` fills the corpus from work a wave already
did, instead of waiting for hand-authored records. It reads two local, typed
sources and NEVER a raw transcript:

- each explicitly admitted change doc's `## Decision Log` becomes a `decision`
  candidate (unadmitted sibling Markdown files are ignored),
- the canonical `events.jsonl` repaired real-defect findings become a
  `failed_attempt` candidate (or a `fragile_file` candidate for a file repaired
  more than once in the same wave). Code targets come from the linked
  `executable_evidence` record, never from free-form disposition prose.

Drafting is CONSERVATIVE: only durable-shaped signals that carry a concrete code
anchor (an implementation-file path or `symbol:`/`community:` ref) are drafted;
documentation and generic config paths are not treated as executable anchors.
It never drafts every material finding, and
the conversational kinds (`operator_preference`, `environment_gotcha`,
`dependency_gotcha`) are structurally unavailable from the typed ledger and left
to operator authoring. `mode='dry_run'` (default) returns the drafts;
`mode='create'` serializes the duplicate scan and write under the shared
cross-process ledger lock, then writes through the normal path (forbidden-content
scanned, exact/normalized duplicates skipped so concurrent re-runs are
idempotent). Each generated record persists its stable `Source event:` and starts
with `Validation: pending`; every later disposition, including rejection and
supersession, suppresses regeneration. Proposal mode always writes candidates and
reports zero promoted. Each proposed record also carries a
`Source exploration cost:` line (see below).

### Agent validation before close

`wf_close_wave` checks the closing wave's eligible sources. Missing candidates or
pending validation block closure with the exact recovery operation, so the active
agent can complete the loop rather than silently lose memory:

1. `memory_propose(wave_id, mode='create')`;
2. follow each candidate's evidence and inspect its current target;
3. state what changes the next action;
4. check durability, canonical overlap, target accuracy,
   duplicates/contradictions, and confidence;
5. call `memory_validate` with one outcome:

- `promote` — verified, actionable, durable, and nonredundant;
- `retain` — useful but still uncertain enough to remain a labeled candidate;
- `reject` — stale, unsupported, status-only, cheaply rediscoverable, or already
  fully owned by a canonical contract;
- `rewrite` — the source is valuable but generated prose is not; create a
  corrected active record and supersede the generated candidate.

This is a bounded focused memory-quality pass, not a new delivery council. A wave
may correctly yield no memories. Python owns extraction, linking, serialization,
and history; the agent owns semantic usefulness. Contradictions are surfaced,
never automatically resolved.

### `Source exploration cost:` (optional metadata)

An optional frontmatter line recording the measured consumed-token cost of the
wave that produced an evidence-derived candidate (its current SQLite
context-efficiency `request_debit + response_debit`; the closed `wave.md`
projection is a portability fallback only when no authoritative live row
exists). It is a measured number, never a constant,
and grounds the separately-labeled "estimated exploration avoided" wave metric.
Absent on manually-authored records, and omitted (not stamped as 0) when the
producing wave's measured cost is zero. A successor record minted through an
explicit supersession link (a validation rewrite or `memory_add` with
`supersedes`) inherits its predecessor's positive cost so the grounding
survives rewrites; an explicitly provided cost wins, and records without
supersession lineage are never stamped by inheritance (wave 1tdl8).

## Forbidden content

Never store: secrets/credentials/tokens, raw transcripts, full logs, or
personal/user-profile facts unrelated to repository work. docs-lint enforces
this with the journal forbidden-content patterns plus personal-fact phrasing.
Records are repo-visible and reviewable by design.

## Template

```markdown
# <short lesson title>

Owner: Engineering
Status: candidate
Last verified: 2026-07-13

Memory ID: `example-fragile-chunker`
Kind: `fragile_file`
Confidence: 0.7
Created: 2026-07-13
Updated: 2026-07-13
Source event: `finding:<wave-id>:<finding-id>`
Validation: pending

<!-- Finalized evidence-derived records additionally carry:
Validated by: agent
Action delta: <what changes>
Validation rationale: <why>
Evidence verified: true|false
Current target verified: true|false
Canonical overlap: none|supplements|duplicates
-->

## Summary

<what changes the next action, one short paragraph>

## Evidence

- `1abcd-bug some-change` — <how this was learned>
- `abc1234` — <commit that demonstrated it>

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
```
