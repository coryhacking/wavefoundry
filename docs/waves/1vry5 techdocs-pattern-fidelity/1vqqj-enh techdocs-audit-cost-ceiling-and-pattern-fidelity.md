# TechDocs audit: close the two remaining pattern-fidelity gaps

Change ID: `1vqqj-enh techdocs-audit-cost-ceiling-and-pattern-fidelity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-20
Wave: 1vry5 techdocs-pattern-fidelity

## Rationale

Wave `1vqqi` originally recorded three follow-ups for `wf techdocs-audit` /
`wf_techdocs_audit`. During that wave, the operator directed that the substantive cost gap be
repaired immediately: both public entries now use one isolated runner with a ten-second worker
deadline and a repository-I/O-free `audit_timeout` degraded report. This plan is therefore
narrowed to the two matcher improvements that remain: remove one known source of wasted
backtracking and close one pattern-fidelity mismatch. It must not schedule or re-implement the
delivered timeout. The change ID is retained for continuity even though its earlier
`cost-ceiling` wording now names historical context rather than new scope.

The cost gap is the substantive one, and its history is the reason it needs a real fix rather
than another number. Four successive attempts to state a worst-admitted per-call cost were each
falsified within hours, every time by reading a figure off one point of a curve and generalizing:
"about 19ms" (beaten 23x), "a quarter of a millisecond" (held only at a 60-character subject),
"15.8ms at the component cap" (held only for a single-component subject; the true figure was
**28.3 seconds**), and "66ms" (held only for segment-local patterns). **One** mechanism was tried
and withdrawn as fail-open: a 32-component subject cap, which refused a legal 33-deep path and so
answered *published* for an ordinary file. A second, the `crosses_separator` flag, was fail-open
in its FIRST form (syntax-derived, it missed that `[!q]` compiles to `[^q]` and matches a
separator) and was then **REPAIRED, not withdrawn**: it now asks the COMPILED class whether it
matches a separator. It is live and load-bearing today, set inside `_translate_pattern`'s emit
loop and consumed by `excluded()` as `reachable = ancestors if crosses else ancestors[:1]`, pinned
by `test_separator_crossing_is_decided_by_the_compiled_class_not_by_syntax`. **It sits inside the
very loop this change edits and must be preserved**, and AC-2's neutrality differential compares
`excluded()` answers, which depend on it. An earlier draft of this plan called it withdrawn, which
contradicted the closed `1vqqi` archive and would have invited an implementer to delete it
(readiness council, docs-contract finding 6).
The lesson remains relevant to the two matcher edits: neither may be presented as the aggregate
cost bound. That bound is already owned by wave `1vqqi`'s public runner.

## Requirements

1. **Preserve the existing aggregate bound as a precondition.** Wave `1vqqi`'s
   `run_techdocs_audit` already gives both public entries a ten-second isolated-worker deadline,
   performs no repository-derived I/O after expiry, and returns `audit_timeout`. This change
   preserves that contract while changing only pattern translation. The historical pre-timeout,
   pre-AC-5
   reproduction remains the control: `**/**/*aX` counts three variable groups and cost **6.3s at 1201 path components and 28.5s at 2001**, measured END TO END through the CLI. **The subject shape is load-bearing and the first draft omitted it:** the same pattern matched ONCE against the same subject costs about 15ms at 1201 components, while `excluded()`'s ancestor walk costs 5.93s, a 400x spread on an identically-stated shape. The figure names `excluded()` with the ancestor walk, against a subject of `"a/"` repeated to the component count when matched against one syntactically ordinary
   Markdown link carrying an adversarially deep href.

2. **Collapse adjacent floating-prefix emissions without changing budget classification.**
   `**/**/` and `**/` denote the same match language, so a run of adjacent `(?:.*/)?` regex
   fragments may be emitted once. Every source variable group must still increment
   `variable_groups`, including a source `**/` whose fragment is not emitted. The optimization
   therefore removes redundant backtracking only for patterns already admitted by
   `_MAX_VARIABLE_GROUPS`; it must not admit a pattern currently refused by the source-group
   ceiling. In particular, `**/**/*aX` remains admitted while `**/**/**/*aX` remains refused and
   listed by `unsupported_patterns`.

   **What this does NOT buy, stated plainly because the first draft implied otherwise.** Historical
   pre-AC-5 diagnosis measured the collapse's named shape from **5.947s to 0.028s** at 1201 components, a 212x win on that
   pattern. In the named measurements, a comparably slow literal-separated case remains. Inserting one literal character
   gives `**/a/**/*aX`: still three source groups, still admitted, not adjacent and therefore not
   collapsible, measured **6.068s before and 6.107s after** at the same subject, and **27.1s at
   2001 components**. So the end-to-end reproduction that motivated the ten-second worker deadline
   survives this change intact through a one-character pattern edit. An earlier draft named
   `**/a/**/b/**/c` as the residual; at 2.82s that is the CHEAPEST of the three and understated
   the real leftover by 2.2x.

   This change is therefore scoped as a **correctness and redundancy** fix, not a cost fix. The
   public worker deadline remains the only aggregate guard, and the ceiling that would actually
   bound this family is deliberately **out of scope** (see the Decision Log and follow-up plan
   `1vt2r-enh techdocs-crossing-group-cost-ceiling`).

3. **`\/` is refused wherever the oracle refuses it, not admitted by a broad local guess.**
   `_translate_pattern("/a\/b/")` returns `ok`, while `pathspec` refuses the pattern outright and
   MkDocs aborts `load_config` with `Invalid git pattern`. The module's own contract already says
   a pattern MkDocs cannot load must be refused so the run degrades rather than presenting a
   boundary for a site that cannot be built; the `//` family follows that rule and this one does
   not. The implementation must check anchored, floating, negated, directory-only, and embedded
   escaped-slash forms against pathspec/MkDocs. Refuse every form the oracle refuses; if any form
   is accepted, preserve that distinction and amend this plan before implementing a broader rule.

