# Surface the wave_upgrade summary on the primary phase + fix MCP handler_not_ready

Change ID: `1p8kz-bug upgrade-summary-surfacing-and-mcp-handler-readiness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-28
Wave: `1p8gx windows-upgrade-hardening`

## Rationale

A real native-Windows 1.9.5 upgrade field trace surfaced two upgrade-tool UX defects (both present since 1.9.4):

1. **`data.summary` is cleanup-phase-only.** The structured summary block (1p8eu) + its reconciliation findings (1p8et) are emitted by `_print_operator_summary`, which is called **only in `phase_cleanup`** (`upgrade_wavefoundry.py:1467`, phase 5). `wave_upgrade_response` parses the sentinel on every phase, but the default `phase="preflight_to_docs_gate"` (0–3) and `update_index` (4) never emit it. So an agent running `wave_upgrade()` and inspecting the response gets **no `summary`** — yet seed-160 prose tells agents to read `data.summary` (with reconciliation findings) from the upgrade. The field agent saw no summary and had to run `reconcile_scan.py` manually.
2. **`handler_not_ready` is a lazy-init gap.** `_get_handler()` (`server.py:39`) **raises** when `_handler is None`, and `perform_mcp_reload` surfaces that as the `handler_not_ready` diagnostic. The handler is set only at full startup (`server.py:286`), so a tool/reload call in the startup or post-reload window errors. The field agent saw **persistent `handler_not_ready`** across the upgrade.

**Operator-direction follow-up (every-upgrade reconciliation):** the reconciliation scan was originally gated to major/minor bumps (sibling of the config-review recommendation). Operator direction: it must run on **every** upgrade — including a patch bump and a **same-version build-successor** (a rebuilt pack at the same semver during testing) — because a patch or build-successor can change or RETIRE a surface too. The scan is **report-only, cheap, and exclusion-aware** (it never auto-edits and skips the pack tree / index / waves / reports / changelog / journals / tests), so there is no cost to always running it; gating it to major/minor risked a stale local surface slipping through a patch/test cycle. `is_major_or_minor` stays in the summary as an **informational** field only.

## Requirements

1. Emit the structured upgrade summary sentinel (`WAVE_UPGRADE_SUMMARY_JSON:` with from/to version, pruned_count, docs_gate, is_major_or_minor + the **reconciliation findings**) at the END of the **primary phase** (`preflight_to_docs_gate`), in addition to cleanup — so `wave_upgrade()` (default phase) returns `data.summary` with reconciliation. Reuse `_build_upgrade_summary` + `_run_reconciliation_scan` (the scan needs only the rendered surfaces, available after phase 1). `index_update` reflects "not yet run" on the primary-phase summary.
2. Both emissions render from the SAME `_build_upgrade_summary` (no drift). The full human prose stays cleanup-only; the primary phase emits only the machine-readable sentinel (+ a one-line pointer).
3. seed-160 (+ `docs/specs/mcp-tool-surface.md`) clarify that `wave_upgrade()` returns `data.summary` (with reconciliation findings) on the primary response, and the final summary on cleanup.
4. `_get_handler()` / `perform_mcp_reload` **lazy-build** the handler when `_handler is None` (stash the root at startup): a started server (root known) never reports `handler_not_ready`; reload builds-if-absent instead of erroring. The error remains only for a genuinely uninitialized server (no root known).
5. Tests: the primary-phase `wave_upgrade` response carries `data.summary` (with reconciliation) on a major/minor bump; handler lazy-init (a reload/tool call before an explicit set_handler builds it on a known root — no `handler_not_ready`).

## Scope

**Problem statement:** the upgrade tool's structured summary only surfaces on the cleanup phase (not where agents look), and the MCP handler reports `handler_not_ready` in the startup/reload window — both observed in the field on a real upgrade.

**In scope:**

- Emit the summary sentinel on the primary upgrade phase (shared builder); seed-160 + mcp-tool-surface clarification.
- Lazy/graceful handler init in `server.py` so `handler_not_ready` cannot occur on a started server.
- Tests for both.

**Out of scope:**

- Changing upgrade phases/behavior or the reconciliation scan itself; the Windows isolation/encoding/install/gpu changes (siblings `1p8gu`/`1p8gv`/`1p8gw`/`1p8gz`).

## Acceptance Criteria

- [x] AC-1: `wave_upgrade(phase="preflight_to_docs_gate")` (the default) returns `data.summary` including the `reconciliation` findings (test reproduces the field gap). — code already implemented (`_emit_primary_phase_summary`, called at the end of `main()`'s default path). Tests: `PrimaryPhaseSummaryTests.test_reconciliation_populated_on_minor_bump` (real root w/ retired-surface ref), `_via_monkeypatched_scan_on_minor_bump`, `test_emits_exactly_one_sentinel_line`, `test_main_default_path_calls_emit_primary_phase_summary` (AST call-site, before the "Phases 0–4 complete" log). (See AC-6: the scan runs on EVERY upgrade, so `reconciliation` is no longer gated to major/minor.)
- [x] AC-2: the primary-phase and cleanup summaries both render from one `_build_upgrade_summary` (no second source); the full human operator prose stays cleanup-only. — `test_primary_and_prose_render_from_same_builder` asserts identical sentinel JSON key sets + matching load-bearing values for the same inputs.
- [x] AC-3: seed-160 + `docs/specs/mcp-tool-surface.md` document that `data.summary` (with reconciliation) is on the primary `wave_upgrade()` response. — seed-160 lines 46+48 + the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` + `docs/specs/mcp-tool-surface.md` (`preflight_to_docs_gate` phase line, `cleanup` phase line, and the structured-summary block) all carry the 1p8kz phase semantics (primary returns `data.summary`; the reconciliation scan runs on **every** upgrade — `is_major_or_minor` informational only; cleanup re-emits + prints prose).
- [x] AC-4: a started server (root known) never returns `handler_not_ready`; `_get_handler`/`perform_mcp_reload` lazy-build when `_handler is None` (test: reload/tool before explicit set_handler builds it, no `handler_not_ready`). — code already implemented (`server._root` stash + lazy-build in `_get_handler`). Tests: `ServerHandlerLazyInitTests` — raises only when uninitialized (no root); lazy-builds when root known; build_server stashes root; `perform_mcp_reload` returns no `handler_not_ready` after the handler is dropped on a started server.
- [x] AC-5: full framework suite + docs-lint pass. — `run_tests.py`: 3625 tests across 38 files OK; `docs_lint.py`: ok.
- [x] AC-6 (operator direction): the reconciliation scan runs on **EVERY** upgrade (any version delta, incl. a patch bump and a same-version build-successor), **not gated on major/minor**; `summary.reconciliation` populates whenever stale refs exist; `is_major_or_minor` remains in the summary as an informational field only. — code already implemented (the major/minor early-return removed from `_reconciliation_recommendation_lines`; `_print_operator_summary` scans `if root is not None and not failed_phase`; `_emit_primary_phase_summary` scans `if root is not None`). Tests flipped + added: `PrimaryPhaseSummaryTests.test_reconciliation_populated_on_patch_bump`, `test_scan_runs_on_patch_bump`, `test_reconciliation_populated_on_same_version_build_successor`; `ReconciliationRecommendationTests.test_patch_bump_runs` / `test_same_version_build_successor_runs` / `test_downgrade_runs` / `test_findings_supplied_render_regardless_of_version_delta` / `test_reconciliation_line_present_in_summary_on_patch_bump`; `ReconciliationScanIntegrationTests.test_scan_runs_on_patch_bump`. A major/minor case stays green (`test_reconciliation_populated_on_minor_bump`).

