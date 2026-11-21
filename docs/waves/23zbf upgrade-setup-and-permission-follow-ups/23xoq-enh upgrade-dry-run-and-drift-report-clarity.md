# Upgrade Dry Run Logs the Extension Source and the Baseline Drift Report Says What to Do

Change ID: `23xoq-enh upgrade-dry-run-and-drift-report-clarity`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23zbf upgrade-setup-and-permission-follow-ups

## Rationale

Field feedback against v1.46.0 (item 5 in `.wavefoundry/work/23zbf/eval/waveforge-feedback-v1.46.0.md`, evaluated in `.wavefoundry/work/23zbf/eval/upgrade-and-backlog.md`) reports two problems in the upgrade preview path. The operator accepted both on 2026-11-21.

**The dry run prints the whole extension module.** `phase_dry_run` in `upgrade_wavefoundry.py` reads the incoming `upgrade_extensions.py` from the pack and prints every line between `── Extension module: … ──` and `── End extension module ──`. Wave 23z46 / change 23zia moved the seed diffs to a log file, so this block is now the largest part of dry-run output. An MCP caller loses most of it anyway: `wf_upgrade` caps its `output` at 60,000 characters.

**`lifecycle_baseline_drift` reports drift that no operator caused.** The comparison normalizes line endings and the `Last verified` date only. The renderer appends its own marker regions to several baseline prompts after it materializes them, so those local copies can never equal their template. The report also prints each finding as raw JSON with a state name and no instruction.

Evidence gathered on 2026-11-21. Probe scripts and their output are in `.wavefoundry/work/23zbf/planning/23xoq/`; the scratch targets lived in the session scratchpad, and nothing in this repository was rendered, upgraded or edited.

- Executed: `upgrade_extensions.py` at HEAD `737d742e` has 4,684 lines. Verified by reading: `_read_extension_source` has one caller, in `phase_dry_run`, so an apply run never prints the source.
- Executed, and it widens the evaluator's claim: a pristine target reports five drifted baselines, not two. The scratch target held only `git archive HEAD .wavefoundry/framework`, the real renderer ran once against it, and `lifecycle_baseline_drift` then compared the ten baselines with the same framework's templates. It returned `upstream_unchanged_local_differs` for the `create-wave`, `implement-wave`, `prepare-wave`, `review-wave` and `close-wave` prompts (`probe_drift_pristine.out`).
- Executed: the renderer writes two marker forms into those five files. `create-wave` and `review-wave` carry `<!-- wave:<name> begin … -->` regions (`executable-review-evidence`, and `context-efficiency-carrier` on `create-wave`). `implement-wave`, `prepare-wave`, `review-wave` and `close-wave` carry a `<!-- wavefoundry:review-policy:begin -->` region. The shipped templates carry no HTML comment at all.
- Executed: masking only the `wave:<name> begin` form, as the evaluator proposed from `chunker._strip_waveframework_marker_regions`, still leaves four findings. A prototype that masks all three marker pairs on both sides and collapses the whitespace seam returns no finding on the pristine target (`probe_mask_pristine.out`).
- Executed on a copy of the pristine target with the same prototype: a sentence added outside any region still reports; a word changed inside a region does not; and a region whose end marker was deleted still reports, because a begin marker with no end marker masks nothing (`probe_mask_edited.out`).
- Executed: deleting a local baseline and running the renderer again materializes it from the template with its regions, and the prototype then reports nothing for that file (`probe_rematerialize.out`).
- Executed read-only against this repository: eight findings before masking and eight after. Its prompts are hand-customized, so the masking hides no real difference here (`probe_selfhost.out`).
- Executed on macOS: `contained_files.write_contained_bytes` creates a missing `.wavefoundry/logs/` folder, writes the module's bytes unchanged, and rewrites an existing file when given its identity (`probe_write.out`).
- Verified by reading: the comparison runs in the incoming renderer. `upgrade_extensions.lifecycle_baseline_report` loads the pack's `render_agent_surfaces.py` in a private child through `_incoming_renderer_query`, on the dry run (`post_extract` with `dry_run=True`) and before extraction (`pre_extract`). Both the incoming extension and the runner's summary print each finding with `json.dumps`, so a key added to a finding appears in every existing print.
- Verified by reading: the renderer accepts older spellings of two of these markers and rewrites them (`waveframework:executable-review-evidence`, and `wavefoundry:context-efficiency-carrier` in `context_efficiency._LEGACY_CONTEXT_EFFICIENCY_MARKERS`).

