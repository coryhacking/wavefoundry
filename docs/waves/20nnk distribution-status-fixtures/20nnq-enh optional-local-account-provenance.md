# Allow projects to omit local-account review provenance

Change ID: `20nnq-enh optional-local-account-provenance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

Review publication resolves local OS-account attribution and stores it in verification_context.local_user; rendered rows display it when present. Projects should be able to omit this optional metadata without losing role approvals or contributor handles.

## Requirements

1. Add the validated optional boolean `wave_review.record_local_account` in `docs/workflow-config.json`, defaulting to existing enabled behavior when absent. A false value omits local-account metadata rather than hashing it. Validate a present value without inserting an absent default into the normalized policy or changing digest canonicalization.
2. When disabled, avoid local-account lookup and omit local_user from new event verification contexts, derived rows and response metadata; no substitute identifier or warning should disclose the omitted account.
3. Preserve role/lane authority, contributor-handle and self-attestation semantics, idempotent event replay, and missing-attribution compatibility.
4. Do not rewrite immutable historical events. Explain that opting out affects new events, not already published Git history, and existing records remain readable under either setting.
5. Keep the setting project-owned through defaults/render/upgrade; no added external identity service, machine secret, account database or consumer-upgrade migration scan.

## Scope

Config validation/default documentation, review-event enrichment and rendering, identity/publication tests. No identity verification claim, salted identifiers, automatic history redaction or signature authority.

## Acceptance Criteria

- [x] AC-1: With the setting disabled, registered review publication performs no OS-account lookup and emits no new local_user metadata while the same approval semantics remain available.
- [x] AC-2: Absent/enabled settings preserve existing attribution; invalid setting types refuse through the normal config diagnostic.
- [x] AC-3: Existing attributed and unattributed records remain readable, and retries preserve event identity without duplicate events or historical rewrites.
- [x] AC-4: Defaults, upgrade/render behavior and documentation preserve the project choice and clearly explain prospective omission.

## Tasks

- [x] Validate `wave_review.record_local_account` through the existing review-policy config owner; update defaults and documentation surfaces.
- [x] Apply opt-out before lookup/enrichment and exercise rendering and retry behavior.
- [x] Validate enabled, disabled, legacy and malformed controls; record immutable-history limitations.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/operator_identity.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_operator_identity.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/install/workflow-config.defaults.json`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/architecture/cross-cutting-concerns.md: optional provenance, configuration ownership and unchanged authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |

| 2026-10-14 | Readback: Add optional boolean wave_review.record_local_account; absent keeps current behavior at lookup only, false avoids new local account lookup/metadata, and malformed values refuse. Do not insert an absent default or alter policy digest normalization; preserve user choice through render/upgrade and preserve original replay attribution. | Admitted policy, server, identity/review tests, default/config documentation and MCP/threat docs. Prospective choice only, no historical redaction or authentication claim. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select a backward-compatible boolean opt-out that omits new local-account metadata. | Provide a workflow-config opt-out for newly recorded OS-account provenance while preserving review authority and existing records. | Hash accounts: requires stable salt ownership and remains identifying metadata. Remove attribution for every project: reverses existing operator intent and behavior without need. |
| 2026-10-14 | Place `record_local_account` under the existing `wave_review` object; an absent value means true without normalization insertion. | Existing policy validation already owns this object and preserves extra options; keeping absent config unchanged avoids incidental policy digest changes for existing projects. | A new top-level attribution object adds another validator/config owner for one boolean. Changing digest canonicalization would unnecessarily invalidate unrelated readiness. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | Retried events or legacy rows could reintroduce omitted metadata or lose integrity. Keep existing events immutable and test publication/row behavior independently. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
