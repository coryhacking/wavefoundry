# The Close Hard Gate Silently Passes A Missing Admitted Document

Change ID: `1v0lx-bug close-gate-silently-passes-a-missing-admitted-doc`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwh artifact-read-fail-closed

## Rationale

`1uu9z` made an **unreadable** admitted change document block close. A **missing** one still sails through, and worse than silently: executed on 2026-08-10, `_collect_silent_unchecked_items_for_close` returns `[]` for a wave whose admitted change has no file on disk, and `_generate_wf_close_wave_summary` emits an **empty-fields entry for the ghost change** — so close succeeds while producing a wave summary describing a document that does not exist. The rationale is `1uu9z` AC-4's, verbatim: the close hard gate cannot verify ACs and tasks it cannot see.

The existing lint backstop does not cover this case: the wave-owned-change-doc existence check fires only when wave `Status` is in its activated set, which `implementing` does not satisfy (verified against the real `1uwpf` record during its delivery reverification, red-team seat P3-3).

## Requirements

1. **A missing admitted document blocks close**, with a diagnostic of its own, `change_doc_missing`: the missing case is not folded into `change_doc_unreadable` (the file is absent, not broken; recovery is restoration or `wf_remove_change`, and the message says so).
2. **The close summary never describes a ghost.** `_generate_wf_close_wave_summary`'s `continue`-with-empty-fields branch is the ghost producer and does not survive as-is: for a missing admitted document the generator raises, matching the `1uu9z` precedent one branch over (the same function already raises `ValueError` for an unreadable admitted doc). The TOCTOU window then fails closed instead of fabricating an empty record. (The readiness council rejected the earlier keep-as-backstop wording as self-contradictory: kept, the branch IS the ghost whenever the window fires.)
3. **The lint existence check covers `implementing`.** Either the activated-status set gains `implementing`, or the check's gating is re-derived from the statuses that can actually hold admitted changes — whichever the census of current statuses supports. The gate is two-conjunct: `_wave_requires_wave_owned_change_docs` tests `status in {"active", "ready"}` and otherwise falls through to `_is_activated_wave` (an `Activated at:` metadata line with zero corpus instances; no framework script writes it, but seeds 170/180/190 instruct implementing agents to set it at activation, so the conjunct is workflow-live, not dead code, and survives the re-derivation). The re-derivation and the red fixture account for both conjuncts so an activation stamp cannot silently satisfy the old gate.
4. **No change for waves whose documents all exist.**

## Scope

**Problem statement:** the close hard gate fails open for an absent document, and the summary generator then fabricates an empty record of it.

**In scope:** `_collect_silent_unchecked_items_for_close` (or its caller) in `server_impl.py`; the lint existence-check gating in `wave_lint_lib`; red-first tests.

**Out of scope:** unreadable-document handling (`1uu9z`, shipped); the wave-record read crashes (`1v0lw`); any change to what a valid close writes.

## Acceptance Criteria

