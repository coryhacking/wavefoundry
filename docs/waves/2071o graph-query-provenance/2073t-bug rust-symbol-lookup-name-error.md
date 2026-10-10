# Restore symbol lookup in Rust-containing graphs

Change ID: `2073t-bug rust-symbol-lookup-name-error`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-09
Wave: 2071o graph-query-provenance

## Rationale

Tensorwell reported code_impact failing with an undefined re. A fresh upstream canonical Rust graph reproduces the actual served handler NameError for symbol='collect', while the exact node ID succeeds. GraphQueryIndex.resolve_symbol imports re as _re but its Rust trait-alias recognition calls re.fullmatch before ordinary suffix/label matching.

The operator requested Plan, Prepare and Review only. No implementation, activation, closure, commit, push or package build is authorized by this request.

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

**Out of scope:** Broader Rust extraction/inference, trait symbol identity redesign, graph refresh policy, new lookup modes, and implementation during this request.

## Acceptance Criteria

- [ ] AC-1: Bare-symbol code_impact reaches the published Rust fixture and returns its existing successful impact contract without NameError; exact-ID lookup retains its result. Oracle: actual response comparisons against canonical graph fixtures.
- [ ] AC-2: Supported Rust trait aliases and mixed-language label/suffix lookups retain their intended identity and ambiguity semantics. Oracle: direct resolver tests plus served callers, with independently specified graph IDs.
- [ ] AC-3: An undefined regex binding or over-broad alias/ambiguity match is detected by selected regression controls. Oracle: safe pre-fix/injected-old behavior and invalid/ambiguous controls, not merely source-string assertions.

## Tasks

- [ ] Add served-path or scanner regression coverage reproducing the confirmed defects with realistic adjacent controls.
- [ ] Implement only the admitted requirements and preserve the stated compatibility boundaries.
- [ ] Run affected tests and selected known-bad controls; record actual AC evidence as each completes.
- [ ] Complete independent delivery review and applicable framework qualification before proposing closure.

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
