# Journal — Planner

Owner: Engineering
Status: active
Last verified: 2026-05-02

Actor: planner
Schema version: 1.0
Last distilled: 2026-04-28

## Operating Identity

- Role: planner — the agent role responsible for discovery, change document authoring, and pre-admission interrogation on the Wavefoundry repository.
- Responsibilities include: scoping change docs using `docs/plans/plan-template.md`, surfacing affected architecture docs, generating lifecycle IDs, and making assumptions explicit before admission.

## Salience Triggers

- **High:** A discovery finding invalidates a planning assumption shared in a prior session — journal immediately; do not proceed on the invalidated assumption.
- **High:** An MCP tool contract change is being planned without `docs/specs/mcp-tool-surface.md` existing — this is a Level 3 blocker.
- **Medium:** A new architectural constraint discovered during planning affects the Affected architecture docs section — surface before admission.
- **Low:** Operator provides a scope directive that changes the planning approach mid-session — record the directive and the rationale.

## Distillation

- **code_patterns is not yet authoritative:** `docs/repo-profile.json` `code_patterns` status is `insufficient_history`. When planning changes to `.wavefoundry/framework/scripts/`, detect patterns by reading the existing scripts directly rather than relying on the profile field.
- **MCP spec is a prerequisite for MCP implementation:** Any wave touching MCP tool contracts requires `docs/specs/mcp-tool-surface.md` to exist before Prepare wave can pass. If this file is missing, record it as a Level 3 blocker in the change doc Risks section.

## Active Signals

- None. This journal was seeded at framework install with no prior wave history.

## Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` and the lesson being promoted (e.g., `code_patterns` semantics once they stabilize).

## Retirement And Supersession

- No entries are retired at init.
- Retire the `code_patterns` lesson once real implementation waves have run and the profile is updated to reflect stable patterns.
- Retire the MCP spec prerequisite lesson once `docs/specs/mcp-tool-surface.md` is created and validated.

## Governance

- No secrets, credentials, or PII in journals.
- Sensitive planning findings: redact and note the secure channel.
- Review: distill at wave closure; promote repeated tradeoffs to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle to keep the journal load-bearing.

## Active Watchpoints

- **Watchpoint:** `docs/repo-profile.json` `code_patterns` status is `insufficient_history`. Until real implementation waves complete and patterns stabilize, do not cite code_patterns as an authority — inspect the actual scripts for patterns at planning time.
- **Watchpoint:** `docs/missing-docs.md` lists `docs/specs/mcp-tool-surface.md` and two ADRs as gaps. Any change doc touching MCP tool contracts or major architectural decisions must note these gaps in the Risks section until the missing docs are created.
- **Watchpoint:** Factor 13 (API first) requires `docs/specs/mcp-tool-surface.md` to exist before MCP implementation begins. A planning pass that admits an MCP implementation change without this spec doc must be blocked at Prepare wave.
