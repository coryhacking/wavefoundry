# An Over-Cap Table Row Part Line-Wraps Into a Header-Only Chunk With No Source Line

Change ID: `1x81x-bug oversized-table-row-wrap-emits-header-only-chunk`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-06
Wave: 1xa00 table-chunk-source-coverage

## Rationale

Found while closing the delivery of wave `1x6ti`: the repository prose
coordinate census (`ChunkCoordinateContractTests.test_repository_prose_coordinate_census_reports_zero_wrong`
in `test_chunker.py`) reported two `empty` chunks, both the second row group
of a change doc's Decision Log table whose header and separator rows were
padded to about 800 characters and whose data rows each exceed the space left
under `MAX_DOC_CHUNK_CHARS`. The mechanism is in `chunker.py`.
`_decompose_oversized_table_chunk` emits one part per row group and, for
every part after the first, reproduces the prelude and the header as
generated context (line map `None`). When such a part is still over the cap
(one wide row alone with a wide header), `split_large_chunks` hands it to
`_line_wrap_chunk`, which treats the leading `None`-mapped lines as the
preamble; because that preamble exceeds half the cap, the helper drops the
preamble budget and windows the WHOLE text, generated lines included. The
first window then holds only the reproduced breadcrumb, header and separator:
no line of it maps to a source line, its coordinates fall back to the part's
row range, and the census cannot score it against the file. The chunk is
served with a section label and a line range that describe a row it does not
contain. A wave-`1x6ti` change doc hit this with two rows; any repository
whose markdown carries a wide table with long rows hits it the same way. The
census caught it (the `empty` verdict was added for exactly this class in
wave `1wpif`), which is why the wave narrowed its two tables' header rows
rather than editing the chunker outside its scope.

## Requirements

1. `_line_wrap_chunk` SHALL never emit a window whose every line is
   generated context (a `None` map entry) when the chunk carries a line
   map; such a window's lines are either carried as the preamble of the
   next window or dropped, and every emitted window SHALL contain at least
   one source-mapped line.
2. When the reproduced prelude-plus-header of a decomposed table part
   exceeds half the cap, `_decompose_oversized_table_chunk` SHALL compact
   the reproduced separator row (a `---` per column) and the header's cell
   padding before reproducing them, so a wide-but-short table no longer
   forces the row parts over the cap; the first part keeps the source text
   verbatim.
3. Every emitted table row group SHALL contain at least one complete data row together with its header and separator. A single row plus its headers may exceed the normal chunk-size limit; never character-split that row to enforce the limit (operator clarification, 2026-09-06).
4. The coordinate census in `test_chunker.py` SHALL gain a fixture with a
   wide padded table whose single rows exceed the remaining budget, pinned
   to `exact` or `superset` verdicts with zero `empty`, and the pre-repair
   shape SHALL be shown to produce the `empty` verdict (non-vacuity).

## Scope

**Problem statement:** a decomposed table part that is still over the cap
line-wraps into a first window made only of reproduced context, served with
a row's coordinates and no row.

**In scope:**

- The two helpers named above, their `split_large_chunks` dispatcher integration, and their tests.
- `CHUNKER_VERSION` moves if the emitted chunk set changes for any existing
  corpus (it does: the header-only window disappears and row windows
  change), with the standing re-chunk consequences disclosed.

**Out of scope:**

- Non-table line-wrap behaviour beyond generated-only filtering; the unmapped wrapper path stays byte-identical.
- The wave `1x6ti` change docs, already repaired by narrowing their headers.

## Design

Keep complete table rows with their header and separator. Greedy grouping still targets the normal cap, but a one-row group is indivisible even when it exceeds that cap. When an over-cap chunk contains a recognized pipe table, take the table route even if the table alone fits the cap (a large surrounding prelude must not split it). Remove the oversized-header fallback that sends a real table to line wrapping; the dispatcher must preserve decomposed table groups instead of re-wrapping them. Preserve first-part source text, existing prelude/postlude ownership, and absolute source maps. Test an oversized row, a header alone over the cap, and the standing real-world Decision Log fixture. Update `TableDecompositionTests.test_real_world_41k_decision_log`: replace its obsolete hard-cap and 70%-header assertions with canonical header, separator and at least one complete source row in every row-group chunk; reject residual `(part N/M)` row tails and permit over-cap indivisible row groups.

