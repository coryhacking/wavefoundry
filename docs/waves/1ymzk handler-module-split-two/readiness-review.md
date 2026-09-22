# Handler Module Split Two Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Phase: readiness. Context: `handler-split-two-readiness-20260921`. This reviews the two plans, not delivered behavior; nothing is implemented.

## Council

Seats ran in separate fresh contexts against the admitted change docs, the wave record and the `1y0h2` precedent: `red-team` (fixed) and `architecture-reviewer` (rotating, bound to the receipt). The code-reviewer and qa-reviewer readiness lanes ran in the same round, also fresh and independent. All four verified plan claims against the tree with AST walks, greps and live reads rather than the plans' prose. The QA lane also ran the eight test modules the plans rely on (1,206 tests green in per-file isolation) and confirmed the whole-suite receipt hash matches the tree.

Strongest challenge (red-team): the memory plan classified thirty-one definitions and said nothing about the fourteen module-level objects the family owns (caps, two caches, a bypass sentinel, a token regex), which are reached from `WaveIndex`, a byte-identical closure, a staying definition and about twenty test sites; moved without re-export, two public tools raise `NameError`. For techdocs, a source-text allowlist test asserts only `server_impl.py` calls the baseline renderer and fails in both directions after the move.

Strongest alternative (architecture): move the two close-gate compositions too and have lifecycle code import the handler module. Rejected: they are lifecycle-gate logic calling public memory entry points, and their eventual home is the lifecycle-gate modules; the plan's original reason for keeping them ("inverts the dependency direction") was false and is replaced by the domain-ownership criterion.

## Findings and repair

Blocking, all repaired in one pass:

- Memory: the move criterion contradicted itself (caller-location rule plus re-exported movers); replaced by domain ownership. Five memory-named definitions stay (two close-gate compositions; three crediting extractors bound in the context-efficiency registry, which raises the outside-called count from three to six). `_draft_view` and `_credit_exploration_avoided_surface` move under the corrected rule.
- Memory: fourteen module-level objects classified as move-and-re-export; re-exporting a dict shares the object so cache clears through `server_impl` keep working.
- Memory: the patch-transparency claim was false for moved-to-moved calls; narrowed, with the four affected sites named and repointed, and the `1y0h2` inert-by-design rule extended to memory names. `project_state_publication_lock` is read through `server_impl` at call time because a test patches it there.
- Memory: the two-process coherence class loses its stated premise for moved code; the plan now corrects the docstring, adds an explicit distinct-cache assertion, and names the child-process class as the fallback.
- Both: the wave owes a before-and-after standing-evaluation receipt pair because `server_impl.py` is a production retrieval module; the first draft made the rerun conditional on the new module joining the list. The before-receipt precedes the techdocs move's first edit; the deviation path is recorded if the current evaluator cannot compare against the standing report.
- Techdocs: the renderer allowlist test and the lifecycle advisory-site census are named edits; two constants and an annotation-only class name were missing from the inventory.

Nonblocking, also folded: `WaveIndex`, `_diagnostic`, `read_review_event_ledger` and `record_paths` as reached names; `_load_script` indirection retained with its three reasons (namespaced reload, patch seams, module identity); `memory_eval.py` not inverted because it threads one `srv` handle for five attributes, two of which do not move; `memory_cli.py` inversion honest about transitive load; existing test modules are the transport-free coverage and the plans add only boundary, identity, reload and derivation tests; the parameterized reload proof; `memory_handlers` does not join `PRODUCTION_RETRIEVAL_MODULES` (three independent closures agree); `domain-map.md` and a `layering-rules.md` boundary row join the affected docs; the intra-wave order is a declared dependency.

Docs-contract seat (ran last, after the receipt rotated its seat to docs-contract-reviewer because the plans declare architecture docs): approved both plans with nonblocking findings, all folded: the checkpoint line names it; the wave objective no longer claims `memory_eval.py` is inverted; the technical-writer's edits are listed in full; the two standing-baseline references that still name the superseded `post-1wybs` receipt are corrected in `1ymzj`; the receipt files are named; the "both siblings" wording in two architecture docs is updated. It also noted a tooling defect worth a plan: the machine-written context-efficiency block in the wave record contains the word "prompt", which steers the rotating-seat heuristic.

Requested lane settings: host default model and effort for all seats and lanes, chosen because plan review against a 29,000-line module needs judgment and each lane is bounded. Observed runtime identity: unknown.

Limits: no implementation; the QA lane's runs were per-file, not the full suite; reachability closures are name-based and do not follow `_load_script` string dispatch, which the committed inventory greps for; the two-process trace is by reading, not execution.

## Focused verification

Two fresh verifiers, one per plan, checked every blocking finding against the repaired text and the tree. Both approved; every item resolved. Each raised precision notes (the underscore-name count in the precedent blocks is fifty-eight, not thirty-eight; one convention for `_diagnostic` across the two plans; the census wording; `_lifecycle_id_tokens` moves with its only callers), folded in before this record was written. Known-bad detection in this round: the self-contradicting move criterion, the unclassified module-level state, the false patch-transparency claim, the conditional receipt rerun and the unnamed source-text test were all detected by the seats and lanes and corrected; the readiness rule of one full review, one bounded repair and one focused verification was followed. Verdict: approved; no readiness blockers remain.

## Scope-neutral currency refresh (2026-09-21)

Removed the wave follow-up and memory out-of-scope bullet for the already-completed `server_impl.Any`/`Optional` cleanup. Independent reviewer `/root/split_currency`, context `1ymzk-currency-review-20260921`, verified zero occurrences using MCP exact search and an independent AST walk, with direct typing imports in both existing handler modules. All move/stay, reload, identity, test and evaluation obligations remain unchanged. Council, code, QA and architecture currency judgments approve against receipt `review-policy-d1082f21160fa68da0de`. This is one fresh shared context for a bounded currency refresh, not four new full reviews. The prior false premise is the negative control. Exact removed lines were supplied by the coordinator because the wave folder was untracked; no implementation tests ran in this check.

## Baseline pin repair (2026-09-21)

Context: `1ymzk-baseline-pin-repair-20260921`. The `1ymzq` index lane, reading `tests/test_docs_lint.py` against `1ymzj` Requirement 5, found that the standing-baseline repoint would break `EvaluatorEditBaselinePolicyPinTests`, which pins the literal `retrieval-quality-post-1wybs.json` in `review-and-evals.md` and `testing-architecture.md` and the exact `--baseline` argument. Repair: one sentence in Requirement 5 names the pin as part of the same change, the test file joins the serialization points, and a progress-log row records the source. Scope-bounded currency approvals recorded on the rotated receipt; the original readiness judgment stands.