- [x] AC-1: Close on a wave with a missing admitted document returns `status: error` with a diagnostic naming the change id and the recovery options, reproduced **red-first** — the test must show today's silent pass first.
- [x] AC-2: `_generate_wf_close_wave_summary` called directly on a ghost fixture raises rather than emitting an empty-fields entry, red-first against today's fabrication. Exercising it only through the blocked hard gate is insufficient: no summary would be generated and the branch would ship byte-unchanged.
- [x] AC-3: The lint existence check fires for a wave at `Status: implementing`, red-first against the current gating (both conjuncts, per Requirement 3).
- [x] AC-4: A wave whose documents all exist closes identically before and after.
- [x] AC-5: The spec documents the `change_doc_missing` contract at the close boundary (`docs/specs/mcp-tool-surface.md`).
- [x] AC-6: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first reproduction of the silent pass and the ghost summary entry (the latter by direct generator call).
- [x] Block at the hard gate; make the summary generator raise on a ghost, per the `1uu9z` precedent.
- [x] Document `change_doc_missing` in the spec.
- [x] Fix the lint gating (both conjuncts); run the full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Silent pass + ghost entry, red-first |
| gate | implementer | red-tests | Hard gate blocks; summary generator raises on a ghost |
| lint | implementer | red-tests | Status-set gating |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`N/A` with rationale: this closes the sibling of the fail-open `1uu9z` already closed at the same gate; the deliberate gate-outcome change (missing doc now blocks) is disclosed here exactly as `1uu9z` disclosed its unreadable-doc change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: a verification gate that passes without its inputs. |
| AC-2 | required | A summary describing a nonexistent document is a false record at close, the worst place for one. |
| AC-3 | important | The backstop that should have caught this was gated off the live status. |
| AC-4 | required | Invisible for normal input. |
| AC-5 | important | New public diagnostic code needs spec coverage, the same omission `1uwpf`'s reverification caught for `wf_list_plans`. |
| AC-6 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings (red-team seat P3-3). Premises executed before authoring: the hard gate returns `[]` for a ghost change and the summary emits an empty-fields entry for it; the lint gating excludes `implementing` | executed probe, 2026-08-10 |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): Requirement 2's keep-the-branch wording was self-contradictory and is rewritten (the generator raises on a ghost, per the `1uu9z` precedent in the same function); AC-2 now exercises the generator directly, closing its vacuity hole; the diagnostic is named `change_doc_missing` with spec coverage added (AC-5); the lint gate's `_is_activated_wave` fallback conjunct is recorded | red-team and docs-contract seat reports, 2026-08-10 |
| 2026-08-11 | Thought: implement in two halves to serialize `server_impl.py` ownership with the delegated 1v0lw lane. Half one (now, coordinator): the lint existence-check gating in `wave_validators.py` plus its red-first fixture in `test_docs_lint.py`, both conjuncts covered per Requirement 3, with the qa lane's constraint that the end-to-end red fixture must be a lint-clean `Status: implementing` wave without an `Activated at:` stamp (an active-status ghost is already blocked by the existence check today). Half two (after 1v0lw lands): the close hard gate `change_doc_missing` block, the ghost-raise in `_generate_wf_close_wave_summary` asserting the ghost cid in the message per the sibling precedent, and the spec entry | readiness lane reports, 2026-08-11 |
| 2026-08-11 | Half one implemented (lint gating). Red executed first: a lint-clean fixture wave at `Status: implementing` with a missing admitted doc passed docs-lint rc=0 with ZERO failures against the pre-fix code (probe preserved in the new e2e test's docstring). Fix: `implementing` added to `_wave_requires_wave_owned_change_docs`'s status set; the `_is_activated_wave` fallback retained with a docstring recording why (seed-driven, not dead code). Tests: `test_implementing_wave_requires_sibling_change_docs` (end-to-end, red-first) and `WaveOwnedChangeDocGateTests.test_status_set_and_activation_fallback` (ten-case both-conjunct matrix incl. the stamp-on-terminal and not-activated edges). Both green post-fix; adjacent `test_activated_wave_requires_sibling_change_docs` and `test_base_fixture_passes` unaffected; live corpus clean with the armed gate (1uzwh itself is the first implementing wave it covers) | executed red probe rc=0 then green runs, 2026-08-11 |
| 2026-08-11 | Half two implemented. Red executed first by direct calls: the collector returned no missing entry for a ghost fixture and `_generate_wf_close_wave_summary` fabricated "delivered one change" for a nonexistent document (both observed as test failures pre-fix). Fix: the collector emits a `change document`/`missing` finding (restore-or-`wf_remove_change` text); the close response partitions doc findings by item id into `change_doc_missing` and `change_doc_unreadable` diagnostics (missing never reuses the unreadable code, asserted); the summary generator raises a `ValueError` naming the ghost cid, wave-relative, making the TOCTOU window fail closed. Tests follow the established race-test convention (garden/validate patched to simulate the lint-passed window). Spec gained the `change_doc_missing` close-gate block including the equality-vs-substring note for the pre-existing `change_doc_missing_sections` code. BulkWaveGetChangeTests 30/30 | direct-call red observations then green class run, 2026-08-11 |
| 2026-08-11 | Suite-gate disclosure: the first canonical full-suite run FAILED with six close-path test failures (`OperatorSignoffTests` x2, `WaveCloseSecretsGateTests` x3, `WaveLifecycleMutationTests` x1), all one class: pre-existing fixtures modeled waves whose referenced change docs never existed on disk, which the new gate now correctly refuses. Repair per Requirement 4's intent: the fixtures now write their admitted sibling docs (extracted with the server's own `_CHANGE_ID_PATTERN`, canonical-producer style), the gate untouched. The failures are the deliberate disclosed gate-outcome change surfacing in the suite, the same shape `1uu9z` disclosed for unreadable docs. Rerun: canonical suite rc=0, 7112 tests across 62 files, OK; docs-lint ok | suite-1uzwh.log (rc captured unpiped), 2026-08-11 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | A distinct diagnostic (`change_doc_missing`) for the missing case rather than reusing `change_doc_unreadable` | The recovery differs (restore or `wf_remove_change` vs repair the file) and an operator filtering by code should see which failure they have | Reuse the unreadable code (rejected: conflates two recoveries) |
| 2026-08-10 | The ghost summary branch raises rather than staying as a documented backstop | Readiness council: keeping the branch contradicts "the summary never describes a ghost"; the sibling unreadable case in the same function already raises, so raising is the established precedent, and it makes the TOCTOU window fail closed | Keep the empty-fields branch as TOCTOU backstop (rejected: it IS the ghost whenever the window fires) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Blocking close on a missing doc strands a wave whose change was legitimately deleted | The diagnostic names `wf_remove_change` as the sanctioned exit; removal then closes cleanly |
| The lint status-set fix over-fires on legacy waves | AC-3's red-first fixture is a live-status wave; closed/legacy statuses stay outside the set |
| `change_doc_missing` is a string prefix of the existing `change_doc_missing_sections` code | Tests and consumers match the code by equality, never substring, on serialized envelopes |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
