# Graph accuracy: Rust module-scope receiver disambiguation (+ C# verify-and-close)

Change ID: `1p9q5-enh same-package-disambiguation-rust-csharp`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1p9q8 graph-index-accuracy`

> **RE-SCOPED 2026-07-05 (freshness + re-readiness + operator decision).** Two findings changed this change: (1) the **C# same-namespace tier is ALREADY IMPLEMENTED** (Wave `1p4ev`, `graph_indexer.py:9040-9057`) — own-namespace ∪ `using`, declared-namespace longest-prefix keying (directory not a signal), unique-survivor refusal — so C# reduces to a **verify-and-close** on namespace-key normalization. (2) The Rust half is **NOT** a bounded "add an elif branch": the re-readiness primer confirmed the extractor models **no Rust module scope at all** (no `mod_item` modeling; `declared_package` is Java/Kotlin-only), and "same file" is not Rust's visibility rule (cross-file visibility is the module tree, not the directory; inline `mod {}` blocks are separate scopes in one file). **Operator decision 2026-07-05: FUND Rust module-tree modeling in this wave** as explicit new scope — so this change now BUILDS the Rust module-path model that the same-scope disambiguation tier keys on. This is a materially larger increment with its own faithfulness surface (module resolution), not a same-directory heuristic.

## Rationale

When a receiver type appears with no explicit import, the cross-file pass disambiguates an otherwise-ambiguous candidate set by preferring a definition in the same language-defined scope. This tier is gated to **Java, Kotlin, Go** (Wave `1p4er`, `graph_indexer.py:9005-9039`, directory=package by language rule) and **C#** (Wave `1p4ev`, `:9040-9057`, declared namespace). **Rust is the genuine remaining gap** — no `.rs` branch exists in the disambiguation elif chain, and `1p4eu`'s Rust work is receiver-type *inference*, not same-scope disambiguation.

Rust's visibility rule is the **module tree**, not the directory tree: items in the same module are visible without `use`; the module a definition belongs to is determined by `mod` declarations (`mod foo;` → `foo.rs` or `foo/mod.rs`), inline `mod foo { … }` blocks (separate nested scopes within one file), and `#[path = "…"]` overrides — none of which the directory determines. To disambiguate faithfully by "same Rust scope," the extractor must first MODEL each definition's module path, then the tier keys on module-path equality. Keying on the raw file path would be wrong both ways (over-binds across inline modules in one file; misses genuine same-module definitions split across `mod`-declared files). This change builds that model and the tier; ambiguity within a module still refuses to bind.

## Requirements

1. **Rust module-path model (new scope plumbing — the bulk of this change).** During Rust extraction, derive a module-path scope key for each definition:
   - **File→module mapping**: a crate-root file (`lib.rs`/`main.rs`) is module `crate`; `mod foo;` in a module maps `foo.rs` / `foo/mod.rs` (2018 edition) to child module `crate::…::foo`; `#[path = "…"]` overrides the file. Where the crate root is ambiguous or a file is unreachable from any `mod` decl (common for partial indexing), fall back to a per-file module identity and record it as such (never guess a parent).
   - **Inline modules**: `mod foo { … }` creates a nested module scope; definitions inside key to `…::foo`, definitions outside do NOT. Multiple inline `mod` blocks in one file are distinct scopes.
   - The model is bounded to what the source declares (no cross-crate resolution, no `pub use` re-export graph beyond the existing barrel-hop cap); unmodeled/uncertain forms fall through to refusal, never to a guess.
