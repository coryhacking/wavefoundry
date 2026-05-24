# Wave Close Summary Generation

Change ID: `12sq4-enh wave-close-summary-generation`
Change Status: `implemented`
Owner: software-engineer
Status: implemented
Last verified: 2026-05-21
Wave: 12sq2 enterprise-role-seeds-and-lint

## Rationale

The `## Wave Summary` section in closed wave records is currently left as `*(Populated at closure.)*` — never actually filled in. Operators have no concise record of what a wave actually delivered, including adjustments made during implementation that deviated from the original plan. At close time, `wave_close` has access to all the information needed to synthesize this summary from the change docs as they actually exist at closure, not as originally planned.

## Requirements

1. `wave_close` must populate `## Wave Summary` in wave.md with a generated summary before writing the closed status.
2. The summary must reflect the work actually done — reading from completed change docs, progress logs, and decision logs — not just the original planned scope.
3. The summary must consist of a few prose paragraphs covering the general narrative — what the wave set out to do, what shipped, any notable pivots, advisory findings, or carry-forwards — followed by bullet points if the wave warrants them (e.g. per-change callouts, significant decisions). Bullet points are optional; prose paragraphs are always present. Length and structure are determined by wave complexity.
4. The summary must be generated from the wave record and its admitted change docs at close time; it must not require operator input to produce.
5. The summary must be written to `## Wave Summary` in wave.md, replacing the `*(Populated at closure.)*` placeholder.

## Scope

**Problem statement:** Wave records have a `## Wave Summary` section that is never populated, leaving no concise readable record of what each wave actually delivered.

**In scope:**

- Summary generation logic in `wave_close` (server_impl.py) that reads admitted change docs and synthesizes the two-part summary
- Prose narrative: a few paragraphs covering what the wave set out to do, what shipped, notable pivots, advisory findings, and carry-forwards
- Optional bullet points: per-change callouts or significant decisions where bullets aid scannability; omitted when prose alone is sufficient
- Writing the result into `## Wave Summary` before the closed status checkpoint is written

**Out of scope:**

- LLM-based summarization — summary is synthesized from structured fields in the change docs (title, completed ACs, progress log, decision log), not from free-text inference
- Retroactively populating summaries for already-closed waves
- Operator-editable summary templates or configuration

## Acceptance Criteria

- [x] AC-1: After `wave_close`, `## Wave Summary` in wave.md contains a populated short paragraph and per-change detail section (not the placeholder)
- [x] AC-2: The per-change detail section reflects completed ACs and any decision log entries from each change doc
- [x] AC-3: The summary is generated entirely from structured data in the wave record and change docs — no operator input required
- [x] AC-4: `wave_close` dry_run includes the summary in its output without writing to disk
- [x] AC-5: Existing `wave_close` behavior (status update, signoff recording) is not regressed

## Tasks

- [x] Read `wave_close` implementation in `server_impl.py` to understand the write sequence and where summary generation fits
- [x] Define the structured fields to read per change: title, completed ACs (`[x]`), progress log entries, decision log entries
- [x] Implement summary generation: short paragraph from wave title + completed change titles; per-change section from change doc fields
- [x] Insert summary write step into `wave_close` before the status checkpoint write
- [x] Update dry_run mode to include generated summary in response without writing
- [x] Write tests: verify summary is populated after close, verify placeholder is replaced, verify dry_run returns summary
- [x] Run full test suite; confirm no regressions

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Read wave_close + define field extraction | software-engineer | — | |
| Implement summary generation | software-engineer | Field extraction | Needs `framework_edit_allowed` gate |
| Insert into wave_close write sequence | software-engineer | Generation | |
| dry_run support | software-engineer | Write sequence | |
| Tests | software-engineer | All above | |
| Full test suite pass | qa-reviewer | Tests | |

## Serialization Points

- `framework_edit_allowed` gate: single open/close around all server_impl.py edits

## Affected Architecture Docs

N/A — change is confined to `wave_close` in `server_impl.py` and its tests. No boundary, flow, or architectural impact beyond the closure write path.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core deliverable |
| AC-2 | required | Per-change detail is the main value |
| AC-3 | required | Must not require operator intervention |
| AC-4 | important | Dry-run parity |
| AC-5 | required | No regression on existing close behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-21 | Change created | Operator requested during 12sq2 wave setup |
| 2026-05-21 | `_generate_wave_close_summary` + `_replace_wave_summary_section` added to server_impl.py | Reads H1, completed ACs, progress log, decision log per change; 1571 tests pass |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-21 | Structured field extraction only — no LLM inference | Keeps close deterministic and fast; LLM summarization is a future enhancement | LLM-based free-text summary |
| 2026-05-21 | Two-part format: short paragraph + per-change detail | Short paragraph gives the at-a-glance outcome; detail section preserves the adjustments and decisions that would otherwise be buried in change docs | Single flat summary only |

## Risks

| Risk | Mitigation |
| --- | --- |
| Change docs with sparse progress/decision logs produce thin summaries | Acceptable — the summary quality reflects the quality of the change doc; this is a signal to improve doc hygiene, not a bug |
| wave_close write sequence ordering — summary must precede status checkpoint | Implement and test write order explicitly |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
