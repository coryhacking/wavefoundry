# Archetype Council Review Surface

Change ID: `1p31i-enh archetype-council-review-surface`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: 1p31b public-launch-prep

## Rationale

Wavefoundry currently surfaces two adversarial-review primitives:

- **`red-team`** — single adversarial stance run in isolation. Acts as Phase 1 primer in the Wave Council, or as a standalone challenge against any artifact. Role-shaped.
- **`Wave Council`** — specialist-role-based seats (architecture-reviewer, security-reviewer, qa-reviewer, reality-checker + rotating fifth) coordinated by `council-moderator`. Mandatory at Prepare and Review when `wave_review.enabled` is true. Role-shaped.

A third shape surfaced organically during the 1p31b Wave Council readiness review and the follow-on `1p318` AC-tightening pass: an **archetype-based council** where seats represent orthogonal *stances* rather than specialist roles. The first instance (Sun Tzu / Yoda / Spock) produced five non-overlapping must-fix findings on a five-line AC that two role-based passes had already cleared. Adding Marcus Aurelius surfaced a sixth axis (durability / dichotomy of control). Adding Feynman would surface a seventh (essentiality / simplicity from understanding).

The stance-shaped council is complementary, not a replacement: role-based seats are better for code/architecture/security review; stance-based seats are better for AC-text precision, prose drafts, decision narratives, naming, and other artifacts where domain-specialist seats are overkill or in the wrong shape.

Make this primitive **first-class but optional**: a named, documented review surface operators can invoke explicitly. Keep it out of the default Prepare/Review lifecycle path so it does not compete with the mandatory Wave Council. Position it as a tool the operator or council-moderator reaches for when the artifact under review is text-precision-heavy or decision-narrative-heavy rather than code/architecture-heavy.

The naming **Archetype Council** (with shortcut **`Archetype review`**) was chosen because the seats are stylized stances, not personas — the trio that gets invoked is interchangeable, and the *axes the seats cover* are the durable contribution, not the names.

## Requirements

1. **A new framework seed prompt defines the Archetype Council protocol.** Located at `.wavefoundry/framework/seeds/NNN-archetype-council.prompt.md` (number chosen at implementation time; recommended slot in the review-surface family between `225-red-team.prompt.md` and `230-council-review.prompt.md`, or in the 236-239 range after the existing reviewer-role seeds). The seed documents: invocation, the five canonical seats, the stance each seat owns, the rotation/swap rules for the fifth seat, the moderator's synthesis duty, the verdict format, and explicit non-overlap with `red-team` and Wave Council. Seed is referenced from `AGENTS.md` review-surface enumeration.
2. **A public prompt body at `docs/prompts/archetype-council.prompt.md`** is the visitor-facing entry. It describes the shortcut phrase, the canonical five seats, when to invoke this council vs. red-team vs. Wave Council, the verdict shape, and one worked example referencing the 1p318 review in this wave. The prompt body links the seed for the full protocol.
3. **The shortcut phrase `Archetype review`** (alias: `Archetype council`) is added to `docs/prompts/index.md` Public Commands table. The catalog entry names the protocol doc and the seed.
4. **The five canonical seats are documented** with their stance, the kind of finding each is best at, and the questions each asks:
   - **Sun Tzu** — strategic positioning / unforced losses / pre-positioning. "What ground is undefended? What loss is preventable here?"
   - **Yoda** — cognitive readiness / commitment threshold / reader orientation. "What does the reader bring to this? What state must they be in? Where do they stand on the path?"
   - **Spock** — logical precision / testable propositions / falsification conditions. "What does this proposition bind? What evidence would falsify it? Where is it under-defined?"
   - **Marcus Aurelius** — durability / dichotomy of control / time-axis / scope-of-self. "Will this still be right in 18 months? What is within our control, and what are we pretending to control? Is this the duty of the role or wishful work?"
   - **Feynman** — essentiality / simplicity from understanding / curse-of-knowledge. "Can this be explained simply? What is the simplest version that still does the job? What are we doing that isn't earning its place?"
