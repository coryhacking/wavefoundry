# Upgrade Finish Guidance Repeats the Index Update and Ends With Stale Next Steps

Change ID: `1zf1t-bug upgrade-finish-guidance`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zf1u upgrade-finish-guidance

## Rationale

Field report from a clean 1.27 -> 1.28.0+pthj upgrade driven through MCP. Every phase succeeded, but four things at the end of the upgrade were wrong or unhelpful. Each was verified against the code:

1. **The index update ran twice.** The primary run (`wf_upgrade()`, phase `preflight_to_docs_gate`) already runs Phase 4, the index update, and its log says a further update is needed only after later edits. The tool's own `next_step` (`upgrade_handlers._upgrade_next_step`, phase `preflight_to_docs_gate`) then tells the agent to call `wf_upgrade(phase='update_index')` and `wf_upgrade(phase='cleanup')`, and seed 160's MCP-first paragraph says the same. Seed 160 step 4 of the operator mental model says the opposite ("the index update runs automatically as the upgrade's final phase ... a manual `update_index` is only for re-running after the agent editing pass"). `--update-index` has no freshness check, so the extra call re-runs the whole index child (about a minute). The new-code backstops that `--update-index` runs (`_ensure_lifecycle_policy_backstop`, `_ensure_rendered_permissions_backstop`) also run in the cleanup path (`phase_cleanup` and the `--cleanup` branch of `main`), so skipping the extra call loses nothing.
2. **Cleanup ends by telling the operator to run the index update and cleanup.** `_print_operator_summary`, called only from `phase_cleanup` (success path, and the failed-phase path just before `SystemExit(1)`), always ends with "Next steps for agent editing pass: ... 5. Index update: wf upgrade --update-index  6. Cleanup lock after rebuild: wf upgrade --cleanup". It is the last thing the upgrade log shows after "Upgrade lock removed", so a completed upgrade reads as unfinished.
3. **The lifecycle lock file keeps a dead PID with no sign it was released.** `.wavefoundry/lifecycle-mutation.lock` persists by design: `RuntimeFileLock.release` keeps the carrier on disk and liveness is the OS lock, never the recorded PID (`runtime_lock.probe_runtime_lock`; nothing reads the PID). But `lifecycle_lock.lifecycle_mutation_lock` writes `{pid, acquired_at}` on acquire and never updates it, so a reader sees a dead PID and cannot tell a clean release from a crash. `index-build.lock` records `ended_at` for the same reason.
4. **The extraction log counts withheld members without naming them.** `_extract_feature_members` computes the withheld set and returns only its size, so the log says "Withheld 7 ... member(s)" with no names.

Goal: the end of an upgrade says what actually remains to do. Consumer: agents and operators reading the `wf_upgrade` response and `.wavefoundry/logs/upgrade.log`. Success: one index update per normal upgrade, a log tail that reads as complete after a successful cleanup, a lock file that shows it was released, and the withheld members named.

## Requirements

1. **One index update per normal upgrade.** The `preflight_to_docs_gate` `next_step` directs the agent to the editing pass and then `wf_upgrade(phase='cleanup')`, and says to call `wf_upgrade(phase='update_index')` first only when the editing pass changed indexed files or the primary run reported the index update failed. The retired journal step is dropped from that text. Seed 160's MCP-first paragraph and its rendered twin `docs/prompts/upgrade-wavefoundry.prompt.md` say the same, consistent with the mental-model step 4. The `update_index`/`rebuild_index` and memory-pause next steps are unchanged.
2. **Cleanup's summary matches the upgrade's state.** On a successful cleanup, `_print_operator_summary` no longer lists `--update-index` or `--cleanup` as next steps. Cleanup has no signal for whether the editing pass was done, so the block always prints on success under a heading that says the upgrade is complete and the steps apply only if not done yet: drift detection, spec gaps, scan findings, docs gate re-run, and an index update only for edits to indexed files. On the failed-phase path the block is omitted, because the recovery instruction printed just before it is the next step. The structured summary (sentinel JSON) is unchanged.
3. **The lifecycle lock records its release.** On release, `lifecycle_mutation_lock` rewrites the metadata as `{pid, acquired_at, released_at}` before releasing the OS lock. A metadata write failure never masks the protected body's outcome or prevents the release. Liveness stays the OS lock; no reader starts trusting the file.
4. **Withheld members are named.** The extraction log names the withheld members (the first ten, then "and N more"), alongside the existing count. `_extract_feature_members` keeps returning the count (callers and tests depend on it); the names come from a separate helper that applies the same selection to the archive's member list.
5. **Platforms.** Behaviour is the same on Windows, macOS, Linux and WSL2. The metadata rewrite uses the existing `write_metadata` (the same byte-zero rewrite `acquire` already performs on every platform, while the OS lock is held).
6. **Transition.** Requirements 1 and 2 take effect once the new MCP server and runner are loaded: the upgrade that installs them still shows the old `next_step` (the old server builds it) and, where the old runner prints the cleanup summary, the old block. Seed 160 notes that the shorter sequence applies from servers carrying the new `next_step`. Requirement 3 applies to locks taken by new code. Requirement 4 applies from the next upgrade's extraction, which the installed runner performs. The CHANGELOG entry goes under `### Fixed` in the open `## [1.28.0]` section.

