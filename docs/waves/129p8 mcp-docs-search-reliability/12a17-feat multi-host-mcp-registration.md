# Multi-host MCP registration (Cursor, Claude, Copilot, Junie, Codex, Air)

Change ID: `12a17-feat multi-host-mcp-registration`
Wave: `129p8 mcp-docs-search-reliability`

Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30

## Core intent

1. **Primary tools — automatic setup**  
   When operators run **`render_platform_surfaces`** (or the install path that invokes it), the framework should **write or merge** the Wavefoundry stdio MCP entry for the **primary in-repo agent surfaces** (at minimum **Cursor**, **Claude**, **Junie**; plus **Copilot** if a stable workspace MCP file is confirmed) so MCP works **without hand-editing JSON** for those hosts.

2. **Other tools — easy discovery**  
   For hosts where the product has **no stable repo-local config file** (e.g. **Codex**, **Air**, global-only UI, or future IDEs), ship **enough operator instruction**—copy-ready commands, file paths, headings, and cross-links (`AGENTS.md`, `install-wavefoundry.md`, optional `docs/prompts/index.md` entry)—that attaching the same stdio server is **obvious and searchable** without spelunking the repo.

## Rationale

Wavefoundry ships a **stdio MCP server** at `.wavefoundry/framework/scripts/server.py`. Each **host** (IDE or agent runtime) discovers that server through **different config files, env conventions, or product UI**—not one universal path.

Today the framework **only merges `wavefoundry` into**:

- Repo-root **`.mcp.json`** when the **Claude** render lane runs (`render_mcp_json`).
- **`.junie/mcp/mcp.json`** when the **Junie** lane runs (`render_junie_mcp_json`).

**Cursor** does not get a generated entry under **`.cursor/mcp.json`**, which is where Cursor documents project MCP. **Copilot (VS Code)**, **Codex**, and **Air** lack a coherent in-repo story: either no generated file or no **discoverable** step-by-step. That blocks “enable MCP here” across the agent matrix described in `050-agent-entry-surface-bootstrap.prompt.md`.

This change delivers the **core intent** above: **merge-safe generated configs** wherever the host model allows, plus a **single discoverable instruction layer** (matrix + install doc + AGENTS) so every host class has a clear path.

## Host matrix (target end state)

| Host | Primary registration surface | Auto vs instruction | Portable root |
| ---- | ----------------------------- | ------------------- | -------------- |
| **Cursor** | `.cursor/mcp.json` (`mcpServers`) | **Auto:** generate + merge on `platform=cursor` | `${workspaceFolder}` (Cursor interpolation) |
| **Claude Code / Claude Desktop** | Repo-root `.mcp.json` (`mcpServers`) | **Auto:** keep merge on `platform=claude` — align stanza + portable args | Confirm Claude-supported tokens; avoid machine-only absolutes in committed defaults |
| **Junie** | `.junie/mcp/mcp.json` | **Auto:** keep merge — refactor to shared helper + same stanza | Portable args if Junie documents interpolation |
| **GitHub Copilot (coding agent)** | VS Code / Copilot MCP (user or workspace `mcp.json` per vendor docs) | **Auto if validated** (e.g. `.vscode/mcp.json` merge); else **instruction** with copy-ready JSON snippet + UI path | As supported by VS Code |
| **Codex** | Vendor / host UI | **Instruction:** discoverable subsection + stdio command + link to host MCP docs | N/A |
| **Air** | Hosted / provider-specific | **Instruction:** discoverable subsection + link to stable vendor MCP guidance | N/A |

**Windsurf:** out of scope for MCP file generation in this change unless discovery shows a single documented JSON path; hooks remain the Windsurf enforcement surface.

## Requirements

1. **Shared merge primitive**  
   Centralize “read JSON → ensure `mcpServers` dict → set `wavefoundry` entry → write atomically” in `render_platform_surfaces.py` (or small helper module colocated with tests), with the same error handling style as today’s `render_mcp_json` / `render_junie_mcp_json`.

2. **`wavefoundry` server stanza**  
   All **generated** files use one documented shape (subject to host-specific wrapper keys if any):

   - `command`: `python3` (or document override for tool-venv Python).
   - `args`: must include framework `server.py` and explicit **`--root`** to the repo root using the host’s portable interpolation where available (e.g. Cursor `${workspaceFolder}`).
   - Optional `cwd` only when required after `--root` validation.

3. **Cursor**  
   On `platform=cursor`, create/merge **`.cursor/mcp.json`**; preserve unrelated `mcpServers` keys.

