# Graph accuracy: extend same-package/same-scope receiver disambiguation to Rust and C#

Change ID: `1p9q5-enh same-package-disambiguation-rust-csharp`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

When a receiver type appears with no explicit import, the cross-file pass can disambiguate an otherwise-ambiguous candidate set by preferring a same-package/same-directory definition — but this mechanism is deliberately gated to **Java, Kotlin, and Go only** (v25 entry in the `GRAPH_BUILDER_VERSION` changelog, `graph_indexer.py:35`), because those languages make same-package visibility an actual language rule (Java/Kotlin package scope; Go package-authoritative resolution). Python/JS/TS were excluded correctly (no same-directory implicit visibility). Rust and C# were excluded conservatively, yet both have well-defined analogues:

- **Rust:** items in the same module (same file, or the module tree under `mod`/`use crate::` semantics) are visible without `use`; a receiver type defined in the same module file is same-scope by language rule.
- **C#:** types in the same namespace are visible without a `using` directive; files declaring the same `namespace X` share scope regardless of directory.

The v25 work already built the per-language mechanism table and the import-edge disambiguation for Rust/C# (`graph_indexer.py:35` changelog); this change extends the *no-import same-scope* tier to the two languages where it is semantically justified, keyed on language-correct scope (Rust: module path; C#: declared namespace — **not** directory, which would over-bind C#). Ambiguity within the same scope still refuses to bind. The multi-language consumer test pack (Java/Swift/JS-TS today) gains Rust/C# same-scope fixtures as the oracle.

## Requirements

