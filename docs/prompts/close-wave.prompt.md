# Close Wave

Owner: Engineering
Status: active
Last verified: 2026-11-22

Shortcut: **`Close wave`**

## Operator-selected small changes

On an eligible small change, close checks the current delivered contents against the independent code reviewer’s approval. Follow the returned review actions when the files have changed or the work has expanded. The operator still signs off and explicitly directs closure.

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-spec.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort for reconciliation and unresolved judgments by task fit. Efficient routine checks do not waive review evidence or explicit operator closure authority. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Close and archive the wave. Closure requires full reconciliation, not just a status flip. **Close wave** is the only wave close, whatever the change count.

## Close a paused delivery

When the operator authorizes closure, pass the ID of the paused delivery directly to Close. Keep the currently open wave’s handoff, focus and edit gates intact, including when Close refuses or retries. The reviewed delivery still goes through the ordinary close checks, including any required current test receipt.

## Closure Requirements (all must be met)

All closure-time code and docs investigation follows the run contract's Retrieval Rules (`.wavefoundry/framework/seeds/020-run-contract.prompt.md`): MCP retrieval tools first, for every lane and briefed subagent.

1. All changes `implemented`, `complete`, or `deferred` with explicit rationale (matching the `wf_close_wave` open-changes gate). **Close spec** (`docs/prompts/close-spec.prompt.md`, `wf_close_change`) is optional: use it to mark a single change `complete` and activate its dependents inside the open wave
2. All required review lanes from readiness reconciled in `## Review checkpoints` (or deferred with rationale)
3. Check each Council signoff required by the current Prepare receipt for its phase (`council-readiness` or `council-delivery`). The approval appears in `## Review Evidence`.
4. **Docs-contract review:** recorded as performed with findings, or `Docs-contract review: not applicable` with rationale — required whenever any `docs/specs/*.md` changed during the wave
5. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses settled
6. Memory capture: important implementation/review lessons recorded as typed memory candidates and validated at the close checkpoint (absence of new candidates is acceptable if nothing warranted one)
7. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable). When a repeated finding can be checked mechanically, name a check as a destination too: a sensor registered under `sensors` in `docs/workflow-config.json` (run by `wf_run_sensors`), a docs-lint rule or a test, and plan it as a change unless this wave already delivers it.
8. **Retrospective step completed:** ask "what was non-obvious in this wave that a future session should know?" — surface memory candidates for architectural decisions (why an approach was chosen), validated approaches that should carry forward (positive confirmations, not only corrections), and workflow discoveries; promote findings to auto-memory or `docs/references/project-context-memory.md`
9. `docs/agents/session-handoff.md` updated to idle format: last-closed wave ID and one-line summary of what shipped, plus an **Open questions / Deferred decisions** section for any intent not captured in a spec
10. **Hard checkbox gate** (wave 1p31b / 1p32k): every AC and every task across the wave's admitted changes is marked either `[x]` (completed) or `[~]` (intentionally deferred). Silent `[ ]` items block close — `wf_close_wave` returns a `silent_unchecked_items_at_close` diagnostic listing each one. ACs at `not-this-scope` priority are exempt (the priority encodes the exclusion). See `170-plan-spec.prompt.md` "AC and task checkbox states — the `[~]` marker" for the canonical convention.

Reconcile the applicable items in wave.md; existing hard gates and required typed authority remain the closure proof. Do not create a duplicate readiness file or checklist artifact.

**Automatic gate — framework test receipt** (wave `1wur7`, framework SOURCE repositories only, nothing to record by hand): `wf_close_wave` verifies the existing `.wavefoundry/framework/test-cache.json` receipt — `result == "ok"` with an `inputs_hash` matching the current framework tree — and returns a blocking `framework_test_receipt_not_proven` diagnostic when it is missing, red, stale, or unreadable. Read the `framework_test_receipt` field on the response; do not invent a checklist line for it. The gate runs no suite and spawns no subprocess; record a fresh receipt with `python3 .wavefoundry/framework/scripts/run_tests.py`, and run it LAST, because any edit under `.wavefoundry/framework/` (a seed edit made during closure included) invalidates the receipt. Two scope facts belong together. The receipt's `inputs_hash` covers `.wavefoundry/framework/` only, so only its STALENESS is framework-scoped. But `run_tests.py` writes a receipt only when the WHOLE suite is green, so a failure triggered by content under `docs/` prevents a NEW receipt from being written; when the framework tree also changed the standing receipt is stale and close is blocked, while in a documentation-only wave a current green receipt persists and close is not blocked despite a red suite. The gate is therefore not a whole-repository *guarantee* (a green receipt attests the framework code, not the tree), and it is not a whole-repository *exemption* either. Where the runner is absent — any repository consuming the packaged framework, since the distribution excludes it — the check is a documented no-op that neither blocks nor claims proof, and this item does not apply.