4. **Every delivered acceptance/performance claim is produced by the predeclared hostile corpus
   and stated with its subject shape.** No figure introduced as current delivery evidence enters a
   comment, a Risks row or a spec entry without naming the pattern AND the subject it was measured
   against. Historical pre-AC-5 diagnostic measurements may remain as motivation only when they
   are explicitly labeled historical; they are not claimed as rows reproduced by the retained
   artifact. "Worst" in current delivery evidence means only the slowest observation in AC-5's
   finite named corpus; it is not a universal maximum. This change does not claim a new universal
   matcher or per-call ceiling; the public worker deadline remains the only aggregate bound. This
   requirement exists because omitting the subject shape is the single defect that recurred four
   times in `1vqqi`.

## Scope

**Problem statement:** Before wave `1vqqi` added the public worker deadline, a target-controlled
`mkdocs.yml` pattern plus one syntactically ordinary Markdown link carrying an adversarially deep
href could consume 28.5 seconds inside the exclusion matcher. Public calls are now stopped after
ten worker seconds and return `audit_timeout`; this follow-up removes one known redundant
backtracking shape and fixes one escaped-slash fidelity mismatch without replacing that guard.

**In scope:**

- Collapsing adjacent `(?:.*/)?` runs in `_translate_pattern`.
- Refusing `\/`.
- Re-running AC-5's finite hostile corpus after the collapse and recording every result with its
  exact pattern and subject shape, without claiming a universal local ceiling.

**Out of scope:**

- The already-delivered public timeout and escaping-nav-symlink refusal from wave `1vqqi`.
- Any change to the boundary semantics themselves. The matcher agrees with
  `mkdocs.structure.files.get_files` at 0 fail-open and 0 fail-closed over 7200 randomized blocks,
  and this change must not move that.

## Acceptance Criteria

- [~] AC-1: Superseded in this plan: wave `1vqqi` now owns and tests the worker deadline, I/O-free expiry, and
  `audit_timeout` envelope at both public entries. This plan preserves that control but does not
  re-implement or re-accept it.