## Product Intent

Operators and agents who preview or run an upgrade of a target repository benefit.

**Drift report (first outcome).** Before: every project sees at least five drift findings on every upgrade and dry run, for prompts nobody edited, with no instruction. After: a baseline that differs from its template only inside regions the renderer owns reports nothing, and each remaining finding states whether to overwrite the local copy, merge by hand or preserve it. This comes first because it reaches every project and acts on the upgrade that installs it. An operator demonstrates it by running a dry run on an untouched install and seeing `none`. AC-4, AC-5 and AC-6 together establish it.

**Dry-run output (second outcome).** Before: a dry run prints 4,684 lines of extension source. After: it prints the module's name, digest, line count and the path of a log file that holds the exact source. AC-1 and AC-2 together establish it. It is independent of the first outcome and can ship without it.

Boundaries: the report stays advisory, never changes a project file and never changes the exit status. The extension source stays available for safety review, in a file. The dry-run change is runner code, so it first shows on the upgrade after the one that installs it; the operator can observe it then (Requirement 9).

## Requirements

1. **Extension module summary on stdout.** When the selected pack carries an extension module, the dry run must not print the module's source. It must print the zip entry name, the SHA-256 of the entry's bytes as 64 hexadecimal characters, the entry's line count, and the repository-relative path of the log file from Requirement 2. The `── Extension module: … ──` and `── End extension module ──` banners go away with the source. The lines for no pack and for a pack without an extension module stay as they are.
2. **Extension module log.** The dry run must write the entry's exact bytes to `.wavefoundry/logs/upgrade-extension-module.preview.log` through the contained-file writer, the same call the seed diff preview uses.
   1. The file holds the bytes as read from the pack, with no decoding, newline translation or timestamp prefix, so a SHA-256 of the file equals the printed digest on every platform.
   2. The dry run must name the file in its final line and in the summary's `preview_logs`, and must never print the file's content. `phase_dry_run` prints the text of each migration preview log the incoming hook writes (verified by reading), so this file must stay out of that printing.
   3. A dry run with no pack, or with a pack that has no extension module, writes no file, prints no path, and leaves an existing file untouched.
   4. A write failure prints one warning that names the zip entry, so the operator can read the source from the pack. The name, digest and line count still print, no path prints, the file is not listed in `preview_logs`, and the dry run continues with its exit code unchanged. The dry run does not fall back to printing the source.
   5. An apply run writes no extension module log. It never printed the source.
3. **No new flag.** The runner gains no `--verbose` flag and no environment switch for the source print (see the Decision Log).
4. **Mask renderer-owned regions in the drift comparison.** `lifecycle_baseline_drift` must ignore every region the renderer owns in a baseline destination, on both sides of each comparison (the local copy, the incoming template and the previous template).
   1. The set is derived by rule, not by list: a region is renderer-owned when the renderer writes it into a destination registered in `_lifecycle_prompt_baselines()` or `scaffold_baselines()`. At HEAD the rule yields three marker pairs: `REVIEW_POLICY_SURFACE_MARKER_BEGIN` and `_END`, `REVIEW_PROTOCOL_MARKER_BEGIN` and `_END`, and `CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN` and `_END` (executed, see the Rationale). The governing check is AC-4: a target rendered by the real renderer reports nothing against its own templates, so a region added to the renderer without its mask fails that test.
   2. Each older spelling of those markers that the renderer itself accepts and rewrites must be masked too, so a target rendered by an older framework does not report the region once.
   3. A region is masked from its begin marker through its matching end marker, with the whitespace the renderer inserts around it. A begin marker with no matching end marker masks nothing.
   4. Text outside the regions is compared exactly as today: line endings and the `Last verified` date are the only other normalizations. Mask only marker names and accepted spellings the renderer writes or migrates in that specific destination. Preserve a project-owned region even when its markers follow the same syntax or the renderer owns that name in another file.
