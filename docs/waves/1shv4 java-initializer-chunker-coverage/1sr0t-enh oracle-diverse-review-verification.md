# Oracle-Diverse Review Verification

Change ID: `1sr0t-enh oracle-diverse-review-verification`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-16
Wave: 1shv4

## Rationale

Wave `1shv4` exposed a correlated-evidence failure: an implementation, its fixtures, and an agent-steered review all shared the same model of valid Java, so a green suite and multiple approvals missed legal `$` identifiers, comments used as token separators, and a time-complexity test standing in for a space-complexity claim. The current executable-evidence protocol requires falsifiable propositions, public-path execution, realistic boundaries, known-bad detection, and fresh independent repair approval, but it does not require a reviewer to diversify the **reference** used to construct probes when an external contract, second implementation, prior version, schema, or metamorphic invariant exists.

Add a bounded oracle-diversity rule so deterministic transformations are checked against evidence that cannot simply repeat the implementation author's examples. This strengthens self-adversarial verification before review while preserving the existing distinction between strong implementer-generated evidence and independent approval by a reviewer who did not implement the repair.

## Requirements

1. Add a canonical **oracle-diverse verification** rule to seed `209-agent-harness-core.prompt.md`: for deterministic transformations, parsers, serializers, migrations, normalizers, compatibility layers, or equivalent mechanisms, when a credible independent reference exists, the finite risk-selected evidence set includes at least one highest-risk probe derived from that reference rather than solely from implementation-authored examples.
2. Define eligible references narrowly: a governing language/protocol specification, a materially independent implementation, a previous-version compatibility oracle, a schema/model, or a metamorphic invariant whose expected output is known without consulting the code under review. Merely using a second test helper or another agent brief authored from the same hypothesis list is not oracle diversity.
3. Require evidence to name the oracle/reference, the exact property compared, and common-mode limitations. Differential agreement is never universal correctness proof: where both implementations can share a defect, pair it with a spec-derived or metamorphic invariant and narrow any universal claim under the existing census rule.
4. Preserve the finite review budget. This rule requires one prioritized oracle-derived probe when applicable, not open-ended fuzzing. Generative/property execution must be reproducible (fixed seed or durable fixture), reject invalid generated inputs before comparison, and compare only the promised contract surface rather than incidental implementation differences.
5. Preserve seed `209`'s actor-independence contract. An implementer may produce strong self-adversarial oracle evidence, but must not mark it `verification_context.independent: true`, restore a withdrawn specialist approval, or replace an independent semantic/security/architecture judgment. Oracle diversity improves evidence; it does not confer reviewer independence.
6. Add compact operational obligations to the code-reviewer and QA reviewer carriers, sourced from the canonical seed rather than creating another evidence schema or disposition vocabulary. The QA obligation includes the per-property check: name the assertion that would falsify each load-bearing correctness, complexity, compatibility, or parity claim; an adjacent green assertion does not satisfy it.
7. Keep the existing executable-evidence schema. Record oracle identity/property in the existing proposition, command-or-fixture, known-bad method, and limitations fields; do not add new JSONL fields or a prose-length/keyword validator.
8. Update the self-hosted review/testing documentation and rendered reviewer surfaces, and prove both fresh-install and upgrade rendering deliver the new rule to other projects without hand-editing generated project surfaces.
9. Keep the proof ceiling explicit: automated tests may prove canonical rule/carrier presence, render parity, scenario wording, and the existing machine-enforced independence invariant, but they must not claim that prompt presence proves an agent followed the rule. Behavioral adherence remains executable review evidence evaluated on the actual wave.

## Scope

**Problem statement:** Review evidence can be internally consistent yet correlated with the implementation's blind spots. The framework currently defines actor independence and evidence integrity, but not reference/oracle diversity for deterministic transformations.

**In scope:**

- Canonical seed `209` oracle-diversity rule and its applicability/non-applicability boundary.
- Compact code-reviewer and QA-reviewer carrier guidance in their canonical seeds and regenerated self-hosted surfaces.
- Spec-derived, differential, metamorphic, and known-bad evidence guidance within the existing finite probe budget.
- Explicit preservation of independent reviewer/approval semantics.
- Install and upgrade render-path regression coverage for target projects.
- Review/testing documentation updates.

**Out of scope:**

- A general-purpose property-testing or fuzzing framework.
- Mandatory randomized testing when no credible oracle exists.
- New `events.jsonl` fields, validator heuristics, or a second evidence schema.
- Removal or weakening of fresh-context/independent approval requirements.
- Treating tree-sitter, another implementation, or differential agreement as an infallible oracle.
- Changes to Java chunker production behavior; those remain owned by change `1sbfl`.

