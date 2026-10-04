# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zqe4 reload-tool-path-free`
Title: Reload Tool Path Free

## Objective

When this wave closes, no exception-derived text in a `wf_reload_mcp` response, or in the reload diagnostics `wf_upgrade` forwards, carries an absolute path. Wave `1zoju` closed that leak for every synchronous tool but left the coroutine reload tool and its handled diagnostics as a recorded follow-up. When this wave closes, one ordinary `wf setup` also repairs a Python minor-version change without writing a spurious storage migration receipt, and recovers a repository already holding that stuck receipt. Rendered hooks no longer exit 2 on a mismatched tool venv: edit gates keep their verdicts and `Stop` hooks exit 0.

## Changes

Change ID: `1zqe3-bug reload-tool-exception-text-is-path-free`
Change Status: `implemented`

Change ID: `1zrag-bug setup-repairs-python-upgrade-and-stuck-migration`
Change Status: `implemented`

Change ID: `1zrah-bug old-runner-stale-vocabulary-profile-at-lifecycle-policy`
Change Status: `implemented`

Change ID: `1zrai-bug python-3-14-suite-compatibility`
Change Status: `implemented`

## Participants

- Coordinator: Engineering (coordinating agent)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-04

## Wave Summary

Wave `1zqe4` (Reload Tool Path Free) delivered 4 changes: Reload Tool Exception Text Is Path-Free, Setup repairs a Python minor-version change, a stuck storage migration receipt and exiting hooks, An upgrade from 1.28.0 crashes at the lifecycle-ID policy phase on a stale vocabulary profile, and Python 3.14 Suite Compatibility: Dead Lance Import, Faulthandler C Stack, And Pathlib Predicates That No Longer Raise. Notable adjustments during implementation: Reload Tool Exception Text Is Path-Free: Implemented. `_wrap_unhandled_tool_exceptions` gains an `async` wrapper for coroutine functions (same envelope, `_wf_rendered`, shared alias wrapper, `Exception` only); `build_server` re-applies `_RENDER_PASS` through `server_impl.mcp_tool_registry` after normalizing `wf_reload_mcp`, guarded by `getattr`, with no new import; a new runner helper `_reload_exception_text(exc, context, root=None)` renders path-free over `root` or `_root`, falls back to `_cause_label` then the class name (a `None` root goes straight to `_cause_label`), writes the original text to stderr and never raises; used at all eight Requirement 6 sites and the three `_record_runner_identity` reason branches. `upgrade_handlers._reload_live_runner(resp, root=None)` renders `mcp_reload_skipped` the same way and `wf_upgrade_response` passes `root`. Spec paragraph and CHANGELOG entry updated. Census of `_record_runner_identity` callers (predicate: every call in a non-test module under `.wavefoundry/framework/scripts/`, `code_keyword` `limit=0`): exactly two, `build_server` and `perform_mcp_reload` in `server.py`. Census of exception-text interpolations (`{exc}`, `str(exc)`, `limit=0`) in `perform_mcp_reload`, `_refresh_mcp_tool_surface` and the `wf_reload_mcp` body: none remain; the remaining `server.py` hits are the helper's own stderr line and startup or `--dry-run` stderr messages (out of scope); in `upgrade_handlers.py` the `mcp_reload_skipped` stderr line plus `spawn_failed` and two `status_error` sites outside the reload. Gapfill: one shell `grep` over `server.py` for `exc!r`, `repr(exc`, `{e}` and the function line ranges, because `code_keyword` returns no enclosing function and its full result exceeded the response limit; it found nothing more; Setup repairs a Python minor-version change, a stuck storage migration receipt and exiting hooks: DEL-F4 verified on that 1.28.0 fixture with a stale venv (`pyvenv.cfg` 3.13 under system `python3` 3.14.8) over the stuck receipt. 1.28.0 `wf setup` refuses (rc 1, `storage_receipt_supersedes_invalid`). `setup_index.py --root . --deps-only` exists in 1.28.0 (`setup_requirements.parse_args`) but over the stale venv exits 2 with the version message: traced to `setup_index.main` importing `model_bundle`, then `index_compatibility`, then `sqlite_runtime` (import-time activation). With the stale venv renamed aside, the same command under an audit hook on `open` rebuilt a 3.14 venv (rc 0), opened the receipt zero times and loaded no `sqlite_storage_migration` or `setup_reconciliation`; receipt and checkpoint SHA-256 unchanged; the plain command (no wrapper) also ran with rc 0. The Python schema probe printed `8`. The restore-the-parent remedy then let 1.28.0 `wf setup` finish with rc 0 (`complete` `already_current`, checkpoint removed). Requirement 7 and the CHANGELOG now say to rename the venv aside first.; Setup repairs a Python minor-version change, a stuck storage migration receipt and exiting hooks: AC-14 executed, outcome: the release-notes branch. Scratch repo `ac14/repo` received the 1.28.0 pack (`~/.wavefoundry/dist/wavefoundry-1.28.0.ptiz.zip`, read only), with `HOME`, `FASTEMBED_CACHE_PATH` and `WAVEFOUNDRY_TOOL_VENV` all under the scratch directory. A fresh 1.28.0 setup writes no receipt, so 1.28.0 code produced the parent itself: (1) `setup_wavefoundry.py` with venv-a, then rerun (rc 0, schema-8 index, no receipt); (2) venv-b absent: the stale binding wrote a pre-staging kind record, rc 3; (3) venv-b `--confirm-hosts-stopped`: the record completed as `already_current`; (4) venv-c absent: rc 1, `ERROR: storage_receipt_supersedes_invalid`. The stuck receipt matches the field file on version 2, kind, `restart_required`, `index_database_rename`, `source_database` `current`, `entry_path` `setup`, no `work_dir`, no pack and source equal to target version, and its parent is a complete version-2 kind record. The field parent also had a version-1 grandparent, which this one lacks. The checkpoint `storage_migration_id` equals the parent id. The fixed pack `wavefoundry-1.28.1.pudq.zip` was built with `build_pack.py --version 1.28.1 --output ac14/dist --skip-docs-gate --skip-manifest-update` from a scratch snapshot of this working tree (`git ls-files -co --exclude-standard`; scratch CHANGELOG heading renamed), because `build_pack` stamps VERSION in its own tree. Then `./.wavefoundry/bin/wf upgrade --pack .../wavefoundry-1.28.1.pudq.zip --yes` with venv-c exited 1. The traceback is in the INSTALLED 1.28.0 `upgrade_wavefoundry.main` (line 5024, its pre-extraction `sqlite_storage_migration.read_receipt` setup-ownership check). VERSION was still `1.28.0+ptiz` and the receipt was byte-identical, so the refusal comes from the installed code before the new pack runs. The CHANGELOG therefore tells operators to apply the restore-the-parent remedy before upgrading. Remedy executed: all six conditions checked true, the receipt was rewritten as its `supersedes`, and 1.28.0 `wf setup` ran with rc 0 (receipt v2 `complete` `already_current`, checkpoint removed). The upgrade to 1.28.1 then got past storage and extraction and failed in `lifecycle_policy_materialization` with `AttributeError: module 'vocabulary_profile' has no attribute 'CHANGE_KINDS'`: the old process has the 1.28.0 `vocabulary_profile` cached, and the new `lifecycle_id.py` needs the attribute (unreleased 1zimf). That is a separate defect, not 1zrag. A rerun passed that phase and stopped only at the docs gate, because the fixture never had an agent-driven install. Direct recovery: copy `repo-direct` was reproduced to the same stuck shape with 1.28.0 (venv-d, venv-e), its framework replaced by the fixed pack's payload framework, and ordinary `setup_wavefoundry.py` with venv-e ran with rc 0. The same migration id is now `complete` `already_current` `reclaimed_bytes` 0, the parent is verbatim, `installed_framework_sha256` is rebound, the checkpoint is gone, and the `index.sqlite` inode (776926163) is unchanged..

