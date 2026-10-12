# Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-10-12

Shortcut: **`Implement wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-change.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort per implementation or verification task; accept changes only after coordinator integration checks. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose and readiness

Implement the admitted changes, then hand the evidence to **Review wave**. **Prepare wave** must have passed; declared review-enabled waves require the typed `council-readiness` approval on the current receipt, with legacy prose-verdict and review-disabled behavior preserved. Implementation consumes that authority without repeating the critique.

Activation enforces the single-OPEN invariant: pause any other OPEN wave before `wf_implement_wave` opens this readied wave.

**Readback before editing:**

Before the first implementation edit of each change, record a concise `Readback:` in its existing Progress Log and surface its substance to the operator: intended behavior, relevant ACs, important scope boundary, and expected affected files. Include one before/after example for nontrivial behavior changes; keep clear tasks brief.

Correct an agent-only misreading directly from the established requirement. Route an actual contract contradiction or missing consequential decision back to planning under existing escalation rules, pausing only dependent work. A readback correction is not automatically Level 3 and adds no second approval. Refresh only materially changed understanding after scope changes or handoff; do not repeat an unchanged readback or create another artifact.

## Execution

1. Orient per change with the code tools and the tool's `retrieval_posture` directive; follow seed 180's exploration contract and its unavailable-MCP fallback.
2. Follow seed 180's ReAct execution model; implement admitted scope only, follow `docs/repo-profile.json` `code_patterns`, and mark each completed AC and task in the completing pass with `wf_mark_ac` and `wf_mark_task`. When one change finishes before the others, `wf_close_change(wave_id, change_id, mode)` closes it to `complete` (dry-run first) and moves the dependents whose `Depends On:` names it to `ready`; the wave stays open and `Close wave` remains the only wave close.
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

Keep routine briefings, per-seat reports, probe captures, source baselines and green logs in task context or temporary storage outside the repository. Consolidate final outcomes and evidence in the existing wave/change records under seed 209's Review Artifact Discipline; preserve cited and unique proof, explaining retained exceptions inline in `wave.md`.

Consume successful typed-write continuation actions and confirm current readiness/delivery authority without repeating unchanged review or list calls. Finish material verification-input edits before the canonical suite; validated routine ledger/projection updates and normalized progress/status/completion may continue under seed 209's Continuation And Qualification Discipline. Use Progress Log during a run and update the standalone session handoff outside it. Routine recording alone does not require another suite or reviewer cycle; reuse only a successful receipt matching current inputs. Required lanes, focused independent repair review and final full docs validation remain unchanged. An operator-authorized close uses one canonical mutation; dry-run resolves uncertain checks and is not a compulsory extra gate.

Implementation is complete only when the admitted behavior, docs, tests, and review evidence agree. It does not authorize commit, release, or wave closure.

<!-- wavefoundry:review-policy:begin -->
## Review-policy implementation

Prepare Wave is the single readiness authority. Implementation consumes the
current shared delivery evaluator and never recreates a separate readiness
review gate.

Put test observations, repair progress, evidence locations and continuation
notes in the canonical `## Progress Log` or existing session handoff. Keep
weighed plan choices and material decisions in `## Decision Log`. Before or with
narration, amend the owning digested section for a change to scope, requirements,
acceptance, task meaning, priority, review targets or authority; the log may link
or summarize that edit, never substitute for it. Follow the existing re-Prepare
and affected readiness approval rules. Legitimate material decision receipt
rotation is intentional.

For example, "Reran tests on Windows; repair passed" belongs in Progress Log.
Changing who may approve a release artifact amends Requirements and any owning
review targets or authority section, with a weighed design choice in Decision
Log when needed. Guidance and existing review enforce authoring discipline;
they do not automatically discover semantic amendments hidden only in narration.
Use the canonical heading; unsupported or ambiguous Progress Log headings may
remain digested.

### Codex patch-write instructions

Treat `apply_patch` as a write regardless of wrapper spelling, including
`tools.apply_patch` inside `functions.exec`. Before invoking a patch, establish
all intended write paths from `*** Add File:`, `*** Update File:`,
`*** Delete File:` and `*** Move to:` headers. A move writes both the Update
source and Move-to destination; inspect and authorize both paths. For example,
`*** Update File: src/old.py` followed by `*** Move to: src/new.py` requires
both `src/old.py` and `src/new.py` to pass the existing stage gate and applicable
approval policy. Add and Delete destinations require the same checks.

Honor the repository stage gate and existing seed/framework approval policy
before invocation, including `seed_edit_allowed` and `framework_edit_allowed`
where applicable. Stop when intended write paths cannot be established. A patch
executed through a shell remains a write under these instructions.

This guidance reaches the profile-resolved Implement wave prompt through its
existing managed policy region and the `wf-implement-wave` skill pointer. It is
workflow-scoped instruction delivery, without native Codex enforcement or proof
of agent adherence. It does not automatically refresh existing root AGENTS,
universal startup instructions or single-change workflows.
<!-- wavefoundry:review-policy:end -->
