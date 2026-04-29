# Agent Team Workflow

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Role Routing

Wavefoundry uses the standard Wave Framework generic roles. The wave-coordinator allocates roles to each admitted change based on change type.

### When to Invoke Each Role

| Role | Invoke when |
|------|------------|
| `planner` | Drafting a consolidated change doc; discovery; planning a wave shape |
| `wave-coordinator` | Admitting changes; managing execution order; closing waves |
| `implementer` | Executing code changes per admitted change doc |
| `code-reviewer` | Any implementation change (mandatory for non-trivial code changes) |
| `architecture-reviewer` | Changes touching module boundaries, integration contracts, or data flow |
| `qa-reviewer` | Bug fixes (required); any change with acceptance criteria requiring test coverage |
| `security-reviewer` | Changes touching trust boundaries, allowed-roots logic, or guard mechanisms |
| `docs-contract-reviewer` | Changes touching `docs/specs/*.md` behavioral contracts |
| `performance-reviewer` | Changes touching indexing, search, or MCP server response paths |
| `release-reviewer` | Changes touching `build_pack.py`, VERSION stamping, or distribution format |

### Bug Fix Policy

`docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes: true` — all bug fixes admitted into a wave must include `qa-reviewer` in readiness and **Review checkpoints** before closure.

## Persona Agent Routing

| Persona | Invoke when |
|---------|------------|
| `framework-operator` | Spec authoring for install/upgrade behavior; MCP tool design review; acceptance of operator-facing changes |
| `wave-coordinator` (persona) | Spec authoring for wave lifecycle behavior; acceptance of wave execution changes |

## Factor-Review Agent Routing

| Factor Agent | Invoke when |
|-------------|------------|
| `factor-03-config` | Changes to configuration reading, defaults, or `docs/workflow-config.json` schema |
| `factor-05-build-release-run` | Changes to `build_pack.py`, VERSION, or distribution format |
| `factor-12-admin-processes` | Changes to CLI tool contracts or admin script behavior |
| `factor-13-api-first` | Changes to MCP tool surface contracts or tool response formats |

## Concurrency

See `docs/prompts/agent-routing-concurrency.md` for read-only vs write-owning lane rules and serialization points.

Protected surfaces that require single-lane ownership:
- `.wavefoundry/framework/seeds/` — seed edits require `seed_edit_allowed` guard approval; single write owner at a time
- `docs/prompts/` and `AGENTS.md` — framework-maintenance edits require `framework_edit_allowed` approval; single write owner
- `docs/workflow-config.json` and `docs/prompts/prompt-surface-manifest.json` — manifest/config writes require coordinator confirmation before parallel work proceeds
