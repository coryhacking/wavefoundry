# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-09-04

## Current State

Wave `1wybs review-churn-follow-ups` is CLOSED (2026-09-02). It shipped the
three `1wuju` follow-ups: the Serialization Points token grammar for both
declaration forms in seeds `170`/`040`/`160`, both plan templates, and the
shipped Prepare lifecycle prompt (parser unchanged, pinned per carrier and
against the parser in both forms); the standing-gate policy that an
evaluator-only edit records no close-time baseline while the next
production-bytes wave records a before/after pair, with the disclosure that a
`cross_generation` comparison attributes corpus drift to the change; and the
verdict-gap and install-audit hardening (sanitizer guards including the Windows
repr-doubled spelling, required `root`, a head-and-tail cause cap, the dead
`1viyu` branch removed behind a real-parser test, repository-relative
`checked_but_missing` paths). Two repair cycles, eleven ledger findings
terminal, four lane approvals plus `wave-council-delivery` and operator
signoff; final tree `614d390b129f4f80`, full suite 8,051 OK, docs lint clean.
The wave recorded the standing reference receipt
`docs/reports/retrieval-quality-post-1wybs.json` (verdict `fail` under the
recorded corpus-drift disposition), which both `review-and-evals.md` and
`testing-architecture.md` row 38 now name as `--baseline`.

