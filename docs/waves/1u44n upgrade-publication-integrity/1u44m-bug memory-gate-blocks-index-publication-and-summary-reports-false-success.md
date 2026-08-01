# Memory Gate Blocks Index Publication While the Summary Reports Success

Change ID: `1u44m-bug memory-gate-blocks-index-publication-and-summary-reports-false-success`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-31
Wave: `1u44n upgrade-publication-integrity`

## Rationale

Field-reproduced on two consecutive upgrades of the same target repository (1.15.0+pfxp and
1.15.0+pg1a), and consistent with two further reports from other targets on the same day:

Phase 4 index publication fails while the upgrade lock still reads
`current_phase: awaiting_memory_validation`, even though historical memory is already indexed with
zero pending candidates. The build epoch is left incomplete and semantic search readers fail closed
until an operator recovers by hand. The working recovery is reliable but undiscoverable:
`resume_after_memory`, then `cleanup`, then `index_build`.

The sharper defect is the reporting. The same run's summary reports
`index_update: "docs layer complete, code layer running in background"` while the build actually
failed. An operator or agent reading the upgrade result is told the index phase succeeded; only an
independent `index_health` call reveals the incomplete epoch. A summary field that reports success
on a failed operation is worse than no field, because it suppresses the check that would have
caught it.

This is the second false-success summary field found in this release cycle. Wave 1u2b0 found the
write-tier permissions consent delta being silently dropped by a value cap and returned as `None`,
likewise invisible in the summary. The two share a root pattern worth naming in the fix: upgrade
summary fields are assembled from intent rather than from the outcome the phase actually produced.

Related prior work that narrowed but did not close this area: wave 1tz6l repaired
`memory-pause-masquerades-as-docs-failure` (a passed docs gate retaining `failed_phase=docs_gate`)
and `memory-id-rename-and-gate-resume-deadlock` (a stale slug stranding the run), and added the
empty-worklist auto-continue.

### Causal story, corrected twice

**First correction (prepare council).** This plan was filed on the theory that the 1tz6l
empty-worklist auto-continue failed to fire. The council disproved that by code-grounded tracing.
The auto-continue at `upgrade_wavefoundry.py:4207-4226` is gated on
`memory_summary["state"] == "awaiting_validation"` and is never reached in either field variant: a
rerun already at `indexed` short-circuits at `memory_backfill.py:686`, and a fresh zero-work run
lands `ready_for_index` with `candidates_drafted == 0`. Both reported field variants are explained
by that one mechanism, so the disproved auto-continue theory is not needed for either.

**Second correction (code-reviewer prepare lane, probe-verified). This one changed the target of
the fix.** The council's replacement story was that the unconditional lock write at
`upgrade_wavefoundry.py:4238-4249` stamps `current_phase="awaiting_memory_validation"` before the
pause branch at `:4250` decides, Phase 4 at `:4273` advances only the local variable, and
publication is therefore refused *on the phase value*. The code lane refuted that with an
executable probe: `index_state_store.begin_build_epoch` refuses on **checkpoint presence**, not on
the phase value.

`begin_build_epoch:2275` calls `publication_control.publication_checkpoint_reason(root,
"index_build")` with no `memory_recovery` flag. That function returns `None` only when
`read_upgrade_checkpoint` finds no checkpoint file at all (`publication_control.py:100-102`); the
`memory_recovery` escape at `:109-110` is unreachable for the `index_build` producer. Every other
input, including `current_phase: index_update`, falls through to the refusal string at `:111-114`.
The probe result: phase `awaiting_memory_validation` raises, phase `index_update` also raises, no
checkpoint succeeds, staged-child receipt succeeds.

Advancing the lock's `current_phase` therefore changes only the refusal *text*. The two things that
actually admit a publisher are the disjuncts at `begin_build_epoch:2268-2276`:

- **owner**: `checkpoint["pid"] == os.getpid()`, which the Phase 4 child never satisfies because it
  is a separate `setup_index.py` subprocess, and
- **staged upgrade child**: a non-empty `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` in the child's
  environment.

Only removing the checkpoint (what `cleanup` does, which is exactly why the field recovery works)
or acquiring one of those two statuses unblocks publication.

**Corollary, and the reason the blast radius is larger than filed:** the memory gate is not the
cause. `phase_index_update` binds the receipt env var only through
`phase_index_update_parent_owned` (`upgrade_wavefoundry.py:2144-2152`), which the primary phase
calls only when `publication_pending` is true (`:4275-4283`). On every other upgrade the plain
`phase_index_update(root)` branch at `:4283` spawns the `setup_index.py` child with no receipt and
no owning pid. **Phase 4 publication is refused on every upgrade whose index build has real work,
not only on memory-gate runs.** It goes unnoticed because the child's non-zero exit is swallowed as
a warning and the summary reports success regardless, which is the same defect from the other end.

This is a code defect against a documented contract, not a contract change. Seed-160 line 51
already documents the correct behavior: "when that run-wide batch produces no candidates, failures,
or remaining waves, upgrade continues automatically to Phase 4". The code does continue to Phase 4;
it simply sends an unauthorized publisher.

## Requirements

