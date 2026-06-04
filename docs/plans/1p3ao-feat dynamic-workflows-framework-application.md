# Dynamic Workflows — Framework Application Roadmap

Change ID: `1p3ao-feat dynamic-workflows-framework-application`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-04
Wave: TBD (roadmap doc; individual changes admitted later under one or more waves)

## Rationale

Claude Code's [dynamic workflows](https://code.claude.com/docs/en/workflows) feature (research preview, v2.1.154+) lets Claude write a JavaScript orchestration script that fans many subagents out in parallel, with intermediate results held in script variables instead of the conversation context. The article identifies the load-bearing pattern as **"draft / audit from several independent angles, then synthesize a cross-checked result"** — not just "more agents."

That pattern shows up across this framework in multiple places where today the work is serialized inside one Claude session. This doc inventories the surfaces, tiers them by leverage, and records design considerations so future admissions can pull from a coherent picture rather than rediscovering it.

**The framework's existing protocols already match the workflow shape.** Wave Council Phase 1 (red-team primer) + Phase 2 (independent specialist seats) + moderator synthesis IS literally the article's "repeatable quality pattern with independent agents adversarially reviewing each other's findings." The current implementation walks the seats sequentially inside one session; the workflow runtime expresses the same protocol natively.

## Application Surfaces

### Tier 1 — Highest leverage; framework-defining

#### T1.1 — All councils as workflows

Four council surfaces currently run sequentially inside one Claude session that plays each seat in turn:

- **Wave Council prepare-phase review** (`seed-180` / `wave_review`) — 5 fixed seats + rotating + red-team primer + moderator
- **Wave Council delivery-phase review** — same protocol, post-implementation
- **Archetype Council** (`seed-236`) — operator-invoked, stance-based, multi-perspective lens applicable to plans, design docs, code, prose, decision narratives, naming, AC formulation
- **Red-team standalone review** (`seed-225`) — 5 thinking stances (adversarial, constructive, simplicity, first-principles, analogical); today one agent applies them sequentially in `council-adversarial-primer` mode

**Workflow shape:**
- Phase 1: red-team primer agent runs first, in isolation. Output is shared as briefing-packet input to Phase 2 seats.
- Phase 2: 4-6 specialist agents spawn in parallel, each receiving the briefing packet + primer + the artifact under review, each producing a finding record per `seed-209-agent-harness-core`.
- Phase 3: moderator agent synthesizes verdict, names strongest challenge / strongest alternative, records advisory follow-ups.

**Why it wins:**
- Stops cross-contamination between seats — each Phase-2 agent forms its read independently rather than being influenced by the previous seat's framing
- Cuts wall-clock review time roughly to (Phase 1 + max(Phase 2 seats) + Phase 3) instead of sequential sum
- The script captures the protocol explicitly — depth-tier rules, rotating-seat selection, MF-recording shape — instead of relying on the moderator agent to remember
- Recordable, rerunnable — re-running a council review on the same artifact produces a comparable trace

**Migration consideration:** the current `wave_review` MCP tool surface stays the contract; the workflow becomes the implementation under the hood. Operators invoking the tool see the same input/output. The workflow is launched from the tool implementation via `claude -p` or the Agent SDK.

#### T1.2 — Install Phase 2 as workflow

`seed-012` Phase 2 has 13 numbered steps. Walking them sequentially inside one Claude session today costs install time and context. Many steps are independent:

**Dependency graph:**
```
seed-030 (repo-profile)  ← prerequisite for almost everything
    ├── seed-040 (docs structure)        — independent
    ├── seed-050 (agent docs)            — independent
    ├── seed-080 (docs gate hooks)       — independent
    ├── seed-090 (gardening harness)     — independent
    ├── seed-100 (prompt surface)        — independent
    ├── seed-110 (waves bootstrap)       — independent
    ├── seed-140 (drift policy)          — independent
    └── seed-060 (architecture map)      ← prerequisite for 070, 120
            ├── seed-070 (posture docs)
            └── seed-120 (personas)      ← also depends on 030
                    └── seed-130 (journals) ← depends on 050
```

**Workflow stages:**
- Stage 1 (sequential): seed-030 — evidence base required by everything downstream
- Stage 2 (parallel fan-out, ~8 agents): the independent seeds (040, 050, 080, 090, 100, 110, 140) + seed-060
- Stage 3 (parallel fan-out, ~3 agents): seed-070, seed-120, seed-130 — each gated on stage-2 outputs
- Stage 4 (synthesis): operator summary, install_log finalization, `wave_install_audit` final pass

