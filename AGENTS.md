# Agent Guide — Wavefoundry

## Start Here

Read in this order at the start of every session:

1. `docs/references/project-overview.md` — project orientation, workflow, roles
2. `docs/references/codebase-map.md` — generated, graceful-scaling map of this project's own code (areas → key files/entry points → `code_*` drill-in); orient here before grep-thrashing
3. `docs/prompts/index.md` — shortcut phrase catalog (public command surface)
4. `docs/ARCHITECTURE.md` — architecture hub and child doc index
5. `docs/agents/session-handoff.md` — current session state (if work is in progress)

Before editing any repository code or framework seeds, read the **Stage Gate (repository code)** and **Framework Script Hygiene** sections below.

**Before working in an area of the codebase, consult that area's `AGENTS.md` if one is present** (vendor-neutral per-area context — local conventions, gotchas, intent). Orient first from `docs/references/codebase-map.md`, which routes you to the right area and links its `AGENTS.md` when one exists. There are no per-folder `CLAUDE.md` bridge files; the only `@import` is the root `CLAUDE.md` → `AGENTS.md` bridge.

## Codebase and documentation questions (auto-Guru)

Operators do **not** need to say **Guru** or **Ask codebase** for questions about how this repository's **code** or **documentation** works.

**Pre-flight question — ask this before responding to any user message:** *does answering this require reading code or documentation to understand what's there?* If yes, route to Guru. Surface forms vary infinitely ("how does X work", "tell me about X", "walk me through X", "I want to understand X", "where is X", "describe the Y flow"); intent does not. Apply the intent check on every message, not just messages that obviously match a phrase pattern.

When the answer is yes (or when the message is primarily about **understanding, locating, or explaining** source code or project docs — including architecture, specs, framework scripts, seeds, and `docs/` content) and is **not** a wave lifecycle shortcut from `docs/prompts/index.md` (**Plan feature**, **Implement wave**, **Close wave**, etc.), adopt the **Guru** workflow:

1. Read and follow `docs/agents/guru.md` (question classification, retrieval loop, mechanism completeness, citations).
2. When MCP is available, use `code_ask(question)` for cross-cutting code questions and `docs_search` for documentation-heavy questions per Guru's classification table.
3. Complete Pass 3 validation (`code_outline`, targeted `code_read`, `code_keyword` as needed) before synthesizing — do not answer from memory or from the `code_ask` `answer` field alone.
4. When MCP is unavailable, follow Guru's **When MCP is Not Available** fallbacks in `docs/agents/guru.md`.

**Examples — anchoring the boundary (these are examples, NOT a keyword list to match against; the rule is the pre-flight question above):**

| Example user question | Route to Guru? | Reason |
| --- | --- | --- |
| "How does authentication work?" | Yes | Explicit how-question; answer comes from reading auth code. |
| "Tell me about the way authentication works" | Yes | Semantic intent = "how does it work"; surface form doesn't match keyword patterns but the answer still comes from reading auth code. |
| "Walk me through the request flow" | Yes | Code investigation; answer comes from reading routing/middleware code. |
| "I want to understand session management" | Yes | Code investigation; answer comes from reading session code. |
| "What's the structure of the API layer?" | Yes | Architecture question; answer comes from reading code + docs. |
| "Where is the rate limiter defined?" | Yes | Code-location question; answer comes from code search. |
| "Explain how config loading works" | Yes | Explanation question; answer comes from reading config code. |
| "Describe the data flow from request to response" | Yes | Flow question; answer comes from reading code. |
| "Rename `getUserId` to `resolveUserId`" | No | Operational; the agent does the rename, no code-understanding required to answer. |
| "Delete the old session config" | No | Operational. |
| "Run the test suite" | No | Operational. |
| "What's the value of `MAX_RETRIES` in this file?" | No | Trivial lookup; targeted read suffices, no investigation needed. |

