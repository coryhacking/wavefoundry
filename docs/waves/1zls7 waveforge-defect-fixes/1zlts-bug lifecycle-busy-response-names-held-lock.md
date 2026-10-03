# Lifecycle Busy Response Names the Lock Actually Held

Change ID: `1zlts-bug lifecycle-busy-response-names-held-lock`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-02
Wave: 1zls7 waveforge-defect-fixes

## Rationale

Every mutating lifecycle tool (`_LIFECYCLE_MUTATION_LOCK_TOOLS`, plus extension tools declared in `EXTENSION_LIFECYCLE_TOOLS`) is wrapped by `_wrap_lifecycle_mutation_lock` in `wf_server/server_impl.py`. When the lock cannot be taken, the wrapper returns `_lifecycle_mutation_busy_response(tool_name, str(busy))`. Waveforge reported three problems with that refusal:

1. **Garbled text with an absolute path.** The message interpolates `str(busy)`, which is `lifecycle_lock._acquire`'s own message, into a sentence that already names the lock, giving "the lifecycle-mutation.lock at lifecycle mutation lock is held: /abs/path/.wavefoundry/lifecycle-mutation.lock is held". The absolute path leaks the operator's home directory into tool output and transcripts.
2. **A lock raised by the tool body is reported as another session.** `_lifecycle_mutation_lock` wraps its `yield`, so a `LifecycleLockBusy` raised inside the tool body is converted into `LifecycleMutationBusy` too. The reachable source is a same-process re-entry (`lifecycle_lock._refuse_if_held_here`, "already held by this process", for example an extension body that takes the lifecycle lock again), reported as "Another session is running a lifecycle mutation", which is false and sends the operator looking for a session that does not exist. (A busy publication lock from `lifecycle_lock.lifecycle_publication_transaction` cannot reach a lock-wrapped body: that transaction is called only from `upgrade_wavefoundry`, `wf_upgrade` is not lock-wrapped, and the transaction takes the lifecycle lock first.)
3. **Unavailable is reported as busy.** `LifecycleLockUnavailable` ("cannot prove lifecycle mutation lock ownership", for example a filesystem without record locks) shares the busy code `lifecycle_mutation_locked` and its "retry once the other operation finishes" advice, which never helps.
4. **The publication refusal leaks absolute paths too (red-team R1).** `review_evidence.ProjectPublicationUnavailable` messages interpolate absolute lock paths (the lifecycle lock path, and `RuntimeFileLock` errors that carry the publication lock path). They reach tool output as `project_publication_busy` through `str(exc)` in `_wrap_upgrade_publication_guard` and through `lifecycle_gate_support._read_error_detail(exc)` in `wf_mark_ac` (which renders `str(exc)` for any non-`OSError`). The root-resolution branch of the lifecycle wrapper also interpolates `{exc}` into its `lifecycle_lock_unavailable` message (red-team R2).

## Requirements

1. **Only acquisition maps to the lifecycle refusal.** The wrapper distinguishes failure to acquire the lifecycle mutation lock from an exception raised by the tool body. A `LifecycleLockBusy` or `LifecycleLockUnavailable` raised while acquiring returns the lifecycle refusal (Requirements 2 and 3); the same exception types raised after acquisition, from the body, never do (Requirement 4). The lock is still released on every path, and no state is written by a refused call.
2. **Busy at acquire.** Code `lifecycle_mutation_locked` (unchanged, so existing callers keep working). The message names the lock by its repository-relative path (`.wavefoundry/lifecycle-mutation.lock`, from `LIFECYCLE_MUTATION_LOCK_REL`), says another process holds it, that nothing was changed, and to retry when that operation finishes. When the refusal at acquire carries the re-entry attribute because another thread of this server holds the lock (`_refuse_if_held_here`, owner "another thread"), the code is the same but the message says another call in this server process holds it, not another process. It contains no absolute path and does not repeat the lower-level exception text.
3. **Unavailable at acquire.** Code `lifecycle_lock_unavailable` (the code the wrapper already uses when the repository root cannot be resolved, so the provenance census in `test_lifecycle_gates.py` `test_provenance_rule_is_derived_and_documented_at_every_site` gains no new member for it). The message says the server cannot prove ownership of `.wavefoundry/lifecycle-mutation.lock` (repository-relative), names the cause class from the exception without its absolute path, and says retrying will not help until the cause (for example a filesystem without byte-range locks) is fixed. `data.busy` is not `true` for this case. The root-resolution branch's `lifecycle_lock_unavailable` message stops interpolating `{exc}` and names only the exception class (red-team R2).
4. **Lock refusals raised by the tool body name the lock held.**
   - A same-process re-entry of the lifecycle mutation lock returns a new code `lifecycle_lock_reentry` whose message says this call (or an extension it invoked) tried to take `.wavefoundry/lifecycle-mutation.lock` while this process already holds it, that no other session is involved, and that nothing further was attempted. It is not advice to retry.
   - Any other exception from the body propagates exactly as today.
