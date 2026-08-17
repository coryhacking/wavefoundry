# Reconciliation Scan Flags the Archive Row Seed-230 Tells the Repo to Write

Change ID: `1vk4b-bug reconcile-scan-flags-mandated-resolved-closed-archive`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-08-16
Wave: 1vk4c field-feedback-1p17p1-seed-scan-gaps

## Rationale

Field feedback from a target repository (Java agent repo, two consecutive upgrades `1.16.4 -> 1.17.0 -> 1.17.1`, `reconciliation_total: 1` both times, same finding). Seed-230 (`230-author-spec`, "6. Resolve missing-docs entries") instructs the agent to move a resolved row into a `## Resolved / closed` table in `docs/missing-docs.md` with a dated resolution note; seed-220 names that file the canonical wave-context path. When the resolved component is a later-retired surface (`docs/agents/journals/`, retired by `1t9wa`), the note necessarily names it, and `reconcile_scan.py`'s retired-content pattern for `docs/agents/journals…` (`_RETIRED_CONTENT_PATTERNS`, wave `1v4mv`) reports it on every upgrade. One framework component's prescribed output is another's false positive, and the scanner's own 1v7a1 comment block already names this collision as the reason the disposition store exists.

Verified against the tree: the scanner's exclusions are path-shaped only (`EXCLUDED_DIRS`, `EXCLUDED_BASENAMES`, `_EXCLUDED_PATH_COMPONENTS = ("journals", "snapshots")`); the only line-scoped exemption on the journals pattern is `_LIVE_JOURNAL_MIGRATION`; `disposition_key` (1v7a1) hashes file + surface + the MATCHED TEXT, where the matched text is the regex match (`docs/agents/journals/`), not the row. Executed at readiness (red-team seat): a `historical-record` disposition for the archive row therefore survives any reword of the note, and it also silences the same path in the live High table of the same file, because both hits share the key. So the field stopgap over-suppresses in exactly the direction memory `1u43m` warns about; the disposition store is the wrong tool here for that reason, not because it is fragile. `load_dispositions` is fail-open. The heading itself is prescribed only by seed-230 §6 as a move destination (no seed templates it; this repository's own `docs/missing-docs.md` has `## Active Gaps` and `## Watchpoints` only), and seed-150 (`150-refresh-wavefoundry`, missing-docs sweep) and seed-160 (post-upgrade checklist) still say resolved items are removed, so the seeds disagree with each other about the archive; this change reconciles them. The flagged row in the field carries the correct forward pointer ("the journal system has since been retired; durable lessons are captured as typed memory records under `docs/agents/memory/`"), i.e. it is the historical record seed-160 and seed-220 protect ("retiring a file removes the file, not the historical record of it"). The repo can therefore only silence the finding by falsifying history (deleting the record, which seed-150/160 currently sanction and seed-160/220 forbid) or by a disposition that over-suppresses the live tables. That is a framework integration gap, not a scanner bug and not a repo bug.

## Requirements

