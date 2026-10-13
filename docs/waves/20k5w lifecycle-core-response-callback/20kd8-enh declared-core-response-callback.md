# Declared lifecycle core response callback

Change ID: `20kd8-enh declared-core-response-callback`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-13
Wave: `20k5w lifecycle-core-response-callback`

## Rationale

A wrapping extension receives lifecycle results after their internal context-efficiency accounting and after mutating calls release their publication hold. The operator selected lifecycle responses first. Provide a small opt-in callback at the existing completion point so trusted distribution code can inspect and enrich the final response before accounting while the mutating operation still holds its existing publication lock. Keep empty defaults cost-free apart from a lookup; no new review step, evidence file or remote dependency.

## Requirements

1. Add an empty-by-default per-canonical-tool declaration mapping a supported tool to one synchronous callback in an existing declared helper module. Reuse declared source loading, provenance, helper validation and reload ownership; no repository discovery or arbitrary import paths. Reject unsupported tool targets, missing/noncallable functions and async callbacks before serving the declaration.
2. Initial supported targets are wf_create_wave, wf_prepare_wave, wf_implement_wave and wf_close_wave, the four native mutating lifecycle handlers with a shared _lifecycle_context_result completion path under their existing publication hold. Invoke exactly once when that completion path is reached, after core response construction and before its context-efficiency/checkpoint accounting. Preview modes keep their existing no-hold/nonmutating behavior; early returns that do not reach completion invoke no callback. Review, retrieval, pause, other lifecycle tools and async runner tools are unsupported, not silently late-bound.
3. Callback receives keyword arguments root, tool_name (canonical), arguments and a detached response copy. It performs synchronous nonmutating inspection and returns a JSON-compatible mapping of additional fields; place it under data.extension_response without overwriting core status, data keys, diagnostics, next actions or receipt authority. Callback code is trusted distribution code, not a sandbox or verifier; it must not perform recursive lifecycle publication or external work.
4. If the callback raises, returns invalid data or attempts to provide an unsupported shape, preserve the core outcome, append a bounded path-free callback diagnostic, and continue normal accounting. Do not retry core writes or claim they rolled back. Use existing response validation/bounds where applicable rather than adding a middleware framework.
5. Direct calls, canonical aliases and overrides that call core_handler observe one callback per actual core execution. An override that does not delegate runs no core callback. Added response content participates in the existing accounting/checkpoint path once; preserve existing override delta accounting.
6. Document declaration, exact target and early-return rule, same-hold guarantee only for mutating modes, synchronous trusted-code limitations, no veto/rollback authority, default no-op, and reload behavior.

## Scope

In scope: explicit declaration/validation, existing helper loading/reload, selected lifecycle completion integration, additive response data, controlled failure diagnostics and registered-path regressions. Out of scope: universal tool middleware, human identity verification, pre-publication veto, async callbacks, external callback protocols, new locks around read-only tools, response replacement, automatic retries or extra review gates.

## Acceptance Criteria

- [x] AC-1: Registered lifecycle controls observe core execution then callback then accounting/checkpoint; a competing publication attempt remains excluded during a mutating callback, while preview remains nonmutating and unsupported/early-return paths are documented and tested.
- [x] AC-2: Empty declaration preserves existing results; valid declared helpers load with current provenance and reload, and invalid target/module/function/async declarations are refused before serving.
- [x] AC-3: Added mapping appears only in data.extension_response and is accounted once; callback exceptions and invalid results produce bounded diagnostics preserving completed core outcome and recovery hints without repeating writes.
- [x] AC-4: Direct, alias and delegated-override controls show exactly one callback per core execution and zero when no delegation occurs; focused tests and changed docs validate with explicit supported-scope limitations.

## Tasks

- [x] Add declaration validation and source-owned synchronous helper binding with reload reset.
- [x] Integrate callback at the selected completion boundary with additive bounded output and truthful failure handling.
- [x] Add ordering, publication-hold, preview, alias/override and negative declaration controls.
- [x] Update MCP contract, control-flow documentation and changelog; complete focused tests and independent review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | Independent council and required lanes | Selected scope | Critique callback ordering and publication claims |
| Implementation | implementer | readiness and prior server edits | Single source writer |
| Delivery | Independent reviewers | frozen implementation | Registered routes, negative controls and exact scope |

