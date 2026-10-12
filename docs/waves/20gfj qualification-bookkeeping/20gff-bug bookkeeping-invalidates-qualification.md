# Preserve qualification during routine wave bookkeeping

Change ID: `20gff-bug bookkeeping-invalidates-qualification`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-12
Wave: 20gfj qualification-bookkeeping

## Rationale

Routine progress and review recording must preserve completed work while keeping material-change checks and detection of tests writing outside their fixtures. The canonical suite recently passed its tests, but the runner refused a green receipt because the coordinator appended a review event while it ran. Another full qualification was required without a source change. Repair the existing boundaries, without copied checkouts, additional approval stages or permanent evidence files.

Discovery separates two mechanisms: `run_tests.py` treats almost every tracked-file change as a test leak; `review_evidence.py` already keeps ordinary ledger entries from invalidating unrelated approvals. Separately, authored Session Handoff prose in a change document can change its readiness digest. Existing Progress Log and session handoff carriers already support continuation updates without changing the approved plan.

## Requirements

1. With unchanged verification inputs and passing tests, concurrent external routine bookkeeping must not prevent the canonical runner from writing its existing green receipt. Derive bookkeeping from canonical append-only review events, validated generated views and existing normalized progress/status/completion carriers; a filename alone is insufficient.
2. Preserve detection or refusal of accidental worker writes into the real repository, including valid typed-ledger publication. Cover full/focused execution, optional qualification reporting, fork descendants, ordinary environment-inheriting Python exec children, and canonical publication API descendants. The selected test-only bootstrap is an accidental-write guard, not writer authentication or an OS sandbox; isolated Python, disabled site initialization, deliberately cleared bootstrap environment, native writes and pre-opened descriptors have the limits below. Unclassified changes remain failures with actionable diagnostics.
3. Source, test, configuration, edit-gate and material plan changes remain consequential. Ledger corruption, truncation and rewriting prior records cannot qualify for the exemption. Findings and repairs retain their existing effect on the appropriate review phase and lanes.
4. Ordinary progress recording must not rotate readiness authority, request another reviewer run or rerun the suite. Reuse existing normalized carriers; do not broadly exclude authored plan prose or change the review authority protocol.
5. Close and package reuse a matching green receipt under their existing rules. Add no extra qualification, historical-wave scan, ledger rewrite, network operation or evidence creation to installation/upgrades.
6. Correct guidance that still requires quiet bookkeeping or encourages continuation edits in substantive plan sections. Update canonical seeds first and render affected local guidance. Retain concise durable results in the existing wave/change records and typed ledger.

## Scope

**In scope:** Narrow runner classification and the minimum worker/write-boundary support needed to preserve leak detection; focused runner and approval-currency controls; affected canonical guidance and testing/build documentation.

**Out of scope:** General qualification snapshots, copied-checkout defaults, blanket ledger/docs exclusions, new receipts or permanent evidence folders, test scheduling redesign, weakened integrity checks, historical cleanup and unrelated upgrade work. Broad canonicalizer changes or approval migration require an explicit scope decision before readiness.

## Selected Design

Use the existing runner and its in-memory before/after state, with two complementary checks. Do not copy the checkout, add another receipt, or require an operator procedure.

