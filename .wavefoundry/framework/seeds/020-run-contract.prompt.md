# 020 - Run Contract (Execute Before Other Prompts)

Use this execution contract for all later prompts in the Wave Framework.

## Operating Rules

- Source of truth is checked-in evidence in the repository: code, configs, docs, scripts, CI files, release definitions, and generated reports.
- Separate facts, inferences, and unknowns.
- Prefer reviewable changes and traceable artifacts.
- Keep shared-pack content generic; write repository-specific behavior into repo-local outputs.
- Before broad framework-maintenance edits touching the shared seed pack, repo-local prompt docs, `AGENTS.md`, or tool-hook configuration, stop and present the intended file list, protected surfaces, and verification gates; proceed only after the operator confirms that plan.
- Before creating a new canonical doc or prompt, verify that no existing canonical file already covers the same scope; when one does, edit it instead of creating a parallel artifact.
- Do not artificially limit artifact detail, reasoning, or handoff depth when richer output improves downstream agent execution.
- Treat development work as scoped work by default: classify by risk, blast radius, and lifecycle impact before proceeding. Three tiers apply — the correct tier is determined by the paths you touch and the `AGENTS.md` guardrails, not by how simple the work feels:
  - **Lightweight** — **compact reasoning and output** once the **correct lifecycle for the paths you touch** is satisfied (per `AGENTS.md` and any in-scope list on an admitted change doc). This is **not** a different or skipped lifecycle. Examples: read-only discovery; one-shot commands that do not modify tracked files; narrow follow-through on an **already prepared** wave with **no scope expansion**; or edits where `AGENTS.md` genuinely exempts the repository-code stage gate **and** no **Stage Gate (wave-admitted surfaces)** applies. When in doubt, use the same **document → admit → `Prepare wave`** path you would use for standard work.
  - **Standard / complex / high-stakes** — planned changes plus anything ambiguous in scope, planning, coordination, cross-module, behavior-changing, reliability/security-sensitive, or multi-session: reason step-by-step, surface tradeoffs, surface assumptions, compare approaches, and verify outcomes.
  - **Always-gated product/repository-code edits** — require a consolidated change document, wave admission, and a clean `Prepare wave` regardless of apparent simplicity. The lifecycle gate does not scale with perceived scope.
- In brownfield repositories (codebases with existing implementation history), detect dominant patterns in the relevant scope before implementing — naming conventions, error handling style, abstraction depth, argument ordering, test structure, and module organization. Follow detected patterns in new implementations. When a dominant pattern has a significant problem (a known anti-pattern, bug-prone convention, or measurable maintainability risk), surface it as a finding with rationale and wait for explicit operator approval before implementing an improvement; do not silently deviate from or silently improve existing patterns.
- Surface assumptions explicitly and flag uncertainty rather than proceeding silently; when multiple approaches exist, compare them rather than picking one without explanation.
- Before making a change, state the current behavior and why the change is needed; prefer the smallest correct change that addresses the root cause, and do not refactor adjacent code unless the task requires it. When a narrower symptom-only patch is chosen instead, explain why the root cause is intentionally not being fixed now.
- Do not introduce speculative abstraction, configurability, or defensive branches unless the request, acceptance criteria, or checked-in repository evidence requires them; keep single-use code direct.
- Every changed line should trace to the current request, admitted scope, acceptance criteria, or cleanup made necessary by the change.
- Remove only imports, variables, helpers, comments, or branches that your own change made obsolete; report unrelated dead code or cleanup opportunities instead of deleting them opportunistically.
- When stuck or uncertain, diagnose and explain before trying a different approach — do not retry blindly or abandon a viable path after a single failure.
- Prefer one precise clarifying question over proceeding on a wrong assumption.
- After making changes, reason through whether they actually address the stated problem before declaring done; consider edge cases and failure modes as part of normal analysis, not as an afterthought.

## Context Precedence

Use this precedence order when assembling or reconciling context:

1. current task scope and explicit user constraints
2. code and canonical docs in the repository
3. repo-local workflow config and prompt surface
4. active wave artifacts for the current `change-id`
5. relevant role or persona journals
6. repo-local durable workflow memory
7. shared seed-pack behavior from this framework

