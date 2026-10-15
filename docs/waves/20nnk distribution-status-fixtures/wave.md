# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-14
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `20nnk distribution-status-fixtures`
Title: Distribution Compatibility and Hardening

## Objective

Deliver the bounded compatibility and hardening repairs in one coordinated wave: shared container statuses, declaration-independent fixtures, read-only lifecycle previews during upgrades, constrained reconciliation Git queries, optional local-account provenance, and worker startup/refusal hygiene.

## Changes

Change ID: `20nnj-ref export-container-status-contract`
Change Status: `implemented`

Change ID: `20nnl-bug distribution-independent-contract-fixture`
Change Status: `implemented`

Change ID: `20nnm-enh read-only-lifecycle-preview-during-upgrade`
Change Status: `implemented`

Change ID: `20nno-bug bounded-literal-git-queries`
Change Status: `implemented`

Change ID: `20nnq-enh optional-local-account-provenance`
Change Status: `implemented`

Change ID: `20nns-bug worker-bootstrap-and-refusal-boundaries`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer after readiness
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-14

## Wave Summary

Wave `20nnk` (Distribution Compatibility and Hardening) delivered 6 changes: Export the container status contract, Make the declared contract fixture independent of shipped wording, Permit genuinely read-only lifecycle previews during an upgrade, Constrain reconciliation Git query execution, Allow projects to omit local-account review provenance, and Harden worker startup and public refusal diagnostics. Notable adjustments during implementation: Permit genuinely read-only lifecycle previews during an upgrade: Observe: Reconciled the exact docs-lint owners required by the existing read-only preview contract. check_hardcoded_secrets publishes both scanner skips and findings; record_only does not suppress publication, and CLI migration-audit output is another write. Added CLI, secrets validator and their existing tests to review targets.; Harden worker startup and public refusal diagnostics: Observe: Added the existing bytecode-cache test file to review targets because it owns the scratch bootstrap and chaining fixtures needed by the admitted startup controls.

**Changes delivered:**

- **Export the container status contract** (`20nnj-ref export-container-status-contract`) — 4 ACs completed. Key decisions: Select immutable shared constants with equivalent-consumer replacement.
- **Make the declared contract fixture independent of shipped wording** (`20nnl-bug distribution-independent-contract-fixture`) — 3 ACs completed. Key decisions: Select a fixture-owned assignment placed before module execution reaches any entry-point invocation, with live declarations patched explicitly in test scope.
- **Permit genuinely read-only lifecycle previews during an upgrade** (`20nnm-enh read-only-lifecycle-preview-during-upgrade`) — 4 ACs completed. Key decisions: Select explicit read-only core evaluation with conservative refusal for unaudited producers.
- **Constrain reconciliation Git query execution** (`20nno-bug bounded-literal-git-queries`) — 4 ACs completed. Key decisions: Select query-local environment sanitization, explicit command-feature suppression and literal path semantics.
- **Allow projects to omit local-account review provenance** (`20nnq-enh optional-local-account-provenance`) — 4 ACs completed. Key decisions: Select a backward-compatible boolean opt-out that omits new local-account metadata.; Place `record_local_account` under the existing `wave_review` object; an absent value means true without normalization insertion.
- **Harden worker startup and public refusal diagnostics** (`20nns-bug worker-bootstrap-and-refusal-boundaries`) — 4 ACs completed. Key decisions: Select prelaunch refusal of cached bootstrap carriers and path-free boundary translation.
## Watchpoints

- Watchpoint: Each change retains its own ACs and targeted regression checks; one coordinated readiness/delivery cycle and final canonical suite cover the combined result.
- Serialize shared server_impl, review_evidence and config edits. Preview exceptions must remain read-only; provenance opt-out is prospective; Git and bootstrap guards retain fail-closed behavior.
- Keep source feedback, attribution and identifying reproductions outside tracked artifacts.
- Planning records no implementation, qualification or approval claim.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-BOOTSTRAP | do_now | no | completed | architecture-reviewer, qa-reviewer, council-delivery |
| ARCH-DEL-IMPORT | do_now | no | completed | code-reviewer, architecture-reviewer, qa-reviewer, council-delivery |
| QA-DEL-RELOAD-CLOSURE | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, council-delivery |
| QA-DEL-RELOAD-INTEGRATION | do_now | no | completed | qa-reviewer |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: pending; closure not requested.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 129 | 4,199,657 |
| implement | 311 | 5,255,885 |
| review | 318 | 2,363,460 |
| **Total** | **758** | **11,819,002** |