## Scope

**Problem statement:** after a successful upgrade, the guidance repeats a finished index update, the log ends with steps that were already done, the lifecycle lock looks abandoned, and withheld members are unnamed.

**In scope:**

- `wf_server/upgrade_handlers._upgrade_next_step` (primary phase text).
- `upgrade_wavefoundry._print_operator_summary` next-steps block; `_extract_feature_members` and its Phase 0b log line.
- `lifecycle_lock.lifecycle_mutation_lock` release metadata.
- Seed 160 MCP-first paragraph and the rendered prompt twin (by hand, under `seed_edit_allowed`).
- Tests; CHANGELOG.

**Out of scope:**

- A freshness short-circuit in `--update-index` (see Decision Log).
- Unlinking the lock carrier (persistence is by design).
- The index update, cleanup and backstop logic themselves.

## Acceptance Criteria

- [x] AC-1: the `preflight_to_docs_gate` `next_step` names `wf_upgrade(phase='cleanup')` as the step after the editing pass, conditions `update_index` on edits to indexed files or a failed index update, and no longer mentions journals; seed 160 and the prompt twin carry the same guidance and no longer tell the MCP path to run `update_index` unconditionally.
- [x] AC-2: a successful `phase_cleanup` run's log states the upgrade is complete, lists no `--cleanup` step, and mentions `--update-index` only as a step conditioned on edits to indexed files; the failed-phase path prints its recovery text without the editing-pass block; the sentinel summary JSON is byte-identical before and after for the same inputs.
- [x] AC-3: after `lifecycle_mutation_lock` exits (normally and when the body raises), the lock file holds `pid`, `acquired_at` and `released_at`, the body's exception propagates unchanged, and the OS lock is free; a `write_metadata` failure at release still releases the lock and does not replace the body's outcome.
- [x] AC-4: extracting a pack with withheld members logs their names (capped at ten with an "and N more" suffix) and the same count as before; the extracted file set is unchanged.
- [x] AC-5: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Rewrite the primary `next_step`; update seed 160 and the prompt twin.
- [x] Gate and reword the cleanup next-steps block; adjust the existing editing-pass tests.
- [x] Record `released_at` in the lifecycle lock.
- [x] Name withheld members in the extraction log.
- [x] Tests for AC-1 to AC-4; CHANGELOG `### Fixed` entry under 1.28.0.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance, summary, lock, extraction log | implementer | readiness | Four small edits |
| Review | code-reviewer, qa-reviewer, docs-contract-reviewer, release-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`, `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`

## Affected Architecture Docs

N/A: operator-facing guidance text, one log line and lock metadata inside existing modules; no boundary, flow or verification change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the redundant index run on every MCP upgrade |
| AC-2 | required | The log tail must not read as an unfinished upgrade |
| AC-3 | important | Diagnostic clarity only; liveness is unaffected |
| AC-4 | nice-to-have | Diagnostic detail |
| AC-5 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Post-approval review (DEL-1ZF1U-ACQUIRE-METADATA): this change had moved the acquisition-metadata construction outside the release-protected `try` (between a successful acquire and the `try`), so an interrupt there skipped `release()`; an independent-process probe saw the lock stay busy. Repaired: `metadata` starts empty before the `try` and is built inside it, so everything after a successful acquire is protected; the release stamp tolerates an empty value. Test: an interrupt from the first `time.time()` call still releases (release spy) and the body never runs. Mutant (construction back outside) caught | 22 lock tests OK |
| 2026-09-30 | Delivery review (independent, Opus): D1 blocking (DEL-1ZF1U-D1): the primary next_step claimed "This run already updated the index" on every envelope for that phase, including a dependency-provisioning failure (index not run) and an exit-2 render failure. Repaired: the text now says "A completed run already updated the index" and conditions `update_index` on edited indexed files or a publication failure in `data.summary.index_update`; seed 160 and the twin say the same and route a dependency failure to `wf setup`. Advisories taken: the release stamp is nested in `try/finally: lock.release()` so an interrupt during the stamp still releases; the failing-stamp test now spies on `release` (Q1: the in-process `_free()` probe was vacuous); CHANGELOG transition note for the withheld names; "a server without this change" replaces "older than 1.28". Declined: seed step 12's unconditional `index_build` and the line-340 shorthand wording predate this change and are outside its scope. Tests: dependency-failure envelope; interrupt during the stamp. Mutants: false claim restored, `release()` deleted, old stamp structure; all caught | 110 focused tests OK |
| 2026-09-30 | Implemented. `upgrade_handlers._upgrade_next_step` (primary phase) now goes to cleanup, `update_index` only for edits to indexed files or a failed index update, journal wording dropped. `_print_operator_summary` returns before the block on a failed phase; on success prints "Upgrade complete. Agent editing pass, if not done yet:" with steps 1 to 4 and a conditional step 5 (no `--cleanup`). `lifecycle_mutation_lock` rewrites `{pid, acquired_at, released_at}` in `finally`, best-effort, before `release()`. `_withheld_member_names` and `_describe_withheld_members` (cap 10, "and N more") feed the Phase 0b log; `_extract_feature_members` still returns the count. Seed 160 and the prompt twin: MCP-first sentence rewritten with the transition note. Tests: primary next step (server); successful and failed real `phase_cleanup`; editing-pass heading; lock stamp on normal exit, raising body and failing stamp; withheld names match the count and extraction; the real `main` extraction log names members. Sentinel JSON byte-identical to HEAD across six input combinations (scratch). Mutants: old next step, block on failure, old steps 5/6, no stamp, unguarded stamp, names missing the bootstrap, log without names, no cap; all caught (the log mutant after adding the `main` test). Gapfill: shell reads for the census and edits, because the change was small and the targets were already known from the investigation | focused tests OK (194) |
| 2026-09-30 | Readiness review (independent, fresh context): all lanes and seats APPROVE, no blocking defect. Adopted: keep `_extract_feature_members` returning an int and name members through a separate helper (tests use the count); cleanup has no "editing pass done" signal, so the block always prints on success under a complete-if-not-done heading; seed transition sentence. Confirmed: skipping `update_index` loses nothing (both backstops run in cleanup; hooks and outcome record run in the primary Phase 4, including under a pre-1.28 runner); the sentinel JSON is emitted before the block; nothing reads the lifecycle lock metadata | Readiness report |
| 2026-09-30 | Planned from a field upgrade report. Verified: `_upgrade_next_step` text; seed 160 line with unconditional `update_index` versus mental-model step 4; `--update-index` has no freshness check and runs the backstops that `phase_cleanup` and the `--cleanup` branch also run; `_print_operator_summary` is called only from `phase_cleanup` and ends with the steps block; `RuntimeFileLock.release` keeps the carrier and nothing reads the lifecycle lock PID; `_extract_feature_members` returns only a count | Code reads; field log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Fix the guidance; do not add a freshness short-circuit to `--update-index` | The redundant call comes from the instructions; a skip would need a reliable "nothing indexed changed since" test and could skip the new-code backstops that an older primary runner relies on | Early no-op when `index_rebuilt_at` is newer than every indexed file |
| 2026-09-30 | Record `released_at` rather than delete the lock file | The carrier persists by design (inode identity, Windows open-file deletion); a release stamp answers the reader's question without changing lock semantics | Unlink on release; document only |

## Risks

| Risk | Mitigation |
| --- | --- |
| An agent skips a needed index update after editing indexed files | The next step names that case explicitly; the index also refreshes incrementally after edits |
| The release metadata write fails on a locked-down filesystem | Best-effort write inside the release path; the release and the body's outcome are unaffected (AC-3) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