2. **Rust same-module disambiguation tier.** For an ambiguous receiver-type candidate set with no resolving `use`, prefer the candidate whose module-path key equals the call site's module-path key. Exactly one survivor → bind (`RECEIVER_RESOLVED` semantics unchanged); zero or multiple → stay `external::`. Slots exactly where the Java/Kotlin/Go/C# tiers do (after explicit-import resolution fails, before `external::`).
3. **C# verify-and-close.** The C# tier already binds/refuses correctly. Verify ONLY that `cs_file_ns` (`graph_indexer.py:8720-8733`) normalizes file-scoped (`namespace A.B;`), compound (`namespace A.B {`), and nested-block (`namespace A { namespace B {`) forms to the identical key `A.B`; if a gap exists, fix the normalization; if already correct, pin it with a regression test and record it closed. No new C# tier work.
4. **Faithfulness invariants.** Unique-within-scope only. Adversarial Rust twin tests: same-name types in two different modules (bind the same-module one), same-name types twice in one module (refuse), a type in an inline `mod` vs one at file scope (different scopes — must NOT cross-bind), `#[path]`-relocated modules, `use x as y` aliasing must not confuse the tier. C# regression: the three namespace-declaration styles resolve to one key; directory-differs-namespace-same still binds, directory-same-namespace-differs does not.
5. **Calibration gate.** The multi-language consumer pack (Java/Swift/JS-TS today) gains **Rust** fixtures exercising the module model + tier (positive binds, inline-mod separation, refusal cases) as the real-world oracle; before/after binding/confidence counts recorded. C# regression fixtures pin the existing behavior.
6. **Version bump + adversarial review.** `GRAPH_BUILDER_VERSION` bumped (coordinated single 39→40 at wave integration); the mandatory adversarial-faithfulness review lane runs at wave review — the Rust module model is a NEW binding surface and its wrong-scope-bind modes are the primary target.

## Scope

**Problem statement:** Rust receiver types defined in the same module as their call site stay `external::` when no `use` exists, because the extractor models no Rust module scope — a recall gap the Java/Kotlin/Go/C# same-scope tiers already solve for those languages. Closing it requires building a Rust module-path model, then keying the disambiguation tier on it.

**In scope:**

- A Rust module-path model at extraction: `mod`-declaration file mapping (`foo.rs`/`foo/mod.rs`), inline `mod {}` nesting, `#[path]` overrides, crate-root identification, per-file fallback identity for unreachable files.
- The Rust same-module disambiguation tier keyed on module-path equality, slotting into the existing elif chain with unchanged tier order and refusal semantics.
- The C# verify-and-close on `cs_file_ns` three-style normalization (fix-or-pin).
- Adversarial Rust twin/inline-mod/`#[path]`/alias tests; Rust multi-language pack fixtures + calibration counts; C# regression pins.
- Version bump.

**Out of scope:**