## Acceptance Criteria

- [x] AC-1: Seed `209` states the applicability gate, eligible oracle classes, one-prioritized-probe finite-budget rule, reproducibility/valid-input requirements, exact-property comparison, common-mode limitation requirement, and the distinction between oracle-diverse evidence and reviewer independence.
- [x] AC-2: Canonical code-reviewer and QA-reviewer seeds carry concise operational guidance sourced from seed `209`; their rendered self-hosted role docs match, and no other role invents a conflicting schema or independence definition.
- [x] AC-3: Executable seed/renderer tests fail on the pre-change carriers and prove the **contract is present and internally coherent**, while existing `review_evidence.py` tests continue to prove the machine-checkable independence invariant: an implementer-produced oracle probe remains `independent: false`. Scenario fixtures cover the required wording for a dual-implementation oracle probe and the no-oracle/unsafe narrowing path, but neither fixture nor a carrier-presence assertion may be described as proof that an agent adhered to the prose rule. **Repaired after focused delivery replay 2026-07-16:** named scenario fixtures now instantiate both paths and assert their bounded carrier/canonical outcomes; `test_implementer_oracle_probe_cannot_restore_withdrawn_lane_approval` records a differential parser proposition as implementer-authored `independent: false` lane reassessment and proves the validator rejects it.
- [x] AC-4: A fresh-install fixture and an upgrade fixture both render the new canonical and reviewer-carrier guidance into a disposable target project, with no manual target-surface edits and no loss of project-authored content. **Repaired after full-wave delivery review 2026-07-16:** every disposable setup/upgrade path now stages the realistic canonical seed set (`209`, `221`, `239`), verifies those target bytes against the packaged source, asserts seed `209` contains the canonical oracle-diversity and implementer-independence contract, and asserts the rendered code/QA carriers—including QA's falsifying-assertion obligation—while retaining the existing project-authored prefix/suffix and historical-wave byte checks.
- [x] AC-5: `docs/contributing/review-and-evals.md` and `docs/architecture/testing-architecture.md` describe oracle diversity as an evidence-quality technique—not a replacement for independent approval—and use the genericized `fallback parser versus grammar-backed parser` initializer-identity case from `1sbfl` as the worked example rather than inventing a synthetic one or making Java-specific behavior a universal requirement.
- [x] AC-6: Full framework tests pass bytecode-free; targeted seed rendering/install/upgrade tests and docs validation pass; seed and framework edit gates are closed after implementation.

## Tasks

- [x] Amend seed `209` with the canonical bounded oracle-diversity contract using existing evidence fields and finite-budget rules.
- [x] Amend the canonical code-reviewer and QA-reviewer seeds with short carrier obligations; regenerate self-hosted role surfaces from seeds.
- [x] Add focused tests for carrier presence, implementer-vs-independent wording, finite applicability, and no duplicate schema language.
- [x] Extend disposable fresh-install and upgrade rendering coverage for other projects. **Repaired:** the setup surface, upgrade surface, and full-upgrade-main fixtures stage/assert canonical seeds `209`/`221`/`239`, canonical seed-209 wording, and both rendered role carriers.
- [x] Update review/testing documentation and synchronize rendered surfaces.
- [x] Run targeted tests, the full bytecode-free suite, `wave_validate`, and diff checks; close every opened edit gate.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| canonical-contract | implementer | — | Seed `209`; no schema or validator expansion |
| reviewer-carriers | implementer | canonical-contract | Code/QA seeds and generated self-hosted role docs |
| distribution-tests | qa-reviewer | reviewer-carriers | Fresh install + upgrade into disposable targets |
| delivery-review | code-reviewer, qa-reviewer | distribution-tests | Exact carrier and independence semantics |


## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md` is the canonical contract and must land before carrier wording.
- Canonical reviewer seeds must land before regenerating `docs/agents/code-reviewer.md` and `docs/agents/qa-reviewer.md`.
- Seed/framework edit gates must be opened only for the implementation window and closed before verification handoff.
- Wave `1shv4` must be re-readied after this change is admitted; implementation must not begin from the wave's superseded readiness verdict.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` — add oracle diversity to the review-evidence strategy and preserve the actor-independence boundary.
- `docs/contributing/review-and-evals.md` — operational guidance and examples.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Canonical behavior and its boundaries must be unambiguous. |
| AC-2 | required | Reviewer carriers are how the rule reaches routine review work. |
| AC-3 | required | The rule must be executable and must not relabel implementer evidence independent. |
| AC-4 | required | Framework behavior must reach installed and upgraded target projects. |
| AC-5 | important | Durable documentation prevents future carrier drift and misuse. |
| AC-6 | required | Distribution and framework verification are release gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-16 | Focused delivery replay found AC-3's two promised scenarios were described but not instantiated. Added a dual-implementation parser scenario, a no-oracle/unauthorized-probe narrowing scenario, and an executable-evidence control proving an implementer-authored differential lane reassessment remains `independent: false` and cannot restore approval. | `test_render_agent_surfaces.py::ReviewProtocolCarrierRegistryTests` (2 scenarios); `test_review_evidence.py::test_implementer_oracle_probe_cannot_restore_withdrawn_lane_approval`; focused renderer 50 + review-evidence 69 OK; final canonical suite 5,643/50 OK. |
| 2026-07-15 | Planned as a second change in wave `1shv4` by operator direction. | The Java initializer review exposed correlated internal evidence; repository-wide seed search found falsification/public-path/known-bad rules but no canonical differential-oracle requirement. |
| 2026-07-16 | Implemented the canonical contract, role-scoped generated carriers, disposable setup/upgrade propagation checks, and durable review/testing guidance. | Focused execution: render-agent-surfaces 48 OK, setup 18 OK, upgrade 302 OK, review-evidence independence 68 OK. Full isolated framework suite: 5,629 OK across 50 files. |
| 2026-07-16 | Closed implementation verification. | `wave_validate`: docs-lint ok with zero warnings; `git diff --check`: clean; `seed_edit_allowed`, `framework_edit_allowed`, and `design_system_edit_allowed` all closed. |
| 2026-07-16 | Full-wave delivery review reopened AC-4. | Setup fixture lines 399–405 and upgrade fixtures lines 1428–1433/1495–1500 create only seed `239`; carriers reference seed `209`, but the target lacks it and no assertion checks the canonical rule. The actual package generically ships framework seeds, so this is a required-AC evidence-integrity gap rather than a confirmed field packaging defect. |
| 2026-07-16 | Repaired AC-4 at the disposable-target boundary. | Setup and both upgrade paths now stage canonical seeds `209`/`221`/`239`, compare target seed bytes with packaged sources, assert the target seed-209 rule and both code/QA carriers, and retain the existing project-content preservation checks. Focused suites: setup 18, upgrade 302, renderer 48, review evidence 68, all OK. Full isolated suite: 5,630 tests across 50 files, OK. Framework edit gate closed after the repair. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-15 | Add oracle diversity without weakening actor independence. | External-reference execution and independent approval solve different correlated-error classes. | Replace independent reviewers with self-review (rejected: semantic judgment and approval authority remain correlated). |
| 2026-07-15 | Reuse existing evidence fields and finite budgets. | The gap is verification guidance, not persistence/schema capability. | Add oracle fields and validator heuristics (rejected: unnecessary burden and weak semantic enforcement). |
| 2026-07-15 | Require one prioritized probe when applicable. | Captures most of the value without open-ended fuzzing or another review rabbit hole. | Require broad randomized testing for every change (rejected: disproportionate and often lacks a credible oracle). |
| 2026-07-16 | Treat prompt/carrier tests as contract-presence evidence only. | A rendered sentence can prove distribution and wording, not behavioral adherence; the latter requires evidence from the reviewed wave. | Describe carrier-presence tests as enforcement (rejected: repeats the same adjacent-proof error this change is meant to prevent). |
| 2026-07-16 | Use the genericized `1sbfl` parser-parity failure as the worked example. | It is executed, current, and demonstrates oracle diversity plus common-mode limits without inventing a hypothetical. | Create a new synthetic example (rejected: weaker evidence and unnecessary prose). |
| 2026-07-16 | Select role-specific carrier obligations by canonical source seed, not only the `docs/agents` destination path. | Installed projects may expose optional native code/QA wrappers; every registered wrapper sourced from seeds `221`/`239` must receive the same compact rule. | Update only the self-hosted Markdown destinations (rejected: host-specific carrier drift on upgrade). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Differential agreement certifies two implementations with the same bug | Require spec-derived/metamorphic invariants and record common-mode limitations. |
| Rule becomes an unbounded fuzzing mandate | Retain seed `209`'s finite probe budget and require only one prioritized oracle-derived probe when applicable. |
| Implementer evidence is mislabeled independent | State the distinction in canonical and carrier seeds and pin it in tests. |
| Installed projects miss the new behavior | Exercise both disposable fresh-install and upgrade rendering paths. |
| Carrier-presence tests are overstated as adherence proof | State the proof ceiling in Requirement 9 and AC-3; reserve adherence claims for executed wave evidence. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