1. `reconcile_scan.py` gains a section-aware exclusion keyed on an exact allowlist of framework-mandated archive sections, initially one entry: file `docs/missing-docs.md` (exact POSIX repo-relative path) and ATX H2 heading whose text is `Resolved / closed`. Heading contract: a line matching `^ {0,3}##[ \t]+<text>[ \t#]*$` with `\r` stripped, text compared after trim and case-fold (not a regex, not a substring); setext underlines and `##Resolved / closed` without a space are not headings; lines inside ``` or ~~~ fences neither open nor close a span; the span runs to the next ATX H1 or H2 or EOF, so nested H3/H4 stay inside it. Within the span, only TABLE ROWS (lines whose first non-space character is `|`) are exempt, because seed-230 mandates a table; prose parked under the heading still reports. The exemption is structural and pattern-agnostic: it applies to every `StaleReference` producer in `scan_repo` (literal wrapper paths, retired-content patterns, stale prompt extensions, renamed MCP tools) for hits inside an exempt row, and lives in `scan_repo` beside `is_excluded`, with the 1v7a1 comment amended to say path and archive exclusions are structural while dispositions stay at the channel boundary.
2. The exclusion is scoped: the same retired reference elsewhere in `docs/missing-docs.md` (the High / Medium / Low priority tables, or any other section) is still reported; no other document or heading gains section-based suppression; a heading that is not exactly the allowlisted text (renamed, demoted to H3, missing) restores reporting. Fail toward reporting, never toward silence, consistent with memory `1u43m` (misrouting toward "no edit needed" is the dangerous direction).
3. Existing `docs/reconcile-dispositions.json` entries keep working unchanged (`disposition_key`, `is_dispositioned`, fail-open `load_dispositions`); the archive exclusion needs no disposition entry. A stopgap disposition recorded for the archive row keeps suppressing every same-matched-text hit in that file (existing 1v7a1 property, verified), so the CHANGELOG bullet tells operators to drop such stopgaps, and a test shows the live-table finding reappears once the entry is removed.
4. Cross-reference and seed reconciliation, one `seed_edit_allowed` window: a comment beside the allowlist constant names seed-230 §6 as the source of the heading; seed-230 §6 gains one sentence stating the heading is exact and that the reconciliation scan treats table rows under it as historical record (worded as a constraint on the heading, not as an escape hatch); seed-150's (`150-refresh-wavefoundry`) missing-docs sweep sentence ("have since been documented and should be removed") and seed-160's checklist line ("resolved items are removed") become "removed, or moved to the `## Resolved / closed` table per seed-230 §6". No rendered `docs/prompts/` mirror exists for seed-230 (verified at plan time); seed-160's rendered surface `docs/prompts/upgrade-wavefoundry.prompt.md` does not carry that checklist line (verified), so no mirror edit is required.
5. Executed field reproduction: a fixture `docs/missing-docs.md` with the archive row (as in the field, under `## Resolved / closed`) and the same path in a priority table yields findings only on the priority-table line. Readiness probe on the current tree: both lines report today (lines 11 and 23 in the seat's fixture), and an archive row that also names a literal `.wavefoundry/bin/docs-lint` reports too, which is why requirement 1 is pattern-agnostic.

## Scope

**Problem statement:** the scanner has no intra-file granularity, so a file that is mixed live guidance plus a framework-mandated archive is scanned uniformly as live guidance.

**In scope:**

- H2-span computation for Markdown files in `scan_repo` and the exact allowlist constant.
- Tests in `test_reconcile_scan.py`: archive row silent, priority-table row reported, disposition path untouched, no implicit suppression elsewhere (same heading in another file, H3, renamed heading), field reproduction fixture.
- Seed-230 §6 cross-reference sentence; seed-150 and seed-160 "removed" wording reconciled with seed-230; no rendered mirror exists (verified).
- CHANGELOG bullet naming the exact (file, heading) pair, the table-row scope, and the instruction to drop stopgap dispositions.

**Out of scope:**

- Whole-file exclusion of `docs/missing-docs.md` (would silence the open-gap tables where a stale reference is a genuine finding).
- Any heading heuristic (`/resolved|closed|historical/i` anywhere): reintroduces over-suppression; the allowlist is explicit and grows only with a specific framework-prescribed archive heading.
- Widening the journals pattern's line-scoped `exempt` to lines that say "retired": keys on incidental agent-written wording, decays like a disposition.
- Changing `disposition_key` semantics.

## Acceptance Criteria

- [x] AC-1: A retired-surface reference in a table row under `## Resolved / closed` in `docs/missing-docs.md` produces no finding, with no disposition entry present, for every producer (a row carrying `docs/agents/journals/`, a literal `.wavefoundry/bin/docs-lint`, an old MCP tool name, and a stale `.md` prompt reference is silent).
- [x] AC-2: The same strings in that file's priority tables, in a section with any other heading, and in a prose paragraph under the archive heading still produce findings, and the field fixture (archive row plus priority-table row) yields findings only on the priority-table line.
- [x] AC-3: Pre-existing `docs/reconcile-dispositions.json` entries continue to be honored and `load_dispositions` stays fail-open; a test shows a stopgap disposition for the archive row still suppresses the live-table hit with the same matched text (documented 1v7a1 property) and that the live-table finding reappears once the entry is removed.
- [x] AC-4: No other document or shape gains suppression: the identical heading in another Markdown file, an H3 `### Resolved / closed`, a renamed heading, a setext heading, `##Resolved / closed` without a space, a `## Resolved / closed` line inside a fenced code block, and a `.py`/`.json` fixture containing the heading text plus a retired reference all report; an H1 terminates the span. The allowlist is one constant with the (file, heading) pair.
- [x] AC-5: Seed-230 §6 and the scanner's archive allowlist cross-reference each other (the allowlist comment cites seed-230 §6; the seed names the reconciliation scan's archive allowlist); seed-150 and seed-160 no longer say resolved rows are simply removed; `CHANGELOG.md` carries a bullet naming the exact (file, heading) pair, the table-row scope, and the stopgap-disposition cleanup; docs-lint clean; the full framework suite passes.

