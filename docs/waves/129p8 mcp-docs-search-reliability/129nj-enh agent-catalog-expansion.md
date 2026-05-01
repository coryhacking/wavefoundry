# Specialist Agent Catalog Expansion And Role Enhancement

Change ID: `129nj-enh agent-catalog-expansion`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30
Wave: `129p8 mcp-docs-search-reliability`

## Rationale

Wavefoundry's current agent surface is intentionally small and lifecycle-focused: generic delivery roles, two project personas, and a narrow set of factor-review agents. That surface is coherent for Wavefoundry itself, but the review of `msitarzewski/agency-agents` surfaced a larger framework-level gap: the seed pack does not yet model broadly reusable specialist roles that should be available across heterogeneous target repositories.

Today the likely seed additions are framed too narrowly around Wavefoundry's own roadmap: MCP design, indexing, workflow mapping, documentation authoring, and evidence-heavy release evaluation. Those are useful, but they are only one slice of the framework's actual target space. The framework is already intended to support materially different repository archetypes, including:

- Apple-platform repos such as Swift and macOS applications
- frontend and full-stack web repos such as React + AWS systems
- backend/platform repos such as Java services and Spring Boot systems
- AI/agent repos that need MCP, indexing, orchestration, and trust specialists

Across those archetypes, the seed pack currently has no explicit reusable place for specialists such as frontend, backend, mobile, UI, UX research, UX architecture, infrastructure, reliability, or broader application security. Those responsibilities are either absent or awkwardly overloaded onto `planner`, `implementer`, `architecture-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, and `wave-coordinator`.

This change therefore needs to do two things at once:

- strengthen existing core roles and review roles using the best structural lessons from the external agent definitions
- define a framework-wide specialist model that is archetype-aware rather than Wavefoundry-local

The goal is still not to import The Agency wholesale. The goal is to seed a disciplined, generic framework catalog that can expose:

- universal specialists that make sense across many repos
- archetype specialists that should appear only when repo evidence supports them
- repo-local specialists that a specific project may add beyond the shared framework

The current core lifecycle roles remain the default delivery surface. Specialists are additive, but the seed framework needs to be broader than the initial Wavefoundry-specific shortlist.

## Requirements

1. Wavefoundry must define an explicit supported-agent taxonomy that is distinct across at least:
   - generic roles
   - personas
   - factor-review agents
   - universal specialists
   - archetype specialists
   - repo-local specialists
2. The framework-wide specialist model must be seed-safe for heterogeneous target repositories rather than being limited to Wavefoundry's own local roadmap.
3. The shared seed framework must adopt only specialists that are broadly reusable across software repositories or clearly tied to a supported project archetype. Unrelated business, marketing, finance, support, regional-platform, and industry-specific agents must remain out of scope for the default seed pack.
4. The initial universal specialist shortlist must cover the highest-signal reusable additions identified in the external review:
   - `codebase-onboarding-engineer`
   - `software-architect`
   - `security-engineer`
   - `technical-writer`
   - `workflow-architect`
   - `reality-checker`
   - `delivery-workflow-steward` (Wavefoundry adaptation of Jira Workflow Steward, without Jira coupling)
   - `mcp-builder`
   - `lsp-index-engineer`
5. The initial archetype-specialist shortlist must cover at least the cross-project families most relevant to known target-repo classes:
   - web / full-stack: `frontend-developer`, `backend-architect`, `ui-designer`, `ux-researcher`, `ux-architect`, `devops-automator`, `sre`, `accessibility-auditor`, `api-tester`, `database-optimizer`
   - mobile / desktop / Apple-platform: `mobile-app-builder`, plus a Wavefoundry-native Apple-platform specialist such as `apple-platform-engineer` if the external catalog does not cover Swift/macOS work well enough
   - AI / agent systems: `ai-engineer`, `mcp-builder`, `lsp-index-engineer`, `incident-response-commander`, and later-phase trust/identity specialists when justified
   - backend platform / JVM: classify whether generic `backend-architect` is sufficient or whether framework-native specialists such as `java-backend-engineer` or `spring-boot-engineer` should be added
6. Each shortlisted specialist must have an explicit classification:
   - new specialist agent definition
   - enhancement folded into an existing Wavefoundry role
   - defer
   - reject
7. Existing Wavefoundry roles must be reviewed for enhancement opportunities and updated where the specialist should strengthen an existing role rather than replace it. At minimum this review must cover:
   - `planner`
   - `wave-coordinator`
   - `architecture-reviewer`
   - `qa-reviewer`
   - `docs-contract-reviewer`
   - `security-reviewer`
8. Existing role-definition structure must be strengthened where useful by adopting the best parts of the reviewed external agent definitions. At minimum, the review must decide which existing roles should gain:
   - an explicit default stance
   - a short anti-goals / boundary section
   - a defined output or deliverable shape
   - explicit review dimensions or decision lenses
   - clearer evidence standards
   - explicit assumption-tracking requirements
9. The resulting documentation must explain when to invoke a specialist versus a generic role, and when a specialist is universal versus archetype-scoped, so the surface does not become ambiguous or duplicative.
10. The framework must define how specialist availability is derived from repo evidence such as `docs/repo-profile.json`, project archetypes, primary languages, platform targets, or other seeded inventory artifacts.
11. The repository must gain a durable doc that lists supported agent categories, supported universal specialists, and supported archetype specialists, rather than leaving that knowledge only in ad hoc discussions.
12. Routing docs must describe how specialist agents participate in planning, implementation, review, and acceptance without changing the existing stage-gate or wave-lifecycle rules.
13. The plan must preserve the current core role set as the default delivery surface. Specialists are additive and situational, not a replacement for `planner`, `implementer`, `wave-coordinator`, or mandatory review lanes.
14. If platform mapping or generated native wrappers are not ready for specialist agents, the docs must state that clearly rather than implying they already exist.
15. Canonical framework seeds must be updated where the supported agent taxonomy, reusable role-definition shape, or seeded routing behavior is meant to apply across target repositories.
16. Seed changes must be limited to the canonical surfaces that actually define or refresh reusable agent behavior. The initial expected touchpoints are:
   - `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
   - `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
   - `.wavefoundry/framework/seeds/150-refresh-wavefoundry.prompt.md`
   Additional seed files may be included when the implementation shows they are required to keep archetype-aware routing, repo-profile mapping, and generated specialist surfaces internally consistent.
17. The final agent-catalog design must be self-hosting-safe: no specialist definition may assume one product stack, hosted infrastructure model, or business function outside the framework boundary.
18. The final seed design must preserve the framework boundary rule: generic framework behavior belongs in the canonical seeds, archetype-gated specialist availability belongs in shared routing logic, and repo-specific reviewer assignments, personas, and operating exceptions remain in the seeded repository's local docs.

## Scope

**Problem statement:** Wavefoundry has clear core lifecycle roles, but no explicit framework-wide specialist model for cross-project software archetypes. Without that model, useful specialists for frontend, backend, mobile, UI, UX, infra, reliability, security, AI/agent systems, and technical writing are either missing or awkwardly overloaded onto generic roles.

**In scope:**

- defining a framework-wide specialist-agent support model for seeded repositories
- classifying the shortlisted external agents into adopt / adapt / defer / reject
- classifying which specialists are universal versus archetype-specific versus repo-local
- authoring new specialist agent docs where adoption is warranted
- enhancing existing generic role docs where specialist posture should be absorbed instead of duplicated
- strengthening existing role definitions with sharper operational structure where warranted:
  - explicit default stance
  - anti-goals / role boundaries
  - defined output shape
  - explicit review dimensions
  - clearer evidence requirements
  - explicit assumption tracking
- documenting specialist routing in the existing workflow docs
- documenting how repo evidence and archetype detection determine which specialist surfaces should be present in a seeded repository
- documenting platform-mapping status for any new specialist definitions
- adding a durable catalog doc for supported agent categories and supported specialists
- updating the canonical framework seeds that make these behaviors reusable across seeded projects, especially:
  - `seed-050` for canonical role-doc shape and agent-entry structure
  - `seed-100` for seeded prompt/routing expectations where specialist vs generic role usage and archetype-scoped specialist availability must be described
  - `seed-150` for upgrade/refresh parity so seeded repositories reconcile to the new taxonomy and specialist surfaces on upgrade
- deciding whether additional framework-native specialists are needed where the external catalog is weak for known target stacks, especially Apple-platform and JVM/Spring work

**Out of scope:**

- importing the full `agency-agents` catalog
- adding business, marketing, sales, finance, support, legal, gaming, regional-market, CMS-specific, or niche vendor/platform agents to the default seed pack
- changing the wave lifecycle, review policy, or stage-gate requirements
- adding new personas unless repository evidence later shows a missing human operator role
- generating native platform wrappers for specialists if wrapper generation is still deferred
- editing public shortcut phrases unless later review proves a concrete need
- broad seed-pack rewrites outside the agent-structure surfaces named by this plan

## Acceptance Criteria

- AC-1: Wavefoundry has a documented supported-agent taxonomy covering generic roles, personas, factor-review agents, and specialists.
- AC-2: The taxonomy distinguishes universal specialists, archetype specialists, and repo-local specialists, with clear rules for when each category should be present.
- AC-3: The shortlist of candidate specialists is classified with explicit rationale for adopt / adapt / defer / reject decisions.
- AC-4: New specialist docs exist for every agent accepted into the initial universal or archetype specialist tiers.
- AC-5: The seeded framework includes a documented first-pass archetype mapping for at least web/full-stack, mobile/desktop, AI/agent systems, and backend/JVM repositories.
- AC-6: Existing role docs are updated where specialist posture should be absorbed into `planner`, `wave-coordinator`, `architecture-reviewer`, `qa-reviewer`, `docs-contract-reviewer`, or `security-reviewer`.
- AC-7: Existing role docs gain sharper operational structure where adopted by the change: explicit default stance, anti-goals or role boundaries, deliverable shapes, review dimensions, evidence requirements, or assumption tracking.
- AC-8: Workflow routing docs explain when to invoke a specialist versus a generic role, and when a specialist is universal versus archetype-scoped, with no ambiguous overlap left undocumented.
- AC-9: Platform mapping docs accurately describe whether specialist agents exist only as generic docs or also as native platform wrappers.
- AC-10: The documented specialist set remains bounded to reusable software-project needs and does not import unrelated agency roles into the shared framework.
- AC-11: Canonical framework seeds are updated where required so the supported specialist taxonomy, stronger role-definition shape, and archetype-aware routing can be seeded into other projects.
- AC-12: Upgrade/refresh guidance remains internally consistent: seed-driven init and upgrade paths know how to create or reconcile the new taxonomy and specialist surfaces without inventing repo-specific behavior in the shared framework pack.

## Tasks

- Inventory the docs that currently define the supported agent surface and identify where a specialist tier should live.
- Define the taxonomy boundaries between generic roles, personas, factor-review agents, universal specialists, archetype specialists, and repo-local specialists.
- Decide the documentation structure for specialist support:
  - extend `docs/agents/README.md`
  - add `docs/agents/specialists/README.md`
  - add one file per supported specialist under `docs/agents/specialists/`
  - decide whether archetype specialists should live under grouped subdirectories or a flat specialist catalog with archetype metadata
- Define the first-pass archetype map the shared framework should recognize, at minimum:
  - web / frontend / full-stack
  - backend / service / platform
  - mobile / desktop / Apple-platform
  - AI / agent systems
  - JVM / Java / Spring
- Classify the shortlisted external agents into:
  - adopt as specialist
  - adapt into an existing role
  - defer
  - reject
- For each accepted specialist, classify whether it is:
  - universal in the shared framework
  - archetype-scoped in the shared framework
  - repo-local only
- Draft specialist docs for the accepted set, grounded in the shared framework boundary rather than only Wavefoundry's local roadmap.
- Decide where the framework needs Wavefoundry-native specialist definitions because the external catalog does not adequately cover known target stacks, especially Apple-platform and JVM/Spring work.
- Update existing role docs to absorb the strongest enhancement patterns from the external agents where duplication would be wasteful.
- For each updated existing role, decide explicitly whether to add:
  - default stance
  - anti-goals / boundaries
  - output or deliverable shape
  - review dimensions
  - evidence requirements
  - assumption tracking
- Update workflow routing docs so specialist usage is explicit and non-conflicting.
- Update workflow routing docs so specialist usage is explicit and non-conflicting across multiple repo archetypes, not only Wavefoundry.
- Decide how seeded repositories learn which specialists apply:
  - `docs/repo-profile.json`
  - archetype and language evidence
  - explicit local overrides
- Update platform mapping docs to show how specialists relate to future native wrappers.
- Decide whether any catalog summary belongs in `docs/references/project-overview.md` or should stay localized to `docs/agents/`.
- Update `seed-050` so canonical role-doc generation guidance and agent-entry structure can carry the sharper role-definition shape and any new specialist-surface rules that belong in the shared framework.
- Update `seed-100` so seeded prompt/routing docs can mention specialist-vs-generic role usage, universal-vs-archetype specialist availability, and repo-profile-driven routing.
- Update `seed-150` so refresh/upgrade parity includes the new taxonomy, archetype-aware specialist surfaces, and reconciliation rules.
- Verify whether any additional overview or subsystem seeds need small consistency updates, and keep that set minimal.
- Guard seed edits with the standard protected-surface workflow when implementation begins; do not treat this planning update as seed-edit authorization.

## Agent Execution Graph


| Workstream          | Owner       | Depends On     | Notes                                                                    |
| ------------------- | ----------- | -------------- | ------------------------------------------------------------------------ |
| taxonomy-design     | planner     | —              | Define supported categories, universal specialists, and archetype boundaries |
| archetype-mapping   | planner     | taxonomy-design | Map specialist availability to repo archetypes and evidence signals     |
| candidate-triage    | planner     | archetype-mapping | Classify shortlisted external and framework-native specialists       |
| role-enhancement    | planner     | candidate-triage | Decide which behaviors fold into existing roles and which structural upgrades to adopt |
| specialist-docs     | implementer | candidate-triage | Author accepted specialist docs                                       |
| routing-docs        | implementer | role-enhancement, specialist-docs | Update workflow and platform mapping docs               |
| seed-updates        | implementer | archetype-mapping, role-enhancement, routing-docs | Update canonical seed surfaces so the behavior is reusable across projects |
| verification        | code-reviewer | seed-updates  | Check overlap clarity, scope discipline, and consistency across docs and seeds |


## Serialization Points

- `docs/agents/README.md` is a single-author surface while the supported taxonomy is being restructured.
- Any new `docs/agents/specialists/` directory structure should be settled before authoring individual specialist docs.
- The universal-versus-archetype classification must be settled before drafting seed behavior, otherwise the framework may over-generate or under-generate specialist surfaces in target repos.
- `docs/contributing/agent-team-workflow.md` should be updated only after specialist classifications are decided, otherwise routing guidance will churn.
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` and `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` are protected single-author surfaces during implementation.
- Seed updates must be sequenced after the local doc model is settled so the shared pack reflects a finalized framework rule instead of a draft local experiment.
- If `docs/references/project-overview.md` is updated, it should happen after the final supported specialist set is chosen so the high-level overview does not drift from the detailed catalog.

