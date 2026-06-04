# 010 - Init Wave Framework (Shortcut router)

**Primary:** **`Init wave framework`**. **Backwards-compatible:** **`Install Wavefoundry`**, **`Install wave framework`**, **`Init wave context`**, **`Install wave context`** — identical behavior; keep accepting them from operators and older docs.

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

When the repository already has an installed Wave Framework layer, hand off to **`Upgrade wave framework`** / **`Upgrade wave context`** (`seed-160`) instead of re-running bootstrap as init. Detection runs as part of agent entry — `seed-011` row 1.2's setup script handles the upgrade-detection branch.

## Authoritative content moved

The original seed-010 body (15-step sequence, execution contract, operator summary, required outputs list) has moved as follows:

- Phase 1 steps + execution contract → `seed-011-install-wavefoundry-phase-1`
- Phase 2 steps + operator summary → `seed-012-install-wavefoundry-phase-2`
- Required outputs list → `docs/references/project-overview.md` after the project's own install completes
- Install state machine + row format + trustworthy invariant → `docs/references/install-log-format.md`

If you came here from a doc that referenced seed-010 for a specific topic (e.g., "see seed-010 for the metadata block"), the topic now lives in one of the phase seeds or the install-log-format doc. Search those first.

## Discoverability

This seed remains the canonical entry for the shortcut phrase. Internal references to "install seed" can keep pointing here; the router will forward.
