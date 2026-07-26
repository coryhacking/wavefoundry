# Cwd Independent Hook Launcher Commands

Change ID: `1tjjk-bug cwd-independent-hook-launcher-commands`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-25
Wave: `1tj0l cwd-independent-host-surface-launchers`

## Rationale

Every rendered agent-host hook command names its script by a repo-relative path:

```
python3 ".claude/hooks/pre-edit.py"
```

The host launches hooks with the working directory of the current session shell, not a fixed project
root. Any working-directory change that persists in a session therefore breaks every hook for the
rest of that session. This was observed in the field: all three Claude hooks failed with
`can't open file '<repo>/.wavefoundry/framework/scripts/.claude/hooks/session-capture.py'` after a
session had changed directory into the framework scripts folder. The hook body was never reached, so
the framework edit gates and docs gates silently stopped running.

The first revision proposed one `python3 -c` resolver for every host. Contract review showed that
this would discard useful host guarantees and create exactly the kind of opaque command string that
enterprise policy reviewers have to scrutinize. The hosts do not expose one common hook contract:
Claude, Copilot, Cursor, Windsurf, and Codex each provide a project anchor or working-directory
control; Junie exposes EAP CLI hooks only through an explicitly selected config; Air and Warp run
underlying agents but do not publish a separate project lifecycle-hook format.

The repair therefore uses a small per-host adapter matrix. It prefers the host's native root/cwd
facility, keeps tracked surfaces project-relative, and records delegated hosts honestly instead of
inventing configuration they do not consume. A machine-absolute repo path remains excluded by wave
1p590. A user-home locator under `~/.wavefoundry/bin` and a shared inline Python resolver are not part
of the design.

## Requirements

1. Native Windows, WSL2, macOS, and Linux are equal release targets. Each hook adapter locates its
   script body correctly when the host starts at the repository root or a descendant directory and
   after the session changes directory. WSL2 is verified independently, not inferred from Linux.
2. Prefer native argv, project-root, and working-directory fields over inline resolver code. No
   tracked surface embeds a machine-absolute repository path, and no shared launcher is installed in
   the user's home directory.
3. Hook bodies continue to resolve the repository root from their own location, so the existing
   `parents[2]` derivation and the first-line venv bootstrap keep working unchanged.
4. When the root genuinely cannot be determined, the hook fails with a message naming the missing
   root and the hook, not an interpreter traceback.
5. The coverage census includes Claude, Copilot, Cursor, Windsurf, Codex, Junie, Air, and Warp. Every
   host is classified as native, explicit opt-in, delegated, or unsupported; coverage never implies
   that every host receives a standalone hook file.
6. Each host-root selection rule chooses the nearest owning project. A nested, independently
   installed Wavefoundry project therefore owns its own hooks; an ordinary subproject directory
   without its own installation resolves to the enclosing project.
7. Trust and activation requirements are part of the delivered contract: Codex project hooks require
   project trust and per-definition hook review; Junie project hooks require an explicit
   `--config-location` selection and apply only to the Junie CLI modes that execute hooks.
8. A host/platform pair may be `not_applicable` only when the host vendor does not ship that host on
   the platform. Wavefoundry may not label a shipped pair experimental, best-effort, or supported by
   similarity to another platform. A failed required platform probe blocks delivery.
9. Every distributed hook config and hook body is Git-tracked and platform-neutral. Wavefoundry
   renders one deterministic project artifact per host, not separate Windows, WSL2, macOS, or Linux
   files. When a host schema supports OS-specific fields, all variants coexist in that one committed
   artifact.

## Scope

**Problem statement:** Hook commands are resolved against the session working directory, so a
persisted directory change disables every framework hook for the rest of the session, with no
diagnostic beyond a file-not-found error.

**In scope:**

- Replace the single `launcher_command` assumption with typed per-host serialization helpers. Reuse a
  shared semantic description of the Wavefoundry hook, not one shared command string.
- Correct and re-render the four existing hook surfaces: `.claude/settings.json`,
  `.github/hooks/hooks.json`, `.cursor/hooks.json`, and the Windsurf hook entries.
- Add repo-local Codex lifecycle hooks at `.codex/hooks.json`, using Codex's documented git-root
  command on POSIX and `commandWindows` on native Windows. Keep hooks separate from
  `.codex/config.toml`, and document project trust plus `/hooks` review.
