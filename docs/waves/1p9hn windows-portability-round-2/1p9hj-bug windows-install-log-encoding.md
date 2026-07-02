# Windows install-log encoding: strict UTF-8 read crashes wave_install_audit on non-UTF-8 logs

Change ID: `1p9hj-bug windows-install-log-encoding`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

`install_log_lib.py:346` reads the operator install log with `log_path.read_text(encoding="utf-8")` and no `errors=` parameter. If the log was written by a PowerShell invocation that defaulted to ANSI (cp1252) or UTF-16 (BOM `\xff\xfe`) — both documented in seed-011 as common Windows pitfalls — Python raises `UnicodeDecodeError` before `is_unparseable()` or `parse_log()` can run.

Wave 1p9bh built `is_unparseable()` to survive non-UTF-8 install logs by matching encoding-agnostic separator bytes. That safety net only works on *decodable* mojibake; it never runs when the strict read raises first. The two call sites in `server_impl.py` handle this differently:

- `wave_install_audit_response` (`:6361`): no `try/except` around the read → `UnicodeDecodeError` propagates → opaque broken tool call on Windows.
- `wave_audit` advisory site (`:6209–6243`): inside `try/except Exception: pass` → silently swallowed → the intended `install_log_unparseable` advisory never fires.

## Requirements

1. `install_log_lib.read_install_log()` must read the install log with `errors="replace"` so any byte sequence decodes without raising.
2. `is_unparseable()` must classify a log where replacement characters are present and no parseable rows (`## Phase` headings or `- [ ]` task rows) were found as unparseable — so UTF-16 BOM logs (which become garbage after replacement) still trigger the actionable `install_log_unparseable` error rather than returning vacuous success.
3. A regression test must write a UTF-16-BOM log (via `write_bytes`) and a raw cp1252 log (e.g. `\x97` em-dash), then assert `read_install_log` returns a string (not raising) and the audit emits the `install_log_unparseable` diagnostic rather than crashing or reporting success.

## Scope

**Problem statement:** On Windows, `wave_install_audit` crashes or silently misbehaves when the operator's install log was written in a non-UTF-8 encoding, because the strict-UTF-8 read raises before the 1p9bh safety net can run.

**In scope:**

- `install_log_lib.py:346`: add `errors="replace"` to the `read_text` call
- `is_unparseable()`: extend classification to catch the replacement-char-but-no-rows case
- Regression tests for UTF-16-BOM and cp1252 log bytes

**Out of scope:**

- Writing the install log itself in a different encoding (operator controls this; seed-011 already documents the pitfall)
- Encoding of other files read by the install/upgrade flow

## Acceptance Criteria

- [x] AC-1: `install_log_lib.read_install_log()` does not raise on a UTF-16-BOM or cp1252-encoded log file — `errors="replace"` added; two byte-level tests
- [x] AC-2: A UTF-16-BOM log causes `is_unparseable()` to return `True` (replacement chars with no parseable rows) — new replacement-char/NUL branch, independent of the phase-heading pattern (per council red-team finding)
- [x] AC-3: `wave_install_audit` returns the `install_log_unparseable` diagnostic for the UTF-16-BOM case rather than crashing or returning vacuous success — end-to-end test `test_utf16_bom_log_surfaces_unparseable_not_crash` in `test_server_tools.py`
- [x] AC-4: A cp1252 log with a `\x97` em-dash decodes without raising and either parses correctly or is classified unparseable depending on its content — `test_read_install_log_does_not_raise_on_cp1252_log`
- [x] AC-5: Regression tests for both byte-level cases pass — `test_install_log_lib` 41/41 green + the server-level test

## Tasks

- [x] Add `errors="replace"` to `read_text` at `install_log_lib.py:346`
- [x] Extend `is_unparseable()` to return `True` when replacement chars (U+FFFD) or NUL bytes are present and zero parseable rows were found — independent of the phase-heading/checkbox patterns
- [x] Write regression tests: UTF-16-BOM log bytes → no raise + `install_log_unparseable` diagnostic (lib + server); cp1252 `\x97` log → no raise

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| fix-read | implementer | — | errors="replace" at read_text |
| fix-is-unparseable | implementer | fix-read | Extend classification logic |
| add-tests | implementer | fix-is-unparseable | Regression tests for both byte cases |

## Serialization Points

- `fix-is-unparseable` depends on `fix-read` being in place so tests run against the corrected path.

## Affected Architecture Docs

N/A — confined to `install_log_lib.py` and its tests. No boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents crash on Windows with non-UTF-8 log |
| AC-2 | required | Ensures the 1p9bh safety net fires for the undecodable case |
| AC-3 | required | Restores the intended actionable error |
| AC-4 | important | cp1252 is less common but still a real Windows scenario |
| AC-5 | required | Regression coverage |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented: errors="replace" on read + U+FFFD/NUL branch in is_unparseable + lib & server regression tests | `test_install_log_lib` 41/41; `test_utf16_bom_log_surfaces_unparseable_not_crash` green |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Use `errors="replace"` (not `errors="ignore"`) | Replacement chars are detectable; `ignore` silently drops bytes making classification harder | errors="ignore" |

## Risks

| Risk | Mitigation |
| --- | --- |
| `errors="replace"` on a valid UTF-8 log changes nothing | Replacement only fires on invalid byte sequences; valid UTF-8 is unaffected |
| A parseable cp1252 log with one non-ASCII char triggers unparseable classification | The condition requires BOTH replacement chars AND zero parseable rows; a log with valid Phase/task rows still parses |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
