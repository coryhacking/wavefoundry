# Show the approval phase in the Review Evidence status table

Change ID: `23zl1-enh review-evidence-phase-column`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-20
Wave: 23z46

## Rationale

Field feedback item 8 on v1.46.0 (`.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) reports that the `## Review Evidence` status table misleads operators between readiness and delivery. The table has one row per signoff key and, except for `council-readiness`, each row shows the key's delivery-phase state. A specialist lane that approved at readiness therefore reads `pending` with the next action "record approval evidence for code-reviewer" before any code exists, which looks like a missing approval.

Executed reproduction (scratch copy of `docs/waves/23ve6 developer-delivery-walkthrough/events.jsonl`, first five records, which hold the receipt and the four readiness approvals): `review_status_human_table` renders `council-readiness` as `approved` and `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` as `pending`, while `review_status_rows(..., approval_phase="readiness")` reports all three specialists `approved`. The readiness approvals exist in the ledger; the table omits them.

## Product Intent

An operator who reads a wave's `## Review Evidence` table between Prepare and Review wave can see that each specialist lane approved the plan at readiness and still owes a delivery approval, instead of reading the lane as a missing approval. The table remains a projection of `events.jsonl`: no gate, approval rule, structured tool field or closed record changes. AC-1 establishes the intent: on a ledger holding only readiness approvals, the rendered table shows those approvals as approved readiness rows.

## Requirements

1. `review_status_human_table` in `.wavefoundry/framework/scripts/review_evidence.py` must render the header `| Signoff | Phase | State | Why | Next action |`. The Signoff column stays first, so `_status_block_row_keys` (which reads the first cell to keep sticky council labels, wave 1zyb4) needs no change.
2. Each existing row gains a Phase cell naming the phase whose state the row shows: `readiness` for the council readiness key, `delivery` for every other key. The derivation is the existing `_council_approval_phase` helper; the row's state, why and next action are unchanged.
3. For a specialist key (as defined by `_specialist_readiness_identity`: not a council key, not `operator-signoff`), the table adds a `readiness` row immediately before that key's `delivery` row when the ledger holds an approval claim for the key under `_approval_rows(records, approval_phase="readiness")`. Its State, Why and Next action come from `review_status_rows(records, keys, approval_phase="readiness")` for that key, so a receipt-stale or finding-blocked readiness approval reads `pending` or `withheld` with the existing reason.
4. The trailing `Readiness <key>: ...known-bad control not applicable...` sentences that `review_status_human_table` appends after the table are removed, because the readiness row's Why already carries that text (`review_authority_projection` appends it to the readiness-phase row). The text must still appear in the rendered block for a wave that recorded such an approval.
5. The empty-table row becomes `| — | — | — | — | — |` to match the five-column header.
6. Structured outputs do not change: `review_authority_projection`, `review_status_rows` and every `status_rows` consumer (`lifecycle_gates.py`, `lifecycle_gate_support.py`, `dashboard_lib.py`, `wf_server/server_impl.py`) keep their current fields and values. Only the Markdown table changes.
7. Closed records are never rewritten. The existing writers and staleness checks already skip closed waves (`wave_lint_lib/wave_validators.py` re-renders the status block only when `not wave_record_closed(text)`; `lifecycle_gates.py` skips `closed_archive`; `review_policy_upgrade.py` skips `Status: closed`). This change keeps those guards.
8. Upgrade must re-render the status block of every non-closed declared wave whose block differs from the incoming renderer's output, without setting the re-Prepare marker and without writing any ledger record, so a target repository with a planned, readied or open declared wave passes the docs gate of the upgrade that installs this renderer.
   1. On the apply path the re-render must run from the incoming pack's `pre_docs_gate` hook in `upgrade_extensions.py`, after that hook's dry-run return and above its `review_sidecar_cleanup` early return. A current runner records that key before it calls the hook, so code placed below the return would not run. Verified by reading: the current runner and both old-runner fixtures (v1.22.0, v1.31.0) call `pre_docs_gate` from the pack-loaded extension after extraction and before the docs gate. It is `unverified` by execution on an old runner until AC-7 runs.
   2. The re-render must use the incoming renderer. The runner process that drives the installing upgrade imported the installed `review_evidence` and its sibling modules before extraction, so the hook must run the re-render in a `-B` child process over the extracted tree's scripts and must not call the renderer through modules the runner already imported. Executed by the architecture reviewer on a five-column prototype: a child that imports the extracted scripts re-rendered both non-closed waves, left each `events.jsonl` and each `review-policy-reprepare-required` line byte-identical, and the following lint exited 0.
   3. The re-render must not live in `plan_review_policy_upgrade`. The runner computes that plan before extraction with the installed module, applies the same plan object after extraction, and the resume branch discards the plan it computes (verified by reading), so a planner branch never compares against the incoming renderer. It must also not reuse `WaveMigration` or `apply_review_policy_upgrade`: that path writes the re-Prepare marker, emits a `review_policy_marker` checkpoint and reports each wave under `waves_marked_for_reprepare`, all of which would be false for a marker-untouched write.
   4. The `--resume-after-gate` branch must call the same re-render before its docs gate, beside `_repair_declaring_scaffold_on_resume`. That branch runs after extraction in a fresh process, so its modules are the extracted ones (verified by reading). Without the call, a wave that could not be re-rendered on the apply run stays stale on every resume.
   5. A wave whose ledger cannot be read is left unchanged and named in one output line. The re-render must not raise for it; the docs gate that follows reports the ledger error.
   6. The re-render also covers a changed-policy upgrade: there the installed planner has already projected the wave with the installed renderer, and the write lands before `pre_docs_gate` runs (verified by reading).
   7. The hook call, its child process, the resume-branch call and the new write path are new review surface added by the readiness repair.
   8. The premise that the docs gate fails without the re-render was executed during readiness review on a prototype renderer (lint exit 1, `review evidence projection is stale` for `23z45` and `23z46`). AC-6 repeats it on the delivered renderer.
9. Behaviour is identical on Windows, macOS, Linux and WSL2. The table change is string rendering inside the existing newline-preserving projection writers. The upgrade re-render is a new write path: it must keep each wave record's newline convention (LF or CRLF) and replace the file atomically. Its child process follows the extension's existing child contract, the one `_incoming_renderer_query` uses: no console window on Windows, captured output, a UTF-8 environment and no bytecode written beside the sources. Windows behaviour of the child is not executed at plan time.

## Scope

**Problem statement:** the status table shows delivery state for specialist lanes and hides their readiness approvals, so an operator reads a correctly readied wave as missing approvals.

**In scope:**

- The Markdown table produced by `review_status_human_table` (header, Phase cell, specialist readiness rows, empty row, removal of the trailing readiness sentences).
- Upgrade-time re-rendering of non-closed declared waves' status blocks on renderer drift, from the incoming `pre_docs_gate` hook and the resume branch.
- The `resume_after_gate` contract text in the `wf_upgrade` docstring, `docs/specs/mcp-tool-surface.md` and seed 160.
- Re-rendering the status blocks of this repository's non-closed declared waves after the renderer change.
- Updating tests and the docs-lint fixture that pin the four-column shape, seed 100's description of the table, and the two project docs that describe it.

**Out of scope:**

- Any change to approval validity, gate decisions, receipts, `events.jsonl` records or the structured `status_rows` fields.
- Rewriting closed wave records or archives, including the 151 closed records whose status block already differs from today's renderer (census below).
- Changing how the `wavefoundry://` wave resource (`_validated_wave_markdown` in `wf_server/server_impl.py`) serves closed records. It re-derives them and appends a stale diagnostic on mismatch; 151 closed records already trigger that today, and this change leaves the behaviour as it is (operator decision 2026-11-20).
- Readiness rows derived from the wave's `Required review lanes` roster for lanes with no readiness approval yet (see Decision Log alternative C).
- Dashboard UI changes beyond the table text it already renders through `review_status_human_table`.

## Acceptance Criteria

- [x] AC-1: A test renders `review_status_human_table` from a ledger holding a receipt, `council-readiness` and specialist readiness approvals but no delivery approvals, and asserts that each specialist has a `| <key> | readiness | approved |` row followed by a `| <key> | delivery | pending |` row, and that `council-readiness` reads `| council-readiness | readiness | approved |`. With the fix absent no readiness row exists for the specialist and the assertion fails.
- [x] AC-2: A test asserts the header line is exactly `| Signoff | Phase | State | Why | Next action |` and that the empty-roster table's only data row is `| — | — | — | — | — |`, with both assertions scoped to the text between the `wave:review-status` markers so the Finding Synthesis table's five-dash row cannot satisfy them.
- [x] AC-3: A test shows a readiness row tracks currency: after a new policy receipt is appended that the readiness approvals do not bind, each specialist readiness row reads `pending` with the existing "approval binding is stale" reason, while `review_status_rows` (default phase) returns the same structured rows as before the change.
- [x] AC-4: A test on a ledger with a specialist readiness approval recorded with `known_bad_detected=null` asserts the known-bad not-applicable text appears in that key's readiness row Why cell and that no line starting `Readiness ` follows the table.
- [x] AC-5: A test renders `render_review_status_projection` on a wave whose block uses the four-column header, then re-reads the block, and asserts the council row keeps its legacy `wave-council-readiness` spelling (sticky labels still work with the new layout).
- [x] AC-6: Known-bad run for the upgrade premise: with the new renderer in place and the requirement 8 re-render disabled, a recorded run of the upgrade docs gate (or docs-lint, which the gate runs) on a fixture target holding one readied declared wave and one never-prepared planned declared wave, each with a four-column block, reports each wave's review evidence projection as stale and fails. The run's command and output are recorded in the Progress Log. If the run does not fail, the requirement 8 premise is refuted and the coordinator decides whether to drop requirement 8 before delivery.
- [x] AC-7: A packaged upgrade that installs the five-column renderer passes its docs gate on a fixture target with an unchanged policy that holds one readied declared wave and one never-prepared (`Status: planned`) declared wave with no policy receipt, each carrying a four-column block. Oracle: a test drives the upgrade path through the real runner entry from a process that imported the four-column `review_evidence` before extraction (an old-runner fixture under `tests/fixtures/upgrade_old_runner/`, or an equivalent process). It does not call the planner or the re-render function in process. With the `pre_docs_gate` re-render absent the same run stops at the docs gate with `review evidence projection is stale` for both waves, so the criterion fails when the re-render does not run on the installing upgrade. Because the driving process holds the four-column module, a re-render made through already-imported modules instead of a child over the extracted tree also fails sub-point 1.
  1. After the run each non-closed wave's status block is the five-column table.
  2. Each wave's `review-policy-reprepare-required` line and `events.jsonl` are byte-identical to their state before the run, and the run reports no wave under `waves_marked_for_reprepare`.
  3. A wave record written with CRLF line endings keeps them.
  4. A target that retained `failed_phase=docs_gate` with a four-column block in a non-closed wave passes `--resume-after-gate`. With the resume-branch call absent the resume fails with the stale projection error.
  5. A closed declared wave fixture whose block uses the four-column header is byte-identical after the run, and docs-lint and the lifecycle gate staleness check report no "projection is stale" error for it.
- [x] AC-8: After implementation, docs-lint reports no stale review evidence projection for any non-closed declared wave in this repository, and `git status` shows no modified closed `wave.md`.
- [x] AC-10: The three texts that describe `resume_after_gate` agree with the delivered behaviour: the status-block re-render, then docs-gardener and docs-lint against the already-extracted tree, then ordinary index publication. Oracle: a test or reviewer check finds the re-render clause in the `wf_upgrade` docstring, in the `resume_after_gate` bullet of `docs/specs/mcp-tool-surface.md` and in the seed 160 sentences that describe the resume path, and finds no statement in any of them that the code does not perform.
- [x] AC-9: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`; change `review_status_human_table` per requirements 1 to 5.
- [x] Before adding the re-render, execute the AC-6 known-bad run against the new renderer and record its command and output in the Progress Log.
- [x] Add the status-block re-render for non-closed declared waves as a function in the extracted tree (`review_policy_upgrade.py`), with its own newline-preserving atomic write and no use of `WaveMigration` or `apply_review_policy_upgrade`. Leave `plan_review_policy_upgrade` unchanged.
- [x] Call the re-render from `pre_docs_gate` in `upgrade_extensions.py` through a `-B` child over the extracted tree, above the hook's `review_sidecar_cleanup` early return, and from the `--resume-after-gate` branch in `upgrade_wavefoundry.py` beside `_repair_declaring_scaffold_on_resume` (requirement 8). Sequence both edits with sibling `23zia`, which edits the same two files.
- [x] Own the `resume_after_gate` contract text and reconcile its three copies (AC-10). The `wf_upgrade` docstring in `wf_server/upgrade_handlers.py` already says the phase rebuilds and persists the review-status projection, which the resume branch does not do today (verified by reading); the resume-branch call makes it true, so correct the docstring only where it still differs from the delivered behaviour. Add the re-render clause to the `resume_after_gate` bullet in `docs/specs/mcp-tool-surface.md`. Open `seed_edit_allowed`, add it to the seed 160 sentences that describe the resume path, and close the gate. Sequence the seed 160 edit with sibling `23zia`.
- [x] Update test pins on the four-column shape (census: 19 `| <key> | <state> |` assertions across `test_build_pack.py`, `test_council_signoff_keys.py`, `test_dashboard_server.py`, `test_docs_lint.py`, `test_review_evidence.py`, `test_review_policy.py`, `test_run_tests_repo_guard.py`, `test_server_tools_lifecycle.py`) and regenerate the active fixture `tests/fixtures/docs_lint/base/docs/waves/change-2026-03/wave.md` from its ledger.
- [x] Add the tests for AC-1 to AC-5 and AC-7, including the CRLF case and the resume case.
- [x] Open `seed_edit_allowed`; update the table description in `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`; close the gate.
- [x] Update `docs/specs/mcp-tool-surface.md` and `docs/architecture/data-and-control-flow.md` descriptions of the `wave:review-status` table, the upgrade flow's re-render step in `docs/architecture/data-and-control-flow.md`, and the `upgrade_extensions.py` edge in `docs/architecture/layering-rules.md`.
- [x] Re-render the status blocks of this repository's non-closed declared waves (today `23z45` and `23z46`) through the existing projection write path; confirm no closed record changed.
- [x] Add a CHANGELOG Unreleased bullet that names the new header and states that the status-block re-render acts on the upgrade that installs this change (sibling `23zia` Requirement 12 carries the same sentence into seed 160); close `framework_edit_allowed`; run `python3 .wavefoundry/framework/scripts/run_tests.py` last.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer | implementer | none | Requirements 1 to 6 and their tests |
| upgrade-rerender | implementer | renderer | AC-6 known-bad run, then requirement 8 (the `pre_docs_gate` child and the resume-branch call) and its tests; sequence the `upgrade_extensions.py` and `upgrade_wavefoundry.py` edits with 23zia |
| docs-and-rerender | implementer | upgrade-rerender | Seeds 100 and 160, the `resume_after_gate` contract text, project docs, fixture, re-render open waves |


## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/review_policy_upgrade.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/layering-rules.md`

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`: the section "Review history and current state" says the `wave:review-status` view holds "one row per canonical signoff key"; it changes to one row per key and phase shown, with the Phase column. The upgrade flow gains the status-block re-render before the docs gate, on the apply path and on resume.
- `docs/architecture/layering-rules.md`: the `upgrade_extensions.py` rows of the edge table gain one edge. `pre_docs_gate` spawns a `-B` child that runs the extracted tree's re-render, so the incoming renderer never runs against the installed runner's cached sibling modules.
- No decision record. The re-render is a new step in an existing hook and moves no ownership boundary.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Proves the intent: readiness approvals are visible as readiness rows. |
| AC-2 | required | Pins the new contract shape and guards against the Finding Synthesis row collision. |
| AC-3 | important | Shows readiness rows report currency, not just presence, and structured rows are unchanged. |
| AC-4 | important | The known-bad text must not be lost when the trailing sentences go. |
| AC-5 | important | Protects wave 1zyb4 sticky council labels across the layout change. |
| AC-6 | required | Executes the upgrade premise before requirement 8 is built (operator decision). |
| AC-7 | required | Proves the re-render runs on the installing upgrade and on resume, is bounded, and leaves closed records unflagged by lint and gates. |
| AC-8 | required | This repository's own open waves must lint clean after the change. |
| AC-9 | required | Change-local verification. |
| AC-10 | important | The docstring, the tool reference and seed 160 must describe the same resume behaviour. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-20 | Spec authored from field feedback item 8 | Scratch reproduction and census in Decision Log |
| 2026-11-20 | Plan review finding: requirement 8 covers every non-closed declared wave but AC-7 exercised only a readied wave. Verified the skip: `plan_review_policy_upgrade` in `.wavefoundry/framework/scripts/review_policy_upgrade.py` (lines 129 to 136) sets `stale_evaluator` only when a receipt exists and skips the wave when `policy_unchanged and not stale_evaluator`. Executed the planner read-only on this repository: zero waves planned, and both planned waves `23z45` and `23z46` have empty ledgers with no receipt. AC-6 and AC-7 now include a never-prepared planned wave. | Advisory plan review relayed by the coordinator; planner run output: `carriers 0 waves planned []` |
| 2026-11-20 | Applied operator decisions: upgrade re-render kept but gated on a known-bad run (AC-6), wave-resource closed-record change cut to Out of scope, readiness rows from recorded approvals kept | Coordinator relay of operator decisions given in the main session |
| 2026-11-20 | 2026-11-20 readiness repair pass 1. Repaired findings `R1-23zl1-rerender-never-runs` (requirement 8 moved from the planner to the incoming `pre_docs_gate` hook, run as a child over the extracted tree, with a resume-branch call; AC-7 now drives the upgrade path) and `R1-23zl1-resume-after-gate-contract` (a task and AC-10 own the three `resume_after_gate` texts). Serialization Points, Affected Architecture Docs, the Decision Log and the Risks follow. The installing-upgrade sentence for the changelog is added to the last task. | Reads of `main`, the resume branch, `pre_docs_gate`, `plan_review_policy_upgrade`, `apply_review_policy_upgrade` and both old-runner fixtures; the architecture reviewer's executed old-window probe and child re-render in `.wavefoundry/work/23z46/review/architecture-reviewer.md`. Old-runner execution of the hook path is `unverified` until AC-7 runs. |


| 2026-11-21 | Readback: A specialist who approved the plan currently reads pending. The status table will show its approved readiness row immediately before its pending delivery row. I will test phase currency, aliases and the unchanged structured results. The incoming upgrade hook and the resume branch will refresh open records from their ledgers and preserve closed history, ledger bytes, markers and line endings. | AC-1 through AC-10 cover review_evidence, review_policy_upgrade, upgrade hooks and the corresponding tests and contracts. |
| 2026-11-21 | Before adding the upgrade repair, ran `python3 -B .wavefoundry/work/23z46/phase-check/before.py`. It created an isolated target with the prior four-column renderer, a ready record with its receipt and approval, and a never-prepared record with an empty ledger. The delivered docs_lint.py --read-only exited 1. | Both 0a001 ready and 0a002 planned reported “review evidence projection is stale; regenerate it from sibling events.jsonl”. The existing active lint fixture also reported stale. |
| 2026-11-21 | Ran the ReadinessDeliveryIsolationTests and ServedReadinessKnownBadTests classes, including stale approvals, legacy labels and the readiness explanation. | All 9 tests passed. The two live record projections and active lint fixture were regenerated from their ledgers. |
| 2026-11-21 | The v1.31.0 runner installed a pack from a process holding the old four-column renderer. Real extraction, policy migration, the incoming hook, docs-gardener and docs-lint all ran. A fresh process exercised retained docs-gate recovery. Both checks passed. | InstallingReviewStatusTests asserts that a readied CRLF record, a planned LF record, their ledger bytes, re-Prepare markers and a closed record survive. The upgrading parent still held the old module after the gate. The fixture substitutes unrelated host preflight, host rendering, pruning and index publication. Native Windows was not exercised. |
| 2026-11-21 | In a temporary fixture, omitting the installing hook produced exit 1. Removing the resume call also produced exit 1. Each run reported stale projections for both open fixture records. Restoring the call let resume exit 0. A missing ledger left that record intact and printed one diagnostic while its sibling refreshed. | Omission control in disposable work; the independent expectations live in test_upgrade_review_status.py. |
| 2026-11-21 | 271 tests passed across the isolated installing upgrade, review-policy CRLF migration, review evidence, null known-bad and council-signoff suites. Another 20 passed across selected build-pack, dashboard, docs-lint, lifecycle and resume tests. Full wf_validate_docs passed. Only the two open-history projections and one test fixture changed. | The coordinator runs the complete framework suite after sibling changes. The existing repo-guard four-column example checks a hand-authored, non-projected region and keeps that purpose. |
| 2026-11-21 | Repaired `D1-23zl1-refresh-removes-human-prose` and `D1-23zl1-completed-history-refresh`. Apply and resume refreshed the ready and planned records. Both preserved the ready record’s prose outside the markers, its ledger, and the entire closed and completed records and ledgers. A separate mixed-newline case preserved both surrounding byte ranges. | 392 focused tests passed. In three disposable packs, restoring the unbounded write deleted the fenced note despite a green gate, restoring the unbounded comparison failed the gate despite preserving the note, and restoring closed-only refresh rewrote the completed record despite a green gate. The current planner also refused a missing live ledger and skipped both historical ledgers. |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Select approach A: a Phase column plus a readiness row for each specialist key that holds a readiness approval in the ledger. | Replaying the motivating case (23ve6 ledger prefix, executed in scratch with a prototype renderer) yields `code-reviewer / readiness / approved` above `code-reviewer / delivery / pending`, which removes the "missing approval" reading; on the full ledger every row reads approved. Efficacy: the mechanism is presentation only and advises; the operator acts on it because it is the table they already read. It can mislead only if a lane required at readiness has no approval yet (no readiness row appears), which Prepare already reports. Existing data gives all the value: the readiness rows come from the existing `review_status_rows(approval_phase="readiness")`. Success after release: no repeat of feedback item 8 and no "missing approval" questions on readied waves. | B: keep one row per key and change the Why or State text (for example "pending delivery; readiness approved"). Weakness: `state` is a structured vocabulary that gates and tools read, and a Why-only change keeps the misleading `pending` cell. C: derive readiness rows from the `Required review lanes` roster so an unapproved required lane shows `pending` at readiness. Weakness: `required_review_status_keys` merges both rosters into one key list, so this needs new phase-aware roster parsing; more mechanism for a case Prepare already covers. D: Phase as the first column. Weakness: `_status_block_row_keys` reads the first cell for sticky council labels and would need a header-aware parser. |
| 2026-11-20 | Phase goes second, after Signoff. | Keeps the first-cell parser unchanged. Cost: 19 test assertions that pin a key cell directly followed by a state cell need the Phase cell inserted; census below. | Phase last: keeps those pins but reads poorly. |
| 2026-11-20 | Reader census (executed, `code_keyword` limit=0 and grep over `.wavefoundry/framework` excluding `tests/fixtures`): code that parses the table text is limited to `_status_block_row_keys` (first cell only). All other references compare the whole rendered block to the renderer's own output (`wave_validators.py`, `lifecycle_gates.py`, `dashboard_lib.py`, `run_tests.py` repo guard, `server_impl.py` resource) or use the structured `status_rows`. The table is outside the review-policy digest: `policy_input_snapshot` in `review_policy.py` hashes config and change docs only, and `run_tests.py` `_strip_projected_regions` removes projected regions. | No receipt rotates from the renderer change; it rotates only the framework test receipt, as any framework edit does. | None |
| 2026-11-20 | Closed-record census (executed in scratch over every closed declared wave with `events.jsonl`): 233 closed blocks match today's renderer and 151 already differ. Lint, gates and upgrade skip closed records, so this drift is accepted history. The wave resource re-derives closed records and appends the stale diagnostic (inferred from reading `_validated_wave_markdown`; not executed through the MCP resource). | Closed records stay unwritten. | See the operator decision below on the resource. |
| 2026-11-20 | Upgrade reprojection on renderer drift is in scope (requirement 8). `plan_review_policy_upgrade` reprojects non-closed waves only when the policy or evaluator version changed (verified by reading). Inferred, not executed: after this renderer change, docs-lint at the upgrade docs gate reports each readied or open declared wave in a target repository as "review evidence projection is stale". | Bumping `REVIEW_POLICY_EVALUATOR_VERSION` would also reproject, but sets the re-Prepare marker and lapses readiness approvals. | Tell operators to replay a typed event per wave after upgrade: manual and fails the gate first. |
| 2026-11-20 | Operator decision: keep the upgrade re-render (requirement 8), but treat its premise as `inferred` until AC-6 executes a known-bad run showing the docs gate failure without it. | A mechanism justified by an unexecuted failure must be proven before it is built. | Build it on the reading alone; drop it. |
| 2026-11-20 | Operator decision: cut the wave-resource closed-record change; it is Out of scope. | 151 closed records already differ from the renderer and draw the stale diagnostic today; this change does not create that behaviour. | Keep it in scope as a widening. |
| 2026-11-20 | Operator decision: readiness rows come from recorded readiness approvals, not the `Required review lanes` roster (approach A stands). | Matches the selected approach; roster parsing adds mechanism for a case Prepare covers. | Alternative C (roster-derived rows). |
| 2026-11-20 | Readiness repair: the requirement 8 re-render runs from the incoming `pre_docs_gate` hook, as a child process over the extracted tree, and from the resume branch. It supersedes the planner branch of the earlier row. | Verified by reading: the runner imports `review_policy_upgrade` and plans before extraction, applies that plan after extraction, and the resume branch discards its plan, so a planner branch runs installed code against the installed renderer and never acts, on the installing upgrade or any later one. Executed by the architecture reviewer: after a simulated extraction of a five-column prototype the docs gate lint exits 1 for both non-closed waves, and exits 0 after a child over the extracted tree re-renders them. `pre_docs_gate` is the existing same-run repair seam: `repair_declaring_scaffold` already clears a docs-gate failure there on the installing upgrade, with a matching resume call. Efficacy: replaying a target with an open declared wave, the hook re-renders before the gate and the gate passes; the mechanism controls the outcome; it misses a wave whose ledger cannot be read, which the gate reports; it writes only the marker-owned status block. | Keep the planner branch (never compares against the incoming renderer). Narrow requirement 8 to "one upgrade later" and disclose it (ships a docs-gate failure after extraction to every target with a non-closed declared wave, the state sibling `23zia` exists to prevent). Reload `review_evidence` in the runner process (the reload re-executes one module against the installed runner's cached siblings). Reuse `WaveMigration` (writes the re-Prepare marker and reports the wave as marked). |
| 2026-11-20 | Readiness repair: the resume branch re-renders too, and the three `resume_after_gate` texts are reconciled to that behaviour. | The `wf_upgrade` docstring already promises a projection rebuild on resume that the code does not perform, while `docs/specs/mcp-tool-surface.md` and seed 160 say only that the docs gate reruns (verified by reading all three and the resume branch). Adding the call makes the docstring true and lets a resume recover a wave that could not be re-rendered on the apply run. | Correct the docstring and add no resume call (a wave left stale on the apply run then fails every resume). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Tests that assert the five-cell empty row with `assertIn` pass vacuously on the Finding Synthesis empty row once the status table also has five columns. | AC-2 scopes assertions to the status markers; the implementer checks each updated empty-row assertion is scoped the same way. |
| The `run_tests.py` repo guard compares the open wave's generated view to the renderer; mid-implementation, `23z46`'s block is stale and may refuse the run (inferred). | Re-render `23z46` immediately after the renderer edit, before running the suite. |
| An operator script or downstream tool parses the four-column table by position. | None found in this repository (census above); the CHANGELOG bullet names the new header. Closed records keep the old shape, so readers must accept both. |
| Sibling `23zia` in this wave edits the same upgrade files: `upgrade_extensions.py`, `upgrade_wavefoundry.py`, seed 160, `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md` and `docs/architecture/layering-rules.md`. | The coordinator orders the two changes' edits to each file; whichever lands second rebases on the first and reruns both changes' upgrade tests. |
| The wave resource keeps flagging closed records as stale, now for all closed declared waves rather than 151. | Accepted by operator decision; out of scope here. |
| Requirement 8 widens upgrade writes to planned, readied and open waves through a new write path. | The write is limited to the marker-owned status block and keeps the file's newline convention; AC-7 proves the marker and ledger are untouched and covers a CRLF record. |
| The `pre_docs_gate` re-render does not run when an old runner drives the installing upgrade. Status: verified by reading for the v1.22.0 and v1.31.0 fixtures, `unverified` by execution. | AC-7 drives the upgrade path from a process that holds the old renderer. If it shows the hook does not run, requirement 8 is narrowed to "takes effect one upgrade later" and the gap is disclosed in seed 160 and the changelog before delivery. |
| A fault in the re-render child raises in `pre_docs_gate`, which the runner turns into exit 3 at the docs-gate phase. Status: `inferred`. | Requirement 8 leaves an unreadable wave unchanged without raising; the resume branch repeats the re-render after the operator's repair. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
