# Correct local agent permissions

Change ID: `21fgs-ops local-agent-permissions-and-morning-portability`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-23
Wave: 21fgy local-agent-environment-maintenance

## Rationale

Audit A6 identifies two retired tool names in project-local Claude permissions. The operator removed audit A7 from this wave on2026-10-23 because Morning is maintained by Anthropic.

## Product Intent

The local project no longer lists permissions for nonexistent tools. This work changes local project configuration and preserves every other setting and permission; it changes no distributed framework behavior.

## Requirements

1. Remove exactly mcp__wavefoundry__code_keyword_search and mcp__wavefoundry__wf_close_wave_gate from .claude/settings.local.json. Preserve every other setting and allowlist entry; do not replace obsolete permissions with broader ones.
2. Verify the exact semantic diff, valid JSON and preservation of all other settings; retain a failing original control.
3. Record the operator-directed exclusion of A7 honestly. Its upstream source correction is outside this wave and must not be represented as applied.

## Scope

In scope: the two obsolete local permission entries (A6), verification and review. Out of scope: A7/Morning and its maintained source or synced cache, framework packaging, plugin removal, credential or transcript export, other permission cleanup and global sandbox changes.

## Acceptance Criteria

- [x] AC-1: The parsed local settings differ only by removal of the two named obsolete entries; exact before/after comparison and JSON parse confirm preservation. The baseline retains both and fails the removal check.
- [~] AC-2: The maintained Morning source contains capability-based browser selection and conditional environment assumptions while retaining screenshot inspection and all unrelated content. Verification names the actual maintained source and sync path; a staged patch alone does not satisfy this AC. *Operator removed A7 on2026-10-23 because Morning is maintained by Anthropic; source correction is outside this wave and was not applied.*
- [x] AC-3: Independent review confirms the exact permission cleanup and preservation boundaries, and full project docs validation passes. The earlier browser smoke check is historical evidence outside the narrowed A6 scope.

## Tasks

- [x] T-1: Remove only the two obsolete permission entries and verify the exact semantic diff.
- [~] T-2: Apply and verify the Morning correction through its maintained source and supported sync route. Intentionally not met: operator removed A7 on2026-10-23 because Anthropic maintains Morning.
- [x] T-3: Independently verify the bounded local permission correction and preservation, retain explicit limitations and validate docs.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | readiness | Single writer |
| Verification | independent reviewer lanes | implementation | Frozen source; public-path and known-bad checks |

## Serialization Points

Coordinator owns records; implementer owns the following files only. Generated surfaces must come from their owning renderer.

**Review targets (repo-relative paths):**

- `.claude/settings.local.json`

## Affected Architecture Docs

N/A: exact project-local permission cleanup changes no distributed architecture or framework behavior.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the bounded correction and preservation contract |
| AC-2 | required | Historical criterion explicitly removed by the operator; see its inline intentionally-not-met note |
| AC-3 | required | Establishes the bounded correction and preservation contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Planned from current audit and inspected owning source; no implementation edits. | Audit findings and declared source paths |

| 2026-10-22 | Prepared a bounded Morning source replacement in temporary storage; installed synced source unchanged and maintained-source location still pending. Chrome exists locally; a synthetic 960x1400 local page rendered successfully in an isolated temporary profile and its screenshot was inspected. Initial sandbox launch aborted; authorized host launch succeeded. This establishes host capability only, not adoption of the skill correction or full Morning output qualification. | Morning-portability.patch and morning-browser-smoke.png under /private/tmp/wf-audit-remediation; Chrome exit 0 |

| 2026-10-22 | Implementation readback: remove only the two obsolete exact permission names from local settings, preserve all other values and formatting, verify parsed before/after and retain a failing original oracle. Morning source adoption remains pending; no synced-cache edit. Gapfill: settings are private project-local configuration outside indexed code; read and compare them locally without printing unrelated configuration. | Current local baseline SHA-256 b4ab58066e359599456a709ef4dc786b0bce11f4d04aede7aeb704f3c9337ec9; both exact names present, 114 other allow entries |

| 2026-10-22 | Removed exactly the two named obsolete local permission lines. Parsed JSON equals original with only those entries removed; 114 other allow entries and all other values preserved. Original fails the removal oracle; final passes. Maintained Morning source and T-2/AC-2 remain pending, not deferred or completed. | local-permission-evidence.json; resulting SHA-256 recorded in that bounded report |

| 2026-10-22 | Fresh independent QA/docs and security reviews verified A6 exact semantic preservation and negative controls. QA independently viewed the Chrome synthetic screenshot. Full project docs validation passed. AC-3 is bounded capability/review evidence; A7/AC-2 and T-2 remain unmet because maintained-source access is unknown. No full-wave delivery approval or source-adoption claim. | qa-docs-21fgy-partial-review.md, security-A6-review.md, wf_validate_docs full pass |

| 2026-10-22 | Operator did not recognize Morning and explicitly requested origin/source investigation. Scoped sync manifest identifies skillId/name morning, source anthropic-example, updatedAt2026-09-14T19:41:01.990356Z. It is an Anthropic-provided example, correcting the earlier personal-source assumption. Official Claude docs confirm account-to-local download only; cache edits do not upload and can be overwritten. No maintained project/personal source was identified. Source correction remains unapplied and upstream-owned; no removal, disablement, cache edit, upload or external message. | morning-origin.json; local synced manifest entry; https://code.claude.com/docs/en/skills#where-synced-skills-load |

| 2026-10-23 | Operator removed A7 from this wave because Anthropic maintains Morning. Narrowed owning Rationale/Product Intent/Requirements/Scope and A6 review wording; retain A7 AC-2/T-2 as intentionally not met with operator/date/reason rather than claim a source correction. A6 remains independently verified and implemented. No installed skill, permissions or framework source changed in this scope update. | Operator: remove A7 since it is Anthropic’s; morning-origin.json; existing A6 preservation evidence |

| 2026-10-23 | Narrowed A6-only scope reviewed independently after operator removal of A7. Refreshed readiness QA/docs/security and council approval; Prepare succeeded on current receipt. Delivery QA/docs/security approvals current; close dry-run reports only missing operator signoff and proves the existing green framework receipt. Exact two-entry removal/114otherentries and complete JSON preservation reconfirmed; known-bad controls detected. AC-2/T-2 intentionally not met is legitimate operator-directed exclusion. Wave paused; no code/config edit, test rerun, commit or closure. | Typed review records; review-policy-be58a3bf7c0a3a1d0d84; /private/tmp/wf-audit-remediation/a6-narrowed-synthesis.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-22 | Retain local settings ownership; Morning correction belongs to the Anthropic-maintained example | Origin investigation identified source anthropic-example; the synced cache is not a maintained source | Keep the proposed patch unapplied; do not fork, disable or mutate the cache |

| 2026-10-23 | Remove A7 from this wave at the operator’s instruction | Morning is maintained by Anthropic; A6 remains the only active scope | Retain historical investigation and mark the removed work intentionally not met |

## Risks

| Risk | Mitigation |
| --- | --- |
| Unrelated local permissions could be changed or broadened | Exact parsed before/after comparison and independent negative controls |

## Session Handoff

A6 implementation is complete. A7 was removed by the operator on2026-10-23. The narrowed scope has a refreshed receipt; required approvals must be re-recorded before closure. No code edits, commit or closure authorized by this scope-removal request.
