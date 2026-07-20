# AI-Native Development: Delivering in Waves
### A Framework to Move Teams Beyond SAFe

Owner: Engineering
Status: draft
Last verified: 2026-07-20

---

## How the Industry Is Changing

SAFe usage dropped approximately 50% in 2025. A Businessmap survey found only 26% of respondents still using it — down from the mid-50s the year before. That is not a gradual erosion; it is an industry-wide rejection of heavyweight ceremony in the face of AI-accelerated delivery.

What is replacing it is not a new framework. 74% of organizations now use hybrid or homegrown approaches (NextAgile, 2026). The industry is not converging on a SAFe successor — it is converging on the idea that building something that fits your organization is the right move.

A separate measure from Deloitte's 2026 State of AI in the Enterprise report arrives at the same number from a different angle: only 34% of organizations are deeply transforming — reinventing core processes and building new capabilities around AI. 37% are using AI at surface level with little process change. The productivity gap between those two groups is where McKinsey's top-quintile numbers live: 16–30% improvement in productivity and time to market, 31–45% gains in software quality. You do not get there by adding AI tools to unchanged SAFe structures.

The organizations achieving durable results share these characteristics:

- **Build a custom model** rather than adopting another vendor framework
- **Make cadences outcome-driven**, not calendar-driven — cycles close when objectives are met
- **Keep governance** — stage gates, reviewer lanes, documented acceptance criteria — because governance becomes more important when teams ship faster, not less important
- **Cut the ceremonies** that were compensating for slow execution; they are now the bottleneck

The specific model described in this document — Cycle → Swell → Wave → Change — does not exist as a named industry standard. That is the point. The enterprises achieving durable AI-native velocity gains are the ones that designed their own delivery model rather than waiting for someone to publish one. This document proposes that approach for our organization.

---

## Overview

The Wave Framework governs individual waves of change — each with a clear objective, reviewer lanes, and a close record. In enterprise environments, teams need structure above the Wave to coordinate work across longer horizons and multiple delivery threads.

This document describes how to apply Wavefoundry inside a four-tier delivery hierarchy:

```
  INVESTMENT THEME
  permanent · strategic portfolio direction
        │
        │  Cycle serves Theme
        ▼
  ┌─────────────────────────────────────────────────────┐
  │  CYCLE                                              │
  │  · outcome declared on open                         │
  │  · closes when achieved or superseded               │
  │  · typically 2–4 months                             │
  │  · artifact: cycle.md                               │
  └──────────────────────┬──────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────┐
  │  SWELL                               JIRA: Epic     │
  │  · coherent campaign of waves                       │
  │  · designated coordinator                           │
  │  · closes with outcome retrospective                │
  │  · 3–6 weeks · artifact: swell.md                   │
  └──────────────────────┬──────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────┐
  │  WAVE                          JIRA: Feature/Story  │
  │  · atomic governance and delivery unit              │
  │  · prepare → implement → review → close             │
  │  · stage gate · reviewer lanes · Wave Council       │
  │  · variable size (Story-level to Feature-level)     │
  └──────────────────────┬──────────────────────────────┘
                         │
                         ▼
  ┌─────────────────────────────────────────────────────┐
  │  CHANGE                       JIRA: Story/Sub-task  │
  │  · feat · bug · enh · maint · doc · debt · and more │
  │  · change doc · acceptance criteria · tasks         │
  └─────────────────────────────────────────────────────┘
```

The Wave and Change tiers are fully handled by the existing Wave Framework. The Swell and Cycle tiers are lightweight coordination constructs layered above it. None of the tiers are calendar-driven; all close against their declared outcome.

---

## A Note on Terminology

The four tiers in this model — Cycle, Swell, Wave, Change — are named deliberately. How they relate to our existing JIRA hierarchy:

| This model | Our JIRA hierarchy | Status |
|---|---|---|
| *(above Cycle)* | Investment Theme | Unchanged — permanent strategic portfolio construct; Cycles serve Themes, not replace them |
| **Cycle** | *(none)* | **New** — outcome-driven strategic rhythm; no existing JIRA analogue |
| **Swell** | Epic | Existing artifact, new governance behavior |
| Wave | Feature | Existing artifact, maps to Wave execution layer |
| Change | Story | Existing artifact, maps to Change execution layer |

