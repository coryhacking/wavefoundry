# Fixture-fidelity rule in the harness seeds

Change ID: `1yd96-doc fixture-fidelity-harness-rule`
Change Status: `complete`
Owner: framework maintainer
Status: complete
Last verified: 2026-09-20
Wave: `1yd24 fixture-fidelity`

## Rationale

The sibling change gives this repository a canonical declared-wave fixture builder. That helper is framework-internal and ships nowhere: the packaged distribution excludes the test tree, so a target repository never sees it. The rule it embodies is not repository-specific, and every project running the harness can make the same mistake in its own fixtures.

Seed `209-agent-harness-core` already carries the closest rule: verification that reuses the implementation's own fixtures is correlated evidence and can only confirm the blind spots it already shares. The gap is one step earlier. A fixture the author writes BY HAND encodes the author's model of the contract, so when the defect is a wrong model, fixture and code agree and the test passes vacuously. That is a different failure from correlated evidence and it is not stated anywhere in the seeds.

Seed `239-qa-reviewer` carries the five conditions a reviewer checks before accepting a claimed test. Condition 2 already requires path reachability. Strengthen that existing condition with fixture setup and early-refusal precision, rather than adding a duplicate sixth condition. This is the failure shape behind how a wave `1y0h0` golden covering three fixtures came to exercise none of the spans it named.

## Requirements

1. Seed `209-agent-harness-core.prompt.md` gains a fixture-fidelity paragraph adjacent to the existing correlated-evidence rule: build fixture STATE through the canonical producers rather than by hand, because a hand-authored fixture encodes the author's model of the contract and cannot catch a defect in that model. It names the failure shape (fixture and code agree, test passes vacuously) and the remedy (call the real writer, creator, or lifecycle tool), while retaining deliberate negative/component/producer-contract inputs and independent expected-value oracles. Canonical producers provide setup fidelity, not an independent correctness oracle. It states the diagnostic-reading corollary: when a tool refuses, read the message, because a list of diagnostic codes is not a diagnosis.
2. Seed `239-qa-reviewer.prompt.md` strengthens existing condition 2, preserving the five-condition contract: canonical setup must reach the claimed path. A response that short-circuits on an earlier gate proves nothing about the span the test names, and a green test over such a fixture is the most expensive kind of false confidence.
3. Both edits are made under the `seed_edit_allowed` gate, opened immediately before and closed immediately after, per the framework's seed-edit contract.
4. Verify propagation through the existing consumer contracts, without changing renderer code: common carriers retain their canonical seed-209 protocol reference; a newly created QA role receives the updated seed-239 body; existing project-owned QA prose is preserved by regeneration. Explicitly sync this repository's QA role wording with the clarified seed rule outside generated regions. Run the renderer and parity checks while preserving unrelated generated drift. Do not claim automatic replacement of existing project-owned prose or direct embedding of seed 209. Presence tests prove the contract's availability, not agent adherence.
5. No lifecycle behavior, tool surface, or validator changes. This is guidance only.

## Scope

**Problem statement:** The fixture-fidelity rule exists only as this repository's hard-won habit; nothing carries it to the projects that run the harness.

**In scope:**

- The two seed edits, explicit self-hosted QA role guidance sync, and surface regeneration/consumer-contract checks.
- A claims-style pin so the rule cannot silently vanish from the seed.

**Out of scope:**

- The helper itself, which is the sibling change and is framework-internal.
- Any new evidence-integrity field or sixth condition; this clarifies existing condition 2 without changing the five-field protocol.
- Reviewer-seat prompts other than `239`.

## Acceptance Criteria

- [x] AC-1: Both seeds carry the new text, edited under an opened `seed_edit_allowed` gate that is closed again in the same session.
- [x] AC-2: A docs test pins the rule's presence in both seeds by a stable phrase, so a later seed rewrite that drops it fails rather than passing quietly. The test proves its known-bad against a mutated source string with the phrase removed.
- [x] AC-3: Public rendering in disposable target roots proves that common carriers reference canonical seed 209, fresh QA roles contain updated seed 239 guidance, and rerendering preserves existing project-owned QA prose. The self-hosted QA role explicitly carries the clarified rule, the renderer is run, and parity coverage passes. A seed-update/rerender check must not falsely claim replacement of an existing role body.
- [x] AC-4: Full docs validation passes and the framework suite is green.