5. **Each finding says what to do.** Every `lifecycle_baseline_drift` finding must carry an `action` string beside `channel`, `file` and `detail`. It starts with one of three tokens, then a colon and one fixed sentence.
   1. `upstream_changed_local_matches_previous` gives `overwrite`: the local copy is the previous template unedited, so taking the incoming template loses no project text.
   2. `upstream_changed_local_differs_from_previous` gives `merge`: keep the local copy and merge the incoming template's changes by hand.
   3. Both states give `preserve`, with distinct instructions. For `already_current`, keep the current copy. For `upstream_unchanged_local_differs`, compare the local copy with the current template. Follow the overwrite procedure only after confirming the difference is an unapplied template update and there are no project edits to keep.
   4. `baseline_unknown` gives `preserve`: the comparison is unavailable, so compare by hand before replacing anything.
   5. The `detail` string of every state stays byte-identical to today's, so a consumer that reads the state from `detail` is unaffected. The mapping from state to action lives in one place in the renderer.
   6. The two `baseline_unknown` findings built outside the renderer (the incoming extension's unavailable-comparison notice and the runner's missing-capture notice) carry the same `action`.
6. **The report stays advisory.** The upgrade and the dry run never replace, refresh or delete a baseline, and a finding never changes an exit code. `overwrite` is advice. Seed 160 must state how an operator performs it: after the upgrade completes, delete the local copy and render surfaces (`wf_sync_surfaces`, or `wf render-surfaces`), which materializes the incoming template and its regions (executed, see the Rationale).
7. **Documentation.** Seed 160, the rendered `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`, the `phase_dry_run` docstring, the `--dry-run` help text and the `wf_upgrade_response` docstring must describe the new behavior: the extension module log and its summary, the region masking, the `action` key with its three tokens, and the overwrite procedure. Seed 160's sentence that a difference "does not establish customization or permission to replace a file" must be revised to match Requirement 5.1: an `overwrite` finding establishes that the local copy holds no project text outside renderer regions; replacing it remains the operator's choice.
8. **Platforms.** Behavior is the same on Windows, macOS, Linux and WSL2.
   1. The log path prints repository-relative with forward slashes on every platform, as the seed diff path does.
   2. The log is written as bytes, so native Windows applies no newline translation and the digest matches (Requirement 2.1). The contained-file writer is the one the seed diff logs already use; its behavior on native Windows is `inferred` from that shared call and was not executed for this plan.
   3. The mask runs after the existing line-ending normalization, so a CRLF checkout on native Windows compares the same as an LF checkout. WSL2 is POSIX, including on a `/mnt/c` checkout.
   4. The dry run opens no console and spawns no new child for either part.
9. **Transition disclosure.** Seed 160 and the changelog bullet must state which part acts when.
   1. The region masking and the `action` key act on the installing upgrade and its dry run, including when a supported older runner drives it, because the incoming extension computes the report with the incoming renderer. This is verified by reading and `inferred` for the frozen old-runner contexts until AC-6.4 runs.
   2. The extension module summary and log are runner code. The installed runner performs the installing dry run and still prints the full source there; the new output first shows on the next upgrade. The text must say that this is expected and is not this change failing.
   3. The runner's own missing-capture notice gains its `action` on the next upgrade for the same reason.

## Scope

**Problem statement:** The upgrade dry run prints 4,684 lines of extension source, and the lifecycle baseline drift report fires for regions the renderer itself wrote and gives no instruction.

**In scope:**

- The extension module summary and preview log in `phase_dry_run`.
- Region masking in `_compare_lifecycle_baselines` and the `action` key on every finding.
- The `action` key on the two fallback findings in `upgrade_extensions.py` and `upgrade_wavefoundry.py`.
- Seed 160, the rendered upgrade prompt in this repository, the MCP tool reference, the architecture flow, three docstrings or help texts, and the changelog.
- Tests for both parts, including a pristine-render fixture that the drift suite lacks today.

**Out of scope (each a recorded DECLINE):**

