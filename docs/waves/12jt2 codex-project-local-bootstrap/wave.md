# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-12

wave-id: `12jt2 codex-project-local-bootstrap`
Title: Codex Project-Local Bootstrap

## Objective

Add a project-local Codex bootstrap launcher that derives the server name from the checkout path hash, registers the Wavefoundry MCP server for that specific checkout, exposes a read-only server identity surface for attached agents, and keeps Claude Code on the existing repo-local auto-discovery path.

## Changes

Change ID: `12jt2-feat codex-project-local-bootstrap`
Change Status: `complete`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| code-reviewer | review | `12jt2-feat codex-project-local-bootstrap` — bootstrap launcher and render helper changes |
| qa-reviewer | review | `12jt2-feat codex-project-local-bootstrap` — launcher idempotence, name derivation, identity response, and docs surface verification |
| docs-contract-reviewer | review | `12jt2-feat codex-project-local-bootstrap` — install prompt, AGENTS matrix, and operator-facing Codex guidance |
| framework-operator | acceptance | `12jt2-feat codex-project-local-bootstrap` — per-project Codex startup flow, naming contract, and identity check |

## Dependencies

- The Codex CLI must be available on the operator's machine.
- The repository must already be initialized as a Wavefoundry target repo so the launcher can derive an absolute repo root.

## Review Evidence

- wave-council-readiness: approved (2026-05-12 — project-local Codex bootstrap launcher and per-repo naming strategy reviewed for operator fit)
- wave-council-delivery: approved (2026-05-12 — checkout-path bootstrap launcher, read-only server identity surface, launcher rendering, docs alignment, and targeted verification all complete)
- code-reviewer: approved (2026-05-12 — launcher generation, path hashing, and server identity response match the checkout-path contract)
- qa-reviewer: approved (2026-05-12 — launcher idempotence, server identity response, and render/test coverage verified)
- docs-contract-reviewer: approved (2026-05-12 — install and upgrade guidance updated to the hash-only Codex naming rule)
- framework-operator: acknowledged (2026-05-12 — Codex registration cleaned up under the new checkout-path name)
- operator-signoff: approved

## Journal Watchpoints

- Watchpoint: Codex still stores the attachment in `~/.codex/config.toml`; the new launcher exists so the repository owns the registration command and path derivation.
- Follow-up: every checkout uses a `wavefoundry-<hash>` server name derived from the absolute repo path.
- Follow-up: attached agents should call `wave_server_info()` first and confirm `repo_root` before relying on any other tool output.
- Watchpoint: keep the launcher deterministic and idempotent so reruns do not create drift in the user's Codex config.

Completed At: 2026-05-12

## Wave Summary

This wave will add a repo-local bootstrap launcher for Codex so each Wavefoundry checkout can register its own MCP server entry with a deterministic checkout-path name. The launcher will keep the repository-owned command and path derivation local to the checkout while preserving the current Claude auto-discovery path. Attached agents will also get a dedicated server identity response so they can confirm which repository the MCP server is serving.

## Completion Criteria

- A repo-local launcher exists that registers the Codex server for the current project.
- The launcher uses `wavefoundry-<hash>` for every checkout. That label is stable for a specific checkout path; moving or recloning the repo intentionally yields a different label.
- The MCP server exposes a read-only `wave_server_info` tool that reports the attached repository root.
- Docs explain how to use the launcher and where the Codex config still lives.
- Tests cover the launcher output, derived server name, and server identity response.

## Handoff or Next-Wave Notes

- Next lifecycle step is `Implement wave`.
