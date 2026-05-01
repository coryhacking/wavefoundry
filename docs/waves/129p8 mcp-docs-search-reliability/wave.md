# Wave — MCP Docs Search Reliability

Owner: Engineering
Status: closed
Last verified: 2026-04-30
Completed At: 2026-04-30

wave-id: `129p8 mcp-docs-search-reliability`
Title: MCP Docs Search Reliability

## Objective

Harden Wavefoundry's operator-facing framework surfaces in one coordinated wave: fix MCP docs-search reliability, expand and sharpen the supported agent catalog and role definitions, and align the lifecycle contract for when admitted change docs move into a wave folder.

## Coordinator

wave-coordinator

## Participants


| Role                         | Lane                       | Owns                                                                                             |
| ---------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| implementer                  | implement                  | `129p7-bug mcp-docs-search-reliability`, `129nj-enh agent-catalog-expansion`, `129pc-enh wave-admit-relocates-change-doc`, `129q6-enh mcp-index-watch-control`, `12a17-feat multi-host-mcp-registration`, `12a1j-feat wavefoundry-bin-cli-wrappers`, `12a0c-debt framework-script-code-quality`, `12a0x-enh mcp-tool-annotations-and-search-limit`, `12a46-enh mcp-round2-review-fixes`, `12a4d-enh wave-audit-tool` |
| architecture-reviewer        | review                     | `129p7-bug mcp-docs-search-reliability` — docs-search contract and index-health design           |
| architecture-reviewer        | review                     | `129nj-enh agent-catalog-expansion` — seed/routing structure for supported specialist roles      |
| architecture-reviewer        | review                     | `129pc-enh wave-admit-relocates-change-doc` — wave lifecycle contract and repair semantics       |
| architecture-reviewer        | review                     | `129q6-enh mcp-index-watch-control` — background index freshness model and watcher ownership     |
| code-reviewer                | review                     | `129p7-bug mcp-docs-search-reliability` — `server.py`, `setup_index.py`, and tests              |
| code-reviewer                | review                     | `129pc-enh wave-admit-relocates-change-doc` — lifecycle mutation behavior and tests              |
| code-reviewer                | review                     | `129q6-enh mcp-index-watch-control` — mutation-triggered reindex behavior and watcher controls   |
| code-reviewer                | review                     | `12a0c-debt framework-script-code-quality`, `12a0x-enh mcp-tool-annotations-and-search-limit`, `12a46-enh mcp-round2-review-fixes`, `12a4d-enh wave-audit-tool` — `server.py`, `render_platform_surfaces.py` as scoped, and tests |
| qa-reviewer                  | review                     | `12a0x-enh mcp-tool-annotations-and-search-limit`, `12a46-enh mcp-round2-review-fixes`, `12a4d-enh wave-audit-tool` — MCP annotations, envelopes, and `wave_audit` regression paths |
| docs-contract-reviewer       | review                     | `12a0x-enh mcp-tool-annotations-and-search-limit`, `12a46-enh mcp-round2-review-fixes`, `12a4d-enh wave-audit-tool` — `docs/specs/mcp-tool-surface.md` and operator-facing hints |
| qa-reviewer                  | review                     | `129p7-bug mcp-docs-search-reliability` — bug-fix verification and degraded-mode coverage        |
| qa-reviewer                  | review                     | `129pc-enh wave-admit-relocates-change-doc` — relocation and repair behavior coverage            |
| qa-reviewer                  | review                     | `129q6-enh mcp-index-watch-control` — repeat-safe freshness triggering and diagnostics           |
| docs-contract-reviewer       | review                     | `129p7-bug mcp-docs-search-reliability` — MCP tool contract and operator recovery docs           |
| docs-contract-reviewer       | review                     | `129nj-enh agent-catalog-expansion` — agent taxonomy, routing, and seeded role-shape docs        |
| docs-contract-reviewer       | review                     | `129pc-enh wave-admit-relocates-change-doc` — lifecycle prompt/spec wording                      |
| docs-contract-reviewer       | review                     | `129q6-enh mcp-index-watch-control` — lifecycle-triggered freshness wording and operator docs    |
| performance-reviewer         | review                     | `129p7-bug mcp-docs-search-reliability` — indexing/search response paths                         |
| performance-reviewer         | review                     | `129q6-enh mcp-index-watch-control` — background indexing trigger overhead and duplicate control |
| factor-12-admin-processes    | review (advisory)          | `129p7-bug mcp-docs-search-reliability` — setup/manual recovery CLI behavior                     |
| factor-12-admin-processes    | review (advisory)          | `129q6-enh mcp-index-watch-control` — operator workflow for non-hook environments                |
| factor-13-api-first          | review (advisory)          | `129p7-bug mcp-docs-search-reliability` — `docs_search` response envelope and diagnostics        |
| factor-13-api-first          | review (advisory)          | `129pc-enh wave-admit-relocates-change-doc` — lifecycle mutation tool contract                   |
| factor-13-api-first          | review (advisory)          | `129q6-enh mcp-index-watch-control` — MCP freshness/control contract                             |
| factor-13-api-first          | review (advisory)          | `12a17-feat multi-host-mcp-registration` — generated MCP host registration JSON shape              |
| architecture-reviewer        | review                     | `12a17-feat multi-host-mcp-registration` — host matrix and merge semantics for MCP config files   |
| code-reviewer                | review                     | `12a17-feat multi-host-mcp-registration` — `render_platform_surfaces.py` and render tests        |
| docs-contract-reviewer       | review                     | `12a17-feat multi-host-mcp-registration` — AGENTS / install MCP enablement matrix                  |
| architecture-reviewer        | review                     | `12a1j-feat wavefoundry-bin-cli-wrappers` — `bin/` layout vs MCP-primary operator contract         |
| code-reviewer                | review                     | `12a1j-feat wavefoundry-bin-cli-wrappers` — hook generator, callers, packaging                     |
| docs-contract-reviewer       | review                     | `12a1j-feat wavefoundry-bin-cli-wrappers` — AGENTS / build-and-verification / seed alignment       |
| factor-12-admin-processes    | review (advisory)          | `12a1j-feat wavefoundry-bin-cli-wrappers` — install/upgrade/hook CLI paths vs root shims          |
| factor-13-api-first          | review (advisory)          | `12a1j-feat wavefoundry-bin-cli-wrappers` — CLI vs MCP routing for agents                         |
| framework-operator (persona) | design review / acceptance | `129p7-bug mcp-docs-search-reliability` — operator-facing MCP behavior                           |
| framework-operator (persona) | design review / acceptance | `129nj-enh agent-catalog-expansion` — shared seed taxonomy and archetype-scoped specialist surface |
| framework-operator (persona) | design review / acceptance | `129q6-enh mcp-index-watch-control` — operator-facing indexing behavior in non-hook clients      |
| framework-operator (persona) | design review / acceptance | `12a17-feat multi-host-mcp-registration` — operator-facing MCP registration across hosts          |
| framework-operator (persona) | design review / acceptance | `12a1j-feat wavefoundry-bin-cli-wrappers` — operator-facing wrapper paths and bootstrap gates     |
| wave-coordinator (persona)   | design review / acceptance | `129pc-enh wave-admit-relocates-change-doc` — wave execution behavior                            |