- Python/JS/TS/Ruby/PHP same-directory tiers (no language-rule basis — standing refusal, recorded so it isn't re-litigated per wave).
- Rust cross-crate resolution and `pub use` re-export graphs beyond the existing barrel-hop cap.
- C# `global using` / SDK implicit usings (build-system coupling; documented limitation) and any new C# tier work (the tier exists).
- Any change to the explicit-import disambiguation tier.

## Acceptance Criteria

- [x] AC-1: **Rust module model** — unit tests prove the module-path key is derived correctly for: a crate-root definition (`crate`), a `mod foo;` file definition (`crate::foo`), a definition inside an inline `mod bar {}` (`…::bar`) vs one outside it (distinct keys), and a `#[path]`-relocated module; an unreachable/ambiguous file falls to a per-file identity (never a guessed parent). Evidence: `test_rust_module_model_crate_root_mod_decl_inline_and_path`, `test_rust_module_model_2018_edition_and_mod_rs_forms`, `test_rust_module_model_unreachable_files_get_distinct_fallback` (`_build_rust_module_index` / `_rust_module_key` in `graph_indexer.py`).
- [x] AC-2: **Rust tier** — an ambiguous receiver type with a same-module definition binds to it; two same-module candidates refuse; a same-name type in a different module or a different inline `mod` scope does NOT cross-bind. Tier logic unit-tested via `_resolve_external_call_target` (`test_rust_same_module_tier_binds_unique_survivor`, `test_rust_inline_mod_scope_does_not_cross_bind`) plus an end-to-end faithful-refusal pin (`test_rust_cross_file_different_module_receiver_stays_external`). **NOTE — productive-bind surface (see AC-6): the tier is faithful and correct but produces ZERO productive end-to-end binds** because (a) same-file same-module defs already resolve at extraction via `symbol_lookup`, (b) a Rust module ≈ one file (module=file), so cross-file candidates never share the caller's module, and (c) the candidate index (`per_file_simple`) collapses same-file same-leaf symbols, hiding intra-file inline-mod ambiguity. This is the "negligible delta" the Risk table anticipated; the module model (AC-1) is the durable deliverable. Flagged for operator disposition.
- [x] AC-3: C# verify-and-close — VERIFIED already-correct: `cs_file_ns` normalizes all three declaration styles (`namespace A.B;`, `namespace A.B {`, nested `namespace A { namespace B {`) to the identical key. Pinned by `test_csharp_namespace_key_normalizes_three_declaration_styles`. No C# tier change. Separate pre-existing nuance recorded (out of this AC's scope, "no new C# tier work"): a **file-scoped-namespace class** carries no namespace prefix in its qname (the class is an AST sibling of `file_scoped_namespace_declaration`), so `_cs_ns` returns `""` for it — the normalization is correct, but such a class does not participate in the C# membership tier.
- [x] AC-4: Alias forms resolve through the existing explicit tier and are not double-handled by the new Rust tier — the import-edge disambiguation binds BEFORE the `.rs` module tier (precedence). Evidence: `test_rust_tier_yields_to_explicit_import_disambiguation`.
- [x] AC-5: No behavior change for any other language — the tier is gated `src_file.endswith(".rs")`; `_build_rust_module_index` is empty for a non-Rust project (`test_rust_module_index_empty_for_non_rust_project`), and the Python same-shape receiver still stays `external::` (`test_python_same_dir_unimported_receiver_stays_external`, unchanged). C# behavior unchanged (verify-and-close only).
- [x] AC-6: Rust fixture calibration added (`test_rust_module_tier_calibration`) — before/after resolution shape recorded: `resolved=0 external=1 wrong-module-binds=0` on the cross-file same-name corpus. Productive same-module binds via the tier: **0 (structural, see AC-2 note)**; faithfulness bar holds (the wrong-module twin is never bound). C# regression pinned (AC-3).
- [x] AC-7: `GRAPH_BUILDER_VERSION` bump **DEFERRED to wave integration** (single coordinated 39→40 across all four changes per the wave.md watchpoint — this lane does NOT bump). The extraction-output change that requires the bump: new `rust_mod_decls`/`rust_inline_mods` module-node properties. The adversarial-faithfulness review lane runs at **wave review** (not this implementer lane). — **[integration 2026-07-05]** the bump portion is DONE: coordinated `39→40` landed (the `rust_mod_decls`/`rust_inline_mods` node-property shape change is named in the changelog head). — **[delivery review 2026-07-06]** the adversarial-faithfulness lane RAN (PASS: the Rust module model refuses every wrong-scope bind — inline-mod separation, `#[path]`, orphan per-file fallback, prefix-trap all verified live; the zero-productive-binds outcome is faithful candidate-collapse, not a silent bug). Findings dispositioned. AC complete.
- [x] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes (see Progress Log); `wave_validate` clean; no `__pycache__` under `scripts/`.

## Tasks

- [x] Build the Rust module-path model at extraction (mod-decl file mapping, inline-mod nesting, `#[path]`, crate-root, per-file fallback); expose a per-definition module-path scope key. Extraction harvests `rust_mod_decls`/`rust_inline_mods` onto each `.rs` module node; finalize `_build_rust_module_index` BFS-maps files to crate-relative module paths; `_rust_module_key` composes file-module + inline-mod suffix.
- [x] Add the `.rs` branch to the same-scope disambiguation elif chain keying on module-path equality; preserve tier order and refusal semantics. `rust_module_index` plumbed through `_build_candidate_indexes` → ctx → `_resolve_external_call_target`; branch slots after the C# branch, unique-survivor bind, else external.
- [x] C# verify-and-close: confirmed `cs_file_ns` three-style normalization already correct; pinned with a regression test. No fix needed.
- [x] Adversarial Rust tests (twins, inline-mod separation, `#[path]`, alias-precedence) + Rust fixture calibration counts; C# regression fixture. Fixtures are inline via `_build` (matching every other graph test + the 1p9q6 calibration precedent); recommended convention for 1p9q7.
- [x] Bump `GRAPH_BUILDER_VERSION` (coordinated 39→40 at integration per the wave.md single-bump watchpoint) — **[integration 2026-07-05]** landed; the changelog head names the `rust_mod_decls`/`rust_inline_mods` node-property change. Ran `run_tests.py` (green) + `wave_validate`; cleaned `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| ws1-rust-module-model | implementer | — | The new scope plumbing: mod-decl file mapping, inline-mod nesting, `#[path]`, crate root, per-file fallback. The bulk of the change. |
| ws2-rust-tier | implementer | ws1-rust-module-model | `.rs` branch in the disambiguation elif chain keyed on module-path equality; refusal semantics. |
| ws3-csharp-verify | implementer | — | `cs_file_ns` three-style normalization verify-and-close + regression pin (parallel; tiny). |
| ws4-tests-calibration | implementer | ws2-rust-tier, ws3-csharp-verify | Adversarial Rust tests + pack fixtures + calibration; C# regression fixtures. |
| ws5-adversarial-review | reviewer | ws4-tests-calibration | Faithfulness red-team on the Rust module model: which module shapes bind the wrong scope? |


## Serialization Points

- Shares the cross-file resolution pass with `1p9q4` (Python) — disjoint language branches, but coordinate the single wave-level `GRAPH_BUILDER_VERSION` bump and merge order on `graph_indexer.py`.
- Multi-language pack fixture layout shared with `1p9q7` (DI fixtures) — agree the fixture directory convention once.

## Affected Architecture Docs

Update the per-language resolution capability documentation (`docs/specs/mcp-tool-surface.md` code-tool notes / capability matrix): the same-scope tier's language list becomes Java/Kotlin/Go/C#/**Rust**, with the Python/JS/TS refusal recorded as a standing decision; note the new Rust module-path model and its bounds (no cross-crate, no re-export graph). Consider a note in `docs/architecture/graph-index-system.md` on the module-path scope key.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The Rust module model is the foundation and the new faithfulness surface. |
| AC-2 | required | The Rust tier is the deliverable; wrong-scope binds are the risk. |
| AC-3 | important | C# verify-and-close — confirms an already-shipped tier; a regression pin, not new work. |
| AC-4 | required | Alias confusion is the likeliest silent-wrong-bind path. |
| AC-5 | required | Language-gate leakage would change untested languages' graphs silently. |
| AC-6 | required | The pack is the standing real-world oracle for cross-language resolution changes. |
| AC-7 | required | Standing version-bump and adversarial-review rules for binding changes. |
| AC-8 | required | Suite + docs-lint green is the standing merge gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-03 | Scoped from the graph-index accuracy evaluation. Same-package tier gated to Java/Kotlin/Go; Rust/C# import-edge disambiguation from v25; multi-lang pack Java/Swift/JS-TS (no Rust/C# fixtures). | evaluation 2026-07-03; multi-lang pack memory (p4ea). |
| 2026-07-05 | **Freshness reconciliation (reality-checker lane): NEEDS-RE-SCOPE.** C# half ALREADY IMPLEMENTED (Wave 1p4ev, `graph_indexer.py:9040-9057`) — verified live. Anchors refreshed (changelog `:38`; C# resolver `_resolve_csharp_call_target:3803`; Rust resolver `_resolve_rust_call_target:4342`; `cs_file_ns:8720-8733`; elif chain `:9021-9057`). Coordinated bump target 39→40. | live verify 2026-07-05. |
| 2026-07-05 | **Re-readiness primer + operator decision.** Primer's strongest challenge: the extractor models NO Rust module scope (no `mod_item` modeling; `declared_package` Java/Kotlin-only), so "same file" is not a faithful Rust scope key — a Rust tier is either a near-no-op or requires building Rust module-tree modeling. **Operator decision: FUND Rust module-tree modeling in this wave.** Requirement 1 rewritten from "add an elif" to an explicit Rust module-path model (mod-decl file mapping, inline-mod nesting, `#[path]`, crate root, per-file fallback); C# reduced to a verify-and-close (AC-3 `[~]`); ACs/AEG/Risks/priorities updated. | re-readiness primer 2026-07-05; operator AskUserQuestion answer "Fund Rust modeling in this wave". |
| 2026-07-05 | **Implemented.** Built the Rust module-path model + tier + C# verify-and-close. AST probe confirmed: inline-`mod` scope is already carried in node qnames (`beta.Widget`), `mod` nodes mislabeled kind `function` (left as-is — pre-existing, out of scope), and no cross-file module tree modeled. Extractor now stores `rust_mod_decls`/`rust_inline_mods` on each `.rs` module node; `_build_rust_module_index` BFS-maps files to crate paths (`crate`, `crate::foo`, 2018-edition `foo/bar.rs`, `mod.rs`, `#[path]` override, per-file fallback for orphans); `_rust_module_key` + the `.rs` tier branch bind unique same-module survivors. C# `cs_file_ns` verified already-correct across all three declaration styles → regression pin. **KEY FINDING (reported, not silently over-built): the tier is faithful+correct but adds ZERO productive end-to-end binds** — same-file resolves at extraction, module≈file so cross-file candidates are always a different module, and `per_file_simple` collapses intra-file inline-mod ambiguity. Matches the anticipated "negligible delta"; the module model is the durable AC-1 deliverable. 10 new test methods; full suite green (4,628 tests across 43 files, OK); one pre-existing test unpack fixed to the 5-tuple; `wave_validate` clean; `__pycache__` cleaned; version bump DEFERRED to integration (39→40). | `graph_indexer.py`; `test_graph_indexer.py` (`CrossFileResolutionTests`); calibration `resolved=0 external=1 wrong-binds=0`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-03 | Key C# on declared namespace and Rust on module scope — language rules, not directories. | The language guarantees same-scope visibility, so the bind is semantics-backed; directory keying would over-bind C# and under/over-bind Rust. | Directory keying (rejected: binds on incidental layout); add Python/JS/TS same-directory tiers (rejected: no language-rule basis — standing decision). |
| 2026-07-05 | Reduce C# to a verify-and-close; the same-namespace tier already exists (Wave 1p4ev). | Freshness verified the C# binding/refusal behavior is live; only namespace-key normalization across declaration styles needs confirming. | Re-implement C# (rejected: already done); drop C# entirely (rejected: the normalization edge is a cheap regression pin worth keeping). |
| 2026-07-05 | **FUND Rust module-tree modeling in this wave** (operator decision) rather than ship a same-file near-no-op or split it out. | The extractor models no Rust module scope, so a faithful Rust same-scope tier requires building the module-path model first; the operator chose to fund it here rather than split (`1rs45`-style) or accept a no-op. | Split Rust module-modeling to its own plan (offered, declined); accept a same-file-only near-no-op tier (rejected: not faithful to Rust visibility — inline mods + module tree ≠ file); drop the Rust tier (rejected: leaves the recall gap open). |


## Risks


| Risk | Mitigation |
| --- | --- |
| The Rust module model mis-attributes a definition's module (wrong `mod` mapping, missed `#[path]`, inline-mod nesting error) → wrong-scope bind. | The model is the new faithfulness surface: AC-1 pins each mapping form; unmodeled/uncertain forms fall to per-file identity then refusal, never a guessed parent; the adversarial lane targets exactly these shapes; unique-within-scope-only keeps ambiguity → `external::`. |
| Partial indexing (crate root not in the indexed set, files unreachable from any `mod` decl) yields no module path. | Per-file fallback identity + refusal — a missing model degrades to `external::` (recall gap), never to a wrong bind. |
| Inline `mod` blocks treated as same scope as file-level definitions → cross-binds within one file. | AC-1/AC-2 explicitly separate inline-mod scope from file scope; adversarial fixture pins it. |
| Rust tier interacts with import-edge disambiguation, double-binding an alias. | AC-4 alias tests; tier order explicit (only after import resolution fails). |
| Calibration shows negligible Rust recall on real corpora (few no-`use` same-module ambiguous receivers). | Honest calibration gate: record the delta; if negligible, disposition per the standard "re-scope on negligible delta rather than ship on faith" stance — the module model still has standalone value for future Rust work. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