For non-table wrapping, filter all-generated windows only when a valid source line map exists, before computing part counts and IDs. Preserve every source-bearing window, including character-split pieces of one long source line. Cover leading, middle, trailing and entirely generated mapped text with a direct boundary fixture; the unmapped path must retain its current output.

Compact only the reproduced header of parts after the first, when that header exceeds half the cap. Preserve header labels, escaped pipes, and separator alignment markers; reduce cosmetic padding and separator hyphen runs without changing source-bearing first-part text. Existing conservative row grouping may remain unchanged while the compacted header fits below the cap. If the header remains at or above the cap after compaction, emit it once with every complete row in one table group; repeating an irreducible header per row would make output grow quadratically. A large prelude or postlude, or a genuinely long header, must not force table rows through wrapping. Apply the table contract to every recognized table run in a section, including tables that follow prose or an earlier table. Surrounding prose remains subject to the universal cap: keep it beside a table group only when the combined chunk fits, otherwise line-wrap it independently before, between, or after the intact table groups. Later tables receive deterministic table-qualified IDs. An indivisible complete row plus headers may exceed the cap; the irreducible-header fallback may contain multiple complete rows so the header appears once. The generated-window filter remains necessary for mapped non-table inputs and needs its own direct tests independent of the table route.

Use chunk_file with a wide padded Markdown table for the end-to-end coordinate oracle, plus mapped/unmapped wrapper controls and short-table preservation. Bump CHUNKER_VERSION from 41 to 42 and its current-version pin. This is an emission-shape migration: next index updates re-chunk every eligible file; with the model and walker unchanged, content-identical chunks reuse embeddings by hash and only new or changed text is embedded. Document that cost without rebuilding live indexes as readiness evidence.

## Acceptance Criteria

Required AC-4 regression evidence in `ChunkCoordinateContractTests`: `test_mapped_wrap_filters_generated_windows_before_numbering` covers leading, middle and trailing generated windows and contiguous labels; `test_all_generated_mapped_wrap_emits_nothing` covers the early return; `test_mapped_character_split_preserves_every_source_character` pins complete payload and unique IDs. These direct wrapper tests must fail with only the filter removed while compaction remains. `test_reproduced_header_compacts_without_rewriting_first_part` pins escaped pipes, alignment colons and verbatim first-part text; removing only compaction must fail it. `test_unmapped_large_preamble_wrap_keeps_legacy_output` pins legacy output. The public `test_wide_padded_table_has_no_generated_only_chunks` supplies AC-1/AC-2 evidence and requires headers plus complete rows; `test_table_row_and_headers_remain_intact_over_cap` must cover row-only and header-only overflow and fail if the dispatcher restores residual line wrapping or the decomposer restores oversized-header fallback, alongside the existing short-table/source-coordinate control. `test_irreducible_header_is_emitted_once_with_linear_output` grows header width and row count together, requires one header-bearing table group containing every complete row, and bounds emitted bytes to the source bytes. `test_long_titled_sections_reach_table_decomposition_before_line_windows` covers direct H2, H3, and mixed later-table forms beyond the 120-line boundary; the standing table-free oversized-section tests retain compatibility coverage. Inspect the same escaped/aligned fixture through `chunk_file` for end-to-end preservation.

- [x] AC-1: A wide padded table whose rows individually exceed the remaining budget chunks with zero `empty` census verdicts and every row's part carries that row's source line, complete row and headers together even when they exceed the normal size limit.
- [x] AC-2: The pre-repair helper, restored in a scratch copy or through a test double, produces the `empty` verdict on the same fixture.
- [x] AC-3: The repository prose coordinate census stays at zero `empty` and zero `wrong`.
- [x] AC-4: The change's own suites pass; the documents it edits validate; no failure elsewhere is attributable to it.

## Tasks

