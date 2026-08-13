# Claude MCP Stanza Embeds Inline Python Exec

Change ID: `1v7a2-bug claude-mcp-stanza-embeds-inline-python-exec`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-13
Wave: 1v7a3 mcp-stanza-without-inline-exec

## Rationale

The rendered Claude MCP registration launches the server through an inline Python program:

```
python3 -c "import os,runpy; runpy.run_path(os.path.join(os.environ['CLAUDE_PROJECT_DIR'], ...), run_name='__main__')"
```

Field-reported from an enterprise deployment: a committed configuration that executes an inline code
string is flagged by their security tooling. A config that names a file is auditable; a config that
carries a program is a code-execution surface in a Git-tracked file, and it reads that way to a
scanner regardless of how benign the program is.

**Claude is the only host that does this.** Every other rendered registration names a path:

| Host | Argument | Working-directory anchor |
| ---- | -------- | ------------------------ |
| Claude `.mcp.json` | inline `python3 -c` program | none (reads `CLAUDE_PROJECT_DIR` inside the program) |
| Cursor `.cursor/mcp.json` | `.wavefoundry/framework/scripts/server.py` | native `"cwd": "${workspaceFolder}"` |
| Junie `.junie/mcp/mcp.json` | `../../.wavefoundry/framework/scripts/server.py` | config-relative by host contract |
| Antigravity `.agents/mcp_config.json` | `.wavefoundry/framework/scripts/server.py` | none |
| Codex `.codex/config.toml` | `.wavefoundry/framework/scripts/server.py` | none |

The inline form arrived in wave `1tj0l` / change `1tjjl-bug`, and that change doc is explicit that
the problem it addressed was **never observed**:

> "The MCP exposure is currently latent: MCP clients normally spawn the server with the workspace
> root as working directory, which is why the server works today on this repository. The exposure is
> that nothing in the rendered configuration enforces that assumption."

So a latent, unreproduced exposure was closed by introducing an active, reported one. That trade is
worth reversing on its own terms, independently of the enterprise report.

**The wrapper was never what supplies the server's root**, which is the operator's observation and it
holds under inspection. `server_impl._discover_root` resolves the repository cwd-independently and
ranks **the script's own install location second**, above any environment variable: `server_impl.py`
always lives at `<root>/.wavefoundry/framework/scripts/`, so `parents[3]` IS the served repository.
`CLAUDE_PROJECT_DIR` is only priority 3, a fallback below that. The docstring states the consequence
directly: "Authoritative for the MCP server and independent of the host's cwd, so the committed
config needs no `--root .`". The wrapper only ever helped the interpreter FIND `server.py`; it never
told the server where the project was.

## Requirements

1. The rendered Claude MCP registration names a path rather than carrying an inline program.
2. No machine-absolute path is embedded, preserving the constraint `1tjjl-bug` Requirement 2 set:
   every distributed MCP registration is Git-tracked and must stay portable.
3. Hook launchers are NOT changed. Hooks genuinely need the project anchor, `1tjjk-bug` established
   that with a reproduced failure, and this change must not weaken it.
4. The server continues to resolve its own repository root without a `--root` argument.

## Scope

**Problem statement:** the Claude MCP stanza is the only rendered registration that embeds an
executable program instead of naming a file, which enterprise security tooling flags, and it was
introduced to close an exposure that was documented as latent.

**In scope:**

- Reverting the rendered Claude MCP argument to the repo-relative
  `.wavefoundry/framework/scripts/server.py`, matching Antigravity and Codex.
- The renderer function that emits it, its tests, and this repository's own `.mcp.json`.
- The docstring and any seeded/rendered documentation that describes the Claude launcher shape.

**Out of scope:**

- Hook launcher commands. They keep `CLAUDE_PROJECT_DIR`; the operator named hooks explicitly as the
  case that still needs it, and `1tjjk-bug` proved that with an observed failure.
