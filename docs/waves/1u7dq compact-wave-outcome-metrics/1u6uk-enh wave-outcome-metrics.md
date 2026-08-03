# Compact Wave Outcome Metrics

Change ID: `1u6uk-enh wave-outcome-metrics`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-01
Wave: 1u7dq compact-wave-outcome-metrics

## Rationale

Wavefoundry already records useful signals in three authorities: Context
Efficiency, the review-evidence ledger, and the memory-advisory projection.
The first is easy to see, while the review and memory signals require manual
inspection of several artifacts. That makes it difficult to judge whether a
wave's tracking cost was justified, or whether the memory system is being used.

Expose a small read-only metric bundle alongside the existing wave listing so
an operator can assess effort, outcomes, and memory use without creating more
recordkeeping. Keep the existing estimated-token-savings metric exactly as it
is, and do not record agent model information.

## Requirements

1. Preserve the current per-stage Context Efficiency calculation and its
   visible estimated-token-savings values without changing its SQLite schema,
   attribution, credits, debits, or paired-evaluation rules.
2. Extend `wf_list_waves` with a bounded, scalar-only `wave_metrics` result
   keyed by the waves returned on that page. Each entry must be derived at read
   time from existing authorities and contain only:
   - Context totals: tool calls and estimated token savings.
   - Review totals: evidence records, review runs, current findings, and the
     existing current-disposition counts.
   - Memory-advisory totals: advisory surfaces, citations, credited records,
     and estimated exploration avoided.
3. A missing, empty, or unreadable optional authority must yield that metric
   group as unavailable (or its existing zero/empty state where authoritative),
   without failing the wave list or inventing values.
4. Do not add model, host, elapsed-time, billing, prompt/response, or new
   per-event telemetry. Do not duplicate the data into a new database, ledger,
   or `wave.md` block.
5. Keep the response bounded: return scalar summaries only for the requested
   page of waves and preserve the MCP response-size safeguards.

## Scope

**Problem statement:** Operators cannot compare tracking effort, review
outcomes, and memory use across recent waves without manually joining three
separate artifacts.

**In scope:**

- A read-only `wave_metrics` object on `wf_list_waves`.
- Reuse of existing Context Efficiency, review-evidence, and
  exploration-avoided read/projection helpers.
- Focused contract and regression tests for populated, empty, and unavailable
  metric sources.
- Documentation of the added response field and its non-goals.

**Out of scope:**

- Model or host provenance capture.
- New telemetry tables, event records, lifecycle checkpoints, or `wave.md`
  sections.
- Changes to Context Efficiency calculations or estimated-exploration-avoided
  calculations.
- Historical backfill or a dashboard redesign.
- Changes to wave ordering, lifecycle gates, review policy, or memory
  retention policy.

## Acceptance Criteria

- [x] AC-1: `wf_list_waves` returns, for each wave on the requested page, a
  scalar-only `wave_metrics` entry containing the specified context, review,
  and memory-advisory values derived from existing authorities.
- [x] AC-2: The Context Efficiency values reported through `wave_metrics`
  match the existing durable snapshot; this change does not alter Context
  Efficiency calculation, storage, or `wave.md` projection behavior.
- [x] AC-3: Review values match `review_evidence_summary` for a ledger with
  multiple runs and current finding dispositions; an empty ledger reports the
  canonical zero summary.
- [x] AC-4: Memory values match the existing exploration-avoided wave read
  model, including the zero/unavailable behavior, and are not added to
  estimated token savings.
- [x] AC-5: A missing or malformed optional source leaves the wave list usable,
  reports only that group unavailable, and does not synthesize a positive
  metric.
- [x] AC-6: No model, host, timing, billing, prompt/response, or new event data
  is introduced; the documented response is bounded to scalar values for the
  requested page.

## Tasks

- [x] Add the response-level metric assembler at the `wf_list_waves` boundary,
  reusing existing read helpers rather than parsing rendered Markdown.
- [x] Add focused unit/contract coverage for normal, empty, unavailable, and
  page-bounded responses.
- [x] Update the MCP tool-surface documentation with field meanings,
  availability behavior, and explicit non-goals.
- [~] Run the focused tests, framework test suite, and documentation validation. *(Focused coverage and docs validation passed; the full suite reaches the host ONNX/CoreML embedding regression then exits with signal 139 before a test result.)*

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Metric assembly | implementer | — | Reuse existing read-only authorities. |
| Verification and contract docs | qa-reviewer / docs-contract-reviewer | Metric assembly | Prove no new telemetry or changed calculations. |

## Serialization Points

- `server_impl.py` owns the public `wf_list_waves` response shape; it is the
  single serialization point for this change.
- Review counts must come from `review_evidence.py`'s structured summary, not
  rendered `wave.md` prose.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` — update the `wf_list_waves` response
contract. Other architecture documents are N/A: this is a read-only extension
of an existing MCP response and does not change a primary control/data path.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Delivers the requested compact metric bundle. |
| AC-2 | required | Preserves the existing token-savings signal. |
| AC-3 | required | Makes review effort and outcomes trustworthy. |
| AC-4 | required | Makes memory value visible without double-counting. |
| AC-5 | required | Keeps the read-only listing resilient and honest. |
| AC-6 | required | Enforces the requested simplification boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-01 | Change drafted; no implementation started. | Operator direction: retain token savings, add existing metrics only, defer model capture. |
| 2026-08-02 | Implemented bounded `wave_metrics` from existing authorities. | List-response contract tests, public MCP smoke, and tool-surface documentation. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-08-01 | Reuse existing authorities in one read-only `wf_list_waves` bundle. | It exposes the requested comparisons without a new tracking system. | Add new telemetry/event schema — rejected: duplicates existing data and increases recordkeeping. Add model provenance — rejected: ordinary telemetry lacks reliable cross-host capture and the operator deferred it. Add new `wave.md` tables — rejected: duplicates existing projections. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Response size grows with wave-page size. | Return scalar fields only for the page already requested; retain response-size tests. |
| A rendered Markdown parse can drift from authority. | Reuse structured Context Efficiency, review-evidence, and exploration-avoided read helpers only. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
