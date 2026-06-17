# Per-area AGENTS.md context (vendor-neutral, no per-folder bridge files)

Change ID: `1p5xc-enh per-area-agents-context`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-16
Wave: `1p5x8 large-codebase-map`

## Rationale

Practitioner feedback on the large-codebase guidance is consistent: a small, area-scoped context file ("/payments uses this lib", "/auth has these gotchas") does more work than a giant root file, and oversized root context actively degrades decisions. The map (`1p5tl`) routes an agent to the right *area*; this change gives each major area a place to carry its own conventions/gotchas — so once routed there, the agent has the local intent without bloating the root.

It must be **vendor-neutral**, not Claude-specific. The canonical file is **`AGENTS.md`** (the agents.md convention many agents read). We deliberately avoid two things the operator flagged: (1) a `CLAUDE.md` bridge file in every folder (boilerplate clutter), and (2) repo-wide `@import` adoption we have no experience with. Instead, area `AGENTS.md` files are reached **on demand** via the map index + a single root convention line + the doc index — mechanisms that are agent-agnostic and rely on what this wave already builds. `@import` is used in exactly **one** place — the root — where it is the Anthropic-recommended pattern and contained.

Confirmed mechanics (Claude Code docs, 2026-06-15): Claude Code reads `CLAUDE.md` only (not `AGENTS.md` natively); nested `CLAUDE.md` loads lazily; `CLAUDE.md` supports `@path` imports (depth 4). Agents like Codex read nested `AGENTS.md` natively. The design below works for both without per-folder bridge files.

## Requirements

1. **Root `@import` bridge (the only `@import` we adopt).** Render the root `CLAUDE.md` as a real `@AGENTS.md` import (replacing the prose "read AGENTS.md first" pointer), so the root `AGENTS.md` is the single source of truth that Claude loads deterministically and other agents read directly. Generic: rendered by `render_platform_surfaces` so every downstream project gets it.
2. **Per-area `AGENTS.md`, major areas only.** Vendor-neutral `AGENTS.md` files live in **major subsystems** (the areas `1p5tl` identifies from the graph/cluster), not in every folder. They are real content (conventions/gotchas/intent pointers), human-authored — **never auto-generated prose** (self-updating docs are unreliable). The framework may scaffold an empty/stub `AGENTS.md` for an area, but does not write its conventions.
3. **No per-folder bridge files, no per-folder `@import`.** There is **no `CLAUDE.md` in subdirectories** and no nested `@import`. Area `AGENTS.md` files are discovered on demand, not auto-loaded.
4. **Discoverability — three agent-agnostic mechanisms.** (a) The codebase map (`1p5tl`) links each area to its `AGENTS.md`; (b) a single standing line in the root `AGENTS.md` instructs any agent to consult an area's `AGENTS.md` before working in it; (c) area `AGENTS.md` files are indexed, so they surface in `docs_search`/`code_ask` when working in that area.
5. **Generic + seed-rooted.** The root-bridge rendering, the root convention line, and the scaffolding behavior ship in the framework (render path + seeds), inherited by every downstream project on upgrade. No wavefoundry-specific paths/values hardcoded.
6. **Weave the operating instruction into the agent-operating seed PROMPTS (not just the root `AGENTS.md` body).** The "before working in an area, consult that area's `AGENTS.md` if present" rule must be added to the relevant agent-operating seed prompt(s) — e.g. the agent-entry-surface (`050-…`) / run-contract surfaces — seed-first, so it is rendered into **every host's agent surface** and agents are actively instructed to use per-area `AGENTS.md`. A convention line that lives only in the root `AGENTS.md` body is not enough; it must be part of the operating contract the seeds render. Weave a discoverability pointer to the codebase map (`1p5tl`) alongside it.

## Scope

**Problem statement:** Area-specific conventions either live in an oversized root file (token-wasteful, degrades decisions) or nowhere. We want per-area context that any agent can use, without Claude-specific bridge files in every folder or unproven repo-wide `@import`.

**In scope:**

- Root `CLAUDE.md` → `@AGENTS.md` import, rendered generically via `render_platform_surfaces`.
- A standing "consult the area's `AGENTS.md`" convention line in the framework's root `AGENTS.md` seed.
- Scaffolding of empty/stub `AGENTS.md` for the major areas `1p5tl` identifies (opt-in/idempotent; never overwrites human content; never auto-writes conventions).
- Map (`1p5tl`) linking each area → its `AGENTS.md`.
- Tests + seed-first docs.

**Out of scope:**

- Per-folder `CLAUDE.md` bridge files or per-folder `@import` (explicitly rejected).
- Auto-authoring the *content* of any `AGENTS.md` (human-authored only).
- An `AGENTS.md` in every folder — major areas only.
- Native nested-`AGENTS.md` reading by Claude (not available; not pursued).

## Acceptance Criteria

