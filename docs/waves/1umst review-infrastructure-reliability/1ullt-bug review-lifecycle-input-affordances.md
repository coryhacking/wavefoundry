# Review Lifecycle Input Affordances

Change ID: `1ullt-bug review-lifecycle-input-affordances`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-06
Wave: 1umst review-infrastructure-reliability

## Rationale

Solaris encountered three avoidable lifecycle dead ends: prepare-council verdicts must fit on one physical line and split semicolon-containing values; `wf_mark_task` cannot address a wrapped task and gives no useful candidates; and review-event input requirements arrive only after multiple rejected requests. The same field report also found terminology drift (`prepare` versus `readiness`), an intuitive but unsupported `evaluate` prepare mode, and a status-transition error that omitted the legal next values. These are MCP contract and parser defects, not user error.

## Requirements

1. Prepare-council verdict parsing must accept a single logical verdict across markdown continuation lines and preserve semicolons inside values.
2. Verdict failures caused by malformed wrapping or delimiters must name the actual parse cause and provide a valid format/template.
3. `wf_mark_task` must recognize and mutate the same wrapped task labels that the sibling AC marker supports; unmatched/ambiguous responses must list every parsed task label.
4. `wf_review_event` guided actions and tool schema must enumerate all required top-level and nested evidence fields for the selected event/phase before a caller submits a write.
5. Review-stage vocabulary must be coherent: callers receive an accepted alias or an explicit mapping between `prepare` and `readiness`, and prepare-mode errors name valid modes (including a supported `evaluate` alias if retained by design).
6. Status transition failures must state the current status and its legal next values, building on the already-filed allowed-values work without duplicating it.

## Scope

**Problem statement:** Lifecycle MCP tools reject valid markdown and under-specify their inputs, producing multi-round-trip recovery loops with no actionable remediation.

**In scope:**

- Prepare verdict parsing/diagnostics and its prompt/template.
- Wrapped task matching and candidate recovery.
- Review-event action/schema completeness and lifecycle terminology aliases/diagnostics.
- Focused documentation and regression coverage.

**Out of scope:**

- Changing review-evidence authority, independent-context rules, or the set of allowed judgment values.
- Replacing the docs-lint transition formatter; that implementation belongs to `1ul77` and this change consumes its contract.

## Acceptance Criteria

- [x] AC-1: A markdown-wrapped prepare-council verdict with every required field validates exactly as its one-line equivalent; values containing semicolons round-trip unchanged.
- [x] AC-2: An invalid wrapped verdict says whether wrapping, a missing field, or an invalid delimiter caused the rejection and supplies a valid format.
- [x] AC-3: `wf_mark_task` marks a two-line task; a non-match returns all parsed task labels rather than an empty candidate list.
- [x] AC-4: The first dry-run action response for finding and approval events enumerates every required nested evidence/integrity field and rejects all missing fields together.
- [x] AC-5: The public review API accepts a documented prepare/readiness alias or emits a diagnostic mapping the two names; prepare mode errors enumerate legal modes.
- [x] AC-6: Invalid change-status transitions name the current status and reachable successors, covered through the shared `1ul77` formatter contract.
- [x] AC-7: Parser, mutation, guided-action, and docs-lint regression suites pass.

## Tasks

- [x] Design a continuation-safe verdict grammar and update its prompt template/diagnostics.
- [x] Share wrapped-checkbox parsing between task and AC mutation paths.
- [x] Derive review-event required-input descriptors from the validation registry and expose them before mutation.
- [x] Reconcile prepare/readiness and prepare-mode diagnostics.
- [x] Add cross-surface tests and update the relevant MCP/prompt docs.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| parser and marker matching | implementer | none | Server implementation seam |
| input contract | implementer | none | Registry-driven schema/action output |
| contract verification | docs-contract-reviewer | both | MCP and prompt terminology |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/prompts/prepare-wave.prompt.md`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` and the prepare prompt require updates because this changes accepted request forms and error/recovery contracts, not the lifecycle authority model.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Valid markdown must not fail a lifecycle gate. |
| AC-2 | important | Prevents opaque parser recovery. |
| AC-3 | required | Restores typed task mutation. |
| AC-4 | required | Removes avoidable write retries. |
| AC-5 | important | Makes public terminology predictable. |
| AC-6 | required | Completes the reported transition recovery path. |
| AC-7 | required | Contract changes need regression evidence. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-06 | Filed from Solaris 1.15.4+ph68 field report; source read confirmed per-line verdict matching and semicolon splitting. | `server_impl.py:14251-14303`; `wave_validators.py:1794-1984` |
| 2026-08-06 | Implemented wrapped verdict/task support, complete action input schema, and `evaluate` Prepare alias. | `test_server_tools.py`; `test_review_evidence.py` |
| 2026-08-06 | **P2 repaired: the `prepare`/`readiness` vocabulary was only half unified.** No tool accepted the sibling word and no error named the mapping, though `wf_review_wave` already mapped `prepare` to `readiness` internally. `readiness` and `delivery` are now accepted aliases, and the invalid-phase error states the mapping in both directions. | `server_impl.py` `_REVIEW_PHASE_ALIASES`, `wf_review_wave_response` |
| 2026-08-06 | **P2 repaired: `evaluate` was documented only on self-hosted surfaces.** The alias was absent from the registered tool docstring that every MCP client reads and from the shipped `install/lifecycle-prompts/prepare-wave.prompt.md` that target repos render, which is the self-hosting pattern AGENTS.md warns against. Both now document it. | `server_impl.py:27945`; `install/lifecycle-prompts/prepare-wave.prompt.md` |
| 2026-08-06 | **P3 repaired: a spec claim about both recovery branches was false.** Only the ambiguous branch carries the not-arbitrarily instruction; the absent branch reports candidates. Corrected, keeping the true fact that the absent branch returns every parsed label. | `mcp-tool-surface.md:644` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-06 | Parse a logical verdict, not one physical line. | Markdown wrapping is normal and fields should not become unrepresentable at readable line lengths. | Enforce one long line; preserves the defect. |
| 2026-08-06 | Derive caller guidance from validation registries. | Separate hand-authored schema text will drift from required-field validation. | Add another static documentation list. |
| 2026-08-06 | Keep allowed-value formatting owned by `1ul77`. | That change already scopes the shared lint formatter; duplicating it risks conflicting edits. | Reimplement transition formatting locally. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Continuation parsing accepts unrelated prose | Require a verdict anchor and only consume indented/explicit continuations. |
| Expanded schema omits an event variant | Test every event and approval phase against the validator's required set. |
| Concurrent `1ul77` changes overlap | Serialize the validator edit after its shared formatter lands. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
