# Closed review records are left alone

Change ID: `20wqa-enh closed-inline-review-records-left-alone`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-17
Wave: 20x1k distribution-review-and-read-tool-follow-ups

## Rationale

A downstream distribution (item K3 of its 2026-10-17 note) asked for a tool to convert the prose signoffs of wave records migrated from older releases into typed review events. The operator decided against conversion: those approvals happened under earlier rules, and converting them would mark them as passing gates they never went through. Closed records stay as they are and nothing should ask for conversion; open waves keep the current rules, which require real current reviews.

An investigation of the tree found that closed records with prose-only signoffs are already left alone. Docs-lint only validates review evidence when a record has a `review-evidence-source:` header, a malformed one, or an inline `review-evidence-protocol:` marker (`wave_lint_lib/wave_validators.check_wave_docs`). `check_closed_wave_requirements` checks no signoffs. Upgrade (`phase_review_evidence_sidecar_cleanup`) rewrites no wave record, and seed 160 says upgrade never rewrites closed waves. No recovery text tells an agent to convert prose to events.

One path does ask a closed record for migration: a closed wave that still carries the 1.13-era inline marker `review-evidence-protocol:` and no `review-evidence-source:` header fails docs-lint with `legacy inline review-evidence wave is no longer readable; migrate manually: ...` from `review_evidence.validate_external_review_evidence`. This change stops that for closed records.

## Requirements

1. **One shared predicate.** `review_evidence.py` gains `closed_legacy_inline_record(text) -> bool`. It is true only when all of these hold:
   - the predicate first normalises CRLF to LF, so a raw Windows record and the normalised text docs-lint reads give the same answer;
   - the record carries the inline `review-evidence-protocol:` marker anywhere in the record, the same check docs-lint and `_wave_uses_external_review_evidence` use;
   - `parse_review_evidence_source(text)` returns no source and no source errors;
   - the record's first `Status:` line, read with the server's own pattern (`^Status:\s+(\S+)`, first match only), has the exact lower-case value `closed` or `completed`.

   A `Status: Closed` or `Status:closed` variant is not a closed record for this purpose. The predicate does not require `Completed at` or the `**current state:** completed.` line: in this repository none of the 431 closed records carries the current-state line and only 4 carry `Completed at`, so either requirement would match no real record.
2. **Docs-lint.** In `wave_lint_lib/wave_validators.check_wave_docs`, a record for which the predicate is true is not passed to `validate_external_review_evidence`, so docs-lint reports no `review evidence:` error for it. Every other wave-record check still runs on it.
3. **Wave resource.** In `server_impl._validated_wave_markdown`, which serves the `wavefoundry://wave/{wave_id}` resource, a record for which the predicate is true is served as its raw text, as a prose-only record is today, instead of the "Wave Review Evidence Unavailable" page with the migration text.
4. **Unchanged:**
   - An open inline-marker wave still fails with `migrate manually`.
   - Any record with a `review-evidence-source:` header, closed or open, is still validated, including its projection-staleness checks.
   - A malformed source header still fails, even on a closed record that also carries the inline marker.
   - Prose-only records stay unvalidated.
   - `validate_external_review_evidence`, `lifecycle_gate_support._wave_uses_external_review_evidence` and the close, review, prepare, approval and reopen gates do not change. Re-running close or review on an already closed wave is out of scope. Reopening a closed inline-marker wave makes it open, so the open-wave rule applies again.
5. **Seed 209.** In the "Legacy review migration is deliberate and operator-directed" paragraph, the clause on old inline typed records ("follow their separate manual migration diagnostic") applies to open or reopened waves. One sentence is added: closed wave records, including those with prose signoffs or a retired inline marker, are historical records left as they are; they need no migration, and their signoffs are not converted into events. Edited under `seed_edit_allowed`.
6. **Platforms.** Behaviour is identical on Windows, macOS, Linux and WSL2. The predicate reads record text already normalised by the existing readers, with no filesystem or platform-specific step.

## Scope

**Problem statement:** a closed wave carrying the retired inline marker is the one historical record that tooling still asks to migrate, in docs-lint and in the wave resource.

**In scope:** Requirements 1 to 6 and their tests.

**Out of scope:**
- Any conversion tool or `wf_review_event` mode.
- What re-running `wf_close_wave` or `wf_review_wave` on an already closed wave reports. Nothing calls these automatically.
- The shared gate classifier and open-wave rules.

## Acceptance Criteria

- [x] AC-1: Docs-lint runs on a temporary docs tree, with fixtures built through the existing `WAVE_DOC_PATH` and `copy_fixture` helpers. These cases pass, with no `review evidence:` error:
  1. a closed (`Status: closed`) inline-marker record without a source header;
  1. a completed (`Status: completed`) inline-marker record;
  1. the closed record with CRLF line endings, through both docs-lint and the predicate called on the raw text.

  These cases fail with `migrate manually`:
  1. the same record with `Status: implementing`;
  1. the same record with `Status: Closed`;
  1. a record whose first `Status:` line says `implementing` and a later line says `Status: closed`.

  These cases keep their existing errors:
  1. a closed inline-marker record with a malformed `review-evidence-source:` header still reports the malformed-header error;
  1. a closed declared record (`review-evidence-source: events.jsonl`) with a stale Finding Synthesis still fails with `review evidence projection is stale`.

  In the passing closed inline-marker record, one other wave-record defect, a missing Objective, still reports its own error. The existing `test_docs_lint` inline-marker rejection still passes.
