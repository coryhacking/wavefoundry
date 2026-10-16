# Memory reranker selection: except clause references an unbound import

Change ID: `20p5j-bug memory-reranker-except-unbound-import`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20ppj rerun-reliability-review-follow-ups`

## Rationale

`_get_memory_reranker` in `wf_server/server_impl.py` wraps its body in a `try` whose first `except` is `except inference_provider.ProviderUnavailable:`. The name `inference_provider` is bound by an `import inference_provider` statement inside that same `try`, after the `WAVEFOUNDRY_DISABLE_RERANKER` check and after `import tensorwell_client`. When anything before that import raises, Python evaluates the except expression, hits `UnboundLocalError`, and the original error is replaced. The following `except Exception` fallback that returns the `local_model_unavailable` selection is bypassed, so memory search surfaces an `UnboundLocalError` instead of degrading. Commit `43621e07` introduced the clause.

## Requirements

1. The `ProviderUnavailable` except clause must be evaluable regardless of where inside the `try` the exception originates. Bind the module reference before the `try`, or catch via a reference that does not depend on a local import.
2. Behaviour is otherwise unchanged: `ProviderUnavailable` still propagates, every other exception still yields the `local_model_unavailable` selection.
3. Windows, macOS, Linux and WSL2: no platform-specific behaviour; the fix is pure control flow.

## Scope

**Problem statement:** an except clause can raise `UnboundLocalError` and mask the intended fallback.

**In scope:**

- `_get_memory_reranker` in `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- A regression test

**Out of scope:**

- Any change to reranker selection policy or Tensorwell qualification

## Acceptance Criteria

- [x] AC-1: With `self._inference_selection` patched to raise for the `reranker_disabled` path, or `import tensorwell_client` patched to fail, `_get_memory_reranker` returns the `local_model_unavailable` selection rather than raising `UnboundLocalError`.
- [x] AC-2: A `ProviderUnavailable` raised from `select_reranker` still propagates unchanged.
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add a failing regression for AC-1.
- [x] Hoist the module reference out of the `try` (or equivalent) and confirm AC-2 still holds.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix and test | Implementer | Readiness | Single write owner |
| Delivery review | QA | Fix and test | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Confined to one function's exception handling with no boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect |
| AC-2 | required | Guards the intended propagation |
| AC-3 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the code review of `43621e07` | Review finding 3 |

| 2026-10-15 | Readback: bind inference_provider before the memory-reranker try so early errors reach local_model_unavailable, while ProviderUnavailable still propagates. AC-1/2; server_impl and isolated reranker regression. No selection-policy change. | Admitted plan and current-source MCP reads |

| 2026-10-15 | Focused controls passed: root follow-ups, rerun, retained docs-gate retry, scope and container-status controls: 44 tests / 0 skips. In-memory mutants restored the unbound import, repeated discovery and missing extraction guard; each targeted test detected its defect. Final combined qualification remains pending. | test_rerun_followups; test_upgrade_rerun_reliability; ResumeAfterGateTests; OpenContainerScopeTests; ContainerStatusContractTests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Bind the module before the `try` | Smallest change; the module is already imported at server load so there is no new import cost | (a) Catch `Exception` and re-raise by `isinstance` check inside the handler: works but hides the intent. (b) Split the `try` so the import sits in its own block: more lines for the same effect. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hoisting the import changes failure timing when the module is absent | AC-1 covers the fallback path; the module is already a hard dependency of the server |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
