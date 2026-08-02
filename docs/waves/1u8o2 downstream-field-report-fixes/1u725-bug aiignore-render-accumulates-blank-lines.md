# .aiignore Render Accumulates Two Blank Lines Per Render, Unbounded

Change ID: `1u725-bug aiignore-render-accumulates-blank-lines`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: `1u8o2 downstream-field-report-fixes`

## Rationale

Downstream field report (Solaris, 2026-08-01), mechanism verified against this tree:
`render_platform_surfaces.render_aiignore` rebuilds `.aiignore` as `index_block` plus a `""`
separator plus `rest`, where `rest` is every line `_is_index_meta_line` does not recognize. The
recognizer matches only the six non-blank members of the index block; it does not recognize the
blank separator inside the block nor the `""` the function itself appends. Both survive the filter
and are inherited into the FRONT of `rest`; the only blank-stripping loop pops from the END. Net:
plus two blank lines per render whenever any project-owned pattern trails the index block, forever.

Field evidence: one repository's committed `.aiignore` grew from 0 to 189 blank lines around 7
content lines over four months (per-render rate verified by the reporter with a 5-render
reproduction: 3, 5, 7, 9, 11 blanks). The bug hides when nothing sits below the index block,
because the trailing pop then drains the orphaned separator and the function is idempotent; any
legitimately owned trailing pattern activates it.

## Requirements

1. `render_aiignore` is idempotent for every input: rendering an already-rendered file of ANY
   composition (index block only; index block plus project patterns; project patterns containing
   intentional interior blank lines) produces byte-identical output.
2. The fix must not destroy project-owned content: intentional blank lines INSIDE the project-owned
   region are preserved. (The field report's suggested fix, treating all blank lines as index-meta,
   would strip interior separators from project content; a front-stripping pass bounded to the
   block boundary, or absorbing exactly the block-adjacent separators, avoids that. Choose at
   implementation and record the choice.)
3. Existing accumulated blanks self-heal: rendering a file that already carries the accumulated
   head-of-rest blank run collapses it to the canonical single separator in one render.
4. A regression test drives the exact field shape (index block, then a trailing project pattern)
   through at least three consecutive renders and asserts byte-stability after the first. The
   stability assertion alone is satisfiable by a blank-eating fix (it converges by render two), so
   the test also asserts EXACT expected content on the FIRST render for a fixture whose
   project-owned region contains a blank line BETWEEN two patterns, proving the interior blank
   survived (interior, never trailing: the final `rstrip()` legitimately collapses tail blanks).
5. Scope note, verified at prepare: `render_aiignore` is the SOLE writer of `.aiignore` in the
   tree (one definition, write at `render_platform_surfaces.py:1910`; sole call site at `:2170`,
   executed on the junie platform pass; the indexer only reads it; no seed instructs manual
   appends). The fix surface is complete at this one function.
6. Self-heal residual, recorded: a user's INTENTIONAL blank run at the very head of the
   project-owned region is indistinguishable from accumulated debris and collapses to the single
   canonical separator. Accepted; the requirement 2 decision record states it.

## Scope

**Problem statement:** every render of `.aiignore` in a repository with any project-owned trailing
pattern adds two blank lines to a committed file, unbounded.

**In scope:** `render_platform_surfaces.render_aiignore` and `_is_index_meta_line`; regression
tests in `test_render_platform_surfaces.py`.

**Out of scope:** the content of the index block; other rendered surfaces.

## Acceptance Criteria

- [ ] AC-1: Three consecutive renders over a file with a trailing project pattern are byte-stable
  after the first render, AND the first render's output equals an exact expected byte string in
  which an interior project-owned blank line (placed between two patterns) survives.
- [ ] AC-2: A file carrying an accumulated blank run (fixture reproducing the field shape)
  collapses to canonical form in one render.
- [ ] AC-3: The index-block-only case remains byte-stable (the previously-idempotent path does not
  regress).
- [ ] AC-4: Full framework suite passes.

## Tasks

- [ ] Reproduce the plus-two-per-render growth with a failing test before fixing
- [ ] Fix the separator handling in `render_aiignore` (record the chosen mechanism and why it
      preserves interior blanks)
- [ ] Add the three-render stability, self-heal, and index-only regression tests
- [ ] Full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `render_platform_surfaces.py` (shared with any concurrent renderer work)

## Affected Architecture Docs

N/A: single-function repair inside one renderer with no boundary, flow, or contract impact.
CHANGELOG `### Fixed` bullet at the release that ships it.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | TBD      |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-01 | Filed from the Solaris downstream defect report; mechanism verified against this tree (`_is_index_meta_line` matches no blank line; trailing-only pop) before filing. | Field report 2026-08-01; `render_platform_surfaces.py` `render_aiignore` |
| 2026-08-01 | Prepare cycle verified the mechanism by EXECUTION: five consecutive renders of the field shape grew blanks 4, 6, 8, 10, 12 (exactly plus two per render, accumulating at the front of the project region) while interior project-owned separators were preserved and the index-block-only shape stayed byte-stable, confirming both the defect and requirement 2's trap. Sole-writer census confirmed; requirements 4 to 6 folded from the lane findings (exact-content first-render assertion; writer census; head-blank self-heal residual). | Executed probe probe_a_aiignore.py, scratchpad 2026-08-01 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A fix that eats all blank lines destroys intentional project-owned separators | Requirement 2 names the trap and demands the choice be recorded; AC-1 asserts interior blanks survive |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