5. **Rotation/swap guidance for the fifth seat** is explicit. The fifth seat defaults to Feynman; operators may swap in alternative archetypes when the artifact rewards a different stance. Documented swap-in candidates: **Hemingway** (prose craft / cut-every-sentence-that-doesn't-move-the-story) for prose-heavy artifacts; **Charlie Munger** (invert / "how would this fail?") for decision-narrative artifacts. The seed names the swap protocol: invocation declares the swap up front ("Archetype review with Hemingway swapped in for Feynman"), and the moderator records the swap in the verdict line.
6. **The verdict format is structured** so a downstream `wave_close` or `wave_review` can verify presence/absence of an archetype-council pass when an operator opts to require one. Suggested verdict line shape (modeled on the existing `prepare-council` verdict): `- **Archetype Council [archetype-review] — <date>: PASS** (moderator: council-moderator; seats: sun-tzu, yoda, spock, marcus-aurelius, feynman; rotating-seat: feynman; strongest-axis: <which seat's finding bound the most must-fixes>; must-fix-count: <n>; advisory-count: <n>)`. The verdict line is recorded in the reviewed artifact's review section (for change docs, that's `## Review Evidence`; for wave docs, `## Review Checkpoints`). The structured format is consumed by no validator at v1 — this is forward-compat scaffolding only.
7. **Explicit non-overlap with the existing surfaces is stated in the seed and prompt body.** When to invoke each:
   - **`red-team`** alone — single adversarial pass on a focused artifact before committing.
   - **Wave Council** — required at Prepare and Review per `wave_review.enabled`; specialist-role seats; integrates with the framework lifecycle.
   - **Archetype Council** — optional, operator-invoked, stance-based; complements the Wave Council on AC text, prose, decision narratives, and naming questions.
8. **The first invocation is recorded as a precedent** in the seed under `## Worked Example`: the three-persona review of `1p318` AC-20/AC-21 that produced MF-1..MF-5. This anchors the protocol in a real artifact that already shipped.
9. **No changes to the existing `wave_review`, `wave_prepare`, or `wave_close` enforcement paths** in v1. The Archetype Council is documented and invocable but not validated by any harness. Validator integration is explicitly out of scope and recorded as a follow-on possibility only.

### Weaving — recommended invocation points across existing seeds

10. **Existing seeds carry a one-line "consider Archetype Council when..." pointer** at each point in the lifecycle where the protocol is well-suited. Pointers are *recommendations*, not gates — they describe the artifact shape that benefits from a stance-based pass and link the Archetype Council prompt body. Each pointer names the typical fifth-seat swap when relevant (e.g., Hemingway for prose-heavy authoring; Munger for decision narratives).

11. **Seeds to weave into (v1 scope):**
    - **`007-review-system-overview.md`** — review-system intro. Enumerate Archetype Council alongside red-team and Wave Council as the third complementary surface. One sentence each on when to reach for which.
    - **`170-plan-feature.prompt.md`** — change-doc authoring. Pointer: "Consider Archetype review on the AC table and rationale section when the change is documentation-heavy or naming-decision-heavy. Default fifth seat Feynman; swap Hemingway for prose-heavy rationale." Placed near the rationale/AC authoring step.
    - **`175-interrogate-plan.prompt.md`** — plan stress-testing. Pointer: "Archetype review is a stance-based alternative to the role-based interrogation pass when the plan's load-bearing surface is text precision rather than execution risk. Use either; use both when the plan is high-stakes."
    - **`176-evaluate-decision.prompt.md`** — ADR / decision evaluation. Pointer: "Archetype review with the canonical five seats is well-suited for ADR review — Marcus Aurelius for durability and Feynman for essentiality are directly load-bearing. Swap Munger in for Feynman when the decision is structured as a comparison." Place after the existing council step.
    - **`225-red-team.prompt.md`** — adversarial primer. Cross-reference: "Archetype Council is the multi-stance sibling of this single-stance primer. Invoke when the artifact rewards multiple orthogonal axes simultaneously rather than a single sharp challenge." Non-overlap statement.
    - **`230-council-review.prompt.md`** — Wave Council protocol. Cross-reference: "Archetype Council is an optional supplement during readiness or delivery passes when the wave or change involves substantial AC text, prose, or naming work. The Wave Council remains mandatory; Archetype Council is invocable in addition." Place in the "when to invoke variants" section.
    - **`215-council-moderator.prompt.md`** — moderator role. Add: "The moderator also chairs Archetype Council invocations. Phase shape is identical (primer → seats in isolation → synthesis); seat composition is stance-based rather than role-based; verdict format matches the structured `archetype-review` line."
    - **`230-author-spec.prompt.md`** — spec authoring. Pointer: "Consider Archetype review on the spec's interface contracts and acceptance section when the spec is text-precision-heavy. Spock is load-bearing here." Placed in the spec-review subsection.
    - **`233-technical-writer.prompt.md`** — technical writing role. Pointer: "Archetype review with Hemingway swapped in for Feynman is the recommended pass for prose-heavy artifacts (README, getting-started guides, conceptual overviews). Run before publishing to a public surface."

