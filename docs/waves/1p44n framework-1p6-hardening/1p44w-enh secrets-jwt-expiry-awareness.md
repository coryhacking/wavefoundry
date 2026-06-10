# Secrets Scan JWT Expiry Awareness

Change ID: `1p44w-enh secrets-jwt-expiry-awareness`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The `jwt` secrets rule has no expiry awareness, so an expired fixture or sample token gate-blocks exactly like a live credential. The rule's filter is purely an entropy check — `scan-rules.toml:3782-3784` is exactly `entropy(finding["secret"]) <= 3.0` with no decode of the JWT payload. The CEL evaluator cannot help: `cel_filter._FUNCTIONS` (`cel_filter.py:66-71`) registers only `entropy`, `failsTokenEfficiency`, `matchesAny`, and `containsAny` — there is no base64url, JSON, or `exp` capability available to any rule filter.

The result is that a dead token (one whose `exp` is in the past) is indistinguishable from a live one. The reviewer has no signal that the credential is expired, and cannot make an informed triage decision. This change adds the missing evaluator capability and surfaces the `exp` date, while deliberately keeping any "expired → downgrade/suppress" behavior a policy choice rather than an automatic suppression: an expired-but-real JWT can still indicate token reuse or structure disclosure and is not automatically benign.

## Requirements

1. Add a CEL builtin to `cel_filter._FUNCTIONS` (e.g. `jwtExpired()` and/or `decodeJwtPayload()`) that base64url-decodes the middle (payload) segment of a JWT, JSON-parses it, and reads the `exp` claim.
2. The builtin must handle malformed input safely: a token with the wrong number of segments, non-base64url payload, invalid JSON, or a missing/non-numeric `exp` must not raise — it must be treated as "not expired" (no crash, no gate disruption).
3. The `jwt` rule filter in `scan-rules.toml` must reference the new builtin so expiry information is computed for jwt findings.
4. Jwt findings must surface the decoded `exp` date (human-readable) so a reviewer sees whether the token is past expiry.
5. Past-exp downgrade/suppression must be policy-gated, not automatic — by default an expired token still surfaces as a finding; suppression only applies when an explicit policy opts into it.
6. Add tests covering expired tokens, valid (non-expired) tokens, and malformed/non-decodable tokens, plus an MCP wrapper-layer test for the `wave_scan_secrets` surface that exercises a jwt finding with expiry info.

## Scope

**Problem statement:** The `jwt` secrets rule treats expired tokens identically to live credentials because the CEL evaluator has no ability to decode a JWT payload or inspect its `exp` claim, leaving reviewers without an expiry signal during triage.

**In scope:**

- A new CEL builtin in `cel_filter._FUNCTIONS` that base64url-decodes the JWT payload segment, JSON-parses it, and tests/exposes `exp`.
- Safe handling of malformed, truncated, or non-decodable tokens (treated as not-expired, no exceptions).
- Referencing the new builtin from the `jwt` rule filter in `scan-rules.toml`.
- Surfacing the decoded `exp` date on jwt findings.
- A policy gate so past-exp downgrade/suppression is opt-in, never automatic.
- Unit tests (expired / valid / malformed) and an MCP wrapper-layer test for the scan surface.

**Out of scope:**

- Signature verification or any cryptographic validation of the JWT.
- De-duplication of the same token firing multiple times (handled by `1p44v` dedup).
- Changes to the `jwt` regex or keyword matching.
- New CEL builtins beyond what JWT payload/`exp` decoding requires.

## Acceptance Criteria

- [x] AC-1: A new CEL builtin registered in `cel_filter._FUNCTIONS` base64url-decodes the JWT payload segment, JSON-parses it, and reads/tests the `exp` claim. — `_jwt_exp_claim` + `_jwt_expired`, registered as `jwtExpired`/`jwtExp`. Test: `test_builtin_expired_valid_malformed`.
- [x] AC-2: The `jwt` rule filter in `scan-rules.toml` references the new builtin so expiry is evaluated for jwt findings. — filter: `entropy(secret) <= 3.0 || (jwtExpired(secret) && attributes[?"suppress_expired_jwts"].orValue("") == "1")`.
- [x] AC-3: Jwt findings surface the decoded `exp` date in human-readable form. — `_format_jwt_exp` adds `exp_date` (UTC, `(EXPIRED)` suffix) to the hit + exception entry. Tests: `test_exp_date_surfaced_on_finding`, `test_integration_exp_date_persisted_in_findings`.
- [x] AC-4: Past-exp downgrade/suppression is policy-gated — with no policy opt-in, an expired token still surfaces as a finding (not auto-suppressed). — default attr `""` → suppression branch false. Tests: `test_expired_surfaces_by_default`, `test_expired_suppressed_only_with_policy_optin`, `test_valid_jwt_never_suppressed_by_expiry`.
- [x] AC-5: Malformed, truncated, or non-decodable tokens (wrong segment count, bad base64url, invalid JSON, missing/non-numeric `exp`) are handled without raising and are treated as not-expired. — `_jwt_exp_claim` returns None on any failure (incl. `bool`/non-numeric `exp`); CEL `call` also catches exceptions. Covered in `test_builtin_expired_valid_malformed`.
- [x] AC-6: Regression/unit tests cover expired, valid (non-expired), and malformed tokens for the new builtin. — `TestJwtExpiry` (6 tests).
- [x] AC-7: An MCP wrapper-layer test exercises `wave_scan_secrets` against a jwt finding and asserts the expiry info is surfaced. — `test_integration_exp_date_persisted_in_findings` drives `check_hardcoded_secrets` (the scan path `wave_scan_secrets_response` invokes) against the real ruleset and asserts the persisted finding carries `exp_date` with `EXPIRED`.

