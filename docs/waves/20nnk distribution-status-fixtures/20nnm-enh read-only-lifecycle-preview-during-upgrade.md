# Permit genuinely read-only lifecycle previews during an upgrade

Change ID: `20nnm-enh read-only-lifecycle-preview-during-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-14
Wave: `20nnk distribution-status-fixtures`

## Rationale

The outer upgrade guard classifies registered publishers by tool name before interpreting their requested mode. Dry-run requests are therefore refused. Some nominal previews also refresh observations or telemetry, so a blanket mode-name exemption would not establish a read-only path.

## Requirements

1. Derive eligible core previews from registered lifecycle handlers whose documented dry_run/evaluate branches can execute without target publication. Start with Prepare and close; inventory other advertised preview modes and explicitly document eligibility or refusal.
2. Separate read-only evaluation from scanner observations, review receipts/projections, events, memory, telemetry publication, index changes and extension completion side effects. Preserve the retained checkpoint, source files and lifecycle state.
3. Resolve actual canonical tool/mode arguments, including supported aliases and positional/default handling, before using a preview exception. Unknown modes, extension writers and mutation requests retain the existing guard.
4. Use installed current code only when its readiness/compatibility checks permit inspection. Corrupt or incompatible state yields a clear bounded refusal; a preview is advisory and cannot authorize later writes or claim upgraded runtime readiness.
5. Keep mutation, memory-recovery and publication lock ordering unchanged. Add no automatic upgrade continuation, model download, new checkpoint or repeated reporting scan.

## Scope

Registered lifecycle preview dispatch, publication classification and affected observation/accounting boundaries, with registered-path tests and contract docs. No blanket bypass of upgrade guards, arbitrary extension preview execution or live pending-run fabrication.

## Acceptance Criteria

- [x] AC-1: Eligible Prepare/close preview calls return a bounded assessment during a valid pending upgrade without changing target checkpoints, records, review state, memory, index or telemetry publications.
- [x] AC-2: Equivalent canonical/alias requests behave consistently; mutation modes, unknown modes and undeclared extension writers remain refused.
- [x] AC-3: Corrupt/incompatible retained state refuses with actionable guidance and remains unchanged; stale preview output cannot authorize a later mutation.
- [x] AC-4: Existing no-upgrade preview and real mutation paths retain their validation and publication behavior.

## Tasks

- [x] Inventory preview mutations and registered wrapper ordering; declare the exact eligible core set and refused cases.
- [x] Implement a strictly read-only evaluation route and preserve write/recovery guards and callback boundaries.
- [x] Exercise actual registered tools under valid, corrupt, aliased and mutation controls; update preview documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | Readiness approval | Sole source write owner |
| Independent review | Required specialist lanes | Reviewable implementation | Read-only; report findings to coordinator |

## Serialization Points

Only the implementer edits the declared targets after readiness. Reviewers are read-only; the coordinator owns lifecycle records. Shared runner, server, policy, seed and prompt changes serialize with adjacent waves. Seed/default/prompt changes require existing edit guards and renderer ownership; do not hand-edit generated regions.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/publication_control.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `.wavefoundry/framework/scripts/tests/test_index_upgrade_guard.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_gates_structure.py`
- `.wavefoundry/framework/scripts/tests/test_tool_surface_golden.py`
- `.wavefoundry/framework/scripts/tests/test_mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

The reload inventory must include the newly imported storage_identity and upgrade_protocol dependencies, preserving supported post-reload preview behavior. Keep exact refusal classification, wrapper arguments and keyless-provenance documentation synchronized; changed handler pins are refreshed selectively after shared handler edits settle. Existing negative assertions remain intact.

## Affected Architecture Docs

docs/specs/mcp-tool-surface.md and docs/architecture/data-and-control-flow.md: preview scope, upgrade ownership and side-effect boundaries.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-2 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-3 | required | Establishes the scoped behavior or preserves its boundary. |
| AC-4 | required | Establishes the scoped behavior or preserves its boundary. |

## Progress Log

Readback: Repair the final reload integration assertion by moving the two new unordered set members after public_contract in server_impl.py. Preserve all members, control flow and existing assertions; verify the named assertion, structural closure and missing-member negative control. No preview behavior, review target or requirement changes. Final qualification remains pending; timing is deferred by the operator.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-14 | Planned from current source inspection; implementation and qualification pending. | Requirements and declared review targets above. |
| 2026-10-14 | Thought: Standard-depth independent readiness council checks the six-change packet, especially actual preview completion side effects and retained-upgrade identity. Current available reasoning model retained for boundary analysis; one fresh seat at a time while the preceding wave's sole implementer works. | Read-only primer, fixed seats and rotating docs-contract; finite scratch controls only, no live checkpoint changes or full suite. |
| 2026-10-14 | Observe: Reconciled the exact docs-lint owners required by the existing read-only preview contract. check_hardcoded_secrets publishes both scanner skips and findings; record_only does not suppress publication, and CLI migration-audit output is another write. Added CLI, secrets validator and their existing tests to review targets. | Focused readiness owner review checks explicit full-lint nonpublication, truthful findings, rejection of incompatible write/incremental modes, and unchanged ordinary lint publication. No requirement or AC expansion. |

| 2026-10-14 | Readback: Permit only audited core Prepare dry_run/evaluate and close-wave dry_run, including actual aliases, after bounded compatible-checkpoint and current-code checks. Full lint uses explicit nonpublication while returning newly found secrets truthfully; reject incompatible changed/advisory/audit-write combinations. Suppress scanner-ledger, callbacks, focus, accounting, index and model side effects. | Admitted publication, server, CLI, secrets validators, registered tests and contract/dataflow docs. Other modes/extensions remain guarded; no resume, pack hashing or checkpoint fabrication. Exact retained-state predicate derives from existing producers. |

| 2026-10-14 | Observe: Actual registered preview and real lint-child controls pass, including target byte preservation, aliases/default/positional modes, copied-marker override refusal, malformed/current-code checks, one-pass unpublished secrets, and ordinary no-upgrade behavior. Fifteen total wave guard/source mutants are detected; final separate per-file focused selections pass 54 tests, zero skips. | Review packet fingerprint and final limitations consolidated in wave.md. Source frozen; full qualification and independent delivery review remain pending. |

| 2026-10-14 | Combined qualification found missing reload inventory entries for the two new preview dependencies, plus unpropagated diagnostic/wrapper/handler contracts. Reopened AC-4 and named the existing integration-test and keyless-provenance documentation owners before repair. | Full default failure report; independent closure oracle identifies exactly storage_identity and upgrade_protocol. No new preview modes or mutation authority. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-14 | Select explicit read-only core evaluation with conservative refusal for unaudited producers. | Allow bounded lifecycle inspection during a retained upgrade without releasing or bypassing publication ownership. | Exempt any mode named dry_run: hidden writes and extensions bypass ownership. Document all previews as refused forever: safe but leaves useful offline inspection unavailable. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Contract regression or scope expansion | A nominal dry run can mutate observations/accounting or invoke callbacks. Prove target immutability at registered completion boundaries and keep unaudited paths guarded. |

## Session Handoff

Planned only. Prepare/readiness must pass before code edits. Keep durable decisions and final command/results in wave.md; compact execution detail stays in ignored cache or temporary storage. No new permanent evidence folder. See docs/agents/session-handoff.md for sequencing.