## Affected Architecture Docs

N/A — this change is about agent-role documentation, workflow routing, and supported operating surfaces. It does not alter Wavefoundry runtime module boundaries, data/control flow, or packaging behavior.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The framework needs a durable supported-agent taxonomy before specialist additions can be seeded coherently across heterogeneous repos. |
| AC-2 | required | Universal-versus-archetype-versus-repo-local distinctions are necessary to avoid either flooding every repo with irrelevant agents or hiding useful ones. |
| AC-3 | required | Adopt/adapt/defer/reject classification is the core planning output that keeps the specialist set bounded and deliberate. |
| AC-4 | required | Any specialist accepted into the initial universal or archetype tiers needs a concrete role doc or the catalog remains conceptual only. |
| AC-5 | required | Archetype mapping is necessary for the framework to work across Swift/macOS, web/full-stack, AI/agent, and JVM/Spring repos. |
| AC-6 | required | Updating existing core roles is part of the requested outcome and prevents duplicate or competing agent definitions. |
| AC-7 | required | Sharper role structure is the highest-value lesson from the external review and is central to the change. |
| AC-8 | required | Routing clarity is needed to keep the expanded surface usable rather than ambiguous across multiple project types. |
| AC-9 | important | Platform-mapping accuracy matters, but it is secondary to defining the catalog, classification rules, and seeded routing behavior. |
| AC-10 | required | Scope discipline is necessary to avoid importing irrelevant agency roles into the shared framework. |
| AC-11 | required | Seed updates are explicitly required so the broader specialist taxonomy and routing behavior are reusable across target repositories. |
| AC-12 | required | Upgrade and refresh parity must stay coherent or seeded repositories cannot reliably consume the new surface. |


