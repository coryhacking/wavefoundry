# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-11-18
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `23qo9 gardener-batched-head-read`
Title: Gardener Batched Head Read

## Objective

Prepare, Close, upgrade and package builds on a repository with many edited documents get the same `Last verified` stamping decisions in a fraction of the time: the docs gardener reads the committed versions of its candidate documents with one Git call in place of one per document. Which documents are stamped does not change, and a Git failure still never suppresses a stamp. A second change ships a Rust practices baseline with the framework: a menu of practices, each with a setting, a check that can fail and its sources, and a project-owned record of what each Rust project adopted; the framework enables nothing by itself. A third change states that an agent's files for a wave belong inside that wave's work folder and reports files left loose in the work root.

## Changes

Change ID: `23qo8-enh gardener-batched-head-read`
Change Status: `implemented`

Change ID: `23rzs-enh rust-practices-baseline`
Change Status: `implemented`

Change ID: `23rzt-enh work-root-loose-files`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-11-19

## Wave Summary

Wave `23qo9` (Gardener Batched Head Read) delivered 3 changes: Read the committed versions of changed documents in one Git call, Ship a Rust practices baseline with the framework, and Keep wave scratch inside the wave's work folder and report loose files in the work root.

Intent outcome: Achieved for the three admitted changes on the tested macOS host. QA independently ran 180 focused tests. The gardener preserves tested stamp decisions with one Git process per nonempty batch and none for an empty batch. The recorded 167-document comparison took 0.044 seconds for the batch versus 2.82 seconds for individual reads. A malformed size leaves the verified prefix usable and causes unread documents to be stamped. Audit and close report loose files and links without acting on them. The framework ships 54 Rust practices with project-owned adoption. Rust 1.100 and Clippy probes distinguished compiler warnings from manual review and runtime tests, including explicit guard discard and arbitrary lint-exception reasons. Downstream adoption, long-term work-folder cleanliness and native Windows or WSL2 behavior remain unmeasured.

**Changes delivered:**

- **Read the committed versions of changed documents in one Git call** (`23qo8-enh gardener-batched-head-read`) — AC-1, AC-2, AC-3, AC-4 and AC-5 completed. Key decisions: Do this follow-up. Operator's instruction, quoted: "plan the batched git read in a new wave"; One `git cat-file --batch` call for the run's candidates. Planner's choice, not separately confirmed by the operator.
- **Ship a Rust practices baseline with the framework** (`23rzs-enh rust-practices-baseline`) — AC-1, AC-2, AC-3, AC-4, AC-5, AC-6 and AC-7 completed. Key decisions: Ship a Rust practices baseline with the framework and consider the Google and Microsoft guidance. Operator's instruction, quoted: "plan the framework-shipped Rust practices baseline as a spec; google and microsoft also recently announced best practices that I'd like to consider as part of this."; Selected approach: a framework-shipped menu document read in place, plus a project-owned decision record that an agent offers to draft; seeds point builders and reviewers at the record. Planner's choice, not separately confirmed by the operator.
- **Keep wave scratch inside the wave's work folder and report loose files in the work root** (`23rzt-enh work-root-loose-files`) — AC-1, AC-2, AC-3, AC-4, AC-5 and AC-6 completed. Key decisions: Make the rule standing for every project, in the open wave. Operator's words: "You should be working in the wave work folder not direclty in work" and "put this in the open wave."; Selected approach: state the rule in the guidance and report loose files as an advisory in audit and close. Planner's choice, presented to the operator before planning and not objected to.

## Watchpoints