**Why it wins:**
- 3-5x install wall-clock speedup on a fresh repo (rough estimate; bounded by seed-030's runtime + the longest stage-2 agent)
- Each agent gets a focused brief (one seed) instead of context-juggling 13 — better quality per artifact
- Cross-checking: in Stage 4 a synthesis agent can verify that all stage-2/3 outputs actually exist and match their seed's expected artifacts before finalizing — catches the "agent claimed done but artifact missing" failure mode that `wave_install_audit` exists to catch, but at install time rather than at audit time
- Operator gets one consolidated handoff at the end, not 13 progress updates

**Constraints:**
- `wave_install_audit` is part of the install protocol (per wave 1p35d). The workflow's final stage MUST still call it; the workflow doesn't replace it.
- The install log (`.wavefoundry/install-log.md`) is the operator-visible state-of-truth. Workflow agents write `[x]` rows as they complete; the synthesizer verifies the log matches on-disk state.
- This is the install surface that **fresh users** see. Failure modes need to be especially clear — a workflow that fails opaquely is worse than a sequential install that fails one step at a time.

#### T1.3 — Guru with multi-path code exploration + cross-checked answers

Guru today gets a question and walks `code_ask` / `code_search` / `code_definition` / `code_graph_path` / `docs_search` serially. It forms one hypothesis, gathers confirming evidence, and returns. Three known failure modes:

- **Tunnel vision**: investigates one code path; misses an equally plausible other path (config-source vs. CLI-flag-source vs. env-var-source).
- **Confident wrong answers**: forms hypothesis, finds confirming evidence, never tries to falsify. Confirmation bias inside one agent's session is invisible to itself.
- **Coverage gaps**: doesn't know what it doesn't know — answers "I didn't find it" when a different search angle would have found it.

**Workflow shape (modeled on `/deep-research`):**
- Phase 1: question-decomposition agent generates 3-5 independent angles to investigate the question (e.g., for "where does X get configured?" — config files, env vars, code defaults, MCP tool params, runtime overrides, CLI flags).
- Phase 2: one agent per angle runs in parallel, each producing a finding record with evidence pointers (file:line) and confidence.
- Phase 3: cross-check agent reads all Phase-2 findings, votes on each claim, filters out claims that didn't survive cross-checking, identifies contradictions.
- Phase 4: synthesis agent produces the answer with citations and explicit notes when angles disagreed.

**Why it wins:**
- Catches tunnel vision: 5 independent agents starting fresh from different angles produce different hypotheses; the cross-check phase surfaces them.
- Catches confirmation bias: angle-1's confirming evidence is angle-2's null result. The contradiction is visible.
- Catches coverage gaps: angle-N agents that found nothing are explicit data points, not silent failures.
- Answer quality goes up; operator gets one synthesized answer + citations instead of a turn-by-turn walk.

**Constraints:**
- Cost. A guru workflow uses 5-10x more tokens than a single-agent guru reply. Make it opt-in (a `guru-deep` mode) rather than the default route; default guru stays single-agent for quick questions.
- The wavefoundry MCP `code_*` tools are the lever the agents pull. The workflow doesn't bypass them; it just fans them out.
- Article calls out `/deep-research` as the bundled workflow — the framework's guru-deep workflow is the same shape applied to code/docs rather than to the open web.

### Tier 2 — Significant leverage; scoped

#### T2.1 — Plan-feature multi-angle drafting

`seed-170 interrogate-plan` exists because single-agent plan-drafting under-explores alternatives. A workflow could spawn 3-5 independent planning agents, each with a different stance (simplicity-first, robustness-first, evidence-first, alternative-first, deferred-by-default), each producing a candidate plan. A synthesis seat then picks the strongest or merges. This is the article's "draft a hard plan from several angles before committing to one" exactly.

#### T2.2 — Wave-readiness multi-dimension audit

`wave_audit` today is a single-pass scan with sub-checks (lint, index health, harness coverage, harness coherence, agent role docs, install log). A workflow could fan out one agent per dimension, each digging deeper than the current scan, with a synthesis seat producing a unified readiness verdict. Especially useful for `wave_prepare` where the gate is "is this wave ready to implement."

#### T2.3 — Multi-stance red-team review (standalone, not council-mode)

Today a standalone red-team review applies the 5 stances sequentially inside one agent. A workflow could spawn one agent per stance in parallel, each operating without seeing the others' framing, then synthesize. Catches the "stance-3 inherits stance-1's framing" cross-contamination problem.

### Tier 3 — Audit and gardening surfaces

#### T3.1 — Multi-seed coherence detector

`_audit_harness_coherence` scans 91 seed files for stale-tool-reference patterns. A workflow could spawn one agent per seed file (or per logical seed-group) with structured cross-checks, catching coherence violations a single regex pass misses (e.g., contract drift, schema drift, example drift).

#### T3.2 — Garden / wave_garden as parallel fan-out

`wave_garden` refreshes doc metadata across the whole tree sequentially. Workflow could fan out per doc-class (waves, plans, agents, prompts, references) with one gardener agent per class, then a synthesizer reconciles cross-class references.

#### T3.3 — Distill journals fan-out

`seed-210 distill-journals` walks N agent journals sequentially. A workflow could fan out one agent per journal (or per role), each producing a per-journal distillation, then a synthesis agent produces the cross-role lesson catalog.

#### T3.4 — Closed-wave retrospective harvest

Extract lessons from N closed waves in parallel — one agent per wave reads `wave.md` + admitted change docs + delivery-council verdicts and produces a structured lesson record. A synthesis agent identifies cross-wave patterns. Today this is a manual operator chore.

#### T3.5 — Cross-seed stale-reference sweep

The C3-DC-1 advisory ("sweep other seeds for `seed-010` topic-pointer references") is exactly this shape — fan out one agent per seed, each checks for a small set of stale patterns, then synthesize.

#### T3.6 — Multi-extractor characterization for `1p397`

Per the in-flight bug plan `1p397` (universal oversized-chunk guard): the per-chunker audit step is naturally fan-out shaped. One agent per chunker type (markdown, plain text, YAML, JSON, TOML, HTML, XML), each constructing oversized fixtures, characterizing emitted chunk sizes, reporting whether the universal guard catches it. Cross-check phase identifies chunkers whose fixtures are missing edge cases. **Most concrete near-term application** — pulls into the `1p397` wave when it admits.

## Cross-Cutting Design Considerations

### Constraints from the article

- **Research preview** — Anthropic may change the API. Framework cannot make this a hard dependency for vendored consumers running on older Claude Code versions.
- **Paid plans + v2.1.154+** — consumers on Pro/Max/Team/Enterprise are the only ones with the feature. Framework needs a graceful degradation path: when workflows aren't available, fall back to the existing sequential implementation of each surface.
- **16 concurrent agent ceiling, 1000 total per run** — every workflow above stays well under both. T1.2 install workflow has the biggest Stage 2 fan-out (~8 agents); plenty of headroom.
- **No mid-run user input** — between stages where the operator might redirect (e.g., council Phase 2 disagreement → operator picks a direction), each phase has to be its own workflow run rather than one long workflow.
- **File edits auto-approved within agents** — fine for council/garden/distill (read-mostly), but the install workflow's Stage 2 agents do write a lot. Operator approval lives at the workflow-launch boundary; agents inherit auto-edit inside.

### Graceful degradation

Every surface in this doc must work without dynamic workflows. The workflow form is a **performance + quality improvement**, not the new contract. Implementation pattern:

```
if dynamic_workflows_available:
    invoke_workflow(<workflow-name>, <args>)
else:
    invoke_sequential_impl(<args>)  # current behavior
```

Vendored consumers on the free tier or on older Claude Code see the existing sequential behavior. Paid-tier maintainers on current Claude Code see the workflow path. The MCP tool surface (e.g., `wave_review`, `wave_audit`) doesn't change shape either way — only the implementation under the tool's hood changes.

### Where the workflow scripts live

Per the article: `.claude/workflows/<name>.js` for project-shared, `~/.claude/workflows/<name>.js` for personal. The framework's workflows belong at `.claude/workflows/` so they're committed and shared with every operator on a seeded repo.

But: those files are JS, not the framework's seeded prose. They need their own contract:
- One workflow per surface (`wave-council-review.js`, `install-phase-2.js`, `guru-deep.js`, etc.)
- Each workflow consumes a documented `args` shape (the contract the tool surface passes in)
- Each workflow is generated/maintained from a corresponding `.wavefoundry/framework/workflows/*.template.js` source-of-truth, similar to how `seed-050` renders hook bodies
- `docs-lint` enforces that committed workflow files at `.claude/workflows/` match what the framework renders, similar to the existing host-config hook contract

### What we don't know yet

- Whether `claude -p` invocation of a workflow from inside a Python subprocess (`server_impl.py`) handles the agent's session model selection correctly. The article mentions per-stage model routing; the implementation contract isn't fully spelled out.
- Whether the workflow runtime exposes a programmatic completion callback the MCP tool can await, or whether the tool has to poll progress files. Probably affects how `wave_review` wraps the workflow.
- How well the workflow runtime composes with the framework's MCP tool surface — the article focuses on web search + filesystem agents; the council/install workflows would heavily call MCP tools. Likely fine, but unverified.

These are first-experiment questions for T1.1 or T1.2 implementation, not roadmap blockers.

## Sequencing Recommendation

Not all of this lands in one wave. Suggested sequence:

1. **First experiment — T3.6 inside `1p397`**: smallest scope, clearest fan-out shape, low risk. Lets us learn the workflow contract + MCP composition before betting on bigger surfaces. Ride on the bug plan we already have.
2. **First production move — T1.1 wave-council workflows**: highest-frequency surface; biggest quality + speed win; the existing `wave_review` MCP tool gives us the surface boundary.
3. **Big bet — T1.2 install workflow**: largest payoff but highest operator-visibility risk. Sequence after T1.1 has been used on real waves enough to trust the contract.
4. **Quality differentiator — T1.3 guru-deep**: opt-in mode for hard questions; lands once we trust the multi-agent cross-check pattern from T1.1.
5. **Remaining tiers** — admit as evidence accumulates that the operator + framework benefit.

## Out of Scope

- Implementing any of these surfaces in this doc — this is roadmap only. Each surface becomes its own admitted change with its own ACs.
- Replacing the existing protocols' prose specs. The seed prose remains the canonical contract; the workflow is one valid implementation of the contract.
- Web-search workflows beyond `/deep-research` itself. The framework's value-add is code/docs/protocol fan-out, not generic research.

## Risks

| Risk | Mitigation |
|---|---|
| Anthropic ships a breaking change to the workflow runtime mid-development | Every surface has graceful degradation to its current sequential impl. A breaking change degrades quality, not correctness. |
| Vendored consumers on free tier never get the workflow path | Acceptable. The sequential implementation is the baseline; workflows are an enhancement for paid-tier maintainers. |
| Install workflow fails in a hard-to-diagnose way for fresh users | Install is the highest-risk surface. Defer T1.2 until T1.1 has produced real operator confidence. Always preserve the sequential fallback. |
| Workflow scripts drift from their template source-of-truth | Treat `.claude/workflows/*.js` as generated artifacts. Lint-enforced contract per the docs-lint hook pattern. |
| Multi-agent runs spend tokens unpredictably on iterative cycles | Workflow-launching tools should default to "sequential" mode and require explicit opt-in for "workflow" mode — at least until the operator has run enough workflows to calibrate cost. |
| Council workflows lose the human-readable per-seat journal trail that operators currently rely on | Each Phase-2 agent's output goes into the wave's `## Review Evidence` section via the moderator synthesizer; the moderator records each seat's verdict, strongest-challenge, and recommendation per the existing council schema. Trail is preserved, not lost. |

## Related Work

- **Claude Code Dynamic Workflows** — `https://code.claude.com/docs/en/workflows` (article that motivated this doc)
- **`seed-225` red-team** — defines the 5-stance model the standalone red-team workflow would parallelize
- **`seed-215` wave-council** — defines the council protocol the workflow would implement
- **`seed-236` archetype-council** — same shape; broader scope
- **`seed-209` agent-harness-core** — finding record schema all parallel-agent outputs must conform to
- **`seed-012` install-phase-2** — sequential install spec the install workflow would parallelize
- **`seed-211` guru** — sequential code/doc Q&A agent the guru-deep workflow would extend
- **`wave_review` MCP tool** — the existing tool boundary the council workflows slot under
- **`wave_install_audit` MCP tool** — install correctness gate the install workflow must continue to call
- **`1p397` (in-flight bug plan)** — T3.6 (multi-chunker audit) is the smallest-scope first experiment

## Session Handoff

Roadmap doc. Not admitted to a wave. The first surface to implement is T3.6 inside `1p397`'s wave; that gives us the first contract validation. T1.1 wave-council workflows is the second move once T3.6 has shaken out the MCP composition + agent SDK boundary.

Future admissions:
- T3.6 → admit alongside `1p397` and `1p399` into the post-1p35d wave
- T1.1 → own wave after T3.6 lands
- T1.2 → own wave after T1.1 has been used on 2-3 real council reviews
- T1.3 → own wave after T1.1
- T2.* and T3.* → opportunistic; admit when an in-flight wave has natural overlap