- [x] AC-2: The `wavefoundry://wave/{id}` resource serves a closed inline-marker record's raw text. An open one still serves the Unavailable page with the migration text.
- [x] AC-3: Seed 209 carries the scoped clause and the sentence, and full docs validation passes.
- [x] AC-4: Focused files pass, and the wave's single final whole-suite run passes with a fresh green receipt.

## Tasks

- [x] Add `closed_legacy_inline_record` and use it in `check_wave_docs` and `_validated_wave_markdown`.
- [x] Add the AC-1 tests to `tests/test_docs_lint.py` and the AC-2 test to the wave-resource tests.
- [x] Edit seed 209 under the seed gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| predicate-and-readers | implementer | none | Requirements 1 to 4 |
| seed | implementer | none | Requirement 5 |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`

## Affected Architecture Docs

N/A: one lint condition and one guidance sentence, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The lint change and each clause of the predicate. |
| AC-2 | required | The wave resource is a normal reader of closed records. |
| AC-3 | required | Agents read the seed; it must say closed records need no migration. |
| AC-4 | required | Receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-17 | Planned from a code census of every path that reads closed records' review sections. | census by investigator (session) |
| 2026-10-17 | Implemented. `review_evidence.closed_legacy_inline_record` added and exported. It normalises CRLF, matches the inline marker anywhere in the record (the same regex docs-lint and the gate classifier use), refuses any source header or source error, and reads only the first `Status:` line with the server's `^Status:\s+(\S+)`. It is used in `check_wave_docs` and in `server_impl._validated_wave_markdown`, and the gate classifier is unchanged. Seed 209 now carries the closed-records sentence, and the inline-records clause is scoped to open or reopened waves. Tests: `test_docs_lint.ClosedInlineRecordLintTests` (6 tests: closed and completed records pass with exit 0; a CRLF record passes through both docs-lint and the predicate on raw text; implementing, `Closed`, and implementing-then-closed records still fail with `migrate manually`; a wrong source and a duplicated source keep their errors; a missing Objective still reports; a closed declared record with a stale Finding Synthesis fails), and `test_server_tools.McpResourceReadTests.test_wave_resource_serves_closed_inline_record_as_written`. Scratch mutants: source-error clause, casefolded status, any-Status-line, lint guard and resource guard are all killed; the source-error mutant was killed only after the duplicated-source case was added. The no-CRLF-normalisation mutant is equivalent, because the status pattern stops at `\r`; normalisation stays as cheap insurance. Gapfill: shell edits and scratch runs for anchored edits and mutation probes. | scratchpad mut20x1k.log |
| 2026-10-17 | Delivery repair cycle 1. DEL-1 (security): swapping a closed declared record's header for the inline marker turned off its projection and ledger checks. The predicate now takes the record path and refuses any record with a sibling `events.jsonl` entry. A retired inline record has none, and the fixture's empty ledger was enough to defeat a size-based rule. DEL-3 (QA, code): the census failed on an unreasoned declaration literal, and my claim that the no-CRLF mutant was equivalent was wrong, because on raw CRLF a valid source header parses as absent. `ClosedInlineRecordLintTests` now has 10 tests: upper-case marker; CRLF with a source header; `Status:closed`, `closed-ish`, a prefixed `Status:` line and no `Status:` line; marker plus valid source; header-swapped records with a stale or malformed ledger. Every literal has a `declaration-check:` reason. Scratch mutants: 12 of 12 killed (DEL-1 ledger check, P1 to P10, lint guard). Focused `test_docs_lint` 350, `test_declared_wave_fixtures` 13 and `test_core_read_hook` 5 pass. | scratchpad mut20x1k-r1.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-17 | No conversion tool; leave closed records alone. | Operator: converted signoffs would claim gates they never passed. | A preview-and-write conversion tool, as requested. |
| 2026-10-17 | Do not add an early return to `wf_close_wave` for already closed waves. | Nothing calls it on closed waves automatically; smaller work wins. | Short-circuit re-close and re-review on closed waves. |
| 2026-10-17 | Readiness folded in: the predicate needs the exact case-sensitive status line (security; the current-state line was dropped because no real closed record carries it), the wave resource uses it too (code), and AC-1 covers each clause of the predicate (QA). The seed 209 inline-records clause is scoped to open waves (docs-contract). | Readiness reviewers. | Put the guard in the shared gate classifier; not taken, because that would change the close and review gates. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A wave marked closed by hand to dodge the check. | The predicate requires the exact lower-case status line the server reads; it silences only the migration request on an undeclared inline-marker record, and closing is operator-owned and runs every gate. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
