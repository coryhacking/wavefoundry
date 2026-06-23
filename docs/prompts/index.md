# Prompt Surface Index

Owner: Engineering
Status: active
Last verified: 2026-06-17

The public catalog of shortcut phrases you can say to your agent. Each phrase routes to the documented prompt body for that command. See `AGENTS.md` for the agent-side routing table.

If you're new to Wavefoundry, the [README](../../README.md) walks the install path and a first wave end-to-end; this index is the reference for everything else.

## Operating principles

The behavioral rules below apply to every command in this catalog. They are summarized here so an agent reading this index has the contract in scope before invoking any phrase.

- **Triage by risk and blast radius before acting.** Compact output is fine for low-stakes work; full lifecycle gates still apply when the work crosses them.
- **Detect existing patterns before introducing new ones.** Surface a divergence with rationale rather than silently changing convention.
- **Surface assumptions; prefer the smallest correct change.** Ask one clarifying question rather than make a wrong assumption. Verify a change actually solved the stated problem.
- **Preflight every task.** Six points: evidence first, own the boundary, what breaks, order matters, state uncertainty, verify before declaring done.
- **Full lifecycle before code.** Change doc → wave admission → Prepare wave → first edit. See `AGENTS.md` **Stage Gate (repository code)** for the gate definition.

## Public Commands

| Phrase | Purpose | Doc |
|--------|---------|-----|
| **Init Wavefoundry** | Initialize Wave Framework in a target repository | `docs/prompts/install-wavefoundry.prompt.md` |
| **Start dashboard** | Start the local repository dashboard and open it in the browser | `docs/prompts/start-dashboard.prompt.md` |
| **Stop dashboard** | Stop the local repository dashboard for the current checkout | `docs/prompts/stop-dashboard.prompt.md` |
| **Restart dashboard** | Restart the local repository dashboard for the current checkout | `docs/prompts/restart-dashboard.prompt.md` |
| **Enable Wavefoundry MCP** | Register the local MCP server in Claude Code, Cursor, Junie, Copilot, Codex, or Air | `docs/prompts/install-wavefoundry.prompt.md#mcp--wavefoundry-server` |
| **Upgrade Wavefoundry** | Upgrade Wave Framework in a target repository | `docs/prompts/upgrade-wavefoundry.prompt.md` |
| **Plan feature** | Author a consolidated change document | `docs/prompts/plan-feature.prompt.md` |
| **Create wave** | Create a wave record | `docs/prompts/create-wave.prompt.md` |
| **Add change to wave** | Admit a change doc into the active wave | `docs/prompts/add-change-to-wave.prompt.md` |
| **Remove change from wave** | Remove an admitted change from the wave | `docs/prompts/remove-change-from-wave.prompt.md` |
| **Prepare wave** / **Ready wave** | Confirm readiness; validate/repair change-doc placement; AC priority | `docs/prompts/prepare-wave.prompt.md` |
| **Implement wave** | Coordinator-managed multi-change implementation loop | `docs/prompts/implement-wave.prompt.md` |
| **Implement feature** | Single-change docs-first implementation | `docs/prompts/implement-feature.prompt.md` |
| **Pause wave** | Park session state in handoff artifact | `docs/prompts/pause-wave.prompt.md` |
| **Review wave** | Run required review lanes with AC reconciliation | `docs/prompts/review-wave.prompt.md` |
| **Reopen wave** | Reopen a prematurely closed wave | MCP: `wave_reopen(wave_id)` |
| **Index build status** | Poll background index refresh progress | MCP: `wave_index_build_status(layer?)` — use after `setup_index.py --background-code` or any detached refresh |
| **Close wave** | Finalize wave with closure reconciliation | `docs/prompts/close-wave.prompt.md` |
| **Finalize feature** | Single-change closure path | `docs/prompts/finalize-feature.prompt.md` |
| **Interrogate this plan** | Stress-test a change doc before admission | `docs/prompts/interrogate-plan.prompt.md` |
| **Council review** / **Run council** | Two-phase adversarial council review on any artifact: red-team primer → fixed seats → synthesis | `docs/prompts/council-review.prompt.md` |
| **Archetype review** / **Archetype council** | Optional stance-based council review on text-precision / prose / naming / AC artifacts (Sun Tzu / Yoda / Spock / Marcus Aurelius / Feynman; swap Hemingway or Munger for the fifth seat). Complementary to Wave Council; does not record `wave-council-readiness` | `docs/prompts/archetype-council.prompt.md` |
| **Evaluate decision** | Red-team + council evaluation of an architectural decision or technology comparison; produces an ADR | `docs/prompts/evaluate-decision.prompt.md` |
| **Framework config review** / **Config review** | Removal-biased audit of the agent operating surface (AGENTS.md/CLAUDE.md root + per-folder, seeds, prompts, constraints, memory, doc-sync) → keep/revise/retire; recommended each major/minor upgrade | `docs/prompts/framework-config-review.prompt.md` |
| **Codebase cleanup review** / **Dead code review** | Code-reviewer's whole-codebase maintainability sweep — dead code, duplication, complexity, abandoned files, debt → keep/simplify/remove (graph-based, recommend-only, safe) | `docs/prompts/codebase-cleanup-review.prompt.md` |
| **Guru** | Ask a natural-language question about the codebase; returns cited answer, next-hop citations, and rank metadata (`final_rank`, `demoted`) | `docs/agents/guru.md` — MCP: `code_ask(question)` |

