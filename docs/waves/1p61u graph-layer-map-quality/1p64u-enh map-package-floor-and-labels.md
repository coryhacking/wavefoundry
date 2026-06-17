# Codebase map: package-structure area floor + label fixes

Change ID: `1p64u-enh map-package-floor-and-labels`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p61u graph-layer-map-quality`

## Rationale

`1p61w`'s per-module floor floors *areas*, but the javaagent re-eval showed the product modules that get crowded out aren't distinct areas at all: hibernate/spring/sailpoint user-enumeration instrumentation is **absorbed into one large `serialization` community** purely because every file calls a shared `JSON.toJson`. The community collapses to its single dominant directory (`serialization`), so the real modules survive only as incidental key-files — and the area-level floor has nothing to protect. shopizer is absent entirely.

The fix is to form areas from **package/directory structure**, not only from a community's single dominant directory: distribute a community's members to the area bucket of *their own* representative directory, so a community spanning hibernate + spring + serialization yields a hibernate area, a spring area, and a serialization area. This surfaces absorbed modules as first-class areas.

Two label fixes ride along (both field-reported, both generator-local):
- **Config-area responsibility (teton p64p, new minor):** a config area ("Agent Entry Guide (config)", files `tsconfig.base.json`/`cdk.json`/`nx.json`) takes its Responsibility from a scraped AGENTS.md *instruction sentence* that landed in the same community ("If the user's request matches a phrase below…") — not a description of the config files. Config areas must not adopt a prose-instruction first line as responsibility.
- **Same-path title collisions (javaagent 3):** `_disambiguate_area_names` resolves *different-path* collisions but not subdivisions of one oversized dir (4×`el/javax`); those need a third distinguisher (the contributing community label / a representative symbol).

## Requirements

1. **Package-structure area floor.** Form the top tier by distributing community members to the area bucket of their own representative directory (not the community's single dominant dir), so a significant top-level module/package surfaces as its own area even when its symbols are absorbed into a larger community via shared-utility fan-in. Bounded: only directories clearing a meaningful file/node floor become their own area; tiny scatter still rolls up.
2. **Faithfulness / anti-fragmentation.** Must not shatter a cohesive community into one area per leaf file; the floor promotes *significant* package/module directories only, and the existing `MAX_TOP_AREAS` cap + per-module floor (`1p61w`) still apply. A genuinely single-module community stays one area.
3. **Config-area responsibility:** for config-kind areas, do not use a prose-instruction AGENTS.md first line as the Responsibility — use a config-descriptive responsibility (or the area name) instead.
4. **Same-path title disambiguation:** when two areas share the same representative path (oversized-dir subdivisions), disambiguate titles with a third distinguisher (contributing community label or top representative symbol), not just the path.
5. Generator-only (`gen_codebase_map.py`); no version bumps; deterministic; generic.

## Scope

**In scope (`gen_codebase_map.py`):**

- Phase-2 collapse: bucket community members by their own representative directory (significant-dir floor), surfacing absorbed modules; keep the oversized-subdivision + cap + `1p61w` floor.
- Config-area responsibility: skip the prose-instruction AGENTS.md first line for config areas.
- Same-path collision disambiguation via a third distinguisher.
- Fixtures: absorbed-module surfacing; anti-fragmentation (cohesive community not shattered); config responsibility; same-path collision.

**Out of scope:**

- Clustering / community-membership changes (e.g. not merging modules through a shared utility) — that is the graph-layer cross-contamination item (teton #3), deferred.
- A fully synthesized natural-language responsibility from entry-point capability (e.g. "authorization capture") — larger NLP-ish effort; this change only stops the *wrong* (scraped-instruction) responsibility and keeps the path/name-consistent one.
- The vendored axis (sibling `1p64t`).

## Acceptance Criteria

- [x] AC-1: A community spanning multiple significant directories (e.g. `inst/hibernate`, `inst/spring`, `serialization`, joined only by calls to a shared util) yields a distinct area per significant directory — the absorbed modules are no longer only incidental key-files. A fixture asserts each module appears as its own area.
- [x] AC-2: Anti-fragmentation — a cohesive single-directory community is NOT split into per-file areas; a scatter of one-off files below the floor does not each become an area. Fixture + the cap/floor still hold.
- [x] AC-3: A config-kind area does not display a prose-instruction AGENTS.md sentence as its Responsibility; same-path title collisions (two areas, same representative path) are disambiguated by a third distinguisher. Regenerated map + full suite + docs-lint clean; no version bumps.

## Tasks

- [x] Redistribute community members to per-representative-directory buckets with a significant-dir floor (surface absorbed modules); keep subdivision + cap + `1p61w` floor.
- [x] Anti-fragmentation guard (significant-dir threshold; cohesive community stays one area).
- [x] Config-area responsibility: skip prose-instruction AGENTS.md first line for config areas.
- [x] Same-path title disambiguation via a third distinguisher.
- [x] Fixtures for each; regenerate map; full suite + docs-lint.

## Affected Architecture Docs

`N/A` — confined to the map generator's area-formation + labeling; no boundary/flow/verification change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The real fix for javaagent #2 — surface absorbed product modules as areas. |
| AC-2 | required | Faithfulness — must not over-fragment cohesive communities. |
| AC-3 | important | Config-responsibility + same-path collisions are field-reported label defects. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | javaagent p64p: per-module floor didn't surface product modules — they're absorbed into the `serialization` community via shared `JSON.toJson` fan-in (only incidental key-files; shopizer absent). teton p64p: config area takes responsibility from a scraped AGENTS.md instruction; same-path `el/javax` collisions persist. | field-feedback memory |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Form areas by per-member representative directory (significant-dir floor), not the community's single dominant dir. | Surfaces modules absorbed into a big community by shared-utility fan-in — the area-level floor alone can't (no area to protect). | Fix clustering so shared-utility fan-in doesn't merge modules (deferred — graph-layer, heavier). |
| 2026-06-17 | Stop the *wrong* (scraped-instruction) config responsibility; defer full capability-synthesized responsibility. | The scraped-instruction label is a clear bug; a synthesized NL responsibility is a larger, fuzzier effort. | Synthesize a capability responsibility now (deferred — scope). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Per-directory bucketing over-fragments the map. | Significant-dir floor (min files/nodes) + existing cap + `1p61w` per-module floor; AC-2 anti-fragmentation fixture. |
| Determinism: per-dir distribution changes the area set. | Deterministic given the graph (sorted inputs, `seed=0` clustering); area-set churn across rebuilds tracks input-graph changes, not this logic (hub_node_id stays the stable anchor). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
