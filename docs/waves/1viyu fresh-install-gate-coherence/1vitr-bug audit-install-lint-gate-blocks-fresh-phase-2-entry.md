# `wf_audit_install` runs the whole-repo docs gate before the next-row check, so a fresh Phase 2 entry can never receive `next_step`

Change ID: `1vitr-bug audit-install-lint-gate-blocks-fresh-phase-2-entry`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-17
Wave: 1viyu fresh-install-gate-coherence

## Rationale

The 2026-08-17 fresh-install field report describes `wf_audit_install` at row 2.1 dumping 60-plus `missing required Wavefoundry file` errors for artifacts rows 2.2 to 2.13 have not created yet, under an instruction ("Fix the docs-lint errors above before advancing the install log") that reads as blocking. The reporter calls it noise to relabel. It is a structural defect: `wf_audit_install_response` (`server_impl.py` line 11755) runs the full `run_validate(root)` as CHECK 1 and returns `status: lint_errors` before CHECK 2 (checked-row artifacts) and CHECK 3 (first unchecked row) ever execute. `check_required_files` (`core_validators.py` line 230) fires unconditionally for every `PROMPT_SURFACE_FILES` and `ADDITIONAL_REQUIRED_DOCS` entry, and `WAVE_REQUIRED_PATHS` (`constants.py` line 41) produce `missing required Wavefoundry generated artifact`. So a repository that has completed Phase 1 correctly cannot obtain any advancing return at all: with `phase=1` the reachable good outcome is `phase_complete` (CHECK 3 filters to Phase 1 rows, all terminal), and without `phase` it is `next_step` for row 2.1 itself, but CHECK 1 returns `lint_errors` before either. (seed-012 step 2.1, line 17, and the template's row 2.1 `expects:` describe `{status: "next_step", row: "2.2 ...", seed: "seed-030"}`, which is unreachable by construction even with clean lint; the surfaces task corrects both.) The only way to advance is to disobey the tool. That contradiction repeats at every audit until the prompt surface exists (row 2.9 in the template numbering), and it hides real lint-as-you-go findings inside a wall of expected absences.

The lint-as-you-go discipline (seed-012 line 11) is right; what is wrong is that CHECK 1 cannot tell an artifact that a later row will create from a defect in an artifact that exists. The audit already holds the information needed to tell them apart: the parsed rows and their states.

## Requirements

1. **Classify before blocking.** Add `install_log_lib.classify_lint_errors(errors, rows, project_root) -> (blocking, expected_pending)`. An error is `expected_pending` iff (i) at least one seed-driven row in the log is still pending (`[ ]`), and (ii) the error matches an entry of a single module-level tuple `INSTALL_PENDING_ERROR_MARKERS` (initially the two absence classes: `missing required Wavefoundry file`, `missing required Wavefoundry generated artifact`), and (iii) the path named before the first `: ` does not exist under `project_root`, after stripping any leading `ERROR:` prefix (one or more: `run_validate` keeps `ERROR:`-prefixed lines and some validators self-prefix, so the raw message can carry the token twice). Everything else is `blocking`. Accepted limitation, stated so it is a decision and not an oversight: rule (i) is global ("any seed row pending"), so an absence produced by an already-`[x]` row's non-row artifact (for example a `check_required_files` entry no row names) is deferred to `pending_lint` until the final gate; a `[x]` row's own artifact absence is unaffected because CHECK 2 (`checked_but_missing`) still runs whenever `blocking` is empty. Mapping every absence to its producing row is out of scope (no such mapping exists in the log). When no seed-driven row is pending, nothing is `expected_pending` (the final completeness gate keeps the "install is not finished until the docs gate passes" invariant intact).
2. **Return the next row when only expected absences remain.** Resolve and parse the install log before invoking `run_validate`: `missing_log` and `unparseable_log` take precedence, do not run lint, and carry no `pending_lint`. After a valid log is parsed, CHECK 1 blocks only on `blocking` errors. When `blocking` is empty, CHECK 2 and CHECK 3 run and the `checked_but_missing` / `next_step` / `phase_complete` / `complete` response carries `pending_lint: {count, errors (capped, with a `truncated` flag), note}` where `note` states that these are expected while Phase 2 seed rows remain pending and become blocking at the final gate. When `blocking` is non-empty, `lint_errors` returns `errors` = blocking only and the same `pending_lint` object, so the actionable list is short. This is the complete status/field matrix: only `lint_errors`, `checked_but_missing`, `next_step`, `phase_complete`, and `complete` carry `pending_lint`; `missing_log` and `unparseable_log` never do.
3. **Say it in every public carrier.** seed-012 step 2.1 and install-log template row 2.1 describe `pending_lint`, state that `lint_errors` lists only blocking findings, and correct the expected return (`phase_complete` for `wf_audit_install(phase=1)`; `next_step` for the no-argument call). `install/install-log-format.md` gains classification in its consumption list and corrects the row-format example and trustworthy-returns sentence to include `phase_complete`; its canonical `docs/references/` twin remains byte-identical. The final-tail audit semantics state `next_step(2.14)` → `next_step(2.15)` → `complete`, consuming instruction row kinds/actions owned by `1viyt`; this change does not own the template/seed row definitions. `docs/specs/mcp-tool-surface.md` gains a Tool Detail naming all seven statuses and the exact Requirement 2 matrix. The registered MCP description names the same statuses, parse-before-lint precedence, and matrix. The root README Phase 2 walkthrough distinguishes blocking lint from expected pending absences. seed-012 line 11 and template line 37 gain the qualifier "blocking lint errors", and `lint_errors.next_action` no longer refers to expected absences as blockers.
4. **Executable falsification.** Tests prove: (a) a real-validator Phase-1-complete scratch repo with pending Phase 2 rows returns `next_step` plus `pending_lint`; (b) one defect in an existing artifact returns only that defect in `lint_errors` and absences in `pending_lint`; (c) with no seed row pending every error blocks; (d) a present path and repeated `ERROR:` prefixes classify safely; (e) the existing non-absence lint test remains intentional; (f) a checked row's missing artifact still yields `checked_but_missing`; (g) an unparseable UTF-16-BOM log wins before a failing lint function, carries no `pending_lint`, and never calls `run_validate`; (h) semantic-anchor tests reach the live registered description, root README Phase 2 section, and MCP Tool Detail and mutation-check their status/matrix/blocking semantics; (i) the runtime final-tail transition test consumes the shipped 2.14/2.15 instruction rows and proves `next_step(2.14)` → `next_step(2.15)` → `complete`, while `1viyt` owns the row-kind/action parity assertions.

## Scope

**Problem statement:** The install audit blocks on absences the install itself has not reached yet, so the tool's documented `next_step` return is unreachable on a fresh Phase 2 entry and real findings drown in expected ones.

**In scope:**

- `install_log_lib.classify_lint_errors` + marker tuple, `wf_audit_install_response` control flow/fields, registered tool description, seed/template row 2.1 audit wording, final-tail runtime semantics (row definitions read-only from `1viyt`), both install-log-format twins, the MCP Tool Detail, root README Phase 2 walkthrough, tests.
- **Delivery-review scope addition (2026-08-17, CODE-DEL-1):** the Phase 1 render output must itself be lint-clean for AC-1 to hold on a faithful tree, so this change also owns: `Owner`/`Status`/`Last verified: {{generated_at}}` metadata in the five shipped `install/lifecycle-prompts/*.prompt.md` baselines that lacked it, the `{{generated_at}}` stamp in `render_agent_surfaces.reconcile_lifecycle_prompt_baselines` (mirroring `reconcile_scaffold_baselines`), metadata in the pointer-form minimum carrier text (`_initial_review_carrier_text`), and a faithful AC-1 fixture (`_build_phase_one_complete_tree`: shipped seeds + install trees, Step 0 provisioning, full `render_agent_surfaces`, template log with Phase 1 `[x]`, real `run_validate`). Also the CODE-DEL-2 fail-closed guard (a `passed=False` lint result with no `ERROR:` line synthesizes one blocking entry).

**Out of scope:**

- Changing docs-lint validators or making lint install-aware (lint has no notion of rows; the classification lives with the log).
- Mapping each absence to its producing row (unnecessary for the fix; the marker tuple plus "any seed row pending" is sufficient and falsifiable; the accepted limitation is stated in Requirement 1).
- The workflow-config and plan-template defects (changes `1vim5`, `1vitq`); after those land the fresh-repo error set shrinks, and test (a) re-derives it from the real validator.

## Acceptance Criteria

- [x] AC-1: On a Phase-1-complete scratch repo with all Phase 2 seed rows pending, `wf_audit_install()` returns `next_step` for the first pending row and `pending_lint.count > 0`, using the real `run_validate`.
- [x] AC-2: A defect in an existing artifact still returns `lint_errors`, with `errors` limited to blocking findings and absences carried in `pending_lint`; an absence whose path exists is blocking; prefix stripping is tested; a `[x]` row's own missing artifact still returns `checked_but_missing` (test f); `missing_log` / `unparseable_log` precede lint and carry no `pending_lint` (test g).
- [x] AC-3: With no seed row pending, every error is blocking and `complete` is unreachable while lint fails (final-gate invariant unchanged).
- [x] AC-4: seed/template row 2.1, both format twins, root README Phase 2, registered description, and MCP Tool Detail describe the correct statuses, exact field matrix, blocking distinction, and expected returns; test (h) mutation-checks all three newly added public carriers, test (i) pins runtime final-tail transitions using `1viyt`'s instruction rows, the marker tuple is the only absence-class authority, docs-lint is clean, and the suite is green.

## Tasks

- [x] `install_log_lib.py`: `INSTALL_PENDING_ERROR_MARKERS`, `classify_lint_errors(errors, rows, project_root)`; unit tests (c)(d).
- [x] `server_impl.py` `wf_audit_install_response`: resolve and parse the log before `run_validate`; classify after a successful parse; block only on `blocking`; attach `pending_lint` (capped list + `truncated`) only to `lint_errors`, `checked_but_missing`, `next_step`, `phase_complete`, and `complete`; reword `next_action`.
- [x] Integration tests (a)(b)(g)(i) with a real Phase-1-complete scratch tree (reuse the fixture the setup/upgrade tests already build if one exists; otherwise build the minimal tree from `install-log.template.md` + `.wavefoundry/framework/`); test (g) spies `run_validate` so lint-first precedence cannot regress, and test (i) executes all three final-tail states.
- [x] Re-evaluate `test_lint_errors_block_and_no_artifact_check` (its mocked error is not an absence class, so it should stay green; record the check).
- [x] Public surfaces under the appropriate gates: seed/template row 2.1 audit wording and blocking qualifier; both format twins including final-tail runtime semantics; root README Phase 2; registered MCP description; MCP Tool Detail; semantic-anchor test (h) for all three carriers; runtime transition test (i) consuming `1viyt`'s row definitions; full suite; `wf_validate_docs`.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| classify   | implementer | none       | Goal: marker tuple + classifier + unit tests (c)(d) |
| audit      | implementer | classify   | Goal: response control flow + `pending_lint` + integration tests (a)(b), (e) recorded |
| surfaces   | implementer | audit      | Goal: seed-012 2.1, template row 2.1, tool-surface doc |


## Serialization Points

- `.wavefoundry/framework/scripts/install_log_lib.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/install/install-log.template.md`
- `.wavefoundry/framework/install/install-log-format.md`
- `docs/references/install-log-format.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_install_log_lib.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`
- `README.md`

**Framework maintenance note.** `server_impl.py` edits follow the server-impl playbook memory (identify the seam: MCP response envelope for `wf_audit_install`; verify producer/consumer, here seed-012 and the template). Seed edit (012) requires `seed_edit_allowed`; script edits require `framework_edit_allowed`. Read-only: `wave_lint_lib/*` (consumed via `run_validate`, not edited).

## Affected Architecture Docs

`N/A` for `docs/architecture/*`; the MCP tool contract change is documented in `docs/specs/mcp-tool-surface.md` (task above).

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The reported failure, executed against the real validator; the documented `next_step` return must be reachable. |
| AC-2 | required  | Lint-as-you-go must still catch real defects, and a stale absence message must never hide a present file. |
| AC-3 | required  | The completeness invariant is what makes `complete` trustworthy; it must not weaken. |
| AC-4 | important | Surface coherence and the single-place marker tuple; enforced by lint and review, not by the mechanism. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-17 | Delivery review repair cycle (findings CODE-DEL-1/2/3, code-reviewer + qa-reviewer, both WITHHOLD): (1) on a faithful Phase-1-complete tree the real validator emitted 21 blocking `Owner/Status/Last verified` errors from renderer-materialized carriers, so `next_step`/`phase_complete` were unreachable and the shipped AC-1 test used an emptier fixture; repaired by adding metadata (with `{{generated_at}}` stamped on write) to the five lifecycle prompt baselines and the pointer-form minimum carrier, and by rebuilding the AC-1 test as a faithful tree with the real validator (`phase=1` -> `phase_complete`, no-arg -> `next_step` 2.1, `pending_lint` = 15 absence-class entries, none about metadata); (2) fail-open regression: `wf_audit_install_response` no longer consulted `lint_result["passed"]`, so a lint failure with zero `ERROR:` lines could reach `complete`; repaired with a synthesized blocking entry + `test_lint_failure_without_error_lines_fails_closed`; (3) test polarity: mutants removing the `ERROR:` prefix loop or dropping `pending_lint` from `checked_but_missing`/`phase_complete`/`complete` or adding it to `missing_log` survived; repaired with a prefixed present-path case, a seed-row-only pending case, `pending_lint` matrix assertions on the existing status tests, and test (f) `test_checked_row_missing_artifact_still_flagged_while_absences_pend`. Independent post-repair probe (`scratchpad/probe_faithful_after_repair.log`): 15 absences only, `phase_complete` / `next_step 2.1 pending 15`, three carriers now stamped. | `test_server_tools.WaveInstallAuditTests` (18 OK incl. the rebuilt real-validator test) + `test_install_log_lib.InstallPendingLintClassifierTests` (3 OK) = 21 in `scratchpad/repair-targeted-1.log`; `probe_faithful_after_repair.log` |
| 2026-08-17 | Delivery council (red-team RTD-1, low): the CODE-DEL-2 synthesized entry was routed through the classifier, so an output tail that happened to quote an absence-marker phrase while a seed row pended could be deferred (no known producer emits such a tail; hardening, not a reachable defect). Repaired in-cycle: the synthesized entry now bypasses the classifier and is prepended to `blocking`; `test_lint_failure_without_error_lines_fails_closed` gained the marker-tail case (`WARNING: docs/x.md: missing required Wavefoundry file` with a pending seed row -> `lint_errors`, pending 0). Note-only from the same seat: `pending_lint.note` says "Phase 2 seed rows" while rule (i) counts any-phase seed rows (equivalent for the shipped template, which has no Phase 1 seed rows). | `server_impl.wf_audit_install_response` (`synthesized_failure`), `test_server_tools.WaveInstallAuditTests` 18 OK + `test_install_log_lib` 51 OK (`scratchpad/repair-rtd1.log`) |
| 2026-08-17 | Thought: remove the self-reference instead of moving it. Observe: final council proved any pending audit verify row returns itself forever; Requirement 5 supersedes the earlier row-2.14 wording, promotes bootstrap removal to instruction row 2.14, keeps summary at 2.15, and observes `complete` only after both are terminal. | `DOC-FINAL-005`; `first_unchecked_row`; repeated pending-row probe |
| 2026-08-17 | Thought: verify that every install-log `expects:` value is observable before its row can be marked done. Observe: `CODE-READY-001` reproduced `next_step(2.14)` → `next_step(2.15)` → `complete`; the plan now makes row 2.14 expect the reachable row-2.15 advance and treats `complete` as the terminal postcondition after row 2.15, pinned by test (i). This supersedes the earlier readiness note that put `complete` on row 2.14. | Typed readiness finding and repair-cycle start; `wf_audit_install_response` final-tail three-state probe |
| 2026-08-17 | Thought: falsify the amended public-carrier and envelope claims, not just their ownership. Observe: `RT-READY-003` added semantic-anchor tests for the root README and live registered tool description; `DOC-READY-004` resolved the `unparseable_log` contradiction with an explicit seven-status field matrix, parse-before-lint precedence, and a failing-lint UTF-16 known-bad test. | Typed readiness findings and repair-cycle starts; existing `_tool_description` test pattern; current `wf_audit_install_response` ordering |
| 2026-08-17 | Thought: close the readiness carrier census before any framework edit. Observe: docs-contract findings `DOC-READY-001` and `DOC-READY-002` showed that the root fresh-install walkthrough and the live registered MCP description repeated the audit contract but were absent from scope. Both are now explicit Requirement 3, scope, AC-4, task, and serialization owners for implementation and independent reverification. | Typed prepare findings and repair-cycle starts in `review/evidence/events.jsonl`; `README.md` fresh-install guide; `server_impl.py` registered `wf_audit_install` description |
| 2026-08-17 | Readiness amendment from the docs-contract seat (DC-3, DC-4, DC-5, DC-11): `install-log-format.md` lines 26 and 61 and the `docs/references/` byte-identical twin added; the final-gate `complete` expectation (row 2.14, seed-012 line 178) gets the verify-row convention; `mcp-tool-surface.md` gets a real Tool Detail entry (none exists today); "blocking" qualifier at seed-012 line 11 / template line 37. | `test_shipped_reference_docs`; `first_unchecked_row` / `is_complete`; `code_keyword wf_audit_install` over `docs/specs` |
| 2026-08-17 | Readiness amendment from the red-team primer (RT-7, RT-8, RT-9, RT-13, RT-15): `ERROR:` prefix stripping in rule (iii); corrected the reachable expected returns (`phase_complete` with `phase=1`, `next_step` for row 2.1 without it) and added seed-012 line 17 / template row 2.1 / `install-log-format.md` consumption list to the surfaces task; stated the global-pending-rule limitation and added test (f) for `checked_but_missing`; named which statuses carry `pending_lint`. | `server_impl.py` CHECK 3 `phase_complete` branch; `run_validate` `ERROR:` filter; `install-log-format.md` "How wf_audit_install consumes the log" |
| 2026-08-17 | Planned from the 2026-08-17 fresh-install field report. Verified: CHECK 1 returns before CHECK 2/3 (`server_impl.py` 11755 to 11780); `check_required_files` unconditional over `PROMPT_SURFACE_FILES` + `ADDITIONAL_REQUIRED_DOCS` (`core_validators.py` 230 to 254); `WAVE_REQUIRED_PATHS` (`constants.py` 41); seed-012 line 17 documents `next_step` as the expected 2.1 return; `Row` carries `state`/`kind`/`artifact_path` (`install_log_lib.py` 133) so the classifier needs no new parsing; existing `test_lint_errors_block_and_no_artifact_check` mocks a non-absence error. | cited lines; `test_server_tools.py` `_call` mocks `run_validate` (integration test must not) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-17 | Classify lint errors against the log's pending state (marker tuple + path-absent + any seed row pending) and block only on the rest, carrying absences as `pending_lint`; final gate unchanged. | Uses information the audit already has, keeps lint-as-you-go for real defects, keeps `complete` strict, and is falsifiable with the real validator on a fresh tree. | Skip CHECK 1 at row 2.1 only (rejected: the same absences fire at 2.2 through 2.8, and real defects would go unlinted at 2.1); make docs-lint install-aware with a phase argument (rejected: couples the docs gate to the install state machine and widens the change into every validator); map each absence to its producing row (rejected: heavier, and the marker tuple + pending-row rule already separates expected from real without knowing which row will create the file); reorder CHECK 1 after CHECK 3 and never block on lint (rejected: abandons lint-as-you-go, which the field report shows is needed, since 144 errors accumulated anyway). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The marker tuple misses an absence class and a fresh repo still cannot reach `next_step`. | Test (a) runs the real validator on a Phase-1-complete tree; a new absence class fails it and forces an explicit decision to add the marker or fix the validator. |
| A real defect is misclassified as pending. | Rule (iii) requires the named path to be absent, and the marker classes are absence messages only; test (d) pins it. |
| `pending_lint` bloats the envelope. | Cap the list, carry `count` and `truncated`; the aggregate envelope-size memory (`1u1xb`) applies. |
| Agents treat `pending_lint` as ignorable forever. | The final gate blocks on everything once no seed row is pending (test c); the note says so. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
