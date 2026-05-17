# `code_outline` should surface SQL routines in PL/pgSQL files

Change ID: `12p2m-bug sql-outline-plpgsql-fallback`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-16
Wave: 12nbr code-intelligence-expansion

## Rationale

`code_outline` still returns `symbols: []` for SQL files that use PostgreSQL procedural blocks, even though the files clearly contain top-level routines. The current SQL path depends on tree-sitter node types such as `create_function`, but `tree-sitter-sql` commonly emits an `ERROR` node for `CREATE OR REPLACE FUNCTION ... LANGUAGE plpgsql AS $$ ... $$` bodies. That leaves agents with an empty outline for the exact SQL files where a structural summary is most valuable.

The TypeScript half of the original code-outline fix is correct and should stay. This follow-up addresses the remaining SQL gap by adding a practical fallback for PL/pgSQL-style routine definitions.

## Requirements

1. `code_outline` must return meaningful symbols for SQL files that declare PostgreSQL functions or procedures with `LANGUAGE plpgsql` bodies, even when the tree-sitter parse tree does not expose a usable `create_function` node.
2. The SQL fallback must be conservative: it should only identify top-level routine headers such as `CREATE FUNCTION`, `CREATE OR REPLACE FUNCTION`, `CREATE PROCEDURE`, and `CREATE OR REPLACE PROCEDURE`.
3. The fallback must preserve existing behavior for plain SQL files, including files with no routines and files already parsed successfully by tree-sitter.
4. The fallback must not fabricate symbols from comments or arbitrary SQL text.
5. The implementation should stay localized to `code_outline` / SQL outline extraction rather than broadening unrelated symbol-navigation paths unless those paths are explicitly reused by the solution.

## Scope

**Problem statement:** SQL outline extraction is still empty for PL/pgSQL routine files because the parser does not surface the routine node the walker expects.

**In scope:**

- `code_outline` SQL handling in `server.py`
- A fallback path for PL/pgSQL routine headers when tree-sitter returns no usable SQL symbols
- Regression tests covering both the PL/pgSQL case and plain SQL files with no routines

**Out of scope:**

- Replacing tree-sitter-sql entirely
- Changing chunking or search behavior
- Broader SQL language support beyond routine discovery for outline purposes

## Acceptance Criteria

- AC-1: `code_outline` on a `.sql` file containing `CREATE OR REPLACE FUNCTION ... LANGUAGE plpgsql AS $$ ... $$` returns at least one function symbol with the routine name and a sensible line span.
- AC-2: `code_outline` on a `.sql` file containing `CREATE OR REPLACE PROCEDURE ... LANGUAGE plpgsql AS $$ ... $$` returns at least one routine symbol with the routine name and a sensible line span.
- AC-3: `code_outline` on a plain SQL file with no routine definitions still returns `symbols: []`.
- AC-4: Existing `code_outline` behavior for TypeScript and non-SQL files remains unchanged.

## Required Review Lanes

- `qa-reviewer` — required (bug fix; preserves the code-outline contract for SQL routine files)
- `code-reviewer` — required (implementation changes SQL outline extraction logic)

## Tasks

- Verify the current SQL parse tree shape for PL/pgSQL routine files and confirm the tree-sitter path still produces no usable symbol node.
- Add a conservative SQL fallback that detects routine headers and extracts the routine name plus start/end lines.
- Add regression tests for PL/pgSQL function and procedure files, plus a no-routine SQL file.
- Re-run the framework test suite and document the result.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| SQL fallback detection | Engineering | — | Header-based routine discovery for PL/pgSQL bodies |
| Regression tests | Engineering | SQL fallback detection | Covers function, procedure, and no-routine cases |

## Serialization Points

- The SQL fallback logic and its tests should land together so the outline contract does not briefly regress to empty SQL output in the middle of the wave.

## Affected Architecture Docs

N/A. This is a localized `code_outline` behavior fix.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Function outline is the primary user-facing failure mode |
| AC-2 | required | Procedures are the same parser gap class as functions |
| AC-3 | required | Prevents false positives on routine-free SQL |
| AC-4 | required | Ensures the follow-up does not disturb existing language support |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-16 | Observed that SQL PL/pgSQL files still return empty `symbols` even though tree-sitter parses the file and `code_outline` reports success. Direct probe showed the parse tree collapses the routine body into `ERROR` nodes, so the current `create_function`-only extraction path never fires. | Local inspection of `server.py` and parser output |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-16 | Add a conservative SQL fallback instead of broadening the tree-sitter node allowlist | The parser does not reliably surface routine nodes for PL/pgSQL bodies, so a header-based fallback is the only practical way to recover useful outlines without changing grammars | Replace `tree-sitter-sql` (too broad), or leave the gap open (not acceptable) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Header-based matching could overmatch nested or commented text | Limit the fallback to top-level routine declaration lines and require a `CREATE ... FUNCTION|PROCEDURE` header |
| Fallback might duplicate symbols if tree-sitter starts working better in some files | Only use fallback when the tree-sitter path yields no usable SQL symbols |
| Routine line spans may be approximate in PL/pgSQL | Keep the fallback conservative and document the span semantics in tests |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