## Changes

Change ID: `129p7-bug mcp-docs-search-reliability`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `129nj-enh agent-catalog-expansion`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `129pc-enh wave-admit-relocates-change-doc`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `129q6-enh mcp-index-watch-control`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a0c-debt framework-script-code-quality`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a0x-enh mcp-tool-annotations-and-search-limit`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a17-feat multi-host-mcp-registration`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a1j-feat wavefoundry-bin-cli-wrappers`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a46-enh mcp-round2-review-fixes`
Previous Change Status: `ready`
Change Status: `complete`

Change ID: `12a4d-enh wave-audit-tool`
Previous Change Status: `ready`
Change Status: `complete`

## Review Evidence

- architecture-reviewer: full-wave review **approved** 2026-04-30 (docs-search contract, catalog seeds, lifecycle relocation, index control).
- code-reviewer: implementation and tests **approved** 2026-04-30.
- qa-reviewer: degraded modes and lifecycle coverage **approved** 2026-04-30.
- docs-contract-reviewer: MCP contract and operator recovery docs **approved** 2026-04-30.
- performance-reviewer: indexing paths and background triggers **approved** 2026-04-30.
- factor-12-admin-processes: setup / manual recovery workflows **approved** 2026-04-30 (advisory).
- factor-13-api-first: tool envelopes and diagnostics **approved** 2026-04-30 (advisory).
- framework-operator (persona): operator-facing MCP and seed surfaces **approved** 2026-04-30.
- wave-coordinator (persona): wave lifecycle relocation behavior **approved** 2026-04-30.

## Dependencies

- No external wave dependencies.
- `129p7-bug mcp-docs-search-reliability` and `129pc-enh wave-admit-relocates-change-doc` both touch `server.py` and `docs/specs/mcp-tool-surface.md`; implementation should serialize those writes even if the broader wave stays parallel elsewhere.
- `129nj-enh agent-catalog-expansion` and `129pc-enh wave-admit-relocates-change-doc` both touch canonical seeds and prompt docs; those protected surfaces require single-owner coordination during implementation.
- `129q6-enh mcp-index-watch-control` also touches `server.py`, `docs/specs/mcp-tool-surface.md`, and operator-facing docs; serialize it with `129p7` / `129pc` around lifecycle mutation and indexing surfaces.
- `12a17-feat multi-host-mcp-registration` touches `render_platform_surfaces.py` and generated MCP JSON paths; serialize with other render/hook work and with `12a0c-debt framework-script-code-quality` if both land in the same window.
- `12a1j-feat wavefoundry-bin-cli-wrappers` touches `render_platform_surfaces.py`, hook templates, packaging, and many canonical seeds; serialize with `12a17` and `12a0c` on the render module; coordinate with `129nj` if both expand seed surfaces in the same window.

## Current Assumptions

- A-1 (tentative): `129p7-bug mcp-docs-search-reliability` can remain within the current `fastembed` model family; reliability fixes do not require an embedding-model swap.
- A-2 (tentative): `129nj-enh agent-catalog-expansion` can stay bounded to reusable software-project specialists through universal/archetype gating without turning the framework into an unbounded agent library.
- A-3 (tentative): `129pc-enh wave-admit-relocates-change-doc` can be implemented as a contract correction within the existing wave lifecycle rather than a broader lifecycle redesign.
- A-4 (tentative): `129q6-enh mcp-index-watch-control` can land an immediate mutation-triggered background freshness path in this wave without requiring the full watcher-control surface to be implemented first.

## Outputs Produced or Expected

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/` updates for docs-search and lifecycle mutation behavior
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/build-and-verification.md`
- `docs/agents/` catalog, role-definition, and routing updates
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/150-refresh-wavefoundry.prompt.md`
- lifecycle prompt updates under `docs/prompts/` for add/prepare/remove wave behavior as required
- `.wavefoundry/bin/` launchers for docs-lint / docs-gardener (and related packaging paths) per `12a1j-feat wavefoundry-bin-cli-wrappers`

