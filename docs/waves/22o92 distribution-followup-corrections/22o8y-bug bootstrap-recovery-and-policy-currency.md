# Keep setup recovery usable and its preparation plan truthful

Change ID: `22o8y-bug bootstrap-recovery-and-policy-currency`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22o92 distribution-followup-corrections

## Rationale

Waveforge reviewed 614ac8a2 and 729c069b before merging. Their follow-up identifies a warning that disappears on an older hook interpreter, incomplete selected-root setup remedies and an unlabeled PowerShell command in Windows MCP responses. It also identifies a dry-run currency discrepancy that can affect setup's decision to skip preparation. Fix these before the next tagged release; this plan does not authorize publication.

Current-tree execution confirms that the exact HOOK_BOOTSTRAP produces its warning when the diagnostic import succeeds, but emits nothing with version_mismatch when that import raises the missing-tomllib error. This is a controlled import-boundary probe, not a native Python 3.9 run. Source confirms setup_readiness imports tomllib while the diagnostic sits inside except Exception: pass.

An actual build_index replay using the existing temporary native-SQLite/fake-embedding fixture reports up_to_date=true for a policy-only change with no pending maintenance, while the subsequent real build advances generation 1 to 2. A separate newly eligible test-file control reports up_to_date=false, indexes one file and makes two bounded fake-embedding calls. The local evidence proves omitted policy maintenance, not an unsafe embedding-without-preparation event. Preserve that distinction.

## Product Intent

Operators and downstream agents should receive visible, selected-repository recovery instructions even when bootstrap prerequisites fail, and setup should base preparation exemptions on a truthful read-only plan. AC-1 to AC-4 establish these outcomes without starting setup or altering the selected inference provider. This supports the adopted vision's Horizon 1 dependable foundation; the vision itself is unchanged.

## Requirements

1. Keep the hook's version-mismatch/activation warning visible when its preferred diagnostic formatter cannot import. The recovery-command owner used before runtime validation must be standard-library-only and usable by the older interpreter being diagnosed, without importing tomllib, activating a venv or depending on installed framework packages. Runtime Python 3.11+ remains required. Prefer one small bootstrap-safe owner over duplicated launcher construction; setup_readiness may retain compatible wrappers.
2. Make dry-run currency account for stored targeted_corpus_policy and other state that the real build uses to decide currency on this affected path. Reads must not initialize, migrate, checkpoint, publish or repair the store. Changed, absent or unreadable policy cannot be silently certified as current. Preserve the existing unchanged, compatible, no-work fast path; preparation/precision checks still run when the canonical plan requires them or cannot prove the exemption. Do not infer that every maintenance action requires native inference. Cover policy-only and newly eligible-file cases separately, with a setup-to-real-build control.
3. Audit executable setup recovery emitted by setup_index, venv_bootstrap, upgrade_wavefoundry, graph_snapshot, indexer and the four reported relative setup recovery_usage branches in wf_server/server_impl. This includes the reported locked/antivirus-held venv, dependency-install/startup status, upgrade continuation and native-runtime graph failures. The rule is to preserve the selected target through every executable setup remedy in those named paths; a historical list or a global string replacement is insufficient. Do not turn generic examples, historical records or unrelated setup prose into implementation scope.
4. Build remedies through the same absolute repository launcher/argv owner. Preserve --full and other load-bearing options, failure codes, caller budgets, pending-install progress, graph migration/recovery distinctions, and ask-before-running instructions. Propagate an explicit root through affected callers instead of substituting cwd. If the root genuinely cannot be established, give a truthful non-executable next step instead of fabricating --root . or a guessed path.
5. Windows OS identity does not identify the agent's shell. Preserve recovery_usage compatibility but expose structured argv and identify the shell/dialect of formatted setup remedies at the affected MCP boundaries. PowerShell text must be labeled as such; do not present it as a universal Windows/Git Bash command. Keep formatting pure and execution-free. Add an explicit formatting choice usable by tests/callers without replacing the entire os module; default calls retain compatibility. Native Windows/Git Bash execution is a separate qualification claim.
6. Keep the session-start diagnostic's length limit and apply its existing printable-text cleaning to the recovery line too. Preserve an unambiguous fallback when display cleaning would change an executable path. Test control characters, quotes and unusually long target names without executing them.
7. Update architecture, tool contracts and release notes to state the delivered scope precisely. Retain diagnostic behavior that already works and the model/precision safeguards fixed earlier. Regenerate only the named managed consumers of changed canonical hook/launcher text. Register any new shared source owner in the existing setup identity/provenance and framework text-ownership inventories so later changes remain observable.
8. Preserve ordinary bare `wf setup` through the public repository launchers. With no explicit --root, use the launcher-owned project root rather than an arbitrary caller directory. Validate the expected owned launcher/dispatcher layout and stop before Python dispatch if root resolution or changing directory fails; no Git repository requirement is added. When the launcher selects a different working directory, emit a bounded stderr notice naming that directory and explaining that an explicit --root still selects the setup target. Forward all arguments unchanged, preserving explicit --root, help, stdout and exit behavior. Do not silently initialize or operate in a foreign directory, add PATH installation, or infer ownership from arbitrary cwd. Native Windows execution remains separately qualified.

