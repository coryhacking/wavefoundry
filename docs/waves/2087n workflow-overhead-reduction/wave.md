# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-10
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `2087n workflow-overhead-reduction`
Title: Workflow Overhead Reduction

## Objective

Reduce redundant review artifacts, qualification bookkeeping and closure work while preserving independent review, exact skip checks, immutable evidence and safe incremental upgrades.

## Changes

Change ID: `208qs-debt compact-review-artifact-lifecycle`
Change Status: `implemented`

Change ID: `20al0-enh compact-qualification-manifest`
Change Status: `implemented`

Change ID: `20aqf-debt operational-evidence-index-scope`
Change Status: `implemented`

Change ID: `20aqg-enh selective-durable-memory-capture`
Change Status: `implemented`

Change ID: `20aqh-debt advisory-lint-trigger-reuse`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (shared source and canonical seed owner), docs specialist (architecture text after interfaces settle)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, performance-reviewer, security-reviewer

Completed At: 2026-10-10

## Wave Summary

Closed2026-10-10 with five delivered changes: compact temporary review material with durable wave/ledger exceptions; one optional exact qualification report; operational-evidence retrieval exclusion with removal-only compatible upgrades; explicit selective memory capture; and process-only advisory lint reuse. All20 ACs and20 tasks are met; no deferrals. Seven required delivery lanes and operator closure approved. The current12,108-test receipt and complete181-worker report prove the final framework source.

Key decisions: preserve full hard gates and independent authority; keep routine captures in task context/TMP; retain exact execution-origin evidence and strict incomplete refusal; add no source/profile suite, broad memory recuration or evidence chore to consumer upgrades. Advisory reuse proves avoided scans, not universal latency improvement. Lessons remain in canonical contracts and regression tests.

Retrospective and retention: memory preview offered one D1 candidate anchored to its regression test. It adds no concrete future action beyond the canonical close/memory contract and test, so it was not selected; zero candidate/rejection files written. This folder contains only wave.md, five admitted change docs and immutable events.jsonl. Cited/unique proof and the pre-turn dirty baseline remain until reconstructable; routine captures stay temporary. Supporting evidence and limits are consolidated below.

## Watchpoints

- Qualification watchpoint: independent delivery review and qualification are complete; source and seed gates are closed. The existing local pack predates these changes.
- Preserve cited originals, immutable ledgers and unreconstructable dirty-tree baselines; ordinary logs stay temporary.
- Serialize shared server_impl.py, close seed and build documentation. Do not add consumer-upgrade qualification or evidence chores.
- The new local pack is 1.29.0+pvkw; it predates and does not include the 2087n implementation.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| D1 | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer |
| D2 | not_issue | no | not_required | code-reviewer, qa-reviewer, release-reviewer |
| D3 | not_issue | no | not_required | code-reviewer, qa-reviewer, release-reviewer, security-reviewer |

*Machine review state — 3 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 2*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 388 | 1,164,457 |
| implement | 452 | 5,088,073 |
| review | 479 | 2,897,276 |
| **Total** | **1,319** | **9,149,806** |

<!-- wave:context-efficiency-state {"generation":990,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":452,"content_source_credit":5947166,"derived_artifact_credit":0,"direct_net":5088073,"estimated_tokens_saved":5088073,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14943,"response_debit":1298219,"source_credit_count":187,"source_credit_drop_count":0,"structural_source_credit":449452,"workflow_prompt_credit":4617},"plan":{"calls":388,"content_source_credit":2526442,"derived_artifact_credit":6643,"direct_net":1164457,"estimated_tokens_saved":1164457,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20561,"response_debit":1351872,"source_credit_count":138,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3805},"review":{"calls":479,"content_source_credit":4388508,"derived_artifact_credit":3693,"direct_net":2897276,"estimated_tokens_saved":2897276,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42303,"response_debit":1455478,"source_credit_count":159,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2856}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1319,"content_source_credit":12862116,"derived_artifact_credit":10336,"direct_net":9149806,"estimated_tokens_saved":9149806,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":77807,"response_debit":4105569,"source_credit_count":484,"source_credit_drop_count":0,"structural_source_credit":449452,"workflow_prompt_credit":11278},"wave_id":"2087n workflow-overhead-reduction"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 79 | 0 | 37 | 42,610,391 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":37,"estimated_exploration_avoided":42610391,"surfaced_events":79} -->
<!-- wave:exploration-avoided end -->
## Review Checkpoints

