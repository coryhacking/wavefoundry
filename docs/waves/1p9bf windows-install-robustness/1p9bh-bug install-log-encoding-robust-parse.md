# Install-log parsing: encoding-robust rows + non-vacuous completeness (no false "install complete")

Change ID: `1p9bh-bug install-log-encoding-robust-parse`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bf windows-install-robustness`

## Rationale

Field feedback (native-Windows install of 1.9.8): the install log was created with a non-UTF-8 PowerShell
write, so its UTF-8 em dashes became Windows-1252 mojibake (`â€"` instead of `—`). Two defects then
combine into a silent failure:

1. **`install_log_lib._ROW_RE` requires a literal `—`** in two places (`—\s+(.+?)\s+` after the step
   number and `\s+—\s+(artifact|expects):` before the artifact field). With the em dashes mojibake'd, the
   regex matches **zero rows** — `parse_log` returns `[]`.
2. **`is_complete(rows)` is `all(r.is_terminal for r in rows)`**, which is **`True` for an empty list**
   (vacuous truth). So a corrupted, unparseable install log reads as **fully complete** — the install
   audit reports success on an install it could not actually verify.

This is the vacuous-truth defect class for the **third** time (cf. the 1.9.4 install-log backtick
CHECK-2). Fix all three layers: parse robustly regardless of the separator encoding, never report
"complete" from a log that parsed to zero rows, and write the log as UTF-8 in the first place.

## Requirements

1. `_ROW_RE` parses a row **regardless of the separator encoding** — anchor on the structural tokens
   (checkbox `[ x~]`, dotted step number, the `(source)` parenthetical, and the optional
   `artifact:`/`expects:` field) and tolerate **any** separator bytes between them (em dash, en dash,
   hyphen, or `â€"`-style mojibake). The captured groups the parser consumes (state, number, source,
   field-type, field-value) are preserved.
2. `is_complete(rows)` returns **`False` for an empty list** — an install log that exists but parses to
   zero rows is never "complete." (`read_install_log` returns `None` when absent, so `is_complete` is only
   reached for a log that exists.)
3. The install audit distinguishes **"no install log"** (fine) from **"install log present but
   unparseable / zero rows"** (a distinct error, e.g. `install_log_unparseable`, whose message names the
   likely encoding cause) rather than silently passing.
4. A framework-owned `write_install_log(project_root, content)` writes the log as **UTF-8**
   (`encoding="utf-8"`, `newline=""`), and the install seed guidance mandates UTF-8 for the install log
   and forbids non-UTF-8 PowerShell writes (`Get-Content`/`Set-Content`/`Out-File` without
   `-Encoding utf8`). *(Seed edit under `seed_edit_allowed`.)*
5. Full framework suite green + `wave_validate` clean.

## Scope

**Problem statement:** a non-UTF-8-written install log parses to zero rows and then reads as vacuously
"complete," so the install audit passes on an unverifiable install.

**In scope:**

- `install_log_lib.py`: encoding-robust `_ROW_RE`; `is_complete([]) → False`; a `write_install_log`
  UTF-8 writer; a parse-error signal (text present ⇒ rows expected).
- `server_impl.py`: the `wave_install_audit` / `wave_audit` advisory surfaces `install_log_unparseable`
  when the log exists but yields zero rows.
- The install seed: UTF-8 mandate for writing the install log. *(seed_edit_allowed)*
- Tests: mojibake'd + en-dash + hyphen rows still parse; `is_complete([])` is False; a present-but-empty
  parse yields the error; `write_install_log` round-trips UTF-8 em dashes.

**Out of scope:**

- The `#1`/`#4` install hangs (validation item on the 1.10.0 Windows install).
- Reworking the install-log template format (the mojibake is an encoding fault, not a format fault).

## Acceptance Criteria

- [x] AC-1: a row whose separators are em dash, en dash, hyphen, **or** `â€"` mojibake parses correctly
      (state/number/source/artifact captured). Evidence:
      `EncodingRobustParseTests.test_row_parses_across_separator_encodings` (all four forms) +
      `test_parse_log_of_mojibake_log_is_not_empty`.
- [x] AC-2: `is_complete([])` returns `False`; a fully-terminal non-empty set returns `True`; any pending
      row returns `False`. Evidence: `test_is_complete_empty_is_false`.
- [x] AC-3: the install audit reports a distinct `install_log_unparseable` error when the log exists but
      parses to zero rows (not "complete", not "no log"). Evidence: `is_unparseable` +
      `wave_install_audit_response` early error + the `wave_audit` advisory; `test_is_unparseable_flags_present_but_zero_rows`.
