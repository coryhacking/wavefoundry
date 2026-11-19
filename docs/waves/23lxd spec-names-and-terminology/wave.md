# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-16
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23lxd spec-names-and-terminology`
Title: Spec Names And Terminology

## Objective

People arriving from spec-driven tools find the vocabulary they already use: the planning document is a "spec", the lifecycle phrases, prompts and skills are named for it, and the durable documents under `docs/specs/` are "behavior contracts". The earlier phrases keep working as aliases and installed repositories migrate without losing project-authored prompt content. No tool name, record label, key, code or path changes in this wave.

## Changes

Change ID: `23mqu-change spec-lifecycle-names`
Change Status: `implemented`

Change ID: `23myn-change spec-and-behavior-contract-terminology`
Change Status: `implemented`
Depends On: `23mqu-change spec-lifecycle-names`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-17

## Wave Summary

Wave `23lxd` (Spec Names And Terminology) delivered two changes: Rename the lifecycle prompts, phrases and skills from "change" to "spec" and Reword live text: the planning document is a "spec", the durable documents are "behavior contracts".

Intent outcome: 2026-11-17: after the reopen; supersedes the earlier Intent outcome paragraph above. Drafted by the coordinator, an interested party, from the lanes' reports; the independent intent checks are qa-reviewer's read, recorded in its delivery approval, and the council-chair's verdict, which follows. `23mqu`: establishes, unchanged. `23myn`: under the default profile, establishes: one name for each document, with the vocabulary stating that tools, record labels and identifiers are named for the change. Under a profile that renames the item, partially: the eleven composed strings (ten composed strings and the council skill's Boundary line) follow the profile's item noun, and literal prose (seeds, install templates, tool descriptions, lint and gate messages) says "spec". That is the scope the operator chose ("I think it should still follow the profile's noun"; "Downstream can change seeds if needed"). The gap typed as `INTENT-DEL-1` is addressed by that decision and its implementation, not by the coordinator's earlier reading, which was withdrawn. The census behind the earlier paragraph (804 to 66) was rerun by qa-reviewer at this review: 66 matches in 36 files. Wave Objective: establishes; no tool name, record label, key, code or path changes. Not evidenced: an installing upgrade from a packaged archive, any real distribution profile, a Windows run.

**Changes delivered:**

- **Rename the lifecycle prompts, phrases and skills from "change" to "spec"** (`23mqu-change spec-lifecycle-names`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10 and AC-11 completed. Key decisions: Operator: "spec" is the real name of the planning document; the durable documents are "behavior contracts"; records keep `Change Status:` and `## Changes`; Rename all five prompts by rule, keeping the earlier phrases as aliases.
- **Reword live text: the planning document is a "spec", the durable documents are "behavior contracts"** (`23myn-change spec-and-behavior-contract-terminology`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9 and AC-10 completed. Key decisions: Reword every live occurrence in one change; Find the durable-document uses of "spec" by classifying occurrences, not by pattern.

## Watchpoints

- Watchpoint: implement `23mqu` first; `23myn` edits the same seeds, the framework README, the agent guide and the prompt index, and uses the names `23mqu` introduces.
- Both changes edit seeds and framework scripts and need `seed_edit_allowed` as well as `framework_edit_allowed`.
- Prove the prompt migration on a scratch copy, under the default profile, the `prompt-names` fixture profile and a profile that reuses an earlier default slug, before the renderer edit lands in this tree.
- Measure the review-policy effect of rewording a carrier on a scratch copy before editing any carrier; a moved digest lapses readiness approvals.
- Description and message edits change the handler digests pinned in `tests/fixtures/register-surface-handler-digests.json`.
- The operator directed that this wave be paused, not closed, after delivery review. Close and commit remain operator-owned.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CR-DEL-1 | do_now | no | completed | code-reviewer |
| INTENT-DEL-1 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair (local account: coryhacking) | none |
| council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair (local account: coryhacking) | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Review Checkpoints

- 2026-11-16, Prepare wave, red-team primer (depth standard): three blocking and five non-blocking plan findings, all repaired in the plans before any lane reviewed them. The main one: the planned fixed-pair prompt migration ignores the profile and would move a distribution's prompt that reuses an earlier default slug; the plan now uses the profile-aware migration. Primer and repairs: `.wavefoundry/work/23lxd/red-team-primer.md`.
- 2026-11-16, Prepare wave, first full readiness review: `code-reviewer` returned one blocking finding (CR-1: the Close entry repair would leave two `close-spec` manifest entries, which docs lint rejects) and six non-blocking; `docs-contract-reviewer` returned six non-blocking. One bounded repair pass applied all of them to the plans: the applied-name rule now covers the Close entry repair and the server lookup, the install template keeps its file name, the slug exclusion is narrowed to applied slugs, earlier skill folders are removed unless a registry or declared skill uses the name, seed 230 and the live seed 160 instructions are in the reworded set, and the pattern covers "Change Doc". One focused verification round follows.
- 2026-11-17, Review wave, initial delivery review by three independent seats (`code-reviewer`, `docs-contract-reviewer` as lane and rotating seat, `red-team`). One blocking finding, recorded as typed finding `CR-DEL-1` with a repair start before the repair: the rewording changed the frozen journal-scaffold oracle `upgrade_extensions._pristine_journal_template`, so an upgrade would stop recognising empty journals written by the earlier framework. Non-blocking findings, repaired in the same pass and not recorded as typed findings:
  - `CR-DEL-2`: the previously-shipped Guru description table missed a profile that renamed other lifecycle prompts but kept the earlier plan shortcut. Added.
  - `CR-DEL-3`: no test pinned that a declared skill may take only an earlier default name, not the current one. Added.
  - `DC-DEL-1`: the self-hosted upgrade prompt lagged seed 160. Synced.
  - `DC-DEL-2`: seed 001 said "a spec is one scoped change". Corrected to the change.
  - `DC-DEL-3`: two planning-document phrases split across a line break were missed by the line-based census (an install template and seed 170). Reworded; a multi-line search found no others.
  - `DC-DEL-4`: the mapping-table evidence did not say what OpenSpec worksets and stores are. Added; the table cell is unchanged.
  - `DC-DEL-5`: recorded-history exceptions beyond Requirement 4's list, judged acceptable and already disclosed in the Progress Log.
  - `RT-DEL-1`: an upgraded repository keeps inline-code mentions of the two renamed seed files, which lint does not check and no instruction named. Seed 160, its self-hosted copy and the changelog now name both files and say to search for them.
  - `RT-DEL-2`: the `seed_get` tool description's example slug no longer named a seed. Corrected and its digest pin refreshed.
- 2026-11-17, Review wave, focused verification after the repair pass: `docs-contract-reviewer` approved (five findings resolved, none new); `code-reviewer` reverified `CR-DEL-1` (its journal probe now reports the earlier pristine journal as deleted, and the new pin test fails when the line is reworded in a scratch copy), confirmed `CR-DEL-2` and `CR-DEL-3`, and its sweep of the non-test script diff found no other reworded oracle; `red-team` confirmed `RT-DEL-1` and `RT-DEL-2` and found one further non-blocking defect, `RT-DEL-3`: `lifecycle_baseline_drift` resolved the Close baseline at the profile's name instead of its applied name, so on the upgrade that renames it a pristine earlier-named Close prompt was dropped from that advisory report. Repaired: the report now resolves lifecycle baselines through the same applied-name rule as the other four readers, with a test that fails when the lookup is disabled. `code-reviewer` confirmed that repair and found `CR-DEL-4`, non-blocking, a regression the repair itself introduced: a manifest symlinked outside the repository made the refused read escape, so the whole drift report came back unknown. Repaired with the one-line change the reviewer named and a test; the reviewer confirmed it and approved the scripts area. The red-team seat did not re-verify the `RT-DEL-3` repair. Final full suite after the last framework edit: 12,865 tests, OK.
- 2026-11-17, Review wave, council delivery verdict: PASS, recorded as the typed `council-delivery` approval with intent fit `partially`. The council-chair, independent of planning, implementation and repair, verified for itself that the journal oracle is byte-identical to the committed one, that the test receipt matches the tree, and that two mutations of the `RT-DEL-3` and `CR-DEL-4` repairs fail their tests; that mutation check is the re-verification of the `RT-DEL-3` repair, which the red-team seat that found it did not perform. The chair found no sixth reader of applied prompt names. Its four non-blocking record findings were repaired the same day: both Change Status lines now read `implemented`; the after census and exceptions list were refreshed after the review repairs; the reworded phrase in `docs/architecture/testing-architecture.md` was confirmed against `test_checkout_spec_is_not_a_hook_contract_input`, which guards a read of `docs/specs/mcp-tool-surface.md`; and the intent outcome follows.
- Intent outcome (2026-11-17, drafted by the coordinator from the council verdict; independent intent check: `docs-contract-reviewer`, which confirmed 23mqu AC-7 and 23myn AC-1 and AC-3 against the tree, and the council-chair). `23mqu`: establishes. Evidenced: the five prompts, their phrases and two skills carry the spec names with the earlier phrases as aliases; an installed repository's prompts move byte-identical on render, including project-authored content, shown on a reconstruction of this repository's pre-wave tree; a distribution's own names are kept. Intended and not yet readable: that an engineer arriving from another spec-driven tool recognises the framework on its first screen. `23myn`: partially. Evidenced under the default profile: the planning-document census fell from 804 matches to 66, all logged exceptions, and an independent sample of about 450 remaining uses of "spec" found none that still means a durable document. The gap, typed as finding `INTENT-DEL-1` and open for the operator: under a distribution profile that renames the item noun, rendered prose says a literal "spec" beside the profile's own noun, which is two names for the planning document in that distribution. Wave Objective: establishes, with limits: the migration is evidenced at the render boundary, not through an installing upgrade from a packaged archive, and no real distribution profile was rendered.
- Executed by the delivery seats, beyond the implementers' tests: an end-to-end upgrade render on a reconstruction of this repository's pre-wave docs and host surfaces with the new framework on top, including a project-authored addition inside a moved prompt (preserved byte-identical), a distribution profile with only the Close prompt renamed, an older install with no Close prompt, a missing manifest, a manifest with CRLF line endings registering three of the five earlier prompts, and an interrupted migration that converged on rerun; seven mutations of the migration code, six of which failed tests and one of which is equivalent under the default profile. Not executed by anyone: an installing upgrade from a packaged archive under old code (traced: the render and the docs gate run as child processes on the extracted scripts), and any real distribution profile.
- 2026-11-17, reopened on operator instruction ("Let's reopen the wave and update it with the new revisions") after the follow-on wave `23lxe` was backed out and its folder deleted. The operator's design decision, in the operator's words: "spec is the superficial name, but underneath it's still really a change"; a downstream distribution that renamed its tiers had left `change_id` alone. Revisions made under `23myn-change spec-and-behavior-contract-terminology`: seed 001 and the project overview now say that tools, record labels and identifiers are named for the change they track; the changelog states that literal "spec" under every profile is intended, because the profile's item noun names the unit of work and "spec" names its document. (That changelog statement was later corrected; see the bullets below.) Coordinator's reading at that point, since withdrawn: that this settles `INTENT-DEL-1` as intended (see the next bullet). A read-only investigation behind it: before this wave only ten composed strings followed the profile's item noun ("ticket doc") and about 200 lines said a literal "change doc" under every profile, so a distribution used to read two names for the planning document and now reads one. At that point the spec bodies had not been edited; the operator then accepted a re-prepare and both bodies were corrected (next bullet).
- 2026-11-17, re-prepare accepted by the operator ("I accept the re-prepare, let's make it correct and go through the re-review"). Both spec bodies and this record's summary were corrected: no second wave, tools and records keep "change". Receipt `review-policy-622755d9546c3a567cbe`. Readiness review of that amended plan: `code-reviewer` and `docs-contract-reviewer` each approved and recorded their own approval; a red-team seat (primer, no ledger record) returned one blocking challenge. The challenge: the operator had already answered `INTENT-DEL-1` ("it should follow the profile's noun"), the only repository record of that answer was a draft plan (`23kyb-enh planning-document-noun-follows-profile`) that was removed with the second wave's files, and the coordinator had then written the opposite reading into `23myn` Requirement 10, AC-9 and the changelog. Executed by the red-team seat under the `second` profile: at the last commit the skill text read "consolidated wave doc" and "Review a wave doc"; this tree read "consolidated spec" and "Review a spec", so a distribution had lost the one place it could rename the planning document. The coordinator put the question to the operator again, who answered: "I think it should still follow the profile's noun." Requirement 10, AC-9, AC-10, the tasks and the Decision Log of `23myn` now say so, and Requirement 11 takes the red-team and docs notes (three sentences that still called the document a change; the label named is the default). These edits rotate the receipt again, so the two lane approvals above are not current and are recorded again after the plan settles. The code under Requirement 10 is not written yet.
- 2026-11-17, operator, on the coordinator's question about scope: "'follow the profile's noun' and add a small addition for any additional ones that should be adjusted now"; "Downstream can change seeds if needed, so I think it's ok to leave them out"; and the vocabulary is confirmed ("spec" is the document, "change" is the unit of work, both supported). Result: `23myn` Requirement 10 lists eleven strings, the eleventh being the council skill's Boundary line; seeds and other literal prose stay literal. Receipt `review-policy-592e92041b0392ffab15`; `qa-reviewer` became a required lane because the plan now names test files.
- 2026-11-17, Prepare wave, readiness review of that plan: `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` (also the rotating seat) each approved and recorded their own approval, with no blocking finding. Executed by lanes on scratch copies: the last commit and this tree under the `second` profile and under a patched Ticket and Batch profile, showing the item-noun forms at the last commit and the literal word now at every one of the ten sites. Their implementation notes are in the `23myn` Progress Log. The red-team seat's primer was written against the previous receipt; its blocking challenge was answered by the operator's decision above and no new primer was run for this receipt. The code under Requirement 10 is not written yet.
- 2026-11-17, Prepare wave, council-chair (independent, fresh context): `council-readiness` PASS, intent fit `partially`, recorded as the typed approval `ev-approval-council-readiness-2`. Seats: docs-contract-reviewer (rotating) on this receipt; the red-team primer was run on the previous receipt and not rerun, so no adversarial seat reviewed the eleven-string design itself. The chair replayed the red-team challenge by execution and prototyped Requirement 10 in a scratch copy. Wave readied on receipt `review-policy-592e92041b0392ffab15`.
- 2026-11-17, Implement wave, `23myn` Requirements 10 and 11: implemented by a delegated implementer and checked against the tree by the coordinator. Full suite `python3 .wavefoundry/framework/scripts/run_tests.py --no-cache`: "Ran 12873 tests across 250 files in 600.730s", "OK" (an earlier run failed four files on a full disk and passed on rerun). The review tool at this point listed only `qa-reviewer` and the operator as pending for delivery: the delivery approvals of `code-reviewer`, `docs-contract-reviewer` and `council-delivery` recorded before the reopen still project as current, because delivery approvals are not bound to the receipt. They predate this code, so all three lanes and the council review delivery again.
- 2026-11-17, Review wave after the amendment: `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` each approved with no blocking finding and recorded a fresh delivery approval. Details and three notes are in the `23myn` Progress Log. After the approvals the coordinator changed one line of a test (a dictionary key written as one literal); the lanes did not review that line. Final full suite after it: "Ran 12873 tests across 250 files in 615.424s", "OK". Not executed by any lane: a Windows run, a packaged install or upgrade, a real distribution profile.
- Intent outcome: 2026-11-17: after the reopen; supersedes the earlier Intent outcome paragraph above. Drafted by the coordinator, an interested party, from the lanes' reports; the independent intent checks are qa-reviewer's read, recorded in its delivery approval, and the council-chair's verdict, which follows. `23mqu`: establishes, unchanged. `23myn`: under the default profile, establishes: one name for each document, with the vocabulary stating that tools, record labels and identifiers are named for the change. Under a profile that renames the item, partially: the eleven composed strings (ten composed strings and the council skill's Boundary line) follow the profile's item noun, and literal prose (seeds, install templates, tool descriptions, lint and gate messages) says "spec". That is the scope the operator chose ("I think it should still follow the profile's noun"; "Downstream can change seeds if needed"). The gap typed as `INTENT-DEL-1` is addressed by that decision and its implementation, not by the coordinator's earlier reading, which was withdrawn. The census behind the earlier paragraph (804 to 66) was rerun by qa-reviewer at this review: 66 matches in 36 files. Wave Objective: establishes; no tool name, record label, key, code or path changes. Not evidenced: an installing upgrade from a packaged archive, any real distribution profile, a Windows run.
- 2026-11-17, Review wave, council delivery verdict after the amendment: PASS, recorded by an independent `council-chair` context as the typed `council-delivery` approval `ev-approval-council-delivery-2` with intent fit `partially` (the reason is in the Intent outcome entry above: under a renamed item the composed strings use the profile's noun and literal prose says "spec", the operator's chosen scope). Council roster for this pass: the chair with `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer`; no red-team delivery primer and no rotating fifth seat, so no adversarial seat reviewed the delivered eleven-string design. The chair reverified `INTENT-DEL-1` with its own probe under the default, `second`, Ticket and Batch, and "an item" profiles, with a known-bad control; the finding's repair is completed. Chair's record notes: the late `repair_start` is labelled actor `implementer` although the coordinator composed it; there is no snapshot of the test file from the time of the lane approvals, so that the coordinator's post-approval edit is only the one key rests on the current line and the disclosure. Both findings (`CR-DEL-1`, `INTENT-DEL-1`) are completed. `operator-signoff` is not recorded. Not executed by anyone: a Windows run, an installing upgrade from a packaged archive, a real distribution profile.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 37 | 89,632 |
| implement | 100 | 93,497 |
| review | 99 | 1,401,625 |
| **Total** | **236** | **1,584,754** |

<!-- wave:context-efficiency-state {"generation":218,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":100,"content_source_credit":112182,"derived_artifact_credit":0,"direct_net":93497,"estimated_tokens_saved":93497,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4347,"response_debit":20813,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6475},"plan":{"calls":37,"content_source_credit":119850,"derived_artifact_credit":5107,"direct_net":89632,"estimated_tokens_saved":89632,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3027,"response_debit":41870,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9572},"review":{"calls":99,"content_source_credit":1636586,"derived_artifact_credit":7310,"direct_net":1401625,"estimated_tokens_saved":1401625,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":31697,"response_debit":214343,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3769}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":236,"content_source_credit":1868618,"derived_artifact_credit":12417,"direct_net":1584754,"estimated_tokens_saved":1584754,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39071,"response_debit":277026,"source_credit_count":110,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19816},"wave_id":"23lxd spec-names-and-terminology"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 6 | 0 | 4 | 472,977 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":472977,"surfaced_events":6} -->
<!-- wave:exploration-avoided end -->
