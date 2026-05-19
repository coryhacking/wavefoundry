# Agent Guide — Wavefoundry

## Start Here

Read in this order at the start of every session:

1. `docs/references/project-overview.md` — project orientation, workflow, roles
2. `docs/prompts/index.md` — shortcut phrase catalog (public command surface)
3. `docs/ARCHITECTURE.md` — architecture hub and child doc index
4. `docs/agents/session-handoff.md` — current session state (if work is in progress)

Before editing any repository code or framework seeds, read the **Stage Gate (repository code)** and **Framework Script Hygiene** sections below.

## Codebase and documentation questions (auto-Guru)

Operators do **not** need to say **Guru** or **Ask codebase** for questions about how this repository's **code** or **documentation** works.

When a message is primarily about **understanding, locating, or explaining** source code or project docs — including architecture, specs, framework scripts, seeds, and `docs/` content — and is **not** a wave lifecycle shortcut from `docs/prompts/index.md` (**Plan feature**, **Implement wave**, **Close wave**, etc.), adopt the **Guru** workflow:

1. Read and follow `docs/agents/guru.md` (question classification, retrieval loop, mechanism completeness, citations).
2. When MCP is available, use `code_ask(question)` for cross-cutting code questions and `docs_search` for documentation-heavy questions per Guru's classification table.
3. Complete Pass 3 validation (`code_outline`, targeted `code_read`, `code_keyword` as needed) before synthesizing — do not answer from memory or from the `code_ask` `answer` field alone.
4. When MCP is unavailable, follow Guru's **When MCP is Not Available** fallbacks in `docs/agents/guru.md`.

Explicit shortcut **Guru** remains available in `docs/prompts/index.md` when the operator wants to name the mode.

### Agent platform routing (all hosts)

**Every agent host** uses the same canonical workflow above (`docs/agents/guru.md`). Operators never need to say **Guru** for code or documentation Q&A.

| Tier | Who | What to read / use |
|------|-----|-------------------|
| **1 — Canonical** | All hosts (Cursor, Claude Code, Codex, Copilot, Windsurf, Junie, Air, Warp, …) | This section + `docs/agents/guru.md`; Wavefoundry MCP when attached (`code_ask`, `docs_search`, …) |
| **2 — Thin pointer** | Each host's entry file (`CLAUDE.md`, `.cursor/rules/project-context.mdc`, `.junie/guidelines.md`, `.github/copilot-instructions.md`, `WARP.md`, …) | One guardrail bullet pointing at tier 1 — no duplicated workflow text |
| **3 — Optional native** | Only when the host supports that affordance | Extra routing (rules, subagents, skills) — **enhances** tier 1; does not replace it |

**Optional native surfaces** (seed when `docs/agents/guru.md` exists; see `docs/agents/platform-mapping.md`):

| Host | Optional surface | MCP registration |
|------|------------------|------------------|
| Cursor | `.cursor/rules/auto-guru.mdc` | `.cursor/mcp.json` |
| Claude Code | `.claude/agents/guru.md` | `.mcp.json` (repo root) |
| Codex | `.codex/skills/auto-guru/SKILL.md` | `.wavefoundry/bin/register-codex-mcp` |
| Copilot / Windsurf / Junie / Air / Warp | Tier 1 + tier 2 only | Per `AGENTS.md` MCP table (stdio entry or provider UI) |

## Purpose

Wavefoundry is the repository for the Wave Framework and its local MCP server.

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
| **Init wave framework** | Initialize Wave Framework in a target repo | `docs/prompts/install-wavefoundry.prompt.md` |
| **Start dashboard** | Start the local repository dashboard | `docs/prompts/start-dashboard.prompt.md` |
| **Stop dashboard** | Stop the local repository dashboard | `docs/prompts/stop-dashboard.prompt.md` |
| **Restart dashboard** | Restart the local repository dashboard | `docs/prompts/restart-dashboard.prompt.md` |
| **Upgrade wave framework** | Upgrade Wave Framework in a target repo | `docs/prompts/upgrade-wavefoundry.prompt.md` |
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
| **Package Wavefoundry** | Build framework zip distribution | `docs/prompts/package-wavefoundry.prompt.md` |
| **Migrate to Wavefoundry** | Migrate a target repo from legacy layout | `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md` |


