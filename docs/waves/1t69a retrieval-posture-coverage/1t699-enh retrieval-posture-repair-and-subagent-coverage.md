# Retrieval Posture: Repair-Window and Subagent Coverage in Every Project's Instructions

Change ID: `1t699-enh retrieval-posture-repair-and-subagent-coverage`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-21
Wave: `1t69a retrieval-posture-coverage`

## Rationale

Operator-observed lapse on wave 1seax (2026-07-21): during the late review-repair cycles, code investigation (literal censuses, region reads, claim verification) ran through harness `grep`/`sed`/`Read` instead of the MCP retrieval tools, so the work earned no context-efficiency credit and, more importantly, bypassed the tools the framework exists to exercise. This happened even though the posture instructions exist, because the two strongest delivery channels are implementation-framed:

- The in-band `retrieval_posture` directive (served by `wf_implement_wave`, `wf_prepare_wave(mode='create')`, `wf_reopen_wave`, `wf_review_wave`) names "implementation AND review" but not repair/verification work inside a review cycle, and not subagent briefs.
- Seed 180's canonical exploration order is introduced as "exploration **before any code edit**", which does not pattern-match to mid-review censuses, reverification reads, or refutation probes.

Seed 020's Retrieval Rules already state the lane-and-subagent scope correctly; the fix is to make the other channels say the same thing, so every project receives the full-scope rule through every channel it already has. The operator direction is explicit: no new tracking or separate accounting, just make the tools the default for all investigation so overall efficiency improves.

## Requirements

1. **Directive covers repair and subagents:** `_RETRIEVAL_POSTURE_DIRECTIVE` (single constant, no duplicated text) states that MCP-first retrieval applies to implementation, review verification, AND repair/reverification work within review cycles, and that agents must carry the same posture into the prompts of subagents they brief for investigation or verification. Executed probes (test runs, mutation probes, git operations) remain legitimately shell work.
2. **Seed 180 reframes the exploration order:** the canonical exploration-order preamble applies to any code investigation at any lifecycle stage (implementation, review verification, repair), not only "before any code edit". The ordered tool list itself is unchanged.
3. **Seed 100 carries the rule to review-phase renders:** add a one-line pointer to seed 020's **Retrieval Rules** in seed 100's explicit `review-wave` and `close-wave` render-rule bullets. Do not copy seed 180's exploration list, its full implementation directive, or its delegation text into either rule. The audit is recorded in this change's Progress Log; current-tree evidence shows both rules lack the pointer, so both insertions are required for this implementation.
4. **Pointer weave, not restatement:** new text points at seed 020's Retrieval Rules as the source of truth for the lane/subagent scope; no seed restates the full rule (consistent with the existing do-not-restate convention for the exploration order).
5. **No new tracking:** no new sensor, stage, bucket, or telemetry field. The existing review-stage accounting absorbs the work wherever it happens.

## Scope

**Problem statement:** the MCP-first retrieval posture reaches every project, but its two strongest channels are implementation-framed, so review-repair investigation and briefed subagents fall outside the instruction's pattern-match.

**In scope:**

- `_RETRIEVAL_POSTURE_DIRECTIVE` text in `server_impl.py` (framework_edit_allowed gate)
- `seeds/180-implement-feature.prompt.md` exploration-order preamble (seed_edit_allowed gate)
- `seeds/100-project-prompt-surface-bootstrap.prompt.md` review-wave and close-wave render rules (seed_edit_allowed gate; audit executed 2026-07-21, both pointers confirmed absent, both insertions required)
- Wavefoundry's own rendered surfaces regenerated after the seed edits (self-hosting)

**Out of scope:**

- Any sensor/telemetry change (operator direction: no separate tracking)
- Reviewer role seeds 214/239 (already carry tool-posture front-loads)
- Seed 020 Retrieval Rules (already correct; it is the pointed-at source of truth)

## Acceptance Criteria

- [x] AC-1: The directive constant names repair/reverification work and subagent briefs; the existing source-census test that pins the directive on all four serving paths still passes, and a content assertion covers the new phrases.
- [x] AC-2: Seed 180's exploration-order preamble is stage-neutral (implementation, review verification, repair) with the tool order unchanged.
- [x] AC-3: Seed 100's `review-wave` and `close-wave` render rules each carry a one-line pointer to seed 020's **Retrieval Rules**, without restating seed 180's exploration list or implementation directive; the before/after audit is recorded in the Progress Log.
- [x] AC-4: Wavefoundry's own rendered prompt surfaces are regenerated and docs validation passes.
- [x] AC-5: Full framework test suite passes (6,086 tests across 59 files, OK, 2026-07-21).

## Tasks