- [x] AC-1: The root `CLAUDE.md` is rendered as an `@AGENTS.md` import (no prose-only pointer), via the agent-surface renderer (`render_agent_surfaces.py`, called by `render_platform_surfaces.py`); root `AGENTS.md` is the single source both Claude and AGENTS.md-native agents use. No `@import` is introduced anywhere except root.
- [x] AC-2: For the major areas identified by `1p5tl`, the framework can scaffold a stub `AGENTS.md` (`gen_codebase_map.py --scaffold-area-contexts`; idempotent; never overwrites or auto-authors content); there are **no** subdirectory `CLAUDE.md` files and no nested `@import` (asserted by repo-invariant test).
- [x] AC-3: Area `AGENTS.md` files are discoverable agent-agnostically — linked from the map (`render_markdown`), indexed so they surface in `docs_search`/`code_ask` (subdir `.md` picked up by `indexer.walk_repo`), **and the "consult the area's `AGENTS.md`" operating instruction is woven into the run-contract seed (`020`) + per-area guidance in `050` (seed-first)** so every rendered host agent surface carries it.
- [x] AC-4: Root-bridge render + convention line + scaffolding are generic/seed-rooted (inherited on upgrade, no project-specific hardcoding); tests cover the render, idempotent scaffolding, no-overwrite, and map linking; docs-lint clean (full suite not run this session per operator scope).

## Tasks

- [x] Render root `CLAUDE.md` as `@AGENTS.md` (update `render_agent_surfaces.py` bridge + this repo's root `CLAUDE.md`); confirm the import approval/behavior.
- [x] Add the standing "consult area `AGENTS.md`" convention line to the framework root `AGENTS.md` surface (woven via run-contract seed `020` + per-area guidance in `050`; rendered into this repo's `AGENTS.md`).
- [x] **Weave the "consult the area's `AGENTS.md`" operating instruction into the relevant agent-operating seed prompt(s)** (`020-run-contract` Operating Rules + `050` agent-entry-surface), seed-first, so it renders into every host agent surface — plus a pointer to the codebase map.
- [x] Implement idempotent area `AGENTS.md` stub scaffolding keyed to `1p5tl`'s areas (`scaffold_area_contexts`; no overwrite, no auto-prose).
- [x] Wire the map (`1p5tl`) to link each area → its `AGENTS.md` (`render_markdown` + `--print` pass `root`).
- [x] Tests (root render/bridge idempotence, scaffolding idempotence/no-overwrite, map linking, repo invariants) + seed-first docs; docs-lint clean (full suite deferred per operator scope).

## Agent Execution Graph


| Workstream  | Owner       | Depends On | Notes |
| ----------- | ----------- | ---------- | ----- |
| root-bridge | Engineering | —          | root CLAUDE.md → @AGENTS.md render + convention line |
| scaffold    | Engineering | (1p5tl)    | idempotent area AGENTS.md stubs keyed to map areas |
| map-link    | Engineering | (1p5tl)    | map links each area → its AGENTS.md |


## Serialization Points

- Scaffolding and map-linking depend on `1p5tl`'s area model (how areas are identified + the map output contract). Settle `1p5tl` first; the root-bridge workstream is independent and can land anytime.

## Affected Architecture Docs

A pointer in `docs/references/project-overview.md` (orientation) and a note alongside the map in `docs/architecture/graph-index-system.md`. The root `CLAUDE.md`/`AGENTS.md` convention is operational, not an architecture contract.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The root `@import` bridge is the single-source-of-truth mechanism the operator approved. |
| AC-2 | required | Area `AGENTS.md` without per-folder bridge files is the core of the design. |
| AC-3 | required | Discoverability (map + convention + index) is what replaces auto-loading. |
| AC-4 | required | Generic/seed-rooted + no-overwrite scaffolding must be tested. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Confirmed Claude Code reads `CLAUDE.md` only (not `AGENTS.md` natively), nested `CLAUDE.md` lazy-loads, `@import` supported (depth 4); Anthropic recommends a `CLAUDE.md` that imports `AGENTS.md`. Operator chose: root `@import` only; per-area `AGENTS.md` reached via map + convention + index; no per-folder bridge files. | Claude Code docs (memory.md, 2026-06-15); this session |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Vendor-neutral `AGENTS.md` per area; `@import` only at root | Keeps content agent-agnostic; avoids a `CLAUDE.md` bridge in every folder (clutter) and repo-wide `@import` (unproven here); root import is the contained, Anthropic-recommended pattern | Per-folder `CLAUDE.md` `@AGENTS.md` (rejected — boilerplate in every folder); per-folder symlink (rejected — Windows-admin caveat); rely on native nested `AGENTS.md` (rejected — Claude doesn't read it) |
| 2026-06-16 | Discover area `AGENTS.md` via map + root convention + index, not auto-load | Replaces Claude's lazy nested-`CLAUDE.md` load with agent-agnostic discovery using surfaces this wave already builds; token-controlled (read only when routed there) | Auto-load via nested bridge files (rejected — the clutter we're avoiding) |
| 2026-06-16 | Scaffold stubs only; humans author the content | Self-updating/auto-authored docs are unreliable (practitioner consensus); the framework provides the slot, not the prose | Auto-generate area conventions from the graph (rejected — unreliable, drifts) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Area `AGENTS.md` not consulted (no auto-load) | Linked from the map, referenced by a root convention line, and indexed so it surfaces in `docs_search`/`code_ask` — three independent discovery paths |
| Root `@import` behaves unexpectedly (new to us) | Single, contained use at root; the Anthropic-recommended pattern; verify the one-time import approval; falls back to the existing prose pointer if needed |
| Scaffolding clobbers human-authored content | Idempotent, never overwrites; only creates a stub when absent; never writes conventions |
| `AGENTS.md` proliferation | Major areas only (keyed to map areas), not every folder |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