## Progress Log


| Date       | Update         | Evidence                 |
| ---------- | -------------- | ------------------------ |
| 2026-04-30 | Plan authored. | This conversation thread |
| 2026-04-30 | Prepare wave completed; change relocated into active wave and marked ready. | `docs/waves/129p8 mcp-docs-search-reliability/wave.md` |
| 2026-04-30 | Plan broadened from a Wavefoundry-local specialist shortlist to a framework-wide, archetype-aware seed strategy. | This conversation thread |
| 2026-04-30 | Prepare wave rerun after scope broadening confirmed the updated taxonomy, archetype mapping, and seed expectations remain implementation-ready. | `docs/waves/129p8 mcp-docs-search-reliability/wave.md` |


## Decision Log


| Date       | Decision                                                                                         | Reason                                                                                       | Alternatives                                                                 |
| ---------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 2026-04-30 | Keep the current generic role set as the default operating surface                               | The lifecycle is already built around these roles; replacing them would create unnecessary churn | Replace generic roles with imported specialists; rejected as unnecessary scope inflation |
| 2026-04-30 | Add a bounded specialist tier instead of importing The Agency wholesale                           | Wavefoundry is a framework/tooling repository with a narrow product boundary                 | Mirror the full external catalog; rejected because most of it is irrelevant   |
| 2026-04-30 | Adapt Jira Workflow Steward into a repository-local delivery workflow specialist if adopted       | Traceability and workflow discipline are useful; Jira coupling is not                        | Import Jira-specific language directly; rejected as incompatible with local scope |
| 2026-04-30 | Use the external agent definitions to sharpen existing role structure, not just to source new specialist names | The highest-value lesson from the review is clearer operational contracts for roles already in use | Limit the change to adding new specialists only; rejected because it misses the strongest structural improvement |
| 2026-04-30 | Canonical seed updates are part of the change, but only in the seed files that actually define reusable role and routing behavior | The requested outcome is framework-level reuse across seeded projects, not a Wavefoundry-only local improvement | Keep the change local-only; rejected because it would not propagate to target repos |
| 2026-04-30 | Model specialists as universal, archetype-scoped, or repo-local rather than as one flat specialist tier | The framework must serve heterogeneous target repos without seeding every specialist everywhere | Treat all specialists as equally global; rejected because it would overfit some repos and underfit others |
| 2026-04-30 | Expand the initial candidate set beyond MCP/index/workflow specialists to include web, mobile, UX, architecture, infrastructure, and reliability roles | The shared framework is intended for Swift/macOS, React/AWS, Java, Spring, and AI/agent repos, not only Wavefoundry-like repos | Keep the shortlist narrow and let each project invent missing specialists locally; rejected because it weakens the value of the shared framework |