- Operator acknowledgment: current request authorizes closing qualified waves, a local test pack, redundant-evidence cleanup and creation/prepare/review of this wave. It does not authorize implementation, Git commit or release publication.
- Plan decisions: each admitted document records the selected approach and rejected alternatives; no unresolved operator preference is invented. Current specialist authority and full validation boundaries are preserved.
- Bounded allocation: independent readiness roles use fresh task-fit technical contexts (requested gpt-6.1-sol/high where available; observed runtime remains host-reported). Read startup context, role and current plans; use MCP-first code validation. Routine briefing/report material remains in temporary storage or task context. A full architectural/data-path primer, fixed architecture/security/QA/reality seats, rotating docs-contract alternative with an additional performance lane and required code/docs/release lanes precede chair synthesis. One automatic plan-repair round maximum.
- Evidence retention after this review: final decisions, real observations, limits and retained exceptions belong here; machine approvals belong only in events.jsonl. No per-seat repository reports are planned.

## Readiness Review Synthesis

Current receipt: `review-policy-a6dbbc09996b0d522243`, policy digest `7b286a04e490ee3c9a98ad57a390535ee9e91e900b2040979dd4b53b4878fc9e`. Full documentation lint and garden passed; initial Prepare correctly refused the seven missing lane approvals and council approval. The readiness run is recorded in events.jsonl. All five admitted plan hashes stayed fixed; all 20 delivery ACs remain unchecked. No code or seed implementation occurred.

The chair selected a full architectural/data-path primer. The evaluator currently stores a fixed standard primer floor and red-team/docs-contract seat selection; this review actually ran red-team, architecture, security, QA, reality and rotating docs-contract, plus separate code, performance and release lanes. No evaluator or policy setting was changed to force this depth.

| Independent review | Observed readiness evidence | Result |
| --- | --- | --- |
| architecture-reviewer | Live owning topology; three deliberately weakened plan contracts detected (profile/receipt, pending memories, hard-gate separation). | No findings in my lane; alternative weighed. |
| security-reviewer | Owned contained unlink passed; replacement/link refused; six publication failures preserved original and removed temps with descriptor delta0; invalid integrity preview refused. | No findings in my lane; wrapper policy remains required. |
| qa-reviewer | Actual two-test worker had one real skip; fake skip/summary produced two apparent identities and the deliberately bad collector was rejected. | No findings in my lane; exact future execution remains unproven. |
| reality-checker | Real pass/skip and failing worker controls; repeated manifest fallback observed; omitted-AC control rejected. | No findings in my lane; finite scope is practical. |
| code-reviewer | Current child cleanup removed a temporary report; deferred read failed while exported data survived. | No findings in my lane; export before cleanup required. |
| performance-reviewer | Actual three-trigger census accepted and omitted repo-profile control rejected; known walker mismatch currently sets full rebuild. | No findings in my lane; no future latency claim. |
| docs-contract-reviewer | Canonical owner matched; omitted-owner control detected; invalid actor refused and valid readiness preview accepted. | No findings in my lane; no new consumer maintenance. |
| release-reviewer | Actual hash/pack fixture: root report left framework hash unchanged; framework/scripts report changed hash and entered payload. Invalid integrity preview refused; canonical 12,057-test receipt still matches. | No findings in my lane; report placement is an implementation watchpoint. |

**Strongest challenge and alternative:** Exact skip IDs/reasons must originate from executed workers and survive profile cleanup; merged output can contain convincing lookalikes. The rotating docs seat independently favored an opt-in structured TestResult collector. All four fixed seats explicitly weighed it and prefer its provenance/simpler proof, acknowledging bounded worker/profile protocol cost. Conservative parsing remains valid only when ambiguity is reported incomplete. This is an implementation recommendation within existing requirements, not a new gate or promise of future execution.

