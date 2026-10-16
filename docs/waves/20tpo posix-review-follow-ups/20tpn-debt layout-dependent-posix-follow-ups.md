# Layout-dependent POSIX follow-ups: link-to-root scan, overlayfs flush, symlinked surface directories

Change ID: `20tpn-debt layout-dependent-posix-follow-ups`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20tpo posix-review-follow-ups`

## Rationale

Three layout-dependent follow-ups need bounded handling. The lock scan can traverse the checkout through `docs/site -> ..`; the current guard also detects lock aliases reached that way, so skipping an already-seen root loses protection. An executed in-memory control demonstrated that loss. A stale cache rename can fail with `EXDEV`; an in-place removal fallback can leave old bytecode and then stamp the new generation, reproduced with partial removal. Surface rendering already rejects linked lexical parent components, including in-repository links; retain and document that policy.

These controls establish guard and cache protocol risks. They do not qualify a native overlayfs filesystem, reboot, Windows host or performance timing.

## Requirements

1. Detect a directory link targeting the repository root or an ancestor of an active scan top before descending and refuse the lifecycle hold with a bounded, path-safe recovery reason. Do not mark it visited and silently accept. Ordinary safe links retain existing coverage. Keep the current phase-2 entry budget, with no new global cap.
2. Do not blanket-exclude `.wavefoundry/cache`: a cache or other skipped subtree must not hide a lock alias that the existing guard detects. The root-alias case is bounded by refusal rather than by deleting scan coverage.
3. On stale-cache rename failure, including `EXDEV`, keep the process uncached and emit at most one bounded, escaped diagnostic per process. Do not remove the live cache in place, stamp the new generation or adopt stale cache reads/writes. Existing successful atomic rename behavior stays intact; disabled/read-only modes remain silent and do not mutate caches.
4. Preserve the renderer's current lexical no-link parent policy. Document its reason and recovery in current support guidance and this change; keep closed historical wave records untouched. No containment relaxation is admitted.
5. Native platform and filesystem claims require actual delivery evidence; injected or in-memory controls must be labelled accordingly. Timing work remains deferred.

## Scope

**Problem statement:** ambiguous layout handling causes expensive scans or silent cache disablement; proposed shortcuts would weaken guards.

**In scope:** `_link_scan_tops` / `_refuse_lock_links` in `lifecycle_lock.py`, cache failure reporting/configuration around `_flush_if_stale` in `bytecode_cache.py`, focused tests and current renderer support guidance.

**Out of scope:** Windows identity work owned by 20qrt; in-place cache deletion; blanket cache traversal exemption; renderer containment relaxation; native performance qualification.

## Acceptance Criteria

- [x] AC-1: A public lifecycle hold with `docs/site -> ..` or a scan-top ancestor alias refuses with a clear bounded reason before full-tree traversal; a hidden lock alias cannot become accepted. Safe-link controls still work, cache lock-alias coverage is retained, and the existing phase-2 budget is unchanged.
- [x] AC-2: Injected `EXDEV` or other failed stale-cache rename leaves caching disabled, preserves the old generation without stamping it current, and reports at most once. A partial-removal known-bad control cannot be accepted; concurrent failure and disabled/read-only controls cause no stale-cache use or mutation.
- [x] AC-3: Current support guidance and this Decision Log explicitly retain lexical linked-parent refusal, with its containment rationale and recovery; a renderer regression proves refusal. No historical wave is rewritten.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add public lifecycle fixtures for root/ancestor aliases, hidden lock aliases, safe links and unchanged scan budget.
- [x] Add bounded root/ancestor-alias refusal without losing lock scan coverage.
- [x] Test and report cache disablement after failed rename; no in-place deletion or new synchronization scheme.
- [x] Document and test the existing renderer lexical no-link policy in current guidance.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Three fixes | Implementer | Readiness | Single owner; independent files |
| Delivery review | QA, security | Three fixes | Security on item 1 (scan is a guard) and item 3 (containment) |

## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/bytecode_cache.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/native-windows-support.md`

## Affected Architecture Docs

