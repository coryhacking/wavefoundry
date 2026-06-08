# Secrets Finding Dedup and Comment Context

Change ID: `1p44v-enh secrets-finding-dedup-and-comment-context`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

A single secret on a single line currently produces multiple findings, and the scanner has no awareness of comment context. In `secrets_validators.py`, `scan_file_raw` (492-558) iterates the outer loop over `compiled_rules` (519) and an inner loop over every raw line (524), appending one hit per `(rule, line)` match (547-556) with no dedup step. Because two distinct rules — `aws-secret-access-key` (`scan-rules.toml:487`) and `generic-api-key` (`scan-rules.toml:1492`) — both match the same key/secret assignment, one line yields two hits, and each becomes its own pending exception in `_match_hits_for_file` (603-619). This is the root of the "jwt fires 4x" symptom: the same secret is counted once per matching rule.

Separately, the module contains no comment-token logic anywhere, so a secret committed inside a comment is treated identically to a live assignment with no signal to triage. A commented-out real key is still a leak, so the scanner should surface the comment context as metadata for the reviewer rather than dropping or merging it silently. This change deduplicates findings to one-per-secret and records an `in_comment` flag without auto-suppressing.

## Requirements

1. When two or more compiled rules match the same secret on the same line, `scan_file_raw` must emit exactly one finding for that secret, not one per matching rule.
2. The dedup key must be collision-safe: key on `line_hash` (plus matched span) rather than `redacted_match` alone, because weak redaction can make distinct secrets redact to the same string, and merging on the redacted value would incorrectly collapse genuinely different secrets.
3. Each hit (and its resulting exception entry) must carry an `in_comment` boolean computed via lightweight per-extension leading-comment-token detection on the line.
4. The `in_comment` flag must NOT cause auto-suppression: a secret in a comment still produces a finding and still requires triage; the flag is recorded for reviewer context only.
5. Dedup must be deterministic so repeated scans of an unchanged file produce identical, stable findings (no ordering-dependent rule attribution).
6. Existing exception-matching behavior in `_match_hits_for_file` (line-drift handling, framework allowlist lookup, pending classification) must continue to work against the deduplicated hit set.

## Scope

**Problem statement:** One secret on one line produces multiple findings because `scan_file_raw` appends a hit per matching rule with no per-secret dedup, and the module has no comment-context awareness, so commented secrets carry no triage signal.

**In scope:**

- Per-secret dedup in `scan_file_raw` keyed on `line_hash` plus matched span (not `redacted_match` alone).
- A lightweight per-extension leading-comment-token detector and an `in_comment` flag recorded on each hit and propagated to the exception entry.
- Tests for a line matched by 2+ rules (one finding) and for a commented secret line (flagged, not suppressed).

**Out of scope:**

- Changing redaction strength or the redaction algorithm itself.
- Auto-suppressing or down-ranking comment findings.
- Multi-line / block-comment parsing; only leading inline-comment tokens are detected.
- Changes to rule definitions in `scan-rules.toml`.

## Acceptance Criteria

- [ ] AC-1: A single line matched by 2+ rules (e.g. `aws-secret-access-key` and `generic-api-key`) yields exactly one finding / one pending exception, not one per rule.
- [ ] AC-2: The dedup key is collision-safe — based on `line_hash` (plus matched span), so two distinct secrets that happen to redact to the same `redacted_match` are NOT merged into one finding.
- [ ] AC-3: Each hit and its resulting exception entry carries an `in_comment` boolean derived from per-extension leading-comment-token detection.
- [ ] AC-4: A secret on a comment line is still reported as a finding with `in_comment=true`; it is NOT auto-suppressed.
- [ ] AC-5: Regression/test coverage exists for (a) a double-rule line producing exactly one finding and (b) a commented secret line flagged but not suppressed; the framework test suite (`run_tests.py`) passes.
- [ ] AC-6: Repeated scans of an unchanged file produce identical deduplicated findings (deterministic rule attribution and `in_comment` flag).

## Tasks

- [ ] Read `scan_file_raw` (492-558) and `_match_hits_for_file` (561-619) to confirm the hit/exception shapes that must be preserved.
- [ ] Add a helper that maps a file extension to its leading line-comment token(s) and returns whether a given line is a comment (`in_comment`).
- [ ] In `scan_file_raw`, accumulate hits into a per-`(line_hash, matched-span)` map so multiple rule matches on the same secret collapse to one hit; preserve a stable rule_id attribution.
- [ ] Record `in_comment` on each surviving hit dict (alongside `line_hash`, `context_hash`).
- [ ] Propagate `in_comment` into the exception entry created in `_match_hits_for_file` (603-619) without changing suppression behavior.
- [ ] Add tests in `tests/test_secrets_validators.py` for the double-rule line and the commented-secret line.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix any regressions.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| dedup-core | Engineering | — | Per-secret dedup keyed on line_hash + matched span in scan_file_raw |
| comment-detect | Engineering | — | Per-extension leading-comment-token detector and in_comment flag |
| exception-propagation | Engineering | dedup-core, comment-detect | Carry in_comment into exception entry; no suppression change |
| tests | Engineering | exception-propagation | Double-rule line and commented-secret line cases |


## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — shared with waves 1p44s, 1p44w, 1p44x, 1p44y, and 1p451; coordinate edits to `scan_file_raw` and the hit/exception dict shape to avoid conflicting changes.

## Affected Architecture Docs

N/A — the change is confined to the `secrets_validators` module's scanning logic and its hit/exception dict shape; it introduces no new boundary, control/data flow, or verification surface beyond existing tests.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Core defect: one secret must yield one finding, not one per rule. |
| AC-2 | required | Collision-safe key prevents merging distinct secrets; correctness-critical. |
| AC-3 | required | The in_comment flag is the second deliverable of this change. |
| AC-4 | required | Flag-not-suppress is the chosen safety stance; a commented key is still a leak. |
| AC-5 | required | Regression and new-behavior tests guard both deliverables. |
| AC-6 | important | Deterministic findings keep scan output and triage stable across runs. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Flag comment secrets via `in_comment`, do not auto-suppress | A commented-out real key is still a committed leak; suppressing would hide real exposure. | Auto-suppress comment matches; treat comments as allowlisted. |
| 2026-06-08 | Dedup on `line_hash` (plus matched span), not `redacted_match` alone | Weak redaction can make distinct secrets redact identically; keying on redacted text would merge genuinely different secrets. | Key on `redacted_match`; key on `(rule_id, line_no)` only. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Dedup loses a rule attribution useful for triage | Preserve a stable primary rule_id per deduped finding and keep deterministic ordering. |
| Comment-token detection mis-flags non-comment lines for unknown extensions | Default to `in_comment=false` for unrecognized extensions; flag only on confident leading-token matches. |
| Shared-file edits collide with 1p44s/1p44w/1p44x/1p44y/1p451 | Coordinate via the serialization point on `secrets_validators.py` before parallel work proceeds. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