- [x] Open `framework_edit_allowed`; extend `_RETRIEVAL_POSTURE_DIRECTIVE`; update/extend its content test; close gate.
- [x] Open `seed_edit_allowed`; reword seed 180 preamble; add the seed-020 Retrieval Rules pointer to seed 100's `review-wave` and `close-wave` bullets without copying seed 180 text; record the before/after audit in the Progress Log; close gate.
- [x] Regenerate rendered surfaces (sync/render path) and run docs validation. (The affected renders are the agent-maintained prompt surfaces, updated per the revised seed rules: implement-wave reframed, review-wave and close-wave gained the pointer line; platform hook configs are untouched by this change so render_platform_surfaces had nothing to regenerate. Docs-lint: ok. Live reload served: the updated directive now ships in-band.)
- [x] Full suite. (6,086/6,086 OK, 273.7s, 2026-07-21.)

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| directive | implementer | — | Constant + test, framework gate |
| seeds | implementer | — | Seeds 180/100, seed gate; both seed-020 pointers on 100 (audit done) |
| render-verify | qa-reviewer | directive + seeds | Regenerate surfaces, docs gate, suite |


## Serialization Points

- None between directive and seeds (disjoint files); render-verify runs after both.

## Affected Architecture Docs

N/A: instruction-surface text only; no module boundary, flow, or verification-architecture change. `docs/references/context-efficiency.md` mentions the directive's content in prose; audit it for drift after the wording change and refresh the sentence if it quotes superseded text.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The zero-render channel every project gets on upgrade. |
| AC-2 | required | The implementation-framed wording is the observed failure cause. |
| AC-3 | required | Review-phase renders are where the lapse lived. |
| AC-4 | required | Self-hosting fidelity; seeds are source of truth. |
| AC-5 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-21 | Drafted from the operator-observed 1seax review-window lapse; channel census run via code_ask/docs_search/code_read (directive constant at server_impl.py:13316; seed 180 preamble; seed 020 already lane/subagent-complete; role seeds 214/239 already postured). | 1seax CE ledger; retrieval citations in plan session. |
| 2026-07-21 | Plan-review repair: direct inspection found seed 100's `review-wave` and `close-wave` bullets both lack a retrieval pointer, while `implement-wave` carries seed 180's full rule rather than a seed-020 pointer. AC-3 and the seed task now require both one-line seed-020 pointers, prohibit copying seed 180 text, and require this audit to be recorded here. | Independent plan review; seed 100 lines 92, 98, and 100. |
| 2026-07-21 | Implemented: directive constant extended (two additions: repair/reverification scope with executed-probes carve-out; subagent-brief carry); content test strengthened with three new phrase assertions (62/62 OK). Seed 180 preamble reframed stage-neutral with the seed-020 scope pointer; tool order untouched. Seed 100: both one-line pointers appended (close-wave, review-wave bullets), no seed-180 text copied. Local renders updated: implement-wave posture bullet reframed stage-neutral; review-wave and close-wave gained the pointer line. | server_impl.py:13316; seeds 180/100 diffs; test_server_context_efficiency 62 OK. |
| 2026-07-21 | Deviation (surfaced, not silent): the framework's shipped lifecycle-prompt templates (`install/lifecycle-prompts/review-wave.prompt.md`, `close-wave.prompt.md`) carried no retrieval line at all and are the most direct review/close instruction surface target projects receive; added the same one-line seed-020 pointer to each under `framework_edit_allowed`. In-scope by the wave objective (every project's instructions), not named in the original scope list. | Template diffs; grep showed zero retrieval mentions in all five templates. |
| 2026-07-21 | Gapfill: test-file location and pin inspection used harness grep/Read because framework test internals are deliberately excluded from the semantic code index; all indexed-surface investigation (directive constant, seeds, prompts, renders census) ran through code_ask/code_keyword/code_read/docs_search. | Session telemetry; index exclusion policy in AGENTS.md MCP section. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-21 | No new sensor or tracking bucket; instruction-surface change only. | Operator direction: "we don't have to track it separately, I just want the tools used". | Windowed per-repair-cycle posture sensor (offered, declined as unnecessary). |
| 2026-07-21 | Point at seed 020 for the lane/subagent scope instead of restating it. | Single source of truth; matches the existing do-not-restate convention. | Restate the full rule in each surface (drift risk). |
| 2026-07-21 | Make both seed 100 review-phase insertions explicit rather than audit-and-skip. | The live tree shows neither `review-wave` nor `close-wave` currently carries the pointer; explicit targets prevent copying the implementation-only seed 180 rule by mistake. | Leave the target conditional (ambiguous implementation scope). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Directive text growth dilutes the rule | Keep the addition to one sentence for repair scope and one for subagent briefs; the Gapfill escape hatch stays. |
| Seed wording drift vs rendered surfaces | Regenerate Wavefoundry's own surfaces in the same change; docs gate verifies. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
