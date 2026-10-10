# Preserve Rust graph identity, provenance and bounded loop resolution

Change ID: `206of-bug rust-graph-identity-and-provenance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-08
Wave: `206og rust-graph-accuracy`

## Rationale

Tensorwell reports three actionable graph-accuracy defects after local pack `1.29.0+pvbx`, verified there with live MCP, stored records and parser/resolver probes while indexes and setup were current. This plan preserves that evidence without claiming a local reproduction. The audience is graph consumers relying on accurate navigation and retained genuine caller relationships. Deliver one cohesive extraction-to-query repair with independent tests for target identity, expression location and relationship coverage.

Correction to the earlier assessment: `execute → Profile.as_str` is a genuine relationship. Its reported line 297 belongs to `VERSION.as_str()`; the intended call is at line 384. This is incorrect provenance, not a false target relationship. The loop-binding coverage gap has no established introduction version. The earlier `.collect()` improvement remains valid.

## Reported evidence

Paths in this section belong to the reporting Tensorwell checkout; they are evidence references, not files in this repository.

- Query: `code_callgraph(symbol="crates/tensorwell-inference/src/profile.rs::Profile.as_str", direction="callers", include_tests=true)`.
- Call-site defect: `crates/tensorwell-inference/src/main.rs::execute` resolves to `Profile.as_str` with `RECEIVER_RESOLVED`, but reports line 297 rather than the actual expression at line 384. An earlier same-name call occurs inside a macro.
- Coverage defect: at `crates/tensorwell-inference/src/profile.rs:79`, `for profile in Self::ALL` iterates an associated constant typed `[Self; 5]`. The call `profile.as_str()` remains `external::profile.as_str`, `EXTRACTED`, with `receiver_unknown` and `unowned_member_call` true.
- Identity defect: `impl FromStr for Profile` and `impl FromStr for Role` both produce `FromStr.from_str`, repeating the defined-symbol ID and retaining one node. The reporter's `_ts_name_candidates` probes identify the trait as the enclosing name.
- Local source inspection confirms label-based call-site enrichment in `wf_server/graph_handlers.py`, first-type-identifier selection in `_find_enclosing_rust_impl_type`, and no for-binding branch in `_search_rust_declarations_in_scope`. No local parser probe or Tensorwell MCP query was executed in this planning pass.

## Requirements

1. Preserve the source expression's file and span with each extracted call occurrence through receiver resolution, edge merging, graph persistence and query projection. Do not reconstruct a precise location from a simple method label. Any fallback must establish target identity and the complete caller boundary; otherwise omit the unsupported location explicitly.
2. Retain distinct occurrences when one caller invokes the same target multiple times. Define the response representation at readiness without silently overwriting occurrences or breaking existing consumers. Macro-contained expressions must retain their actual source location; this does not require arbitrary macro expansion.
3. Read Rust impl grammar fields for implementing type and optional trait. Method identity must distinguish different implementing types of the same trait, and different traits with the same method on one type. Receiver inference uses the implementing type, including `Self`; unsupported or ambiguous forms remain unresolved rather than taking the first child token.
4. Add bounded lexical inference for simple for-loop bindings whose iterable has an explicit array element type, initially local typed arrays and associated constants such as `Self::ALL: [Self; N]`. Resolve `Self` in the correct impl context. Honor binding scope and shadowing; do not infer arbitrary iterator adapters, generic trait dispatch, destructuring, or interprocedural return types.
5. Preserve the conservative unknown-member guard. Unknown or unrelated receivers must not acquire project targets by same-name matching. Retain existing `.collect()` behavior and its regression evidence.
6. Audit extraction caches, persisted graph schema and compatibility fingerprints for changed node IDs and call metadata. Use the existing invalidation/rebuild contract where needed so a current source index cannot mask an old extraction format. Fresh and incremental builds must agree on identity and call occurrences.
7. Document observable ID/location changes, multiplicity and unresolved limits. Existing records without proven locations must not be presented with fabricated precise lines. Keep unrelated language behavior compatible through focused controls.

## Readiness Design Contract

- Rust trait methods use `path::<ImplementingType as Trait>.method`; inherent methods retain `path::Type.method`. Inline module scope remains part of the qualified name. Read grammar `type` and `trait` fields; preserve normalized qualified type/trait spelling in identity. Unsupported generic dispatch stays unresolved. `Type.method` aliases are allowed only when exactly one candidate exists; ambiguous legacy `Trait.method` IDs never select a survivor silently. `Self` receiver inference uses the implementing type, separately from trait-qualified identity.
- Preserve the current edge grouping and confidence/evidence contract. Add a deterministic, deduplicated `call_sites` list to call-edge attributes: each proven occurrence carries repository-relative `source_file`, zero-based UTF-8 `start_byte` and exclusive `end_byte`, and one-based `line`, `column`, `end_line`, `end_column` (columns count UTF-8 bytes). Sort by file and byte span. A call expression belongs to its extracted caller; macro token-tree parsing must retain offsets into the original source, not the synthetic parse buffer. Occurrence evidence is resolved before union: an unknown witness must never inherit another witness's target or precision merely because an aggregate edge has a known receiver.
- MCP callgraph keeps existing edge topology and adds `call_sites`. Its optional legacy `line` is the first proven occurrence in source order, never a name scan. Unknown or legacy provenance gives an empty list and no `line`; no fallback guess is permitted. Shared query snapshots remain immutable. Non-Rust extractors may emit empty occurrence lists until they can prove spans; preserve their target/confidence behavior and document the intentional removal of unsupported guessed lines.
- Use existing JSON edge attributes for occurrences; no SQLite table or graph schema-version change is planned. Increment `GRAPH_BUILDER_VERSION` from the then-current value (currently 53) to invalidate incompatible extraction and published graph generations through existing compatibility/setup/read/query gates. Verify the per-file cache cannot reuse the previous builder's record. Rebuild failures remain not-ready; never serve a mixed old/new identity generation. Existing pins retain coherent snapshot semantics and must not be mutated in place.
- Bound loop inference to a simple identifier binding inside its own for body and a local explicitly typed array or same-file associated array constant with a uniquely resolved owner. Resolve `[Self; N]` using that declaration's impl owner. Nearest preceding lexical bindings win; an unknown shadow blocks outer inference. Exclude siblings, later declarations, outer calls and arbitrary adapters/destructuring. Build/reuse lexical facts per file/function instead of rescanning the whole file for each call.
- Performance validation uses a fixed synthetic Rust corpus with many calls/loops and repeated same-target occurrences, identical runtime/grammar and fixtures before and after. Record extraction time, edge/occurrence counts and serialized size separately; require bounded growth proportional to source calls, not a Cartesian product of callers and methods. No arbitrary latency threshold is claimed before a baseline exists.

Evidence grounding: direct source reads show `_merge_call_evidence` currently selects one witness, `graph_edges.attributes` can carry additive JSON, and `graph_query.load_graph` invokes the existing builder-version rebuild path. A fresh installed-tree-sitter probe observed separate `trait=FromStr` and `type=Profile/Role` fields, and `for_expression` pattern/value fields for `profile` and `Self::ALL`. This establishes feasibility, not completed product behavior.

## Scope

In scope: the three reported defects and the extraction, resolver, graph persistence/query, compatibility and test paths necessary to repair them. Derive affected consumers by tracing call occurrence metadata and Rust method IDs from extraction to public graph responses, including cache serialization and merge paths.

Out of scope: a general Rust type checker, arbitrary macro expansion, broad recall increases, rewriting unrelated language extractors, global graph refactors, live Tensorwell changes, release publication or outbound reporting.

## Acceptance Criteria

- [x] AC-1: A function calling unrelated types' same-name methods yields the correct target and source expression for each edge, including an earlier macro-contained call; a neighboring caller's expression cannot supply its location. Verify extracted records, persisted records and public callgraph responses against fixture source spans.
- [x] AC-2: Repeated calls to one target preserve all supported call occurrences across storage and queries, while records without proven provenance report no invented precise location. Verify both fresh and incremental builds.
- [x] AC-3: Two types implementing the same trait produce distinct method nodes, caller relationships and locations; two same-name trait methods on one type do not collapse. `Self` resolves to the implementing type in supported forms, and ambiguous forms remain unresolved.
- [x] AC-4: A loop over a supported explicitly typed array, including an associated `[Self; N]` constant, retains the genuine incoming method relationship. Lexical shadowing and unsupported or unknown iterable controls remain unresolved or resolve only to their proven type.
- [x] AC-5: Existing unknown-receiver and `.collect()` regression cases retain their intended behavior. Evaluation reports target identity, occurrence-location accuracy and retained expected relationships independently; reduced edge counts alone cannot satisfy this criterion.
- [x] AC-6: Fixtures with previous cached/persisted representations follow the documented invalidation or compatibility path; rebuilt and incremental graphs match the expected new nodes and occurrences without duplicate stale identities. The affected MCP response contract and compatibility documentation validate.

## Tasks

- [x] Reproduce all three reports in small generic Rust fixtures and record baseline extraction, stored graph and public-response evidence.
- [x] At readiness, specify qualified impl-method IDs, occurrence multiplicity in storage/API, caller boundaries and existing-index invalidation requirements.
- [x] Correct trait/type field handling and implement bounded loop-binding inference with scope controls.
- [x] Carry expression provenance through extraction, resolution, persistence and queries; retire unsupported name-only location enrichment.
- [x] Add fresh/incremental/legacy-cache regressions and separate identity, provenance and coverage evaluation results.
- [x] Update affected architecture/spec documentation and obtain independent code, architecture and QA review before delivery.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and baseline | Implementer | Readiness | Establish IDs, occurrences and cache transition |
| Extraction and resolution | Implementer | Contract | Single writer for graph_indexer.py |
| Persistence and MCP projection | Implementer | Contract and extraction | Coordinate metadata end to end |
| Independent verification | QA and code reviewers | Implementation | Read-only review; verify expected relationships, not aggregate edge counts |
| Documentation | Technical writer | Contract | Own named docs only |

## Serialization Points

One writer per graph module. Finalize the identity/provenance contract before splitting implementation work. Architecture review covers persistent IDs and API compatibility; QA independently verifies fixtures against source. The implementation census may narrow the review paths below when a module proves unaffected.

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_store.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/graph_snapshot.py`
- `.wavefoundry/framework/scripts/index_compatibility.py`
- `.wavefoundry/framework/scripts/wf_server/graph_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_call_integrity.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for source provenance through the graph pipeline; `docs/architecture/testing-architecture.md` for separate identity/location/coverage oracles; and `docs/specs/mcp-tool-surface.md` for graph ID and call occurrence output compatibility. Review the architecture hub for links if a focused graph contract document is required; no new document is presumed necessary.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Correct the reported misattributed line |
| AC-2 | required | Prevent provenance loss during edge deduplication |
| AC-3 | required | Preserve distinct trait implementations |
| AC-4 | required | Recover proven genuine loop relationships conservatively |
| AC-5 | required | Preserve precision and the earlier valid improvement |
| AC-6 | required | Deliver correct results to existing index consumers |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Observe: repair cycle 1 records all three typed repair starts before source mutation. Binding facts now sort visibility endpoints per lexical scope and name; binary search returns the nearest visible declaration, with a let becoming visible only after its initializer. Explicit scoped receiver names normalize to existing dotted module aliases without weakening unique-candidate or unknown-receiver refusal. Both independent public-query counterexamples now pass. | `test_let_initializer_uses_previous_binding_then_new_binding`, `test_initializer_loop_keeps_outer_array_type`, `test_explicit_module_receiver_paths_preserve_identity_and_ambiguity`; `/tmp/wf-206og-repair-initializer-after.log`, `/tmp/wf-206og-repair-qualified-after.log` |
| 2026-10-08 | Observe: all 50 integrity tests and nine actual-publication provenance tests pass after repair. Four executed repair mutants are killed by assertions (no errors/skips): premature visibility in method initializer; premature visibility in array initializer; restoring raw scoped receiver mismatch; restoring the full candidate scan. The deterministic producer-bound test counts iteration and indexed access and meets its eight-visits-per-call bound at 64/128/256 calls. AC-3 and AC-4 are checked again from this executed evidence; independent reverification remains pending. | `test_repeated_bindings_use_bounded_candidate_lookup`; `/tmp/wf-206og-repair-mutants.py`, `/tmp/wf-206og-repair-integrity.log`, `/tmp/wf-206og-repair-provenance.log` |
| 2026-10-08 | Observe: repeated-binding review corpus at 250/500/1,000/2,000 calls takes 16.4/35.3/85.1/221.4 ms after repair, retaining exactly N occurrences and 71,522/141,160/281,166/563,166 serialized bytes. Plain-call and macro-loop controls also retain every expected target occurrence. The fixed finding concerns declaration-candidate growth; neither these finite timings nor the review's HEAD comparison establish an overall extractor regression or a universal linear-runtime guarantee. | Fresh execution of the same review corpus and grammar; `/tmp/wf-206og-repair-perf.jsonl`; bounded candidate test and scan-restoration mutant |
| 2026-10-08 | Reflect: independent delivery found premature let visibility, module-qualified receiver mismatch and quadratic repeated-name lookup. Reopened AC-3 and AC-4; freshly reproduced both exact public-target failures and 4,096/16,384/65,536 declaration visits at 64/128/256 bindings. One bounded repair will use visibility endpoints, indexed nearest-binding lookup and canonical explicit module paths. | `code-qa-delivery.md`, `architecture-docs-performance-delivery.md`; typed repair cycle 1 |
| 2026-10-08 | Observe: implementation preserves explicit Rust trait/type identities, unique implementing-type aliases, lexical typed-array loop facts and individual call witnesses through cross-file resolution. Final call edges deduplicate and sort original UTF-8 spans; macro argument parsing retains original offsets and caller boundaries. Unsupported generic identities remain visible while unsupported self dispatch stays unresolved. Builder 54 invalidates prior extraction. | `RustIdentityProvenanceTests` (eight targeted cases); `test_graph_call_integrity.py`: 46 tests green, including existing unknown-receiver and collect controls |
| 2026-10-08 | Reflect: actual publication tests exposed two integration boundaries missed by extraction alone: occurrence-only edits reused a topology-only fingerprint, and failed builder refreshes still exposed old identities. Fingerprints now cover occurrences; both cached and uncached query paths refuse failed, skipped or in-progress incompatible rebuilds. | `test_graph_rust_provenance.py`: nine tests green after repair, including real storage, generation publication, pinned snapshots, failed refresh and prior-builder per-file caches |
| 2026-10-08 | Observe: six executed runtime mutants each produced one assertion failure and zero errors: replacing implementing owner with trait; ignoring unknown lexical shadows; guessing unsupported iterable element types; suppressing macro extraction; choosing the first ambiguous alias; and disabling unsupported-self refusal. Independent test author additionally killed dropped-repeat and wrong-target-span merge mutants. | Named pins: `test_trait_impl_identity_and_explicit_calls`, `test_typed_loops_and_lexical_unknown_shadows`, `test_macro_provenance_and_same_line_callers`, `test_ambiguous_trait_alias_stays_unresolved`, `test_generic_impl_identity_retained_but_dispatch_unresolved`; `/tmp/wf-206og-mutants.py` |
| 2026-10-08 | Observe: matched 50/100/200-call extraction minima were 1.534/2.922/5.669 ms versus baseline 1.259/2.439/4.670 ms. Treatment retains exactly 50/100/200 occurrences and uses 14,450/27,408/53,608 serialized artifact bytes; a 1,000-call extension took 28.780 ms and retained 1,000 occurrences (263,591 bytes). Raw witnesses grow with calls and merge only after resolution. This small synthetic corpus measures bounded growth, not a production latency guarantee. | `/tmp/wf-206og-baseline.json`, `/tmp/wf-206og-treatment.json`; same interpreter, grammar, fixture generator and five repetitions |
| 2026-10-08 | Observe: graph-indexer owner suite passed 549 tests before the final narrow unsupported-self guard (subsequently covered by the 46-test integrity run and its deletion mutant). Quality evaluation passed 102 tests with seven existing skips after regenerating the canonical post report for builder 54; baseline report untouched, totals unchanged at 10 true positives, zero false positives and two false negatives. Source is frozen for coordinator full-suite and independent delivery review. | `/tmp/wf-206og-indexer.log`, `/tmp/wf-206og-integrity.log`, `/tmp/wf-206og-provenance.log`, `/tmp/wf-206og-quality.log`; `docs/reports/graph-quality-post.json` |
| 2026-10-08 | Readback: implement AC-1–6 as one extraction-to-response repair. Before: unrelated `as_str` calls can lend a line to a genuine edge, trait implementations collapse, and typed loops stay unresolved. After: trait-qualified identities and individually resolved source occurrences survive storage and queries; only explicitly supported lexical loop bindings resolve. Own graph_indexer, graph handlers, focused graph tests and named contract docs; no general type checker or unrelated language inference. Inherited capable context fits this coupled parser pipeline; runtime identity is unknown. | Readiness design contract; MCP source reads and pre-implementation memory briefing |
| 2026-10-08 | Observe: scratch baseline reproduced duplicate `FromStr.from_str` IDs, unresolved associated-array loop calls, omitted macro-contained method extraction and collapsed repeated calls with no occurrence metadata. Matched 50/100/200-call extraction minima over five runs were 1.259/2.439/4.670 ms; each artifact had five edges, zero occurrences and 1,638 serialized bytes. | Actual GraphIndexSession extraction; `/tmp/wf-206og-baseline.json`; baseline counts measure information loss, not correctness |
| 2026-10-08 | Recorded Tensorwell report and correction; inspected local response/resolver code; planning only | Reported evidence and declared review targets above |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Preserve provenance end to end, qualify impl identities and add bounded inference in one graph-specific wave | The defects share extraction/resolution/storage contracts and need integrated evidence | Response-only line heuristics cannot establish receiver identity; broad Rust inference increases scope and could defeat conservative guards |
| 2026-10-08 | Keep this separate from public compatibility wave 204mp | Distinct source area, verification contract and downstream report; shared graph changes need their own review | Adding unrelated graph fixes to distribution seams would obscure readiness and delivery evidence |

## Risks

| Risk | Mitigation |
| --- | --- |
| Symbol identity changes leave stale cached nodes or break saved references | Review compatibility fingerprints and documented lookup behavior before readiness; test old and incremental records |
| Edge merging erases occurrence provenance | Choose multiplicity explicitly and test multiple calls through persistence and MCP |
| Loop inference crosses lexical scopes or guesses iterator types | Bound supported syntax and test shadowing, unknown and unrelated receivers |
| Tree-sitter forms differ for generic or qualified impl types | Probe the installed grammar fields; unsupported forms stay conservative and are documented |
| Green aggregate metrics conceal lost real relationships | Use independent expected target, source-span and coverage assertions |

## Session Handoff

Implementation and repair cycle 1 are complete. Independent code, architecture, docs-contract and performance delivery approvals are recorded; QA awaits the quiet canonical suite. All three delivery findings have independent terminal reverification. Source is frozen and the framework edit gate is closed. Memory curation rejected two generated candidates whose temporary probe targets were not durable repository paths; the reviewed contracts and named regression tests retain the lessons. No closure, commit or push is authorized in this request. See `docs/agents/session-handoff.md`.
