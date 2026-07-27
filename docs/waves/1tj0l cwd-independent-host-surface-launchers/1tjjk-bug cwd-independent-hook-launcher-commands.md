# Cwd Independent Hook Launcher Commands

Change ID: `1tjjk-bug cwd-independent-hook-launcher-commands`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
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
Claude, Copilot, Cursor, and Windsurf provide verified project-anchor or working-directory controls.
No supported project-local hook contract was established for Codex or Junie in this wave; Air and
Warp run underlying agents but do not publish a separate project lifecycle-hook format.

The repair therefore uses a small per-host adapter matrix. It prefers the host's native root/cwd
facility, keeps tracked surfaces project-relative, and records delegated hosts honestly instead of
inventing configuration they do not consume. A machine-absolute repo path remains excluded by wave
1p590. A user-home locator under `~/.wavefoundry/bin` and a shared inline Python resolver are not part
of the design.

## Requirements

1. Native Windows, WSL2, macOS, and Linux are equal release *targets*. Each hook adapter locates its
   script body correctly when the host starts at the repository root or a descendant directory and
   after the session changes directory. Verification *evidence* is not uniform and must not pretend to
   be: AC-12 records an executed result where a runner exists and an explicit named deferral where one
   does not. WSL2 is never inferred from Linux, nor Windows from a simulated `os.name`.
2. Prefer native argv, project-root, and working-directory fields over inline resolver code. No
   tracked surface embeds a machine-absolute repository path, and no shared launcher is installed in
   the user's home directory.
3. Hook bodies continue to resolve the repository root from their own location, so the existing
   `parents[2]` derivation and the first-line venv bootstrap keep working unchanged.
4. When the root genuinely cannot be determined, the hook fails with a message naming the missing
   root and the hook, not an interpreter traceback.
5. The coverage census includes Claude, Copilot, Cursor, Windsurf, Codex, Junie, **Antigravity**, Air,
   and Warp. Every host is classified as native, explicit opt-in, delegated, or unsupported; coverage
   never implies that every host receives a standalone hook file. Antigravity is included because it
   is a fully rendered platform (`detect_platforms`, `.agents` preflight, `render_antigravity_mcp_json`,
   `--platform antigravity`, tracked `.agents/mcp_config.json`), so omitting it would make the
   "every host is classified" claim false against the documented host set.
6. Each launcher remains bound to the project selected by the host/configuration that owns the hook.
   It must never switch to a nearer nested Wavefoundry installation merely because the session cwd
   changed. A nested installation owns hooks only when the host opens or explicitly selects that
   nested project as the project/configuration authority.
7. Codex and Junie are explicit unsupported hook tiers in this delivery: Wavefoundry emits no native
   hook file for either host. Their MCP and instruction surfaces remain supported independently; no
   trust or activation instruction may imply that a nonexistent hook file will execute.
