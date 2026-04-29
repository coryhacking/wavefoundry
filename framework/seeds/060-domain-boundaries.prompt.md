# 060 - Domain Boundaries

Intent:

- Document architecture boundaries, integration points, hotspots, trust and data seams, and safe coordination surfaces so wave planning, **architecture-reviewer** lanes, and implementation prompts share the same mental model.

Inputs (consume before writing):

- `docs/repo-index.md` and `docs/repo-profile.json` from `seed-030`
- Top-level manifests: package/project files, workspace layout, CI workflow names, primary build or run entrypoints
- Existing canonical architecture docs if present — **merge and refresh** rather than duplicating or wiping repo-grown detail

Tasks:

1. **System context** — Identify actors (human, OS, browser, other services), major deployable units (apps, daemons, libraries, workers), and where authoritative state lives. Distinguish **development-time** vs **runtime** topology when they differ.

2. **Domain and module map** — Name cohesive domains (by folder, package, or service), their **owned responsibilities**, and **inbound/outbound dependencies**. Call out **dependency direction rules** (who may import whom) even when enforcement is informal.

3. **Integration and contract surfaces** — List machine-relevant boundaries: HTTP/IPC APIs, CLI contracts, file formats, env vars, feature flags, DB schemas, message buses, push notifications, platform SDKs, cloud service SDKs, vendor APIs, etc. For each, note **stability** (stable / evolving / internal) and **owner**.

4. **Trust, privilege, and data sensitivity** — Map trust boundaries (localhost-only vs network, user data, secrets, crypto, entitlements). Tie to `docs/architecture/threat-model.md` and security posture without duplicating full threat analysis in every file.

5. **Concurrency, lifecycle, and failure domains** — Describe processes/threads/async models, startup/shutdown ordering where it matters, and what can fail independently. Identify **hotspots** (shared mutable state, global singletons, caches, schedulers) and **serialization points** (must not be edited in parallel without coordination).

6. **Build, test, and release seams** — Note how modules enter artifacts (bundles, containers, fat binaries), signing/notarization edges, and which directories affect shipped vs dev-only behavior. Helps **release-reviewer** and wave partitioning for build changes.

7. **Wave-planning hooks** — Explicitly list **safe-for-concurrent-work** clusters (isolated subtrees or features) vs **single-lane** areas. Feed `docs/contributing/agent-routing-concurrency.md` and readiness prompts with real names from the repo.

8. **Cross-link the hub** — Keep `docs/ARCHITECTURE.md` as a short **index**: scope, table of child docs with purpose/status (including **data-and-control-flow**, **testing-architecture**, and **decisions/**), **update triggers**, and links to `docs/repo-index.md`, `docs/specs/index.md`, and `docs/architecture/decisions/README.md`.

9. **Unknowns and verification** — Maintain an **Open questions / weak evidence** subsection (in `current-state` or `domain-map`) listing boundaries that could not be verified from inventory; set `Verification method` metadata on draft docs where the repo uses it. Mirror or link material **watchlist** items in `docs/missing-docs.md` when they represent doc debt, not transient chat notes.

10. **Boundary behavioral invariants** — For each major integration edge from task 3, capture **runtime semantics** that implementers and **architecture-reviewer** must not accidentally violate: message/event ordering expectations, **idempotency** or retry behavior, **consistency** (strong vs eventual vs best-effort), error propagation, and **ownership of reconciliation** after partial failure. Prefer a **Boundary invariants** subsection in `docs/architecture/layering-rules.md` (table keyed by edge) or one short paragraph per edge in `docs/architecture/data-and-control-flow.md` when the invariant is inseparable from a flow narrative. Label **inferred** vs **verified** (spec or code citation).

11. **Data and control flow** — Create or refresh `docs/architecture/data-and-control-flow.md`: **primary control paths** (user action, timer, IPC, job), **where authoritative state is read and written**, and **which domain owns each mutation**. Prefer named paths that reuse **domain-map** identifiers; optional Mermaid or numbered step lists; avoid duplicating full spec text — link `docs/specs/*.md` where behavior is contractual.

12. **Testing architecture** — Create or refresh `docs/architecture/testing-architecture.md`: unit vs integration vs E2E (or repo-appropriate tiers), **which module or package owns which test targets**, where doubles/mocks are allowed vs forbidden, CI entrypoints, and **minimum verification bar** for cross-module changes. Use the same module names as `domain-map.md` so **qa-reviewer** and **release-reviewer** align with architecture vocabulary.

13. **ADR template** — Ensure `docs/architecture/decisions/template.md` exists (seeded by `seed-040`) and link it from `docs/architecture/decisions/README.md`; new decision records should copy the template and follow the naming rules in README.

Required target-repo outputs (seed or refresh from evidence; omit only when the repository truly has no separable architecture — e.g. single-file script — and say so in `docs/ARCHITECTURE.md`):

- `docs/ARCHITECTURE.md` — Canonical hub (see task 8)
- `docs/architecture/current-state.md` — Runtime topology, major flows, risks, and **how this doc was verified** (sources: modules inspected, scripts read)
- `docs/architecture/domain-map.md` — Named domains, responsibilities, and **interaction edges** (table or diagram in prose)
- `docs/architecture/layering-rules.md` — Allowed and forbidden dependencies; how violations are detected (lint, review, convention)
- `docs/architecture/cross-cutting-concerns.md` — Config, logging, observability, reliability hooks, shared utilities — **where they live** and **which layers may use them**
- `docs/architecture/data-and-control-flow.md` — Control paths, state ownership, mutations (task 11)
- `docs/architecture/testing-architecture.md` — Test tiers, target ownership, doubles policy, CI hooks (task 12)
- `docs/architecture/decisions/README.md` — Decision-record convention (may already exist from `seed-040`)
- `docs/architecture/decisions/template.md` — Copy-paste skeleton for new `DEC-*` files (task 13)
- `docs/architecture/threat-model.md` and `docs/architecture/performance-budget.md` — Baseline adaptive artifacts (even when posture is low-risk); reference boundaries defined above

Alignment with review and roles:

- Content in these files should give **architecture-reviewer** and **planner** concrete anchors: module roots, boundary rules, and integration surfaces to cite in readiness and review checkpoints.
- When product code spans multiple top-level dirs, ensure `docs/repo-index.md` **top-level modules** stay consistent with **domain-map** naming.

Routing guidance for later prompts:

- **Implement / plan prompts** — Point implementers at `docs/ARCHITECTURE.md` and the relevant child doc before cross-cutting edits.
- **190-finalize-feature** / promotion — Architectural decisions discovered during a change should update `docs/ARCHITECTURE.md` or `docs/architecture/decisions/` and, when boundaries move, **domain-map** / **layering-rules**; when flows or state ownership change, **data-and-control-flow**; when test topology or CI gates change, **testing-architecture**; when integration invariants change, **layering-rules** (boundary invariants) and linked specs.

Guardrails:

- Do not overstate boundaries when evidence is weak — label inference vs verified fact.
- Be explicit about what must stay **serialized** across agents or workstreams.
- Avoid copy-pasting large code blocks; use paths, module names, and short interface summaries.
- Do not contradict `docs/specs/*.md` contracts; architecture docs **interpret** layout and runtime — specs remain behavior authority where they exist.
- Preserve repo-specific depth already in canonical architecture docs when refreshing; **extend and reconcile**, do not replace with generic pack boilerplate.