**Implementation notes:** Keep one owned optional report outside `.wavefoundry/framework/`, canonical receipt, hashed source and packed payload; prefer `.wavefoundry/cache/qualification/`. Refuse protected/unowned/link/special targets and verify report writes leave `_hash_inputs` unchanged. Report-specific link refusal must be enforced by the wrapper: the existing contained writer can follow internal links. Scan actual wave-linked pending memories independently of proposal eligibility. Handle semantic and graph compatibility separately; count graph-derived recomputation separately from unchanged-source extraction. Ordinary consumer upgrades retain their existing bounded historical-memory checkpoint; this wave adds no broad memory/evidence/qualification pass.

**Evidence limits and retention:** These are current-plan/source feasibility observations, including local safe controls; no delivery AC is checked off, no suite/profile/index rebuild was repeated, and no Windows claim is made. Some indexed queries returned stale/not-ready responses, so source facts were validated through live MCP reads. QA read the artifact before the primer and formed its initial read then, but emitted its pre-primer sentence after primer loading; this timing limitation is retained rather than claimed as perfect audit order. Individual reports/control files are temporary. This summary and typed ledger retain useful conclusions; no repository per-seat reports were created.

Council synthesis and red-team closing completed with no retained findings. All seven specialist readiness approvals and council-readiness are recorded against the current receipt in events.jsonl. Red-team reconciled every primer concern and the empty synthesis rowset; its falsification check retained execution-origin and report self-contamination as concrete delivery watchpoints. No plan-repair round was needed.

## Readiness Verdict

PASS: final `wf_prepare_wave(mode="ready")` returned `readied: true`, `transitioned_to_active: false`, clean full lint/garden, zero repairs and no pending readiness lanes. The current receipt remains `review-policy-a6dbbc09996b0d522243`. The wave stays planned and readied; no OPEN slot or source-edit authorization was taken. Next: operator-authorized implementation of the five admitted changes, followed by their existing delivery obligations.

## Implementation Allocation

Operator requested implementation of 2087n. Coordinator owns shared server_impl.py, memory, advisory lint, canonical seeds and shared docs. Two isolated implementers own runner qualification and indexing respectively; requested gpt-6.1-sol/high for bounded but technically consequential work, observed runtime unknown. Fresh delivery contexts will review independently. Temporary baseline material stays outside the repository. No closure, commit or new pack is authorized.

## Implementation Evidence

| Admitted change | Delivered behavior and retained proof |
| --- | --- |
| 208qs compact artifacts | Canonical seeds/install/authored/role transport uses task context or TMP for working material; final wave synthesis, immutable ledger, cited originals and unique/dirty proof exceptions remain. Four render/contract controls plus real contained cleanup matrix preserve cited, unique and dirty bytes and refuse identity replacement, links and escapes. No deletion tool, retention TTL, reduced roster or extra consumer maintenance. |
| 20al0 qualification | Opt-in callback-origin worker aggregate, bounded owned cache report, exact strict comparison, source/profile provenance export before cleanup and matching-detail reuse. Public positive/failing/cache/profile/output controls and named guard mutants passed; default/declared tool goldens passed without regeneration flags. Ordinary runs add no report; canonical receipt authority remains separate. D2 preserves the pre-discovery Python sink; D3 now owns a non-inheritable descriptor duplicate through cleanup, surviving actual server stdout isolation. |
| 20aqf retrieval scope | Record-owned operational evidence excluded from default semantic/lexical/graph retrieval; direct reads and typed history remain available. Nine populated public-store controls, 19 compatibility controls and eight guard mutants cover zero unchanged-source embedding/extraction, all resident removal, separate communities, rollback/retry, unknown identities, missing/unreadable roots and absent siblings. A three-path removal took0.299s independently with zero embedding/extraction; no live self-host rebuild. |
| 20aqg selected memory | Current contained targets, explicit source-event selection, immediate pre-write target check, stable dispositions and all actual pending selected records. Generated records use agent validation; manual candidates use existing reviewed status reconciliation. Historical/setup backfill56 passed; selection/target/history/census controls and targeted mutants passed. No live memory files created or reclassified. D1 includes exact wave evidence for manual candidates without reopening finalized manual history. |
| 20aqh advisory reuse | Bounded content-identified process-only full-proof reuse skips repeated unchanged broad triggers while changed documents/dependencies still run; explicit full gates always fresh. Root/rule/version/helper movement, invalid documents, bad scans, special inputs and finite cache/inventory/byte bounds tested with named mutants. No durable proof sidecar. |

