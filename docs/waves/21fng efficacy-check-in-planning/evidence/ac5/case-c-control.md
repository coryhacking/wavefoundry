Owner: Engineering
Status: active
Last verified: 2026-10-23

# Let the Claude Pre-Edit Hook Pass Read-Only Grep and Glob

A downstream distribution reported that after upgrading, the Claude Code pre-edit hook refuses a Grep scoped to framework seeds, so agents fall back to shell reads. The rendered hook registers on every tool, and its non-edit list, `CLAUDE_NON_EDIT_TOOL_NAMES` in `render_platform_surfaces.py`, holds only `Read` and `Bash`. Any other tool is treated as a possible edit, so its `tool_input.path` is checked against the seed and framework gates, which refuse while the gates are closed. Grep and Glob carry a `path` but cannot write, so a search under `.wavefoundry/framework/seeds/` is blocked for no protective benefit. Propose adding `Grep` and `Glob` to the non-edit list so they pass like Read. Edit, Write, MultiEdit and NotebookEdit stay gated exactly as now, and an unfamiliar tool naming a gated path is still refused. Hook tests would drive the rendered hook with Grep, Glob and edit payloads, and the re-rendered `.claude/hooks/pre-edit.py` would match the renderer output.

Source: Rationale, Product Intent and Requirements of `docs/waves/21cw4 windows-pack-setup-root-and-record-hardening/21ayv-bug pre-edit-hook-gates-read-only-search-tools.md`. Deliberately left out: ACs, tasks, commit hashes and the out-of-scope host list.
