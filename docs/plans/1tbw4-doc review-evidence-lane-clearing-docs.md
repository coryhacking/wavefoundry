# Document the wf_review_evidence Lane-Clearing Protocol

Change ID: `1tbw4-doc review-evidence-lane-clearing-docs`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-23
Wave: TBD

## Rationale

During the 1t8la independent delivery review (2026-07-22), the reviewer had to discover the multi-lane clearing protocol by reading `build_compact_review_event` and iterating on validator errors: a finding whose `blocking_required_lanes` names several lanes is cleared only by ORDERED reverification events in which each fresh, independent actor drops exactly their own lane from the list (the builder then auto-mints the `lane_reassessment` evidence and links it on the synthesis); passing the full list unchanged clears nothing, and passing an empty list from one actor fails with "clearing a required lane requires the same fresh independent actor". None of this is stated on the tool's registered docstring, in the tool-surface spec, or in the error's recovery text — the first multi-lane review paid an archaeology cost every future reviewer would repeat.

## Requirements

1. **The registered `wf_review_evidence` docstring documents lane clearing:** a finding's `blocking_required_lanes` persists on the chain head; each reverification that drops exactly the acting lane (fresh_context and independent required) clears that lane and auto-mints the linked `lane_reassessment` evidence; lanes clear one per event, in any order, until the head's list is empty (or an explicit operator waiver applies); a reverification that repeats the prior list verifies without clearing.
2. **The lane-clearing validator errors carry recovery guidance:** "clearing a required lane requires the same fresh independent actor" and the closure-time "retains unresolved required lanes" error each gain a sentence naming the required event shape (actor equals the single cleared lane, fresh + independent, `blocking_required_lanes` = prior list minus that lane).
3. **`docs/specs/mcp-tool-surface.md`'s `wf_review_evidence` entry** gains a short lane-clearing paragraph consistent with the docstring, and the review-wave prompt surfaces reference it where reviewers are pointed at repair chains.
4. **No behavioral change:** validators, builder logic, and event shapes are untouched; a docstring-comparison test pins that the registered description mentions lane clearing so future rewrites keep the contract discoverable.

## Scope

**Problem statement:** the lane-clearing contract is enforced but undocumented; reviewers learn it from validator archaeology.

**In scope:**

- `server_impl.py` registered `wf_review_evidence` docstring
- The two lane-clearing error messages in `review_evidence.py` (guidance sentences only)
- `docs/specs/mcp-tool-surface.md` tool entry; review-wave prompt pointer
- A docstring-content pin in tests

**Out of scope:**

- Any change to lane-clearing semantics, event shapes, or validation rules
- Auto-clearing conveniences (e.g. multi-lane clears in one event) — behavior change, separate decision

## Acceptance Criteria

- [ ] AC-1: the registered `wf_review_evidence` description explains per-lane clearing (single lane per event, actor-matching, fresh + independent, auto-minted reassessment evidence, waiver alternative) and a fresh MCP session can execute a multi-lane clearing sequence from the docstring alone.
- [ ] AC-2: both lane-clearing errors name the required event shape; the messages are pinned by tests.
- [ ] AC-3: the tool-surface spec and review-wave prompt reflect the same contract; docs gate and full framework suite green; no validator behavior changes (existing review-evidence tests unmodified except the new pins).

## Tasks

- [ ] Docstring + error-message guidance with pinned tests.
- [ ] Spec and prompt updates; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| docs-and-messages | implementer | — | Docstring, two messages, spec, prompt, pins |

## Serialization Points

- None; single small surface.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (tool entry). No boundary or flow changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The discoverability gap being closed. |
| AC-2 | required | The error is where the next reviewer actually meets the contract. |
| AC-3 | required | Contract consistency + standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-23 | Drafted from the 1t8la review observation: four validator-error iterations plus a read of `build_compact_review_event` (lines ~1900-1917) were needed to discover per-lane clearing before the chains could reach terminal state. | 1t8la events.jsonl reverification sequence; session review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-23 | Documentation and error-guidance only; no semantic change. | The enforced protocol is sound (per-lane independent reassessment is the point); the defect is discoverability. | Multi-lane clearing in one event (weakens per-lane independence, behavior change out of scope); leaving discovery to validator errors (the cost this change removes). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Docstring drifts from validator behavior later. | The docstring-content pin plus the message pins fail on rewording; semantics live in one validator module. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
