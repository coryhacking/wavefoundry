# Agent Body — Review Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Review wave** on Wavefoundry.

## Wavefoundry Review Specifics

| Lane | What to Check |
|------|--------------|
| `code-reviewer` | Framework script correctness; pattern compliance; test coverage in `framework/scripts/tests/`; no project-specific guidance added to generic seeds |
| `qa-reviewer` | AC coverage per `## AC priority` table; multi-step verification for stateful behavior; framework test suite passes |
| `architecture-reviewer` | Module boundary violations; layering rules compliance; domain-map consistency |
| `docs-contract-reviewer` | Behavioral spec consistency; manifest/VERSION alignment |
| `release-reviewer` | VERSION stamp correctness; zip naming semantics; gitignore coverage |

## AC Priority Reconciliation

Update the `## AC priority` table if scope shifted during implementation. `qa-reviewer` must attest every required row has verification evidence or a recorded deferral.

## Findings Classification

- Level 1: fix internally, no log entry
- Level 2: fix and re-run reviewer, no re-Prepare
- Level 3: scope or plan invalidation → stop and re-Prepare
