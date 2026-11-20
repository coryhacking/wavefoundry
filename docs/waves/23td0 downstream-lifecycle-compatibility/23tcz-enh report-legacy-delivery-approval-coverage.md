# Flag legacy delivery approvals during upgrade

Change ID: `23tcz-enh report-legacy-delivery-approval-coverage`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23td0 downstream-lifecycle-compatibility

## Product Intent

An operator upgrading with work in progress can identify which existing approvals need another look if a criterion is later deferred or its rationale changes. AC-1 demonstrates that the operator and an MCP client receive the same actionable information. This supports Horizon 1, dependable delivery across an upgrade.

## Rationale

Waveforge asked whether an approval recorded before an upgrade could miss a later deferral. A current delivery approval can lack the tool-written criterion-status line. The existing compatibility test exercises Review after such a deferral and expects no chronology diagnostic. The framework cannot infer an earlier criterion state from the current document. The upgrade is a useful time to identify where that limitation applies.

## Requirements

1. In the successful upgrade summary inspect the target checkout's open containers (active or implementing), across all configured roots and parent scopes, using existing lifecycle discovery and validated review authority. For each current approved `council-delivery` or `operator-signoff` with no recorded criterion-status line, name the container and affected signoff. Use record content to determine coverage, irrespective of the version label or approval date. Exclude other signoffs, superseded approvals, containers without such an approval and closed archives.
2. Explain that if the operator later defers a criterion or changes its deferral rationale, they should obtain a fresh affected approval covering the revised criteria. Preserve the original approval, ledger, gate results and upgrade outcome. The advisory reports missing comparison evidence. It makes no assertion that narrowing already happened.
3. Use the existing common human and machine upgrade summary. Show the number of affected containers and list each once with its affected signoff keys. Preserve total and omitted counts when the MCP budget truncates results and direct the reader to the complete upgrade summary. Render project nouns through the existing vocabulary. Older producer output with no new field means coverage was not assessed.
4. If enumeration or validated authority reading fails, distinguish incomplete inspection from a complete zero. Identify the affected container when known. A present but malformed criterion-status line means comparison is unavailable there, with the reason distinguished from a missing legacy line. Preserve any independently established results and existing error handling. Limit reads to open records and their necessary authority. Do not scan archived event histories.

## Scope

Add a read-only observation to existing upgrade reporting, with tests and an operator-facing explanation in the upgrade/MCP contract. Freestanding prose-only legacy records with no typed signoff are outside the approval census. A valid recorded line with a later change missing from its map is governed by the existing scope and currency rules. The upgrade has no authority to renew approvals, backfill evidence, or start review. The separate vocabulary and Markdown parsing changes have their own specs.

## Acceptance Criteria

- [x] AC-1: Upgrade a fixture with two open containers in different configured parent scopes. One has current delivery approvals with a missing criterion-status line, the other has comparable approvals. The CLI and served MCP summary identify only the affected container, the appropriate signoff keys and the conditional action. The ledger bytes and delivery gate result match the pre-upgrade control.
- [x] AC-2: With older superseded approvals, an open container without delivery approval, and a closed historical record, the summary excludes those records. A clean control reports zero after successful inspection. A malformed status line or unreadable open ledger produces an explicit coverage limitation. In one summary mix a verified affected container, a clean peer and an unreadable peer. Retain the verified affected result, mark inspection incomplete and identify the unreadable peer. Older summary payloads continue to parse without claiming zero.
- [x] AC-3: For affected results large enough to trigger the existing MCP response budget, the operator can recover the complete list. The structured result reconciles returned and omitted rows to the total, including when multiple signoffs belong to one container.

## Tasks

- [x] Resolve open records and assess the current delivery authority through existing readers.
- [x] Carry the advisory through the common upgrade summary and document compatibility and the conditional action.
- [x] Exercise the CLI and MCP paths, interrupted inspection, mixed-version parsing, bounded output and read-only controls.

## Agent Execution Graph

| Workstream | Owner | Depends on | Evidence |
| --- | --- | --- | --- |
| Upgrade reporting | Implementer | Readiness | Open record selection and summary |
| Compatibility checks | QA reviewer | Reporting | Independent fixture outcomes and byte comparisons |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

Update the upgrade summary contract in `docs/specs/mcp-tool-surface.md`. The existing CLI producer and MCP consumer retain their responsibilities.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Demonstrates the operator action in the reported case. |
| AC-2 | required | Distinguishes affected approvals from unknown coverage and unrelated history. |
| AC-3 | required | Protects summary usability in downstream profiles with multiple open containers. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Ran the existing compatibility control against the checkout. | `CriterionDeferralCurrencyTests.test_a_closed_wave_and_an_approval_without_the_line_report_nothing` passed. It covers a missing line with a later deferral, an unparseable line and closure. The common upgrade summary and MCP collection bounds were inspected in source. |
| 2026-11-19 | Readback: report exactly which open records have approvals without comparison evidence and when to renew them. | The bounded fresh reporting worker supplies all upgrade summaries. Scope includes incomplete inspection and old producers. |
| 2026-11-19 | Exercised the fresh cleanup CLI through the registered upgrade tool, with two parent scopes, legacy and comparable signoffs, mixed unreadable and malformed records, and older and paged summaries. | 35 upgrade-surfacing tests, 33 delegated/primary summary tests and 9 criterion-currency tests passed. The cleanup log named the same affected record and signoffs as MCP. Both ledgers and the original Review result survived the upgrade. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Identify affected open records at upgrade and explain when to renew approval. | Persisted signoffs distinguish missing coverage from a comparable recorded state. The operator can act before relying on an older approval. During the next downstream upgrade with an affected container, ask whether the named signoff and action were clear. | A generic release note makes the operator inspect every record. Blocking or rewriting approvals would attribute an earlier criterion state without evidence. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A truncated list or unreadable ledger appears clean. | Preserve counts and incomplete-inspection reasons in both delivery paths. |
| A compatibility warning triggers redundant reviews. | Limit it to current affected approvals and give the precise condition for seeking a new one. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
