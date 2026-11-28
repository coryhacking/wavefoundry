# An explicit declaration can rule out the cross-platform Council trigger

Spec ID: `24jwf-enh platform-statement-council-trigger`
Spec Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-11-27
Wave: 24jwg cheaper-verification-and-council-triggers

## Rationale

`review_policy.FULL_COUNCIL_TRIGGER_TOKENS` maps the bare words `windows`, `macos` and `linux` to `cross_platform_changed`, and `review_policy.extract_full_council_triggers` searches the whole admitted spec. A spec that only states its platform behaviour, as this repository requires of every change, therefore sets `delivery_council_required` and pays for a delivery Wave Council (primer plus synthesis) even when nothing platform-specific changes. The 24i2t process review ran `extract_full_council_triggers` on that wave's spec and got only `('cross_platform_changed',)` (`.wavefoundry/work/24i2t/process-review.md`). In 24i2t the Council was justified on other grounds; in a docs-only or single-module wave it is not.

## Product Intent

A maintainer whose spec names operating systems without changing platform-specific behaviour can say so with one line, `cross_platform_changed: false`, and no longer pays for a delivery Council because of those names. A change that alters platform-specific behaviour still triggers it, through the phrases "cross-platform" and "cross platform" or an explicit `cross_platform_changed: true`, and readiness reviewers judge whether a `false` is honest. Boundaries: no other trigger changes; readiness Council is unaffected. Expected effect is honest about adoption: the readiness red-team replayed the last 60 waves and found 41 set the trigger, mostly through inline platform statements and log rows, so the saving arrives only as authors add the declaration (seed 170 tells them to).

AC-1 and AC-2 establish the outcome. After release, observe how many new waves carry `cross_platform_changed: false` and how often `delivery_council_required` drops for them.

## Requirements

1. In `extract_full_council_triggers`, an explicit `cross_platform_changed: false` (same syntax the explicit `true` already uses) suppresses only the bare OS-name tokens (`windows`, `macos`, `linux`) for that field, and only within the admitted text that declares it: `cross_platform_changed` is evaluated per element of `texts` and the result is the union, so one spec's declaration never suppresses a sibling spec's trigger. The phrases "cross-platform" and "cross platform" and an explicit `cross_platform_changed: true` still select the field; when both explicit values appear, `true` wins. Every other trigger field is matched exactly as today.
2. `small_change_lane` uses the same extraction, so it inherits the rule; this is intended and stated in the CHANGELOG. It passes the normalized review text, which includes the Progress Log, while Prepare's canonical text excludes it, so a declaration written only in a Progress Log counts for the small lane and not for Prepare; a test pins that difference.
3. The review-policy evaluator version is bumped, because the same input can now produce a different receipt. The bump's effect on readied or open waves is stated: at implementation time no other wave is readied or open, and this wave's own receipt is re-Prepared after the change.
4. Seed 170 (Plan spec) states that a spec which names operating systems without changing platform-specific behaviour may declare `cross_platform_changed: false`, that the declaration is reviewed like any other plan claim, and that a change altering platform-specific behaviour says so or declares `cross_platform_changed: true`. The rendered `docs/prompts/plan-spec.prompt.md` follows its seed if it carries that text.

## Scope

**In scope:** `review_policy.extract_full_council_triggers`, the evaluator version, their tests (including one `small_change_lane` case), seed 170 and any rendered copy, CHANGELOG.

**Out of scope:**

