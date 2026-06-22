# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-21

wave-id: `1p6nm dashboard-ui-navigation`
Title: Dashboard Ui Navigation

## Objective

Turn the single-scroll dashboard into a navigable shell so the operator's primary focus (waves, changes, ACs, tasks) owns the home page and the framework surface can grow. Introduce a **collapsible left sidebar (default-collapsed icon rail)** + hash routing + a data-driven section registry that decouples nav chrome from views, and use it for the first move: **relocate the graph index visualization off the home page into its own Graph view.** When this closes, "Work" is the focused home, the graph lives in its own full-width view, and Config/Secrets/Docs sections are drop-in for later increments.

## Changes

Change ID: `1p6nl-enh dashboard-nav-shell-and-graph-view`
Change Status: `implemented`

Completed At: 2026-06-21

## Wave Summary

Wave `1p6nm` (Dashboard Ui Navigation) delivered one change: Dashboard UI — collapsible-sidebar nav shell + graph relocation (increment 1).

**Changes delivered:**

- **Dashboard UI — collapsible-sidebar nav shell + graph relocation (increment 1)** (`1p6nl-enh dashboard-nav-shell-and-graph-view`) — 9 ACs completed. Key decisions: Collapsible left sidebar, **default-collapsed** to an icon rail.; Decouple nav chrome from a data-driven section registry + hash routing.
## Journal Watchpoints

- **Watchpoint — graph history collision:** `GraphPanel` uses its own internal `pushState` breadcrumbs (`dashboard.js:3610`); page-level hash routing must isolate/namespace from it or back/forward will break. Test both together.
- **Watchpoint — graph reflow:** the SVG/ELK graph must relayout when the sidebar collapses/expands (it gains width when collapsed); verify on toggle.
- **Guard:** the dashboard lives in `.wavefoundry/framework/dashboard/` (canonical framework source, not seed-rendered) — implementation needs the `framework_edit_allowed` gate.
- **Follow-up (deferred, not blocking):** Config / Secrets / Docs views + grouped-section rendering are registered in the IA as roadmap; the registry carries `group` from day one so they're drop-in later.
- **Scope discipline:** additive shell change — wrap `<main>` in a registry-driven view-switch and move one component; `GraphPanel` internals stay untouched. No build step, no new endpoints.

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-19 (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, accessibility lens). Scope: increment 1 — collapsible-sidebar nav shell (default-collapsed icon rail) + section registry + hash routing + Work view (home minus graph) + relocated Graph view. Grounded: `GraphPanel` is self-contained (`{snapshot}` prop, own `/api/graph` fetch), so relocation is additive; shell change wraps the main content area in a registry-driven view-switch and moves one component; stays no-build. Strongest challenge: `GraphPanel`'s internal `pushState` breadcrumbs colliding with page-level hash routing (back/forward). Conditions into implement: (1) isolate/namespace graph `pushState` from page routing and test back/forward across both; (2) relayout the SVG/ELK graph on sidebar collapse/expand; (3) accessible collapsed icon rail (`aria-label`/tooltips + keyboard nav for the toggle); (4) frontend is manual-verify-heavy (no JS test harness) — deliberate no-regression pass over modals/SSE/theme/metrics/agent dialogs; (5) resolve open questions (icon set, mobile breakpoint, Work view contents) at implement. Strongest alternative: ship top-nav tabs now (rejected — operator chose the collapsible sidebar; the chrome-agnostic registry makes the look swappable later regardless). Faithfulness N/A (UI restructure; no detection/binding/data change; no new endpoints).
- wave-council-delivery: approved (PASS) — delivery review 2026-06-21 (moderator: wave-council; primer-depth: lightweight; fixed-seat: red-team adversarial primer; seats: reality-checker, architecture-reviewer, qa-reviewer, accessibility lens [rotating fifth]; rotating-seat: accessibility-reviewer — UI/a11y change: collapsed icon rail, tooltips, brand-as-toggle). Lane verdicts: architecture-reviewer PASS, accessibility-reviewer PASS, code-reviewer CONCERNS, qa-reviewer CONCERNS — zero blockers. Adversarial verify: all four "major" findings verified real but severity-corrected major to minor (deletion-only dead code, no behavior/correctness/a11y impact); none rejected; zero blockers. Strongest challenge: the operator-directed Header removal orphaned a dead-code island (StateBadge/computeState + .site-header/.header-*/.state-* + @keyframes pulse + dark/@media variants) — RESOLVED in-session (deletion-only, suite-covered, live selectors preserved). Strongest alternative: fold the cleanup into 1p6nl rather than a follow-up wave (adopted, council-unanimous, fix-now-not-later). The primer's "--header-h dead token ships" claim was refuted by all four seats — the token was already removed by AC-9. Doc drifts reconciled (open-Q#4 brand-as-toggle, token list, Header-retained task line, "no shell edits" ADR wording, graph-breadcrumb-reset note in AC-5/ADR). All five prepare conditions confirmed delivered (graph History-state isolation traced non-colliding across five interleaving scenarios; viewBox reflow; accessible rail; no-regression; open questions resolved). Re-verified post-fix: node --check OK, full suite 3335 green + 161 dashboard tests, served-asset smoke 200s. Faithfulness N/A (UI restructure; no detection/binding/data change, no new endpoints).
- operator-signoff: approved — operator confirmed closure 2026-06-21 ("run the final checks and close the wave"). Final checks independently re-run green: node --check OK, full suite 3335, served-asset smoke 200s, dead-code removal confirmed.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-19: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, docs-contract-reviewer, accessibility lens; fixed-seat: red-team; rotating-seat: docs-contract-reviewer (wave adds an ADR + documentation updates); scope: `1p6nl` dashboard nav shell + graph relocation, increment 1; strongest-challenge: `GraphPanel` internal `pushState` colliding with page hash routing (+ graph reflow on collapse) — conditions into implement: isolate graph history, relayout on collapse, accessible icon rail, deliberate no-regression pass, resolve open questions; strongest-alternative: top-nav tabs now (rejected — operator chose sidebar; registry keeps the chrome swappable); additive shell change, stays no-build, no new endpoints; faithfulness N/A)

