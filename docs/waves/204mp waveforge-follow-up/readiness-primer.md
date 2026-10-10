# Waveforge follow-up readiness primer

Owner: Engineering
Status: draft
Last verified: 2026-10-08

Wave: `204mp waveforge-follow-up`
Phase: readiness
Role: isolated red-team primer; no specialist approval or wave verdict
Context: `204mp-public-primer-20261008`

## Review boundary

Mode: council-adversarial-primer. This independent read covers the four admitted plans, the readiness briefing, the red-team role, and seeds 209 and 215. Live MCP `code_read` and `code_keyword` were discovered and successfully called before source investigation. Source reads supplied the mechanism evidence; changed setup inputs and runtime staleness prohibit treating indexed retrieval as a freshness proof. No implementation files or typed evidence were edited.

Depth recommendation: full. Seed 215 assigns full depth to trust-boundary, architectural or cross-cutting changes. Actor compatibility affects approval identity, the renderer writes customized project documentation, and extracted-pack callbacks execute during upgrade. This primer therefore applies all five stances and supplies three questions. The coordinator must align the settled receipt and actual roster; this recommendation does not itself publish a receipt.

## Strongest challenge

The version-independent journal trigger can fulfill its version contract and still fail its purpose if presence is checked only in the destination to which the hook must relocate journals. Current `upgrade_extensions._JOURNALS_REL`, `migrate_journals` and `_migrate_journals_on_path` discover the canonical `docs/agents/journals` directory; the declaration loader does not supply alternative source roots. Thus “journals_present” is incomplete until the source-location decision identifies which pre-relocation files qualify. Moving the version condition alone cannot answer that question.

Evidence: live reads of `upgrade_extensions.pre_docs_gate` show both declaration loading and callback invocation inside the pre-1.15 gate. The executed preview control below demonstrates canonical-only discovery. Inference: using that discovery unchanged for a different source location would suppress the callback. The operator's actual Waveforge location remains unverified; this report does not presume it equals the alternate scratch location.

Confidence: high for current mechanisms and the unresolved contract; unverified for Waveforge's source layout.

## Best alternative

Keep the selected empty-default-compatible trigger, but settle its presence predicate before readiness. If Waveforge uses canonical direct Markdown entries, reuse that narrow discovery and document it explicitly. If it has a different source location, define the smallest explicitly supported pre-relocation source set and its containment rules from the operator's answer. Evaluate that predicate before callback invocation, retain the existing pre_docs_gate boundary, invoke once per attempt, and leave built-in migration gated independently. Use the same statically readable trigger information to explain preview eligibility without importing the declaration or callback.

This improves the selected design because it makes eligibility testable at the actual input boundary and avoids pretending version independence provides location independence. The cost is one explicit scope decision and corresponding positive/negative fixture cells. A recursive repository scan would add uncertain ownership and false positives; an unconditional callback would violate AC-1's no-journals/no-invocation contract and run arbitrary distribution work needlessly. Neither is a stronger substitute.

Consequence of the current unresolved path: the implementer must invent scope or deliver a callback that never runs on the files it was introduced to relocate. Recommendation: hold wave-wide readiness until the source decision is recorded, then verify the exact presence/failure/preview cells. Continue reviewing settled C1–C5 and the other C6 contracts now.

## Thinking stances applied

- Adversarial: an extra actor alias must not become a second repair identity or an operator identity. `review_evidence._reverification_independence_defect` already canonicalizes repair-start and reviewer actors before comparison; the new merged set must reach that same function through the registered review path. Keep unknown actors unknown and reject collisions against actual project reviewer/operator identities, rather than only a small shipped-name list.
- Constructive: the C3 frozen historical encoder is stronger than deriving expected hashes from current production normalization. Keep its fixed payload and golden checks independently reviewable; a renamed profile changes the fixture's spellings, not the meaning of the oracle.
- Simplicity: C5 should change destination spans only. Retain unsupported syntax with a diagnostic rather than introducing a general Markdown rewriter or weakening docs-lint. The current role rename pairs are a narrow authoritative mapping.
- First-principles: a migration has separate eligibility, ownership and completion facts. For C5, old-absent/new-present is a retry state only when the destination is a safe regular project file. For C6, version eligibility, journal presence, hook success and built-in migration eligibility must remain separate predicates.
- Analogical: treat C1's ownership inventory like a distribution bill of materials and C5's link repair like a resumable migration. A bill of materials must include zero-hit owned files; a resumable migration must inspect current destinations and remaining references rather than using only writes performed in this invocation.