1. **Classify only existing canonical carriers.** Extend `run_tests.py` to keep bytes for existing wave records, admitted/planned change documents and their declared sibling review ledgers, using `record_paths` and `vocabulary_profile` rather than hard-coded folder names. All other tracked/non-ignored changes and the edit-gate file retain their existing consequential behavior. New/deleted carrier files, symlinks, malformed carriers and uncertain classification fail the guard. No whole `docs/` or ledger-path exclusion is allowed.
2. **Validate ledger appends, not merely JSON.** An eligible ledger must belong to an existing wave that declares external review authority. Both endpoints must pass `parse_review_event_bytes` and `validate_review_evidence_records`; the old bytes must be an exact prefix of the new bytes. A bookkeeping exemption must not include a new policy receipt or change previous rows. Validate the generated finding/status views against the canonical renderer and corresponding endpoint ledger; only that generated delta, existing telemetry regions, and the existing progress/status/completion normalization can be tolerated. Capture related ledger/view bytes under the existing project publication lock, only for the short observation phase; never hold it while tests execute or introduce another lock file. A bounded inability to obtain a consistent observation fails with its reason.
3. **Reuse the existing plan normalization.** Compare `gardener_metadata.canonical_review_policy_body` for recognized change documents, and for the authored remainder of recognized wave records after validated generated regions are removed. This preserves dates, status, ordinary `[ ]`/`[x]` completion and the canonical `## Progress Log` carrier. AC `[~]`, labels, scope, requirements and substantive Session Handoff prose remain material. Do not expand the normalizer or treat the standalone session-handoff file as an unvalidated filename exception. Routine continuation belongs in Progress Log or the existing session handoff outside the qualification observation window.
4. **Prevent supported workers from exploiting those tolerances accidentally.** Add a small, test-activated `test_worker_guard.py` helper and `test_worker_bootstrap/sitecustomize.py` startup shim. The runner supplies an inherited protected-root/carrier description and adds only the bootstrap directory to the child Python search path, preserving existing entries and existing site customization. Install the Python audit hook before test imports for both ordinary and optional-report workers; make installation idempotent. Refuse writes to the real repository's exemption-capable record carriers through audited `open`/`os.open`, replacement/rename, deletion and relevant link/directory mutation operations. Resolve relative paths and ordinary symlink aliases; handle supported `dir_fd` operations explicitly or refuse uncertain protected targets. Fixture roots outside the protected repository remain writable. Fork inherits the hook; ordinary Python exec children inherit the site bootstrap. Preserve outer protected roots when a test launches a nested runner.
5. **Guard canonical publication too.** At `review_evidence.project_state_publication_lock`, reject a test-worker-marked attempt to publish into its protected real repository before mutation. The inherited marker is a cooperative guard, not an identity proof. It catches canonical API descendants even when their Python launch omits site initialization. Real external coordinator processes have no marker and keep the ordinary API path. No approval evaluation, ledger format or policy digest change is planned.
6. **Keep source qualification independent.** Recompute the framework input hash after successful execution and before writing the existing receipt. If it differs from the pre-run hash, fail without a new green receipt, even when size/mtime were restored. Retain full/focused/schedule-control guarding and optional-report success/failure agreement. Close, install and upgrade gain no new work or code path; packaging changes only the source membership described below, with no new qualification step.

**Bootstrap, registration and distribution contract.** The new flat `test_worker_guard.py` is a stdlib-only library with no `__main__` launcher and no import-time hook installation. `review_evidence` reaches its protected-root refusal helper, so it is a declared shipped dependency, despite activation being restricted to runner-marked processes. Add `test_worker_guard` to `mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES`; retain the existing stock and declared-profile census in `tests/test_extension_tool_modules.py` and add a focused registration/reachable-dependency control there. Do not list the nested `test_worker_bootstrap/sitecustomize.py` in the flat-module roster, register it as an extension, or add an `__init__.py` solely to package it.

The ordinary main-worker command remains `-B` and explicitly imports/installs `test_worker_guard` before invoking unittest discovery (a short `-c` entry using `runpy` is sufficient); the optional qualification worker explicitly installs it before discovery too. Main-worker installation failures are fatal, independently of Python's normally nonfatal site-hook import diagnostics. The inherited shim loads the same helper by its adjacent source path, reuses its stable `sys.modules` identity and calls the idempotent installer; it need not add the whole framework scripts directory to descendant import search paths. No new worker launcher file is needed.

Prepend one resolved bootstrap directory to the inherited `PYTHONPATH`, retain every other entry in order and deduplicate only that injected directory. After installing the marked-worker guard, the shim searches the remaining normal filesystem path for the next `sitecustomize` using `importlib.machinery.PathFinder`, excluding every alias of its own directory, and executes that module once with its original spec/loader and normal `sitecustomize` module identity. If none exists, do nothing. Test a pre-existing file-based customization (including one that imports sibling code), missing customization, repeated/nested startup and unchanged no-marker behavior. Do not intercept or rewrite arbitrary subprocess commands, install a global hook, or claim equivalent handling of third-party custom meta-path importers. Failure in the inherited customization retains ordinary Python site-startup behavior; failure of the main-worker guard is separately fatal as above.

Keep `test_worker_guard.py` in the source pack because `review_evidence` imports it. Add only `scripts/test_worker_bootstrap` to `build_pack.EXCLUDED_REL_PATHS`; the nested startup shim is source-host test infrastructure, alongside the already excluded runner/tests. Do not change existing `qualification_worker.py` membership as unrelated cleanup. Extend `tests/test_build_pack.py` with a miniature pack/manifest control proving helper inclusion, shim-directory exclusion and successful production dependency availability with no marker. No release build, new artifact or upgrade step is required by this change.