**Investment Themes and Cycle**

Investment Themes are the permanent, portfolio-level strategic commitments — they sit above this model and are unchanged. Cycle is the only genuinely new concept: there is no existing JIRA artifact for it. It inserts between Theme and Epic, grouping Swells under a declared outcome. In JIRA, represent it as a Fix Version or labeled group — the mechanism matters less than the artifact: a `cycle.md` with an outcome statement, success criteria, and in-scope Swells. Themes don't close; Cycles do.

**Why "Swell" instead of "Epic"**

Swell maps exactly to where Epic sits in our hierarchy. The reason for using a new term rather than Epic is behavioral, not structural. In our current practice, an Epic is a JIRA container — a parent ticket that groups features. The Swell is a governance construct: it has an outcome statement, measurable success criteria, a designated coordinator, and a close ceremony that evaluates whether the outcome was achieved. That is meaningfully different behavior from how Epics are used today.

Using a new word signals to teams that this is not what they used to call an Epic. The unfamiliarity is intentional — it prompts the question "what does this require?" rather than defaulting to old behavior.

**Path to renaming**

Once the new governance behaviors are established and teams are consistently running Swells with outcome statements, success criteria, and close ceremonies, renaming Swell to Epic is straightforward. At that point the word change costs nothing because the behavior is already embedded. The risk of renaming early is that teams hear "Epic," revert to treating it as a JIRA container, and the governance layer quietly disappears.

This document uses Swell throughout. When the organization is ready to consolidate vocabulary, substitute Epic for Swell and update the JIRA mapping accordingly.

**The case for keeping Epic**

The counterargument is straightforward: the behavioral change — outcome statement, success criteria, designated coordinator, close ceremony — is what this model actually requires, and none of that depends on using a new word. Epic is already understood, already in JIRA, and already in everyone's vocabulary — and that vocabulary extends well beyond R&D. Business stakeholders, product leadership, and finance teams all use "Epic" today. Renaming it to "Swell" is not just an engineering vocabulary problem; it is an organizational one, and the change surface is much larger than it first appears.

Introducing a new term on top of a governance change also creates a practical risk: teams end up debating the name rather than adopting the new behaviors. The unfamiliarity that is meant to prompt reflection can just as easily prompt resistance. Several organizations have made their Epics outcome-based without renaming them, simply by changing what an Epic is required to contain before it opens and what it must demonstrate before it closes. If the goal is behavior change, owning the word the whole organization already uses and redefining it may be more durable than introducing a new term and hoping it sticks.

---

## Why Four Tiers

SAFe provides strong portfolio discipline (Lean Portfolio Management) and strong team-level execution (sprints), but leaves a coordination gap in the middle: the Program Increment (PI) is simultaneously too large for day-to-day coherence and too small for genuine strategic direction. Teams either over-stuff waves with unrelated work or lose thematic continuity across many small waves.

In practice, delivery history shows two recurring failure modes:

- **Overstuffed waves**: A single wave accumulates dozens of changes because there is no grouping construct to hold related-but-distinct work. The wave becomes hard to govern, review, and close cleanly.
- **Thematic drift**: Teams run many small waves without a shared narrative, losing the strategic thread that connects them. Work ships but momentum on the objective is invisible.

The Swell fills the gap between Wave and Cycle. The Cycle provides the strategic declaration that a portfolio of Swells serves.

---

## The Four Tiers

### Cycle

**What it is:** A strategic outcome declaration. The Cycle names the objective the team is pursuing and the success criteria for knowing it is achieved. It groups one or more Swells.

**Duration:** Determined by the objective, not the calendar. A Cycle opens when a strategic outcome is declared and closes when that outcome is achieved or explicitly superseded. There is no fixed interval.

The discipline is writing a clear objective before the Cycle opens. If you cannot state what "done" looks like, sharpen it before proceeding — a well-defined objective has a natural close point; a vague one produces an open-ended Cycle with no natural end.

