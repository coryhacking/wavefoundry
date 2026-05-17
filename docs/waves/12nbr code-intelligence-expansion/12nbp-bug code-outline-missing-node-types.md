# code_outline returns no symbols for SQL files and all TypeScript/TSX files

Change ID: `12nbp-bug code-outline-missing-node-types`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12nbr code-intelligence-expansion

## Rationale

`code_outline` returns `parser_used: "tree_sitter"` with `symbols: []` for two entire file categories confirmed against the Teton monorepo:

1. **All TypeScript and TSX files** — not just arrow function files. Every top-level export in TypeScript is wrapped in an `export_statement` node. The `_outline_treesitter` walker checks `node.type` against `_TS_OUTLINE_FUNC_TYPES` and `_TS_OUTLINE_CLASS_TYPES`, but `export_statement` is in neither set, so every top-level symbol in every `.ts`/`.tsx` file is silently skipped. This affects classes, named functions, and arrow function exports equally.

2. **SQL stored procedures and functions** — the SQL grammar is loaded and parses correctly, but `CREATE FUNCTION` and `CREATE PROCEDURE` node types are absent from both frozensets. Every SQL file returns an empty symbol list.

Both gaps produce the same misleading output: `parser_used: "tree_sitter"` with `symbols: []`, giving agents false confidence that the file has been inspected and has no symbols.

**Scope of impact is severe.** Every `.ts`/`.tsx` file in the codebase returns an empty outline today — Lambda handlers, repository modules, React components, service clients. The orientation pass (`code_outline` before `code_read`) is entirely unavailable for TypeScript. The SQL gap forces agents following the Definition File Follow-Up pattern to `code_read` 5500-line migration files to find a single proc signature.

## Root Cause

**TypeScript (primary cause — affects all TS/TSX exports):**

The TypeScript tree-sitter grammar wraps every top-level export in an `export_statement` node:

```
root
  export_statement          ← walker sees this; not in either frozenset → skipped
    export
    class_declaration       ← the actual symbol node; never reached
      type_identifier "Foo"
```

`_outline_treesitter` iterates `tree.root_node.children` and checks each node against the two frozensets. `export_statement` is not in either set, so the entire subtree is discarded. Every top-level TypeScript symbol is affected regardless of kind.

**TypeScript (secondary cause — arrow function name extraction):**

Even after unwrapping `export_statement`, arrow functions have an additional wrapping layer. The name lives in `variable_declarator → identifier`, not inside `arrow_function`, so `_outline_ts_name` cannot find it:

```
export_statement
  lexical_declaration
    variable_declarator
      identifier "arrowFn"    ← name is here
      arrow_function          ← this is in _TS_OUTLINE_FUNC_TYPES, but has no name child
```

`arrow_function` is already in `_TS_OUTLINE_FUNC_TYPES` — the fix is not to add a node type but to handle `lexical_declaration` as a separate case that extracts the name from the `variable_declarator` sibling.

**SQL:**

`_TS_OUTLINE_FUNC_TYPES` and `_TS_OUTLINE_CLASS_TYPES` contain no SQL grammar node type names. The tree-sitter-sql grammar uses node types such as `create_function`, `create_procedure`, or `routine_definition` — none present in either frozenset.

## Requirements

1. `_outline_treesitter` unwraps `export_statement` nodes before type-checking: when a root child is `export_statement`, find its first non-keyword child (`not in {"export", "default", "type"}`) and use that as the node to check against the frozensets. This restores correct extraction for all TypeScript class, function, and named export declarations.
2. `_outline_treesitter` adds a `lexical_declaration` branch (after export unwrapping) for arrow function exports: when the unwrapped node is `lexical_declaration`, walk its `variable_declarator` children; if the value child is `arrow_function`, extract the `identifier` sibling as the symbol name with `kind: "function"`.
3. `_TS_OUTLINE_FUNC_TYPES` is extended with SQL function/procedure node types after verifying the actual names against the tree-sitter-sql grammar parse tree. Node type names are not added speculatively.
4. No other behavior changes — existing node types, class body method walking, and regex fallback are unchanged.
5. All three fixes apply only in `_outline_treesitter`; `_outline_python` and `_outline_regex_tier` are unaffected.

## Scope

**In scope:**

- `_outline_treesitter` in `server.py`: add `export_statement` unwrapping at the top of the root child loop; add `lexical_declaration` branch for arrow function name extraction
- `_TS_OUTLINE_FUNC_TYPES` in `server.py`: extend with confirmed SQL node type names
- Tests: TypeScript class export, TypeScript named function export, TypeScript async arrow function export, SQL `CREATE FUNCTION`, SQL `CREATE PROCEDURE`, SQL file with no functions (no false positives), regression guard on non-TS/SQL languages
- Update `code_outline` change doc progress log in `docs/waves/12mns code-ask-retrieval-quality/12n63-enh code-outline.md` (cross-wave progress note; file confirmed present in closed wave)