12. **Each weaving pointer follows a consistent shape** so an operator scanning a seed recognizes the pattern instantly:
    - **Format:** *"Consider **Archetype review** when [artifact-shape signal]. Default seats: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman. [Optional swap recommendation.] Seed: `archetype-council.prompt.md`."*
    - **Length:** one to three sentences.
    - **Placement:** at the step in the seed where the relevant artifact is being authored or reviewed, not in a generic header or footer.

13. **Seeds NOT in v1 weaving scope (called out explicitly to bound the change):**
    - Reviewer-role seeds (`212-performance-reviewer`, `213-security-reviewer`, `214-architecture-reviewer`, `216-reality-checker`, `217-senior-engineering-challenger`, `221-code-reviewer`, `229-security-engineer`, etc.) — these are role definitions, not lifecycle prompts; the role IS the seat. Cross-referencing Archetype Council from each would be noise.
    - Implementer-role seeds (`222-software-engineer`, `223-frontend-developer`, `224-data-engineer`, `226-backend-architect`, `227-software-architect`, `228-database-optimizer`, `231-ai-engineer`, `232-api-tester`, `234-workflow-engineer`, `235-enterprise-integration-engineer`) — implementation phase, not review phase.
    - Setup/installation/maintenance seeds (`010-install-wavefoundry`, `150-refresh-wavefoundry`, `160-upgrade-wavefoundry`, `240-package-wavefoundry`, `250-migrate-existing-wave-project`) — no review-shaped artifacts in scope.
    - Dashboard seeds (`152-153-154-*-dashboard`) — operational, not review-shaped.
    - Guru / index / persona seeds (`211-guru`, `120-project-persona-synthesis`, `130-agent-journal-bootstrap`, etc.) — orthogonal to review surface.

14. **Weaving is documented as a *recommendation pattern*, not a mandate.** The Archetype Council remains optional and operator-invoked. The pointers exist to surface the option at the right moment in the lifecycle; they do not gate any step or block any path. Anywhere the pointer is added, the seed's existing protocol still works without it.

## Scope

**Problem statement:** The framework has two adversarial-review primitives (red-team, Wave Council) but no first-class shape for stance-based review. The third shape surfaced organically during 1p31b but lives only in conversation history; without seed/prompt-body capture it cannot be re-invoked consistently and the protocol drifts on each use.

**In scope:**

- New framework seed: `.wavefoundry/framework/seeds/NNN-archetype-council.prompt.md`
- New public prompt body: `docs/prompts/archetype-council.prompt.md`
- Public Commands entry in `docs/prompts/index.md` for `Archetype review`
- One-line mention in `AGENTS.md` review-surface enumeration
- Worked-example anchor in the seed citing 1p318 MF-1..MF-5
- **Weaving pointers added to existing seeds:** `007-review-system-overview.md`, `170-plan-feature.prompt.md`, `175-interrogate-plan.prompt.md`, `176-evaluate-decision.prompt.md`, `225-red-team.prompt.md`, `230-council-review.prompt.md`, `215-council-moderator.prompt.md`, `230-author-spec.prompt.md`, `233-technical-writer.prompt.md` — one to three sentences each, following the consistent format in Req-12.