- [x] AC-2: **The collapse demonstrably HAPPENED**, proven by an assertion that fails on the
  unmodified module: the compiled pattern for `**/**/*aX` contains **exactly one** `(?:.*/)?`
  fragment (it contains two today), and `excluded()` on that pattern against the subject
  `"/".join(["a"] * 1201)` completes in **under 0.5s** (the historical pre-AC-5
  baseline took 5.947s). Both clauses are
  falsifiable against the current tree; the earlier draft's clauses were all true before any edit,
  so an implementer shipping only the escaped-slash refusal satisfied it with true statements.
  Neutrality is then proven separately with an explicit outcome partition over **6000 generated patterns at seed
  `20260819`**, of which at least 400 must have their emitted regex changed by the collapse (a run
  where none changed proves nothing), shows `excluded()` and `unsupported_patterns()` return
  identical results before and after across at least 15000 block-and-subject comparisons for the
  **collapse-neutral partition**, including the oracle-accepted escaped-slash controls. The
  **intentional escaped-slash partition** is derived from AC-4b's stored oracle verdict table and
  permits exactly one observable contract delta: each AC-3 oracle-refused form moves from today's
  `ok`/supported result to `refused`/unsupported and appears in the public degraded report.
  `excluded()` answers are deliberately not compared for that partition: MkDocs cannot load those
  configurations, so they have no publication boundary, and the post-change matcher correctly
  omits refused patterns. It permits no other classification or report delta. This partition is
  mandatory because unrestricted before/after identity would contradict AC-3 by requiring the
  known fidelity repair not to happen.
  **The generator alphabet is specified, not left to the implementer**, and must include `\`,
  `\\`, `/`, `**`, `*`, `?`, character classes and negation: without backslashes in the alphabet
  the corpus cannot see AC-3 over-refusal, and without a stated alphabet the "at least 400
  changed" floor is self-tunable (a corpus saturated with `**/**/` clears it while proving almost
  nothing, and a genuinely broad corpus may fall under it and pressure the implementer to bias
  the generator). The
  polarity pins stand as preservation checks, not as gates: `**/**/*aX` stays admitted and
  `**/**/**/*aX` stays refused. **Baseline recovery:** `techdocs_audit_lib.py` is UNTRACKED, so
  `git show HEAD:` yields nothing and `git stash`/`restore`/`checkout --` are forbidden here; the
  implementer must byte-copy the module to scratch BEFORE the first edit and use that copy as the
  "before" side.
- [x] AC-3: Escaped slash is refused and reported through
  `publication.unsupported_patterns` for every oracle-refused form. The matrix covers anchored
  `/a\/b`, floating `a\/b`, negated `!a\/b`, directory-only `a\/b/`, and embedded
  `pre\/post.md` patterns, with pathspec/MkDocs determining the expected classification in each
  case so the refusal boundary is not a local opinion. **The rule is causal, not positional, and an earlier
  draft got it WRONG in the fail-closed direction.** That draft said "any `\/` occurrence anywhere
  is refused, because the oracle refuses it anywhere". The oracle does no such thing: it refuses a
  backslash that **escapes** a separator. Where the backslash is itself escaped the sequence `\/`
  still appears, and both `pathspec` and `mkdocs.config.load_config` **accept** the pattern.
  Measured: `a\\/b`, `\\/x.md`, `a\\/b/c` and `x/\\/y` all contain `\/` and all load
  cleanly, so the naive reading (`if "\\/" in pattern: refuse`) breaks four configs MkDocs really
  builds. That is the direction this module's own docstrings call the wrong answer.

  **The rule to implement:** refuse a `/` immediately preceded by a backslash **that the
  translator's escape branch actually reaches**, that is, a backslash not already consumed as part
  of a `\\` pair. A 24-form sweep found **nine** divergent shapes, not the five an earlier draft
  enumerated: the five named above, plus `\/a`, `**/a\/b`, `a/\/b`, and `a\\\/b` (three
  backslashes then a slash, which the oracle refuses and the module accepts today).

  **Controls that must keep AGREEING**, and the `\\/` family is the one that catches
  over-refusal: `a\\/b`, `\\/x.md`, `a\\/b/c` and `x/\\/y` must stay ACCEPTED by both sides;
  `a\/` and `\/` are already refused; `a\//b` is refused; `[a\/b]` and `[\/]` are inert on both
  sides; ordinary escapes (`a\*b`, `a\?b`, `\!a`, `a\ b`, `\\`) are accepted by both.

  **Non-vacuity floor, and it must be DERIVED:** the oracle-refused set is obtained by filtering
  the full matrix against a stored oracle verdict table that AC-4b's harness regenerates, and the
  test asserts that set is non-empty and contains the nine known forms. A hardcoded literal list
  cannot fail its own "non-empty and contains these" check and would detect nothing; since
  `pathspec` cannot be imported in the suite, the verdict table is the only honest carrier. All
  nine forms return `ok` from `_translate_pattern` today while the oracle refuses them, so the
  floor is satisfiable now and would have to be deliberately emptied to go vacuous.