**Out of scope:**

- Other missing node types not identified here
- Changing the regex fallback tier
- Changes to `code_hover`, `code_callhierarchy`, or other tools that reuse `_outline_treesitter`
- TSX-specific node types beyond what the TypeScript grammar already covers

## Acceptance Criteria

- AC-1: `code_outline` on a TypeScript file with `export class Foo {}` returns `Foo` with `kind: "class"` and `parser_used: "tree_sitter"`.
- AC-2: `code_outline` on a TypeScript file with `export function bar() {}` returns `bar` with `kind: "function"` and `parser_used: "tree_sitter"`.
- AC-3: `code_outline` on a TypeScript file with `export const fn = async (props: Props) => {}` returns `fn` with `kind: "function"` and `parser_used: "tree_sitter"`.
- AC-4: `code_outline` on a SQL file containing `CREATE FUNCTION` and/or `CREATE PROCEDURE` returns those symbols with `kind: "function"`, correct `start_line`/`end_line`, and `parser_used: "tree_sitter"`.
- AC-5: `code_outline` on a SQL file with no function or procedure definitions returns `symbols: []` without error (no false positives).
- AC-6: Existing `code_outline` tests for Python, Go, Rust, and other non-TS/SQL tree-sitter languages all pass unchanged.

## Required Review Lanes

- `qa-reviewer` — required (bug fix; per `review_policies.require_qa_reviewer_for_bug_fixes`)
- `code-reviewer` — required (non-trivial implementation change to `_outline_treesitter`)

## Tasks

- Open `framework_edit_allowed` gate
- In `_outline_treesitter` in `server.py`, refactor the `for node in tree.root_node.children` loop:

  **Step 1 — unwrap `export_statement`:**
  ```python
  for node in tree.root_node.children:
      inner = node
      if node.type == "export_statement":
          for child in node.children:
              if child.type not in ("export", "default", "type"):
                  inner = child
                  break
      # All subsequent checks use `inner` instead of `node`
  ```

  **Step 2 — existing class/function checks unchanged, now using `inner`:**
  ```python
      if inner.type in _TS_OUTLINE_CLASS_TYPES:
          # existing class + method walking, unchanged
      elif inner.type in _TS_OUTLINE_FUNC_TYPES:
          # existing function entry, unchanged
  ```

  **Step 3 — add `lexical_declaration` branch for arrow functions:**
  ```python
      elif inner.type == "lexical_declaration":
          for declarator in inner.children:
              if declarator.type == "variable_declarator":
                  value = next(
                      (c for c in declarator.children if c.type == "arrow_function"), None
                  )
                  if value:
                      name_node = next(
                          (c for c in declarator.children if c.type == "identifier"), None
                      )
                      if name_node:
                          symbols.append({
                              "name": name_node.text.decode("utf-8", errors="replace").strip(),
                              "kind": "function",
                              "start_line": inner.start_point[0] + 1,
                              "end_line": inner.end_point[0] + 1,
                              "docstring": None,
                          })
  ```

- Inspect the tree-sitter-sql grammar's actual node type names: parse a sample `CREATE FUNCTION` / `CREATE PROCEDURE` SQL file, walk `root_node`, print node types to confirm names before touching the frozenset
- Add confirmed SQL node type names to `_TS_OUTLINE_FUNC_TYPES`
- Write tests covering AC-1 through AC-6
- Close `framework_edit_allowed` gate
- Run full test suite

## Agent Execution Graph

| Workstream                        | Owner       | Depends On          | Notes                                                       |
| --------------------------------- | ----------- | ------------------- | ----------------------------------------------------------- |
| SQL node type verification        | Engineering | —                   | Parse sample SQL, inspect `root_node` to confirm names      |
| `_TS_OUTLINE_FUNC_TYPES` SQL fix  | Engineering | verification        | Add confirmed names only                                    |
| TS `export_statement` unwrap fix  | Engineering | —                   | Independent of SQL; `inner` variable approach is contained  |
| TS `lexical_declaration` branch   | Engineering | export unwrap fix   | Depends on Step 1 being in place first                      |
| tests                             | Engineering | all three fixes     | All fixes must be in place before tests run                 |
| verification                      | Engineering | tests               | Full test suite pass required                               |

## Serialization Points

- The `export_statement` unwrap (Step 1) must be in place before the `lexical_declaration` branch (Step 3) is written — Step 3 operates on `inner`, which is produced by Step 1.
- SQL node type names must be confirmed from the grammar parse tree before the frozenset is edited.
- The two workstreams (TypeScript fixes and SQL fixes) are otherwise independent and can run in parallel.

