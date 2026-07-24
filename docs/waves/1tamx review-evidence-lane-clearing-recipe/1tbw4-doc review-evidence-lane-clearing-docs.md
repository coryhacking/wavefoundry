# Document the wf_review_evidence Lane-Clearing Recipe

Change ID: `1tbw4-doc review-evidence-lane-clearing-docs`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-23
Wave: `1tamx review-evidence-lane-clearing-recipe`

## Rationale

During the 1t8la independent delivery review (2026-07-22), the reviewer needed four validator-error iterations plus a read of `build_compact_review_event` to clear a multi-lane finding chain. The HIGH-LEVEL rule is already documented — the registered description says fresh independent actors clear their own required lanes (`server_impl.py:24606`), the MCP spec says the same (`docs/specs/mcp-tool-surface.md:564`), and seed 209 documents exact actor matching, freshness, independence, linkage, and single-use evidence (`209-agent-harness-core.prompt.md:158`). What is missing everywhere is the OPERATIONAL RECIPE: inspect the current head with `event="list"`, submit one reverification per lane where the actor equals the single removed lane and `blocking_required_lanes` is the current list minus that actor, and understand that repeating the list unchanged verifies without clearing. This change sharpens the existing surfaces with that recipe and makes the two lane-clearing diagnostics state-derived and actionable; it changes no state machine and no event shape.

## Requirements

1. **The registered `wf_review_evidence` description carries the recipe:** per-lane clearing means one lane per reverification event; the actor equals the removed lane; `fresh_context=true` and `independent=true` are required; the builder auto-mints the linked `lane_reassessment` evidence; a reverification repeating the prior list verifies without clearing; start from `event="list"` to read the current head before every clearing event. The description also states, exactly and only: a separately recorded protocol-valid operator waiver is another terminal state; it is not a lane-reverification shortcut. (The public tool authors no waiver — typed waiver authoring would be a separate behavioral change.)
2. **Both lane-clearing diagnostics become state-derived recovery guidance:** the builder error at `review_evidence.py:1902` ("clearing a required lane requires the same fresh independent actor") and the closure error at `review_evidence.py:2778` ("retains unresolved required lanes") each append: call `event="list"` for the finding, choose one currently blocking lane as the actor, then submit a fresh independent reverification with `blocking_required_lanes` equal to the current list minus that actor. This shape stays correct under sequential multi-reviewer activity because it never assumes the caller knows the pre-action head.
3. **Existing surfaces are sharpened, not duplicated:** the spec's existing `wf_review_evidence` bullet is expanded with the recipe (no new parallel prose); seed 209's lane section gains the recipe steps. The renderer-owned review-wave prompt block (`render_agent_surfaces.py:88` ownership; `docs/prompts/review-wave.prompt.md:70`) is NOT edited directly — its existing pointer to seed 209 is verified as the delivery path for the sharpened seed.
4. **No state-machine or event-shape change:** validators, builder transitions, and record shapes are untouched. Diagnostics are observable behavior and DO change (guidance text only); tests pin the new guidance.

## Scope

**Problem statement:** the lane-clearing rule is documented but the event transformation that satisfies it is not; reviewers reconstruct it from validator archaeology, and the errors do not route to a state-derived recovery.

**In scope:**

- Sharpening the registered `wf_review_evidence` description (recipe + waiver-terminal-state sentence)
- Appending recovery guidance to the two diagnostics at `review_evidence.py:1902` and `:2778`
- Expanding the existing spec bullet; sharpening seed 209; verifying the review-wave prompt's existing seed-209 pointer
- Semantic description anchors and error-guidance pins in tests; a delivery verification through the reload path

**Out of scope:**

- Any state-machine, validator-semantics, or event-shape change
- Typed operator-waiver authoring through the public tool (separate behavioral change)
- Editing the renderer-owned review-wave prompt block
- Multi-lane clearing in one event (weakens per-lane independence)

## Acceptance Criteria

- [x] AC-1: the registered description contains the operational recipe, and a fresh MCP session can execute a multi-lane clearing sequence from the description alone using only public call shapes (`event="list"` then per-lane reverifications); the waiver sentence states the terminal-state fact without presenting an executable path.
- [x] AC-2: both diagnostics carry the state-derived recovery text (list, choose one blocking lane as actor, current list minus that actor); each is pinned by its own test.
- [x] AC-3: description tests assert stable semantic anchors through the existing public MCP schema-inspection seam (`event="list"`, one lane per reverification, actor equals the removed lane, `fresh_context=true`, `independent=true`, auto-minted `lane_reassessment`) rather than pinning the docstring verbatim.
- [x] AC-4: the spec bullet and seed 209 carry the same recipe; the review-wave prompt's renderer-owned block is unchanged and its seed-209 pointer verified; docs gate green.
- [x] AC-5: delivery verification through the reload path — `wf_reload_mcp` reports `wf_review_evidence` as description-changed and the refreshed tool description contains the recipe; full framework suite green with existing lane-progression and reassessment-evidence tests unmodified.