**Retrieval-intent backstop — late-detect signal:** if you find yourself about to call `code_search`, `code_keyword`, `code_lexical`, `code_read`, `code_definition`, `code_outline`, `code_callhierarchy`, `code_references`, or `code_pattern` in service of a user question, **stop**. That retrieval IS Guru's job. Route to Guru instead of doing the retrieval yourself. The tool reach-for catches misses the pre-flight skipped. **This applies to delegated work too:** when you spawn a subagent for code investigation or implementation, route it through a role-typed agent (`implementer`/`guru`) or carry the MCP-first directive in its prompt — subagents without an explicit `tools:` allowlist inherit the parent's MCP tools, and role wrappers with an allowlist include the retrieval tools explicitly, so a bare general-purpose subagent grepping by habit is the same defect (the exploration order lives in `seed-180`/`seed-211` — do not restate it).

Explicit shortcut **Guru** remains available in `docs/prompts/index.md` when the operator wants to name the mode.

### Agent platform routing (all hosts)

**Every agent host** uses the same canonical workflow above (`docs/agents/guru.md`). Operators never need to say **Guru** for code or documentation Q&A.

| Tier | Who | What to read / use |
|------|-----|-------------------|
| **1 — Canonical** | All hosts (Cursor, Claude Code, Codex, Copilot, Windsurf, Junie, Air, Warp, Antigravity, …) | This section + `docs/agents/guru.md`; Wavefoundry MCP when attached (`code_ask`, `docs_search`, …) |
| **2 — Thin pointer** | Each host's entry file (`CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `.github/copilot-instructions.md`, `WARP.md`, …) | One guardrail bullet pointing at tier 1 — no duplicated workflow text |
| **3 — Optional native** | Only when the host supports that affordance | Extra routing (rules, subagents, skills) — **enhances** tier 1; does not replace it |

**Optional native surfaces** (seed when `docs/agents/guru.md` exists; see `docs/agents/platform-mapping.md`):

| Host | Optional surface | MCP registration |
|------|------------------|------------------|
| Cursor | `.cursor/rules/auto-guru.mdc` | `.cursor/mcp.json` |
| Claude Code | `.claude/agents/guru.md` | `.mcp.json` (repo root) |
| Codex | `.codex/skills/auto-guru/SKILL.md` | `.codex/config.toml` (project-local, committed) |
| Copilot / Windsurf / Junie / Air / Warp | Tier 1 + tier 2 only | Per `AGENTS.md` MCP table (stdio entry or provider UI) |

## Purpose

Wavefoundry is the agent harness repository. It owns the Wave Framework and the local MCP server that delivers the harness to AI coding agents: feedforward seed prompts that guide correct behavior at every lifecycle step, and feedback sensors — computational sensors and inferential reviewer lanes — that verify what was actually done.

It owns the canonical framework source and provides local tooling for framework-aware work across target repositories. The MCP tool surface covers semantic search, cited codebase Q&A, wave inspection, change creation, and framework operations (lint, garden, audit, index health/build, sync surfaces).

Each target repository still owns its rendered local operating surface: `AGENTS.md`, `docs/prompts/`, `docs/agents/`, `docs/waves/`, `docs/plans/`, project specs, architecture docs, and workflow config.

The goal is not to hide the framework inside MCP. The goal is to make the canonical framework installable, upgradable, searchable, auditable, and operable while preserving explicit project-local instructions that agents can read without secret context.

## Product Boundary

This project is a framework and tooling repository, not a target product repository.

Wavefoundry should work against any explicitly configured target repository with Wave Framework state. Target examples in docs and tests must stay generic unless a fixture intentionally names a sample repository.

## Self-Hosting Boundary

Wavefoundry uses the Wave Framework to develop the Wave Framework.

This is intentional bootstrapping, not a source-of-truth collapse:

