# Ignore hidden headings when reading lifecycle documents

Change ID: `23tcx-bug ignore-commented-lifecycle-headings`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23td0 downstream-lifecycle-compatibility

## Product Intent

Teams can leave optional instructions in a plan template inside a Markdown HTML comment. Prepare must still select the reviewers warranted by every visible target, and Close must still see every visible unfinished task or acceptance criterion. AC-1 and AC-2 establish these Horizon 1 delivery outcomes.

## Rationale

Waveforge reported the problem against v1.44.1. In a local replay, `serialization_point_paths` returned only `a/b.py` when a multiline comment containing an H2 separated it from `c/d.py`. Both paths appeared when the comment was removed or replaced by a fenced example. The checklist reader likewise lost the unchecked task after the comment. The layout check flagged the hidden heading as missing a blank line.

## Requirements

1. Lifecycle readers must recognize visible section starts and ends on the original lines. Inside a closed HTML comment, headings, target declarations, acceptance criteria and tasks are inactive. Keep visible content on either side, including visible text sharing a line with an inline comment. Never join separated tokens to manufacture a heading or path.
2. Apply the rule to the siblings that read lifecycle sections to select lanes, fingerprint reviewed scope, locate or mark checkboxes, validate or repair record layout, and gate closure. Trace the callers of the affected readers during implementation. Preserve original offsets, line endings and bytes outside the intended edit. Compare visible section boundaries when normalizing tracking metadata. A hidden heading must neither exempt a visible requirement from the digest nor end a tracking-only section early. Keep current digest treatment of prose outside existing exclusions.
3. Preserve existing fenced-example behavior, including delimiters printed literally inside fenced examples and inline code spans. Fence-looking lines inside a comment cannot extend the comment past its closing delimiter. An unmatched comment opener must not cause a reader to silently drop visible obligations through end of file. Preserve the existing behavior of renderer-owned begin/end comments and their enclosed visible Markdown.

4. Version the changed review-policy canonicalizer so the receipt history distinguishes a parser change from a plan edit. Follow the existing evaluator transition: disclose the one-time re-Prepare for already readied or open declared waves, including those whose visible targets stay the same. Preserve validation of closed records from stored fields.

## Scope

Cover the reported Prepare reader, the corresponding lifecycle checklist and metadata readers and heading-layout checks on wave/spec files. Include consumers that bypass those shared readers for the same decisions. Preserve caller-specific heading and fence conventions. Semantic index chunking, general Markdown rendering and unrelated document formats are outside this change.

## Acceptance Criteria

- [x] AC-1: Prepare selects the same target-driven lanes as the equivalent visible-only spec. Targets before and after the block appear in the extracted paths, a hidden section or declaration contributes none, and the next visible H2 ends the section. A target below the block uniquely triggers a lane in the test.
- [x] AC-2: In a disposable wave, the registered close preview reports a visible unchecked criterion and task after the comment and ignores hidden checklist examples. The mark tools edit only the requested visible rows. Check the same visible item with an inline comment through mark and close. Under the new evaluator, on equivalent unmodified review scope, tracking-only edits retain the receipt while a visible requirement change invalidates it.
- [x] AC-3: Layout lint and repair leave commented headings and renderer markers intact, still diagnose and repair a visible heading, and preserve CRLF and unterminated final lines. Reader controls cover a comment delimiter in literal code, a fenced example inside a comment, visible text adjacent to a comment, and an unmatched opener followed by a visible obligation.

- [x] AC-4: Starting from old-evaluator receipts, exercise a wave where a hidden heading suppressed a target and a control with identical visible scope before and after upgrade. Both disclose the evaluator change and re-Prepare once. Verify restored target-driven review in the first case, stable lane selection in the control, and an unchanged historical closed ledger. Under the new evaluator a hidden Progress Log heading inside Requirements cannot mask a real edit, and a hidden H2 inside the real Progress Log cannot make tracking prose change the digest.

## Tasks

- [x] Trace the public operations above to their section readers, document the bounded caller inventory and replay the field input.
- [x] Implement shared comment visibility at the affected readers and keep raw source available to writers, markers and evidence fingerprints.
- [x] Run targeted public-path controls and existing fence, marker, layout and review-policy regression tests. Document changed lifecycle behavior.

## Agent Execution Graph

| Workstream | Owner | Depends on | Outcome |
| --- | --- | --- | --- |
| Parser and integrations | Implementer | Readiness | Consistent visibility across lifecycle readers |
| Verification | QA and code reviewers | Implementation | Check the field case, retained obligations, writes and receipt behavior |

## Serialization Points

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/gardener_metadata.py`
- `.wavefoundry/framework/scripts/markdown_layout.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

Document the effective lifecycle section rule with the relevant Prepare and Close contracts in `docs/specs/mcp-tool-surface.md`. The ledger schema and approval policy stay as defined.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces the reported downstream failure. |
| AC-2 | required | Prevents invisible obligations and incorrect writes or review scope. |
| AC-3 | required | Preserves literal examples, generated regions and source positions. |
| AC-4 | required | Keeps review history interpretable when the rule used to compute the receipt changes. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Replayed the two visible declarations separated by a hidden heading. | Extraction lost the second declaration, checklist parsing lost a later task, and layout reported the hidden heading. Public Prepare and Close comparisons are delivery checks. |
| 2026-11-19 | Readback: retain visible declarations and checkboxes across hidden headings, preserve mark offsets, and disclose evaluator migration. | Exercise Prepare, mark, close, canonicalization, and layout with live and hidden controls. |
| 2026-11-19 | Prepare and upgrade scaffold repair read visible serialization targets. Policy digests and review-context headings share comment visibility with tracking metadata. Checklist, mark, close, projection and spacing readers retain original write positions. | The registered mark tools changed the visible CRLF rows only. Close preview reported the visible unfinished criterion and task. A hidden second heading left the following target active at Prepare. |
| 2026-11-19 | Verified evaluator 7 to 8 for a restored lane and an unchanged lane set. Prepare appends once for each open record and preserves a closed record's ledger. | 507 focused tests passed across Prepare, mark, close, section layout, checklists, review policy and evidence, phase gates, and upgrade scaffold repair. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Share comment visibility among lifecycle readers while retaining original source positions. | The readers make routing, editing and closure decisions. A common rule can keep visible declarations active across them. Verify each decision at its public entry. | A template workaround leaves installed templates affected. Removing comments globally before parsing changes offsets and erases renderer markers. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A mask changes receipt meaning or hides live work. | Compare clean and commented cases at both policy and gate boundaries, including an incomplete comment. |
| A shared fence helper changes unrelated callers. | Keep fence-only behavior for callers outside the scoped operations and use controls for mixed literals. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