## Review Checkpoints

- **Full wave review (2026-04-30): PASS**

  **Framework tests pass. Docs gate clean (`wave_validate` when using MCP, or `.wavefoundry/bin/docs-lint` for CLI-only verification).**

  **`129p7-bug mcp-docs-search-reliability` — PASS** — Offline-safe `docs_search` (structured diagnostics, lexical fallback); `wave_index_health` exposes stale/missing index diagnostics without O(repo) work on every query; spec and `build-and-verification.md` aligned with the health-tool recovery path.

  **`129nj-enh agent-catalog-expansion` — PASS** — Taxonomy and routing in `docs/agents/README.md` and `docs/agents/specialists/README.md`; per-specialist classification and rationale; role docs under `docs/agents/specialists/`; core reviewer/coordinator docs and seeds 050/100/150 updated consistently.

  **`129pc-enh wave-admit-relocates-change-doc` — PASS** — `wave_add_change` relocates change docs into the wave folder with structured failure modes; prepare/repair and duplicate diagnostics covered in tests; prompts, seeds, and lifecycle docs aligned.

  **`129q6-enh mcp-index-watch-control` — PASS** — MCP watcher control, mutation-triggered background freshness, `wave_index_build` with stats for project and framework layers; contract and architecture docs updated.

  **`12a0c-debt framework-script-code-quality` — PASS** — `_load_script` module caching, `run_validate` forwards `PROJECT_ROOT`, dead-code removal, fingerprint helper extraction, and related hygiene; tests green.

  **`12a0x-enh mcp-tool-annotations-and-search-limit` — PASS** — Tool `annotations` on registrations, search/list limits, `wavefoundry_mcp` server name, `isError` on error envelopes, and related MCP contract polish; tests green.

  **`12a17-feat multi-host-mcp-registration` — PASS** — `render_platform_surfaces.py` merges Wavefoundry stdio MCP into Cursor `.cursor/mcp.json` and preserves Junie/Claude paths; operator matrix docs updated.

  **`12a1j-feat wavefoundry-bin-cli-wrappers` — PASS** — `.wavefoundry/bin/docs-lint` and `docs-gardener` launchers; hooks and seeds aligned on MCP-primary agents + bin for hooks/CI; self-host policy B (no repo-root shims).

  **`12a46-enh mcp-round2-review-fixes` — PASS** — `wave_index_health` returns `status: "ok"` when computation succeeds but index is absent/stale; dry-run lifecycle skips `run_garden`; list totals and help-catalog hints aligned.

  **`12a4d-enh wave-audit-tool` — PASS** — `wave_audit` read-only aggregate (`wave` + `validation` + `index`, `ready` boolean, recovery `next_tools`); registered with `_READONLY_TOOL`; `core_tools` and `inspect_wave` chain updated; `test_server_tools.WaveAuditTests` covers healthy, lint-fail, index-absent, and no-wave paths; spec § Audit updated.

