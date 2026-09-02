# Serialization Points Scaffold Guidance: Root-Level Files and Globs Declare Nothing

Change ID: `1wxe6-enh serialization-points-scaffold-guidance`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-01
Wave: 1wybs review-churn-follow-ups

## Rationale

All three `1wuju` change documents, and the `1wpaj` document in wave `1wpig`
(since repaired), lost review lanes silently. A bare root-level `CHANGELOG.md`
in the first case and a glob (`docs/reports/retrieval-quality-*.json`) in the
second turned the whole `## Serialization Points` bullet into prose, so the
test and architecture paths sharing that bullet went undeclared and the
documents dropped the `architecture-reviewer` and `qa-reviewer` lanes. Both
incidents were in the bullet form: its grammar (`_REPO_PATH_RE` in
`review_policy.py`, consulted by `_pure_path_bullet_targets`) accepts only a
token with at least one `segment/` and a character class without `*`, and a
bullet declares all or nothing. The explicit `**Review targets (repo-relative
paths):**` block has a different gap, found at this wave's readiness: its span
parser (`_span_bullet_targets`) never consults `_REPO_PATH_RE`, so a span such
as `docs/reports/retrieval-quality-*.json` is accepted as a declared target
that matches no file and recruits no lane, and a block holding only such spans
leaves the document in declared mode with an empty roster. The scaffold
guidance in seeds `170`, `040`, and `160`, the shipped
`install/plan-template.md`, the project `docs/plans/plan-template.md`, and the
shipped Prepare lifecycle prompt teach the two forms, the all-or-nothing rule,
and the wrapped-bullet rule, but not the token grammar of either form. In this
repository `test_declaration_change_loses_no_lane_anywhere_in_the_corpus`
catches the mixed-bullet symptom at the full suite; a target repository has no
such census, so its lanes are simply lost. Recorded as an out-of-scope
follow-up by the `1wuju` delivery review (DOCS-DEL-1).

## Requirements