In practice, most Cycles run 2–4 months because strategic objectives tend to have that horizon — but this is an observation, not a rule. A Cycle addressing a narrow, urgent objective might close in six weeks. One addressing a significant platform shift might run longer. What matters is that it has a declared outcome and closes against that outcome, not against a calendar date.

**JIRA analogue:** No direct equivalent. Represent as a Fix Version or labeled grouping. The `cycle.md` artifact is the authoritative record. Investment Themes sit above the Cycle and are unchanged; a Cycle declaration names which Theme(s) it serves.

**Artifacts:**
- A `cycle.md` document declaring the outcome statement, success criteria, and in-scope Swells.
- A Cycle Close retrospective: did we achieve the outcome? What did we learn about the objective itself?

**Governance:** Human-owned. AI provides portfolio health analytics and progress synthesis; human leads own the strategic declaration and the close verdict.

**SAFe equivalent:** Would replace PI Planning as the strategic rhythm. The Cycle Open serves the same function as the two-day PI Planning event — not as a lighter alternative running alongside it, but as its replacement. AI synthesizes backlog state, dependency signals, and alignment gaps into a brief; human leads review and resolve exceptions. Target: a half-day, not two days.

---

### Swell

**What it is:** A group of related waves serving a shared theme. The Swell provides the narrative that connects individual waves and surfaces cross-wave dependencies before they become blockers.

**Duration:** 3–6 weeks. The upper bound prevents thematic drift; there is no minimum — a Swell with just one wave is usually just a labeled wave.

**JIRA analogue:** Epic (maps to our existing Epic tier; see *A Note on Terminology* above).

**Artifacts:**
- A `swell.md` document with a one-paragraph outcome statement, measurable success criteria, the in-scope wave list, and a designated coordinator.
- A Swell retrospective at close: what shipped, what was deferred, what did we learn about the theme?

**Governance:** The designated coordinator coordinates cross-wave dependencies, maintains the outcome narrative, and escalates blockers. AI agents surface dependency conflicts and draft progress briefs.

**The Swell test:** If you cannot state the Swell's outcome in one sentence, it is probably two Swells. If achieving the outcome will take longer than 6 weeks, it is either a Cycle or it needs to be split. Related waves should share a coherent narrative, not merely a time window.

**SAFe equivalent:** No direct equivalent. This is the layer SAFe leaves as a gap between PI and sprint. In practice, teams form Swells organically around themes (e.g., "search quality," "dashboard improvements," "auth rework") — the Swell tier formalizes what was already happening informally.

---

### Wave

**What it is:** The core governance and delivery unit. A Wave admits one or more Changes, enforces reviewer lanes, and closes with a documented record of what was done, what was deferred, and what was learned.

**Duration:** Variable. Sized to the coherence of the objective, not the calendar. A Wave can close in days (a single-change bug fix) or span two weeks (a multi-change capability). If a Wave is growing beyond 8–10 changes, consider whether it should be two Waves under a Swell instead.

**JIRA analogue:** Feature *or* Story, depending on scope. A Wave containing multiple Changes maps to a JIRA Feature; a Wave containing a single Change maps to a JIRA Story.

**Artifacts:** Fully defined by the Wave Framework. See `docs/contributing/feature-wave-lifecycle-overview.md`.

**Governance:** Full Wave Framework lifecycle applies — Prepare wave stage gate, required reviewer lanes, Wave Council (when enabled), Progress Log, Wave Summary at close.

**Wave sizing heuristics from practice:**

| Wave Size | Change Count | JIRA Fit | Appropriate When |
|---|---|---|---|
| Focused | 1 | Story | Single tight objective; no cross-change serialization |
| Standard | 2–4 | Feature | Related changes that share watchpoints or reviewer lanes |
| Large | 5–12 | Feature (large) | Full capability area; approaching Swell scope — multiple required review lanes |
| Overloaded | 13+ | Reconsider | Consider splitting into two Waves under a Swell |

---

### Change

**What it is:** A sub-wave work item. A Change is the unit of implementation — a scoped piece of work with a change doc, acceptance criteria, and a defined kind (`feat`, `bug`, `enh`, `maint`, `doc`, `debt`, `ref`, `task`, `ops`, `change`).