- **Prepare wave — readiness verdict (2026-04-30): READY**
  - `129p7-bug mcp-docs-search-reliability`: change doc relocated into the wave folder; required planning sections are complete; AC Priority is populated. Required review lanes recorded: architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, performance-reviewer; advisory lanes recorded: factor-12-admin-processes, factor-13-api-first; persona acceptance recorded: framework-operator. Change Status: `planned` -> `ready`.
  - `129nj-enh agent-catalog-expansion`: change doc relocated into the wave folder; required planning sections are complete; AC Priority is populated. Required review lanes recorded: architecture-reviewer and docs-contract-reviewer. Change Status: `planned` -> `ready`.
  - `129pc-enh wave-admit-relocates-change-doc`: change doc relocated into the wave folder; required planning sections are complete; AC Priority is populated. Required review lanes recorded: architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer; advisory lane recorded: factor-13-api-first; persona acceptance recorded: wave-coordinator persona. Change Status: `planned` -> `ready`.
  - Product-owner acknowledgment: framework-operator / engineering lead acknowledgment is required for the operator-facing MCP and wave-lifecycle contract changes in `129p7` and `129pc`; the operator requested both changes in this thread. `129nj` remains internal framework-role surface work and does not need separate product-owner acknowledgment.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129nj` scope refresh**
  - `129nj-enh agent-catalog-expansion`: broadened from a Wavefoundry-local specialist shortlist to a framework-wide, archetype-aware seed strategy. Required planning sections remain complete after the scope expansion; AC Priority remains populated and consistent with the updated requirements.
  - Required review lanes for `129nj` remain architecture-reviewer and docs-contract-reviewer. Persona acceptance is now also required from `framework-operator` because the change affects shared seeded operator-facing role and routing surfaces across target repositories.
  - `129p7-bug mcp-docs-search-reliability` and `129pc-enh wave-admit-relocates-change-doc` remain unchanged from the prior ready pass; their relocation state, AC Priority tables, and recorded review lanes still satisfy readiness.
  - Product-owner / framework-operator acknowledgment: the operator explicitly requested the broadened framework-wide scope for `129nj` in this thread; implementation remains blocked on the normal review and acceptance lanes, not on further planning.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129q6` admission**
  - `129q6-enh mcp-index-watch-control`: change doc relocated into the wave folder; required planning sections are complete; AC Priority is populated. Required review lanes recorded: architecture-reviewer, code-reviewer, qa-reviewer, docs-contract-reviewer, performance-reviewer; advisory lanes recorded: factor-12-admin-processes and factor-13-api-first; persona acceptance recorded: framework-operator.
  - The operator explicitly requested implementing mutation-triggered background indexing in the current wave. This is treated as active-wave scope expansion and is now staged correctly before repository-code edits.
  - `129p7`, `129nj`, and `129pc` remain ready with no placement drift introduced by the additional admission.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129q6` rebuild-tool scope refresh**
  - `129q6-enh mcp-index-watch-control`: scope expanded to include a first-class MCP manual index path (`wave_index_build`) in addition to watcher control and mutation-triggered background freshness.
  - The rebuild tool stays within the same indexing-control contract surface and does not alter required review lanes or protected-surface ownership.
  - This scope refresh was requested explicitly by the operator before implementation; the wave remains ready for repository-code work on the expanded `129q6` surface.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129q6` framework-rebuild scope refresh**
  - `129q6-enh mcp-index-watch-control`: scope expanded again so the manual MCP rebuild path covers both the active project index and the packaged framework seed/docs index.
  - This remains inside the existing index-maintenance contract and does not change required review lanes or serialization points beyond the existing `server.py` and operator-doc ownership.
  - The operator requested the framework-layer rebuild path explicitly after validating the shell-based framework indexer flow; the wave remains ready for repository-code work on the expanded `129q6` surface.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129q6` rebuild-stats scope refresh**
  - `129q6-enh mcp-index-watch-control`: scope expanded again so `wave_index_build` returns structured rebuild statistics instead of only raw subprocess output.
  - This stays within the same MCP index-maintenance contract and does not change review lanes beyond the existing indexing and docs surfaces already owned by `129q6`.
  - The operator requested auditable rebuild counts explicitly; the wave remains ready for repository-code work on the expanded `129q6` surface.
- **Prepare wave — readiness verdict (2026-04-30): READY after `129q6` generic include-prefix scope refresh**
  - `129q6-enh mcp-index-watch-control`: scope expanded again so additional project index roots are configured through generic `docs/workflow-config.json` path prefixes rather than a Wavefoundry-specific framework-code toggle.
  - This remains inside the indexing-control contract and mainly affects `indexer.py`, `setup_index.py`, `server.py`, workflow-config docs, and the seeding/refresh surfaces that own shared config schema.
  - The operator requested a generic, cross-project config shape explicitly; the wave remains ready for repository-code work on the expanded `129q6` surface.

- **Wave closure — seven requirements (2026-04-30): SATISFIED**

  1. **All changes complete or deferred:** All ten admitted changes are **`complete`**; none deferred.
  2. **Review lanes:** Required and advisory lanes reconciled in **Review Evidence** above and prior Prepare-wave checkpoints.
  3. **Docs-contract review:** Performed during the wave; `docs/specs/mcp-tool-surface.md` was updated for `wave_audit`, index control, and MCP-first validation. Closure pass: removed stale **Open Questions** entry implying `wave_audit` was undecided; added `openWorldHint: false` to the Audit bullet for parity with tool registration.
  4. **Chronology:** Wave **`Status: closed`**, **`Completed At: 2026-04-30`**, all **`Change Status: complete`** in **Changes** (see above).
  5. **Journal distillation:** `docs/agents/journals/wave-coordinator.md` updated with a **2026-04-30** closure capture listing all ten change IDs and the **`wave_audit`** preference; no separate persona journal entries were required.
  6. **Durable memory:** Promoted **`wave_audit`** landing guidance to `docs/references/project-context-memory.md` (**MCP audit landing**).
  7. **`session-handoff`:** Refreshed to post-closure state (see `docs/agents/session-handoff.md`).

- **Verification log (closure, 2026-04-30)**

  - `python3 -B .wavefoundry/framework/scripts/run_tests.py` — **PASS** (includes `WaveAuditTests` and `wave_audit` tool registration).
  - `.wavefoundry/bin/docs-lint` — **PASS** after doc edits in this closure pass.

- **Retrospective closure audit (2026-04-30): PASS**

  - Re-ran **`python3 -B .wavefoundry/framework/scripts/run_tests.py`** and **`.wavefoundry/bin/docs-lint`** — both **PASS** (no regressions since prior verification log).
  - **`wave_audit`:** contract, annotations, `wave_help` / `inspect_wave` wiring, and `test_server_tools.WaveAuditTests` paths reviewed against `12a4d`; healthy-path **`next_tools`** default documented in spec + change doc.
  - **Reports:** `docs/reports/reindex-2026-04-30.md` **archived** to `docs/waves/129p8 mcp-docs-search-reliability/reindex-2026-04-30.md` with **`## Reports`** summary below (strict `Close wave` hygiene).
  - **Process note:** `wave.md` **`Status: closed`** matches prior closure; `docs/waves/README.md` lifecycle prose still says **`completed`** while wave anchors use **`closed`** — both mean “not active”; no action required unless you want wording unified later.

