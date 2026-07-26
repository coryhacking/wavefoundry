# Cwd Independent Mcp Server Stanzas

Change ID: `1tjjl-bug cwd-independent-mcp-server-stanzas`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-25
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Every rendered MCP registration names the server by a repo-relative argument,
`.wavefoundry/framework/scripts/server.py`, and only one host pins a working directory:

| Host | Surface | Working-directory anchor |
| ---- | ------- | ------------------------ |
| Claude | `.mcp.json` | none |
| Codex | `.codex/config.toml` | none |
| Antigravity | `.agents/mcp_config.json` | none |
| Junie | `.junie/mcp/mcp.json` | none |
| Cursor | `.cursor/mcp.json` | `"cwd": "${workspaceFolder}"` |

The Cursor pin exists because the relative argument does not resolve unless the client happens to
spawn the server from the workspace root. Four hosts carry the same unanchored argument without that
protection.

This is the same defect class as the hook failure repaired in `1tjjk-bug`, but the severity is
different and should not be overstated. The hook failure is confirmed and reproduced. The MCP
exposure is currently latent: MCP clients normally spawn the server with the workspace root as
working directory, which is why the server works today on this repository. The exposure is that
nothing in the rendered configuration enforces that assumption, and the assumption is host behavior
the framework does not control.

`render_mcp_json` already reasons about this correctly for the root resolution: `server.py` anchors
on its own install location, so `--root` is resolved cwd-independently. That reasoning covers what
happens *after* the interpreter opens the file. It does not cover the interpreter finding the file in
the first place, which is the gap here.

## Requirements

1. Every rendered MCP stanza locates `server.py` when spawned from the repository root or any
   descendant directory. Launches from outside the repository succeed only where a host provides a
   verified project-root or working-directory anchor; otherwise the bootstrap fails clearly instead
   of selecting or guessing a repository.
2. No stanza embeds a machine-absolute path. Every distributed MCP registration is Git-tracked and
   platform-neutral: one deterministic committed artifact per host, with any official OS-specific
   fields contained inside that artifact rather than emitted as per-platform files.
3. The `server.py` self-anchoring root resolution continues to work unchanged.
4. Rendered-host coverage, in priority order: Claude, Codex, Antigravity, Junie, Cursor. The
   hand-committed self-hosted Air stanza is included in the migration and standing census even though
   Air remains instruction-only in the distributable platform matrix.
5. Cursor's existing `cwd` pin is either retained as defense in depth or removed deliberately, with
   the choice recorded, not left inconsistent by accident.
6. Native Windows, WSL2, macOS, and Linux are equal required delivery targets. WSL2 is executed as
   its own environment rather than inferred from Linux, and a missing runner blocks delivery.

## Scope

**Problem statement:** Four of five rendered MCP registrations depend on an unstated assumption that
the host spawns the server from the workspace root, and nothing in the rendered configuration
enforces it.

**In scope:**

- Implement an MCP-specific, shell-free argument-vector locator. It may share pure project-root
  selection semantics with the host-specific hook adapters in `1tjjk-bug`, but it does not reuse or
  force one hook command serialization across unlike host contracts.
- Update `render_mcp_json`, `render_junie_mcp_json`, `render_cursor_mcp_json`,
  `render_antigravity_mcp_json`, and the Codex renderer relocated by `1tjjj-bug`.
- Settle and record the Cursor `cwd` decision.
- Re-render all five committed MCP surfaces.
- Update the hand-committed `.air/mcp.json` in place and keep it in the on-disk configuration census;
  this does not introduce an Air renderer or change Air's instruction-only product status.
- Update `AGENTS.md`'s copy-ready stdio entry and the per-host registration table so the documented
  manual-attachment form matches what the renderer emits.
- Execute every applicable MCP stanza on native Windows, WSL2, macOS, and Linux from repository-root,
  descendant, and space-containing paths. WSL2 separately covers a Linux-filesystem checkout and a
  `/mnt/<drive>` checkout.
- Keep all distributed MCP registrations in the committed surface census and reject platform-specific
  sibling configs or an untracked launcher required for normal operation.

**Out of scope:**

- Hook commands, covered by `1tjjk-bug`.
- Renderer ownership, covered by `1tjjj-bug`, which lands first and is what brings the Codex stanza
  into scope for a single uniform fix.
- Changing `server.py` root resolution, which is already cwd-independent and correct.

The planned root-signal contract is:

| Host | Root behavior |
| ---- | ------------- |
| Cursor | Retain `${workspaceFolder}` as the verified cwd anchor unless implementation evidence justifies removal |
| Claude, Codex, Antigravity, Junie | Resolve from repository-root or descendant cwd; do not assume an undocumented outside-repository signal |
| Air | Same bootstrap in the hand-committed self-hosted config; no new renderer or distribution promise |

The delivery evidence includes a host/platform matrix with `pass`, `fail`, or `not_applicable` for
every cell. `not_applicable` requires a cited vendor limitation. Parser success, patched `os.name`,
ordinary Linux, and a container do not substitute for real native Windows, WSL2, macOS, or Linux
execution.

