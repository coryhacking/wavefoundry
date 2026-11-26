# Review Memories

Owner: Engineering
Status: active
Last verified: 2026-11-25

Shortcut: **`Review memories`**
Alias: **`Memory review`**

Use this maintenance workflow when the operator asks to review, consolidate, archive,
or purge repository memory. Invocation is apply-oriented: it authorizes the reviewed,
eligible memory mutations below, including irreversible purge. If the operator explicitly
asks for a read-only review, use the separate read-only procedure and make no mutation.

## Safety boundaries

- Review meaning and current evidence; never retire a record because of age alone. The
  audit order selects a record for review and never decides its outcome.
- Treat the active-memory budget as a curation signal, not a deletion quota. Do not merge
  unrelated records or remove useful knowledge merely to reach the cap.
- Decisions, operator preferences, and fragile-file records are protected kinds. Supply
  `eligibility_confirmed=true` only after current review proves that protected knowledge is
  no longer operational.
- Leave unresolved judgment calls unchanged and report them.
- Archive only memories that remain important to project history. Git remains the recovery
  record for everything else, so purge reviewed retired records that are not history-worthy.
  The exception: records the active-record audit retires are archived in the same run, never
  purged in it, so a later review gives them a second look before any purge.

## Capture during ordinary wave close

Review `memory_propose(wave_id, mode="dry_run")` before creating a file. Select only sources that change a future action and supplement canonical guidance with a real contained current target; call create with explicit `source_events`. Omitted selection creates nothing; empty selection is a no-op. Put an honest no-new-memory retrospective in wave.md. All actual wave-linked pending candidates still need validation, independently of current drafting eligibility. Ordinary close and upgrade do not invoke this broad maintenance workflow; historical curation is on demand.

## Apply procedure

1. Inventory before-state counts and bytes. Use `memory_brief(context="review")`, then
   `memory_search(...)` and `memory_search(include_history=true, ...)` as needed to inspect
   active, candidate, retired, and archived records. Follow cited evidence and current targets.
2. Route candidates by provenance:
   - For an evidence-derived candidate containing both `Source event:` and
     `Validation: pending`, call
     `memory_validate(memory_id=..., verdict=..., action_delta=..., rationale=...,
     evidence_verified=..., current_target_verified=..., canonical_overlap=...,
     rewrite_kind=..., rewrite_title=..., rewrite_summary=..., rewrite_evidence=...,
     rewrite_targets=..., rewrite_confidence=...)`. Supply every `rewrite_*` value only when
     `verdict="rewrite"`.
     `canonical_overlap="duplicates"` also covers a lesson the code at the target already
     shows, in a comment, docstring, assertion or the code itself, so reject it. A rewrite
     keeps its concrete anchor: at least one original target that still resolves, and the
     path, command, error string or finding it was drawn from, not condensed into a general
     lesson. When no original target still resolves, pass a single-line `retarget_reason`.
   - Never send a hand-authored or already-finalized candidate to `memory_validate`. When
     justified, disposition it with `memory_reconcile(memory_id=...,
     status="active"|"rejected")`; otherwise leave it unchanged and report it unresolved.
     Promoting a candidate to active needs no `check_note` and is not refused on an
     unresolved target. A keep of an already-active record is different: it needs a
     `check_note` and is refused on an unresolved target (step 3).
3. Audit a bounded batch of active records. List it with
   `memory_search(status="active", order="least_recently_reviewed", limit=15)`: the 15 active
   records of every kind, signal first. Each record's `revalidation_reasons` puts it in a
   group: `target_unresolved` (a target no longer resolves in the working tree) first, then
   `target_churn` (commits on a target since its last recorded check reached the threshold),
   then `target_not_canonical` alone (a target named by a bare suffix that matches one file),
   then records with no reason. Within a group the oldest `updated_at` comes first, weakest
   effective confidence first on a tie. A flag is a reason to check, not a verdict.
   Protected kinds retire only after current review proves the knowledge is no longer
   operational. Archive every record this step retires in step 6; do not purge it in this run.
   Record one outcome and a reason that names current evidence for each record:
   - **keep:** the record still changes a future action, or you cannot name the evidence another
     outcome needs. Record the check with `memory_reconcile(memory_id=..., status="active",
     check_note="<what you checked>")`. A keep needs a single-line `check_note`; without one
     it is refused with `memory_check_required`. A keep is refused with
     `memory_target_unresolved` while a target is unresolved, so rewrite or retire that record
     instead. A `target_not_canonical` record can be kept, but prefer a rewrite that names the
     full path. The check re-stamps `Updated:`, writes `Checked at:`, `Check note:` and
     `Check flags:`, and moves the record to the end of its group. It means "reviewed,
     unchanged", not a content change. Repeated runs advance through the corpus. A
     retirement below may carry a `check_note` too, which records the check the same way.
   - **retire to stale, encoded elsewhere:** name the specific assertion (test, check or code
     path) that would fail on a regression of the lesson. It must cover the lesson's whole scope,
     not only the instance the record came from; otherwise keep or rewrite. Then call
     `memory_reconcile(memory_id=..., status="stale")`.
   - **retire to stale, target gone or duplicate:** name the missing target path, or the canonical
     document and section that already carries the same action.
   - **supersede:** another active record carries the knowledge at equal or wider scope. Call
     `memory_reconcile(memory_id=..., status="superseded", superseded_by=...)`.
   - **rewrite:** the knowledge is still operational but the record is wrong or outdated. Call
     `memory_add(..., status="active", supersedes=<original id>, action_delta=...)`, keeping the
     concrete anchor as in step 2; it also marks the original superseded. Write `action_delta` as
     one line: the condition under which the lesson applies and what the next action does
     differently. Do not restate the summary or title, and write it fresh from the rewritten
     lesson rather than copying the original's line. `validation_rationale` is optional: one line
     stating the evidence checked in this review.
     Only when it reports `supersedes_target_not_updated`, finish with
     `memory_reconcile(memory_id=<original id>, status="superseded", superseded_by=<new id>)`.
     Never send an active record to `memory_validate`.
   - **unresolved:** leave the record unchanged and report it.
