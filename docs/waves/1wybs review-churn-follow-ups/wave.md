# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-08
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1wybs review-churn-follow-ups`
Title: Review Churn Follow Ups

## Objective

Land the three follow-ups wave `1wuju` recorded out of scope, each small and pinned: scaffold guidance so a root-level file or a glob in a Serialization Points bullet never silently drops review lanes in any target repository; a standing-gate policy under which an evaluator-only edit records no close-time baseline and the next ranking wave records its own before-receipt; and six low hardening notes from the `1wuju` code and docs-contract lanes on the verdict-gap and install-audit paths.

## Changes

Change ID: `1wxe6-enh serialization-points-scaffold-guidance`
Change Status: `complete`

Change ID: `1wybq-enh evaluator-edit-baseline-policy`
Change Status: `complete`

Change ID: `1wybr-debt verdict-gap-and-install-audit-hardening`
Change Status: `complete`

## Participants

- Coordinator: coordinator
- Write-owning roles: implementer
- Requested review lanes: docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-09-02

## Wave Summary

Wave `1wybs` (Review Churn Follow Ups) delivered 3 changes: Serialization Points Scaffold Guidance: Root-Level Files and Globs Declare Nothing, Evaluator-Only Edits Record No Close-Time Baseline, and Verdict-Gap and Install-Audit Hardening. Notable adjustments during implementation: Serialization Points Scaffold Guidance: Root-Level Files and Globs Declare Nothing: Implemented. Seed `170` (the `## Serialization Points` bullet, after "declares no target"), seed `040` (the section description, after the wrapped-bullet rule), and seed `160` (the repair instruction, introduced by "State the token grammar too:", and the checklist item as a parenthetical) carry the two-form sentence; the install template gains it after its guidance paragraph, the project template after its "Prepare uses declared paths" paragraph, and the shipped Prepare lifecycle prompt inside readiness check 5, with both fence blocks byte-identical (`test_the_fenced_examples_are_untouched`). `seed_edit_allowed` opened and closed around the seed edits; `wf_sync_surfaces` run (nothing rendered changed: the sentence lives outside renderer-owned regions). Pins: `SerializationPointsTokenGrammarPinTests` in `test_docs_lint.py` (every carrier with an existing-phrase anchor plus four fragments; seed 160 at both sites; fenced examples untouched) and `test_the_documented_token_grammar_matches_both_declaration_forms` in `test_review_policy.py` (bullet form: a root-level or glob token makes the bullet prose, the clean bullet declares both paths; explicit block: a root-level span declares nothing while its sibling declares, a `*.ext` span is returned and recruits no lane). CHANGELOG Added bullet. The existing declares-nothing pins, the corpus census, and the shipped-docs parity pin stay green. Gapfill: the edits are exact-string replacements applied with the shell, and region reads during implementation used shell `sed` over anchors located with MCP `code_keyword`/`code_read` at planning and readiness (docs-only work, per the retrieval posture).; Verdict-Gap and Install-Audit Hardening: Delivery round 1 repair (ARCH-DEL-2 merging CODE-DEL-2; CODE-DEL-3 merging RT-DEL-3, QA-DEL-2; DOCS-DEL-5 merging RT-DEL-2; CODE-DEL-5 merging RT-DEL-4; DOCS-DEL-3 merging QA-DEL-3; DOCS-DEL-4). `_strip_root_forms(text, forms)` now carries the replacement loop and adds each spelling's repr-doubled variant (its doubled separator handled before the single one), so `_strip_repository_root` is unchanged on POSIX and the Windows `%r` case is pinned at string level (`test_the_sanitizer_strips_a_repr_doubled_windows_spelling`). `test_a_long_cause_keeps_its_head_and_tail` asserts the exact cap unchanged, cap+1 truncated to the cap, and, with the temp root straddling the head cut, equality with `_cap_cause_line(_strip_repository_root(line, root))` plus no 20-character fragment of either root spelling (the reversed order leaves `/private/var/folders...` beside the marker). `_install_artifact_display` falls back to `os.path.relpath` over the resolved pair (a `..`-relative path) and to the resolved string only when no common anchor exists; the escaping subtest asserts `../outside/config.json` and no parent-directory segment; the spec sentence and both format copies say relative to the repository root with leading `..` segments. The spec sentence is pinned in `test_audit_install_public_carriers_pin_status_and_pending_lint_matrix`; the shipped format copy's field list is pinned in `test_install_log_format_names_the_checked_but_missing_fields_the_audit_emits`; the CHANGELOG bullet gains the doubled-spelling and `..` clauses and is pinned. Landing rule (scratch `mut16`, controls first): strip and cap order reversed CAUGHT; cap boundary loosened CAUGHT; doubled-variant expansion removed CAUGHT; relpath fallback replaced by the resolved string CAUGHT; both format copies renamed CAUGHT; spec sentence deleted CAUGHT; CHANGELOG lead deleted CAUGHT. `RunValidateTests` + `WaveInstallAuditTests` 34 OK; the real-subprocess leak pin, the every-gate crash pin, and the install-audit advisory pin 4 OK.; Verdict-Gap and Install-Audit Hardening: Landing rule: seven scratch-copy mutants under session scratch `mut15`, each caught on an otherwise green base (controls run first): the sanitizer guard removed (`test_the_sanitizer_ignores_a_filesystem_root_or_relative_spelling`, four subtests fail: `/`, `repo`, `.`, `docs`); the `root` default restored (`test_the_gap_producer_requires_the_root`); the cause cap removed (`test_a_long_cause_keeps_its_head_and_tail`); the `run_validate` synthesis removed (`test_a_lint_crash_reaches_the_install_audit_through_the_real_parser`, both subtests); the prefix bypass removed (the same test, the absence-marker subtest only); the repo-relative render removed and, separately, the tolerant fallback removed (`test_checked_but_missing_artifact_returns_diagnostic`, the second as an error from `ValueError`).