- Removing the OS-name tokens altogether (rejected: a genuine Windows-only change would lose its Council).
- Stripping a named platform-statement section (rejected at readiness: removes the trigger from only 2 of 41 recent waves).
- Deriving `primer_depth` in the receipt (declined at planning: seed 215 makes the tier the council-chair's declaration; the receipt field is a default, and changing it is a schema change for a small saving).
- Any other full-Council trigger.

## Acceptance Criteria

- [x] AC-1: A spec that names Windows, macOS or Linux and declares `cross_platform_changed: false` yields no `cross_platform_changed`; adding the phrase "cross-platform", or an explicit `true` alongside the `false`, yields it again; without the declaration the OS names still yield it; and two texts, one declaring `false` and one naming Windows with no declaration, still yield it. Oracle: `review_policy` unit tests, plus one `small_change_lane` test with the same spec; the first case fails today, and the two-text case fails against a corpus-level override.
- [x] AC-2: The declaration suppresses no other trigger field. Oracle: unit test with a trust-boundary phrase and the `false` declaration.
- [x] AC-3: The evaluator version is bumped and an existing receipt from the old version is reported stale rather than silently reused. Oracle: existing receipt-currency tests updated and passing.
- [x] AC-4: Seed 170 carries the Requirement 4 guidance. Oracle: seed text assertion plus docs review.
- [x] AC-5: The change's own suites and every test it adds pass, including the second profile for each touched test file; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the explicit-`false` override to `extract_full_council_triggers`, with review-policy and small-lane tests.
- [x] Bump the evaluator version and update receipt-currency tests.
- [x] Add the seed 170 guidance (under `seed_edit_allowed`) and sync any rendered copy.
- [x] CHANGELOG entry.

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`, `.wavefoundry/framework/scripts/small_change_lane.py`
- `.wavefoundry/framework/seeds/170-plan-spec.prompt.md`, `.wavefoundry/framework/seeds/007-review-system-overview.md`
- `docs/architecture/contracts/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`, `docs/contributing/review-and-evals.md`

## Affected Architecture Docs

`docs/architecture/contracts/mcp-tool-surface.md` (the evaluator version and a re-Prepare sentence), `docs/architecture/data-and-control-flow.md` (trigger extraction and the evaluator version: one sentence on the per-text override), `docs/contributing/review-and-evals.md` and seed 007 (the delivery-Council trigger list). Seed 209's repair-depth booleans are a different mechanism and do not change.

## Platform Behaviour

Pure text matching; identical on Windows, macOS, Linux and WSL2.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The outcome |
| AC-2 | required | No other trigger weakens |
| AC-3 | required | Receipt honesty after an evaluator change |
| AC-4 | important | Authors know the convention |
| AC-5 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-27 | Close preparation: the `.wavefoundry/work/24jwg/` readiness and delivery reports, delivery paths and final suite log are archived in `evidence/review-notes.tar.gz` | `evidence/review-notes.tar.gz` |
| 2026-11-27 | Gapfill: implementation edits were bulk-mechanical exact-string replacements and appends applied with short Python scripts, and code was read with targeted `sed`/`grep` over known symbols named by the readiness reports; MCP code tools were used by every review lane for claim checks. Recorded so the retrieval-posture advisory has its explanation | close dry run `retrieval_posture_gap` |
| 2026-11-27 | Final verification: three full runs launched from the shell harness were killed externally (exit 144, at files 191, 6 and 15, no summary; memory and framework code ruled out); a run launched in its own session completed. It surfaced two more evaluator-version pins, both confirmed version-only: `test_close_change.py` digest (reproduces the old value with the version line set back to 8) and the `_check_comment_evaluator_upgrade` current-version pin in `test_server_tools_lifecycle.py`; both moved to v9 with notes. The partial runs showed the guard files completing first, as AC-6 requires | `run_tests.py --no-cache`: 13673 tests, 261 files OK, receipt written |
| 2026-11-27 | Delivery lane notes repaired inline in one editorial batch after all four lanes approved (review-wave step 8): the line-of-its-own rule stated in the CHANGELOG, `mcp-tool-surface.md` and `data-and-control-flow.md` (docs-contract, architecture, code nit 4); `_schedule_order` docstring names the production `_guard_first` wrapper (architecture); `--guards --no-cache` message now asserted (code nit 1); the intended-diff half of the F1 test uses a bare `cross_platform_changed: false` so it tests F1 alone (code nit 2); a test docstring no longer claims cached timings (code nit 3). Not repaired: QA's note that 24jwf AC-3 is covered indirectly (golden digest and receipt-id change across versions; the existing upgrade path marks a different-version receipt for re-Prepare) | delivery reports in `.wavefoundry/work/24jwg/`; focused + guards 267 tests OK |
| 2026-11-27 | Delivery red-team primer repairs (before any delivery lane, one batch): F1 the small-change lane now passes the spec and the intended diff as two texts, so neither one's `false` silences the other's platform names (test `test_spec_and_intended_diff_declarations_do_not_cross`); F2 a `false` counts only on a line of its own (optional bullet or backticks), so a mention inside prose such as "do not declare ... false" no longer switches the trigger off, while `true` stays unanchored because a stray mention can only add review. F2 narrows Requirement 1's "same syntax the explicit true uses" toward the safe side; seed 170 states the line rule. Evaluator stays 9 (unreleased). F5 nit kept: the tripwire test keeps its historical name `test_evaluator_version_eight_is_the_shipped_transition_boundary`, which must never be deleted, and its docstring records v9 | `.wavefoundry/work/24jwg/delivery-red-team.md`; focused + guards 153 tests OK; second profile OK |
| 2026-11-27 | Implemented: per-text `cross_platform_changed` with the explicit-false override in `review_policy.extract_full_council_triggers`, evaluator 8 -> 9 with bump-history line, pins in `test_review_policy.py` (tripwire extended) and `test_phase_gates.py`, lifecycle golden regenerated (only evaluator version and derived digests changed) with its transition pin moved to 9; seeds 170 and 007, contract, data-and-control-flow and review-and-evals updated. Requirement 2's premise was disproved by execution: `normalized_review_text` is the same canonical body Prepare uses and also excludes the Progress Log, so there is no difference to pin; a Progress Log-only declaration counts for neither path, and the tests pin that consistent behaviour instead. Re-Prepared after reload: receipt `review-policy-d213add1300766776f3e` (v9), no spec changed | `test_review_policy.py`, `test_small_change_scope.py`, `test_phase_gates.py`, `test_lifecycle_golden.py` OK; `--profile second` OK |
| 2026-11-27 | Readiness implementation notes: per-text extraction still applies `comment_visible_text` and lowercasing to each text (code); the legacy no-receipt fallback passes the whole wave record as one text, so there the declaration is wave-wide, acceptable as compatibility-only (architecture); the CHANGELOG tells target projects that readied or open declared waves need one re-Prepare after upgrading and that the `false` declaration can drop `delivery_council_required` (architecture) | `.wavefoundry/work/24jwg/readiness-code.md`, `readiness-architecture.md` |
| 2026-11-27 | Readiness lane repairs (one batch, cycle 1): QA-RDY-1 and CODE-RDY-1 scoped the override per admitted text with a two-text AC-1 case; the small-lane Progress Log difference is stated and pinned; docs-contract's list added to Affected Architecture Docs and Serialization Points. Implementation notes: bump the evaluator from 8 to 9 with a bump-history line, extend (never delete) `test_evaluator_version_eight_is_the_shipped_transition_boundary`, update `test_phase_gates.py`'s pin, check the contract test on the `mcp-tool-surface.md` version line | `.wavefoundry/work/24jwg/readiness-code.md`, `readiness-qa.md`, `readiness-docs-contract.md` |
| 2026-11-27 | Readiness red-team primer: finding 2 (low efficacy) and finding 4 repaired by switching to the explicit-false override and adding a small-lane test, before any lane approval | `.wavefoundry/work/24jwg/readiness-red-team.md` |
| 2026-11-27 | Planned from the 24i2t process review | `.wavefoundry/work/24i2t/process-review.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-27 | An explicit `cross_platform_changed: false` overrides bare OS names | Readiness red-team replay (executed, last 60 waves): 41 set the trigger and section stripping fixes only 2, because platform statements are inline and OS names recur in log rows. The declaration covers every placement with no parser, keeps "cross-platform" and explicit `true` as triggers, and puts the honesty of the claim in front of readiness reviewers. Misses: specs whose authors never add it | Strip a `## Platform Behaviour` section (rejected: 2 of 41) | Drop OS-name tokens (rejected: loses real Windows changes); require explicit declaration only (rejected: same) |
| 2026-11-27 | Decline deriving `primer_depth` | Planner default: seed 215 assigns the tier to the council-chair; the receipt field is a default; a schema change saves little | Derive from triggers (rejected for now) |

## Risks

| Risk | Mitigation |
| --- | --- |
| An author declares `false` for a real platform change | The declaration is a plan claim readiness reviewers check; the cross-platform phrases still trigger |
| Evaluator bump re-Prepares open waves | None open at implementation; this wave re-Prepares itself |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