`docs/references/native-windows-support.md` and current surface guidance where applicable: state lexical linked-parent refusal for all applicable platforms. No architecture boundary change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Self-inflicted lifecycle outage |
| AC-2 | important | Silent performance loss in containers |
| AC-3 | important | Undocumented behaviour change |
| AC-4 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Readback: the lock scan currently follows root/scan-ancestor directory links into phase 2; visited-root seeding or a blanket cache skip would remove existing lock-alias protection. Cache rename failures already disable caching but report nothing; retain that no-delete/no-stamp protocol and add one bounded escaped diagnostic. Renderer already refuses linked lexical parents; test/document existing policy only. | MCP outline/read confirmed callable against current files. Preserve 20qrs/20qrt predicate and keying repairs. Runtime model identity unknown. Public holds, hidden-cache alias known-bad control, rename faults/concurrency/disabled controls, renderer refusal and named source mutants will verify. Native filesystem/platform and final batch gates pending. |
| 2026-10-15 | Planned from the POSIX review of commits 2026-10-01 to 2026-10-15 | Items 1 and 2 confirmed at HEAD; item 3 confirmed, intent unknown |

| 2026-10-15 | Renderer recovery guidance preserves settings: replace a linked output parent with a real directory and restore contents before rendering again. This documents the existing admitted lexical no-link policy; no policy amendment. | Current support guidance and renderer regression |

| 2026-10-15 | Implemented root/scan-top-ancestor link refusal before traversal/deduplication, preserving cache lock-alias coverage and ordinary phase-2 budgets. Failed cache rename remains uncached without deletion/stamping and now reports one bounded escaped path-free diagnostic. The warning-only in-memory lock suppresses duplicate diagnostics; it does not synchronize flushes. Current support guidance explains retained renderer lexical parent refusal, redirected-write rationale and replacing the linked parent with a real directory before retry. | New test_posix_layout_guards: 10 tests green; lifecycle-link suite 45 / 0 skips green, bytecode-cache suite 67 / 0 skips green, Windows path parity 3 and Windows scan 9 green (134 total focused tests, 0 skips). Earlier root-alias fixtures for cycles and budget checks now use ordinary bounded wave/src/index links, preserving those assertions. Original source reproduced five failures in the initial eight-test fixture; renderer/cache preservation controls already passed. |
| 2026-10-15 | AC-1–AC-3 and tasks complete; AC-4 remains open for final batch docs/framework gates. Six named guard mutants detected, with original guard and partial-removal controls executed in scratch/in-memory code. | `visited-root-skip-acceptance` → `test_root_alias_never_accepts_a_hidden_lock_alias`; `root-ancestor-refusal-removed` → `test_public_scan_top_ancestor_refuses_even_if_already_visited`; `blanket-cache-scan-exclusion` → `test_cache_lock_alias_coverage_and_safe_link_budget_remain`; `partial-removal-new-generation-adoption` → `test_failed_rename_never_accepts_partial_in_place_removal`; `repeat-concurrent-warning` → `test_concurrent_failures_do_not_adopt_stamp_or_repeat_diagnostic`; `stale-cache-prefix-adoption` → `test_rename_failures_preserve_old_generation_and_report_once`. Each produced one failure with zero errors/skips. `/private/tmp/20tpn-guard-mutants.py` also confirmed the original guard refuses the hidden alias as `lock_link` and the known-bad partial-removal fallback accepts a new stamp while stale payload remains. No shipped source replacement, native overlayfs/Windows/reboot or timing qualification. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Refuse root/ancestor aliases before descent; preserve coverage elsewhere | TPO-RD4 control proved naive visited-root seeding accepts a hidden lock alias | Blanket cache skip and unconditional successful hold rejected |
| 2026-10-15 | Disable cache on rename failure and report once | TPO-RD2 partial-removal control retained stale bytecode under a new stamp | In-place deletion rejected; no new cache-lock subsystem |
| 2026-10-15 | Preserve lexical linked-parent refusal | TPO-RD5 closes the plan decision; current `write_text` explicitly requires lexical no-link ancestry to prevent redirected surface writes | Relaxation and rewriting historical decisions rejected |

## Risks

| Risk | Mitigation |
| --- | --- |
| Root-alias layouts still cannot take lifecycle holds | Explain the exact unsupported layout and safe recovery rather than scanning the whole checkout |
| Overlayfs cache remains unavailable | Explicit one-time diagnostic; safe uncached operation is the admitted outcome |
| Tests overstate native support | Separate injected fault evidence from native qualification; timing remains deferred |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