- A `--verbose` flag that restores the source print. DECLINE: the log file keeps the source one read away, a flag cannot reach the installing upgrade, and it would add a pass-through to the dispatcher and the MCP handler for no reported need.
- Moving convention hook scripts out of dry-run output. Operator decision 2026-11-21: DECLINE; they stay printed in the dry run. They are project-owned files already on disk at the path the dry run prints, they are short, and no report names them.
- Printing findings as prose instead of JSON. DECLINE: supported older runners print each finding with `json.dumps`, so the `action` key reaches every output with no second format.
- Suppressing `upstream_unchanged_local_differs`. DECLINE: it is the only signal that a local copy diverges from its template; with masking it now fires only for a real difference, and its action asks the operator to compare the files before deciding whether to take an unapplied template update.
- Replacing a baseline automatically when the action is `overwrite`. Operator decision 2026-11-21: DECLINE. Baseline prompts are project-owned and the report performs no refresh by recorded decision (seed 160); the operator performs the documented two-step procedure.
- A summary field for the extension module digest. DECLINE: no consumer is identified; stdout and the file carry it.
- Making the dry-run change act on the installing upgrade. DECLINE: the installed runner prints the source before any incoming code runs, and incoming code cannot remove what was already printed.
- Editing the frozen old-runner fixtures under `tests/fixtures/upgrade_old_runner/`. DECLINE: they record what older runners print and must keep printing the source.

## Acceptance Criteria

Intent is established by AC-4, AC-5 and AC-6 together for the drift report and by AC-1 and AC-2 together for the dry run.

- [x] AC-1: A dry run of a pack that carries an extension module prints a summary and no source. Oracle: a test drives the real dry-run entry with a real pack whose extension module contains a sentinel line that appears nowhere else. Against the current code the sentinel and the end banner are in stdout, so the criterion fails with the change absent.
  1. Stdout does not contain the sentinel line or `── End extension module ──`.
  2. Stdout contains the zip entry name, the entry's line count and the path `.wavefoundry/logs/upgrade-extension-module.preview.log`.
  3. Stdout contains the SHA-256 that the test computes itself from the zip entry's bytes.
- [x] AC-2: The log holds the exact module and is disclosed. Oracle: the test's module fixture uses CRLF line endings and one non-ASCII character. An implementation that writes decoded or newline-translated text fails the byte comparison.
  1. The file's bytes equal the zip entry's bytes.
  2. The dry run's final line names the file and the summary's `preview_logs` lists it.
  3. The exit code is 0 and no upgrade lock exists.
- [x] AC-3: The edge cases of Requirement 2 hold. Oracle: tests through the real dry-run and apply entries.
  1. A dry run with a pack that has no extension module prints the existing `none` line, writes no file, and leaves a file from an earlier dry run byte-identical.
  2. When the log cannot be written (the target path is refused by the contained-file writer), the dry run exits 0, prints the name, digest and one warning that names the zip entry, prints no log path, omits the file from `preview_logs`, and still does not print the sentinel. Fails when a write error aborts the dry run or triggers a source print.
  3. An apply run of the same pack writes no `upgrade-extension-module` log.
- [x] AC-4: A target whose baselines the real renderer just materialized reports no drift against that framework's own templates. Oracle: a test renders a scratch target through the public render entry, then calls the public `lifecycle_baseline_drift` with the same templates and expects an empty list. Executed: the current code returns five findings, and a mask for the `wave:<name> begin` form alone returns four, so neither satisfies it.
- [x] AC-5: Masking hides only renderer-owned regions. Oracle: tests with literal fixtures, each starting from a rendered baseline.
  1. A sentence added outside every region reports `upstream_unchanged_local_differs`.
  2. A change inside a region only reports nothing.
  3. A region whose end marker is removed reports a finding, and a sentence added after that begin marker is still detected. Fails for a mask that runs from a begin marker to the end of the file.
  4. A baseline that carries an older accepted spelling of a region marker reports nothing.
  5. When the incoming template differs from the previous one and the local copy is the previous template plus its renderer regions, the state is `upstream_changed_local_matches_previous`. Today the same input reports `upstream_changed_local_differs_from_previous`.
  6. Add a paired project-owned marker region to a baseline, then change the incoming template. The report retains that difference and recommends `merge`. Repeat with a marker the renderer owns in a different destination. Neither case may recommend `overwrite`.