Both new Python files are covered by `tests/test_bytecode_cache.py`'s recursive source census, but neither is a direct executable entry. Preserve the library rule: no unconditional import-time bytecode flag/cache configuration, no new pinned exemption, and no warm/prune operations. The runner's existing `-B`, inherited `PYTHONDONTWRITEBYTECODE=1` and removal of `PYTHONPYCACHEPREFIX` apply before worker/descendant startup. Add a focused no-source-`__pycache__`/no-prefix-writes startup control to that test module, with the shim loaded and the prior customization chained; run the unchanged source and `-c` command censuses. Ordinary unmarked production imports must leave bytecode/cache policy unchanged.

**Supported boundary and honest limits.** The guard targets accidental Python writes. It covers the main workers before import, ordinary Python exec descendants that retain site initialization and the injected environment, and fork descendants; canonical publication refusal also follows the inherited protected-root marker. A Python child started with `-I`, `-S`, an environment that removes/replaces the bootstrap, native/ctypes code, shell/native executables, and writes through descriptors opened before instrumentation are not universally intercepted. Their unclassified repository deltas still fail the parent guard. A bypassing child that produces exactly valid exempt bookkeeping can be indistinguishable from a coordinator; this is explicitly not a hostile-code isolation or authentication guarantee. Do not grow this repair into subprocess rewriting, a general site-hook framework, OS policy or a separate qualification checkout. If compatibility requires more than the two small bootstrap/helper files, surface that concrete conflict before expanding scope.

**Planning evidence.** Current-file MCP reads validated `_run_file`, `_execute_files`, `repo_state_snapshot`, the ledger parser/validator/renderers and `canonical_review_policy_body`. Temporary probes outside the repository showed audited `Path.write_text` and `os.open` refused, the same hook inherited across `fork`, and ordinary Python exec refused through `sitecustomize`; an `-I` child bypassed that bootstrap, confirming the stated limitation. These are design-feasibility probes, not implementation qualification.

## Acceptance Criteria

- [x] AC-1: A real runner fixture with passing tests and concurrent external canonical review/progress recording succeeds and writes the existing matching receipt; an unchanged subsequent run reuses it. Oracle: exit status, receipt contents and worker invocation count.
- [x] AC-2: Accidental bookkeeping writes by ordinary/reporting workers, fork descendants, ordinary environment-inheriting Python exec children and canonical publication API descendants are refused before changing protected bytes or fail qualification without a new green receipt. Oracle: actual workers against temporary repository fixtures, including direct `Path.write_text`, `os.open` append, atomic replacement, deletion, relative/symlink paths and a valid typed-ledger publication; companion fixture-root writes succeed. Native/isolated/bootstrap-cleared raw-write limits are documented and demonstrated without claiming universal detection.
- [x] AC-3: Material source/test/configuration/edit-gate/plan changes and malformed, truncated, rewritten or policy-rotating ledgers remain consequential; forged generated views do not receive an exemption. Oracle: paired controls through the actual runner guard, including a same-size/restored-mtime framework edit, substantive handoff/AC-label/[~] change, and ledger/projection publication observed consistently.
- [x] AC-4: Routine ledger/status/progress recording preserves approvals; actual blocking findings and material plan edits still affect the correct authority. Oracle: existing evaluator and policy-digest paths comparing affected and unaffected phases/lanes.
- [x] AC-5: Existing close/package boundaries consume the same matching green receipt without a second suite or reviewer cycle solely for qualifying bookkeeping; install/upgrade paths gain no qualification or historical bookkeeping work. Oracle: existing boundary integration controls/call counts and a scoped diff showing these runtime paths unchanged apart from the declared pack source-membership exclusion.
- [x] AC-6: This change's edited documents validate, canonical guidance matches rendered local surfaces, and no new durable evidence carrier is introduced. Oracle: docs validation, renderer comparison, module/bytecode censuses, miniature pack/manifest inclusion-exclusion and artifact inspection.

## Tasks

- [x] Before readiness, select the bounded audit-hook/site-bootstrap and canonical publication refusal design, name exact paths and document descendant/raw-write limits. Evidence: Selected Design and temporary feasibility probes; no claim that valid JSON, actor claims, environment markers or worker-visible nonces prove a writer identity.
- [x] Implement bookkeeping classification and leak protection together; do not ship an exemption before its negative controls work.
- [x] Extend the existing real-worker fixture harness with concurrent-bookkeeping, worker-leak, material-change and corrupt-ledger controls.
- [x] Verify current approval currency and normalized carriers; change them only if a focused control demonstrates a defect.
- [x] Correct affected canonical guidance and architecture/build docs, render local surfaces and validate the changed documents.
- [x] Complete required wave reviews and one final canonical qualification after behavioral edits; record concise results in the existing wave record.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Boundary design | Coordinator | — | Selected above; review the bounded coverage and limits before readiness. |
| Runner repair | Implementer | Design and readiness | Own source/tests; preserve leak protection with the exemption. |
| Verification | Required reviewers | Implementation | Read-only review of controls and protected authority. |