## Tasks

- [x] Open `seed_edit_allowed`.
- [x] Add the fixture-fidelity paragraph to `209-agent-harness-core.prompt.md` beside the correlated-evidence rule.
- [x] Strengthen existing path-reachability condition 2 in `239-qa-reviewer.prompt.md`.
- [x] Close `seed_edit_allowed`.
- [x] Write the AC-2 presence pin with its known-bad.
- [x] Sync self-hosted QA guidance, run rendering, and verify seed-pointer, fresh-role, preserved-existing-role and parity contracts.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph

| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| seeds      | implementer | —          | both seed edits under the gate |
| pin        | qa          | seeds      | AC-2 presence test and its known-bad |
| render     | implementer | seeds      | surface regeneration and parity |

## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `.wavefoundry/framework/seeds/239-qa-reviewer.prompt.md`
- `.wavefoundry/framework/scripts/tests/`
- `docs/prompts/`

## Affected Architecture Docs

None. Seed guidance carries no architectural boundary change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The seed edit is the change |
| AC-2 | required  | Without a pin the rule is prose that a later rewrite drops silently |
| AC-3 | required  | An unrendered seed reaches no project, which defeats the purpose |
| AC-4 | required  | Standard change-local verification |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-18 | Change planned alongside `1yd25-debt`. Seed homes identified: `209` already carries the correlated-evidence rule the new paragraph sits beside, and `239` carries the five acceptance conditions the sixth joins | this document |

| 2026-09-20 | Readback: strengthen existing QA condition 2 and add producer-built setup guidance with independent oracle and deliberate-input exceptions. Thought: edit seeds under gate, sync local QA wording, then pin phrase deletion and actual renderer consumer contracts | AC-1 through AC-4; seeds 209/239, QA role, guidance tests |

| 2026-09-20 | Observe: seed edits completed with seed gate opened/closed in this session; local QA condition clarified. New guidance tests and renderer/platform suites passed: 231 tests in 5.774s. Eight phrase-deletion controls fail the same presence assertions; public renderer proves fresh239 copy, seed209 pointer, preserved existing body and explicit local sync. Renderer ran on repository with zero additional writes | test_fixture_fidelity_guidance.py; test_render_agent_surfaces; test_render_platform_surfaces; /tmp/1yd24-guidance-tests.log. Contract/transport proof only, not agent adherence |

| 2026-09-20 | Final integration: 9444 tests across117 files passed in281.625s with12 existing skips; fresh receipt independently recomputed by coordinator. Full docs validation passed with no errors; existing AC wording advisory remains nonblocking. All required ACs/tasks have evidence | run_tests.py; receipt inputs_hash `4decf445ea1e79f2584c875baea38b21ba8179d1aa445eb7abaa67b5107c6132`; delivery-evidence.md |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-18 | Extend `209` and `239` rather than author a new seed | Both rules have an existing home whose subject they continue; a new seed would separate the fixture rule from the correlated-evidence rule it completes | A dedicated testing-practice seed: more discoverable in isolation, but splits one argument across two documents and adds a surface to keep in sync |
| 2026-09-18 | Carry the diagnostic-reading corollary in the same paragraph | The two failures were observed together: hand-authored fixtures produce refusals, and reading only the diagnostic codes turns a one-run fix into four | State it separately in the implement seed: correct but loses the causal link that makes it memorable |

| 2026-09-20 | Strengthen existing QA condition 2 and preserve all five integrity fields; distinguish producer-built setup from independent assertions and deliberate test subjects | Current seed 239 already requires reachability, so a sixth condition would duplicate the rule and misstate the contract | Add sixth condition: rejected as redundant |

| 2026-09-20 | Readiness repair: describe the existing pointer/fresh-role transport and explicitly sync self-hosted QA prose | Both independent lanes reproduced that rerender preserves existing project-owned QA prose; seed 209 is referenced, not embedded | Expand renderer behavior: unnecessary production scope and risks overwriting target-owned guidance |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Seed prose grows without bound as each wave adds its lesson | The addition is two short passages placed inside existing rules rather than new sections, and it replaces no existing guidance |
| The presence pin becomes brittle against ordinary rewording | The pin keys on a short distinctive phrase rather than a sentence, following the existing claims-style pins |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
