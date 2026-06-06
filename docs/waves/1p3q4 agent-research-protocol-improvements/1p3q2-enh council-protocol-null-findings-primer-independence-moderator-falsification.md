# Council protocol — null findings, primer independence, moderator falsification, axis declaration

Change ID: `1p3q2-enh council-protocol-null-findings-primer-independence-moderator-falsification`
Change Status: `implemented`
Owner: framework-maintainer
Status: planned
Last verified: 2026-06-06
Wave: 1p3q4 agent-research-protocol-improvements

## Rationale

A council review of the `1p3ao` dynamic-workflows roadmap doc surfaced three failure modes in the current sequential council protocol that are addressable now — without dynamic workflows — as seed-level protocol additions. The same review also identified a gap in the Archetype Council's axis-declaration ordering that is independently fixable.

**Failure mode 1 — Silent null findings.** When a seat has no findings in its lane, the current protocol produces no output for that seat. The moderator cannot distinguish "this lane is genuinely clear" from "this seat was surfaced poorly and missed something." Silence and absence look identical. This is the same gap the Guru multi-angle research protocol (`1p3q1`) addresses for retrieval: null results must be stated as explicit negative evidence, not omitted.

**Failure mode 2 — Invisible primer anchoring.** The red-team primer is shared with all Phase 2 seats by design — this is intentional and correct. But the current protocol does not instruct seats to form and state their initial read *before* engaging with the primer. In the current sequential single-session execution, every seat reads the primer first and anchors on it before forming its own view. When the primer is wrong or overweighted, this contamination is invisible. Making each seat declare its pre-primer view — even one sentence — makes the primer's influence auditable rather than hidden.

**Failure mode 3 — Unchecked moderator confirmation bias.** The moderator synthesizes across seats and produces a verdict, but the current protocol does not require an explicit falsification check before finalizing. This is the same pattern as Guru's single-hypothesis retrieval: confirming evidence is gathered, the hypothesis is never challenged, and a wrong verdict can be confidently issued. The risk is highest for `PASS` verdicts on waves the team wants to ship — moderator bias toward approval is strongest exactly when the stakes are highest.

**Failure mode 4 (Archetype Council only) — Post-hoc axis declaration.** The Archetype Council requires each seat to name its axis in the output, but does not require the seat to declare the axis *before* reading the artifact. A seat can drift into another seat's axis without realizing it, producing overlapping coverage that the `axes_covered` check catches only after the fact. Declaring the axis before engaging with the artifact locks in the lens before it can be shaped by the artifact's framing.

These four additions are protocol-level changes to `seed-215` (Wave Council) and `seed-236` (Archetype Council). They do not require dynamic workflows, new MCP tools, or infrastructure changes. They are a direct lesson from the multi-angle research discipline being added to Guru in `1p3q1` — the same null-result, falsification, and independence principles apply to review councils.

**Relationship to `1p3ao`:** The workflow-era improvement (true parallel seat isolation) is a separate and later change. These additions make the current sequential council more transparent and rigorous; they are not a substitute for parallel execution, but they close gaps that parallel execution alone would not fix.

## Requirements

### Wave Council (seed-215)

1. Each Phase 2 fixed seat must begin its output with a **pre-primer statement**: one sentence stating its initial read of the artifact *before* engaging with the red-team primer. The seat then explicitly states whether the primer confirmed, extended, or changed that read. Format: `Pre-primer read: [one sentence]. Primer effect: [confirmed / extended / changed — one sentence on what shifted / not applicable — primer skipped at lightweight tier].`
2. Each Phase 2 fixed seat must explicitly state **"No findings in my lane"** when it has no findings to report — along with a one-line statement of what it checked and why nothing surfaced. Silence is not a valid seat output.
3. The rotating fifth seat is subject to the same null-finding requirement: if no credible alternative exists, it must say why — the existing seed already requires this ("silence is not" valid), but the requirement is extended to match the null-finding framing used across all seats.
4. The moderator must run an explicit **Falsification Check** as the penultimate step before finalizing the verdict: state the working verdict in one sentence, name the strongest argument against it (sourced from any seat output or the primer), and state why that argument does not change the conclusion. If the argument does change the conclusion, revise the verdict before finalizing. Record the falsification check in the synthesis output under a `## Falsification Check` heading.
5. When two or more seats surface the **same finding** in a sequential council run, the synthesis must flag it as potentially correlated — "seats A and B both surfaced finding X; treat as one signal, not independent confirmation, given sequential execution" — rather than counting it as stronger independent evidence.

### Archetype Council (seed-236)

