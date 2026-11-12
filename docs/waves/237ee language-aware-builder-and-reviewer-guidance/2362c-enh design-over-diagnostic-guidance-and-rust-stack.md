# Design-over-diagnostic guidance and a Rust stack block

Change ID: `2362c-enh design-over-diagnostic-guidance-and-rust-stack`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-11
Wave: 237ee language-aware-builder-and-reviewer-guidance

## Rationale

A Rust and Swift project on 1.42.0+q2u7 reports that agents get Rust to compile by patching each borrow-checker error where it appears: copies added to end a borrow, fields checked out and back in, runtime-checked cells added to pass the checker. The result passes tests and carries hidden cost. The reporter cites a public case study of a ported engine that ran nearly twice as fast after an ownership refactor; that figure is the reporter's, is not reproduced here and is not an acceptance target.

The tree confirms the gaps. Seed 222 (software-engineer) detects Python, JVM, C# and TypeScript only and has no Rust block. Seed 180 (implement-change) has no rule for a compiler error whose only local fix is a structural workaround. Seed 170 (plan-change) says nothing about ports or rewrites. Seed 221 (code-reviewer) has a "Suppressed failures" check covering ignore comments and lint or type configuration, but nothing on copies, check-outs, cells or unchecked casts. Seed 080 is the docs gate, not a home for language lints.

## Product Intent

Builders and reviewers in statically checked languages treat a compiler or type-checker error as feedback on the data design, and a reviewer can find where the design was worked around. AC-1 through AC-4 establish that the guidance is delivered and conditional. They do not prove agents write better Rust; the reporter's next upgrade and port are the field check.

## Requirements

1. **Rust detection.** Seed 222's stack detection adds Rust, confirmed from `Cargo.toml` and `*.rs` source files.
2. **More than one stack.** Today the seed includes one block for the "primary" stack and none for mixed projects, so a Rust and Swift project would get nothing. When repository evidence shows more than one substantial language, include the block for each detected language that has one, and name each in the Operating Identity. Reword every place the seed says "primary stack" (the detection step, the block-inclusion step, the skills introduction and the default line) so they agree; the default applies only when no language is detected.
3. **Generic first.** Guidance that holds in any language goes in the all-stacks text; a language block holds only that language's constructs. Add to the all-stacks skills in seed 222:
   1. Fix the design, not the diagnostic: a compiler, borrow-checker or type-checker error is feedback on the data design.
   2. Decide ownership first: which component owns each piece of state and whether access is shared or exclusive.
   3. Do not add per-item, per-request or per-frame threads or runtimes, or whole-buffer copies across thread or process boundaries, merely to appease a diagnostic. Document a necessary design or performance tradeoff when these costs are justified.
   4. Build data once in the shape its consumer needs.
   5. Keep types cohesive.
   6. Follow the project's existing lint, panic and unsafe-code policy; never add a broad suppression to get a green build.
