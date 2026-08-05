# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ugk8 upgrade-reporting-and-doc-accuracy`
Title: Upgrade Reporting And Doc Accuracy

## Objective

Close the two remaining items from the 1.15.x field-report stream: make the upgrade's summary schema token observable on runs that deviate through the primary phase (1uf68, so the drift tripwire stops going blind on exactly the runs worth watching), and correct four doc surfaces that tell downstream projects the upgrade configures universal review when it configures targeted (1ug7o).

## Changes

Change ID: `1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs`
Change Status: `implemented`

Change ID: `1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping`
Change Status: `implemented`

## Participants

- Coordinator: session agent (Claude Code)
- Write-owning roles: implementer (fix workstream)
- Requested review lanes: code-reviewer, docs-contract-reviewer, qa
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, qa

Completed At: 2026-08-04

## Wave Summary

Wave `1ugk8` (Upgrade Reporting And Doc Accuracy) delivered two changes: The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate and Four Doc Surfaces Tell Downstream Projects the Upgrade Sets universal Review When It Sets targeted. Notable adjustments during implementation: The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate: Readiness council FAILED the first draft and the findings were folded whole: the call-site citation had drifted to :4984, the actual cleanup carrier is `_print_operator_summary` (never named), `_build_upgrade_summary` is shared with the fallback so mutating it would break three pins and falsify the ADR, a THIRD token-less window exists (`--resume-after-memory`), the pause has two exit paths with the plain `return` the common one, option (a) breaks the `:5019` equality pin (narrow, not delete), failure summaries also gain the token and needed ratification, and the bounder can make a present token read as absent without terminal-key registration. The docs seat added the four-surface required carrier set and the CHANGELOG no-open-section problem.; The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate: Prepare-phase lanes: release APPROVED (class (a) verified by executed AST reachability probe plus both invocation paths; no transition-run disclosure needed; ship path and rollback confirmed). Five lanes withheld and every finding is folded: `_print_operator_summary` is reachable ONLY via `--cleanup` so AC-1 and R6(a)/(b) were unsatisfiable as written and are now two-invocation shapes; the token's semantic is restated as self-witnessing so no producer-identity field is added and ADR `:100`'s Alternatives row is amended instead; R5 misstated the terminal-key set as one key when it holds ten, and the registration is class (c); the R7 census missed `mcp-tool-surface.md:966` and the seed-160 `:49`/`:85` pair with its rendered mirror, so the seed gate is now declared; R6(b) was structurally identical to R6(c) and R6(e) was vacuous without budget pressure; the pre-cleanup refusal exits are censused and ruled out; the `## [Unreleased]` rename step is recorded.; The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate: Mutation check on a byte-copy of the framework tree under the scratchpad (repository files byte-identical afterwards, verified with `cmp`). Mutant 1 (cleanup token assignment removed) was caught by (a), both subTests of (b), and the narrowed `test_primary_and_prose_render_from_same_builder`: 4 failures. Mutant 2 (terminal-key registration removed) was caught by (d) alone: 1 failure, which is the correct blast radius for a server-resident registration. Mutant 3 (token moved INTO the shared builder, the wrong fix) was caught by (c), by the narrowed one-builder pin, and by 9 pre-existing degradation pins including the `:5680` fallback assertions: 11 failures. No survivors.

**Changes delivered:**

- **The Summary Schema Token Is Unobservable on Exactly the Runs That Deviate** (`1uf68-bug summary-schema-token-unobservable-on-non-nominal-runs`) — 6 ACs completed. Key decisions: Cleanup carries the token at the emit site; the paused primary does not emit; Register the token as a terminal key rather than only pinning current bounder behavior
- **Four Doc Surfaces Tell Downstream Projects the Upgrade Sets universal Review When It Sets targeted** (`1ug7o-bug seed-160-misstates-legacy-delivery-mode-mapping`) — 5 ACs completed. Key decisions: Amend `1tsbu-adr:13` inline rather than correcting or deleting its text; Correct the carriers to match the canonical block; do not restate the mapping a third way
## Watchpoints