6. Each Phase 2 archetype seat must **declare its axis before reading the artifact**: the first thing each seat records is `Axis: [axis name] — [one-sentence description of what this axis is looking for]`, stated before any artifact analysis. This locks the lens before the artifact's framing can shape it.
7. Each Phase 2 archetype seat is subject to the same **null-finding requirement** as Wave Council seats: if no findings surface under the declared axis, the seat must state "No findings under [axis name]" with a one-line explanation of what was checked.
8. The Archetype Council moderator is subject to the same **Falsification Check** requirement as the Wave Council moderator (Requirement 4 above).

## Scope

**Problem statement:** Both councils have protocol gaps that allow silent null findings, invisible primer anchoring, unchecked moderator confirmation bias, and post-hoc axis drift in the Archetype Council. All four are addressable with seed instruction additions, without infrastructure changes.

**In scope:**

- `seed-215` (`215-wave-council.prompt.md`): pre-primer statement, null-finding requirement for all seats, correlated-finding flag in synthesis, moderator falsification check.
- `seed-236` (`236-archetype-council.prompt.md`): axis-declaration-before-artifact, null-finding requirement, moderator falsification check.
- `docs/agents/wave-council.md` (if it exists): regenerate from updated seed.
- `docs/agents/archetype-council.md` (if it exists): regenerate from updated seed.
- CHANGELOG bullet under `[Unreleased]` → `### Changed`.

**Out of scope:**

- True parallel seat isolation — requires dynamic workflows (`1p3ao` T1.1). These additions make the sequential protocol more transparent; they do not eliminate cross-contamination.
- Changes to `seed-225` (red-team standalone) — red-team is a single-seat protocol; the multi-seat isolation requirements do not apply.
- Changes to `seed-007` (review system overview) — only update if the overview's description becomes materially inconsistent after this change; verify at implementation.
- Changes to the verdict format, severity ladder, lifecycle signoff shape, or `seed-209` finding record schema.
- Any MCP tool changes — `wave_review` and `wave_prepare` tool surfaces are unchanged.

## Acceptance Criteria

- [x] AC-1: `seed-215` Phase 2 seat instructions require a pre-primer statement (`Pre-primer read:` + `Primer effect:`) before any seat findings.
- [x] AC-2: `seed-215` requires each fixed seat to explicitly state "No findings in my lane" (with one-line check description) when it has no findings — silence is not a valid output.
- [x] AC-3: `seed-215` rotating fifth seat null-finding language is aligned with the null-finding framing across all seats.
- [x] AC-4: `seed-215` moderator synthesis includes a required `## Falsification Check` step: working verdict → strongest counter-argument → why verdict holds (or verdict revision).
- [x] AC-5: `seed-215` synthesis instructions require correlated-finding flagging when two or more seats surface the same finding in a sequential run.
- [x] AC-6: `seed-236` Phase 2 seat instructions require axis declaration (`Axis: [name] — [description]`) as the first recorded output, before any artifact analysis.
- [x] AC-7: `seed-236` requires each archetype seat to state "No findings under [axis name]" (with one-line check description) when no findings surface — aligned with AC-2 framing.
- [x] AC-8: `seed-236` moderator synthesis includes the same `## Falsification Check` step required by AC-4.
- [x] AC-9: Existing protocol sections in both seeds (phase shape, seat roster, challenge round trigger, anonymized synthesis, output schema, anti-patterns, non-waiver guard) remain unchanged — verified by diff review.
- [x] AC-10: `docs-lint` returns clean.
- [~] AC-11: If `docs/agents/wave-council.md` and/or `docs/agents/archetype-council.md` exist, they are regenerated from their updated seeds. (deferred — neither rendered doc exists in this repo)
- [x] AC-12: `seed-215` Phase 2 seat instructions are structured as explicit numbered steps (Steps 1–5) with "do not read yet" guards at Step 1, and an auditability-not-isolation explanation at Step 1 so agents apply the step in good faith.
- [x] AC-13: `seed-236` Phase 2 seat instructions are structured as explicit numbered steps (Steps 1–3) with "do not read the artifact yet" guard at Step 1.
- [x] AC-14: Both seeds require a mandatory `### Recommendations Verdict` table in synthesis — every advisory and recommended finding verdicted `fix now` / `defer` / `accept` with rationale and red-team challenge folded into a single table. Advisories may not go unverdicted.
- [x] AC-15: Both seeds require a red-team closing reconciliation pass integrated into the recommendations verdict table — challenges each verdict row and may add new findings as rows. No separate section; one unified table.
- [x] AC-16: `seed-215` synthesis includes a pre-primer read quality check — moderator flags verbatim phrase echo or exact primer framing in seat pre-primer reads as contamination signal; topical overlap alone is not flagged.
- [x] AC-17: `seed-215` Step 2 `Primer effect` one-sentence explanation is mandatory regardless of state — label alone is not valid output.
- [x] AC-18: Both seeds include an `## Output Verbosity` section specifying summary-level output: seat summaries (one paragraph each), recommendations verdict table always shown in full, falsification check condensed to one line on a clean PASS and shown in full only when findings are present or verdict is not PASS.