**JIRA analogue:** Story or Sub-task, depending on the parent Wave's JIRA level.

**Artifacts:** Fully defined by the Wave Framework — change doc at `docs/plans/<change-id>.md`, admission into a Wave, progress tracking via tasks.

**Decision changes:** A Change of kind `change` is used for binding decisions that produce no immediate code — selecting a design direction, adopting a policy, recording a constraint. These are first-class Changes that can anchor a Wave, producing binding decisions that subsequent implementation Waves inherit.

---

## JIRA Integration

JIRA is the system of record for stakeholder-facing tracking. The Wave Framework adds governance depth that JIRA does not provide natively (reviewer lanes, Wave Council, stage gates, progress logs). The two systems are complementary.

| Framework Tier | JIRA Artifact | Notes |
|---|---|---|
| *(above model)* | Investment Theme | Unchanged; Cycles declare which Theme(s) they serve |
| Cycle | Fix Version or labeled group | New concept; no native JIRA tier — use Fix Version or custom field to represent Cycle scope |
| Swell | Epic | Maps to existing Epic artifact; the term "Swell" will be renamed to "Epic" once governance behaviors are established |
| Wave | Feature *or* Story | Feature when multi-Change; Story when single-Change |
| Change | Story *or* Sub-task | Sub-unit of the Wave's objective |

**Linking rule:** Every Wave has a JIRA Feature or Story ID as its anchor, recorded in `wave.md`. Every Change has a JIRA Story or Sub-task ID in its change doc. Swells reference JIRA Epics. Cycles reference the Investment Theme(s) they serve and are represented in JIRA as a Fix Version or labeled grouping.

**What lives where:**
- *Status and stakeholder visibility* — JIRA
- *Acceptance criteria, reviewer lanes, stage gates, review evidence, watchpoints* — Wave Framework docs
- *Strategic narrative, outcome declaration, success criteria* — Cycle and Swell docs

---

## Ceremonies: SAFe → AI-Native Mapping

| SAFe Ceremony | Replaced By | Target Duration |
|---|---|---|
| PI Planning (2 days) | Cycle Open — replaces PI Planning entirely; AI-synthesized brief, human resolution of exceptions | Half-day |
| System Demo | Swell mid-check — "are we serving the Cycle objective?" | 30 min |
| PI Retrospective | Cycle Close — outcome retrospective, AI first draft | 1 hour |
| Sprint ceremonies (planning, review, retro) | Optional — sprint cadence is a team execution choice, independent of wave governance. Waves open and close against their objective, not a calendar boundary. Teams that keep sprints coordinate wave work within them; teams that drop sprints run waves continuously until the Swell objective is met. | Team discretion |
| IP Iteration | Inline — architectural runway is maintained continuously as a Wave discipline, not a dedicated iteration |  |

---

## Planning Flow

A fully-running Cycle → Swell → Wave hierarchy operates as follows:

```
Cycle Open
  → Declare Cycle objective and success criteria
  → Identify in-scope Swells for the Cycle
  → AI synthesizes backlog state and dependency signals
  → Human leads review and resolve exceptions

  Swell Open (for each Swell in the Cycle)
    → Author swell.md: outcome statement, success criteria, wave list
    → Resolve cross-wave dependencies at Swell Open, not mid-wave
    → Assign designated coordinator

    Wave lifecycle (for each Wave in the Swell)
      → Plan feature → Create wave → Add change → Prepare wave
      → Implement → Review → Close
      (full Wave Framework lifecycle per docs/contributing/change-workflow.md)

  Swell Close
    → Verify Swell success criteria
    → Swell retrospective: shipped, deferred, learned
    → Promote durable Swell-level lessons to project memory

Cycle Close
  → Verify Cycle outcome against declared success criteria
  → Cycle retrospective: outcome achieved / retired / superseded?
  → Distill strategic learning; inform next Cycle declaration
```

> **Note on Cycle-level tooling:** AI synthesis at Cycle Open is the target state. Today this step is manual or agent-assisted — dedicated MCP tooling for Cycle-level synthesis is not yet built. See Wavefoundry Tooling at Each Tier.

