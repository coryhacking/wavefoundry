# Agent Memory Records

Owner: Engineering
Status: active
Last verified: 2026-07-20

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
| `Owner:` / `Status:` / `Last verified:` | standard doc metadata | `Status:` carries the MEMORY status: `candidate`, `active`, `stale`, `superseded`, or `rejected` |
| `Memory ID:` | `` `slug` `` (must equal the filename stem) | stable identity for supersession links |
| `Kind:` | `` `one of the eight kinds` `` | drives decay policy and advisory routing |
| `Confidence:` | number in `[0.0, 1.0]` | advisory ranking input; decays kind-awarely, never deletes |
| `Created:` / `Updated:` | `YYYY-MM-DD` | `Created` anchors churn-based decay |
| `Supersedes:` / `Superseded by:` | `` `memory-id` `` (optional; `Superseded by:` REQUIRED when status is `superseded`) | history is preserved through supersession, never deletion |

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

## Duplicate detection

Adding a record runs a deterministic, DETECTION-ONLY duplicate check against
existing `active`/`candidate` records (retired history is never a duplicate).
Two independent signals are reported:

- `evidence_ref`: the new record shares at least one `## Evidence` ref (an
  originating event id, a wave/change id, or a path) with an existing record.
- `normalized_content`: the `(kind, sorted targets, summary)` identities match,
  where the summary is compared after a fixed normalization (lowercased, every
  run of non-alphanumeric characters collapsed to one space, trimmed).

`wave_memory_add` still writes the record and attaches a `possible_duplicate`
advisory naming the matched ids and signals; pass `abort_if_duplicate=True` to
refuse the write instead (no mutation). This detection is what keeps evidence
derived candidate supply idempotent. It NEVER marks a record superseded, merges,
or deletes: reconciliation stays an explicit operator action. Semantic
contradiction detection (conflicting but not duplicate claims) is deliberately
not attempted here.

## Proposing candidates from review evidence

### Historical install/upgrade backfill

Established projects use `wave_memory_backfill(mode='create',
entry_path='setup|upgrade')` after the newly installed MCP is reloaded. The
tool inventories closed waves without Git and processes bounded,
server-selected batches. It checkpoints per-wave fingerprints and short random
claims in `.wavefoundry/index/memory-state.sqlite`; there is no fallback state
file. Every created record remains `candidate` / `Validation: pending` until a
focused agent follows its evidence and current target and calls
`wave_memory_validate`.

Repeat backfill and validation until the response reports
`ready_for_index`. Setup and migration resume by rerunning ordinary `wf setup`;
upgrade uses `wave_upgrade(phase='resume_after_memory')`. The owning lifecycle
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

`wave_memory_propose(wave_id, mode)` fills the corpus from work a wave already
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

`wave_close` checks the closing wave's eligible sources. Missing candidates or
pending validation block closure with the exact recovery operation, so the active
agent can complete the loop rather than silently lose memory:

1. `wave_memory_propose(wave_id, mode='create')`;
2. follow each candidate's evidence and inspect its current target;
3. state what changes the next action;
4. check durability, canonical overlap, target accuracy,
   duplicates/contradictions, and confidence;
5. call `wave_memory_validate` with one outcome:

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
Absent on manually-authored records.

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
