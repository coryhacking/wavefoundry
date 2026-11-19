# Implement Spec

Owner: Engineering
Status: active
Last verified: 2026-11-11

Shortcut: **`Implement spec`** | Alias: **`Implement change`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-spec.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort per implementation or verification task; accept changes only after coordinator integration checks. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Single-change docs-first implementation path. Use when one admitted change needs implementation without multi-workstream coordination.

## Pre-condition

Repository code stage gate must pass:
1. Consolidated spec exists and is admitted into a wave
2. Prepare wave has passed cleanly; declared review-enabled waves require the typed `council-readiness` approval on the current receipt. Legacy prose-verdict and review-disabled behavior are preserved.

If any step is missing, stop and route back to **Plan spec**, **Create wave**, **Add spec to wave**, or **Prepare wave**.

**Structural workarounds.** When the only local fix to a compiler, borrow-checker or type-checker error is a structural workaround, stop and report the ownership or type conflict to the coordinator. With no coordinator, record the conflict in the spec and resolve it within admitted scope; ask the operator only when the fix leaves that scope. This adds no approval or gate and preserves the existing operator decision for deviation from a dominant pattern.

**Readback before editing:**

Before the first implementation edit of each change, record a concise `Readback:` in its existing Progress Log and surface its substance to the operator: intended behavior, relevant ACs, important scope boundary, and expected affected files. Include one before/after example for nontrivial behavior changes; keep clear tasks brief. Briefly relate the chosen work to Product Intent (or the wave Objective); name how the mechanism serves the intended outcome. Intent does not authorize broader scope or silent contract changes: preserve existing requirement-amendment, re-Prepare and operator-authorization rules.

Correct an agent-only misreading directly from the established requirement. Route an actual contract contradiction or missing consequential decision back to planning under existing escalation rules, pausing only dependent work. A readback correction is not automatically Level 3 and adds no second approval. Refresh only materially changed understanding after scope changes or handoff; do not repeat an unchanged readback or create another artifact.

## Disposable work

Use the lifecycle-reported `.wavefoundry/work/<wave-id>/` and include it in coordinator briefs. Follow seed 180’s **Disposable work** lifetime and seed 209’s preservation duties; new durable approvals must not depend solely on scratch paths.

Write every file you create for a wave, including coordinator briefs, logs, captured test output and build output, inside that wave's own work folder, in a child folder when that helps; never write a file directly in `.wavefoundry/work/`. Before the wave exists, keep the content in task context until a lifecycle call reports the work area. `wf_audit` and close report files and links left directly in the work root as the advisory `work_root_loose_files`. If you wrote such a file for a wave, move it into that wave's folder while the wave is open, or delete it. Leave any other loose file in place, including one you are not sure you wrote (a name that starts with a wave id does not prove who wrote it), and report it to the operator, who decides. Never move a file you did not write into a wave's folder: close removes that folder with everything in it.

## Steps

1. Read the spec at `docs/waves/<wave-id>/<change-id>.md` and the AC priority table.
2. Implement per Requirements and Acceptance Criteria.
3. Follow `docs/repo-profile.json` `code_patterns` when populated.
4. Routine documentation edits already receive automatic incremental changed-set lint. After implementation: run framework tests, then prefer the full MCP **`wf_validate_docs`** (and **`wf_garden_docs`** if metadata needs refresh). **CLI fallback:** `wf docs-gardener && wf docs-lint` when MCP is unavailable.
5. Complete required review lanes before closing.
6. Continue the lifecycle: **Review wave**, then optionally **Close spec** (`docs/prompts/close-spec.prompt.md`) to mark this change `complete` once review has cleared it, then **Close wave**, the only wave close. The full path is Plan spec -> Create wave -> Add spec to wave -> Prepare wave -> Implement spec -> Review wave -> Close spec (per change, optional) -> Close wave.
7. If the operator requests a follow-up that still belongs to the current wave and the scope fits an admitted change, update that existing change's Acceptance Criteria and Tasks instead of opening a new change; create a new change only when the new work is materially different or needs separate tracking.

## Guardrails

Follow seed 209's Continuation And Qualification Discipline: finish material verification-input edits before the canonical suite. Validated routine ledger/projection updates and normalized progress/status/completion may continue without another suite or reviewer cycle solely for recording them. Use the canonical Progress Log during a run; the standalone session handoff and other documentation outside the wave under test may also change during it, as seed 209 describes. Reuse only a successful receipt matching current inputs; material changes, actual findings and required reviews retain their existing effects.

- Prefer the smallest correct change; do not refactor adjacent code unless required.
- After changes, verify they actually address the stated problem.
- Stage gate does not scale with perceived scope — always follow the lifecycle.