<!-- wave:context-efficiency-state {"generation":638,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":311,"content_source_credit":5320266,"derived_artifact_credit":0,"direct_net":5255885,"estimated_tokens_saved":5255885,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":11508,"response_debit":303355,"source_credit_count":108,"source_credit_drop_count":0,"structural_source_credit":245212,"workflow_prompt_credit":5270},"plan":{"calls":129,"content_source_credit":4637894,"derived_artifact_credit":3997,"direct_net":4199657,"estimated_tokens_saved":4199657,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":57501,"response_debit":399330,"source_credit_count":259,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14597},"review":{"calls":318,"content_source_credit":3081875,"derived_artifact_credit":389,"direct_net":2363460,"estimated_tokens_saved":2363460,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36725,"response_debit":685010,"source_credit_count":128,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2931}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":758,"content_source_credit":13040035,"derived_artifact_credit":4386,"direct_net":11819002,"estimated_tokens_saved":11819002,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":105734,"response_debit":1387695,"source_credit_count":495,"source_credit_drop_count":0,"structural_source_credit":245212,"workflow_prompt_credit":22798},"wave_id":"20nnk distribution-status-fixtures"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 73 | 0 | 36 | 22,023,808 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":36,"estimated_exploration_avoided":22023808,"surfaced_events":73} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

Existing defaults and authority remain unchanged until this wave is prepared and implemented. No commit, push or close is authorized by this planning step.

## Outputs produced or expected

- Admitted change documents with requirements, AC priorities and alternatives.
- Implementation and regression coverage in declared files after readiness.
- Final results in wave.md and typed review events; no permanent evidence folder.

## Review checkpoints

- 2026-10-14: Source-grounded planning complete. Requested lanes express anticipated scope; Prepare will calculate required lanes and obtain independent readiness review. No approvals recorded.
- 2026-10-14: Operator requested fewer waves. Moved the unchanged changes from unreviewed drafts `20nnn`, `20nnp`, `20nnr` and `20np3` here, then removed their empty untracked scaffolds. All six change documents and their ACs remain. Selected one repair wave to share specialist review and final qualification; rejected separate per-fix waves as repetitive and merging qualification-policy work here as an unnecessary dependency.

## Completion criteria

Every admitted AC and task has evidence or an explicit scoped disposition; required delivery reviews and canonical qualification pass before operator-owned closure.

## Handoff or next-wave notes

Prepare after qualification-efficiency work so this batch can benefit from result reuse. The repairs have independent ACs; shared files have one coordinated write owner. Use focused regression feedback during implementation and perform final canonical qualification against the settled combined source.

- 2026-10-14: 20nnl fixture now installs its own declaration using the copied assignment AST span, independent of empty/nonempty or multiline formatting; installed checker/renderer/incoming-hook paths remain exercised. DeclaredLegacyReviewPlanTests passed 3 tests / 0 skips in 0.220 s. Production declarations and migration behavior unchanged; independent review remains pending.

- 2026-10-14: 20nnj exports immutable supported and OPEN status sets; equivalent lifecycle, lint, renderer, memory and context consumers use them. Two focused tests passed across eight status controls, legacy lint and server-free import. Widening OPEN with paused caused one assertion failure, zero errors/skips. Narrow transition subsets remain explicit. Independent review pending.

- 2026-10-14: Status consumer census: equivalent OPEN classifications in render_platform_surfaces.py, context_efficiency.py, wf_server/server_impl.py, wf_server/memory_handlers.py, wf_server/context_efficiency_handlers.py and wave_lint_lib/wave_validators.py now import the shared constant. Operation-specific transition subsets remain explicit; ready/completed remain legacy supported metadata and readied waves retain planned metadata.

- 2026-10-14: 20nno Git queries now clear inherited Git routing/config variables, disable fsmonitor and prefix each literal pathname with ./; exact output mapping and byte bounds are preserved. Nine scope tests passed with no skips, including linked worktree and harmless command markers. Three source mutants removing environment filtering, fsmonitor disabling or literal prefix each caused one assertion failure, zero errors/skips. Existing Git rejected --literal-pathspecs for check-ignore, so the documented prefix alternative is used.

- 2026-10-14: 20nns bootstrap/publication repair passed nine focused controls, including nested/chained child execution and protected publication under -S, zero skips. Lexical bootstrap/source links, nonregular carriers and adjacent cache entries refuse before launch and remain preserved. Removing validation caused four assertion failures; restoring raw exception text caused two, zero errors/skips. No coverage pins refreshed without review.

- 2026-10-14: 20nnq optional boolean provenance control passed five registered publication controls, zero skips: absent/enabled behavior, disabled lookup/metadata, malformed values and both replay directions. Defaults remain absent and policy normalization does not insert a key. Historical attribution remains immutable; docs describe prospective omission.