- `.wavefoundry/framework/` is the canonical framework product source: seed prompts, reference material, scripts, renderers, validators, packaging logic, and upgrade logic.
- `docs/` is Wavefoundry's self-hosted project operating surface: plans, waves, local prompt surfaces, agent roles, handoff, journals, MCP design docs, and project-specific decision records.
- Changes to framework behavior should be planned, reviewed, and closed through Wavefoundry's local `docs/` wave process.
- When `.wavefoundry/framework/seeds/` conflicts with rendered local prompt surfaces under `docs/prompts/`, treat `.wavefoundry/framework/seeds/` as source of truth for framework behavior.
- When project-specific process policy under `docs/` conflicts with generic framework defaults, treat the project-specific `docs/` policy as the local operating rule for Wavefoundry, then decide whether the framework default should be changed through an explicit wave.
- Install and upgrade tools should support a self-hosting mode where Wavefoundry is both the framework source repository and a target repository consuming rendered framework surfaces.
- Do not edit generated self-hosted surfaces as a substitute for fixing canonical framework seeds. If a rendered file is wrong because a seed is wrong, update the seed and regenerate or document the drift.

## Shortcut Phrases

Public Wave Framework commands for Wavefoundry's self-hosted surface. Full details in `docs/prompts/index.md`.


| Phrase | Purpose | Doc |
| --------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------- |
| **Init Wavefoundry** | Initialize Wave Framework in a target repo | `docs/prompts/install-wavefoundry.prompt.md` |
| **Start dashboard** | Start the local repository dashboard | `docs/prompts/start-dashboard.prompt.md` |
| **Stop dashboard** | Stop the local repository dashboard | `docs/prompts/stop-dashboard.prompt.md` |
| **Restart dashboard** | Restart the local repository dashboard | `docs/prompts/restart-dashboard.prompt.md` |
| **Upgrade Wavefoundry** | Upgrade Wave Framework in a target repo | `docs/prompts/upgrade-wavefoundry.prompt.md` |
| **Plan feature** | Author a consolidated change doc | `docs/prompts/plan-feature.prompt.md` |
| **Create wave** | Create a wave record | `docs/prompts/create-wave.prompt.md` |
| **Add change to wave** | Admit a change doc into the active wave | `docs/prompts/add-change-to-wave.prompt.md` |
| **Remove change from wave** | Remove an admitted change | `docs/prompts/remove-change-from-wave.prompt.md` |
| **Prepare wave** / **Ready wave** | Confirm readiness before implementation | `docs/prompts/prepare-wave.prompt.md` |
| **Implement wave** | Coordinator-managed multi-change implementation | `docs/prompts/implement-wave.prompt.md` |
| **Implement feature** | Single-change docs-first implementation | `docs/prompts/implement-feature.prompt.md` |
| **Pause wave** | Park session state in handoff artifact | `docs/prompts/pause-wave.prompt.md` |
| **Review wave** | Run required review lanes | `docs/prompts/review-wave.prompt.md` |
| **Close wave** | Finalize and archive the wave | `docs/prompts/close-wave.prompt.md` |
| **Finalize feature** | Single-change closure path | `docs/prompts/finalize-feature.prompt.md` |
| **Interrogate this plan** | Stress-test a change doc before admission | `docs/prompts/interrogate-plan.prompt.md` |
| **Evaluate decision** | Structured decision evaluation for ADR-shaped choices | `docs/prompts/evaluate-decision.prompt.md` |
| **Distill journals** | Promote stable journal findings to durable memory; retire stale ones | `docs/prompts/distill-journals.prompt.md` |
| **Archetype review** / **Archetype council** | Optional stance-based review applied to plans, design docs, code, prose, decision narratives, naming, AC formulation | `docs/prompts/archetype-council.prompt.md` |
| **Package Wavefoundry** | Build framework zip distribution | `docs/prompts/package-wavefoundry.prompt.md` |
| **Migrate to Wavefoundry** | Migrate a target repo from legacy layout | `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` |


Legacy aliases: `Init wave framework`, `Init wave context`, `Upgrade wave framework`, `Upgrade wave context`, `Package wave framework`, `Package wave context` — identical behavior; accept from operators and older docs.

## Implementation Principles

Behavioral rules for all agents working in this repository. Apply these before writing any code or docs.