- [x] AC-6: Every finding carries the action for its state. Oracle: the test's expected mapping is a literal table, not a call to the producer.
  1. The five states map to `overwrite`, `merge`, `preserve`, `preserve` and `preserve` as Requirement 5 lists, and each `action` starts with its token and a colon.
  2. Each state's `detail` string is byte-identical to the string the current code produces for the same input. Fails for an implementation that appends the instruction to `detail`.
  3. The incoming extension's unavailable-comparison finding and the runner's missing-capture finding each carry a `preserve` action.
  4. With a supported older runner context driving the incoming `post_extract` dry-run hook and the `pre_extract` hook, the printed and captured findings carry `action`. Fails when the action is added only in runner code.
  5. A finding does not change the dry-run or apply exit code, and the local baseline bytes are unchanged after the report.
  6. Run the comparison for an upgrade from template N to N+1 with an untouched local copy of N. It recommends `overwrite`. Advance the installed templates to N+1 and leave the local copy at N. A second comparison against N+1 recommends `preserve` and explains how to recognize and take the unapplied update. An already-current copy never gets that instruction.
- [x] AC-7: The documented overwrite procedure works. Oracle: for a baseline with an `overwrite` finding, a test deletes the local copy, runs the public render entry, and the report against the incoming template then lists nothing for that file while the file carries its renderer regions. With the masking absent the re-rendered file reports drift again, so the criterion fails without the change.
- [x] AC-8: The documents of Requirement 7 describe the delivered behavior. Oracle: a test or reviewer check on the named files.
  1. Seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` name `.wavefoundry/logs/upgrade-extension-module.preview.log`, the region masking, the `action` key with its three tokens, and the overwrite procedure with both commands.
  2. Seed 160 no longer states without qualification that a difference does not establish permission to replace a file.
  3. Seed 160 and the changelog bullet carry the transition statement of Requirement 9, including the sentence that the installing dry run still prints the source.
  4. The `--dry-run` help text, the `phase_dry_run` docstring and the `wf_upgrade_response` docstring no longer say the dry run prints or surfaces the extension module source on stdout.
  5. `docs/specs/mcp-tool-surface.md` and `docs/architecture/data-and-control-flow.md` describe findings as `{channel, file, detail, action}` and name the masking.
- [x] AC-9: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`. List the tests that read the extension module banners or a finding's exact keys before editing (known at plan time: `tests/test_upgrade_docs_preflight.py` splits output on `── End extension module ──`; `tests/test_lifecycle_baseline_drift.py` is the only suite that names `lifecycle_baseline_drift`, by an executed search of `scripts/tests`).
- [x] In `_compare_lifecycle_baselines`, mask renderer-owned regions in `comparable()` per Requirement 4, including the older accepted spellings and the unpaired-marker rule.
- [x] Add the state-to-action mapping in `render_agent_surfaces.py` and set `action` on every finding the comparison builds.
- [x] Add the `preserve` action to the unavailable-comparison finding in `upgrade_extensions.lifecycle_baseline_report` and to the missing-capture finding in `upgrade_wavefoundry._lifecycle_baseline_findings`.
- [x] In `phase_dry_run`, replace the source print with the summary of Requirement 1, write the preview log from the entry's bytes, add it to `preview_logs`, and keep it out of the migration preview printing. Read the entry as bytes so the digest and the file agree.
- [x] Update the `phase_dry_run` docstring, the `--dry-run` help text and the `wf_upgrade_response` docstring. Refresh the handler-digest pin in `tests/test_mcp_tool_registry.py` if the docstring edit rotates it (`unverified` whether it does).
- [x] Tests for the dry run: sentinel pack, independent digest, CRLF and non-ASCII byte equality, final line and `preview_logs`, no-module pack, refused write, apply run. Adjust `tests/test_upgrade_docs_preflight.py` for the removed banner.
- [x] Tests for the report: the pristine-render fixture (AC-4), the destination-specific masking cases (AC-5), the two-upgrade stale-copy case (AC-6.6), the literal action table, unchanged `detail` strings, both fallback findings, the older runner context (AC-6), and the overwrite procedure (AC-7).
- [x] Open `seed_edit_allowed`. Update seed 160: the dry-run extension module log, the drift report section (masking, `action`, overwrite procedure, the revised permission sentence) and the transition statement. Close the gate.
- [x] Update `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/specs/mcp-tool-surface.md` and `docs/architecture/data-and-control-flow.md`.
- [x] Add an operator-facing bullet to the `## [Unreleased]` section of the root `CHANGELOG.md` that covers both parts and the transition, ending "Wave 23zbf / 23xoq.".
- [x] Run the declared test profile for the upgrade and render suites, then the full framework suite last. Close `framework_edit_allowed`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| drift-masking-and-action | implementer | none | `render_agent_surfaces.py`, the two fallback findings |
| dry-run-extension-log | implementer | none | `phase_dry_run`, docstrings and help text |
| docs-and-seed | docs-contract | drift-masking-and-action, dry-run-extension-log | seed 160, rendered prompt, tool reference, architecture flow, changelog |
| verification | qa | all | pristine-render fixture, byte-exact log, older runner context, full suite last |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_baseline_drift.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_docs_preflight.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