## Tasks

- [x] `reconcile_scan.py`: `_ARCHIVE_SECTIONS` allowlist constant; `_archive_row_spans(text, rel)` helper (ATX H2 spans per the contract, fence-aware, table rows only); drop matches inside those spans for every producer in `scan_repo`; amend the 1v7a1 comment.
- [x] Tests: `ArchiveSectionExclusionTests` covering AC-1 to AC-4 plus the field reproduction and the disposition interaction, with executed known-bads (allowlist emptied -> archive row reports; heading renamed -> reports; fenced heading -> reports; prose under heading -> reports).
- [x] Seed-230 §6 sentence, seed-150 and seed-160 "removed" reconciliation, under one `seed_edit_allowed` window.
- [x] CHANGELOG bullet (advisory scan channel; operators who recorded a stopgap disposition for the archive row must drop it, because it also suppresses live-table hits).
- [x] docs-lint; full suite; record results.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Scanner exclusion + tests | implementer | — | `reconcile_scan.py`, `test_reconcile_scan.py`; memory `1u43m` applies (vary the LOCATION in the fixture, not just the string). |
| Seed-230 cross-reference | implementer | — | Under `seed_edit_allowed`. |
| Verification | qa-reviewer | Both | Known-bads executed; full suite. |

## Serialization Points

