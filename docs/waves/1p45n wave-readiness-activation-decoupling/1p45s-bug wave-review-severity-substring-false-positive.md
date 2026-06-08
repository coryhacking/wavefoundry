# `wave_review` Severity Detection Substring-Matches Inside Larger Words (False High-Severity)

Change ID: `1p45s-bug wave-review-severity-substring-false-positive`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-06-08
Wave: 1p45n wave-readiness-activation-decoupling

## Rationale

`_max_severity_from_evidence` (`server_impl.py:7622-7635`) scans `## Review Evidence` signoff lines and ranks severity by **substring** containment: `for sev in _SEVERITY_ORDER: if sev in line and line.index(sev) > 0`, where `_SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]` (`:7619`). Because it is a bare substring test, ordinary review prose triggers false severity findings:

- `"high"` matches inside `highest`, `highlight`, `highly` → false **high** severity.
- `"low"` matches inside `flow`, `below`, `allow`, `lower`, `slow`, `follow` → false **low**.
- `"critical"` matches inside `criticality` → false **critical**.

This was hit live during the `1p458` delivery review: a `wave-council-delivery` evidence line containing "highest-salience surface" produced a `high_severity_finding` from `wave_review`, which surfaces as a close-time advisory ("prioritise operator review of these before closing"). The wording had to be changed to clear a phantom finding. The matcher should detect severity words as **whole tokens**, not substrings.

## Requirements

1. Severity detection in `_max_severity_from_evidence` recognizes a severity level only when it appears as a **whole word/token** (word-boundary delimited), not as a substring of a larger word.
2. Ordinary prose containing a severity word as a substring — `highest`, `highlight`, `flow`, `below`, `allow`, `lower`, `follow`, `criticality` — yields no elevated severity (returns `none` absent any genuine standalone severity word).
3. A genuine standalone severity annotation in an evidence line (e.g. `severity: high`, `… — high …`, `[critical]`) still ranks correctly to the highest present level.
4. The existing `line.index(sev) > 0` quirk (which silently ignores a severity word at the very start of a line) is reconciled by the word-boundary approach so position no longer changes the result incorrectly.

## Scope

**Problem statement:** `_max_severity_from_evidence` substring-matches severity words, so normal review prose (e.g. "highest-salience") registers false high/critical findings in `wave_review`.

**In scope:**

- `server_impl.py` `_max_severity_from_evidence` (`:7622-7635`): replace the substring containment test with whole-word/token matching (e.g. a `\b(none|low|medium|high|critical)\b` regex over each lowercased evidence line, or equivalent tokenization), preserving the highest-rank-wins behavior.
- Tests (`test_server_tools.py`): false-positive words return `none`; genuine standalone severity words rank correctly; highest-of-several wins.

**Out of scope:**

- Introducing a structured `severity:` evidence-field schema (a larger contract change) — whole-word matching is the minimal correct fix.
- The behavior of `wave_review`'s other gates (council/lane/operator signoffs).

## Acceptance Criteria

- [x] AC-1: A `## Review Evidence` line containing only substring matches (`highest`, `highlight`, `flow`, `below`, `allow`, `lower`, `criticality`) and no standalone severity word yields `max_severity == "none"`.
- [x] AC-2: A line with a standalone severity word (e.g. `severity: high`) yields the correct rank (`high`), and the highest level wins when several appear.
- [x] AC-3: Severity detection is position-independent — a standalone severity word ranks the same whether or not it starts the line (the old `index(sev) > 0` quirk is gone).
- [x] AC-4: Tests in `test_server_tools.py` cover the false-positive words and the true positives; `python3 .wavefoundry/framework/scripts/run_tests.py` is green.

## Tasks

- [x] `server_impl.py` `_max_severity_from_evidence`: switch to whole-word/token severity matching (word-boundary regex), keep highest-rank-wins, drop the `index(sev) > 0` substring guard.
- [x] Add `test_server_tools.py` cases: false-positive words → `none`; standalone words → correct rank; multi-level → highest; position-independence.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| severity-word-match | software-engineer | — | Whole-word matching in `_max_severity_from_evidence`. |
| tests | qa-reviewer | severity-word-match | False-positive + true-positive coverage. |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py` — shared with `1p45l` (`wave_prepare`/`wave_implement`). Different function (`_max_severity_from_evidence`); coordinate edits to avoid clobbering.

## Affected Architecture Docs

N/A — a localized correctness fix to one helper; no module boundary, data-flow, or contract change (it does not alter the evidence-line format, only how severity words are detected within it).

## AC Priority

_Confirmed at Prepare wave 1p45n (2026-06-08) — classifications interrogated by the readiness council._


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The defect — substring false positives must stop. |
| AC-2 | required   | Genuine severity words must still be detected. |
| AC-3 | important  | Removes the position-dependent quirk. |
| AC-4 | required   | Regression coverage + green suite. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Replaced the substring severity match in `_max_severity_from_evidence` with whole-word matching (`_SEVERITY_WORD_RE`), so `highest`/`flow`/`below`/`allow`/`lower`/`criticality` no longer false-trigger; dropped the position quirk. | `run_tests.py` green (2789); new false-positive + standalone-word + unit tests pass. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Fix via whole-word/token matching of severity levels rather than introducing a structured `severity:` evidence field. | Minimal, correct fix that preserves the existing freeform-evidence format and highest-rank-wins behavior; no contract change. | A structured `severity:` schema (larger change, churns every signoff line); deny-list specific words like "highest" (brittle). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Word-boundary regex misses a legitimately-formatted severity annotation. | AC-2 covers common standalone forms; keep matching case-insensitive over the lowercased line. |
| Edit collides with `1p45l` in `server_impl.py`. | Serialization point; different function; sequence and re-verify. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