## Tasks

- [x] Edit `seed-215`: add pre-primer statement instruction to Phase 2 seat protocol.
- [x] Edit `seed-215`: add null-finding requirement to Phase 2 fixed seat protocol.
- [x] Edit `seed-215`: align rotating fifth seat null-finding language with fixed-seat framing.
- [x] Edit `seed-215`: add Falsification Check step to moderator synthesis protocol.
- [x] Edit `seed-215`: add correlated-finding flag instruction to synthesis protocol.
- [x] Edit `seed-236`: add axis-declaration-before-artifact instruction to Phase 2 seat protocol.
- [x] Edit `seed-236`: add null-finding requirement to Phase 2 archetype seat protocol.
- [x] Edit `seed-236`: add Falsification Check step to Archetype Council moderator synthesis.
- [x] Diff review: confirm no existing sections modified beyond insertion points in either seed.
- [x] Check whether `docs/agents/wave-council.md` and `docs/agents/archetype-council.md` exist; regenerate if present. (neither exists)
- [x] Run `docs-lint`.
- [x] Add CHANGELOG bullet.
- [x] In-session refinement: restructure Phase 2 seat instructions in `seed-215` and `seed-236` from flat bullet lists to explicit numbered steps with explicit "do not read the artifact/primer yet" instructions at each pre-commitment step.
- [x] In-session fix (RC-ADV-1): add auditability-not-isolation explanation to `seed-215` Step 1 so agents understand the purpose of the pre-primer read in sequential execution.
- [x] In-session addition: add mandatory `### Recommendations Verdict` table to synthesis in `seed-215` and `seed-236` — every advisory and recommended finding must be verdicted `fix now` / `defer` / `accept` with a one-line rationale before the council output is complete.
- [x] In-session addition: add `recommendations_verdict_table` to the output shape in both seeds.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-215 edits | framework-maintainer | — | Five insertion points across Phase 2 seat and synthesis sections. |
| seed-236 edits | framework-maintainer | — | Three insertion points; independent of seed-215 edits. |
| Agent doc regeneration | framework-maintainer | seed-215 edits, seed-236 edits | Only if rendered docs exist. |
| Verification | framework-maintainer | Agent doc regeneration | Diff review + docs-lint. |

## Serialization Points

- `seed-215` and `seed-236` are independent files; edits can proceed in parallel.
- Agent doc regeneration depends on both seed edits completing.

## Affected Architecture Docs

