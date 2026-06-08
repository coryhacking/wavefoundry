# Secrets Redaction Short-Secret Tightening

Change ID: `1p44x-enh secrets-redaction-short-secret-tightening`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The `redact()` helper over-exposes short secret values. At `secrets_validators.py:195-198` the logic is `if len(text) <= 8: return "****"` else `return f"{text[:4]}****{text[-4:]}"`. The fixed 4+4 reveal window means a 10-character value leaks 8 of its 10 characters — only the middle 2 are masked. This matters because the `generic-api-key` rule admits secrets as short as 10 characters (`[\w.=-]{10,150}`, `scan-rules.toml:1492`), so under-redacted short values are routinely produced.

The redacted form is persisted, not just displayed: `redacted_line` is built from `redact(matched_text)` (`secrets_validators.py:545-546`), `new_entry["matched_text"] = hit["redacted_line"]` (`secrets_validators.py:610`), and `save_exceptions` writes to the in-tree, git-committed `docs/scan-findings.json` (`secrets_validators.py:257-261`, `SCAN_FINDINGS_PATH`). A weak redaction therefore lands in version control where it can be recovered from history. Tightening the reveal so short values disclose proportionally fewer characters closes this leak for all findings produced going forward.

## Requirements

1. `redact(text)` MUST scale the revealed-prefix/suffix window by input length so short values disclose proportionally fewer characters than long ones.
2. For very short values (length `<= 16`), `redact()` MUST reveal at most a 2+2 window (or fully mask), never the 4+4 window.
3. The 4+4 reveal window MUST only be used when the input length comfortably exceeds the window (length `>= 20`).
4. Across all input lengths, `redact()` MUST never expose more than approximately 40% of the input characters.
5. Redaction of long secrets MUST be unchanged aside from the 40% exposure cap (i.e. a sufficiently long value still yields a 4+4 reveal).
6. The change MUST NOT retroactively scrub redacted rows already committed to `docs/scan-findings.json` git history; this limitation MUST be documented and a re-redaction on the next full scan recommended.

## Scope

**Problem statement:** `redact()` (`secrets_validators.py:195-198`) uses a fixed 4+4 reveal window that leaks 80% of a 10-character secret. Because the `generic-api-key` rule admits 10-character values and the redacted output is persisted to the git-committed `docs/scan-findings.json`, short secrets are under-redacted in version control.

**In scope:**

- Rewriting `redact()` to length-scale the prefix/suffix reveal window.
- Enforcing a hard cap of approximately 40% exposed characters for all lengths.
- Unit tests covering representative short, boundary, and long inputs.
- Documenting the historical-committed-rows limitation and recommending a re-redaction on the next full scan.

**Out of scope:**

- Changing the `generic-api-key` minimum-length rule (`scan-rules.toml:1492`).
- Rewriting or migrating existing rows already committed to `docs/scan-findings.json` history.
- Changing the persistence flow (`redacted_line` construction, `save_exceptions`, `SCAN_FINDINGS_PATH`).
- Any change to long-secret redaction beyond applying the 40% exposure cap.

## Acceptance Criteria

- [ ] AC-1: `redact()` exposes proportionally fewer characters for short values — a 10-character input reveals at most a 2+2 window (no longer 4+4 / 8 of 10 chars).
- [ ] AC-2: For inputs of length `<= 16`, `redact()` reveals at most 2 leading and 2 trailing characters (or fully masks); the 4+4 window is only used when length `>= 20`.
- [ ] AC-3: `redact()` never exposes more than approximately 40% of the input characters for any input length.
- [ ] AC-4: Redaction of long secrets is unchanged apart from the 40% cap — a value of length `>= 20` still yields a 4+4 reveal where the cap permits.
- [ ] AC-5: Unit tests assert the redacted output for 8-, 10-, 16-, 20-, and 40-character inputs, including the proportional-exposure and 40% cap invariants.
- [ ] AC-6: The framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) passes with the new tests included.
- [ ] AC-7: The historical-committed-rows limitation is documented in this change doc and a re-redaction on the next full scan is recommended (or the residue accepted as a known limitation).

## Tasks

- [ ] Rewrite `redact()` in `secrets_validators.py:195-198` to length-scale the reveal window (length `<= 16` → at most 2+2 or full mask; length `>= 20` → up to 4+4) with a hard cap of approximately 40% exposed characters.
- [ ] Add unit tests for 8-, 10-, 16-, 20-, and 40-character inputs in `tests/test_secrets_validators.py`, asserting exact redacted output and the proportional-exposure and 40% cap invariants.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm a clean pass.
- [ ] Document the historical-committed-rows limitation and the recommended next-full-scan re-redaction in this change doc's Decision Log / Risks.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| redact-rewrite | Engineering | — | Length-scaled reveal window + 40% cap in `secrets_validators.py:195-198` |
| redact-tests | Engineering | redact-rewrite | Unit tests for 8/10/16/20/40-char inputs in `tests/test_secrets_validators.py` |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — shared with waves 1p44s, 1p44v, 1p44y, and 1p451; coordinate edits to avoid conflicting changes to the same module.

## Affected Architecture Docs

N/A — the change is confined to the `redact()` helper within a single module and its tests, with no boundary, data-flow, or verification-architecture impact.

## AC Priority


| AC | Priority | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required | Core fix: short values must stop leaking the 4+4 window. |
| AC-2 | required | Defines the length-scaled reveal behavior that closes the leak. |
| AC-3 | required | The 40% exposure cap is the central invariant of the change. |
| AC-4 | important | Guards against regressing long-secret redaction. |
| AC-5 | required | Tests pin the exact behavior across the boundary lengths. |
| AC-6 | required | Suite must stay green for the change to land. |
| AC-7 | important | Documents the known limitation so committed-history residue is understood. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Length-scale the reveal window (≤16 → ≤2+2 or full mask; ≥20 → up to 4+4) with a hard ~40% exposure cap, rather than a flat fixed window. | The fixed 4+4 window leaks 80% of a 10-char value; a proportional cap bounds exposure across all lengths while preserving long-secret behavior. | Always return `****` (loses all triage signal for long secrets); raise the `generic-api-key` minimum length (out of scope, doesn't fix the leak for admitted values). |
| 2026-06-08 | Do not retroactively scrub already-committed `docs/scan-findings.json` rows; document the limitation and recommend re-redaction on the next full scan. | Rewriting git-committed history is out of scope and risky; the fix is forward-looking and the residue is bounded and known. | Force a history rewrite (high risk, out of scope); immediately rescan and overwrite the findings file (deferred to the next full scan). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Already-committed rows in `docs/scan-findings.json` history retain the weaker redaction. | Documented as a known limitation; recommend a re-redaction on the next full scan (AC-7, Decision Log). |
| Tightening reduces triage signal for short findings. | Cap is proportional, not flat — long secrets keep the 4+4 window where the 40% cap permits, preserving signal where it is safe. |
| Edit collides with concurrent waves touching `secrets_validators.py`. | Listed as a Serialization Point with waves 1p44s/1p44v/1p44y/1p451; coordinate the merge. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
