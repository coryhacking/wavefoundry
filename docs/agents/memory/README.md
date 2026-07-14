# Agent Memory Records

Owner: Engineering
Status: active
Last verified: 2026-07-13

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

## Summary

<what changes the next action, one short paragraph>

## Evidence

- `1abcd-bug some-change` — <how this was learned>
- `abc1234` — <commit that demonstrated it>

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
```
