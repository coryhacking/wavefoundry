# Codebase map generator polish (round 3): vendored key-files, config/structural names, typings collapse

Change ID: `1p65l-enh map-generator-polish-round3`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-17
Last verified: 2026-06-17
Wave: `1p65k codebase-map-round3`

## Rationale

teton round-3 field feedback on `1.7.0+p65a` (rounds 1–2 confirmed landed). Four generator-local polish items in `gen_codebase_map.py`, all deterministic:

- **#1 (P2, highest-leverage):** vendored files leak into a product community's `key_files`/`key_symbols`. The vendored axis (`1p64t`) only collapses vendored-DOMINATED communities (fraction > 0.4) and blocks Phase-2.5 seeding; it never strips vendored matches from the key-files of a product area they're absorbed into (a <40% minority — e.g. `prism.js`, `otel.cjs` — slips both gates). Confirmed: `key_files` scores by member degree with no vendored/generated filter.
- **#3 name (P3):** a config area still takes a doc-prose **cluster label** as its name (`"Agent Entry Guide"` for a tsconfig/cdk/nx.json area) because rep_path `(root)` → empty segment → falls to the cluster label. (The *responsibility* was already fixed in `1p64u`; teton's contrary view is a stale, un-regenerated map.)
- **#4:** `libs/typings/src/lib` still yields ~6 single-file `*.types` areas, each named after its type file with Responsibility = the same filename — no real responsibility.
- **#5 (deterministic; also fixes #4/round-2 name churn):** structural/version leaf names carry no info (`v1`/`v2` → Responsibility `v1`; `shared`/`common`/`core`/`utils`/`lib`/`src`/`index`/`components`/`base`/`impl`).

## Requirements