**Out of scope:**

- Validator/harness integration. The Archetype Council does not gate Prepare, Review, or Close in v1.
- Changes to the existing Wave Council *protocol* (red-team + fixed seats + moderator + rotating fifth). Cross-reference pointers in `225-red-team.prompt.md`, `230-council-review.prompt.md`, and `215-council-moderator.prompt.md` add awareness of the sibling primitive without modifying their protocols.
- A `mcp__wavefoundry__wave_archetype_review` MCP tool. The protocol is text-driven for v1; explicit tooling is a follow-on if usage warrants it.
- Per-project workflow-config keys for Archetype Council policy. The framework owns generic defaults; downstream projects pick up the seed on upgrade.
- Expanding the seat catalog past the five canonical archetypes + two documented swap-ins (Hemingway, Munger). Operators may invoke other archetypes ad hoc; canonical-set expansion happens in a future change if a fourth common swap-in emerges from real usage.
- Weaving pointers into reviewer-role seeds (212-217, 221, 229), implementer-role seeds (222-228, 231-235), setup/install/upgrade seeds, dashboard seeds, or persona/index seeds — listed explicitly in Req-13 with rationale for each exclusion.

## Acceptance Criteria

- [x] AC-1: Framework seed `.wavefoundry/framework/seeds/236-archetype-council.prompt.md` exists, documents the invocation, the five canonical seats with their stances, the swap protocol, the verdict format, and the worked example. *(Slot 236 chosen — between engineer-specialist seeds and packaging seeds; review-surface family cluster.)*
- [x] AC-2: Public prompt body `docs/prompts/archetype-council.prompt.md` exists, names the shortcut phrase, names the canonical five seats, explains when to invoke vs. red-team and Wave Council, links the seed.
- [x] AC-3: `docs/prompts/index.md` Public Commands table has an entry for `Archetype review` (alias `Archetype council`) pointing at the prompt body.
- [x] AC-4: `AGENTS.md` Shortcut Phrases table has a one-line entry for `Archetype review` / `Archetype council` placing it alongside the other review surfaces with the optional context noted.
- [x] AC-5: The five canonical seats each carry a stance description and an example-question block. *Verified by inspection of `236-archetype-council.prompt.md` "The Five Canonical Seats" section.*
- [x] AC-6: Swap protocol for the fifth seat is documented with Hemingway and Munger named as canonical swap-in candidates, including when each is the right swap. *Verified at "Swap-In Candidates" subsection.*
- [x] AC-7: Verdict line format is structurally consistent with the existing `prepare-council` verdict shape — bold header `**Archetype Council [archetype-review] — <date>: PASS**` followed by semicolon-separated `key: value` meta in parens. Forward-compat scaffolding only in v1.
- [x] AC-8: Explicit non-overlap "when to use this vs. red-team vs. Wave Council" decision table present in both seed and prompt body.
- [x] AC-9: Worked-example section cites `1p318` MF-1..MF-5 with the original finding IDs preserved (Sun Tzu ST-1, ST-2; Yoda Y-1, Y-2; Spock SP-1..SP-4) — both in the seed's "Worked Example" section and the prompt body's "Worked example" section.
- [x] AC-10: `docs-lint` passes after all additions. *Verified post-edit.*
- [x] AC-11: No regression on existing review-surface enforcement: `wave_prepare`, `wave_review`, `wave_close` behavior unchanged — no validator references Archetype Council. *Verified via 2262 framework tests passing.*
- [x] AC-12: Weaving pointers added to all nine seeds named in Req-11 (`007-review-system-overview.md`, `170-plan-feature.prompt.md`, `175-interrogate-plan.prompt.md`, `176-evaluate-decision.prompt.md`, `225-red-team.prompt.md`, `230-council-review.prompt.md`, `215-council-moderator.prompt.md`, `230-author-spec.prompt.md`, `233-technical-writer.prompt.md`). Each pointer follows the consistent format in Req-12 — artifact-shape signal + default seats + optional swap recommendation + seed reference — and is placed at the relevant lifecycle step within the seed (after AC discussion in `170`; after interrogation contract in `175`; before Operator Interview in `176`; new "Archetype Council Meta-Review (Optional)" section in `007`; in Role Boundaries in `225`; in Relationship to Other Commands in `230-council-review`; new "Chair Of The Archetype Council" section in `215`; before Required outputs in `230-author-spec`; new "Recommended Review Pass For Public-Facing Drafts" section in `233`).
- [x] AC-13: Each weaving pointer is a *recommendation* not a mandate. Verified by inspection: every pointer uses recommendation language ("Consider..."), none introduce gates or required actions, and each is removable without breaking the surrounding seed's existing protocol.
- [x] AC-14: The cross-references in `225-red-team` (Role Boundaries) and `230-council-review` (Relationship table) explicitly state the non-overlap — `red-team` is single-stance, Wave Council is role-based and mandatory, Archetype Council is stance-based and optional/in-addition.
- [x] AC-15: Out-of-scope seeds (reviewer-role 212-217 + 221 + 229; implementer-role 222-228 + 231-235 minus 233; setup/install 010 + 150 + 160 + 240 + 250; dashboard 152-154; guru/index/persona 211 + 120 + 130) carry no Archetype Council reference. *Verified via the targeted grep returning only the 10 expected files (9 woven seeds + the new 236 seed itself).*

