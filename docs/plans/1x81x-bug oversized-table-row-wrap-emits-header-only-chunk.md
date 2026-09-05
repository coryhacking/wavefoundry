# An Over-Cap Table Row Part Line-Wraps Into a Header-Only Chunk With No Source Line

Change ID: `1x81x-bug oversized-table-row-wrap-emits-header-only-chunk`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-05
Wave: TBD

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
3. The coordinate census in `test_chunker.py` SHALL gain a fixture with a
   wide padded table whose single rows exceed the remaining budget, pinned
   to `exact` or `superset` verdicts with zero `empty`, and the pre-repair
   shape SHALL be shown to produce the `empty` verdict (non-vacuity).

## Scope

**Problem statement:** a decomposed table part that is still over the cap
line-wraps into a first window made only of reproduced context, served with
a row's coordinates and no row.

**In scope:**

- The two helpers named above and their tests.
- `CHUNKER_VERSION` moves if the emitted chunk set changes for any existing
  corpus (it does: the header-only window disappears and row windows
  change), with the standing re-chunk consequences disclosed.

**Out of scope:**

- Any other line-wrap behaviour; the unmapped-chunk path stays byte-identical.
- The wave `1x6ti` change docs, already repaired by narrowing their headers.

## Acceptance Criteria

- [ ] AC-1: A wide padded table whose rows individually exceed the remaining budget chunks with zero `empty` census verdicts and every row's part carries that row's source line.
- [ ] AC-2: The pre-repair helper, restored in a scratch copy or through a test double, produces the `empty` verdict on the same fixture.
- [ ] AC-3: The repository prose coordinate census stays at zero `empty` and zero `wrong`.
- [ ] AC-4: The change's own suites pass; the documents it edits validate; no failure elsewhere is attributable to it.

## Tasks

- [ ] Red first: the wide-table census fixture, failing on the current chunker.
- [ ] Skip or carry all-generated windows in `_line_wrap_chunk`; compact the reproduced header in `_decompose_oversized_table_chunk`; bump `CHUNKER_VERSION` with its pins.
- [ ] Mutations in a scratch copy; record the table.
- [ ] Docs: the table-decomposition and coordinate-contract passages of `docs/architecture/chunking-and-indexing-pipeline.md`; CHANGELOG under Unreleased.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                   |
| ---------- | ----------- | ---------- | --------------------------------------- |
| wrap       | implementer | —          | `_line_wrap_chunk` generated-window rule |
| header     | implementer | wrap       | Compact reproduced header.              |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`

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


| Date       | Update                                                                                       | Evidence                                              |
| ---------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from the wave `1x6ti` delivery run: the full suite's coordinate census reported two `empty` chunks, both header-only windows of over-cap Decision Log row parts; mechanism traced to `_line_wrap_chunk` dropping the preamble budget and windowing generated lines. The wave repaired its own docs by narrowing the tables' header rows and left the chunker for this plan. | Full-suite log `full_suite_1x6ti_1.log` and the census probe in the session scratchpad. |


## Decision Log


| Date       | Decision                                                   | Reason                                                                                  | Alternatives                                                       |
| ---------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 2026-09-05 | Park as its own plan rather than repair inside wave `1x6ti`. | `chunker.py` is outside that wave's review targets and the fix moves `CHUNKER_VERSION`. | Repair in-wave: widens the wave's blast radius to a re-chunk of every corpus. |


## Risks


| Risk                                                        | Mitigation                                                     |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| The chunker bump forces a re-chunk and re-embed everywhere. | Standing convention; disclosed in the CHANGELOG Upgrading note. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