1. Seed `170-plan-feature` (the `## Serialization Points` bullet) and seed `040-docs-structure-bootstrap` (the section description) SHALL each gain one generic sentence, true for both declaration forms, stating the token grammar the parser enforces: a declared path token has at least one `/`, so a root-level file is never a token in either form, and a bullet declares all or nothing in either form, so one such token turns the whole bullet into prose and every other path in it goes undeclared with it; in a bullet a `*` also disqualifies the token; inside the explicit block a span is kept only when its last segment carries an extension or the span ends in `/` (the parser's `_is_declared_target` predicate), so a `*` span that satisfies that is accepted as a phantom that matches no file and recruits a lane only through a trigger token it happens to carry (a directory prefix, an extension, or a trigger basename), a block holding only phantoms leaves the document declared with whatever roster those triggers recruit (empty when none is a trigger), and any other `*` span turns its bullet into prose (delivery review CODE-DEL-1, CODE-RV1-1). The sentence SHALL name the remedy: put a root-level file in its own prose bullet, and declare the directory that holds globbed files. Examples stay generic (a changelog, a readme); no test name, wave id, or repository specific enters a seed.
2. Seed `160-upgrade-wavefoundry` SHALL carry the same sentence in its merge-safe template repair instruction and in its verification checklist items for `docs/plans/plan-template.md` and for `docs/prompts/prepare-wave.prompt.md` (the shipped Prepare prompt is materialized only when absent, so the upgrade checklist is the only path that brings an existing one to the guidance; delivery review ARCH-DEL-3), so an upgrade brings an existing operator template to the same guidance.
3. The shipped `.wavefoundry/framework/install/plan-template.md`, the project `docs/plans/plan-template.md`, and the shipped Prepare lifecycle prompt `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md` (which teaches both forms without the grammar) SHALL carry the sentence outside any fence; both templates SHALL still declare zero targets, and neither fenced example block in either template moves by a byte (the existing pin replaces the install template's fence block byte-exactly).
4. Every sentence SHALL be pinned by an `assertIn` test anchored on the new sentence AND on one existing phrase of the same bullet or paragraph, so a rewrite of the bullet cannot pass the pin by accident. One grammar-parity pin SHALL demonstrate the documented rule against `review_policy.serialization_point_paths` and `select_required_review_lanes` in both forms: a pure-path bullet carrying a root-level file token or a glob token declares nothing while the same bullet without that token declares the remaining paths; an explicit block holding a `*.ext` or `dir/*/` span returns that span and recruits no lane when the phantom carries no trigger and the trigger's lane when it does (`docs/specs/*.md` recruits docs-contract-reviewer, `src/*/` recruits code-reviewer), a root-level span in the block returns nothing while its sibling bullets still declare, a bare `*` span with no extension is prose (its sibling still declares, and when it shares a bullet with a real path that path is dropped while another bullet keeps the document declared), and a root-level span sharing a block bullet with a real path makes that bullet prose. The pin fails when tier 1 is relaxed for `/` or `*`, when tier 2 stops accepting the phantom, when tier 2 accepts a bare `*` span, or when tier 2 skips a failing span instead of turning the bullet prose (the guidance must move with the grammar).
5. `CHANGELOG.md` `## [Unreleased]` SHALL announce the guidance.

## Scope

**Problem statement:** The scaffolds teach two declaration forms and the all-or-nothing rule but not the token grammar, so a root-level file or a glob silently drops review lanes in every target repository: in the bullet form by turning the bullet into prose, in the explicit block by declaring a phantom.

**In scope:**

- One sentence in seeds `170`, `040`, and `160` (two sites), with the seed gate opened and closed around the edits and `wf_sync_surfaces` run afterwards.
- The same sentence in both plan templates and the shipped Prepare lifecycle prompt, outside the fences.
- The `assertIn` pins, the two-form grammar-parity pin, and the CHANGELOG bullet.

**Out of scope:**

- Changing the parser. Loosening it to accept a root-level token or a glob reopens the phantom-declaration defect the strict grammar closed (a dotted word such as a version string would declare itself; a glob names no file). Tightening `_is_declared_target` to reject `*` in both forms is the better end state and is recorded in the Decision Log as a deferred alternative with its cost: it is an evaluator-version transition (`REVIEW_POLICY_EVALUATOR_VERSION` 7 to 8, the tripwire test, a public v7-to-v8 prepare transition test per memory `1ty9f`, the spec line naming the version, and one re-Prepare per readied wave, including waves another session owns).
- A docs-lint sensor that warns when a Serialization Points bullet mixes path tokens with a non-path token. A later change with field data, shipped advisory-first.
- Re-authoring existing change documents. A census over 908 change documents (`docs/plans/*.md` minus the template plus `docs/waves/*/*.md` minus `wave.md`) found zero declaring a `*` target in either form today.
- The upgrade's scaffold repair code (`repair_declaring_scaffold` fences declaring examples; it injects no guidance, and the seed `160` instruction is the merge path for operator templates).
- The hand-maintained project prompts `docs/prompts/plan-feature.prompt.md` and `docs/prompts/prepare-wave.prompt.md`, which carry no declaration guidance at all (a pre-existing omission, not a contradiction).

## Acceptance Criteria

- [x] AC-1: Seeds `170`, `040`, and `160` (all three sites) carry the two-form token-grammar sentence with its remedy, each pinned by an `assertIn` test anchored on the new sentence and an existing phrase of the same bullet, failing when the sentence is removed.
- [x] AC-2: Both plan templates and the shipped Prepare lifecycle prompt carry the sentence outside any fence, each pinned the same way; the existing declares-nothing pins (`test_the_shipped_scaffolds_declare_nothing_until_an_author_edits_them`, `test_shipped_template_has_required_headings_and_declares_nothing`) still pass on the edited templates with both fence blocks byte-identical to today.
- [x] AC-3: The grammar-parity pin shows, in the bullet form, that a bullet carrying `CHANGELOG.md` or a `*` token declares nothing under `serialization_point_paths` while the same bullet without that token declares the rest, and, in the explicit block, that a `*.ext` or `dir/*/` span is returned and `select_required_review_lanes` recruits no lane while a trigger-carrying phantom (`docs/specs/*.md`, `src/*/`) recruits that trigger's lane, a root-level span returns nothing while sibling bullets still declare, a bare `*` span is prose (sibling kept; a shared real path dropped when another bullet keeps the document declared), and a root-level span sharing a bullet makes it prose; the pin fails when tier 1 is relaxed for `/` or `*`, when tier 2 is changed to reject the phantom, when tier 2 accepts a bare `*` span, and when tier 2 skips a failing span (delivery review CODE-DEL-1).
- [x] AC-4: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `seed_edit_allowed`; add the sentence to seeds `170`, `040`, and `160` (repair instruction and checklist item); close the gate; run `wf_sync_surfaces`.
- [x] Add the sentence to both plan templates (after the existing "Prepare selects automatic review lanes ..." paragraph in the install template and after the "Prepare uses declared paths ..." paragraph in the project template; fence blocks untouched) and to the shipped Prepare lifecycle prompt; confirm both templates still declare nothing with `serialization_point_paths`.
- [x] Add the `assertIn` pins beside the existing scaffold pins in `test_docs_lint.py` and the two-form grammar-parity pin in `test_review_policy.py`.
- [x] CHANGELOG Unreleased bullet.
- [x] Record the mutant table in this Progress Log: each sentence deleted in a scratch copy fails its pin; tier 1 relaxed for `/` and for `*`, and tier 2 changed to reject `*`, each fail the parity pin in a scratch copy.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed text | implementer | — | Seed gate opened and closed around the edits |
| Templates and lifecycle prompt | implementer | — | Sentence stays outside every fence; fence blocks byte-identical |
| Pins and CHANGELOG | implementer | Seed text, Templates and lifecycle prompt | Mutant table before review |


## Serialization Points

- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/install/plan-template.md`, `docs/plans/plan-template.md`, `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

N/A: the change adds guidance to seeds, templates, and a lifecycle prompt and pins it; the parser, its module boundaries, and the review-policy flow are untouched.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The seeds are what every target repository reads. |
| AC-2 | required | The templates are what every new change doc is born from, and they must keep declaring nothing. |
| AC-3 | important | The parity pin is what keeps the guidance true when either grammar moves. |
| AC-4 | required | The change's own evidence. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-02 | Cycle-2 reverification editorial notes (inline, no new cycle): DOCS-RV2-2, the enumeration "prefix or extension" omitted the basename and interior-fragment trigger shapes (`*/build_pack.py` recruits release-reviewer by basename; executed by the docs-contract lane, safe direction), so the clause in every carrier now reads "through a trigger token it happens to carry (a directory prefix, an extension, or a trigger basename)" with the pin fragment and the seed-160 count pin moved with it; DOCS-RV2-1, the parity test's docstring and one assertion message still said "recruits no lane"; DOCS-RV2-3, AC-1 said "both sites" for seed 160's three. Coordinator mutant: the reworded clause deleted from one carrier fails the carrier pin. Process lapse recorded: the three seed edits of this editorial pass were made with `seed_edit_allowed` closed; the gate was opened and closed immediately afterwards for the audit trail, and `wf_sync_surfaces` was run. | `mut19_run.log`; the cycle-2 reverification reports (docs-contract, architecture). |
| 2026-09-02 | Delivery round 2 repair (CODE-RV1-1 merging DOCS-RV1-2, found by the code and docs-contract reverifications; DOCS-RV1-1 folded in). Executed by both lanes: a phantom whose prefix or extension is a risk trigger recruits that lane (`docs/specs/*.md` docs-contract, `src/*/` and `lib/*.py` code, `tests/*/` qa, `docs/architecture/*.md` architecture), so 'recruits no lane' and 'empty roster' were false in the safe direction. The clause in all seven carriers, both seed-160 checklist parentheticals, and the CHANGELOG now reads 'recruits a lane only through a trigger prefix or extension it happens to carry' with 'whatever roster those triggers recruit (empty when none is a trigger)'; `FRAGMENTS` gains that clause; the seed-160 count pin counts the predicate clause and the trigger clause at all three sites; the parity pin gains two trigger-carrying phantom subtests. Landing rule (scratch `mut18`): the clause deleted from one carrier, the predicate clause deleted at one seed-160 site, and phantoms made to recruit nothing each fail their pin. | `mut18_run.log`; the round-1 reverification reports (code, docs-contract). |
| 2026-09-02 | Delivery round 1 repair (CODE-DEL-1 merging RT-DEL-1, RT-DEL-5, DOCS-DEL-1, DOCS-DEL-2, QA-DEL-1; ARCH-DEL-3; DOCS-DEL-4). Four seats executed the parser and found the explicit-block clause over-approximate: only a span whose last segment carries an extension or that ends in `/` is kept (`_is_declared_target`), a bare `docs/reports/*` span makes its bullet prose, and the code lane showed a bare-glob or root-level span sharing a block bullet with a real path drops that path's lane whenever another bullet keeps the document declared, so the sentence was not uniformly in the safe direction. Repair: the sentence in all seven carriers, the seed-160 checklist parenthetical, and the CHANGELOG bullet now state the predicate (a bullet declares all or nothing in either form; a `*` span in the block is a phantom only when it satisfies the predicate, otherwise its bullet is prose); seed 160's Prepare-prompt checklist item gains the parenthetical (third site; `test_seed_160_states_it_at_all_three_sites`); `FRAGMENTS` gains the predicate clause; the parity pin gains the `docs/*/` phantom, the bare-glob own bullet, the bare-glob-plus-path bullet with a declared sibling, and the root-level-plus-path bullet; both `1wybs` CHANGELOG bullet leads are pinned (`test_the_unreleased_changelog_announces_the_wave`). Landing rule (scratch `mut16`, controls first): tier-2 predicate accepting any `*` span CAUGHT; tier-2 skipping a failing span CAUGHT; seed-170 narrowed clause deleted CAUGHT; seed-160 third-site parenthetical deleted CAUGHT; each CHANGELOG lead deleted CAUGHT. The arch and qa lanes preferred a pin-only repair with the wording bundled into the deferred tightening; the coordinator adopted the wording change on the code lane's sibling-loss reproduction. | `mut16_run.log` (12 of 12 caught across the wave); `1wybs_r1_targeted_c.log` (199 OK); `full_suite_1wybs2.log` (8,051 OK). |
| 2026-09-01 | Landing rule: six scratch-copy mutants under session scratch `mut15`, each caught by its named test on an otherwise green base (controls run first): the seed-170 sentence deleted (`test_every_carrier_states_the_token_grammar`, carrier subtest); the seed-160 checklist clause deleted (`test_seed_160_states_it_at_both_sites`); the project-template sentence deleted (`test_every_carrier_states_the_token_grammar`, carrier subtest); tier-1 grammar relaxed to accept `*` and, separately, a root-level token (`test_the_documented_token_grammar_matches_both_declaration_forms`, bullet subtests); tier 2 changed to reject the phantom (the same pin, explicit-block assertion). | `mut15_run.log`: 16 of 16 caught across the wave. |
| 2026-09-01 | Implemented. Seed `170` (the `## Serialization Points` bullet, after "declares no target"), seed `040` (the section description, after the wrapped-bullet rule), and seed `160` (the repair instruction, introduced by "State the token grammar too:", and the checklist item as a parenthetical) carry the two-form sentence; the install template gains it after its guidance paragraph, the project template after its "Prepare uses declared paths" paragraph, and the shipped Prepare lifecycle prompt inside readiness check 5, with both fence blocks byte-identical (`test_the_fenced_examples_are_untouched`). `seed_edit_allowed` opened and closed around the seed edits; `wf_sync_surfaces` run (nothing rendered changed: the sentence lives outside renderer-owned regions). Pins: `SerializationPointsTokenGrammarPinTests` in `test_docs_lint.py` (every carrier with an existing-phrase anchor plus four fragments; seed 160 at both sites; fenced examples untouched) and `test_the_documented_token_grammar_matches_both_declaration_forms` in `test_review_policy.py` (bullet form: a root-level or glob token makes the bullet prose, the clean bullet declares both paths; explicit block: a root-level span declares nothing while its sibling declares, a `*.ext` span is returned and recruits no lane). CHANGELOG Added bullet. The existing declares-nothing pins, the corpus census, and the shipped-docs parity pin stay green. Gapfill: the edits are exact-string replacements applied with the shell, and region reads during implementation used shell `sed` over anchors located with MCP `code_keyword`/`code_read` at planning and readiness (docs-only work, per the retrieval posture). | `1wybs_targeted_1.log` (199 OK: the two new pin classes, `FreshPlanTemplateTests`, `ScaffoldDeclaresNothingTests`, all of `test_review_policy`, `test_shipped_reference_docs`, `test_install_log_lib`); `wf_validate_docs` green; `wf_sync_surfaces` written: none. |
| 2026-09-01 | Readiness council amendments applied (RT-RDY-1, RT-RDY-8, DOCS-RDY-1, DOCS-RDY-2, DOCS-RDY-3): the sentence now covers both declaration forms (the explicit block accepts a `*.ext` span as a phantom; executed by both seats: a glob-only block yields declared mode with an empty roster, a glob-plus-test block loses the architecture lane against its prose reading); the parity pin gains the two explicit-block probes; the shipped Prepare lifecycle prompt joins the carriers; pins anchor on an existing phrase too; the parser tightening is a recorded deferral with its evaluator-version cost. | Readiness council checkpoint in `wave.md`; `_span_bullet_targets` lines 557 to 565; census 908 documents, zero `*` targets. |
| 2026-09-01 | Drafted from the `1wuju` close follow-ups (delivery review DOCS-DEL-1). The parser grammar was read, not remembered: `_REPO_PATH_RE` requires `segment/` and has no `*` in its class; `_pure_path_bullet_targets` returns nothing when any token fails. | `review_policy.py` lines 450 and 583 to 600; `1wujr` Progress Log gapfill row; `1wuju` wave record follow-up bullet. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | Readiness council (both seats): keep the parser untouched in this wave; make the sentence true for both forms and pin the explicit-block phantom as it behaves today; record the `_is_declared_target` tightening (`"*" not in candidate`, one clause shared by both tiers) as the deferred better end state. | The tightening can never lose a lane (removing a phantom leaves the other declared paths or returns the document to fallback, which is equal or more review, the invariant `test_declaration_change_loses_no_lane_anywhere_in_the_corpus` asserts) and honours the parser's own docstring, which names phantoms as the defect. Its cost is an evaluator-version transition: `REVIEW_POLICY_EVALUATOR_VERSION` 7 to 8 (a `policy_input_digest` input), the tripwire test's docstring and assertion, a public v7-to-v8 prepare transition test (memory `1ty9f`), the `mcp-tool-surface.md` line naming version 7 (no lint pins it), a `framework_edit_allowed` edit, and one re-Prepare per readied or open wave, including `1wpig`, which another session readied. Zero documents are affected today, so the guidance loses nothing by waiting. The operator decides whether to admit the tightening separately. | **Tighten now inside this wave:** the better end state, at the cost above and a cross-session re-Prepare. **Say nothing about the explicit block:** ships a sentence that is false for the form seed `170` tells authors to use for spaced paths. |
| 2026-09-01 | One guidance sentence per scaffold surface plus a grammar-parity pin. | Smallest change that reaches every target repository through the seeds and every new change doc through the templates, and the parity pin keeps it true. | **Relax the parser to accept root-level files and globs:** a root-level token is indistinguishable from a dotted word (a version string, an abbreviation) and a glob names no file, so both reopen the phantom-declaration defect the strict grammar closed. **A docs-lint sensor on mixed bullets:** larger, and a new sensor ships advisory, so it warns after the fact rather than teaching at authoring; a candidate later change with field data. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The guidance sentence drifts from either enforced grammar. | The parity pin demonstrates the documented behaviour of both forms against `serialization_point_paths` and `select_required_review_lanes`. |
| The sentence itself declares a target (it names path shapes). | It is written as prose with English words and is pinned by the existing declares-nothing tests on both templates. |
| The install template's fenced example moves and the byte-exact replace in its pin silently no-ops. | The sentence is placed after the existing guidance paragraph and AC-2 asserts both fence blocks are byte-identical to today. |
| An upgraded operator template never receives the sentence. | Seed `160` carries the instruction in both its repair step and its verification checklist. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
