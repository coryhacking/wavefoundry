# Declare distribution legacy council actors

Change ID: `204mm-enh declarable-legacy-council-actors`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-08
Wave: `204mp waveforge-follow-up`

## Rationale

Legacy signoff keys are extensible, but LEGACY_COUNCIL_ACTORS remains fixed. Distributions need to recognize their own previous council identity without rewriting historical evidence or changing the canonical write identity. Addresses Waveforge public request C4 against `d11da852`, received 2026-10-08. Deliverable: framework fixes, focused regression evidence and documented compatibility behavior. This document authorizes planning only; implementation follows admission and readiness.

## Requirements

1. Add an empty-by-default EXTRA_LEGACY_COUNCIL_ACTORS profile tuple; validate token shape and reject malformed declarations and collisions with active non-council reviewer/operator identities with actionable diagnostics. Treat repeated built-in or extra legacy aliases as idempotent duplicates rather than additional identities.
2. Merge declared aliases with built-in legacy actors deterministically, deduplicating entries and retaining council-chair as the canonical actor.
3. Use the merged set consistently for recognition, canonicalization, stored-identity replay and write-side conversion. Alias recognition must not bypass review roles, policy, evidence or operator authority checks. Repair-start and reverification under two spellings of the same council identity must still fail the distinct-actor guard; extra aliases must not alter the built-in moderator spelling used in policy digests.
4. Preserve historical ledgers byte-for-byte and preserve existing default-profile compatibility. Expose the seam through shipped profile support and reload behavior.

## Scope

In scope: the public request C4 and the declared review targets below.

Out of scope: other requests, native host hook classification, packaging skip-parity policy, publishing, release creation, and unrelated refactors.

## Acceptance Criteria

- [x] AC-1: A declared legacy actor is recognized and replayed as a council identity, and new evidence uses council-chair; undeclared actors remain unrecognized.
- [x] AC-2: Default aliases and historical replay remain compatible without rewriting stored ledgers, supported by before/after fixture comparison.
- [x] AC-3: Invalid declarations fail clearly; duplicate entries do not duplicate aliases; role and operator authority checks remain effective.
- [x] AC-4: A real reload observes changed profile declarations, and the shipped profile template documents the empty default and compatibility scope.

## Tasks

- [x] Add and validate the profile declaration and shipped defaults.
- [x] Wire merged aliases through all existing actor consumers and reload.
- [x] Exercise history replay, canonical writes, invalid aliases and authority negative controls.
- [x] Document the seam and collect independent code/QA and authority-boundary review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and fixtures | Implementer | Readiness | Own declared source/test edits only |
| Documentation | Technical writer | Contract | Own named documentation; coordinate shared files |
| Independent review | Code reviewer and QA reviewer | Implementation | Read-only review and evidence; additional lanes selected at Prepare |

## Serialization Points

One writer per shared file. Complete test-oracle repairs before consumers extend those tests; serialize `upgrade_extensions.py`, shared profile modules and the MCP surface specification across changes. Reviewers do not edit implementation files. Generated local surfaces are regenerated from canonical sources, never patched in lieu of seeds.

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_council_signoff_keys.py`
- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/architecture/cross-cutting-concerns.md: profile compatibility seam and review identity boundaries.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Direct evidence for the requested compatibility behavior |
| AC-2 | required | Direct evidence for the requested compatibility behavior |
| AC-3 | required | Direct evidence for the requested compatibility behavior |
| AC-4 | required | Direct evidence for the requested compatibility behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Planned from public report and current source inspection; not implemented or readied | Declared source targets and request C4 |
| 2026-10-08 | Readback: add validated empty-default distribution actor aliases; recognize/read/replay them as council-chair while preserving ledger bytes, operator/reviewer authority and repair independence. Example: a declared retired-chair input writes council-chair, but retired-chair and council-chair cannot verify each other after repair. | AC-1–4; vocabulary_profile, review_evidence, server_impl, record_layout_support, direct lifecycle_gate_support validation caller; standalone actor tests and affected profile-support pins avoid shared ownership. |
| 2026-10-08 | Thought: C1–C3 helper owns shared fixtures first; ground and implement the actor declaration/runtime validator in distinct files before consuming its released compatibility owner. Memory advisories require canonical authority, contained renderer I/O and preserved user bytes. | Current readiness receipt; MCP code_read/impact/reference grounding; memory_brief pre_implementation. |
| 2026-10-08 | Observe: declared aliases are merged once behind the existing recognition, approval wrapper, stored-identity lookup and repair-independence paths; current base/prepare/close and requested roles are validated before policy receipt creation. Actual MCP reload observes a changed on-disk declaration. | test_legacy_council_actors: 4 tests, 0 skips, 3.352s; test_legacy_council_actors + test_review_evidence + test_review_policy: 295 tests, 0 skips, 9.372s. New profile support pins updated; server_impl requires no edit because its existing reload purge and alias tuple import consume the new declaration. |

| 2026-10-08 | Observe: canonical merged-actor consumer now derives the expected alias tuple from profile inputs, including duplicate built-in declarations; documentation covers validation, replay, reload and identity boundaries. Five guard mutants fail named actor assertions. | Actor/merged-consumer final: 8 tests, 0 skips, 6.471s; profile/actor owner: 78 tests, 0 skips, 33.802s; /tmp/wf-204mp-actor-mutants.log; independent delivery review still pending. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Add a narrow profile alias tuple and reuse existing council canonicalization. | Preserve the requested behavior and existing compatibility boundaries | Hardcoding each distribution’s actor cannot scale; rewriting old ledgers changes evidence and is unnecessary. |

| 2026-10-08 | Preserve canonical actor equivalence through repair-independence checks as well as approval recognition. | review_evidence canonicalizes both actors in _reverification_independence_defect, while approval_status checks exact non-council actors. New aliases must not become a second repair identity or an operator/reviewer alias. | Wiring only displayed approvals leaves replay and independence inconsistent. |

## Risks

| Risk | Mitigation |
| --- | --- |
| An alias could accidentally widen approval authority. | Review identity recognition separately from authorization; request architecture and security review of the new seam. |

## Session Handoff

See `docs/agents/session-handoff.md`. Readiness must resolve the design choices named above before implementation.
