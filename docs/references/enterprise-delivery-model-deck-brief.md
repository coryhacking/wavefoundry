# AI-Native Development: Delivering in Waves — Slide Deck Brief

Owner: Engineering
Status: active
Last verified: 2026-05-24

Red-team perspectives on the enterprise delivery model, assembled as a brief for slide deck preparation. Each reviewer writes from their fixed lens. Use these briefs to anticipate objections, ground aspirational claims, and ensure the deck tells a coherent story.

Source document: `docs/references/enterprise-delivery-model.md`

---

## Red Team (adversarial)

*Lens: What will the audience push back on?*

- **"This is just a renamed PI."** Cycle looks like a PI with a different name to anyone who has lived through SAFe rebranding before. The deck must lead with the closure criterion — a Cycle closes when its declared outcome is achieved, not when a calendar interval expires. That single difference is the point; say it explicitly and early.
- **Two 34% statistics in the opening will read as a data error.** The Businessmap 34% (organizations that built their own model) and the Deloitte 34% (organizations deeply transforming) are different numbers from different surveys that happen to be the same. A room full of skeptics will assume they are the same stat cited twice. Separate them clearly in the deck — source each one on the slide.
- **"Teams will just keep doing sprints and nothing changes."** Sprint cadence being optional sounds like a loophole. The deck needs a one-sentence answer to the implied question: sprints are invisible to the governance model; the Wave is the unit that governs delivery. Teams that keep sprints coordinate wave work within them and that is fine. Teams that drop sprints run waves continuously. Either way, the Wave is what gets reviewed and closed.
- **Designated coordinator without a title creates a budget and accountability gap.** RTEs and senior PMs will ask whether this is a demotion. The deck needs explicit role continuity language: these are reorientations, not eliminations. The functions are preserved; the PI ceremony overhead is not.
- **10–14 days reads as a sales timeline, not an engineering one.** The audience will immediately ask what happens when compliance takes three weeks or JIRA admin takes four days. Frame the timeline as a target with explicit blocking dependencies — compliance gate and JIRA admin are named risks, not line items.

---

## Reality Checker

*Lens: What is grounded? What is aspirational? Where will the plan drift?*

- **AI synthesis at Cycle Open does not exist yet.** Every reference to "AI synthesizes the brief" in the deck risks implying tooling that teams will not find on Day 1. Flag it explicitly as the target state; describe what today looks like — manual planning with agent assistance. Teams who attend and then find no tool will lose trust in the whole model.
- **2–4 months will drift to quarterly without discipline.** The natural gravity of enterprise planning pulls toward calendar quarters. The deck should name this risk and describe the forcing function: Cycles close against declared outcomes, not quarter-end. The team owns the close verdict.
- **The first Cycle will be messy — set expectations now.** The value of this model is not visible in Cycle 1. It shows up in Cycle 2, when carry-over rates drop and Cycle Open takes two hours instead of two days. If the audience benchmarks success against the first Cycle alone, they will declare failure prematurely. Say this on a slide.
- **Wave Framework onboarding is non-trivial.** Gate 2 (team readiness) is real. Do not imply teams can absorb the Wave lifecycle in a one-day workshop. Under-promise here; the cost of overpromising is adoption failure, not a missed demo.
- **The Swell test is honest.** "If you cannot state the Swell's outcome in one sentence, it is probably two Swells" is a real forcing function with real precedent in how teams over-scope campaigns. This is a credibility moment in the deck — it shows the model has been stress-tested.

---

## Architecture Reviewer

*Lens: Is the structural story coherent? Are there gaps between tiers?*

- **Four tiers with distinct closure criteria is the structural argument.** Cycle closes on outcome. Swell closes on theme completion. Wave closes on delivery review. Change closes on AC fulfillment. SAFe has PI at the top, sprint at the bottom, and a coordination gap in the middle where the Swell belongs. The deck's structural slide should make this comparison explicit.
- **The Swell is the novel architectural claim.** SAFe genuinely has no equivalent. Teams already form Swells informally around themes ("auth rework," "search quality," "dashboard improvements") — the Swell tier formalizes what is already happening. This framing is disarming and accurate; it belongs on a slide.
- **The tooling gap at Cycle and Swell is a structural risk for the deck.** Wave and Change have full tooling. Cycle and Swell are manual artifacts today. Without naming this, the upper tiers will read as slide-ware. Frame it as a staged rollout: Wave governance is operational now; Cycle and Swell tooling follows.
- **Decision waves are the structural answer to "we implement before we align."** Every SAFe practitioner in the room has lived this failure mode. A Wave whose sole purpose is to produce binding decisions before any implementation begins is concrete, recognizable, and immediately valuable. It deserves its own slide or at minimum its own moment.
- **The JIRA integration story is clean.** Theme → Fix Version/Cycle → Epic/Swell → Feature/Wave → Story/Change maps to the existing hierarchy without disruption. This reduces the change surface to governance behavior, not tooling replacement.

