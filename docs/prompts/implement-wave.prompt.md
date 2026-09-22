# Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-09-22

Shortcut: **`Implement wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort per implementation or verification task; accept changes only after coordinator integration checks. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose and readiness

Implement the admitted changes, then hand the evidence to **Review wave**. **Prepare wave** must have passed; declared review-enabled waves require the typed `wave-council-readiness` approval on the current receipt, with legacy prose-verdict and review-disabled behavior preserved. Implementation consumes that authority without repeating the critique.

Activation enforces the single-OPEN invariant: pause any other OPEN wave before `wf_implement_wave` opens this readied wave.

**Readback before editing:**

Before the first implementation edit of each change, record a concise `Readback:` in its existing Progress Log and surface its substance to the operator: intended behavior, relevant ACs, important scope boundary, and expected affected files. Include one before/after example for nontrivial behavior changes; keep clear tasks brief.

Correct an agent-only misreading directly from the established requirement. Route an actual contract contradiction or missing consequential decision back to planning under existing escalation rules, pausing only dependent work. A readback correction is not automatically Level 3 and adds no second approval. Refresh only materially changed understanding after scope changes or handoff; do not repeat an unchanged readback or create another artifact.

## Execution

1. Orient per change with the code tools and the tool's `retrieval_posture` directive; follow seed 180's exploration contract and its unavailable-MCP fallback.
2. Follow seed 180's ReAct execution model; implement admitted scope only, follow `docs/repo-profile.json` `code_patterns`, and mark each completed AC and task in the completing pass with `wf_mark_ac` and `wf_mark_task`.
3. Follow seed 180's **Builder-lane allocation** and **Host-neutral orchestration** for lane selection and delegated work (`frontend-developer` for UI; `data-engineer` only where seed 050's database evidence renders that role).
4. Run focused tests per change and the canonical suite before delivery review; verify that the change addresses the stated problem.
5. Follow seed 209's typed authoring contract: the coordinator is the writing hand; record `repair_start` before mutation and obtain distinct fresh reverification, treating `recommended_fix` as a hypothesis to re-derive from the code.

- **Landing rule for guards** (seed 180/209, wave `1wuju`): a guard, validator member, carve-out, or tuning constant is landed only when a named test fails with it deleted or loosened; record the mutant and the failing test in the change doc's Progress Log before requesting review. A pin that passes for an unrelated reason is not a pin.
- **External blockers** (seed 209): when a gate is blocked by an artifact this wave does not own, present the exact fix and a yes/no decision to the operator in the same message that reports the block.

## Framework Script Changes

After framework script changes, run `python3 .wavefoundry/framework/scripts/run_tests.py`.

At every completion boundary, run full **`wf_validate_docs`** with MCP attached; use **`wf_garden_docs`** when metadata needs refresh. Without MCP, use `wf docs-gardener && wf docs-lint`. Fix failures before declaring implementation complete.

## Agent Memory Briefing

Before the first edit, call `memory_brief(context='pre_implementation', targets=[...])` with the files in scope — active memory records (fragile files, prior failed attempts, operator preferences) surface as capped, cited advisories. Treat a `needs_reverification` fragile-file advisory as a prompt to re-check the concern against current code before editing. `wf_prepare_wave` responses carry the same advisories for the admitted change set. Absence of records is not absence of risk.

## Completion

Implementation is complete only when the admitted behavior, docs, tests, and review evidence agree. It does not authorize commit, release, or wave closure.

<!-- wavefoundry:review-policy:begin -->
## Review-policy implementation

Prepare Wave is the single readiness authority. Implementation consumes the
current shared delivery evaluator and never recreates a separate readiness
review gate.
<!-- wavefoundry:review-policy:end -->