---

## Decision Waves

A recurring pattern in practice: a Wave whose sole purpose is to produce binding decisions — selecting a design approach, adopting a policy, making a scope call — with no implementation. These "decision waves" use Change kind `change` and close when the decisions are recorded and approved.

Decision waves often open a Swell before any implementation waves begin. The decisions become the contract that implementation waves inherit. This prevents mid-wave discovery of conflicting direction and avoids the common failure mode of implementing before alignment is achieved.

**Example flow:**
```
Swell: "Auth Rework"
  Wave 1: Decision wave — select auth provider, token storage policy, migration approach
  Wave 2: Implementation — core auth refactor (inherits Wave 1 decisions)
  Wave 3: Implementation — migration tooling (inherits Wave 1 decisions)
```

---

## Transition: Mid-PI Cutover

> **Scope note:** This section outlines how a mid-PI cutover could work if the organization decides to proceed. If adopted, it would become an execution guide for a one-time transition — not standing operating procedure for teams running the model afterward.

This proposal recommends a hard-stop cutover rather than a gradual phase-out. The current PI would end on a declared date, and the Cycle → Swell → Wave model would take over immediately. Running the new model alongside SAFe in parallel is not recommended — it produces all the overhead of both with the discipline of neither.

### Before the date is set

Two gates must be resolved before the cutover date becomes public.

**Gate 1 — Compliance and audit.** Determine whether PI artifacts (PI objectives, System Demo records, PI retrospectives) feed a compliance or regulatory process (SOX, ISO, CMMI, internal audit). If yes, the replacement artifacts (Cycle and Swell docs, Wave review evidence) must be accepted by your compliance function before the PI artifacts are retired. Get written acceptance before the date is announced. In regulated environments this gate alone can take two to three weeks — find out now, not on cutover day.

**Gate 2 — Wave readiness by team.** Identify which teams are already running waves and which are still on sprints. Teams without Wave practice cannot absorb a cold cutover. Two options: (a) commit to Wave Framework onboarding for all teams within the cutover window, or (b) set a firm primary cutover date for Wave-ready teams and a hard "no later than +4 weeks" date for teams that need onboarding. Option b creates a brief hybrid state; that is acceptable only if the end date is firm. An open-ended stagger becomes permanent parallelism.

### Mapping in-flight work

Cutting mid-PI means the current PI is incomplete. Three categories of PI work require explicit handling:

| Category | What to do |
|---|---|
| PI Features that are fully complete | Record as closed in the PI archive. No Wave needed. |
| PI Features in progress | Scope what is done. Create a Wave for the remaining stories; the Wave inherits the PI Feature's JIRA anchor. |
| PI Features not yet started | Evaluate for Swell inclusion, or defer to backlog with a note. |

Do not force-complete a sprint before cutover — it inflates defect rate. Convert mid-sprint work to a Wave, set the Wave objective to match what the sprint was targeting, and continue. The sprint boundary disappears; the Wave objective replaces it.

### 10–14 day sequence

**Days 1–2: Resolve gates (internal)**
- Brief the compliance function. Show them the replacement artifacts and get written acceptance before the date is set.
- Survey Wave readiness by team. Use the answer to set a single cutover date or a primary date with a staggered end date for teams needing onboarding.
- Identify and brief designated coordinators for each active thematic cluster before the announcement.

**Day 3: Announce**

A single leadership communication to all teams:

> "We are ending the current PI on [date]. There will be no more PI Planning events after that date. We are moving to a Cycle → Swell → Wave model. The transition work begins immediately."

Brief language. No hedging. The date is firm.

**Days 4–10: Map and artifact**
- Categorize every PI Feature: complete, in-progress, or not-started
- Map PI objectives → Cycle objective declarations; PI feature clusters → Swells
- Create Wave stubs for all in-progress features
- Draft one `cycle.md` per Cycle objective; one `swell.md` per thematic cluster (outcome statement, success criteria, wave list, designated coordinator)
- JIRA admin: add a Cycle representation (Fix Version or custom label); confirm Swell=Epic, Wave=Feature/Story, Change=Story/Sub-task. Allow 2–3 days — do not underestimate this step.

