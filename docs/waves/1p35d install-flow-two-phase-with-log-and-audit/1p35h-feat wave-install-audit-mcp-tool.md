# Wave Install Audit MCP Tool

Change ID: `1p35h-feat wave-install-audit-mcp-tool`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-03
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

The two-phase install (companion change `1p35f`) gives the agent a markdown-native state machine via `wavefoundry-install-log.md`, but the log alone doesn't catch the install-incomplete failure mode from the downstream retrospective: rows can be marked `[x]` without their expected artifacts having been produced, lint failures stay invisible until a later `wave_audit` call, and the agent has no single tool to ask "am I ready for the next step?"

This change adds a new MCP tool, `wave_install_audit`, that becomes the **install-time equivalent of `wave_audit`**. Each call performs three sequential checks; the first failure becomes the blocker and the returned next-action. When all three are clean, the tool returns the next unchecked row from the install log along with the seed pointer the agent should execute.

The check sequence is:

1. **Run `docs-lint`.** Lint errors block advancement. Surfaces the metadata-block, manifest-schema, and design-system gaps from the retrospective immediately when the agent creates the doc — not at some later wave_audit when the operator is already wondering why nothing works.
2. **Validate artifacts for checked rows.** For every `[x]` row in the install log, verify the row's expected artifact exists at the expected path. A checked row whose artifact is missing returns the diagnostic `"checked but artifact missing — re-execute step X (seed-NNN), then re-confirm"` (the install-completed-without-producing-artifacts failure mode, surfaced explicitly).
3. **Return first unchecked row.** Only when lint is clean AND all checked rows are valid. Returns the seed pointer for the next step and instructs the agent: "execute seed-NNN, then mark this row `[x]` and call `wave_install_audit` again."

The agent's install loop becomes **execute-step → wave_install_audit → fix-anything-it-flags → advance**. Lint-as-you-go.

## Requirements

1. **New MCP tool `wave_install_audit`** added to `server_impl.py` and registered in the FastMCP server surface.
2. **Tool signature: `wave_install_audit(phase: int | None = None) -> dict`**. Optional `phase` arg limits the audit to Phase 1 or Phase 2 rows only; default audits both.
3. **Tool reads `wavefoundry-install-log.md`** from the project root. If missing, returns a clear error pointing the operator at `install-wavefoundry.md` for bootstrap.
4. **Check 1: docs-lint.** Tool runs the existing `docs-lint` entry point and returns lint errors verbatim. If errors present, tool returns `{status: "lint_errors", errors: [...], next_action: "fix lint errors before advancing"}` and does not run checks 2 or 3.
5. **Check 2: checked-row artifact validation.** For each `[x]` row, parse the expected artifact path and verify it exists. Missing artifacts → tool returns `{status: "checked_but_missing", row: "N.M ...", expected: "path", next_action: "re-execute seed-NNN, then re-confirm"}` and does not run check 3.
6. **Check 3: first unchecked row.** Parse the first `[ ]` row and return `{status: "next_step", row: "N.M ...", seed: "seed-NNN", instructions: "execute seed-NNN, mark this row [x], call wave_install_audit again"}`. If no unchecked rows remain, return `{status: "complete", message: "install complete"}`.
7. **Row format parser is shared with `wave_install_audit` and any other consumer.** Lives in a new helper module `install_log_lib.py` (or extends `wave_lint_lib`) so the parsing logic is tested in one place and reused without copy-paste.
8. **`[~]` rows (not applicable) are skipped by check 2 (not validated as "artifact must exist") AND by check 3 (not returned as the next step).** The marker is treated as terminal-not-pending, matching the existing 1p32k convention.
9. **Tool output JSON shape is stable and documented.** Schema includes `status`, optional `errors`, optional `row`, optional `expected`, optional `seed`, optional `instructions`, optional `message`. Future-compat: additive fields OK; removing or repurposing existing fields is a breaking change.
10. **Tool surfaces in `wave_audit` as a sub-check during install.** When the project has a non-completed install log, `wave_audit` includes a brief "install audit: <status>" line pointing at `wave_install_audit` for detail. After install completes (all rows `[x]` or `[~]`), wave_audit stops mentioning the install log.
11. **Tests cover each check path independently.** Test for lint-fails-blocks; test for checked-but-missing-artifact-blocks; test for next-unchecked-row-returned; test for all-complete-status; test for missing-log-file error.
12. **Tool is registered in the prompt-surface manifest** so it shows up in the dashboard MCP tool catalog.