Durable executable anchors: `.wavefoundry/framework/scripts/tests/test_compact_review_artifacts.py`, `test_qualification_report.py`, `test_indexer.py::OperationalEvidencePolicyTests`, `test_index_compatibility.py`, `test_memory_records.py::MemoryProposeTests`, `test_advisory_lint_reuse.py`, existing upgrade recovery controls and default/declared tool goldens. Commands use the configured interpreter via run_tests.py or finite named unittest controls; full qualification uses `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache --qualification-report .wavefoundry/cache/qualification/2087n-default.json`.

Performance limits: independent tiny advisory trace avoided two of three full scans but was slower (baseline401/398/399ms; reuse421/482/449ms). Live identity measured335contained reads,241distinct paths,11,430,698bytes and61–86ms. These prove avoided full-corpus work and conservative bounded overhead, not universal latency gains. Ordinary consumer upgrades gain no broad source/profile qualification, new evidence chore or memory recuration; finite recovery tests preserve docs → bounded historical memory → index ordering.

Qualification history: initial sandbox12101/181/13 run failed integration declarations/bootstrap/digest/vocabulary/precision-fixture checks and host-denied process/socket/cache tests; fixes preserved guards and production precision refusal. A direct host unittest lacking runner-managed psutil was discarded. Host-qualified canonical run then passed12101tests/181files/13skips in645.413s at source7773b6b25d51b968e591a14590170b63235ae4c802d93acf317f29c85bf5e508. Its optional report was honestly incomplete solely for indexer407; no exact aggregate comparison was claimed. After repair, all12103worker tests/181files/13skips passed in649.191s, but the overall run was red because coordinator AC/ledger/wave updates occurred during execution; the repository guard correctly refused a new receipt. No qualification claim uses this run. Its optional report exposed a further actual server-transport envelope loss, reproduced independently using actual server isolation and the existing server transport class. D3 repairs descriptor ownership; the new actual-isolation regression failed before repair. All19 report/ownership controls then passed in13.640s with no skips. Complete all review/bookkeeping before a quiet canonical repeat.

**Final qualification (2026-10-10):** The quiet canonical command above passed12,108tests across181files with13skips in628.632s. Fresh `test-cache.json` resultok at2026-10-10T06:06:12.483400+00:00 matches current framework hash `bfdf8d1ecb910925f9633f3ff215385ca38110310d77faf1bc9f74114695f7af`. The opt-in report is executed/complete, validates strictly, matches that source identity, and retains exact detail for all181workers; counts agree with the receipt. All43 reviewed source/contract hashes remain unchanged at fingerprint `85da743756b25cce046847d28123e480971a268102e17fb805727852b8419b9e`. No source edit followed qualification. All20 ACs and20 tasks are met; operator closure is authorized in the current request.

## Delivery Review and Repairs

The current receipt selects seven delivery lanes and no council-delivery. Fresh code/security contexts requested gpt-6-astra/high; other technical lanes requested gpt-6.1-sol/high; observed runtime unknown. Reviewers used original admitted requirements, live MCP source, finite public paths and targeted mutants. Working reports stayed temporary. Source fingerprints: initialde3dd77cf5ed238226000845c5a039158c383c4e80edaa6beb5e70e878e9b677; repair1bc1e24dbb3f74a783f07aebe0749109eabce457c4761f06a76f159884ac78993; current repair2 85da743756b25cce046847d28123e480971a268102e17fb805727852b8419b9e. Typed conclusions and continuation authority are in events.jsonl.