N/A — changes are confined to the two council seeds and their rendered agent docs. No boundary, flow, layering, or cross-cutting impact. The council tool surface (`wave_review`, `wave_prepare`) is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Pre-primer statement is the load-bearing addition for primer-anchoring visibility. |
| AC-2 | required | Null-finding requirement closes the silent-absence gap — the core motivation for this change. |
| AC-3 | important | Alignment pass; the rotating seat's null-finding language already exists, just inconsistently framed. |
| AC-4 | required | Moderator falsification check addresses confirmation bias at the synthesis level — the highest-leverage single addition. |
| AC-5 | required | Correlated-finding flag prevents sequential-execution coincidence from being misread as independent confirmation. |
| AC-6 | required | Axis declaration before artifact engagement is the Archetype Council's primary gap. |
| AC-7 | required | Null-finding parity with Wave Council (AC-2). |
| AC-8 | required | Falsification check parity with Wave Council (AC-4). |
| AC-9 | required | Existing protocol is validated; do not drift it. |
| AC-10 | required | docs-lint is a pre-merge gate. |
| AC-11 | important | Rendered docs must stay in sync if they exist. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-06-06 | Change doc created from council review of `1p3ao` and operator follow-up analysis of council failure modes. | `wave_new_enhancement` → `1p3q2`. |
| 2026-06-06 | In-session refinement during delivery council review: Phase 2 seat instructions in both seeds restructured from flat bullet lists to explicit numbered steps. The flat-list form allowed the pre-primer read and axis declaration to be written after the primer/artifact was already in context. Numbered steps with explicit "do not read yet" guards enforce the correct execution order. | seed-215 and seed-236 diffs; docs-lint clean. |
| 2026-06-06 | In-session fix (RC-ADV-1): added auditability-not-isolation explanation to seed-215 Step 1. "Do not read yet" without a why invites mechanical compliance; explaining that sequential execution makes true isolation impossible — and that the step is an auditability discipline — gives agents the intent they need to apply the step in good faith. | seed-215 diff; docs-lint clean. |
| 2026-06-06 | In-session addition: mandatory Recommendations Verdict table added to synthesis in seed-215 and seed-236. Every advisory and recommended finding must be verdicted fix-now / defer / accept with a one-line rationale before the council output is complete. Motivated by delivery council review revealing that the advisory aggregate was never acted on — the operator had to ask separately what to do with each finding. | seed-215 and seed-236 diffs; docs-lint clean. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-06-06 | One change doc covering both councils rather than two separate docs. | The four additions share a single motivation (multi-angle research discipline, lessons from `1p3q1`) and a single implementation surface (two seed files, same session). Splitting would produce two thin change docs with overlapping rationale. | (a) Two separate docs (one per seed) — adds overhead without isolation benefit; the edits are interdependent in motivation if not in code. (b) Fold into `1p3q1` (Guru change) — the council protocol is a different surface with different reviewers; keeping them separate preserves clean scope boundaries. |
| 2026-06-06 | Pre-primer statement is one sentence, not a full independent review pass. | A full independent-pass requirement before the primer would double seat execution time in the sequential protocol and produce redundant output. One sentence captures the independent read without the overhead; it makes primer influence *auditable* without eliminating it. The workflow-era fix (true parallel isolation) eliminates the contamination entirely. | (a) Full independent pass before primer — over-scope for sequential protocol; saves for workflows era. (b) No pre-primer statement — leaves primer anchoring invisible. |
| 2026-06-06 | Correlated-finding flag for sequential councils only, not a general finding-deduplication rule. | The existing synthesis protocol already deduplicates findings with the same `finding_id`. The correlated-finding flag is specifically about the *evidential weight* assigned to two seats reaching the same finding in a sequential run — not about deduplication, but about not overcounting as independent confirmation. | (a) Treat same-finding from two seats as always independent — incorrect epistemically in a sequential single-session run. (b) Mandate challenge round on any same-finding pair — over-triggers; same finding from two seats is expected, not itself a signal of contamination. |
| 2026-06-06 | Axis declaration added to Archetype Council Phase 2 only, not Phase 1 (primer). | Phase 1 primer is optional for Archetype Council and operates adversarially across all stances, not from a declared axis. The axis-declaration requirement applies to the stance-specific Phase 2 seats where the orthogonal-axis design is load-bearing. | (a) Apply to Phase 1 as well — Phase 1 primer is not axis-specific; the requirement would be incoherent there. |
| 2026-06-06 | Phase 2 seat instructions restructured as explicit numbered steps rather than flat bullet list. | The flat-list form ("Each seat receives the briefing packet plus the primer and must: begin with a pre-primer statement...") gave agents the primer in context before telling them to form a view without it. The instruction and the briefing structure contradicted each other — the pre-primer read could be written after the primer was already read. Numbered steps with explicit "do not read the artifact/primer yet" guards at Steps 1 and 2 enforce the correct execution order. Same fix applied to seed-236 axis-declaration step. | (a) Keep flat list, add stronger "must not read primer before stating pre-primer read" language — inline adverbs are weaker than structural sequence; agents follow steps more reliably than inline cautions. |
| 2026-06-06 | Depth-tiering of new Phase 2 additions deferred to a follow-on change doc. | The new additions (numbered steps, pre-primer read, null-finding, recommendations verdict, red-team closing) are not tiered by primer depth — `lightweight` waves get the same Phase 2 complexity as `full` waves. Tiering each addition per depth tier is a meaningful separate change; scope would exceed this wave. Route to a follow-on: `council-protocol-depth-tiering`. | (a) Tier now — over-scope for this wave; each addition would need a per-tier decision. (b) Leave untriggered forever — not acceptable; `lightweight` waves doing full 5-step Phase 2 is unnecessarily heavy. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Pre-primer statement adds boilerplate that seats produce mechanically without real independent thought. | The statement is one sentence, not a paragraph. Its value is auditability — it tells the moderator what the seat's prior was before the primer shaped it. Even a mechanical one-sentence statement is more useful than silence. |
| Null-finding statements pad output without adding value when lanes are genuinely clear. | A one-line "No findings — checked X and Y" is low overhead and actively useful: the moderator knows what the seat checked, not just that it was quiet. |
| Moderator falsification check becomes formulaic ("strongest counter-argument: none; verdict holds"). | The check is only formulaic when the verdict is genuinely uncontested — which is useful information in itself. When a real counter-argument exists and the moderator dismisses it without reasoning, that dismissal is visible and reviewable. |
| Axis declaration before artifact constrains Archetype seats from updating their axis if the artifact rewards a different lens. | The declared axis is the seat's commitment for that run. If the artifact rewards a different lens, that is the moderator's call at synthesis via the swap protocol — not an individual seat's unilateral pivot mid-run. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
