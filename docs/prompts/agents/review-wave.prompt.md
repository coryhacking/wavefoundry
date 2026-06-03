# Agent Body — Review Wave

Owner: Engineering
Status: active
Last verified: 2026-06-03

## Context

You are running **Review wave** on Wavefoundry.

## Wavefoundry Review Specifics

| Lane | What to Check | Prompt body |
|------|--------------|-------------|
| `code-reviewer` | Framework script correctness; pattern compliance; test coverage in `.wavefoundry/framework/scripts/tests/`; no project-specific guidance added to generic seeds | _(inline — see Wavefoundry Review Specifics)_ |
| `qa-reviewer` | AC coverage per `## AC priority` table; multi-step verification for stateful behavior; framework test suite passes | _(inline — see Wavefoundry Review Specifics)_ |
| `architecture-reviewer` | Module boundary violations; layering rules compliance; domain-map consistency | _(inline — see Wavefoundry Review Specifics)_ |
| `docs-contract-reviewer` | Behavioral spec consistency; manifest/VERSION alignment | _(inline — see Wavefoundry Review Specifics)_ |
| `release-reviewer` | VERSION stamp correctness; zip naming semantics; gitignore coverage | _(inline — see Wavefoundry Review Specifics)_ |
| `performance-reviewer` | Algorithmic complexity on hot paths (chunker, indexer, query); O(n) per-file model; pre-compiled regex constants; bounded in-memory structures | `docs/prompts/agents/performance-reviewer.prompt.md` |
| `security-reviewer` | Path confinement on file-access tools; `re.escape` on symbol interpolation; write-path constraint on read-only tools; untrusted content handling | `docs/prompts/agents/security-reviewer.prompt.md` |

When `wave_review.enabled` is true, Wavefoundry also requires a delivery-phase council pass. The `wave-council` first declares a primer depth tier (`lightweight` / `standard` / `full`) based on trust boundaries touched and change scope; `red-team` then runs the adversarial primer (`council-adversarial-primer` mode) in isolation at that depth (Phase 1); fixed seats each receive the primer and must engage with it before producing findings (Phase 2); `wave-council` synthesizes all outputs and records `wave-council-delivery` in `## Review Evidence` and the tradeoffs in `## Review checkpoints`.

## Guru Orientation

All reviewer lanes have direct access to Guru tools — use them to verify claims without reading entire files:

| Need | Tool |
|------|------|
| Jump to a symbol definition | `code_definition(symbol)` |
| Find all call sites | `code_references(symbol)` |
| Check module boundaries and imports | `code_dependencies(path)` |
| Confirm test coverage for a symbol exists | `code_keyword(symbol)` |
| Orient to module shape before reviewing | `code_search(topic, kind="code-summary")` |

If MCP is not available, use `grep -rn "symbol" .` for references and `grep -n "^import\|^from" <path>` for dependencies. Cite results as `path:line_number`.

## AC Priority Reconciliation

Update the `## AC priority` table if scope shifted during implementation. `qa-reviewer` must attest every required row has verification evidence or a recorded deferral.

## Findings Classification

- Level 1: fix internally, no log entry
- Level 2: fix and re-run reviewer, no re-Prepare
- Level 3: scope or plan invalidation → stop and re-Prepare