**Changes delivered:**

- **Reload Tool Exception Text Is Path-Free** (`1zqe3-bug reload-tool-exception-text-is-path-free`) — 12 ACs completed. Key decisions: Extend `_wrap_unhandled_tool_exceptions` with a coroutine branch and have `build_server` re-apply `_RENDER_PASS` after registering `wf_reload_mcp`; Operator decision: keep the default class prefix of `path_free_exception_text` for every handled reload diagnostic, including `reload_failed`
- **Setup repairs a Python minor-version change, a stuck storage migration receipt and exiting hooks** (`1zrag-bug setup-repairs-python-upgrade-and-stuck-migration`) — 15 ACs completed. Key decisions: Delivery-review alternative adopted (operator-reversible): when the stuck record's `supersedes` is a complete version-2 kind record, the automatic recovery restores that parent verbatim, after the same qualified probe returns `8` and after binding the setup checkpoint to the parent. Close-in-place stays only for a version-1 parent (N6) or no parent. This supersedes the "as the automatic recovery: rejected" half of the council-alternative row below.; Requirement 7 venv branch: when only the venv condition fails, rename the stale venv aside and run `setup_index.py --root . --deps-only`; when any other condition fails, keep everything and report the receipt.
- **An upgrade from 1.28.0 crashes at the lifecycle-ID policy phase on a stale vocabulary profile** (`1zrah-bug old-runner-stale-vocabulary-profile-at-lifecycle-policy`) — 10 ACs completed. Key decisions: Refresh the record-layout leaves in place in the pack-loaded `post_extract` hook.; Do not refresh `mcp_tool_extensions`.
- **Python 3.14 Suite Compatibility: Dead Lance Import, Faulthandler C Stack, And Pathlib Predicates That No Longer Raise** (`1zrai-bug python-3-14-suite-compatibility`) — 17 ACs completed. Key decisions: Disable the faulthandler C stack on 3.14 rather than widen the tail.; Treat failure 3 as a product defect and fix the guard.
## Watchpoints

