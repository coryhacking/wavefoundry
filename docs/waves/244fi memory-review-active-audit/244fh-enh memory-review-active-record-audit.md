# Memory review audits a bounded batch of active records

Change ID: `244fh-enh memory-review-active-record-audit`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-22
Wave: 244fi memory-review-active-audit

## Rationale

The memory review workflow (seed 240, `Review memories`) can shrink the corpus only through records that are already pending or retired. It validates pending candidates, applies at most one consolidation group, and archives or purges stale, superseded or rejected records. Step 1 says to "follow cited evidence and current targets", but no step acts on what that reveals about an active record.

On 2026-11-22 this repository held 175 active records against a budget of 50 and no retired records. `memory_brief(context="review")` reported `curation_required: true` and `remaining: 0`. The defined review therefore cannot retire active knowledge that is no longer operational, even though `memory_reconcile` can already move an active record to `stale`, or to `superseded` with a successor. The operator decided on 2026-11-22 to fix the gap in the framework first and then run the review here.

## Product Intent

A maintainer who runs `Review memories` gets a bounded audit of active records in each run. Before this change, active records leave the live corpus only through consolidation. After it, each run judges a small, ordered batch against the current tree and retires the records whose knowledge is encoded elsewhere, whose target is gone, or which duplicate canonical guidance. Each outcome carries a stated reason. The budget stays a curation signal, never a deletion quota, and age alone never retires a record. AC-6 tests the intent: a walk of the new step on this repository's corpus must select a bounded batch and yield at least one justified retirement.

## Requirements

