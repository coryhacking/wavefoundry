# wave_create_wave scaffold placeholder + wave_add_change section placement

Change ID: `12as3-bug wave-create-scaffold-and-admit-placement`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-01
Wave: 12as7 wave-lifecycle-tool-fixes

## Rationale

`wave_create_wave` produces a `wave.md` that fails `wave_validate` immediately, and `wave_add_change` appends change blocks outside the `## Changes` section. Both were hit while opening wave `12as1 design-system-extraction` on 2026-05-01 and required manual fix-up before lint would pass. Reproducible in minutes; root-cause is in two adjacent code paths in `server.py`.

**Observed on 2026-05-01 against HEAD:**

- Ran `wave_create_wave(slug="design-system-extraction", mode="create")`. The emitted `wave.md` contained the literal string `Last verified: <date>`, which `wave_validate` flags as `missing or invalid "Last verified" metadata`.
- Ran `wave_add_change` three times. Each call appended a `Change ID: ... / Change Status: ...` block immediately before `## Dependencies`. Because the scaffold places `## Changes` (empty), `## Wave Summary`, `## Journal Watchpoints`, `## Dependencies` in that order, the inserted blocks landed *after* `## Journal Watchpoints` rather than inside `## Changes`. The `## Changes` section stayed empty, triggering a second lint-adjacent issue: a human reader and the lint's watchpoint heuristic both fail to see admitted changes where they belong.

Both behaviors already have regression risk: every new wave scaffolded via MCP fails lint by default, and every change admission produces mislocated blocks.

## Requirements