- The other four hosts. None carries an inline program, so none is in the reported defect class.
- Adding a `cwd` field to the Claude stanza. Tempting as a way to keep cwd independence without
  inline code, but `1tjjk-bug`'s Decision Log records the framework getting burned by assuming Claude
  host-substitution behaviour without an executed probe (Claude passed `$CLAUDE_PROJECT_DIR`
  literally on native Windows). Inventing an unverified field would repeat that mistake. If cwd
  independence is wanted back later, it needs a probe first and its own change.
- `server_impl._discover_root`, which already does the right thing and is the reason this revert is
  safe.

## Acceptance Criteria

- [x] AC-1: The rendered `.mcp.json` Wavefoundry entry contains no inline program: its `args` name the server path and no argument begins with `-c`.
- [x] AC-2: The rendered argument is repo-relative, containing no absolute path and no drive letter, asserted so a machine path cannot be reintroduced.
- [x] AC-3: The server started from the rendered stanza resolves THIS repository as its root with no `--root` argument, asserted by executing the resolution rather than reasoning about it.
- [x] AC-4: Claude hook launchers still carry the project anchor, asserted so this change cannot be read as a licence to weaken them.
- [x] AC-5: A repository that already carries the inline form is migrated to the path form by an install/upgrade render, rather than keeping the flagged stanza forever.
- [x] AC-6: The rendered Claude stanza matches the shape the other path-naming hosts already ship, asserted against the Antigravity and Codex arguments so the five registrations cannot drift into five idioms.

## Tasks