- 2026-10-14: All six implementations frozen for qualification and independent review. Final separate per-file focused selections passed 54 tests, zero failures/errors/skips; fifteen guard/source mutants were detected by named assertion failures, zero errors/skips. Review packet inventory has 27 files, fingerprint eec25a1c2d14bf300fe2ddd0f49f05fe76fa3342b1f3678e0ee7d25c1a95813e. No full-suite or delivery-approval claim yet.
- 2026-10-14: 20nnm actual registered Prepare/default/evaluate and close dry-run controls preserve target bytes, use the real nonpublishing lint child, report unpublished secrets once, and refuse mutations, copied-marker replacements, unknown modes, malformed identities/protocols and stale source/runner identities. Validated preview context alone suppresses lifecycle locks and completion/accounting. Bounded existing identity algorithms remain coupled; preview grants no resume/pack authority. Ordinary no-upgrade behavior is unchanged.
- 2026-10-14: An artificial combined diagnostic loaded eight test modules into one interpreter and exposed an existing extension fixture module-retention interaction (53/54 passing). The identical selections passed with canonical per-file isolation; no unrelated fixture change. POSIX controls ran on macOS, native Windows remains unexecuted. Public refusal str/detail are path-free; explicitly formatting the preserved exception cause is outside that promise.
- 2026-10-14: Canonical seed 160 trust prose changed outside managed carriers; equivalent local architecture documentation is updated, with no generated region change or whole-file seed/prompt parity claim. Optional provenance defaults remain absent; render/migration preserves explicit false. Coverage inventory remains unchanged and conservatively falls back to full profiles after worker-guard changes.

- 2026-10-14: Delivery review allocation uses a fresh chair and isolated role seats with available gpt-6.1-sol/high reasoning for publication-boundary and stateful compatibility checks; requested settings are recorded, observed runtime identity is not exposed. Full primer precedes fixed seats and rotating docs-contract seat. Source remains frozen while canonical qualification runs; no final qualification approval until its result is assessed.

- 2026-10-14: Canonical qualification stopped red after 15 file completions: cold-import circularity (ARCH-DEL-IMPORT) and newly produced source-adjacent bootstrap bytecode (ARCH-DEL-BOOTSTRAP). Independent chair/architecture scratch probes and actual fixture/worker diagnosis confirmed both. No green receipt written. Source cache artifact is preserved; full delivery seats held while bounded repairs and the package-owner readiness delta are prepared. Full red-team primer completed on the unchanged 27-file fingerprint.

- 2026-10-14: Complete focused repair checks before pausing this wave, then implement the already-readied provider-status wave. Run canonical qualification once against the settled combined tree before final delivery approvals; this avoids a full run immediately invalidated by the next authorized source change. Pending qualification is not a waiver or a completion claim.

- 2026-10-14: Current-receipt readiness restored through focused package-owner review; original unaffected security/full-council judgments retained with explicit attribution. Both delivery repair starts recorded before code changes. Lazy public lint main removes cold-import cycle while preserving no-argument/return behavior. Cache-enabled test startup now uses a private argv prefix; a separate nested read-only sensor uses -B and copied bootstrap. Production carrier refusal remains unchanged.
- 2026-10-14: Guarded diagnostic checks: bytecode file 67 tests passed, zero skips (26.8 s); advisory, change-kinds, archive and distribution files previously passed 110 tests. Initial scratch-only carrier inference was corrected by tracing the actual nested sensor producer; both observed source bytecode artifacts were preserved with verified identical SHA-256 outside the repository. Removing nested -B fails the copied-fixture zero-cache assertion. Final profile-aware fixture checks and independent repair reverification pending; no canonical green receipt or final delivery approval claimed.

- 2026-10-14: Both delivery findings terminal after fresh architecture reverification (nine positive tests, three known-bad controls, all 28 hashes stable). Paused for provider-status implementation; final combined-tree qualification and required full delivery lanes/council remain pending. Full docs validation passed; no close or completion claim.

## Progress Log

- 2026-10-14: Operator authorized closing all six paused waves, committing/pushing and a local 1.31.0 pack, with timing investigation still deferred and one shared default qualification run. That run completed 11,671 tests / 187 files / 12 skips in 884.077s, exit 1: test_tensorwell_client.ClientTests.test_cli_exact_child_timeout_bounded_capture expected the oversized-output ValueError but the child wait reached its deadline and raised TimeoutError. The projection-timing file passed. Source-only independent triage does not establish a capture-cap defect or a harmless scheduling flake; final QA remains unproven. All 60 reviewed source hashes stayed unchanged. No retry or profile run followed the failed default; no current green receipt, closure or new pack is claimed. Compact report remains in ignored cache (close-pack-1.31-default.json); routine log remains temporary. Existing source reviews and terminal repairs stand. Memory proposals add no action beyond canonical tests/guidance, so none were selected; folders retain only wave/change records and typed ledgers.