## Acceptance Criteria

- [ ] AC-1: A red test spawns each current unpinned rendered stanza from a nested repository
  subdirectory and asserts the server starts. It fails against the current relative form before the
  fix because the interpreter cannot locate `server.py`, then passes through the bootstrap.
- [ ] AC-2: After the fix, each of the five rendered stanzas and the committed Air stanza starts the
  server from the repository root and a nested subdirectory. From an unrelated directory, a stanza
  succeeds only when the host's verified cwd/root anchor is applied; an unanchored stanza fails with
  a clear project-root diagnostic. The hermetic test appends `--dry-run` and executes the parsed
  command and args rather than attempting a long-lived stdio session.
- [ ] AC-3: `server.py` still resolves the repository root to the correct path when launched through
  the new stanza, asserted against the server's own reported root rather than assumed.
- [ ] AC-4: No rendered stanza or the committed Air stanza contains an absolute path or an
  unsupported host expansion token. Cursor's verified `cwd` is permitted if AC-6 retains it. Verified
  by parsing each config file.
- [ ] AC-5: Stanzas are byte-identical when rendered under a patched POSIX and a patched
  native-Windows `os.name`; real Windows, WSL2, macOS, and Linux renders are also compared before
  delivery. Official OS-specific fields coexist in the same committed host artifact.
- [ ] AC-6: The Cursor `cwd` pin is explicitly retained or removed, with the rationale recorded in
  the Decision Log and the renderer docstring. Whichever is chosen, Cursor passes AC-2.
- [ ] AC-7: The `AGENTS.md` copy-ready stdio entry matches the renderer output for the
  instruction-only hosts, verified by a test comparing the documented form against the rendered form
  so the two cannot drift.
- [ ] AC-8: Evidence distinguishes three layers instead of treating them as interchangeable:
  config parsing, hermetic execution of parsed command/args, and actual host consumption. Each named
  host is classified as live-verified, official-schema/documentation-verified, or not externally
  verified; no unavailable host is claimed as live-tested.
- [ ] AC-9: The completed MCP host/platform matrix contains real execution evidence for native
  Windows, WSL2, macOS, and Linux. Every applicable stanza starts from repository-root, descendant,
  and space-containing paths; Windows exercises native path syntax; WSL2 separately passes a
  Linux-filesystem checkout and a `/mnt/<drive>` checkout. A failed or unexecuted required cell blocks
  delivery rather than becoming a best-effort support note.
- [ ] AC-10: `git ls-files` contains every distributed MCP registration, and clean renders on native
  Windows, WSL2, macOS, and Linux produce byte-identical tracked artifacts. No `.windows`, `.wsl`,
  `.macos`, `.linux`, ignored, or user-home launcher/config is required for normal operation. Runtime
  credentials, trust state, caches, indexes, and virtual environments remain intentionally untracked.
- [ ] AC-11: An **existing** target repository that upgrades has its unanchored MCP stanzas replaced by
  the corrected anchored forms, for every host this change renders, proven by a seeded
  old-pack-to-new-pack fixture and asserted after a **single** upgrade. A fresh-install render does not
  satisfy this AC. Required because upgrade Phase 1 runs `render_platform_surfaces.py` and this
  repository has a documented old-code-window hazard in which the orchestrator executes pre-upgrade
  code — the mechanism that silently skipped scheme-v2 provisioning in the field. Because the MCP
  exposure is latent rather than an observed outage, an upgrade that silently defers the fix would be
  invisible until a host happens to spawn from a non-root working directory.

## Tasks

- [ ] Write the AC-1 red test across the unpinned rendered hosts and confirm each fails because the
  interpreter cannot find the relative `server.py`, not because of server initialization.
- [ ] Implement the MCP argument-vector locator. Share only root-selection semantics that are truly
  common with `1tjjk-bug`; keep hook and MCP serialization separate.
- [ ] Update the four platform MCP renderers plus the relocated Codex renderer.
- [ ] Settle the Cursor `cwd` question and record it.
- [ ] Re-render all five surfaces and inspect the diff.
- [ ] Update `.air/mcp.json` and the standing committed-config census alongside the rendered surfaces.
- [ ] Update the `AGENTS.md` MCP table and copy-ready entry, and add the anti-drift test.
- [ ] Record per-host consumption evidence at its honest level; use live host smoke evidence where
  available and official schema/documentation evidence otherwise.
- [ ] Run and retain the four-environment platform matrix, including both required WSL2 checkout
  locations and space-containing paths.
- [ ] Add the committed MCP surface census and reject per-platform or per-machine registration files.
- [ ] Build the AC-11 seeded old-pack-to-new-pack upgrade fixture proving each host's unanchored stanza
  is replaced after a single upgrade, and confirm whether the old-code window defers it.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Four unpinned rendered hosts; confirm the relative-path failure |