Legacy aliases: `Init wave context`, `Upgrade wave context`, `Package wave framework`, `Package wave context` — identical behavior; accept from operators and older docs.

## Stage Gate (repository code)

Applies to all repository code: framework scripts, seed prompts, test files, build manifests, and any checked-in code or config that affects shipped or verified behavior.

**Before the first code edit in a given effort, all three of the following must be true:**

1. A consolidated change document exists at `docs/plans/<change-id>.md` or `docs/waves/<wave-id>/<change-id>.md`.
2. The change is admitted into a wave via **Create wave** / **Add change to wave**.
3. The wave has a successful **Prepare wave** / **Ready wave** pass as the immediately preceding lifecycle step.

If any step is missing, stop and route back to **Plan feature**, **Create wave**, **Add change to wave**, or **Prepare wave**.

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

After edits under `docs/`, agents with MCP should run `**wave_validate**` (and fix failures) before handoff; use `**wave_garden**` when metadata timestamps need refresh. The Cursor post-edit hook still runs `**.wavefoundry/bin/docs-lint**` automatically — that is not a substitute for MCP-first verification when the server is available.

Or: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests`

If `__pycache__` directories appeared anyway, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

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
python3 .wavefoundry/framework/scripts/setup_index.py
```

This checks for the required runtime packages (`fastembed`, `numpy`, `mcp[cli]`) and builds the docs/seed index. If dependencies are missing, it prints an isolated tool-venv install command instead of modifying the system Python. Pass `--root <path>` to target a different repository. Semantic code embeddings are optional and slower; add `--include-code` only when needed. Code indexing defaults to source files only and skips tests/generated platform hooks; add `--include-tests` or `--include-generated` when those are useful. Wavefoundry framework internals under `.wavefoundry/framework/scripts/tests/` are never included in the semantic code index. The setup wrapper runs docs and code indexing in separate subprocesses to keep each pass isolated.

The project-local index is stored at `.wavefoundry/index/` (gitignored). Packaged framework docs/seeds are indexed at `.wavefoundry/framework/index/` during `Package Wavefoundry`, then searched as a read-only framework layer. The project-local index is refreshed incrementally — the post-edit hook fires `indexer.py` as a background process after each file edit. Use `wave_index_health()` to check whether a layer is ready, `wave_index_build_status(layer?)` to poll background refreshes, and `wave_index_build(content=..., mode=...)` when you need a deterministic update or rebuild.

### MCP / Wavefoundry server — enabling per host