- [x] AC-3b: **Re-point the inherited timeout reproduction, do not merely retain it.**
  `test_the_bounded_runner_kills_the_recorded_crossing_pattern_reproduction` injects `**/**/*aX`
  with a 2000-component href and asserts `audit_timeout` at a 0.2s budget. That is EXACTLY the
  shape this change removes: historical pre-AC-5 diagnosis measured `excluded()` dropping from
  about 28s to **0.077s**, a
  370x reduction, so after the collapse the test either passes on subprocess-spawn latency alone
  or fails outright, and its docstring becomes false about the shipped code. AC-2's differential
  is structurally blind to this, because `excluded()` answers False both before and after. The
  test must be re-pointed at the surviving reproduction this plan already establishes,
  `**/a/**/*aX` (historically 27.13s over 2001 components before the AC-5 corpus was defined),
  and its docstring updated to match. A run that
  leaves it pointed at the collapsed shape fails this criterion even though the suite is green.
- [x] AC-4: For every **oracle-loadable** generated block, the boundary is unchanged: the randomized differential against
  `mkdocs.structure.files.get_files` filtered on `inclusion.is_included()` still reports 0
  fail-open and 0 fail-closed, and this repository's dogfood still reports 62 survivors, 4 nav
  entries, 2 findings and an empty degraded list. **Re-derivable by someone other than the
  implementer**, which the first draft was not. The implementer **shall write** an oracle harness
  to `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py` and stage it
  for operator commit (no path under `tests/oracle/` exists today; "is committed" was a
  description of a tree that does not exist, and committing is operator-owned regardless). It
  **shall** run **7200 blocks over 6 seeds, 1200 each, seeds `20260819` through `20260824`**,
  against the fixture tree produced by `test_techdocs_audit_lib._build` extended to cover deep
  paths, dotfiles and `templates/` (the current `_build` writes 5 pages, not the 19 an earlier
  draft asserted; enumerate the final page list in the harness module docstring). The exact
  command goes in that docstring.
- [x] AC-4b: **Oracle environment, provisioned and pinned.** `mkdocs` and `pathspec` are in
  NEITHER the tool venv nor system Python, so neither AC-3's classification oracle nor AC-4's
  differential can be a unit test, and the suite must keep reporting 0 skips. Both run against a
  scratch environment created as `python3 -m venv <scratch>/oracle-env && <scratch>/oracle-env/bin/pip
  install "mkdocs==1.6.1" "pathspec==1.1.1"`. Those versions are **pinned deliberately**: AC-3's
  expected classifications are oracle-version-dependent, and `1vqqi` measured against exactly this
  pair. The harness records the two versions it observed in its output, so a run against different
  versions is visible rather than silent. An earlier draft demanded this statement of the plan and
  then did not make it.
- [x] AC-4c: **The `crosses_separator` pin is edited deliberately, not left for delivery lanes to
  arbitrate.** `test_separator_crossing_is_decided_by_the_compiled_class_not_by_syntax` asserts
  `_translate_pattern("/a\\/b")[4]` is True. Under AC-3 that pattern becomes REFUSED, so the
  subTest necessarily flips to False and the escape branch's
  `if pattern[i + 1] == "/": crosses_separator = True` becomes unreachable. The Rationale calls
  this mechanism load-bearing and says it must be preserved, so the change must state explicitly
  which `\/` probe replaces `/a\\/b` in that pin (an accepted `a\\/b` control is the natural
  substitute, since it exercises the same branch and stays admitted), and whether the now-dead
  line is removed or retained with a comment. Silence here leaves a reviewer arbitrating against
  an emphatic "must be preserved".
- [x] AC-5: **The finite hostile corpus reports the slowest observed admitted cost BEFORE and
  AFTER over identical inputs**, not only the delta on the shape the collapse removes. The
  permanent AC-4 harness owns the protocol. Its exact pattern set is `**/**/*aX`,
  `**/a/**/*aX`, `**/**/a/**/*aX`, `**/a/**/b/**/*aX`, `*/*/*/*.md`, and
  `/*?*?*?*?*?*?x.md`. For each pattern it tests both subjects `"a/" * (depth - 1) + "aY"`
  and `"a/" * (depth - 1) + "z.md"` at depths **201, 401, and 801**. The baseline scratch
  byte-copy and delivered module receive the identical Cartesian product. Each pair gets one
  untimed warmup and three isolated timed runs; the recorded value is the median wall time.
  Patterns refused by either module remain in the artifact as classification controls but are
  excluded from that module's admitted maximum. The harness writes deterministic JSON containing
  module SHA-256s, Python/platform metadata, pattern, subject-shape label, depth, translation
  classification, three timings, median, and the before/after maximum rows to
  `docs/waves/1vry5 techdocs-pattern-fidelity/techdocs-pattern-cost-results.json`.

  On Requirement 2's measurements the slowest observation is expected to remain in the
  literal-separated family. Recording only the adjacent-collapse win while omitting the corpus
  maximum is the selective-figure failure this plan says recurred four times. Every reported cost
  names its exact pattern and subject shape. The plan and artifact call the result only the
  **slowest observed in this named corpus**, never a universal matcher or aggregate ceiling.

