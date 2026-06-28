# Structured wave_upgrade summary

Change ID: `1p8eu-enh structured-wave-upgrade-summary`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8ev upgrade-reconciliation`

## Rationale

`wave_upgrade` returns the entire upgrade subprocess stdout+stderr as one verbatim `output` blob (`server_impl.wave_upgrade_response`: `output = (result.stdout or '') + (result.stderr or '')`), with no `next_tools`. In the 1.8.1→1.9.4 field upgrade the agent had to `jq`/`tail` the output **twice** to find phase status, the docs-gate result, and the next step.

Every value the agent dug for already exists — but only as PROSE inside `upgrade_wavefoundry._print_operator_summary` (version, `Files pruned: N`, docs-gate `PASSED/FAILED/NOT RUN` via `_docs_gate_summary_line`, index-update state, the major/minor reconciliation recommendation via `_is_major_or_minor_upgrade`, and a numbered next-steps list). Exposing these as **structured fields** removes the parsing friction and lets agents read computed values instead of regex-scraping prose whose wording can change. It also gives the sibling reconciliation scan (`1p8et`) a structured field to surface its findings in.

## Requirements

1. `upgrade_wavefoundry` builds the operator summary **once** as a dict and emits it BOTH as the existing human prose AND machine-readably (a `WAVE_UPGRADE_SUMMARY_JSON:` sentinel line and/or a `.wavefoundry/logs/upgrade-summary.json` file), carrying at least: `from_version`, `to_version`, `pruned_count`, `docs_gate` (passed/failed/not-run), `index_update`, `failed_phase`, `is_major_or_minor`, and (from `1p8et`) the `reconciliation` findings.
2. `wave_upgrade` (server_impl) parses the machine-readable summary into `data['summary']`, adds a top-level `next_step`, and populates `next_tools` (e.g. `wave_upgrade_status`, `wave_mcp_reload`).
3. Parsing is **fail-safe**: an absent or malformed summary falls back to the raw `output` with no exception; `output` and `exit_code` remain present and unchanged (back-compatible).
4. The summary is rendered from ONE dict source-side so the prose and the machine-readable form cannot drift.
5. The `summary` block is documented (seed-160 one-line note + `docs/specs/mcp-tool-surface.md` `wave_upgrade` entry) so agents read fields instead of grepping `output`.

## Scope

**Problem statement:** the `wave_upgrade` response is an unstructured blob; agents parse phase status / docs-gate / next-step by hand.

**In scope:**

- The summary dict source-side (reuse `_docs_gate_summary_line`, `_is_major_or_minor_upgrade`) emitted machine-readably alongside the existing prose.
- The parse boundary-side in `wave_upgrade_response` → `data['summary']` + `next_step` + `next_tools`, fail-safe.
- The doc note (seed-160 + mcp-tool-surface).

**Out of scope:**

- Changing upgrade behavior or phases (output content is unchanged; only its structure is exposed).
- The reconciliation scan itself (sibling `1p8et`); this change only adds the field that carries its findings.

## Acceptance Criteria

- [x] AC-1: `upgrade_wavefoundry` renders the operator summary from one dict and emits it machine-readably (sentinel line and/or `.wavefoundry/logs/upgrade-summary.json`) without removing the human prose. — Implemented as the `WAVE_UPGRADE_SUMMARY_JSON:` sentinel line built from the single `_build_upgrade_summary` dict (the file-on-disk variant was the optional "and/or" alternative; the sentinel line was chosen).
- [x] AC-2: `wave_upgrade` returns `data['summary']` (`from_version`, `to_version`, `pruned_count`, `docs_gate`, `index_update`, `failed_phase`, `is_major_or_minor`, `reconciliation`) plus a top-level `next_step` and `next_tools`; `output` and `exit_code` are unchanged.
- [x] AC-3: parsing is fail-safe — an absent/malformed summary falls back to `output` with no exception; tested with a missing and a corrupt summary.
- [x] AC-4: the `summary` block is documented in seed-160 and `docs/specs/mcp-tool-surface.md`.
- [x] AC-5: full framework suite and docs-lint pass.

## Tasks

- [x] Build the summary dict once in `upgrade_wavefoundry._print_operator_summary` (reuse `_docs_gate_summary_line` / `_is_major_or_minor_upgrade`); emit it machine-readably + keep the prose.
- [x] Parse the summary in `wave_upgrade_response`; add `data['summary']`, `next_step`, `next_tools`; fail-safe fallback to `output`.
- [x] Add the seed-160 + mcp-tool-surface doc note.
- [x] Tests (`test_upgrade_wavefoundry.py`, `test_server_tools.py`): summary fields present; missing/corrupt-summary fallback.
- [x] Run full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Source summary | implementer | — | One dict; emit prose + machine-readable. |
| Boundary parse | implementer | Source summary | `data['summary']` + next_tools; fail-safe. |
| Docs | docs-contract-reviewer | Boundary parse | seed-160 + mcp-tool-surface note. |
| QA | qa-reviewer | all | Field presence + fallback tests. |

## Serialization Points

- Depends on `1p8et` for the `reconciliation` field shape; shares `upgrade_wavefoundry.py` and `server_impl.py` `wave_upgrade` — edit as one coordinated unit with `1p8et`.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (the `wave_upgrade` response shape). Architecture hub / ADR `N/A` — additive response field, no boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Single-source summary is the anti-drift contract. |
| AC-2 | required | The structured fields are the deliverable. |
| AC-3 | required | Must never break existing callers / the raw fallback. |
| AC-4 | important | Discoverability so agents use the fields. |
| AC-5 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from the 1.8.1→1.9.4 field trace (agent jq/tail'd the output twice) + trace-mining synthesis. | Values exist only as prose in `_print_operator_summary`; `wave_upgrade_response` returns one `output` blob, no `next_tools`. |
| 2026-06-27 | Implemented. `_build_upgrade_summary` assembles the dict once; `_print_operator_summary` renders prose + the `WAVE_UPGRADE_SUMMARY_JSON:` sentinel from it (carrying the 1p8et `reconciliation` findings). `server_impl._parse_upgrade_summary` parses the sentinel into `data['summary']`, fail-safe; `_upgrade_next_step` adds `next_step` + `next_tools`; `output`/`exit_code` unchanged. seed-160 + mcp-tool-surface note added. | `test_upgrade_wavefoundry` UpgradeSummarySentinelTests (4) + ReconciliationScanIntegrationTests pass; `test_server_tools` WaveUpgradeMcpToolTests incl. summary/missing/corrupt-fallback (5 new) pass; full suite 3542 tests pass; docs-lint ok. |
| 2026-06-27 | Adversarial-review fixes (pre-1.9.4): TA-1 deleted the duplicate `_WAVE_UPGRADE_SUMMARY_SENTINEL` in server_impl — now imports the single `upgrade_wavefoundry.WAVE_UPGRADE_SUMMARY_SENTINEL` via `_upgrade_summary_sentinel()` (literal fallback pinned by a round-trip test); F1 `_parse_upgrade_summary` broadened to `except Exception` (RecursionError-safe); F2 `next_step`/`next_tools` now computed before the returncode check and attached to the error response too. | New tests: round-trip emit→parse (TA-1), sentinel-constant-imported-not-redefined (TA-1), deeply-nested-no-exception (F1), failure-response-carries-next_step (F2). `test_server_tools` WaveUpgradeMcpToolTests all pass; full suite 3555 pass; docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Additive `summary` field; keep `output`/`exit_code`. | Back-compatible; existing callers/tests unaffected. | Replace `output` (rejected: breaks callers). |
| 2026-06-27 | Render prose + machine-readable from one dict. | Two sources would drift. | Parse the prose (rejected: brittle to wording changes — the exact friction being fixed). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Two-sources-of-truth drift (sentinel vs prose). | Render both from one dict. |
| Malformed summary breaks the tool. | Fail-safe parse → fall back to `output`; tested. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