**AI assist:** Have an AI agent ingest the current PI board and produce a first-pass mapping (PI Features → Swells, sprint stories → Wave stubs). Human leads review and correct. This step should take 2–3 hours per team, not 2 days.

**Days 8–11: Update calendars and notify stakeholders**
- Cancel all PI Planning events permanently — do not reschedule, do not leave tentative
- Convert the next PI demo slot to a Swell Close event; brief stakeholders on the format change
- Convert the PI retrospective slot to a Cycle Close
- Send stakeholders the dashboard URL — this is their new visibility surface

**Days 11–14: Onboard and go**
- Wave Framework onboarding for teams not yet running waves (Wave lifecycle overview, one guided Wave creation, stage gate walkthrough)
- Cycle Open dry run with all designated coordinators
- Cutover day: author the PI Closure Record (what was completed, what was migrated, what was deferred) and declare the first Cycle open

The PI Closure Record is the artifact that makes the cutover credible and auditable — the clean break between the old model and the new. Archive it; do not delete it.

### Role transitions

An aggressive cutover would change the day-to-day responsibilities of RTEs, Scrum Masters, and SAFe PMs. Not addressing this is the main source of resistance — teams that call it a Swell but run it like a PI planning event.

| SAFe Role | Becomes | What changes |
|---|---|---|
| Release Train Engineer (RTE) | Designated coordinator | Lighter coordination; no PI planning facilitation; owns cross-wave dependency resolution and Swell narrative |
| Scrum Master | Wave Coordinator | Owns Wave lifecycle routing, prepare gate, and review lane management |
| Product Manager (SAFe) | Cycle/Swell owner | Authors outcome statements and success criteria; owns Cycle declaration; no longer maintains PI feature backlogs |
| Product Owner (team) | Wave AC owner | Owns acceptance criteria and review lane participation at the Wave level; no longer runs sprint reviews |
| Business Owner | Swell stakeholder | Receives Swell Close reports and dashboard visibility instead of PI System Demo |

These would be reorientations, not eliminations. The functions are preserved; the ceremony overhead is not. Job descriptions and performance agreements should be updated to reflect the new model on or before the cutover date.

### What would stop on cutover day

- Story-point-based sprint planning — Wave admission replaces it
- Fixed sprint cadence — Waves close when objectives are met
- IP (Innovation & Planning) iterations — architectural work becomes a Wave type, not a dedicated iteration
- Velocity tracking — cycle time and Wave throughput replace it
- PI Planning events — cancelled permanently; Cycle Open replaces the function at a fraction of the time

### Measuring success in the first Cycle

| Signal | Target |
|---|---|
| Ceremony time per team | Under 4 hours for Cycle Open + Swell Open combined, vs. 2+ days for PI Planning |
| Cross-wave dependency conflicts mid-wave | Establish baseline before cutover; target improvement by Cycle 2 |
| Stakeholder visibility complaints | None after the first Swell Close event |
| Waves that close without carry-over | Trend improving vs. prior sprint carry-over rate |
| Teams running PI ceremonies in parallel | Zero |

---

## Industry Context

Enterprise AI-native SDLC transformation is an active and well-documented area. The following evidence base informs this model.

### Adoption benchmarks

- By 2025, 70% of enterprises had implemented AI-driven automation across their SDLC, up from under 10% in 2022 (Stack Overflow Developer Survey 2025).
- Top-quintile adopters achieved 16–30% improvements in productivity and time to market, and 31–45% gains in software quality (McKinsey, 2025).
- Developers who use AI tools daily complete 126% more projects per week than manual-only peers — compressing 6-month feature roadmaps into 3 months without adding headcount (multiple 2025 enterprise case studies).
- Gartner projects 70% of developers will use AI tools by 2027; up to 90% of enterprise developers will use AI coding assistants by 2028.

### Why parallel-running fails

Industry evidence consistently shows that organizations that achieve real AI-native velocity gains do not add AI tools to existing SAFe structures — they restructure delivery around AI capabilities. Companies that attempt to bolt AI onto unchanged ceremony structures see productivity gains that plateau quickly, as ceremony overhead consumes the time AI execution saves.