1. **Scaffold date field.** `wave_create_wave` must emit `Last verified: <ISO-8601 date of today, UTC>` instead of the literal `<date>` placeholder. Use the same date source that the rest of the server uses for today (repo helper if one exists; otherwise `datetime.date.today().isoformat()` with a comment noting this runs in the server process's local timezone is acceptable, matching the current convention — see `lifecycle_id.py` use of local date).
2. **Admit-time section placement.** `wave_add_change` must insert `Change ID: ... / Change Status: ...` blocks **inside the `## Changes` section**, not immediately before `## Dependencies`. Required behavior:
   - Find the `## Changes` heading.
   - Insert the new change block between `## Changes` and the next `## ` heading (or end-of-file).
   - Append (after any existing change blocks within `## Changes`) rather than prepending, so admission order is preserved.
   - When `## Changes` is missing (shouldn't happen with the scaffold, but guard against operator-edited waves), create it above the first existing `## ` heading.
3. **Fallback unchanged.** Pre-existing waves that have change blocks in the legacy before-`## Dependencies` position must not be rewritten by this change — the fix applies on new admissions only. Existing correct layouts must round-trip unchanged.
4. **Test coverage.** Add tests under `.wavefoundry/framework/scripts/tests/test_server_tools.py`:
   - `test_wave_create_wave_last_verified_populates_today` — the emitted `wave.md` has `Last verified: <today's ISO date>`, not `<date>`.
   - `test_wave_create_wave_lint_clean` — after `wave_create_wave`, running docs lint over the created `wave.md` passes (no `Last verified` or `Journal Watchpoints` errors introduced by scaffolding alone); may still require a journal reference to pass end-to-end, so this test asserts specifically that scaffold-originated errors are absent.
   - `test_wave_add_change_inserts_inside_changes_section` — after `wave_create_wave` + `wave_add_change`, the added `Change ID:` block appears between `## Changes` and the next `## ` heading.
   - `test_wave_add_change_preserves_order` — admit three changes; all three blocks appear inside `## Changes` in admission order.
   - `test_wave_add_change_legacy_layout_round_trips` — craft a wave.md with change blocks already placed before `## Dependencies` (legacy); admit one more change; existing blocks stay in place and the new block lands inside `## Changes`. (Asserts the migration rule in Requirement 3.)
5. **No contract changes.** Tool response envelopes (`status`, `data`, `diagnostics`, `next_tools`, `usage`) must not change. Existing test cases for `wave_create_wave_response` and `wave_add_change_response` must still pass without edits.

## Scope

**Problem statement:** `wave_create_wave` emits an invalid `Last verified` placeholder that trips `wave_validate` on every new wave, and `wave_add_change` places change blocks outside the `## Changes` section because its anchor is `## Dependencies` rather than `## Changes`. Operators hitting these bugs must hand-edit `wave.md` before lint will pass — which defeats the point of MCP lifecycle tools.

**In scope:**

- `create_wave` function at `.wavefoundry/framework/scripts/server.py:2383` — replace `<date>` with today's ISO date.
- `wave_add_change_response` insertion logic at `.wavefoundry/framework/scripts/server.py:2563-2566` — switch anchor from `## Dependencies` to `## Changes` with tail-append semantics.
- Tests in `.wavefoundry/framework/scripts/tests/test_server_tools.py` as listed in Requirement 4.

**Out of scope:**

- Other wave-lifecycle tools (`wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_close`).
- Lint validator changes — the lint already correctly flags `<date>`; the fix is in the emitter.
- Journal-reference auto-creation — already a separate concern; operator or journal-distillation flow owns that.
- Migrating existing wave.md files with legacy block placement — explicitly excluded per Requirement 3.

## Acceptance Criteria

- **AC-1** (Scaffold date): `wave_create_wave(mode="create")` emits `Last verified: <today's ISO date>` instead of `<date>`. Asserted by `test_wave_create_wave_last_verified_populates_today`.
- **AC-2** (Lint-clean scaffold): `wave_validate` against a freshly scaffolded `wave.md` does not emit `missing or invalid "Last verified" metadata`. Journal-reference and watchpoint-text errors are outside this AC — operators resolve those per existing docs.
- **AC-3** (Admit placement): `wave_add_change(mode="create")` inserts the `Change ID:` block inside the `## Changes` section (between `## Changes` and the next `## ` heading). Asserted by `test_wave_add_change_inserts_inside_changes_section`.
- **AC-4** (Admit order): multiple admissions preserve insertion order inside `## Changes`. Asserted by `test_wave_add_change_preserves_order`.
- **AC-5** (Legacy round-trip): wave.md files with change blocks already in the pre-`## Dependencies` position are not rewritten; new admissions still land inside `## Changes`. Asserted by `test_wave_add_change_legacy_layout_round_trips`.
- **AC-6** (Envelope compat): existing `test_wave_create_wave_dry_run`, `test_wave_create_wave_last_verified_populates_today`'s sibling tests, and `wave_add_change` existing tests all pass without modification to the tools' response shape.

## Tasks

- Before editing framework scripts, set `.wavefoundry/guard-overrides.json` `framework_edit_allowed.enabled: true`; restore after.
- `.wavefoundry/framework/scripts/server.py` `create_wave` (line 2383) — replace the hardcoded `"Last verified: <date>\n"` with today's ISO date. Use `datetime.date.today().isoformat()` unless a canonical helper exists in the module (grep for existing date helpers first).
- `.wavefoundry/framework/scripts/server.py` `wave_add_change_response` insertion logic (lines 2563-2566) — replace the `## Dependencies` anchor with a `## Changes` section-bounded insertion:
  - Locate `## Changes` heading.
  - Find the next `## ` heading after it (or EOF).
  - Insert the new change block immediately before that next heading, after any existing change blocks in the section.
  - Preserve blank-line spacing between blocks.
- Add the five tests from Requirement 4 under `.wavefoundry/framework/scripts/tests/test_server_tools.py` — name them per the Requirement 4 list; follow existing test style (use `self.srv.wave_create_wave_response` / `self.srv.wave_add_change_response`, temp-root fixture).
- Run framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`. All existing tests must pass.
- Restore `.wavefoundry/guard-overrides.json` `framework_edit_allowed.enabled: false`.
- Run `wave_validate` end-to-end against a freshly scaffolded test wave to confirm lint passes on the scaffold-owned fields (journal reference separately required; that's the operator's job).

## Agent Execution Graph


| Workstream           | Owner       | Depends On      | Notes                                                              |
| -------------------- | ----------- | --------------- | ------------------------------------------------------------------ |
| scaffold-date-fix    | implementer | —               | `create_wave` emits ISO-8601 today                                 |
| admit-placement-fix  | implementer | —               | `wave_add_change` anchors on `## Changes`                          |
| tests                | implementer | scaffold-date-fix, admit-placement-fix | Five new tests + regression of existing tests   |
| review               | reviewer    | all above       | code-reviewer + qa-reviewer lanes                                  |


## Serialization Points

- `server.py` is single-owner for this change — no other in-flight wave modifies the same functions (verify at implementation).
- Framework-edit guard must be flipped for the duration of edits.

## Affected Architecture Docs

N/A — bug fix confined to two adjacent functions in `server.py` and their tests. No boundary, flow, or verification contract changes. If `docs/architecture/current-state.md` mentions scaffold format explicitly (grep at implementation), update the example to match.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority     | Rationale                                                                     |
| ---- | ------------ | ----------------------------------------------------------------------------- |
| AC-1 | required     | Every new wave fails lint without the fix.                                    |
| AC-2 | required     | Lint-clean scaffold is the minimum bar for the tool.                          |
| AC-3 | required     | Misplaced change blocks make the `## Changes` section uninformative.          |
| AC-4 | required     | Admission order is a property operators rely on for change sequencing docs.   |
| AC-5 | important    | Migration safety — don't rewrite operator-edited legacy layouts.              |
| AC-6 | required     | Envelope compat prevents silent breakage of downstream MCP callers.           |


## Progress Log


| Date       | Update                                                                                                                                                                                                                                                      | Evidence                                                   |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 2026-05-01 | Bug identified while opening wave `12as1 design-system-extraction`. Two separate scaffold issues hand-fixed; reported to operator; bug doc opened                                                                                                           | Session transcript; manual edits to `docs/waves/12as1 design-system-extraction/wave.md` |
| 2026-05-01 | Implementation: added `import datetime` and `datetime.date.today().isoformat()` in `create_wave` (server.py:2387); replaced `## Dependencies` anchor with new `_insert_change_block_into_changes_section` helper (server.py above `wave_add_change_response`); added 4 tests under `WaveCreateWaveLastVerifiedTests` and `WaveAddChangeSectionPlacementTests` | server.py diff; tests/test_server_tools.py diff; 426 framework tests pass |


## Decision Log


| Date       | Decision                                                                                   | Reason                                                                                                                  | Alternatives                                          |
| ---------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-05-01 | Scope limited to the two identified functions; no broader lifecycle audit                  | Both bugs reproducible, isolated to adjacent call sites, and already blocking normal operation; audit is a separate ask | Bundle a full lifecycle-tool scaffold audit           |
| 2026-05-01 | Do not migrate existing wave.md files with legacy block placement                          | Operator-edited content is never rewritten silently; test covers the round-trip case                                    | Rewrite legacy wave.md files on first admission       |
| 2026-05-01 | Use `datetime.date.today().isoformat()` for scaffold date (local timezone)                 | Matches existing `lifecycle_id.py` convention in this codebase; UTC would diverge from lifecycle ID epoch semantics     | Force UTC via `datetime.now(timezone.utc).date()`     |


## Risks


| Risk                                                                 | Mitigation                                                                         |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Insertion logic breaks waves with unusual heading orders             | Test covers missing `## Changes` heading (guard branch); test fixture exercises reordered headings |
| Date-source timezone ambiguity                                       | Decision Log pins local-date convention; matches existing `lifecycle_id.py` behavior |
| Test for AC-2 (lint-clean scaffold) flakes if journal validator evolves | AC-2 narrowly asserts scaffold-originated `Last verified` errors are absent; journal-reference errors are out of scope |
| Admission-order preservation fails across legacy + new layouts       | AC-5 test exercises the mixed case explicitly                                      |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