4a. **Publication refusals are path-free.** Every `project_publication_busy` message built from a `ProjectPublicationUnavailable` (`_wrap_upgrade_publication_guard`, which returns `str(exc)`, and `wf_mark_ac`, which renders `_read_error_detail(exc)`) contains no absolute path: the server builds the message from repository-relative lock names (`.wavefoundry/locks/review-evidence-adoptions.lock` from `PROJECT_STATE_PUBLICATION_LOCK_REL`, `.wavefoundry/lifecycle-mutation.lock`) and the cause class, either from attributes on `ProjectPublicationUnavailable` or by making its own messages repository-relative. The implementer also checks the sibling consumer `wf_server/context_efficiency_handlers.py` (its `publication_lock_busy` result stores `str(exc)` as `error`) and records whether that field reaches a tool response; if it does, it is made path-free the same way.
5. **Structured lock identity.** `lifecycle_lock.LifecycleLockBusy` and `LifecycleLockUnavailable` carry the lock's repository-relative path and whether the refusal is a same-process re-entry as attributes, so the server builds its messages from those attributes and never parses `str(exc)`. Their `str()` text may keep the absolute path for local logs and existing tests; tool responses never include it.
6. **Census of busy-response consumers.** Tests and docs that pin today's behaviour are updated to the new contract and listed in the Progress Log. Known on 2026-10-02: `tests/test_extension_tool_modules.py` `test_an_unhandled_reentry_returns_busy_and_keeps_the_hold_until_return` and `test_the_hold_is_registered_and_reentry_is_refused_without_opening_the_file` (both expect `lifecycle_mutation_locked` for a re-entry), `tests/test_lifecycle_mutation_lock.py`, `tests/test_readiness_convergence.py` and `tests/test_lifecycle_gates.py` `test_provenance_rule_is_derived_and_documented_at_every_site` (its expected code set gains `lifecycle_lock_reentry`); docs `docs/specs/mcp-tool-surface.md` (the `lifecycle_mutation_locked` paragraph), `docs/architecture/cross-cutting-concerns.md` (the lifecycle lock paragraph) and `docs/architecture/threat-model.md` (the extension tool modules row says `lifecycle_mutation_locked` "on contention or re-entry").

## Scope

**Problem statement:** the lifecycle lock refusal leaks an absolute path, garbles its text, blames another session for a lock the call itself (or its body) hit, and treats an unprovable lock as a busy one.

**In scope:**

- `wf_server/server_impl.py`: `_lifecycle_mutation_lock`, `LifecycleMutationBusy` (or its replacement), `_lifecycle_mutation_busy_response`, and the `locked` wrapper in `_wrap_lifecycle_mutation_lock`.
- `lifecycle_lock.py`: attributes on `LifecycleLockBusy` and `LifecycleLockUnavailable` raised by `_acquire` and `_refuse_if_held_here`.
- The root-resolution branch of the wrapper (Requirement 3) and the `ProjectPublicationUnavailable` messages surfaced by `_wrap_upgrade_publication_guard` and `wf_mark_ac` (Requirement 4a), including `review_evidence.py` where the messages are built.
- Tests and docs named in Requirement 6, and the CHANGELOG (an Unreleased `### Fixed` bullet).

**Out of scope:**

- Lock semantics (non-blocking, strict, process-hold registry, release stamping) and the set of wrapped tools.
- A body-raised busy publication lock inside a lock-wrapped tool (unreachable: see Rationale 2).
- Body exceptions that are not lock refusals and surface `str(exc)` through FastMCP (red-team R3): recorded as a follow-up.
- Other locks (index build, install, dashboard).

