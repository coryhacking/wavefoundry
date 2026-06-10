# Fix scan-rules.toml Header Comment to Reflect Actual CEL Behavior

Change ID: `1p452-doc scan-rules-cel-header-comment-fix`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The header comment in `.wavefoundry/framework/scan-rules.toml:11-13` is factually wrong and actively misleads false-positive diagnosis. It states: "betterleaks uses CEL expressions (prefilter/filter) for path and value exclusions. Our Python scanner does not execute CEL — it reads [allowlist] paths/regexes below instead."

This is contradicted by the code. `secrets_validators.py:530` runs `if cel_filter_expr and eval_filter(cel_filter_expr, secret, matched_text, rel, line_no):`, which invokes the full CEL evaluator in `cel_filter.py` (tokenizer/parser/evaluator at :104-503). Per-rule `filter` expressions ARE executed — for example the `generic-api-key` rule (scan-rules.toml:1505) and the `jwt` rule (:3782) carry `filter` blocks that the scanner evaluates.

What the scanner does NOT consume is the top-level betterleaks `prefilter`/`filter` blocks (:37-88); those are parsed by upstream betterleaks but ignored by our Python scanner, which instead relies on per-rule `filter` plus the `[allowlist]` paths/regexes.

A reviewer or engineer triaging a false positive who trusts the current comment would wrongly conclude that editing a CEL `filter` expression has no effect, or that only `[allowlist]` controls suppression. The comment must precisely capture the three-way distinction: per-rule `filter` is executed, `[allowlist]` is honored, and top-level `prefilter`/`filter` is ignored. This is a comment-only fix with no behavior change.

## Requirements

1. Rewrite the header comment at `scan-rules.toml:11-13` to state that the Python scanner DOES evaluate per-rule CEL `filter` expressions via `wave_lint_lib/cel_filter.py`.
2. Name the supported CEL subset in the comment: `entropy`, `failsTokenEfficiency`, `matchesAny`, `containsAny`, logical/comparison operators, and `attributes[?'path']`.
3. State that the scanner honors the `[allowlist]` paths/regexes.
4. State that the scanner does NOT consume the top-level `prefilter`/`filter` blocks (those remain upstream-only).
5. Make the three-way distinction explicit and unambiguous: (a) per-rule `filter` = executed, (b) `[allowlist]` = honored, (c) top-level `prefilter`/`filter` = ignored.
6. Introduce no rule, allowlist, or scanner behavior change — comment text only.

## Scope

**Problem statement:** The `scan-rules.toml` header comment (:11-13) claims the Python scanner does not execute CEL, but `secrets_validators.py:530` invokes the full CEL evaluator in `cel_filter.py` for per-rule `filter` expressions. The comment misleads false-positive diagnosis by hiding that per-rule CEL filters are live.

**In scope:**

- Rewriting the comment block at `.wavefoundry/framework/scan-rules.toml:11-13` to accurately describe CEL handling.
- Precisely distinguishing per-rule `filter` (executed), `[allowlist]` (honored), and top-level `prefilter`/`filter` (ignored).
- Naming the supported CEL subset implemented in `cel_filter.py`.

**Out of scope:**

- Any change to rules, `[allowlist]` entries, `prefilter`/`filter` blocks, or scanner logic.
- Any change to `secrets_validators.py` or `cel_filter.py` behavior.
- Adding support for the top-level `prefilter`/`filter` blocks in the Python scanner.

## Acceptance Criteria

- [x] AC-1: The header comment at `scan-rules.toml:11-13` no longer states "Our Python scanner does not execute CEL"; it states the scanner DOES evaluate per-rule CEL `filter` expressions via `wave_lint_lib/cel_filter.py`. — case (a) of the new block.
- [x] AC-2: The comment precisely distinguishes all three cases: (a) per-rule `filter` = executed, (b) `[allowlist]` = honored, (c) top-level `prefilter`/`filter` = ignored. — three lettered cases.
- [x] AC-3: The comment names the supported CEL subset: `entropy`, `failsTokenEfficiency`, `matchesAny`, `containsAny`, logical/comparison operators, and `attributes[?'path']`. — plus `jwtExpired()`/`jwtExp()` (added by 1p44w, in the same subset).
- [x] AC-4: No rule, allowlist, `prefilter`/`filter`, or scanner-behavior change is introduced; a diff of `scan-rules.toml` touches only the comment lines, and `secrets_validators.py`/`cel_filter.py` are unchanged. — THIS change's diff is the header comment only (the `[allowlist]`/rule/scanner edits belong to sibling changes 1p44t/1p44u/1p44w/1p456).
- [x] AC-5 (regression): The secrets-scan test suite (`scripts/tests/test_scan_secrets.py`, `scripts/tests/test_secrets_validators.py`) passes unchanged, confirming no behavior drift from the comment edit. — full suite green (2849).
- [x] AC-6: `docs-lint` (and `wave_validate`) report clean for this change doc. — verified at wave-end docs validation.