## Wavefoundry Maintainer Commands

| Phrase | Purpose | Doc |
|--------|---------|-----|
| **Package Wavefoundry** | Build framework zip distribution | `docs/prompts/package-wavefoundry.prompt.md` |
| **Migrate to Wavefoundry** | Migrate a target repo from legacy layout | `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` |

## Legacy Aliases

The following phrases are accepted for backwards compatibility but redirect to primary commands:

| Legacy Phrase | Routes To |
|--------------|----------|
| Init wave framework / Init wave context | Init Wavefoundry |
| Upgrade wave framework / Upgrade wave context | Upgrade Wavefoundry |
| Install Wavefoundry / Install wave framework / Install wave context | Init Wavefoundry (greenfield) or Upgrade Wavefoundry (already seeded) |
| Package wave framework / Package wave context | Package Wavefoundry |
| Ask codebase / Ask CIA / Code insight | Guru |

## Usage Notes

- **Full lifecycle required before code:** Every non-trivial code change needs a change doc, wave admission, and a clean **Prepare wave** before implementation. See `AGENTS.md` **Stage Gate (repository code)**.
- **Wave Council:** when `docs/workflow-config.json` `wave_review.enabled` is true, every wave also requires a council readiness pass during **Prepare wave** and a council delivery pass during **Review wave** / before **Close wave**. These are universal meta-review checkpoints and do not replace specialist lanes.
- **Implement wave vs Implement feature:** Use **Implement wave** for multiple admitted changes; use **Implement feature** for a single docs-first change.
- **Concurrency and protected surfaces:** See `docs/prompts/agent-routing-concurrency.prompt.md` for read-only vs write-owning lane rules.
- **Stress-testing plans:** After **Plan feature**, use **Interrogate this plan** to walk unresolved decision branches before admission.
- **MCP freshness workflow:** Use `wave_audit` for a combined read-only post-change check; `wave_validate` for docs lint; `wave_garden` for metadata-only refresh; `wave_index_health` to decide whether search is ready, stale, missing, or degraded; `wave_index_build_status` only to poll a detached refresh; `wave_index_build` when you need a deterministic update or rebuild.
- **Codebase map (MCP surface):** Read the generated orientation map via the resource `wavefoundry://codebase-map` (served fresh from `docs/references/codebase-map.md`; regenerated fail-safe if missing). Refresh just the map — without a full index rebuild — with `wave_index_build(content="map")` (runs the ~0.09 s generator only; change-only/idempotent, so an unchanged codebase is a no-op; fail-safe). The map is also regenerated automatically on **every** index rebuild path. **Reconnect caveat:** a newly added MCP resource or tool option only appears after the MCP client **reconnects** to the server (FastMCP limitation) — restart/reconnect if `wavefoundry://codebase-map` or `content="map"` is not yet visible.
- **Guru output:** `code_ask` citations preserve the reranker `score`, but `final_rank` reflects the post-partition order. When `demoted: true` is present, the citation was intentionally pushed behind stronger implementation evidence. Do not treat score order and output order as the same thing.
- **Wavefoundry self-hosting:** When editing framework seeds, use **Package Wavefoundry** to produce a distribution and **Upgrade Wavefoundry** in a target repo to consume it.

## Internal Agent-Oriented Prompt Bodies

Supporting agent-oriented prompt bodies live under `docs/prompts/agents/`. These are checked-in context helpers and are not listed as public commands.

| File | Lane |
|------|------|
| `docs/agents/guru.md` | Guru / `code_ask` retrieval agent — canonical role doc |
| `docs/prompts/agents/performance-reviewer.prompt.md` | `performance-reviewer` |
| `docs/prompts/agents/security-reviewer.prompt.md` | `security-reviewer` |

## Prompt Search Routing

All files under `docs/prompts/` are indexed with `kind="prompt"` and searched via the MCP server.

- **When the prompt name is unknown** — use `docs_search(query="...", kind="prompt")` to discover relevant commands. Example: `docs_search(query="how do I start a wave", kind="prompt")`.
- **When the prompt ID is known** — use `seed_get(id="...")` for direct retrieval of a framework seed prompt (e.g. `seed_get(id="170-plan-feature.prompt.md")`). For project prompt docs, use `code_read(path="docs/prompts/prepare-wave.prompt.md")`.
- **Omit `kind`** to search across all doc kinds (prompts, architecture, wave records, seeds) in a single query.
