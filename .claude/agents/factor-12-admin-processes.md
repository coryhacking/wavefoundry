---
name: factor-12-admin-processes
description: PROACTIVELY use when reviewing CLI admin scripts and operational commands. Canonical factor doc: `docs/agents/factor-12-admin-processes.md`.
tools: Read, Grep, Glob, Bash, ToolSearch, mcp__wavefoundry__code_ask, mcp__wavefoundry__code_search, mcp__wavefoundry__code_keyword, mcp__wavefoundry__code_lexical, mcp__wavefoundry__code_read, mcp__wavefoundry__code_outline, mcp__wavefoundry__code_definition, mcp__wavefoundry__code_references, mcp__wavefoundry__code_callhierarchy, mcp__wavefoundry__code_dependencies, mcp__wavefoundry__code_impact, mcp__wavefoundry__code_list_files, mcp__wavefoundry__code_constants, mcp__wavefoundry__code_pattern, mcp__wavefoundry__code_callgraph, mcp__wavefoundry__code_graph_path, mcp__wavefoundry__code_graph_community, mcp__wavefoundry__docs_search, mcp__wavefoundry__seed_get
model: sonnet
---

# Factor 12 — Admin Processes Review Agent (Wrapper)

Canonical factor doc: `docs/agents/factor-12-admin-processes.md`.

Use the canonical doc for coverage, applicability evidence, review questions, and findings guidance. This wrapper is thin and mechanical.

Load and prefer the Wavefoundry `code_*` MCP tools (via `ToolSearch` when the host defers schemas) over grep/raw reads for locating and understanding code; back any how-many/blast-radius claim with `code_references`/`code_callhierarchy`. Full posture: `docs/contributing/agent-team-workflow.md` § Retrieval Posture (All Lanes).
