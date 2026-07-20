# Install Log Format

Owner: Engineering
Status: active
Last verified: 2026-06-03

The canonical schema for the **Wavefoundry install log**, the markdown-native state machine that gates Wavefoundry's two-phase install.

## File locations

- **Template (framework source of truth):** `.wavefoundry/framework/install/install-log.template.md` — ships in every distribution zip; overwritten on framework upgrades.
- **Live log (operator-owned state):** `.wavefoundry/install-log.md` — copied from the template by the agent on first install; **NEVER shipped in the zip**; preserved across framework upgrades.

The agent reads-and-edits the live log directly. `wf_audit_install` (the validating MCP tool) reads it for validation. The template is read only when bootstrapping a new install (or replacing a corrupted live log).

## Row format

Each row in the install log is a single-line markdown checkbox. Rows are **slugs that point at the canonical source** for their step — they do NOT carry the full step instructions inline. Full content lives in the referenced seed, script, or accompanying phase seed.

There are four row kinds, distinguished by the parenthesized source tag:

| Kind | Form | Example |
|---|---|---|
| **Seed-driven** | `- [STATE] N.M — <slug> (seed-NNN) — artifact: <path>` | `- [ ] 2.3 — Bootstrap evidence base (seed-030) — artifact: docs/repo-profile.json` |
| **Script-driven** | `- [STATE] N.M — <slug> (<script>.py) — artifact: <path>` | `- [ ] 1.2 — Create venv (setup_wavefoundry.py) — artifact: .wavefoundry/venv/` |
| **Verification** | `- [STATE] N.M — <slug> (verify) — expects: <return shape>` | `- [ ] 2.1 — Audit Phase 1 (verify) — expects: wf_audit_install(phase=1) returns next_step` |
| **Instruction** | `- [STATE] N.M — <slug> (instruction)` | `- [ ] 1.7 — STOP: restart agent (instruction)` |

Common fields:

- **`STATE`** is one of: `[ ]` (pending), `[x]` (done), `[~]` (not applicable).
- **`N.M`** is the step number. `N` is the phase (1 or 2). `M` is the step within the phase. Insertions between existing rows use decimal extension (e.g., `1.3.5` between `1.3` and `1.4`). **Existing row numbers are never renumbered** — that would invalidate the install log of any in-progress install.
- **`<slug>`** is a short phrase (5–10 words) describing the step. The slug is for the operator's at-a-glance scan; the canonical content is at the referenced source.
- **`(seed-NNN)`** → execute the seed; read from `.wavefoundry/framework/seeds/NNN-*.prompt.md`. Phase 1 reads seeds from disk directly; Phase 2 may use `seed_get` since MCP is available.
- **`(<script>.py)`** → invoke the script: `python3 .wavefoundry/framework/scripts/<script>.py`.
- **`(verify)`** → run the named tool/check. `expects:` describes the return shape that confirms success.
- **`(instruction)`** → operator/agent action with no on-disk artifact (e.g., restart the agent, deliver a summary).
- **`artifact:`** (seed and script rows) — names the expected on-disk artifact whose presence proves the row's step was completed. Single path per row; multiple artifacts use multiple rows. No globs in v1.
- **`expects:`** (verify rows) — describes the expected tool return shape.

The slug + source-tag combination means the install log stays terse and scannable. Per-step details (defaults, fallbacks, edge cases, validation steps) belong in the referenced seed, not in the row.

## States

- **`[ ]` pending** — step has not been executed. `wf_audit_install` returns this row as the `next_step` once all preceding rows are `[x]` or `[~]`.
- **`[x]` done** — step has been executed AND the agent confirms the artifact exists. `wf_audit_install`'s check 2 verifies the artifact actually exists on disk; mismatch → `checked_but_missing` diagnostic.
- **`[~]` not applicable** — step genuinely doesn't fit this project (e.g., design-system row in a CLI-only project). Operator-authoritative; the tool trusts the marker. Treated as terminal (not pending, not validated by artifact check). Matches the `[~]` convention from wave 1p32k.

## Phases