**Changes delivered:**

- **Serialization Points Scaffold Guidance: Root-Level Files and Globs Declare Nothing** (`1wxe6-enh serialization-points-scaffold-guidance`) — 4 ACs completed. Key decisions: Readiness council (both seats): keep the parser untouched in this wave; make the sentence true for both forms and pin the explicit-block phantom as it behaves today; record the `_is_declared_target` tightening (`"*" not in candidate`, one clause shared by both tiers) as the deferred better end state.; One guidance sentence per scaffold surface plus a grammar-parity pin.
- **Evaluator-Only Edits Record No Close-Time Baseline** (`1wybq-enh evaluator-edit-baseline-policy`) — 4 ACs completed. Key decisions: Policy only: the next ranking wave records its own before-receipt and after-receipt, compared as `cross_generation`.
- **Verdict-Gap and Install-Audit Hardening** (`1wybr-debt verdict-gap-and-install-audit-hardening`) — 5 ACs completed. Key decisions: Land all six as one debt change, plus the format-doc field correction the readiness council found.

**Deferred (recorded, not silent).** No AC or task is `[~]`: every acceptance criterion and task across the three changes is `[x]`. Two items are deferred by decision rather than by marker. (1) Tightening `review_policy._is_declared_target` to reject `*` in both declaration forms is the better end state and stays out of this wave: it is an evaluator-version transition (`REVIEW_POLICY_EVALUATOR_VERSION` 7 to 8, the tripwire test, a public v7-to-v8 prepare transition test, the spec line naming the version, and one re-Prepare per readied wave including another session's `1wpig`), and a census over 908 change documents found zero affected today. (2) `docs/prompts/prepare-wave.prompt.md` (self-hosted, project-owned) carries no declaration guidance and is left to a later docs wave (DOCS-RV1-3).

**Key decisions.** The readiness council reversed the plan's explicit-block claim before implementation. Delivery review then established that `1wybr` moved `production_identity` through `server_impl.py`, so this wave owed the receipt its own `1wybq` policy prescribes (ARCH-DEL-1); the after-receipt `docs/reports/retrieval-quality-post-1wybs.json` (run `2691fb86`, `cross_generation` 174 to 211, evaluator unchanged) returned `fail` on five zero-tolerance `code_ask` holdout regressions, dispositioned as corpus drift on a byte-exact reconstruction against the `1wuju` receipt's production digest plus a reachability closure showing no changed symbol is reachable from any retrieval tool, and the policy text now discloses that attribution. The reference receipt moved to `post-1wybs.json` (ARCH-RV1-2). The scaffold sentence was narrowed twice: first to the parser's predicate (CODE-DEL-1), then to name trigger tokens honestly (CODE-RV1-1).

**Review.** Readiness PASS with amendments (two seats). Delivery: nine merged findings in round 1 (one blocking), repaired in one batch and reverified by four fresh lanes; two further findings in cycle 2, repaired and reverified by two fresh lanes; five editorial notes repaired inline. Eleven ledger findings terminal, four required lane approvals plus `wave-council-delivery` and operator signoff. Mutation evidence: 16, 12, 7, 4, and 2 scratch-copy mutants by the implementer and 13, 19, 22, 4, and 4 by the lanes, every landed mechanism failing a named test on deletion. Final tree fingerprint `614d390b129f4f80`, full suite 8,051 OK, docs lint clean, both edit gates closed.

**Docs-contract review:** performed. The `docs-contract-reviewer` lane reviewed both delivery cycles and approved with notes; `docs/specs/mcp-tool-surface.md` changed in this wave and its new `checked_but_missing` sentence is pinned in `test_audit_install_public_carriers_pin_status_and_pending_lint_matrix`.

**Lessons promoted.** `docs/references/project-context-memory.md` gained "Retrieval-Receipt Attribution and Production Identity (wave 1wybs)": whole-module production identity means any `PRODUCTION_RETRIEVAL_MODULES` edit owes a receipt; a `cross_generation` comparison attributes corpus drift to the change, and the reverse-patch digest reproduction plus a reachability closure is the proof pattern that settles attribution; `wf_prepare_wave(mode='ready')` gardens a canonical shipped-doc twin without its shipped copy, so re-sync every pair before the last suite run. `memory_propose` drafted no candidates (no Decision Log entry carried a code anchor and no repaired finding met the durable shape), which the tool reports as sparse by design.

## Watchpoints

- Watchpoint (gates): `seed_edit_allowed` opened and closed around each seed edit in `1wxe6`, then `wf_sync_surfaces`; `framework_edit_allowed` around the script edits in `1wybr`.
- Watchpoint (receipt; corrected by delivery review ARCH-DEL-1): none of the three changes may edit `retrieval_eval.py`; `1wybr`'s lint-parse and install-audit edits live in `server_impl.py`, which the evaluator binds whole-module as a production retrieval module, so `production_identity` moved and the wave records one after-receipt on the final delivered tree with `--baseline docs/reports/retrieval-quality-post-1wuju.json` (the before-receipt: pre-change tree, current evaluator), recorded after every repair landed and cited in the `1wybr` Progress Log.
- ARCH-DEL-1 receipt recorded: `docs/reports/retrieval-quality-post-1wybs.json` (run `2691fb86`, `cross_generation` 174 to 211, evaluator unchanged, production moved by `server_impl.py` only) with verdict `fail` on five zero-tolerance `quality_regression` violations (largest 0.055 nDCG@10) while nine case metrics moved in both directions, three on `code_search` (two of them down); the pre-wave `server_impl.py` reconstructed byte-exactly against the `1wuju` receipt's digest shows a 168-line diff on four lint-parse and install-audit functions with no call path from any retrieval tool. Disposition: corpus drift, routed to operator review; the `1wybq` policy now discloses that a cross-generation comparison attributes drift to the change. OPERATOR DECISION: whether the drift disposition stands as the wave's receipt outcome.
- FOLLOW-UP (docs-only, outside this wave's scope; DOCS-RV1-3): the self-hosted `docs/prompts/prepare-wave.prompt.md` is project-owned, materialized only when absent, and says only "Select required review lanes ... see agent-team-workflow.md", while seed `160` now expects a target's Prepare prompt to state the lane floor and the token grammar; bring it to the shipped baseline's guidance in a later docs wave.
- OPERATOR FOLLOW-UP (drift-free pairs): `retrieval_eval.run_evaluation`'s `production_scripts_dir` is identity-only, so a same-generation before-receipt with the pre-change bytes cannot be recorded; loading the modules it hashes would make `production_change_same_generation` reachable and remove corpus drift from every future comparison.
- OPERATOR FOLLOW-UP (whole-module production identity): the edited lines cannot affect retrieval results, yet the receipt was owed, because `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` binds whole module bytes (`1wur7` RT-RDY-4 kept whole-module identity for the evaluator; production identity works the same way). Every future lifecycle-only edit to `server_impl.py` costs a quiet-machine receipt. A finer production identity (retrieval functions only, or a module split) is the operator's decision; no change in this wave touches the evaluator.
- Watchpoint (landing rule, wave `1wuju`): every sentence and mechanism has a named test that fails on its deletion; the implementer records the mutant table in each Progress Log before requesting review; lanes report mutation tables.
- Watchpoint (frozen tree per round): the briefing packet carries `tree_fingerprint`, `time_budget`, and `sweep_rule`; snapshot the fingerprint AFTER `wf_prepare_wave(mode='ready')`, which gardens changed documents' metadata dates; collect every lane's findings, repair once, re-snapshot once; run the full suite last.
- Watchpoint (declared targets): each change document's Serialization Points bullets are pure paths with `/` and no `*`; the root `CHANGELOG.md` is named in prose, which is the rule `1wxe6` writes down.
- Sequencing: the three changes are independent; `1wybq` is documentation and can land first while `1wxe6` and `1wybr` are in flight.
- OPERATOR DECISION (readiness council, deferred alternative): the explicit `**Review targets**` block accepts a `*.ext` span as a phantom target that recruits no lane and can leave a document declared with an empty roster (executed by both seats; zero of 908 change documents carry one today). The clean fix is one clause in `review_policy._is_declared_target` (`"*" not in candidate`), but it is an evaluator-version transition (`REVIEW_POLICY_EVALUATOR_VERSION` 7 to 8, the tripwire test, a public v7-to-v8 prepare transition test, the spec line naming the version, and one re-Prepare per readied wave, including `1wpig`, which another session readied). This wave documents and pins the phantom as it behaves; the operator decides whether to admit the tightening as its own change.
- Watchpoint (fence blocks): the install template's declares-nothing pin replaces its fenced example byte-exactly; `1wxe6` places its sentence after the existing guidance paragraphs and never touches a fence block.
- Watchpoint (`1wybr` envelope): the repo-relative render must be tolerant of an artifact that resolves outside the repository (`_repo_rel` raises `ValueError` there); the envelope must survive an operator-authored escaping row.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-09-01: PASS with amendments** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1wxe6`'s planned token-grammar sentence was true for the bullet form and false for the explicit `**Review targets**` block, whose span parser never consults `_REPO_PATH_RE` and accepts a `*.ext` span as a phantom target that recruits no lane and can empty a roster, while the planned bullet-only parity pin would have stayed green; strongest-alternative: tighten `_is_declared_target` with one clause shared by both forms, which can never lose a lane and honours the parser's own docstring, at the cost of an evaluator-version transition and one re-Prepare per readied wave including another session's `1wpig`; ADOPTED as a recorded deferral, with the sentence made true for both forms, the explicit-block phantom pinned as it behaves, and the shipped Prepare lifecycle prompt added as a carrier).
- Seat evidence — red-team (adversarial primer, standard depth; stances adversarial, constructive, simplicity): executed the parser on both forms (RT-RDY-1); found the `1wur7` Unreleased CHANGELOG bullet still states the retired re-baseline obligation (RT-RDY-2); showed `production_change_same_generation` is unreachable for a production-module edit here because the modules are indexed, the preflight refuses a stale index, and a completed build advances the generation (RT-RDY-3); showed a "slashes intact" assertion passes on the unguarded sanitizer for a relative root (RT-RDY-4); showed `_repo_rel` raises `ValueError` outside the root (RT-RDY-5); found `expected_artifact` undocumented (RT-RDY-6); measured that a head-only cause cap under about 140 characters breaks existing pins that assert tail tokens (RT-RDY-7); located the byte-exact fence replace in the install template pin (RT-RDY-8); proposed one real-parser test through `_mcp_subprocess_run` (RT-RDY-9); noted the refusal ordering (RT-RDY-10). Claims table: 20 claims, 16 hold, 2 partly, 1 refuted (the claims lint does not constrain the CHANGELOG wording), 1 unverified (the since-repaired `1wpaj` glob).
- Seat evidence — docs-contract-reviewer (rotating, best-alternative seat): confirmed and extended RT-RDY-1 (only extension-bearing spans are phantoms; a root-level span in the block behaves as the remedy says; both field incidents were bullet-form; census re-derived at 908 documents with zero `*` targets under a stated predicate); confirmed the evaluator-version cost from `review_policy.py`, `review_policy_upgrade.py`, the tripwire test, the lifecycle transition tests, memory `1ty9f`, and `mcp-tool-surface.md`'s version line (no lint pins it); answered primer question 2 (`cross_generation`, with the mechanism); found the shipped Prepare lifecycle prompt teaches both forms without the grammar (DOCS-RDY-2), the seed bullets unpinned today (DOCS-RDY-3), the trailing "same way" sentence in `review-and-evals.md` surviving the planned rewrite (DOCS-RDY-5), row 38's hardcoded `--baseline` (DOCS-RDY-7), and both `install-log-format.md` copies naming a field `expected` the producer never emits (DOCS-RDY-8); ran four pins green; verified every change document's declared targets and lane roster against the wave record.
- seat_agreement_aggregate: seat_agreement unanimous (both seats independently recommended the fallback with the tightening deferred); max_severity medium after amendment (the primer's severe RT-RDY-1 was a plan-text defect repaired by amendment before readiness; no delivered code is affected). No challenge round.
- **Delivery review round 1 — 2026-09-02** (fingerprint `0d6072917125c3a2` over 16 paths; red-team primer at standard depth, then the four required lanes in parallel, each with the primer; all lanes reported at budget with mutation tables). Lane verdicts: code approve with notes, qa approve with notes, architecture blocking (ARCH-DEL-1), docs-contract approve with notes. Nine merged findings, all `do_now`: CODE-DEL-1 (merges RT-DEL-1, RT-DEL-5, DOCS-DEL-1, DOCS-DEL-2, QA-DEL-1: the explicit-block clause over-approximated; a bare `*` span is prose, and a bare-glob or root-level span sharing a bullet drops its sibling's lane when another bullet keeps the document declared); ARCH-DEL-1 (`server_impl.py` moved production identity; after-receipt owed under the `1wybq` policy); ARCH-DEL-2 (merges CODE-DEL-2: strip-then-cap order unpinned); CODE-DEL-3 (merges RT-DEL-3, QA-DEL-2: exact-cap boundary unpinned); DOCS-DEL-5 (merges RT-DEL-2: Windows repr-doubled spelling not stripped); CODE-DEL-5 (merges RT-DEL-4: escaping fallback rendered the parent chain); DOCS-DEL-3 (merges QA-DEL-3: format field list unpinned); DOCS-DEL-4 (spec sentence and CHANGELOG bullets unpinned); ARCH-DEL-3 (seed 160 Prepare-prompt checklist item lacked the grammar). Observations with no action: CODE-DEL-4 (a cap below the marker length degenerates; unreachable through the single call site); the `finalize_build_epoch` docstring's sole-advancer claim is stale (production module, untouched). Disagreement resolved by the moderator: the arch and qa lanes preferred a pin-only repair for the sentence with the wording bundled into the deferred tightening; the code lane's executed sibling-loss shape refuted the safe-direction premise, so the wording moved now. Repair: one batch (`1wybs-repair-round-1`), 12 of 12 scratch mutants caught (`mut16`), full suite 8,051 OK, post-repair fingerprint `b3d9b629613f7968`; the after-receipt and the reverifications follow.
- **Round-1 reverification — 2026-09-02** (fingerprint `849822bba8584323`; four fresh lanes): all nine findings REPAIRED and terminal (code lane 13 of 13 mutants caught; docs-contract lane 17 of 19 with two expected survivors; qa lane 20 of 22 with two expected survivors; architecture lane reproduced the byte-exact reconstruction by reverse patch, ran an AST reachability closure from all four retrieval tools, and re-derived the receipt's run id). ARCH-DEL-1 is repaired with the receipt outcome routed to the operator decision above. Every lane approves with notes. New findings: CODE-RV1-1 (merging DOCS-RV1-2; moderate; the 'recruits no lane' and 'empty roster' clauses are false for a phantom under a risk-trigger prefix or extension, executed by two lanes) and ARCH-RV1-2 (merging QA-RV1-1; moderate; the reference-receipt pointer still named the `1wuju` receipt); editorial notes ARCH-RV1-1 (malformed `1wybr` Progress Log rows), QA-RV1-2 (stale resolved-string comment and Risks row), DOCS-RV1-1 (predicate clause counted at one seed-160 site only), DOCS-RV1-4 (this record's `code_search` mover count), and DOCS-RV1-3 (the self-hosted `docs/prompts/prepare-wave.prompt.md` carries no declaration guidance; pre-existing, outside the 16-path scope, recorded as a follow-up).
- **Delivery round 2 repair — 2026-09-02** (`1wybs-repair-round-2`): CODE-RV1-1 and ARCH-RV1-2 repaired in one batch with the four editorial items inline; scratch mutants in `mut18`; reverification by the docs-contract and architecture lanes follows on the re-snapshotted tree.
- **Cycle-2 reverification — 2026-09-02** (fingerprint `a584462b4d85f5a0`; two fresh lanes): CODE-RV1-1 REPAIRED (docs-contract lane: the trigger clause executed over eight phantom shapes and a multi-phantom union; four mutants caught) and ARCH-RV1-2 REPAIRED (architecture lane: the pointer text re-derived against both receipts' identity blocks and the live tree's identities, the compatibility rule read end to end with no verdict check, four mutants caught). Editorial notes repaired inline by the coordinator with its own mutants (`mut19`): DOCS-RV2-2 (the clause now names basename triggers too), DOCS-RV2-1 (parity-test prose), DOCS-RV2-3 (AC-1 site count), ARCH-RV2-1 (row 38's incomparable clause), ARCH-RV2-2 (the handoff's commit list names the new receipt). Process notes: the seed edits of the editorial pass were made with the seed gate closed (opened and closed afterwards, `wf_sync_surfaces` run, recorded in `1wxe6`); the final `wf_prepare_wave(mode='ready')` re-stamped the canonical `install-log-format.md` and not its shipped twin, which the parity pin caught in the last full suite (re-synced, recorded in `1wybr`).
- **Delivery-phase Wave Council [delivery-council] — 2026-09-02: PASS with notes** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the round-1 primer's over-approximate explicit-block clause, sharpened by the code lane into a lane-losing sibling shape and repaired; strongest-alternative: the primer's predicate-stated sentence, adopted, and the architecture lane's insistence that the wave record the after-receipt the `1wybq` policy prescribes, adopted, which exposed that a cross-generation comparison attributes corpus drift to the change and produced the policy disclosure and two operator follow-ups). seat_agreement_aggregate: seat_agreement unanimous on every repair (both cycles); max_severity medium (nothing above moderate in either cycle). Every lane approves with notes on the final tree (fingerprint `614d390b129f4f80`, full suite 8,051 OK, receipt written 2026-09-02T06:44Z, docs lint clean). Eleven ledger findings, all terminal; receipt outcome and the two granularity follow-ups routed to the OPERATOR DECISION bullets above; improvements_recommended beyond the wave: the drift-free same-generation pair (loadable `production_scripts_dir`) and a finer production identity.
- Amendments applied before readiness was recorded: `1wxe6` Rationale, Requirements 1 to 4, Scope, AC-1 to AC-3, Tasks, Serialization Points, a Decision Log row, Risks; `1wybq` Requirements 1 to 5, AC-1 to AC-3, Tasks, Risks; `1wybr` Rationale, Requirements 1 to 5, Scope, AC-1 to AC-4, Tasks, Serialization Points, Decision Log, Risks. improvements_recommended beyond the amendments: none outstanding.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | not_issue | no | not_required | — |
| ARCH-DEL-2 | not_issue | no | not_required | — |
| ARCH-DEL-3 | not_issue | no | not_required | — |
| ARCH-RV1-2 | not_issue | no | not_required | — |
| CODE-DEL-1 | not_issue | no | not_required | — |
| CODE-DEL-3 | not_issue | no | not_required | — |
| CODE-DEL-5 | not_issue | no | not_required | — |
| CODE-RV1-1 | not_issue | no | not_required | — |
| DOCS-DEL-3 | not_issue | no | not_required | — |
| DOCS-DEL-4 | not_issue | no | not_required | — |
| DOCS-DEL-5 | not_issue | no | not_required | — |

*Machine review state — 11 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 11*
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
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Wave `1wpif` is paused and waves `1wpig`/`1wpih` belong to another session; this wave touches none of their files.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 20 | 752,716 |
| implement | 222 | 4,038,820 |
| review | 143 | 5,649,097 |
| **Total** | **385** | **10,440,633** |

<!-- wave:context-efficiency-state {"generation":388,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":222,"content_source_credit":4478810,"derived_artifact_credit":0,"direct_net":4038820,"estimated_tokens_saved":4038820,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8640,"response_debit":431350,"source_credit_count":199,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":20,"content_source_credit":765537,"derived_artifact_credit":3127,"direct_net":752716,"estimated_tokens_saved":752716,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1974,"response_debit":19670,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":143,"content_source_credit":6087094,"derived_artifact_credit":2738,"direct_net":5649097,"estimated_tokens_saved":5649097,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":38063,"response_debit":404561,"source_credit_count":835,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":385,"content_source_credit":11331441,"derived_artifact_credit":5865,"direct_net":10440633,"estimated_tokens_saved":10440633,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":48677,"response_debit":855581,"source_credit_count":1051,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7585},"wave_id":"1wybs review-churn-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 12 | 0 | 9 | 6,335,467 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":6335467,"surfaced_events":12} -->
<!-- wave:exploration-avoided end -->