## Acceptance Criteria

- [x] AC-1: With `.wavefoundry/lifecycle-mutation.lock` held by another process, a wrapped tool returns `lifecycle_mutation_locked`; the message names `.wavefoundry/lifecycle-mutation.lock`, does not contain the repository's absolute path (asserted against the temporary root's resolved path, on every platform), and contains the phrase "lock is held" at most once.
- [x] AC-2: With `LifecycleLockUnavailable` raised at acquire, a wrapped tool returns `lifecycle_lock_unavailable` (not `lifecycle_mutation_locked`), with `data.busy` not `true`, a message that names the repository-relative lock path and contains no absolute path.
- [x] AC-3: A wrapped tool whose body re-enters the lifecycle mutation lock in the same process returns `lifecycle_lock_reentry`, whose message says no other session is involved and contains no absolute path; the hold is released after the call and another process can then acquire the lock.
- [~] AC-4: Dropped at readiness (2026-10-02): a busy publication lock inside a lock-wrapped body is unreachable (`lifecycle_publication_transaction` is called only from `upgrade_wavefoundry`, `wf_upgrade` is not lock-wrapped, and the transaction takes the lifecycle lock first). The reachable publication leak is covered by AC-8.
- [x] AC-5: A body exception that is not a lock refusal propagates unchanged, and the lifecycle lock is released.
- [x] AC-6: The tests and docs listed in Requirement 6 describe the new contract (no doc says re-entry returns `lifecycle_mutation_locked`), and the CHANGELOG has the Unreleased bullet.
- [x] AC-8: While another process holds `lifecycle_lock.lifecycle_publication_transaction(root)` (the upgrade shape, which holds both the lifecycle and the project publication lock; holding only the lifecycle lock lets `wf_mark_ac` succeed, and holding only the publication lock makes it wait), a `wf_mark_ac` call that needs the publication lock returns `project_publication_busy` whose message and data contain no absolute path (asserted against the temporary root's resolved path); a `_wrap_upgrade_publication_guard`-wrapped tool raising `ProjectPublicationUnavailable` likewise returns a path-free `project_publication_busy`; and the root-resolution `lifecycle_lock_unavailable` message contains no `str(exc)` text. An acquire-time refusal while another thread of this server holds the lock says "another call in this server process".
- [x] AC-7: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write failing-first tests: lock held in another process, held by another thread of this server, unavailable at acquire, same-process re-entry from a tool body, a non-lock body exception, and the path-free publication and root-resolution refusals (AC-8).
- [x] Add repository-relative path and re-entry attributes to `LifecycleLockBusy` and `LifecycleLockUnavailable` in `lifecycle_lock.py`.
- [x] Restructure the wrapper so only acquisition maps to the lifecycle refusal; add the unavailable and re-entry responses; make the root-resolution message path-free.
- [x] Make the `project_publication_busy` messages in `_wrap_upgrade_publication_guard` and `wf_mark_ac` path-free; check the `context_efficiency_handlers.py` sibling.
- [x] Update the Requirement 6 tests (re-entry expectations, provenance code set) and docs; add the CHANGELOG bullet.
- [x] Run the change's suites and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| busy-response | implementer | none | server_impl.py lifecycle wrapper and publication responses, lifecycle_lock.py, review_evidence.py, tests and docs; serialize `server_impl.py` edits with `1zltv` and `1zlu0` |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/lifecycle_lock.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` (lifecycle lock paragraph) and `docs/architecture/threat-model.md` (extension tool modules row): the refusal contract gains a re-entry code and stops reporting re-entry as contention. No boundary or flow change.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The garbled, path-leaking message is the reported defect. |
| AC-2 | required | An unprovable lock must not be advised as a retry. |
| AC-3 | required | Re-entry must not blame another session. |
| AC-4 | important | Dropped at readiness: unreachable. |
| AC-8 | required | The reachable publication and root-resolution path leaks. |
| AC-5 | required | Non-lock failures and lock release must not change. |
| AC-6 | important | Docs and tests must describe the new contract. |
| AC-7 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Delivery-review repair. index_health leak: `context_efficiency_handlers._project_context_efficiency_wave` stored `str(exc)` (the absolute index-source lock path) in its `index_source_busy` and `index_source_unavailable` rows and `TypeName: text` in its generic failure row, which `index_health` surfaces under `data.background_monitors.context_efficiency_projection.failure.error`. The rows now carry `lifecycle_lock._cause_label` (exception class and errno name), the lock rows followed by `on .wavefoundry/locks/index-source-mutation.lock` from the new `index_source_guard.INDEX_SOURCE_LOCK_REL`. Tests in `test_index_source_guard.py`: `test_busy_projection_row_names_the_lock_without_an_absolute_path` (the guard held in a child process) and `test_unavailable_and_failed_projection_rows_are_path_free` (raw path, JSON-escaped and backslash forms all absent); failing-first `scratchpad/1zls7-repair-others/failing-first-ce-leak.txt`. CHANGELOG: the 1zimc `Fixed` bullet now says a re-entry from another thread gets the busy response and one from the same thread `lifecycle_lock_reentry`; the 1zlts bullet names the path-free projection rows. Mutations in a scratch copy (`scratchpad/1zls7-repair-mutations.txt`), 18 of 18 killed: busy row, unavailable row and generic row each restored to the exception text. Follow-ups (recorded, not fixed): `memory_consolidate` and `memory_purge` are not registered publishers, so under an upgrade hold they raise `ProjectPublicationUnavailable`, whose text carries an absolute path through FastMCP (pre-existing, red-team R3 family); the projection monitor's own `monitor_error` row and the `authority_unavailable` row still carry exception text into `index_health`. Suites (scratch copy of the repaired tree, `scratchpad/1zls7-repair-suite-*.txt`): `run_tests.py --no-cache` 10722 tests across 156 files OK, 34 skipped; `--profile second` 10719 run, 0 of 156 files failed; `--profile declared` 10722 run, 0 of 156 files failed. | `scratchpad/1zls7-repair-*`, 2026-10-02 |
| 2026-10-02 | Implemented. `lifecycle_lock`: `LifecycleLockBusy` and `LifecycleLockUnavailable` share a base carrying `lock_rel` (repository-relative, forward slashes), `reentry`, `same_thread` and `cause` (exception class plus errno name, never its text); `_acquire` and `_refuse_if_held_here` set them; `str()` keeps the absolute path for local logs. `server_impl`: `_lifecycle_mutation_lock` enters the authority lock through an `ExitStack` and converts only an acquisition refusal into `LifecycleMutationBusy` (now with `kind` busy, in_process, reentry or unavailable, `lock_rel`, `cause`); the `locked` wrapper keeps an `acquired` flag so a body-raised `LifecycleMutationBusy` re-raises, returns the new `lifecycle_lock_reentry` (`_lifecycle_lock_reentry_response`) for a body-raised re-entry `LifecycleLockBusy`, and lets every other body exception propagate; `_lifecycle_mutation_busy_response(tool_name, busy)` builds `lifecycle_mutation_locked` (another process, or another call in this server process for an other-thread hold), `lifecycle_lock_unavailable` (data.busy false, names the cause class, says retrying will not help) and, for a same-thread re-entry at acquisition (a nested served locked tool), `lifecycle_lock_reentry`, all naming `.wavefoundry/lifecycle-mutation.lock` and never repeating the exception text; the root-resolution refusal names only the exception class. Requirement 4a: `review_evidence.ProjectPublicationUnavailable` gains a path-free `detail` set at all seven raise sites (repository-relative publication and lifecycle lock names and the cause class) and `publication_unavailable_detail(exc)` (never `str(exc)`; a generic path-free fallback for an exception without detail); used by `_wrap_upgrade_publication_guard`, `wf_mark_ac` (`_mark_change_item_response`, replacing `_read_error_detail(exc)`) and the sibling `context_efficiency_handlers._project_context_efficiency_wave`, whose `publication_lock_busy` `error` DOES reach tool responses (`data.context_efficiency_persistence` of lifecycle tools via `_flush_context_efficiency`, and the CE monitor failure detail), so it is made path-free too. Its `index_source_busy` and `index_source_unavailable` rows still carry `str(exc)` of a runtime lock error (out of scope here; follow-up). Tests (AC mapping): `test_lifecycle_mutation_lock.LifecycleRefusalContractTests` AC-1 `test_contention_from_another_process_names_the_relative_lock_once`; AC-2 `test_unavailable_at_acquire_is_not_busy`; AC-3 `test_body_reentry_is_reported_as_reentry_and_the_hold_is_released`, `test_nested_wrapped_call_on_the_same_thread_is_reentry`; AC-5 `test_non_lock_body_exception_propagates_and_releases`, `test_body_lock_refusals_that_are_not_reentry_propagate`; AC-8 `test_contention_from_another_thread_says_this_server_process`, `test_root_resolution_refusal_names_only_the_exception_class`, `test_upgrade_guard_publication_refusal_is_path_free`, `test_context_efficiency_publication_error_is_path_free`, and `test_lifecycle_gates.test_mark_ac_publication_refusal_is_path_free_under_the_upgrade_shape` (a real child holding `lifecycle_publication_transaction`); every path-free assertion checks the temporary root and its resolved path. Failing-first: 9 of the 10 new contract tests failed before the code change (8 of the first 9 written plus the mark_ac test; the AC-5 non-lock propagation pin passed, as intended, and the later-added body-refusal propagation test was proven by mutation M8), for example the AC-1 message read "the lifecycle-mutation.lock at lifecycle mutation lock is held: /var/folders/.../.wavefoundry/lifecycle-mutation.lock is held" (scratchpad `1zls7-1zlts-failing-first-*.txt`). Requirement 6 census, predicate: a test or doc under `.wavefoundry/framework/scripts/tests/` or `docs/` (waves excluded) naming `lifecycle_mutation_locked`, `lifecycle_lock_unavailable`, `LifecycleMutationBusy`, `_lifecycle_mutation_busy_response`, the old message text, or the keyless refusal set. Updated: `test_extension_tool_modules.py` `test_the_hold_is_registered_and_reentry_is_refused_without_opening_the_file` (served nested call now `lifecycle_lock_reentry`) and `test_an_unhandled_reentry_returns_busy_and_keeps_the_hold_until_return` (renamed `..._returns_reentry_...`); `test_lifecycle_mutation_lock.py` `test_busy_response_shape` (passes the exception, asserts path-free), `test_middleware_returns_busy_for_a_reentered_tool_call` (renamed `..._returns_reentry_...`, same-thread re-entry), and `test_server_impl_only_names_the_lock_for_messages` (accepts `LIFECYCLE_MUTATION_LOCK_REL.as_posix()` as a message-only use); `test_lifecycle_gates.py` `test_provenance_rule_is_derived_and_documented_at_every_site` (expected set gains `lifecycle_lock_reentry`, derived from the code). Unchanged and passing: `test_readiness_convergence.py` (patches acquisition with `LifecycleMutationBusy('fixture-lock')`, still `lifecycle_mutation_locked`), the other `lifecycle_mutation_locked` assertions in `test_extension_tool_modules.py` (another-process contention), `test_review_evidence.py`, `test_index_source_guard.py` (asserts the reason only). Docs: `docs/specs/mcp-tool-surface.md` (the 1zimf lifecycle-tools paragraph and the prepare `configured_gates` keyless list), `docs/architecture/cross-cutting-concerns.md` (lifecycle lock bullet and the keyless rule, now six members), `docs/architecture/threat-model.md` (extension tool modules row). Gapfill: shell `grep` over `tests/*.py`, `docs/` and the scripts tree for the census literals and for `ProjectPublicationUnavailable` consumers (exhaustive literal census; `code_references` may be stale). Focused suites (direct unittest, not run_tests.py, while sibling forks edit the tree): `test_lifecycle_mutation_lock` 55 OK, `test_lifecycle_gates` 26 OK, `test_extension_tool_modules` 134 OK, `test_readiness_convergence` 10 OK, `test_review_evidence` 170 OK, `test_server_tools_lifecycle` 583 OK (2 skipped), `test_index_source_guard` 7 OK, `test_secrets_lock_exclusion` 9 OK, `test_setup_reconciliation` 29 OK; `test_context_efficiency` 86 with one timing failure under concurrent load (`test_candidate_scale_p95_budgets`) that passes alone. Mutations (scratch copy, scratchpad `1zls7-1zlts-mutations.txt`): M1 same-thread acquisition re-entry read as other-thread contention fails `test_nested_wrapped_call_on_the_same_thread_is_reentry`; M2 upgrade guard renders `str(exc)` fails `test_upgrade_guard_publication_refusal_is_path_free`; M3 unavailable mapped to busy fails `test_unavailable_at_acquire_is_not_busy`; M4 body re-entry not caught fails `test_body_reentry_is_reported_as_reentry_and_the_hold_is_released`; M5 root-resolution interpolates the exception fails `test_root_resolution_refusal_names_only_the_exception_class`; M6 CE error back to `str(exc)` fails `test_context_efficiency_publication_error_is_path_free`; M7 `wf_mark_ac` back to `_read_error_detail` fails `test_mark_ac_publication_refusal_is_path_free_under_the_upgrade_shape`; M8 dropping the `acquired` re-raise survived the first test set, so `test_body_lock_refusals_that_are_not_reentry_propagate` was added and now fails under it. Platform: messages use the forward-slash repository-relative path on every platform; the busy and unavailable mapping is independent of the `fcntl` or `msvcrt` lock backend. Follow-up (recorded, not done): body exceptions that are not lock refusals still surface `str(exc)` through FastMCP (red-team R3), and the CE `index_source_*` rows carry `str(exc)`. Coordinator suite run (scratch copy of the whole wave tree): `run_tests.py --no-cache` 10689 tests across 156 files OK (34 skipped); `--profile declared` 10689 OK; `--profile second` 10686 run, its one failure was a 1zltr fixture (fixed, the file then passed under the second profile). | Focused unittest runs and scratch-copy mutations, 2026-10-02 |
| 2026-10-02 | Planned from the Waveforge report. Verified against the tree: `_lifecycle_mutation_lock` wraps `yield` inside its `except (LifecycleLockBusy, LifecycleLockUnavailable)`; `_lifecycle_mutation_busy_response` interpolates the hint into "the {lock name} at {hint} is held"; `lifecycle_lock._acquire` formats `f"{label} lock is held: {lock.path}"` with the absolute path; `_refuse_if_held_here` raises `LifecycleLockBusy` for re-entry; `lifecycle_publication_transaction` raises `LifecycleLockBusy` for the publication lock; the wrapper already uses `lifecycle_lock_unavailable` for root-resolution failure. | Planning read, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Keep `lifecycle_mutation_locked` for contention at acquire; reuse `lifecycle_lock_unavailable` for unavailable; add only `lifecycle_lock_reentry` | Existing callers and the provenance census keep their codes; one new code covers the only genuinely new case | A new code for every lock and cause |
| 2026-10-02 | A body-raised publication lock returns the existing `project_publication_busy` | That code already means the publication lock is held elsewhere (`wf_mark_ac`, the upgrade publication guard) | A new code |
| 2026-10-02 | Build messages from exception attributes, never from `str(exc)` | Parsing exception text is what produced the garbled message; attributes keep the path repository-relative | Strip the absolute path from `str(exc)` |
| 2026-10-02 | Readiness amendments: Requirement 4's publication-lock bullet and AC-4 dropped (unreachable: `lifecycle_publication_transaction` is called only from `upgrade_wavefoundry`, `wf_upgrade` is not lock-wrapped, and the transaction takes the lifecycle lock first); the reachable leak brought into scope as Requirement 4a and AC-8 (red-team R1: `ProjectPublicationUnavailable` text with absolute paths returned as `project_publication_busy` by `_wrap_upgrade_publication_guard` via `str(exc)` and by `wf_mark_ac` via `_read_error_detail`); the root-resolution `lifecycle_lock_unavailable` message made path-free (R2); an acquire-time refusal held by another thread of this server says "another call in this server process"; body exceptions surfacing `str()` through FastMCP (R3) recorded as a follow-up | Readiness review: the dropped case cannot occur, and the absolute-path leak it was meant to cover is reachable elsewhere | Keep AC-4 with a synthetic body (rejected: tests a path no caller takes) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A caller depends on re-entry returning `lifecycle_mutation_locked` | Requirement 6 census; the threat model row and tests are updated together |
| Restructuring the context manager leaks a hold on an exception path | AC-3 and AC-5 assert another process can acquire after each path |
| Absolute path forms differ by platform | AC-1 asserts against the resolved temporary root, so a Windows drive path, a macOS `/private/var` path and a Linux or WSL2 path are all covered; the record lock is `fcntl` on POSIX and `msvcrt` byte-range on Windows, and the busy and unavailable mapping is the same on both |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
