# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-02
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zls8 extension-surface-two`
Title: Extension Surface Two

## Objective

Distribution extension modules gain the rest of the public helper surface a lifecycle-tool wrapper needs, declared helper modules that are hashed into provenance and reloaded, declared nested response-key renames for parameter-mapped aliases, and cost recording for what an override of a self-recording tool adds, so a downstream distribution (Waveforge) stops reaching private names and its aliases answer in its own vocabulary.

## Changes

Change ID: `1zltx-enh extension-helper-surface`
Change Status: `implemented`

Change ID: `1zlty-enh extension-response-key-renames`
Change Status: `implemented`
Depends On: `1zltx-enh extension-helper-surface`

Change ID: `1zltz-enh override-response-cost-recording`
Change Status: `implemented`
Depends On: `1zltx-enh extension-helper-surface`, `1zlty-enh extension-response-key-renames`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-03

## Wave Summary

Wave `1zls8` (Extension Surface Two) delivered 3 changes: Public Lifecycle Helpers and Declared Helper Modules for Extensions, Declared Response Key Renames for Mapped Aliases, and Cost Recording for What Overrides of Self-Recording Tools Add. Notable adjustments during implementation: Public Lifecycle Helpers and Declared Helper Modules for Extensions: Commit-order constraint (reverification D1): `FRAMEWORK_SCRIPT_MODULE_NAMES` lists `verify_vendored_scripts`, a file added by wave 1zls7 and not yet committed. Commit 1zls7 first or together with 1zls8, or the framework-script census fails in the committed tree. CHANGELOG now names the ASCII module-name refusal (D2).; Public Lifecycle Helpers and Declared Helper Modules for Extensions: Delivery-review repair (non-blocking findings N1, N3, N6, N7). N1: the `server_impl` reload purge now evicts `mcp_tool_roster` with `mcp_tool_extensions`, so a roster imported before a server load no longer validates the evicted declaration module; this removes the test-ordering fragility reported at implementation (the three-test repro now passes). N6a: the `_load_extension_module` collision check uses the strict marker test eviction uses (`vars(module).get("__wf_extension__") is True` on a real module), so a module-level `__getattr__` answering every name no longer passes as marked. N6b: `_module_name_problems` refuses non-ASCII extension and helper module names (an NFD `acmé_x` passed `isidentifier()` and failed only at load). N3 and N7: the spec's **Helper modules** paragraph now says names must be ASCII, that a module importing a helper should itself be declared, and that a fork's own undeclared flat script fails the framework-script census, so it must be declared; the threat-model row names the ASCII rule and the strict marker test. Failing-first on the pre-repair tree: `RosterReloadPurgeTests`, the four non-ASCII subtests and the two `lazy_truthy` refusal cases failed (7 failures). Mutations, each reverted singly in a scratch copy, all killed: roster not purged, lenient collision marker test, non-ASCII names allowed. Full suite in a fresh scratch copy (`run_tests.py --no-cache`): 10,813 tests OK; Public Lifecycle Helpers and Declared Helper Modules for Extensions: Implemented. Signatures re-read and confirmed as planned (no Decision Log difference). `server_impl` gains the five late-bound wrappers and an eleven-name `EXTENSION_PUBLIC_HELPERS`; `mcp_tool_extensions` gains `EXTENSION_HELPER_MODULES`, `FRAMEWORK_SCRIPT_MODULE_NAMES` (106 stems, including the 1zls7 file `verify_vendored_scripts.py` present in the tree), shared module-name rules, the tuple and both-lists refusals and `declared()` coverage; `_install_extension_tools` evicts marked modules first, snapshots `sys.modules`, delegates to `_install_declared_extension_tools` (helpers load first) and pops new declared modules on failure; `_load_extension_module` compares `<name>.py` with the exact directory listing before `find_spec`; `helper_modules` provenance in the declaration, the install record and `wf_server_info`. Deviations: the existing refusal case `already_imported` used `record_paths`, now refused earlier as a framework script name, so it uses a plainly imported fixture `plain_imported` and a new case `framework_script_name` keeps `record_paths`; the census test enumerates flat scripts through `framework_files.framework_source_files(include_aliases=True)` because `test_server_package` forbids a flat glob; `FRAMEWORK_SCRIPT_MODULE_NAMES` is classified in `NON_BEHAVIOR_COLLECTIONS` (it holds `memory_backfill`, also a tool name); the helper roster test patches the declaration module the roster imported (an earlier ordering fragility between `LockAndCreditDeclarationTests` and `DeclarationValidationTests` exists on the unchanged tree too). Failing-first on the unfixed tree: 38 tests reported 15 failures and 43 errors, including the mis-cased extension module served as `acme_case` under `PYTHONCASEOK=1` on macOS. Mutations, each reverted singly in a scratch copy, all killed: contract name dropped, wrapper aliased at import, `wave_dirs` dropped, framework-script refusal off, helper preloading off (AC-5 known-bad), eviction off and eviction after the `declared()` return (AC-10, AC-11), failure cleanup off (AC-11), exact-name check off, both-lists refusal off, `declared()` ignoring helpers, helper `register` called. Suites in a scratch copy: default `run_tests.py --no-cache` 10,811 OK; `--profile second` and `--profile declared` 156 of 156 files passed

**Changes delivered:**

- **Public Lifecycle Helpers and Declared Helper Modules for Extensions** (`1zltx-enh extension-helper-surface`) — 11 ACs completed. Key decisions: Names `find_wave_record`, `refuse_if_archived`, `fail_closed_on_record_layout`, `attach_lint`, `refresh_index_for_paths`; `attach_lint` names its third parameter `mode`, not `mode_s`
- **Declared Response Key Renames for Mapped Aliases** (`1zlty-enh extension-response-key-renames`) — 8 ACs completed. Key decisions: Paths in canonical names with `[]` for list elements; the value is a bare new key name; Per-object collision leaves that object unchanged and adds one advisory
- **Cost Recording for What Overrides of Self-Recording Tools Add** (`1zltz-enh override-response-cost-recording`) — 10 ACs completed. Key decisions: Record the override's added size as a delta, measured by a scope that `core_handler`'s wrapper feeds; Treat overrides of exempt names like replacements (`extractor_free`) was rejected
## Watchpoints

- Watchpoint: all three changes edit `wf_server/server_impl.py`, `docs/specs/mcp-tool-surface.md` and `CHANGELOG.md`, and two edit `mcp_tool_extensions.py`; implement in order 1zltx, 1zlty, 1zltz, never in parallel.
- Watchpoint: wave `1zls7 waveforge-defect-fixes` is planned against the same server module; whichever wave opens second rebases its line references and re-runs its suites after the first closes.
- Watchpoint: every new extension surface keeps the 1zim3 rule that hints and renames never rewrite argument or response values, and never lowers a `write` tier or touches `EDIT_GATE_TOOLS`.
- Watchpoint: run the whole suite under the default run, `--profile second` and `--profile declared` before delivery review, in a scratch copy if another wave is editing docs; `SHIPPED_DECLARATION` must list `EXTENSION_HELPER_MODULES`.
- Follow-up: a declared post-response hook inside the core recording and publication scope stays unplanned until a distribution needs override additions inside the published context-efficiency checkpoint (`1zltz` Decision Log).
- Follow-up (not in scope): an override function that already carries `_wf_mutation_locked`, `_wf_upgrade_guarded` or `_wf_cost_wrapped` skips that wrapper, because each `MIDDLEWARE` pass returns early on its own marker (`wf_server/server_impl.py`, the lock, guard and cost passes); an install-time refusal of an override or extension handler carrying any of the three markers would harden this.
- Watchpoint: readiness amendments 2026-10-02 applied review findings B1 to B3, N1 to N9 and the council red-team challenge to all three change docs (see each change's Decision Log); `1zltx` Requirement 10 now always runs the exact directory-listing case check, so the earlier probe follow-up is closed.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZLS8-ROSTER-PURGE-AND-HARDENING | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: helper-module eviction was justified only by dropped helpers and out-of-order detection on reload yet was untested, and a reload window lets a concurrent lazy import insert an unmarked copy; resolved by tests that fail without the eviction and a failure cleanup that makes the next reload succeed; strongest-alternative: evict only the names the previous install recorded and sweep after success, declined because it would hide an out-of-order import while loading)
- Prepare council seat evidence (2026-10-02): one independent reviewer ran both seats and the code, qa, architecture and docs-contract lanes; round one found three blocking plan gaps (delta events doubling Tool calls, an eviction test that detected nothing, a case check bypassable with PYTHONCASEOK) and nine non-blocking items, all applied; the security seat confirmed no new helper weakens the lock, edit gates, archive refusal or provenance; the scoped recheck approved every lane and seat.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 50 | 1,157,855 |
| implement | 99 | 0 |
| review | 10 | 48,953 |
| **Total** | **159** | **1,206,808** |

<!-- wave:context-efficiency-state {"generation":159,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":99,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-18330,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3889,"response_debit":20447,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6006},"plan":{"calls":50,"content_source_credit":1191449,"derived_artifact_credit":13000,"direct_net":1157855,"estimated_tokens_saved":1157855,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2914,"response_debit":50191,"source_credit_count":38,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":10,"content_source_credit":72764,"derived_artifact_credit":1214,"direct_net":48953,"estimated_tokens_saved":48953,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3469,"response_debit":23872,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":159,"content_source_credit":1264213,"derived_artifact_credit":14214,"direct_net":1188478,"estimated_tokens_saved":1206808,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10272,"response_debit":94510,"source_credit_count":54,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14833},"wave_id":"1zls8 extension-surface-two"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
