# Graph Tree-Sitter Language Coverage

Change ID: `12y4x-enh graph-tree-sitter-language-coverage`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph indexer currently models Python and JS/TS structurally, while the chunker already has tree-sitter-backed coverage for a much broader language surface. That leaves the graph behind the supported parsing surface and makes the graph look like a partial view of the repo rather than a structural index of the repo itself.

The goal of this change is to make graph extraction tree-sitter-backed across every language Wavefoundry already supports with tree-sitter today, while keeping the graph symbol-oriented instead of turning it into DOM or syntax noise. The graph should capture meaningful structural boundaries, names, imports, references, and named markup/config anchors where those are useful. It should not try to mirror every parseable token.

This is a follow-on to the existing graph extraction wave, not a reopening of the completed baseline. The baseline graph shape, directional persistence, clustering, and dashboard validation stay in place; this change expands the structural coverage.

## Requirements

1. Extend the graph indexer so it uses tree-sitter-backed structural extraction for the language families already supported by the chunker today, instead of only Python and JS/TS.
2. Keep the graph symbol-oriented:
   - model modules/files, namespaces, classes, functions, methods, imports, and other meaningful named structural boundaries
   - for markup and config-like languages, prefer named elements, anchors, and structural containers over raw tag or DOM noise
   - do not add graph nodes for arbitrary low-value syntax tokens
3. Preserve the canonical graph contract:
   - directional `source` -> `target` edges
   - provenance on every edge
   - the same persisted graph schema/versioning behavior already in place
4. Keep regex only as a fallback when a tree-sitter grammar is unavailable or a syntax tree cannot be parsed.
5. Make coverage explicit per language family so tests and reviews can verify which structural rules are supported.
6. Add tests that cover representative tree-sitter-backed graph extraction for the languages and file families already supported by the chunker.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/indexer.py` only if dispatch wiring needs to change
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` only if graph API snapshots need new assertions

**Out of scope:**

- dashboard polish beyond what is needed to consume the richer graph data
- new graph clustering behavior
- semantic or LLM-derived graph edges
- adding new tree-sitter grammars that the chunker does not already support

## Language Coverage Target

The graph extractor should align with the current tree-sitter-backed chunker surface, including:

- Java
- Scala
- C#
- C and C++
- Go
- Rust
- Kotlin
- Swift
- Objective-C
- Ruby
- PHP
- JavaScript and TypeScript
- HTML and XML-family markup, including JSP-style markup files where the extension is already routed that way
- YAML, TOML, JSON
- CSS and SCSS
- PowerShell
- HCL / Terraform
- SQL

For each family, the extractor should only emit structural graph nodes and edges that help explain ownership, dependency, impact, or navigation. If a language or file family does not have meaningful symbol boundaries, it should degrade to a small, explicit structural representation rather than a noisy token dump.

## Graphify Reference Lens

Graphify is still the useful shape guide here, but only at the level of pipeline discipline: extract structure, assemble a persistent graph, and keep presentation separate. The language-specific implementation detail worth borrowing is the idea that the extractor should be grammar-aware rather than regex-led whenever the parser surface exists.

## Acceptance Criteria

- [x] AC-1: The graph indexer uses tree-sitter-backed structural extraction for the languages already supported by the chunker surface, not just Python and JS/TS.
- [x] AC-2: The graph output remains symbol-oriented and avoids DOM or token-level noise for markup/config-style files.
- [x] AC-3: The canonical graph contract remains unchanged: directional edges, per-edge provenance, and versioned persisted graph artifacts.
- [x] AC-4: Regex-based graph extraction remains only a fallback path when tree-sitter support is unavailable or parsing fails.
- [x] AC-5: Tests cover representative structural extraction across the supported language families.

## Tasks

- [x] Add or extend tree-sitter-backed graph extraction branches for each supported language family.
- [x] Define the language-specific structural nodes and edges for markup/config-style file families.
- [x] Keep the fallback extraction path explicit and minimal.
- [x] Add tests for representative supported languages and file families.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| language extraction coverage | implementer | existing graph extraction baseline | Add structural branches by language family |
| markup/config modeling | implementer | language extraction coverage | Keep only meaningful structure, not DOM noise |
| tests | qa-reviewer | implementation | Verify representative language families and fallback behavior |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` should note that the graph extractor now aligns with the tree-sitter language surface already used by the chunker.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The graph should not lag behind the supported parser surface |
| AC-2 | required | Graph utility depends on preserving meaningful structure rather than syntax noise |
| AC-3 | required | The graph persistence contract must remain stable |
| AC-4 | required | Fallbacks must remain safe and explicit |
| AC-5 | required | Representative coverage is needed before this can be relied on for non-Python projects |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted as the tree-sitter coverage follow-on to the graph extraction wave. | `chunker.py`, `graph_indexer.py` |
| 2026-05-27 | Implemented tree-sitter-backed graph extraction across the supported language families and added representative coverage tests. | `graph_indexer.py`, `test_graph_indexer.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Treat this as a follow-on change rather than reopening the completed baseline extraction change. | The existing graph foundation is complete; this work expands parser coverage and symbol modeling across the supported tree-sitter surface. | Reopen `12xsz` and broaden its scope — rejected to keep the baseline change intact |
| 2026-05-27 | Keep the graph symbol-oriented rather than DOM-oriented. | The graph should explain ownership and impact, not mirror parse trivia. | Emit nodes for arbitrary markup tokens — rejected as noise |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Broadening graph extraction across many languages could introduce noisy or unstable edges | Keep the language rules structural and minimal, and require representative tests |
| Markup/config files could overwhelm the graph if every tag or token becomes a node | Only surface named or structurally meaningful elements |
| The graph extractor could drift from the chunker's supported language surface | Keep the coverage target aligned with the chunker tree-sitter dispatch table |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
