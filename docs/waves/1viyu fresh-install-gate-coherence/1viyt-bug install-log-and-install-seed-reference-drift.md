# The install-log template, seed-012, seed-010, and seed-040 disagree with each other and with the shipped pack

Change ID: `1viyt-bug install-log-and-install-seed-reference-drift`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-17
Wave: 1viyu fresh-install-gate-coherence

## Rationale

The 2026-08-17 fresh-install field report's fifth item is a checklist row that points at a seed that does not exist: `install/install-log.template.md` row 2.12, "Bootstrap per-role journals (seed-130), artifact: `docs/agents/journals/`". No `130-*.md` ships (69 seeds listed, none numbered 130); the journal system was retired into typed memory records (waves 1t9w8/1t9wa), and seed-012's own step 2.11 says so ("Per-role journals (retired). Action: None ... Do not create `docs/agents/journals/`"). Row 2.10 still says "journals tree". Every install has to discover the dangling row and mark it `[~]` on its own. This was recorded as an open follow-up after the 2026-08-11 doc refresh and never got a wave.

Verifying that item exposed the family it belongs to. The template and seed-012 are supposed to mirror each other (seed-012 line 13: "Steps (mirror `.wavefoundry/install-log.md` Phase 2)"), but their Phase 2 numbering is off by one for the entire phase: the template has 2.2 = legacy baseline wave, 2.3 = seed-030, 2.4 = seed-040, and so on to 2.15; seed-012 has 2.2 = seed-030, 2.3 = seed-040, and no legacy-baseline step at all, so a `wf_audit_install` `next_step` row and the seed-012 heading an agent reads for it name different work. seed-010 line 21 tells an agent to regenerate a missing log from `.wavefoundry/framework/templates/wavefoundry-install-log.md.template`, a path that does not exist (the file is `.wavefoundry/framework/install/install-log.template.md`, which `wf_audit_install`'s `missing_log` diagnostic names correctly). And the report's third item is the same drift in a different seed: seed-040 line 118 mandates the dot-path token schema with lowercase examples but never states the segment charset that `design_system_validators.py` line 116 enforces (`^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*|\.\d+)*$`, error text "expected lowercase segments"), so an agent emitting DTCG-natural `fontSize` or component-derived `kpi-card` fails its own gate (28 errors in the report). Finally the framework README still lists `006-agent-journal-system-overview.md` (line 133; no such seed) and `docs/agents/journals/` as an artifact home (line 162).

None of these needs a mechanism; each is a reference that a test can hold in place once it is fixed.

## Requirements

1. **Install-log template retires dead/circular rows without renumbering.** Remove row 2.12 (seed-130), drop "journals tree" from row 2.10, replace circular verify row 2.14 with bootstrap-file removal, and make row 2.15 **prepare** the structured operator summary. Both instruction rows end at literal `(instruction)` so `_ROW_RE` parses them; details move to adjacent prose. Existing row numbers stay fixed, legacy row 2.2 remains, live logs are untouched, and row 2.13 assertions remain valid.
2. **seed-012 mirrors every parser-visible numbered template row.** Each template row has exactly one `### N.M` heading with the same seed, verify, or instruction kind and action. Add legacy baseline 2.2, bootstrap-removal instruction 2.14, and **prepare structured operator summary** instruction 2.15; only scan-rules and secrets-baseline remain lettered. Keep retired-journals prose under 2.10 and drop 2.12. After preparing and marking 2.15, call the audit, observe `complete`, then deliver the prepared summary to the operator as the postcondition. Reconcile step citations and both format twins. Tests parse the shipped rows with `_ROW_RE`, so suffix drift such as `covers:` fails.
3. **seed-010 regeneration path and the phantom zip-root log.** Line 21 names `.wavefoundry/framework/install/install-log.template.md`. The same drift class one file over: seed-010 line 16, seed-011 lines 3, 20 and 72, and the `setup_wavefoundry.py` module docstring (line 10) name a zip-root `wavefoundry-install-log.md` that the pack does not emit (`build_pack.py` writes only `install-wavefoundry.md` at the zip root; `test_build_pack.py` pins that the log template ships inside the framework tree); they are reworded to the live log path `.wavefoundry/install-log.md` (created from the shipped template) so the two install seeds and the setup script describe the same file the tool reads.
4. **seed-040 token charset.** Line 118 states the segment grammar exactly as the validator enforces it (every segment is lowercase; the first segment starts with a letter and continues with `a-z0-9`; each later segment either starts with a letter and continues with `a-z0-9`, or is all digits, so `500` and `4` pass but `2xl` and `4xl` do not; no hyphens, no uppercase), gives the normalization rule for source names that violate it (split at camelCase and hyphen boundaries into additional dot segments: `fontSize` to `font.size`, `kpi-card` to `kpi.card`, `in-review` to `in.review`; record the original in `source-map.json` `normalizedFrom`), and names the validator so the reader knows it is enforced, not advisory. The regex is not changed.
5. **README dead references.** Line 133 (`006-agent-journal-system-overview.md`) is removed or repointed to the memory overview seed that replaced it; line 162 drops `docs/agents/journals/` from the artifact-home list.
6. **Executable falsification.** Tests prove: (a) every `(seed-NNN)` reference in the install-log template resolves to a shipped seed file (a mutation restoring `seed-130` must fail); (b) every numbered template row has exactly one seed-012 `### N.M` heading with the same seed reference or verify kind, and no seed-012 numbered heading lacks a template row (lettered sub-steps exempt); the test parses both files, so a heading edit or a row edit on either side without the other fails it; (c) every `.wavefoundry/framework/...` path literal in seeds 010, 011, 012 exists in the tree (catches the `templates/` path and any future move); (d) seed-040 line 118's example normalizations (`font.size`, `kpi.card`, `in.review`) match `_DOT_PATH_RE` and the source forms do not, and a digit-leading mixed segment (`size.2xl`) fails as the prose says (the seed prose and the validator are pinned to each other); (e) every "step N.M" / "Phase 2 step N.M" mention across `.wavefoundry/framework/seeds/*.md` and `install/*.md` names a step that exists in seed-012 with the same seed reference or verify kind (a mention-resolution test, so a future renumber cannot strand a citation).

7. **Executable final-tail rows and carrier census.** Preserve numbers and use parser-compatible instruction rows 2.14/2.15 ending at `(instruction)`: remove bootstrap file, then prepare summary. Mirror both in seed-012, which observes `complete` after 2.15 is terminal and only then delivers the prepared summary. Parity tests pin exact kinds/actions, parser visibility, and no suffixes; `1vitr` alone owns runtime advancement tests. Extend the path/reference census to setup docstring and framework README carriers.

8. **Pin the pack-test carrier.** In `test_build_pack.py`, remove `wavefoundry-install-log.md` from the zip-root `allowed_prefixes`, correct the test-class docstring that says it ships there, and assert that exact member is absent from the built archive. A known-bad archive member must fail the same public pack test.

## Scope

**Problem statement:** The install checklist, the seed that mirrors it, the router seed's recovery path, the design-token seed prose, and the README carry references that disagree with the shipped pack, so a fresh install has to discover and paper over each one.

**In scope:**

- `install/install-log.template.md` rows 2.10 through 2.15 (including instruction rows 2.14/2.15), install-log-format row/final-tail mentions, seed-012 Phase 2 headings and postcondition, seed-010 paths, setup module docstring, seed-040 token grammar, framework README dead references, tests, and rendered install prompt if affected.

**Out of scope:**

- Loosening `_DOT_PATH_RE` to accept hyphens or camelCase (a design decision for an ADR if ever wanted; this change makes seed and validator agree as they stand).
- The README's broader journal-philosophy prose (lines 53, 65, 312, 448, 450): a documentation sweep, not an install defect; recorded here as a follow-up candidate.
- Rows 1.2 and 2.1 of the same template are owned by `1vim5` and `1vitr`; this change exclusively owns rows 2.10, 2.12, 2.14, and 2.15 plus their seed parity, while `1vitr` consumes 2.14/2.15 read-only for runtime transition tests.
- Renumbering template rows (forbidden by `install-log-format.md` line 32; the gap at 2.12 is the contract-compliant outcome).
- README line 192 ("journal root path" under the `agent_memory` anchors) belongs to `1vim5`, which owns the anchor list.

## Acceptance Criteria

- [x] AC-1: The install-log template has no `seed-130` row and no journals wording; every pre-existing row keeps its number (no renumber, gap at 2.12); test (a) passes and fails under the seed-130 mutation.
- [x] AC-2: seed-012 numbered Phase 2 headings and the template rows agree number-for-number and seed-for-seed (test b), including a legacy-baseline step 2.2 and an operator-summary step 2.15; sub-steps without a row are lettered; every step-number citation in seeds 011/012/160 and `install/*.md` resolves (test e); the two `install-log-format.md` twins stay byte-identical.
- [x] AC-3: seed-010 line 21 and every framework path literal in seeds 010/011/012 resolve (test c); the zip-root `wavefoundry-install-log.md` name is gone from seeds 010/011 and the setup docstring.
- [x] AC-4: seed-040 line 118 states the enforced segment grammar (including the digit-leading rule) and normalization rule; test (d) pins the prose examples and the `2xl` negative to `_DOT_PATH_RE`.
- [x] AC-5: README lines 133 and 162 no longer reference the missing seed or the journals directory; docs-lint clean; suite green; rendered `docs/prompts/install-wavefoundry.prompt.md` refreshed if affected.
- [x] AC-6: Template/seed rows 2.14 and 2.15 are parser-visible bootstrap-removal and summary-preparation instructions with unchanged numbers, literal `(instruction)` endings, and exact parity; after 2.15 is terminal seed-012 observes `complete` before delivering the prepared summary; runtime transitions are read-only to `1vitr` tests.
- [x] AC-7: Path/reference census tests explicitly pin the setup module docstring and framework README corrections and fail if the phantom zip-root log, missing seed, or journals directory wording is restored.
- [x] AC-8: `test_build_pack.py` neither documents nor allows the phantom zip-root `wavefoundry-install-log.md`, asserts it absent, and fails when the member is injected.

## Tasks

- [x] `install/install-log.template.md`: retire 2.12, fix 2.10, make 2.14 bootstrap-removal and 2.15 summary-preparation instructions without renumbering; mirror exact actions in seed-012, then audit complete and deliver the prepared summary; re-verify both format twins.
- [x] Seeds under `seed_edit_allowed`: seed-012 Phase 2 headings mirrored to the template (add legacy-baseline step, renumber, keep journals-retired note as prose) plus its own step citations (lines 84, 194); seed-011 line 11 and seed-160 lines 217/220/221/222 step citations; seed-010 line 21 path; seed-010 line 16 / seed-011 lines 3, 20, 72 / `setup_wavefoundry.py` docstring zip-root log name; seed-040 line 118 charset + normalization + validator name.
- [x] `README.md` lines 133 and 162.
- [x] Tests (a) through (e) in `test_install_log_lib.py` (template/seed parity, seed-ref resolution, step-mention resolution) and `test_docs_lint.py` (dot-path pin); apply any `install-log-format.md` edit to both twins; full suite; `wf_validate_docs`; `wf_sync_surfaces` dry-run to see whether the rendered install prompt changes.
- [x] Final-tail/carrier tests: pin parser-visible instruction row 2.14 bootstrap removal and row 2.15 summary preparation, literal `(instruction)` endings, seed ordering `prepare → mark → audit complete → deliver`, setup-docstring wording, and framework README corrections; leave runtime advancement assertions to `1vitr`.
- [x] `test_build_pack.py`: remove the phantom root member from `allowed_prefixes`, fix the stale class docstring, add exact absence/known-bad assertions, and run focused pack tests.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| log        | implementer | none       | Goal: template rows + seed-012 mirror + tests (a)(b) |
| refs       | implementer | none       | Goal: seed-010 path, README lines, test (c) |
| tokens     | implementer | none       | Goal: seed-040 line 118 + test (d) |


## Serialization Points

- `.wavefoundry/framework/install/install-log.template.md`
- `.wavefoundry/framework/install/install-log-format.md`
- `docs/references/install-log-format.md`
- `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/README.md`
- `.wavefoundry/framework/scripts/tests/test_install_log_lib.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

**Framework maintenance note.** Seed edits (010, 011, 012, 040, 160) require `seed_edit_allowed`; the `setup_wavefoundry.py` docstring edit requires `framework_edit_allowed` (shared with `1vim5`, which owns Step 0 code; this change owns the module docstring line only). seed-160 lines 217 to 222 are this change's; `1vitq` owns 198/199 and `1vim5` owns 516. `install-log.template.md`, seed-012, seed-040, and README are shared with `1vim5` (row 1.2, seed-040 line 64, README anchors) and `1vitr` (row 2.1, seed-012 step 2.1): the wave coordinator serializes edits to those files; this change owns rows 2.10 onward, the seed-012 heading numbers, seed-040 line 118, and README lines 133/162. Read-only: `design_system_validators.py` (pinned by test, not edited).

## Affected Architecture Docs

`N/A`: reference reconciliation only; no boundary, flow, or verification-seam change.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The reported dangling row; the resolution test stops the next one. |
| AC-2 | required  | The audit's `next_step` row and the seed heading must name the same work or the state machine misleads. |
| AC-3 | required  | A recovery path that names a nonexistent file is a trap at the worst moment. |
| AC-4 | required  | Reported item 3; the seed must match the gate it points the agent at. |
| AC-5 | important | Dead references in the README; harmless to install mechanics but reported-adjacent and cheap. |
| AC-6 | required  | The live install state machine must never require marking a row before its success condition is observable. |
| AC-7 | important | The explicitly corrected setup/README carriers need mutation-sensitive owners to prevent the same reference drift recurring. |
| AC-8 | important | The pack test is itself a public-release contract carrier; its stale allowlist otherwise permits the phantom artifact to return. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-17 | Delivery review editorial repairs (docs-contract lane APPROVE-with-editorial): DC-DEL-1 two more dead seed filenames in the framework README (`130-agent-journal-bootstrap.prompt.md` removed; `210-agent-journal-distillation.prompt.md` corrected to `210-migrate-journals.prompt.md`) and the manifest anchor `journal root` reworded to `memory root`, held by the new generalized `test_framework_readme_seed_filenames_all_ship` (every backticked `NNN-*.md` in the README must ship); DC-DEL-2 install-log template line 54 now cites seed-012 step 2.15 instead of the removed `§ Operator summary handoff`, and seed-012's closing sentence no longer points at seed-010 lines 148-195; DC-DEL-3 rendered `docs/prompts/install-wavefoundry.prompt.md` items 6/7 reordered to match seed-012 (bootstrap file removed at row 2.14, summary delivered after the final `complete` at 2.15). Note-only: `docs/architecture/threat-model.md:60` still says `seed-130` (self-hosted doc, follow-up candidate). | `.wavefoundry/framework/README.md`; `test_shipped_reference_docs` (16 OK); `install/install-log.template.md` line 54; seed-012 tail; `docs/prompts/install-wavefoundry.prompt.md` items 6-7 |
| 2026-08-17 | Thought: test the parser and pack carrier, not just prose shape. Observe: final red-team found row 2.15's `covers:` suffix made it invisible to `_ROW_RE`, and `test_build_pack.py` still allowed the phantom zip-root log. Requirements 1/2/7/8 now require parser-compatible instruction rows and an exact negative pack assertion. | Final-tail parser probe; `RT-FINAL-007`; build-pack member mutation |
| 2026-08-17 | Thought: preserve row numbers while giving every row executable work. Observe: Requirement 7 supersedes the rowless-bootstrap example, makes 2.14 bootstrap removal and 2.15 summary, and expands the path/reference census to the setup docstring and framework README. | `DOC-FINAL-005`, `RT-FINAL-006`; final-tail probe; carrier census |
| 2026-08-17 | Readiness amendment from the docs-contract seat (DC-1, DC-2, DC-3, DC-12): step-number citations in seeds 011/160/012 move with the renumber and get a mention-resolution test (e); the phantom zip-root `wavefoundry-install-log.md` name in seeds 010/011 and the setup docstring is folded in; the `install-log-format.md` canonical twin (`docs/references/`) is named and kept byte-identical; the token grammar prose now states the digit-leading rule with a `2xl` negative in test (d). | `test_shipped_reference_docs.test_shipped_templates_are_byte_identical_to_canonical`; `build_pack.py` zip-root members; `_DOT_PATH_RE` |
| 2026-08-17 | Readiness amendment from the red-team primer (RT-1, RT-2): dropped the contiguous renumber (contract at `install-log-format.md` line 32; parser tolerates gaps), scoped the parity test to numbered rows with lettered sub-steps for seed-012's 2.3a/2.3b/2.14, added the 2.15 summary step, and reassigned README line 192 to 1vim5. | primer verified against `install_log_lib._ROW_RE`, `first_unchecked_row`, `test_install_log_lib.py` `by_num["2.13"]` |
| 2026-08-17 | Planned from the 2026-08-17 fresh-install field report (items 3 and 5) plus verification finds. Verified: `code_list_files` shows 69 seeds, none `130-*`; template rows 2.10/2.12 (`install-log.template.md` 48/50); seed-012 step 2.11 retires journals and step numbers 2.2 to 2.13 do not match template rows 2.2 to 2.15; seed-010 line 21 `templates/` path absent (`ls` confirms); seed-040 line 118 states dot-path with no charset while `_DOT_PATH_RE` (`design_system_validators.py` 116, applied at 380) is lowercase-alnum only; README 133/162. | cited lines; memory `project_doc_refresh_2026_08_11_followups` (open item) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-17 | Row 2.15 prepares the summary; delivery occurs only after the terminal audit returns `complete`. | A row named "deliver" cannot truthfully be marked before delivery on single-response hosts, but the final audit cannot run until the row is terminal. Preparation is executable before marking and preserves post-gate delivery. | Deliver then audit (rejected: the user sees success before the terminal gate); mark delivery before sending (rejected: false `[x]` state). |
| 2026-08-17 | Promote bootstrap-file removal to instruction row 2.14 and observe `complete` only after instruction row 2.15 is terminal; this supersedes the earlier decision to keep bootstrap removal rowless. | A pending `wf_audit_install` verify row necessarily returns itself, so no audit expectation can be observed before marking that row. The two existing instructions provide truthful row work without renumbering. | Keep/move an audit expectation on row 2.14 (rejected: circular under first-pending semantics); remove row 2.14 entirely (workable but leaves bootstrap removal without a checklist owner). |
| 2026-08-17 | Template numbering wins; the retired row is removed and the gap kept (no renumber, per `install-log-format.md` line 32); seed-012 headings are renumbered to the template with lettered sub-steps for row-less steps; parity and path-resolution tests hold the references. | The template is the live state machine operators copy, and `wf_audit_install` returns its row numbers; the shipped row-format contract forbids renumbering existing rows because it invalidates in-progress logs, and the parser tolerates gaps; a test is the only thing that has kept a reference honest in this pack. | Renumber 2.13 to 2.15 contiguously (rejected at readiness on the red-team primer, RT-1: violates the shipped contract and breaks `test_install_log_lib.py`'s `2.13` assertion for no user-visible gain); keep row 2.12 as a pre-marked `[~]` "retired" row (rejected: a permanent not-applicable row in every fresh log is the debris the report complained about); make seed-012 canonical and rewrite the template to it (rejected: seed-012 lacks the legacy-baseline row, which is a real conditional step, and the template's numbers are already what the tool emits); promote seed-012's 2.3a/2.3b/2.14 to template rows (rejected: changes what `wf_audit_install` surfaces; they are sub-steps of an existing row's work). |
| 2026-08-17 | State the token charset in seed-040 and pin the examples to `_DOT_PATH_RE`; do not widen the regex. | The seed points the agent at a gate; they must agree, and widening the naming grammar is a design decision that deserves its own ADR with the token-build pipeline (Style Dictionary exports) in view. | Widen the regex to accept hyphens/camelCase (deferred: changes the shipped naming contract for existing design-system trees); leave the seed as-is and rely on the lint message (rejected: that is the reported failure). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A row reference elsewhere (docs, tests, `install-log-format.md`) names row 2.12 or a seed-012 sub-step number that moves. | No template renumber happens; grep for `2\.1[0-5]` and `2\.3[ab]` mentions across the pack at implement; test (b) pins the seed; `install-log-format.md` re-verified. |
| Three changes edit the same template and seed files. | Ownership by row/line is stated above; the coordinator sequences; docs-lint runs after each. |
| The normalization rule in seed-040 conflicts with an existing target repo's token names. | The rule is install guidance for extraction; existing trees are already validated by the same regex, so nothing that passes today changes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