## Serialization Points

Implementation files (the only new files are the small guard library and test startup shim; responsibilities are specified in Selected Design):

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/qualification_worker.py`
- `.wavefoundry/framework/scripts/test_worker_guard.py`
- `.wavefoundry/framework/scripts/test_worker_bootstrap/sitecustomize.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_repo_guard.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`
- `.wavefoundry/framework/scripts/tests/test_qualification_report.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_bytecode_cache.py`
- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`
- `.wavefoundry/framework/seeds/190-close-wave.prompt.md`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/prompts/implement-change.prompt.md`
- `docs/prompts/implement-wave.prompt.md`
- `docs/prompts/close-wave.prompt.md`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/build-and-verification.md`

The three seeds replace quiet-bookkeeping requirements with the precise supported routine-update rule; render the affected local lifecycle guidance from those canonical sources. `gardener_metadata.py`, review policy/digest definitions, approval chronology, close/install/upgrade implementations and package behavior beyond the declared source-membership edit and historical waves remain unchanged unless a focused control proves a defect that is explicitly brought back into scope. Serialize runner edits with qualification. Reviewers inspect; the implementer owns source/tests and guidance edits.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: runner mutation guard, qualification reuse, concurrent bookkeeping and worker-write limits. Update another review/data-flow contract only if boundary design changes its ownership; do not duplicate existing authority descriptions.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Removes the observed needless qualification rerun. |
| AC-2 | required | Prevents hiding accidental test leaks. |
| AC-3 | required | Keeps material changes and corrupt authority consequential. |
| AC-4 | required | Preserves review intent and phase/lane boundaries. |
| AC-5 | required | Avoids moving overhead into other lifecycle operations. |
| AC-6 | required | Aligns shipped instructions with actual behavior. |

## Progress Log

- 2026-10-12: Combined qualification exposed two integration checks omitted from the focused selection: compact-guidance pins still named the retired quiet-bookkeeping wording, and one malformed-declaration negative fixture lacked its census classification. Updated the existing contract assertions to the admitted material-edit/routine-bookkeeping rule and added the reasoned negative-fixture comment; deletion/reversal and render controls remain intact. The two files pass all 17 tests. The already-red combined run was stopped (exit 143); no green receipt is claimed. Restart combined qualification after pausing and closing the edit gate.

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-11 | Drafted follow-up; no admission, readiness or source edits. | Current runner guard, approval evaluator and policy-body normalizer inspected. |
| 2026-10-11 | Before readiness, declared helper production dependency/roster membership, shim pack exclusion, bytecode census and exact prior-sitecustomize chaining; serialized paths now use path-only bullets. | Current-file reads of module roster/census, pack exclusions/manifest tests and bytecode source/command census. |
| 2026-10-11 | Resolved the design to semantic carrier checks plus a small inherited Python worker guard and canonical publication refusal. | Current-file MCP validation and temporary audit/fork/site-bootstrap probes; isolated-interpreter bypass explicitly observed. |

| 2026-10-12 | Readback before implementation: current stat guard rejects canonical external ledger/progress changes; implement the frozen coupled semantic-endpoint and pre-import supported-worker guard, preserving normalizer/evaluator and material/source invalidation. | Actual ordinary/reporting/nested/child worker controls, canonical external publisher, corrupt/material negatives, final hash, cache reuse and helper pack/bytecode censuses will verify the repair. Readiness and both edit gates confirmed; root owns guidance, this implementer owns runner/test integration. One combined full qualification remains coordinator-owned after all four waves. |

| 2026-10-12 | Guidance source-of-truth integration includes the existing `.wavefoundry/framework/install/lifecycle-prompts/implement-wave.prompt.md` baseline, required for fresh installs. No new qualification behavior or gate. | Root changed canonical seeds first, mirrored project-owned local prose, rendered 8 fresh baselines and checked 3 local prompts with zero generated-region drift. Source-based bytecode guidance corrected; no bytecode source behavior changed. |
| 2026-10-12 | Coupled runner classifier and supported worker prevention implemented; current direct controls validate concurrent canonical publication, unchanged receipt reuse, restored-mtime source invalidation and protected ordinary/reporting/fork/exec writes. | Real-worker fixture controls caught and repaired generated-section seam ordering, descriptor-relative audit context and harmless ancestor mkdir handling. The two-location inherited shim chaining defect was repaired within the admitted helper/shim scope and pinned with a real two-copy startup control. Both existing synthetic-copy filters now preserve the shipped `test_worker_guard.py` dependency, including the 20gx1 storage rename fixture. |
| 2026-10-12 | Bounded current-tree observation cost measured without running qualification. | One actual `repo_state_snapshot()` retained 50,166,965 carrier bytes across 1,941 carriers out of 4,025 entries in 0.638 seconds on this machine. This is one observation, not a cross-platform bound or paired speedup claim. |