- Operator instruction, quoted: "plan the batched git read in a new wave". It authorizes planning and admission only; Prepare, implementation, close and commit are not authorized by it.
- Operator instructions for the second change, quoted: "plan the framework-shipped Rust practices baseline as a spec; google and microsoft also recently announced best practices that I'd like to consider as part of this." and "prepare and review this with our wave." Earlier, on this wave: "prepare and review the wave until the other wave is closed". Implementation, close and commit are not authorized by these.
- Operator instruction to implement, quoted, 2026-11-18: "wave 23r7u is being closed. watch it and implmenet this wave once it's complete." Wave `23r7u` was closed when checked, and this wave was opened. Close and commit are not authorized by it.
- Third change `23rzt`, admitted while the wave was open on the operator's direction, quoted: "put this in the open wave." and "then prepare, review, and implement it." Watchpoint: its report is advisory and read-only; no loose file is deleted or moved by any tool, and no write to the work root is refused.
- Watchpoint for `23rzs`: no lint is enabled and no configuration file is installed by the framework (the rule from closed wave `237ee`); an existing project record is never rewritten; shipped text carries no internal identifiers or reviewed-repository names; four operator decisions are open in the spec's Decision Log and are built as planned unless the operator decides otherwise.
- Watchpoint: the stamping decisions must stay identical; a failure of the batched read counts as differing. Windows is enterprise-critical: the comparison keeps its CRLF normalization.
- The working tree is uncommitted and holds closed waves `23lxd`, `23p89`, `23q0t`, `23p9u` and another session's work.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DELIV-QO8-SIZE-CONVERSION | do_now | no | completed | code-reviewer, qa-reviewer |
| DELIV-QO8-TRUNCATED-AT-BOUNDARY | do_now | no | completed | — |
| DELIV-RZS-ADOPT-SCOPE | do_now | no | completed | — |
| DELIV-RZS-CHECK-OVERSTATED | do_now | no | completed | — |
| DELIV-RZS-INHERIT-CONFLICT | do_now | no | completed | — |
| DELIV-RZT-HELPER-CENSUS | do_now | no | completed | qa-reviewer |
| DELIV-RZT-READY-VACUOUS | do_now | no | completed | — |
| READY-RZS-AC4-PRODUCER | do_now | no | completed | — |
| READY-RZS-AC4-RENDER-ORACLE | do_now | no | completed | code-reviewer |
| READY-RZS-DOC-1 | do_now | no | completed | — |
| READY-RZS-QA-01 | do_now | no | completed | — |
| READY-RZS-QA-02 | do_now | no | completed | — |
| READY-RZS-STANCE | do_now | no | completed | — |
| READY-RZT-AUTHORITY | do_now | no | completed | — |

*Machine review state — 14 findings; current: do_now 14, maybe_later 0, dont_do_later 0, not_issue 0*
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

