# Prompt Surface Index

Owner: Engineering
Status: active
Last verified: 2026-08-21

The public catalog of shortcut phrases you can say to your agent. Each phrase routes to the documented prompt body for that command. See `AGENTS.md` for the agent-side routing table.

If you're new to Wavefoundry, the repository `README.md` walks the install path and a first wave end-to-end; this index is the reference for everything else.

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
| **Review memories** / **Memory review** | Review and apply eligible memory consolidation, archival, and purge | `docs/prompts/memory-review.prompt.md` |
| **Refresh TechDocs** / **Author TechDocs** | Generate the missing-only Backstage catalog and TechDocs baseline (MCP: `wf_techdocs_baseline(mode='run')` after a `mode='dry_run'` preview; CLI: `wf techdocs-baseline`; `catalog-info.yaml`, `mkdocs.yml`, `docs/index.md`; gated on the navigation targets existing), then author the published pages with the technical-writer-coordinated collaboration and validate with the publication audit (MCP: `wf_techdocs_audit`; CLI: `wf techdocs-audit`); an explicit read-only request selects the review-only branch, which runs the audit alone and writes nothing; registration and publication stay operator-owned | `docs/prompts/refresh-techdocs.prompt.md` |
| **Reopen wave** | Reopen a prematurely closed or paused wave | MCP: `wf_reopen_wave(wave_id, purpose="review"\|"implement")` — `purpose` is required: it selects the context-efficiency stage the following work is attributed to. A missing or unrecognized value is rejected before anything changes. |
| **Index build status** | Poll background index refresh progress | MCP: `index_build_status(layer?)` — use after `wf setup --background-code`, `wf setup --background-docs`, or any detached refresh |
| **GPU doctor** | Embedding-provider / GPU capability diagnostic (platform, ONNX providers, selected provider, CUDA ABI-gap) | MCP: `wf_gpu_doctor()`; CLI: `wf gpu-doctor` (same report; also `wf setup --check-gpu`) |
| **Close wave** | Finalize wave with closure reconciliation | `docs/prompts/close-wave.prompt.md` |
| **Finalize feature** | Single-change closure path | `docs/prompts/finalize-feature.prompt.md` |
| **Interrogate this plan** | Stress-test a change doc before admission | `docs/prompts/interrogate-plan.prompt.md` |
| **Council review** / **Run council** | Two-phase adversarial council review on any artifact: red-team primer → fixed seats → synthesis | `docs/prompts/council-review.prompt.md` |
| **Red-team review** / **Red team this** | Standalone single-stance adversarial pass on one artifact (plan, code, ADR, design, prose, workflow); mode chosen from the red-team specialist's standalone lenses; records no signoffs, satisfies no gate | `docs/prompts/red-team-review.prompt.md` |
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
- **Wave Council:** when `docs/workflow-config.json` `wave_review.enabled` is true, every wave requires a council readiness pass during **Prepare wave**. Delivery Council during **Review wave** / before **Close wave** follows `delivery_mode`: `targeted` is the default and escalates full Council for upgrade/release, permission/trust-boundary, cross-platform, and other shared boundary triggers; `universal` applies it to every wave; `disabled` requires review disabled. These meta-review checkpoints do not replace the persisted specialist roster.
- **Implement wave vs Implement feature:** Use **Implement wave** for multiple admitted changes; use **Implement feature** for a single docs-first change.
- **Concurrency and protected surfaces:** See `docs/prompts/agent-routing-concurrency.prompt.md` for read-only vs write-owning lane rules.
- **Stress-testing plans:** After **Plan feature**, use **Interrogate this plan** to walk unresolved decision branches before admission.
- **Skills (`/wf-…`):** In Claude Code, Codex, and Antigravity, every core lifecycle command above is also a project-local skill under the `wf-` prefix (`/wf-plan-feature`, `/wf-prepare-wave`, `/wf-implement-wave`, `/wf-review-wave`, `/wf-close-wave`, `/wf-interrogate-plan`, `/wf-pause-wave`, `/wf-council`, `/wf-evaluate-decision`, `/wf-memory-review`, plus `/wf-guru` and `/wf-upgrade`); typing `/wf` filters the host's command menu to the family. Each skill is a thin pointer to the same prompt doc as its phrase, so either invocation runs the identical workflow. Skills render on `wf setup` and **Upgrade Wavefoundry**; the phrase interface works on every host. Rendering and gating detail: `docs/agents/platform-mapping.md` § Skills.
- **MCP freshness workflow:** Use `wf_audit` for a combined read-only post-change check; `wf_validate_docs` for docs lint; `wf_garden_docs` for metadata-only refresh; `index_health` to decide whether search is ready, stale, missing, or degraded; `index_build_status` only to poll a detached refresh; `index_build` when you need a deterministic update or rebuild.
- **Codebase map (MCP surface):** Read the generated orientation map via the resource `wavefoundry://codebase-map` (served fresh from `docs/references/codebase-map.md`; regenerated fail-safe if missing). Refresh just the map — without a full index rebuild — with `index_build(content="map")` (runs the ~0.09 s generator only; change-only/idempotent, so an unchanged codebase is a no-op; fail-safe). The map is also regenerated automatically on **every** index rebuild path. **Adoption caveat:** a newly registered MCP resource such as `wavefoundry://codebase-map` is startup-bound and requires reconnect/restart. For a new tool or option such as `content="map"`, start a fresh turn first; if it is still absent, reconnect the MCP client, then restart the host only if reconnect does not refresh it.
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