## Scope

In scope: bootstrap-safe command ownership and diagnostic fallback, truthful policy-aware planning, named setup recovery consumers, additive shell/argv reporting, the test formatting seam, affected generated hooks/launchers and concise contracts.

Out of scope: provider selection redesign, model downloads, live project setup/index changes, live storage-policy changes, automatic recovery, new authentication/authorization, unrelated bare-command prose, downstream edits, release publication or changes to the adopted vision. No source edit is permitted before admission and readiness.

## Acceptance Criteria

- [x] AC-1: Executing the actual generated hook/bootstrap with a version-mismatched venv and an unavailable diagnostic import still emits a bounded actionable warning; supported and missing-venv cases preserve their intended behavior. The current silent case fails this check. Report simulated versus actual older-Python execution.
- [x] AC-2: Read-only dry-run and setup controls distinguish unchanged currency, changed/missing/unreadable corpus policy, maintenance-only refresh and newly required embeddings. A setup/native-preparation exemption is justified by the actual plan; removing the policy observation is detected. Original database entries/bytes remain unchanged during planning; the unchanged-index fast path survives.
- [x] AC-3: Actual named setup/MCP/graph/upgrade consumers run from a different cwd and return the selected repository's launcher with required arguments and preserved failure semantics. MCP responses identify formatted-command dialect and provide usable argv; bare, relative, wrong-root and mislabeled-shell variants fail. No probe runs setup or downloads models.
- [x] AC-4: Actual session-start output remains printable and bounded for hostile/long path text, and the canonical hook/launcher render agrees with all affected declared Claude, Cursor, Copilot and Windsurf generated consumers. Published claims match the paths and platforms tested.

- [x] AC-5: Actual emitted POSIX `wf` invoked through PATH from the owner root, a nested directory and an unrelated directory selects the launcher-owned root, warns on stderr when changing working directory, and preserves explicit --root arguments and help behavior. A missing dispatcher or failed root/cd operation cannot invoke Python or mutate the caller tree. Controlled emitted Windows checks verify equivalent ordering and failure/notice contracts without claiming native execution. Removing root/cd guards or notice handling fails the relevant controls; raw wf_cli invocation is not substituted for this public-boundary test.

## Tasks

- [x] Establish before-fix consumer failures and freeze the relevant diagnostic/currency baselines.
- [x] Implement the smallest shared bootstrap/formatting repair and policy-aware read-only plan; integrate the named callers.
- [x] Regenerate affected owned hooks/launchers and update contracts and release notes.
- [x] Verify public launcher ownership, foreign-directory notices and fail-closed dispatch while preserving explicit targets.
- [x] Verify actual consumers, independent negative controls and required delivery reviews; qualify the settled framework once.