## Tasks

- [x] Confirm the contradiction by reading `scan-rules.toml:11-13`, `secrets_validators.py:530`, and `cel_filter.py:104-503`.
- [x] Open the framework-edit gate (`wave_gate_open(gate="framework_edit_allowed")`) before touching `scan-rules.toml`. — gate held open across the Tier-3 scan-rules edits.
- [x] Rewrite the comment block at `scan-rules.toml:11-13` per Requirements 1-5 with the precise three-way distinction.
- [x] Verify the diff touches only comment lines (no rule/allowlist/prefilter/filter changes). — this change's edit is the header block only.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` (including the secrets-scan tests) to confirm no behavior drift. — full suite green (2849).
- [x] Restore the gate (`wave_gate_close(gate="framework_edit_allowed")`). — closed at the Tier-3 boundary.
- [x] Run `docs-lint` / `wave_validate` on this change doc. — at wave-end docs validation.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| comment-rewrite | Engineering | —            | Edit `scan-rules.toml:11-13` only; coordinate via serialization point with sibling waves |
| verify          | Engineering | comment-rewrite | Confirm comment-only diff; run secrets-scan tests; docs-lint |


## Serialization Points

- `.wavefoundry/framework/scan-rules.toml` — shared with waves 1p44t, 1p44u, and 1p44w. Coordinate edits to avoid conflicting changes; this change touches only the header comment lines (:11-13), but the file must be merged carefully against sibling-wave edits.

## Affected Architecture Docs

N/A — this is a comment-only documentation fix confined to a single file's header. It changes no module boundary, control flow, data flow, or verification surface.

## AC Priority


| AC   | Priority        | Rationale |
| ---- | --------------- | --------- |
| AC-1 | required        | Core fix: the false "does not execute CEL" claim must be removed/corrected. |
| AC-2 | required        | The three-way distinction is the substance that makes false-positive diagnosis correct. |
| AC-3 | important       | Naming the supported subset prevents wrong assumptions about which CEL constructs work. |
| AC-4 | required        | Guarantees this is comment-only; any behavior change is out of scope. |
| AC-5 | required        | Regression guard: proves the edit introduced no scanner drift. |
| AC-6 | important       | Lint-clean is the gate for landing the doc and the edited TOML comment. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-08 | Fix the comment text only; do not add Python-scanner support for the top-level `prefilter`/`filter` blocks. | The blocks are upstream-only by design; the scanner relies on per-rule `filter` plus `[allowlist]`. Scope is to make the comment truthful, not to expand behavior. | Implement top-level prefilter/filter consumption (behavior change, out of scope); delete the comment entirely (loses useful CEL-handling documentation). |
| 2026-06-08 | State the precise three-way distinction (per-rule filter executed / allowlist honored / top-level prefilter+filter ignored) rather than a generic "scanner uses CEL" note. | A vague correction would still mislead triage; the value is in disambiguating which mechanism suppresses a given finding. | Keep a short "scanner does evaluate CEL" line without distinguishing the three cases. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An edit accidentally touches a rule, allowlist entry, or prefilter/filter block. | AC-4 requires a diff that touches only comment lines; verify the diff and run secrets-scan tests. |
| Merge conflict with sibling waves (1p44t/1p44u/1p44w) editing the same file. | Serialization point names the shared file; coordinate ordering and re-verify the comment-only diff after merge. |
| New/inaccurate description of the supported CEL subset. | Cross-check the subset names against `cel_filter.py` evaluator (:104-503) before finalizing the comment. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