## Tasks

- [x] Open `seed_edit_allowed` gate (framework seed addition + cross-seed weaving)
- [x] Choose the seed number for the new Archetype Council seed — **slot 236** (between engineer-specialist seeds and packaging seeds; review-surface cluster)
- [x] Author the new seed with invocation, canonical five seats with stance + question, swap protocol, verdict format, non-overlap with red-team + Wave Council, worked-example anchor citing 1p318 MF-1..MF-5
- [x] Author the public prompt body at `docs/prompts/archetype-council.prompt.md`
- [x] Add the Public Commands entry to `docs/prompts/index.md` (alias entry as well)
- [x] Add the `AGENTS.md` Shortcut Phrases entry placing Archetype Council alongside the other review surfaces
- [x] **Weave pointer into `007-review-system-overview.md`** — new "Archetype Council Meta-Review (Optional)" section with when-to-invoke decision table
- [x] **Weave pointer into `170-plan-feature.prompt.md`** — italicized pointer after AC/Tasks discussion
- [x] **Weave pointer into `175-interrogate-plan.prompt.md`** — italicized pointer after optional stress-testing description
- [x] **Weave pointer into `176-evaluate-decision.prompt.md`** — italicized pointer before Phase 4 Operator Interview
- [x] **Weave cross-reference into `225-red-team.prompt.md`** — new Role Boundaries entry stating non-overlap as multi-stance sibling
- [x] **Weave cross-reference into `230-council-review.prompt.md`** — Relationship to Other Commands table entry
- [x] **Weave addition into `215-council-moderator.prompt.md`** — new "Chair Of The Archetype Council" section
- [x] **Weave pointer into `230-author-spec.prompt.md`** — italicized pointer before Required outputs
- [x] **Weave pointer into `233-technical-writer.prompt.md`** — new "Recommended Review Pass For Public-Facing Drafts" section
- [x] Verify all weaving pointers follow consistent format (Req-12); verify none introduce gates or required actions (AC-13)
- [x] Run `docs-lint`; iterate to clean (passed)
- [x] Re-run framework tests to confirm no regression on existing enforcement (2262 tests passing)
- [x] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — this change adds a documentation/protocol surface; no architectural boundary, data flow, or testing-architecture impact. Existing review-surface enforcement paths are unchanged in v1.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (seed exists with invocation, seats, swap protocol, verdict format, worked example) | required | The seed is the canonical source of truth for the protocol. Without it, the public prompt body and weaving pointers have nothing to link. |
| AC-2 (public prompt body) | required | Visitor-facing entry; pairs with the seed and is what the catalog points at. |
| AC-3 (index.md catalog entry for `Archetype review`) | required | Discoverability via the public catalog. Without it, the shortcut phrase is undiscoverable from the routing table. |
| AC-4 (AGENTS.md one-line mention) | required | Agent-facing enumeration of the review-surface family. Pairs Archetype Council with red-team and Wave Council so agents see all three together. |
| AC-5 (five canonical seats with stance + question each) | required | The seats ARE the protocol. Without stance descriptions and example questions, the seed cannot be invoked consistently across operators. |
| AC-6 (swap protocol with Hemingway/Munger named) | required | The swap protocol is the artifact-fit affordance. Without it, the protocol is rigid in a way that defeats the stance-based design. |
| AC-7 (structured verdict format) | important | Forward-compat scaffolding for future validator integration. Not load-bearing in v1 — current invocations are text-driven. |
| AC-8 (non-overlap decision table in seed and prompt body) | required | Discoverability and disambiguation. Without explicit "when to invoke which" guidance, operators reach for the wrong surface and the value of having three primitives collapses. |
| AC-9 (worked example citing 1p318 MF-1..MF-5) | required | Anchors the protocol in a real artifact. Generic worked example was explicitly rejected in the Decision Log. |
| AC-10 (docs-lint passes) | required | Standard hygiene gate. |
| AC-11 (no regression on existing enforcement) | required | Hard gate on the v1 promise: Archetype Council adds a surface without changing any existing gate. |
| AC-12 (weaving pointers added to nine named seeds per Req-11) | required | Operator-flagged: the primitive must be woven into existing seeds so it surfaces at the right lifecycle moments rather than only when an operator already knows to look. |
| AC-13 (pointers are recommendations not mandates; removable test) | required | Anchors the non-mandate property of the primitive. Without this discipline, weaving converts "optional" into "expected" by association. |
| AC-14 (non-overlap statements in red-team and council-review cross-references) | required | Load-bearing on the distinction that Wave Council remains mandatory and Archetype Council is in addition, not in place of. |
| AC-15 (out-of-scope seeds carry no Archetype Council reference) | important | Scope bound. Verifies the weaving did not over-extend into reviewer-role, implementer-role, or operational seeds. Important rather than required because over-extension is recoverable in a follow-on. |