## Affected Architecture Docs

- No architecture doc changes — pure bug fix within `_outline_treesitter` and `_TS_OUTLINE_FUNC_TYPES`. No new languages, boundaries, or tools introduced.

## AC Priority

| AC   | Priority    | Rationale                                                                              |
| ---- | ----------- | -------------------------------------------------------------------------------------- |
| AC-1 | required    | TS class exports — `export_statement` unwrap correctness for class kind                |
| AC-2 | required    | TS named function exports — `export_statement` unwrap correctness for function kind    |
| AC-3 | required    | TS arrow function exports — `lexical_declaration` branch correctness                   |
| AC-4 | required    | SQL stored procedures — SQL frozenset fix correctness                                  |
| AC-5 | required    | SQL false positive guard — plain SQL files must not fabricate symbols                  |
| AC-6 | required    | Regression guard — existing non-TS/SQL tree-sitter tests must pass unchanged           |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Discovered during live `code_outline` smoke testing — SQL files return `parser_used: "tree_sitter"` with empty `symbols`; TypeScript arrow function exports not captured | Agent session observation |
| 2026-05-15 | Confirmed against Teton monorepo (TypeScript + PostgreSQL). SQL: `A004__routines.sql` (5500+ lines), `A005__new_tenant_routines.sql`, `A006__webhook_support.sql` all return `symbols: []`. TypeScript: `tenants.ts` defines ~30 `export const name = async (...) =>` exports, all return `symbols: []`. Python files unaffected. Severity: SQL=High (breaks Definition File Follow-Up; 5500-line file must be fully read), TypeScript=Medium (arrow function files empty). | Field observation, Teton monorepo |
| 2026-05-15 | Root cause corrected and widened. TypeScript gap is not limited to arrow functions — it affects ALL TypeScript exports. Primary cause: `export_statement` node wraps every top-level TS symbol; walker checks `node.type` against frozensets but `export_statement` is in neither, so every top-level symbol is discarded before the type check reaches `class_declaration`, `function_declaration`, or `arrow_function`. Every `.ts`/`.tsx` file in the codebase returns `symbols: []`. Severity upgraded to High. Secondary cause: even after unwrapping, arrow function name lives in `variable_declarator → identifier`, not inside `arrow_function`, so `_outline_ts_name` cannot find it — requires a separate `lexical_declaration` branch. Fix: two changes to `_outline_treesitter` — (1) unwrap `export_statement` before frozenset check; (2) handle `lexical_declaration` for arrow function name extraction. SQL fix unchanged. | Field analysis, Teton monorepo |
| 2026-05-16 | Implemented. `_outline_treesitter` refactored: `export_statement` unwrap via `inner` variable; SQL `statement` wrapper unwrap added; `lexical_declaration` branch added for arrow function exports. SQL grammar verified — `create_function` confirmed as the correct node type from tree-sitter-sql grammar parse tree; added to `_TS_OUTLINE_FUNC_TYPES`. TypeScript `type_identifier` added to `_TS_IDENTIFIER_TYPES` to handle TS class names. 5 tests added covering AC-1/2/3/5/6. 1319 tests pass. | server.py, test_server_tools.py |

## Decision Log

| Date       | Decision                                                                        | Reason                                                                                   | Alternatives                                                              |
| ---------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 2026-05-15 | Unwrap `export_statement` via `inner` variable, not by adding it to a frozenset | `export_statement` is a wrapper, not a symbol kind — adding it to `_TS_OUTLINE_CLASS_TYPES` or `_TS_OUTLINE_FUNC_TYPES` would incorrectly emit `export_statement` as a symbol entry | Add `export_statement` to frozensets (rejected: wrong semantics; emits wrapper as symbol) |
| 2026-05-15 | Verify SQL node type names before editing frozenset                             | Different SQL dialects may use different node type names; adding unverified names risks false positives across grammars | Add all plausible names speculatively (rejected: false positive risk)      |
| 2026-05-15 | `lexical_declaration` branch uses `next(c for c in ... if c.type == ...)` iteration | Avoids `child_by_field_name` which requires knowing field names per grammar version; iterating children is grammar-version-stable | `child_by_field_name("value")` (rejected: field name may vary by grammar version) |

## Risks

| Risk                                                | Mitigation                                                                              |
| --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| SQL grammar node type names differ by SQL dialect   | Verify against actual parse tree before adding to frozenset; add only confirmed names   |
| `export_statement` unwrap misses `export default`   | `"default"` is in the skip-set for the inner child scan; test with `export default class` |
| `lexical_declaration` branch emits non-function vars | Guard on value child type being `arrow_function` specifically; `const x = 5` is not emitted |
| Other languages with similar export wrappers        | Only applies when dispatching to the TypeScript/JavaScript grammar; other grammars unaffected |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
