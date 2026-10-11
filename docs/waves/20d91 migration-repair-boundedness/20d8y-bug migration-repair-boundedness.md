# Bound migration cleanup, preview extraction and exact link repair

Change ID: `20d8y-bug migration-repair-boundedness`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-10-11
Wave: 20d91 migration-repair-boundedness

## Rationale

Let framework operators preview and retry supported document migrations without unrelated unreadable files aborting a no-op, unsafe stale artifacts interrupting cleanup, or unbounded incoming preview extraction. Scratch fixtures show a directory cleanup refusal escapes `render_platform_surfaces.remove_files`, an empty role-pair plan reads invalid UTF-8 and raises, and lifecycle guide moves retain supported links to the old path. Repair only these existing seams.

## Product Intent

Supported migration moves and exact current-document links should converge predictably, with truthful dry-run and partial-progress diagnostics. Existing project-authored prose and history remain protected. Context: `docs/ARCHITECTURE.md`, `docs/architecture/data-and-control-flow.md` and `docs/contributing/build-and-verification.md`.

Design Intent: N/A — no UI surface changes.

## Requirements

1. `render_platform_surfaces.remove_files` reports and skips refused linked paths, directories and special files, preserving them and their referents; ordinary stale regular files are still removed with contained identity checks. A skipped cleanup must not authorize later writes through the refused path.
2. `upgrade_extensions._preview_council_role_links` validates selected incoming Python member names as portable relative paths before reading: reject drives, absolute names, backslashes, empty/dot/traversal components and aliases/duplicates. Cap selected-member count, per-member bytes and aggregate bytes before any content read; bounded reads must also reject inconsistent/decompressed excess. Reuse applicable existing archive validation helpers; no target extraction or new permanent artifact is permitted for this preview.
3. Use explicit finite preview limits of at most 2,000 selected members, 8 MiB per selected member and 64 MiB in aggregate; preflight the complete selected set before reading a member. Current-tree census of every Python file under scripts (including tests, hence an upper bound for the shipped set) found 357 members, a 1,272,686-byte maximum and 20,987,797 aggregate bytes; the proposed caps accommodate this measured control with finite headroom.
4. With no confirmed migration candidates, `_council_role_link_plan` performs no docs traversal. Candidate discovery and current-doc reads treat unreadable, undecodable or refused paths predictably, with actionable preserved-path diagnostics. An unrelated refused document is skipped and reported while safe independent repairs continue; an unreadable candidate/source blocks its own unsafe move before writing it. Existing mandatory source/target conflicts remain blocking and preserve all files. If unreadability cannot be skipped without preserving the contract, preflight that blocking condition before target extraction; never defer a newly predictable fatal refusal until extraction has already completed.
5. Do not silently abort migration after framework extraction: surface incomplete repair and retry guidance. Existing role metadata remains role-pair authority. For lifecycle pairs, preflight every mandatory source/target conflict, plan supported exact edits using a readable contained legacy source as authority, apply those readable-document edits before moving/unlinking that source, and retain the source if an actual planned write fails. A retry then completes remaining planned edits before the byte-preserving move, without duplicate moves. If the old source is absent, lifecycle-overview's new target confirms the pair only when it is a contained readable regular file at the registered carrier path and contains exactly one balanced existing review-policy region whose normalized body equals `review_policy.REVIEW_POLICY_SURFACE_BLOCKS` for that carrier. New-only delivery-workflow has no existing control marker and grants no automatic repair authority. Refused/unreadable unrelated docs are preserved and reported; later links from those skipped docs to an unconfirmed new-only target remain diagnostic/manual repair. Do not claim automatic convergence for every skipped unreadable link, use prose/title matching as proof, or add a marker, manifest or evidence artifact.
6. `migrate_lifecycle_document_renames` uses the same exact supported local-link destination repair and dry-run preview as role moves, with lifecycle pre-move edit ordering. Preview and apply agree on eligible edits; a source document's own link edits apply at its old path before the move, and the move copies those current bytes and mode exactly. Preserve unrelated bytes, labels, suffixes, line endings and file modes; unsupported/ambiguous destinations remain diagnostic-only and history stays untouched.
7. Combine confirmed role and lifecycle move pairs into one bounded current-doc traversal per rendering/preview operation. Preserve public return forms: `ChangePromptMigration` with tuple `written`/`link_report`, and the renderer's existing path-list result. Apply finite caps of 50,000 visited filesystem entries (including directories and non-Markdown names), 20,000 candidate documents, 8 MiB per document and 256 MiB aggregate bytes read. Count metadata traversal before descending/reading rather than materializing an unbounded rglob result; never descend linked directories. A per-file refusal/oversize is a preserved-path skip/report; an entry/count/aggregate overflow deterministically refuses the combined plan before its writes or moves, with the limit class and retry remedy visible. Reuse this bounded plan in existing preflight/preview flow where blocking before extraction is required; add no separate whole-upgrade pass. Reuse the current scanner/mask/replacement helpers rather than a new general migration framework. A no-follow census of the entire docs tree found 3,843 filesystem entries, 2,235 Markdown documents, a 315,344-byte maximum and 27,615,735 Markdown bytes; caps leave finite headroom above that measured broader-than-current-doc control.
8. Do not add whole-upgrade scans, new reports or unrelated reconciliation work; test the actual renderer and incoming-preview entry paths as well as focused helpers.