**Close-handoff surfacing of `[~]` items:** the close summary in `## Wave Summary` must list every `[~]` AC across the wave's admitted changes, grouped by change, with the inline status note. Future-readers see them as one discoverable list of intentional deferrals rather than scattered across individual specs.

Final review evaluates any reviewer/persona lanes newly applicable to the delivered scope. This is not a blanket rerun of an unchanged readiness Council. Material policy, roster or readiness changes follow existing re-Prepare and current-approval requirements; otherwise consume the current readiness authority and complete the required delivery reviews. A change admitted after delivery review makes the earlier delivery approvals not current once the wave is re-prepared, so re-Prepare, then record the affected delivery approvals again before closing.

## Final validation cadence

Finish material documentation, source and surface-rendering edits before the canonical source suite. Validated routine ledger/projection updates and normalized progress/status/completion may continue under seed 209's Continuation And Qualification Discipline; they alone require neither another suite nor another reviewer cycle. Use Progress Log during a run; the standalone session handoff and other documentation outside the wave under test may also change during it, as seed 209 describes. Reuse a matching current green receipt; changed, red or unproven inputs still require fresh qualification. Consume successful typed-write continuation actions without an extra full-review/list loop. When current authority already proves readiness and the operator has authorized closure, perform one close mutation; use dry-run for unresolved checks rather than a compulsory extra gate. Fresh full docs validation and required independent reviewers remain unchanged.

Consumer upgrades retain render → docs gate → incremental index ordering, without source/profile qualification, routine evidence generation or broad recuration.

## Wave-folder cleanup

Before finalizing evidence, promote unique long-term proof out of disposable work into maintained wave records, tests or explicitly retained evidence. New durable approvals must not depend solely on work-area paths. Before final docs validation and the close mutation, tidy only artifacts established to belong to this wave. Dates and filenames are discovery hints, not proof of ownership.

