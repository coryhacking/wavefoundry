# Deferring an AC refreshes its review receipt

Change ID: `1ulnu-enh defer-ac-refreshes-review-receipt`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: 1uj12 legacy-direct-upgrade-compatibility

## Rationale

`wf_mark_ac(state='~')` correctly preserves a contract deferral in the review digest, but it leaves the agent to discover and invoke a separate Prepare step. Deferral should publish the new receipt as part of the same action and return the precise re-approval work; it must never fabricate an approval.

## Requirements

1. When `wf_mark_ac` successfully marks an AC `[~]` with its required reason, atomically refresh the review-policy receipt for a declared wave and reproject current review state.
2. Return an explicit `review_receipt_refreshed` result with the new receipt identity and the next required approval actions. Do not record or preserve approvals as current merely because the receipt was refreshed.
3. Preserve existing behavior for task and `[x]` tracking changes: they must not refresh the receipt or create review churn.
4. If receipt refresh cannot be completed, fail the marking operation without leaving a deferred AC or partial receipt publication.
5. Document the automatic refresh and recovery behavior in the lifecycle tool contract.

## Scope

**Problem statement:** A legitimate AC deferral requires agents to perform unnecessary manual receipt bookkeeping after using the tracking tool.

**In scope:**

- `wf_mark_ac` defer path, receipt refresh, projection, recovery response, tests, and lifecycle documentation.

**Out of scope:**

- Automatic approval creation, relaxing independent review, and changes to `[x]` or task tracking semantics.

## Acceptance Criteria

- [x] AC-1: Deferring a required AC through `wf_mark_ac` writes the `[~]` reason, publishes a new receipt, and returns its identity plus re-approval actions in one successful operation.
- [x] AC-2: No prior approval is reported current after the defer/refresh transition; the response guides the agent to the required fresh approvals.
- [x] AC-3: A `[x]` AC update and task update leave the receipt unchanged.
- [x] AC-4: A simulated receipt/projection failure leaves the change doc and receipt unchanged.
- [x] AC-5: Lifecycle documentation explains the automatic receipt refresh and that it does not auto-approve the new contract.

## Tasks

- [x] Add the transactional defer-and-refresh path to `wf_mark_ac`.
- [x] Add positive, no-churn, and failure-atomicity regression tests.
- [x] Update the MCP lifecycle tool contract.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Receipt refresh | implementer | — | Reuse existing receipt/projection authority; do not duplicate it. |
| Regression coverage | qa-reviewer | Receipt refresh | Cover defer, tracking-only, and forced failure paths. |
| Contract update | docs-contract-reviewer | Receipt refresh | Explain action and non-action precisely. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Path scoring is a floor, not a ceiling: ANY lane may also be requested by judgment through the wave's `Requested review lanes` field, and the coordinator is expected to use it. Architecture review especially is usually a judgment call, since an ownership shift or a protocol change can live entirely in files whose paths recruit only the code lane. A requested lane is always honored and costs no receipt churn.

## Affected Architecture Docs

N/A: this reuses the existing lifecycle receipt authority rather than changing a system boundary.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Removes the manual receipt bookkeeping after a contract deferral. |
| AC-2 | required | Preserves the independent approval gate. |
| AC-3 | required | Retains the no-churn tracking behavior. |
| AC-4 | required | Makes the combined operation fail safely. |
| AC-5 | important | Makes recovery discoverable to agents. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Planned during wave 1uj12 after an external-validation deferral required a separate receipt refresh. | Current digest intentionally preserves AC `[~]`; the missing behavior is automatic receipt publication and guidance. |
| 2026-08-05 | Implemented and reviewed the deferred-AC receipt refresh. | Focused mark/receipt regression tests pass; forced projection failure restores the change, ledger, and wave projection. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Refresh the receipt automatically but never approvals. | A deferral changes the approved contract; receipt publication is bookkeeping, while approval remains an independent judgment. | Leave manual re-Prepare (rejected: needless tool choreography); auto-carry approval (rejected: would approve a changed contract). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Receipt refresh partially writes. | Use the existing transactional receipt/projection path and prove failure atomicity. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
