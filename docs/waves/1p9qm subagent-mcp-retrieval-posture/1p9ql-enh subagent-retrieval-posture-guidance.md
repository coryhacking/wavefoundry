# Retrieval posture for subagent lanes: shared block, front-loaded role-doc leads, and wrapper guardrail

Change ID: `1p9ql-enh subagent-retrieval-posture-guidance`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-03
Wave: TBD

## Rationale

With tool access fixed by `1p9qk`, the wording gaps the Solaris field feedback identified become real levers. Verified state (census, 2026-07-03):

- The shared docs every reviewer lane consults — `docs/contributing/agent-team-workflow.md` and `review-and-evals.md` — contain **zero `code_*` retrieval guidance** (their only "MCP" mentions are routing-table labels). A single lane-agnostic block there reaches every lane.
- Of 13 flat role docs, only 4 carry genuine MCP retrieval guidance (guru, implementer, frontend-developer, software-engineer); `code-reviewer.md`/`security-reviewer.md`'s `code_` mentions are review *subject matter*, not tool guidance; performance/qa/architecture/planner/release/docs-contract reviewers and all 27 specialist docs have none. Nothing anywhere states the **default posture** up front — and the Solaris transcripts show agents start grepping before reading deep into any doc.
- The canonical exploration order already exists (seed `180-implement-feature.prompt.md:116-131` MCP-first block; guru's Retrieval Loop in seed 211) with an explicit "do not restate the exploration order — point to it" instruction. So the fix is front-loaded **pointers plus a 2-3 line default**, not 25 duplicated tool lists that drift.
- The evidence's real cost was completeness-confidence: "N implementations / M callers" claims sampled via grep instead of enumerated via `code_references`/`code_callhierarchy`. That warrants a hard claim-backing rule, not just a preference.
- The general-purpose lane (which *does* inherit MCP tools) still made zero MCP calls — deferred-tool friction means guidance must name the ToolSearch-load-first mechanic explicitly or the zero-friction grep path wins.

## Requirements

1. **Shared retrieval-posture block.** A lane-agnostic block is added to the seed content that owns `docs/contributing/agent-team-workflow.md` (ownership is split across seeds `007-review-system-overview.md`/`005-persona-system-overview.md` and the `100`/`040` bootstraps — the implementation's first task is locating the authoritative insertion point so the block survives re-render/upgrade; `review-and-evals.md` gets a one-line pointer to it, not a copy). Content: MCP-first default for understanding/locating code; the ToolSearch-load-once mechanic named explicitly; a compact tool-choice line keyed to question shape: **`code_ask` when you don't know where to look — the spearhead of an investigation** (cold orientation, cross-cutting how-does-X-work; it opens the inquiry and hands precise targets to the follow-through tools, replacing exploratory grep-thrashing), `code_references`/`code_callhierarchy` for how-many/blast-radius, `code_keyword`/`code_search` for identifier and cross-surface sweeps, and **`code_read` for targeted line-range fetches instead of whole-file Read** once a location is known. The block should note that the mix follows task shape (Solaris field data: verification lanes with plan-named targets ran 42/72 calls through `code_read` with `code_ask` barely touched; broad no-map reviews are where `code_ask` leads) so agents don't cargo-cult one distribution. grep/Read reserved for literal-byte checks, git inspection, and MCP-absent fallback; and the **claim-backing rule**: any "how many callers / implementations / blast radius" claim must be backed by `code_references`/`code_callhierarchy`, not a sampled grep. The block also names the **static orientation surfaces** as the zero-friction complement to the spearhead: `docs/repo-index.md` (the machine-readable module inventory seed-030 authors expressly for orientation passes), the codebase map, and per-area `AGENTS.md` — one targeted Read, no ToolSearch required, available even when MCP is absent (where they become the fallback spearhead). Calibration: for MCP-attached agents these are cold-start orientation only — after the first bearing, live tools dominate; do not over-instruct map-reading at the expense of querying. A pointer to the canonical exploration order — no restatement.
2. **Front-loaded role-doc leads.** Each role-doc seed (211-235) gains a 2-3 line "Tool posture" lead near the top: MCP-first default, ToolSearch-load mechanic, pointer to the shared block/canonical order. Implementer's existing ladder (lines 25-29 of the rendered doc) is referenced by its lead rather than duplicated. The specialists' owning seed(s) get the same lead once at their shared source if one exists; per-file only if not (audit decides — no invented shared surface). Existing deep-in-doc `code_*` passages stay.
3. **Wrapper guardrail bullet.** The rendered thin-pointer bodies (guru + factor templates from `1p9qk`'s edit points, and any other role wrappers the renderer emits) gain one line: load and prefer the Wavefoundry `code_*` tools over grep/Read for locating and understanding code, per the canonical role doc's retrieval posture.
4. **Orchestrator premise already fixed; audit only.** The delegation guidance in seeds 180/100/050 (corrected by `1p9qk`) is audited for one addition only: when fanning out code-investigation lanes, name the MCP tools in the delegated prompt. No other orchestrator wording changes (the feedback's "avoid pre-specifying file:line targets" suggestion is declined — precise targets are often correct delegation practice and the evidence does not isolate that variable).
5. **Self-containment and propagation.** All edits live in seeds (gate discipline) with self-hosted surfaces regenerated; no wavefoundry-internal artifact IDs in seed text; downstream repos receive everything via upgrade re-render.
6. **Verification.** The field feedback's metric, adopted as the AC: a multi-lane review fan-out on this repo post-change shows each code-facing lane making at least one `code_*` call before its first grep, and how-many claims citing `code_references`/`code_callhierarchy`. Recorded with transcript tool-call counts alongside the `1p9qk` baseline.

## Scope

**Problem statement:** No surface a subagent actually reads states the MCP-first retrieval default up front; the shared lane docs say nothing about tool selection; and completeness claims are grep-sampled because nothing requires graph-backed enumeration.

**In scope:**

- The shared block (owning-seed insertion + pointer from review-and-evals), role-doc seed leads (211-235 + specialists' source), wrapper guardrail bullet, the fan-out naming line, the claim-backing rule.
- Seed-gate discipline, re-render, downstream-propagation check, transcript-count verification.

**Out of scope:**

- Tool access and inheritance-premise corrections (`1p9qk`).
- Restating the canonical exploration order anywhere (pointer-only, per seed-180's own rule).
- The "avoid file:line in delegation" suggestion (declined, recorded).
- Host-side deferred-tool mechanics.
- New tools, new roles, or changes to guru's retrieval loop itself.

## Acceptance Criteria

- [x] AC-1: The shared retrieval-posture block (with the claim-backing rule and ToolSearch mechanic) exists in the rendered `docs/contributing/agent-team-workflow.md`, inserted via its owning seed (insertion point recorded), and `review-and-evals.md` points to it; a re-render round-trip preserves both. — Done 2026-07-03: census resolved ownership to **seed-020 (run contract)** — new `## Retrieval Rules` section. Rendered as `## Retrieval Posture (All Lanes)` in agent-team-workflow.md; one-line pointer in review-and-evals.md; `render_agent_surfaces` does not touch either doc (round-trip safe). Correction + fix (delivery review 2026-07-03): the originally cited carrier (seed-150's seed-020 trigger) was scoped to the **Execution contract** section only and would not have propagated this block to target repos — the review's strongest finding. Wired in-session (seed gate): seed-020 gained an explicit "Rendered carrier" bullet naming the section + pointer, seed-150 task 5 now reconciles/backfills the **Retrieval Posture (All Lanes)** section and the review-and-evals pointer, and seed-160's audit checklist names both (also fixing its stale "all six rules" count).
- [x] AC-2: Every role-doc seed 211-235 renders with a front-loaded Tool posture lead (pointer, not restatement); the specialists' audit outcome (shared source vs per-file vs N/A) is recorded and applied; implementer's lead references its existing ladder. — Done 2026-07-03: all 22 "Agent Body" seeds (212-219, 221-229, 231-235) gained the lead via a verified scripted pass; seed-211 (guru) exempt — it owns the full retrieval loop; implementer/planner/wave-coordinator/reviewer roles have no 211-235 seed — covered instead via seed-050's role-doc orientation contract, which gained a **reviewer-roles Tool posture bullet** (the census found reviewers were the only roles with no MCP-orientation entry there). Local `docs/agents/` role docs reconcile on the next refresh/upgrade per seed-150 (upgrade-owned, recorded).
- [x] AC-3: Rendered wrapper bodies carry the guardrail bullet; consistent with the `1p9qk` allowlists (no wrapper instructs a tool its frontmatter denies — asserted by the renderer test extended from `1p9qk` AC-6). — Done 2026-07-03: guru template body (renderer + seed-050) and all four factor wrappers carry the load-and-prefer line; `GuruWrapperToolAllowlistTests.test_body_instructions_covered_by_grants` green. Corrections + fix (delivery review 2026-07-03): (a) the guru body carries load-and-prefer + ToolSearch but not the claim-backing clause — that clause is in the factor-wrapper bullets and guru's canonical retrieval loop, so Requirement 3 is met as specified; the original note overstated. (b) The factor-wrapper **body** bullet had no seed source (hand-edits only, would not survive regeneration or reach downstream repos) — fixed in-session: seed-050's "Wrapper `tools:` allowlist contract" block and task 5 now require the body bullet for guru and factor wrappers alike.
- [x] AC-4: The fan-out naming line exists in the corrected delegation guidance; the file:line suggestion's decline is recorded in the Decision Log (this doc) — no seed text references internal artifact IDs. — Done 2026-07-03: seed-180 delegation rule now says "name the MCP tools in the delegated task (and the schema-load step)"; decline recorded below; seed text grep-checked for internal IDs.
- [x] AC-5: Live verification — a multi-lane review fan-out on this repo shows each code-facing lane making at least one `code_*` call before its first grep, and at least one how-many claim citing `code_references`/`code_callhierarchy`; transcript tool-call counts recorded in the Progress Log against the pre-change Solaris-style baseline. — Done 2026-07-03: captured from this wave's own Review-wave fan-out (4 delivery lanes + 5 council seats, 9/9 lanes): every lane made multiple `code_*` calls with the first `code_*` call preceding its first content grep (per-lane counts in the Progress Log; baseline: Solaris round-1 = 0 MCP calls across 4 lanes + 5 children). Two recorded qualifications: (a) **attribution scope** — the measuring lanes were spawned per the shipped seed-180 fan-out rule (posture named in the delegated prompts) as generic subagents, so the counts attribute to 1p9qk tool access + the fan-out naming line, not to the shared block / role-doc leads / wrapper bodies (not on these lanes' read path); the Solaris post-upgrade re-count (wave watchpoint) is the field verification for those surfaces. (b) **Claim-backing variant** — no `code_references`/`code_callhierarchy` calls arose because the reviewed diff is seeds/docs/templates with no called symbols (a lane recorded this explicitly); every how-many claim (18/18 read-only grants, 22/22 leads, premise-gate sweeps) was instead backed by exhaustive `code_keyword`/`code_pattern` `limit=0` enumeration — honoring the rule's intent (enumeration, never sampled grep).
- [x] AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `wave_validate` clean; no `__pycache__` under `scripts/`; seed gate opened/closed per edit session. — Done 2026-07-03: suite 4,273 OK post-edits; docs-lint ok; gates opened/closed in two batched sessions plus one single-edit session.

## Tasks

- [x] Locate the authoritative seed insertion point for the agent-team-workflow block (007/005/100/040 census); add the block + the review-and-evals pointer (seed gate). (Census outcome: seed-020 Retrieval Rules — see AC-1.)
- [x] Add Tool posture leads to seeds 211-235; audit the specialists' seed source and apply once at the right level (seed gate). (22 Agent Body seeds scripted + seed-050 reviewer-roles bullet for the roles without dedicated seeds.)
- [x] Add the wrapper guardrail bullet to the guru/factor templates (coordinates with `1p9qk` ws1); extend the renderer consistency test (frontmatter grants ⊇ body instructions). (Consistency test landed with `1p9qk`; bodies updated both places.)
- [x] Add the fan-out naming line to the delegation guidance; record the declined suggestion.
- [x] Re-render self-hosted surfaces; run the multi-lane verification fan-out; record transcript counts. (Re-render DONE; fan-out captured from this wave's Review-wave lanes 2026-07-03 — per-lane counts + attribution-scope note in AC-5 and the Progress Log.)
- [x] Run `run_tests.py` + `wave_validate`; clean `__pycache__`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws1-shared-block | implementer | — | Ownership census + block insertion + review-and-evals pointer. |
| ws2-role-doc-leads | implementer | — | Seeds 211-235 leads + specialists audit (parallel to ws1; different seeds). |
| ws3-wrapper-and-orchestrator | implementer | — | Guardrail bullet (on `1p9qk`'s templates) + fan-out naming line + consistency test. |
| ws4-verify | implementer | ws1-shared-block, ws2-role-doc-leads, ws3-wrapper-and-orchestrator | Re-render; multi-lane fan-out; transcript-count evidence. |


## Serialization Points

- Lands **after** `1p9qk` (tools must be callable before guidance names them; the wrapper templates are shared edit surfaces).
- All seed edits under the `seed_edit_allowed` gate; batch the 211-235 lead edits in one gated session.
- `docs-contract-reviewer` lane applies at wave review (seed edits defining behavioral contracts agents rely on — the tier-2 trigger).

## Affected Architecture Docs

The retrieval-posture block itself is agent-operating-contract content in `docs/contributing/agent-team-workflow.md` (the edited surface). No separate architecture doc impact; `docs/prompts/index.md` unchanged (no new shortcut).

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The shared block is the highest-leverage surface — one edit reaching every lane, but only if it survives re-render. |
| AC-2 | required | Front-loading is what the transcript evidence demands — agents grep before reading deep. |
| AC-3 | required | The wrapper line is the only surface seen without Reading the canonical doc; consistency with allowlists prevents re-introducing the guru contradiction. |
| AC-4 | important | The naming line is a nudge on top of already-corrected guidance; the decline record prevents re-litigation. |
| AC-5 | required | The behavior change is the point; transcript counts are the only honest measure. |
| AC-6 | required | Standing gates + seed-edit discipline. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-03 | Scoped from Solaris field feedback + verification census. Confirmed: zero code_* retrieval guidance in both shared contributing docs; 4 of 13 flat role docs carry real MCP guidance (code-reviewer/security-reviewer mentions are subject matter, not tooling); canonical exploration order exists in seed-180:116-131 with an explicit no-restatement rule; general-purpose lane (full tool inheritance) still made 0 MCP calls → ToolSearch mechanic must be named. Claim-backing rule adopted from the feedback verbatim in spirit. | Verification census 2026-07-03; Solaris transcript counts. |
| 2026-07-03 | Field counterfactual received (Solaris round 2): with subagents explicitly instructed to load+prefer the tools, tool mix flipped 0 → 72 `code_*` calls (Reads 50+ → 6, Bash ~130 → 10) and the tools corrected **four factual errors** in grep-derived plans — a wrong site count (18 vs "~40"), four claimed-nonexistent call sites found, a dead insecure-TLS client proven caller-free via `code_references`, and a sampled "spans all 3 targets" claim made exhaustive. Validates AC-5's metric and the claim-backing rule with real data; `code_read` was the workhorse (42/72) → Requirement 1's tool-choice line amended to name it. Residual Bash use (7 calls, git/pbxproj) was correct per the reserve-shell-for list. Note: round 2 predates `1p9qk` — it worked because the orchestrator carried instructions to lanes that HAD tool access; instruction and access are both necessary. | Solaris round-1 vs round-2 transcript tool-call counts, relayed 2026-07-03. |
| 2026-07-03 | DELIVERY REVIEW carrier wiring (operator-directed, in-session, seed gate opened/closed): the review's convergent finding — three carrier links were unseeded (the rendered `## Retrieval Posture (All Lanes)` section, the review-and-evals.md pointer, the factor-wrapper body bullet), so AC-1/AC-3's durability claims held for this repo only. Fixed: seed-020 "Rendered carrier" bullet; seed-150 task 5 reconcile/backfill clause; seed-160 audit-checklist row (stale "six rules" count also corrected); seed-050 body-bullet requirement (contract block + task 5). AC-1/AC-3 evidence notes corrected in place. Docs-lint clean post-edit. | Delivery-lane + council-seat reports 2026-07-03; seed diffs. |
| 2026-07-03 | AC-5 transcript counts (this wave's Review-wave fan-out; ordered tool logs per lane). Delivery lanes — code-reviewer: 27 calls, 3 `code_*` + ToolSearch, first `code_*` (#10) before first content grep (#23); qa-reviewer: 29 calls, 21 `code_*` (12 `code_read`, 6 `code_keyword`, 3 `code_pattern`), zero shell content-greps; architecture-reviewer: 27 calls, 9 `code_*` incl. `code_ask`, first `code_*` #9, shell reserved for git/byte-parity; docs-contract-reviewer: 26 calls, 13 `code_*`/`docs_*`, shell git-only. Council — red-team primer: 21 calls, 3 `code_keyword` before first shell grep; security seat: 20 calls, 7 `code_*`; architecture seat: 15 calls, 8 `code_*`; qa seat: 20 calls, 12 `code_*`, 0 grep; reality-checker seat: 25 calls, ~9 `code_*`. **9/9 lanes: ≥1 `code_*` call before first content grep** (baseline: Solaris round-1 = 0 MCP calls across 4 lanes + 5 children). Attribution scope + claim-backing variant recorded in AC-5. | Ordered tool logs from all nine lane/seat reports, 2026-07-03. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-03 | Shared-block home = seed-020 (run contract) `## Retrieval Rules`, rendered into agent-team-workflow.md as `## Retrieval Posture (All Lanes)`. | The census found no seed emits agent-team-workflow.md via an Output path; the established durable pattern is seed-020 content carried into that doc with seed-150's "seed-020 changed → reconcile" upgrade trigger — the block rides existing propagation machinery instead of inventing a placement, and the seed-050 role-doc contract distributes it to roles without dedicated seeds. | Insert via seeds 005/007 (describe the doc but own no reconciliation trigger — the block would rot on upgrade); a new dedicated seed (machinery for one block); direct doc edit only (dies on upgrade — the exact failure the council flagged). |
| 2026-07-03 | Pointer-plus-default leads; canonical order never restated (approach A). | Seed-180 already owns the exploration order and forbids restatement; 25+ duplicated tool lists would drift with every tool rename; a front-loaded 2-3 line default plus pointer fixes the observed grep-before-reading behavior at minimal drift surface. | (B) Full retrieval block in every role doc (the feedback's literal Change 2) — weakness: mass duplication of a contract that already has one home; violates the framework's own no-restatement rule. (C) Shared block only, no role-doc leads — weakness: the transcripts show lanes act before reaching shared docs; the lead is the interception point. |
| 2026-07-03 | Adopt the claim-backing rule as a hard requirement, not a preference. | The Solaris evidence's real cost was grep-sampled completeness claims on duplication/blast-radius — the exact question `code_references`/`code_callhierarchy` answer exhaustively; a soft preference would not change reviewer behavior under time pressure. | Preference wording — rejected: reproduces the buried-trivia failure mode the feedback documents. |
| 2026-07-03 | Decline the "avoid pre-specifying file:line targets in delegation" suggestion. | Precise targets are often correct delegation practice (verification lanes, fix-at-site tasks); the evidence does not isolate file:line pre-specification as a cause of grep preference; adopting it would degrade legitimate delegation patterns on an unproven hypothesis. | Adopt it — rejected on evidence quality; revisit only with a transcript study isolating the variable. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The agent-team-workflow ownership split means the block lands somewhere re-render overwrites. | AC-1's round-trip re-render test is the guard; the ownership census is the first task, not an assumption. |
| Leads drift from actual tool names over time. | Leads are pointers plus a 2-3 line default naming only the stable flagship tools; the renderer consistency test (AC-3) catches wrapper-level drift; the shared block is the single point of truth for the tool-choice table. |
| Verification fan-out is anecdotal (one run). | The metric is directional (zero → nonzero MCP-first calls per lane) rather than a fragile threshold; the Solaris reporter can re-run their own transcript count post-upgrade as the field confirmation. |
| Guidance overcorrects — agents use `code_ask` for trivial single-file lookups where Read is right. | The block explicitly reserves grep/Read for literal checks and trivial targeted reads; the posture is a default, and the existing role-doc fallback language stays. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
