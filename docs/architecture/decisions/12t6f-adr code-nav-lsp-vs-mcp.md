# 12t6f-adr — Code Navigation: MCP-Embedded Tree-Sitter over LSP

Owner: Engineering
Status: accepted
Last verified: 2026-05-22

## Context

Wavefoundry exposes code navigation to agents as MCP tools. These tools fall into two distinct categories with different backing strategies:

**Semantic search** (`code_search`, `code_ask`) — concept and intent-based retrieval backed by BGE-base embeddings over LanceDB. LSP is irrelevant here; no LSP server produces embeddings or answers concept-level queries. This backing is settled and not subject to this decision.

**Structural navigation** (`code_definition`, `code_references`, `code_outline`, `code_hover`, `code_callhierarchy`, `code_dependencies`) — symbol-level lookup backed by Python stdlib AST, tree-sitter, and regex fallback. LSP servers (pyright, tsserver, jdtls, rust-analyzer, gopls, clangd, etc.) provide type-aware navigation that structural parsing cannot match — resolving definitions through inheritance, filtering references by type, surfacing diagnostics. This is the category this ADR addresses.

The decision was revisited in May 2026 with a full red-team and Wave Council review. This ADR records the conclusion and the bounds under which it should be reconsidered.

## Decision

Code navigation tools are implemented in-process inside the MCP server using a tiered strategy: Python stdlib AST → tree-sitter (20+ languages) → regex/structural fallback. LSP is not used as a backing layer. Semantic search (`code_search`, `code_ask`) uses BGE-base embeddings over LanceDB, which has no LSP equivalent and is unaffected by this decision.

## Consequences

**Positive:**
- Zero external process dependencies — tree-sitter is a single pip package; the full tool surface works on any machine that can run the MCP server
- 20+ languages covered uniformly, including SQL, YAML, TOML, Bash, and others with no production-quality LSP server
- All structural tools (`code_definition`, `code_references`, `code_outline`) are stateless and always read from disk — no synchronization required when agents edit files
- No startup latency — tools respond immediately with no server warm-up
- Semantic search (`code_search`, `code_ask`) provides concept-level navigation that LSP cannot offer
- Degrades gracefully — tree-sitter absence falls through to regex; regex always available

**Negative / tradeoffs:**
- No type-accurate navigation: `code_definition` on an overridden method returns all structural definitions with that name, not the runtime dispatch target
- No type-filtered references: `code_references` on an overloaded identifier in Java/C# returns all text matches, not type-scoped call sites
- No cross-file type graph: "all implementors of interface X" or "all subclasses of Y" is not available
- No diagnostics, semantic tokens, or rename refactoring
- Tree-sitter grammar quality varies — SQL, Kotlin, Scala grammars are community-maintained and less battle-tested than Python AST

**Constraints imposed:**
- Agents doing type-accuracy-sensitive work (impact analysis on overridden methods, safe-delete checks in typed languages) must work within structural precision limits
- Tasks requiring "find all implementors of interface X" must use `code_search` + `code_keyword` as an approximation

## Alternatives Considered

| Alternative | Reason rejected |
|---|---|
| LSP as the primary backing for structural navigation | N language server binaries required per deployment; startup latency (jdtls: 15–30s, rust-analyzer: minutes) incompatible with on-demand agent calls; stateful servers require file-change synchronization; process lifecycle management adds new failure surface; language coverage has large holes for SQL/YAML/Bash/TOML |
| LSP as primary with tree-sitter fallback | Preserves the deployment and startup problems as the primary path; fallback only engaged when the LSP server fails; doesn't improve language coverage |
| Build our own LSP client to query standalone language servers | Significant implementation cost with no advantage over leveraging clients that already exist; standalone servers (pyright, rust-analyzer, gopls, etc.) are widely available but require an LSP client to speak the wire protocol — we should not write one |
| LSP as optional tier-0 above tree-sitter | **Not rejected** — this is the recommended future path if type precision becomes a constraint (see Revisit Conditions). The key constraint: we do not implement our own LSP client. We leverage clients and servers that already exist. |

## Revisit Conditions

This decision should be reconsidered when agent tasks consistently require type-accurate dispatch resolution — e.g., refactoring or safe-delete analysis where structural name matching produces too many false positives.

**When revisiting, do not implement an LSP client.** Plenty of options already exist:

- **IDE extension bridge** — Claude Code's VS Code extension has direct access to `vscode.executeDefinitionProvider`, `vscode.executeReferenceProvider`, etc., backed by whatever language servers VS Code is running. The JetBrains plugin has access to JetBrains PSI, which is more capable than LSP. Cursor (VS Code-based) and Zed expose the same APIs. The extension bridges intelligence into the MCP server over local IPC; wavefoundry consumes structured results and never touches the LSP wire protocol.
- **Standalone language servers already installed** — pyright, rust-analyzer, gopls, clangd, typescript-language-server, bash-language-server, and many others are installable via a single command (`npm i -g`, `go install`, `rustup component add`, `brew install`). Neovim's `mason.nvim` package manager installs and manages ~200 language servers consistently across platforms; developers using Neovim likely have the relevant servers on PATH already.
- **AI tool native intelligence** — Cursor, GitHub Copilot, and other AI coding tools have warmed code intelligence that could be bridged similarly to the IDE extension approach.

In all cases, tree-sitter remains the universal fallback for CLI, CI, web, and headless contexts where no IDE or language server is present.

## References

- `docs/specs/mcp-tool-surface.md` — governing contract for the code navigation tool surface
- `docs/architecture/decisions/12dzj-adr embedding-model-and-format.md` — related decision on the semantic search layer
- Wave Council review: 2026-05-22 — red-team evaluation + council synthesis on file in session history