| mcp-locator | implementer | red-test | Shell-free argument vector; no hook serialization coupling |
| host-renderers | implementer | mcp-locator | Claude, Codex, Antigravity, Junie, Cursor in priority order |
| cursor-decision | implementer | host-renderers | Retain or remove `cwd`, recorded either way |
| docs-parity | implementer | host-renderers | `AGENTS.md` entry plus anti-drift test |
| platform-matrix | implementer | host-renderers | Real Windows, WSL2, macOS, and Linux startup evidence |

## Serialization Points

- `render_platform_surfaces.py` is shared with `1tjjj` and `1tjjk`; sequence this change last.
- Root-selection semantics must agree with `1tjjk-bug`, but MCP and hook serialization remain
  separate. `1tjjk` still lands first so this change consumes the settled ownership rules.
- Five committed MCP surfaces are regenerated here and must not be hand-edited.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` and the `AGENTS.md` MCP registration table need the corrected
stdio entry. No ADR is required: this closes an unstated assumption in an existing design rather than
changing the transport or registration model.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Reproduces the relative-path failure before changing the launcher. |
| AC-2 | required | Proves the supported cwd contract across rendered and committed surfaces. |
| AC-3 | required | Preserves the server's correct self-anchored root. |
| AC-4 | required | Preserves portable, project-relative tracked configuration. |
| AC-5 | required | Prevents per-render-host configuration divergence. |
| AC-6 | required | Makes the Cursor anchor decision explicit. |
| AC-7 | required | Keeps instruction-only setup aligned with generated forms. |
| AC-8 | required | Prevents hermetic subprocess evidence from being overstated as client compatibility. |
| AC-9 | required | Makes all four operating environments first-class MCP startup gates. |
| AC-10 | required | Ensures first-class MCP support ships as one portable, version-controlled surface. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Pre-implementation review revisions: bounded cwd contract, separate host-consumption evidence, and Air census coverage added | Readiness findings `mcp-launcher-lacks-project-identity`, `host-config-tests-do-not-validate-host-consumption`, and `air-mcp-config-omitted-from-surface-census` |
| 2026-07-25 | Added native Windows, WSL2, macOS, and Linux as equal MCP delivery gates and decoupled MCP serialization from the withdrawn shared hook resolver | Operator first-class platform requirement and reconciled `1tjjk-bug` adapter design |
| 2026-07-25 | Required one Git-tracked, platform-neutral MCP artifact per host | Operator clarified that first-class support must not depend on per-platform generated files |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Treat the MCP exposure as latent rather than a confirmed outage | The server runs correctly today on this repository, so claiming an active failure would misstate the evidence. The defect is that correctness depends on unenforced host behavior. | Report it as broken, rejected as unsupported by observation; leave it alone, rejected because Cursor's existing `cwd` pin shows the assumption already failed for at least one host. |
| 2026-07-25 | Share root-selection semantics, not one serialized resolver, between hooks and MCP stanzas | Hooks have host-native cwd/root fields while MCP clients consume shell-free command/argument vectors. Coupling their serialized commands would erase useful host guarantees. | One shared serialized resolver, rejected after host-contract review; unrelated root-selection rules, rejected for ownership drift. |
| 2026-07-25 | Bound MCP cwd independence to repository descendants plus verified host anchors | The Python bootstrap can start from any descendant and walk to the project. From an unrelated directory, a project-relative stanza has no information identifying its owning checkout unless the host supplies an anchor. | Preserve the arbitrary-cwd claim, rejected as unsupported; embed a machine-absolute path, rejected by the tracked-surface portability contract. |
| 2026-07-25 | Include `.air/mcp.json` as a committed self-hosted surface without adding an Air renderer | The standing census already treats it as part of the runtime-entry surface, but Air remains provider-specific and instruction-only for distribution. | Omit it, rejected because it would retain the old command and break the census; add a generic Air renderer, rejected as unsupported product scope. |
| 2026-07-25 | Require real execution on Windows, WSL2, macOS, and Linux | MCP startup crosses executable lookup, argument quoting, path syntax, and process cwd boundaries that parser tests cannot prove. | Infer WSL2 from Linux or simulate platforms, rejected as insufficient for a first-class support claim. |
| 2026-07-25 | Keep platform variants inside the canonical committed host config | A clone must contain the complete registration contract before any local setup runs; official OS override fields preserve one reviewable authority. | Per-platform generated configs or a user-home locator, rejected because neither is a portable Git-tracked project surface. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A `-c` argument vector is rejected by a specific MCP client's schema | AC-8 separates direct execution from client consumption; use live or official-schema evidence and record a per-host adapter when required. |
| Codex TOML quoting differs from JSON | AC-2 executes the parsed Codex stanza; AC-4 parses the TOML; AC-8 separately records whether Codex itself consumed it. |
| Changing a working registration breaks a host that was fine | AC-1 records which hosts already pass, so any regression is attributable; Cursor's pin is changed only under AC-6 with an explicit decision. |
| CI covers three operating systems but silently omits WSL2 | AC-9 requires real WSL2 evidence for both Linux-filesystem and mounted-drive checkouts; missing access blocks delivery. |
| An MCP stanza works only because of untracked machine state | AC-10 verifies the committed census from a clean clone and rejects platform-specific or user-home launcher dependencies. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
