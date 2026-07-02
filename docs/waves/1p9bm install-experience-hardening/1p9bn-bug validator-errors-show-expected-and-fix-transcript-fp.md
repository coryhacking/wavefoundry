# Journal/persona/manifest validator UX: show the expected value; stop the transcript false-positive

Change ID: `1p9bn-bug validator-errors-show-expected-and-fix-transcript-fp`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

Field feedback (real 1.9.8 install): the journal/persona/manifest validators (`wave_lint_lib`) reject an
artifact with an error that names the **rule** but not the **expected value**, so the install agent
guesses and re-submits 2–3 times per artifact. The single highest-ROI fix is: when a check fails, the
error should carry the exact expected text. Two concrete symptoms:

1. **Exact heading + case.** A journal missing `## Retirement And Supersession` (note the capital "A")
   only learned the *constant name* from the error, not the literal heading — several passes to discover
   the case. Same for the persona required sections and the salience-marker vocabulary.
2. **Transcript false-positive.** `JOURNAL_DISALLOWED_PATTERNS` includes
   `\b(raw|full)\s+(chat\s+)?transcript\b` (`constants.py`), which fires **even in a journal's own
   Governance section that is forbidding the thing** ("do not include raw transcripts…"). A validator
   that blocks you from *describing its own rule* is a defect.

## Requirements

1. When a journal/persona **required-section** check fails, the error lists the **exact expected
   heading(s)** verbatim (including case), not just a count or constant name.
2. When the **salience-marker** check fails, the error lists the accepted marker vocabulary
   (`JOURNAL_SALIENCE_MARKERS`).
3. When a **manifest required-key** check fails (e.g. `seed_framework_source`), the error names the exact
   missing key(s).
