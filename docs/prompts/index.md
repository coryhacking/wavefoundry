# Prompt Surface Index

Owner: Engineering
Status: active
Last verified: 2026-04-30

Public shortcut phrase catalog for Wavefoundry. See `AGENTS.md` for the routing table.

## Operating Rules

This prompt surface follows `.wavefoundry/framework/seeds/020-run-contract.prompt.md` as the authoritative run contract. Key behavioral rules:

- **Scoped-work triage:** classify by risk, blast radius, and lifecycle impact before proceeding. Lightweight means compact output *within* the lifecycle checkpoints that apply per `AGENTS.md` — not a skipped document/admit/Prepare-wave path when those gates apply. Complex/high-stakes and always-gated work requires full reasoning depth and lifecycle gates.
- **Brownfield pattern detection:** detect dominant patterns before implementing; follow them; surface significant problems with rationale before deviating; no silent divergence.
- **Surface assumptions explicitly;** prefer the smallest correct change after pattern obligations; diagnose before retrying; prefer one clarifying question over a wrong assumption; verify changes actually solved the problem.
- **Full lifecycle before code:** document → admit → Prepare wave. See `AGENTS.md` **Stage Gate (repository code)**.

## Public Commands

| Phrase | Purpose | Doc |
|--------|---------|-----|
| **Init wave framework** | Initialize Wave Framework in a target repository | `docs/prompts/install-wavefoundry.md` |
| **Enable Wavefoundry MCP** | Register the local MCP server in Claude Code, Cursor, Junie, Copilot, Codex, or Air | `docs/prompts/install-wavefoundry.md#mcp--wavefoundry-server` |
| **Upgrade wave framework** | Upgrade Wave Framework in a target repository | `docs/prompts/upgrade-wavefoundry.md` |
| **Plan feature** | Author a consolidated change document | `docs/prompts/plan-feature.md` |
| **Create wave** | Create a wave record | `docs/prompts/create-wave.md` |
| **Add change to wave** | Admit a change doc into the active wave | `docs/prompts/add-change-to-wave.md` |
| **Remove change from wave** | Remove an admitted change from the wave | `docs/prompts/remove-change-from-wave.md` |
| **Prepare wave** / **Ready wave** | Confirm readiness; validate/repair change-doc placement; AC priority | `docs/prompts/prepare-wave.md` |
| **Implement wave** | Coordinator-managed multi-change implementation loop | `docs/prompts/implement-wave.md` |
| **Implement feature** | Single-change docs-first implementation | `docs/prompts/implement-feature.md` |
| **Pause wave** | Park session state in handoff artifact | `docs/prompts/pause-wave.md` |
| **Review wave** | Run required review lanes with AC reconciliation | `docs/prompts/review-wave.md` |
| **Close wave** | Finalize wave with closure reconciliation | `docs/prompts/close-wave.md` |
| **Finalize feature** | Single-change closure path | `docs/prompts/finalize-feature.md` |
| **Interrogate this plan** | Stress-test a change doc before admission | `docs/prompts/interrogate-plan.md` |

## Wavefoundry Maintainer Commands

| Phrase | Purpose | Doc |
|--------|---------|-----|
| **Package Wavefoundry** | Build framework zip distribution | `.wavefoundry/framework/seeds/240-package-wavefoundry.prompt.md` |
| **Migrate to Wavefoundry** | Migrate a target repo from legacy layout | `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` |

## Legacy Aliases

The following phrases are accepted for backwards compatibility but redirect to primary commands:

| Legacy Phrase | Routes To |
|--------------|----------|
| Init wave context | Init wave framework |
| Upgrade wave context | Upgrade wave framework |
| Install wave framework / Install wave context | Init wave framework (greenfield) or Upgrade wave framework (already seeded) |
| Package wave framework / Package wave context | Package Wavefoundry |

## Usage Notes

- **Full lifecycle required before code:** Every non-trivial code change needs a change doc, wave admission, and a clean **Prepare wave** before implementation. See `AGENTS.md` **Stage Gate (repository code)**.
- **Implement wave vs Implement feature:** Use **Implement wave** for multiple admitted changes; use **Implement feature** for a single docs-first change.
- **Concurrency and protected surfaces:** See `docs/prompts/agent-routing-concurrency.md` for read-only vs write-owning lane rules.
- **Stress-testing plans:** After **Plan feature**, use **Interrogate this plan** to walk unresolved decision branches before admission.
- **Wavefoundry self-hosting:** When editing framework seeds, use **Package Wavefoundry** to produce a distribution and **Upgrade wave framework** in a target repo to consume it.

## Internal Agent-Oriented Prompt Bodies

Supporting agent-oriented prompt bodies live under `docs/prompts/agents/`. These are checked-in context helpers and are not listed as public commands.
