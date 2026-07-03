# 010 - Init Wavefoundry (Shortcut router)

**Primary:** **`Init Wavefoundry`**. **Backwards-compatible:** **`Install Wavefoundry`**, **`Init wave framework`**, **`Install wave framework`**, **`Init wave context`**, **`Install wave context`** — identical behavior; keep accepting them from operators and older docs.

This seed used to carry the full install body. As of wave `1p35d` (1.5.0), install is restructured into two phases backed by a markdown-native state machine. **The install body now lives in seeds 011 and 012.**

## Where the work happens

| Phase | Seed | When MCP is available | Scope |
|---|---|---|---|
| 1 — Harness | `seed-011` | NO (this phase installs MCP) | venv, deps, bin/ launchers, host configs, framework + project indexes, MCP-server-can-start check, restart-agent marker |
| 2 — Project discovery | `seed-012` | YES (restart between phases) | architecture, agents, personas, prompt surface, docs gate, journals, drift expectations, final completion check |

## Where the state lives

The install state machine is `wavefoundry-install-log.md`, a pre-populated checkbox list that ships at the zip root next to `install-wavefoundry.md` (the agent-readable entry doc). The agent reads the first unchecked row, executes the named seed step, marks `[x]`, advances. After the restart between phases, Phase 2 uses `wave_install_audit` for end-to-end validation.

## How to enter

- **From a fresh zip** (the common case): operator extracts the zip into their repo root. Agent finds `install-wavefoundry.md` and follows the install log.
- **From the shortcut phrase** (`Install Wavefoundry` etc.): if the install log already exists, continue from the first unchecked row. If the install log doesn't exist (rare — only when the entry doc was deleted), regenerate it from `.wavefoundry/framework/templates/wavefoundry-install-log.md.template`.
- **Mid-install resumption**: a new agent session entering this surface MUST call `wave_install_audit` first to confirm the log's `[x]` markers actually have their expected artifacts. The trustworthy-invariant rule is captured in `docs/references/install-log-format.md`.

## What about Upgrade?

When the repository already has an installed Wave Framework layer, hand off to **`Upgrade Wavefoundry`** (legacy: **`Upgrade wave framework`** / **`Upgrade wave context`**) (`seed-160`) instead of re-running bootstrap as init. Detection runs as part of agent entry — `seed-011` row 1.1's setup script handles the upgrade-detection branch.

## Authoritative content moved

The original seed-010 body (15-step sequence, execution contract, operator summary, required outputs list) has moved as follows:

- Phase 1 steps + execution contract → `seed-011-install-wavefoundry-phase-1`
- Phase 2 steps + operator summary → `seed-012-install-wavefoundry-phase-2`
- Required outputs list → `docs/references/project-overview.md` after the project's own install completes
- Install state machine + row format + trustworthy invariant → `docs/references/install-log-format.md`

If you came here from a doc that referenced seed-010 for a specific topic (e.g., "see seed-010 for the metadata block"), the topic now lives in one of the phase seeds or the install-log-format doc. Search those first.

**Design-system mode selection (wave `1p799`).** Before seeding the extraction contract, consume `docs/repo-profile.json` `design_system.mode` (set by `seed-030` from the deterministic `classify_design_system_mode(design_evidence)` classifier — `bootstrap` / `extract-mirror` / `adopt` / `ambiguous`):

- **bootstrap** → emit the nulls skeleton (no-design-system path).
- **extract-mirror** → seed the full extraction tree (current behavior) and set up the token-build pipeline below.
- **adopt** → seed the **thin reference index** (`manifest.json` with `externalReference`, `source-map.json` pointers, `AGENTS.md` retargeted to the project's `consumptionDoc`/`varPrefix`, `gaps.md`, `README.md`); `sourceStrategy: external-reference`; do **not** extract a parallel `tokens/`/`exports/` mirror, and do not set up the token-build pipeline. The full schema + thin-tree + derived-`AGENTS.md` rules live in `seed-040` task 14.
- **ambiguous** → **ask the operator** which mode applies before seeding; never silently adopt or mirror on weak evidence. **Decline path:** if the operator says the project owns its system, choose `adopt` (thin reference); if they want extraction, choose `extract-mirror`.

Never overwrite or duplicate an existing design system — adopt-in-place defers to it.

**Design-system token-build pipeline setup (wave `12atj`).** When `docs/design-system/` is seeded in `extract-mirror` mode (or `hybrid` with an extracted tree), the install must also set up the token-build pipeline: detect `docs/design-system/build.config.json` and emit the default stub (`tool: "style-dictionary"` + the four standard targets) only when absent, seed the `docs/design-system/bin/build-tokens` wrapper, and instruct the operator to run `bin/build-tokens` to generate `exports/` after installing the chosen tool. The full contract (config schema, wrapper behavior, default targets, `manifest.json` export-parity fields) lives in `seed-040` task 14; the upgrade backfill is in `seed-160`. Under `external-reference` (adopt) mode there is no token-build pipeline — the project builds its own tokens.

## Discoverability

This seed remains the canonical entry for the shortcut phrase. Internal references to "install seed" can keep pointing here; the router will forward.
