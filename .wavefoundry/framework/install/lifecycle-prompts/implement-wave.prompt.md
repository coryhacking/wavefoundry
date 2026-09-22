# Implement Wave

Owner: Engineering
Status: active
Last verified: {{generated_at}}

Shortcut: **`Implement wave`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort per implementation or verification task; accept changes only after coordinator integration checks. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Open a readied wave and execute all admitted changes through a focused
implement and verify loop, then hand the completed evidence to `Review wave`.

## Readiness handoff

Before the first code edit, confirm `Prepare wave` completed and its current
typed readiness approval is recorded. Prepare owns the failure-first critique
and packet-completeness decision; implementation does not repeat that review.

**Readback before editing:**

Before the first implementation edit of each change, record a concise `Readback:` in its existing Progress Log and surface its substance to the operator: intended behavior, relevant ACs, important scope boundary, and expected affected files. Include one before/after example for nontrivial behavior changes; keep clear tasks brief.

Correct an agent-only misreading directly from the established requirement. Route an actual contract contradiction or missing consequential decision back to planning under existing escalation rules, pausing only dependent work. A readback correction is not automatically Level 3 and adds no second approval. Refresh only materially changed understanding after scope changes or handoff; do not repeat an unchanged readback or create another artifact.

## Execution

1. Use repository-native navigation and the Wavefoundry code tools to identify
   ownership, callers, and established patterns before editing.
2. Implement only admitted scope and preserve unrelated working-tree changes.
3. Update AC and task checkboxes as evidence is produced.
4. Run focused tests after each bounded repair and the canonical project suite
   before delivery review.
5. Record findings when discovered during an exceptional named checkpoint or
   the later delivery review, record `repair_start` before mutation,
   repair immediately, and reverify in the currently open partial repair cycle.
   Advancing a cycle number is chronology, not a reason to delay the repair or
   summon another council.
6. Re-prepare only when scope, required contracts, architecture ownership,
   trust boundaries, or readiness semantics materially change.

## When the Wavefoundry MCP is attached

Before the first edit, call `memory_brief(context='pre_implementation', targets=[...])` for the files in scope. At completion, run full `wf_validate_docs` and resolve its findings. Delegate code work through a role-typed agent or carry the MCP-first navigation directive in the worker's prompt, checking its actual tools and allowlist.

Without MCP, follow the repository's documented navigation and validation fallbacks.

Follow seed 180's **Builder-lane allocation** for implementation lane selection on every host.

## Completion

Implementation is complete only when the admitted behavior, docs, tests, and
review evidence agree. It does not authorize commit, release, or wave closure.
