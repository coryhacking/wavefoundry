# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-02

wave-id: `1p9hi python3-prereq-stop`
Title: Python3 Prereq Stop

## Objective

Make the Python setup prerequisite explicit and blocking: `python3 --version` must work from the command line and report Python 3.11 or newer before Wavefoundry setup proceeds.

## Changes

Change ID: `1p9hh-bug python3-prereq-stop`
Change Status: `implemented`

Completed At: 2026-07-02

## Wave Summary

Wave `1p9hi` (Python3 Prereq Stop) delivered one change: Stop on missing or too-old python3. Notable adjustments during implementation: Stop on missing or too-old python3: Change scoped and admitted to wave `1p9hi`.

**Changes delivered:**

- **Stop on missing or too-old python3** (`1p9hh-bug python3-prereq-stop`) — 5 ACs completed. Key decisions: Keep `python3` as the committed launch command and fail setup if it is unavailable or too old.
## Journal Watchpoints

- Watchpoint: fallback wording must not imply agents can bypass the `python3` PATH prerequisite with a tool-venv MCP command.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: GUI-host PATH fallback wording could soften the hard `python3 --version` prerequisite; strongest-alternative: accept `python` on native Windows, rejected because the committed launch contract and operator direction require `python3`.)

## Review Evidence

- wave-council-readiness: approved 2026-07-02 — READY. Single bug change `1p9hh` keeps the existing generated `python3` launch contract and tightens setup failure guidance for missing or below-3.11 `python3`. Scope is localized to setup prerequisite diagnostics plus install prompt/seed text and focused regression tests. No architecture boundary change, no network or secrets impact, and no support for `python` fallback is introduced.
- wave-council-delivery: approved 2026-07-02 — PASS. Implementation removes the setup-printed/tool-venv MCP fallback path, keeps generated `command: "python3"` unchanged, and makes missing or below-3.11 `python3` fail closed with `python3 --version` repair instructions. Prompt/seed/AGENTS/native-Windows guidance now matches the behavior. Focused setup/venv tests and full framework suite passed; docs-lint clean.
- operator-signoff: approved 2026-07-02 — operator confirmed closure in-session.

## Dependencies

- No external wave dependencies.