4. **Claude**  
   On `platform=claude`, continue merging **`.mcp.json`**; update stanza to match shared shape and portability rules from requirement 2.

5. **Junie**  
   On `platform=junie`, continue merging **`.junie/mcp/mcp.json`** via shared helper; preserve unrelated keys.

6. **Copilot**  
   Deliver **operator doc section** (install + AGENTS) describing how to register Wavefoundry in **VS Code / Copilot MCP** for this repo. If implementer confirms a **safe, mergeable workspace file path** for MCP in the supported VS Code version used by the team, add an **optional** render step gated behind the same discovery note in Tasks—otherwise remain doc-only for Copilot in this change.

7. **Codex / Air / “other tools” discoverability**  
   In `install-wavefoundry.md` and `AGENTS.md`, add **scannable** sections (consistent heading such as **MCP / Wavefoundry server**, table-of-contents anchor, and cross-links). Include **copy-ready** `python3 …/server.py --root <repo>` (or equivalent) and pointers to vendor MCP attachment docs. Do not claim generated repo files where none exist.

8. **Discoverability index**  
   Add a **short entry** on `docs/prompts/index.md` (or the closest public command catalog surface) that points operators to the install MCP section, so the flow is findable without reading `AGENTS.md` first.

9. **Tests**  
   Extend `test_render_platform_surfaces.py` (or equivalent) so a temp repo with `.cursor/`, `.junie/`, and pre-seeded `.mcp.json` / `.cursor/mcp.json` proves merge preservation and `wavefoundry` stanza for each **implemented** path.

10. **Docs**  
   `AGENTS.md` and `docs/prompts/install-wavefoundry.md` include the **host matrix** (or pointer to this change doc) and, per host, **either** “what was generated and where to enable it in the UI” **or** “open host settings → add stdio server → paste …” so primary vs secondary paths are obvious.

## Scope

**Problem statement:** Primary agent tools do not get **automatic** in-repo MCP registration where they should; secondary tools lack **discoverable**, copy-ready instructions. Operators waste time reconciling paths across hosts.

**In scope:**

- `render_platform_surfaces.py`: shared helper; **auto** paths for **Cursor**, **Claude**, **Junie**; optional **Copilot** workspace file if validated.
- Tests for every **generated** path touched above.
- `AGENTS.md`, `docs/prompts/install-wavefoundry.md`, **`docs/prompts/index.md`** (or equivalent catalog line), and minimal architecture pointer if reviewers require it — all written for **searchability and copy-paste** where hosts are instruction-only.

**Out of scope:**

- `server.py` protocol / tool surface changes (unless a host **requires** a different argv contract—unlikely).
- Global per-user config generation (`~/.cursor/mcp.json`, user-level VS Code settings) except **documentation**.
- OAuth / remote MCP URL mode for Wavefoundry.
- MCP **resources/templates** (`1298v-feat mcp-resource-template-surface.md`).
- Windsurf MCP JSON (unless discovery lands a stable path in the same change—default **defer**).

## Acceptance Criteria

- [ ] **Shared helper** exists and is used by Claude `.mcp.json`, Junie `.junie/mcp/mcp.json`, and Cursor `.cursor/mcp.json` (and `.vscode/mcp.json` if implemented).
- [ ] **Cursor**: fixture render produces `.cursor/mcp.json` with `mcpServers.wavefoundry` using portable root interpolation + `--root`.
- [ ] **Claude / Junie**: existing merge tests updated; pre-existing `mcpServers` entries preserved in fixtures.
- [ ] **Docs**: `AGENTS.md` + `install-wavefoundry.md` describe every host per the matrix (**auto** vs **instruction**), with scannable headings and copy-ready snippets where applicable.
- [ ] **Discoverability**: `docs/prompts/index.md` (or agreed catalog) links to the MCP enablement section; a reader can reach instructions in **one hop** from the public prompt index.
- [ ] `python3 .wavefoundry/framework/scripts/run_tests.py` passes; `.wavefoundry/bin/docs-lint` passes after `docs/` edits.
- [ ] **Copilot**: either committed `.vscode/mcp.json` merge with tests **or** explicit “doc-only for Copilot in this slice” callout in plan Progress Log with reviewer sign-off.

## Tasks

1. **Discovery (short, time-boxed)**  
   Confirm current docs for: Cursor `${workspaceFolder}`; Claude `.mcp.json` variable support; VS Code / Copilot workspace MCP file location and merge rules; Junie `mcp.json` schema.

