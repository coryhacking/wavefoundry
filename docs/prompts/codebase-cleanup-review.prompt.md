# Codebase Cleanup Review

Owner: Engineering
Status: active
Last verified: 2026-06-16

**Shortcut phrases:** `Codebase cleanup review` · `Dead code review` · `Maintainability sweep`

Run the **code-reviewer** in its whole-codebase **Maintainability & Dead-Code** mode: a senior-engineer pass that finds dead code, duplication, over-complexity, abandoned files, redundant work, and other technical debt — and recommends what to **simplify** or **remove**. **Aggressive but safe**: remove anything that provides no value, while never deleting something load-bearing.

> **Recommend-only.** This review never deletes; it produces a findings list to feed a normal reviewed change/wave. Run it on demand, and ideally on the same cadence as the **Framework Config Review** (at a major/minor upgrade).

---

## What it finds

Dead code (unused functions, files, components, routes, APIs, variables, imports, dependencies); duplicate logic to consolidate; unused UI components; overly complex implementations to simplify; legacy / no-longer-needed code; redundant expensive operations (repeated reads/fetches or recomputation); files disconnected from the application; general technical-debt reduction.

## How it detects (graph, not grep)

With the MCP attached it uses the index, which is far more reliable than scanning:

- Dead symbols → `code_references` + `code_callhierarchy(direction="incoming")`.
- Abandoned / disconnected areas → `code_graph_community` + the generated codebase map (`docs/references/codebase-map.md`).
- Blast radius before recommending removal → `code_impact` / `code_callgraph`.

## Aggressive but SAFE

Zero static references does **not** mean dead. Before recommending a deletion, the review rules out the surfaces invisible to static analysis: framework registration / decorators / DI, reflection, plugin / entry-point / hook registration, callbacks, symbols referenced by string or serialized name, test fixtures, and the public API. Empty graph results are corroborated with `code_references` / `code_keyword`, and heuristic (EXTRACTED) graph edges are never trusted alone.

## Output

For each finding: **target** (file + symbol/line) · **verdict** (`keep` / `simplify` / `remove`) · **why** · **impact** · **risks** · **cleanup plan**. Removals land through a reviewed wave.

## Relationship to Other Commands

| Command | When to use |
|---|---|
| **Codebase cleanup review** | Prune **code** — dead code, duplication, complexity, debt |
| **Framework config review** | Prune the **agent-operating surface** — seeds, prompts, config, docs |
| **Council review** | Adversarial + council pass on a specific artifact |