- [x] Red first: the wide-table census fixture, failing on the current chunker.
- [x] Skip or carry all-generated windows in `_line_wrap_chunk`; compact the reproduced header in `_decompose_oversized_table_chunk`; preserve indivisible table groups in the dispatcher; bump `CHUNKER_VERSION` with its pins.
- [x] Mutations in a scratch copy; record the table.
- [x] Docs: the table-decomposition and coordinate-contract passages of `docs/architecture/chunking-and-indexing-pipeline.md`; CHANGELOG under Unreleased.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                   |
| ---------- | ----------- | ---------- | --------------------------------------- |
| wrap       | implementer | —          | `_line_wrap_chunk` generated-window rule |
| header     | implementer | wrap       | Compact reproduced header.              |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `./CHANGELOG.md`
- `docs/architecture/performance-budget.md` (lint-bound version pin only)

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` (the record that owns
table decomposition and the coordinate contract) gains the generated-window
rule. No boundary change.

## AC Priority


| AC   | Priority | Rationale                                            |
| ---- | -------- | ---------------------------------------------------- |
| AC-1 | required | The defect itself.                                   |
| AC-2 | required | Non-vacuity of the fixture.                          |
| AC-3 | required | The standing census gate.                            |
| AC-4 | required | Standard delivery gate.                              |


## Progress Log

Observe (2026-09-06, readiness repair cycle 5): the refreshed red-team seat found that the first table captured every later table as postlude, so a 4,513-character row in table two still split into three fragments. The surrounding-content path now scans its block once, emits ordinary prose through mapped wrapping, and routes every later table independently; a public three-table regression keeps both later oversized rows complete with their own headers and deterministic unique IDs. Final configured framework run: 8,521 tests across 75 files in 200.697 seconds, three expected skips; `test_chunker.py` contributes 577 passing tests and the receipt is fresh.

Observe (2026-09-06, delivery repair cycle 6): fresh performance review found that an irreducible header at or above 2,000 characters was copied once per data row, producing 16,122,890 output characters from a 54,908-character public fixture (293.63×). The bounded fallback now emits that header once with every complete row in one table group. A public scaling regression grows header width and row count together and requires byte-exact single-copy table output. The configured framework runner passes 8,522 tests across 75 files in 192.077 seconds with three expected skips; `test_chunker.py` contributes 578 passing tests and the receipt is fresh.

Observe (2026-09-06, readiness repair cycle 6): the refreshed red-team and architecture seats independently found that the standard Markdown H2 path line-windowed a long table before universal table decomposition, leaving 122 of 240 rows without their header. Table-bearing oversized titled sections now bypass that upstream fixed-window branch and reach the existing table-aware splitter intact; direct H2, H3, and mixed later-table regressions cover the boundary while table-free sections retain their existing windows. The configured framework runner passes 8,523 tests across 75 files in 189.090 seconds with three expected skips; `test_chunker.py` contributes 579 passing tests and the receipt is fresh.

Observe (2026-09-06, delivery repair cycle 4): fresh code review found that routing every recognized table through decomposition made a 29-character table plus ordinary postlude emit one 7,566-character chunk. The repair now budgets table groups independently and splits oversized non-table prelude/postlude through the ordinary mapped wrapper; a public two-sided regression proves all chunks remain at or below 2,000 characters when the table unit itself fits, while the row/header unit stays intact. The configured framework runner passes 8,520 tests across 75 files in 188.196 seconds with three expected skips and writes a fresh green receipt; `test_chunker.py` contributes 576 passing tests.

Observe (2026-09-06, delivery repair cycle 4): corrected the stale current-version cell in `docs/architecture/chunking-and-indexing-pipeline.md` from `CHUNKER_VERSION` 41 to 42. The adjacent migration section already said 42; historical version references remain unchanged. Fresh QA, architecture, release and code-lane reverification follows against the frozen repaired packet.

Observe (2026-09-06, implementation complete): final `python3 .wavefoundry/framework/scripts/run_tests.py` passes 8,519 tests across 75 files in 206.101 seconds, with three expected skips; `test_chunker.py` contributes 575 passing tests. A fresh green framework receipt is recorded. Full docs validation and `git diff --check` pass. All ACs/tasks are complete. Delivery Review wave, closure and commit remain separate operator-directed steps.

Observe (2026-09-06, Level 1): full docs validation found the shared lint-bound version pin in `docs/architecture/performance-budget.md` still at 41. Synchronize that documentation-only pin to 42 and make the new Unreleased upgrade note the explicit current `CHUNKER_VERSION` claim; historical wave entries retain their original version facts. This is required propagation of the admitted version bump, with no code or behavioral scope expansion.

Observe (2026-09-06): seven new repository tests ran red before source edits (six failing methods, nine failure records including subcases; no errors/skips). After repair, all 24 table/coordinate tests pass, including the full repository prose census with zero empty/wrong. The real-world Decision Log changes from 31 chunks / six row-tail parts to 28 complete-row groups / zero row tails; largest group 2,710 characters. Four unmapped wrapper fixtures match their pre-repair serialized output exactly.

Mutation proof (all executed in memory; no source-file mutation): load original functions with AST from `git show 37311f29:.wavefoundry/framework/scripts/chunker.py`, replace only the named function on a fresh `load_chunker()` module, and run the listed `ChunkCoordinateContractTests` method. The last two cases remove the exact current early-return block or restore the finder argument directly. Every mutant fails; restored current code passes all seven new methods. No errors or skips.

| Mutant | Failing test | Observation |
| --- | --- | --- |
| Original `_line_wrap_chunk`, compaction retained | `test_mapped_wrap_filters_generated_windows_before_numbering`, `test_all_generated_mapped_wrap_emits_nothing`, `test_mapped_character_split_preserves_every_source_character` | Three methods fail independently of table compaction; four failure records. |
| Original `_decompose_oversized_table_chunk`, filter retained | `test_reproduced_header_compacts_without_rewriting_first_part` | One failure; generated header remains padded. |
| Original `split_large_chunks`, new helpers retained | `test_table_row_and_headers_remain_intact_over_cap` | All three boundary subcases fail; residual wrapping breaks row/header integrity. |
| Original decomposer, new dispatcher retained | `test_table_row_and_headers_remain_intact_over_cap` | Header-overflow and large-prelude subcases fail. |
| All three original functions | `test_wide_padded_table_has_no_generated_only_chunks` | Same public fixture returns two empty verdicts (4 exact, 1 superset, 2 empty), proving AC-2. |
| Delete only all-generated early return | `test_all_generated_mapped_wrap_emits_nothing` | Under-cap generated-only input fails while window filtering remains. |
| Restore finder argument `max_chars` instead of `0` | `test_table_row_and_headers_remain_intact_over_cap` | Small-table/large-prelude subcase fails with other repairs retained. |
| Delete only the under-cap decomposer early return | Scratch `UnderCapTableCompatibility.test_direct_decomposer_leaves_small_table_unchanged` | A three-line Name/Value header, separator and one data row at cap 2,000 returns None on current code; deleting only that return yields a group and fails the compatibility assertion. One test, zero errors/skips in each control. |

Gapfill: some fresh native readiness reviewers had no MCP code-navigation tools and reported bounded read-only shell fallback. Root implementation used MCP outlines and targeted helper/test reads before mechanical edits. One preliminary broad scratch run used system Python without tree-sitter grammars; configured-runtime execution resolved those environment failures. Final delivery evidence comes from repository tests against the actual edited files, not the scratch loader.

Thought (2026-09-06): implement in order: install failing regressions; repair recognized-table routing, copied-header compaction and mapped-window filtering; update version/docs; execute independent mutations and the repository census, then the full framework suite. One implementer owns all four review targets.


| Date       | Update                                                                                       | Evidence                                              |
| ---------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from the wave `1x6ti` delivery run: the full suite's coordinate census reported two `empty` chunks, both header-only windows of over-cap Decision Log row parts; mechanism traced to `_line_wrap_chunk` dropping the preamble budget and windowing generated lines. The wave repaired its own docs by narrowing the tables' header rows and left the chunker for this plan. | Full-suite log `full_suite_1x6ti_1.log` and the census probe in the session scratchpad. |


## Decision Log

Operator clarification (2026-09-06): keep a minimum of one complete data row with its headers in every table chunk, exceeding the normal size cap when necessary. This supersedes the former residual row-wrapping behavior and requires refreshed readiness before implementation.


| Date       | Decision                                                   | Reason                                                                                  | Alternatives                                                       |
| ---------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 2026-09-05 | Park as its own plan rather than repair inside wave `1x6ti`. | `chunker.py` is outside that wave's review targets and the fix moves `CHUNKER_VERSION`. | Repair in-wave: widens the wave's blast radius to a re-chunk of every corpus. |


## Risks


| Risk                                                        | Mitigation                                                     |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| The chunker bump re-chunks every eligible file; only new or changed chunk text needs embedding when the model and walker are unchanged. | Standing convention; disclosed in the CHANGELOG Upgrading note. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