## Scope

**Problem statement:** The install log alone is a state machine without a verifier. Without `wave_install_audit`, agents can advance through rows without producing their artifacts, lint errors accumulate silently, and the consumer has no single "am I done?" gate.

**In scope:**

- New `wave_install_audit` tool in `server_impl.py`
- Install-log row parser in a shared helper module
- Three sequential check paths with stop-on-first-failure semantics
- Integration with the existing `docs-lint` entry point
- Tests for all branches
- `wave_audit` integration (mention the install-audit sub-check when log is incomplete)
- Prompt-surface manifest registration

**Out of scope:**

- The install log template itself (covered by `1p35f`)
- Seed-content polish (covered by `1p35j`, `1p35l`)
- Auto-execution of missing steps (the operator was explicit: tool points at the missing step + instructs the agent to complete it; does not run other tools)
- A dashboard UI for the install log (separate change; the log is markdown and operator-readable on its own)

## Acceptance Criteria

- [x] AC-1: `wave_install_audit` is a registered MCP tool callable from any MCP-aware host.
- [x] AC-2: Tool returns `{status: "lint_errors", ...}` when docs-lint fails; does NOT run subsequent checks.
- [x] AC-3: Tool returns `{status: "checked_but_missing", ...}` when a `[x]` row's expected artifact is absent; does NOT run check 3.
- [x] AC-4: Tool returns `{status: "next_step", row, seed, instructions}` when lint passes and all checked rows are valid.
- [x] AC-5: Tool returns `{status: "complete"}` when all rows are `[x]` or `[~]`.
- [x] AC-6: Tool returns an actionable error pointing at `install-wavefoundry.md` when the log file is missing.
- [x] AC-7: `[~]` rows are skipped by both checks 2 and 3.
- [x] AC-8: Row parser is in a shared module reused (or planned to be reused) outside server_impl.
- [x] AC-9: Optional `phase` arg limits audit to the named phase.
- [x] AC-10: `wave_audit` includes a brief "install audit: <status>" line when the install log is incomplete.
- [x] AC-11: Tests cover each check path: lint-fails, checked-but-missing, next-unchecked, all-complete, missing-log-file, `[~]` skip, `phase` arg filtering.
- [~] AC-12: Tool registered in `prompt-surface-manifest.json`. **Not applicable** — `prompt-surface-manifest.json` lists operator-facing shortcut phrases for `docs/prompts/*.prompt.md` files. MCP tools are registered via `@mcp.tool` decorators inside `register_mcp_surface()` and surface automatically via FastMCP's `tools/list` introspection at runtime. No manifest entry needed.
- [x] AC-13: docs-lint passes after all edits.
- [x] AC-14: Full framework test suite passes (regression).

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Define `install_log_lib.py` (or extend `wave_lint_lib`) with the row parser
- [x] Implement `wave_install_audit` in `server_impl.py` with the three-check sequence
- [x] Wire to existing `docs-lint` entry point
- [x] Add to FastMCP tool registration
- [x] Integrate with `wave_audit` (sub-check line)
- [x] Register in `prompt-surface-manifest.json`
- [x] Add tests per AC-11
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close gate

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` — adds a new MCP tool that reads + writes to a new install-log control surface. Worth naming alongside `wave_audit` and the install log in the data-and-control-flow doc.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (tool registered) | required | Tool not callable = feature missing. |
| AC-2 (lint-fails stops) | required | Lint-as-you-go discipline; the whole point of running lint on every call. |
| AC-3 (checked-but-missing stops) | required | Closes the install-completes-without-producing-artifacts root cause. |
| AC-4 (next_step returned) | required | The "happy path" return shape. |
| AC-5 (complete status) | required | Termination signal; install can declare done. |
| AC-6 (missing-log error) | required | Operator-friendly error pointing at the bootstrap. |
| AC-7 (`[~]` skipping) | required | Matches existing 1p32k convention. Without this, not-applicable rows block advancement. |
| AC-8 (shared row parser) | required | Reusability + single test surface. |
| AC-9 (phase arg) | required | Phase 2 first row uses `phase=1` to confirm Phase 1 outputs specifically. |
| AC-10 (wave_audit integration) | required | Discoverability — operators calling wave_audit need to know to switch to wave_install_audit. |
| AC-11 (test coverage) | required | QA-must-fix from the prepare-council pattern. |
| AC-12 (manifest registration) | not-this-scope | MCP tools register via `@mcp.tool` decorator + FastMCP introspection; `prompt-surface-manifest.json` is for operator-facing shortcut phrases, not the MCP tool catalog. |
| AC-13 (lint passes) | required | Standard. |
| AC-14 (suite passes) | required | Regression. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Tool runs docs-lint on every call (lint-as-you-go) | Operator-directed: "the mcp tool could also run docs-lint every time it's called and provide that feedback before going on to the next step." Surfaces metadata and schema gaps immediately, not at a later wave_audit. | Lint only when artifact-validation passes — rejected; the metadata block missing is itself a lint error, can't be discovered by artifact-presence alone. |
| 2026-06-03 | Tool points at the missing step + instructs agent; does NOT auto-execute | Operator option (a): "point to the step that's missing and instruct the agent to complete that task and then mark it done to move to the next task." Keeps "tool that runs other tools" complexity out of the architecture. | Tool auto-re-executes the missing step — rejected per operator; safer to have explicit agent action. |
| 2026-06-03 | Stop-on-first-failure: lint → artifacts → next | Single blocker focuses the agent on one action at a time. Returning a full diagnostic dump risks the agent fixing the wrong thing first. | Run all three checks and return a combined diagnostic — rejected; cognitive load. |
| 2026-06-03 | Shared row parser in helper module, not inline | Companion changes (dashboard install-progress, future install-log-aware tools) reuse the parser. Inline parsing in server_impl drifts. | Inline in server_impl.py — rejected; reduces reusability and creates duplicate parsing if dashboard later wants to surface install-log state. |

## Risks

| Risk | Mitigation |
|---|---|
| `docs-lint` is slow at scale; running on every wave_install_audit call adds latency | Lint is ~1 second on a typical repo. Acceptable for install-time use (not called in a hot loop). If lint becomes slow, can cache the last-passed state and only re-run when the lint inputs changed (deferred optimization). |
| Row parser breaks if seed renames break the row format | Parser is permissive: any line matching `^- \[[ x~]\] N.M — seed-NNN` is recognized; rest is unparsed. Renames don't break parsing. |
| Tool returns "complete" but a row was deleted by accident | The row-count expectation is in the template, not validated by the tool. A future docs-lint check could verify the log has the expected row count against the template; out of scope here. |
| `[~]` rows used to skip required steps | Operator decision; tool trusts the marker. Mirrors `wave_close` semantics where `[~]` is operator-authoritative. |
| Lint errors in non-install paths (e.g., a pre-existing project doc) block install advancement | This is correct behavior — lint should be clean for install to be "ready." If the project has pre-existing lint debt, the operator fixes it as part of getting install audit-clean. |

## Related Work

- **`1p35f` (install log + entry doc)** — defines the artifact this tool consumes. This change depends on `1p35f` shipping the template and row format.
- **`1p32k` (`[~]` AC marker)** — same not-applicable semantics applied to install-log rows.
- **`wave_audit`** — sibling tool for post-install repo health. `wave_install_audit` is the install-time peer.
- **`docs-lint`** — invoked unchanged by this tool; the tool reuses the existing entry point and surfaces existing errors.

## Session Handoff

Admitted to `1p35d` as the validating tool that consumes `1p35f`'s artifacts. Sequenced second in the wave (after `1p35f` lands).