---

## QA Reviewer

*Lens: Is anything missing, underdeveloped, or not ready to present?*

- **Success metrics are well-defined and should be the opening commitment.** Ceremony time per team, cross-wave conflict rate, Wave carry-over rate, stakeholder visibility after Swell Close, and zero parallel PI ceremonies — these are concrete and observable. Open with them so the audience evaluates the model against criteria, not against feeling.
- **Role transitions need a concrete before/after example, not just a table.** The five-row role table in the source doc is correct but will be skimmed. One slide showing a single role — e.g., RTE before (PI planning facilitation, ART coordination, two-day event prep) and after (cross-wave dependency resolution, Swell narrative, lightweight coordination) — will land better than a table.
- **Recovery path for a superseded Cycle is missing.** The model says Cycles close when "achieved or superseded" but does not describe what superseded looks like operationally. The audience will ask: what happens to in-flight Swells when a Cycle is superseded? This question will come up. Have a brief answer prepared even if it is not on a slide.
- **The Swell test belongs on a slide, not just in prose.** "If you cannot state the Swell's outcome in one sentence, it is probably two Swells. If achieving it takes longer than 6 weeks, it is a Cycle or needs to be split." This is the most memorable and testable heuristic in the model. Make it a callout.
- **The diagram is the right centerpiece.** The ASCII diagram is clear and hierarchical. For slides, a visual equivalent should be the deck's anchor — every tier described relative to it.

---

## Release Reviewer

*Lens: Rollout risk, adoption path, and what happens when execution goes wrong.*

- **The compliance gate is the most underestimated risk in the transition.** It must appear on a slide as a potential hard stop, not a checklist item. In regulated environments, getting written acceptance that Cycle/Swell/Wave artifacts satisfy PI artifact requirements can take two to three weeks. Discover this before the cutover date is announced, not after.
- **Staggered cutover must be bounded or it becomes permanent parallelism.** Wave-ready teams cut over on the primary date; teams needing onboarding get a hard "no later than +4 weeks" date. If the deck does not show a hard end date for the stagger, the audience will hear "teams that aren't ready don't have to change."
- **JIRA admin work is chronically underestimated and must be named explicitly.** Updating hierarchy, mapping Cycles, and reconciling Feature/Story assignments across ARTs takes 2–3 days per JIRA project — more for complex configurations. This step is often the actual bottleneck on Day 7 when everything else is waiting on it.
- **The PI Closure Record is the artifact that makes the cutover credible.** It is the clean break: what was completed, what was migrated into Waves, what was deferred. Closing the PI with a written record is what prevents the old model from persisting informally. Name it as a concrete deliverable, not a process step.
- **Announce once, firmly.** The transition proposal includes a sample announcement with "Brief language. No hedging. The date is firm." Put this on a slide. Organizations that hedge on the cutover date create a signal that reverting is acceptable. The announcement framing is a governance decision, not a communication preference.

---

## Suggested Slide Arc

1. **Why now** — SAFe's 50% drop; what the successful 34% are doing (source each stat separately)
2. **The gap we are solving** — SAFe's missing middle; overstuffed waves; thematic drift
3. **Our model** — Cycle → Swell → Wave → Change diagram; each tier in one sentence; closure criteria
4. **The Swell** — the novel tier; formalizes what already happens informally; the Swell test
5. **Decision waves** — the pattern that prevents implementing before aligning
6. **What changes for teams** — ceremony time before/after; sprints are optional, Waves govern; one role before/after
7. **JIRA stays** — hierarchy mapping; what lives in JIRA vs. Wave Framework docs
8. **Transition plan** — two gates (compliance, Wave readiness); 10–14 day sequence; staggered option; PI Closure Record
9. **What success looks like** — first Cycle metrics; what to watch in Cycle 2; setting expectations for Cycle 1 messiness
10. **What isn't ready yet** — AI synthesis is target state; Cycle/Swell tooling follows Wave tooling; onboarding is non-trivial
11. **Next step** — resolve compliance gate; survey ART Wave readiness; nominate designated coordinators; set the date