## Primer questions for subsequent seats

1. Which exact pre-relocation journal location and file predicate does the operator authorize, and can the same decision distinguish absent journals, unsupported paths, preview uncertainty and a real callback failure while preserving the legacy default? Answer the pending scope decision explicitly before a wave-wide readiness approval.
2. How will C4 reject collisions with project-declared non-council roles and operator identity, and which registered review/replay/repair paths prove that two council spellings remain one actor? Explain why the built-in policy digest moderator spelling stays independent of the expanded recognition set.
3. What current-state evidence permits C5 to repair links after old-absent/new-present, and how will exact destination edits preserve reference definitions, code examples, historical roots and custom modes on a failed attempt followed by retry? State how the upstream ownership inventory update is checked so new zero-hit framework files cannot silently escape C1's census.

## Source-grounded observations

| Request | Observed mechanism | Review implication |
| --- | --- | --- |
| C1 | `LiteralReconcileKeyTests._expected` calls prompt_slug with an assembled key. `actor_token_census` enumerates all qualifying text files under the framework, including added downstream tests. | Literal keys and explicit ownership repair the reported oracle defects; do not remove negative controls or exclude all framework tests. |
| C2 | `test_hook_contract_documents_the_1_15_0_limit` includes the checkout's project spec when present. | Replace the spec-dependent oracle with shipped controlled input; C6 must later update the legacy-default contract deliberately. |
| C3 | `DigestInputTests.PINNED_OLD_INPUT` contains literal old names and compares their computed digest to the upstream golden. The prompt profile still borrows implement-change and close-change slugs. | Preserve an independent historical encoder and a synthetic slug-chain case; replacing every example with unique destinations alone would lose chain coverage. |
| C4 | The fixed legacy actor tuple feeds recognition, canonicalization, replay spellings and server write conversion; the repair-independence check canonicalizes both actors. | Wire the merged aliases into existing consumers, then exercise public identity boundaries and a real reload. Source inspection establishes feasibility, not delivered behavior. |
| C5 | `migrate_council_role_renames` builds its link report from old paths written during this invocation. `_moved_prompt_link_report` reports simple inline links, including historical records, and never repairs them. | The planned retry, syntax and history boundary need new evidence. Reusing the reporter's scanned file set or regex unchanged would not satisfy the plan. |
| C6 | `pre_docs_gate` holds extracted scripts on sys.path for declaration load and hook call; preview uses static AST literal reading. | Keep these boundary guarantees while changing scheduling. No callback execution or declaration import belongs in preview. |

## Executed readiness-safe control

Probe: `public-primer-journal-presence-boundary`. One fresh Python process, with `.wavefoundry/framework/scripts` on PYTHONPATH and `python3 -B`, imported `upgrade_extensions` and used a TemporaryDirectory. It called the existing public `migrate_journals(root, apply=False, templates=())` helper twice. No hook or declaration module was executed. Explicit empty templates avoid changing the test into a declaration-loading claim.

Expected: an alternate-only directory does not appear in current discovery; adding an identical canonical direct Markdown entry makes that entry appear in `left`; preview preserves both byte sequences.

Observed: with only `docs/history/journals/manual.md`, the report was exactly `{'deleted': [], 'moved': [], 'left': [], 'warnings': []}`. After adding identical `# Manual historical notes` bytes at `docs/agents/journals/manual.md`, `left` was exactly `['docs/agents/journals/manual.md']`; the other report arrays remained empty. Both files retained identical original bytes. Explicit assertions passed with no skip.

Known-bad detection: the alternate-only case refutes an assumption that current journal discovery covers arbitrary pre-relocation locations. The canonical case is the legitimate adjacent control preventing an empty-report result from being attributed to an inert probe. This is readiness-safe-control evidence of the current helper boundary; it is not an executed upgrade scheduling, static-preview or new-trigger AC claim. No mutation or full suite was needed.

Reproduction: create those two scratch paths in the stated order and call `migrate_journals` with `apply=False, templates=()` after each creation; compare the returned dictionaries and original file bytes. All state is temporary, no network or external write occurs, and the parent explicitly authorized bounded scratch readiness controls. Universal claim: false; only these two cases and inspected mechanisms were checked.

## Finding boundary

The actionable readiness issue is the already-pending C6 source-location decision. It is substantive because it determines whether AC-1 is implementable, and it must remain a readiness blocker until settled. The other challenges above are verification questions and implementation notes against requirements already present, rather than independently demonstrated plan defects. No additional blocker is asserted, no required specialist lane is waived, and no typed approval is supplied. Product behavior remains unimplemented.