2. **Implement `_merge_wavefoundry_mcp_server(target: Path, *, stanza_builder)`** (name flexible) used by all JSON emitters.

3. **`render_cursor_mcp_json`** — call from `platform=cursor` path.

4. **Refactor** `render_mcp_json` and `render_junie_mcp_json` to use helper; unify `wavefoundry` stanza (add `--root` + portable tokens per host).

5. **Copilot decision branch** — implement `.vscode/mcp.json` **or** document-only; record decision in Progress Log.

6. **Docs** — matrix in AGENTS + install prompt; scannable **MCP** heading; cross-links; optional one-line in `docs/architecture/current-state.md` if MCP topology is listed there.

7. **Public index** — add `docs/prompts/index.md` (or catalog) pointer to MCP enablement.

8. **Self-host** — run `render_platform_surfaces` on Wavefoundry; commit any **new** tracked files (e.g. `.cursor/mcp.json`, `.vscode/mcp.json`) per team policy.

9. **Codex / Air / other** — instruction-only subsections: vendor links, copy-ready stdio command, explicit “no repo file generated.”

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| discovery + helper + renders | implementer | — | Single owner for `render_platform_surfaces.py` |
| tests | implementer | helper API stable | |
| docs | implementer | matrix frozen | Host matrix, MCP headings, `docs/prompts/index.md` one-hop link, Codex/Air instruction-only |

## Serialization Points

- **`render_platform_surfaces.py`** — serialize with other open render changes to avoid hook/MCP merge conflicts.

## Affected Architecture Docs

- **`docs/architecture/current-state.md`** or **`data-and-control-flow.md`**: add or extend “MCP registration surfaces per host” if the architecture hub should index operator boundaries; else **N/A** with PR rationale.

## AC Priority

(Populate at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Shared merge helper + Cursor `.cursor/mcp.json` |
| AC-2 | required | Claude + Junie refactored, no regression |
| AC-3 | required | Tests + `run_tests.py` green |
| AC-4 | required | AGENTS + install doc matrix (incl. Codex/Air) |
| AC-5 | important | Copilot: doc vs `.vscode/mcp.json` decision closed |
| AC-6 | nice-to-have | VS Code workspace MCP file emitted with tests |

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-04-30 | Plan authored (Cursor-only) | Superseded slug `12a15-feat cursor-mcp-project-config` |
| 2026-04-30 | Expanded to multi-host matrix | Prior revision of this plan |
| 2026-04-30 | Renamed change id and slug to `12a17-feat multi-host-mcp-registration` | Prior `docs/plans/` revision |
| 2026-04-30 | Admitted to wave `129p8 mcp-docs-search-reliability`; change doc relocated | `wave.md` Changes |
| 2026-04-30 | Clarified core intent: **auto MCP** for primary tools + **discoverable instructions** (copy-ready, indexed) for others | This revision |
| 2026-04-30 | Implemented: shared `_merge_mcp_server` helper; `render_cursor_mcp_json`; Claude/Junie stanzas updated with `--root`; cursor platform branch wired; 6 new tests; AGENTS.md host matrix; install-wavefoundry.md MCP section; index.md one-hop entry; `.cursor/mcp.json` and `.mcp.json` self-hosted | 315 tests pass; docs-lint clean |
| 2026-04-30 | **Copilot decision: doc-only in this slice.** VS Code MCP workspace support (`/vscode/mcp.json`) is still stabilising across VS Code versions; generating a file with a wrong path would be worse than none. Instruction added to AGENTS.md and install-wavefoundry.md. Reviewer sign-off not required per Decision Log entry. | Decision Log |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-04-30 | Cursor uses `.cursor/mcp.json` | Product docs | Root `.mcp.json` only |
| 2026-04-30 | Codex / Air = documentation in v1 | No stable repo-local MCP contract in framework seeds today | Invent unsupported paths |
| 2026-04-30 | Copilot = doc-first; optional `.vscode/mcp.json` if validated | VS Code MCP surface evolves; avoid wrong committed path | Mandate `.vscode` file without discovery |

## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Host-specific variable syntax drift | Time-box discovery; pin doc links to reviewed vendor pages; smoke-test Cursor + one Claude path |
| `.vscode/mcp.json` wrong for some VS Code versions | Gate Copilot file emission on confirmed schema; default to doc-only |
| Merge conflicts with operator-custom MCP servers | Strict merge: only touch `mcpServers["wavefoundry"]` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