## Tasks

- [~] Timeout task superseded: delivered and contract-pinned in wave `1vqqi`; no seed 178 edit was
  needed because the workflow consumes degrade tokens generically.
- [x] Collapse adjacent `(?:.*/)?` emissions in `_translate_pattern` while counting every source
  variable group; pin admitted `**/**/*aX` and refused `**/**/**/*aX` polarity and prove
  `excluded()` plus `unsupported_patterns()` neutrality before claiming the cost win.
- [x] Refuse oracle-refused `\/` forms in the escaped-character branch, with anchored, floating,
  negated, directory-only, and embedded pathspec/MkDocs cross-checks.
- [x] Re-run the oracle differential and dogfood; run AC-5's exact finite pattern × subject ×
  depth protocol against the scratch baseline and delivered module, retain the JSON artifact,
  and report the slowest observed admitted row with its exact shape.
- [x] Add the permanent pinned oracle harness at
  `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`, document this
  scratch-environment oracle tier in `docs/architecture/testing-architecture.md`, and keep the
  ordinary unit suite dependency-free with zero skips.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Matcher translation and focused regressions | `implementer` | — | Collapse adjacent floating prefixes and refuse escaped slash in the existing translator. |
| Boundary/oracle verification | `qa-reviewer` | Matcher translation | Differential against MkDocs/pathspec, dogfood, and preservation of the public timeout envelope. |
| Test-tier architecture review | `architecture-reviewer` | Oracle harness | Confirm the pinned scratch-oracle tier remains outside the dependency-free unit suite and changes no runtime ownership boundary. |
| Adversarial cost verification | `performance-reviewer` | Matcher translation | Search hostile admitted patterns and subjects; report shapes with every timing. |
| Hostile-pattern refusal review | `security-reviewer` | Matcher translation | Confirm target-controlled patterns fail conservatively and do not bypass the existing worker guard. |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `.wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py`
- `docs/waves/1vry5 techdocs-pattern-fidelity/techdocs-pattern-cost-results.json`
- `docs/architecture/testing-architecture.md`

The translator and focused regressions land first. The oracle differential, adversarial cost
search, and hostile-pattern review may then run in parallel against identical bytes. Dogfood and
the final docs validation run after those checks so their evidence describes the delivered tree.

## Affected Architecture Docs

