# Context Efficiency Marker Placement

Change ID: `1xgbd-bug context-efficiency-marker-after-heading`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-08
Wave: 1xgbe context-efficiency-marker-placement

## Rationale

Place the Context Efficiency begin marker after its heading, matching other generated wave sections. Fix the renderer and existing wave documents so refreshes preserve the consistent layout without changing recorded accounting data.

## Requirements

1. Render the Context Efficiency heading, blank line, then begin marker and generated body.
2. Read existing marker-before-heading checkpoints and update either layout idempotently without duplicate headings or altered state/prose.
3. Normalize existing repository wave documents with exact formatting-only edits; destination projects accept their existing layout and normalize on subsequent checkpoint publication.

## Design

Update render_checkpoint_block, marker/layout canonicalization and replace_checkpoint_block in context_efficiency.py. Keep state schema and validation semantics unchanged; normalize only the exact previously generated heading/marker arrangement before canonical validation. Replacement must handle new external heading without duplicating it, and preserve surrounding prose. Tests cover old and new layout parsing, repeat replacement, legacy marker namespace, nonempty state and tamper rejection. Existing dashboard old-layout fixture remains a compatibility control. Bulk-normalize exact old layouts in docs/waves wave records after refreshing the running MCP implementation; compare embedded state bytes before/after. Do not change sealed accounting, events or totals.

## Scope

In scope: renderer/layout compatibility, focused existing tests, existing wave Markdown formatting. Out of scope: accounting, marker names, schema, other section layout changes, new upgrade migrations or unrelated cleanup.

## Acceptance Criteria

- [x] AC-1: Newly rendered Context Efficiency sections place the begin marker after the heading and a blank line.
- [x] AC-2: Old and new checkpoint layouts parse to the same state; repeat replacement leaves exactly one heading and preserves surrounding prose and validation of tampered state.
- [x] AC-3: Existing repository wave sections use the new order with identical embedded checkpoint state.

## Tasks

- [x] Update checkpoint rendering and backward-compatible replacement/validation.
- [x] Verify focused layout and compatibility controls.
- [x] Normalize existing wave sections and validate documentation.

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_context_efficiency.py`
- `docs/waves/`

## Affected Architecture Docs

N/A: formatting within the existing checkpoint module; no accounting, schema or public tool contract change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Requested consistent generated layout. |
| AC-2 | required | Existing targets and repeated publications must remain correct. |
| AC-3 | required | Operator sees consistency in existing wave documents. |

## Progress Log

Observe / final verification: canonical framework suite passed8,560tests across75files in199.748seconds, three skips. All three ACs and tasks are complete. Existing118wave sections and active MCP publication use heading-before-marker. Full docs validation passes. Delivery review and closure remain pending; no commit performed.

Observe: 55 context-efficiency tests pass, including seven checkpoint tests. New and old layouts plus legacy namespace round-trip nonempty state; tampered displayed table still fails. Repeat replacement is byte-identical, surrounding prose survives, and carrier publication performs only the intended exact layout normalization. Four temporary source mutants are caught: old_renderer_order and skip_legacy_layout_normalization fail test_checkpoint_heading_precedes_marker_with_legacy_compatibility; consume_inline_heading and consume_unmatched_prefix fail test_checkpoint_replacement_preserves_nonheading_prefix. The first unmatched-prefix mutation survived because existing prefixes did not reach that length branch; added an equal-length nonheading sentinel and verified the mutant now fails by assertion.

Observe: reloaded MCP implementation, then normalized118docs/waves/*/wave.md records by exact old-prefix byte substitution. Every changed file retained identical embedded state-comment bytes; reverse substitution recovered its original bytes and repeated normalization was a no-op. No events, accounting tables or sealed totals were edited. Full docs validation passed; canonical full framework suite running. Framework edit gate closed.


Readback: move the begin marker below the heading with one blank line, accept the exact historical layout, and replace only an exact adjacent heading at line start. Implement renderer/compatibility first, verify old/new/legacy and surrounding prose, then normalize existing docs by exact byte substitution. No accounting, state schema, totals or event changes.

Thought: choose source fix plus exact layout normalization. The current renderer puts the heading inside the marker block; simply swapping two lines would duplicate headings on later replacement and reject old checkpoints through exact-render validation. Address those existing paths together before updating wave documents. Preserve previous waves' uncommitted changes. No closure or commit requested for this new wave.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-08 | Change renderer, accept the old layout, and normalize existing wave formatting. | Makes current and future output consistent without invalidating checkpoint state. | Edit docs only: next publication reverts. Renderer-only reorder: replacement duplicates headings and old validation fails. |

## Risks

Duplicate headings or rejected historical checkpoints: exercise old/new replacement and parsing. Formatting migration must preserve embedded state bytes and surrounding prose; use exact old-prefix substitutions only.

## Session Handoff

See docs/agents/session-handoff.md.
