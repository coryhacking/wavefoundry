# Scope generic-api-key Docs/Markdown Prose With A Path Clause

Change ID: `1p44u-enh generic-api-key-docs-path-scope`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The `generic-api-key` rule (`.wavefoundry/framework/scan-rules.toml:1490`) uses a deliberately broad regex (`:1492`): a trigger word (`access|auth|api|key|secret|token|…`) followed by a delimiter and a `[\w.=-]{10,150}` (or base64-ish) run. In documentation and markdown prose this over-matches — ordinary architecture sentences that contain a trigger word, a colon/comma, and a long enough alphanumeric phrase are flagged as secrets, producing false positives in `docs/` and `.md` files.

The rule's filter block (`:1505-2971`) already AND-combines path scoping with content signal for one ecosystem: the BitBake clause at `:2961-2970` matches `attributes[?"path"]` against `\.bb$`/`\.bbappend$`/`\.bbclass$`/`\.inc$` and then requires a BitBake-specific line shape before suppressing. There is currently **no** equivalent `docs/`/`.md` clause, and the global `[allowlist].paths` (`:98`) has no `.md`/`docs` entry, so docs prose is scanned with the full broad regex and no prose carve-out.

The evaluator already supports exactly the construct we need: `attributes["path"]` is populated in `cel_filter.py:500`, and `matchesAny` (registered `:46-55`/`:69`), `orValue` (`:449-451`), and the optional-index `[?` form (`:350-356`/`:432-439`) are all implemented. So this is a pure rule-data change — no evaluator code change is required.

We choose a **surgical per-rule filter clause** AND-combined with a prose/low-signal test (mirroring the BitBake pattern) rather than adding `.md`/`docs` to the global `[allowlist].paths`. A blanket docs allowlist would suppress every finding in docs and lose recall on a genuine high-entropy secret pasted into a markdown file; the AND-combined clause suppresses only prose-like matches while still catching real secrets.

## Requirements

1. Add a new filter clause to the `generic-api-key` rule that is AND-combined: a path test matching markdown/docs files against `attributes[?"path"].orValue("")`, and a content/line-signal test that only fires for prose-like (low-signal) matches.
2. The path test MUST use the supported `matchesAny(attributes[?"path"].orValue(""), [...])` form, matching `.md`/`.markdown` extensions and/or a `docs/` path segment.
3. The clause MUST NOT blanket-suppress all docs findings: a genuine high-entropy/high-signal secret string in a `.md` file must still fire (recall preserved). Suppression applies only when the matched line/secret looks like prose.
4. Do not modify the global `[allowlist].paths`; keep the carve-out local to the `generic-api-key` rule.
5. Make no changes to `cel_filter.py`; rely on its existing `attributes[?'path']`, `matchesAny`, `orValue`, and optional-index support.
6. Optionally extend the same docs-prose clause to peer high-recall rules if they exhibit the same over-match, without weakening their recall.

## Scope

**Problem statement:** The broad `generic-api-key` regex produces false positives on documentation/markdown prose because the rule's filter has no `docs/`/`.md` path-scoped prose carve-out, and the global allowlist does not cover docs either.

**In scope:**

- A new AND-combined path + content-signal filter clause appended to the `generic-api-key` rule in `.wavefoundry/framework/scan-rules.toml`.
- Tests for both the prose-suppression case and the real-secret-still-caught (recall) case.
- Optional extension of the clause to peer high-recall rules where the same prose over-match is demonstrated.

**Out of scope:**

- Any change to the `cel_filter.py` evaluator (it already supports the needed constructs).
- Adding `.md`/`docs` to the global `[allowlist].paths`.
- Tightening the base `generic-api-key` regex itself.
- Re-tuning unrelated rules' entropy/token-efficiency thresholds.

## Acceptance Criteria

- [ ] AC-1: A representative architecture/prose sentence in a `.md` file that previously triggered `generic-api-key` (trigger word + delimiter + long alphanumeric phrase) no longer produces a finding.
- [ ] AC-2: A planted REAL high-entropy API key value placed in a `.md` file STILL produces a `generic-api-key` finding (recall preserved; suppression is not blanket).
- [ ] AC-3: The new clause uses the supported `matchesAny(attributes[?"path"].orValue(""), [...])` path form and is AND-combined (`&&`) with a content/line-signal test, consistent with the BitBake clause at `scan-rules.toml:2961-2970`.
- [ ] AC-4: The global `[allowlist].paths` and `cel_filter.py` are unchanged by this change.
- [ ] AC-5 (regression/test): Automated tests cover both the prose-suppression case (AC-1) and the real-secret-still-caught case (AC-2), and the existing secrets-scan and validator test suites continue to pass.
- [ ] AC-6 (MCP wrapper-layer): `wave_scan_secrets` invoked over the MCP surface against a fixture markdown file reflects the same outcomes as the library tests (prose suppressed, real key still reported), confirming the rule change flows through the MCP wrapper.