- [x] AC-4: `write_install_log` writes UTF-8 and round-trips em dashes; the install seed (`seed-011`)
      mandates UTF-8 and forbids non-UTF-8 PowerShell writes. Evidence:
      `test_write_install_log_roundtrips_utf8_emdash`; `seed-011` diff.
- [x] AC-5: `run_tests.py` + `wave_validate` pass; no regression to existing install-log parsing
      (38 install-log tests green incl. the existing set). Evidence: suite + docs gate.

## Tasks

- [x] `install_log_lib.py`: restructured `_ROW_RE` to be separator/encoding-agnostic (six groups
      preserved for `parse_row`); `is_complete([]) → False`; added `is_unparseable` + `write_install_log`
      (UTF-8). Done.
- [x] `server_impl.py`: `wave_install_audit_response` returns an `install_log_unparseable` error before
      CHECK 2 when a present log yields zero rows; the `wave_audit` advisory adds the same. Done.
- [x] Install seed `seed-011` (under `seed_edit_allowed`): UTF-8 write mandate for the install log;
      forbids bare non-UTF-8 PowerShell writes. Done.
- [x] Tests (`EncodingRobustParseTests` 5: separator forms, mojibake-parses, `is_complete` arms,
      unparseable, writer round-trip); `run_tests.py` + `wave_validate` pending final run. Done.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Ordered: `install_log_lib` parser/completeness/writer, then the `server_impl` audit error, then the seed UTF-8 mandate, then tests. `install_log_lib` is the shared parse contract — full suite gates it. |

## Serialization Points

- `install_log_lib._ROW_RE` / `is_complete` are the shared parse contract read by `server_impl`'s
  install-audit and `wave_audit` advisory; the group indices the parser consumes must stay stable across
  the regex restructure.

## Affected Architecture Docs

N/A — a parser-robustness + encoding fix; no boundary/flow change. (`docs/references/install-log-format.md`
documents the format; reconcile if the separator wording implies a required em dash.)

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — parse must not depend on em-dash fidelity. |
| AC-2 | required | The vacuous-truth guard — an empty parse is never "complete." |
| AC-3 | required | The operator must see "unparseable," not a false "complete." |
| AC-4 | important | UTF-8 write prevents the corruption at the source. |
| AC-5 | required | No regression; docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned from 1.9.8 native-Windows field feedback: PowerShell non-UTF-8 write mojibake'd the install-log em dashes → `_ROW_RE` matched zero rows → `is_complete([])` vacuously `True` → false "install complete." Confirmed both defects in code. Admitted to the pre-1.10.0 `1p9bf` wave. | operator field report; `install_log_lib._ROW_RE` (literal `—`) + `is_complete` (`all()` over empty). |
| 2026-07-01 | Implemented. `_ROW_RE` separator-agnostic (opaque `\S+` token, six groups preserved); `is_complete([])→False`; `is_unparseable` + UTF-8 `write_install_log`; `wave_install_audit`/`wave_audit` emit `install_log_unparseable`; `seed-011` UTF-8 mandate. Notably, with the robust parser a mojibake'd log now PARSES (better than erroring); `is_unparseable` is the safety net for corruption the parser still can't recover. AC-1..5 met. | `EncodingRobustParseTests` (5) + 38 install-log tests green; `seed-011` diff. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Make `_ROW_RE` separator/encoding-agnostic (anchor on structural tokens) rather than adding the `â€"` mojibake to a dash class. | Robust to any mis-encoding, not just the one observed; keys off the tokens that actually matter (state/number/source). | Add `â€"` to a dash alternation (rejected — fragile, only fixes one mojibake form). |
| 2026-07-01 | `is_complete([]) → False`; a present-but-zero-rows log is a distinct audit error. | Empty-list vacuous truth is the root of the false "complete"; the operator needs to see "unparseable," not silence. | Guard only at each call site (rejected — the vacuous default recurs at the next call site). |
| 2026-07-01 | Fix the write side too (UTF-8 writer + seed mandate), not just the parser. | Prevents the corruption at the source across every host; the robust parser is the safety net. | Parser-only (rejected — leaves the log itself corrupted and human-unreadable). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Loosening `_ROW_RE` over-matches non-row lines. | Anchor on the checkbox + dotted number + `(source)` parenthetical + line start/end; tests assert phase headings and prose lines are NOT matched. |
| Regex group-index shift breaks `parse_log`'s consumers. | Preserve the exact groups the parser reads; the full existing install-log test set gates the restructure. |
| `is_complete([]) → False` breaks a legitimate empty-log path. | `is_complete` is only reached when a log exists (`read_install_log` returns `None` when absent); an existing zero-row log is genuinely not complete. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