## Tasks

- [x] Extract/emit the summary sentinel at the end of the primary phase in `upgrade_wavefoundry.main` (reuse `_build_upgrade_summary` + `_run_reconciliation_scan`); keep the full prose in `phase_cleanup`. — implemented by coordinator (not modified here).
- [x] seed-160 + mcp-tool-surface clarification + re-render the rendered upgrade prompt. — done (this change).
- [x] `server.py`: stash root at startup; `_get_handler`/`perform_mcp_reload` lazy-build when `_handler is None`. — implemented by coordinator (not modified here).
- [x] Tests (primary-phase summary w/ reconciliation; handler lazy-init) + full suite + docs-lint. — done (this change).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| primary-phase summary emit | implementer | — | reuse _build_upgrade_summary; sentinel only |
| handler lazy-init | implementer | — | server.py; must not break startup/reload |
| docs (seed-160 + mcp-tool-surface) | docs-contract-reviewer | summary emit | clarify phase semantics |
| tests | qa-reviewer | both | primary-phase summary + handler lazy-init |

## Serialization Points

- Touches `upgrade_wavefoundry.py` + `server.py`. `upgrade_wavefoundry.py` is shared with the (already-implemented) `1p8gu`/`1p8gv` edits — additive (a new emit at the primary phase), no conflict. `server.py` is a new touch this wave.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (the `wave_upgrade` response/phase semantics). Architecture hub / ADR `N/A` — additive emission + a startup-robustness fix, no boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The field gap: summary must surface on the main upgrade call. |
| AC-2 | important | Single-source = no drift between the two emissions. |
| AC-3 | important | Docs must match the new phase semantics. |
| AC-4 | required | handler_not_ready was observed in the field; must not occur on a started server. |
| AC-5 | required | Regression safety. |
| AC-6 | required | Operator direction: a patch / same-version build-successor can change/retire a surface during testing — the scan must run on every upgrade so no stale local surface slips through. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Planned from the 1.9.5 native-Windows upgrade field trace (no `data.summary` on the upgrade call; persistent `handler_not_ready`). | `upgrade_wavefoundry.py:1467` (cleanup-only summary); `server.py:39/151/286` (handler lazy-init gap). |
| 2026-06-28 | Implementation already landed + smoke-verified by coordinator (`_emit_primary_phase_summary`/`_emit_summary_line` + the `main()` call site; `server._root` stash + `_get_handler` lazy-build). This change added TESTS + DOCS + bookkeeping only — implementation code NOT modified. | Tests: `PrimaryPhaseSummaryTests` (8) in test_upgrade_wavefoundry; `ServerHandlerLazyInitTests` (5) in test_server_tools. Docs: seed-160 + rendered upgrade prompt + mcp-tool-surface phase semantics. Full suite 3624 OK; docs-lint ok. |
| 2026-06-28 | AC-6 (operator direction): reconciliation now runs on EVERY upgrade — the major/minor gate was removed in the code (3 sites; coordinator, not modified here). Flipped the stale patch-gating tests to assert the scan RUNS/populates on a patch bump, a same-version build-successor, and a downgrade; added a build-successor positive test; kept a major/minor case green. Updated seed-160 (lines 46+48), the rendered upgrade prompt, and mcp-tool-surface to "every upgrade"; added AC-6 (required). | Flipped/added: `PrimaryPhaseSummaryTests.test_reconciliation_populated_on_patch_bump`/`test_scan_runs_on_patch_bump`/`test_reconciliation_populated_on_same_version_build_successor`; `ReconciliationRecommendationTests.test_patch_bump_runs`/`test_same_version_build_successor_runs`/`test_downgrade_runs`/`test_findings_supplied_render_regardless_of_version_delta`/`test_reconciliation_line_present_in_summary_on_patch_bump`; `ReconciliationScanIntegrationTests.test_scan_runs_on_patch_bump`. Full suite 3625 OK; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | Emit the summary on the primary phase (not just clarify docs). | The agent looks at the main upgrade response; docs-only would leave the UX gap. | Doc-only clarification (rejected: leaves the agent scraping/manual). |
| 2026-06-28 | Lazy-build the handler rather than only improving the message. | Eliminates `handler_not_ready` on a started server entirely. | Better error text only (rejected: doesn't fix the window). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The handler lazy-init breaks startup/reload (high blast radius). | Keep the explicit-startup path; lazy-build only when `_handler is None` and a root is known; test reload + startup ordering. |
| Primary-phase summary duplicates prose / confuses output. | Emit only the machine-readable sentinel on the primary phase; full prose stays cleanup-only. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