- [x] Reproduce first: assert the current rendered stanza carries `-c` and an inline program, so the AC-1 assertion is known to fail before the change.
- [x] Revert `render_claude_mcp_json` to the repo-relative path and correct its docstring, which currently explains the inline launcher.
- [x] Update the tests that pin `CLAUDE_PROJECT_DIR` in the MCP stanza; leave the hook-launcher assertions untouched.
- [x] Re-render this repository's `.mcp.json`.
- [x] Verify the stale-launcher rewrite path migrates an existing inline stanza (AC-5) rather than merging alongside it.
- [x] Check the seeds and `AGENTS.md` MCP table for any copy that documents the inline shape.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| revert | implementer | — | Renderer plus docstring; one function. |
| migration | implementer | revert | AC-5: an existing inline stanza must be rewritten, not duplicated. |
| docs | implementer | revert | Seeds and MCP table copy describing the launcher shape. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.mcp.json`

## Affected Architecture Docs

`N/A`. This restores a previously shipped launcher shape and decides no boundary. The cwd-dependence
tradeoff it re-accepts is already recorded in `1tjjl-bug`, and this change doc supersedes that
disposition rather than creating a new architectural claim.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | `1tjjl-bug` Requirement 2 still binds; a machine path would be a worse regression than the inline program. |
| AC-3 | required | The whole revert rests on the server self-anchoring. If that were untrue the change would be unsafe, so it is executed rather than asserted from a docstring. |
| AC-4 | required | Hooks are a different, reproduced case; this change must not be read as weakening them. |
| AC-5 | required | Without migration, every already-installed repository keeps the flagged stanza, which is the operator's actual problem. |
| AC-6 | important | Five registrations converging on one idiom is what stops this drifting again. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-13 | Filed from enterprise field report. Verified before planning rather than taken on report: Claude is the ONLY rendered registration carrying an inline program, the other four name paths; `1tjjl-bug` documents its own motivating exposure as latent and never reproduced; and `_discover_root` ranks the script's install location above every environment variable, so the wrapper never supplied the root. | `render_platform_surfaces.render_claude_mcp_json`; the four sibling host configs; `1tjjl-bug` Rationale; `server_impl._discover_root` docstring and priority order. |
| 2026-08-13 | Reverted `render_claude_mcp_json` to the repo-relative path and re-rendered this repository's `.mcp.json`. AC-5 verified on the real artifact: the existing inline stanza was REPLACED, not merged alongside, and a foreign `my-other-server` entry in the same file survives untouched. | `.mcp.json` before/after; `test_render_migrates_an_existing_inline_stanza`. |
| 2026-08-13 | **The suite proved the exposure was not purely hypothetical, which the plan understated.** `1tjjl-bug` shipped an EXECUTED test, `test_claude_mcp_stanza_runs_owner_server_from_nested_cwd`, that spawned the stanza from a nested cwd and asserted success. The revert breaks it by design. It was NOT deleted: it is replaced by two tests that pin the new contract honestly, one asserting the supported repository-root launch works, and one asserting a nested cwd fails LOUDLY with a missing file. The second matters more than the first: it proves the failure happens before the server starts, so `_discover_root` never runs and the dangerous outcome (starting successfully against the WRONG repository) is impossible. A future change that made the nested path start successfully would now be caught. | `test_claude_mcp_stanza_runs_owner_server_from_the_repository_root`; `test_claude_mcp_stanza_fails_loudly_from_a_nested_cwd`. |
| 2026-08-13 | Three further test sites pinned the inline form and were reconciled rather than loosened: the per-host `valid_args` gate, the byte-identical `CLAUDE_ARGS` constant (now an alias of `EXPECTED_ARGS`, since Claude is no longer a special case), and the committed-config scan, which failed until the real `.mcp.json` was re-rendered and so did its job. AC-4 honoured: the two hook-launcher assertions referencing `CLAUDE_PROJECT_DIR` are untouched. | `test_render_platform_surfaces` 94/94; hook assertions at the `.claude/hooks/pre-edit` and `session-capture` sites unchanged. |
| 2026-08-13 | Discharged the council's docs obligation. One seed described the retired shape: `seeds/011-install-wavefoundry-phase-1.prompt.md` told installers to expect a stanza that "resolves `server.py` from Claude's `CLAUDE_PROJECT_DIR`". Corrected under the `seed_edit_allowed` gate to describe a path argument, to state that no `--root` or project anchor belongs in the stanza, and to name hooks as the separate case that does need the variable. `AGENTS.md`'s copy-ready entry is for instruction-only hosts where an operator types an absolute path by hand; it is a different contract and out of scope. | Seed line rewritten; gate opened and closed around the edit. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-13 | Revert the Claude stanza to the repo-relative path, re-accepting the cwd-dependence that `1tjjl-bug` closed. | The exposure that change addressed was explicitly latent and never reproduced; the problem introduced is active, reported from a real deployment, and applies to a Git-tracked file. An unobserved risk does not justify shipping a code-execution surface in committed configuration, and the reverted shape is what three other hosts already ship. | Keep the inline form and document it for security review (rejected: the operator's tooling flags the file, and an exception request is a recurring cost imposed on every enterprise consumer). Embed an absolute path (rejected: violates `1tjjl-bug` Requirement 2 and breaks portability of a committed file). Add a `cwd` field (rejected: unverified for this host; see Scope). |
| 2026-08-13 | Leave hook launchers alone. | The operator named hooks as the case that genuinely needs the project anchor, and `1tjjk-bug` established that with a REPRODUCED failure rather than a latent one. The asymmetry is the point: hooks are invoked by the host from an unknown cwd, while an MCP server is spawned once per session by a client that supplies the workspace root. | Revert hooks too for consistency (rejected: reinstates a confirmed defect to tidy an idiom). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future MCP client spawns the server from a cwd other than the workspace root, and the relative path fails to resolve. | This is the latent exposure being re-accepted, and it is stated rather than hidden. It fails loudly at startup (the interpreter cannot open the file) rather than silently mis-rooting, because `_discover_root` never runs. Three other hosts already carry the same exposure, so the framework's contract is unchanged rather than newly weakened. |
| The revert is read as licence to strip `CLAUDE_PROJECT_DIR` from hooks. | AC-4 asserts the hook launchers still carry it, and the Decision Log records why the two cases differ. |
| Already-installed repositories keep the flagged stanza. | AC-5 requires the install/upgrade render to migrate an existing inline entry rather than merge alongside it. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