1. **Ask, don't assume.** If something is unclear, ask before writing a single line. Never make silent assumptions about intent, architecture, or requirements.
2. **Simplest solution first.** Always implement the simplest thing that could work. Do not add abstractions or flexibility that weren't explicitly requested.
3. **Don't touch unrelated code.** If a file or function is not directly part of the current task, do not modify it, even if you think it could be improved.
4. **Flag uncertainty explicitly.** If you are not confident about an approach or technical detail, say so before proceeding. Confidence without certainty causes more damage than admitting a gap.

## Stage Gate (repository code)

Applies to all repository code: framework scripts, seed prompts, test files, build manifests, and any checked-in code or config that affects shipped or verified behavior.

**Before the first code edit in a given effort, all three of the following must be true:**

1. A consolidated change document exists at `docs/plans/<change-id>.md` or `docs/waves/<wave-id>/<change-id>.md`.
2. The change is admitted into a wave via **Create wave** / **Add change to wave**.
3. The wave is **readied** — a successful **Prepare wave** / **Ready wave** pass with `wave-council-readiness` recorded. A successful prepare requires that signoff: `wave_prepare` returns `status: "ready_for_council_review"` when technical checks pass but the council review has not yet been run; run the review immediately, then call `wave_prepare` again (`mode='ready'` to ready-without-opening, or `mode='create'` to prepare-and-open).

If any step is missing, stop and route back to **Plan feature**, **Create wave**, **Add change to wave**, or **Prepare wave**.

**READY vs OPEN (wave 1p45l):** readiness (plan → admit → ready) does **not** take the single-OPEN slot — any number of waves may be readied in parallel. Only **one** wave may be OPEN (`active`/`implementing`) at a time; that guard fires at the **activation** step (`Implement wave` / `wave_reopen` / `wave_prepare(mode='create')`). Readying other waves never displaces the currently OPEN wave.

**Out of scope for this gate:**

- Documentation-only edits under `docs/` with no behavioral impact
- Prompt/framework docs edits that don't change repository code
- Operator-approved explicit waivers for a named scope (record in change doc or `docs/agents/session-handoff.md`)

## Implementation Guard (product code)

No product implementation source exists in this repository yet. When `src/wavefoundry/` or other implementation directories appear, add a full Implementation guard section at that time requiring a consolidated change document and clean **Prepare wave** before the first edit to those paths.

## Framework Script Hygiene

Run framework tests without writing bytecode:

```bash
python3 .wavefoundry/framework/scripts/run_tests.py
```

After edits under `docs/`, agents with MCP should run `**wave_validate**` (and fix failures) before handoff; use `**wave_garden**` when metadata timestamps need refresh. The post-edit hook still runs docs-lint automatically — via the rendered hook `.py` body, which invokes `docs_lint.py` directly (not a bin wrapper) — that is not a substitute for MCP-first verification when the server is available. Manual CLI fallback: POSIX `**./.wavefoundry/bin/wf docs-lint**`; native Windows `**.\\.wavefoundry\\bin\\wf.cmd docs-lint**`.