## Agent Execution Graph

One implementation owner serializes the common command owner, setup/index planning and generated carriers. Required independent code, QA, architecture, security and docs-contract reviews inspect actual consumers and limits; reviewers do not edit source. Coordinate shared render_platform_surfaces.py, setup_readiness.py and CHANGELOG.md with the sibling plans.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_commands.py`
- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/venv_bootstrap.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/graph_snapshot.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_setup_commands.py`
- `.wavefoundry/framework/scripts/tests/fixtures/framework-text-ownership.json`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_setup_readiness.py`
- `.wavefoundry/framework/scripts/tests/test_venv_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/framework/scripts/tests/test_graph_snapshot_readers.py`
- `.wavefoundry/framework/scripts/tests/test_process_info_callers.py`
- `.wavefoundry/framework/scripts/tests/test_startup_install.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`
- `.claude/hooks/`
- `.cursor/hooks/`
- `.github/hooks/`
- `.windsurf/hooks/`
- `.wavefoundry/bin/`
- `docs/architecture/domain-map.md`
- `docs/architecture/chunking-and-indexing-pipeline.md`
- `docs/contributing/build-and-verification.md`
- `docs/specs/mcp-tool-surface.md`

setup_commands.py and its test are proposed new files, not existing behavior. The implementation owner may omit them if the same bootstrap-safe shared boundary is achieved more simply. CHANGELOG.md receives one scoped entry. Generated platform consumers outside the declared directories must be enumerated before admission/readiness if discovery shows they change. Seeds, unrelated generated surfaces, old wave records, model identities and unrelated :memory:.ses are protected. Reviewers are read-only; no source gate is open.

## Affected Architecture Docs

Update domain-map.md for the command owner, indexing architecture for read-only currency, the MCP tool contract for argv/shell metadata, and build-and-verification.md for scoped recovery and qualification limits.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The warning must survive the failure it diagnoses. |
| AC-2 | required | A preparation exemption requires truthful plan currency. |
| AC-3 | required | Recovery must target the selected repository in a known shell. |
| AC-4 | required | Generated diagnostics must preserve a safe readable contract. |
| AC-5 | required | Bare setup must identify its launcher-owned project and disclose directory selection without dispatching from an unproved root. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-06 | Preserve launcher-owned bare setup, add explicit directory notice and fail-closed owner/cd checks. | The operator clarified that omitted --root must not trust arbitrary cwd. Actual POSIX launcher already selects its owner, but does so silently; the Windows launcher has no cd failure check. This bounded amendment closes those gaps without replacing CLI parsing. | Requiring --root on every invocation loses the requested convenience; trusting arbitrary cwd risks acting in another directory; parsing/requoting every argument in wrappers duplicates the CLI. |
| 2026-11-05 | Use a bootstrap-safe shared command boundary, preserve a visible fallback, and make the canonical plan truthful. | The hook import probe loses its warning; policy-only preview omits work that the real builder performs. Shared argv/dialect reporting addresses wrong-root and shell ambiguity at their owner. Success is actual consumer output and faithful plan/preparation behavior, not a text census alone. | Narrowing release prose leaves operator recovery defects; duplicated inline builders avoid the import but multiply drift; blanket preparation removes the useful current-index fast path. |
| 2026-11-05 | Keep the policy safety claim bounded. | The actual builder replay advanced generation 1 to 2 after a current preview; a new eligible file was correctly planned and embedded. An unsafe native-preparation bypass remains reported/inferred pending a stronger consumer fixture. | Claiming reproduced unsafe inference would overstate this evidence. |

## Risks

A bootstrap helper can reintroduce imports or circular activation; verify under an older-interpreter boundary. A read-only policy observation must not open a writer or ignore a live WAL. A command can be valid PowerShell but unusable in another host shell; expose argv/dialect instead of guessing. Extra preparation on genuine no-work inputs would regress the prior fix. Native platform evidence must remain explicit.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Implementation and all required technical delivery reviews complete; no deferred AC or task. | Final canonical run passes 12,400 tests across 218 files in 575.668 seconds, with 12 expected skips and green input hash 2e773a18ef0cde23bd5bf478dcb01125cbf9eab7c5f16df94c63a0640231553a. All seven lane approvals and Council PASS establish intent. Operator closure signoff remains pending; the requested pause permits scanner-wave implementation next. |
| 2026-11-06 | Independent code/architecture/performance and QA verify R8/AC-5 on the unchanged frozen candidate. | Each context independently ran all 11 public launcher tests without skips. Code/architecture removed the dispatcher guard and observed forbidden interpreter dispatch. QA's separate guard-removal and notice-suppression mutants failed four and ten assertions respectively, with zero errors. All 62 manifest targets remained unchanged. Both contexts approve the delta subject to final canonical qualification; native Windows remains unqualified. |
| 2026-11-06 | Implemented the readied launcher delta and froze 62 source/contract targets for focused delivery verification. | Manifest 5a542918f10139bc9b99224b14e9d20f4589cf49. Root reports 11 emitted-launcher tests passing: actual PATH calls from own/nested/foreign roots, hostile/long names, explicit root forms, help and exit preservation, missing dispatcher and root/cd refusal before interpreter execution. Owner/cd/notice mutants fail 4/12/10 assertions with zero errors. POSIX command substitution now preserves trailing newlines in real paths; display truncation does not alter execution. Windows ordering remains controlled, not native. Independent delta checks and final canonical receipt remain pending. |
| 2026-11-06 | Focused readiness refresh approved the launcher amendment; canonical Prepare reopened implementation with no pending readiness lanes. | Receipt ec9dafffac39fc15bf44. Seven lane approvals and council PASS establish intent; code/architecture/performance share one context, docs/release share one. Independent actual emitted PATH-launcher probes reproduced silent owner selection and interpreter dispatch with a missing dispatcher; explicit targets and caller files were preserved. Reality review attributes those observations. Native Windows remains unqualified. Root owns renderer, launchers and tests; coordinator owns contract prose. |
| 2026-11-06 | Operator clarified public bare setup ownership after delivery review. R8, required AC-5 and one task amend the owning plan before implementation; existing renderer/test/bin targets already cover the delta. | Actual POSIX wf via PATH from foreign cwd selects its owner but emits no notice. Raw wf_cli cwd-only probing was below the public launcher boundary and is not evidence of launcher behavior. Focused readiness refresh is required for this amendment. Previous 12,396-worker retry passed, but concurrent lifecycle accounting refused its receipt; no green receipt claimed. |
| 2026-11-06 | First canonical suite exposed integration gaps; repaired them within the existing targets after all frozen reviewers completed and typed repair starts were recorded. | 12,396 tests / 218 files, five failing modules: missing helper reload/census registration; session-hook length-reason drift; old indexer command expectations; old readiness formatting mocks. Helper registration and length-specific fallback are restored. Indexer refusals/no-embed/publication assertions remain; formatting tests keep real os and use the explicit seam. Coordinator 44 and root 16 focused repair tests pass. Final sync writes nothing; retry source manifest 16274db06378b27b4cd82a1047bd8104925d5403. Independent focused checks and canonical retry are pending. |
| 2026-11-06 | Root and coordinator isolated the fifth upgrade failure to the staged child dependency list, then added setup_commands.py without weakening the finding-count assertion. Typed D92-delegate-fixture-dependency and repair_start precede the edit. | Same real delegated test failed before repair; root in-memory dependency control passed. QA independently reverifies the repaired fixture and omission mutant. Final source manifest 3905e3c510732fcb211d552457123923b419c0a3 excludes only preserved bytecode caches. Build guide clarifies the operator-selected ordinary bare wf setup convenience remains; explicit selected-root recovery still avoids ambiguous lookup. |
| 2026-11-06 | Pre-lane verification corrected four old cleanup test expectations to the selected-root launcher and retained --check options. No runtime change was needed. | PhaseCleanupSetupBaselineTests: 15 pass. Initial full upgrade module reported five failures under restricted permissions; four were reproduced as stale expectations, remaining permission-related result is being separated by the root worker before final qualification. Primer ran 12 consumer tests and rejected the baseline silent-bootstrap mutation, with no new delivered defect. Refrozen target manifest: 421e2366bc1987d94954148892e4bf282bc05666. |
| 2026-11-06 | Integrated command ownership, policy observation, recovery consumers and regenerated hooks. | setup_index 208 tests; startup affected 39; helper/policy 20; four actual MCP recovery boundaries in one selected-root fixture pass. Root separately verified graph 45, venv 43, upgrade failure 32 and process-info 17. Removed policy observation is rejected; real rendered hooks cover import failure and hostile/long paths. Database bytes/logical contents stay unchanged during planning. Python 3.9 and Windows behavior are controlled simulations, not native runtime qualification. |
| 2026-11-05 | Readback: AC-1–4 require visible bootstrap warnings, truthful read-only policy currency, selected-root setup remedies with argv/dialect and printable generated output. A missing diagnostic import currently hides a mismatch warning; the repair keeps that warning visible. One stdlib command owner feeds named consumers; no setup, provider or live-index mutation is authorized. | Implementation owns the declared setup/index/bootstrap/recovery files and focused tests; shared renderer and server/upgrade edits are serialized with siblings. Existing readiness probes provide failing baselines. |
| 2026-11-05 | Readiness repair R92-generated-hook-targets: added the existing Cursor, Copilot and Windsurf hook directories to Serialization Points and made their parity coverage explicit in AC-4. No source or generated file changed. | Independent initial renderer probes found eight additional affected carriers; the initial targets named only Claude hooks and bin. Focused verification pending. |
| 2026-11-05 | Planning only; source inspected through MCP, then bounded actual/bootstrap and temporary builder probes executed. No framework source changed. | HOOK_BOOTSTRAP warning control true / missing-tomllib case false; policy-only preview current, real generation 1→2; newly eligible file preview pending, one file indexed/two fake-embedding calls. Probe source /private/tmp/wf-followup-probes.py is disposable, not future approval authority. |
| 2026-11-06 | Implemented bootstrap-safe shared command ownership, read-only corpus-policy currency, selected-root remedies and additive argv/dialect at named MCP boundaries. Regenerated carriers are coordinated by the wave owner. | Focused checks: setup-index 208; startup affected paths 39; helper/policy 20; four actual retrieval/seed recovery boundaries 1. Root worker additionally verified graph readers 45, venv bootstrap 43, upgrade failures 32 and process info 17. |
| 2026-11-06 | Currency controls preserve the unchanged fast path, distinguish policy-only refresh from newly required embeddings, and refuse exemption for changed, missing or unreadable policy. Planning preserves the existing database snapshot; the policy-only real build advances publication without requesting an embedder. | DryRunIdleMaintenanceTests includes a removed-policy-observation mutant rejected by the same oracle, a setup-to-real-build path, and newly included code with fake embeddings. No live setup, index or models were modified. |
| 2026-11-06 | Bootstrap and session-output checks execute canonical generated text. Four actual MCP branches retain the selected fixture root from a different cwd and required code options, with explicit argv and dialect. | test_setup_commands blocks tomllib/readiness imports, tests static fallback, and rejects altered/truncated executable paths. Python 3.9 syntax/import boundaries and Windows formatting are controlled simulations, not native runtime qualification. |
| 2026-11-06 | Released source for delivery review and the canonical full suite. Initial broad multi-module unittest execution exposed dynamic-module mock contamination; isolated affected modules pass. | One unrelated startup cache-path test could not inspect a real home cache under the sandbox; the canonical suite owner will verify in the normal test environment. Decisive oracles are retained in test source, not temporary logs. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
