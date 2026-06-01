# Doc-Dialog Tables Inherit `white-space: nowrap` from Parent Agent-Dialog Rule

Change ID: `130o3-bug doc-dialog-table-nowrap-leak`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-31
Wave: 130et framework-bin-mcp-server-launcher

## Rationale

Operator report 2026-05-31: in the dashboard's change-doc dialog, the Risks table's first column shows as nowrap — long sentences get cut off at the dialog edge instead of wrapping. Verified locally: the symptom is not Risks-specific. **Every** table in every change doc rendered through `.doc-dialog-body` has the same nowrap behavior on its first column.

Root cause: `dashboard.css:2612-2614` declares an unconditional rule:

```css
.agent-dialog-body td:first-child {
  white-space: nowrap;
}
```

`DialogFrame` (`dashboard.js:886`) wraps every dialog body in `<div className="agent-dialog-body">`. The `doc-dialog` adds its own `<div className="doc-dialog-body">` nested inside that wrapper (`dashboard.js:4285`). The selector `.agent-dialog-body td:first-child` matches descendant `<td>` cells through both layers, so doc-dialog tables inherit the nowrap rule.

This makes the existing opt-in mechanism — `NOWRAP_FIRST_COL_SECTIONS = {"AC Priority", "Progress Log", "Decision Log"}` in `dashboard.js:4158` plus the `table--nowrap-first` CSS class in `dashboard.css:3554-3556` — effectively dead code: every doc-dialog table already gets nowrap on its first column, whether the JS adds the class or not.

The intended behavior (per the JS opt-in design) is: doc-dialog tables wrap by default; only AC Priority / Progress Log / Decision Log opt in to nowrap so their compact short-token first columns stay on one line.

## Requirements

1. `.doc-dialog-body` tables must wrap their first column by default — long sentences in Risks/Decision Log notes/Mitigation columns must reflow to fit the dialog width, not extend past it and get clipped by the parent dialog's `overflow: hidden`.
2. The existing opt-in mechanism (`table--nowrap-first` class added by `dashboard.js` for AC Priority / Progress Log / Decision Log) must continue to enable nowrap for those specific tables.
3. The fix must not affect other dialog views that legitimately use `.agent-dialog-body` directly (e.g. the AgentDialog component used by `agents/*.md` docs). The nowrap rule there is intentional for short label/value tables.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css` — add a single override rule scoped to `.doc-dialog-body` that resets `white-space` to `normal` on first-column cells. The existing `.doc-dialog-body table.table--nowrap-first td:first-child` rule (line 3554-3556) has higher specificity and continues to apply nowrap when the class is set.

**Out of scope:**

- Refactoring the dialog DOM structure to remove the double-body nesting. Keeping the wrapper structure preserves the existing CSS layering for headers, padding, and scrollbars; the targeted override is the smallest correct fix.
- Re-evaluating which sections deserve nowrap. The current set (AC Priority / Progress Log / Decision Log) is unchanged.
- Tests. CSS rules of this shape (`.doc-dialog-body td:first-child { white-space: normal }`) don't have a test surface in this repo — the framework test suite covers structure, not rendered CSS. Manual verification via the dashboard is the verification path.

## Acceptance Criteria

- [x] AC-1: `.doc-dialog-body td:first-child` has `white-space: normal` declared explicitly, overriding the inherited `.agent-dialog-body td:first-child { white-space: nowrap }` rule.
- [x] AC-2: Tables in change docs (Risks, Related Work, Requirements, etc.) wrap their first column to fit the dialog width — no horizontal overflow or clipped text.
- [x] AC-3: AC Priority / Progress Log / Decision Log tables continue to apply nowrap to their first column (the `table--nowrap-first` opt-in path still works).
- [x] AC-4: Agent dialogs (AgentDialog component used for `agents/*.md` views) remain unchanged — their `.agent-dialog-body td:first-child` rule continues to apply because they don't nest a `.doc-dialog-body` inside.
- [x] AC-5: Manual verification: open the 130ol change doc dialog and confirm the Risks table first column wraps. Open the same doc and confirm AC Priority still has compact single-line AC IDs in its first column.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `.doc-dialog-body td:first-child { white-space: normal; }` to `dashboard.css` next to the existing `.doc-dialog-body table.table--nowrap-first td:first-child` rule so the relationship is locally visible
- [x] Re-render platform surfaces (dashboard.css is part of `.wavefoundry/framework/dashboard/`; pack rebuild ships it)
- [x] Manual verification per AC-5
- [x] Close `framework_edit_allowed` gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The CSS rule that lands the fix |
| AC-2 | required | The observable behavior change operators see |
| AC-3 | required | The opt-in path must keep working for the three tables that do want nowrap |
| AC-4 | required | No regression for agent dialogs |
| AC-5 | required | Verification path — no automated test surface exists for CSS rendering |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-31 | Targeted override in `.doc-dialog-body` rather than scoping the parent rule | The parent rule is intentional for agent dialogs. An override is one line, preserves agent-dialog behavior, and keeps the opt-in mechanism (already in place via `table--nowrap-first`) as the authoritative way to enable nowrap | Scope the parent rule to exclude doc-dialog (rejected — more complex selector, easier to break in future). Remove the parent rule entirely (rejected — would regress agent dialog tables) |
| 2026-05-31 | Keep the existing `NOWRAP_FIRST_COL_SECTIONS` set and `table--nowrap-first` class | The set's three sections (AC Priority / Progress Log / Decision Log) all have short-token first columns where nowrap is genuinely desirable. The bug is that the opt-out was missing for everyone else, not that the opt-in was wrong | Remove the opt-in mechanism entirely (rejected — those three tables look better with nowrap) |
| 2026-05-31 | Add to existing wave 130et | Operator-reported framework-provisioning hot-fix in the same session; fits the wave's bucket | New wave (rejected — overhead for a one-line CSS fix) |

## Risks

| Risk | Mitigation |
|---|---|
| The override could accidentally affect other classes that nest under `.doc-dialog-body` | The selector targets `td:first-child` only and the `.doc-dialog-body` class is only ever applied to the change-doc body wrapper. No collision risk |
| Future tables added to `NOWRAP_FIRST_COL_SECTIONS` won't immediately take effect if a higher-specificity rule shadows the opt-in | The existing `.doc-dialog-body table.table--nowrap-first td:first-child` rule already has higher specificity than the new `.doc-dialog-body td:first-child` rule; the opt-in continues to work |

## Related Work

- Sixth change in wave 130et alongside `130eu` (mcp-server launcher), `130f9` (wave-gate rearchitecture), `130nf` (project-meta layer scoping), `130o2` (transient artifact filter), `130ol` (graph extractor — planned). All session-level framework provisioning fixes from operator reports.
- The opt-in mechanism (`table--nowrap-first`) was originally added when AC Priority / Progress Log / Decision Log were the first tables to need nowrap. The inherited rule at line 2612 predates that opt-in design and was never updated to defer to it. This change closes that gap.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
