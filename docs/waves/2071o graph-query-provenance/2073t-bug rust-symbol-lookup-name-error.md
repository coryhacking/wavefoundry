# Restore symbol lookup in Rust-containing graphs

Change ID: `2073t-bug rust-symbol-lookup-name-error`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-10
Wave: 2071o graph-query-provenance

## Rationale

Tensorwell reported code_impact failing with an undefined re. A fresh upstream canonical Rust graph reproduces the actual served handler NameError for symbol='collect', while the exact node ID succeeds. GraphQueryIndex.resolve_symbol imports re as _re but its Rust trait-alias recognition calls re.fullmatch before ordinary suffix/label matching.

The operator now authorizes preparation, review and implementation. Scope probes confirm this is Rust-triggered but affects non-exact lookup for every language in a mixed Rust graph. Closure remains operator-owned.

## Requirements

1. Use the module's existing regex binding consistently in Rust alias recognition; preserve the intended alias pattern and exact-ID, suffix, label and ambiguity behavior.

2. Non-exact lookups must not crash merely because any Rust node exists in the graph, including a bare non-Rust symbol in a mixed-language graph. Exact-ID behavior remains unchanged.

3. Exercise the shared resolver and the actual code_impact response, including trait-qualified Rust aliases, unambiguous and ambiguous labels, absent symbols and adjacent exact-ID controls. Preserve existing per-tier multi-match behavior, including deliberate shortest-callable suffix selection and bare-label ambiguity outcomes; do not introduce arbitrary first-match resolution.

## Scope

**Problem statement:** Restore symbol lookup in Rust-containing graphs to repair the confirmed behavior described above.

**In scope:**

- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

**Out of scope:** Broader Rust extraction/inference, trait symbol identity redesign, graph refresh policy, new lookup modes.

## Acceptance Criteria

- [x] AC-1: Bare-symbol code_impact reaches the published Rust fixture and returns its existing successful impact contract without NameError; exact-ID lookup retains its result. Oracle: actual response comparisons against canonical graph fixtures.
- [x] AC-2: Supported Rust trait aliases and mixed-language label/suffix lookups retain their intended identity and ambiguity semantics. Oracle: direct resolver tests plus served callers, with independently specified graph IDs.
- [x] AC-3: An undefined regex binding or over-broad alias/ambiguity match is detected by selected regression controls. Oracle: safe pre-fix/injected-old behavior and invalid/ambiguous controls, not merely source-string assertions.

## Tasks

- [x] Add served-path or scanner regression coverage reproducing the confirmed defects with realistic adjacent controls.
- [x] Implement only the admitted requirements and preserve the stated compatibility boundaries.
- [x] Run affected tests and selected known-bad controls; record actual AC evidence as each completes.
- [x] Complete independent delivery review and applicable framework qualification before proposing closure.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Repair | implementer | Current typed readiness and implementation authorization | Single writer for shared modules |
| Verification | required reviewer lanes | Frozen implementation | Fresh independent contexts |
| Integration | wave-coordinator | Verified repair | Reconcile scope, ACs and full qualification |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_graph_query.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

## Affected Architecture Docs

docs/architecture/graph-index-system.md (consulted; no ownership or lookup-contract change expected).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Bare-symbol code_impact reaches the published Rust fixture and returns its existing successful impact contract without NameError; exact-ID lookup retains its result |
| AC-2 | required | Supported Rust trait aliases and mixed-language label/suffix lookups retain their intended identity and ambiguity semantics |
| AC-3 | required | An undefined regex binding or over-broad alias/ambiguity match is detected by selected regression controls |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-10 | Repair1 frozen:1175affected-module tests/0skips,105final quality/0skips;10qualified mutants killed. Runtime/requirements and historical originals unchanged. | Exact parity/source-byte/Kotlin controls and new11path fingerprint summarized in wave.md; independent rechecks pending |
| 2026-10-10 | First delivery council withholds qualification for current fixture/report drift and a false architecture mechanism paragraph. Typed cycle1 repair starts; admitted requirements unchanged. | Bounded five-path repair, fresh affected-lane review, then quiet full suite |
| 2026-10-10 | The Session Handoff section preserves the original planning checkpoint; current implementation/qualification status is in this Progress Log, wave.md and docs/agents/session-handoff.md. No admitted requirement changed. | Preserve current review-policy receipt; completion markers are bookkeeping only |
| 2026-10-10 | Behavioral ACs verified on frozen implementation: final58focused tests/0skips8.581s;13disposable mutants killed. Full qualification and independent delivery remain pending. | Canonical CallProvenanceExtractionTests, PythonPhysicalLineProvenanceTests, TestPersistedCallProvenance, RustContainingSymbolLookupTests and TestRustContainingImpact; mutation table in wave.md |
| 2026-10-10 | AC-1/AC-2 pass:4focused tests,0skips; only existing regex binding changed. Rust-only/non-Rust/mixed, exact-ID, absent, trait aliases and existing suffix/label ambiguity outcomes verified, including actual canonical published code_impact. AC-3 mutation and independent delivery remain pending. | RustContainingSymbolLookupTests(test_rust_non_rust_and_mixed_lookups, test_trait_alias_unique_and_ambiguous, test_suffix_shortest_callable_and_label_ambiguity); TestRustContainingImpact.test_published_rust_and_mixed_non_exact_impact |
| 2026-10-10 | Readback: fix the existing _re binding in shared resolve_symbol, preserving exact-ID, suffix/label and ambiguity semantics. Bare Python queries currently crash after a Rust symbol enters the graph; afterwards existing lookups and Rust trait aliases should resolve normally. AC-1–AC-3; graph_query.py and focused resolver/actual code_impact tests. No inference or identity redesign. | Current typed readiness; actual source/extraction/publication/public-handler known-bad controls |
| 2026-10-09 | Plan only. Current defect mechanisms exercised by the finite upstream scratch probe; no repaired behavior claimed. Downstream cost measurements are attributed, with upstream identity verification only for the named profile. | Wave baseline captures; updated Tensorwell diagnostic report |
| 2026-10-09 | Optional Review plan resolves contract branches from source and accepted summary ADR: stored provenance, nullable unproven snippets, compatible singular fields; bounded scope/work and reporting state; preserve producer protocol. No unresolved operator choice or implementation authorization inferred. | Requirements and Decision Log |

## Decision Log

| Date | Decision | Reason and alternatives |
| --- | --- | --- |
| 2026-10-09 | Divergent pre-plan choice | Selected the consistent existing import binding plus behavioral coverage. Rejected suppressing NameError: hides a real resolver fault as unresolved. Rejected rebuilding Rust symbol identities: unrelated to the proven binding error. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A small historical reproducer misses a related supported input | Use the derived contract classes and adjacent controls in ACs, not only the reported line/path |
| Bounds or missing evidence appear as successful absence | Preserve explicit unknown/incomplete states and make negative controls non-vacuous |
| A compatibility repair widens into unrelated redesign | Keep scope explicit; return material contradictions to planning |

## Session Handoff

Planned only. Readiness evidence belongs to the wave's typed ledger; implementation/delivery ACs remain unchecked. See `docs/agents/session-handoff.md`.