| Finding | Independently observed failure and repair | Current evidence |
| --- | --- | --- |
| D1 manual pending census | Registered memory_add creates a candidate linked by exact wave evidence without source_event; close omitted memory_validation_required. The omission predates this wave but violates its all-actual-pending requirement. Candidate-only evidence fallback now includes it and preserves finalized manual history. Canonical/authored/spec/recovery distinguish manual reconciliation from generated-record validation. | New registered test covers current/disappeared target, unrelated prefix, active bytes and reviewed rejection; independent full-wave-label variant passes. Restored old guard fails pending count; overbroad fallback fails active-history exclusion. Code/QA/architecture independently verified. Other fixture blockers remain; no successful closure claimed. |
| D2 worker output | Real during-test indexer wrapper prefixes the terminal envelope, losing detail despite green execution. Capture protocol stdout before discovery/tests; strict parser unchanged. | Real wrapper/buffered/cache/profile/public comparison controls pass; old current-stdout emission mutant fails completeness. Code/QA/release independently verified. Import-time stderr format replacement remains unqualified and is safely incomplete; no general wrapper immunity claimed. |
| D3 native stdout isolation | Actual server isolation redirects the captured Python sink’s fd to devnull, losing the envelope. Own a descriptor duplicate before discovery; close it on success/error and preserve borrowed sinks. | Actual isolation with exact intentional skip now passes, alongside indexer wrapper and four ownership/exception controls. Fresh code/QA/security checks passed actual server-class/isolation, exact skip, paired profile export/receipt, cleanup/runner exception and exec noninheritance controls. Old capture, omitted cleanup and inheritable-dup mutants fail intended assertions. Release13 public/ownership/strict-reader controls passed6.344s/no skips; normalized pack collection preserves helper/runner/test/cache boundaries. Strict incomplete-evidence refusal remains. |

All typed repair_start events preceded their source mutation. D3 cycle2 independently reverified conforming and atomically derived the required convergence checkpoint; current affected code/QA/release/security approvals follow it. All seven delivery lanes are approved; operator closure signoff is recorded from the current request. Final quiet qualification and completion tracking are now finished. Corrected regression baselines failed the intended assertions before production fixes; one missing thin-runner initialization was corrected and discarded. All252 focused memory/report/compact tests passed in22.891s without skips after repair. Fresh affected code/QA/release contexts each executed positive and safe known-bad controls; architecture and docs independently completed their affected verification. Initial QA62, security16, architecture15, docs10, release CLI and independent performance controls provide unaffected-boundary evidence. Security, performance and original docs scopes had no additional findings.

Authority bookkeeping: a worker changed20aqf's historical Session Handoff outside the digest-excluded ProgressLog, staling its receipt. Restored the approved historical body and moved current status into ProgressLog; original requirements and currency recovered without re-Prepare or scope change. Gates are closed. Fresh registered full docs validation after repair returned full/ok with zero errors/warnings. Renderer wrote no unexpected files; authored canonical carriers reconciled. No configured computational sensors found. MCP implementation/runner match disk; assessment/producer setup remains stale and requires host restart before indexed retrieval. No setup/rebuild added.

Retrospective: D1/D2/D3 are captured by regression tests and existing canonical contracts; no separate memory adds a new future action beyond those owners. No candidate or rejection files were manufactured. Preserve the pre-turn dirty baseline and any cited/unique proof until reconstructable; routine review/test captures remain temporary. Native Windows, downstream installed-consumer integration, exact new archive and whole second/declared package qualification remain unverified. The current request authorizes wave closure; no commit, push or new pack is authorized.

## Evidence Retention

Authorized closure/cleanup completed 2026-10-10. This wave has no evidence folder: its seven durable files are wave.md, five admitted change docs and events.jsonl. Routine captures remain temporary; retain the unique pre-turn dirty baseline until reconstructable. The older 20-series audit covered nine evidence folders with 725 files (11,260,951 bytes); cleanup removed 248 redundant files (2,382,959 bytes) and two duplicate-only folders. The 477 retained files include immutable-ledger citations, unique controls, historical source identities and dirty baselines; the planned/readied 2071o wave remains intact. Each affected closed wave records its exceptions; mutable citations were consolidated or redirected to the retained original, without rewriting history or generating another permanent report. No source edit, suite rerun, setup, commit, push or pack was needed for cleanup.