4. **Language examples.** Add one or two lines of language-specific workaround examples to each applicable block, preserving its existing expertise guidance. Rust, rendered only when Rust is detected: a copy (`clone`, `to_vec`, `collect`) added only to end a borrow, a check-out and return of a field, or a shared runtime-checked cell added to pass the checker needs a one-line reason in the code or change record. TypeScript: unchecked casts. Python: an unexplained type-ignore. C#: the null-forgiving operator.
5. **Escalation trigger.** Seed 222 "Do Not" and seed 180 state: when the only local fix to a compiler, borrow-checker or type-checker error is a structural workaround, stop and report the ownership or type conflict to the coordinator. With no coordinator, record the conflict in the change doc and resolve it within admitted scope, asking the operator only when the fix leaves that scope. This adds no approval or gate and does not replace seed 222's existing rule that deviating from a dominant pattern needs an operator decision.
6. **Review check in seed 221.** Add a conditional check for compiler and type-checker workarounds, applying when the change touches a statically checked language. It asks whether each new copy, check-out, runtime-checked cell or unchecked cast works around the data design; copies in loops or request paths need a stated reason; assess several workarounds on one type together and raise a finding when their combined design or cost is unsupported, even if each looks acceptable alone. It allows a reasoned N/A and points to the existing "Suppressed failures" check for suppressions instead of repeating it.
7. **Seed 212 follows the same split.** The generic checks added by `2362b-bug performance-reviewer-seed-ships-wavefoundry-internals` cover allocation per item or request, buffer copies across threads, thread or runtime creation per operation, data reshaped twice and lock hold times. This change adds one short Rust section naming the Rust forms of those costs. Because the renderer copies seed 212 word for word, the section is present in every project's reviewer doc and is worded to apply only when the code under review is Rust.
8. **Ports and rewrites in seed 170.** When a change ports code between languages or rewrites a module, the change doc states the ownership and data model, the hot paths and what "equivalent" means, within its existing sections. Tests and replay hashes prove behaviour, not design quality, and the doc says so. No new required heading and no lint rule.
9. **Lint candidates are opt-in.** The all-stacks text states the rule for every language: an agent may propose a lint that catches these workarounds but never enables it automatically or without explicit operator direction. As the Rust example, the Rust block lists `redundant_clone`, `implicit_clone`, `needless_collect`, `large_types_passed_by_value` and `too_many_lines` as candidates. The agent checks each lint's group on the project's pinned toolchain; the seed states no group.
10. **Delivery.** Seed 160 generates `docs/agents/software-engineer.md` only when it is absent and has no rule that refreshes an existing one. Add a separate seed 160 rule, leaving the existing changed-carrier sentence untouched, that merges changed seed 222 guidance into an existing `docs/agents/software-engineer.md` and changed seed 180 guidance into an existing `docs/prompts/implement-change.prompt.md`, preserving project additions. Naming destinations or creating only missing files does not satisfy this requirement. Update this repository's rendered implement-change, implement-wave, plan-change and upgrade prompts by the seed-first workflow, and the changelog. A software-engineer role doc for a project without Rust has the generic rules and no Rust block; reviewer docs copied word for word from seeds 212 and 221 carry short sections that apply only when the reviewed code is in the named language.

## Scope

**Problem statement:** No builder, reviewer or planning seed addresses compiler-appeasing workarounds, and Rust projects get no stack guidance.

**In scope:**

- `.wavefoundry/framework/seeds/222-software-engineer.prompt.md`, `221-code-reviewer.prompt.md`, `212-performance-reviewer.prompt.md`, `180-implement-change.prompt.md`, `170-plan-change.prompt.md`, and seed 160's role-doc guidance
- This repository's rendered `docs/prompts/` copies of implement-change, implement-wave, plan-change and upgrade-wavefoundry, and `docs/agents/` role docs where the all-stacks text applies
- Focused seed-content tests and the changelog

**Out of scope:**

- Go, Swift and C or C++ blocks; the report names them as missing but asks only for Rust
- Seed 080, any lint or sensor, and any automatic lint enablement
- A new change-doc section, approval, gate or review lane
- Rewriting existing Python, JVM, C# or TypeScript blocks beyond the one-line examples

## Acceptance Criteria

- [x] AC-1: Seed 222 carries the six generic rules of Requirement 3 in its all-stacks text, lists Rust detection from `Cargo.toml` and `*.rs`, carries a Rust block marked as conditional on Rust that holds only Rust constructs (the extracted block contains none of the six generic rule sentences and names no other language), and instructs including a block per detected language when more than one is substantial. A test over the seed fails on the current text.
- [x] AC-2: The escalation trigger appears in seed 222 "Do Not" and in seed 180, and in this repository's rendered implement-change and implement-wave prompts. Both seeds state that it adds no approval. A test fails when either seed lacks it.
- [x] AC-3: Seed 221 carries the new check with an applies-when condition and an N/A path, and references the "Suppressed failures" check instead of restating it. Seed 212 carries a Rust section worded to apply only when the reviewed code is Rust, containing none of the generic check sentences. Tests fail on the current text.
- [x] AC-4: Seed 170 and the rendered plan-change prompt ask for the ownership and data model, hot paths and the meaning of "equivalent" for ports and rewrites, state that parity checks do not prove design quality, and add no required heading. The plan template and docs lint are unchanged.
- [x] AC-5: The opt-in lint rule is stated for all stacks, and the Rust lint candidates appear only as proposals with the instruction to check groups on the pinned toolchain; seed 080 is unchanged and nothing enables a lint.
- [x] AC-6: Seed 160 explicitly requires merging changed seed 222 and seed 180 guidance into the existing software-engineer role and implement-change prompt, preserving project additions. A test checks this existing-document merge obligation rather than destination names alone, fails on the current seed 160 text, and leaves the existing changed-carrier pin passing. This repository's rendered software-engineer role doc contains the generic rules and no Rust block. The changelog names each edited seed. The documents this change edits validate, and the change's own tests pass.