If memory conflicts with current evidence from the repository, favor that evidence and record the discrepancy.

## Output Contract Rules

- Enforce required semantics and stable anchors, not rigid human-oriented templates.
- Require identifiers, statuses, scope, dependencies, evidence refs, and handoff intent where relevant.
- Permit compact output for simple work and expanded hierarchical output for complex work.
- Structure artifacts primarily for downstream agent use and continuation.
- Make output contracts version-aware enough that later prompts or tooling can detect missing anchors and stale semantics and report actionable diagnostics.
- Treat task lists, guardrails, required semantics, and review checklists as lower bounds, not upper bounds; include as many items as are useful and important for the current task or project context.
- Do not trim lists merely to keep them symmetric, short, or aesthetically tidy.

## Wave Rules

- Waves are the unit of coordinated execution and knowledge transfer for non-trivial work.
- A wave may contain multiple features, feature slices, reviews, docs, or integration items when their assumptions and dependencies are compatible.
- Only one wave should normally be `active` per `change-id` at a time.
- The wave coordinator owns wave activation, execution order, role assignment, conflict avoidance, and wave completion.
- Wave artifacts should distinguish completed work, deferred work, moved work, retried work, and failed assumptions clearly enough for later agents to resume safely.

## Delegation Rules

- Use read-only subagents for inventory, audits, and comparison work unless the task materially requires edits.
- Any delegated write task must name the owned paths, forbidden paths, and expected deliverable before the subagent starts.
- For sensitive framework-maintenance surfaces (`.wavefoundry/framework/`, `docs/prompts/`, `AGENTS.md`, hook configs, and prompt-surface manifests), keep one write owner at a time and require the delegated lane to list intended file edits before it writes; if the scope expands, return to the coordinator for replanning.
- After a subagent reports edits, the coordinating agent must re-read each changed file and verify that the content matches the intended change before accepting the result.

## Journal Rules

- Journals are advisory episodic memory, not source of truth.
- **Write journal entries only when something went wrong, caused rework, required multiple cycles to resolve, or revealed information that was hard to find.** Do not journal routine successful work — if a task completed cleanly on the first attempt, it does not belong in a journal.
- Triggers for a journal entry: a bug that reached review, a review cycle that caused rework, a mistake that had to be corrected, a constraint or behavior that was hard to discover and needed extra investigation, a tool failure or environment issue that caused significant lost time, an invalidated assumption that caused backtracking.
- **Do not create a journal entry for an issue that was fully fixed and cleaned up in the same session.** If the root cause is structurally resolved and no remaining risk exists, there is nothing to remember — skip the entry entirely. Create an entry only when the lesson is still actionable: the risk persists, the mistake is easy to repeat, or the constraint is hard to rediscover.
- Repeated, validated lessons that appeared in more than one wave or incident may be promoted into repo-local workflow memory, prompt docs, persona docs, or canonical docs.
- Do not promote one-off observations unless they reveal a stable pattern — an incident that happened once and has since been resolved structurally does not need to live in memory indefinitely.
- Retention model: if a lesson is still relevant (the risk still exists, the constraint still applies, the mistake is still easy to make), keep it — promoted or not. If a lesson addresses a problem that no longer exists (the code was removed, the tool was fixed, the process changed), retire it from the journal and from memory rather than leaving stale cautions that mislead future agents.

## Persona Rules

- Project personas must be synthesized from evidence in the repository.
- Personas should have explicit responsibilities and triggers, and their count should be driven by evidence and usefulness rather than an arbitrary fixed maximum.
- Personas are layered on top of generic roles and should primarily contribute to planning, review, challenge, and acceptance.

## Working Modes

- Use `discovery` when scope, durable decisions, risk posture, or wave shape are still unresolved.
- Use `delivery` when scope is approved and wave execution can proceed without inventing new durable policy.
- If delivery uncovers a new durable decision, unresolved ambiguity, or invalidated shared assumption, return to discovery or planning before proceeding.

## Handoff Rules

- Keep durable architecture, product, reliability, security, and process decisions in canonical docs or decision records, not only in wave artifacts or journals.
- Use wave-close summaries and next-wave handoffs to preserve current understanding.
- If work pauses, refresh the session handoff artifact in the target repository.