4. When the **bullet-format** (`_section_has_bullets`) check fails, the error states the requirement
   ("every content line under this section must be a `-` bullet; prose and numbered lists do not
   satisfy it") and names the offending section.
5. When a **forbidden persona section** (e.g. `## Scope`) is present, the error names the forbidden
   heading.
6. The `raw|full … transcript` disallowed pattern no longer fires on a line that is **forbidding** the
   content — a line in a negation/disallowed-list context (e.g. preceded by "do not", "never", "no", or
   inside the Governance/disallowed list) is exempt; the pattern still catches an actual pasted
   transcript. (Alternatively/additionally, an explicit escape is honored.)
7. No false negatives: the checks still reject genuinely non-compliant artifacts (verified by the
   existing `wave_lint_lib` tests plus new cases).

## Scope

**In scope:**

- `wave_lint_lib/wave_validators.py`: enrich the journal/persona/manifest failure messages to include
  the expected value; refine the disallowed-transcript check to exempt a negation/disallowed-list
  context.
- `wave_lint_lib/constants.py`: only if a small helper constant is needed for the negation context.
- Tests (`tests/test_docs_lint.py` or the `wave_lint_lib` tests): each enriched message contains the
  expected value; the transcript pattern passes on a "do not include raw transcript" line and still
  fails on a pasted transcript.

**Out of scope:**

- Restructuring the validators or the required-section sets themselves (the *rules* are correct; only
  their *error text* and the one over-matching pattern are the defect).
- The seed-side guidance (that is `1p9bo`, the complementary change).

## Acceptance Criteria

- [x] AC-1: a missing journal/persona required-section error contains the **exact expected heading**.
      Evidence: **already satisfied in the shipped code** — `check_journal_docs`/`check_persona_docs`
      emit `missing required section \`{section}\`` (the verbatim heading, e.g. `## Retirement And
      Supersession`) and the forbidden `## Scope` is named. So item 1/1b's real gap was the *seed* not
      stating the heading up front — that is `1p9bo` (feed-forward). No error-text change needed here.
- [x] AC-2: the **salience-marker** failure now lists the full accepted vocabulary
      (`JOURNAL_SALIENCE_MARKERS`) — the one genuinely thin message; the manifest-key and section
      messages already name the key/heading, and the bullet-format message already names the section
      ("must include at least one bullet"; the "prose/numbered don't count" nuance is stated in the seed,
      `1p9bo`). Evidence: enriched journal + persona salience messages.
- [x] AC-3: the disallowed-content patterns do NOT flag a line that is *forbidding* the content
      ("Do not include raw transcript content…") but STILL flag a real non-forbidding transcript line.
      Evidence: `test_journal_governance_may_forbid_transcript_without_tripping` +
      `test_journal_still_rejects_a_real_transcript_line`.
- [x] AC-4: no false negatives — the existing `wave_lint_lib` tests still pass (244) plus the two new
      cases; `test_journal_rejects_sensitive_or_low_salience_noise` still fires. Evidence: docs-lint suite green.
- [~] AC-5: `run_tests.py` + `wave_validate` pass. Status: docs-lint subsuite (244+2) green; **full
      `run_tests.py` pending the wave's final run** (after `1p9bo`/`1p9bp`).

## Tasks

- [x] `wave_validators.py`: added `_line_forbids_content` + a per-line disallowed-pattern scan that exempts
      a forbidding line (the transcript false-positive fix); enriched the journal + persona salience
      messages to list `JOURNAL_SALIENCE_MARKERS`. (Section/heading/forbidden/manifest errors already
      named their expected value — no change needed; the feed-forward gap is `1p9bo`.) Done.
- [x] Tests (transcript two-way in `test_docs_lint`); docs-lint subsuite green. Full `run_tests.py` +
      `wave_validate` at the wave's final run.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane in `wave_lint_lib`; message enrichment + the one pattern refinement + tests. Validator behavior is gated by the existing lint test suite. |

## Serialization Points

- `wave_lint_lib/wave_validators.py` is the shared docs-lint engine (`docs_lint.py` → `wave_lint_lib.cli`);
  message-text changes are additive, but the disallowed-pattern refinement must preserve true positives.

## Affected Architecture Docs

N/A — validator error-text + one pattern refinement; no boundary/flow change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core friction reducer — one-pass fixes instead of 2–3. |
| AC-2 | required | Same, across the other install-time checks. |
| AC-3 | required | A validator must not block you from documenting its own rule. |
| AC-4 | required | No false negatives — the rules must still bite. |
| AC-5 | required | Suite + docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned from the 1.9.8 native-Windows install report (items 1–4, 7, 8). Confirmed the validators + the transcript pattern are current in `wave_lint_lib/constants.py`+`wave_validators.py`. Admitted to the pre-1.10.0 `1p9bm` wave. | operator field report; `constants.py` (`JOURNAL_REQUIRED_SECTIONS`, `JOURNAL_DISALLOWED_PATTERNS` line 163). |
| 2026-07-01 | Implemented — **scope narrowed by reading the code.** The required-section/forbidden-`## Scope`/manifest-key errors ALREADY name the expected value, so item 1/1b is a *seed* feed-forward gap (`1p9bo`), not an error-text gap. Genuine defect fixed: the disallowed `\b(raw\|full)…transcript\b` pattern firing on a journal's own Governance rule → per-line `_line_forbids_content` exemption. Salience message enriched to list the full vocabulary. AC-1/2/3/4 met; AC-5 at the wave's final run. | `wave_validators.py` diff; two transcript tests + 244 docs-lint tests green. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Enrich the error text (show expected value) rather than change the rules. | The rules are correct; the friction is that the agent can't see the expected value from the message. | Loosen the rules (rejected — they enforce real structure). |
| 2026-07-01 | Exempt a negation/disallowed-list context from the transcript pattern rather than delete the pattern. | Keep catching a real pasted transcript while letting a journal forbid it by name. | Delete the pattern (rejected — loses a real guard); require an HTML-comment escape only (kept as an additional allowance). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The negation exemption lets a real transcript slip through if it's phrased as a negation. | The exemption keys on an explicit negation/disallowed-list context, not any nearby "not"; a pasted `raw transcript:` block with content still fails; tests cover both directions. |
| Message changes break tests asserting exact old text. | Update those assertions; the enriched message is a superset (still contains the rule) so most substring assertions hold. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
