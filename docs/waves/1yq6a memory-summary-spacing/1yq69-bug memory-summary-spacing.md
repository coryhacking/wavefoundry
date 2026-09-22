# Memory Summary Spacing

Change ID: `1yq69-bug memory-summary-spacing`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-22
Wave: `1yq6a memory-summary-spacing`

## Rationale

The operator observed validation metadata immediately adjoining `## Summary`. `_replace_or_insert_metadata` inserts new fields after the existing separator, with only one newline before the heading. Fix future helper writes so exactly one blank line separates metadata from Summary; repeated updates must not accumulate blank lines. Existing records are not migrated.

## Requirements

1. After inserting or replacing metadata through `_replace_or_insert_metadata`, exactly one empty line separates the metadata block from the first Summary heading, normalizing zero, one or multiple blank lines at that boundary.
2. Repeated helper updates preserve that separator without accumulating blank lines; retain section content and metadata values, including body text resembling metadata.
3. Preserve missing-Summary error behavior on insertion and existing replacement behavior on records without a Summary marker. Do not broaden mutation scope outside the metadata-to-Summary boundary and the requested field.
4. Do not rewrite historical records, change memory schema/status semantics, introduce a migration, or change seeds, index configuration or public tool signatures.

## Scope

**In scope:** the existing helper in memory_records.py and focused regression tests in test_memory_records.py, plus wave evidence.

**Out of scope:** historical memory files, schema or lifecycle changes, new lint rules, arbitrary Markdown normalization, whole-document newline conversion, retrieval changes, commit and closure.

## Acceptance Criteria

- [x] AC-1: Insert and replace operations yield exactly one blank line before Summary for absent, single and excess separators, verified by exact expected text.
- [x] AC-2: Repeated updates remain stable and preserve the body and unrelated metadata, verified by boundary and content assertions.
- [x] AC-3: Real record rendering and validation produce the correct separator while preserving parsed validation fields; missing-Summary behavior remains compatible. Tests fail against the original helper.

## Tasks

- [x] Repair the helper with normalization confined to the metadata/Summary boundary.
- [x] Add and run focused helper and producer-built validation regressions, including an original-helper negative control.
- [x] Run the full suite, validate edited documentation, and obtain independent delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Helper and tests | implementer | readiness | One bounded writer |
| Delivery verification | code-reviewer, qa-reviewer | implementation | Fresh independent contexts |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_records.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`

## Affected Architecture Docs

N/A: formatting-only repair within one writer; no ownership, public signature, data flow or verification architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Directly fixes the reported output |
| AC-2 | required | Operator explicitly forbids accumulating separators |
| AC-3 | required | Proves the actual producer path and preserves refusal behavior |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Normalize the local boundary inside the existing helper on both insert and replace | Covers repeated updates and known missing spacing with one owner | Merely add a newline on insertion leaves replacement spacing defective; re-render whole records risks unrelated formatting/content changes; historical migration explicitly excluded by operator |

## Risks

| Risk | Mitigation |
| --- | --- |
| Metadata regexes can consume separator whitespace | Normalize after the field mutation and test replacement |
| Broad substitution changes body examples | Keep the boundary to the first Summary; preserve body content and scope field replacement to metadata where Summary exists |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Full suite green: 9,535 tests, 121 files, 12 intentional skips; fresh independent code and QA approvals. Sandbox-only dashboard failure resolved by host-permission rerun with no source change. | delivery-review.md and lane reports |
| 2026-09-22 | Implemented bounded header update and normalized boundary. 15 focused tests pass. Original-helper control causes 11 assertion failures and zero errors across helper and real producer tests; no historical files changed. | `evidence/original-helper-control.py`; MemoryMetadataSpacingTests; MemoryAgentValidationTests |
| 2026-09-22 | Readback: change only memory_records.py helper and test_memory_records.py; exactly one boundary blank line on insert/replace, repeated operations stable, body untouched, no historical migration (AC-1–3). | Readiness review approved |
| 2026-09-22 | Planned from reproduced helper defect; operator excludes historical repair | Current helper insertion produces `Canonical overlap: duplicates` immediately before Summary |

## Session Handoff

See `docs/agents/session-handoff.md`.