- Add a Junie CLI EAP hook config at `.junie/wavefoundry-hooks.json`. Do not place hooks in the normal
  `.junie/config.json` and claim they load: Junie deliberately ignores hooks from that default project
  config. Render the explicit activation command using `--config-location`, and prove the hook command
  has a stable project anchor before claiming cwd independence. Junie IDE, ACP, and server modes remain
  outside the hook claim unless an executed contract probe proves otherwise.
- Add Air and Warp to the coverage census as delegated hosts. Air consumes the selected agent's own
  project configuration; Warp can run third-party CLI agents. Do not generate `.air/hooks*` or
  `.warp/hooks*` without an official native contract.
- Add a required platform verification matrix for native Windows, WSL2, macOS, and Linux. Cover both
  repository-root and descendant cwd, a repository path containing spaces, native path syntax, and
  the actual shell/argv behavior used by each host. WSL2 covers a Linux-filesystem checkout and a
  `/mnt/<drive>` checkout so cross-filesystem path handling is not assumed.
- Keep the resulting hook configs and bodies in the committed surface census. Do not generate
  `.windows`, `.wsl`, `.macos`, `.linux`, or other per-machine sibling files; encode a host's official
  OS override inside its canonical config when needed.
- Emit a clear diagnostic when no candidate root is found.
- Update the existing invariant tests that pin the old command shape.
- Re-render the committed hook surfaces.

The adapter contract is deliberately host-specific:

| Host | Coverage tier | Root/cwd contract | Rendered surface |
| ---- | ------------- | ----------------- | ---------------- |
| Claude Code | native | Native command/args form with `${CLAUDE_PROJECT_DIR}` substitution; no shell interpolation | `.claude/settings.json` |
| GitHub Copilot / VS Code | native | Hook `cwd` anchored to the workspace root; cross-platform command with an OS-specific override only where the schema requires it | `.github/hooks/hooks.json` |
| Cursor | native | Project hooks execute from the project root | `.cursor/hooks.json` |
| Windsurf | native | `working_directory` anchored to the workspace root | renderer-owned Windsurf hook entries |
| Codex | native, trust-gated | Repo-local hooks resolve from Git root; `commandWindows` supplies the native-Windows form | `.codex/hooks.json` |
| Junie CLI | explicit opt-in, EAP | Explicit `--config-location`; implementation must prove a stable project anchor on POSIX and Windows before claiming support | `.junie/wavefoundry-hooks.json` |
| JetBrains Air | delegated | Selected Claude, Codex, or Junie agent owns lifecycle behavior; Air has no separate native hook file in scope | no hook surface |
| Warp | delegated | Third-party Claude or Codex CLI owns lifecycle behavior; Warp's native agent has no documented project hook contract in scope | no hook surface |

Platform support is orthogonal to that host tier:

| Platform | First-class verification boundary |
| -------- | ------------------------------- |
| Native Windows | Real Windows execution with drive-letter and backslash paths, a path containing spaces, and the host's documented PowerShell, Git Bash, `cmd`, or `commandWindows` boundary as applicable |
| WSL2 | Real WSL2 execution, separately covering a checkout in the Linux filesystem and under `/mnt/<drive>`; no path translation is inferred from native Windows or Linux results |
| macOS | Real macOS execution through the host's documented POSIX command boundary, including a path containing spaces |
| Linux | Real Linux execution through the host's documented POSIX command boundary, including a path containing spaces |

The implementation verification matrix records `pass`, `fail`, or `not_applicable` for every
host/platform pair. `not_applicable` requires a cited vendor availability limitation; missing access
to a runner is not `not_applicable` and blocks delivery.

