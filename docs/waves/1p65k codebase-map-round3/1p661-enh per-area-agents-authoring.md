# Per-area AGENTS.md: author content for major areas (the codebase-map ROI lever)

Change ID: `1p661-enh per-area-agents-authoring`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p65k codebase-map-round3`

> Operator-directed addition. Broadens this wave from map-generator polish to **per-area context population** — the higher-ROI lever a downstream MCP agent identified (memory `project-codebase-map-roi`): for an MCP-equipped agent the map is cold-start orientation; its UNIQUE, non-redundant value is human-authored per-area `AGENTS.md` content, which is empty stubs today.

## Rationale

`1p5xc` shipped the per-area `AGENTS.md` *slot* (scaffolded by `--scaffold-area-contexts`, linked from the map, indexed for `code_ask`/`docs_search`) but the framework deliberately *never authors content* and nothing triggers it — so the slots stay empty and the map stays a routing index over already-queryable info. Field verdict: empty stubs = marginal map. The lever is **content**.

This change adds the missing instructions to author concise, evidence-grounded per-area `AGENTS.md` for **major** areas during inventory (the same trust model as the other inventory-authored docs the agent already writes — `repo-index.md`, domain-map), and backfills them on upgrade.

## Requirements

1. **Policy reversal (narrow, deliberate).** Revise `seed-050`'s per-area block (`:245`) from "human-authored content; the framework never auto-authors" to: the agent authors a **grounded initial draft** for major areas during inventory; **humans refine**. Keep the slot-only `--scaffold-area-contexts` tool unchanged (still makes empty stubs, never overwrites). Document the trust model: one-time inventory authoring (NOT regenerated each build), evidence-grounded, major areas only — the same reliability basis as `repo-index.md`.
2. **`seed-030` authoring task.** After the area model is known, for each **major** subsystem (the bounded top-tier areas `gen_codebase_map.compute_areas` identifies + the deployable units from the seed-030 architecture handoff), author a concise `AGENTS.md` at the area's representative path: one-line purpose/responsibility, key local conventions/patterns, non-obvious gotchas/intent, main entry points. **Hard guardrails:** every line evidence-grounded; **major areas only** (not all areas); **no boilerplate** — if an area has no real local context beyond what the map already shows, leave it unwritten rather than pad; mark the file an initial draft for human refinement; never overwrite an existing human-authored `AGENTS.md`.
3. **`seed-160` upgrade backfill.** When upgrading a repo that has the codebase map but whose major areas lack `AGENTS.md`, author them under the same rules (so existing installs gain the lever, not just fresh ones); never overwrite existing files.
4. **Discoverability stays intact.** The authored files keep the existing wiring: map links them, root convention points at them, indexer picks them up (`code_ask`/`docs_search`). No change to the on-disk-file delivery model (a sibling MCP resource is added separately in `1p662`, complementing not replacing the file).
5. Seed-first (framework seeds → every project on upgrade); vendor-neutral / language-neutral; docs-lint clean.

## Scope

**In scope:** `seed-030-inventory-and-map.prompt.md` (author task), `seed-050-agent-entry-surface-bootstrap.prompt.md` (policy reversal at `:245`), `seed-160-upgrade-wavefoundry.prompt.md` (backfill), and any thin discoverability touch (`002` overview note if it documents the per-area contract).

**Out of scope:** the per-area MCP resource (sibling `1p662`); auto-regeneration of `AGENTS.md` on every build (explicitly NOT — one-time inventory authoring + human refinement); changing `--scaffold-area-contexts` (stays slot-only).

## Acceptance Criteria

- [x] AC-1: `seed-050`'s per-area block states the agent authors a grounded initial draft for major areas during inventory (humans refine), with the evidence-grounded / major-areas-only / no-boilerplate / never-overwrite guardrails and the one-time-not-regenerated trust note. The `--scaffold-area-contexts` tool description stays slot-only.
- [x] AC-2: `seed-030` carries a concrete task to author per-area `AGENTS.md` for major areas/deployable units from observation (purpose + conventions + gotchas + entry points), with the same guardrails; it names the area model (`compute_areas`) + the seed-030 deployable-unit handoff as the "major area" source.
- [x] AC-3: `seed-160` backfills per-area `AGENTS.md` for major areas on upgrade (never overwriting), under the same rules. Seed-first; docs-lint clean; full suite green.

## Tasks

- [x] Revise `seed-050` per-area block (policy reversal + guardrails + trust note); keep scaffold-tool wording slot-only.
- [x] Add the `seed-030` authoring task (major areas; evidence-grounded; no boilerplate; never overwrite).
- [x] Add the `seed-160` upgrade backfill.
- [x] docs-lint + full suite (seed prose; keep the gate green).

## Affected Architecture Docs

`N/A` — seed-prose/policy guidance; no code path.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The policy reversal is the load-bearing decision that unblocks content. |
| AC-2 | required | The inventory authoring task is the actual lever (turns the map from overhead to worth-opening). |
| AC-3 | important | Existing installs need the backfill, not just fresh ones. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | teton/agent ROI verdict: map is cold-start orientation for MCP agents; unique value = human-authored per-area AGENTS.md content; empty stubs = marginal. Operator: add seed/upgrade instructions to author the content; fold into this wave. | memory `project-codebase-map-roi`; `seed-050:245` (current slot-only/"never auto-author" wording) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Reverse `1p5xc`'s "framework never auto-authors per-area AGENTS.md" — agent drafts grounded content for MAJOR areas during inventory; humans refine. | Empty stubs make the map marginal (field verdict); agent-drafted grounded content is the same trust model as `repo-index.md`/domain-map the agent already authors. The `1p5xc` risk (unreliable self-updating docs) is mitigated: one-time inventory authoring (not per-build), evidence-grounded, major-areas-only, no-boilerplate, never-overwrite. | Keep strictly human-authored + scaffold/prompt harder (rejected — adoption stays near-zero, the lever doesn't fire); auto-regenerate every build (rejected — the exact self-updating-docs unreliability `1p5xc` avoided). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Agent writes boilerplate / pads every area → noise that erodes trust (the binary-kinds/grab-bag distrust pattern). | Hard guardrails: major areas only, every line evidence-grounded, leave-unwritten when no real local context, marked draft-for-refinement. Quality over coverage. |
| Authored draft overwrites human edits on re-run/upgrade. | Never overwrite an existing `AGENTS.md` (idempotent, matches `--scaffold-area-contexts`); authoring only fills absent files. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
