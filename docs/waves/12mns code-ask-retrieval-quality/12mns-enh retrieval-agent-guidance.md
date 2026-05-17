# Retrieval Agent Guidance: Layer Recognition, Call Chain, and Definition File Patterns

Change ID: `12mns-enh retrieval-agent-guidance`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-05-15
Wave: `12mns code-ask-retrieval-quality`

## Rationale

Field testing identified four agent-behavior problems that the retrieval system cannot fix on its own and that require explicit guidance in agent role docs:

1. **Layer recognition:** Scaffolding and wiring citations (CDK constructs, Terraform modules, Spring config beans, Express route declarations) looked like plausible evidence and were synthesized from directly, without recognizing that they confirm a connection exists but do not answer an explanatory question.
2. **Call chain obligation:** Multi-hop answers (entry point → handler → service → data layer) require tracing N levels deep; nothing in current instructions obligates this.
3. **Confidence misinterpretation:** `confidence: high` was treated as "good answer" when it means "2+ citations returned" — high confidence with wrong-layer citations still requires follow-up.
4. **Definition file follow-up gap:** Definitions for database schema objects (tables, procs, indexes, constraints) and schema languages (GraphQL types, protobuf messages) will almost never surface from vector search regardless of how the application code references them — whether via string-literal proc calls, direct SQL queries, DML statements, or ORM method calls. Agents need an explicit pattern for finding these definitions and reading them fully (columns, types, constraints, indexes) before synthesizing.
5. **Architect agent gap:** The architecture reviewer has no guidance for requiring schema verification when data-layer changes are reviewed. Repository or service layer changes can alter data access patterns without the reviewer knowing whether the underlying schema (table structure, constraints, indexes) supports the change.

These are agent-side mitigations for retrieval gaps that complement the technical fixes in `12mns-enh question-type-aware-retrieval` and `12mns-enh sql-candidate-window-boosting`.

## Requirements

1. `docs/agents/code-insight-agent.md` must add a **Layer Recognition** heuristic in the `## Retrieval Loop` section: for explanatory questions, citations from scaffolding/wiring/routing path segments (e.g. constructs, stacks, modules, config, beans, routes — the specific names vary by framework) are structural evidence only — they confirm a connection exists but do not answer how the logic works; always follow up with a read of the actual handler, service, or repository layer before synthesizing. The heuristic must name common framework examples so the pattern is recognizable across project types.
2. `docs/agents/code-insight-agent.md` must add a **Call Chain Obligation** heuristic in the `## Retrieval Loop` section: for questions about sequences, flows, or provisioning ("how does X work", "what is the flow for", "how is X created/provisioned"), identify the entry point from citations, then read at least 2–3 levels of the call chain (handler → called fn → called fn) before synthesizing; stop when hitting a leaf (DB call, external SDK call, third-party service boundary).
3. `docs/agents/code-insight-agent.md` must update the `## Assumption Discipline` confidence levels to clarify that `confidence` is a retrieval signal: "High — 2+ citations returned; not an answer-quality guarantee — evaluate citations by path and content layer, not score alone."
4. `docs/agents/code-insight-agent.md` must add a **Definition File Follow-Up** pattern in the `## Retrieval Loop` section: when citations include application code files that interact with a database in any form — stored procedure calls (string literals, EXEC statements, or ORM method calls), direct queries (SELECT/INSERT/UPDATE/DELETE referencing table names), DML operations, or ORM model references — always follow up with `code_keyword` for the referenced table name, proc name, or schema object. Once the definition file is found, read it fully: columns, types, constraints (PRIMARY KEY, UNIQUE, FOREIGN KEY, CHECK), and indexes before synthesizing. SQL definitions are typically in migration or schema directories; ORM models in model files. For non-SQL schema languages (GraphQL types, protobuf messages, OpenAPI operation IDs referenced from application code), apply the same pattern: keyword-search the referenced identifier and read the definition before synthesizing.
5. `AGENTS.md` must add a concise note to the `code_ask` shortcut description covering: (a) `confidence` is a retrieval signal not an answer-quality signal — evaluate citations by path and layer; (b) for explanatory questions, scaffolding-layer citations (constructs/stacks/routes/config/modules) confirm wiring only — follow up with the handler or service layer.
6. `docs/agents/architecture-reviewer.md` must add a **Data Layer Verification** note to the `## Review Dimensions` section: when reviewing changes to repository, service, or data-access layers that interact with a database, require evidence that the underlying schema has been verified — table columns, types, constraints, and indexes must be consistent with the claimed behavior change; flag changes that add or modify data access patterns (new query, new proc call, new ORM method, modified DML) without a corresponding schema verification; the CIA call-chain trace to the data layer and a read of the full schema definition are the standard evidence sources.

