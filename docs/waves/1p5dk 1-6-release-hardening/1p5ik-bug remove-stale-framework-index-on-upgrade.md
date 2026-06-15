# Remove the deprecated `.wavefoundry/framework/index/` on upgrade

Change ID: `1p5ik-bug remove-stale-framework-index-on-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-14
Wave: `1p5dk 1-6-release-hardening`

## Rationale

`.wavefoundry/framework/index/` is a **deprecated pre-1p4ww artifact**. Wave 1p4ww folded framework seeds + README into the project docs index and stopped shipping a framework index — verified: the current pack ships **zero** `framework/index/` entries; `build_pack.py:279-281` explicitly excludes it; and every read path is dead (`_index_dir_for_layer` raises for any non-`project` layer; `_graph_layer_for_index_dir` returns `"project"` unconditionally with the comment "the framework graph layer was removed"; `docs_search`/`code_search`/graph tools/dashboard all use only the project layer). Nothing reads or re-creates it.

But the directory **persists on disk after upgrade**, observed on a downstream consumer. The `WALKER_VERSION` 5→6 comment (`indexer.py:459-460`) claims "the stale shipped `framework/index/` is removed by the manifest-prune on upgrade" — that is **false**: index `.lance` artifacts were never listed in any MANIFEST, and `prune_framework.py` only deletes MANIFEST-listed files. So prune cannot remove it, and a within-1.6 upgrade (both packs post-1p4ww) never even has it in the old MANIFEST. The folder is inert dead weight that lingers indefinitely.

## Requirements

1. The upgrade flow removes `.wavefoundry/framework/index/` when present — unconditionally (a simple `is_dir()` check, not gated on MANIFEST), so it handles both the within-1.6 case (prune can't) and the pre-1p4ww case.
2. Removal happens **after the index rebuild** (in the cleanup phase), so a live index `update` running on the OLD code earlier in the upgrade can't re-create it after deletion; it is logged for operator visibility.
3. The false `WALKER_VERSION` comment is corrected to describe the real mechanism (explicit removal step, not manifest-prune).
4. No effect on the self-host (the directory doesn't exist there; `build_pack` doesn't build it) and no effect on any live code path (all framework-layer reads are already dead).

## Scope

**Problem statement:** the deprecated `.wavefoundry/framework/index/` is never cleaned up on upgrade (manifest-prune can't remove it; nothing else does), so it lingers as stale dead weight on every consumer.

**In scope:**

- `upgrade_wavefoundry.py`: an explicit `shutil.rmtree(.wavefoundry/framework/index/)` in `phase_cleanup` after the rebuild (`is_dir()`-guarded, logged).
- `indexer.py`: correct the `WALKER_VERSION` 5→6 comment.
- A test asserting the upgrade removes a pre-existing `framework/index/`.

**Out of scope:**

- Resurrecting or re-purposing the framework index layer (it's fully deprecated).
- The stale `release-flow.md` mention of "framework-index .lance files" — noted as a separate doc-drift item, not fixed here.
- The project index (`.wavefoundry/index/`) — untouched.

## Acceptance Criteria

- [x] AC-1: an upgrade over a tree containing `.wavefoundry/framework/index/` removes it (logged) via `_remove_deprecated_framework_index`, called in `phase_cleanup` AFTER the index rebuild (so a live old-code update during the upgrade can't re-create it post-deletion); asserted by `test_removes_deprecated_framework_index`. Absent → `False`, no error (`test_remove_framework_index_absent_is_noop`).
- [x] AC-2: the `WALKER_VERSION` 5→6 comment now states manifest-prune CANNOT remove `framework/index/` (its `.lance` files were never in MANIFEST) and points to the explicit upgrade-prune-phase removal. Full suite **3120 OK**; docs-lint clean.

## Tasks

- [x] Add the `is_dir()`-guarded `shutil.rmtree` + log line to the upgrade prune phase (`_remove_deprecated_framework_index`).
- [x] Correct the `WALKER_VERSION` comment in `indexer.py`.
- [x] Test: pre-existing `framework/index/` removed on upgrade; absent → no-op.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- Shares `upgrade_wavefoundry.py` with `1p5do` (same wave) — no concurrent-edit conflict.

## Affected Architecture Docs

`N/A` — removes a dead on-disk artifact; no boundary/flow/contract change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Removing the stale dead-weight directory is the fix. |
| AC-2 | required  | The false comment is what hid the bug; correcting it prevents the same wrong assumption. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-14 | Added `_remove_deprecated_framework_index(root)` (unconditional `is_dir()`-guarded `shutil.rmtree`, logged) + corrected the false `WALKER_VERSION` 5→6 comment in `indexer.py`. 2 tests. Confirmed (guru) the framework index layer is fully dead (all reads hard-reject non-`project` layer). | `upgrade_wavefoundry.py`, `indexer.py`, `test_upgrade_wavefoundry.py` |
| 2026-06-14 | **Placement corrected (operator):** moved the removal from `phase_pruning` (pre-rebuild) to `phase_cleanup` (AFTER the rebuild). A live index `update` runs on the OLD code during the upgrade and re-creates `framework/index/`; deleting in the prune phase gets undone by that update. Only after the rebuild lands on the new code (which never touches it) is removal durable. The guru's static trace missed this because it analyzed only the new code. | `upgrade_wavefoundry.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-14 | **Remove in `phase_cleanup` AFTER the index rebuild** (operator-corrected), unconditional `is_dir()` | A live index `update` runs on the OLD code during the upgrade (before the new code/reload is in effect) and RE-CREATES `framework/index/`; deleting it earlier (prune phase, pre-rebuild) gets undone by that old-code update. Only after the rebuild lands on the new code (which never touches it) is removal durable. Cleanup is also after the background code build + reload. | Prune phase pre-rebuild (REJECTED — undone by the old-code live update; the guru's static trace missed this because it analyzed only the new code); indexer full-rebuild path (fires on every rebuild, wrong responsibility) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Some unknown consumer still reads the framework layer | Verified dead: all read paths hard-reject non-`project` layer (guru trace, file:line evidence) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