The log is divided into two sections by H2 headings: `## Phase 1 — Harness (no MCP required)` and `## Phase 2 — Project discovery (MCP required)`.

- **Phase 1** rows must not depend on MCP. The agent reads seeds from disk, runs shell + Python, edits files. `wf_audit_install` is NOT callable during Phase 1 (it lives in the MCP server). Phase 1 row kinds are limited to seed-driven (read seed from disk), script-driven, and instruction.
- The **last row of Phase 1** is an `(instruction)` row marked STOP — restart agent. After it is marked `[x]`, the operator restarts their agent. The MCP server becomes available.
- **Phase 2** rows may use any MCP tool. The **first row of Phase 2** is a `(verify)` row calling `wf_audit_install(phase=1)` to confirm Phase 1 actually produced its artifacts before Phase 2 begins.
- The **second-to-last row of Phase 2** is a `(verify)` row calling `wf_audit_install()` (no phase arg) for the end-to-end completion check.
- The **last row of Phase 2** is an `(instruction)` row delivering the operator summary handoff.

## Trustworthy-invariant rule

**The install log is trustworthy when the last operation against it was a `wf_audit_install` call that returned `status: "next_step"` or `status: "complete"`.** Any other resumption (fresh agent session, partial recovery from an abort) MUST start by calling `wf_audit_install` before trusting the `[x]` markers on existing rows.

Reason: an agent can in principle mark `[x]` without producing the artifact (a bug or interruption mid-step). The tool's check 2 (artifact validation) is what catches that drift. The tool runs that check on every call, so the log returning to a `next_step`/`complete` state is the assurance that all `[x]` rows truly have their artifacts on disk.

## Phase 1 MCP-free invariant

No Phase 1 row may require an MCP tool call. The MCP server isn't running yet — Phase 1 is what installs it. Phase 1 rows are constrained to:

- Shell commands (`mkdir`, `mv`, `chmod`, etc.)
- Python script invocations (`python3 .wavefoundry/framework/scripts/<script>.py`)
- File reads + edits (the install log itself, workflow-config.json, etc.)
- Direct seed reads from `.wavefoundry/framework/seeds/`

If a future change adds a Phase 1 row that needs MCP, the install is broken by construction. This invariant is checked by AC-13 in the foundational change (`1p35f`): a grep test verifies seed-011 contains no `wave_*` MCP-tool references as required actions.

## How `wf_audit_install` consumes the log

On each call, the tool:

1. **Runs `docs-lint`.** Lint errors block advancement; tool returns `{status: "lint_errors", errors: [...]}` without continuing.
2. **Validates artifacts for each `[x]` row.** For every checked row, the tool parses the `artifact: <path>` field and verifies the file/directory exists. Missing artifact → `{status: "checked_but_missing", row, expected, next_action}`.
3. **Returns the first `[ ]` row.** Skipping `[~]` rows. If no `[ ]` rows remain (all are `[x]` or `[~]`), returns `{status: "complete"}`. Otherwise `{status: "next_step", row, seed, instructions}`.

The tool does not auto-execute steps. It points at the next action and instructs the agent to complete it manually, then re-call.

## Parser semantics

The install-log row parser lives at `.wavefoundry/framework/scripts/install_log_lib.py` (or extends `wave_lint_lib`). The parser:

- Recognizes any line matching the row regex; lines that don't match are passed through unchanged (the log can contain prose between rows).
- Permissive on prose changes within a row's intent text; the load-bearing fields are STATE, the N.M number, the seed-NNN, and the `artifact:` path.
- Tolerant of trailing whitespace, paragraph breaks, and surrounding headings.

The parser is shared between the installing agent (via the tool) and any future consumer (e.g., dashboard install-progress widgets).

## Related

- **Companion tool**: `wf_audit_install` (see `1p35h` change in wave `1p35d`).
- **Entry doc**: `install-wavefoundry.md` ships at the zip root and points the agent at the install log.
- **Companion AC marker**: the `[~]` not-applicable state is the same convention introduced in wave 1p32k for AC checkboxes.