1. **The Phase 4 index child must hold authorized-publisher status at the `begin_build_epoch`
   boundary.** The repair target is the authorization disjunction at
   `index_state_store.begin_build_epoch:2268-2276` (`owner` pid, or the staged-receipt env var),
   **not** the lock's `current_phase` value. On every upgrade path that reaches Phase 4, the
   `setup_index.py` child spawned by `phase_index_update` (`upgrade_wavefoundry.py:2046-2051`), the
   graph child at `:2075-2080`, and the `phase_index_rebuild` children at `:2173-2177` and
   `:2184-2188` must satisfy one of those disjuncts, so that `begin_build_epoch` admits the build
   and `finalize_build_epoch` completes the epoch. "Every upgrade path that reaches Phase 4" means
   all three: the primary phase, standalone `--update-index`, and standalone `--rebuild-index`; an
   implementation covering only the update path does not satisfy this requirement.

   Both `index_state_store.begin_build_epoch` and the staged-receipt mechanism
   (`phase_index_update_parent_owned` at `upgrade_wavefoundry.py:2118-2157`,
   `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` at `index_state_store.py:2273` and `:2308-2310`,
   `finalize_staged_build_epoch` at `:2438`) are **in scope**. Two mechanics the implementer must
   design against rather than discover:

   - `finalize_build_epoch` writes a staging receipt only when `backfill_run_id` **and**
     `parent_receipt_path` are both set (`index_state_store.py:2323`). With a receipt path and no
     memory run id it falls through to the plain `_finalize()` at `:2426-2427` and completes the
     epoch in the child. That is the behavior a non-memory Phase 4 needs, but it means the parent's
     `_finalize_existing()` recovery at `upgrade_wavefoundry.py:2126-2138` will find no receipt.
     Reusing `phase_index_update_parent_owned` unmodified for the non-memory path would therefore
     raise the "child did not produce a valid staging receipt" error at `:2153-2157`. Choose
     deliberately between extending the receipt path to the no-run-id case and authorizing the
     child without routing it through the parent-owned wrapper, and record the choice.
   - `subprocess_util.isolated_run` inherits `os.environ` when the caller passes `env=None`
     (`subprocess_util.py:74-101`), and `utf8_child_env()` starts from a copy of `os.environ`
     (`:184`). An env var set in the parent therefore reaches the Phase 4a child, the Phase 4b graph
     child, **and** the detached background code child launched at
     `upgrade_wavefoundry.py:2091-2115`, which outlives the parent and the lock. Scope the
     authorization so the detached background child is not left holding a stale publisher grant. The
     grant primitive is presence-bound today: `index_state_store.py:2272-2274` admits ANY caller
     whose `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` is non-empty, with no binding to a specific
     upgrade, epoch, or run. Decide whether the grant should be value-bound (a token or path the
     store validates) rather than presence-bound, and record the choice either way.

   Red-first test: `begin_build_epoch` from a non-owner pid with a checkpoint present must fail
   before the fix and succeed after it, with the checkpoint's `current_phase` held constant across
   both the `awaiting_memory_validation` and `index_update` values, proving the fix is not keyed on
   the phase.

2. **The refusal message must state the complete recovery, composed once for both surfaces.** Today
   the message names none of `resume_after_memory`, `cleanup`, or `index_health`, and three
   separate sessions rediscovered the sequence by tracing. Branch the message on the checkpoint's
   `memory_backfill_pending`: when pending is zero, emit the ordered `resume_after_memory`, then
   `cleanup`, then `index_build` sequence, name `index_health` as the confirming check, and state
   that `resume_after_memory` exits zero while the lifecycle is still non-terminal. When pending is
   non-zero the run is in a genuine pause, so that sequence would tell the operator to skip
   validation; route instead to `memory_backfill` / `memory_validate`. Treat an absent or unreadable
   `memory_backfill_pending` as a genuine pause (fail safe): `read_upgrade_checkpoint` returns `{}`
   for corrupt or unreadable checkpoint files (`publication_control.py:85-89`), and the
   skip-validation recovery must never be emitted on unknown state.

   Compose the enriched text at exactly one site: the message tail of
   `publication_control.publication_checkpoint_reason` (`publication_control.py:111-114`). Two
   refusal surfaces consume that one string and will diverge if it is enriched at either of them
   instead:

   - the MCP `index_build` caller, where the guarded wrapper at `server_impl.py:25542-25557` strips
     the `upgrade_in_progress: ` prefix into an `upgrade_in_progress` diagnostic, and
   - the in-upgrade `setup_index.py` child, where `begin_build_epoch:2277` raises the same string as
     a `RuntimeError` that surfaces only as a child exit code.

   Assert both surfaces render the same enriched text in the same scenario.

   A THIRD index-publication refusal surface exists outside `publication_control` and must be made
   consistent in this same change (release lane, 2026-07-31): the standalone transaction gate at
   `upgrade_wavefoundry.py:3595-3622`, entered for `--update-index`, `--rebuild-index`, and
   `--cleanup`, refuses whenever the memory summary state is not `indexed` and emits "Historical
   memory validation is pending; ... Run bounded memory backfill + validation, then
   --resume-after-memory" at `:3617-3619`. In the zero-pending field scenario that statement is
   false and the guidance is wrong, this gate fires BEFORE the `pre_index_update` hook at `:3643`
   (so the requirement 3 bridge cannot act there), and it does not consume
   `publication_checkpoint_reason`. Branch its message on the same `memory_backfill_pending` logic
   (zero pending routes to the `resume_after_memory`, then `cleanup`, then `index_build` sequence)
   or route it through the same composition site; do not leave a dishonest message on the documented
   recovery path the field operators actually used.

3. **Bridge the fix onto the installing upgrade through the new pack's `pre_index_update` hook.**
   `_load_extension_module` reads `upgrade_extensions.py` out of the NEW pack zip without extracting
   it (`upgrade_wavefoundry.py:944-984`), and the OLD parent runner already calls
   `_run_hook("pre_index_update", ctx, ext_mod)` at `:4274`, immediately before the Phase 4 dispatch
   at `:4275-4283`, and again on the standalone `--update-index` path at `:3643`. The hook body is
   therefore new code executing inside the old parent at exactly the seam that needs to change, and
   it already reads the checkpoint and the memory run id (`upgrade_extensions.py:687-694`).
   Establishing the child's publisher authorization there makes the fix effective **on the upgrade
   that installs it** instead of one upgrade later.

   Constraints. (a) The authorization must be placed **before** the existing early return at
   `upgrade_extensions.py:691-692` (which returns as soon as the lock carries no
   `memory_backfill_run_id`, the exact non-memory case that needs the bridge most). (b) Fail-safety
   must be implemented INSIDE the hook body, because the dispatcher is fail-fatal: `_run_hook`
   re-raises `SystemExit` (`upgrade_wavefoundry.py:1008-1009`) and converts any other hook exception
   into `sys.exit(3)` (`:1000`, `:1010-1012`), after which `_finalize_failed_upgrade`
   (`:2930-2954`) stamps `failed_phase="index_update"` and RETAINS the lock, so an unwrapped bug in
   the bridge would convert every zip-borne upgrade into a retained-lock failure. Wrap only the NEW
   bridge portion in its own try/except; the two INTENTIONAL `SystemExit(ACTION_REQUIRED_EXIT)`
   pause branches at `upgrade_extensions.py:695-707` must be preserved, and the existing pause test
   at `test_upgrade_wavefoundry.py:6347-6351` must stay green. (c) On the standalone
   `--update-index` path the extension module loads via `_zip_from_lock`
   (`upgrade_wavefoundry.py:3640-3642`); if the lock lacks a resolvable zip path (zips are transport
   artifacts and may have been deleted) the bridge silently does not run there; record this residual
   in the design record. Every real upgrade is zip-borne (operator-confirmed 2026-07-31), so this
   bridge is the PRIMARY delivery mechanism for already-upgraded targets, not a fallback; the
   `zip_path is None` branches in `_load_extension_module` exist in code but do not occur in
   practice and must not shape the design. Requirement 1 remains the durable repair because every
   subsequent upgrade runs the new parent code, not as insurance against a zip-less run. Do not add
   defensive scope for the no-zip case beyond what already exists.