1. Seed 240 must add an active-record audit step to the apply procedure. The step runs after candidate routing and before consolidation, so that consolidation and the retired-record step see its results.
2. Queryless `memory_search` must accept `order="least_recently_reviewed"`. It sorts the selected records by `updated_at` ascending (the record's `Updated:` date, so the record reviewed or changed longest ago comes first), then by `effective_confidence` ascending, then by `memory_id`. The sort applies before the existing cap of 20 (`MEMORY_SEARCH_CAP`). A call that combines this order with a non-empty `query` must return a validation error. A call without `order` must keep today's ordering.
3. The audit batch is one uniform list of 15 records of every kind, taken from `memory_search(status="active", order="least_recently_reviewed", limit=15)`. The seed passes `status="active"` because the default statuses also include candidates. There is no separate fragile-file pass, no churn-based selection and no skip window. Fifteen fits within the cap of 20, so no offset is needed.
4. A keep is recorded with `memory_reconcile(memory_id=..., status="active")`. The tool accepts this same-status call today: `reconcile_memory_record` rewrites the `Updated:` line to the run date and leaves the body, `Created:` and decay unchanged. The stamp moves the record to the back of the order, so consecutive runs advance through the corpus: 175 active records are covered in about 12 runs. The seed must say that a keep stamp means "reviewed, unchanged", not a content change. A test must pin the same-status behavior.
5. For each record in the batch, the reviewer must record one outcome and a reason that names current evidence:
   1. **keep:** the record still changes a future action, or the reviewer cannot name the evidence that another outcome requires. Stamp it as Requirement 4 describes.
   2. **retire to stale, encoded elsewhere:** the reviewer names the specific assertion (a test, check or code path) that would fail on a regression of the lesson, and that assertion covers the lesson's whole scope, not only the instance the record came from. Use `memory_reconcile(memory_id=..., status="stale")`. If no such assertion can be named, the outcome is keep or rewrite.
   3. **retire to stale, target gone or duplicate of canonical guidance:** the reviewer names the missing target path, or the canonical document and section that carries the same action.
   4. **supersede:** another active record already carries the knowledge at equal or wider scope. Use `memory_reconcile(memory_id=..., status="superseded", superseded_by=...)`.
   5. **rewrite:** the knowledge is still operational but the record is wrong or outdated. Create the successor with `memory_add(..., status="active", supersedes=<original id>)`, then supersede the original with `memory_reconcile(memory_id=<original id>, status="superseded", superseded_by=<successor id>)`. `memory_add` writes only a `Supersedes:` line; it does not change the original's status. `memory_validate` rewrites only pending candidates and must not be used for active records.
   6. **unresolved:** the reviewer cannot settle the judgment. Leave the record unchanged and report it.
6. Records the audit retires in a run must be archived in that run with `memory_reconcile(memory_id=..., status="archived", retain_for_history=true, archive_reason=..., eligibility_confirmed=...)`, never purged. A later review may purge them after a second look. The seed's retired-record step must say it covers both earlier retired records and records the audit retired in this run, and that only the earlier ones may be purged.
7. Protected kinds (`decision`, `operator_preference`, `fragile_file`) follow the rule the seed already states. The invocation authorizes eligible mutations, and no per-record operator confirmation is added. A protected record retires only when the current review proves its knowledge is no longer operational. The reviewer supplies `eligibility_confirmed=true` at archive only after that review. The report lists each protected retirement separately.
8. The seed must keep every existing safety boundary. No record retires on age or decay alone; the order selects a record for review and never decides its outcome. The batch size is not a deletion quota.
9. The read-only procedure must include the audit as a walk that lists the batch with `memory_search` and reports proposed outcomes. Its forbidden-tool sentence names `memory_reconcile`, `memory_add` and docs mutations without call parentheses, because the contract test counts each `name(` token in that section as a call.
10. The report must add audited, kept, retired, superseded, rewritten and unresolved counts, and list each retired or superseded record with its reason.
11. The installed template `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md` and this repository's `docs/prompts/memory-review.prompt.md` must carry the same audit step as the seed.

## Scope

**Problem statement:** The memory review has no step that judges active records against the current tree, so an over-budget corpus with no retired records cannot shrink.

**In scope:**

- Seed `.wavefoundry/framework/seeds/240-memory-review.prompt.md`: the audit step, outcomes, archive-only rule for audit retirements, step-5 wording, read-only walk and report fields.
- Template `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`: the same edits. The renderer materializes `docs/prompts/memory-review.prompt.md` from this template only when the file is missing, so a target with an existing copy receives the change through the upgrade drift report (overwrite when the local copy matches the previous template, otherwise a hand merge).
- This repository's `docs/prompts/memory-review.prompt.md`: a hand merge, because the renderer preserves an existing copy.
- The `order="least_recently_reviewed"` parameter on `memory_search` (`wf_server/server_impl.py`, `wf_server/memory_handlers.py`). No other tool option and no new view field: the order reads the existing `updated_at` and `effective_confidence` values, and the keep stamp uses the existing same-status `memory_reconcile` call.
- Tool reference `docs/specs/mcp-tool-surface.md` for the new parameter and the same-status keep stamp on `memory_reconcile`.
- Test pins: new literals in `assert_memory_review_contract`, applied to the template, seed 240 and `docs/prompts/memory-review.prompt.md`, with known-bad controls, in `tests/test_render_agent_surfaces.py`; ordering, validation and same-status reconcile tests in `tests/test_memory_records.py`; the `memory_search` entry in `tests/fixtures/register-surface-handler-digests.json`.
- A `CHANGELOG.md` `[Unreleased]` entry.

**Out of scope:**

- Running the memory review on this repository. The operator runs it after this change closes.
- A tool guard for active-to-stale transitions of protected kinds. `memory_reconcile` does not guard that transition today; the seed's review rule governs it.
- Changes to decay formulas, the budget value or briefing inclusion.
- The `wf-memory-review` skill files under `.claude/skills/`, `.codex/skills/` and `.agents/skills/`: they are thin pointers to the prompt.

## Acceptance Criteria

AC-6 tests whether the intent was established; the other ACs check the implementation.

- [x] AC-1: Seed 240 contains the audit step with the call of Requirement 3, the outcomes of Requirement 5 including the whole-scope assertion rule, the archive-only rule of Requirement 6, and the sentence that the order selects a record and never decides its outcome. A contract test applied to seed 240 fails when any of these literals is removed.
- [x] AC-2: The installed template, seed 240 and `docs/prompts/memory-review.prompt.md` each pass `assert_memory_review_contract`, extended with the new literals, in a test that reads each file. Every existing literal still passes, including the two whose line wrapping the test pins.
- [x] AC-3: On a fixture corpus whose expected order is written as literals in the test, `memory_search(status="active", order="least_recently_reviewed")` returns records by `updated_at` ascending, then `effective_confidence` ascending, then `memory_id`. The fixture mixes kinds, including a `decision` and a flagged `fragile_file` with no decay. With the ordering removed, the test fails.
- [x] AC-4: Known-bad orders fail the AC-3 fixture.
   1. A confidence-first order fails: the fixture holds an old-`updated_at` record at base confidence 0.95 that must come first, and a newer record at 0.6 that a confidence-first order would list first.
   2. A skip-then-cap order fails: after the test stamps the first record's `Updated:` line with a same-status reconcile, that record must move to the end and the next record must come first. An order that keeps sorting by confidence and filters recent records after the cap does not produce this list.
   3. `memory_search(query="x", order="least_recently_reviewed")` returns a validation error, and a call without `order` returns the same list as before this change.
- [x] AC-5: On a fixture active record dated earlier, `memory_reconcile(memory_id=..., status="active")` returns `updated: true`, sets `updated_at` to the run date, and leaves `status`, `created_at`, `effective_confidence` and the record body unchanged. A known-bad control that drops the `Updated:` rewrite fails the test.
- [x] AC-6: A read-only walk of the new step on this repository's corpus, using the shipped `memory_search(status="active", order="least_recently_reviewed", limit=15)`, selects 15 records and yields at least one retirement candidate (stale or superseded) with a reason that meets Requirement 5. The walk mutates nothing: `git status --porcelain docs/agents/memory` is identical before and after.
   1. The walk records batch size, outcome counts and each candidate with its reason in the Progress Log.
- [x] AC-7: The report section of the seed names audited, kept, retired, superseded, rewritten and unresolved counts and a per-record list of retirements with reasons.
- [x] AC-8: The read-only procedure lists the audit walk and still forbids `memory_reconcile`, `memory_add` and docs mutations; the existing read-only call-token check passes.
- [x] AC-9: `python3 .wavefoundry/framework/scripts/run_tests.py` passes, and `wf_validate_docs` reports no errors.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed`.
- [x] Add the audit step, outcomes, archive-only rule, step-5 wording, read-only walk and report fields to seed 240.
- [x] Apply the same edits to the installed template, keeping the template's existing differences from the seed (it has no "Capture during ordinary wave close" section).
- [x] Hand-merge the edits into `docs/prompts/memory-review.prompt.md`.
- [x] Add `order="least_recently_reviewed"` to `memory_search` and `memory_search_response`, sorting before the cap, with the validation error for `query`.
- [x] Refresh the `memory_search` digest in `tests/fixtures/register-surface-handler-digests.json`.
- [x] Extend `assert_memory_review_contract`, apply it to seed 240 and the docs copy, and add known-bad controls.
- [x] Add ordering, known-bad, validation and same-status reconcile tests to `tests/test_memory_records.py`.
- [x] Update `docs/specs/mcp-tool-surface.md` for the new parameter and the same-status keep stamp.
- [x] Run the read-only walk for AC-6 with the shipped tool and record it in the Progress Log.
- [x] Add a `CHANGELOG.md` `[Unreleased]` entry.
- [x] Close both gates, then run `run_tests.py` last and `wf_validate_docs`.

## Agent Execution Graph

The tool change and the prompt edits can run in parallel. Both must finish before the AC-6 walk, and the walk must finish before the final test run.

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| tool-order | implementer | none | `memory_search` order, keep-stamp test, digest |
| prompt-audit | implementer | none | seed, template, docs prompt, contract test |
| walk | implementer | tool-order, prompt-audit | AC-6 read-only walk |
| verify | implementer | walk | `run_tests.py`, `wf_validate_docs` |

## Serialization Points

- `.wavefoundry/framework/seeds/240-memory-review.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/memory-review.prompt.md`
- `docs/prompts/memory-review.prompt.md`
- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. The change adds one ordering option to an existing read tool and one step to an existing prompt. No module boundary, data flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The seed is the source of truth for the step. |
| AC-2 | required | Installed and self-hosted copies must carry the step. |
| AC-3 | required | The batch depends on the least-recently-reviewed order. |
| AC-4 | required | The two rejected orders must fail, and the default ordering must not change. |
| AC-5 | required | Rotation depends on the keep stamp. |
| AC-6 | required | Tests whether the step shrinks the corpus with justified outcomes. |
| AC-7 | required | The operator reads the outcome counts and reasons. |
| AC-8 | important | Keeps the read-only boundary intact. |
| AC-9 | required | Suite and docs gate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-22 | Planning walk, read-only, under the first design (10 weakest plus 5 flagged fragile). Superseded by the readiness repair below. | Proposed then: retire `1tax0`, `1ti6d`, `1tdvh`; rewrite `1u8q1`. Under the whole-scope assertion rule of Requirement 5, each of those three encodings covers only the original instance, so they would be kept or rewritten. |
| 2026-11-22 | Readiness repair, cycle 1, for `244fi-cr-fragile-order`, `244fi-qa-fragile-pass-ordering`, `DOCS-RDY-1`, `244fi-cr-skip-vs-cap` and `244fi-qa-skip-window-stall`. Redid the read-only walk with the least-recently-reviewed order, simulated in a scratch script over the existing ranking function with `updated_at` from each record's `Updated:` line; AC-6 repeats it with the shipped tool. No memory file changed (`git status --porcelain docs/agents/memory` identical before and after). | Batch of 15: 12 dated 2026-07-18 and 3 dated 2026-07-19; 7 `successful_pattern`, 4 `failed_attempt`, 2 `environment_gotcha`, 2 `dependency_gotcha`. Proposed outcomes: 1 supersede, 14 keep, 0 stale. Supersede `1sxln` (mid-file `unittest.main` hides later tests, targets `test_build_pack.py`) by `1t018` (the same rule for every test module run by the canonical runner). No retire-as-encoded: no test asserts `unittest.main` placement suite-wide, and no other batch record had a whole-scope assertion. Simulated rotation: a second run after keeping all 15 overlaps the first in 0 records. Known-bad probes on the live corpus: a confidence-first fragile sort lists 3 unflagged 0.6 records among the first five, and weakest-plus-skip with the 20 cap leaves 10, 10, 0 and 0 eligible records over four runs. |
| 2026-11-22 | Focused readiness round 2: code-reviewer, qa-reviewer and docs-contract-reviewer reverified all five findings (terminal) and approved on receipt `review-policy-e1de797da926301811f4`. Correction for implementation, found independently by qa-reviewer and docs-contract-reviewer: Requirement 5.5 is wrong that `memory_add(supersedes=...)` leaves the original's status unchanged. It already supersedes the original (`memory_handlers.py` lines 751 to 753), so a rewrite is one `memory_add` call and the extra `memory_reconcile(status="superseded")` is redundant. The implementer follows the code. Docs-contract advisory: the seed's purge boundary bullet names that audit-retired records are archived in the same run. | `.wavefoundry/work/244fi/review/*-focused-r2.md` |
| 2026-11-22 | Implementation. `memory_search` gains `order="least_recently_reviewed"` (sort before the cap; `query` with an order, or an unknown order, returns `invalid_arguments`). Seed 240, the install template and `docs/prompts/memory-review.prompt.md` gain the audit step (new step 3), the archive-only rule in the purge boundary bullet and step 6, the read-only audit walk and the report counts. Deviation from Requirement 5.5, following the code: `memory_add(supersedes=...)` already marks the original superseded (`wf_server/memory_handlers.py`, pinned by `test_add_with_supersedes_marks_old_record`), so the seed's rewrite is one `memory_add` call, with `memory_reconcile(status="superseded")` only as recovery when `memory_add` reports `supersedes_target_not_updated`. Scope discovery: the keep stamp removed the blank line after `Updated:` (`_UPDATED_LINE_RE` ended in `\s*$`, which consumed the next newline), which would break AC-5's unchanged-body rule and 25 live records' heading spacing; the regex in `memory_records.py` now matches only the date with a lookahead that also accepts a CRLF ending. Not changed: `reconcile_memory_record` reads text with newline translation, so a CRLF record is rewritten with LF endings (pre-existing). | Focused runs: `test_memory_records.py` 242 OK; `test_render_agent_surfaces.py` 228 OK; `test_mcp_tool_registry.py` 27 OK after the `memory_search` digest refresh; `test_handler_modules.py` OK; `test_tool_surface_golden.py` OK after regenerating `fixtures/tool-surface-golden.json` and `fixtures/tool-surface-golden/declared.json` with `WF_UPDATE_TOOL_SURFACE_GOLDEN=1`. |
| 2026-11-22 | AC-6 walk, read-only, through the shipped handler `memory_search_response(status="active", order="least_recently_reviewed", limit=15)` in process (the connected MCP client's cached schema does not yet expose `order`). Batch of 15, matching the planning walk: 12 dated 2026-07-18, 3 dated 2026-07-19. Proposed outcomes: 1 supersede, 14 keep. `memory_search(query="x", order=...)` returned `invalid_arguments`. | Supersede `1sxln-mem mid-file-unittest-main-hides-later-tests` by `1t018-mem place-unittest-main-at-eof-in-per-file-test-modules`: `1t018` states the same rule for every test module run by the canonical runner, a wider scope than `1sxln`'s single file. `git status --porcelain docs/agents/memory` identical before and after. |
| 2026-11-22 | Gapfill: retrieval for this implementation was mostly shell (`grep`, `sed`, small read-only Python probes) with MCP `memory_search`, `wf_review_event` and `wf_validate_docs`; the edited files were already known from the readiness notes. | Factual record only. |
| 2026-11-22 | The coordinator's full suite failed `test_server_package.RetiredFlatNameCensusTests.test_no_module_outside_the_package_uses_a_retired_flat_name`: a new test in `test_memory_records.py` (`test_default_order_is_unchanged`) used `from wf_server import memory_handlers`. Fixed to `import wf_server.memory_handlers as memory_handlers`, matching sibling tests. `test_server_package.py` and `test_memory_records.py` pass through `run_tests.py --file`. | Coordinator `run_tests.py --file` output |
| 2026-11-22 | Delivery repair, cycle 2. `244fi-docs-changelog-updated-regex-scope`: the CHANGELOG bullet now says memory validation, status changes and archives no longer remove the blank line after `Updated:`, because `_UPDATED_LINE_RE` serves all three (`memory_records.py` lines 1099, 1147 and 1420). `244fi-cr-sort-before-cap-unpinned`: added `test_sort_runs_before_the_cap` (`limit=2`, expects `mem-old-decision`, `mem-tie-weak`). | `test_memory_records.py`: 243 OK. On a scratchpad copy with `ranked = ranked[:n]` inserted before the sort, `test_sort_runs_before_the_cap` fails and the other five order tests pass. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-22 | Fix the gap in the framework, then run the review here. | Operator decision, 2026-11-22. | Run an ad hoc review without a framework step. |
| 2026-11-22 | Add one ordering option to queryless `memory_search` and audit a bounded batch. | Planner default. Queryless `memory_search` orders best-first with a cap of 20 and no offset, so most of the 175 active records cannot be reached for review today. | A new `memory_audit` tool: weakness is a new mechanism where one ordering parameter suffices. |
| 2026-11-22 | Order by least recently reviewed (`updated_at` ascending, then `effective_confidence` ascending, then `memory_id`) and audit one uniform batch of 15 of every kind. This replaces `order="weakest"`. | Coordinator decision, 2026-11-22 (reversible), adopting the red-team primer's strongest alternative after readiness findings `244fi-cr-fragile-order`, `244fi-qa-fragile-pass-ordering` and `DOCS-RDY-1`. `fragile_file`, `decision` and `operator_preference` never decay, so a confidence-first order misranks them, and churn has no field of its own. Ordering by review date covers every kind, including obsolete decisions and records whose target was deleted (which read churn 0). | Weakest-first plus a fragile-by-churn pass: declined, because the planning probe showed it lists unflagged 0.6 records and needs a churn field that does not exist. |
| 2026-11-22 | Decline the 30-day skip window. A keep re-stamps `Updated:` through the existing same-status `memory_reconcile(status="active")`, which rotates the record to the back. | Coordinator decision, 2026-11-22 (reversible), after `244fi-cr-skip-vs-cap` and `244fi-qa-skip-window-stall`. A caller-side skip applied after the 20-row cap stalls: the simulation reached 0 eligible records on run 3. Rotation by review date needs no skip and works at any run spacing. Verified in code: `wf_garden_docs` takes no paths and never stamps an unchanged record; `reconcile_memory_record` rewrites `Updated:` on a same-status call. | A tool-side `updated_before` filter or an offset: declined, because the rotation removes the need for both. |
| 2026-11-22 | Retire as "encoded elsewhere" only when the reviewer names an assertion that would fail on a regression and covers the lesson's whole scope; otherwise keep. | Coordinator decision, 2026-11-22, from the red-team primer's Front 1: a test at the original site does not stop the same mistake at a new site. | Accept any named test in the area: declined, because it retires lessons that still apply elsewhere. |
| 2026-11-22 | Archive, not purge, every record the audit retires in the same run; a later review may purge it. | Coordinator decision, 2026-11-22, removing the path from active to purged in one run on one judgment. | Purge in the same run: declined. |
| 2026-11-22 | No per-record operator confirmation for protected retirements. | Planner default, consistent with seed 240: the invocation authorizes eligible mutations, and protected kinds need `eligibility_confirmed=true` only after current review. | Ask the operator per protected record (weakness: contradicts the seed's existing authorization model). |

## Risks

| Risk | Mitigation |
| --- | --- |
| The rotation relies on same-status `memory_reconcile`, which no test pins today; a later guard that refuses same-status calls would stop it. | AC-5 pins the behavior with a known-bad control. |
| `Updated:` changes meaning from "last content change" to "last reviewed or changed". | The seed states that a keep stamp means reviewed and unchanged. |
| The audit concentrates on old records, so a recent but wrong record waits up to about 12 runs. | Reversible default; the coordinator accepted it in exchange for covering every kind. |
| `memory_reconcile` does not guard an active-to-stale transition for protected kinds. | The seed requires current review for any protected retirement and the report lists each one. A tool guard is out of scope. |
| A target repository with an edited `docs/prompts/memory-review.prompt.md` does not receive the step automatically. | The upgrade drift report already says to hand-merge when the local copy differs from the previous template. |
| A reviewer could treat the batch as a quota. | Requirement 8 and the existing budget boundary state that the order only selects. |

Platforms: Windows, macOS, Linux and WSL2 behave the same; the change is prompt text plus an in-process sort over existing record fields, with no paths, processes or shell use.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