## Closing reconciliation after the canonical C6 split

Closing context: the same independent red-team reviewer returns for the explicitly requested closing pass. This reviewer authored neither admitted plans nor implementation. Receipt reviewed: `review-policy-5de6f84316a3a4bf9e13`, limited to 204ml, 204mm and 204mn (C1–C5). The original four-change primer above is historical; its substantive C6 challenge is retained, not withdrawn.

Closing judgment: the provisional **PASS for C1–C5 readiness holds**, with no additional blocking candidate. A separate independent chair must issue the actual council judgment; this report supplies no typed approval and does not activate the wave.

Scope reconciliation was checked against current files, not only the coordinator's statement. Wave 204mp now admits three change IDs. Wave `206is journal-hook-follow-up` admits the original `204mo-enh version-independent-journal-hook` ID. That document retains all five requirements, four required ACs, the unresolved source-location task and risk, preview restrictions, legacy default, pre_docs_gate boundary and older-runner loading requirement. Its new decision-log row records the transfer. It remains planned with no readiness approval. The source-location issue therefore remains actionable for 206is and is outside this receipt; this is preserved work, not a waiver or a completed request.

The strongest argument against PASS is that splitting can cosmetically remove a blocker while dependencies still require the unresolved behavior. It does not change the conclusion here: C1–C5 do not introduce the journal trigger or require the new presence predicate. C2 replaces a checkout-dependent test oracle with controlled shipped input under the existing hook contract. C6 can subsequently change that contract under its own readiness and delivery evidence. The destination/link and actor changes have separate named contracts and independent implementation paths. This conclusion does not authorize assuming journal locations later.

The specialist report's five lane judgments are explicitly five dimensions from one context, not five independent corroborations. That disclosure preserves their meaning. Its six control groups cover existing producer compatibility, repair identity, runtime role scope, migration retry/collision, census leakage, independent digest feasibility and strict upgrade-gate refusal. Their limits are explicit: renamed fixtures, new aliases, runtime collision enforcement, actual reload and complete link repair still require delivery proof. Those limits do not falsify readiness because the corresponding behaviors remain unchecked product ACs rather than asserted completed behavior.

Independent closing replay: the four `LifecycleCompatibilityTests` named in specialist E1 were rerun through the existing `wf_review_event_response` fixture boundary in a fresh `python3 -B` process with scripts and tests on PYTHONPATH. All four passed in 1.000 seconds, zero skips: old actor and key converted on canonical writes, historical approval replay remained compatible, and changed replay evidence was rejected. This corroborates only that bounded existing seam; it does not duplicate or independently attest to the specialist's other five executed groups or to unimplemented extra aliases. No shared live-server reload, source edit, network call or full suite ran.

| Candidate or challenge | Closing disposition | Evidence and limit |
| --- | --- | --- |
| C6 pre-relocation presence scope | Retained outside current receipt in planned 206is | Original ID, requirements, required ACs and pending risk remain present; not resolved or waived. |
| C4 configured-role collisions and equivalent repair actors | Implementation verification note; no new blocker | Requirements expressly retain these guards; specialist E2 demonstrates current dynamic lane scope and existing actor equivalence. Delivery must exercise declared aliases at runtime. |
| C5 retry discovery and exact destination preservation | Implementation verification note; no new blocker | Requirements demand current-state retry and syntax/history/mode preservation; specialist E3 demonstrates the real baseline retry defect and collision preservation. New repair is not claimed. |
| C1 inventory completeness and C3 oracle independence | Implementation verification note; no new blocker | The selected inventory includes zero-hit owned files; maintenance check and omitted-file control remain required. The historical encoder uses explicit fields and goldens, rather than production normalization. |

The table is reconciliation prose, not a second typed actionability record or newly sealed candidate universe. For the current C1–C5 readiness candidate set, the reported empty synthesis is coherent: no concrete plan contradiction, unresolved build-changing decision or falsely completed product claim was evidenced. The known baseline defects motivate the planned changes and are not delivery failures before implementation.

Actual full-depth primer coverage remains documented independently of the generated metadata's standard value. Five stances and three questions were applied; trust-boundary/cross-cutting rubric remains seed 215. This mismatch must continue to be disclosed in chair synthesis and must not be represented as a source-fixed metadata field. No additional review round or scope expansion is recommended.