## Journal Refs

- `docs/agents/session-handoff.md`

## Journal Watchpoints

- Watchpoint: `129p7` and `129pc` both modify `server.py` and `docs/specs/mcp-tool-surface.md`; keep one write owner on those files at a time.
- Watchpoint: `129q6` also modifies `server.py`, tests, and operator docs around background freshness; keep its writes serialized with `129p7` on indexing behavior and with `129pc` on lifecycle mutation tools.
- Watchpoint: `129nj` and `129pc` both modify `.wavefoundry/framework/seeds/` and `docs/prompts/`; protected-surface guard approvals and single-owner sequencing remain mandatory before implementation.
- Watchpoint: `129nj` now spans shared archetype routing and may require framework-native specialist definitions for Apple-platform or JVM/Spring repos if the imported external catalog is insufficient; record those additions explicitly before implementation broadens the seed surface further.
- Watchpoint: `12a17-feat multi-host-mcp-registration` edits `render_platform_surfaces.py` MCP merge paths; coordinate with `12a0c-debt framework-script-code-quality` and any concurrent hook/MCP render changes.
- Watchpoint: `12a1j-feat wavefoundry-bin-cli-wrappers` performs a guarded canonical seed sweep; avoid partial seed states and keep hook/MCP render edits serialized with `12a17` / `12a0c`.