## Scope

In scope: the source symbols named in Requirements and Discovery evidence, their tests listed below, directly necessary contained-helper edits, and the named architecture/build guidance.

Out of scope: new receipt gates, general frameworks, release packaging, index rebuilds, unrelated host hooks/prompts, history rewriting, commits and wave closure. Optional bytecode exemptions are not admitted.

## Acceptance Criteria

- [x] AC-1: Cleanup reports and preserves refused links, directories and available special-file fixtures while deleting eligible ordinary stale files; both parent and final links have preservation controls. A fix-absent cleanup must fail the continuation expectation.
- [x] AC-2: Incoming preview rejects invalid portable names and duplicate/alias members before reading content; safe nested Python members still preview. Both Windows-style and POSIX-style invalid-name controls are portable fixtures.
- [x] AC-3: Member count, per-member and aggregate limits reject over-bound selected sets before any member-content read, and bounded extraction refuses actual excess; just-under-bound controls pass. Preview does not mutate the target or create a permanent report.
- [x] AC-4: No confirmed migration candidates causes zero document reads/traversals, including on a tree containing unreadable or undecodable ordinary docs; a fixture catches the current empty-pair traversal.
- [x] AC-5: Unreadable/refused unrelated current docs are preserved, reported with retry guidance and skipped while readable supported links repair; unsafe source/candidate confirmation refuses before its own move. Actual renderer/upgrade entry tests verify incomplete repair is visible after extraction.
- [x] AC-6: Role and lifecycle moves repair the same supported exact destinations in current docs and share dry-run planning; unsupported links and history remain unchanged. Lifecycle supported edits occur before source move/unlink, including edits inside the source guide; preview's planned edits agree with apply, with no preview target writes and exact current source bytes/mode at the move boundary.
- [x] AC-7: An actual lifecycle planned-link write failure preserves the legacy source, and retry completes readable planned edits before moving it without lost bytes/modes or duplicate moves. Existing role metadata and the exact registered lifecycle-overview policy-region control admit confirmed new-only retries; unmarked new-only delivery-workflow, malformed/duplicate/mismatching regions and unrelated targets grant no automatic repair authority. Refused/unreadable skipped docs remain preserved/reported, and later unconfirmed new-only links receive manual-repair diagnostics rather than a false convergence claim.
- [x] AC-8: Combined role and lifecycle migration uses one bounded current-doc traversal per renderer/preview operation; instrumented entry/byte counters and bounds controls detect duplicate traversal, unbounded metadata descent or reads. Per-file skips and aggregate-plan refusals have distinct deterministic diagnostics; aggregate overflow writes/moves nothing. Existing public return forms are unchanged and no extra whole-upgrade pass or permanent artifact is introduced.
- [x] AC-9: This change's focused suites and added tests pass, its authored/edited docs validate, and no failure elsewhere is attributable to this change; fix-absent controls discriminate each repaired seam.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Non-destructive cleanup. |
| AC-2 | required | Portable member boundary. |
| AC-3 | required | Resource bounds. |
| AC-4 | required | True no-op. |
| AC-5 | required | Predictable failure behavior. |
| AC-6 | required | Repair/preview parity. |
| AC-7 | required | Retryable partial repair. |
| AC-8 | required | Bounded shared work. |
| AC-9 | required | Scoped verification. |