Or: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests`

If `__pycache__` directories appeared anyway, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Change Doc Tracking (Real-Time)

Mark task and AC checkboxes `[x]` as each item completes; update `Change Status` in the change doc and `wave.md` immediately — not at wave end.

Three checkbox states are canonical: `[ ]` (unmet, in scope), `[x]` (done, evidence exists), and `[~]` (**intentionally not met** — requirement reconsidered, removed by operator direction, or genuinely narrowed by scope-discovery during implementation). Every `[~]` AC at required priority must carry an inline status note explaining the rationale; silent `[~]` is a docs-lint error. At `wave_close` every AC and task must be `[x]` or `[~]` (the hard close-time gate); silent `[ ]` blocks close. See `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` *"AC and task checkbox states — the `[~]` marker"* for the canonical convention.

## Git Commits (Operator-Owned)

Agents must **not** run `git commit` unless the operator explicitly instructs them to finalize that commit in the **current** request after reviewing the diff. Default agent behavior: hand off a suggested commit message and diff for the operator to commit locally.

This applies to all changes: framework source edits, self-hosted docs changes, platform surface renders, and packaging builds. See `docs/contributing/build-and-verification.md` **Git commits** for the full policy.

**Commit message style:** Do not mention Claude Code, Claude, or any AI tool in commit message subject lines or bodies. The `Co-Authored-By` trailer is also prohibited — omit it entirely.

## Wave Close (Operator-Owned)

Agents must **not** call `wave_close(mode="create")` (or `mode="apply"`) unless the operator explicitly instructs them to close the wave in the **current** request. Passing a dry-run is always safe and encouraged; writing the closed status is not.

Do **not** infer close approval from adjacent actions such as "remove the dead code", "fix the tests", "run the review", or "implement wave". Those phrases authorize the named task only. The operator must say something like "close the wave", "go ahead and close it", or "yes" after you have explicitly asked for closure confirmation.

`wave_close` dry-run (`mode="dry_run"`) does not require operator approval and may be used freely to validate readiness.

## Core Principles

- Local-only by default: no network dependency, no remote indexing, no hosted service requirement.
- Project-visible contracts: generated project-local files remain the operating contract for agents.
- Canonical source in one place: seed prompts, renderers, lifecycle rules, validators, and upgrade logic live here.
- MCP as capability, not identity: the MCP server is one Wavefoundry interface.
- Typed tools over arbitrary shell: MCP tools should expose structured operations rather than raw command execution.
- Read-first mutation model: tools should inspect, validate, and propose patches before writing where practical.
- Reusable target model: every tool should accept a target repository root or use configured allowed roots.
- Drift detection is a first-class feature: Wavefoundry should compare canonical framework state with project-local rendered surfaces.

## MCP Server

The Wavefoundry MCP server ships at `.wavefoundry/framework/scripts/server.py` and runs via stdio transport.

**Build the semantic index before first use:**

```bash
wf setup
```

This checks for the required runtime packages (`fastembed`, `httpx[socks]`, `numpy`, `mcp[cli]`) and builds the project index: docs/seeds, semantic code embeddings, and graph in the foreground by default. If dependencies are missing, it prints an isolated tool-venv install command instead of modifying the system Python. Pass `--root <path>` to target a different repository. Use `--background-code` only when you intentionally want docs/graph ready first while code embeddings continue in a detached background pass; use `--background-docs` for the inverse code-first tradeoff. `--include-code` remains accepted for explicit CI/full-build callers, but default setup already includes code. Code indexing defaults to source files only and skips tests/generated platform hooks; add `--include-tests` or `--include-generated` when those are useful. Wavefoundry framework internals under `.wavefoundry/framework/scripts/tests/` are never included in the semantic code index. The setup wrapper runs indexing in subprocesses to keep each pass isolated.

If `wf setup` fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path. In agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of switching to a separate manual model-download step.

The project-local index is stored at `.wavefoundry/index/` (gitignored) and is the **only** semantic index: the framework's own seeds/docs fold into each project's docs index at setup/upgrade, so distributions ship framework **source only** — there is no separately packaged `.wavefoundry/framework/index/` "framework layer" (ADR `1p4xx fold-framework-index-into-project-docs`; `build_pack.py` ships source only). The project-local index is refreshed incrementally — the post-edit hook fires `indexer.py` as a background process after each file edit. Use `wave_index_health()` to check whether a layer is ready, `wave_index_build_status(layer?)` to poll background refreshes, and `wave_index_build(content=..., mode=...)` when you need a deterministic update or rebuild. **To check whether a build is currently running, read the `lock` object on `wave_index_build_status` (the `held` boolean) — do NOT read `.wavefoundry/index/index-build.lock` directly.** That lock file persists **by design** as a crash-safe last-owner record and is reclaimed lazily on the next build, so its *presence does not mean a build is running*. `held` is determined by **testing the real OS lock** (not the file), and `ended_at` distinguishes a clean finish from an interrupted build.

### MCP / Wavefoundry server — enabling per host


| Host | Registration surface | How |
| ------------------ | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Claude Code** | `.mcp.json` (repo root) | **Auto:** generated by `render_platform_surfaces --platform claude`. Open the project in Claude Code — it discovers `.mcp.json` automatically. |
| **Cursor** | `.cursor/mcp.json` | **Auto:** generated by `render_platform_surfaces --platform cursor`. Enable under **Cursor → Settings → MCP** if not auto-loaded. |
| **Junie** | `.junie/mcp/mcp.json` | **Auto:** generated by `render_platform_surfaces --platform junie`. Junie discovers this file on project open. |
| **GitHub Copilot** | VS Code MCP settings | **Instruction:** open **VS Code → Settings → MCP servers** (or workspace `.vscode/mcp.json` if your VS Code version supports it) and add the stdio entry below. No auto-generated file in this release — VS Code MCP workspace support is still stabilising. |
| **Codex** | `.codex/config.toml` (committed) | **Auto:** project-local `.codex/config.toml` is committed to the repo. Codex loads the `wavefoundry` MCP server automatically for trusted projects — no manual registration step needed. Trust the project on first clone when Codex prompts. |
| **Air** | Provider-specific | **Instruction:** add the stdio server in your Air project settings or MCP config using the entry below. See your Air provider's MCP documentation for the current attachment path. |
| **Antigravity** | `.agents/mcp_config.json` | **Auto:** generated by `render_platform_surfaces --platform antigravity`. The `ag` CLI discovers and loads `.agents/mcp_config.json` automatically. The app/IDE uses the global `~/.gemini/…` config (manual). Antigravity reads the project-root `AGENTS.md` natively (Tier-1), so no thin-pointer entry file is rendered. |
| **Windsurf** | Windsurf MCP settings | **Instruction:** add the **copy-ready stdio entry below** via Windsurf's MCP settings (no auto-generated MCP file). Hooks *are* auto-rendered (`render_platform_surfaces --platform windsurf`); only MCP attachment is manual. |
| **Warp** | Warp MCP settings | **Instruction:** add the **copy-ready stdio entry below** via Warp's MCP settings. |


**Copy-ready stdio entry** (for instruction-only hosts — replace `<repo>` with the absolute path to this repository):

```json
{
 "command": "python3",
 "args": [
 "<repo>/.wavefoundry/framework/scripts/server.py",
 "--root", "<repo>"
 ]
}
```

Use the `python3` on PATH after `wf setup`; do not point MCP config at `.wavefoundry/venv/Scripts/python.exe` or a project-local venv path as a workaround for a missing or too-old `python3`. Before setup proceeds, `python3 --version` must work from the command line and report Python 3.11 or newer. `wf setup` verifies that this interpreter can import `mcp` and smoke-test `server.py --dry-run`. After changing MCP config or fixing Python on PATH, fully quit and reopen the agent host or start a fresh conversation; existing sessions may keep the toolset from the failed startup.

**Available tools:** `wave_help`, `wave_server_info`, `wave_gpu_doctor`, `wave_audit`, `wave_map`, `docs_search`, `code_search`, `code_ask`, `seed_get`, `wave_current`, `wave_list_waves`, `wave_list_plans`, `wave_get_change`, `wave_get_prompt`, `wave_get_handoff`, `wave_set_handoff`, `wave_gate_open`, `wave_gate_close`, `wave_gate_status`, `wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_review`, `wave_record_review_evidence`, `wave_context_efficiency_attach_evaluation`, `wave_close`, `wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`, `wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`, `wave_validate`, `wave_garden`, `wave_sync_surfaces`, `wave_index_health`, `wave_index_build_status`, `wave_index_build`, `wave_mcp_reload`, `wave_implement`, `wave_reopen`, `wave_upgrade`, `wave_upgrade_status`, `wave_dashboard_start`, `wave_dashboard_stop`, `wave_dashboard_restart`, `wave_dashboard_open`, `code_list_files`, `code_read`, `code_keyword`, `code_lexical`, `code_constants`, `code_pattern`, `code_outline`, `code_definition`, `code_references`, `code_dependencies`, `code_impact`, `code_callgraph`, `code_callhierarchy`, `code_graph_path`, `code_graph_community`, `wave_graph_report`.

**Graph index:** `wave_index_build(content='graph', mode='rebuild')` rebuilds only the structural graph (no semantic embedding). Graph query tools operate on the single `project` layer (target-repo code under workflow include-prefixes) — there is no framework or union graph layer. Community detection optionally uses `igraph`+`leidenalg` (installed by `wf setup`) and falls back to a built-in label-propagation pass when they are unavailable.

**Codebase Q&A shortcut:** `code_ask(question)` — ask a cross-cutting natural-language question about the codebase; returns `{answer, citations, reranked, confidence, gaps, question_type, index_freshness, partition_applied, demotion_count, second_hop_symbols, total_ms, vector_ms, rerank_ms}`. Each citation may also include `final_rank`, `demoted`, `partition_reason` (`doc_code_drift` — drift-flagged doc moved behind a comparable current alternative; the partition ships default-off), and an optional `freshness` object ({age_days, churn_score}, plus {drifted, commits_since_verified} on living docs or {historical, waves_behind} on wave archives) telling whether the cited content still matches the code it describes — distinct from the envelope `index_freshness` (index-vs-working-tree). Synthesize from `citations` directly — the `answer` field is a navigation pointer, not a synthesized answer. `score` is the pre-partition reranker score; `final_rank` is the post-partition output order. `reranked: true` means cross-encoder ranking ran (trust the order unless a citation is explicitly `demoted: true`); `reranked: false` means degraded ordering — vector/coverage on the healthy path (reranker disabled/unbuildable) or BM25 in `lexical_fallback`. Use `code_search`/`docs_search` instead when you want raw results to browse. See `docs/agents/guru.md` for retrieval loop, citation format, and uncertainty protocol.

Full tool reference — `code_ask` signal notes, `wave_new_*` creation tools, session handoff, edit gates, Codex server selection, wave lifecycle notes: `docs/specs/mcp-tool-surface.md` → **Tool Detail** section.

### Code Navigation

See `docs/specs/mcp-tool-surface.md` → **Code Navigation** for the full three-layer listing (semantic search, exact navigation, symbol navigation, graph query) with per-tool parameter docs. Quick chooser:

- Use `code_search` when you know the behavior or concept but not the exact symbol or file.
- Use `code_definition` when you know the symbol and want its defining declaration.
- Use `code_references` when you know the symbol and want call sites or usages.
- Use `code_keyword` when you need exact-token or exact-string matches; use `queries=[...]` for multiple patterns.
- Use `code_lexical` when you need BM25-ranked exact-token search over the indexed chunk corpus (compound identifiers, error strings, rare tokens) or to verify what the lexical (FTS5) layer holds. Not regex; tokens keep `_` inside, so query the full compound identifier.
- Use `code_constants` when you need the current value of one or more named constants.
- Use `code_pattern` when you need regex matching (non-literal patterns like `def .*handler`).
- Use `code_outline` when you need the structural shape of a file before deciding what to read.
- Use `code_read` after any of the above once you know which file to inspect directly.

### MCP Resources and Resource Templates

The server also exposes read-only **MCP resources** and **resource templates** for stable context discovery without tool calls:

Full resource documentation: `docs/specs/mcp-tool-surface.md` → **MCP Resources** section.

**Stable resources** (no parameters — attach to context directly):

- `wavefoundry://overview` — project overview doc
- `wavefoundry://prompts` — prompt/command index
- `wavefoundry://architecture/current-state` — architecture current-state summary
- `wavefoundry://wave/current` — active wave.md as markdown
- `wavefoundry://session-handoff` — session handoff state
- `wavefoundry://agents` — AGENTS.md (this file; primary agent operating guide)
- `wavefoundry://index/status` — semantic + graph index health summary (present/absent, counts, builder version)
- `wavefoundry://graph/status` — graph index metadata (present, node/edge/file counts, builder version, path)
- `wavefoundry://graph/communities` — catalog of code-graph communities (id, label, node count, boundary count, top members by degree); read first before `code_graph_community(community_id=…)`
- `wavefoundry://waves` — markdown summary of all wave records and admitted changes

