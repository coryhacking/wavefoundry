# Close One Change And Activate Its Dependents

Change ID: `1zlu2-enh close-one-change-and-activate-dependents`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-02
Wave: 1zlu1 lifecycle-features-for-distributions

## Rationale

A downstream distribution (Waveforge) runs waves whose changes finish at different times and depend on one another through `Depends On:` lines. Today there is no tool to mark one change finished: the only lifecycle write that touches change status is wave-level (`wf_close_wave` closes the whole wave; `wf_implement_wave` moves the wave, not its changes). Operators edit `Change Status:` by hand in two places (the change doc header and the wave record block), get the `Previous Change Status` transition wrong or forget one side (which `wf_current_wave` then reports as status drift), and then hand-advance each dependent change. Docs-lint already encodes the rules (`ALLOWED_CHANGE_STATUS_TRANSITIONS`, and the check in `check_wave_docs` that a change in a progressable status has every dependency in `TERMINAL_CHANGE_STATUSES`), so a tool can apply them instead of the operator.

The operator decided (2026-10-02): a new tool `wf_close_change(wave_id, change_id, mode)` with `dry_run` and `create`, under the lifecycle lock; it writes `complete` for one change and moves each newly unblocked dependent to `ready`; no per-change review evidence and no ledger event; reopening a completed change is out of scope.

Brief: consumers are operators and distributions running multi-change waves; success is that finishing one change is one validated call that leaves the change doc, the wave record and docs-lint consistent, and reports which dependents became ready.

## Product Intent

One change can be closed inside an open wave without closing the wave, and the dependency graph advances itself. The wave-level close (`wf_close_wave`) stays the only way to close a wave and keeps all of its gates. Spec: `docs/specs/mcp-tool-surface.md`.

## Requirements

1. **Tool surface.** New MCP tool `wf_close_change(wave_id: str, change_id: str, mode: str = "dry_run")`. Modes: `dry_run` (read-only, reports what `create` would write and what would fail) and `create` (alias `apply`, as `wf_close_wave` accepts). Any other mode returns `invalid_arguments` with `valid_modes`. Extra arguments are refused through `_ensure_no_extra_args`, as on every lifecycle tool. `wave_id` accepts a unique prefix, resolved like `wf_close_wave`; `change_id` must be the full admitted change id (as `wf_mark_ac` requires).
2. **Registration.** The tool joins `_LIFECYCLE_MUTATION_LOCK_TOOLS`, takes `project_state_publication_lock` in `create` (as `wf_close_wave` does), is `TIER_WRITE` in `mcp_tool_roster.py`, is registered as a `PublicationWriter` (`"lifecycle"`, `"fail_fast"`) in `publication_control.py`, and is dispositioned in every other name-keyed tool registry. The census predicate for "every other registry": every literal occurrence of `wf_close_wave` or `wf_mark_ac` in `.wavefoundry/framework/scripts/` (tests excluded), not only module-level collections, so function-level name checks are covered too (for example the `if tool_name == "wf_close_wave"` branch near line 16424 of `wf_server/server_impl.py`). A keyword search on 2026-10-02 found `wf_close_wave` in `wf_server/server_impl.py`, `wf_server/edit_gate_handlers.py`, `context_efficiency.py`, `render_agent_surfaces.py`, `render_platform_surfaces.py`, `mcp_tool_roster.py`, `publication_control.py`, `wave_lint_lib/cli.py` and `wave_lint_lib/secrets_validators.py`; the census is re-run at implementation and each hit gets an entry or a recorded reason for none. The tool-surface golden (`tests/fixtures/tool-surface-golden.json`), the handler digests (`tests/fixtures/register-surface-handler-digests.json`), the `AGENTS.md` **Available tools** list (pinned by `test_agents_available_tools_census_matches_registration`), the label census in `tests/test_label_reader_census.py` (for each new label reader or writer) and `docs/specs/mcp-tool-surface.md` are updated.
3. **Gate.** `create` writes only when all hold, and `dry_run` reports every one that fails (all, not the first), each as its own diagnostic:
   - the wave record is found and readable (existing unreadable-record refusal);
   - the wave is open: its `Status:` is `active` or `implementing` (the OPEN statuses used by `_find_other_active_wave`);
   - the change is admitted: its id appears as a `Change ID:` block under the wave record's `## Changes` (the profile's `MEMBER_HEADING`);
   - the change doc exists and is readable at the wave-folder path;
   - the change's current status in the wave record is closable: in `PROGRESSABLE_CHANGE_STATUSES` or `implemented`, not in `TERMINAL_CHANGE_STATUSES`, with `complete` in `ALLOWED_CHANGE_STATUS_TRANSITIONS[current]`. Operator decision 2026-10-02: `implemented` is closable (a change is closed only when it is closed, and `implemented` is the repository's usual pre-close status), so the lint constants gain `implemented` as a recognized status with the transition `implemented` -> `complete` (`implemented` stays non-terminal, but it satisfies dependencies through `DONE_CHANGE_STATUSES` from `1zlu0`). The closable set is derived from the lint constants at call time, never hardcoded;
   - the change doc's status agrees with the wave record (otherwise the existing drift is reported and nothing is written);
   - the per-change checkbox gate passes: the findings of `lifecycle_gate_support._collect_silent_unchecked_items_for_close`, filtered to this `change_id`, are empty (silent `[ ]` ACs at non-exempt priority, silent `[ ]` tasks, missing or unreadable doc, missing `## Acceptance Criteria`/`## Tasks` sections all block, with the same item text close uses);
   - every dependency of the change (its wave-record `Depends On:` targets) is in `DONE_CHANGE_STATUSES` (terminal or `implemented`); this repeats docs-lint's dependency rule as changed by `1zlu0` rather than inventing one. A target that is not admitted to this wave counts as not done.
