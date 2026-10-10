# Architecture, Docs Contract and Performance Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-10-08

Wave: `206og rust-graph-accuracy`
Change: `206of-bug rust-graph-identity-and-provenance`

## Review boundary

Fresh independent reviewer context, inherited capable model; actual runtime model and effort identity are not exposed. Initial-delivery review only. Six-minute target budget; targeted public-producer controls and mutants per risk, broader tests only for surviving mutants. Frozen input hashes: `/tmp/wf-206og-frozen.json`; all reviewed hashes matched on final readback. No source edit occurred during this review. Existing code/QA findings about initializer binding visibility and module-qualified calls were read and are not duplicated here.

## Verdict

Architecture and documentation boundary checks pass within the bounded evidence below. Performance approval is withheld for `rust-binding-lookup-quadratic`. The wave has blocking findings and is not delivery-approved. Full-suite receipt, Tensorwell qualification and operator signoff are outside this review's evidence.

## Architecture and documentation evidence

MCP-first source reads confirmed the explicit trait/type fields, trait-qualified IDs and unique implementing-type aliases; occurrence facts resolve before union and use existing JSON attributes. No SQLite schema change was introduced. Builder 54 retires predecessor extraction caches. Public projection copies edge and occurrence data; a missing occurrence removes precise `line`, including non-Rust edges. The MCP spec explicitly documents that intentional compatibility change and preserves target/confidence semantics. The changelog documents builder transition and source-dependent rebuild time. RELIABILITY binds the current graph builder to 54. Architecture documents describe original UTF-8 spans, conservative loop scope, failure refusal and coherent pins.

Executed the canonical public-producer regression cases independently: snapshot response isolation, failed predecessor rebuild, generation pins, non-Rust target/confidence preservation and predecessor per-file cache retirement. Five tests passed with zero skips/errors. These test fixtures establish representational and query behavior; they do not prove all Rust forms or live downstream source quality. Two in-memory production-function mutants were killed by the public path without changing repository sources.

The existing initializer-shadow finding violates the architecture's lexical-scope claim until repaired. The existing qualified-call finding requires a focused identity repair. Architecture approval is limited to the unaffected storage/API/cache boundaries and must be reverified if those boundaries change.

## Performance finding

`rust-binding-lookup-quadratic`, severity medium, disposition do_now, blocking performance-reviewer. `_RustLexicalFacts.declaration` constructs all preceding declarations and takes a maximum for every receiver lookup. A single block with N successive `let p: P = P; p.hit();` bindings therefore performs quadratic declaration comparisons. Per-file facts avoid tree rescans but do not bound same-name lookup growth as the readiness design requires.

Actual canonical `GraphIndexSession._extract_tree_sitter_artifact` measurements used one interpreter and grammar, three repetitions, minimum time, valid generic fixtures and assertions of exactly N proven `P.hit` occurrences. Results:

| Calls | Plain repeated calls, seconds | Repeated same-name binding, seconds | Associated-array loops with macro calls, seconds |
| --- | ---: | ---: | ---: |
| 250 | 0.017073 | 0.042846 | 0.049696 |
| 500 | 0.029277 | 0.108849 | 0.101306 |
| 1000 | 0.057179 | 0.299142 | 0.194661 |
| 2000 | 0.121692 | 0.982510 | 0.393444 |

All three retain exactly 250/500/1000/2000 occurrences. Serialized output grows approximately linearly: repeated-binding artifacts are 71,522/141,160/281,166/563,166 bytes. Plain calls and macro loops have approximately linear timing; repeated binding growth is materially superlinear, matching the source-level quadratic mechanism. No arbitrary production latency threshold is claimed. Requested repair: keep per-scope/per-name declaration positions ordered and use bounded lookup, respecting declaration visibility (including the separately reported initializer case). Reverify source-growth comparisons and exact targets/spans, not merely timing or counts.

A deterministic canonical-producer control additionally wraps the per-name declaration lists solely to count yielded candidates. At 64/128/256 same-name bindings, lookup visits are exactly 4,096/16,384/65,536 (N squared), with all N target occurrences retained. An independent generous bound of eight visits per source call fails by assertion at each size. This isolates candidate visitation from elapsed-time noise. Probe: `/tmp/wf-206og-perf-visitation.py`. A subsequent bounded HEAD comparison executed the same canonical extractor and fixture with the historical lookup instrumented: it visits 576/1,152/2,304/9,000 nodes for 64/128/256/1,000 calls, exactly nine nodes per call. The new lookup performs N-squared candidate visitation, so `introduced_or_worsened_by_wave=true` applies specifically to declaration-lookup complexity. This does not claim overall extraction slowdown: HEAD has other costs and collapses raw calls to one edge, and the matched comparison actually measured HEAD at 0.00416/0.01025/0.02931/0.30837 seconds versus treatment 0.00395/0.00861/0.02005/0.14801 seconds. Counts and specific lookup operations, rather than total times, establish the finding. Historical loading suppressed only the compatibility source-registration preamble in the scratch module; no index publication or compatibility result is claimed from that control. Evidence: `/tmp/wf-206og-head-perf-comparison.py` and `/tmp/wf-206og-head-perf-comparison.jsonl`.

Probe and raw results: `/tmp/wf-206og-perf-review.py`, `/tmp/wf-206og-perf-review.jsonl`.

## Mutation and integrity table

| Boundary/control | Production deviation | Independent oracle | Result |
| --- | --- | --- | --- |
| Shared query snapshot | Return original edge and occurrence objects instead of copies | Mutating returned occurrence must leave stored snapshot unchanged | One assertion failure, zero errors/skips; detected |
| Failed old-builder refresh | Remove graph-auto-rebuild diagnostic refusal from query-index construction | Public response must be error with no incompatible edges | One assertion failure, zero errors/skips; detected |
| Bounded lexical lookup | Existing repeated-name linear scan per occurrence | Matched call-count corpus, deterministic N-squared candidate visitation and source complexity audit | Three bounded-visitation assertions detect the bad implementation; actionable finding |

Executed mutation script: `/tmp/wf-206og-architecture-mutations.py`; results: `/tmp/wf-206og-architecture-mutations.jsonl`. Mutants were in-memory and scoped, restored immediately, and exercised real scratch SQLite publication/public query behavior. There were no surviving mutants requiring whole-file expansion.

Integrity facts for architecture/docs approval: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`. Known-bad detection used production-function snapshot-alias and failed-rebuild-refusal mutants, each caught by an assertion rather than a harness error. Performance approval remains withheld; its canonical extraction path was reached with no skips, realistic source forms, non-vacuous occurrence assertions and directly observed bad complexity.

## Preservation limits

No live Tensorwell access, full suite rerun, native platform test, generic trait solver, arbitrary macro expansion or broader Rust call recall is claimed. Five public controls and three finite synthetic extraction corpora were executed. The source frozen at review retains both known code/QA defects plus the newly identified lookup-growth defect; coordinator collects findings before one bounded repair and fresh rebrief.
