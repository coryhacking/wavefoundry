# Retired-Surface References Survive Migration

Change ID: `1v4mv-bug retired-surface-references-survive-migration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-12
Wave: 1v4mx retired-surface-reconciliation

## Rationale

Migrations move files. Nothing reconciles the instructions that point at the moved files, so a
repository that dutifully runs every prescribed migration still carries instructions naming surfaces
that no longer exist.

Three instances from one downstream repository, spanning 1.13.0 to 1.16.1:

1. **The upgrade instructs a retired step on every run.** `upgrade_wavefoundry.py` hardcodes
   `"2. Journal reconciliation"` into the editing-pass output, while seed-120 says "Do not generate
   persona journals — the journal system is retired" and seed-160 says journals are "retired and
   never a closure requirement." Verified in the tree, including a comment three lines above the log
   line that says "fix the journal label" — seen previously and never done. Shipped in 1.16.1.

2. **Journal retirement never reaches the instructions.** seed-210 migrates files under
   `docs/agents/journals/`, but nothing touches the instructions pointing there: roughly 90 sites
   across 43 files in the reporting repository, including "Memory responsibility: journal …", "Stop
   and journal when:", closure prompts' "distill journals", and personas' "Associated journal". The
   reporter verified these strings are neither in current seeds nor emitted by
   `render_agent_surfaces.py`: they are install-time content from an older version that no migration
   reaches. A repo that runs **Migrate journals** still tells its agents to write durable memory into
   a directory that no longer exists.

3. **The `.md` to `.prompt.md` rename never reconciled inbound references.** The upgrade reports
   "Prompt files: none (all already use .prompt.md extension)" because it checks *files*, not
   *references*. The reporting repository had 41 stale references across 27 files, every target
   resolvable under the new name; one line, `docs/agents/wave-coordinator.md:15`, broke three at
   once. Current seeds are clean, so this is purely a legacy-reference gap.

The reporter's key observation, which shapes this change: the existing retired-surface reconciliation
scan **already does exactly this shape of work** for `.wavefoundry/bin/*`. It walks the tree, matches
retired surfaces, and emits report-only `{file, line, retired_surface, matched, suggested}` findings
that the agent resolves. Items 2 and 3 are a request to point that machinery at two more surfaces,
not to build new machinery.

## Requirements

1. The upgrade's editing-pass output does not instruct a retired step.
2. The retired-surface reconciliation scan covers references to the retired journal system.
3. The same scan covers stale `.md` references to prompt files that now carry `.prompt.md`.
4. Findings stay **report-only**, matching the existing scan's contract: the scan never mutates
   operator content.
5. A repository with no stale references reports none, so a clean repo gains no noise.

## Scope

**Problem statement:** migrations relocate or retire surfaces without reconciling the instructions
that reference them, so prescribed migrations leave behind instructions pointing at things that are
gone.

**In scope:**

- Removing the retired journal step from the upgrade's editing-pass output.
- Two NEW pattern families inside the existing `reconcile_scan.py`, one for retired journal-system
  references and one for the `.md` to `.prompt.md` rename. Corrected at readiness: the original
  wording called this "adding to the retired-surface list", which the code does not support. Every
  existing pattern is bound to the `.wavefoundry/bin/<name>` or `mcp__wavefoundry__<tool>` shape and
  cannot express prose or a path-extension rename. The constraint that survives is architectural, not
  textual: stay inside the one scan, the one report-only contract, and the one
  `{file, line, retired_surface, matched, suggested}` findings shape. Do not add a second scanner.
- Reconciling this repository's own 32 stale journal references. Forced, not optional: the shipped
  guard asserts the editable channel is empty for this repo, so the journal pattern cannot land
  green until the self-hosted surface it flags is fixed. Operator-approved 2026-08-12.

**Out of scope:**

- Auto-rewriting operator content in TARGET repositories. The scan stays report-only. This
  repository's 32 files are edited directly because they are ours, which is a different act from the
  scan mutating a target repo's files.
- Rebuilding or redesigning the reconciliation scan, its exclusion policy, or its channel routing.
- Other retired surfaces not named here; if the census finds more, file them rather than widening
  this change.
- Whether seed-210's migration itself is correct. It moves the files fine; only the references lag.

## Acceptance Criteria

- [x] AC-1: The upgrade's editing-pass output contains no retired journal step, asserted by a test that fails if the step returns.
- [x] AC-2: The reconciliation scan reports stale references to the retired journal system, asserted with the field-reported shapes ("Memory responsibility: journal", "Stop and journal when:", "distill journals", "Associated journal").
- [x] AC-3: The scan reports stale `.md` references to prompt files that exist as `.prompt.md`, asserted with a reference whose target resolves under the new name.
- [x] AC-4: A file with several stale references on one line yields a finding for each, since `docs/agents/wave-coordinator.md:15` broke three at once.
- [x] AC-5: Findings are report-only; a scan run mutates no file, asserted by comparing the tree before and after.
- [x] AC-6: A repository with no stale references produces no findings.
- [x] AC-7: This repository's own 32 stale journal references are reconciled, so the shipped guard `test_no_live_file_references_a_retired_wrapper` passes with the journal pattern active. Asserted by the guard itself, which routes through the shipped helper rather than a duplicated regex.
- [x] AC-8: The new patterns do not fire on historical records. Wave archives, plans, and the framework's own source are already excluded or protected; asserted so a closed-wave archive that legitimately narrates journal history is not reported as stale.

## Tasks

- [x] Remove the retired journal step from the editing-pass output and pin its absence with a test.
- [x] Add the journal system and the prompt-extension rename to the retired-surface list the scan walks.
- [x] Confirm the scan's report-only contract still holds for the new surfaces.
- [x] Reconcile this repository's 32 stale journal references to the typed-memory-record vocabulary that replaced them.
- [x] Census the seeds for any other retired surface with the same reference-lag shape; file separately rather than widening this change.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| journal-step | implementer | — | One-line removal plus a test that fails if it returns. Independent of the scan work. |
| scan-surfaces | implementer | — | Extend the existing list; do not build a second scan. |
| census | implementer | — | Other retired surfaces with lagging references. File, do not absorb. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`

## Affected Architecture Docs

`N/A`. This points existing machinery at two more surfaces and deletes one stale log line; no
boundary, contract, or flow decision.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The upgrade actively instructs a retired step on every run today. |
| AC-2 | required | The primary reported gap, roughly 90 sites in one repository. |
| AC-3 | required | Same gap, second surface; 41 references in one repository. |
| AC-4 | required | Per-line-first reporting would silently under-count, which is the failure mode being fixed. |
| AC-5 | required | The existing scan's contract; violating it would rewrite operator content. |
| AC-6 | required | A scan that cries wolf on clean repositories gets ignored. |
| AC-7 | required | The pattern cannot land green without it, and a framework that ships a staleness detector while carrying the staleness is its own counterexample. |
| AC-8 | required | Over-firing on archives would train operators to ignore the channel, which is the same end state as not reporting at all. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | Filed from downstream upgrade feedback spanning 1.13.0 to 1.16.1. Item 1 verified directly in the tree: the editing-pass output hardcodes the retired journal step, with an adjacent comment noting the label needed fixing. Items 2 and 3 are reported counts from the downstream repository (about 90 sites across 43 files; 41 references across 27 files) and are not yet reproduced here. | Field report; `upgrade_wavefoundry.py` editing-pass log block; existing retired-surface scan emitting `{file, line, retired_surface, matched, suggested}`. |
| 2026-08-12 | **Readiness council, code-grounded: the plan's mechanism claim is FALSE and the scope is corrected below.** `reconcile_scan.py` is not a generic retired-surface list. It carries TWO pattern families, and every pattern in both is hardcoded to a specific textual shape: `_LITERAL_PATTERN`, `_DYNAMIC_PATTERN` and `_VAR_BINDIR_PATTERN` all match the `.wavefoundry/bin/<name>` form, and `_TOOL_MCP_PATTERN` / `_TOOL_BARE_PATTERN` match `mcp__wavefoundry__<tool>` and bare tool tokens. Neither family can express a prose instruction (`Stop and journal when:`) or a path-extension rename (`docs/prompts/X.md` to `X.prompt.md`). Adding a name to `_RETIRED_SURFACE_REPLACEMENTS` would only make the scan look for `.wavefoundry/bin/journal`, which is meaningless. Items 2 and 3 therefore require NEW pattern families inside the existing scan, not a list extension. The Decision Log row rejecting "a new dedicated journal-reference scanner" as duplicative stands on its conclusion (stay inside one scan, one report-only contract, one findings shape) but not on its stated reason, and is corrected. | `reconcile_scan.py` `RETIRED_SURFACES` derived from `_RETIRED_SURFACE_REPLACEMENTS`; the five compiled patterns above. |
| 2026-08-12 | **Item 2 REPRODUCES in this repository: 32 live files** under `docs/` carry stale journal instructions (`Stop and journal when:`, `distill journals`, `Memory responsibility: journal`, `docs/agents/journals`), excluding wave and plan archives, which the cleanup policy protects as historical. The field report's diagnosis is confirmed at the source: the string is absent from `.wavefoundry/framework/seeds/`, from every renderer under `scripts/*.py`, and from `.wavefoundry/framework/install/`, so it is legacy install-time content that no migration reaches, exactly as reported. | `grep` over `docs/**` excluding `docs/waves/` and `docs/plans/`: 32 files; three negative checks against seeds, renderers, and install templates. |
| 2026-08-12 | **Item 3 does NOT reproduce here: zero stale references.** Every `docs/prompts/*.md` reference in live surfaces already resolves, so AC-3 needs a constructed fixture rather than the local corpus. Consistent with the plan's own "current seeds are clean" note. Recorded so nobody reads the local `docs/agents/wave-coordinator.md:15` as the cited breakage: that line is a downstream observation and the local line 15 is unrelated prose. | Resolver script over `docs/**` matching `docs/prompts/<name>.md` where `<name>.prompt.md` exists: 0 files, 0 refs. |
| 2026-08-12 | AC-1 delivered as a DELETION, not a rename, after checking what the cited step actually is. seed-160's step 0 is pack adoption; the log line called it journal reconciliation. So the line was wrong twice over and there is no current step to rename it to. Remaining steps renumbered 1-6, pinned by a contiguity assertion so a future removal cannot leave a gap. A pre-existing test asserted the retired step was PRESENT (wave 1p454's own AC-2); that assertion is INVERTED in place rather than deleted, so the reversal stays visible at the original site. | `test_editing_pass_does_not_instruct_the_retired_journal_step`; `test_editing_pass_steps_are_contiguously_numbered`; `test_next_steps_defers_to_seed_160` inverted; seed-160 step-0 references read directly. |
| 2026-08-12 | AC-2/AC-3 delivered as a THIRD pattern family in `reconcile_scan.py`, per the corrected scope. Journal shapes are matched by anchored patterns over the retired system's own vocabulary rather than the bare word "journal", because prose legitimately narrates history. The prompt-extension surface is RESOLUTION-based, not textual: a reference is stale only when its `.prompt.md` twin exists on disk, so a genuinely-`.md` prompt doc is never flagged. Same scan, same report-only contract, same findings shape; no second scanner. | `_RETIRED_CONTENT_PATTERNS`; `_stale_prompt_extension_hits`; `RetiredContentReferenceScanTests` 8/8. |
| 2026-08-12 | **False positive found by running the new scan against this repository, then fixed.** `Distill journals` is not only a retired instruction: it is the documented legacy alias of the LIVE **Migrate journals** command (seed-210). The first pattern flagged `AGENTS.md`'s shortcut table, which would have told operators to delete a working command's alias. Added a line-scoped exemption that names the live command, so it cannot silence a bare instruction that merely sits near one. This is why the scan was run against a real corpus before the tests were written rather than after. | `_LIVE_JOURNAL_MIGRATION`; `test_live_migrate_journals_alias_is_not_reported` asserts the alias line is exempt AND the instruction line on the next line still fires. |
| 2026-08-12 | **AC-4 caught a real defect in my own regex.** The prompt-extension pattern ended with `(?![\w.])`, which excludes a following period, so the LAST reference on a sentence-ending line was silently dropped: three references on one line reported two. That is precisely the under-count AC-4 exists to prevent, and it was found by the fixture rather than by inspection. Guard corrected to `(?!\w)`. | `test_every_stale_reference_on_one_line_is_reported` failed 2 != 3, then passed. |
| 2026-08-12 | AC-7 delivered: this repository's stale journal references reconciled, editable channel now empty. Final local count was **34 findings across 34 files**, not the 32 estimated at readiness; the readiness estimate used a hand-filtered grep, while the scan's own exclusion policy (which excludes `docs/waves`, `docs/reports`, `docs/agents/memory`, `.wavefoundry/framework`, `journals/` and test files) is the authority. 30 files took the two uniform replacements; four close-wave step descriptions were reconciled individually, including one inside an ASCII diagram in `.wavefoundry/README.md` verified not to be a generated surface first. **Gapfill:** the 30-file pass used a scripted replacement rather than MCP retrieval, which the retrieval posture names as legitimate for bulk-mechanical edits; the target set itself came from the scan, not from grep. | `scan_repo_channels(REPO_ROOT)` returns `([], [], [])`; `NoLiveReferenceToRetiredWrapperTests` passes with all three families active. |
| 2026-08-12 | One INTERMITTENT failure observed in `test_server_tools.py` (`MaybeRefreshIfStaleTests`, a background-refresh registry assertion) during a full run, then did not reproduce: the class passes in isolation, the whole file passes in isolation, and two subsequent full runs are green. Recorded as a flake rather than repaired, because there is nothing repaired to point at; it is unrelated to this change, which touches no index-refresh path. Do not treat this note as a diagnosis. | Failing full run vs `test_server_tools.MaybeRefreshIfStaleTests` 8/8 OK, `test_server_tools` 1692 OK in isolation, and a clean 7207/62 full run. |
| 2026-08-12 | Census closed with **nothing to file**, using two instruments with different blind spots per seed-209. Instrument A (retirement DECLARATIONS in seeds: "is retired", "was removed", "no longer exists") returned only the journal system and the bin wrappers the scan already covers. Instrument B (unresolvable TARGETS: `docs/**` directory references that do not resolve on disk) returned exactly one, `docs/agents/memory/pointers/`, whose three references all deliberately describe migrating away from it rather than instructing its use. A declaration-based instrument cannot see a surface retired without an announcement; a target-based one cannot see a retired surface whose directory still exists. Both agree there is no third instance. | Instrument A over `.wavefoundry/framework/seeds/*.md`; instrument B over live `docs/**` excluding archives; the three `memory/pointers` sites read individually. |
| 2026-08-12 | **Consequence the plan does not disclose, surfaced at readiness.** `test_no_live_file_references_a_retired_wrapper` asserts `scan_repo_channels(REPO_ROOT)` returns an EMPTY editable-channel list for this repository, deliberately routing through the shipped helper so the guard and the upgrade-time scan cannot diverge. Adding journal patterns to that helper therefore turns this repo's 32 stale files into suite failures the moment the pattern lands. That is not avoidable by construction and should not be avoided by excluding `docs/agents/**`, which is where the staleness lives. Landing the scan extension requires reconciling those 32 files in the same wave. | `tests/test_wf_cli.py` `NoLiveReferenceToRetiredWrapperTests.test_no_live_file_references_a_retired_wrapper` asserting `offenders == []` against `REPO_ROOT`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | Extend the existing retired-surface reconciliation scan rather than add migration-time rewriting. | Its report-only contract keeps operator-authored content under operator control, and one scan means one exclusion policy, one channel routing, and one findings shape. **Corrected at readiness:** the original reason given was that the scan "already performs this exact shape of work", which the code does not support. It performs a related shape, bound to `.wavefoundry/bin/<name>` and `mcp__wavefoundry__<tool>` literals. The conclusion survives; the reason was wrong and the work is larger than the plan implied. | Auto-rewrite references during migration (rejected: mutates operator content, and a wrong rewrite is harder to notice than a stale reference). A new dedicated journal-reference scanner (rejected: a second implementation of an existing scan, which is how the two marker families in the sibling change diverged — that reason holds independently of the mechanism correction). |
| 2026-08-12 | Reconcile this repository's own 32 stale journal references inside this wave rather than excluding `docs/agents/**` from the new pattern. | The staleness lives exactly where the exclusion would go, so excluding it would ship a detector aimed away from the only instance we can observe. Fixing our own surface is also the strongest available evidence that the pattern matches real staleness rather than a synthetic fixture. Operator chose this scope explicitly on 2026-08-12 when the size difference was presented. | Exclude `docs/agents/**` (rejected: defeats the purpose). Split the journal pattern and the cleanup into a later wave (offered and declined). Land item 1 only (offered and declined). |
| 2026-08-12 | Keep all three items in one change rather than splitting the one-line fix out. | They share a single theme, a single reviewer context, and two of the three share a mechanism. Splitting would triple the ceremony for no additional safety. | Three separate changes (rejected as disproportionate). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Reference matching could fire on legitimate prose that merely mentions journals historically, such as closed-wave archives. | AC-6 requires a clean repository to report nothing, and the framework's cleanup policy already protects historical records; exclusions belong in the scan's existing inclusion policy rather than in new logic. |
| Items 2 and 3 were counted downstream and are not yet reproduced in this repository. | The Progress Log records that distinction. Reproduce locally before claiming the counts; the ACs assert shapes rather than counts for that reason. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
