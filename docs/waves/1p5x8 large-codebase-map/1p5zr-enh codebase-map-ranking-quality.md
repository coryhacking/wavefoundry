# Codebase map ranking quality + feed repo-index (Option A)

Change ID: `1p5zr-enh codebase-map-ranking-quality`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-16
Wave: `1p5x8 large-codebase-map`

## Rationale

The `1p5tl` map is a correct, fast (~0.09 s) foundation, but an evaluation of the rendered output for this repo found the **content quality** does not yet clear the "doesn't ship unless useful" bar:

- **The dominant area is an undifferentiated blob.** `server_impl` = 1612 graph nodes covering the entire `scripts/` dir — exactly where orientation matters most, the map says "it's all one area."
- **"Key entry points (by graph degree)" surface utilities, not entry points** — `_response`, `_diagnostic`, `_ensure_no_extra_args` (ubiquitous leaf helpers), not `register_mcp_surface` / tool handlers / `build_index`. Raw degree ranks "most-called helpers," the opposite of useful orientation.
- **Config files leak in as code areas** — `workflow-config` and `manifest` list JSON keys (`wave_review`, `enabled`, `validationSummary`) as "key entry points… (class)". Misleading; there's no code there.
- **Weak area labels** — named after the single biggest symbol, not a domain.

Separately, an evaluation against `docs/repo-index.md` decided **Option A**: the generated map **feeds `repo-index`'s structural section** (keeping it fresh — `repo-index` is currently stale, e.g. it still claims "no MCP server scaffolded"), while **humans/agents** keep the narrative (summary, tech, architecture, personas) — deliberately authored, not auto-generated prose. And `1p5xc`'s map-linking has a bug — it emits area→`AGENTS.md` links for files that do not exist (docs-lint broken-link failure).

This change makes the map genuinely useful, fixes the link bug, and wires Option A. Implemented in stages: **quality fixes first → re-evaluate the rendered map with the operator → then wire the repo-index feed** (feed clean data, not noise).

## Requirements

