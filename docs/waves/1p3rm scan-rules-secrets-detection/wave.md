# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-06

wave-id: `1p3rm scan-rules-secrets-detection`
Title: Scan Rules Secrets Detection

## Objective

Add an integrated secrets-detection system to the framework: a Gitleaks community rules TOML (`.wavefoundry/scan-rules.toml`) drives both a mechanical lint check in `wave_lint_lib` and a pre-scope step in the security reviewer agent. A findings file (`docs/scan-findings.json`) tracks findings through a pending → false-positive / confirmed-secret lifecycle with multi-user confirmation and wave-scoped acknowledgment. Wave close is gated on resolution: pending entries hard-block, confirmed-secret and suspected-secret entries require per-wave operator acknowledgment. The ruleset is designed to extend to PHI/PII/PCI scanning in future waves.

## Changes

Change ID: `1p3rn-enh scan-rules-engine`
Change Status: `implemented`

Change ID: `1p3ro-enh security-reviewer-scan-integration`
Change Status: `implemented`

Change ID: `1p3rp-enh wave-close-secrets-gate`
Change Status: `implemented`

Change ID: `1p3rs-enh scan-rules-committer-threshold`
Change Status: `implemented`

Completed At: 2026-06-07

## Wave Summary

Wave `1p3rm` (Scan Rules Secrets Detection) delivered 4 changes: Scan Rules Engine, Security Reviewer Scan Integration, Wave Close Secrets Gate, and Scan Rules Committer Threshold.

**Changes delivered:**

- **Scan Rules Engine** (`1p3rn-enh scan-rules-engine`) — 16 ACs completed. Key decisions: Use Gitleaks TOML schema for scan-rules.toml; Download Gitleaks community rules as the framework default base
- **Security Reviewer Scan Integration** (`1p3ro-enh security-reviewer-scan-integration`) — 12 ACs completed. Key decisions: Pre-scope placement (before explicit_non_goals); env-var-read auto-classifies as `false-positive` (no prompt)
- **Wave Close Secrets Gate** (`1p3rp-enh wave-close-secrets-gate`) — 10 ACs completed. Key decisions: pending = hard block, no override; confirmed-secret = soft block with wave-scoped persistent acknowledgment
- **Scan Rules Committer Threshold** (`1p3rs-enh scan-rules-committer-threshold`) — 7 ACs completed. Key decisions: Map 0–1→1, 2–6→2, 7+→3; 24-month time window for committer count, with all-time fallback
## Journal Watchpoints

- **watchpoint — seed edit gate:** `1p3ro` touches seed-213. `wave_gate_open(gate="seed_edit_allowed")` required before any seed edit; close immediately after.
- **watchpoint — framework edit gate:** `1p3rn` adds a new validator module and constants to `wave_lint_lib`. `wave_gate_open(gate="framework_edit_allowed")` required before edits; close immediately after.
- **blocking — sequencing:** `1p3rn` (engine) must complete before `1p3ro` (agent integration) and `1p3rp` (close gate) — both depend on `scan-exceptions.json` schema being defined. `1p3ro` and `1p3rp` can proceed in parallel after `1p3rn` completes.
- **watchpoint — schema stability:** `scan-findings.json` entry schema is the shared contract between all admitted changes. Do not alter field names after `1p3rn` is implemented without updating `1p3ro` and `1p3rp` in the same session.
- **watchpoint — TOML parsing:** The lint check must parse `.wavefoundry/scan-rules.toml` in pure Python (no subprocess, no binary dependency). `tomllib` (stdlib ≥ 3.11) or `tomli` (backport) is the only allowed dependency.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: MCP tool calls have no TTY so interactive acknowledgment was unimplementable — resolved by fail-with-instructions + agent-prompt + wave-scoped acknowledged_for_wave field in exceptions JSON; strongest-alternative: boolean wave_close parameter — rejected: leaks acknowledgment concern into tool API)
- **Design-revision Wave Council [design-revision] — 2026-06-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; trigger: significant design changes after first review — status model redesign, multi-user confirmation, UTC datetimes, lint behavior per status; strongest-challenge: phantom fields reviewed_at/reviewed_by in 1p3rp gate error template not in schema — removed; second-strongest: git diff HEAD fails on no-commits repo — fallback added; strongest-alternative: hand-craft initial ruleset — rejected in favor of downloading Gitleaks community rules)

## Review Evidence

- wave-council-readiness (round 1): approved 2026-06-06 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; depth: standard; must-fix-count: 0; recommended-count: 5 all applied in-session [RC-1 redesigned soft-block from TTY prompt to fail-with-instructions + agent-prompt + acknowledged_for_wave; RC-2 wave-touched scope defined as git diff --name-only HEAD; RC-3 short-token full redaction when ≤8 chars; RC-4 heuristic priority order specified env-var-read > real-credential > test-fixture > placeholder > ambiguous; RC-5 tomllib failure mode specified]; advisory-count: 1 [Sec-ADV-1 env-var-read or hardcoded-fallback pattern deferred]; verdict: PASS)
- wave-council-readiness (round 2): approved 2026-06-06 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; depth: standard; must-fix-count: 6 all applied in-session [RC-1 phantom schema fields reviewed_at/reviewed_by removed from 1p3rp gate error template; RC-2 AC-4 stale confirmed-safe renamed to false-positive with correct threshold semantics; RC-3 AC-13 corrected from pending to false-positive behavior; RC-4 AC-14 rationale corrected to threshold-check not auto-promotion; RC-5 1p3rp rationale corrected from ephemeral to wave-scoped persistent; RC-6 git diff HEAD no-commits fallback added to Req 4]; recommended-count: 5 all applied in-session [RC-7 Risks confirmed-safe renamed; RC-8 redundant Req 4 in 1p3ro removed; RC-9 decision log confirmed-safe renamed in 1p3ro; RC-10 Risks confirmed-safe renamed in 1p3rp; RC-11 AC numbering corrected in 1p3ro]; additional: RC-12 download Gitleaks community rules as framework base added as new task + AC-16 + decision log entry; verdict: PASS)
- wave-council-delivery: approved 2026-06-07 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; must-fix-count: 3 all applied in-session [RC-1 wave.md Objective and Journal Watchpoints scan-exceptions.json → scan-findings.json; RC-2 Wave Summary rewritten to capture full delivery scope including MCP tool, subprocess arch, ProcessPoolExecutor parallelism, rules-hash auto-escalation, scan-state.json tracking; RC-3 rules-hash auto-escalation test coverage added — 21 new tests in test_scan_secrets.py covering _compute_rules_hash, update_secrets_scan escalation, run_secrets_scan helpers, and main() escalation paths]; advisory-count: 2 [concurrent scan-state.json write between indexer and MCP paths is last-write-wins with no corruption risk; no post-install/upgrade baseline scan trigger in seeds — deferred to follow-on]; verdict: PASS)
- operator-signoff: approved 2026-06-07

## Dependencies

- No external wave dependencies.
