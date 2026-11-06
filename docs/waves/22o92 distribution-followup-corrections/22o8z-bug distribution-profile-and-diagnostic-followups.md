# Respect distribution profiles and finish bounded diagnostics

Change ID: `22o8z-bug distribution-profile-and-diagnostic-followups`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22o92 distribution-followup-corrections

## Rationale

The follow-up to 614ac8a2/729c069b finds portable tests that still assume upstream prompt names and prose, an ambient-profile golden, model hints that can exhaust their budget before Downloads, narrow WindowsApps recognition, and clarification that does not reach consumers. A bounded current-tree probe reproduces FileNotFoundError when source_carriers yields the literal prepare-wave template despite a renamed prepare-set template. Actual unused_bundle_hint with synthetic directory entries visits home and another search directory, exhausts its shared budget and misses a candidate in Downloads; directly searching Downloads finds it. Its truncated label contains no truncation marker. The remaining findings are source-confirmed; native Windows aliases and a renamed-profile suite have not been executed here.

## Product Intent

Downstream maintainers should run portable checks without importing upstream wording, and operators should receive complete bounded diagnostics that explain platform limits and evidence authority. AC-1 to AC-4 verify those outcomes at their actual consumers. This maintains the adopted vision's Horizon 1 foundation without changing the destination or imposing a new process on target projects.

## Requirements

1. Separate test carriers by ownership and promised behavior, not by the .wavefoundry/framework path prefix. Resolve install/lifecycle-prompts template names through the existing profile. Gate exact overridable seed prose with source_repository_fixture; retain portable structural/behavior checks and their independent bad controls. Do not hide missing required canonical assets or malformed source opt-in configuration by skipping whole classes.
2. Make the committed lifecycle golden deterministic under the default vocabulary by explicitly isolating that profile in its fixture/capture. Keep alternate-profile behavior tested separately; do not tell distributions to regenerate a golden merely to accept ambient nouns. Retain immutable fixture/regeneration guards and a negative changed-diagnostic control.
3. Replace the shared model-hint entry budget with fair bounded coverage of the finite deduplicated search directories, including Downloads after crowded preceding directories. Define per-directory and aggregate bounds; never unboundedly traverse a directory. A truncated quoted basename visibly marks truncation inside its existing total length budget. Preserve printable sanitization, display-only use, nonselection, explicit selectors, model-set validation and the independently pinned models.
4. Broaden recognition of the selected WindowsApps python3 placeholder to supported redirected and equivalent path spellings without assuming LOCALAPPDATA string equality. Use component-aware/case-insensitive matching plus the silent execution probe, preserving the ordinary real-interpreter path and one actionable failure. A literal suffix match alone does not prove an 8.3-shortened WindowsApps component: either resolve that spelling through a safe bounded existing facility or disclose the unsupported case. Do not add admin, Store, execution-policy bypass or python.exe fallback requirements. Record native versus controlled coverage.
5. State the current capability limit in the work/snapshot spec, build guide and changelog: hosts missing the required descriptor-safe operations, including the current native Windows path, report work/snapshots unavailable and use full-review fallback. This is an implemented limitation, not merely missing qualification. Preserve reboot-safe identity and within-operation substitution checks; this change adds no native work-area implementation.
6. Carry the token-integrity explanation to downstream-visible run_tests --reconcile inspection/help output: the token binds inspected inputs and proves neither operator identity nor authorization. Preserve parseable inspection JSON, return codes, explicit operator direction, allowed reconciliation scope, worker-pass/hash checks and immutable reports. Add no authentication prompt or authority bypass.
7. Apply the explicit formatting seam supplied by the setup/recovery sibling plan to the three new tests that currently replace all setup_readiness.os. Keep every root, mode, pending, quote, no-build and failure assertion; demonstrate that an unrelated os.environ/stat use no longer breaks the platform test harness. Coordinate the shared test/renderer/changelog files; do not duplicate command ownership.

## Scope

In scope: reported source-carrier/profile assumptions, lifecycle golden isolation, model hint fairness/truncation, WindowsApps diagnostic recognition, work-area limitation documentation, shipped token wording and affected test seams.

Out of scope: native Windows work-area implementation, new models/providers, blanket exclusion of downstream tests, new authentication, scanner rules, live setup/downloads, downstream edits or release publication. README/vision work and scanner evaluation are separately authorized work, not hidden additions to this plan.

## Acceptance Criteria

- [x] AC-1: A controlled non-source distribution with renamed prepare/review/close templates and locally overridden seeds runs meaningful portable checks without missing-file or upstream-prose failures. Source-project assertions still run under explicit opt-in. Default golden comparison is independent of ambient vocabulary, while an actual changed diagnostic remains detected and alternate vocabulary retains its own checks.
- [x] AC-2: The actual model-hint consumer finds an eligible Downloads candidate after crowded earlier folders within declared finite bounds, visibly marks a truncated label within 120 characters and never selects or opens candidate bytes. The current shared-budget and unmarked-truncation behavior fails the controls.
- [x] AC-3: Rendered wf.cmd handles the supported alternate WindowsApps spellings, a broken placeholder, working alias, real interpreter, missing Python and too-old Python with the intended diagnostics and exits. No claim is made for unexecuted 8.3/native cases; unsupported work-area documentation describes unavailable/full-review fallback accurately.
- [x] AC-4: Actual reconciliation inspection/help communicates token integrity versus authorization while JSON remains parseable and existing acceptance guards reject bad cases. Platform tests use the explicit formatting seam and retain their bad-root/continuation detection.