- Blocking: BOTH changes edit `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` under the `seed_edit_allowed` gate (1uf68 at `:49`/`:85` plus the rendered mirror, 1ug7o at `:518`). 1uf68 runs first; one gate window; 1uf69's `(a no-op migration marks nothing and rewrites no wave)` qualifier stays byte-identical.
- Blocking: `CHANGELOG.md` has no open unreleased section (1.15.2 is released). 1uf68 implements FIRST and creates `## [Unreleased]`; 1ug7o appends. Both declare CHANGELOG as a shared serialization point. The release runner must later rename that heading to `## [<version>] - <date>` because `build_pack` matches `^## \[{version}\]` and hard-fails otherwise.
- Watchpoint: 1uf68's insertion goes in `_print_operator_summary`'s body only. Never `_build_upgrade_summary` (shared with the primary-phase fallback, which must stay token-free) and never the shared `_emit_summary_line` helper. It narrows one existing equality pin rather than deleting it.
- Watchpoint: `_print_operator_summary` is reachable ONLY through `phase_cleanup`, whose sole production caller is `main`'s `--cleanup` branch. The pause and resume runs emit no sentinel in their own process; their token appears at the recovery `--cleanup`. AC-1's pins must drive `main(["--cleanup"])`, not call the emitter directly, or the reachability claim stays unpinned.
- Watchpoint: no new summary field. The token is self-witnessing (only code carrying the emit line can emit it), so ADR 1u49j's Alternatives row at `:100` is amended instead of adding a producer or phase scalar.
- Watchpoint: 1uf68's contract tests EXTEND the existing DelegatedSummaryContractTests family and the `test_server_tools` upgrade-summary tests; no new schema key, no new test module. FOUR red-first cases, not five (the post-resume lock shape is a subTest of the nominal case, exercising no distinct path). The bounded-response pin needs real budget pressure and a red run against a key set without the token, or it is vacuous.
- Watchpoint: 1uf68's emit fix is class (a) (executed-verified: cleanup runs a fresh post-extraction process on both the CLI and MCP paths, so no transition-run disclosure is needed). Its terminal-key registration is class (c) and takes effect only after a host restart.
- Watchpoint: 1ug7o amends `1tsbu-adr:13` inline in the convention at `1p7pb-adr native-windows-distribution-model.md:27` rather than rewriting an accepted decision record. Its census pin lives in `test_events_only_residue_census.py` (not `test_review_policy.py`), keys on THREE claim-shaped patterns rather than the bare word `universal` (a live legal enum measured at 64 legitimate occurrences across 28 in-scope files), adds `docs/references/` to scope, and keeps `docs/architecture/decisions/` excluded.
- Watchpoint: an independent reverifier confirmed every folded finding and landed three more corrections before implementation (a missed `session-handoff.md:20` carrier, the ADR `:100` amendment's missing grounding, and 1ug7o's miscounted sentence ordinal). Both plans were also simplified: 1uf68 dropped to four red-first cases and demoted `layering-rules.md:29` to recommended; 1ug7o dropped one unfireable census pattern and replaced a padded negative-control list with the measured result.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-04: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: both seats FAILED both first drafts on substantive code-grounded defects, all folded in-phase before the receipt mint: for 1uf68 a drifted call-site citation, an unnamed actual cleanup carrier, a shared builder whose mutation would break three pins and falsify the ADR, a third token-less window (`--resume-after-memory`), a mischaracterized pause exit path, a live equality pin that the chosen mechanism breaks and must narrow, unratified failure-path tokens, and a bounder path that makes a present token read as absent; for 1ug7o an incomplete census missing two live carriers including the Tier-1 startup doc and an accepted ADR, plus an AC-3 rationale that was outright false since the seed sentence carries no contract pin; strongest-alternative: emit the token from the paused primary phase instead of cleanup, which the docs seat scored materially cheaper on doc cost and which preserves the token's delegation-provenance meaning; rejected because it runs pre-extraction code and so would be class (b), ineffective on its own installing upgrade, while also falsifying the audited `failed_phase=None` justification and claiming an undetermined index state)

- **Prepare-phase lane review [prepare-lanes] — 2026-08-04: PASS after in-phase repair** (six required lanes run as three independent MCP-first agents; release-reviewer APPROVED outright after verifying the class (a) claim by executed AST reachability probe across both invocation paths plus ship-path and rollback checks; the other five withheld and every finding was folded into the plan bytes before the receipt mint. Substantive corrections: `_print_operator_summary` is reachable only via `--cleanup` so AC-1 and two red-first specs were unsatisfiable as written and are now two-invocation shapes pinned through `main`; the token's semantic was restated as self-witnessing so the reviewer-proposed new flat scalar was rejected in favor of amending ADR 1u49j's Alternatives row at `:100`; the terminal-key set was misdescribed as one key when it holds ten, and its registration is class (c); the doc census missed `mcp-tool-surface.md:966` and the seed-160 `:49`/`:85` pair with its rendered mirror, which pulled the seed gate into 1uf68; one red-first case was structurally identical to another and one was vacuous without budget pressure; the pre-cleanup refusal exits were censused and ruled out on exit-code grounds; and for 1ug7o the census pin's home, scope, and key shape were all corrected along with a citation to a nonexistent ADR filename. Executed evidence: 150-test baseline green across five clusters, defect reproduced with the exact pgt9 signature, key-set equality measured 18 == 18, `migrate_wave_review_policy` re-executed.)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review evidence — 24 records; 2 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| qa | approved | current executed approval follows every affected repair | none |
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
| plan | 93 | 1,106,462 |
| implement | 47 | 2,463,872 |
| review | 47 | 569,967 |
| **Total** | **187** | **4,140,301** |

<!-- wave:context-efficiency-state {"generation":198,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":47,"content_source_credit":2571436,"derived_artifact_credit":803,"direct_net":2463872,"estimated_tokens_saved":2463872,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1731,"response_debit":108067,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":93,"content_source_credit":1331363,"derived_artifact_credit":2797,"direct_net":1106462,"estimated_tokens_saved":1106462,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9298,"response_debit":219716,"source_credit_count":81,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1316},"review":{"calls":47,"content_source_credit":653363,"derived_artifact_credit":2505,"direct_net":569967,"estimated_tokens_saved":569967,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6957,"response_debit":80290,"source_credit_count":26,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":187,"content_source_credit":4556162,"derived_artifact_credit":6105,"direct_net":4140301,"estimated_tokens_saved":4140301,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17986,"response_debit":408073,"source_credit_count":179,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4093},"wave_id":"1ugk8 upgrade-reporting-and-doc-accuracy"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 16 | 0 | 9 | 7,027,190 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":7027190,"surfaced_events":16} -->
<!-- wave:exploration-avoided end -->
