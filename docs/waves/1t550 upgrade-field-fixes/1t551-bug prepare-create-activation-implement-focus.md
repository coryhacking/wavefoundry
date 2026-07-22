# Prepare-Create Activation Advances Context-Efficiency Focus to Implement

Change ID: `1t551-bug prepare-create-activation-implement-focus`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-21
Wave: `1t550 upgrade-field-fixes`

## Rationale

Live-caught on wave 1t550 itself: the registered `wf_prepare_wave` tool passes a hardcoded `focus_stage="plan"` to `_lifecycle_context_result` for every mode. Context-efficiency focus is sticky, and `wf_implement_wave` / `wf_reopen_wave` are the only tools that advance it to `implement` — so a wave activated via `wf_prepare_wave(mode='create')` keeps attributing every instrumented call to the plan stage for the whole implementation. On 1t550 all 10 implementation retrieval calls (48,860 estimated tokens saved) landed under `plan`, and the close-time `retrieval_posture_gap` sensor false-fired at implement-calls=0 despite full MCP-first retrieval, requiring a Gapfill entry to clear.

## Requirements

1. When `wf_prepare_wave` succeeds with `transitioned_to_active` true in its response data (mode `create`/`apply` that actually opened the wave), the tool wrapper passes `focus_stage="implement"` so subsequent instrumented calls attribute to the implement stage.
2. All other prepare outcomes (`dry_run`, `ready`, and a `create` that did not transition) keep `focus_stage="plan"` exactly as today.
3. The stage is derived from the canonical response envelope (`transitioned_to_active` read via `_context_data`), not re-derived from wave state, so the wrapper cannot disagree with what the core call reported.
4. Hermetic tests cover both sides of the boundary: after a transitioning `create` the telemetry focus stage is `implement`; after `ready` (readied but not opened) it remains `plan`.
5. No change to `wf_implement_wave`, `wf_reopen_wave`, review/close focus, milestone credit, flush, or general-bucket transfer semantics; the derived stage feeds the existing `focus_stage` parameter only.

## Scope

**Problem statement:** the prepare-create activation path is the one wave-opening route that never advances context-efficiency focus to `implement`, misattributing implementation work to `plan` and false-firing the retrieval-posture sensor.

**In scope:**

- `server_impl.py` registered `wf_prepare_wave` wrapper (focus-stage derivation only)
- Hermetic tests in the server context-efficiency test module

**Out of scope:**

- Rebalancing historical stage splits already recorded (append-only store; 1t550's own split stays as documented by its Gapfill entry)
- Any change to the posture sensor's counting or the three-stage vocabulary

## Acceptance Criteria

- [x] AC-1: after `wf_prepare_wave(mode='create')` reports `transitioned_to_active: true`, the context-efficiency focus stage is `implement`; subsequent instrumented retrieval attributes there.
- [x] AC-2: after `wf_prepare_wave(mode='ready')` and `mode='dry_run'` the focus stage remains `plan`; a non-transitioning `create` also remains `plan`.
- [x] AC-3: full framework test suite passes; live post-reload probe confirms the stage advance on a real activation (fragile-file protocol for CE instrumentation).

## Tasks

- [x] Derive `focus_stage` from `transitioned_to_active` in the `wf_prepare_wave` wrapper.
- [x] Hermetic tests for the transitioning and non-transitioning outcomes.
- [x] Full suite; live post-reload verification per the CE fragile-file memory.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| focus-derivation | implementer | — | Single wrapper edit in the CE-fragile region |
| tests | qa-reviewer | focus-derivation | Real telemetry store, canonical envelopes |

## Serialization Points

- None; single-file change.

## Affected Architecture Docs

N/A: telemetry attribution fix inside the existing three-stage context-efficiency model (1t3gt); no boundary, flow, or vocabulary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The misattribution being fixed. |
| AC-2 | required | Guards against over-advancing focus on non-activating prepares. |
| AC-3 | required | Standard gate plus the fragile-file live-probe protocol. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-21 | Drafted from the live 1t550 observation (all implementation retrieval attributed to plan; posture sensor false-fired at 0). Mechanism verified at server_impl.py: hardcoded `focus_stage="plan"` in the `wf_prepare_wave` wrapper; `wf_implement_wave`/`wf_reopen_wave` are the only implement-stage transitions. Operator directed late admission into wave 1t550. | wave 1t550 Context Efficiency block (plan: 10 calls, no implement row); code_keyword/code_read on the five focus_stage sites |
| 2026-07-21 | Implemented: wrapper derives `focus_stage="implement" if transitioned else "plan"` from the envelope's `transitioned_to_active`; hermetic four-case test (dry_run/ready/non-transitioning create → plan; transitioning create → implement) through the real registered wrapper via FakeMcp with only the core response stubbed; CE module 65 OK; mutation probe forcing the pre-fix hardcoded-plan wrapper flipped the test to failure. Live post-reload probe: wf_reload_mcp then a real dry_run prepare exercised the non-transition branch on live code; the `transitioned_to_active` field name is live-confirmed on both sides from this session's real envelopes (true at the 1t550 activation, false at dry_run). Limitation: the transition branch cannot fire live while 1t550 holds the single-OPEN slot; it is proven hermetically through the real wrapper. | test_prepare_create_activation_advances_focus_to_implement; in-process mutation probe; wf_reload_mcp + live dry_run |
| 2026-07-21 | AC-3 met: full framework suite 6,114/6,114 OK on the final tree; docs lint clean. | run_tests.py output |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-21 | Derive the stage from the response's `transitioned_to_active`, in the wrapper only. | The envelope already states whether activation happened; re-deriving from wave state could disagree with the reported outcome. | Deriving stage from wave status at commit time inside the telemetry store (bigger blast radius in the CE-fragile region); leaving prepare as plan and requiring wf_implement_wave (leaves the documented activation path mis-attributing). |
| 2026-07-21 | Historical splits are not rebalanced. | The store is append-only and the totals are correct; only the stage split was off, and 1t550's Gapfill entry documents it. | Hand-editing sealed checkpoint history (rejected: history surgery for a display split). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| CE instrumentation is a fragile area (five prior repairs). | Envelope field read via the canonical `_context_data` accessor; hermetic tests on real envelopes plus a live post-reload probe per the standing fragile-file memory. |
| Prepare's own instruction-proxy credit moves to implement on activation. | Acceptable and consistent: `wf_implement_wave`'s own proxy already credits to implement at the same boundary. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