Ordering: sibling `23xor-enh setup-checkpoint-recovery-wording` is expected to edit `upgrade_wavefoundry.py` and seed 160 as well (per the evaluation's file list; its spec was not yet authored when this one was written, so the overlap is `unverified`). The two changes touch different functions and different seed sections; land them one after the other.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md`: the upgrade preview paragraph gains the region masking and the `action` key in the baseline comparison, and the dry-run description names the extension module log.
- `docs/specs/mcp-tool-surface.md`: the `wf_upgrade` entry's dry-run bullet names the extension module preview log and the finding shape.
- `docs/architecture/layering-rules.md`: unchanged. The comparison already runs in the incoming renderer, the dry run already uses the contained-file writer, and no import edge is added.
- No ADR. The change moves no ownership boundary and adds no flow step.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The field request: the source leaves stdout |
| AC-2 | required | The safety review the dry run promises needs the exact source, on Windows too |
| AC-3 | important | A preview must not fail or mislead on its edge cases |
| AC-4 | required | The executed defect: an untouched install reports five findings |
| AC-5 | required | A mask that hides project edits would be worse than the false findings |
| AC-6 | required | The field request: say whether to preserve or overwrite, on the installing upgrade |
| AC-7 | required | The overwrite advice must be a procedure that works |
| AC-8 | required | Agents follow seed 160; stale text would send them looking for printed source |
| AC-9 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-21 | Real scratch installs produced zero drift after rendering and preserved project edits through a two-upgrade comparison. The frozen v1.22.0 runner loaded the incoming extension, printed the action on a dry run and retained it at pre-extraction. The public summary and MCP response replayed the captured findings. | 56 focused preview, drift and containment tests passed. Disabling the destination mask failed the pristine-install check. A test writer that translated CRLF to LF failed the exact-byte assertion on a UTF-8 module. These are local fixture observations. Downstream adoption was outside this run. |
| 2026-11-21 | Readback: a fresh render should report no baseline drift. A project edit outside its owned marker must survive and yield merge on an incoming template change. A dry run writes exact module bytes to a contained preview log and prints its identity, even when the log fails. | Work on the renderer, incoming hook, runner, tests and upgrade documentation. Exercise the installed runner and incoming hook independently. Existing tests pin old banners, exact returned keys, helper text and the final preview-log list. |
| 2026-11-21 | Spec authored from field feedback item 5 and the operator-accepted verdicts 5.1 and 5.2. The pristine-install comparison the evaluator did not run was executed: five baselines drift, through two marker forms, which widens the claim from two files and rules out the proposed single-form mask. | Probe scripts and output under `.wavefoundry/work/23zbf/planning/23xoq/`; Rationale evidence list |
| 2026-11-21 | The operator accepted the three planning recommendations: `action` is a new key, `overwrite` stays advice only with no automatic replace, and convention hook scripts stay printed in the dry run as a DECLINE. No requirement or acceptance criterion changed. | Decision Log rows and Scope bullets marked Operator decision 2026-11-21 |
| 2026-11-21 | Repaired the two QA readiness findings. Requirement 4.4 and AC-5.6 protect project-owned regions. Requirement 5.3 and AC-6.6 distinguish an unapplied template update from a current copy. | R1-23xoq-lookalike-region-mask and R1-23xoq-preserve-hides-stale-copy; independent verification pending. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-21 | Dry run: print the module's name, digest and line count, and write the exact source to `.wavefoundry/logs/upgrade-extension-module.preview.log`. | It follows the 23zia seed diff pattern, so it reuses one writer and the existing `preview_logs` disclosure, and it keeps the safety review one file read away. Efficacy: replaying the field case, 4,684 printed lines become a few; the mechanism controls the output; it misses convention hook scripts, which stay printed by a recorded DECLINE; it does nothing on the installing dry run, which the old runner performs (disclosed). Success measure: on the upgrade after the installing one, dry-run stdout contains no extension source line. | A `--verbose` flag (operator direction: only with a strong reason; none found: a flag cannot reach the installing upgrade, needs dispatcher and MCP pass-through, and doubles the paths to test). Drop the print with no file (breaks the documented safety review and needs an unzip tool, which is awkward on native Windows). Print a truncated head (a partial module cannot be reviewed). |
| 2026-11-21 | Write the log from the zip entry's bytes, not from decoded text. | A hash of the file then equals the printed digest on every platform, and native Windows cannot alter line endings. The current reader decodes to text, which the summary no longer needs. | Write the decoded text (digest and file can disagree after newline translation). |
| 2026-11-21 | Drift report: mask renderer-owned regions inside the comparison, on both sides, with the set derived by rule and proven by a pristine-render test. | Executed: it turns five false findings into none on a pristine target and keeps every real difference in the probes. Efficacy: the mechanism runs in the incoming renderer, so it fixes the installing upgrade; the report is advisory, and the `action` key is what makes someone act; it hides an edit made inside a region, which the next render overwrites anyway; it reports a region whose markers were hand-deleted, which is a real difference; the marker constants and upsert code already exist, so no new registry is needed. Success measure: an untouched install's dry run prints `none`, and field reports of permanent drift on unedited prompts stop. | Mask the `wave:<name> begin` form only, reusing the chunker's pattern (executed: four of five findings remain, because the review-policy region uses a different marker form). Render the regions into the template and compare whole files (region bodies differ between the installed and incoming renderer, so it would report again on every release that edits a region). Drop the `upstream_unchanged_local_differs` state (hides real project edits). |
| 2026-11-21 | Operator decision 2026-11-21: carry the instruction in a new `action` key and leave `detail` unchanged. | Every existing print, in old and new runners, dumps the finding as JSON, so a new key reaches the operator on the installing upgrade with no print change, and consumers that read the state from `detail` keep working. | Append a phrase to `detail` (the evaluator's sketch; changes strings that tests and any summary consumer compare). Print prose lines (older runners would still print JSON). |
| 2026-11-21 | Operator decision 2026-11-21: `overwrite` stays advice only, with a documented procedure and no automatic replace. | Baseline prompts are project-owned and the report's no-refresh rule is a recorded decision in seed 160. Executed: delete and re-render materializes the incoming template with its regions. | Replace matching baselines automatically (a new write path over project files, and incoming code cannot know an operator's intent). |
| 2026-11-21 | Operator decision 2026-11-21: convention hook scripts stay printed in the dry run, recorded as a DECLINE. | They are project-owned files already on disk at the path the dry run prints, they are short, and no field report names them. | Move them to a preview log beside the extension module (new output for files the operator already owns and can open). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A future renderer region in a baseline destination has no mask and the false findings return. | AC-4 renders with the real renderer, so the suite fails when a region is added without its mask. |
| The mask hides an operator edit placed inside a renderer region. | Accepted: the renderer overwrites such an edit on the next render. AC-5.3 keeps an unpaired marker from hiding text outside a region. |
| A target rendered by a much older framework carries a marker spelling the mask does not know, and reports that region once. Status: `inferred`; only the two older spellings found by reading are covered. | Requirement 4.2 covers every spelling the renderer accepts; the finding's action is `preserve` or `merge`, never a wrong `overwrite`, because an unmasked region makes the local copy differ. |
| `overwrite` is shown for a file whose only differences were inside regions, and the operator deletes it. | The procedure re-renders the regions (AC-7), so nothing outside the renderer's ownership is lost. |
| The contained-file writer behaves differently on native Windows for the new file. Status: `inferred` safe, because the seed diff logs use the same call; no native Windows run was made for this plan. | The write failure path prints a warning and continues (AC-3.2). Windows byte fidelity is asserted with a CRLF fixture on the test platform (AC-2). |
| Operators read the installing dry run's full source print as this change failing. | Requirement 9 puts the transition sentence in seed 160 and the changelog. |
| A docstring edit in `upgrade_handlers.py` rotates a handler-digest pin. Status: `unverified`. | The task names the pin's test file. |
| Sibling `23xor` edits the same runner file and seed. Status: `unverified` until its spec exists. | Serialization Points list both files; the ordering note sequences the two changes. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
