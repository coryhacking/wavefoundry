# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-15
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ve3a package-skill`
Title: Package Skill

## Objective

Add two doc-gated skills to the wave-`1p6lp` registry by generalizing its guru gate into a doc-presence gate: `wf-package` (Package Wavefoundry, framework source repo only) and `wf-code-cleanup` (Codebase cleanup review, wherever that surface exists). When this wave closes, both commands are `/wf`-discoverable exactly where their backing prompts live, and target repos are proven unaffected in both directions by test.

## Changes

Change ID: `1vbpl-enh wf-package-skill-doc-gated`
Change Status: `implemented`

Change ID: `1ve3b-enh wf-code-cleanup-skill`
Change Status: `implemented`

## Participants

- Coordinator: agent session coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-15

## Wave Summary

Wave `1ve3a` (Package Skill) delivered two changes: wf-package skill, gated to repositories that carry the packaging surface and wf-code-cleanup skill, doc-gated like wf-package. Notable adjustments during implementation: wf-code-cleanup skill, doc-gated like wf-package: Interrogated (batch) before implementation. Four branches walked, all resolved: the name is operator-settled; description collision risk is bounded by the boundary phrasing requirement plus the standing pairwise-distinctness test; the gate-polarity fixture trivially controls doc absence in a temp repo; whether to seed the cleanup prompt to target repos remains a deliberately deferred separate decision, and the doc gate keeps this change correct under either outcome. One out-of-scope observation recorded for the record, not a blocker: in a target repo whose upgrade doc-reconciliation arm lags, `wf-council`'s third pointer (`red-team-review.prompt.md`) can briefly dangle, the same two-arms caveat wave `1p6lp` already disclosed; a future change could doc-gate nothing or extend `requires_doc` thinking there, but no evidence yet warrants it. Zero open operator questions.

**Changes delivered:**

- **wf-package skill, gated to repositories that carry the packaging surface** (`1vbpl-enh wf-package-skill-doc-gated`) — 5 ACs completed. Key decisions: Gate on backing-doc presence (`requires_doc`), not on repo identity.; Generalize `requires_guru` to `requires_doc` rather than adding a second boolean.
- **wf-code-cleanup skill, doc-gated like wf-package** (`1ve3b-enh wf-code-cleanup-skill`) — 4 ACs completed. Key decisions: Name `wf-code-cleanup`.; Doc-gate on the backing prompt rather than shipping ungated.
## Watchpoints

- **Sequencing:** implementation starts only after wave `1p6lp` closes (single-OPEN rule); this wave depends on `1p6lp`'s registry being in the tree, which it is (uncommitted). Within the wave, `1vbpl` (the gate mechanism) lands before `1ve3b` (which consumes it).
- **The negative direction is the deliverable:** a repo without the backing prompt doc must emit neither skill on any host; the gate-polarity tests prove it, not the description prose.
- **`wf-guru` must not move:** the gate generalization is a refactor for that entry; its emission behavior is pinned by the existing gating regression.
- **Names:** `wf-code-cleanup` is recommend-only; the description and body must keep the sweep from reading as a mutating command, and deletions route through the ordinary lifecycle.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the doc-presence gate makes emission follow repo-local doc state, so any repo that authors or copies a packaging or cleanup prompt gains the skill including its instructions, accepted by design and recorded in both change docs as the capability-follows-doc rationale with the description stating the scoping; strongest-alternative: hardcode a framework-source-repo identity check for wf-package, rejected because the framework has no such signal, `build_pack.py` ships to every target so script presence cannot distinguish, and the doc gate needs no new mechanism)

Seat evidence (code-grounded, verified against the tree 2026-08-15):

- red-team: every load-bearing claim in both change docs resolves against HEAD: `Skill.requires_guru` exists with exactly two gate consumers (`render_skills`, `_skill_output_destinations`, verified in-session); seed `100-project-prompt-surface-bootstrap.prompt.md` marks the packaging prompt public-only/when-present at the quoted line; `install/lifecycle-prompts/` contains neither prompt; zero seed references to `codebase-cleanup-review` (grep empty); both backing prompt docs exist in this repository; the `wf-guru` gating regression (`test_guru_gate_and_host_dir_gate`) exists to pin the refactor. No findings.
- docs-contract-reviewer: AC Priority populated at plan time in both docs (before this council, per the receipt warning); serialization points declared as pure repo-relative paths; catalog obligations named; neither change touches seeds, so no `seed_edit_allowed` cycle is in scope; the registry's standing distinctness/YAML-safety/pointer-target tests cover both new entries automatically. No findings.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 23 | 82,789 |
| implement | 36 | 0 |
| review | 12 | 10,287 |
| **Total** | **71** | **93,076** |

<!-- wave:context-efficiency-state {"generation":71,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":36,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-4980,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1167,"response_debit":6295,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2482},"plan":{"calls":23,"content_source_credit":100596,"derived_artifact_credit":1768,"direct_net":82789,"estimated_tokens_saved":82789,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2846,"response_debit":20235,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":12,"content_source_credit":25100,"derived_artifact_credit":1020,"direct_net":10287,"estimated_tokens_saved":10287,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2116,"response_debit":15063,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":71,"content_source_credit":125696,"derived_artifact_credit":2788,"direct_net":88096,"estimated_tokens_saved":93076,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6129,"response_debit":41593,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7334},"wave_id":"1ve3a package-skill"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