Implementation must re-check the current vendor contracts before editing because Junie hooks are EAP
and Codex hooks are new. The reviewed sources are the official
[Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Junie hooks](https://junie.jetbrains.com/docs/junie-cli-hooks.html),
[Junie configuration](https://junie.jetbrains.com/docs/junie-cli-configuration.html),
[Air supported agents](https://www.jetbrains.com/help/air/supported-agents.html),
[Air platform setup](https://www.jetbrains.com/help/air/set-up.html),
[Warp agent capabilities](https://docs.warp.dev/agent-platform/capabilities), and
[Warp supported shells](https://docs.warp.dev/getting-started/supported-shells) documentation.

**Out of scope:**

- MCP server stanzas, covered by `1tjjl-bug`.
- Renderer ownership, covered by `1tjjj-bug`, which lands first.
- New hook policy. Existing Wavefoundry hook behavior is mapped only to semantically equivalent host
  events; unsupported event mappings are reported rather than approximated.
- A global locator or launcher under `~/.wavefoundry/bin`.
- Native Air or Warp hook files unless their vendors publish and the implementation verifies such a
  contract before this wave begins implementation.

## Acceptance Criteria

- [ ] AC-1: A red test reproduces the field failure through the current Claude config. It invokes the
  configured hook from a descendant working directory, proves the existing relative command never
  reaches the body, and passes only when the native Claude project anchor selects the expected path.
- [ ] AC-2: Contract tests parse and execute each native surface according to that host's own schema:
  Claude command/args substitution, Copilot `cwd`, Cursor project-root cwd, Windsurf
  `working_directory`, and Codex `command`/`commandWindows`. A generic subprocess test that bypasses
  the host field responsible for correctness does not satisfy this AC.
- [ ] AC-3: The Copilot surface is no longer `bash`-only. POSIX and native-Windows forms both execute
  the same hook semantics from a descendant directory, and the config remains valid under the
  published VS Code/Copilot hook schema.
- [ ] AC-4: No rendered hook surface contains a machine-absolute repository path or depends on a
  `~/.wavefoundry/bin` install. OS-specific fields may differ where the host schema explicitly
  supports them; portable fields remain deterministic across render hosts. Existing byte-identity and
  `$CLAUDE_PROJECT_DIR` assertions are updated to the new per-host contract rather than deleted. The
  committed-surface census proves there is one canonical config per host and no platform-specific
  sibling artifact.
- [ ] AC-5: A hook body launched through the new command still resolves `parents[2]` to the
  repository root and still activates the tool venv. Proven by executing a real rendered hook body
  from a nested working directory and asserting on its resolved root, not by inspection.
- [ ] AC-6: Codex renders `.codex/hooks.json` with the equivalent session, pre-edit, and post-edit
  lifecycle mappings supported by Codex. Both command variants resolve from a descendant cwd; the
  config remains project-relative; and docs state that project trust and `/hooks` review are required
  before the hooks run.
- [ ] AC-7: The Claude settings and simulate-map parity test still passes, so every rendered hook
  remains dry-runnable through `.claude/hooks/simulate-hooks.py`.
- [ ] AC-8: A nested ordinary subproject resolves to the enclosing project's hook, while a nested
  independently installed Wavefoundry project resolves to its own nearest hook. Both cases are
  executed so the host-root selection rule is explicit and regression-protected.
- [ ] AC-9: Junie renders only the explicit opt-in `.junie/wavefoundry-hooks.json` surface and an
  activation instruction using `--config-location`. An executed POSIX and native-Windows contract
  probe must prove that its command reaches the expected project hook after a cwd change. Junie must
  pass the full Windows, WSL2, macOS, and Linux matrix; a missing stable anchor or runner blocks the
  wave rather than producing a fragile relative command or a downgraded support claim.
- [ ] AC-10: Air and Warp are present in the host census without invented native hook files. Tests
  pin their delegated status, docs name which underlying agents carry Wavefoundry hooks, and native
  Air/Warp agents are not described as protected by hooks without executed evidence.
- [ ] AC-11: The event-mapping table is tested against every rendered host. Missing or non-equivalent
  events fail closed in the renderer or appear as an explicit limitation; they are not silently mapped
  to a nearby event with different blocking semantics.
- [ ] AC-12: The completed host/platform matrix contains an executed result for native Windows,
  WSL2, macOS, and Linux. Required pairs pass from repository root, descendant cwd, and a path with
  spaces. Windows uses native path syntax; WSL2 separately passes Linux-filesystem and `/mnt/<drive>`
  checkouts. A simulated `os.name`, patched path class, container standing in for WSL2, or parser-only
  config test may supplement but cannot replace the real platform execution evidence.
- [ ] AC-13: A clean render on native Windows, WSL2, macOS, and Linux produces byte-identical tracked
  files. `git ls-files` contains every distributed hook config and body, and the render leaves no
  untracked or ignored platform-specific launcher needed for normal operation. Runtime trust records,
  credentials, caches, indexes, and virtual environments are explicitly excluded from this source
  portability requirement.
- [ ] AC-14: An **existing** target repository that upgrades has its stale relative-path hook commands
  replaced by the corrected per-host forms, for every host this change renders, proven by a seeded
  old-pack-to-new-pack fixture and asserted after a **single** upgrade. A fresh-install render does not
  satisfy this AC. Required because upgrade Phase 1 runs `render_platform_surfaces.py` and this
  repository has a documented old-code-window hazard in which the orchestrator executes pre-upgrade
  code — the mechanism that silently skipped scheme-v2 provisioning in the field. Without this, every
  already-installed project keeps broken hooks until a second upgrade, with no diagnostic, which is
  precisely the silent failure this change exists to remove. If the window is confirmed to apply, the
  repair belongs to this change rather than a follow-up.

## Tasks

- [ ] Write the AC-1 red test and confirm it fails for the stated reason before editing the renderer.
- [ ] Replace `launcher_command` with per-host serializers that preserve the native schema fields and
  keep the existing hook bodies unchanged.
- [ ] Add the Codex hook renderer and event mapping, including `commandWindows`, trust guidance, and
  project-local merge behavior for `.codex/hooks.json`.
- [ ] Add the explicit Junie CLI hook config and activation guidance; run the required contract probes
  before marking either operating system supported.
- [ ] Add Air and Warp to the host capability census and docs as delegated hosts; assert that no
  unsupported native hook file is rendered.
- [ ] Add the four-platform verification harness and CI/runner matrix. Retain machine-readable
  host/platform results as delivery evidence, including cited `not_applicable` cells.
- [ ] Add a committed-surface census and cross-platform render comparison that reject per-OS or
  per-machine hook artifacts.
- [ ] Build the AC-14 seeded old-pack-to-new-pack upgrade fixture proving each host's stale relative
  hook command is replaced after a single upgrade, and determine whether the documented old-code window
  defers it. If it does, repair it in this change rather than shipping a one-upgrade-late fix.
- [ ] Add the not-found diagnostic path.
- [ ] Update `LauncherCommandTests`, event-map tests, schema fixtures, and host-specific invariants to
  the adapter contract.
- [ ] Re-render all hook surfaces and inspect the diff.
- [ ] Update `docs/references/native-windows-support.md` item C-3 and the `launcher_command`
  documentation to record the superseding per-host decision and the delegated-host boundary.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Must fail first, naming the resolved path |
| existing-host-adapters | implementer | red-test | Claude, Copilot, Cursor, Windsurf plus Windows correction |
| codex-adapter | implementer | red-test | Repo hooks, event map, trust, and Windows override |
| junie-probe-and-adapter | implementer | red-test | EAP opt-in surface; support claim follows executed probes |
| delegated-host-census | implementer | — | Air and Warp classification, no invented files |
| platform-matrix | implementer | all adapters | Real Windows, WSL2, macOS, and Linux execution |
| test-contract | implementer | all adapters, platform-matrix | Host-schema execution, event parity, nested ownership |
| re-render | implementer | test-contract | Native and opt-in surfaces only |
| docs | implementer | all adapters | C-3 supersession, activation, trust, and limitations |

## Serialization Points

- `render_platform_surfaces.py` is shared with `1tjjj` and `1tjjl`; sequence after `1tjjj`.
- Committed hook surfaces are regenerated here and must not be hand-edited.

## Affected Architecture Docs

`docs/references/native-windows-support.md` item C-3 needs a supersession note. No ADR is required:
the cross-OS byte-identity constraint set is unchanged, and this change satisfies it by a different
mechanism rather than revisiting the decision.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Reproduces the confirmed field failure before the fix. |
| AC-2 | required | Proves the host fields that actually make each native adapter cwd-independent. |
| AC-3 | required | Closes the existing Copilot native-Windows gap. |
| AC-4 | required | Preserves portable tracked surfaces without a global locator. |
| AC-5 | required | Proves the real hook body and venv bootstrap still execute. |
| AC-6 | required | Adds Codex on its documented repo-local and trust-gated surface. |
| AC-7 | required | Preserves the existing Claude simulation contract. |
| AC-8 | required | Makes nearest-project selection deterministic for ordinary and nested projects. |
| AC-9 | required | Adds Junie without pretending its default project config or unsupported modes run hooks. |
| AC-10 | required | Adds Air and Warp to coverage without fabricating native contracts. |
| AC-11 | required | Prevents semantic drift while mapping Wavefoundry hooks to new host events. |
| AC-12 | required | Makes all four operating environments first-class release gates. |
| AC-13 | required | Ensures first-class support ships as one portable, version-controlled surface. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Pre-implementation review revisions: bootstrap execution boundary, descendant-cwd contract, verified host-signal matrix, and nested-project ownership added | Readiness findings `hook-root-contract-is-contradictory` and `mcp-launcher-lacks-project-identity` |
| 2026-07-25 | Expanded host coverage to Codex, Junie, Air, and Warp; replaced the generic inline resolver with native, opt-in, and delegated adapter tiers | Official host hook/config contracts reviewed; operator requested all four hosts in this wave |
| 2026-07-25 | Made native Windows, WSL2, macOS, and Linux equal required delivery targets | Operator required first-class support; vendor availability checked before defining the matrix |
| 2026-07-25 | Required one Git-tracked, platform-neutral artifact per host | Operator clarified that first-class support must not depend on per-platform generated files |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Use per-host adapters instead of one `python3 -c` resolver | Native root/cwd fields are shorter, reviewable, and carry stronger host semantics. One opaque command would throw those guarantees away and add enterprise-policy friction. | Shared inline Python resolver, rejected as unnecessarily complex for hosts with native anchors; user-home locator, rejected because it adds untracked global installation state. |
| 2026-07-25 | Render Codex hooks in `.codex/hooks.json`, separate from `.codex/config.toml` | Codex documents repo-local hook discovery, trust review, Git-root resolution, and a Windows command override. A separate file avoids mixing two hook representations in one config layer. | Inline `[hooks]`, rejected because it couples lifecycle and MCP ownership and can trigger merge warnings when a hook file also exists; plugin packaging, deferred because it adds an installation boundary not needed for project-local hooks. |
| 2026-07-25 | Treat Junie as an explicit opt-in EAP adapter | Junie deliberately ignores hooks in the default project config; `--config-location` is the documented explicit selection. Support must follow an executed stable-root probe, not an assumed cwd. | Put hooks in `.junie/config.json`, rejected because they will not run; modify `~/.junie/config.json`, rejected as global user state; claim IDE/ACP coverage, rejected because those modes do not share the CLI hook guarantee. |
| 2026-07-25 | Treat Air and Warp as delegated hosts | Their documented integrations run an underlying agent and do not define a separate project lifecycle-hook file. The underlying Claude, Codex, or Junie contract remains the authority. | Invent `.air/hooks` or `.warp/hooks`, rejected because neither host documents consuming it. |
| 2026-07-25 | Gate delivery on four real platform environments | Quoting, path syntax, shell selection, and WSL2 mount behavior are execution properties that parser tests or patched `os.name` cannot prove. | Treat WSL2 as Linux, rejected because its mounted-drive and Windows-host boundary are distinct; accept simulated platform tests, rejected as insufficient for a first-class support claim. |
| 2026-07-25 | Keep OS variants inside one committed host artifact | Git-tracked portable configuration is reviewable, upgradeable, and identical for every clone. Host-native override fields can express platform differences without producing platform-specific files. | Generate per-OS configs, rejected because clones and reviews would not share one authority; install a global launcher, rejected because it is outside project version control. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A native host contract changes after release | Pin schema-shaped fixtures, retain official-source links in implementation notes, and fail the renderer when required fields are unavailable. |
| Codex hooks are present but never trusted | Installation/upgrade output names `/hooks`; tests distinguish rendered from activated state. |
| Junie's EAP hook contract lacks a stable cross-platform root | AC-9 blocks delivery until all four required platform probes have a stable solution; no fragile command or downgraded support claim is allowed. |
| Delegated Air/Warp coverage is mistaken for native enforcement | The census and user docs label the tier and underlying agent on every claim; no native hook file is rendered. |
| CI covers Windows/macOS/Linux but silently treats WSL2 as Ubuntu | AC-12 requires real WSL2 evidence for both Linux-filesystem and mounted-drive checkouts. |
| A platform probe passes only because of an untracked local launcher | AC-13 compares clean renders and tracked files, and rejects any normal-operation dependency outside the committed project surface. |
| A host-root rule selects a different nested installation | AC-8 defines nearest installed project as the owner and distinguishes it from an ordinary subproject folder. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
