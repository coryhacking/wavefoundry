# Wavefoundry Docs

Owner: Engineering
Status: active
Last verified: 2026-04-28

This folder is Wavefoundry's self-hosted Wave Framework project operating surface. Framework seed prompts and reusable framework reference material live under `framework/seeds/`. Project-local docs (plans, waves, architecture notes, agent roles, journals) live here.

## Documentation Boundaries

- `README.md` at the repository root explains Wavefoundry as the product.
- `AGENTS.md` gives agents repository-level operating instructions, shortcuts, and stage gate.
- `framework/README.md` maps the canonical Wave Framework seed pack.
- `framework/seeds/` contains framework source material.
- `framework/scripts/` contains framework tooling.
- `docs/` is Wavefoundry's self-hosted project operating surface.

## Documentation Map

| Section | Path | Purpose |
|---------|------|---------|
| Project overview | `docs/references/project-overview.md` | Orientation, workflow, roles |
| Architecture | `docs/ARCHITECTURE.md` | Hub + child docs |
| Plans (in-flight) | `docs/plans/` | Change docs before wave admission |
| Waves (admitted) | `docs/waves/` | Wave records and admitted change docs |
| Contributing | `docs/contributing/` | Workflow, build, review, lifecycle |
| Prompts (public) | `docs/prompts/index.md` | Shortcut phrase catalog |
| Agent roles | `docs/agents/README.md` | Role docs |
| Personas | `docs/agents/personas/` | Project-specific persona docs |
| Journals | `docs/agents/journals/` | Episodic memory for roles/personas |
| References | `docs/references/` | Project context memory, roles, tech debt |
| Quality | `docs/QUALITY_SCORE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md` | Quality posture |

## Near-Term Docs To Add

- `docs/specs/mcp-tool-surface.md` — MCP tool contracts (once server is scaffolded)
- `docs/architecture/decisions/DEC-001-self-hosting-symlink.md` — ADR for symlink approach
- `docs/contributing/docs-maintenance.md` — doc freshness and metadata policy