4. **If any phase advance remains in the design, the resume allow-list must move with it.** The
   `--resume-after-memory` guard at `upgrade_wavefoundry.py:3481-3490` accepts only
   `awaiting_memory_validation`, `memory_resume_preflight`, and `index_complete`. Advancing the
   on-disk lock to `index_update` without adding `index_update` to that set strands the only working
   recovery, which is the same deadlock shape 1tz6l already repaired once. Either add it in this
   same change or land no phase advance at all; do not defer.

5. **No upgrade summary field may report a phase outcome the phase did not achieve.**
   `index_update` must derive from the observed publication result at **all three** writers, not
   from the phase having been attempted:

   - `_emit_primary_phase_summary:2787` passes `ran_index_rebuild=True` hardcoded.
   - The cleanup path's `_cl_rebuilt` at `:3719` derives from `index_rebuilt_at`, which the primary
     phase writes unconditionally at `:4287-4291` after Phase 4 regardless of the child's result.
   - The standalone `--update-index` writer at `:3673-3676` and the standalone `--rebuild-index`
     writer at `:3696-3699` both stamp `index_rebuilt_at` unconditionally as well, so `_cl_rebuilt`
     reads a success marker from either of those paths too.

   Fixing the derivation is not sufficient on its own: the index child's non-zero exit is swallowed
   as a warning at three sites, so the true outcome is not observable by any writer. All three must
   be addressed for this requirement to be satisfiable at all:

   - `:2052-2059` in `phase_index_update`, which raises only when a memory run id is bound and
     otherwise logs `"Docs index update exited N — continuing"`,
   - `:2178-2179` in `phase_index_rebuild`, the same shape with no memory-run-id escape at all, and
   - `:2189-2190`, the graph child in the same function (`:2081-2082` is the update path's twin).

   The graph swallow may stay a warning if the change records why the first-query rebuild safety net
   makes it benign, but the decision must be explicit, not inherited. When publication fails or is
   refused, the field says so and the response carries a diagnostic naming `index_health` as the
   confirming check.

6. **Audit the sibling summary fields, and the sibling checkpoint writers, for the same
   intent-versus-outcome and retained-phase defects.** Two bounded, enumerable surfaces:

   - The 18 keys returned by `_build_upgrade_summary` (`upgrade_wavefoundry.py:2712-2748`). Audit
     exactly that list, not an open-ended sweep. In-repo prior art for the identical repair is
     `_docs_gate_summary_line:2486`, where wave 1p44o replaced a hardcoded `PASSED` with a value
     derived from real lock state; follow that shape. `_emit_primary_phase_summary` also hardcodes
     `failed_phase=None` at `:2788`; that one is benign because the site is unreachable on failure,
     so audit-and-justify it rather than changing it. The permissions delta from wave 1u2b0 is the
     known precedent this sweep should have caught.
   - `resume_after_gate` at `:3852-3885`, which is a candidate second instance of the retained-phase
     shape: it selects `index_complete` only when `memory_state == "indexed"` and otherwise leaves
     `awaiting_memory_validation`, then routes the operator to `resume_after_memory` even on the
     `ready_for_index` branch at `:3880-3885`. Determine whether that leaves the same unauthorized
     publisher downstream and fix or justify. Include the four sibling checkpoint writers currently
     outside the audit surface: `upgrade_wavefoundry.py:3441-3452` and `:3533-3543`, and
     `upgrade_extensions.py:654-664` and `:708-716`.

7. **Regression tests must defeat the known vacuity traps.** Three traps are already identified:

   - `begin_build_epoch` exempts a same-process caller through the `owner` disjunct, so a naive
     in-process fixture goes green while appearing to cover the field scenario. The prior art that
     defeats it is an explicit `"pid": -1` in the written checkpoint, as
     `test_review_policy.py:625` already does, **plus** clearing
     `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` from the test environment, since the second
     disjunct at `index_state_store.py:2272-2274` is satisfied by any non-empty value.
   - `_build_upgrade_summary(ran_index_rebuild=False)` proves nothing about the defect: the bug is
     that no caller ever passes `False` on a failed publication. Tests must drive both emit sites
     end to end and assert on what the emitted sentinel actually says. "End to end" means starting
     from a failing child exit: the correct stub boundary is `subprocess_util.isolated_run`
     returning `returncode != 0`, so the observability chain through the de-swallowed exits
     (`:2052-2059`, `:2178-2179`) is exercised, not just the writer.
   - Three existing tests pin the current behavior and must be **re-pointed, not deleted**:
     `test_server_tools.py:24610` (the `_summary_output` fixture's `"docs layer complete, code layer
     running in background"`), `test_upgrade_wavefoundry.py:4556-4560`
     (`test_index_update_reflects_running_on_primary_phase`, which asserts
     `assertIn("running in background", summary["index_update"])` and pins exactly the hardcoded
     behavior requirement 5 removes), and `test_upgrade_wavefoundry.py:967-972`
     (`test_index_rebuilt_at_recorded`, whose docstring documents the exact intent-derived
     `_cl_rebuilt` contract requirement 5 replaces; because it hand-writes `index_rebuilt_at` into
     the lock, it would SILENTLY KEEP PASSING after the fix while documenting the removed contract,
     so it must be rewritten to the outcome-derived contract).
   - Named negative controls that must stay green: `test_review_policy.py:618-631`
     (`test_background_index_epoch_cannot_begin_or_finalize_during_upgrade`, which pins that a
     non-owner with NO grant stays refused), the `publication_block_reason` cluster at
     `test_review_policy.py:503-547`, and the hook pause test at
     `test_upgrade_wavefoundry.py:6347-6351`. No existing test pins the full refusal text (all match
     the `upgrade_in_progress` prefix only), so requirement 2's enrichment breaks none of them.

   Preserve `ran_index_rebuild`'s parameter name and arity across
   `_build_upgrade_summary`, `_emit_primary_phase_summary`, `_print_operator_summary`, and
   `phase_cleanup`: 31 references exist across source and tests, and renaming or re-signing it turns
   a two-site behavior fix into a mechanical sweep that hides the real change. Since the retained
   name says "ran" while the fixed semantics are "publication observed successful", update the
   parameter's docstring or comment at `_build_upgrade_summary` to state the new meaning, so the
   next reader does not reintroduce a hardcoded `True`.

## Scope

**Problem statement:** the Phase 4 index child is not an authorized publisher at the
`begin_build_epoch` boundary while the upgrade checkpoint exists, so publication is refused, and the
upgrade summary reports that phase as successful anyway.

**In scope:**

- `index_state_store.begin_build_epoch`'s authorization disjunction and the staged-receipt
  mechanism, including `finalize_build_epoch`'s receipt-write condition and
  `phase_index_update_parent_owned`
- The Phase 4 child spawn sites in `phase_index_update` and `phase_index_rebuild`, and the
  environment inheritance that reaches the detached background code child
- The new pack's `pre_index_update` hook in `upgrade_extensions.py` as the installing-upgrade bridge
- The `resume_after_memory` allow-list at `:3481`, if and only if a phase advance remains
- Refusal-message completeness composed once in `publication_control.publication_checkpoint_reason`,
  branched on `memory_backfill_pending`, plus the standalone gate's refusal at
  `upgrade_wavefoundry.py:3617-3619` made consistent with the same branch
- The `index_update` summary field's derivation at all three writers, the three swallowed child
  exits, a bounded audit of the 18 `_build_upgrade_summary` keys, and the `resume_after_gate` plus
  four-sibling checkpoint-writer audit
- Regression tests reproducing the field scenario with the vacuity traps defeated

**Out of scope:**

- The memory-gate pause itself when work genuinely is pending (correct behavior)
- The doc-drift gardener classifier failure reported alongside this (separate defect, see Risks)

**Explicit non-goal: do not change `publication_control.py`'s guard PREDICATE.** Seed-160 line 511
pins the invariant that at `awaiting_memory_validation` only `memory_backfill` / `memory_validate`
may publish and "every other registered publisher fails fast with `upgrade_in_progress` until
terminal cleanup". The predicate is the `checkpoint is None` early return at
`publication_control.py:100-102` together with the `memory_recovery` escape at `:109-110`; both stay
byte-identical. Relaxing them to admit `index_build` when `memory_backfill_pending == 0` would
weaken documented shipped behavior and trade a visible refusal for a silent publication during a
genuine pause. The non-goal is scoped to the predicate only: the **message tail** at `:111-114` is
in scope under requirement 2, because it is the single composition point both refusal surfaces read
and enriching it changes no authorization decision. The correct repair is to send an authorized
publisher, not to widen who may publish.

**Old-code window.** The in-runner repair of requirement 1 does not take effect on the upgrade that
installs it, because the parent runner executing Phase 4 is still the old code. Requirement 3's hook
bridge closes that window; every real upgrade is zip-borne, so the bridge applies universally (the
hook dispatch and zip-borne extension loading have shipped since v1.4.0, so runners on any
realistic installed version fire the new pack's hook). For the residual case (a hook failure
absorbed fail-safe inside the hook body) no `--cleanup` backstop is required: `phase_cleanup`
reaches `remove_upgrade_lock` at `upgrade_wavefoundry.py:2319` whenever `failed_phase` is falsy,
and on the field pause path the run exits via `ACTION_REQUIRED_EXIT` (`:4265`) without touching
`failed_phase`, so the field scenario does not reach the retain-and-exit branch at `:2253-2286`.
(A failed dashboard restart is the one other retaining gate, at `:2288-2317`; a cleanup rerun after
repairing the dashboard still removes the lock.) Removing the lock removes the checkpoint, which
is precisely what makes `publication_checkpoint_reason` return `None` and is why the field recovery
works. An installed-but-not-yet-effective fix therefore leaves every target recoverable by the
documented `cleanup` step.

## Acceptance Criteria

- [x] AC-1: On every upgrade path that reaches Phase 4 (primary phase, standalone `--update-index`,
  standalone `--rebuild-index`), the `setup_index.py` child satisfies an
  authorized-publisher disjunct at `begin_build_epoch` (owner pid or staged receipt), the build
  epoch is admitted and finalized, and publication completes without manual recovery. Proven by a
  test that writes a checkpoint with an explicit non-owner `"pid": -1`, clears
  `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT`, and asserts the same outcome for both
  `current_phase: awaiting_memory_validation` and `current_phase: index_update`, so the pass cannot
  be attributed to the phase value. An executed assertion proves the DETACHED background code
  child's environment carries no publisher grant. On a genuinely paused run the
  `memory_backfill` / `memory_validate` exemption is intact, and `publication_control.py`'s
  predicate is unchanged.
- [x] AC-2: The `index_build` refusal names the complete recovery, branched on
  `memory_backfill_pending` (absent or unreadable treated as genuine pause), the MCP `index_build`
  diagnostic and the in-upgrade child raise render the same text from the same composition site, and
  the standalone gate at `upgrade_wavefoundry.py:3617-3619` no longer emits a false
  "validation is pending" statement in the zero-pending scenario.
- [x] AC-3: The fix takes effect on the upgrade that installs it. A test loads the extension module
  through `_load_extension_module` from a real zip (not by importing the module directly), drives
  `pre_index_update` with no `memory_backfill_run_id` in the lock, and asserts the pass/fail
  observable: after the hook runs, `begin_build_epoch` ADMITS a simulated non-owner child
  (checkpoint `"pid": -1`, child-inherited env), not merely that a flag or env var was set. A
  second test drives an actually-raising bridge body and asserts the failure is absorbed inside the
  hook while the intentional `ACTION_REQUIRED_EXIT` pause branches still raise. The hook is a no-op
  when authorization is already in place. The in-runner repair of AC-1 passes independently with no
  extension module loaded.
- [x] AC-4: A refused or failed index publication is never reported as a successful `index_update`
  in the upgrade summary, at any of the three writers; the response carries a diagnostic naming
  `index_health` as the check; and no index-child non-zero exit is swallowed silently without a
  recorded justification.
- [x] AC-5: The bounded audit is recorded for both surfaces: every one of the 18
  `_build_upgrade_summary` keys is fixed or explicitly justified (including the benign hardcoded
  `failed_phase=None` at `:2788`), and `resume_after_gate` plus the four sibling checkpoint writers
  are each classified as affected-and-fixed or unaffected-with-reason.
- [x] AC-6: If the delivered design advances the lock's `current_phase`, `index_update` is present
  in the `resume_after_memory` allow-list at `:3481` and a test proves resume succeeds from that
  phase. If no phase advance is delivered, the AC is satisfied by the design record stating so.
- [x] AC-7: Regression tests reproduce the field scenario and fail against current code, the
  vacuity traps are defeated as specified in requirement 7, all three pinned tests
  (`test_server_tools.py:24610`, `test_upgrade_wavefoundry.py:4556-4560`, and
  `test_upgrade_wavefoundry.py:967-972`) are re-pointed rather than removed, the named negative
  controls stay green, `ran_index_rebuild` keeps its name and arity with its new semantics
  documented at the parameter, and the full framework suite passes.
- [x] AC-8: `CHANGELOG.md` carries a bullet under the existing `## [1.15.0] - unreleased` →
  `### Fixed` section describing the publication refusal and the false-success field, plus a
  sentence in `### Upgrading to 1.15.0` stating that a target already on a 1.15.0 prerelease build
  (`+pfxp`, `+pg1a`) will still hit the defect on the transition run under the old parent runner
  unless the pack's `pre_index_update` bridge applies.

## Tasks

- [x] Reproduce the refusal from a non-owner pid with a checkpoint present, at both
      `awaiting_memory_validation` and `index_update`, before writing any fix
- [x] Choose and record the authorization mechanism for the Phase 4 child (owner-pid versus staged
      receipt), including the `finalize_build_epoch:2323` receipt-write condition and the detached
      background-child env inheritance
- [x] Implement the in-runner authorization at the Phase 4 child spawn sites
- [x] Add the new-pack `pre_index_update` bridge before the early return at
      `upgrade_extensions.py:691-692`; keep it fail-safe and idempotent
- [x] Enrich the refusal message once at `publication_control.py:111-114`, branched on
      `memory_backfill_pending` (absent treated as genuine pause); leave the predicate at
      `:100-110` untouched
- [x] Make the standalone gate's refusal at `upgrade_wavefoundry.py:3617-3619` consistent with the
      same `memory_backfill_pending` branch (no false "validation is pending" at zero pending)
- [x] If a phase advance is delivered, add `index_update` to the `resume_after_memory` allow-list at
      `:3481` in the same change (audited: NO phase advance is delivered anywhere in this change;
      the allow-list is unchanged by design, see the Decision Log)
- [x] Derive `index_update` from the publication outcome at all three writers (`:2787`, `:3675`,
      `:3698` feeding `_cl_rebuilt` at `:3719`), and stop swallowing the index child's non-zero exit
      at `:2059`, `:2179`, and `:2190` (or record why the graph swallow stays)
- [x] Audit the 18 `_build_upgrade_summary` keys; fix or justify each intent-derived field
- [x] Audit `resume_after_gate` (`:3852-3885`) and the four sibling checkpoint writers
      (`upgrade_wavefoundry.py:3441-3452`, `:3533-3543`; `upgrade_extensions.py:654-664`, `:708-716`)
- [x] Re-point the three pinned tests (`test_server_tools.py:24610`,
      `test_upgrade_wavefoundry.py:4556-4560`, `test_upgrade_wavefoundry.py:967-972`) to the new
      values; keep the named negative controls green
- [x] Update `docs/specs/mcp-tool-surface.md` lines 917 and 918 for the refusal list and the
      `index_update` value domain, and add the `upgrade_in_progress` refusal sentence to the
      `index_build` section at `:874-886`
- [x] Add the `### Fixed` bullet and the `### Upgrading to 1.15.0` sentence to `CHANGELOG.md`
- [x] Add regression tests with the vacuity traps defeated; rerun the phase-transition seam test
      cluster and the full suite

## Requirement 6 Audit (implementer, 2026-07-31)

All 18 `_build_upgrade_summary` keys, classified from the value each is assembled from:

| # | Key | Classification | Basis |
| - | --- | -------------- | ----- |
| 1 | `review_sidecar_cleanup` | unaffected | Carries the run's actual recorded cutover counts, or `None` when no counts were recorded; no outcome claim beyond what was observed |
| 2 | `from_version` | unaffected | Factual preflight input |
| 3 | `to_version` | unaffected | Factual preflight input |
| 4 | `zip_applied` | unaffected | Factual (`zip_path.name` or `None`) |
| 5 | `pruned_count` | unaffected | Actual prune-phase count |
| 6 | `docs_gate` | unaffected (prior art) | Derived from real lock state by `_docs_gate_summary_line` since wave 1p44o; this is the in-repo shape this change follows |
| 7 | `index_update` | AFFECTED, fixed | Now derived from the OBSERVED publication result at all three writers (`ran_index_rebuild` = observed success, `index_update_failed` = observed failure); the pre-fix hardcoded `True` at `_emit_primary_phase_summary` is removed |
| 8 | `failed_phase` | audit-and-justify | Cleanup path reads the lock's real failure marker (outcome-derived). The hardcoded `None` at `_emit_primary_phase_summary` stays: the emit site is unreachable on failure (main raises past it and the failure summary renders at cleanup from the lock marker); justified in a code comment at the site |
| 9 | `is_major_or_minor` | unaffected | Computed from the version pair; informational only |
| 10 | `reconciliation` | unaffected-with-reason | Populated from the actually executed scan; the fail-safe empty return can under-report findings but is a report-only channel that claims no phase outcome |
| 11 | `host_permission_flags` | unaffected-with-reason | Same scan channel as 10 |
| 12 | `renderer_provenance_flags` | unaffected-with-reason | Same scan channel as 10; self-healing by construction |
| 13 | `permissions_file` | unaffected | Read from the persisted render delta record (wave 1u2b0 repaired this channel) |
| 14 | `permissions_added` | unaffected | Actual render delta list |
| 15 | `permissions_removed` | unaffected | Actual render delta list |
| 16 | `permissions_changed` | unaffected | Tri-state derived from delta presence and counts (1u2b0 precedent this sweep was required to catch) |
| 17 | `permissions_unmanaged_present` | unaffected | From the delta record; `None` when not established |
| 18 | `skipped_scan_locations` | unaffected | Actual recorded skip list from the pack scan |

`resume_after_gate` and the sibling checkpoint writers:

| Writer | Classification | Basis |
| ------ | -------------- | ----- |
| `resume_after_gate` (`upgrade_wavefoundry.py:3852-3885` pre-change) | unaffected-with-reason | Writes `current_phase` and memory fields from a freshly reconciled summary (outcome-derived) and runs no Phase 4 itself. It does route the `ready_for_index` branch to `resume_after_memory`, whose plain `phase_index_update` branch WAS the downstream unauthorized publisher; that publisher is repaired by this change's grant, and the zero-drafted branch now raises on an observed docs-layer failure instead of marking indexed, so the routing guidance is now correct end to end |
| `_new_code_upgrade_backstop` tail writer (`upgrade_wavefoundry.py:3441-3452` pre-change) | unaffected | Mirrors a just-computed `sync_inventory` summary into the lock; no outcome claim beyond the observed sync |
| resume non-ready writer (`upgrade_wavefoundry.py:3533-3543` pre-change) | unaffected | Restores `awaiting_memory_validation` with the freshly reconciled state and pending count |
| `post_docs_gate` writer (`upgrade_extensions.py:654-664` pre-change) | unaffected | Writes state and pending from the fresh `sync_inventory` summary |
| `pre_index_update` tail writer (`upgrade_extensions.py:708-716` pre-change) | unaffected | Writes state and pending from the `reconcile_index_publication` summary |

Two additional writers inside the named serialization files were found carrying the same
intent-derived shape and fixed in this change: the primary Phase 4 tail writer (pre-change
`:4287-4291`), which stamped `memory_backfill_state="indexed"` plus `index_rebuilt_at`
unconditionally and now stamps only on the observed outcome via
`_record_index_publication_outcome`; and the resume success writer (pre-change `:3576-3581`), whose
`index_rebuilt_at` stamp is now reached only after an observed success (the zero-drafted branch
raises on failure) and which additionally clears `index_publication_failed`.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                       |
| ---------- | ----------- | ---------- | --------------------------------------------- |
| fix        | implementer | —          | Publisher authorization, hook bridge, and summary derivation move together |


## Serialization Points

- `index_state_store.py` (the authorization boundary), `upgrade_wavefoundry.py` (the Phase 4 child
  spawn, the three summary writers, the three swallow sites, and the resume allow-list),
  `upgrade_extensions.py` (the hook bridge), and `publication_control.py`'s message tail all move
  together.
- `_build_upgrade_summary` (`:2670`), `_emit_primary_phase_summary` (`:2763`), `_cl_rebuilt`
  (`:3719`) and `_docs_gate_summary_line` (`:2486`) all live in `upgrade_wavefoundry.py`, not in
  `server_impl.py`; `server_impl.py` only parses the emitted sentinel and composes the MCP refusal
  diagnostic.

## Affected Architecture Docs

Resolved at Prepare:

- `docs/specs/mcp-tool-surface.md:917` — the retained-phase refusal list, which today names
  `review_sidecar_cleanup` and `docs_gate` but omits that index publication is refused for the whole
  duration of a checkpoint, at any phase. Required update.
- `docs/specs/mcp-tool-surface.md:918` — add a value domain for `index_update` inside the
  structured `summary` bullet (the line names the field today but documents no domain). Required
  update once the field can report failure.
- `docs/specs/mcp-tool-surface.md:874-886` — the `index_build` tool section documents no
  upgrade-time refusal at all today (`upgrade_in_progress` appears nowhere in the spec). Add a
  sentence documenting the refusal and its `index_health`-naming diagnostic alongside the
  requirement 2 enrichment. Required.
- `CHANGELOG.md` `## [1.15.0] - unreleased` — a `### Fixed` bullet plus an `### Upgrading to 1.15.0`
  sentence. Required; see AC-8.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md:51` and `:511` — OPTIONAL companion
  only. Line 51 already documents the correct behavior ("upgrade continues automatically to Phase
  4"), and line 511's fail-fast invariant is preserved by construction, since the Phase 4 child
  becomes an authorized publisher rather than a relaxed registered one. Touch only if the refusal
  wording needs to match.

## AC Priority


| AC   | Priority | Rationale                                                                    |
| ---- | -------- | ------------------------------------------------------------------------------ |
| AC-1 | required | The unauthorized publisher is the defect; without it publication stays refused |
| AC-2 | required | Three sessions rediscovered the recovery by tracing; two surfaces must not diverge |
| AC-3 | required | Without the bridge the fix helps only the upgrade after the one that installs it |
| AC-4 | required | A field reporting success on failure suppresses the check that catches it    |
| AC-5 | required | The sweep is the general defense; wave 1u2b0 proves one-off fixes miss siblings |
| AC-6 | required | Advancing a phase without the allow-list strands the only working recovery   |
| AC-7 | required | A same-process fixture goes green on this defect; vacuity is the live risk   |
| AC-8 | required | A version-keyed bullet cannot express a boundary inside one unreleased version |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-31 | Prepare council (red-team, docs-contract-reviewer) DISPROVED the plan's original causal story (a failed 1tz6l empty-worklist auto-continue) by code-grounded tracing, and supplied a replacement seam: the unconditional lock write at `:4238-4249` versus the pause branch at `:4250` and the local-only advance at `:4273`. Corrections folded into requirements, Scope, ACs, tasks, and the architecture-doc list. | `wave.md` `## Review Checkpoints`; ledger readiness run |
| 2026-07-31 | OPERATOR CORRECTION folded in: there is always a zip file for upgrades. The rewrite had justified the standalone in-runner scope by citing `_load_extension_module` returning `None` when `zip_path is None`; those branches exist in code (the staged-tree direct-merge path) but do not occur in practice and must not shape the design. Requirement 3, the Old-code window note, and Decision Log alternative (b) restated: the `pre_index_update` bridge is the PRIMARY delivery mechanism for already-upgraded targets, and the in-runner repair is durable because every subsequent upgrade runs the new parent code. | Operator message 2026-07-31; `docs/agents/session-handoff.md` |
| 2026-07-31 | Code-reviewer prepare lane REFUTED that corrected plan with an executable probe and recorded no approval. `begin_build_epoch` refuses on checkpoint PRESENCE, not on the phase value: phase `awaiting_memory_validation` raises, phase `index_update` also raises, no checkpoint succeeds, staged-child receipt succeeds. Re-authored: AC-1 and requirement 1 now target authorized-publisher status at the `begin_build_epoch` boundary; `index_state_store.begin_build_epoch` and the staged-receipt path are in scope; the `publication_control.py` non-goal is narrowed to the guard predicate with the message tail explicitly in scope; the blast radius is restated as every upgrade with real index work; the release lane's `pre_index_update` bridge is adopted as requirement 3; the resume allow-list, the two extra summary writers, the third swallow site, the `resume_after_gate` audit, the test-vacuity traps, the file misattribution in Serialization Points, and the changelog task are all folded in. | Code-lane refutation probe; `index_state_store.py:2268-2277`; `publication_control.py:100-114` |
| 2026-08-01 | FULL SUITE GREEN: `run_tests.py` under the wavefoundry venv ran 6671 tests across 61 files in 305.7s, result OK, exit 0, zero failures, zero errors; no `skipped=` annotations on any module (the five seam modules run directly under unittest each printed plain OK: test_upgrade_wavefoundry 413, test_review_policy 30, test_index_state_store 37, test_upgrade_protocol 29, test_server_tools 1558). All eight ACs marked with evidence; Change Status advanced to implemented. | Background run bkyn20xex output, 2026-08-01 |
| 2026-08-01 | IMPLEMENTED (fix workstream). Requirement 1: value-bound publisher grant (checkpoint `publisher_grant` token matched against `WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN`) admitted at `begin_build_epoch` and `finalize_build_epoch`; granted to the blocking docs and graph children at all three Phase 4 paths (primary, `--update-index`, `--rebuild-index`); the detached background child's env is stripped of both grant vars, with executed assertions. Requirement 2: recovery text composed once in `publication_control._checkpoint_recovery_tail`, branched on `memory_backfill_pending` (absent or unreadable = genuine pause); child raise and MCP diagnostic asserted byte-identical modulo the stripped prefix; the standalone gate refusal branched on the same pending composition. Requirement 3: fail-safe, idempotent `pre_index_update` bridge placed before the no-memory early return; AC-3 tests load the extension from a REAL zip via `_load_extension_module` and assert post-hook admission of a non-owner child, plus an actually-raising-bridge absorption test with the pause branches still raising. Requirement 4: no phase advance delivered (Decision Log). Requirement 5: `index_update` outcome-derived at all three writers via observed child exits, `_record_index_publication_outcome`, and the new `index_update_failed` domain; docs-layer swallows removed (standalone index phases now exit non-zero); both graph swallows stay warnings with the recorded first-query-rebuild justification; `wf_upgrade` responses carry an `index_publication_failed` diagnostic naming `index_health` on ok and error envelopes. Requirement 6: bounded audit recorded in this doc. Requirement 7: red-first evidence below, vacuity traps defeated (pid -1 + cleared receipt env; isolated_run rc!=0 stub boundary; real-zip bridge load), three pinned tests re-pointed, negative controls green, `ran_index_rebuild` name/arity preserved with new semantics documented at the parameter. | Seam cluster green 2026-08-01: test_upgrade_wavefoundry 413, test_review_policy 30, test_index_state_store 37 (cluster run 512 incl. test_upgrade_protocol), test_server_tools 1558; `wf_validate_docs` passed |
| 2026-07-31 | RED-FIRST reproduction recorded (requirement 1 / AC-1). New test `tests.test_index_state_store.BuildEpochTests.test_value_bound_publisher_grant_admits_phase4_child_at_any_phase` (non-owner `"pid": -1`, receipt env cleared, grant token present) FAILS against current code at BOTH phases with `RuntimeError: upgrade_in_progress: publication by index_build is blocked while Upgrade is at awaiting_memory_validation` and the identical refusal at `index_update`, proving refusal is phase-independent. Negative controls (`test_ungranted_non_owner_stays_refused_at_both_phases`, `test_publisher_grant_is_value_bound_not_presence_bound`) pass pre-fix. | `python3 -B -m unittest tests.test_index_state_store.BuildEpochTests...` 2026-07-31, FAILED (errors=2) |
| 2026-07-31 | Full four-lane prepare re-review of the REWRITTEN plan (fresh contexts, prior approvals discarded as stale-by-substance). Code lane PASS: 10/10 executable probe assertions, all 47 file:line claims verified, `ran_index_rebuild` count exactly 31. QA lane PASS with repairs folded: hook fail-safety scoped inside the hook body preserving the `ACTION_REQUIRED_EXIT` pause branches, third pinned test `test_index_rebuilt_at_recorded` added to the re-point list, AC-3 observable specified as post-hook `begin_build_epoch` admission of a non-owner child. Docs lane PASS with repairs folded: `wave.md` re-synced off the refuted causal story, absent `memory_backfill_pending` treated as genuine pause, spec `index_build` section added to required doc updates. Release lane FAIL with two P2s, both folded: the THIRD refusal surface at `upgrade_wavefoundry.py:3595-3622` (dishonest zero-pending message on the standalone recovery path, fires before the bridge hook) added to requirement 2 and AC-2; detached-child no-grant executed assertion added to AC-1 with the presence-bound grant primitive named in requirement 1. Release lane also confirmed the bridge fires on runners back to v1.4.0 and that `upgrade_extensions.py` ships in the pg1a pack at the expected member path. | Four lane reports, 2026-07-31; ledger prepare-phase records |


| 2026-08-01 | Gapfill: implement-stage MCP retrieval telemetry is near zero against a 22-file code diff because exploration was completed during the prepare cycle, not skipped. The four-lane prepare re-review verified 47 file:line claims and every mechanism the implementation targets (two executable probes included), so the implementer worked from those pre-verified targets with direct reads at known offsets and shell-executed tests; re-running semantic retrieval over already-verified sites would have added calls without adding information. Review-phase verification returns to MCP-first per the standing directive. | This row; prepare-cycle lane reports and ledger records dated 2026-07-31 |


## Decision Log


| Date       | Decision                             | Reason                                                                          | Alternatives                                                                          |
| ---------- | ------------------------------------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 2026-07-31 | Filed from reproduced field feedback | Two consecutive reproductions on one target plus corroboration from two others   | Leave as an operator-known recovery ritual (rejected: three sessions rediscovered it) |
| 2026-07-31 | Target authorized-publisher status at `begin_build_epoch`, not the lock's `current_phase` | Probe-verified: `publication_checkpoint_reason` returns a refusal for any existing checkpoint at any phase, so advancing the phase changes only the message text. Only the `owner` pid or the staged-receipt disjunct at `index_state_store.py:2268-2276` admits a publisher | Advance the lock's `current_phase` to `index_update` on the non-pausing branch (rejected: refuted by executable probe; phase `index_update` raises exactly as `awaiting_memory_validation` does) |
| 2026-07-31 | Adopt the release lane's `pre_index_update` hook bridge as an ADDITIVE requirement | `upgrade_extensions` is loaded from inside the NEW pack (`upgrade_wavefoundry.py:944-984`) while the parent runner is still old code, and the old parent already calls the hook at `:4274` immediately before the Phase 4 dispatch, so acting there makes the fix effective on the installing upgrade and closes the old-code window for once | (a) Ship only the in-runner fix and document the old-code window (rejected: every currently affected target would need a second upgrade before the fix applies). (b) Ship only the hook bridge (rejected: the bridge executes only while the parent runner is old code; once the new runner is installed the repair must live in the runner itself. Operator direction 2026-07-31: every real upgrade has a zip, so the zip-less `_load_extension_module` branches must not shape the design). (c) Add a `--cleanup` backstop (rejected: unnecessary, see the Old-code window note in Scope) |
| 2026-07-31 | Narrow the `publication_control.py` non-goal to the guard PREDICATE only | The predicate (`:100-110`) is the documented seed-160:511 invariant and stays byte-identical; the message tail (`:111-114`) is the single composition point both refusal surfaces read, so enriching it there is the only way the MCP diagnostic and the child raise cannot diverge | Enrich the message at each consumer (rejected: two surfaces, guaranteed divergence). Relax the predicate to admit `index_build` at `memory_backfill_pending == 0` (rejected: weakens documented shipped behavior and trades a visible refusal for a silent publication during a genuine pause) |
| 2026-07-31 | Couple the `resume_after_memory` allow-list change to any delivered phase advance | Advancing the on-disk lock to `index_update` while `:3481` accepts only three other phases strands the only working recovery, which is the same deadlock shape 1tz6l already repaired once | Land the advance now and the allow-list later (rejected: the intermediate state is a deadlock) |
| 2026-07-31 | Preserve `ran_index_rebuild`'s name and arity | 31 references across source and tests; renaming turns a two-site behavior fix into a mechanical sweep that hides the real change from review | Rename to something outcome-shaped such as `index_published` (rejected for this change; revisit separately if the field survives) |
| 2026-07-31 | Authorization mechanism: a VALUE-BOUND publisher grant. The runner (and the requirement 3 bridge) records a random token as `publisher_grant` in the upgrade checkpoint and exports `WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN` into the Phase 4 child environments; `begin_build_epoch` / `finalize_build_epoch` admit the caller only when the environment token MATCHES the checkpoint's recorded token. The child then completes the epoch in-child via the plain `_finalize()` path (no run id, no receipt routing), which is exactly the behavior the non-memory Phase 4 needs. The existing presence-bound `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT` disjunct and the staged-receipt write condition at `finalize_build_epoch:2323` stay byte-identical for the memory-staged path. | Value binding is the containment for the detached-child leak: the new runner strips the token from the Phase 4c background env (executed assertion), and under the old-parent bridge, where the env var can still leak into the detached child, the grant dies with this checkpoint because a subsequent upgrade's checkpoint carries a fresh token; a presence-bound grant would admit any caller into any later upgrade's fenced publication | (a) Reuse the presence-bound receipt env var for the non-memory path (rejected: any non-empty value admits any caller, and the old parent's Phase 4c popen would hand the detached background child a live publisher grant). (b) Extend the staging-receipt path to the no-run-id case and route through `phase_index_update_parent_owned` (rejected: `_finalize_existing()` would raise "child did not produce a valid staging receipt" since no receipt is written without a run id, and it adds parent-CAS machinery the non-memory path does not need while touching verified 1tz6l memory publication code). (c) Record the child pid in the checkpoint to satisfy the owner disjunct (rejected: racy, serializes children, and cannot be established by the bridge before the old parent spawns) |
| 2026-07-31 | No lock `current_phase` advance is delivered anywhere in this change (requirement 4 / AC-6) | The repair grants publisher status; probe-verified that the phase value never decides admission, so advancing it buys nothing and risks the 1tz6l resume deadlock shape | Advance to `index_update` and extend the `resume_after_memory` allow-list at `:3481` (rejected: pure churn on a fragile seam) |
| 2026-07-31 | De-swallow shape: the docs-layer child's non-zero exit is OBSERVED and propagated (phase returns the outcome, the writers stamp `index_rebuilt_at` only on success and `index_publication_failed` on failure, the summary reports the failure, the MCP response carries an `index_health` diagnostic), but the primary upgrade still completes instead of retaining the lock; the standalone `--update-index` / `--rebuild-index` invocations exit non-zero. Both graph-child swallows stay warnings. The resume zero-drafted branch raises into its existing `failed_phase="index_update"` handler. | Aborting the whole primary upgrade on an index failure would retain the lock for a condition whose documented recovery (`index_build` + `index_health`) does not need it; the defect was silence, not continuation. Graph justification: the graph store sits outside the semantic build epoch and the first-query rebuild remains its safety net, so a graph warning cannot produce a false-success `index_update` field | Raise at all three swallow sites (rejected: converts a recoverable index failure into a retained-lock failed upgrade); keep exit 0 on standalone failures (rejected: a false process-level success on an explicitly requested index phase) |
| 2026-07-31 | Bridge scope: `pre_index_update` only; no `pre_index_rebuild` bridge | Requirement 3 names the primary-phase and `--update-index` hook dispatches; a standalone `--rebuild-index` under an OLD parent runner remains covered by the documented cleanup recovery and by requirement 1 on every subsequent upgrade | Add a `pre_index_rebuild` twin (rejected: outside the reviewed scope; records as residual together with the zip-less `--update-index` case, where `_zip_from_lock` cannot resolve a deleted transport zip and the bridge silently does not run) |


## Risks


| Risk                                                                                                                                       | Mitigation                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| A publisher grant set in the parent env leaks into the DETACHED background code child (`:2091-2115`), which outlives the parent and the lock, and could collide with a subsequent upgrade's fenced publication | Requirement 1 names the leak and the presence-bound grant primitive explicitly; AC-1 requires an executed assertion that the detached child's env carries no grant; the value-bound versus presence-bound choice is recorded either way |
| Widening who may publish during an upgrade could admit a real concurrent writer                                                            | The predicate in `publication_control.py` is unchanged; only the Phase 4 child, already inside the upgrade's own serialization, gains status through the existing owner/staged-receipt disjuncts |
| A same-process test fixture satisfies the `owner` disjunct and goes green without covering the defect                                      | Requirement 7 mandates the explicit `"pid": -1` checkpoint plus clearing `WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT`, with the phase held constant across two values |
| The hook bridge runs old-parent code paths that were never exercised with a publisher grant in place                                       | Keep the hook fail-safe and idempotent; AC-3 requires a no-op assertion when authorization is already present, and AC-1 must pass with no extension module loaded |
| Adjacent unfixed defect: the doc-drift gardener classifier fails on every build (0 flagged, prior state preserved) across multiple targets  | Out of scope here; file separately so it is not lost                              |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
