# Close Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Close wave`**

## Operator-selected small changes

On an eligible small change, close checks the current delivered contents against the independent code reviewer’s approval. Follow the returned review actions when the files have changed or the work has expanded. The operator still signs off and explicitly directs closure.

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-spec.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort for reconciliation and unresolved judgments by task fit. Efficient routine checks do not waive review evidence or explicit operator closure authority. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Close a delivered wave after implementation, review, documentation, and
handoff state are fully reconciled. Close wave is the only wave close, whatever
the change count.

## Close a paused delivery

When the operator authorizes closure, pass the ID of the paused delivery directly to Close. Keep the currently open wave’s handoff, focus and edit gates intact, including when Close refuses or retries. The reviewed delivery still goes through the ordinary close checks, including any required current test receipt.

## Closure checks

All closure-time code and docs investigation follows the run contract's
Retrieval Rules (`seed-020`): MCP retrieval tools first, for every lane and
briefed subagent.

1. Every change is `implemented`, `complete`, or `deferred` with rationale, and
   every AC and task is completed or intentionally deferred with rationale.
   **Close spec** (`wf_close_change`) is optional; use it to mark a single
   change `complete` and activate its dependents inside the open wave.
2. Required review lanes are current. Check each Council signoff required by the current Prepare receipt for its phase (`council-readiness` or `council-delivery`).
3. Change status, wave status, completion date, and chronology agree.
4. Architecture, behavior contracts, public prompts, and release notes reflect the
   delivered behavior.
5. Journals, durable memory candidates, and the session handoff are reconciled.
   Run `memory_propose(wave_id, mode='create')`, then use
   `memory_validate` on every evidence-derived candidate. The validating
   agent follows the linked evidence and current target, states the future
   action delta, checks canonical overlap and confidence, and records
   `promote`, `retain`, `reject`, or `rewrite`. A wave may correctly produce
   zero memories; a missing or pending eligible candidate blocks close.
6. The canonical test suite, docs gate, and relevant packaging checks pass.
7. The context-efficiency checkpoint has been projected from durable telemetry
   when telemetry is available.
8. Run `wf_close_wave(mode='dry_run')` before requesting operator approval.
9. Before the final docs validation and the close write, read the dry run's
   advisory `record_extras_present`, which lists each file in the wave folder
   other than the record, its admitted specs and its ledger, with size and
   citation state. Give every listed file one disposition: keep it and name it
   with the reason in `## Review Checkpoints`; summarize it there or in a
   spec's Progress Log, then remove it; or remove it. Always keep a
   `cited_in_ledger` file, a `cited_in_record` file whose citation sits in a
   spec section other than the Progress Log, and a `not_cited` file with
   `name_in_ledger`, `name_in_record` or `directory_in_ledger` true. Before
   removing a `not_cited` file with all four booleans false, search the ledger
   for its name stem and the other extras for its name; a match keeps it. When
   in doubt, keep it and say why. The report lists at most 50 files: list the
   folder yourself and give every extra a disposition under the same rules,
   including files the report does not list, and review the folder by hand
   when `complete` is false. An unlisted file has no citation state or flags,
   so search the ledger, the record and the specs for its path, name and
   directories, and keep it unless nothing refers to it. Follow seed 190's **Wave-folder cleanup** for the full rules;
   the tool removes nothing and blocks nothing.

Before closure, explicitly author one concise `Intent outcome:` paragraph in the existing exact `## Review Checkpoints` section: state achieved, partial or not established, cite evidence, and retain material limitations. When the plan states a measure of success, cite it and say whether it can be read yet. It may cover changes sharing an outcome. The close-summary composer carries the last such paragraph or list item (optionally dated `YYYY-MM-DD: `) into Wave Summary, preserving its text and qualification; do not infer achievement from titles or checked ACs. Legacy records without this assessment remain closable under existing gates and retain their existing summary behavior; this adds no schema or blocking gate. When the current `council-delivery` approval records `intent_fit: does_not`, Review and Close report the `delivery_intent_not_established` advisory; it does not block, and the operator's sign-off accepts that outcome.

Final review evaluates any reviewer/persona lanes newly applicable to the delivered scope. This is not a blanket rerun of an unchanged readiness Council. Material policy, roster or readiness changes follow existing re-Prepare and current-approval requirements; otherwise consume the current readiness authority and complete the required delivery reviews. A change admitted after delivery review makes the earlier delivery approvals not current once the wave is re-prepared, so re-Prepare, then record the affected delivery approvals again before closing.

## Operator authority

Only an explicit operator instruction authorizes `wf_close_wave(mode='create')`
or equivalent apply mode. Passing dry-run, finishing implementation, or asking
for review does not imply closure approval. Commit, tag, push, and release
authority remain separately operator-owned.

## Disposable work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply. Before finalizing evidence, preserve unique long-term proof in maintained wave records, tests or explicitly retained evidence; new durable approvals must not rely solely on disposable paths. Only successful operator-authorized whole-wave closure attempts owned cleanup after its transition. Failure is advisory; unsupported safe deletion preserves files. Dry-run, failed close and single-change close preserve work. Authorized repeated close may retry; stale cleanup cannot remove a reopened generation. Ordinary wave-folder evidence is protected. Close reports, and never deletes, what it leaves: advisory `work_retained` when this record's folder stays (path, outcome `preserved` or `partially_removed`, reason, failed entry and errno, size and completeness, next action), `work_leftovers_present` for other folders of closed, archived or not-found records, `work_root_loose_files` for files and links left directly in the work root, and `work_path_cited` for maintained lines that cite this record's own work folder; `wf_audit` sizes the leftovers in `data.work_root`. To reclaim one such folder, preview `wf_cleanup_work(work_key='<key>')`, show the preview to the operator and call `mode='apply'` with its `confirmation` only when the operator directs cleanup of that key in the current request; native Windows previews and refuses apply.

Write every file you create for a wave, including coordinator briefs, logs, captured test output and build output, inside that wave's own work folder, in a child folder when that helps; never write a file directly in `.wavefoundry/work/`. Before the wave exists, keep the content in task context until a lifecycle call reports the work area. `wf_audit` and close report files and links left directly in the work root as the advisory `work_root_loose_files`. If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it. Leave any other loose file in place, including one you are not sure you wrote (a name that starts with a wave id does not prove who wrote it), and report it to the operator, who decides. Never move a file you did not write into a wave's folder: close removes that folder with everything in it.