1. **Vendored/generated never a key file OR hub (#1).** Filter `vendored_paths` / `.gitattributes linguist-vendored` matches AND `generated`-tagged nodes out of `key_files`, `key_symbols`, AND `hub_node_id` selection for EVERY area, regardless of the area's vendored/generated fraction. A vendored/generated file is never a "key file", "key entry point", or the drill-in hub of a product area. (Round-3 update: the drill-in hub was itself landing on `otel.cjs` — `.cjs` is a code extension so it passed the existing non-code/config hub filter; vendored/generated must be excluded from the hub pool too, falling back to the full pool only if nothing else remains.)
2. **Config-area name from config (#3 name) — GENERIC.** For `is_config` areas, derive the name **deterministically from the area's own representative path / config files**, NOT a doc-prose cluster label. Language/ecosystem-neutral: use the representative directory segment when meaningful, else a neutral label (e.g. `configuration`). **No hardcoded toolchain strings** (no "Build & tooling config" / `tsconfig`/`nx`-specific text) — the same logic must produce a sensible name for a Python `setup.cfg`/`pyproject.toml` dir, a Go module config, a Maven `pom.xml` dir, a YAML-config dir, etc.
3. **Structural/version leaf qualification (#5) — GENERIC.** When the derived name is a non-descriptive structural/version segment, walk up to the nearest distinctive ancestor and qualify it (`…/github/cards/v1` → `github-cards (v1)`); coalesce sibling version folders under one parent. The denylist is **ecosystem-neutral and extensible** — version segments (`v\d+`) plus common structural segments across stacks (`shared`, `common`, `core`, `util`/`utils`, `helper`/`helpers`, `lib`/`libs`, `src`, `index`, `components`, `internal`, `base`, `impl`, `app`, `main`, `pkg`, `cmd`, `mod`, `dist`, `build`), defined as a single named constant so projects/stacks can extend it. Deterministic (reuses `_disambiguate_area_names` machinery) → also stabilizes names across rebuilds.
4. **Same-package type-only collapse (#4) — GENERIC by KIND, not filename.** Collapse multiple type-only communities resolving to the same representative package into one "types" area. Detect "type-only" by the area's **node KINDS** (predominantly `type`/`interface`/`property`/`enum` — accurate post-`1p61v`), NOT by `.types`/`libs/typings`-style filename or path patterns, so it works for any language's type/interface-declaration grouping (TS `.d.ts`/type files, a package of pure interfaces, etc.).
5. **Project- and language-generic, implemented broadly.** All four fixes are derived from observed feedback (teton TS, javaagent Java) but MUST be implemented against generic signals — config-presence, node KINDS, path structure, the explicit vendored/generated signals — with **no hardcoded teton/JS-specific paths, filenames, or labels**. Fixtures are synthetic and cross-stack (not teton paths). Generator-only (`gen_codebase_map.py`); no version bumps; deterministic; faithfulness preserved (vendored/generated detection stays explicit-signal/tag-based — never a name heuristic; product files are never excluded).

## Scope

**In scope (`gen_codebase_map.py`):** the four items above + fixtures for each + regenerate `docs/references/codebase-map.md`.

**Out of scope:** cross-directory clustering cohesion (sibling `1p65m` — that's the `graph_cluster` source of the grab-bag that #1 mitigates downstream); kind-taxonomy enrichment (cosmetic, deferred); any `GRAPH_/CLUSTER_BUILDER_VERSION` bump.

## Acceptance Criteria

- [x] AC-1: A product area that absorbs a vendored or generated file shows that file in NEITHER `key_files`, `key_symbols`, NOR as the `hub_node_id`; a fixture with a vendored + a generated minority file (incl. a high-degree vendored `.cjs` that would otherwise win the hub) confirms all three exclude it while real product files remain, with a safe fallback to the full pool if an area is entirely vendored/generated.
- [x] AC-2: A config (`is_config`) area's name is derived deterministically from its representative path / config files — language-neutral, **no hardcoded toolchain string** and not a doc-prose cluster label; the responsibility stays `configuration / manifest files`. Fixtures confirm it for ≥2 different config ecosystems (e.g. a JS `tsconfig`-style dir AND a non-JS config dir).
- [x] AC-3: A structural/version leaf name is qualified by walking up to a distinctive ancestor (`…/cards/v1` → `cards (v1)`); sibling version folders coalesce; the denylist is a single ecosystem-neutral extensible constant. A synthetic fixture confirms `v1`/`v2` + a `shared`/`core`-style leaf no longer render as bare opaque areas. Deterministic across repeated runs.
- [x] AC-4: Multiple type-only communities (detected by node KIND — `type`/`interface`/`property`/`enum` — NOT by `.types` filename) resolving to the same representative package collapse into one "types" area; a synthetic (non-teton-path) fixture confirms the by-kind collapse. Regenerated map + full suite + docs-lint clean; no version bumps.

## Tasks

- [x] Filter vendored/generated from `key_files` + `key_symbols` (#1).
- [x] Config-area name from config files (#3 name).
- [x] Structural/version-leaf denylist + walk-up qualification + sibling-version coalesce (#5).
- [x] Same-package type-only community collapse (#4).
- [x] Fixtures for each; regenerate map; full suite + docs-lint.

## Affected Architecture Docs

`N/A` — map generator area-selection/labeling internals; no boundary/flow/verification change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Vendored/generated leaking into key-files is the highest-leverage round-3 item. |
| AC-2 | important | Config-area name is a field-reported mislabel. |
| AC-3 | important | Opaque structural/version names + the deterministic naming pass (also stabilizes names). |
| AC-4 | nice-to-have | Typings fragmentation; reduces slot waste. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | teton round-3 (p65a): #1 vendored key-file leak (confirmed `key_files` has no vendored filter), #3-name config-area doc-prose label, #4 typings fragmentation, #5 structural/version leaf names. #3-responsibility already fixed (1p64u) — teton map stale. | field-feedback memory; `gen_codebase_map.py` key_files + `_finalize` name path |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Bundle the four generator-local fixes into one change; clustering cohesion (#2) is a separate change (`1p65m`). | All four are `gen_codebase_map` deterministic label/selection fixes with shared fixtures; clustering is a different subsystem + version constant. | One change for everything (rejected — couples deterministic generator polish to a fuzzy clustering investigation). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Over-filtering removes a real product file from key-files. | Vendored/generated detection is explicit-signal/tag-based (same matcher as `1p64t`/the `generated` tag); AC-1 fixture asserts real product files remain. |
| Walk-up qualification produces awkward names. | Denylist-gated (only fires on opaque leaves); `data-grid`-style descriptive leaves are untouched; deterministic + fixture-checked. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