The V-Bounce model (an adaptation of the traditional V-model) documents this pattern: AI dramatically reduces time in implementation phases, but only when the planning and coordination layer is redesigned to match. Organizations that keep heavyweight PI planning while adopting AI execution find the planning layer becomes the bottleneck within one or two cycles.

### What enterprises are getting right

The SDLC transformations achieving durable results share three characteristics:

1. **Outcome-driven cadences, not calendar-driven cadences.** Delivery cycles that close when the objective is achieved — not when the quarter ends — produce better strategic alignment and lower carry-over rates.

2. **Async-first coordination with human escalation paths.** AI synthesizes planning briefs; humans resolve exceptions. This compresses PI Planning-equivalent events from two days to half a day while improving dependency identification accuracy.

3. **Governance that scales with velocity.** When AI accelerates execution, governance must scale with it — not slow it down. Stage gates, review lanes, and council-based delivery validation become more important when teams ship faster, not less important. Organizations that remove governance to go faster accumulate defects; organizations that right-size governance to the change type sustain velocity.

### Sources

- McKinsey & Company. *The AI Revolution in Software Development.* 2025. [Link](https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/the-ai-revolution-in-software-development)
- Baytech Consulting. *AI-Native SDLC: A Strategic Blueprint for CTOs.* 2025. [Link](https://www.baytechconsulting.com/blog/ai-native-sdlc-strategic-blueprint-for-ctos)
- Baytech Consulting. *Agentic SDLC: The AI-Powered Blueprint Transforming Software Development.* 2025. [Link](https://www.baytechconsulting.com/blog/agentic-sdlc-ai-software-blueprint)
- Agile Hive. *How Artificial Intelligence Is Transforming Scaled Agile.* 2025. [Link](https://agile-hive.com/blog/how-ai-is-shaping-the-future-of-scaled-agile/)
- Scaled Agile. *AI-Native.* 2025. [Link](https://scaledagile.com/ai-native/)
- EPAM. *The Future of SDLC Is AI-Native Development.* 2025. [Link](https://www.epam.com/insights/ai/blogs/the-future-of-sdlc-is-ai-native-development)
- arXiv. *The AI-Native Software Development Lifecycle: A Theoretical and Practical New Methodology.* 2024. [Link](https://arxiv.org/pdf/2408.03416)
- NextAgile. *Future of Enterprise Agility 2026.* [Link](https://nextagile.ai/blogs/agile/future-of-enterprise-agility/)

---

## Wavefoundry Tooling at Each Tier

| Tier | Wavefoundry Tools | Notes |
|---|---|---|
| Cycle | Manual artifact (`cycle.md`); `wave-dashboard` for portfolio visibility | No dedicated MCP tools yet; managed as a docs-tier artifact |
| Swell | Manual artifact (`swell.md`); `wf_list_waves` to survey in-scope waves | Swell acts as a grouping label on wave docs |
| Wave | Full MCP surface — `wf_create_wave`, `wf_current_wave`, `wf_prepare_wave`, `wf_implement_wave`, `wf_review_wave`, `wf_close_wave`, `wf_garden_docs`, `wf_audit`, `wf_validate_docs` | See `docs/prompts/index.md` for full command catalog |
| Change | `wf_add_change`, `wf_get_change`, `wf_new_*` tools for each change kind | Change docs authored at `docs/plans/`; admitted into waves |

The Wave Framework's full lifecycle governance — stage gates, reviewer lanes, Wave Council (when enabled), progress logs, journal watchpoints — applies at the Wave and Change tiers. Swell and Cycle tiers are lighter-weight: they govern narrative and outcome alignment, not implementation mechanics.

---

## Related Documents

- `docs/contributing/change-workflow.md` — the Wave and Change lifecycle in detail
- `docs/contributing/feature-wave-lifecycle-overview.md` — Wave lifecycle with reviewer lanes and Wave Council
- `docs/references/project-overview.md` — Wavefoundry's own workflow
- `docs/prompts/index.md` — full MCP and CLI command catalog
- `AGENTS.md` — stage gate and guardrails