1. **Entry-point ranking by importance, not raw degree.** Rank by cross-area/cross-file **fan-in** (callers outside the symbol's own file) and/or chokepoint-ness; **filter trivial private helpers** (leading `_` with no cross-area callers) and ubiquitous utilities; prefer public/registered/exported symbols (module-level public defs, MCP-registered handlers, etc.). **Exclude config-key nodes** from entry points entirely.
2. **Config-only area demotion.** Areas whose nodes are predominantly config (source file is `.json`/`.yaml`/etc., no real code symbols) are flagged as **config**: list files only, **no "entry points (class)"**, and demoted below code areas (or clearly marked). The `workflow-config`/`manifest`-style areas must stop presenting fake entry points.
3. **Sub-divide oversized areas.** When one area exceeds a threshold (a share of the total graph or an absolute node cap), **split it into navigable sub-areas** (by sub-directory / community / file cluster) so a 1612-node `scripts/` blob becomes multiple real areas — the whole point at density. Overall output stays bounded (the existing `MAX_TOP_AREAS` cap still holds).
4. **Tiered area labels (auto-accurate, human-authoritative, carry-forward).**
   - **Tier 1 — auto (best-effort, never wrong-category):** never use a doc/spec/config node as the representative (Solaris fix). Prefer, in order: (a) a meaningful **directory segment** (skip generic roots `scripts`/`src`/`lib`), (b) the **dominant shared token** across the area's *code* symbol/file names, (c) the most-central code symbol. **Disambiguate by path**, never bare `N` suffixes.
   - **Tier 2 — authoritative (rich, human/agent-named):** if the area has an `AGENTS.md`, use its **title** (first `# heading`) as the label and its **first content line** as the "Responsibility", overriding the auto-label.
   - **Carry-forward / no-loss (the load-bearing property):** durable human/agent knowledge lives **only** in the per-area `AGENTS.md` (committed, never auto-overwritten); the map is a regenerated **view** that **re-reads** that `AGENTS.md` on every build, so the knowledge is folded into the auto-generated map **without living in it** — a regeneration can never lose it. The generated map keeps its "GENERATED — do not edit" header; humans add knowledge in `AGENTS.md`, not the map. (Same principle as the repo-index feed: generated content in markers, human narrative outside.)
5. **Fix the `1p5xc` map-link bug.** Emit an area→`AGENTS.md` link **only when that file actually exists**; the generated map must be docs-lint-clean (no broken links).
6. **Option A — map feeds `repo-index` (sequenced after 1–5, on clean data).** The generator refreshes a **marker-delimited** structural block (e.g. `<!-- waveframework:repo-index-modules begin/end -->`) in `docs/repo-index.md` from the map's area data, keeping the "Top-Level Modules and Roots"-style structure fresh. The **human/agent-authored** narrative (summary, tech, architecture, personas, open questions) stays **outside** the markers, untouched. Generic + seed-rooted (the repo-index seed carries the marker so any consuming project benefits); idempotent; fail-safe (never corrupts the narrative sections).
7. **teton field defects (second consumer — TS/Nx monorepo).** Fix the generator defects verified against a real TypeScript monorepo:
   - **a. Symbol-kind tagging.** Don't default every non-class node to `(function)`. Detect `type`/`interface`/`property`/`const`/`enum-member`/etc. from the graph node kind, and **omit the kind tag when it can't be determined** rather than mislabeling. (TS type members, object props, theme tokens, HTTP headers, route segments were all shown as `(function)`.)
   - **b. Same-package fragmentation.** Collapse multiple communities that resolve to the **same representative package/directory** into one area (e.g. `libs/typings/src/lib` was split into 7 `*.types` areas eating 7 of 24 slots). Don't let one package crowd out distinct subsystems.
   - **c. Hub/area consistency.** The chosen `hub_node_id` (drill-in) **must be a member of the area's representative package and appear in its key-files** — no drilling into a file outside the area (a stores area drilled into `Application.tsx`).
   - **d. Exclude non-code from the code graph/areas.** `.html`/styleguide/asset files must not form or contaminate code areas — exclude them (or weight them out of community formation) so they don't become or pollute areas.
8. **Usefulness bar (re-evaluated, not auto-asserted).** After 1–5 + 7, the re-rendered map for this repo must: break the `scripts/` blob into sub-areas; show **meaningful** entry points (not `_response`/`_diagnostic`); present **no** config keys / non-code as entry points; and carry **accurate kind tags** (or none). The operator re-evaluates the rendered map before the repo-index feed (req 6) is wired and before close. (The map-not-generated-on-upgrade defect teton reported is fixed by `1p601`'s regen-hook relocation.)

## Scope

**In scope:**

- `gen_codebase_map.py` ranking + grouping + labeling improvements (reqs 1-4) and the map-link existence fix (req 5).
- The repo-index marker-block feed (req 6) + the seed change so `repo-index` carries the marker (seed-first).
- Tests for ranking (meaningful over utilities), config-area demotion, oversized-area subdivision, the link fix, and the repo-index feed (idempotent, narrative preserved).
- A re-rendered `docs/references/codebase-map.md` + (once wired) the refreshed `repo-index` block.

**Out of scope:**

- LLM-generated prose summaries (still rejected — humans author the narrative; the map is mechanical).
- Changing the graph/cluster extraction itself (read-only consumer; no `GRAPH_BUILDER_VERSION` bump).
- `repo-index`'s narrative sections (human/agent-owned, deliberately authored; the feed only touches the marked structural block).

## Acceptance Criteria

- [x] AC-1: Entry points are ranked by cross-area fan-in / importance (not raw degree); trivial private utilities are filtered and config-key nodes excluded. Verified on this repo (the `scripts` area no longer leads with `_response`/`_diagnostic`) and by a fixture test.
- [x] AC-2: Config-only areas are demoted/flagged with files only — no "(class)" entry points. The `workflow-config`/`manifest`-style areas no longer present JSON keys as entry points (verified on this repo + a fixture).
- [x] AC-3: An area exceeding the size threshold is sub-divided into multiple navigable sub-areas (the `scripts/` blob splits); overall output stays within `MAX_TOP_AREAS`. Verified on this repo + a synthetic fixture.
- [x] AC-4: Tiered labels. **Tier 1 (auto):** never a doc/spec/config representative (Solaris fix — no more `repo-index`/`current-state`/`manual-override-contract` labels), prefer directory segment → shared code token → central code symbol, disambiguated by path (no bare `N` suffixes). **Tier 2 (authoritative):** when an area has an `AGENTS.md`, its title → label and first line → responsibility, overriding the auto-label. **Carry-forward (no-loss):** a test asserts that human knowledge in `AGENTS.md` survives a full regeneration (the map re-reads it; it is never stored in the map). Map-link bug fixed; generated map docs-lint-clean.
- [x] AC-5: The generator refreshes a marker-delimited structural block in `docs/repo-index.md` from the area data, leaving the human narrative outside the markers untouched; generic/seed-rooted, idempotent, fail-safe; tested. (Wired only after the operator re-evaluation in AC-6 passes.)
- [x] AC-6: Re-rendered map for this repo passes the usefulness re-evaluation (operator review: scripts split, meaningful entry points, no config-key noise); full suite + docs-lint clean.
- [x] AC-7 (teton defects): kind tags are accurate or omitted (no blanket `(function)`); communities resolving to the same representative package are collapsed into one area; each area's `hub_node_id` is a member of its representative package + appears in its key-files; non-code (`.html`/styleguide/assets) is excluded from areas. Verified by fixtures (mixed-kind nodes; multi-community-same-package; hub-membership; non-code exclusion).

## Tasks

- [x] Rework entry-point ranking (cross-area fan-in / importance; filter private utilities; exclude config nodes).
- [x] Add config-only area detection + demotion (files-only, no fake entry points).
- [x] Add oversized-area subdivision (split by sub-path/community; keep within the cap).
- [x] Domain-descriptive labels; fix the map-link existence check.
- [x] **Label root-cause fix (Solaris):** prefer a code symbol over a doc/spec/config node as the community representative used for the label; disambiguate duplicate `N`-suffixed labels; re-render.
- [x] **teton defects:** accurate/omitted kind tags (no blanket `(function)`); collapse same-package communities into one area; ensure `hub_node_id` ∈ area's package + key-files; exclude non-code (`.html`/styleguide) from areas.
- [x] Re-render the map; **operator re-evaluation checkpoint**.
- [x] Wire the repo-index marker-block feed (seed-first marker + generator fill; narrative preserved); tests.
- [x] Full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| ranking    | Engineering | —          | reqs 1-2 (entry-point ranking + config demotion) |
| grouping   | Engineering | —          | reqs 3-4 (subdivision + labels) |
| linkfix    | Engineering | —          | req 5 (map-link existence) |
| repo-index | Engineering | ranking, grouping | req 6, after the re-eval checkpoint |


## Serialization Points

- The repo-index feed (req 6) is sequenced AFTER the quality fixes (1-5) and the operator re-evaluation (req 7 / AC-6) — feed clean data, not noise.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — update the map note to describe the ranking signals + that the map feeds `repo-index`'s structural block (Option A). `docs/repo-index.md` gains a generator-managed marker block.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Meaningful entry points are the core usefulness fix. |
| AC-2 | required | Config-key noise actively misleads; must go. |
| AC-3 | required | Sub-dividing the dominant blob is where the map earns its keep. |
| AC-4 | required | Labels + the broken-link fix (docs-lint-clean) are correctness. |
| AC-5 | required | Option A — the map keeping repo-index fresh is the agreed design. |
| AC-6 | required | The "doesn't ship unless useful" bar — operator re-evaluation gates close. |
| AC-7 | required | teton field defects (kind tags, same-package collapse, hub consistency, non-code exclusion) — verified across a second real consumer. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Scoped from the operator's evaluation of the rendered map: dominant `scripts` blob (1612 nodes), degree-ranking surfaces utilities (`_response`/`_diagnostic`), config JSON keys shown as "(class)" entry points, weak labels. Plus Option A (map feeds `repo-index`) and the `1p5xc` map-link broken-link bug. | `docs/references/codebase-map.md`, `docs/repo-index.md` |
| 2026-06-16 | teton (2nd consumer, TS/Nx monorepo, 1685 files) field defects folded in as req 7 / AC-7: blanket `(function)` kind tags; same-package fragmentation (`libs/typings` → 7 `*.types` areas); hub/area inconsistency (drill-in outside the area); non-code (`.html`/styleguide) polluting areas. Corroborates Solaris on domain-vs-leaf labels. Map-not-generated-on-upgrade → fixed by 1p601 hook relocation. | teton 1.7.0+p5zy field report |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Quality fixes first → operator re-eval → then wire the repo-index feed | Feed clean structure into `repo-index`, not the current noise; "doesn't ship unless useful" | Wire the feed immediately (rejected — would propagate noisy areas into repo-index) |
| 2026-06-16 | Rank entry points by cross-area fan-in / importance, not raw degree | Degree surfaces ubiquitous leaf utilities; cross-area fan-in / public-surface signals surface real entry points | Keep degree (rejected — proven noisy); LLM-pick entry points (rejected — unreliable prose) |
| 2026-06-16 | Option A: map feeds a marker-block in `repo-index`; humans/agents keep the narrative | One fresh structural source (the map) + deliberately-authored human/agent narrative; stops `repo-index` drifting stale | Two independent docs (rejected — drift); merge fully (rejected — auto-generating narrative is the prose we rejected) |
| 2026-06-16 | Tiered labels with carry-forward: durable knowledge in per-area `AGENTS.md`, the auto-map re-reads it each build | Auto-labels can't be reliably rich (names live in human intent); storing human knowledge IN an auto-generated file would lose it on regen — so keep it in `AGENTS.md` (never overwritten) and have the regenerated map fold it in. Labels improve monotonically; nothing is lost | Hand-edit the generated map (rejected — lost on regen); auto-generate rich labels (rejected — unreliable prose); leave labels plain (rejected — operator wants human knowledge incorporated + carried forward) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| New ranking still surfaces noise on a real repo | Operator re-evaluation checkpoint (AC-6) before close; iterate |
| Subdivision breaks the bounded-output guarantee | Keep the `MAX_TOP_AREAS` cap; subdivide within it; test |
| repo-index feed corrupts human narrative | Marker-delimited block only; fail-safe; idempotent; test asserts narrative outside markers is untouched |
| Map-link fix misses an edge | Test: link present iff `AGENTS.md` exists; docs-lint-clean on the generated map |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
