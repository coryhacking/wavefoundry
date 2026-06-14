# Install Assets Map

Owner: Engineering
Status: active
Last verified: 2026-06-13

The single index of every Wavefoundry **install-related asset** — where each one lives and the role it plays. The framework-side install assets are consolidated under `.wavefoundry/framework/install/`; each plays a role in the **source → ship → provision** flow. Use this page to find an install asset and understand its role before moving or editing one.

## How install assets flow

Wavefoundry is developed in this repository (the framework **source**) and shipped to target projects:

- **Source** — authored under `.wavefoundry/framework/` (and, for the self-host's own canonical copies, under `docs/`).
- **Ship** — `build_pack` carries the framework tree (including the shipped reference-doc templates) into the distribution zip.
- **Provision** — the install/upgrade seeds copy the shipped templates into a target project's working tree on first install.

An asset's location is wired into its consumers (`build_pack` constants, `server_impl`, `install_log_lib`, the provisioning seeds), so moving one means updating those references in the same change (wave `1p591` consolidated the install assets under `.wavefoundry/framework/install/` and updated every consumer). The canonical format specs additionally keep a project copy under `docs/references/` — the self-host canonical, held byte-identical to the shipped template.

## Asset inventory

| Asset | Role | Lives at | Consumed by |
| --- | --- | --- | --- |
| Install-flow seeds | Framework source of the two-phase install prompt | `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`, `011-install-wavefoundry-phase-1.prompt.md`, `012-install-wavefoundry-phase-2.prompt.md` | Seed authoring/rendering; install/upgrade flow |
| Install-prompt surface | The project's install prompt (lint-required surface) | `docs/prompts/install-wavefoundry.prompt.md` | Docs lint (core validators); operators invoking "Install Wavefoundry" |
| Bootstrap entry point | Agent-readable file the operator extracts at repo root to start the install | `.wavefoundry/framework/install/install-wavefoundry.template.md` | `build_pack` (ships in zip) |
| Install-log template | Scaffold for the install-log state machine | `.wavefoundry/framework/install/install-log.template.md` | `build_pack` (ships in zip); referenced by `server_impl`, `install_log_lib` |
| Install-log live state | Operator-owned install log, copied from the template on first install; **never shipped** | `.wavefoundry/install-log.md` (target project) | install/upgrade flow; `wave_install_audit` |
| Install-log format spec | Canonical schema for the install log | canonical: `docs/references/install-log-format.md` · shipped template: `.wavefoundry/framework/install/install-log-format.md` | `install_log_lib`, `server_impl`, install seeds; provisioned to targets (`1p4dc`) |
| Scan-findings format spec | Canonical schema for secrets-scan findings | canonical: `docs/references/scan-findings-format.md` · shipped template: `.wavefoundry/framework/docs/scan-findings-format.md` (a secrets reference, not an install asset) | secrets flow; provisioned to targets (`1p455`) |
| Release-notes install block | The "Install" snippet embedded in release notes | `.wavefoundry/framework/install/install-block.md` | `build_pack` (`RELEASE_NOTES_INSTALL_BLOCK_REL`) |

## The shipped-template ↔ canonical invariant

For each format spec the **shipped framework template** (`.wavefoundry/framework/install/install-log-format.md`; `.wavefoundry/framework/docs/scan-findings-format.md`) must stay **byte-identical** to its **canonical copy** under `docs/references/`. The framework copy is what `build_pack` ships and the seeds provision into target projects; if the two drift, installed projects receive a stale schema. This is an intentional source-vs-shipped pair, not accidental duplication.

- **Guarded by** `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py`, which fails if any shipped reference doc drifts from its canonical copy.
- Because the pair must match byte-for-byte, neither file carries an inline pointer back to this index — this page is the single map instead.