## Scope

**Problem statement:** Agent instructions do not address layer recognition for infrastructure citations, call-chain depth obligations, confidence signal interpretation, full database schema verification (all reference forms, not just string-literal proc calls), or architecture reviewer requirements for data-layer change evidence — all of which caused incorrect synthesis or missed review gaps in field testing.

**In scope:**

- `docs/agents/code-insight-agent.md`: Layer Recognition heuristic, Call Chain Obligation heuristic, confidence level clarification, Definition File Follow-Up pattern (all SQL reference forms + schema depth)
- `AGENTS.md`: two-line addition to `code_ask` shortcut description
- `docs/agents/architecture-reviewer.md`: Data Layer Verification note in `## Review Dimensions`

**Out of scope:**

- Changes to other agent role docs (code-reviewer, planner, implementer, etc.)
- Changes to MCP tool descriptions (handled separately in `12mc3` cleanup)
- Enforcing call-chain depth via tooling

## Acceptance Criteria

- AC-1: `code-insight-agent.md` contains a Layer Recognition heuristic that names the scaffolding-layer concept with framework-specific examples (CDK, Terraform, Spring, Express/NestJS) and specifies the required follow-up action.
- AC-2: `code-insight-agent.md` contains a Call Chain Obligation heuristic that specifies minimum depth (2–3 levels) and a stop condition (DB call / external SDK / third-party service boundary).
- AC-3: `code-insight-agent.md` confidence levels describe `confidence` as a retrieval signal, not an answer-quality signal.
- AC-4: `code-insight-agent.md` contains a Definition File Follow-Up pattern that covers all forms of SQL database interaction (proc calls, direct queries, DML, ORM references) and non-SQL schema languages (GraphQL types, protobuf messages) as the same cross-reference pattern; specifies `code_keyword` on the referenced identifier; and requires reading the full schema definition (columns, types, constraints, indexes) before synthesizing.
- AC-5: `AGENTS.md` `code_ask` entry includes the confidence-as-retrieval-signal note and the scaffolding-layer citation note.
- AC-6: `docs-lint` passes after all edits.
- AC-7: `architecture-reviewer.md` `## Review Dimensions` includes a Data Layer Verification note requiring schema evidence (columns, constraints, indexes) for repository/service layer changes that interact with a database, and names the CIA call-chain trace as the standard evidence source.

## Tasks

- [ ] Add **Layer Recognition** heuristic to `## Retrieval Loop` in `docs/agents/code-insight-agent.md` — framework-agnostic with named examples (CDK constructs/stacks, Terraform modules/resources, Spring config/beans, Express/NestJS routes)
- [ ] Add **Call Chain Obligation** heuristic to `## Retrieval Loop` in `docs/agents/code-insight-agent.md`
- [ ] Update confidence level descriptions in `## Assumption Discipline` in `docs/agents/code-insight-agent.md`
- [ ] Add **Definition File Follow-Up** pattern to `## Retrieval Loop` in `docs/agents/code-insight-agent.md` — all SQL reference forms (proc calls, direct queries, DML, ORM), schema depth (columns, types, constraints, indexes), and non-SQL schema languages (GraphQL, protobuf) as the same cross-reference pattern
- [ ] Add confidence + scaffolding-layer note to `code_ask` entry in `AGENTS.md`
- [ ] Add **Data Layer Verification** note to `## Review Dimensions` in `docs/agents/architecture-reviewer.md`
- [ ] Run `docs-lint` and confirm clean

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| cia-doc | implementer | — | `code-insight-agent.md` all four additions including expanded Definition File Follow-Up |
| agents-md | implementer | — | `AGENTS.md` code_ask entry; independent of cia-doc |
| architect-doc | implementer | — | `architecture-reviewer.md` Data Layer Verification note; independent |
| lint | implementer | cia-doc, agents-md, architect-doc | Run docs-lint; fix failures |