- 2026-10-14: Operator chose to keep timing deferred and commit/push the reviewed implementation with this wave paused. Final qualification, closure and a new local pack remain pending; no waiver, passing receipt or final delivery approval is claimed.

- 2026-10-14: Final repaired-tree qualification executed 11,661 tests across 187 files with 12 skips in 825.892 s. Both child-marker and reload integration repairs passed; the only failure was the deferred lifecycle projection timing check (32.396 ms p95 versus 25.724 ms effective limit). No green receipt, profile matrix or final QA approval resulted, and the sequence stopped without an unchanged retry. Closure/build remain pending an operator decision on timing; source reviews and terminal repairs remain valid. Retrospective and cleanup: no new memory selected because canonical regression tests and this wave/ledger preserve the future-action lessons. Dry-run proposals were reviewed; no candidate files or routine evidence folders were created.

- 2026-10-14: Operator explicitly retained timing deferral. Final qualification and dependent delivery approvals remain pending; no waiver, suite retry, close, commit, push or build. All three waves are paused with gates closed. The final reload integration repair is terminal after fresh independent verification; preexisting child completion-marker fixture repair awaits a separate scope decision.


- 2026-10-14: Full-depth delivery council source review found no new behavioral defect at the 42-file reviewed boundary. Roster: isolated red-team primer/closing; one disclosed code/architecture context; independent security, QA and reality contexts; rotating docs-contract; chair synthesis. Fixed seats weighed the rotating executable-contract-table alternative and retained the smaller explicit contracts rather than add generation authority. Code/architecture/security approvals are recorded; docs, final QA and council approvals remain conditional on qualification. Existing prose parity test misses prose-only deletion; the reviewer's separate comparison caught omissions but is not shipped regression coverage. No native-platform, live-service or whole-repository universal claim.
- 2026-10-14: Final default ran 11,661 tests / 187 files / 12 skips in 882.161 s, with three failed assertions in two files. All previously repaired functional files passed; an existing reload source-sequence assertion also required integration. QA-DEL-RELOAD-INTEGRATION cycle 3 repositions two unordered membership entries only; the existing named assertion and structural closure test pass (two tests, zero skips), and a missing-context sentinel mutant remains detectable. Fresh verification pending. Child fixture race is preexisting and outside current targets; timing remains explicitly deferred. No green receipt or final qualification claim.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Integration repair cycle 2 is frozen: reload evicts both new stateless helpers; exact refusal/golden/profile fixtures and miniature package dependencies are synchronized; lazy parser freshness and generated-hook parity remain asserted. 48 focused tests across ten isolated groups passed with zero skips. Both missing-helper mutants failed the intended closure assertion. | Existing lifecycle, registry, extension, renderer, upgrade-protocol and bytecode tests; generated session-capture hook came from its canonical renderer. Independent review and full qualification pending; original ARCH repairs remain terminal. |
| 2026-10-14 | QA-DEL-RELOAD-CLOSURE is terminal after fresh independent cycle-2 verification; convergence checkpoint recorded. The reviewer exercised closure, actual parser reload, real bridge/feature bundle, wrapper permutations and registered preview/contracts with zero skips; both removed-helper mutants were rejected. | Durable regression owners: .wavefoundry/framework/scripts/tests/test_lifecycle_gates_structure.py, test_server_tools_lifecycle.py, test_upgrade_protocol.py and test_tool_surface_golden.py. All 42 reviewed target hashes remained stable. Final delivery synthesis and whole-source qualification remain pending. |

- 2026-10-14 final shared qualification: repaired default green (11,672 tests, 187 files, 12 skips); declared reference green with exact 12-skip comparison. Renamed reference completed 11,664 tests with only two timing assertions failing (candidate p95 32.098 > 25 ms; projection p95 31.372 > 30.432 ms), plus 16 correctly marked default-profile-only skips. Reports retained in ignored qualification cache; red comparator result preserved. No functional errors, timing root-cause claim, unchanged retry or duplicate selected matrix. Timing investigation remains deferred. Wave paused pending explicit local-pack/closure timing exception and remaining conditional review approvals.

- 2026-10-14 operator disposition: accepted the two observed renamed-profile timing failures (50-candidate p95 32.098 ms > 25 ms; lifecycle projection p95 31.372 ms > 30.432 ms) for closure and this local 1.31.0 pack. Preserve the red report and comparator refusal; timing investigation remains deferred. Default and declared are green and source identities match. This grants no official release or performance qualification. Current approvals reconcile this exception without another test run. Canonical tests and existing guidance retain the fixture/qualification lessons; no new memory candidate or disposable evidence file is needed.
