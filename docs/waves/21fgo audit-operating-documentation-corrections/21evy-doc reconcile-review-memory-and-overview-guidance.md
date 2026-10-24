# Reconcile review, memory and overview guidance

Change ID: `21evy-doc reconcile-review-memory-and-overview-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-22
Wave: 21fgo audit-operating-documentation-corrections

## Rationale

Audit findings A3-A5 identify contradictions in active project documentation: the lane table mandates delivery Council universally, the closure checklist mandates retired journals and unconditional memory promotion, and the overview describes code_ask as LLM synthesis while another section correctly calls it mechanical retrieval. Its distribution filename is also stale.

## Product Intent

Agents and maintainers reading the project guide receive the same review and memory obligations as the canonical lifecycle, and an accurate code_ask description. AC-1 through AC-3 establish consistency against the current canonical sources; no change to executable policy is intended.

## Requirements

1. Align the delivery Council table with the configured mode and persisted Prepare receipt, retaining the existing conditional rule.
2. Replace legacy journal distillation and mandatory memory creation with typed candidate review, durable promotion only when justified, and the valid zero-new-memory outcome. Retain other applicable closure obligations.
3. Describe code_ask as existing mechanical retrieval routing rather than LLM synthesis. Replace the transient old distribution filename with a maintained release reference. Do not infer implementation status of unrelated overview bullets.

## Scope

In scope: the two project-authored files named below and their directly contradictory passages. Out of scope: seeds, generated prompts, tools, gate semantics, historical records, broad documentation rewrite and unrelated audit findings.

## Acceptance Criteria

- [x] AC-1: The lane table and closure guidance agree with seed 190's conditional delivery Council requirement; the previous universal statement is absent from that table.
- [x] AC-2: The closure checklist describes typed candidate review and explicitly permits zero new memories with rationale; it no longer requires journal writes or unconditional promotion. Direct comparison with the canonical close workflow is the oracle.
- [x] AC-3: The overview's code_ask capability/status descriptions agree on mechanical retrieval and do not claim LLM synthesis; the obsolete distribution filename is replaced with a maintained release reference.
- [x] AC-4: The edited documents validate and independent review confirms the correction preserves existing policy and unrelated content.

## Tasks

- [x] T-1: Correct the review lane table and memory closure items against current canonical guidance.
- [x] T-2: Correct the overview's code_ask and distribution passages.
- [x] T-3: Verify the changed passages, show the old passages fail the correction checks, obtain independent review and run full docs validation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Documentation edits | implementer | readiness | Single writer for both files |
| Independent review | qa-reviewer and docs-contract-reviewer | current phase packet | Read-only; verify against canonical policy |

## Serialization Points

Only the named project-authored documentation is write-owned. Canonical seed 190, runtime tools, generated surfaces and unrelated wave records are read-only. Coordinator owns this wave's records.

**Review targets (repo-relative paths):**

- `docs/contributing/review-and-evals.md`
- `docs/references/wavefoundry-overview.md`

## Affected Architecture Docs

N/A: correcting explanations to current policy changes no architecture, tool behavior or ownership.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes contradictory review obligation |
| AC-2 | required | Removes obsolete memory obligation |
| AC-3 | required | Restores accurate tool/release guidance |
| AC-4 | required | Verifies the bounded correction |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Planned from confirmed audit A3-A5; no source edits. | Audit report and seed 190 lines 34-42 |

| 2026-10-22 | Readback: correct only the two declared guides to match existing conditional Council, typed-memory and mechanical-retrieval policy (AC-1–AC-4). Keep candidate review mandatory even when no new memory is justified; retain unrelated content and generated regions. | Canonical seed 190 and readiness council; memory_brief read before edits |

| 2026-10-22 | Implemented AC-1–AC-3 and T-1/T-2. Three paired correction predicates fail on the saved original text and pass on the current text; generated policy/protocol regions unchanged. Full docs validation passed. Delivery review pending against frozen two-file diff. | git blobs 8b690c275f724a5101ff3dea0de2813d58263ad7 / c2b84696fb2563ddb6c9630514a765430aa033e9; scratch 21fgo-delivery-probes.json; release v1.36.0 verified with gh release view |

| 2026-10-22 | Independent delivery QA and docs-contract approvals recorded from one disclosed fresh context. Eight checks reject HEAD originals and pass current text; canonical policy, generated regions and unrelated content verified. All ACs/tasks met; no runtime behavior changed and no framework suite needed for prose-only scope. | ev-approval-qa-reviewer-2 / ev-approval-docs-contract-reviewer-2; unchanged git blobs; full docs validation passed |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-22 | Correct two owning project docs | Smallest change removes known contradictions without changing policy | A broad drift sweep expands scope; changing seeds would alter the correct source of truth |

## Risks

| Risk | Mitigation |
| --- | --- |
| Wording inadvertently changes policy | Compare with canonical close seed and use independent docs-contract review |

## Session Handoff

Plan, prepare, implement and independently review; pause for operator-owned closure. No commit authorization.