- Keep `wave.md`, admitted specs and authoritative `events.jsonl` in place. Routine briefings, per-seat reports, raw probes and green logs belong in task context or temporary storage, not a permanent repository file forest. Preserve unique review evidence, reproducible probes and historical fingerprints needed to substantiate claims. Never rewrite ledger history for cosmetic cleanup.
- Manually remove only verified wave-owned disposable scratch output or redundant copies with no unique evidence and no live references, using contained I/O and a parent-descriptor identity check before unlink. Keep cited originals and unreconstructable dirty-tree baselines. The sole automatic-cleanup exception is the newly designated owned `.wavefoundry/work/<wave-id>/`: after successful operator-authorized whole-wave closure, the tool attempts contained cleanup; failure is advisory and unsupported safe deletion preserves files with a notice. Dry-run, failed close and single-change close retain work; an authorized repeated close may retry, and reopening protects its fresh generation. Close reports the citation state of this wave folder's extra files and never deletes them (below); no other automatic deletion, expiry policy or cleanup gate is introduced. If ownership, uniqueness or reference use is uncertain, retain the artifact and note why.
- Close reports work it leaves behind; it deletes nothing beyond the owned cleanup above. When the closed record's own work folder stays in place, the response carries an advisory `work_retained` diagnostic with the path, the outcome (`preserved`, or `partially_removed` when some entries were removed before a failure), the reason token from the notice (for example `work_ownership_unproven` or `safe_work_io_unsupported`), the failed entry, operation and errno name when known, the folder's entry count, logical bytes and completeness, and a next action; the record stays closed. Every close, dry-run included, lists other leftover folders in an advisory `work_leftovers_present`: folders whose record is `closed`, `completed` or `archived`, or is not found in this checkout (it may exist on another branch). It reads only the work root's immediate children, without sizing; `wf_audit` reports their sizes in `data.work_root`. At the same point an advisory `work_root_loose_files` names the plain files and links left directly in `.wavefoundry/work/` (the count, up to 20 names with sizes from the listing, a lower bound when the listing stopped early) and says who acts: the agent that wrote one for a wave moves it into that wave's folder while the wave is open, or deletes it; any other file is left in place and reported to the operator, who decides. Close moves and deletes none of them, and a close that returns before this report, such as a blocked dry run, does not carry it; `wf_audit` reports the same entries. An advisory `work_path_cited` names each line of the record, its admitted change documents or `docs/agents/session-handoff.md` that cites this record's own `.wavefoundry/work/<key>/`, with `coverage: incomplete` naming any input it could not read: copy unique proof to durable evidence before the folder is cleaned up. A permission failure is reported as an errno; close does not diagnose its cause, such as an access control list. On a host without descriptor-relative deletion (native Windows) close preserves the folder with `safe_work_io_unsupported`; after review, remove it by hand. Close writes no cleanup note into the closed record or the handoff: the folder itself is the durable state, and later closes, `wf_audit` and the upgrade report rediscover it.
- To reclaim one retained or leftover folder through the framework, preview it with `wf_cleanup_work(work_key='<key>')` and show the preview to the operator. Call it with `mode='apply'` and the preview's `confirmation` only when the operator directs cleanup of that key in the current request. The token binds the repository, the key, the folder's device and inode, the owner file's hash and the record state, not the folder's contents: apply removes whatever the folder holds at that moment, and a device number that changes after a reboot or remount makes the token stale (`preview_stale`; preview again). Apply needs no owner file; it refuses live, ambiguous and unreadable keys, an unsafe `.owner.json` (`unsafe_owner_entry`) and a folder on another file system (`work_filesystem_changed`), but cannot detect a bind mount on the same device. Stop anything writing to the folder first. A failure part-way returns `partially_removed` with the removed count, the failing entry, operation and errno; nothing is restored and no permission is changed, so repair the cause, then preview and apply again. Native Windows previews without a token and refuses apply with `safe_work_io_unsupported`; removing the folder there is the operator's own action.
- Give every extra file in the wave folder a disposition before the final docs validation and the close write. Run `wf_close_wave(mode='dry_run')` and read its advisory `record_extras_present`. It lists each entry in the folder other than `wave.md`, the admitted specs and `events.jsonl`, at any depth and including hidden files: its path relative to the folder, its size and its citation state, largest first, up to 50 files with the total count and the number not listed, plus totals per top-level directory. Citation state is `cited_in_ledger` when `events.jsonl` contains the file's relative path (or the folder's repository-relative path followed by it), `cited_in_record` when only `wave.md` or an admitted spec does, and `not_cited` otherwise. The booleans `name_in_ledger`, `name_in_record`, `directory_in_ledger` and `directory_in_record` say whether the file name, alone or as the tail of another path, or a containing directory followed by `/`, still appears in those texts; such a loose mention never makes a file cited. `events.jsonl` is matched against the decoded string values of its lines, so a JSON escape does not hide a path. Paths are compared exactly as written, in forward-slash form, on every platform: a citation written with backslashes or in another letter case reads as `not_cited`. The report appears whenever the folder holds extras or its coverage is incomplete, on the dry run and on the close write's own response, blocked or not; it never removes, moves or blocks anything. The report lists at most 50 files, so list the folder yourself and review every extra, including the files the report does not list, and give each one a disposition under the same rules. When `complete` is false, likewise review the folder by hand. A file the report does not list has no citation state or flags from the tool, so judge it yourself: search `events.jsonl`, `wave.md` and the admitted specs for its path, its name and its containing directories, apply the same keep rules to what you find, and keep the file unless you establish that nothing refers to it. Give each extra one of three dispositions:
  - **Keep**: the file stays, and one line in `## Review Checkpoints` names it (or its group) and says why it is kept. When a file is kept only because of a loose mention, that line cites it by path, so later closes read it as cited.
  - **Summarize, then remove**: write the conclusion, the command that reproduces it, the source identity and the limits into `## Review Checkpoints` or a spec's Progress Log, then remove the file.
  - **Remove**: remove the file with no summary, because it adds nothing that the record, the tests or Git history do not already hold. Before removing a `not_cited` file whose four booleans are all false, search `events.jsonl` for the file's name stem (the name without its extension, and without any leading prefix that a copy of the file may have dropped) and search the folder's other extras for its name; a match means the file is referenced, so keep it.
