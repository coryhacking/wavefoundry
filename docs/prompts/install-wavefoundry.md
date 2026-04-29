# Init Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Init wave framework`** | Legacy: **`Init wave context`**

## Purpose

Initialize a target repository with the Wave Framework operating surface. Detects existing state first: if the repository is already seeded, hands off to **Upgrade wave framework** instead of re-running init.

## What Init Does

1. Reads the run contract (seed-020) and builds an evidence base (seed-030): `docs/repo-index.md`, `docs/repo-profile.json`.
2. Detects existing Wave Framework state. If already installed, routes to **Upgrade wave framework**.
3. For greenfield repos (no prior context): skips baseline wave; proceeds directly to bootstrap.
4. For repos with legacy corpus (pre-wave plans/specs): captures and closes a `00000 wave-zero-plans-and-specs` baseline wave before bootstrapping.
5. Bootstraps the full Wave Framework operating surface: docs structure, agent entry files, architecture docs, quality posture, prompt surface, wave artifacts, personas, and journals.
6. Delivers an operator summary covering what was seeded, the workflow, commands, roles, and docs gate.

## Required Outputs

See `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md` for the complete required output list.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## Aliases

- **Install wave framework** / **Install wave context** — accepted; routes to init (greenfield) or upgrade (already seeded)
- **Init wave context** — legacy alias; identical behavior