| 2026-10-12 | Focused canonical qualification passed: 905 tests across 9 files, zero skips, exit 0 in 94.806 seconds. Full-suite receipt unchanged. | Runner guard (44), cache (97), qualification CLI (34), review evidence (195), review policy (116), extension roster (224), miniature pack (120), bytecode (60) and storage resume (15). Paired actual-worker mutants disable semantic classification (valid external publication rejected) or omit fixture protection from child environment (valid worker progress leaks and a receipt is incorrectly accepted); intact production detects both boundaries. Same-size/restored-mtime source change is rejected by final hash. No code source mutations during qualification. |
| 2026-10-12 | Implementation and guidance complete; unchanged evaluator/normalizer and close/install/upgrade authority retained. | Full docs validation and diff whitespace check passed. AC-5 close-boundary integration and the required reviews/final combined full-suite task remain coordinator-owned; focused packaging controls already pass. Exactly two helper/bootstrap files added; no permanent evidence carrier. |

| 2026-10-12 | Repaired four combined-suite integration failures within the existing guard/profile contracts; production reload and runtime-lock behavior are unchanged. | The marked worker now captures Darwin's native descriptor resolver once before discovery, avoiding simulated fcntl modules; retained-module census explicitly classifies the process bootstrap and pins count 24; the arbitrary bytecode fixture uses a neutral filename; the classifier consumes the vocabulary profile's escaped member-ID label. Normal reload preserves module, os.open wrapper, protected roots and refreshed publication binding. |
| 2026-10-12 | Repair qualification passed through actual marked canonical workers: 191 tests across 8 files, 2 existing platform skips, exit 0 in 23.388 seconds. This does not replace the still-required green combined full run. | Runtime lock 40, lifecycle structure 15, profile literal census 8, vocabulary census 5, runner guard 46, bytecode 60, declared fixtures 13 and compact review contracts 4. A real renamed-profile runner accepts canonical publication and reuses its receipt; a disposable hardcoded-label mutant fails that same control. A disposable lazy-fcntl mutant fails the new descriptor control while intact source passes, with the loaded helper path verified. Full docs validation and whitespace check follow before write handoff. |

| 2026-10-12 | Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster. | Canonical final qualification: 12,402 tests / 185 files / 12 unchanged existing skips, 798.065 seconds, exit 0; matching receipt `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Exact report worker/skip comparison and all reviewed source fingerprints verified. Full documentation validation passed with zero errors and warnings. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-11 | Directly separate bookkeeping from material inputs while preserving worker-leak detection. | Repairs the semantic coupling at the existing boundaries. | Copied qualification checkouts isolate the symptom and add coordination cost; operator rejected them. Blanket ledger/docs exclusions can hide test leaks and corruption. |
| 2026-10-11 | Use an inherited Python site bootstrap plus a pre-import worker hook and canonical publication refusal; do not implement OS confinement. | Covers common accidental Python descendants while exposing raw/native/isolated limits honestly. | Filename ignores lose leak detection; universal raw-child attribution needs disproportionate OS isolation. |
| 2026-10-11 | Retain existing approval evaluator and canonicalizer unless a focused control proves a defect. | Ordinary appends already preserve unrelated approvals; canonicalizer changes can unnecessarily lapse readiness. | Ignoring all handoff prose can hide substantive plan restrictions. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A valid append does not identify its writer. | Prevent supported accidental worker writes before mutation; validate external bookkeeping semantically. Explicitly retain the unsupported raw-descendant indistinguishability limit; do not call this authentication. |
| Protection misses descendants/raw operations. | Exercise main/fork/site-inheriting Python routes and canonical publication API children; demonstrate isolated/bootstrap-cleared limitations, fail unclassified changes and avoid claiming a hostile-code sandbox. |
| Site bootstrap changes test startup semantics. | Keep the shim inert without the marker, preserve existing path/customization behavior, test ordinary/reporting startup and nested roots, and stop before expanding beyond the small helper/shim scope. |
| Bookkeeping hides substantive changes. | Validate append relationships and preserve material inputs, corruption checks and affected-finding evaluation. |
| Repair adds more process than it removes. | Reuse existing carriers; no new permanent files, recurring reviews, historical scans or upgrade steps. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