## Tasks

- [x] Create ordinary scratch migration/preview/cleanup regressions through real producers and entry paths.
- [x] Add contained cleanup refusal reporting and fully preflighted bounded incoming preview extraction.
- [x] Reuse exact destination helpers for combined bounded role/lifecycle planning; implement no-op, bounded metadata/read work, skip/report, pre-move lifecycle edits and the explicit source/registered-marker retry rule.
- [x] Update migration boundary and preview documentation; retain custom prose/newline/mode and history contracts.
- [x] Run focused tests, work-counter controls and independent security/QA/performance review; record AC evidence before canonical qualification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Reproduction and minimal repair | implementer | Readiness and activation | Python stdlib, contained I/O, regression controls; one write owner. |
| Documentation reconciliation | implementer | Repair behavior stable | Named docs only; no new report/evidence folder. |
| Independent delivery review | code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, performance-reviewer | Current implementation | Read-only; Council synthesizes; coordinator owns state. |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_document_names.py`
- `.wavefoundry/framework/scripts/tests/test_contained_repo_access.py`
- `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`
- `docs/ARCHITECTURE.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/layering-rules.md`
- `docs/contributing/build-and-verification.md`

The implementer exclusively owns listed source/test/doc edits during activation; review lanes remain read-only. Protected: canonical seeds, generated agent/platform surfaces, root AGENTS.md, workflow/repo-profile config, qualification/test receipts, shipped ownership fixture, Git and history. No protected-surface edit is planned; directly necessary helper or fixture changes require coordinator scope check. Other waves touching shared modules must finish/pause before activation; never edit another wave's artifacts.

## Affected architecture docs

- `docs/ARCHITECTURE.md`: reconcile only this change's boundary or verification contract.
- `docs/architecture/data-and-control-flow.md`: reconcile only this change's boundary or verification contract.
- `docs/architecture/layering-rules.md`: reconcile only this change's boundary or verification contract.

No new ADR or architecture restructuring is planned.

## Knowledge Transfer Plan

Record focused regression names, fix-absent outcomes and material limits in this change's Progress Log and wave.md. Preserve custom-prose/newline and real-producer fixture cautions from project memory; a guard is complete only when its absence is detected. Keep scratch captures outside the repository; no permanent evidence folder.

## Persona Review Plan

Use the material specialist lanes declared by wave.md; framework-operator concerns are incorporated into their refusal/retry review rather than a separate blanket persona pass. Product-owner and additional persona/factor lanes are requested only when Prepare policy derives them or a material scope finding justifies them. Existing policy-derived lanes and Council authority remain binding.

## Wave Readiness Plan

Coordinator performs docs validation, independent required specialist lanes and Council readiness, then final ready-only Prepare. Implementation requires clean typed readiness and later single-OPEN activation. Operator authorized preparation/review/implementation; this planner owns docs only. Existing open wave remains open until its coordinator pauses it.

## Watchpoints

Use generic fixtures and source anchors only. Report changed assumptions before implementation. Partial failure and skipped safety refusals stay visible. Reuse current matching evidence; never mint receipts manually or copy raw transcripts into docs.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Implementation, qualification and required delivery review complete; pause for operator closure. | All nine ACs and five tasks are complete. Matching isolated canonical suite passed 12,321 tests/185 files/769.255s, exit 0, with 12 aggregate skips. Current genuine receipt inputs `78b932974d651666233577f7a80a8baefda3bc680ea11871af91117658df2c94` were verified and transferred byte-identically. Three actual fixture findings are independently completed with cycle-2 convergence; six required specialist lanes and FULL Council approve. Current full docs boundary passed with zero errors/warnings. Native Windows/live-host upgrade behavior and automatic convergence of skipped unreadable links remain unqualified; only operator closure approval remains. |
| 2026-10-11 | Repair read-back: paired freshness observations only. | The coordinator recorded repair_start for a confirmed preexisting observation-clock qualification fixture failure and approved the directly necessary AmbientGitEnvBuildIsolationTests scope under AC9. Capture one realistic observation time per fixture and apply it only during the two paired freshness reads through a fixture helper, including the shallow-env sibling. Keep real clean/ambient builds, raw-Git rename nonvacuity, every history/freshness/drift comparison and field. No production clock, assertions, budget, requirements or inventory change; preserve all eleven prior frozen targets. Run the affected class and faithful deterministic rounding-boundary/fix-absent controls; qualification and independent reverification remain pending. |
| 2026-10-11 | Shared-observation fixture repair verified and refrozen. | Actual AmbientGitEnvBuildIsolationTests passed both tests (2.603s), preserving real builds and every original field/assertion. Deterministic private probes kept both real full-build bodies: repaired global-config and shallow-file cases passed, while removing only the shared-read clock control made each fail its existing freshness equality across a 20ms rounding boundary, with two real builds/two reads per case and no setup errors/skips. Adjacent BatchedRetrievalReadTests passed both tests; the production query clock and all eleven previously frozen paths remain unchanged. The new fixture controls only paired freshness-read time, not build/runtime clocks. Canonical qualification and independent chair reverification remain pending; AC9/final task stay unchecked. |
| 2026-10-11 | Repair read-back: derive two combined-render fixture literals. | The coordinator recorded repair_start for the independently reported qualification actor-census finding. Derive the legacy role content from the declared actor table and its link destination from the existing role-rename pair; retain identical default scratch bytes and all existing assertions. Only this already-owned fixture case and its necessary import may change; ownership inventory/census, product behavior, memory policy and requirements remain untouched. The valid-ZIP repair stays frozen. Rerun the actual combined renderer, unchanged actor census and adjacent migration controls; canonical qualification and independent reverification remain pending. |
| 2026-10-11 | Derived legacy fixture repair verified and refrozen. | Actual combined-render case passed (one test, 0.051s); the full lifecycle fixture file plus unchanged ActorTokenCensusTests passed (31 tests, 0.339s), all exit 0 without skips. An instrumented execution of the real combined case confirmed its role and peer producers retain the exact pre-repair default scratch bytes (one test, 0.049s). No single-walk, byte, newline, mode or retry assertion changed. Only the necessary review_evidence import and two derived fixture values differ from the previous freeze; the other nine original targets, valid-ZIP repair, ownership census/inventory and contained helper remain unchanged. Canonical qualification and independent chair reverification remain pending. |
| 2026-10-11 | Verified existing carrier evidence and cap headroom. | executed: real scratch renderer put the review-policy marker in lifecycle-overview but not delivery-workflow. Current no-follow docs census: 3,843 entries/2,235 Markdown files/315,344-byte max/27,615,735 bytes; all-Python scripts census: 357/1,272,686-byte max/20,987,797 bytes. source-inspected: `review_policy.REVIEW_POLICY_CARRIER_REGISTRY`, `REVIEW_POLICY_SURFACE_BLOCKS`, marker constants and `_change_prompt_pair_conflict`. No source/target conflict refusal is softened. |
| 2026-10-11 | Planning discovery completed; implementation pending. | executed: stale directory was preserved but refusal escaped; empty pair list plus invalid UTF-8 ordinary doc raised; lifecycle source moved and exact local link retained its old destination. source-inspected: `remove_files`, `_council_role_link_plan`, `_confirmed_council_role_pairs`, both migration entry functions, `_preview_council_role_links`, `render_agent_surfaces`, `post_extract`. Archive portability/cap failures and partial-repair behavior remain unverified executable premises for readiness/implementation; absence of member caps was observed in the preview extraction code, not claimed repository-wide. |
| 2026-10-11 | Read-back confirmed and implementation activated after the prior delivered wave paused. | Coordinator relayed: preserve refused stale entries/referents; preflight portable incoming Python names and finite count/member/aggregate caps; combine confirmed role/lifecycle exact-link planning into one bounded no-follow current-doc traversal. No candidate means no traversal. Source-present lifecycle edits precede current-byte/mode-preserving moves; actual failed edits retain the old source; registered-region proof alone admits supported new-only overview retries. Unconfirmed/unreadable paths remain diagnostic/manual repair. All nine ACs/five tasks remain pending. Memory cautions about custom prose, byte/newline/mode preservation, exact migration matching and fix-absent controls apply. Original Session Handoff is the planning snapshot; current authority is this log and wave.md. Scope/requirements/digested handoff unchanged. |
| 2026-10-11 | Implemented admitted migration guards and regression controls; final qualification/review pending. | Cleanup preserves/reports linked, directory and FIFO entries and continues to eligible regular files; platform lexical preflight refuses subsequent existing-link writes while retaining ordinary unchanged-byte/executable-mode mtime behavior. Incoming preview checks raw portable names/aliases and complete count/member/aggregate metadata before content reads, then bounds decompressed reads. Role/lifecycle pairs share one bounded current-doc walk, with unrelated per-file skips and aggregate prewrite refusal. Lifecycle edits precede fresh-byte/mode moves; retry/registered-region and manual-repair controls apply. Existing contained identity-bound movers still accept safe in-repository parent links; the no-follow docs walker never descends linked directories. `contained_files.py` is unchanged from the prior wave. |
| 2026-10-11 | Integration failures corrected within admitted source/test scope; no waiver or receipt claim. | First six-file run was diagnostic: an extra mover-parent restriction broke its preexisting control and was removed; six scalar/graph-doc fixtures supplied nonexistent `MagicMock` or non-ZIP archives, so their unrelated incoming migration hook is explicitly isolated while new real incoming/hook tests retain execution. Concurrent implementation/doc edits invalidated that diagnostic run. Corrected named fixture/mover/focused controls passed. Earlier selection/import/indent errors were test-authoring/command diagnostics, not successful qualification. |
| 2026-10-11 | Guard-removal controls distinguish the repaired seams. | Private in-memory faithful mutants: 17 variants rejected by named assertions, no setup errors. Covered cleanup continuation; no-candidate traversal; raw portable names/case aliases; count/member/aggregate preflight; bounded decompression; lifecycle link planning and edit-before-move ordering; exact registered-region authority; metadata/document/aggregate limits; failed-read budget charge; pre-extraction hook ordering; fresh source bytes; unrelated-doc continuation; denied candidate inspection. Failed reads conservatively charge cap plus one sentinel; a crossing stops work, bounding scan reads by aggregate budget plus at most one crossing sentinel. This may refuse earlier than actual consumed IO. No native Windows or arbitrary same-user atomic-path authentication is claimed. |
| 2026-10-11 | Prior six-file candidate qualified; final denied-inspection correction tested separately before freeze. | Genuine focused runner exit 0: 1,146 tests/6 files/191.976s, two aggregate existing skips (no skip-identity/parity claim). Final candidate discovery now uses lstat, with only FileNotFoundError classified absent; PermissionError refuses before independent edits/moves, with a path-free remedy. Final direct added tests: 25, zero skips; affected public entry and existing mover/scalar-doc controls rerun on that final source. Canonical whole-suite and all independent delivery approvals remain coordinator-owned and pending, so AC9/final task stay unmet. |
| 2026-10-11 | Repair read-back: qualification fixture archive producers only. | Independent QA identified plain-byte release.zip controls in IndexUpgradeGuardTests; the coordinator recorded repair_start and approved this directly necessary AC9 fixture target. Replace only its primary and concurrent-root valid-control producers with distinct valid empty ZIP archives, using comments to retain distinct package identities. Keep deliberate corruption and every handoff assertion; production preview remains real and unchanged. The original 44-test diagnostic had 23 BadZipFile errors, which are fixture failures, not guard-removal or exploit proof. The ten frozen implementation targets remain unchanged; rerun the affected file and retain AC9/final task pending canonical qualification and fresh QA reverification. |
| 2026-10-11 | Narrow valid-archive fixture repair verified and refrozen. | The affected test_index_upgrade_guard.py file passed all 44 tests in 6.801s, exit 0 with no skips; real preview remained enabled. Both actual fixture producers additionally yielded empty readable ZIPs with different comments and distinct SHA-256 identities, preserving primary bytes across the concurrent-root control. Existing altered-package/checkpoint negatives and handoff assertions passed unchanged. This repairs qualification setup, without a new guard or product-behavior claim. The original ten frozen targets and contained helper remain unchanged; canonical qualification and independent QA reverification remain coordinator-owned and pending. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Request only material specialist review lanes. | Wave record names scope-specific lanes; preserve policy-derived requirements and Council. | Reject blanket independent specialties/personas absent a material boundary or policy trigger because they add overhead without a demonstrated quality benefit. |
| 2026-10-11 | Use source-present pre-move lifecycle link edits and existing registered-marker confirmation only. | A planned-write failure retains the source and remains retryable; new-only lifecycle-overview has bounded explicit carrier evidence. Unmarked delivery-workflow grants no retrospective authority, so skipped-doc links may need manual repair. | Reject a new persistent marker/manifest because it adds an artifact and changes custom-guide bytes; reject filename/title/prose proof because unrelated targets could satisfy it. |
| 2026-10-11 | Required divergent pre-plan completed. | Select targeted shared planning with existing exact-link helpers: it meets cleanup, preview and retry needs within existing migration entry points. Reject documenting failed repairs alone because supported lifecycle links would remain broken. Reject a general migration engine or extra whole-upgrade scan because it adds ownership surface and repeated work beyond the bounded seam. | Alternatives critiqued in selection rationale. |
| 2026-10-11 | Execute authorized follow-up within named scope. | Operator authorized preparation, review and implementation; coordinator serializes waves and pauses completed work. | No close, commit or push; unchanged authorized execution packet needs no new permission hold. |

## Risks

New-only delivery-workflow lacks machine identity and cannot safely authorize automatic retrospective repair; skipped unreadable documents may require explicit manual link repair. Actual planned-write retries retain the legacy source until edits finish. The lifecycle-overview region is a bounded framework-carrier confirmation, not authentication against arbitrary same-user content forgery. Test specified finite traversal/read caps at readiness and implementation; preserve current role-link exclusions, exact-span handling and platform tree-kill routing.

## Session Handoff

Planned; no code edited and no AC/task complete. Coordinator owns Prepare/Council and future activation. Read this file and wave.md for durable scope/evidence. Global handoff is coordinator-owned.

Review routing note: requested lanes are scope-specific; Prepare's actual policy-derived requirements and current Council gate remain authoritative. Product-owner and other unrequested specialties are not independently mandatory absent policy selection or a justified material finding.

