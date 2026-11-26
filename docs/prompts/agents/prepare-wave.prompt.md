# Agent Body — Prepare Wave

Owner: Engineering
Status: active
Last verified: 2026-11-25

## Context

You are running **Prepare wave** on Wavefoundry. This is the stage gate for implementation.

## Steps

1. Validate that all admitted specs already live in `docs/waves/<wave-id>/`; repair any staged-only doc by moving it there, and stop on duplicate staged + wave copies.
2. Verify each spec has: Rationale, Requirements, Scope, Acceptance Criteria, Affected architecture docs.
3. Select review lanes (see `docs/contributing/agent-team-workflow.md`).
4. For ordinary review, include `qa-reviewer` for bug fixes when project policy requires QA. For an eligible small change, use the independent `code-reviewer` named by Prepare.
   For readiness, collect one assigned independent reviewer’s prediction before sharing the primer or separate answer-bearing material with that reviewer. Prefer QA when assigned. Use the two exchanges in the council-chair guidance and keep the original prediction in ordinary readiness evidence.

5. When the receipt requires `council-readiness`, run the Wave Council readiness pass: declare a primer depth tier (`lightweight` / `standard` / `full`), run `red-team` in `council-adversarial-primer` mode first, then fixed seats each receiving the primer, then `council-chair` synthesizes; record `council-readiness` in `## Review Evidence`.
6. Record `## AC priority` on each spec.
7. Record readiness verdict in wave record `## Review checkpoints`.
8. Use `wf_prepare_wave(mode='ready')` to record readiness. Activation is a separate step.

## Ordinary review lanes for Wavefoundry

| Change Type | Required Lanes |
|-------------|--------------|
| Framework seed edit | architecture-reviewer, docs-contract-reviewer |
| Framework script | code-reviewer, qa-reviewer |
| MCP tool contract | architecture-reviewer, docs-contract-reviewer |
| Packaging / build | code-reviewer, release-reviewer |
| Bug fix | qa-reviewer (required by policy) |

When the receipt requires readiness Council, `red-team` runs first as the adversarial primer (Phase 1) before any other seat; fixed Phase 2 seats are `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker` — each receives the primer and must engage with it; the fifth seat rotates from wave evidence.

## Guru Orientation

During scope assessment (step 2), use Guru to answer "what does X currently do?" and "which files are affected?" without launching full file reads:

```
code_search(topic, kind="code-summary", limit=5) # which modules are in scope?
code_dependencies(path) # what does the target file import/export?
code_ask("what are the entry points for X?") # cross-cutting questions; use final_rank/demoted to interpret reordered citations
```

This speeds up the Affected Architecture Docs check and helps select accurate review lanes. If MCP is not available, use `grep -n "^import\|^from" <path>` for dependencies and `grep -r "keyword" .` for module discovery.

## Product-Owner Acknowledgment

Wavefoundry has no external product owner. Record `product-owner: N/A — internal framework tooling` for all changes unless the change affects published API contracts or distribution format (in which case the engineering team lead acts as product-owner).