1. **Rust same-module tier.** For an ambiguous receiver-type candidate set with no resolving `use`, prefer a candidate defined in the same Rust module scope (same file; plus `mod`-declared child modules where the existing extractor already models them). Multiple same-module candidates → stay `external::`.
2. **C# same-namespace tier.** For an ambiguous receiver-type candidate set with no resolving `using`, prefer a candidate whose file declares the identical namespace (exact namespace string match, including file-scoped namespace declarations). Directory location is explicitly not a signal. Multiple same-namespace candidates → stay `external::`.
3. **Tier ordering preserved.** The new tier slots exactly where Java/Kotlin/Go's does: after explicit-import resolution fails, before falling back to `external::`. No change to any other language.
4. **Faithfulness invariants.** Unique-within-scope only; adversarial twin tests: same-name types in two namespaces/modules, same-name types twice in one namespace/module (must refuse), aliasing (`use ... as`, C# `using X = ...`) must not confuse the tier.
5. **Calibration gate.** Multi-language pack gains Rust and C# fixtures exercising the tier (positive + refusal cases); before/after edge-confidence/binding counts on those fixtures recorded.
6. **Version bump + adversarial review.** `GRAPH_BUILDER_VERSION` bumped; adversarial faithfulness review lane at wave review (standing rule for binding changes).

## Scope

**Problem statement:** Rust and C# receiver types defined in the same language scope as their call site stay `external::` when no explicit import exists, even though both languages guarantee same-scope visibility — a recall gap the Java/Kotlin/Go tier already solves for those languages.

**In scope:**

- The same-scope disambiguation tier for Rust (module) and C# (declared namespace), including file-scoped C# namespaces.
- Scope-model plumbing where the extractors don't already record it (C# namespace per definition; Rust module path as modeled today).
- Adversarial twin/refusal/alias tests; Rust + C# fixtures in the multi-language pack; calibration counts.
- Version bump.

**Out of scope:**

- Python/JS/TS/Ruby/PHP same-directory tiers (no language-rule basis — explicitly a standing refusal, recorded here so it isn't re-litigated per wave).
- Rust cross-crate resolution, `pub use` re-export graphs beyond the existing barrel-hop cap (`_TS_BARREL_RESOLVE_MAX_HOPS` analogue behavior unchanged).
- C# `global using` / implicit usings from SDK project files (build-system coupling; documented limitation).
- Any change to the explicit-import disambiguation tier.

## Acceptance Criteria

- [ ] AC-1: Rust — an ambiguous receiver type with a same-module definition binds to it (`RECEIVER_RESOLVED` path unchanged in confidence semantics); two same-module candidates refuse. Unit-tested both ways.
- [ ] AC-2: C# — an ambiguous receiver type with a same-declared-namespace definition binds (block-scoped and file-scoped namespace forms); two same-namespace candidates refuse; same directory but different namespace does NOT bind. Namespace scope keys are normalized across declaration styles: nested blocks (`namespace A { namespace B {`), compound (`namespace A.B {`), and file-scoped (`namespace A.B;`) all yield the identical key `A.B` (council finding, prepare review 2026-07-03). Unit-tested all three ways plus the three-style normalization equivalence.
- [ ] AC-3: Alias forms (`use x as y`, `using Alias = Ns.Type`) resolve through the existing explicit tier and are not double-handled or confused by the new tier. Unit-tested.
- [ ] AC-4: No behavior change for any other language — the tier gate list is explicit and tested (a Python/TS fixture with the same shape stays `external::`).
- [ ] AC-5: Multi-language pack Rust/C# fixtures added and passing; before/after binding counts on those fixtures recorded in the Progress Log.
- [ ] AC-6: `GRAPH_BUILDER_VERSION` bumped; adversarial review lane run at wave review; findings dispositioned.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [ ] Record/verify scope keys at extraction: C# declared namespace per type/definition (both namespace forms); Rust module path as currently modeled — extend only if the existing model lacks the same-file case.
- [ ] Extend the same-scope disambiguation tier's language gate + scope-comparison logic for Rust (module) and C# (namespace), preserving tier order and refusal semantics.
- [ ] Adversarial tests: twins across scopes, twins within scope (refuse), aliases, other-language non-change; Rust/C# multi-lang pack fixtures.
- [ ] Calibration counts before/after on pack fixtures; record in Progress Log.
- [ ] Bump `GRAPH_BUILDER_VERSION` with changelog entry; run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-scope-keys | implementer | — | Namespace/module scope recording at extraction where missing. |
| ws2-tier-extension | implementer | ws1-scope-keys | Language-gate + scope-comparison extension in the cross-file pass; refusal semantics. |
| ws3-tests-calibration | implementer | ws2-tier-extension | Adversarial + pack fixtures; calibration counts. |
| ws4-adversarial-review | reviewer | ws3-tests-calibration | Faithfulness red-team: what namespace/module shapes could bind the wrong twin? |


## Serialization Points

- Shares the cross-file resolution pass with `1p9q4` (Python) — disjoint language branches, but coordinate the single wave-level `GRAPH_BUILDER_VERSION` bump and merge order on `graph_indexer.py`.
- Multi-language pack fixture layout shared with `1p9q7` (DI fixtures) — agree the fixture directory convention once.

## Affected Architecture Docs

Update the per-language resolution capability documentation (same surfaces as `1p9q4`: `docs/specs/mcp-tool-surface.md` code-tool notes and any capability matrix): the same-scope tier's language list becomes Java/Kotlin/Go/Rust/C#, with the Python/JS/TS refusal recorded as a standing decision. No boundary/flow impact.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The Rust tier is half the change. |
| AC-2 | required | The C# tier is the other half; the directory-is-not-namespace refusal is its critical faithfulness edge. |
| AC-3 | required | Alias confusion is the likeliest silent-wrong-bind path. |
| AC-4 | required | Language-gate leakage would change untested languages' graphs silently. |
| AC-5 | required | The pack is the standing real-world oracle for cross-language resolution changes. |
| AC-6 | required | Standing version-bump and adversarial-review rules for binding changes. |
| AC-7 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Confirmed: same-package tier gated to Java/Kotlin/Go by design (v25 changelog, `graph_indexer.py:35`); Rust/C# import-edge disambiguation mechanisms already exist from v25; Rust/C# resolvers at `graph_indexer.py:3493,~5000s`; multi-lang pack currently Java/Swift/JS-TS (no Rust/C# fixtures). | `graph_indexer.py:35,3493`; evaluation 2026-07-03; multi-lang pack memory (p4ea). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Key C# on declared namespace and Rust on module scope — language rules, not directories (approach A). | Mirrors why Java/Kotlin/Go qualified: the language itself guarantees same-scope visibility, so the bind is semantics-backed, not layout-backed; directory keying would over-bind C# (namespace ≠ folder) and under/over-bind Rust (module tree ≠ directory tree with `path` attrs). | (B) Directory-based keying for both — weakness: binds on incidental file layout; exactly the guess the faithfulness stance forbids. (C) Also add Python/JS/TS same-directory tiers — weakness: no language-rule basis; rejected as a standing decision to prevent per-wave re-litigation. |
| 2026-07-03 | Exclude C# `global using`/implicit usings. | They live in project files/SDK defaults outside the indexed source model; consuming build metadata couples the indexer to toolchain files. Documented limitation with the refusal (stay `external::`) as the safe default. | Parse `.csproj`/`GlobalUsings.g.cs` — deferred; revisit only on field evidence that the gap materially depresses C# recall. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| C# file-scoped vs block-scoped namespace forms handled inconsistently → missed or wrong scope keys. | Both forms are explicit AC-2 test cases; scope key is the declared string, one extraction path for both forms. |
| Rust module-model gaps (inline `mod` blocks, `path` attributes) cause wrong same-module conclusions. | Tier only consults the module model the extractor already maintains; unmodeled forms fall through to refusal (`external::`), never to a guess; adversarial review targets exactly these shapes. |
| Tier interacts with import-edge disambiguation double-binding an alias. | AC-3 alias tests; tier order is explicit (only after import resolution fails). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
