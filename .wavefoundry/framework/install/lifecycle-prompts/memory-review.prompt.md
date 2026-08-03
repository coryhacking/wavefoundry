# Review Memories

Owner: Engineering
Status: active
Last verified: 2026-08-02

Shortcut: **`Review memories`**
Alias: **`Memory review`**

Use this maintenance workflow when the operator asks to review, consolidate, archive,
or purge repository memory. Invocation is apply-oriented: it authorizes the reviewed,
eligible memory mutations below, including irreversible purge. If the operator explicitly
asks for a read-only review, use the separate read-only procedure and make no mutation.

## Safety boundaries

- Review meaning and current evidence; never retire a record because of age alone.
- Treat the active-memory budget as a curation signal, not a deletion quota. Do not merge
  unrelated records or remove useful knowledge merely to reach the cap.
- Decisions, operator preferences, and fragile-file records are protected kinds. Supply
  `eligibility_confirmed=true` only after current review proves that protected knowledge is
  no longer operational.
- Leave unresolved judgment calls unchanged and report them.
- Archive only memories that remain important to project history. Git remains the recovery
  record for everything else, so purge reviewed retired records that are not history-worthy.

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
   - Never send a hand-authored or already-finalized candidate to `memory_validate`. When
     justified, disposition it with `memory_reconcile(memory_id=...,
     status="active"|"rejected")`; otherwise leave it unchanged and report it unresolved.
3. Call `memory_consolidate(mode="dry_run")`. If a related group is worth consolidating,
   apply at most one exact returned group with
   `memory_consolidate(mode="create", memory_ids=<one exact groups[].memory_ids>,
   title=..., summary=..., reviewed=true, eligibility_confirmed=...)`. Set
   `eligibility_confirmed=true` only after current protected-kind review. The tool does not
   expose or accept a bulk retired-record cleanup list; disposition retired records individually.
4. Consolidation creates the replacement before superseding and archiving every selected
   source. Verify the replacement through `memory_search(...)` and
   `memory_search(include_history=true, ...)`. Do not re-archive those source IDs. Retain a
   source archive only when it remains history-worthy; otherwise purge that retired source
   individually with `memory_purge(memory_id=..., reviewed=true,
   eligibility_confirmed=...)`.
5. Review other pre-existing retired records individually:
   - Keep important history with `memory_reconcile(memory_id=..., status="archived",
     retain_for_history=true, archive_reason=..., eligibility_confirmed=...)`.
   - Remove unimportant history with `memory_purge(memory_id=..., reviewed=true,
     eligibility_confirmed=...)`.
   Protected kinds receive `eligibility_confirmed=true` only after the current review.
6. Verify the final live and historical corpus with `memory_search(...)` and
   `memory_search(include_history=true, ...)`, then run `wf_validate_docs()`.
7. Run `index_build(content="docs", mode="update")`. If it reports `up_to_date=true`,
   continue. Otherwise poll `index_build_status(layer="project")` until `lock.held=false`,
   `lock.ended_at` records clean completion, and either `state="finished"` or
   `state="idle"` with `epoch.status="complete"` and `epoch.interrupted=false`. If the
   build fails, is interrupted, or never reaches one of those clean terminal forms,
   stop and report it; do not evaluate memory against a stale or partial index.
8. After clean index completion, run `index_health()` and `wf_memory_eval()`, then report.

## Read-only procedure

When the operator explicitly requests read-only review, use only:

- `memory_brief(context="review")`
- `memory_search(...)` and `memory_search(include_history=true, ...)`
- `memory_consolidate(mode="dry_run")`
- `wf_memory_eval()`

Do not call `memory_validate`, consolidation create, `memory_reconcile`, `memory_purge`,
any docs mutation, or any index mutation in the read-only procedure.

## Report

Keep the result compact and include:

- before/after counts by status, disposition counts, and active count versus budget;
- unresolved records left unchanged;
- live-corpus bytes before/after: UTF-8 byte sizes of lint-valid record bodies directly
  under `docs/agents/memory/`, excluding `README.md` and `archive/`;
- estimated removed tokens as `ceil(max(before_bytes - after_bytes, 0) / 4)`, clearly
  labeled as an estimate;
- archive-body file count and total UTF-8 bytes under `docs/agents/memory/archive/`, plus
  `docs/agents/memory-archive.md` bytes reported separately; and
- final docs validation, index health, and memory-evaluation results when available.

Do not record model names.