## Tasks

- [x] Open `seed_edit_allowed`; edit seeds 222, 221, 212, 180, 170 and 160; close the gate.
- [x] Refresh the rendered prompts and role docs in this repository.
- [x] Add seed-content tests; update the changelog.
- [x] Run focused tests and docs validation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed text | implementer | 2362b | Seed 212's Rust section needs the generic checks and section structure |
| Rendered copies and tests | implementer | seed text | Seed-first |
| Verification | independent reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/seeds/222-software-engineer.prompt.md`, `.wavefoundry/framework/seeds/221-code-reviewer.prompt.md`, `.wavefoundry/framework/seeds/212-performance-reviewer.prompt.md`, `.wavefoundry/framework/seeds/180-implement-change.prompt.md`, `.wavefoundry/framework/seeds/170-plan-change.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/implement-change.prompt.md`, `docs/prompts/implement-wave.prompt.md`, `docs/prompts/plan-change.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/agents/software-engineer.md`, `docs/agents/code-reviewer.md`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Prompt text and tests only; no module boundary, data flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reporting project gets Rust guidance at all |
| AC-2 | required | The builder stops before the workaround, where it is cheapest |
| AC-3 | required | Review can find what the builder missed |
| AC-4 | important | Ports are where the failure is most likely |
| AC-5 | important | Keeps lint rollout a project decision |
| AC-6 | required | Existing projects receive the guidance at upgrade, and a non-Rust builder doc gets no Rust block |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-11 | Planning only. Verified five of the report's six gap claims against the seeds. The sixth differs: seed 221 already has a "Suppressed failures" check, and seed 080 is the docs gate. No parked plan covers this. Lint group membership is `unverified` and deliberately left out of the seed. | `grep` of seeds 080, 170, 180, 212, 221, 222; `wf_list_plans` |
| 2026-11-11 | Authorized bounded readiness repair: made AC-6 require changed-guidance merges into existing documents; qualified diagnostic-driven cost and aggregate-workaround rules, preserved existing language expertise, and clarified operator-owned lint enablement. | Independent Review plan; QA-RDY2-1; parent authorization |
| 2026-11-11 | Readback: extend all-stack ownership/design guidance, detected-stack Rust examples, conditional reviewer checks, escalation and port-planning instructions; merge them into existing carriers. Before: borrow errors invite isolated workarounds. After: builders explain justified costs and report structural conflicts within existing authority. AC-1–6; six seeds, local carriers, tests and changelog; no new gate, automatic lint or runtime feature. | Current amended plan and source readback |
| 2026-11-11 | Thought: apply the readied guidance through seeds and existing authored carriers, then verify actual missing-role delivery and negative controls. Observe: six seeds and local carriers updated; local performance-specific checks retained; no renderer, lint, template or runtime changes. Gapfill: targeted Python replacements performed bulk mechanical Markdown edits after MCP reads. | Scoped diff; baseline seeds in disposable work |
| 2026-11-11 | Observe: eight new guidance tests and the existing changed-carrier pin pass; eight tests also pass under the second profile with no skips. Actual missing-role renderer exercised. Original six seeds fail the changed contract checks; leaked-module and removed-lock-cost mutants are detected. Full docs validation passes; both edit gates closed. | `test_language_guidance.py`; `TechdocsCarrierLiteralPinTests.test_upgrade_carriers_pin_merge_safe_project_prompt_reconciliation`; disposable focused logs |
| 2026-11-11 | CODE-DEL-1 repair: both independent reviewers showed that adjacent seed 160 bullets could lend words to the merge oracle. The test now isolates one owning bullet and deletes each new rule for all four destinations. Eight focused tests pass; no shipped guidance changed. | `assert_existing_merge`; `test_upgrade_requires_existing_document_merge_not_names`; repair cycle 3 |
| 2026-11-11 | Observe: repaired upgrade assertions pass all eight tests under the second profile with zero skips; code reverification and docs-contract delivery approval are current. QA independently checks the same repair before final suite freeze. | `guidance-second-repaired.log`; typed review ledger |
| 2026-11-11 | Integration finding: full suite ran 12,822 tests with one existing Readback carrier identity failure; no green receipt. The new paragraph was inside the extracted local Readback block. Moved it before Readback in both local implement prompts without changing the test or seed contract. Eight guidance tests and all three BriefingLoopCarrierTests now pass. Focused selection had checked the upgrade pin but missed the adjacent briefing-carrier group; include that group in final verification. | INTEGRATION-DEL-1; full-suite.log; repair cycle 4 |
| 2026-11-11 | Final verification: canonical suite passes 12,822 tests across 249 files, 12 reported skips, 604.553 seconds (exit 0). Required delivery approvals are current; all readiness and delivery findings are terminal. No source or review input changed during the final run. Field effectiveness, native Windows and full release-profile qualification remain unverified. | Framework test receipt; typed ledger; `full-suite-final.log` in disposable work |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-11 | Deliver guidance in the builder, reviewer, implement and plan seeds; no sensor or gate. | Replay: an agent meeting a borrow error now has a stop-and-report rule, and a reviewer has a check that counts workarounds per type. The mechanism advises; a reviewer finding is typed and triaged, which is what makes someone act. It will flag legitimate cheap copies (hence the one-line reason) and will miss reviewers with weak Rust knowledge. Success is measured by the reporter's eight upgrade checks and its next port. | A lint or sensor for workarounds: cannot tell a justified copy from an appeasing one and breaks the opt-in rule. Rust block only, no escalation or review check: leaves the habit uncaught when the builder ignores the block. |
| 2026-11-11 | Operator direction: make guidance generic where it applies beyond Rust. | Ownership, hot-path and cohesion rules hold in any language, so they go in the all-stacks text and every project receives them; language blocks keep only their own constructs. | Rust-only blocks as first drafted: other stacks would miss rules that apply to them. |
| 2026-11-11 | Readiness primer repair: add seed 222 to seed 160's changed-carrier rule and cover implement-wave. | The tree confirms an existing software-engineer role doc is never refreshed, and implement-wave is the coordinator's carrier for seed 180. | Leave delivery to the generic stale rule. |
| 2026-11-11 | CODE-RDY-1 repair: the Rust section in seed 212 is a review-time condition, present everywhere. | The renderer copies seeds 212 and 221 word for word into missing role docs, so "no Rust text in non-Rust projects" can hold only for the agent-generated software-engineer doc. A two-line conditional section costs little. | Strip blocks in the renderer: new mechanism for a prose change. |
| 2026-11-11 | Keep a separate review check instead of widening "Suppressed failures". | The primer's alternative is smaller, but it loses the per-type count, which is the part most likely to catch a rationalized workaround. | Widen the existing check. |
| 2026-11-11 | Put lint candidates in the Rust block, not seed 080. | Seed 080 defines the docs gate; language lints do not belong there. | Seed 080 as requested: mixes two unrelated enforcement topics. |
| 2026-11-11 | Ports and rewrites use existing change-doc sections. | Plan-change guidance elsewhere avoids new mandatory sections; a required heading would need template and lint work for a rare case. | A new required section: more mechanism than the case needs. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Over-escalation: every copy becomes a stop | The trigger applies only when a structural workaround is the only local fix; a one-line reason clears a legitimate one |
| Prompt growth dilutes existing guidance | Six generic rules; new workaround additions take one or two lines per applicable language block, preserving existing expertise text |
| Guidance is delivered but ignored | Review check in seed 221 is the backstop; field check after release |
| Including several stack blocks bloats mixed-project role docs | Only languages with substantial code and an existing block are included |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