- These rules decide the disposition:
  - Always keep a `cited_in_ledger` file, because the ledger is never rewritten.
  - Keep a `cited_in_record` file, or rewrite its citation in the same edit that removes it. When the citation sits in a spec section other than the Progress Log, keep the file: rewriting that citation changes the review-policy digest, and Close then blocks with `review_policy_receipt_stale`.
  - Keep a `not_cited` file whose `name_in_ledger`, `name_in_record` or `directory_in_ledger` is true, unless you establish that the text refers to a different file and say so in the record.
  - When ownership, uniqueness or use is uncertain, keep the file and say why.
  - Write summaries and rewritten citations only into `## Review Checkpoints` or a spec's Progress Log, never into another spec section. A summary in a Progress Log contains no line that starts with `## `, because such a line ends the region the digest excludes.
  - Before removing a file, check the kept extras for references to it; a kept manifest that lists a removed file is otherwise left pointing at nothing.
  - Every removal meets the manual-removal conditions above: only files established as belonging to this wave, verified redundant or summarized, with no live references, removed with contained I/O and an identity check. Dates and file names are not proof of ownership. Remove nothing from another wave's folder.
  - Removal is your edit, visible in the diff the operator reviews; the tool removes nothing.
  - Read `record_extras_present` again on the close write's response: a file added after the dry run appears only there.
- What is worth keeping in a wave folder:
  - Keep by default: `wave.md`, the admitted specs and `events.jsonl`.
  - Worth keeping: proof that cannot be reproduced from a recorded command, the tests and Git history. Examples: a baseline taken from a working tree that no longer exists; a measurement from a machine, data set or model that cannot be rerun; input received from outside the repository, such as a field report; a reproducer that is not suited to be a maintained test.
  - Summarize and remove: output whose conclusion fits in a few lines and whose command is recorded. Examples: green test logs, probe captures, census dumps, per-reviewer reports, and intermediate drafts of a result that the record states.
  - Remove: copies of files that exist elsewhere in the repository, generated output that a recorded command rebuilds, and scratch.
  - Cite a kept file by its path, not only by its directory. A large kept file needs a stated reason in proportion to its size.
- Group movable supporting files under `evidence/` when useful; no fixed layout is required. Keep ledger-cited paths stable. Update mutable links and reproduction commands after any move, and verify they resolve and remain usable. Leave other waves and unrelated files untouched.
- Consolidate repeated status notes into the final outcome and an evidence index in wave.md; do not erase historical review conclusions. Record the cleanup disposition and retained exceptions there, then run the existing docs gate. No separate cleanup report or new validator is required.

## What Goes in Wave Summary

Before closure, explicitly author one concise `Intent outcome:` paragraph in the existing exact `## Review Checkpoints` section: state achieved, partial or not established, cite evidence, and retain material limitations. When the plan states a measure of success, cite it and say whether it can be read yet. It may cover changes sharing an outcome. The close-summary composer carries the last such paragraph or list item (optionally dated `YYYY-MM-DD: `) into Wave Summary, preserving its text and qualification; do not infer achievement from titles or checked ACs. Legacy records without this assessment remain closable under existing gates and retain their existing summary behavior; this adds no schema or blocking gate. When the current `council-delivery` approval records `intent_fit: does_not`, Review and Close report the `delivery_intent_not_established` advisory; it does not block, and the operator's sign-off accepts that outcome.

`## Wave Summary` is populated at closure. Include:
- What was delivered
- What was deferred (with rationale)
- Key decisions made during the wave
- Lessons promoted to memory records or canonical docs

## Wavefoundry-Specific Closure Checks