All required ACs are load-bearing on either the protocol existing (AC-1..AC-9), the discoverability of the protocol (AC-3, AC-4, AC-8, AC-12), or the integrity of the non-mandate property (AC-13, AC-14). AC-7 and AC-15 are important rather than required because both are bound-checks rather than load-bearing surfaces — they protect against drift but their absence does not break the protocol.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Name the primitive **Archetype Council** with shortcut **`Archetype review`** | The seats are stylized stances, not personas — the trio is interchangeable, and the *axes the seats cover* are the durable contribution. "Archetype" captures stance-not-role; parallels existing "Council review" naming. | (a) "Lens Council" — clean but less recognizable as a sibling of "Wave Council". (b) "Triad review" — names the structure but loses the stance framing; also locks in three when the actual recommended default is five. |
| 2026-06-03 | Five canonical seats default: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman | Five orthogonal axes (positional / cognitive / logical / temporal-and-scope / essentiality) with no echo. Three was the original surfacing but Marcus added a distinct axis (durability) and Feynman added a distinct axis (essentiality). A sixth was considered and rejected — Hemingway and Munger are recommended as swap-ins rather than fixed seats because their axes are narrower than the canonical five. | (a) Keep the original three (Sun Tzu, Yoda, Spock) — rejected; Marcus and Feynman both produced distinct must-fixes the original three did not. (b) Six seats with Hemingway as default sixth — rejected; Hemingway's prose-craft axis is narrower than the other five and is better positioned as a swap-in for artifact-specific invocations. |
| 2026-06-03 | First-class but optional; no validator integration in v1 | The Wave Council already covers mandatory adversarial review at Prepare/Review. Adding Archetype Council to the gated path would double the review surface for waves that do not benefit from stance-based review. Optional invocation keeps the cost where the value is. | (a) Add an Archetype Council gate at Prepare for prose-heavy changes — rejected; "prose-heavy" is not a clean classification and would require classification logic that itself drifts. (b) Make Archetype Council mandatory at Prepare for documentation-kind change docs — rejected; the canonical seats are still useful for code change docs too. Optional invocation is the right shape. |
| 2026-06-03 | Verdict line is structured forward-compat for future validator integration but not consumed by any validator in v1 | A consistent structured format (bold header → key:value meta in parens) is cheap to author at v1 and avoids a breaking-change pass if the framework later opts to require Archetype Council on certain change kinds. | Unstructured prose verdict — rejected; if validator integration becomes desirable later, the cost of retroactively structuring historical verdicts is non-trivial. |
| 2026-06-03 | Swap-in fifth seat documented with Hemingway and Munger as canonical alternatives; operator-declared swap up front; moderator records swap in verdict line | The fifth seat is where stance-tailoring to artifact happens. Two named swap-ins is enough scaffolding for operators to see the pattern without over-specifying. Declaring the swap up front (rather than mid-review) keeps the seat composition transparent in the recorded verdict. | (a) Hard-code the fifth seat as Feynman with no swap protocol — rejected; loses the artifact-fit affordance the trio-plus-rotating-fifth shape already established for the Wave Council. (b) Allow mid-review swap — rejected; would obscure which axes were actually exercised. |
| 2026-06-03 | Worked example anchors the seed in 1p318 MF-1..MF-5 — original finding IDs preserved | A protocol that names a real artifact survives the protocol's own drift. A future reader can read 1p318 and the seed together and verify the seed describes what actually happened. | Generic worked example — rejected; loses the audit-trail value. |
| 2026-06-03 | Weave Archetype Council pointers into nine specific existing seeds (per Req-11) rather than leaving the primitive as an orphan invocation | Operator-flagged concern: a new review primitive that only lives in its own seed surfaces only when an operator already knows to reach for it. Weaving makes the option discoverable at the moment in the lifecycle where it is most likely to be useful — during planning, interrogation, decision evaluation, and Wave Council. The cost is a maintenance overhead on cross-references; the value is discoverability of an optional tool exactly when it is most leveraged. | (a) Leave as orphan invocation — rejected; surfacing only via `docs/prompts/index.md` Public Commands means the operator must already know to look. (b) Weave into every seed — rejected; reviewer-role and implementer-role seeds have no review-shaped artifact to which the pointer would apply. The bounded list in Req-11 + the exclusion list in Req-13 is the right scope. (c) Make the pointers mandatory — rejected; the primitive is optional by design and weaving must preserve that. |
| 2026-06-03 | Weaving pointers follow a consistent format (Req-12) — artifact-shape signal + default seats + optional swap + seed reference, one to three sentences | A consistent visual shape lets an operator scanning any seed recognize the Archetype Council pointer instantly without re-reading each instance. The format itself becomes the affordance. | Free-form pointers per seed — rejected; loses the recognizability affordance and increases the risk of drift across pointers as the protocol evolves. |
| 2026-06-03 | Pointers are recommendations, not mandates (Req-14 / AC-13) | The Archetype Council is optional by design. Weaving must surface the option at the right moment without gating any step. The "removable without breaking the seed" test in AC-13 is the discipline that prevents weaving from quietly converting "optional" into "expected." | Make the pointers required at certain lifecycle steps — rejected; the optionality is a feature, not a hedge, and converting it to a requirement defeats the explicit non-overlap with the mandatory Wave Council. |