- Watchpoint: `server.py` is runner code, so a consuming host loads the runner part of this change only after a restart (`runner_stale` reports it); until then the first reload of the new `server_impl` renders the survivor tool through the coroutine branch.
- No retrieval receipt pair is owed: the change adds no retrieval, ranking or index behaviour.
- Edits to `wf_server/server_impl.py`, `server.py` and `wf_server/upgrade_handlers.py` need `framework_edit_allowed`; run suites in a scratch copy.
- `1zrag` edits `venv_bootstrap.py`, one of the two runner files `compute_runner_identity` hashes, so every running MCP host reports `runner_stale` until restarted. Its `sqlite_*` module edits stay at launch version across a reload (`loaded_code_stale`), so a host on old code must be restarted after the chained receipt is written.
- `1zrag` hook fixes land in `render_platform_surfaces`; the rendered hooks under `.claude/hooks/`, `.cursor/hooks/`, `.github/hooks/` and `.windsurf/hooks/` are regenerated with `wf_sync_surfaces` (CLI fallback `wf render-surfaces`), never hand-edited.
- `1zrag` edits to `venv_bootstrap.py`, `sqlite_storage_migration.py`, `setup_reconciliation.py` and `render_platform_surfaces.py` need `framework_edit_allowed`; a seed edit, not expected, needs `seed_edit_allowed`.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-F1 | do_now | no | completed | — |
| DEL-F2 | do_now | no | completed | — |
| DEL-F3 | do_now | no | completed | — |
| DEL-F4 | do_now | no | completed | — |
| DEL-F5 | do_now | no | completed | — |
| DEL-F6 | do_now | no | completed | — |
| DEL-F7 | maybe_later | no | pending | — |
| DEL-F8 | do_now | no | completed | — |
| DEL-F9 | do_now | no | completed | — |

*Machine review state — 9 findings; current: do_now 8, maybe_later 1, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the same reload exception also reached the wf_upgrade client through mcp_reload_skipped as raw exception text, outside the planned wf_reload_mcp scope; resolved by adding that diagnostic to the path-free set; strongest-alternative: render path-free at the source inside perform_mcp_reload, not adopted because the render pass also covers hosts on the old runner after their first reload)
- Prepare council seat evidence (2026-10-04): one independent reviewer ran both seats and the code, qa and docs-contract lanes against c805b3c0 with a patched scratch probe through build_server, FastMCP Tool.run and a real perform_mcp_reload; all approved; amendments F1 (mcp_reload_skipped), F2 (torn-tree guard), F3 (fallback without a root), F4 to F6 (wording and wave record) applied.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 172 | 4,831,845 |
| implement | 165 | 3,167,539 |
| review | 57 | 983,655 |
| **Total** | **394** | **8,983,039** |

<!-- wave:context-efficiency-state {"generation":384,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":165,"content_source_credit":3307396,"derived_artifact_credit":2692,"direct_net":3167539,"estimated_tokens_saved":3167539,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10355,"response_debit":144336,"source_credit_count":100,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12142},"plan":{"calls":172,"content_source_credit":4937428,"derived_artifact_credit":55176,"direct_net":4831845,"estimated_tokens_saved":4831845,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10613,"response_debit":153955,"source_credit_count":186,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":57,"content_source_credit":1137676,"derived_artifact_credit":5360,"direct_net":983655,"estimated_tokens_saved":983655,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17919,"response_debit":143778,"source_credit_count":86,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":394,"content_source_credit":9382500,"derived_artifact_credit":63228,"direct_net":8983039,"estimated_tokens_saved":8983039,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38887,"response_debit":442069,"source_credit_count":372,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18267},"wave_id":"1zqe4 reload-tool-path-free"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 14 | 0 | 12 | 5,388,765 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":5388765,"surfaced_events":14} -->
<!-- wave:exploration-avoided end -->
