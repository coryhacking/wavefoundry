# wave_install_audit / install-log format mismatch

Change ID: `1p8gw-bug install-audit-log-format-mismatch`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p8gx windows-upgrade-hardening`

## Rationale

During a real native-Windows install/upgrade, **`wave_install_audit` mis-parsed the install log's artifact DESCRIPTION text as a literal file path** (the on-machine agent diagnosed "a known format mismatch between the install-log-format template and the current row format"). `install_log_lib.parse_log` (consumed by `wave_install_audit_response` at `server_impl.py:6098` via `:5985-5988`) expects a row shape that no longer matches what the `install-log-format` template renders, so the parser reads the wrong column — treating the description as a path — and the audit then verifies/repairs against bogus "paths."

## Requirements

1. Realign `install_log_lib.parse_log` with the `install-log-format` template row format so the artifact **path** and the **description** parse into their correct fields — a description is never treated as a path.
2. A **parity test** asserting the `install-log-format` template's row format and `parse_log` agree: a row rendered per the template round-trips through the parser into the expected fields, and a divergence fails the test.
3. `wave_install_audit` reports correctly against a fixture install log rendered per the current template (no description-as-path artifacts).

## Scope

**Problem statement:** `parse_log` and the `install-log-format` template have drifted, so `wave_install_audit` parses artifact descriptions as file paths and mis-reports install state.

**In scope:**

- Realign the parser with the template (fix whichever is wrong — likely the parser's column/regex expectations).
- A parity test tying the template row format to `parse_log`.
- Fix the downstream `wave_install_audit` behavior that consumed the bad parse.

**Out of scope:**

- The subprocess isolation + encoding/path fixes (siblings `1p8gu`/`1p8gv`).

## Acceptance Criteria

- [x] AC-1: `parse_log` extracts the artifact path and description into the correct fields for a template-rendered row; a description containing path-like text is NOT classified as a path. — **CORRECTED after adversarial review (F1, BLOCKER):** the first fix's "any backtick ⇒ prose" rule made 0/15 shipped-template rows stat-able (the template backtick-wraps EVERY path) → CHECK 2 silently disabled. Reworked: `_artifact_path_token` STRIPS markdown backticks + one trailing parenthetical aside FIRST, then classifies STRUCTURALLY (single path-shaped token = PATH; multi-span/leading-prose/conjunction = DESC). Row regex also widened to parse MULTI-SEED tags (`seed-080 + seed-090`, `seed-110 / conditional`) that were silently dropped (rows 2.2/2.8). Now 11 stat-able rows recovered on the shipped template. Tests: `DescriptionAsPathTests`.
- [x] AC-2: a parity test ties the `install-log-format` template row format to `parse_log` (template/parser drift fails the test). — `TemplateParserParityTests` now carries POSITIVE assertions over the SHIPPED template: ≥10 stat-able rows (`test_check2_validates_a_minimum_of_real_paths_on_shipped_template` — FAILS if CHECK 2 is disabled, so the earlier vacuous pass can't recur), exact anchored paths (2.3=`docs/repo-profile.json`, 2.2 with the spaced dir name, 2.8 recovered), and compound 1.2/2.13 stay DESC.
- [x] AC-3: `wave_install_audit` returns correct results against a fixture install log rendered per the current template (regression test reproducing the field defect). — `WaveInstallAuditTests.test_compound_artifact_row_not_reported_as_missing_path` + `_brief_exposes_description_not_path` (compound `[x]` row not flagged), AND `CheckTwoIsNotVacuousTests`: a `[x]` row with a MISSING backtick-wrapped path IS flagged (`test_missing_backtick_wrapped_artifact_is_flagged`) and a PRESENT one is not — proving CHECK 2 actually validates. `_install_audit_row_brief` surfaces `field`/`artifact_path`/`description`.
- [x] AC-4: full framework suite + docs-lint pass. — `run_tests.py`: 3611 tests OK; `docs_lint.py`: ok.

## Tasks

- [x] Read `install_log_lib.parse_log` + the `install-log-format` template (seed); identify the row-format drift. — drift: template row 1.2's `artifact:` value is a compound verification CLAUSE, but the parser stat'd any `artifact:` value as a path.
- [x] Realign the parser (or template) so columns parse correctly. — parser realigned (field-keyword capture + path/description classifier); template left as the canonical source (1.2 legitimately carries a verification clause).
- [x] Add the template↔parser parity test + a `wave_install_audit` regression test reproducing the description-as-path defect.
- [x] Full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| diagnose parser↔template drift | implementer | — | install_log_lib + install-log-format seed |
| realign + fix downstream audit | implementer | diagnose | description never parsed as a path |
| parity + regression tests | qa-reviewer | realign | drift fails; field defect reproduced then fixed |

## Serialization Points

- Independent of `1p8gu`/`1p8gv` (different files: `install_log_lib.py` + the install-log-format seed + `wave_install_audit_response`). No shared touch-points.

## Affected Architecture Docs

`N/A` — confined to the install-log parser + its template; no boundary/flow change. (If the template is a seed, the `seed_edit_allowed` gate applies.)

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core correctness bug. |
| AC-2 | required | Parity test prevents future drift. |
| AC-3 | required | Reproduce + lock the field defect. |
| AC-4 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from a real native-Windows install/upgrade — wave_install_audit parsed artifact descriptions as file paths. | `server_impl.py:5985-5988/:6098` → `install_log_lib.parse_log`; template/row-format drift. |
| 2026-06-27 | First implementation: field-keyword capture + path/description classifier. | (superseded — see below.) |
| 2026-06-27 | Adversarial-review fix (F1, BLOCKER): the first classifier treated ANY backtick as prose, but the shipped template backtick-wraps every path → 0/15 stat-able rows → CHECK 2 was a silent no-op and the 3 parity tests passed VACUOUSLY. Rows 2.2/2.8 (multi-seed tags) were also dropped. Fix: `_artifact_path_token` strips backticks + trailing aside, then classifies structurally; row regex widened for multi-seed tags. Now 11 stat-able rows on the shipped template. Parity tests rewritten with POSITIVE assertions (≥10 stat-able, anchored paths) + a `CheckTwoIsNotVacuousTests` proving a missing path IS flagged. | `test_check2_validates_a_minimum_of_real_paths_on_shipped_template`, `test_known_rows_classify_exactly_as_expected_on_shipped_template`, `CheckTwoIsNotVacuousTests`. 2.3→`docs/repo-profile.json`; 11 stat-able. Full suite 3611 OK. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Add a template↔parser parity test. | The drift was silent (no test tied the template format to the parser). | Fix the parser only (rejected: drift recurs without a parity guard). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Fixing the parser breaks older install logs. | Test against both the current template format and a representative prior row if the format changed intentionally. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