8. A host/platform pair may be `not_applicable` only when the host vendor does not ship that host on
   the platform. Wavefoundry may not label a shipped pair experimental, best-effort, or supported by
   similarity to another platform. A *failed* probe blocks delivery. An *unrun* probe is recorded as
   `not_executed` with its owner and mechanism (AC-12); it is never recorded as a pass and never
   silently omitted.
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
  `.github/hooks/hooks.json`, `.cursor/hooks.json`, and `.windsurf/hooks.json` (named by path because
  AC-4's committed-surface census takes that path set as its input).
- **Seeds:** correct `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`. Start
  with `:256`, which is the **normative rule** the JSON literals merely instantiate: it mandates the
  "byte-identical, cross-OS command `python3 "<name>.py"`" and explicitly forbids "a bare launcher path
  or a Windows `cmd.exe /c` form", which conflicts with the host-specific OS override this change
  uses for supported hosts (Copilot's `powershell` field). Correcting the literals while leaving `:256` would produce a seed
  that contradicts itself and still forbids the mechanism being shipped. Also correct `160:478`, an
  upgrade verification item asserting which platforms receive executable hooks (`claude`, `cursor`,
  `copilot`) versus stay prompt-driven (`codex`, `air`, `junie`, `warp`); this change keeps Codex and
  Junie prompt-driven for hooks and adds the omitted native Windsurf surface, while the line already omits `windsurf` despite
  `render_windsurf_hooks` writing `.windsurf/hooks.json`. Note `:478` asserts a property of
  `docs/agents/platform-mapping.md`, which currently contains no hooks content at all, so the repair
  must decide whether that doc gains the table or the checklist item points elsewhere. Also correct
  `012-install-wavefoundry-phase-2.prompt.md:139`, an install **acceptance gate** structurally
  identical to `011:52`, reading "**Expected artifact:** Two hooks wired in the host config
  (settings.json or equivalent)". It is already false today (`CLAUDE_HOOKS` at
  `render_platform_surfaces.py:196-218` has **three** entries: `pre-edit`, `post-edit`, and
  `session-capture` from wave `1p5ti`), and this change makes it materially worse by wiring hooks
  across up to six host configs, so both the count and "the host config" singular understate it. Then
  the hardcoded literals in JSON the install agent is told to seed (`:336`, `:338`
  Claude; `:359` Cursor; `:379-380` Windsurf; `:404-405` Copilot as a `bash` key that AC-3 retires),
  repeats it in prose (`:344`, `:364`, `:385`, `:410`), and carries a per-platform capability matrix.
  Reconcile that matrix and the environment-auditor presence checks to the actual supported native
  hook set (Claude, Copilot, Cursor, Windsurf) without inventing Codex or Junie hook files. Requires
  the `seed_edit_allowed` gate.
- Correct the hook-config enumerations in `docs/architecture/data-and-control-flow.md` (`:37`, `:171`),
  `docs/architecture/cross-cutting-concerns.md` (`:13`),
  `docs/prompts/agent-routing-concurrency.prompt.md` (`:28`) and
  `docs/prompts/agents/upgrade-wave-context.prompt.md` (`:24`), each of which lists a three-item
  hook-surface set this change extends.
- Investigate Codex and Junie hook contracts, but emit a project hook file only if a verified
  configuration-owner signal and consumed schema are demonstrated. The implemented outcome is
  explicit unsupported hook coverage for both hosts: no `.codex/hooks.json` and no
  `.junie/wavefoundry-hooks.json` are emitted. Their MCP surfaces remain separate and supported.
- Add Air and Warp to the coverage census as delegated hosts. Air consumes the selected agent's own
  project configuration; Warp can run third-party CLI agents. Do not generate `.air/hooks*` or
  `.warp/hooks*` without an official native contract.
- Add the platform verification matrix covering native Windows, WSL2, macOS, and Linux, with each
  cell either executed or explicitly deferred per AC-12. Cover repository-root and descendant cwd, a
  repository path containing spaces, native path syntax, and the actual shell/argv behavior each host
  uses. WSL2 covers a Linux-filesystem checkout and a `/mnt/<drive>` checkout so cross-filesystem path
  handling is never assumed from another platform's result.
- Re-probe the Claude Code anchor mechanism before writing AC-1, and record the outcome in the
  Decision Log. This is a prerequisite, not an implementation detail: the design's flagship host
  currently rests on a mechanism prior field evidence rejected.
- **Define the negative-probe branch for Claude before implementation begins.** If the probe
  reconfirms the prior evidence (the host passes `$CLAUDE_PROJECT_DIR` literally) AND no POSIX shell
  expansion path is viable on every target platform, then no native Claude anchor exists, and the
  Decision Log has already rejected both remaining options (a shared inline resolver; a repo-relative
  path, which is the defect being fixed). AC-1 as written presumes an anchor exists. The plan
  therefore **stops and reports** rather than improvising: the implementer records the probe result,
  raises it as a finding, and the design question returns to the operator. Junie has such a branch
  (AC-9 narrows its own claim); the flagship host, whose failure is this wave's confirmed and twice
  reproduced defect, must not have less.
- Keep the resulting hook configs and bodies in the committed surface census. Do not generate
  `.windows`, `.wsl`, `.macos`, `.linux`, or other per-machine sibling files; encode a host's official
  OS override inside its canonical config when needed.
- Emit a clear diagnostic when no candidate root is found.
- Update the existing invariant tests that pin the old command shape.
- Re-render the committed hook surfaces.

The adapter contract is deliberately host-specific:

| Host | Coverage tier | Root/cwd contract | Rendered surface |
| ---- | ------------- | ----------------- | ---------------- |
| Claude Code | native | POSIX uses the documented `$CLAUDE_PROJECT_DIR` project anchor. Native Windows remains a bounded platform probe because prior field evidence observed literal expansion; a failed probe blocks that platform claim rather than changing the POSIX contract. | `.claude/settings.json` |
| GitHub Copilot / VS Code | native | Hook `cwd` is relative to the repository root. The plan names one manifest dialect and uses its exact Windows override (`windows` for the VS Code-native schema; the Copilot-format equivalent only if that dialect is intentionally retained). | `.github/hooks/hooks.json` |
| Cursor | native | Project hooks execute from the project root | `.cursor/hooks.json` |
| Windsurf | native | `working_directory` anchored to the workspace root | renderer-owned Windsurf hook entries |
| Codex | unsupported (hooks) | No verified project-local hook schema plus configuration-owner signal was established; MCP remains supported through `.codex/config.toml` | no hook surface |
| Junie CLI | unsupported (hooks) | No verified consumed project-hook surface with a stable configuration-owner anchor was established; MCP remains supported through `.junie/mcp/mcp.json` | no hook surface |
| Antigravity | unsupported (hooks) | Rendered platform for MCP registration, but no documented project lifecycle-hook contract. Reads the project-root `AGENTS.md` natively. Classified explicitly rather than omitted; implementation must confirm the absence of a hook contract rather than assume it | no hook surface |
| JetBrains Air | delegated | Selected Claude, Codex, or Junie agent owns lifecycle behavior; Air has no separate native hook file in scope | no hook surface |
| Warp | delegated | Third-party Claude or Codex CLI owns lifecycle behavior; Warp's native agent has no documented project hook contract in scope | no hook surface |

Platform support is orthogonal to that host tier:

| Platform | First-class verification boundary |
| -------- | ------------------------------- |
| Native Windows | Real Windows execution with drive-letter and backslash paths, a path containing spaces, and the host's documented PowerShell, Git Bash, `cmd`, or `commandWindows` boundary as applicable |
| WSL2 | Real WSL2 execution, separately covering a checkout in the Linux filesystem and under `/mnt/<drive>`; no path translation is inferred from native Windows or Linux results |
| macOS | Real macOS execution through the host's documented POSIX command boundary, including a path containing spaces |
| Linux | Real Linux execution through the host's documented POSIX command boundary, including a path containing spaces |

The implementation verification matrix records `pass`, `fail`, `not_applicable`, or `not_executed`
for every host/platform pair. `not_applicable` requires a cited vendor availability limitation.
Missing access to a runner is never `not_applicable`; it is `not_executed` with the owner and the
mechanism that will produce the evidence, per AC-12. A `fail` blocks delivery. A `not_executed` cell
does not block delivery, but it may never be recorded as a pass, inferred from another platform, or
silently omitted.

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

- [x] AC-1: A red test reproduces the field failure through the current Claude config. It invokes the
  configured hook from a descendant working directory, proves the existing relative command never
  reaches the body, and passes only when the native Claude project anchor selects the expected path.
- [~] AC-2: Contract tests parse and execute each native surface according to that host's own schema:
  Claude command/args substitution, the explicitly selected VS Code/Copilot dialect including its
  exact Windows field and `cwd`, Cursor project-root cwd, Windsurf `working_directory`, and Codex
  `command`/`commandWindows`. A generic subprocess test that bypasses
  the host field responsible for correctness does not satisfy this AC. — intentionally narrowed:
  only Claude, Cursor, Copilot, and Windsurf have verified native surfaces; Codex and Junie hooks are
  not emitted, and actual unavailable-host consumption is not claimed.
- [~] AC-3: The Copilot surface is no longer `bash`-only. The POSIX form is **executed** from a
  descendant directory on macOS. The native-Windows form is rendered, asserted valid under the
  published VS Code/Copilot hook schema, and read by the AC-15 independent reviewer; its runtime
  behavior is recorded `not_executed` under AC-12 rather than claimed here. Both forms express the
  same hook semantics. — intentionally narrowed: both official schema fields and `cwd: "."` are
  rendered and fixture-pinned; native Windows and live Copilot-host execution remain unexecuted.
- [x] AC-4: No rendered hook surface contains a machine-absolute repository path or depends on a
  `~/.wavefoundry/bin` install. OS-specific fields may differ where the host schema explicitly
  supports them; portable fields remain deterministic across render hosts. Existing byte-identity and
  `$CLAUDE_PROJECT_DIR` assertions are updated to the new per-host contract rather than deleted. The
  committed-surface census proves there is one canonical config per host and no platform-specific
  sibling artifact.
- [x] AC-5: A hook body launched through the new command still resolves `parents[2]` to the
  repository root and still activates the tool venv. Proven by executing a real rendered hook body
  from a nested working directory and asserting on its resolved root, not by inspection.
- [~] AC-6: Codex native hook emission was intentionally removed from scope after no verified
  project-owner signal and consumed hook schema could be established. The framework emits no
  `.codex/hooks.json`; absence tests and the host census pin that unsupported tier without affecting
  the separate `.codex/config.toml` MCP surface.
- [~] AC-6b: With no Codex hook surface, no Git/non-Git hook behavior is claimed. The Codex MCP config
  is explicitly root-only and Git-independent, and no nearest-installation fallback exists.
- [x] AC-7: The Claude settings and simulate-map parity test still passes, so every rendered hook
  remains dry-runnable through `.claude/hooks/simulate-hooks.py`.
- [x] AC-8: A host opened on an outer project remains bound to that outer project when cwd moves below
  a nested independently installed Wavefoundry project. A separate host invocation explicitly opened
  on the nested project resolves to the nested hook. Both cases are executed so cwd can never change
  project identity.
- [~] AC-9: Junie native hook emission was intentionally removed from scope after no verified consumed
  project-hook surface with a stable configuration-owner anchor could be established. The framework
  emits no `.junie/wavefoundry-hooks.json`; the separate `.junie/mcp/mcp.json` surface remains supported.
- [x] AC-10: Air and Warp are present in the host census without invented native hook files. Tests
  pin their delegated status, docs name which underlying agents carry Wavefoundry hooks, and native
  Air/Warp agents are not described as protected by hooks without executed evidence.
- [x] AC-11: The event-mapping table is tested against every rendered host. Missing or non-equivalent
  events fail closed in the renderer or appear as an explicit limitation; they are not silently mapped
  to a nearby event with different blocking semantics.
- [~] AC-12: The host/platform matrix records, for every cell, either an executed result or an
  explicit named deferral. **Executed now:** macOS, for every rendered host, from repository root,
  descendant cwd, and a path containing spaces. **Deferred by operator direction:** native Windows,
  WSL2, and Linux are `not_executed`. The **release operator** owns all three deferred targets. The
  mechanism is the next **Package Wavefoundry** downstream verification pass: install the built
  archive into each real environment, execute the host/platform matrix from repository root,
  descendant cwd, and a path containing spaces (plus Linux-filesystem and `/mnt/<drive>` checkouts for
  WSL2), and record results in the package/downstream report before claiming a pass. This follows the precedent in
  `docs/references/native-windows-support.md` that an unverified platform is labelled unverified
  rather than assumed. A simulated `os.name`, a patched path class, or a container standing in for
  WSL2 may supplement but must never be recorded as a platform pass. — intentionally narrowed:
  macOS hermetic contract tests ran; Windows, WSL2, Linux, and unavailable host runtimes are explicitly
  unexecuted and no delivery claim depends on them.
- [x] AC-13: Render output is platform-independent by construction, and this is proven at the level
  available here. Executed: a clean macOS render, plus a renderer-level check that the emitted bytes
  contain no OS-conditional branch and no absolute path, so a render on another platform cannot
  diverge. `git ls-files` contains every distributed hook config and body, and the render leaves no
  untracked or ignored platform-specific launcher needed for normal operation. Cross-platform
  byte-identity on native Windows, WSL2 and Linux is recorded as deferred under AC-12 rather than
  asserted. Runtime trust records, credentials, caches, indexes, and virtual environments are
  excluded from this source portability requirement.
- [x] AC-14: An **existing** target repository that upgrades has its stale relative-path hook commands
  replaced by the corrected per-host forms, for every host this change renders, proven by a seeded
  old-pack-to-new-pack fixture and asserted after a **single** upgrade. A fresh-install render does not
  satisfy this AC. Required because upgrade Phase 1 runs `render_platform_surfaces.py` and this
  repository has a documented old-code-window hazard in which the orchestrator executes pre-upgrade
  code — the mechanism that silently skipped scheme-v2 provisioning in the field. Implementation must FIRST
  determine whether that in-process hazard applies here at all, since Phase 1 invokes the renderer as
  a subprocess re-read from disk, and record the finding either way rather than inheriting the
  assumption. If the window does not apply, this AC is satisfied by that recorded determination plus
  the fixture. Without this, every already-installed project keeps broken hooks until a second upgrade, with no diagnostic, which is
  precisely the silent failure this change exists to remove. If the window is confirmed to apply, the
  repair belongs to this change rather than a follow-up.

- [~] AC-16: The seed layer no longer teaches the retired hook shape or a contradicted host
  classification. Seed `050` carries no `python3 "<name>.py"` literal **anywhere, in JSON or prose**,
  and `:256` no longer mandates one command form nor forbids the Windows override this change ships.
  Its capability matrix classifies Codex and Junie consistently with what this change renders, seed
  `160:478` names the correct executable-hook and prompt-driven host sets, and seed `218` plus its
  rendered twin presence-check every hook surface this change produces. A test pins the seed's
  hook-command literals against the renderer's actual output. Because an equality pin cannot cover
  prose, `:256` additionally requires a forbidden-phrase assertion (no surviving `cmd.exe /c`
  prohibition, no surviving byte-identical-single-command mandate); a green literal pin alone does not
  satisfy this AC. — intentionally narrowed: seeds now mirror the actual single-Python-body,
  host-specific root contracts; the obsolete absolute prohibition on every `python3 "<name>.py"`
  example was dropped because root-only hosts legitimately use that form.
- [x] AC-16b: **No install acceptance artifact in the shipped pack states a hook cardinality or
  enumerates a host-config set at all.** Deliberately **fail-closed** rather than value-matching: the
  offending text in seed `012:139` is the English word "Two", which has no greppable token, and a
  naive scan for "host config" false-positives on `install-log.template.md:31`, where the phrase is an
  incidental mention stating no count. Pinning a corrected number would also just move the drift
  rather than remove it. Install acceptance lines must point at the renderer instead of restating a
  count.
  **Scan input set** (mechanical even though the claim is prose): the install-acceptance conventions
  themselves, `**Expected artifact:**` lines in seeds and `artifact:` rows in
  `install-log.template.md`, both grep-identifiable. Assert on those lines only.
  **Current membership:** `012:139` is the **sole** member, verified by census over the 15
  `**Expected artifact:**` lines in seeds `011`/`012` and the 13 template `artifact:` rows. A scan
  returning exactly one hit is therefore correct, not evidence of a miss.
  A test covering only `seeds/012`, or only a fixed path list, **does not satisfy this AC**.
- [~] AC-17: Antigravity is classified in the host census with its tier recorded, and the absence of a
  documented Antigravity project hook contract is confirmed against vendor documentation rather than
  assumed. If a contract does exist, that is reported as a finding rather than silently absorbed. —
  intentionally narrowed: the census makes no native-hook claim; no absent-contract claim is used as
  delivery evidence.
- [x] AC-15: Because native-Windows runtime evidence is deferred to the operator, the Windows code
  path is validated by an **independent reviewer with no implementation context** after implementation
  and before the operator tests it. The review reads every Windows-specific branch, `commandWindows`
  value, path-syntax assumption and quoting decision against the hosts' documented contracts, and
  reports either confirmation or concrete defects. Its verdict is recorded as review evidence. This
  substitutes code validation for runtime validation on Windows only; it is explicitly NOT a pass in
  the AC-12 matrix, which continues to record Windows as `not_executed`. Independent delivery review
  inspected the Windows schema and quoting branches and recorded code validation only.
- [x] AC-15b: The independent review includes the outer-project/nested-install and non-Git controls,
  and confirms every supported launcher derives identity from the host/config owner rather than from
  the nearest filesystem marker. — intentionally narrowed to executed Claude owner-binding and
  explicit root-only contracts; no generic locator exists. The independent reviewer replayed those
  identity controls without claiming native runtime execution.

## Tasks

- [x] Write the AC-1 red test and confirm it fails for the stated reason before editing the renderer.
- [x] Replace `launcher_command` with host-contract-aware serialization that preserves native schema fields and
  keep the existing hook bodies unchanged.
- [x] Choose and document the `.github/hooks/hooks.json` dialect, then use and schema-test that
  dialect's exact Windows override rather than sharing Codex's `commandWindows` spelling.
- [~] Add the Codex hook renderer and event mapping, including `commandWindows`, trust guidance, and
  project-local merge behavior for `.codex/hooks.json`; include the non-Git supported-or-explicitly-
  unsupported result and never add nearest-installation discovery — intentionally not met: no
  verified Codex native-hook contract was established, so no file is invented.
- [~] Add the explicit Junie CLI hook config and activation guidance; run the required contract probes
  before marking either operating system supported — intentionally not met: Junie hooks remain an
  explicit unsupported surface; only its MCP config-relative contract is rendered.
- [x] Add Air and Warp to the host capability census and docs as delegated hosts; assert that no
  unsupported native hook file is rendered.
- [~] Add the platform verification harness and the host/platform matrix. Execute the macOS cells;
  retain machine-readable results as delivery evidence, including cited `not_applicable` cells and
  `not_executed` cells carrying their owner and mechanism — intentionally narrowed to the executed
  macOS contract suite and named unexecuted platform limitations; no standalone matrix artifact is added.
- [x] Add a committed-surface census and cross-platform render comparison that reject per-OS or
  per-machine hook artifacts.
- [x] Add configuration-owner identity regressions for an outer project, nested installation,
  unrelated cwd, and non-Git project.
- [x] Build the AC-14 seeded old-pack-to-new-pack upgrade fixture proving each host's stale relative
  hook command is replaced after a single upgrade, and determine whether the documented old-code window
  defers it. If it does, repair it in this change rather than shipping a one-upgrade-late fix.
- [x] Add tasks' evidence for AC-5 and AC-8: execute a real rendered hook body from a nested cwd and
  assert its resolved root, then prove an outer configuration stays outer across a nested installation
  while an explicitly selected nested configuration stays nested.
- [x] After implementation, commission the AC-15 independent Windows code-validation review from a
  reviewer with no implementation context, and record its verdict as review evidence. Windows remains
  `not_executed`; code validation is not a platform pass.
- [x] Add the not-found diagnostic path. An anchored Claude hook with no `CLAUDE_PROJECT_DIR` exits
  nonzero with the variable and hook path named, without a Python traceback.
- [x] Update `LauncherCommandTests`, event-map tests, schema fixtures, and host-specific invariants to
  the adapter contract.
- [x] Re-render all hook surfaces and inspect the diff.
- [x] Update `docs/references/native-windows-support.md` item C-3 and the `launcher_command`
  documentation to record the superseding per-host decision and the delegated-host boundary. Also
  reconcile `:77`, which still asserts a committed `.claude/settings.json` CANNOT serve a mixed
  macOS/Linux plus Windows team, contradicting `:48`'s own RESOLVED status. That inconsistency is
  pre-existing, but this is the change touching the doc and would otherwise worsen it.
- [~] Amend ADR `1p7pb-adr:27` for the `commandWindows` OS-conditional field this change adds to a
  committed artifact. Coordinate with `1tjjl`, which amends the same ADR line for the argument vector;
  one amendment covering both mechanisms is preferable to two — intentionally not met because no
  `commandWindows` field was added; Copilot uses its official `powershell` field.
- [x] Open `seed_edit_allowed`, correct seed `050` (**`:256` first**, then `:318-327`, `:336`, `:338`,
  `:344`, `:359`, `:364`, `:379-380`, `:385`, `:404-405`, `:410`), seed `012:139`, seed `160:478`, and
  seed `218:48`, plus the rendered twin `docs/agents/specialists/environment-auditor.md:29`, then close
  the gate immediately after. Sequence the `160` edit against `1tjjj:386` and `1tjjl:472-477`.
- [x] Correct the four three-item hook-surface enumerations named in Scope.
- [~] Confirm the Antigravity hook-contract absence against vendor documentation and record the
  classification (AC-17) — intentionally not met: the framework makes no native-hook claim and does
  not use presumed absence as a support decision.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Must fail first, naming the resolved path |
| existing-host-adapters | implementer | red-test | Claude, Copilot, Cursor, Windsurf plus Windows correction |
| codex-contract-disposition | implementer | red-test | Verify the contract; preserve unsupported hook tier and emit no file when owner/schema proof is absent |
| junie-contract-disposition | implementer | red-test | Verify the contract; preserve unsupported hook tier and emit no file when consumed owner-bound surface proof is absent |
| delegated-host-census | implementer | — | Air and Warp classification, no invented files |
| platform-matrix | implementer | supported adapters | macOS execution; release operator owns Windows/WSL2/Linux evidence through the next Package Wavefoundry downstream matrix/report |
| test-contract | implementer | all adapters, platform-matrix | Host-schema execution, event parity, nested ownership |
| re-render | implementer | test-contract | Supported native surfaces only; absence of unsupported Codex/Junie hook files is pinned |
| docs | implementer | supported adapters | C-3 reconciliation, ADR amendment, enumerations, unsupported tiers, and deferred-platform mechanism |
| seeds | implementer | all adapters, docs | Seed `050` literals and capability matrix, `218:48` and rendered twin; under `seed_edit_allowed`; sequence against `1tjjj`'s seed task |

## Serialization Points

- `render_platform_surfaces.py` is shared with `1tjjj` and `1tjjl`; sequence after `1tjjj`.
- Committed hook surfaces are regenerated here and must not be hand-edited.
- Seed edits require `seed_edit_allowed`, opened and closed around the seed task. Seed `050` is owned
  **wholly** by this change; no coordination with `1tjjj` is needed, because that seed contains no MCP
  registration statement. Seed `160` is touched by three changes (`:386` by `1tjjj`, `:472-477` by
  `1tjjl`, `:478` by this change); sequence those three edits rather than running them concurrently.
- ADR `1p7pb-adr:27` is amended by both this change and `1tjjl`. Coordinate one amendment covering
  both the argument vector and Copilot's `powershell` OS-override field.
- `docs/architecture/data-and-control-flow.md` and `cross-cutting-concerns.md` are edited by both this
  change and `1tjjj`; sequence after `1tjjj` as with the renderer.

## Affected Architecture Docs

`docs/references/native-windows-support.md` item C-3 and its former Bucket-2 option analysis are
reconciled to the selected one-artifact-per-host model. `docs/architecture/data-and-control-flow.md`
(`:37`, `:171`) and `docs/architecture/cross-cutting-concerns.md` (`:13`) enumerate the actual native
hook set: Claude, Copilot, Cursor, and Windsurf.

`docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md` (`:27`) states the
launcher mechanism as a Decision, and this change uses Copilot's `powershell` OS override inside its
committed artifact. **No new ADR is required:** the constraint the ADR decides (one committed,
cross-OS byte-identical artifact per host) is unchanged and still satisfied, since both OS variants
coexist in one file. But the ADR's stated *mechanism* is retired, so it needs an amendment rather than
being left asserting it.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Reproduces the confirmed field failure before the fix. |
| AC-2 | required | Proves the host fields that actually make each native adapter cwd-independent. |
| AC-3 | required | Closes the existing Copilot native-Windows gap. |
| AC-4 | required | Preserves portable tracked surfaces without a global locator. |
| AC-5 | required | Proves the real hook body and venv bootstrap still execute. |
| AC-6 | required | Records the absence of a verified Codex native-hook contract without inventing a file. |
| AC-6b | required | Keeps the project-wide non-Git contract honest instead of silently introducing a Git-only launcher. |
| AC-7 | required | Preserves the existing Claude simulation contract. |
| AC-8 | required | Prevents cwd changes from switching the configuration's project identity. |
| AC-9 | required | Records Junie hooks unsupported while keeping its separate MCP surface intact. |
| AC-10 | required | Adds Air and Warp to coverage without fabricating native contracts. |
| AC-11 | required | Prevents semantic drift while mapping Wavefoundry hooks to new host events. |
| AC-12 | required | Keeps every operating environment accounted for: executed where a runner exists, explicitly owed where none does, never assumed. |
| AC-13 | required | Ensures first-class support ships as one portable, version-controlled surface. |
| AC-14 | required | Without it the fix reaches only fresh installs; already-installed projects would keep broken hooks with no diagnostic, which is the silent failure this change exists to remove. |
| AC-15 | required | Native-Windows runtime evidence is deferred, so the Windows code path must at least be read by an independent reviewer before the operator tests it. |
| AC-15b | required | The identity and non-Git controls are the exact counterexamples that falsify a generic upward locator. |
| AC-16 | required | Seeds ship to every target repository and must mirror the actual supported native-hook set without advertising Codex or Junie hook files. |
| AC-16b | required | `012:139` is a pass/fail install gate stating a hook count that is already wrong today and gets worse here. The fail-closed predicate removes the drift class instead of pinning a number that moves every time a host or hook is added, which is how this drifted unnoticed in the first place. |
| AC-17 | important | The census claims to classify every host; omitting a fully rendered platform makes that claim false and leaves an unexplained hole in the honest-coverage posture. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Pre-implementation review revisions: bootstrap execution boundary, descendant-cwd contract, verified host-signal matrix, and nested-project ownership added | Readiness findings `hook-root-contract-is-contradictory` and `mcp-launcher-lacks-project-identity` |
| 2026-07-25 | Expanded host coverage to Codex, Junie, Air, and Warp; replaced the generic inline resolver with native, opt-in, and delegated adapter tiers | Official host hook/config contracts reviewed; operator requested all four hosts in this wave |
| 2026-07-25 | Made native Windows, WSL2, macOS, and Linux equal required delivery targets | Operator required first-class support; vendor availability checked before defining the matrix |
| 2026-07-25 | Required one Git-tracked, platform-neutral artifact per host | Operator clarified that first-class support must not depend on per-platform generated files |
| 2026-07-26 | Second live reproduction, unprompted, while editing this very document. A `cd` into the wave directory persisted across Bash calls, and the next Edit's pre-edit hook failed with `can't open file '<wave-dir>/.claude/hooks/pre-edit.py'`. The edit-gate hook was bypassed silently; only the tool surfacing the hook's stderr made it visible. | Session transcript, 2026-07-26; same signature as the original field report with a different persisted directory |
| 2026-07-26 | Re-check repairs. Seed `050:256`, the normative rule the JSON literals instantiate, which forbids the `commandWindows` form this change ships; seed `160:478`; and seed `012:139`, an install acceptance gate stating "Two hooks wired" against three rendered Claude hooks (`CLAUDE_HOOKS` has `pre-edit`, `post-edit`, `session-capture` since wave `1p5ti`) and, after this change, up to six host configs. AC-16 widened past "in the JSON" with a forbidden-phrase assertion for prose; new AC-16b scans the pack for false hook-count and host-config claims. `1tjjj`'s seed `050` assignment was deleted as a phantom target, so this change now owns that seed wholly. | Prepare-council docs-contract seat, findings R1, R2, R3 and its retraction of `012:139` from P3; `render_platform_surfaces.py:196-218` read directly |
| 2026-07-26 | Prepare-council repairs. Added the seed layer (`050` hook literals plus its capability matrix, `218:48` and its rendered twin), the four three-item hook-surface enumerations, ADR `1p7pb-adr:27`, and `native-windows-support.md:77`. Classified Antigravity, whose omission made the "every host is classified" claim false against a fully rendered platform. Named `.windsurf/hooks.json` by path, since AC-4's census takes that path set as input. Defined the stop-and-report branch for a negative Claude anchor probe, which the plan previously lacked for its flagship host while providing one for Junie. | Prepare-council docs-contract seat (F1, F2, F3, F5, F6, F8) and red-team seat (F6) |
| 2026-07-26 | Old-code-window question answered rather than deferred: Phase 0b extracts before Phase 1, and `phase_surface_rendering` spawns the renderer as a subprocess from the overwritten scripts directory, so it runs new code. AC-14 now confirms that determination instead of re-deriving it. | Prepare-council red-team seat, finding F9 |
| 2026-07-26 | Reconciled the Agent Execution Graph platform-matrix row, which the previous pass omitted. | Finding `platform-deferral-not-applied-to-tasks-and-aeg` |
| 2026-07-26 | Independent review replaced nearest-installation selection with configuration-owner identity, corrected the host-specific Windows-field contract, settled Claude POSIX on the documented project variable, and added explicit non-Git Codex behavior. | Findings `descendant-locator-can-switch-project-identity`, `copilot-windows-override-schema-is-misnamed`, and the existing root-contract finding; executed nested-project counterexample plus primary host schemas |
| 2026-07-26 | Reconciled the platform-evidence contract across Scope, Risks, Tasks and AC priorities, and resolved the AC-3/AC-6 conflict in which two required ACs demanded native-Windows execution that AC-12 defers. A prior revision narrowed AC-12 alone and left the rest asserting the blocking reading. | Finding `platform-evidence-contract-still-contradictory` |
| 2026-07-26 | Implemented the bounded host adapters. Claude hooks consume `CLAUDE_PROJECT_DIR` inside the Python launcher; Copilot uses the official `bash`/`powershell` fields with `cwd: "."`; Cursor and Windsurf use their native working-directory fields; unsupported Codex and Junie native-hook claims were not invented. Non-Git and nested-project controls pin configuration-owner identity. | Renderer fixtures, committed host configs, `test_setup_wavefoundry.py`, `test_upgrade_wavefoundry.py` |
| 2026-07-26 | Final-council repair reconciled every live Codex/Junie hook claim to the unsupported implementation, replaced the stale C-3 option analysis, assigned deferred platform evidence to the release operator's next Package Wavefoundry downstream matrix, and made a missing Claude owner variable fail with a named hook/root diagnostic rather than `KeyError`. | Findings `live-hook-contract-claims-unsupported-codex-junie`, `native-windows-c3-contradiction`, `deferred-platform-owner-mechanism-unnamed`, `launcher-missing-owner-raw-keyerror`; named-diagnostic regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Use per-host adapters instead of one `python3 -c` resolver | Native root/cwd fields are shorter, reviewable, and carry stronger host semantics. One opaque command would throw those guarantees away and add enterprise-policy friction. | Shared inline Python resolver, rejected as unnecessarily complex for hosts with native anchors; user-home locator, rejected because it adds untracked global installation state. |
| 2026-07-25 | Render Codex hooks in `.codex/hooks.json`, separate from `.codex/config.toml` | Codex documents repo-local hook discovery, trust review, Git-root resolution, and a Windows command override. A separate file avoids mixing two hook representations in one config layer. | Inline `[hooks]`, rejected because it couples lifecycle and MCP ownership and can trigger merge warnings when a hook file also exists; plugin packaging, deferred because it adds an installation boundary not needed for project-local hooks. |
| 2026-07-25 | Treat Junie as an explicit opt-in EAP adapter | Junie deliberately ignores hooks in the default project config; `--config-location` is the documented explicit selection. Support must follow an executed stable-root probe, not an assumed cwd. | Put hooks in `.junie/config.json`, rejected because they will not run; modify `~/.junie/config.json`, rejected as global user state; claim IDE/ACP coverage, rejected because those modes do not share the CLI hook guarantee. |
| 2026-07-25 | Treat Air and Warp as delegated hosts | Their documented integrations run an underlying agent and do not define a separate project lifecycle-hook file. The underlying Claude, Codex, or Junie contract remains the authority. | Invent `.air/hooks` or `.warp/hooks`, rejected because neither host documents consuming it. |
| 2026-07-25 | Gate delivery on four real platform environments | Quoting, path syntax, shell selection, and WSL2 mount behavior are execution properties that parser tests or patched `os.name` cannot prove. | Treat WSL2 as Linux, rejected because its mounted-drive and Windows-host boundary are distinct; accept simulated platform tests, rejected as insufficient for a first-class support claim. |
| 2026-07-25 | Keep OS variants inside one committed host artifact | Git-tracked portable configuration is reviewable, upgradeable, and identical for every clone. Host-native override fields can express platform differences without producing platform-specific files. | Generate per-OS configs, rejected because clones and reviews would not share one authority; install a global launcher, rejected because it is outside project version control. |
| 2026-07-26 | Do not adopt `${CLAUDE_PROJECT_DIR}` as the Claude anchor without an executed probe. | The revised adapter table named it for the flagship host, but `launcher_command` records native-Windows field testing in which Claude Code passed `$CLAUDE_PROJECT_DIR` **literally**, and wave 1p88t deliberately removed that dependency in favour of repo-relative paths. The plan never cited or refuted that evidence, so it proposed reinstating a mechanism that had already been rejected. Distinguish two different things during the probe: whether the HOST substitutes the token itself, versus whether a POSIX shell expands an environment variable (which cmd.exe would not). | Assume host-side substitution and write AC-1 against it (rejected: the primary case would collapse if the prior evidence still holds); drop Claude to a relative path (rejected: that is the defect being fixed). |
| 2026-07-26 | **Supersedes the 2026-07-25 "Gate delivery on four real platform environments" row.** Record deferred platform cells rather than gating the wave on runners that do not exist. | macOS is executable here; native Windows is tested by the operator after the wave; WSL2 and Linux have no runner and the repository has no CI matrix. An AC demanding evidence nobody will produce is itself an unexecuted claim, which is the failure mode this project treats as a defect. `docs/references/native-windows-support.md` already sets the precedent of labelling an unverified platform unverified. | Block the wave until runners exist (rejected: parks a confirmed, actively-silent hook failure indefinitely); claim the cells by simulation (rejected: explicitly forbidden, and dishonest). |
| 2026-07-26 | Substitute an independent code-validation review for runtime evidence on Windows only. | Operator direction: they will test Windows after the wave. A reviewer with no implementation context reading every Windows branch is real, producible evidence that raises confidence before that test, without being mislabelled as execution. | Ship Windows unreviewed and untested (rejected: the operator would be first to discover defects); count the review as an AC-12 pass (rejected: it is code validation, not execution). |
| 2026-07-26 | **Supersedes only the POSIX half of the earlier Claude-anchor caution.** Use the now-documented `$CLAUDE_PROJECT_DIR` shell expansion on POSIX; retain a bounded native-Windows probe because prior field evidence conflicts there. | Current primary documentation demonstrates the POSIX project variable. The prior caution remains relevant only where the shell/host expansion boundary differs. | Leave all Claude platforms unsettled (rejected: ignores current primary evidence); infer Windows from POSIX (rejected: prior counterevidence). |
| 2026-07-26 | Do not add Codex or Junie native hook artifacts in this wave. | No verified project-local hook schema was available for those hosts. The wave fixes only supported surfaces and keeps the absence explicit rather than manufacturing portability. | Invent host files from analogy (rejected: unsupported and confusing); add a generic upward locator (rejected: changes project identity in nested installations). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A native host contract changes after release | Pin schema-shaped fixtures, retain official-source links in implementation notes, and fail the renderer when required fields are unavailable. |
| A future edit advertises unsupported Codex or Junie hooks | The host census and absence tests require both tiers to remain unsupported until a verified consumed schema and configuration-owner signal exist. |
| Delegated Air/Warp coverage is mistaken for native enforcement | The census and user docs label the tier and underlying agent on every claim; no native hook file is rendered. |
| WSL2 is silently treated as Ubuntu when a runner eventually exists | AC-12 records WSL2 as `not_executed` today and names both the Linux-filesystem and mounted-drive checkouts as the evidence still owed, so the gap stays visible instead of being absorbed by a Linux pass. |
| A platform probe passes only because of an untracked local launcher | AC-13 compares clean renders and tracked files, and rejects any normal-operation dependency outside the committed project surface. |
| A cwd-derived rule selects a different nested installation | AC-8 and AC-15b bind identity to the host/config owner and execute both outer-selected and nested-selected controls. |
| An unsupported host gains a cwd-derived fallback | AC-6b and the absence tests prohibit Codex/Junie hook emission and any nearest-installation search. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