- **Delivery Wave Council [wave-council-delivery] — 2026-06-21: PASS** (moderator: wave-council; primer-depth: lightweight; fixed-seat: red-team adversarial primer; seats: reality-checker, architecture-reviewer, qa-reviewer + rotating fifth = accessibility-reviewer (rotating because this is a UI/a11y change — collapsed icon rail, tooltips, brand-as-toggle). Lane verdicts: architecture + accessibility PASS, code + qa CONCERNS — **zero blockers**. Adversarial verification: four "major" findings all verified real but severity-corrected major to minor (deletion-only dead code, no behavior/correctness/a11y impact); zero rejected; zero blockers. **Material disagreement + resolution:** the red-team primer's headline claim that a misleading dead `--header-h` token shipped was REFUTED by all four seats and independently — the token was already removed by AC-9; the real defect was the inverse (a stale change-doc task line), since reconciled. **Strongest challenge resolution:** the Header-removal dead-code island was deleted in-session per fix-now-not-later (council-unanimous; deletion-only; covered by the green 3335 + 161 suite) rather than deferred to a follow-up wave; live `.shell`/`.site-footer`/`.status-*`/`metric-pulse`/`sse-pulse`/`--rail-w` preserved. All five prepare conditions confirmed delivered (graph History-state isolation traced non-colliding across five interleaving scenarios; viewBox reflow; accessible rail; no-regression; open questions resolved). **Pre-implementation gate reconciliation:** the prepare-council readiness verdict (2026-06-19) is structured and machine-readable. Re-verified post-fix: node --check OK, suite 3335 + 161 green, served-asset smoke 200s.)

## Dependencies

- No external wave dependencies.