COMMITTED 2026-09-02 on `main` (subject "Land waves 1wur7, 1wuju, and 1wybs:
evaluator identity, advisory sensors, scaffold grammar"): one commit on
operator instruction covering all three closed waves, their receipts, the six
memory records, and the concurrent session's uncommitted `1wpif` implementation
and `1wpig`/`1wpih` change documents; 102 files, working tree clean afterwards.
STILL PENDING: reload the MCP server (`wf_reload_mcp` or reconnect) so live
sessions serve the delivered gate code, and push when the operator chooses.

Wave `1wuju review-churn-and-evaluator-baseline` is CLOSED (2026-09-01, evening;
framework test receipt proven at 8,039 tests on the final tree; docs lint
clean). It was reopened once the same evening on operator instruction and closed
again unchanged after a clean dry-run: no in-scope file moved between the two
closes, so the recorded approvals and signoff bind the same tree. Delivered: Delivered: `1wujr` (review-cycle churn controls in seeds
180/190/209/214/221/239: landing rule for guards, packet fields
`tree_fingerprint`/`time_budget`/`sweep_rule`, frozen tree per round,
external-blocker escalation, once-per-round repair, census re-derivation, lane
mutation tables; prompts, role docs, and architecture doc reconciled and every
clause pinned), `1wujs` (docs-lint `SENSOR_POLARITY_REGISTRY`; the AC-locality
sensor is ADVISORY, rendered as `docs_lint_warning` with `advisory: true` at
every gate including all five post-parse install-audit envelopes and never
blocking close; a `docs_lint.py` crash with no `ERROR:` line now reaches every
gate as one synthesized, path-free `docs_lint_error`), and `1wujt` (a single
receipt is a baseline at the 0.25 floor; the disclosure tool mirrors it).
Delivery review: eleven findings over three repair cycles, all terminal; four
lane approvals plus operator signoff on receipt
`review-policy-9babd443c497f6f52eba`. The standing baseline
`docs/reports/retrieval-quality-post-1wuju.json` is signed (run `60eed88e`,
verdict `baseline`, zero violations, retrieval quality identical to the
`1wur7` receipt on the same fixture digest).

LESSONS recorded in the Progress Logs: the full suite caught a path leak that
every targeted set and every lane missed, so the sweep rule never replaces the
whole suite before approvals; `wf_prepare_wave(mode='ready')` gardens changed
docs' metadata dates and moves the tree fingerprint (snapshot after prepare);
the evaluator refuses to sign if the index generation moves during its run,
and the context-efficiency projection into the open wave's record plus the
staleness monitor rebuild every few minutes, so record a baseline in the
FOREGROUND with the index brought current first and the
`.wavefoundry/index/reindex-pending` marker kept fresh (holding the build lock
does not work: the evaluator's preflight then reports the index not ready).

FOLLOW-UPS (now admitted into wave `1wybs`, above, except the MCP-server note at the end): scaffold guidance for declarable
`Serialization Points` paths in seeds 170/040/160 and the install plan
template (a root-level file or a glob turns the bullet into prose and drops
lanes); evaluator-only edits should not require a close-time re-baseline (let
the next ranking change record its own before-receipt); low code notes carried
from the code lane (filesystem-root hardening of `_strip_repository_root`, a
required `root` parameter, the uncapped cause line, the dead `1viyu`
synthesized-failure branch on the public path, the install-audit gap pin
hand-building its entry); the `install_log_checked_but_missing` message renders
an absolute artifact path (wave `1p35d` behaviour). Two older MCP servers from
earlier sessions (started 2026-08-30 and 2026-08-31, before chunker 41) still
run on this repository; restart them before the next long evaluator run.

COMMIT OBLIGATION (SATISFIED 2026-09-02 by the single landing commit above;
kept for the record of what it had to stage, since `git commit -a` stages none
of these):
`git add "docs/waves/1wuju review-churn-and-evaluator-baseline/"`,
`git add "docs/waves/1wur7 evaluator-identity-and-ac-locality/"` (both wave
folders are untracked), `git add docs/reports/retrieval-quality-post-1wuju.json`
(the `1wuju` receipt, now the before-receipt wave `1wybs` consumed) and
`git add docs/reports/retrieval-quality-post-1wybs.json` (the current reference
receipt the docs name, verdict `fail` under the recorded drift disposition), the two `1wur7` receipts
`docs/reports/retrieval-quality-post-1wur7-run1.json` and
`docs/reports/retrieval-quality-post-1wur7.json` (historical, superseded
identity), the six untracked memory records under `docs/agents/memory/`
(`1wt78`, `1wud5`, `1wuq9`, `1wv0x`, `1wv6w`, `1wvo1`; two are recorded as
rejected), and the `1wur7` paths below. The `1wpif` test modules and receipts
and the two `1wpih` change documents belong to the concurrent session; the
operator asked for everything to be committed, so they landed in the same
commit while wave `1wpif` stays paused with its attestation outstanding.

Wave `1wur7 evaluator-identity-and-ac-locality` is CLOSED (2026-09-01, receipt
proven at 8,010 tests, eleven findings terminal). Its COMMIT is still pending
(operator-owned) and must explicitly stage the untracked paths below; the
`1wuju` wave folder (`docs/waves/1wuju review-churn-and-evaluator-baseline/`)
is also untracked and belongs in the same or a following commit.
Close-time decisions recorded in `1wuuh`'s Progress Log: latency is ADVISORY
for every comparison kind, and a contended baseline is REPORTED
(`inherited_contended_baseline`) rather than refused. The `1wur7` pair on disk
(`docs/reports/retrieval-quality-post-1wur7-run1.json` +
`retrieval-quality-post-1wur7.json`, UNTRACKED) binds evaluator identity
`3ada285e`, superseded first by the advisory-latency edit and now by `1wujt`;
it is historical, and `1wuju` records the new single-run standing baseline.

COMMIT OBLIGATION for `1wur7` (delivery review REL-DEL-6; SATISFIED by the
landing commit, which staged every path named here): the commit MUST
explicitly `git add ".wavefoundry/framework/scripts/benchmarks/compare_retrieval_receipts.py"`
(now also edited by `1wuju`) and `git add ".wavefoundry/framework/scripts/tests/fixtures/retrieval_eval/"`,
plus the two `1wur7` receipts above as historical artifacts. All are untracked
while tracked files reference them, and `git commit -a` does not stage
untracked paths, so omitting the first two leaves a tracked test reading a
missing fixture and a fresh clone failing at collection. None of them ships.

Foreign failure RESOLVED on operator instruction (2026-09-01): the
uncommitted `1wpig/1wpaj-bug graph-query-contract-correctness.md` carried a
glob (`docs/reports/retrieval-quality-*.json`) inside its second Serialization
Points bullet, which the stricter declaration parser rejects, so every path
after it went undeclared and the document lost `architecture-reviewer` and
`qa-reviewer`. The glob was removed and the receipts named as run outputs in
prose. NOTE FOR THE `1wpig` SESSION: this is the only edit made to your
document. The same trap (a bare root-level `CHANGELOG.md` in a path bullet)
hit all three `1wuju` change docs and was fixed by moving it to a prose bullet.

Same-class observation for `1wpif` (found while auditing `1wur7`'s untracked
paths, not acted on): `1wpif`'s two new test modules
`tests/test_fts_query_honesty.py` and `tests/test_retrieval_candidate_generation.py`
are also untracked. That wave's commit needs the same explicit `git add`.

Wave `1wpif index-content-and-retrieval-correctness` is PAUSED (2026-08-31,
implementation complete and repaired, attestation outstanding; see the
resume checklist below). It was activated 2026-08-31 after a full typed readiness pass:
prepare council PASS with amendments A1-A7, four independent lane reviews
approve-with-notes with every pin applied, five typed approvals on receipt
`review-policy-d811cff42925a023e39d`). Ordered changes: `1wngv` chunk
identity/source ranges, then `1wpag` FTS honesty, then `1wpah` candidate
generation; integrity invariants land before the final comparison. The ANN
threshold battery was relocated to `1wpih` by the council (recorded in that
wave's Dependencies). The `framework_edit_allowed` gate is OPEN for the
implementation phase. Delivery review round 1 produced seven typed findings
(all `do_now`); the repair pass landed all of them at **chunker 41** with a
whole-repository coordinate census reporting zero wrong and a full suite of
7,889 tests. The live index and the receipts are still at chunker 40 and are
STALE: rebuild at 41 on a quiet machine, re-record the pair, recompute the
comparison, then run the security seat and the reverification lanes on the
settled tree before any approval. Progress: `1wngv` implemented (chunker 40 then 41, zero
collisions on a 56,387-chunk census, full suite 7,802 OK); `1wpag`
implemented (keyed FTS digest, single probed-serving chokepoint, healing
under the build lock, 36-test fault battery; AC-6's full-suite clause is
blocked by a failure outside this wave, below); `1wpah` implemented (filter
pushdown, bounded refill with typed ceilings, ANN constants retired with an
executed `explain_plan` proof; suite 7,867 with only the foreign failure).
Evidence recorded (SUPERSEDED by the chunker-41 repair round, re-run
pending): the standing pair on the chunker-40 index
(`retrieval-quality-post-1wpif-run1.json` + `retrieval-quality-post-1wpif.json`,
`pass`, generation 6, production `8c62c3d0`); the cross-generation comparison
against the `1sear` pair is refused by the evaluator's store-file inode binding
(the store file was recreated during the evidence window by the store's
corrupt-open recovery branch, which treated a busy-timeout as corruption;
finding ARCH-DEL-2, repaired: lock waits now propagate and the store is
preserved), so
`retrieval-quality-post-1wpif-vs-1sear-computed.json` reproduces the comparison
arithmetic at the data level (pass, zero violations; `code_lexical` p95 673 to
25 ms; `code_search`/`docs_search` p95 up about 15%, near their thresholds).
The `1sear` pair files are untouched (`1wpih` cites them). Next: delivery
review lanes and council, then the close decision (operator-owned).

Concurrency note (2026-08-31): a second agent session is editing waves
`1wpig` and `1wpih` on this tree (uncommitted edits to `1wpig/1wpaj-bug
graph-query-contract-correctness.md` and both wave records; `1wpih` now
admits four changes: `1wsc8-enh ann-reference-and-tuning-certification`,
which owns the ANN battery relocated from `1wpah`, and
`1wscp-enh retrieval-evidence-adjudication-and-confidence-contracts`, both
untracked, beside `1wpid` and `1wpie`). Its in-flight `1wpaj` declaration edit
currently fails `test_review_policy.py::test_declaration_change_loses_no_lane_anywhere_in_the_corpus`;
that failure is theirs to resolve and is the only red test on the tree.
This session does not touch `1wpig`/`1wpih` files. The 1wpif evidence
receipts (rebuild under chunker 41, comparison run) need a quiet repository,
so that session must be paused for the pipeline window, as in 1seaw.

Wave `1seaw retrieval-intent-golden-queries` is CLOSED (2026-08-31;
operator signoff in session; commit `27ec5fe6` on main; MCP server
reloaded by the operator, so live sessions serve the delivered retrieval
code). History of that delivery below.
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

**Resuming `1wpif` (paused 2026-08-31):** all three changes are implemented
and repaired at chunker 41; the tree is uncommitted and the suite is green
(8,001 tests after `1wur7`'s round 5) except one foreign red test. To close,
in order: (0) expect THREE blocking docs-lint errors the moment `Status:` flips
to `active`: `1wur7` landed the AC-locality sensor, and `1wpif`'s `1wngv` AC-7,
`1wpag` AC-6 and `1wpah` AC-6 each assert whole-repository suite state, which
is out of scope while the wave is paused and in scope at the first lint after
resumption; narrow each to what its change controls (or mark it `[~]` with a
status note) before running validation; (1) wait for the other
session to land wave `1wpig`'s `1wpaj` change doc, which is what trips
`test_review_policy.py::test_declaration_change_loses_no_lane_anywhere_in_the_corpus`
and blocks the two AC-6 full-suite clauses; (2) record `repair_start` plus an
INDEPENDENT reverification for each of the seven repaired findings
(ARCH-DEL-2, RED-DEL-1 to 4, CODE-DEL-2, CODE-DEL-3) and for PERF-DEL-6,
whose repair_start is already recorded and whose reverification is held for
the performance lane's delivery approval; (3) run the delivery council's
security seat (never run: it was cancelled once for a rate limit and once to
avoid reviewing a moving tree); (4) record the four required lane delivery
approvals and `wave-council-delivery`; (5) re-run `wf_prepare_wave(mode='ready')`
for the stale review-policy receipt; (6) operator signoff, then close.
Three follow-up plans came out of this wave: `1wtpl` (evaluator binds the store
file inode), `1wuuh` (evaluator jitter estimator reads one order statistic), and
`1wuui` (acceptance criteria assert repository-wide state). All three were
admitted into wave `1wur7` and delivered on 2026-09-01; see that wave's section
above. The `297` figure this paragraph previously carried was withdrawn as
mis-scanned during `1wur7`'s readiness review, along with a replacement `317`;
the load-bearing count is eight carriers in non-closed waves and five in parked
plans.

## Open Questions / Deferred Decisions

- **Wave `1wybs` receipt outcome (operator).** The after-receipt
  `docs/reports/retrieval-quality-post-1wybs.json` is `fail` on five
  zero-tolerance `code_ask` holdout regressions (largest 0.055 nDCG@10) across
  37 index generations. The wave dispositions this as corpus drift on a
  byte-exact reconstruction against the `1wuju` receipt's production digest and
  a reachability closure showing no changed symbol reaches a retrieval tool.
  The operator closed the wave on that record; if the disposition is ever
  revisited, the evidence is in the `1wybr` Progress Log.
- **Whole-module production identity (operator decision, open).**
  `retrieval_eval._production_identity` hashes whole module bytes, so any
  lifecycle-only edit to `server_impl.py` moves `production_identity` and owes
  a quiet-machine receipt. A finer identity (retrieval functions only, or a
  module split) is unowned.
- **Drift-free comparison pairs (operator decision, open).**
  `run_evaluation`'s `production_scripts_dir` is identity-only: it hashes that
  directory but runs the imported modules, so `production_change_same_generation`
  is unreachable for an indexed production module and every comparison inherits
  corpus drift. Loading the modules it hashes would close this.
- **Parser tightening for `*` spans (recorded deferral, wave `1wxe6`).**
  Rejecting `*` in `review_policy._is_declared_target` would make the shipped
  guidance true by construction in both forms; it is an evaluator-version
  transition (7 to 8) costing one re-Prepare per readied wave, including
  another session's `1wpig`. Zero of 908 change documents are affected today.
- **`docs/prompts/prepare-wave.prompt.md` declaration guidance (DOCS-RV1-3).**
  The self-hosted, project-owned Prepare prompt carries no declaration
  guidance, while seed `160` now expects a target's prompt to state the lane
  floor and the token grammar; a later docs wave should bring it to the shipped
  baseline.

## Follow-Ups

- DONE 2026-08-31: reverification round complete, final evidence recorded,
  delivery approved, operator signoff given, wave closed.
- Evaluator follow-up (surfaced by 1wpif, owner: the `1wpih` successor
  evaluator `1wsc8`): `retrieval_eval._index_identity` binds the sqlite
  state-store file inode for every comparison kind, so a compatibility rebuild
  that rewrites the file makes the evaluator's own `cross_generation` kind
  unusable; bind the store by repository identity and path (or bind the inode
  only for same-generation pairs). Until then, cross-generation comparisons
  after a rebuild are data-level computations, disclosed as such.
- Before any post-rebuild evidence run, `wf_reload_mcp` (or reconnect) so the
  live server's chunker version matches the index; a stale server re-triggers
  builds every quiet period and invalidates every frozen run. Record the pair
  on a quiet machine (no test suites, no other session, load below 2,
  `index_build_status.lock.held` false): the chunker-40 pair carried about
  15% contention inflation (PERF-DEL-2), and a cross-generation comparison
  inherits the baseline pair's jitter, so an inflated pair ratchets the
  latency gate for every later wave.
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
(2026-09-02) — Serialization Points token-grammar guidance across seeds and
templates, the evaluator-edit baseline policy with its drift disclosure, and
the verdict-gap and install-audit hardening. Framework and seed gates are
CLOSED. The three closed waves are COMMITTED on `main` (one commit, 102 files);
the MCP server reload and any push remain.