## Risks

| Risk | Mitigation |
|---|---|
| The Archetype Council becomes a "performative review" — operators invoke it to perform thoroughness rather than to surface findings the existing councils miss | Document the explicit non-overlap test in the seed: invoke Archetype Council only when the artifact is AC-text precision, prose, decision narrative, or naming-heavy. If the protocol is invoked and produces zero must-fixes that the prior reviews missed, the moderator notes "no archetype-distinct findings" in the verdict so the pattern surfaces if it becomes load-bearing. |
| Persona drift — Sun Tzu / Yoda / Spock / Marcus Aurelius / Feynman become caricatures of their stances over repeated use | Anchor the seed's seat descriptions to the *stance* (positional / cognitive / logical / durability / essentiality), not the persona. The personas are mnemonic shells over the axes; if a future operator picks different mnemonics, the axes carry the protocol. |
| Operators invoke ad-hoc archetypes that overlap one of the canonical five and produce echo-chamber findings | Seed names overlap-detection as the moderator's duty: if two seats' findings cluster on the same axis, the moderator flags the overlap in the verdict line ("axes-covered" field) and the protocol is recorded as having operated on N axes rather than M. |
| Validator integration becomes desirable later but the v1 verdict format does not parse cleanly | Mitigated by the AC-7 / Decision Log entry choosing structurally consistent format from v1. Same shape as `prepare-council` verdict — a future parser is a straightforward extension. |
| Adding a third review primitive crowds the prompt catalog and confuses operators about which to invoke | Seed and prompt body each carry an explicit decision table for when to invoke red-team / Wave Council / Archetype Council. Decision table is part of AC-8 — it is the load-bearing affordance for catalog discoverability. |
| The 1p318 worked example becomes outdated as the surface-rewrite continues to evolve | The worked example cites the *finding IDs* (MF-1..MF-5, ST-1, Y-1, SP-1..SP-4), which are stable artifacts in the change-doc Decision Log even if the README ultimately ships differently. The audit trail is in the change doc, not in the eventual README. |
| Weaving pointers across nine seeds creates maintenance overhead — if the Archetype Council protocol evolves, every pointer is a touch point | Consistent format (Req-12) makes the pointers grep-able: a single search for `Archetype review` enumerates every weaving point. The pointers are deliberately short (one to three sentences) so updates are localized. The protocol detail lives in the seed, not in the pointers — pointers link to the seed by name and do not duplicate protocol content. |
| Operators read weaving pointers as implicit mandates ("the framework recommends this, so I should do it") even though they are optional | Each pointer uses recommendation language ("Consider...") not imperative language ("Run..."). The non-mandate property is anchored by AC-13's "removable without breaking the seed" test — pointers that fail this test are by definition the wrong shape and must be revised before close. |
| Weaving makes Wave Council seem less mandatory by association with the optional Archetype Council | The cross-references in `225-red-team` and `230-council-review` (Req-11 + AC-14) explicitly state Wave Council remains mandatory; Archetype Council is in addition, not in place of. The cross-references are load-bearing on this distinction. |

## Related Work

- `1p318-enh public-launch-surface-doc-rewrite` (this wave) — produced the first invocation of the proto-Archetype-Council (Sun Tzu / Yoda / Spock) and the precedent the seed cites. The MF-1..MF-5 findings are preserved in 1p318's Decision Log.
- Wave Council protocol: `.wavefoundry/framework/seeds/225-red-team.prompt.md`, `docs/prompts/council-review.prompt.md`. The Archetype Council seed should reference these as the sibling primitives whose non-overlap it explicitly preserves.
- 1p2q3 close-readiness review and the 1p31b Wave Council readiness verdict (this wave's `## Review Checkpoints`) demonstrate the existing role-based council shape that Archetype Council complements.

## Session Handoff

Unattached future-wave plan at scaffold time. **Operator decision: admit to wave `1p31b public-launch-prep` as a late-admitted third change.** Sibling to `1p312-bug` and `1p318-enh`. Late admission is acceptable because this change is documentation-only and does not introduce code-test gating; the existing wave's drift diagnostic at close covers the late-admitted scope.