## Tasks

- [x] Sharpen the registered description; append the two diagnostics' recovery text.
- [x] Expand the spec bullet; sharpen seed 209; verify the prompt pointer.
- [x] Semantic anchors + message pins; reload-path delivery verification; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| docs-and-diagnostics | implementer | — | Description, two messages, spec, seed, pins |

## Serialization Points

- None; small coordinated surface.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (existing tool entry expanded). No boundary or flow changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The discoverability gap being closed, executable from public shapes only. |
| AC-2 | required | The error is where the next reviewer meets the contract; recovery must be state-derived. |
| AC-3 | required | Anchors survive rewording; verbatim pins would rot. |
| AC-4 | required | Sharpen owned sources; never edit renderer-owned output. |
| AC-5 | required | Live delivery proof through the reload path + standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-23 | Drafted from the 1t8la review observation (four validator-error iterations plus a `build_compact_review_event` read to discover the recipe). | 1t8la events.jsonl reverification sequence |
| 2026-07-23 | Revised per operator plan review before admission: waiver removed from the executable recipe (public tool authors no waiver — `server_impl.py:24552`; kept as a terminal-state statement only); baseline corrected (high-level rule already present in description/spec/seed 209 — the gap is the operational recipe); renderer-owned review-wave prompt block excluded from direct edits in favor of sharpening seed 209 (`render_agent_surfaces.py:88` ownership); recovery guidance made state-derived starting from `event="list"`; verbatim docstring pin replaced with semantic anchors through the existing schema-inspection seam plus a reload-path delivery verification; "no behavioral change" narrowed to "no state-machine or event-shape change" since diagnostics are observable behavior. | Operator plan review findings (2 P1, 2 P2) |
| 2026-07-23 | Implemented: registered description carries the state-derived recipe plus the waiver terminal-state sentence (no executable waiver path); both diagnostics (`review_evidence.py` builder clear-mismatch and closure unresolved-lanes) append the list-first recovery text; spec bullet expanded in place; seed 209 Repair re-verification section gains the three-step recipe with the always-re-list caution; review-wave prompt's renderer-owned block untouched, its seed-209 pointer verified at line 74. | Diffs; pointer grep |
| 2026-07-23 | Tests: `test_review_evidence_description_carries_lane_clearing_recipe` asserts seven semantic anchors through the canonical fresh-build description accessor (one anchor adjusted to a line-wrap-safe phrase after a live failure); `test_lane_clearing_errors_carry_state_derived_recovery_guidance` pins both recovery messages through the public typed path (clear-both rejection + closure validation). Reload delivery check executed live: `wf_reload_mcp` reported `wf_review_evidence` in `description_changed_tools` with the list_changed notification sent; the fresh-build description contains the recipe (the anchors test is that check). Honest caveat: this session's own client-side tool cache still serves the pre-change description, the documented reload-survivor host limitation — a reconnect surfaces it. | Test runs OK; `wf_reload_mcp` envelope |
| 2026-07-23 | Full suite green: 6,170 tests across 59 files OK in a single run (2 net-new tests); existing lane-progression and reassessment-evidence tests unmodified. AC-1 through AC-5 met. | Suite output |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-23 | Documentation and diagnostics guidance only; no state-machine or event-shape change. | The enforced protocol is sound (per-lane independent reassessment is the point); the defect is discoverability and recovery routing. | Multi-lane clearing in one event (weakens per-lane independence); typed waiver authoring (behavioral change, separate decision); leaving discovery to validator archaeology. |
| 2026-07-23 | Deliver the recipe to review prompts through seed 209, not the generated prompt block. | The review-wave prompt block is renderer-owned and already points at seed 209; editing generated output violates the seed-first contract. | Changing the shared renderer block (only warranted if every review carrier should embed the recipe inline; rejected as duplication). |
| 2026-07-23 | Recovery guidance starts from `event="list"`. | A caller cannot reliably know the current head after another reviewer acted; state-derived recovery is safe under sequential multi-reviewer activity. | "Prior list minus acting lane" phrasing (assumes head knowledge the caller may not have). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Description drifts from validator behavior later. | Semantic anchors + message pins fail on contract-losing rewrites; semantics live in one validator module. |
| Seed 209 sharpening drifts from the rendered prompt pointer. | AC-4 verifies the pointer as part of delivery; renderer ownership untouched. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