Update `docs/architecture/testing-architecture.md` to document the permanent, version-pinned,
scratch-environment TechDocs oracle tier and its separation from the dependency-free unit suite.
No runtime architecture changes: the change remains confined to pattern translation within the
existing TechDocs audit module and does not change MCP/CLI ownership, the isolated-worker
boundary, the timeout envelope, or the documented data/control flow. If implementation discovery
changes any of those boundaries, this section and the required review lanes must be amended
before that broader edit.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | not-this-scope | The public deadline, I/O-free expiry, and timeout envelope were delivered and accepted in wave `1vqqi`; this wave only preserves them. |
| AC-2 | required | The optimization is acceptable only if it is semantically neutral and removes the reproduced adjacent-prefix shape. |
| AC-3 | required | Refusal must match the MkDocs/pathspec oracle and remain visible to callers. |
| AC-4 | required | The publication boundary and repository dogfood must remain unchanged. |
| AC-3b | required | The collapse silently hollows out the inherited timeout reproduction: it removes the exact shape that test injects, so the test goes green on subprocess-spawn latency while its docstring becomes false. AC-2's differential cannot see it, because `excluded()` answers False on both sides. |
| AC-4b | required | AC-3's derived non-vacuity floor depends on the verdict table this harness regenerates, so without it the floor degrades to a literal list that cannot fail. It carries its own row because the close gate parses `AC-4b` as an id distinct from `AC-4`, and an AC with no row resolves to `unknown`. |
| AC-4c | important | The pin edit changes no delivered behaviour, but the Rationale calls the mechanism load-bearing and says it must be preserved, so leaving delivery lanes to arbitrate that against AC-3's refusal is a review cost rather than a correctness one. |
| AC-5 | required | Honest, shape-specific adversarial measurement prevents another unsupported cost claim. |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-19 | Narrowed the plan to the two remaining matcher improvements, clarified that the 28.5-second result is historical pre-timeout behavior on an adversarially deep href, and completed execution, review-target, architecture, priority, decision, and risk sections. | Wave `1vqqi` delivered the ten-second public worker deadline; current `techdocs_audit_lib.py` retains that guard and documents the `**/**/*aX` reproduction. |
| 2026-08-19 | Readiness repair cycle 1 separated emitted-fragment collapse from source-group budget accounting and expanded escaped-slash verification to an oracle-owned context matrix. | `PREP-SOURCE-GROUP-BUDGET-001`; direct polarity showed `**/**/*aX` admitted and `**/**/**/*aX` refused before implementation. |
| 2026-08-19 | Readiness repair cycle 2 partitioned collapse-neutral outcomes from the intentional escaped-slash classification delta, corrected the derived refused floor from eight to nine forms, and declared the permanent oracle harness plus testing-architecture carrier. | `PREP-DIFFERENTIAL-POLARITY-002`; retained pathspec 1.1.1 and MkDocs 1.6.1 refuse all nine named forms that the current translator reports `ok`. |
| 2026-08-19 | Readiness repair cycle 3 removed match-answer identity from oracle-unloadable forms while preserving exact identity for every loadable pattern and requiring the refused/unsupported/degraded public delta. | `PREP-REFUSED-MATCH-DELTA-003`; five current escaped-slash pattern/subject pairs actively exclude paths, but refusal necessarily removes those patterns from `excluded()`. |
| 2026-08-19 | Readiness repair cycle 4 replaced an unbounded “worst admitted” claim with a deterministic finite hostile corpus, explicit depth/subject grid, median protocol, admission filter, and retained JSON schema. | `PREP-ADVERSARIAL-SEARCH-UNIVERSE-004`; the prior AC allowed different implementer-selected families to produce incompatible maxima while both passing. |
| 2026-08-20 | **Thought:** implement the two translator edits at their existing branches, keeping source-group counting independent from emitted-fragment deduplication and refusing only a slash reached by the escape branch. | Pre-edit baseline byte-copy `/tmp/1vry5-baseline.VWH4y5/techdocs_audit_lib.py`, SHA-256 `81ee30055e1b84e35102303c635ffe808a23bbf4ca704dac41193c0db18e74cc`; current `_translate_pattern` branches at `**/` and backslash escape. |
| 2026-08-20 | **Observe:** the delivered translator collapses adjacent floating-prefix emissions without reducing source-group accounting, and the escape branch now refuses only an escaped separator that actually reaches it. | Warning-strict focused audit/CLI/MCP matrix: 102 tests OK. The 6,000-pattern seed-20260819 before/after differential recorded 1,025 changed regex emissions—993 in the 5,955-pattern random partition—17,973 neutral answer comparisons, zero failures, and exactly nine `ok`/supported → `refused`/unsupported deltas. |
| 2026-08-20 | **Observe:** the independent publication oracle and repository dogfood preserve the public boundary. | Pinned MkDocs 1.6.1/pathspec 1.1.1 harness: 7,200 blocks over six seeds, 0 fail-open, 0 fail-closed, all nine refused and four accepted escaped-slash controls matched; dogfood: 62 survivors, 4 nav entries, 2 expected findings, degraded `[]`. |
| 2026-08-20 | **Reflect:** the collapse removes its redundant adjacent-prefix shape but does not establish a broader cost ceiling; the literal-separated family remains the slowest observation in the named corpus. | Retained `techdocs-pattern-cost-results.json`: before maximum `**/**/*aX` × `deep_aY` at depth 801, median 1.828621s; after maximum `**/a/**/*aX` × `deep_aY` at depth 801, median 1.816011s. Full framework suite: 7,452 tests across 64 files, OK. |
| 2026-08-20 | **Repair cycle 5:** removed the surviving universal “worst admitted” sentence, derived escaped-slash expectations from the live MkDocs/pathspec results with a stale-label falsifier, separated the 32 directed regressions from the random non-vacuity floor while adding the standalone backslash alphabet member, updated the load-bearing matcher comment from stale future tense to the delivered collapse plus surviving literal-separated reproduction, and scoped AC-5 provenance to current delivery evidence while labeling older motivating measurements historical pre-AC-5 context. | `PERF-DEL-1`, `QA-DEL-1`, `QA-DEL-2`, `ARCH-DEL-1`, `PREP-COST-PROVENANCE-005`; repaired pinned run: 7,200 boundary blocks with zero fail-open/fail-closed, 5,955 random patterns with 993 changed emissions (floor 400), 17,973 neutral comparisons, zero failures; refreshed delivered-module SHA-256 `31aa4e64bcee2c15aa2fabe51a2f98d674766f79f40f8b7df116b1ad821e53e2`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-19 | Selected a matcher-only follow-up that collapses the redundant adjacent floating prefix and refuses escaped slash while preserving the existing public deadline. | It closes both remaining admitted gaps with the smallest behavioral surface and keeps aggregate availability ownership in the already-delivered worker. | Reopen timeout/cost-ceiling design: rejected because `1vqqi` already delivered the aggregate guard and local measurements repeatedly failed to generalize. Defer both gaps indefinitely: rejected because one wastes the worker budget and the other disagrees with MkDocs/pathspec. Replace the translator wholesale: rejected as disproportionate and likely to disturb the verified publication boundary. |
| 2026-08-19 | Keep the existing `_MAX_VARIABLE_GROUPS` source-group ceiling for this change, and record the divergence it preserves rather than silently carrying it. | The readiness council showed the ceiling is coarser than the oracle in both directions. After the collapse, `**/**/**/*aX` emits the regex of an ADMITTED pattern, yet stays refused on a source-group count that no longer describes what the regex does; and the entirely ordinary `*/*/*/*.md` is refused today (`excluded()` answers False, the run degrades) while `GitIgnoreSpec` matches `w/x/y/z.md` on a linear, unambiguous regex. This change does not close that, so a change titled pattern fidelity is knowingly leaving a fidelity gap, and says so here rather than leaving it as an unexamined invariant. | Charge the budget on post-collapse separator-CROSSING group count instead of raw source-group count. Measured, crossing-group count predicts cost and source-group count does not, so a ceiling of at most one crossing group admits `*/*/*/*.md` (0.0119s, refused today) and `**/**/**/*aX` (0.0264s, refused today) while refusing `**/a/**/*aX` (5.89s, admitted today) and `**/a/**/b/**/c` (2.82s, admitted today). It must stay ADDITIVE with the within-segment budget, since `/*?*?*?*?*?*?x.md` has zero crossing groups and is still exponential. **Correction:** an earlier version of this row named the deferred design as charging for a run of ADJACENT variable groups with no intervening literal separator, and called it the council's recommendation. That metric rates `**/a/**/*aX` at ZERO adjacent runs, because each `(?:.*/)?` is separated by the literal `a/`, so it would admit the 5.89s shape it was meant to catch. It does not subsume the collapse and is recorded here only so it is not re-proposed. Deferred to plan `1vt2r-enh techdocs-crossing-group-cost-ceiling`, which depends on this change because the metric is defined on the POST-collapse emission. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Collapsing regex fragments reduces the counted group budget and admits patterns currently refused. | Count every source variable group even when its regex fragment is deduplicated; pin `**/**/*aX` admitted and `**/**/**/*aX` refused; require before/after match/classification identity for the collapse-neutral and oracle-accepted partitions, and the exact oracle-derived `ok`/supported to `refused`/unsupported/degraded delta—without an undefined match-answer comparison—for AC-3 forms; retain 0 fail-open and 0 fail-closed over oracle-loadable blocks. |
| A plausible benchmark or self-selected family is mistaken for a universal ceiling. | Run AC-5's predeclared finite Cartesian product with its fixed warmup/repetition/median rule, retain the JSON artifact, call the result only the slowest observation in that corpus, and leave aggregate ownership with the ten-second worker deadline. |
| Escaped-slash refusal becomes a local opinion that diverges from the real builder. | Cross-check the exact pattern family against pathspec/MkDocs and assert `publication.unsupported_patterns` plus degraded output. |
| The follow-up accidentally changes the public runner or timeout envelope. | Keep runner code out of the edit surface and retain focused CLI/MCP timeout preservation tests. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