## Tasks

- [ ] Reproduce the false positive: build a fixture `.md` line (trigger word + delimiter + long prose phrase) and confirm `generic-api-key` currently fires via the secrets scanner.
- [ ] Author the new filter clause for `generic-api-key`: `matchesAny(attributes[?"path"].orValue(""), [docs/.md patterns]) && <prose/low-signal line test>`, appended to the filter block ending at `scan-rules.toml:2971`.
- [ ] Define the prose/low-signal line test so a genuine high-entropy secret on the same docs path is not suppressed (lean on entropy/word-shape signals rather than path alone).
- [ ] Add a prose-suppression test (AC-1) and a real-secret-recall test (AC-2) to the secrets-scan/validator test suites.
- [ ] Add or extend an MCP wrapper-layer test (AC-6) exercising `wave_scan_secrets` against markdown fixtures.
- [ ] Evaluate peer high-recall rules for the same over-match; extend the clause only where it does not erode recall.
- [ ] Run the framework test suite and the secrets-scan tests; confirm green and no unintended suppression elsewhere.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rule-clause | Engineering | — | Append docs-prose path+signal clause to `generic-api-key` filter in `scan-rules.toml` |
| tests | Engineering | rule-clause | Prose-suppression + real-secret-recall library tests |
| mcp-test | Engineering | rule-clause | `wave_scan_secrets` wrapper-layer fixture test |
| peer-rules | Engineering | rule-clause | Optional extension to peer high-recall rules |

## Serialization Points

- `.wavefoundry/framework/scan-rules.toml` — shared with waves 1p44t / 1p44w / 1p452; coordinate edits to avoid clobbering concurrent rule changes.
- `.wavefoundry/framework/scripts/wave_lint_lib/cel_filter.py` — shared read-only dependency with 1p44w; this change must NOT modify it, only rely on its existing path-clause support.

## Affected Architecture Docs

N/A — this is a localized rule-data change to a single `generic-api-key` filter clause plus tests; it does not alter module boundaries, data/control flow, or the verification architecture. The evaluator contract and MCP tool surface are unchanged.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The core defect — prose false positives must stop firing. |
| AC-2 | required | Recall guarantee; without it the fix degrades to a harmful blanket suppression. |
| AC-3 | required | Constrains the implementation to the supported, evaluator-compatible path form. |
| AC-4 | required | Guards the chosen approach (per-rule, not global allowlist; no evaluator change). |
| AC-5 | required | Regression coverage for both directions of behavior. |
| AC-6 | important | Confirms the rule change surfaces correctly through the MCP wrapper layer. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Use a per-rule AND-combined path + content-signal filter clause on `generic-api-key`. | Suppresses prose-like docs matches while preserving recall on real secrets pasted into docs. | Add `.md`/`docs` to global `[allowlist].paths` — rejected: blanket docs suppression loses recall on genuine secrets in docs. |
| 2026-06-08 | Implement as rule-data only, with no `cel_filter.py` change. | Evaluator already supports `attributes[?'path']`, `matchesAny`, `orValue`, and optional-index (`cel_filter.py:46-55`, `:350-356`, `:449-451`, `:500`); the BitBake clause (`:2961-2970`) is the proven pattern. | Add a new evaluator helper — rejected: unnecessary, widens blast radius and shared-file coupling. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Clause is too broad and suppresses a real secret in docs. | AND-combine path with a low-signal/entropy prose test; AC-2 recall test plants a real high-entropy key in `.md` and requires it to still fire. |
| Concurrent edits to `scan-rules.toml` by sibling waves cause conflicts. | Treat `scan-rules.toml` as a serialization point; coordinate with 1p44t/1p44w/1p452 and append the clause adjacent to the existing path-clause block. |
| Prose carve-out logic diverges from peer rules. | Optionally reuse the same clause shape on peer high-recall rules; keep the line-signal test centralized in pattern. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