## Completion Criteria

- `129p7-bug mcp-docs-search-reliability` implemented, reviewed, and all required ACs passing
- `129nj-enh agent-catalog-expansion` implemented, reviewed, and local plus seeded agent surfaces reconciled consistently
- `129pc-enh wave-admit-relocates-change-doc` implemented, reviewed, and lifecycle relocation behavior consistent across server, prompts, seeds, and tests
- `129q6-enh mcp-index-watch-control` implemented, reviewed, and mutation-triggered background freshness is documented and repeat-safe
- `12a17-feat multi-host-mcp-registration` implemented, reviewed, and multi-host MCP registration matrix is reflected in renderer output and operator docs
- `12a1j-feat wavefoundry-bin-cli-wrappers` implemented, reviewed, and `.wavefoundry/bin/` plus seed/bootstrap guidance are consistent with MCP-primary operator docs
- Required review-lane sign-offs for all non-deferred changes recorded in this wave record
- Protected-surface guard approvals obtained before any implementation edits to canonical seeds or prompt surfaces

## Handoff or Next-Wave Notes

- Keep `129p7` and `129pc` serialized around `server.py` and `docs/specs/mcp-tool-surface.md`.
- Keep `129q6` serialized with `129p7` around index freshness behavior and with `129pc` around lifecycle mutation handlers.
- If `129nj` expands beyond the planned seed touchpoints (`050`, `100`, `150`), record the rationale before broadening seed scope.
- Serialize `12a17-feat multi-host-mcp-registration` with other `render_platform_surfaces.py` edits (`12a0c` and hook renders) to avoid MCP JSON merge conflicts.
- Serialize `12a1j-feat wavefoundry-bin-cli-wrappers` with `12a17` / `12a0c` on `render_platform_surfaces.py`; run the `12a1j` seed sweep under `seed_edit_allowed` in one guarded window.