- Do not close with an unreconciled `tree_moved_under_review` finding: a lane that saw the tree change under it holds evidence for an earlier tree (seed 190).
- Advisory docs-lint findings (`WARNING:` lines from sensors registered `advisory` in `wave_lint_lib/constants.py`, surfaced by `wf_close_wave` as `docs_lint_warning` diagnostics with `advisory: true`) are review notes at close, never a closure blocker; a flip to blocking is a recorded change decided at the release checklist (seed 190).
- If framework scripts changed: confirm `python3 .wavefoundry/framework/scripts/run_tests.py` passes
- If `docs/prompts/` or manifest changed: confirm docs gate passes (**`wf_validate_docs`** over MCP, or **`wf docs-lint`** if MCP is unavailable)
- If seed prompts changed: confirm guard-overrides reset to `false`
- Check that each receipt-required Council signoff is current for its phase (typed approval events in the wave's `events.jsonl` on declared waves, projected into `## Review Evidence`; prose lines count only on legacy waves)

## Agent Memory Validation Checkpoint

Before closure, inspect `memory_propose(wave_id, mode='dry_run')`. Review concrete future action and canonical overlap before selecting source-event IDs with `memory_propose(wave_id, mode='create', source_events=[...])`. Omitted selection creates nothing and empty selection is a no-op. Keep the retrospective and any no-new-memory rationale inline in wave.md; do not create a per-repair rejection file for an unselected proposal. Review every actual wave-linked pending selected candidate, including when its target disappears or its source is no longer draft-eligible. Use `memory_validate` for evidence-derived records; review manually selected candidates through the existing `memory_reconcile` status transition to active or rejected:

- Follow the linked evidence and inspect the current target.
- State what changes the next action.
- Check durability, canonical overlap, target accuracy, existing
  duplicates/contradictions, and confidence.
- Choose **promote**, **retain**, **reject**, or **rewrite**.

This is a bounded focused curation pass, not a new council. A wave may correctly
yield no memories. A pending candidate blocks close; rejected and superseded
source-event dispositions persist and prevent regeneration. History is preserved
through supersession, never deletion, and contradictions are never auto-resolved.

Physical archival is an explicit retention decision after reconciliation, not
automatic age cleanup. Only `stale`, `superseded`, or `rejected` records are
eligible through
`memory_reconcile(status='archived', archive_reason=...)`. Decisions, operator
preferences, and fragile-file records require a current evidence check before
setting `eligibility_confirmed=true`. Archival renames the canonical body and
leaves a compact active pointer; it does not delete history.

<!-- wavefoundry:review-policy:begin -->
## Review-policy closure

Close Wave consumes the same shared delivery evaluator and current
`wave_review.delivery_mode`; it performs closure-only delta checks and does not
recompute a parallel review policy.
<!-- wavefoundry:review-policy:end -->

## Distribution upgrade preview

Declared compatible Prepare/close overrides may opt in through `EXTENSION_UPGRADE_PREVIEW_TOOLS`. Only supported dry-run modes run during a compatible retained upgrade with current loaded core, launcher, declaration, module and helper provenance. `mcp.upgrade_preview_active()` exposes the inherited no-publication context, including through `core_handler`. Framework publication APIs refuse writes; trusted extension code is responsible for direct I/O. This preview grants no mutation or recovery authority.

## Disposable work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/`, keyed by the resolved unique prefix, for shared temporary work; include the path and availability notices in coordinator briefs. Follow seed 180’s **Disposable work** and seed 209’s **Review Artifact Discipline**. Reads and dry-runs create nothing; unavailable work is advisory and existing host permissions apply. Before finalizing evidence, preserve unique long-term proof in maintained wave records, tests or explicitly retained evidence; new durable approvals must not rely solely on disposable paths. Only successful operator-authorized whole-wave closure attempts owned cleanup after its transition. Failure is advisory; unsupported safe deletion preserves files. Dry-run, failed close and single-change close preserve work. Authorized repeated close may retry; stale cleanup cannot remove a reopened generation. Ordinary wave-folder evidence is protected. Close reports, and never deletes, what it leaves: advisory `work_retained` when this record's folder stays (path, outcome `preserved` or `partially_removed`, reason, failed entry and errno, size and completeness, next action), `work_leftovers_present` for other folders of closed, archived or not-found records, `work_root_loose_files` for files and links left directly in the work root, and `work_path_cited` for maintained lines that cite this record's own work folder; `wf_audit` sizes the leftovers in `data.work_root`. To reclaim one such folder, preview `wf_cleanup_work(work_key='<key>')`, show the preview to the operator and call `mode='apply'` with its `confirmation` only when the operator directs cleanup of that key in the current request; native Windows previews and refuses apply.

Write every file you create for a wave, including coordinator briefs, logs, captured test output and build output, inside that wave's own work folder, in a child folder when that helps; never write a file directly in `.wavefoundry/work/`. Before the wave exists, keep the content in task context until a lifecycle call reports the work area. `wf_audit` and close report files and links left directly in the work root as the advisory `work_root_loose_files`. If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it. Leave any other loose file in place, including one you are not sure you wrote (a name that starts with a wave id does not prove who wrote it), and report it to the operator, who decides. Never move a file you did not write into a wave's folder: close removes that folder with everything in it.