**Resource templates** (parameterized reads):

- `wavefoundry://change/{change_id}` — change doc by ID or prefix
- `wavefoundry://wave/{wave_id}` — wave.md by ID or prefix
- `wavefoundry://prompt/{slug}` — prompt doc by slug
- `wavefoundry://seed/{slug}` — seed doc by slug
- `wavefoundry://architecture/{slug}` — architecture doc by slug
- `wavefoundry://area/{area_id}` — a major area's per-area `AGENTS.md` (local conventions/gotchas/intent) by `area_id` (the URI-safe key shown in the codebase map; read `wavefoundry://codebase-map` first to discover area ids). Resolves by walking **up** from the area's representative path to the nearest ancestor `AGENTS.md` (so a conventionally project-root-placed file is found even when the area is a deep subdirectory). Serves the on-disk file (also indexed for `code_ask`/`docs_search`); a missing/un-authored area returns a `# Not Found` message — never synthesized.

**When to use resources vs tools:**

- Use **resources/templates** when you need to attach stable reference material as context (project overview, architecture docs, a specific change doc). Resources return raw markdown.
- Use **tools** (`wave_get_change`, `wave_current`, `seed_get`, etc.) when you need structured envelope responses with `diagnostics`, `next_tools`, and `usage` hints — especially for error-handling, recovery, or actions that return metadata beyond raw text.
- Missing resources return a clear `# Not Found` markdown message rather than raising an error.

