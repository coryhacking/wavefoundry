# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-27

## Current State

Wave `1to78 preship-events-authority-hardening` is **CLOSED** (2026-07-27), typed operator
approval recorded in its ledger, close gate returned zero diagnostics, lint clean, no
confirmed-secret reminders. Nothing is committed yet: the working tree carries 1to78's full
implementation plus the follow-up work below.

## Operator Waiver (named scope)

The operator explicitly waived the stage gate for one named scope on 2026-07-27: **follow-up FU4
from wave 1to78**, the content-driven wave-folder role predicate. No change doc, wave admission, or
Prepare pass was run for it. The waiver covers only that predicate split and its tests; nothing
else was edited under it. Recorded here per the AGENTS.md waiver route.

## FU4: landed

`is_canonical_wave_events_path` in `review_evidence.py` decided the wave-folder role (and therefore
the indexer's retrieval exclusion) by folder-name shape. Renaming a wave directory made that wave's
raw ledger index-eligible while the wave stayed fully live, the same defect class DF1 fixed on the
lint side. The role is now decided by position: any direct child directory of `docs/waves/` holding
the fixed sibling basename. Depth and basename bounds are unchanged.

The surviving name-shape test is a new `is_id_shaped_wave_dir_name`, documented as a lint MESSAGE
hint that decides nothing, split into its own symbol precisely so the shape cannot be re-borrowed
as a role test. `wave_lint_lib/wave_validators.py` now binds only the hint and holds no role
predicate at all, since it enumerates the role itself and a second copy could drift.

Evidence: both new tests proven red first (`AttributeError` on the missing hint symbol; `False is
not true` on the renamed folder), then green. Four existing controls that encoded the old
name-driven semantics were repointed at the depth bound with the reason stated inline, not deleted.
Suites: test_indexer, test_docs_lint 887, test_review_evidence, residue census, all OK; repo
docs-lint ok; `git diff --check` clean.

## FU5: withdrawn, not a defect

The recorded follow-up claimed `_resolve_wave_md_matches` resolves waves by id-shaped naming,
leaving a renamed wave invisible to id-based lookup. It does not. It globs `*/wave.md` and
prefix-matches the DECLARED `wave-id` from the parsed record, with the directory name only as an
alternative, and `_token_matches_id` imposes no shape constraint. A hermetic probe resolved all
four rename spellings to one correct match. Lifecycle lookup and the orphan lint were both already
content-driven; the indexer predicate was the only name-driven one, which is what FU4 closed.

## Also landed this pass

- Wave `1tsyx review-lifecycle-simplification` (planned): FU1 named into AC-2 plus the AC-11
  census sweep (typed Gate 1 activation read), FU2 named into AC-1 with an AC-7 fixture
  (approval phase-currency). FU3, the Participants lane-roster scaffold, deliberately NOT folded
  in: Requirement 5 makes lane selection risk-derived and may delete the hand-authored roster.
- 1tsyx stale blocker cleared: its watchpoint and Session Handoff still said 1to78 was the only
  OPEN wave and blocked it.
- Repo memory `1trcp-mem` updated: it still said the name-driven indexer exclusion was an open
  follow-up.
- A residue-census failure was found and fixed in this handoff document itself: the previous
  version named the deleted prose state-line writer verbatim, and the census forbids that token in
  live surfaces. Worth knowing that prose in a live doc can trip the census.

## Next

- Full canonical suite is the last outstanding verification for FU4.
- Commit is operator-owned: nothing has been committed, diff plus a suggested message on request.
- The 1.15 cutover still REQUIRES a full restart of every attached MCP or agent host after commit;
  the live server is running pre-change code.
- Next release is 1.15.0 folding 1tomw plus 1to78; CHANGELOG section is ready.

## Open operator decisions (not scheduled)

- FU3 lane-roster scaffold, pending the 1tsyx roster decision.
- Whether to note the FU5 withdrawal on 1to78's sealed record, or leave it as history. The
  correction currently lives in this handoff and in agent memory only.