| Host | Registration surface | How |
| ------------------ | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Claude Code** | `.mcp.json` (repo root) | **Auto:** generated by `render_platform_surfaces --platform claude`. Open the project in Claude Code — it discovers `.mcp.json` automatically. |
| **Cursor** | `.cursor/mcp.json` | **Auto:** generated by `render_platform_surfaces --platform cursor`. Enable under **Cursor → Settings → MCP** if not auto-loaded. |
| **Junie** | `.junie/mcp/mcp.json` | **Auto:** generated by `render_platform_surfaces --platform junie`. Junie discovers this file on project open. |
| **GitHub Copilot** | VS Code MCP settings | **Instruction:** open **VS Code → Settings → MCP servers** (or workspace `.vscode/mcp.json` if your VS Code version supports it) and add the stdio entry below. No auto-generated file in this release — VS Code MCP workspace support is still stabilising. |
| **Codex** | `.wavefoundry/bin/register-codex-mcp` | **Per-project registration:** run the repo-local bootstrap launcher to register the current repository in `~/.codex/config.toml`. The launcher names every checkout `wavefoundry-<hash>`, where the hash is stable for that checkout path. Moving or recloning the repo intentionally changes the label. See [OpenAI Codex MCP docs](https://platform.openai.com/docs/docs-mcp) for the current attachment path. |
| **Air** | Provider-specific | **Instruction:** add the stdio server in your Air project settings or MCP config using the entry below. See your Air provider's MCP documentation for the current attachment path. |


**Copy-ready stdio entry** (for instruction-only hosts — replace `<repo>` with the absolute path to this repository):

```json
{
 "command": "python3",
 "args": [
 ".wavefoundry/framework/scripts/server.py",
 "--root", "<repo>"
 ]
}
```

**Available tools:** `wave_help`, `wave_server_info`, `wave_audit`, `wave_map`, `docs_search`, `code_search`, `code_ask`, `seed_get`, `wave_current`, `wave_list_waves`, `wave_list_plans`, `wave_get_change`, `wave_get_prompt`, `wave_get_handoff`, `wave_set_handoff`, `wave_open_gate`, `wave_close_gate`, `wave_create_wave`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_review`, `wave_close`, `wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`, `wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`, `wave_validate`, `wave_garden`, `wave_sync_surfaces`, `wave_index_health`, `wave_index_build_status`, `wave_index_build`, `wave_dashboard_start`, `wave_dashboard_stop`, `wave_dashboard_restart`, `code_list_files`, `code_read`, `code_keyword`, `code_constants`, `code_pattern`, `code_outline`, `code_definition`, `code_references`, `code_dependencies`.

**Codebase Q&A shortcut:** `code_ask(question)` — ask a cross-cutting natural-language question about the codebase; returns `{answer, citations, reranked, confidence, gaps, question_type, index_freshness, partition_applied, demotion_count, second_hop_symbols, total_ms, vector_ms, rerank_ms}`. Each citation may also include `final_rank`, `demoted`, and `partition_reason`. Synthesize from `citations` directly — the `answer` field is a navigation pointer, not a synthesized answer. `score` is the pre-partition reranker score; `final_rank` is the post-partition output order. `reranked: true` means cross-encoder ranking ran (trust the order unless a citation is explicitly `demoted: true`); `reranked: false` means RRF fallback (index/model unavailable, slightly lower quality). Use `code_search`/`docs_search` instead when you want raw results to browse. See `docs/agents/guru.md` for retrieval loop, citation format, and uncertainty protocol.

**Retrieval signal notes for `code_ask`:** `confidence` is a retrieval signal (High = 2+ citations, Medium = 1, Low = 0) — not an answer-quality guarantee. Evaluate citations by path and content layer, not score alone. For explanatory questions, citations from scaffolding-layer paths (constructs/, stacks/, routes/, config/, modules/) confirm wiring only — always follow up with reads of the actual handler or service layer before synthesizing. When `question_type == "explanatory"` and `reranked: true`, the tool automatically performs two-hop symbol expansion: symbol names are extracted from top citations and a second keyword retrieval pass fetches their definitions. `second_hop_symbols` (when present) lists the symbols that were chased — do not re-chase them manually; start the next retrieval pass from the layer they represent. If `partition_applied` is true, the visible citation order intentionally differs from score order; trust `final_rank` over `score` when deciding which citation is primary.

For change-plan creation, use the **`wave_new_<kind>` tools** — one call per kind, no `kind` argument needed: `wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`, `wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`. All MCP creation tools wrap lifecycle ID generation and scaffold `docs/plans/<change-id>.md` in one call. Use `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>` only as a CLI fallback when MCP is unavailable, or for wave-folder IDs until lifecycle mutation tools exist.

**Session handoff tools:**

- `wave_get_handoff()` — read `docs/agents/session-handoff.md`; returns `content` (null if the file doesn't exist yet), `mtime`, and `path`
- `wave_set_handoff(content=...)` — write (or create) `docs/agents/session-handoff.md` with the provided content; use this to record active session state across context windows

**Edit gate tools:**

- `wave_open_gate(gate=...)` — enable an edit guard in `.wavefoundry/guard-overrides.json`. Valid gates: `seed_edit_allowed`, `framework_edit_allowed`. Returns an error if the gate is already open (double-open indicates a forgotten close). Every open must be paired with a `wave_close_gate` call.
- `wave_close_gate(gate=...)` — disable an edit guard. Returns `status: "ok"` with an advisory diagnostic if the gate was already closed (harmless). Use `.wavefoundry/bin/gate open|close <gate>` as a CLI fallback.
- **Auto-close:** `wave_pause` and `wave_close` (create mode) automatically close all open gates and emit a `gates_forced_closed` advisory if any were open. `wave_close` dry-run emits the diagnostic without writing.
- Do **not** edit `.wavefoundry/guard-overrides.json` directly — use these tools instead.

### Codex server selection

When Codex is attached to multiple Wavefoundry repos, prefer the MCP server whose label matches the current repo's generated name. After attaching, call `wave_server_info()` first and confirm the returned `repo_root` before using any other tools:

- `wavefoundry-<hash>` for every checkout, stable for the checkout path

Do not guess across similarly named Codex entries. The launcher is the source of truth for the current repo-to-label mapping, and `wave_server_info()` is the source of truth for the connected repository.

**Bulk wave_get_change:** `wave_get_change(wave_id=...)` (without `change_id`) returns all admitted changes for the wave in `data.changes`, each with `id`, `status`, `path`, and `content` (capped at 300 lines). Use this at session start to ingest all change context in one call.

**Drift detection:** `wave_current` surfaces a non-blocking `change_status_drift` advisory when wave.md Change Status fields disagree with the actual change doc files. Status remains `ok`; update wave.md to resolve.

**`wave_current` returns `data.waves[]`:** The response carries all non-closed waves in `data.waves` (array), not `data.wave` (single object). Order: active first (0 or 1), then planned, then paused, then other in lifecycle-ID order. Each entry includes `wave_id`, `status`, `changes`, `path`, and `next_action` — `implement_wave` (active), `prepare_wave` (planned), `resume_wave` (paused). The `resume_wave` next-action is a semantic hint; the underlying transition is `wave_prepare` on the paused wave.

**Single-active-wave rule:** Only one wave may be `Status: active` at a time. `wave_prepare` enforces this with an `another_wave_active` diagnostic when another wave is already active; recovery is `wave_pause` on that wave, then re-run `wave_prepare` on the target. `wave_pause(mode='create')` transitions `active → paused` (and writes a session-handoff entry); resuming a paused wave means re-running `wave_prepare` on it (the guard still applies — resume is blocked if any other wave is active).

**Search mode transparency:** `docs_search` responses now include a `mode` field (`"semantic"` or `"lexical"`) alongside the existing `search_mode` field, for clear fallback visibility.

### Code Navigation (three layers)

The MCP server exposes three complementary code-navigation layers — use the right layer for the task:

> **Naming rule:** a tool carries the `_search` suffix **if and only if it uses the semantic index** (vector embeddings + reranker). Tools that operate by filesystem scan, regex, AST, or exact-key lookup do not carry `_search`. Use this to infer retrieval strategy from the tool name alone.

| Layer | Tools | When to use |
| --------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Semantic search** | `docs_search`, `code_search` | Find conceptually related content when you don't know the exact text; great for orientation and discovery |
| **Exact navigation** | `code_keyword`, `code_constants`, `code_read`, `code_list_files` | Deterministic lookup when you know the exact text, function name, constant name, or file; use for code review, implementation, debugging |
| **Symbol navigation** | `code_definition`, `code_references` | Jump-to-definition and find-references across Python plus supported non-Python languages; Python uses AST, JS/TS/Java/C#/Go/Rust/C/C++/Kotlin/Bash/SQL use tree-sitter-backed navigation, broader language support uses structural/text fallback |


**Exact navigation tools:**

- `code_list_files(glob?)` — list all repo-relative file paths; respects `.gitignore`/`.aiignore` and hardcoded excludes
- `code_read(path, start_line?, end_line?)` — read a file with line-numbered output; rejects absolute and traversal paths
- `code_keyword(query?, glob?, queries?)` — exact substring search; single `query` or batch `queries` list; batch mode merges results with `matched_query` tagging; `glob` applies across all queries
- `code_constants(symbols, glob?)` — batch constant value lookup; returns name/value/file/line/kind for each symbol; supports scalar and multiline values (frozenset, list, dict); not-found symbols included with null value
- `code_pattern(pattern, glob?, max_results?, ignore_case?)` — Python regex search across repository files; invalid patterns return structured error; files over 1 MB skipped; results include `truncated`/`total_matches_found`
- `code_outline(path)` — structural symbol map of a file; tiered parser (Python AST → tree-sitter → regex); returns functions, classes, methods, constants with line ranges and docstrings

**Symbol navigation tools (milestone 2):**

- `code_definition(symbol)` — finds Python definitions via AST, JS/TS/Java/C#/Go/Rust/C/C++/Kotlin/Bash/SQL definitions via tree-sitter-backed navigation when available, and other supported non-Python definitions via structural fallback; falls back to broad keyword matches when no structural definition is found
- `code_references(symbol)` — finds Python references plus tree-sitter-backed JS/TS/Java/C#/Go/Rust/C/C++/Kotlin/Bash/SQL references, then falls back to language-aware text matching and broad keyword matches when needed

**Quick chooser:**

- Use `code_search` when you know the behavior or concept but not the exact symbol or file.
- Use `code_definition` when you know the symbol and want its defining declaration.
- Use `code_references` when you know the symbol and want call sites or usages.
- Use `code_keyword` when you need exact-token or exact-string matches; use `queries=[...]` for multiple patterns in one call.
- Use `code_constants` when you need the current value of one or more named constants without parsing raw grep output.
- Use `code_pattern` when you need regex matching (non-literal patterns like `def .*handler`).
- Use `code_outline` when you need the structural shape of a file before deciding what to read.
- Use `code_read` after any of the above once you know which file to inspect directly.

### MCP Resources and Resource Templates

The server also exposes read-only **MCP resources** and **resource templates** for stable context discovery without tool calls:

**Stable resources** (no parameters — attach to context directly):

- `wavefoundry://overview` — project overview doc
- `wavefoundry://prompts` — prompt/command index
- `wavefoundry://architecture/current-state` — architecture current-state summary
- `wavefoundry://wave/current` — active wave.md as markdown
- `wavefoundry://session-handoff` — session handoff state

**Resource templates** (parameterized reads):

- `wavefoundry://change/{change_id}` — change doc by ID or prefix
- `wavefoundry://wave/{wave_id}` — wave.md by ID or prefix
- `wavefoundry://prompt/{slug}` — prompt doc by slug
- `wavefoundry://seed/{slug}` — seed doc by slug
- `wavefoundry://architecture/{slug}` — architecture doc by slug

**When to use resources vs tools:**

- Use **resources/templates** when you need to attach stable reference material as context (project overview, architecture docs, a specific change doc). Resources return raw markdown.
- Use **tools** (`wave_get_change`, `wave_current`, `seed_get`, etc.) when you need structured envelope responses with `diagnostics`, `next_tools`, and `usage` hints — especially for error-handling, recovery, or actions that return metadata beyond raw text.
- Missing resources return a clear `# Not Found` markdown message rather than raising an error.

### Docs validation and gardening (agents)

**Prefer MCP over shell launchers.** Use `**wave_validate`** for docs lint results, `**wave_garden**` for metadata gardening (follow the tool’s `mode` contract), and `**wave_audit**` when you need wave state + validation + index health in one structured response. Treat `**.wavefoundry/bin/docs-lint**` and `**.wavefoundry/bin/docs-gardener**` as **CLI fallbacks** for hooks, CI, terminals, or any host where MCP is not attached — not the default path for agent instructions. More broadly: **before reaching for `ls`, `grep`, or filesystem tools to answer any question about wave state, plans, or change docs, check the MCP tool list first** — `wave_list_plans`, `wave_list_waves`, `wave_current`, `wave_get_change`, and related tools return structured answers directly without shell round-trips.

## Repository Layout

Current repository shape:

```text
wavefoundry/
 AGENTS.md
 README.md
 docs/
 .wavefoundry/
 bin/ ← docs-lint, docs-gardener launchers (canonical CLI for hooks/CI)
 framework/
 README.md
 VERSION
 seeds/ ← canonical seed prompts and framework reference material
 scripts/ ← validation, packaging, rendering, MCP server, index builder
 index/ ← gitignored; generated by indexer.py
```

`.wavefoundry/framework/seeds/` contains canonical seed prompts and framework reference material. `.wavefoundry/framework/scripts/` contains framework validation, packaging, rendering, migration, maintenance, and MCP tooling.

## Target Repository Model

A target repository may contain:

- `AGENTS.md`
- `docs/prompts/`
- `docs/prompts/agents/`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/agents/`
- `docs/agents/session-handoff.md`
- `docs/agents/journals/`
- `docs/waves/`
- `docs/plans/`
- `docs/workflow-config.json`
- `docs/repo-profile.json`
- project-specific `docs/specs/`, `docs/architecture/`, `docs/contributing/`, `docs/references/`

Wavefoundry may also support repositories that do not yet have these files, using install/bootstrap tools.

## What Wavefoundry Owns

- Canonical Wave Framework seed prompts.
- Framework reference docs.
- Renderers for project-local prompt and agent surfaces.
- Install and upgrade logic.
- Lifecycle ID generation.
- Wave validation and docs-lint style checks.
- Docs-gardener style metadata refresh.
- Framework packaging/export logic.
- Local MCP server tools.
- Optional local code index and source search.

## What Target Repositories Own

- Product code and product docs.
- Local rendered framework surfaces.
- Wave and plan records.
- Project-specific workflow config and repo profile.
- Product/persona/reviewer policy customizations.
- Any local modifications that should be preserved during upgrade.

## Initial MCP Tool Surface

Start with a small, reliable read-only tool set.

- `wave.current`
 - Return active wave, last closed wave, handoff state, admitted changes, and next lifecycle action.
- `wave.validate`
 - Run framework validation against a target repository and return structured failures.
- `wave.prompt_surface_audit`
 - Compare shortcut table, prompt index, manifest, seed references, and rendered local prompt bodies.
- `wave.resolve_seed`
 - Resolve `seed-175`, `prepare-wave`, or similar references to canonical files and generated local surfaces.
- `code.search`
 - Local exact search over target repository files.
- `code.read`
 - Read file ranges with line numbers.

Add `wave.lifecycle_id` early if lifecycle ID generation is needed before mutation tools.

## Later MCP Tool Surface

- `wave.lifecycle_id`
- `wave.install`
- `wave.upgrade`
- `wave.package`
- `wave.create`
- `wave.add_change`
- `wave.prepare`
- `wave.review`
- `wave.close`
- `wave.archive_reports`
- `wave.memory_candidates`
- `code.symbols`
- `code.references`
- `code.semantic_search`

Lifecycle mutation tools should be introduced only after validation and audit tools are trustworthy.

## Configuration Sketch

Target repositories should be configured explicitly.

```json
{
 "allowed_roots": [
 "/path/to/target-repository"
 ],
 "default_root": "/path/to/target-repository",
 "index": {
 "enabled": true,
 "path": ".wavefoundry/index.sqlite",
 "ignore": [".git", ".build", "DerivedData", "node_modules", "__pycache__"]
 },
 "framework": {
 "canonical_revision": "local-dev",
 "render_project_surfaces": true
 }
}
```

Use real target paths only in local configuration, fixtures, or operator-provided examples. Do not hardcode any one product repository as the only supported target.

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

**Seed prompts:** Never delete or overwrite seed prompts under `.wavefoundry/framework/seeds/` without an explicit wave and `seed_edit_allowed` guard approval. Open the gate with `wave_open_gate(gate="seed_edit_allowed")` before editing and close it immediately after with `wave_close_gate(gate="seed_edit_allowed")`. Seed edits affect all target repositories.

## Initial Milestones

1. Inventory `.wavefoundry/framework/seeds/` and `.wavefoundry/framework/scripts/`.
2. Implement `wave.current`, `code.search`, and `code.read`.
3. Port lifecycle ID generation into Wavefoundry.
4. Port or wrap validation logic for `wave.validate`.
5. Add `wave.resolve_seed` for canonical seed lookup.
6. Add `wave.prompt_surface_audit` for shortcut/index/manifest/seed drift.
7. Add install/upgrade rendering for project-local surfaces.
8. Add package/export support.
9. Add local code index only after exact search and wave tools are stable.

## Definition Of Done For MVP

- Runs as a local MCP stdio server.
- Can inspect a configured target repository without modifying it.
- Can report active wave state and validation failures as structured JSON.
- Can search and read target repository files.
- Can resolve canonical seed references.
- Can audit prompt surface drift.
- Has tests for target-root safety, seed resolution, exact search, and prompt-surface audit behavior.
- Uses `Wavefoundry` consistently for the project identity.