4. Call `memory_consolidate(mode="dry_run")`. If a related group is worth consolidating,
   apply at most one exact returned group with
   `memory_consolidate(mode="create", memory_ids=<one exact groups[].memory_ids>,
   title=..., summary=..., reviewed=true, eligibility_confirmed=..., action_delta=...)`. Write
   `action_delta` for the merged lesson, not one source: one line stating when it applies and
   what the next action does differently, written fresh rather than copied from a source record.
   `validation_rationale` is optional: one line stating the evidence checked in this review. Set
   `eligibility_confirmed=true` only after current protected-kind review. The tool does not
   expose or accept a bulk retired-record cleanup list; disposition retired records individually.
5. Consolidation creates the replacement before superseding and archiving every selected
   source. Verify the replacement through `memory_search(...)` and
   `memory_search(include_history=true, ...)`. Do not re-archive those source IDs. Retain a
   source archive only when it remains history-worthy; otherwise purge that retired source
   individually with `memory_purge(memory_id=..., reviewed=true,
   eligibility_confirmed=...)`.
6. Review retired records individually, both those retired before this run and those the
   audit retired in step 3:
   - Archive every record the audit retired in step 3 with `memory_reconcile(memory_id=...,
     status="archived", retain_for_history=true, archive_reason=..., eligibility_confirmed=...)`.
   - For a record retired before this run, keep important history with
     `memory_reconcile(memory_id=..., status="archived", retain_for_history=true,
     archive_reason=..., eligibility_confirmed=...)`.
   - For a record retired before this run, remove unimportant history with
     `memory_purge(memory_id=..., reviewed=true, eligibility_confirmed=...)`.
   Protected kinds receive `eligibility_confirmed=true` only after the current review.
7. Verify the final live and historical corpus with `memory_search(...)` and
   `memory_search(include_history=true, ...)`, then run `wf_validate_docs()`.
8. Run `index_build(content="docs", mode="update")`. If it reports `up_to_date=true`,
   continue. Otherwise poll `index_build_status(layer="project")` until `lock.held=false`,
   `lock.ended_at` records clean completion, and either `state="finished"` or
   `state="idle"` with `epoch.status="complete"` and `epoch.interrupted=false`. If the
   build fails, is interrupted, or never reaches one of those clean terminal forms,
   stop and report it; do not evaluate memory against a stale or partial index.
9. After clean index completion, run `index_health()` and `wf_memory_eval()`, then report.

## Read-only procedure

When the operator explicitly requests read-only review, use only:

- `memory_brief(context="review")`
- `memory_search(...)` and `memory_search(include_history=true, ...)`
- `memory_search(status="active", order="least_recently_reviewed", limit=15)` for the audit
  walk: report the batch, each record's `revalidation_reasons`, and each proposed outcome with
  its reason. A proposed keep needs a `check_note` and cannot apply to a record with
  `target_unresolved`; a candidate promotion needs neither.
- `memory_consolidate(mode="dry_run")`
- `wf_memory_eval()`

Do not call `memory_validate`, consolidation create, `memory_reconcile`, `memory_add`,
`memory_purge`, any docs mutation, or any index mutation in the read-only procedure.

## Report

Keep the result compact and include:

- before/after counts by status, disposition counts, and active count versus budget;
- unresolved records left unchanged;
- active-record audit counts: audited, kept, retired, superseded, rewritten and unresolved,
  plus each retired or superseded record with its reason, protected kinds listed separately;
- live-corpus bytes before/after: UTF-8 byte sizes of lint-valid record bodies directly
  under `docs/agents/memory/`, excluding `README.md` and `archive/`;
- estimated removed tokens as `ceil(max(before_bytes - after_bytes, 0) / 4)`, clearly
  labeled as an estimate;
- archive-body file count and total UTF-8 bytes under `docs/agents/memory/archive/`, plus
  `docs/agents/memory-archive.md` bytes reported separately; and
- final docs validation, index health, and memory-evaluation results when available.

Do not record model names.