## Serialization Points

- No `framework_edit_allowed` gate required — `docs/agents/` and `AGENTS.md` are project docs, not framework files.
- `seed_edit_allowed` gate not required — no seed edits.

## Affected Architecture Docs

N/A — agent guidance docs only, no architecture boundary changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Layer Recognition is the primary fix for scaffolding-citation synthesis errors |
| AC-2 | required  | Call Chain Obligation is the primary fix for shallow multi-hop answers |
| AC-3 | required  | Confidence reinterpretation prevents systematic misreading of the retrieval signal |
| AC-4 | required  | Definition File Follow-Up covering all SQL reference forms and schema depth is the expanded core deliverable |
| AC-5 | important | AGENTS.md note provides summary signal to non-CIA agents; CIA doc is authoritative, AGENTS.md is derivative |
| AC-6 | required  | docs-lint must pass — wave cannot close with lint failures |
| AC-7 | required  | Architect agent Data Layer Verification is in-scope new addition — required for the change to be complete |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Change scoped from four-problem field feedback | Layer synthesis without layer check; call chain not traced; confidence misread; SQL procs not found |
| 2026-05-15 | Generalized Problems 1 and 4 to framework-agnostic patterns | Layer Recognition: extended from CDK-specific to scaffolding/wiring concept with multi-framework examples; Definition File Follow-Up: generalized from SQL-only to string-literal cross-reference pattern covering GraphQL, protobuf |
| 2026-05-15 | Expanded Definition File Follow-Up to all SQL reference forms; added schema depth requirement; added architect agent Data Layer Verification | Problem 4 narrowed too tightly to string-literal proc calls — direct queries, DML, and ORM method calls have the same schema-visibility gap; schema depth (columns, constraints, indexes) added so agents read the full definition, not just find the file; architect agent added as Problem 5 |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Guidance in role doc + AGENTS.md, not MCP tool description | Role doc provides space for detailed heuristics; AGENTS.md gives any agent the summary signal | MCP tool description only — too terse for call-chain and SQL patterns |
| 2026-05-14 | Call chain stop condition at DB/SDK/external service call | Avoids unbounded traversal; DB and SDK calls are always leaves in the business logic sense | Fixed depth of 3 — misses shallow chains and over-constrains deep ones |
| 2026-05-15 | Definition File Follow-Up covers all SQL reference forms, not just string literals | String-literal proc calls are one pattern; direct SELECT/INSERT/UPDATE/DELETE and ORM method calls have identical schema-visibility gap in vector search; narrowing to string literals would miss the majority of real query patterns | String-literal only — simpler trigger, misses most data-access patterns |
| 2026-05-15 | Schema depth explicitly required (columns, constraints, indexes) | Finding the definition file is not sufficient — answering schema-sensitive questions requires reading column types, constraint semantics, and index coverage; without this the agent may stop at file identification and synthesize from the file name alone | File identification only — agent may infer schema from path/name without reading content |
| 2026-05-15 | Added architect agent Data Layer Verification | Architecture reviewers approve repository/service layer changes without a schema check — the underlying table structure is invisible to them unless explicitly required | CIA-only — architect reviewer never sees schema evidence without a mandate |

## Risks

| Risk | Mitigation |
|------|------------|
| Scaffolding-layer heuristic over-fires in a project where business logic lives in a `constructs/` path | Heuristic is advisory and framework-specific examples make the pattern auditable; agents apply judgment, not a hard rule |
| Definition file follow-up adds unnecessary tool calls on non-database citations | Pattern triggers on any data-access citation (queries, DML, ORM calls) — broader than before; risk is a keyword search on a table name that returns many results; `DEFINITION_BOOST_RULES` in `12mns-enh sql-candidate-window-boosting` provides the vocabulary gate at retrieval time; agent guidance is the post-retrieval layer |
| Architect agent Data Layer Verification blocks review on changes that have no schema impact | Note is conditional — applies when the change touches data-access patterns; reviewers apply judgment; the note names the evidence source (CIA call-chain trace) rather than mandating a fixed checklist |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