## Serialization Points

Run after the earlier repair and local-attribution waves. Serialize server_impl.py, extension declarations and shared architecture/spec/changelog edits. Reviewers are read-only; coordinator owns lifecycle records.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Root CHANGELOG.md records the opt-in seam. Protected publication/upgrade refusal guards, typed review authority, default tool tiers, public request schemas and existing checkpoint ownership remain unchanged.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` documents callback order and retained publication hold. `docs/specs/mcp-tool-surface.md` defines declaration, callback inputs/output, supported targets, failures and reload compatibility. No new seed or permanent review artifact required.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Demonstrate the exact requested insertion point |
| AC-2 | required | Preserve default and source-owned declaration safety |
| AC-3 | required | Keep publication truth and response accounting intact |
| AC-4 | required | Avoid duplicate callbacks and overclaimed coverage |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Implementation and required independent delivery reviews complete. All three batch findings are repaired and independently cleared; all ACs/tasks are checked. Combined canonical qualification passes 12,471 tests across 185 files, 12 reported skips. Wave remains paused for operator signoff and closure. | Current typed approvals; green test receipt 83e8456ae65b35e56e2409ee1f48216471edb27552d52272329cd7bcbfc7c520; wave Review checkpoints |
| 2026-10-13 | Final focused integration is green. The broad lifecycle run exposed four outdated expectations and one mock signature; eight targeted controls now pass with original historical digests preserved, deterministic account attribution, the exact callback advisory site and the original replacement-refusal oracle. No production repair was needed. All five implementations are paused; canonical combined qualification and independent delivery are next. | test_server_tools_lifecycle named failed methods and LocalUserReviewEventTests; git diff --check clean |
| 2026-10-13 | Callback implementation and focused controls are complete: 39 context/accounting/focus tests pass, all 10 new tests pass by direct-file execution, and 21 extension tests pass in the existing tool environment after system-Python MCP import setup errors. Six known-bad callback/limit/declaration controls are detected. Full lifecycle module is still running with failures awaiting final traces; combined qualification and independent delivery remain pending. | LifecycleResponseCallbackTests; LifecycleCallbackServingTests; LifecycleCallbackDeclarationTests; no native Windows execution |
| 2026-10-13 | Readied and opened after the shared declaration fixture received focused readiness review. Readback: four canonical lifecycle completion paths invoke a declared synchronous helper once, with detached input, before accounting and inside the existing mutating publication hold; bounded additive output cannot veto or replace core outcome. Defaults perform only a lookup. | Current typed readiness; AC-1..AC-4; local_user source preserved; pre-implementation memory brief |
| 2026-10-13 | Added the shared shipped-declaration fixture to review targets: its exact declaration census and profile resets must include the new empty callback mapping. This supports the already admitted loader/profile contract; callback semantics are unchanged. Focused readiness currency check precedes implementation. | tests/record_layout_support.py SHIPPED_DECLARATION and declaration_support consumers |
| 2026-10-13 | Operator selected lifecycle responses first. Live MCP reads identify four supported mutating completion callers; semantic retrieval was unavailable, so named live reads grounded the plan. No implementation yet. | _measured_core_handler, _extension_staging_surface, _install_declared_extension_tools, _lifecycle_context_result and its registered lifecycle callers |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Lifecycle-first completion seam for four existing mutating handlers. | Operator selected bounded coverage; existing hold/accounting boundary is usable. | Outer wrapping runs too late; all-tool support crosses unrelated self-accounting paths and broadens scope. |
| 2026-10-13 | One callback per tool in an existing declared helper, additive response namespace, diagnostic-on-failure. | Small predictable seam preserving core publication truth and loading provenance. | Callback chain creates ordering policy; replacing envelopes can hide completed writes; raising after publication invites unsafe retries. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hook name suggests all lifecycle tools | Explicit supported set and registration refusal for others |
| Trusted callback writes or blocks under the hold | Nonmutating synchronous contract and no sandbox or timeout guarantee; use bounded fixture callbacks |
| Partial core result is mistaken for rollback | Preserve original status/recovery hints and add a separate diagnostic |
| Copying/returned data adds unbounded retention | Validate supported JSON-like output through existing limits and test bounded failure |

## Session Handoff

Implement after earlier waves, then pause after independent review. No close, commit, push or release requested.