## Tasks

- [x] Freeze consumer-shaped failures and profile assumptions before changing the tests.
- [x] Repair profile carriers/golden and bounded model/launcher diagnostics.
- [x] Update affected test seams and downstream-visible documentation/CLI output.
- [x] Verify negative controls, required independent reviews and settled framework qualification with the sibling changes.

## Agent Execution Graph

One owner serializes shared renderer/setup test surfaces with 22o8y. Independent code, QA, architecture, security and docs-contract reviewers verify the delivered boundaries. Supporting fixtures remain temporary; no new review workflow or routine transcript archive is introduced.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/upstream_fixture_support.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`
- `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`
- `.wavefoundry/framework/scripts/tests/test_upstream_fixture_support.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_model_bundle.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_reconciliation.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/bin/wf.cmd`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`
- `docs/references/native-windows-support.md`

The fixture helper test path is a proposed named test target if absent. CHANGELOG.md receives scoped claims. Protect seeds, source opt-in policy, ledger authority, runtime SQLite behavior, model identity and unrelated :memory:.ses. Reviewer lanes are read-only. No source gate is open.

## Affected Architecture Docs

Testing architecture explains carrier ownership and isolated goldens. The MCP/build/native-Windows docs distinguish implemented fallback from unqualified native behavior and token integrity from authorization.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distribution profiles must not inherit upstream-only prose or filenames. |
| AC-2 | required | A bounded hint must reach each relevant search location fairly. |
| AC-3 | required | Diagnostics must describe real capabilities and supported cases. |
| AC-4 | required | Consumers need correct evidence semantics and stable test seams. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Isolate source prose and the default golden; preserve portable behavioral coverage. | Renamed-template execution reproduces FileNotFoundError. Pinning the default fixture plus separate profile tests controls its oracle without hiding runtime contracts. | Skipping the whole test file loses portable checks; downstream golden regeneration can normalize a regression. |
| 2026-11-05 | Use fair finite hint budgets and precise platform wording. | The actual hint misses Downloads after earlier synthetic entries; display truncation is invisible. Consumer output and bounded iteration are the success measures. | An unbounded scan increases startup cost; blanket WindowsApps assumptions mislabel real interpreters; documentation alone leaves the hint defect. |

## Risks

Fixture isolation can skip useful portable behavior if ownership is misclassified. Fair per-folder bounds must retain an aggregate ceiling. Windows path aliases differ from spelling equivalence; simulated suffix matching is not native qualification. CLI wording must not corrupt machine-readable JSON or imply authentication. Coordinate the formatting seam with 22o8y before editing shared tests.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Implementation and all required technical delivery reviews complete; no deferred AC or task. | Final canonical run passes 12,400 tests across 218 files in 575.668 seconds, with 12 expected skips and green input hash 2e773a18ef0cde23bd5bf478dcb01125cbf9eab7c5f16df94c63a0640231553a. All seven lane approvals and Council PASS establish intent. Operator closure signoff remains pending; the requested pause permits scanner-wave implementation next. |
| 2026-11-05 | Model hints and token output implemented and checked by the root worker; carrier/golden and launcher controls integrated. | model_bundle: 33 tests pass; reconciliation: 26 pass; launcher: 7 pass; process-info: 17 pass; upgrade output: 6 pass. Old shared-budget and truncation functions each fail their new consumer control. Carrier helper: 13 pass; golden/distribution boundary: 7 pass. Old carrier helper fails the renamed-distribution control; ambient-noun leakage fails the golden control after correcting the test to use the live reloaded vocabulary module. Native Windows execution was not run. |
| 2026-11-05 | Readback: resolve lifecycle template names through the profile and restrict upstream prose assertions to opted-in source repositories while preserving portable checks. Pin the golden's default vocabulary. Hints inspect at most 512 entries per distinct supplied folder, reaching Downloads after crowded predecessors; aggregate work is bounded by 512 times the finite distinct folder count. Truncation shows ... within 120 quoted characters. Reconcile output distinguishes integrity from authorization; Windows alias diagnostics and explicit formatting tests retain their supported boundaries. | AC-1–4; named helper, golden, model-bundle, launcher and reconciliation targets. Before: renamed templates fail and prior folders exhaust hint budget. After: selected names resolve and each folder gets a bounded turn. Root owns model_bundle/run_tests and their tests; coordinator owns carriers/golden/docs; bootstrap owner serializes the shared renderer and formatting seam. |
| 2026-11-05 | Planning only. MCP source reads and bounded exact-function probes confirm renamed-template FileNotFoundError, skipped Downloads and unmarked label truncation. | /private/tmp/wf-followup-probes.py; probe evidence is summarized here and must be rerun at implementation. Native alias and alternate-profile suite execution remain unverified. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