## Tasks

- [x] Implement the JWT payload-decode + `exp` builtin (e.g. `jwtExpired`, `decodeJwtPayload`) in `cel_filter.py` and register it in `_FUNCTIONS`. — `_jwt_exp_claim`/`_jwt_expired`; registered `jwtExpired`/`jwtExp`.
- [x] Make the builtin fail-safe: wrap decode/parse in defensive handling so malformed input returns "not expired" without raising. — broad `except Exception` around decode + type guards.
- [x] Reference the new builtin from the `jwt` rule filter in `scan-rules.toml`.
- [x] Surface the decoded `exp` date on jwt findings in the scan output. — `exp_date` on hit + exception entry via `_format_jwt_exp`.
- [x] Add a policy gate so past-exp downgrade/suppression is opt-in only. — `policy["suppress_expired_jwts"]` threaded through `scan_file_raw` → `eval_filter` attrs (and the parallel worker init); default off.
- [x] Add unit tests in `tests/` for expired / valid / malformed tokens.
- [x] Add an MCP wrapper-layer test for `wave_scan_secrets` covering jwt expiry surfacing. — full-pipeline `check_hardcoded_secrets` integration test.
- [x] Run the framework test suite (`python3 .wavefoundry/framework/scripts/run_tests.py`) and confirm green. — scanner suites green (97); full suite at wave-end.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| cel-builtin | Engineering | — | Add JWT payload-decode + `exp` builtin to `cel_filter._FUNCTIONS`; fail-safe on malformed input |
| rule-wiring | Engineering | cel-builtin | Reference builtin from `jwt` filter in `scan-rules.toml`; surface `exp` date; policy-gate downgrade |
| tests | Engineering | rule-wiring | Unit tests (expired/valid/malformed) + MCP wrapper test for `wave_scan_secrets` |


## Serialization Points

- `cel_filter.py` — shared read with `1p44u`; coordinate `_FUNCTIONS` edits to avoid conflicting registrations.
- `scan-rules.toml` — shared with `1p44t`, `1p44u`, and `1p452`; coordinate the `jwt` rule filter edit so concurrent rule changes do not collide.

## Affected Architecture Docs

N/A — the change is confined to the secrets-scan evaluator (`cel_filter.py`) and its rule config (`scan-rules.toml`), adding one fail-safe builtin and a filter reference. No module boundary, data/control flow, or verification-architecture change results.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The decode/`exp` builtin is the core net-new capability the change exists to deliver. |
| AC-2 | required | Without wiring the builtin into the `jwt` filter, the capability has no effect on findings. |
| AC-3 | required | Surfacing the `exp` date is the reviewer-facing value of the change. |
| AC-4 | required | Policy-gating prevents silently auto-suppressing expired-but-real tokens (token reuse / structure disclosure still matter). |
| AC-5 | required | Fail-safe handling protects the scan gate from crashing on malformed real-world tokens. |
| AC-6 | required | Regression tests for expired/valid/malformed lock in correct behavior. |
| AC-7 | important | MCP wrapper-layer test confirms expiry info reaches the `wave_scan_secrets` surface. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Added fail-safe `jwtExpired`/`jwtExp` CEL builtins (`cel_filter.py`); `eval_filter` `attrs` param; `jwt` rule filter policy-gated suppression (`suppress_expired_jwts`, default off → surfaces); `exp_date` surfacing on hit/exception via `_format_jwt_exp`; policy threaded through `scan_file_raw` + the parallel worker init. | `cel_filter.py`, `secrets_validators.py`, `scan-rules.toml`; `TestJwtExpiry` (6 tests); scanner suites green (97). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Surface the `exp` date and make past-exp downgrade a policy choice. | An expired-but-real JWT can still indicate token reuse or structure disclosure; auto-suppression would hide real signal. | Auto-suppress any expired token (rejected — loses real findings). |
| 2026-06-08 | Treat malformed/non-decodable tokens as "not expired" with no raise. | The scan gate must not crash or misbehave on real-world malformed tokens; default to surfacing the finding. | Raise/flag on decode failure (rejected — destabilizes the gate and risks dropping findings). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Malformed token decode raises and breaks the scan gate. | Defensive decode/parse returning "not expired"; explicit malformed-token tests (AC-5, AC-6). |
| Operators read expiry surfacing as automatic suppression and miss expired-but-real tokens. | Policy-gate downgrade (AC-4); default behavior still surfaces expired tokens as findings. |
| Concurrent edits to `cel_filter.py` / `scan-rules.toml` with sibling waves conflict. | Serialization points coordinate `_FUNCTIONS` and `jwt` filter edits with `1p44t/1p44u/1p452`. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