4. **Write.** On `create`, in one operation under both locks:
   - the change doc header: `Change Status:` and `Status:` become `complete` (labels from the vocabulary profile: `MEMBER_STATUS_LABEL`; `Status` is a fixed key). No `Previous Change Status` line is written into the change doc.
   - the wave record block for the change: `Change Status` becomes `complete` and `Previous Change Status` (the profile's `PREVIOUS_STATUS_LABEL`) is set to the prior status, replacing an existing previous line, in the order the existing block regex expects (`Change ID`, optional previous line, status). Status values are never translated by the profile; only labels are.
   - Writes go through the existing atomic writers (`_atomic_replace_text`), and the background index refresh is requested for the written paths.
   - On a successful `create`, the repo cache is invalidated (`cache.invalidate()`), as `wf_create_wave_response` does.
5. **Activate dependents.** Activation candidates are ONLY the other changes in the same wave record whose wave-record `Depends On:` line names the closed change id. A change with no `Depends On:` line, or whose line does not name the closed change, is never a candidate and is never written, even when its dependencies are all done. Dependencies are read with one existing parser, `wave_validators._parse_change_records` (the docs-lint work-record parser, which applies `DEPENDS_ON_LINE_PATTERN` from `wave_lint_lib/constants.py`); no new regex is written. A `Depends On:` target that is not admitted to this wave counts as not done. In the same operation, each candidate whose wave-record `Depends On:` targets are now all in `DONE_CHANGE_STATUSES` (terminal or `implemented`, from `1zlu0`), and whose current status is `planned` or `blocked`, moves to `ready` in both its change doc header and its wave record block, with `Previous Change Status` set in the wave record block only. A dependent is never moved to `active`. A change whose dependencies are declared only in its own change doc (legacy lines) is not activated, and is reported as `dependencies_not_in_wave_record` (advisory). Activated and skipped dependents are reported in `data.activated` and `data.not_activated` (each with id, prior status and reason).
6. **Lint after the write.** Before writing, the tool checks the new statuses in memory against the same constants docs-lint uses (transition table, terminal set, the dependency rule) and refuses on any violation. Before writing, it also records a lint baseline: docs-lint scoped to the documents it will write. After writing, it runs the same scoped lint and diffs against the baseline; only a failure that names a written document and is absent from the baseline (a failure the write introduced) restores every written file's prior bytes and returns `status: "error"` with `close_change_lint_failed` and the new lint lines. Pre-existing failures never trigger rollback. `dry_run` runs the in-memory checks, reports what would fail, and reports pre-existing lint failures on the documents it would write as advisory. The post-write lint runs while `project_state_publication_lock` is held: docs-lint takes no lock of its own (no lock use found in `docs_lint.py` or `wave_lint_lib/` on 2026-10-02), which the implementer confirms before relying on it, so it cannot deadlock under the publication lock.
7. **No review effects.** No ledger event is appended, no review evidence is required, and the review-policy receipt does not move: `canonical_review_policy_body` normalizes `Change Status:` and `Status:` lines in a change doc's leading metadata (`normalize_review_tracking_status`), and the wave record is not part of the digest. The `Previous Change Status` line is kept out of the change doc for this reason (it is a carrier key but is not normalized, so writing it there would move the digest and lapse approvals).
8. **Wave close is unchanged for completed changes.** `wf_close_wave` treats an already `complete` change as finished and does not rewrite it.
9. **Response.** `data` carries `wave_id`, `change_id`, `mode`, `previous_status`, `status` (`complete` on success), `written` (repo-relative paths), `activated`, `not_activated`, and the lint result attached as on `wf_create_wave`. Refusals use stable diagnostic codes with recovery tools (`wf_current_wave`, `wf_get_change`, `wf_mark_ac`/`wf_mark_task` for open checklist items).
10. **Docs.** The tool docstring, `docs/specs/mcp-tool-surface.md` (new entry beside `wf_mark_ac`), the `AGENTS.md` tool list, and a CHANGELOG `### Added` bullet. `docs/prompts/implement-wave.prompt.md` gains one sentence naming the tool for finishing a change mid-wave. That prompt has shipped sources, so distributions see the tool only when they are edited too: the packaged template `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md` (behind `framework_edit_allowed`), the implement-wave rule in seed `100` (near line 98, the `**implement-wave**:` bullet) and the matching implement-wave wording in seed `180-implement-feature.prompt.md` (both behind `seed_edit_allowed`). The seeds and the template are edited first, then the project-local prompt. (The earlier note that no seed carries this text was wrong; corrected at readiness.)

## Scope

**Problem statement:** finishing one change and advancing its dependents is a manual, two-file, error-prone status edit.

**In scope:**

- The `wf_close_change` tool, its gate, writes, dependent activation, lint rollback and registration.
- Tests in a new `tests/test_close_change.py` (or the lifecycle test module) covering every gate, the writes in both files, activation, rollback, the lock, the receipt staying current and a non-default vocabulary profile.
- The lint constants in `wave_lint_lib/constants.py` (`implemented` and its transition, if `1zlu0` has not already added them) and the transition-table test near line 2015 of `tests/test_docs_lint.py`, checked for the widened table.
- Golden fixtures, `AGENTS.md`, the spec, the implement-wave prompt sentence (project-local prompt, packaged template, seeds `100` and `180`) and the CHANGELOG.
- Architecture docs `docs/architecture/current-state.md` and `docs/architecture/data-and-control-flow.md`.

**Out of scope:**

- Reopening a completed change (operator decision; `complete` has no outgoing transition in lint).
- Closing a change in a wave that is not open, or across waves; cross-wave dependencies are not declared in this framework.
- Per-change review evidence, signoffs or ledger events.
- Changing the close-wave status gate (that is `1zlu0` in wave `1zls7`).
- Moving a dependent to `active`.

## Acceptance Criteria

- [x] AC-1: In an `active` wave, `wf_close_change(create)` on a `ready`, an `active` and a `review` change (one fixture each) writes `complete` to the change doc's `Change Status:` and `Status:` and to the wave record block with `Previous Change Status` equal to the prior status; docs-lint passes on the result; `dry_run` on the same fixture writes nothing and reports the same planned writes.
- [x] AC-2: Each gate in Requirement 3 refuses with its own diagnostic and no write: wave not open (`planned`, `closed`), change not admitted, change doc missing, status not closable (`planned`, `blocked`, `complete`, an unknown token; an `implemented` change is closable and closes to `complete` with `Previous Change Status: implemented` passing lint), status drift between the two files, a silent `[ ]` AC or task in this change, and a non-terminal dependency; a silent `[ ]` item in a different change of the same wave does not block. `dry_run` lists every failing gate at once.
- [x] AC-3: In a wave where B and C depend on A, D depends on A and E, and E is `planned`: closing A moves B (`planned`) and C (`blocked`) to `ready` in both files with the previous status recorded in the wave record, leaves D unchanged and reports it in `not_activated`, never writes `active`, and reports B and C in `activated`; with E `implemented` instead of `planned`, D is activated too. Two non-candidates stay byte-for-byte unchanged in both files and are absent from `activated`: F, a `planned` change with no `Depends On:` line, and G, a `planned` change whose only dependency is a different change that was already `complete` before A closed.
- [x] AC-4: When a write would leave docs-lint failing on a written document (forced in a test by a fixture lint cannot accept after the write), every written file is restored byte for byte and the response is `close_change_lint_failed`; a lint failure already present on a written document before the write does not trigger rollback, and `dry_run` reports it as pre-existing.
- [x] AC-5: The review-policy digest of the wave is identical before and after a successful `create` (computed with the existing policy snapshot), and no line is appended to `events.jsonl`; a test that also writes `Previous Change Status` into the change doc shows the digest moving, proving the exclusion is load-bearing.
- [x] AC-6: The tool is refused with the lifecycle busy response while another holder has the lifecycle lock, is decorated with `@_fail_closed_on_record_layout("wf_close_change")` (as `wf_close_wave` is), and appears in `_LIFECYCLE_MUTATION_LOCK_TOOLS`, the roster as `TIER_WRITE`, `PUBLICATION_WRITER_REGISTRY`, the tool-surface golden, the handler digests and the `AGENTS.md` list, and in the hand-listed tool tables of `tests/test_archive_root.py` (`ArchiveWriterRefusalTests`), the wrapper lists in `tests/test_record_layout_lifecycle.py` and `tests/test_lifecycle_mutation_lock.py`; the registry census of Requirement 2 is recorded in the Progress Log.
- [x] AC-7: Under a non-default vocabulary profile (the test profile helper), the tool reads and writes the profile's labels and writes the same status values.
- [x] AC-8: The spec entry, the `AGENTS.md` list, the implement-wave prompt sentence (project-local prompt, packaged template `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`, seeds `100` and `180`), `docs/architecture/current-state.md`, `docs/architecture/data-and-control-flow.md` and the CHANGELOG describe the tool.
- [x] AC-9: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Run the Requirement 2 registry census and record it.
- [x] Write failing tests for AC-1 through AC-7.
- [x] Implement the response function (gate, in-memory checks, writes, activation, post-write lint and rollback).
- [x] Register the tool (lock set, publication lock, record-layout fail-closed decorator, roster, publication writer, other registries per census, the hand-listed test tables named in AC-6).
- [x] Update `wave_lint_lib/constants.py` if `1zlu0` has not already added `implemented`, and check the transition-table test near line 2015 of `tests/test_docs_lint.py`.
- [x] Regenerate the tool-surface golden and handler digests; update the label census.
- [x] Update seeds `100` and `180` (under `seed_edit_allowed`) and the packaged implement-wave template (under `framework_edit_allowed`), then the project-local implement-wave prompt.
- [x] Update the spec, `AGENTS.md`, `docs/architecture/current-state.md`, `docs/architecture/data-and-control-flow.md` and the CHANGELOG.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| close-change-tool | implementer | none | server code, registries, tests |
| close-change-docs | implementer | close-change-tool | spec, AGENTS.md, implement-wave prompt, CHANGELOG |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/publication_control.py`
- `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `.wavefoundry/framework/scripts/tests/test_label_reader_census.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_archive_root.py`
- `.wavefoundry/framework/scripts/tests/test_record_layout_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`
- `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`

- The repository-root AGENTS.md and CHANGELOG are edited too.

## Affected Architecture Docs

`docs/architecture/current-state.md` (lifecycle tool list, if it enumerates lifecycle writers) and `docs/architecture/data-and-control-flow.md` (a second status writer beside the wave-level lifecycle tools). No ADR: the operator decided the tool shape.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core write. |
| AC-2 | required | The gate is the safety contract. |
| AC-3 | required | Dependent activation is half the request. |
| AC-4 | required | Lint must pass after the write. |
| AC-5 | required | Closing a change must not lapse approvals. |
| AC-6 | required | Lifecycle writers must be serialized and registered. |
| AC-7 | important | Distributions rename labels. |
| AC-8 | important | Discoverability. |
| AC-9 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Gapfill: implement-stage retrieval telemetry shows no MCP code_* calls for this wave. The implementer and reviewer subagents explored with harness grep and file reads (and ran probes, mutations and suites as shell work); their MCP calls, where made, were not attributed to the wave. The harness fallback was used deliberately for exhaustive censuses (lane readers, registry and tool-table literals, wf_close_wave sites) where a literal file walk is the authoritative instrument. | Close dry run retrieval_posture_gap advisory, 2026-10-03 |
| 2026-10-03 | Delivery-review repair F5: `implemented` is now reachable, added to the allowed transitions from `ready`, `active` and `review` in `ALLOWED_CHANGE_STATUS_TRANSITIONS`; new lint test `test_implemented_is_reachable_from_ready_active_and_review` (`tests/test_docs_lint.py`, beside the transition-table test) shows a block with `Previous Change Status: active` and `Change Status: implemented` linting clean and the same block refused with the transition removed. Follow-up recorded (F6, left as is): a `Depends On:` line inside a fenced block of the wave record's member list is read by `_parse_change_records`, so it activates the dependent; this matches docs-lint, which reads the same line. | Failing-first and mutation R8 (transition removed from `active`) killed by the new test; full suite 10,878 OK (34 skipped), `--profile second` 10,875 OK, `--profile declared` 10,878 OK, in a fresh scratch copy |
| 2026-10-03 | Implemented. `wf_close_change_response` beside `wf_close_wave_response` in `wf_server/server_impl.py` (decorated `@_fail_closed_on_record_layout("wf_close_change")`), the `wf_close_change` tool (publication lock on create), `wave_lint_lib/constants.py` gains `"implemented": {"implemented", "complete", "completed"}` (1zlu0 had added only `DONE_CHANGE_STATUSES`). Registry census (predicate: every literal `wf_close_wave` or `wf_mark_ac` in `.wavefoundry/framework/scripts/`, tests excluded, quoted or bare): `_LIFECYCLE_MUTATION_LOCK_TOOLS` added; `mcp_tool_roster.TOOL_TIERS` added (`TIER_WRITE`); `PUBLICATION_WRITER_REGISTRY` added (`lifecycle`, `fail_fast`); `_LIFECYCLE_CONTEXT_STAGES`, `_TRACKING_CONTEXT_TOOLS`, `_lifecycle_milestone_completed` (`if tool_name == "wf_close_wave"`) and `_COST_EXEMPT_TOOLS` none (the tool is not a stage transition and records no lifecycle context, so it takes the default first-party cost accounting like `wf_mark_ac`); `context_efficiency.LIFECYCLE_PROMPT_MAP` none (no lifecycle prompt of its own, as `wf_mark_ac`); `render_platform_surfaces` legacy rename map none (no legacy name); `render_agent_surfaces`, `wave_lint_lib/cli.py`, `wave_lint_lib/secrets_validators.py`, `wave_lint_lib/wave_validators.py`, `change_doc_checklist.py` none (prose about close or marking only); `wf_server/edit_gate_handlers.py` has no literal in the current tree. Hand-listed tables updated: `tests/test_archive_root.py` (12 writers), `tests/test_record_layout_lifecycle.py` (both wrapper lists), `tests/test_server_context_efficiency.py` `SERIALIZED_WAVE_WRITERS`, `tests/test_server_tools.py` expected set; `tests/test_lifecycle_mutation_lock.py` has no enumerated list, so the busy refusal is pinned in `tests/test_close_change.py`. Goldens: tool-surface golden adds the `wf_close_change` entry; handler digests add `wf_close_change`; label census adds one `writer` entry (the wave-record previous-status line). Roster counts and digests re-measured in `test_server_tools.py`, `test_server_tools_retrieval.py`, `test_extension_tool_modules.py` (lock tools 11 to 12). Advisory sanctioned set gains `close_change_lint_preexisting` and `dependencies_not_in_wave_record`. Docs-lint was confirmed lock-free (no lock use in `docs_lint.py` or `wave_lint_lib/`); the scoped lint runs in process. Deviations: dry-run reports `planned_writes` beside the empty `written`; refusal codes are `wave_not_open`, `change_not_admitted`, `change_doc_missing`/`change_doc_unreadable`, `change_status_not_closable`, `change_status_drift`, `silent_unchecked_items`, `dependencies_not_done`, `close_change_transition_invalid`, `close_change_lint_failed`, `close_change_write_failed`; AC-7 is exercised by writing every fixture in the loaded profile and running the suite under `--profile second`. | `tests/test_close_change.py` (29 tests); failing-first: 2 failures and 32 errors on the pre-change tree; mutations Z1-Z10 each killed by its named test; full suite 10,866 OK (34 skipped), `--profile second` 10,863 OK, `--profile declared` 10,866 OK, all in a scratch copy |
| 2026-10-02 | Planned from the operator's decisions. Verified against the tree: `_LIFECYCLE_MUTATION_LOCK_TOOLS` (server_impl), `TIER_WRITE` roster entries, `PUBLICATION_WRITER_REGISTRY`, `_collect_silent_unchecked_items_for_close` (returns dicts carrying `change_id`, so it can be filtered), `ALLOWED_CHANGE_STATUS_TRANSITIONS` and `PROGRESSABLE_CHANGE_STATUSES` in `wave_lint_lib/constants.py`, the dependency rule in `check_wave_docs`, and `normalize_review_tracking_status` (normalizes only `Change Status`/`Status` lines in the leading carrier; `Previous Change Status` is a carrier key that is not normalized). `wf_implement_wave_response` reads `Depends On:` from the wave record's `## Changes` blocks with change-doc lines as a legacy fallback. Census finding carried from `1zlu0`: `implemented`, this repository's usual pre-close status, is not progressable, so this tool refuses an `implemented` change unless the `1zlu0` decision changes the vocabulary. | Code reads, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | An `implemented` dependency satisfies its dependents (activation and lint use `DONE_CHANGE_STATUSES` from `1zlu0`) | Operator decision: dependents move forward without forcing the dependency closed first | Require the dependency to be `complete` |
| 2026-10-02 | `implemented` is closable by `wf_close_change` (to `complete`) and stays non-terminal | Operator decision: changes marked `implemented` do not block wave close, but a change is closed only when it is closed | Make `implemented` lint-terminal |
| 2026-10-02 | New tool `wf_close_change(wave_id, change_id, mode)` under the lifecycle lock | Operator decision | A `change_id` argument on `wf_close_wave` (rejected: mixes wave and change gates in one tool); a generic status-setter (rejected: unbounded transitions, no gate) |
| 2026-10-02 | Dependents move to `ready`, never `active` | Operator decision: activation means "may start", and starting stays an operator act | Move to `active` (rejected) |
| 2026-10-02 | No per-change review evidence and no ledger event | Operator decision: review stays wave-level; status writes do not touch the digest | Require a per-change approval (rejected: no lane model for it) |
| 2026-10-02 | Reopening a completed change is out of scope | Operator decision; lint gives `complete` no outgoing transition | Allow `complete` back to `active` (rejected) |
| 2026-10-02 | `Previous Change Status` is written in the wave record block only | Keeps the review-policy digest unchanged: the change doc's previous line would not be normalized | Write it in both files (rejected: lapses approvals on every change close) |
| 2026-10-02 | Dependencies are read from the wave record's `Depends On:` lines; change-doc-only declarations are reported, not activated | The wave record owns dependency declarations (seed 110, `wf_implement_wave`) | Also honor legacy change-doc lines (rejected: prefix-matching legacy tokens could activate the wrong change) |
| 2026-10-02 | Post-write lint failure restores every written file | Operator requirement that lint passes after the write; a partial write would leave the two files in drift | Validate in memory only (rejected: cannot see every lint rule) |
| 2026-10-02 | Readiness amendments: activation candidates are only changes whose wave-record `Depends On:` names the closed change, with AC-3 cases for a no-dependency change and an already-satisfied one (B1); `wave_lint_lib/constants.py` and the `test_docs_lint.py` transition test added to targets and tasks (N1); `cache.invalidate()` on success (N2); registry census widened to every literal `wf_close_wave` outside tests (N3); rollback only on lint failures the write introduced, against a pre-write baseline, and docs-lint confirmed lock-free under the publication lock (N4); one existing parser, `wave_validators._parse_change_records`, and an out-of-wave target counts as not done (N5); `@_fail_closed_on_record_layout("wf_close_change")` and the hand-listed test tables in AC-6 (N6); the packaged implement-wave template and seeds `100` and `180` planned so distributions see the tool (N8); architecture docs in tasks and ACs (N11); blocked-dependent risk recorded | Readiness review findings, 2026-10-02. Operator decisions above are unchanged | Leave the findings to implementation (rejected: B1 is a correctness gap in the plan) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A dependency reaching `implemented` by a hand edit activates nothing automatically | Activation runs when `wf_close_change` closes a change; dependents whose dependencies are all in `DONE_CHANGE_STATUSES` (terminal or `implemented`) are activated then, and lint already lets an operator move such a dependent forward by hand |
| `_collect_silent_unchecked_items_for_close` is being changed by `1zltr` in wave `1zls7` | Reuse it rather than copy it, so this tool inherits `1zltr`'s fixes; implement after `1zltr` lands or rebase on it |
| A new name-keyed registry is missed (the 1z8oz lesson) | Requirement 2 census with a stated predicate |
| Auto-moving a `blocked` dependent to `ready` may override a reason for blocking it that is not a dependency (for example an operator hold) | The operator decision to activate `blocked` dependents stands; the response reports every activated change in `data.activated` with its prior status, so the move is visible and the operator can set the change back |
| Rollback after a partial write on Windows (a file held open by an editor or indexer) | Atomic replace per file; a restore failure is reported with the paths left changed, never silent. Behaviour is otherwise identical on Windows, macOS, Linux and WSL2; paths are repo-relative POSIX in the response |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