## Wave Summary

**Delivered**

- **Docs search & index health (`129p7`):** Offline-safe `docs_search` with structured diagnostics and lexical fallback; `wave_index_health` for explicit stale/missing layer reporting without indexing every query; `setup_index` hardening for model cache expectations.
- **Agent catalog (`129nj`):** Supported specialist taxonomy, archetype routing, `docs/agents/specialists/` corpus, and seed parity (`050` / `100` / `150`).
- **Lifecycle relocation (`129pc`):** `wave_add_change` moves admitted change docs into `docs/waves/<wave-id>/`; `wave_prepare` validates and repairs placement; tests and prompts aligned.
- **Index control (`129q6`):** Watcher MCP controls, mutation-triggered background freshness, `wave_index_build` (project + framework layers) with structured stats, generic `indexing.project_include_prefixes` wiring.
- **Framework script quality (`12a0c`):** Caching, env forwarding, dead-code removal, fingerprint helper, docstrings as scoped.
- **MCP annotations round 1 (`12a0x`):** Annotations, limits, server rename, `isError`, `Literal` kinds on `docs_search`, dry-run modes on garden/sync.
- **Multi-host MCP registration (`12a17`):** Generated `.cursor/mcp.json` merge plus matrix documentation for other hosts.
- **Bin CLI wrappers (`12a1j`):** `.wavefoundry/bin/` launchers, hook templates, seeds, and docs on MCP-primary vs bin for hooks/CI.
- **MCP round-2 fixes (`12a46`):** Health `status: "ok"` semantics, dry-run garden skips, list `total`, help hints, `docs_search` kind normalization.
- **`wave_audit` (`12a4d`):** Single read-only MCP tool combining wave state, `wave_validate` output, and index `semantic_ready`; `next_tools` recovery; `_READONLY_TOOL` annotations; tests and spec.

**Deferred**

- None in-wave.

**Key decisions**

- Self-host **policy B:** no repo-root `./docs-lint` / `./docs-gardener`; `.wavefoundry/bin/` + MCP for agents.
- Index recovery split: explicit **`wave_index_health`** / **`wave_index_build`** rather than inferring failure only from search.
- **`wave_audit`** is the preferred combined readiness check; individual tools remain for targeted debugging.

**`wave_audit` validation note (closure review)**

- **Contract:** `wave_audit_response` aggregates `current_wave` (or prefix-matched wave), `run_validate`, and `index.docs_health()`; returns `_response("ok", {ready, wave, validation, index}, ...)`. **`ready`** is true only when a wave exists (active or planned for default path; explicit `wave_id` match uses the same status set), lint passes, and **`semantic_ready`** is true — matches spec and `12a4d` AC-2 (interpreted as active/planned per `current_wave` semantics).
- **Read-only:** Handler does not call mutating helpers or `wave_index_build`.
- **Annotations:** Tool uses `_READONLY_TOOL` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` all set per `_READONLY_TOOL` dict).
- **Discovery:** `wave_audit` is in `_help_catalog["core_tools"]` and **`inspect_wave.recommended_chain`** leads with `wave_audit`.
- **Tests:** `test_healthy_state_returns_ready_true`, `test_lint_fail_path`, `test_index_absent_path`, `test_no_active_wave_path`; `ServerToolRegistrationTests` asserts `wave_audit` is registered.

## Reports

- **`reindex-2026-04-30.md`** (archived in this folder) — docs-gardener pass that stamped **`Last verified:`** on the listed Wavefoundry `docs/` surfaces during this wave (reliability, architecture, contributing, prompts, references, personas). No anomalies beyond routine metadata refresh.