- `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/seeds/230-author-spec.prompt.md`, `.wavefoundry/framework/seeds/150-refresh-wavefoundry.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A: one scanner exclusion rule inside an existing module and one seed sentence; no boundary, flow, or verification-architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect. |
| AC-2 | required | The scoping that keeps the channel honest. |
| AC-3 | required | 1v7a1 behavior must not regress. |
| AC-4 | required | Over-suppression is the dangerous direction for this file (memory `1u43m`). |
| AC-5 | important | The invisible coupling is why this shipped. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-16 | Planned from the Aceiss field report (two upgrades, same single finding). Every claim re-verified against the tree: seed-230 §6 heading and instruction, seed-220 canonical path, path-shaped exclusions, `_LIVE_JOURNAL_MIGRATION` as the only journals exemption, `disposition_key` shape and fail-open store, the 1v7a1 comment naming the collision. Section-aware allowlist chosen over a line-scoped wording exemption because seed-230 mandates the heading but not the note's wording. | `code_read`/`code_keyword` over `reconcile_scan.py`; seeds 230, 220; field report 2026-08-16 |
| 2026-08-16 | Readiness council (red-team fixed seat, docs-contract rotating seat, code and qa readiness lanes) corrected the plan: disposition semantics restated from an executed probe (matched-text key; over-suppression of the live table), table-row scope, pattern-agnostic exemption, pinned heading contract, seed-150/160 reconciliation, CHANGELOG AC, concrete non-Markdown control, no rendered mirror for seed-230. | council seat returns 2026-08-16; field-fixture scan output (lines 11 and 23 report today) |
| 2026-08-16 | Implemented. `reconcile_scan.py`: `_ARCHIVE_SECTIONS = (("docs/missing-docs.md", "resolved / closed"),)`, `_ATX_HEADING_RE`, `_FENCE_RE`, `_archive_row_spans(text, rel)` (ATX H2 spans, fence-aware, next H1/H2 or EOF ends the span, nested H3 stays inside, table rows only, `\\r` stripped), and an `_archived(m)` predicate applied to every producer in `scan_repo` (literal wrapper paths, retired-content, stale prompt extension, qualified and bare tool patterns); 1v7a1 comment amended (dispositions at the channel boundary; structural exclusions in `scan_repo`). Tests: `ArchiveSectionExclusionTests` (6): every producer silent in an archive row; same strings report in a priority table, in prose under the heading, and under another heading; the field fixture reports only the High-table row; a stopgap disposition suppresses the live hit until removed and the store stays fail-open; the shape matrix (other file, H3, renamed heading, setext, `##` without a space, fenced heading, H1 termination, exact text not substring, `.py`/`.json` fixtures) all report; helper contract incl. CRLF and closing hashes. Executed mutants in scratch (allowlist emptied, substring heading match, fences ignored, whole span exempt, level check dropped, literal producer not exempt): each fails the intended tests and passes on restore. Seeds under one `seed_edit_allowed` window: seed-230 §6 names the exact heading and the scanner allowlist; seed-150 and seed-160 say removed or moved per seed-230 §6. CHANGELOG bullet added (exact heading, table-row scope, drop stopgap dispositions). `test_reconcile_scan` 48 OK; targeted seed-census files 1166 OK; docs-lint ok. Gapfill: none needed, discovery ran through `code_read`/`code_keyword`. | `tests.test_reconcile_scan.ArchiveSectionExclusionTests`; scratch `mut-1vk4b` |
| 2026-08-16 | Full framework suite after implementation: 7267 tests across 63 files OK (`suite-1vk4c.log`). Delivery review (three fresh lanes) approved the mechanism and returned one aggregated low finding (`archive-exclusion-hardening-and-suite-evidence`), repaired: fence bookkeeping now tracks (char, length) and closes only on the same character with a run at least as long as the opener (a ``` line inside a ```` block no longer closes it; `~~~` inside a ``` block is content); an empty ATX heading (`##`) terminates a span; tests add the mixed-marker fence, the 4-backtick fence, the empty-heading terminator, an indented table row, byte-equality of the archive-row and live-hit disposition keys, and end-to-end reappearance after a corrupt store; the previously surviving mutants (any-marker fence close, lstrip dropped, empty heading ignored) now fail their tests. Prose: seed-230 §6 names the archive allowlist without the private constant and states prose under the heading still scans; seed-160 qualified to the canonical `docs/missing-docs.md` (the legacy `docs/gaps/` path gets no exemption, consolidate per seed-220); CHANGELOG says the key hashes the matched text (here the retired path). `test_reconcile_scan` 48 OK. | typed ledger; scratch `mut-1vk4b2` |
| 2026-08-16 | Post-repair full framework suite (after the delivery hardening): 7267 tests across 63 files OK (`suite-1vk4c-2.log`); reverifier and delivery council APPROVE. | `suite-1vk4c-2.log`; reverify-1vk4c return |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-16 | Readiness council corrections adopted: exempt TABLE ROWS under the heading, not the whole span (seed-230 mandates a table; parked prose still reports); apply to every producer; pin the ATX/fence/EOF contract; keep the exclusion structural in `scan_repo`; reconcile seed-150/160 wording; make dropping the stopgap disposition an operator step. | Red-team seat executed the field fixture and showed a disposition on the archive row also silences the live High-table hit (same matched text), which is the dangerous direction; the whole-span design leaves a park-live-prose vector; the seeds disagree about removal vs archive. | Whole-span exemption (rejected: gameable, no cost saving); channel-boundary placement like 1v7a1 (rejected: this is structural like path exclusions, and scan_repo already applies those). |
| 2026-08-16 | Section-aware exclusion keyed on an exact (file, H2 heading) allowlist, initially only `docs/missing-docs.md` / `Resolved / closed`. | The framework mandates that exact heading, so the signal is structural (like the `journals`/`snapshots` path components), it fails toward reporting when the heading changes, and it removes the class at the source without touching the disposition store. | Whole-file exclusion (rejected: silences live gap tables). Heading heuristic across all docs (rejected: over-suppression through the back door). Line-scoped wording exemption (rejected: keys on incidental prose). Per-repo dispositions only (rejected: recurring per-repo chore for a framework-caused condition, invalidated by any reword). |

## Risks

| Risk | Mitigation |
| --- | --- |
| The allowlist quietly grows into a general suppression mechanism. | One constant, exact pairs only, a test asserting the identical heading elsewhere still reports; each addition needs a seed that mandates the heading. |
| A repo's `missing-docs.md` uses a slightly different heading and keeps getting the finding. | Fail-toward-reporting is the intended direction; the CHANGELOG bullet names the exact heading; seed-230 keeps the heading verbatim. |
| Live content parked as a table row under the archive heading is silenced. | Accepted residual: table-row scope narrows it to a deliberate act; the seed-230 sentence is worded as a heading constraint, not an exemption recipe; the open-gap tables above still report. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