## Risks


| Risk                                                                 | Mitigation                                                                                                  |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Specialist additions duplicate existing roles and make routing fuzzy  | Require explicit adopt / adapt / defer / reject classification and update routing docs in the same change   |
| The seed catalog grows into an unbounded prompt library              | Split specialists into universal, archetype-scoped, and repo-local classes and require evidence-based gating |
| New specialist docs imply native platform wrappers that do not exist | Update `docs/agents/platform-mapping.md` with accurate status and avoid overclaiming generated support       |
| Existing role docs remain stale after specialist additions           | Treat role-enhancement updates as part of the same change, not a follow-on                                  |
| High-level overview docs drift from detailed agent docs              | Update overview docs only after the supported specialist set is finalized and cross-check before closure     |
| Seed-pack changes accidentally encode Wavefoundry-local assumptions as framework-wide rules | Keep seed edits restricted to generic reusable structure; leave repo-specific assignments and evidence in local docs |
| Local docs and seeds diverge during implementation                   | Settle the local target structure first, then mirror the generic reusable rule into `seed-050` / `seed-100` / `seed-150` in the same wave |
| Known target stacks such as Swift/macOS or Java/Spring are not adequately covered by the imported external specialist set | Allow framework-native specialists where the external catalog is too weak or too vendor-specific for the framework's needs |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