### Docs validation and gardening (agents)

**Prefer MCP over shell launchers.** Use `**wave_validate`** for docs lint results, `**wave_garden**` for metadata gardening (follow the tool’s `mode` contract), and `**wave_audit**` when you need wave state + validation + index health in one structured response. Treat the no-PATH dispatcher forms as **CLI fallbacks** for hooks, CI, terminals, or any host where MCP is not attached — POSIX `**./.wavefoundry/bin/wf docs-lint**` / `**./.wavefoundry/bin/wf docs-gardener**`, native Windows `**.\\.wavefoundry\\bin\\wf.cmd docs-lint**` / `**.\\.wavefoundry\\bin\\wf.cmd docs-gardener**` — not the default path for agent instructions. More broadly: **before reaching for `ls`, `grep`, or filesystem tools to answer any question about wave state, plans, or change docs, check the MCP tool list first** — `wave_list_plans`, `wave_list_waves`, `wave_current`, `wave_get_change`, and related tools return structured answers directly without shell round-trips.

## Repository Shape and Ownership

See `docs/references/project-overview.md` for repository layout, target repository model, and framework vs. target ownership boundaries.

## Safety Rules

- Never operate outside configured allowed roots.
- Never run destructive operations by default.
- Never overwrite project-local customizations without showing a diff or conflict report.
- Never require a network call for install, upgrade, validation, indexing, or packaging.
- Keep generated project-local surfaces readable and reviewable.
- Treat target repository docs as source of truth for project-specific facts.
- Treat canonical framework seeds as source of truth for framework behavior.

## Cleanup and Destructive Operations

**Historical reference preservation:** During legacy cleanup, only remove live working docs and deprecated prompt/wrapper files that have valid replacements. Do not delete mentions of removed artifacts from wave records, closed-wave archives, or historical documentation.

**Framework distribution zip archives:** Zip files at the repository root (`wavefoundry-*.zip`) are transport artifacts only. Never commit them. If a zip was accidentally committed, remove it with `git rm --cached <file>.zip`.

**Seed prompts:** Never delete or overwrite seed prompts under `.wavefoundry/framework/seeds/` without an explicit wave and `seed_edit_allowed` guard approval. Open the gate with `wave_gate_open(gate="seed_edit_allowed")` before editing and close it immediately after with `wave_gate_close(gate="seed_edit_allowed")`. Seed edits affect all target repositories.
