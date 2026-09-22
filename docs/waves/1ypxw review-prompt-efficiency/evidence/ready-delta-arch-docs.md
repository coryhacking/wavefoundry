# Focused readiness delta — architecture and docs contract

Owner: Engineering
Status: active
Last verified: 2026-09-22

Phase: readiness only. Policy receipt: `review-policy-d33fe310355179ea758d`.
Context: `ypxw_readiness_arch_docs`. Actor: delegated architecture/docs-contract reviewer and council synthesizer. Architecture, docs-contract and synthesis share this context and are correlated judgments, not three independent reviews. Requested model/effort: inherited host defaults; observed runtime identity unknown. This context must not provide delivery approval later.

## Verdicts

Architecture: **approved for the bounded plan delta**. Docs-contract: **approved for the bounded plan delta**. Council synthesis: **approved for the same delta**, incorporating the separately supplied `ypxw_readiness_delta` red-team challenge. No claim is made that implementation passes or that unrelated plan scope was reviewed afresh.

The operator-selected rules are explicit and consistent in `1yoy2-bug review-ledger-tool-gaps.md` Requirements 1, 3 and 5 and Decision Log, and `tool-inventory.md` Clarifications surfaced: a bare test ID does not suppress temporary-only path evidence warnings; rotation reminders inspect each lane's latest readiness approval and clear after all lanes refresh, preserving history. The prior `readiness-review.md` remains historical evidence rather than an assertion about completed implementation.

## Architecture and contract checks

Direct MCP `code_outline` and `code_read` verified `review_evidence.py` `_approval_rows` and `review_authority_projection`. `_approval_rows` selects the last eligible append-order row by approval claim, filters the requested approval phase, and retains historical rows in the input. The projection owns approval facts, actor/independence checks, receipt binding and repair currency. Use those existing lane facts for the new advisory; do not create a second approval authority or parse presentation prose. In particular, clearing this advisory must not confer approval on a missing/invalid lane or erase an affected-repair requirement.

The code's `receipt_binding_applies` remains readiness-specific, and the unchanged plan excludes receipt identity, digest inputs, rotation rules, readiness rules and approval schema from scope. The delta only changes when an advisory appears; it does not widen lifecycle mutation authority, change evidence acceptance, make a bare test ID invalid, or invalidate delivery approvals. The advisory predicate stays in `review_evidence.py` and envelope diagnostics stay with the tool. This preserves the facade and dependency direction in `docs/architecture/layering-rules.md` Boundary Invariants.

The conservative delimiter/path-token classification is appropriate for an advisory. A cited repository path suppresses the warning; a bare identifier supplies no path evidence. This is a lexical heuristic, not proof that the cited file exists, is tracked, or contains valid evidence. No filesystem existence or external-path authority should be inferred from it. Required final documentation remains the plan's architecture and tool-surface updates; no new ADR or authority surface is needed for these two clarifications.

## Readiness-safe negative controls

A standalone in-memory Python model was executed with `python3 -B`; exit status 0. It is a specification counterexample check, not a test of the delivered public tool and not a mutation of source or ledger.

| Case | Expected | Observed |
| --- | --- | --- |
| arch=old, qa=old, then arch=new | Advisory remains because qa is old | Per-lane selection warns; rejected global-latest predicate clears incorrectly |
| Append qa=new to that history | Advisory clears, all four rows retained | Per-lane selection clears; rejected all-history predicate still warns |
| `/tmp/evidence.txt test_case_name` | Warning remains | Warning remains; bare ID contributes no path token |
| `/tmp/evidence.txt docs/reports/evidence.md` | Warning suppressed | Suppressed by repository path |
| `test_case_name` | No path warning | Zero path tokens, no warning |

The separate red-team primer's strongest challenge was premature clearing from a global latest row versus permanent warning from all-history scanning. The accepted per-lane rule defeats both counterexamples. Reusing the existing phase-aware projection is the strongest architectural alternative to duplicating selection logic.

## Integrity and limitations

Fresh delegated context for this focused readiness review; no implementation authorship and no source, seed, test or lifecycle-event edits. Only this evidence document was written. Load-bearing reads were current-tree MCP reads. `code_ask` reported a stale index, so indexed excerpts were navigation only; direct source reads supplied the conclusions. The probe used synthetic in-memory values, made no network call, and performed no repository mutation. Observed outcomes agreed with expected contract behavior and detected both rejected rotation predicates plus bare-ID suppression.

No full suite, canonical producer fixture, Windows environment probe, or registered public-path execution was performed here. Those remain delivery verification obligations, including partial versus complete per-lane refresh, phase separation, legacy receipts, and mixed evidence citations. The approval is readiness-scoped and does not assert delivered behavior or count correlated roles as independent evidence.
