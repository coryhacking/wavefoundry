# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-22
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1yp0y pre-release-install-reliability`
Title: Pre Release Install Reliability

## Objective

For the Windows prerequisite change, proper diagnosis is the primary outcome: make every inability to run python3 visible with the failed stage, observed evidence, uncertainty and an actionable next step, including when local repair is prohibited. Repair mechanisms are secondary and a new launcher is not mandatory.

Before the next release, discover and diagnose native-Windows python3 prerequisite failures, including a usable python.exe without python3, and provide reviewed remediation guidance while keeping MCP launches on python3, and remove the verified validation and renderer-discovery gaps from the 1.25.0 install report. Preserve cross-platform launches, source-repository drift checks, permission boundaries and resumable installation.

## Changes

Change ID: `1yo5l-bug windows-python-launch-compatibility`
Change Status: `implementing`

Change ID: `1yp0x-bug fresh-install-validation-and-resume`
Change Status: `implementing`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (single source/seed writer; coordinator owns lifecycle records)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-09-22

## Wave Summary

Wave `1yp0y` (Pre Release Install Reliability) delivered two changes: Windows Python Prerequisite Discovery and Remediation and Fresh Install Validation and Resume. Notable adjustments during implementation: Windows Python Prerequisite Discovery and Remediation: Added non-admin enterprise remediation, conditional launcher qualification and policy-blocked IT handoff; Windows Python Prerequisite Discovery and Remediation: Operator corrected scope: preserve python3, discover/diagnose missing availability and guide or perform reviewed remediation.

**Changes delivered:**

- **Windows Python Prerequisite Discovery and Remediation** (`1yo5l-bug windows-python-launch-compatibility`) — 5 ACs completed. Key decisions: Defer native Windows qualification until after the next release; Select guidance-only remediation; no environment repair implementation
- **Fresh Install Validation and Resume** (`1yp0x-bug fresh-install-validation-and-resume`) — 4 ACs completed. Key decisions: Use explicit docs_lint.framework_internal_constants boolean opt-in; Select scoped validation and existing-renderer guidance

**Intentional deferrals — 1yo5l:** AC-3 (native repair, fresh-host MCP and representative hook) and AC-6 (native standard-user repair and policy-blocked IT handoff) remain unverified. Operator deferred these and their two associated verification tasks to external Windows testers after the next release on 2026-09-22. Guidance is delivered; no native pass claimed. Protocol: post-release-windows-validation.md. No deferred ACs in 1yp0x.

**Retrospective and retention:** alternate Python discovery is not canonical readiness; packaged scripts do not establish source identity. Canonical guidance captures both lessons; memory checkpoint yielded zero candidates. Retain all eleven authoritative/unique wave files, both fingerprints and ledger-cited paths; no disposable scratch found. Evidence index: final-review.md, implementation-evidence.md, guidance-propagation.md, readiness-review.md and post-release-windows-validation.md.

## Watchpoints

- Fresh checkouts of already-seeded repositories need the same pre-MCP diagnosis: committed config/install history does not prove machine-local python3 readiness; no reseed or rebuild as a diagnosis remedy.
- Release blocker: required before the next release; no version bump or publication is authorized by this plan.
- Guidance-only remediation is selected; canonical MCP launches remain python3. No new launcher or environment repair is implemented. This is an explicit design decision, not permission to edit source prematurely.
- Enterprise remediation must support standard users without assuming admin rights, Store access or Developer Mode. Qualify permitted user-level repair; treat a user-local python3.exe launcher as an unverified candidate until native evidence exists. If enterprise policy blocks repair, provide an IT handoff and keep setup unready.
- Operator deferred native Windows qualification to external testers after the next release on 2026-09-22. Simulated platform tests and source review do not qualify Windows support; retain that limitation and follow post-release-windows-validation.md.
- The field report does not establish why Phase 1 failed to surface the Python concern; logs would be needed for that attribution.
- Preserve MCP renderer permission boundaries and project-authored regions. No implicit PATH repair, alternate MCP command, new renderer tool, historical-doc sweep or index rebuild. Any repair writes require a named reviewed scope.
- The existing planned prompt-template work (1vvs3) is separate; this wave does not absorb it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| downstream-guidance-contracts | do_now | no | completed | docs-contract-reviewer |
| timeout-discards-probe-output | do_now | no | completed | security-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 103 | 2,117,020 |
| implement | 138 | 1,691,471 |
| review | 157 | 1,052,498 |
| **Total** | **398** | **4,860,989** |

<!-- wave:context-efficiency-state {"generation":307,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":138,"content_source_credit":1913453,"derived_artifact_credit":31,"direct_net":1691471,"estimated_tokens_saved":1691471,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5011,"response_debit":225999,"source_credit_count":67,"source_credit_drop_count":0,"structural_source_credit":5051,"workflow_prompt_credit":3946},"plan":{"calls":103,"content_source_credit":2140890,"derived_artifact_credit":3841,"direct_net":2117020,"estimated_tokens_saved":2117020,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4462,"response_debit":113004,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":80542,"workflow_prompt_credit":9213},"review":{"calls":157,"content_source_credit":1318021,"derived_artifact_credit":4405,"direct_net":1052498,"estimated_tokens_saved":1052498,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":20237,"response_debit":252007,"source_credit_count":98,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":398,"content_source_credit":5372364,"derived_artifact_credit":8277,"direct_net":4860989,"estimated_tokens_saved":4860989,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29710,"response_debit":591010,"source_credit_count":263,"source_credit_drop_count":0,"structural_source_credit":85593,"workflow_prompt_credit":15475},"wave_id":"1yp0y pre-release-install-reliability"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 21 | 0 | 15 | 14,462,416 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":15,"estimated_exploration_avoided":14462416,"surfaced_events":21} -->
<!-- wave:exploration-avoided end -->
## Current assumptions

A discovered python.exe is diagnostic evidence, not an alternate MCP launch command. The required outcome is a usable canonical python3 command. Guidance-only remediation is selected; the operator approved an explicit docs_lint.framework_internal_constants opt-in, defaulting to consumer behavior. The next release number is deliberately unspecified. Native qualification will use an available Windows host or an operator-run reproducible procedure; no host execution is claimed at planning time.

## Outputs produced or expected

Two admitted bug plans now exist. Delivery must include the prerequisite-path census and remediation decision, guidance propagation tables, source/consumer validation evidence, real-renderer partial-install evidence, operator-deferred native-Windows test protocol, independent review and the normal framework/docs receipts.

## Review checkpoints

- **Final readiness and delivery council — 2026-09-22: PASS.** Standard primer; rotating seat docs-contract-reviewer. Actual roster: independent red-team primer; code/architecture paired context; QA context; security/docs paired context and council synthesis. Three fresh specialist contexts, not five. Strongest challenge is untested native diagnostic semantics; strongest alternative is holding release for Windows qualification. Operator selected post-release external testing, retained explicitly as unverified. Documentation timing conflicts corrected after the frozen review and independently reverified; no remaining implementation blocker. See final-review.md and both fingerprints. Current typed approvals bind review-policy-87cce96d1a31c1090b1e.
- **Close readiness — 2026-09-22:** Prepare succeeds; close dry-run proves current 9,550-test framework receipt, lint and garden pass. Only operator approval/signoff remains withheld. No close or commit performed. Scanner coverage advisories retain binary/compressed/presentation skips; they are not a complete scan guarantee. No confirmed-secret reminder returned.


Prepare and readiness Council must resolve the remediation scope and validator applicability before source edits. Code/QA cover real producers and meaningful negative controls; architecture verifies the unchanged launch contract and remediation boundary; security checks probing and unchanged permission authority; docs-contract verifies canonical-to-local propagation. Delivery follows the current Prepare receipt.

## Completion criteria

All admitted required ACs and tasks reconciled, independent reviews current, native-Windows qualification explicitly operator-deferred with retained protocol, docs validation clean and framework receipt current. No silent waiver of Windows evidence to meet a release date. Operator owns closure and release publication.

## Release sequencing

Both changes belong before the next release. They have no semantic dependency on each other's code; use one implementer and serialize shared launch/install guidance. Settle the Windows remediation path first, then reconcile the install instructions once. Package and release only after this wave is delivered and closed and ordinary release gates pass.

## Handoff or next-wave notes

Implementation and final review complete. Operator instructed closure then commit. Native Windows testing follows after the next release; no release or push is authorized.

## Implementation allocation

Coordinator implements Windows diagnostics and setup ordering, then integrates independent validator implementation and guidance reconciliation. All source writers wait for readiness and activation. Read-only reviewer contexts are independent of implementation; native Windows qualification is explicitly deferred to post-release testing by the operator.

## Work allocation rationale

Readiness review used independent contexts with paired compatible remits; models/effort inherited from the session (actual worker identity not exposed). Implementation uses a cross-cutting coordinator for Windows process diagnostics and separate bounded implementers for validator scope and authored guidance; these paths do not overlap. Existing host model inheritance is adequate for bounded Python/config and prose changes; integration and tests remain coordinator-owned.
