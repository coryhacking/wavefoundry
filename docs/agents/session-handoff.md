# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-08-31

## Current State

Wave `1seaw retrieval-intent-golden-queries` is CLOSED (2026-08-31;
operator signoff and closure instruction given in session; `wf_close_wave`
wrote the closed checkpoint and wave summary). The tree is uncommitted:
the operator owns the commit. After the commit, reload the MCP server so
live sessions serve the delivered retrieval code.
History of the delivery below.
Review wave cycle 2 (2026-08-31; five fresh lanes plus the delivery council)
BLOCKED the first repair round's report-class evidence source as a
subject-blind, fixture-shaped prior, and it has been REMOVED from
`server_impl.py` (see the wave record's cycle-2 Review Checkpoint and the
1seas Decision Log 2026-08-31). What stays: the five-value classifier (now
with an explanatory-lead rule and a review-frame assessment regex), the
derived docs query at true reranker scores, the score-only report-class
prior, walker 16, owner-row injection with a mechanism-framed pin gate, the
corrected cue regex (dot-directory paths anchor whole), `section` on
citations, and the evaluator receipts (now with `retrieval_toggles`,
`production_drift`, a `git` disclosure block, and a stricter abstention
oracle). The corpus is 35 fixtures / 11 classes / 7 floors. All focused
suites pass (929 retrieval, 42 evaluator, 25 parity, 40 state-store, 313
indexer). Cycle-2 reverification (2026-08-31, five fresh lanes) approved five
lanes with notes and returned two bounded revisions, both repaired inline: the
exact-ownership post-filter dropped mixed-case owner rows (`AGENTS.md`), and
the runtime `code_ask` description lagged the spec; prose slash pairs, the
article-before-filename pin boundary, the caller-less `path_prefix`, blob-byte
`matches_head`, and the docs-lint holdout label were repaired alongside (see
the wave record's reverification checkpoint).

**Operator decision taken 2026-08-31, option (a)** (1seas Decision Log): the
recall floor on `architecture-review-holdout-remediation` is removed from the
fixture file; the class keeps its question-type floor; assessment retrieval
is reported per class as a measured baseline weakness; 1seas AC-1 and 1sear
AC-6 carry `[~]` status notes; the typed findings-register surface is the
follow-up plan `docs/plans/*findings-register-assessment-surface*.md`. The
fixture digest changed, so the five-report evidence set must be re-run
before AC-4 (1seas) can close on it.

Evidence (final): the five-report set on the frozen post-reverification
tree (index epoch attempt `8916932c`, corpus digest `bda67546`, seven
floors, `end_digest_verified` on all five receipts): the standing pair
`retrieval-quality-baseline-run1.json` (`baseline`) +
`retrieval-quality-baseline.json` (`pass`, metric jitter 0.00%), the HEAD
before pair `retrieval-quality-before-1seas*.json` (`fail`, five floors),
and the receipt `retrieval-quality-post-1seas-vs-before.json` (`pass`,
zero violations, production `05ab0836` to `dab71287`). 1seas AC-4 is
closed on it. It supersedes and overwrites the generation-12 attempt
`06c20179` set in place. The injector-era reports are preserved as
`retrieval-quality-superseded-injector-*.json` (provenance only). The
focused re-reverification approved both lanes with notes (firm
confidence) and its three boundary reproductions (RV3-1/2/3: path-named
subjects pin, dot-directory prefixes never leak as cues, a noun between
article and filename keeps the pin) are repaired with the reproductions as
tests. The fresh five-report evidence run is recorded and the delivery
approval line is in `wave.md`. Remaining before closure: operator signoff,
closure (operator-owned).
Pipeline note for any re-run: `run_evidence.sh` in the session scratchpad
needs a quiet repository (no other session mutating waves, no turn ending
mid-run); a follow-up worth doing is letting the pipeline hold the index
build lock for its whole duration so hook-triggered builds skip instead of
publishing a new generation mid-sequence.
This wave is on the legacy prose review authority (no `events.jsonl`); the
cycle-1 evidence lines contain the bare token "critical" (kept as history),
which trips `max_severity: critical` in `wf_review_wave`.

Operational lessons recorded in the change docs: the turn-end Stop hook
rewrites `wave.md` (Context Efficiency checkpoint) and invalidates a frozen
run's preflight unless the tree is quiet first; a full rebuild leaves FTS5
unmerged and pushes `code_lexical` over its absolute ceiling until
`index_optimize` runs. The attached MCP session still serves pre-`1seas`
code until it is reloaded.

Waves `1wpig graph-correctness-and-trust-contracts` is formally readied.
`1wpif index-content-and-retrieval-correctness` and `1wpih
index-quality-evaluation-and-ranking` are prepared/reviewed but remain
dependency-gated. Their plans and the original multi-agent audit prompt
and dispositions are present in the uncommitted tree.

## Follow-Ups

- DONE 2026-08-31: reverification round complete, final evidence recorded,
  delivery approved, operator signoff given, wave closed.
- At close, keep `docs/reports/index-quality-audit-dispositions.md` and
  `docs/reports/index-quality-audit-prompt.md` where they are: the assessment
  fixtures label them, and relocating them makes the evaluator raise
  `stale_corpus` on the next run (ARCH-RV-1).
- Recorded follow-ups (not in this wave): a typed findings-register surface
  for assessment context (MCP resource or a `report` kind on `docs_search`);
  memoizing the per-call store integrity probe that dominates `code_lexical`
  latency; a currentness predicate for the report-class prior; the
  `constant_value_lookup` label-versus-classifier mismatch (UPPER_SNAKE
  constants never anchor; question-type accuracy 0.0 on both sides); the
  second live review-session misranking phrasing not yet encoded verbatim;
  `docs_search` and `enumeration` holdout recall 0.0 on both sides; the
  evaluator's own source taking result slots; both assessment fixtures
  labelling a wave-period report the close procedure may relocate. The
  `1wpih index-quality-evaluation-and-ranking` wave is the natural home.
- After the wave commits, reload the MCP server so live sessions see the
  `assessment` type, the evidence source, and `section` on citations.

- `_ts_flat_emit_chunker` un-anchored config ids: the recorded 1wh1b
  follow-up, quantified by the 1wl7w delivery council's whole-repo sweep at
  151 colliding ids / 565 dedupe losses in css/js/toml (route through
  `_dedupe_id_base` in a future wave).
- Miro boards: recorded 1wl7v non-goal (cloud-resident, no open on-disk
  format). Dual-extension exports (`.drawio.png` etc.) and over-walk-cap
  boards with embedded images: recorded non-goals/limitations.
- The malformed-notebook line-window fallback stays in the both-tables
  drop class by recorded disposition (1wl7u).
- Oracle-home consolidation (seed-211/guru parity oracles in two test
  modules) remains the recorded 1wip2 non-goal.

## Current Session

**Active wave:** *(none)*