- Readiness, 2026-11-18. No blocking finding from any seat. `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved; council PASS, intent fit `establishes` (`ev-approval-council-readiness`; chair `council-chair`; seats `red-team` fixed and `security-reviewer` rotating, neither recorded an event because neither had a finding; the chair noted that only these two seats sat). The reviewers' nine binding implementation notes are in the spec's Progress Log. Readied without opening, because another session's wave was open; implementation waits for that wave to close.
- Readiness after the second spec was admitted, 2026-11-18. `23rzs`: six blocking findings covering three defects (`READY-RZS-QA-01`, `READY-RZS-AC4-RENDER-ORACLE` and `READY-RZS-AC4-PRODUCER`: a criterion required a rendered role document no code produces; `READY-RZS-DOC-1` and `READY-RZS-QA-02`: the entry format had no place for the platform statement a criterion tested; `READY-RZS-STANCE`: no rule decided an entry's default stance). One repair pass amended the spec; fresh contexts of the raising lanes reverified all six; `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved against receipt `review-policy-d851fbb93d6ced9e87cc`. Council PASS, intent fit `partially` (`ev-approval-council-readiness-2`; seats `red-team` fixed and `docs-contract-reviewer` rotating): `23qo8` establishes its intent; for `23rzs` the baseline, the offered record and the seed pointers are specified and testable, and whether builders then work from a drafted record is seen only at later installs. Carried to delivery: the truth of each stance and platform statement is judged by reviewers against the sources, since the tests prove shape only. Four operator decisions in the `23rzs` Decision Log are open; the repair set the panic-family lint stances by rule (`propose` and `situational`, not `adopt`).
- Wave opened 2026-11-18 on the operator's instruction once wave `23r7u` was closed. `23qo8` implemented (focused runs only; the full suite follows the delivery review). Third spec `23rzt` admitted while open: readiness typed one blocking finding, `READY-RZT-AUTHORITY` (`red-team`: the advisory did not say who may act on a loose file, and a file moved into the closing wave's folder is deleted by that close); repaired in one pass and reverified; `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved against receipt `review-policy-ea0e243b44bb436e5976`; council PASS, intent fit `partially` (`ev-approval-council-readiness-3`; seats `red-team` fixed and `docs-contract-reviewer` rotating): `23qo8` and `23rzt` establish their intent, `23rzs` remains partial for the reason above. The chair noted that only two seats sat.
- Implementation, 2026-11-18. Three implementers, one per spec, in sequence; each ran focused test files only. Coordinator records and the implementers' rows are in the specs' Progress Logs. The full framework suite runs after the delivery review.

- Delivery council passed all three changes after the standard red-team primer. Architecture, security, QA and reality-checker reviewed independently. The rotating performance reviewer confirmed per-document Git reads as the comparison for valid replies and injected malformed replies as the separate failure check. The chair verified both close modes preserve an external symlink and its target. A focused reality check settled the initial partial assessment against the delivered scope. Native Windows, WSL2 and downstream Rust adoption remain unmeasured.
- Full qualification first exposed two stale 23rzt test inventories. QA verified all six new helper calls and the single report-only advisory site. The prior expectations failed and the corrected exact checks passed. QA renewed its approval and the chair rechecked both guards before recording council delivery.

- Final default framework qualification passed 13,052 tests across 251 files in 660.113 seconds on macOS, with 12 skips. Both previously failing inventory checks passed.

Intent outcome: Achieved for the three admitted changes on the tested macOS host. QA independently ran 180 focused tests. The gardener preserves tested stamp decisions with one Git process per nonempty batch and none for an empty batch. The recorded 167-document comparison took 0.044 seconds for the batch versus 2.82 seconds for individual reads. A malformed size leaves the verified prefix usable and causes unread documents to be stamped. Audit and close report loose files and links without acting on them. The framework ships 54 Rust practices with project-owned adoption. Rust 1.100 and Clippy probes distinguished compiler warnings from manual review and runtime tests, including explicit guard discard and arbitrary lint-exception reasons. Downstream adoption, long-term work-folder cleanliness and native Windows or WSL2 behavior remain unmeasured.

- Evidence retained at close: `evidence/rzs-entry-sources.md` and `evidence/rzs-source-verification.md` preserve the dated, per-entry source checks for the Rust baseline. The spec Progress Logs and delivery ledger record compiler results, toolchain limits, the timing comparison and failure controls. Temporary build outputs and routine test logs can be removed with the wave work area.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 62 | 274,152 |
| implement | 14 | 412,912 |
| review | 334 | 4,836,680 |
| **Total** | **410** | **5,523,744** |

<!-- wave:context-efficiency-state {"generation":413,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":14,"content_source_credit":417100,"derived_artifact_credit":1272,"direct_net":412912,"estimated_tokens_saved":412912,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":273,"response_debit":7832,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2645},"plan":{"calls":62,"content_source_credit":545996,"derived_artifact_credit":3436,"direct_net":274152,"estimated_tokens_saved":274152,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":29684,"response_debit":255175,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9579},"review":{"calls":334,"content_source_credit":6457757,"derived_artifact_credit":4931,"direct_net":4836680,"estimated_tokens_saved":4836680,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":60021,"response_debit":1572549,"source_credit_count":218,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6562}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":410,"content_source_credit":7420853,"derived_artifact_credit":9639,"direct_net":5523744,"estimated_tokens_saved":5523744,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":89978,"response_debit":1835556,"source_credit_count":289,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":18786},"wave_id":"23qo9 gardener-batched-head-read"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 7 | 0 | 6 | 5,554,763 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":5554763,"surfaced_events":7} -->
<!-- wave:exploration-avoided end -->
