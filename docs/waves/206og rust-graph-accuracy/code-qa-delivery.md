# Rust graph independent code and QA delivery review

Owner: Engineering
Status: active
Last verified: 2026-10-08

Review context: `rust-code-qa-delivery-206og-20261008`, fresh independent code-reviewer and qa-reviewer context; this reviewer did not implement. Runtime model identity is unknown. This report is a durable consolidated reference for reproducible counterexamples and the mutation table requested by the coordinator; the typed ledger remains authority. The selected review budget was eight minutes, with targeted tests per mutant and no whole-file rerun for killed mutants.

**Verdict: changes required.** Two bounded, compiler-valid fixtures expose incorrect or missing project relationships. No delivery approval is recorded by this reviewer. All 13 frozen-path hashes still match `/tmp/wf-206og-frozen.json` at report time.

## Independently executed evidence

The independent reference is lexical Rust binding visibility and explicit trait/type/module identity, read against the readiness design contract and original Tensorwell report. Fixtures were produced through `_RepoDriver` extraction/merge/SQLite publication, with `index_state_store.begin_build_epoch` and `finalize_build_epoch`; results were consumed through real `code_callgraph_response`, not just resolver helpers. `rustc --crate-type lib --emit metadata` accepted both defect fixtures with exit 0, confirming valid reachable Rust shapes.

- `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_graph_rust_provenance.py -v`: nine tests, zero failures/errors/skips. Real public projection retains macro/UTF-8 occurrences, repeat multiplicity, immutable responses, builder-53 invalidation, failed refresh refusal and pinned generations.
- `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_graph_call_integrity.py -v`: 46 tests, zero failures/errors/skips. Supported loops, trait identities, unique cross-file candidates, unknown receivers, established language controls and `.collect()` controls execute successfully.
- Independent initializer fixture below: one expected assertion failure, zero setup errors/skips; the public response merges both expressions into `R.hit`.
- Independent inline-module fixture below: one expected assertion failure, zero setup errors/skips; the public response emits two external relationships instead of the two explicit project targets.

## CODE-DEL-1: let binding becomes visible during its own initializer

File and anchor: `.wavefoundry/framework/scripts/graph_indexer.py`, `_RustLexicalFacts.declaration`, the `entry.start_byte < ref.start_byte` visibility predicate. Class: incorrect lexical scope. Confidence: high. Severity: medium correctness impact, repository-local. Reachability: supported.

```rust
struct P; struct R;
impl P { fn hit(&self) -> R { R } }
impl R { fn hit(&self) -> R { R } }
fn run(p: P) { let p: R = p.hit(); p.hit(); }
```

Expected: the initializer's expression at UTF-8 bytes `[118,125)` resolves to `types.rs::P.hit`; the later expression `[127,134)` resolves to `types.rs::R.hit`. Observed: both proven occurrences belong to one `types.rs::R.hit` edge, confidence `RECEIVER_RESOLVED`. The genuine initializer relationship to P is lost. A HEAD extractor comparison, loaded in scratch with only its source-registration hook bypassed, produces aggregate P.hit instead; the new resolver specifically introduces the false R attribution for the initializer. That historical aggregate is not a complete correctness oracle for the later call.

Reproducer: `/tmp/wf-206og-independent-code-qa.py`. The independent assertion locates the initializer by exact source byte offset and requires its target P.hit. Repair hypothesis: a let declaration may supply a binding only after its initializer has completed; an initializer lookup must continue to an earlier visible lexical binding. Preserve visibility for following expressions and unknown-shadow refusal.

## CODE-DEL-2: qualified module receivers do not match callable aliases

File and anchors: `.wavefoundry/framework/scripts/graph_indexer.py`, `_resolve_rust_call_target`, `_rust_method_alias`, `_build_candidate_indexes`. Class: retained genuine relationship missing. Confidence: high. Severity: medium correctness/coverage impact, repository-local. Reachability: supported. This report does not establish a historical introduction date; the gap prevents the admitted qualified inline-module contract from being satisfied.

```rust
trait T { fn hit(); }
mod a { use crate::T; pub struct P; impl T for P { fn hit() {} } }
mod b { use crate::T; pub struct P; impl T for P { fn hit() {} } }
fn run() { a::P::hit(); b::P::hit(); }
```

Expected: distinct caller relationships to `types.rs::a.<P as T>.hit` and `types.rs::b.<P as T>.hit`, with occurrences `[167,178)` and `[180,191)`. Observed: nodes retain those distinct IDs, but the public relationships target `external::a::P.hit` and `external::b::P.hit`, confidence `EXTRACTED`. Proven spans are accurate; project incoming relationships are absent. `_resolve_rust_call_target` keeps receiver scope as `a::P`, whereas extracted module-qualified implementing aliases are dotted `a.P.hit`.

Reproducer: `/tmp/wf-206og-qualified-probe.py`. Repair hypothesis: normalize supported explicit receiver paths into the same qualified-name representation used by definition/alias indexing, preserving implementing type, module scope and trait ambiguity. Do not enable name-only lookup or first-candidate selection. Tests must retain unknown and ambiguous controls.

## AC assessment

| AC | Current evidence and verdict |
| --- | --- |
| AC-1 | Macro, unrelated method, UTF-8 and neighbor-caller fixture survives actual storage/public projection; passing bounded evidence |
| AC-2 | Repeated occurrences, no guessed line, incremental replacement and immutable/pinned responses pass; repeat-discard mutant fails a named assertion |
| AC-3 | Distinct same-file and unqualified cross-file trait nodes/targets pass; explicit inline-module receiver fixture fails, so required criterion is incomplete |
| AC-4 | Existing supported-array and unknown/later/sibling shadow controls pass; valid own-initializer lexical fixture fails, so required criterion is incomplete |
| AC-5 | Existing conservative receiver and `.collect()` tests pass; identity, spans and genuine relationships were asserted independently rather than accepting reduced counts |
| AC-6 | Previous-builder per-file cache, occurrence-only fingerprint, failed refresh and pinned generation tests pass; canonical full suite remains a coordinator-run check not independently asserted here |

## Mutation and known-bad table

| Control | Targeted test / independent oracle | Expected | Observed |
| --- | --- | --- | --- |
| Discard all but first occurrence inside `_merge_call_evidence` (runtime monkeypatch in scratch process) | `RustPublishedProvenanceTests.test_exact_receiver_spans_survive_extraction_storage_and_public_projection` | Assertion detects lost repeat | One assertion failure, zero errors/skips; killed, no whole-file rerun |
| Live new lexical visibility defect | Exact initializer offset must target P.hit | Assertion detects incorrect target | One assertion failure, zero errors/skips; real public path reached |
| Live qualified-receiver mismatch | Set of explicit targets must equal a/b trait-qualified project IDs | Assertion detects genuine relationship loss | One assertion failure, zero errors/skips; real public path reached |

Both defect findings truthfully affirm `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, and `known_bad_detected`. The method is executed live defect for findings and focused mutation for repeat-loss coverage. Scratch files and fixture databases only; no frozen repository source edits, external actions, release operations, closure, commits or pushes.

## Limits

This is bounded evidence, not a universal Rust type-checker or exhaustive macro proof. Arbitrary adapters, generic dispatch and macro expansion remain out of scope. Tensorwell's live repository was unavailable. The canonical full suite was running under the coordinator when this verdict was formed; its eventual result cannot erase these directly observed counterexamples. Native Windows behavior and broad production performance were not independently measured. Prior implementer performance data was inspected as reported evidence only, not reclassified as this reviewer's independent measurement.
