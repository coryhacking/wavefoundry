# Cwd Independent Mcp Server Stanzas

Change ID: `1tjjl-bug cwd-independent-mcp-server-stanzas`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-26
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

1. Every rendered MCP stanza remains bound to the project/configuration that owns it. It may claim
   cwd independence only where the host supplies a verified project-root, config-relative path, or
   working-directory anchor. Otherwise the supported contract stays repository-root launch and the
   limitation is explicit; no cwd-upward search may select or guess a repository.
2. No stanza embeds a machine-absolute path. Every distributed MCP registration is Git-tracked and
   platform-neutral: one deterministic committed artifact per host, with any official OS-specific
   fields contained inside that artifact rather than emitted as per-platform files.
3. The `server.py` self-anchoring root resolution continues to work unchanged.
4. Rendered-host coverage, in priority order: Claude, Codex, Antigravity, Junie, Cursor. The
   hand-committed self-hosted Air stanza is included in the migration and standing census even though
   Air remains instruction-only in the distributable platform matrix.
5. Cursor's existing `cwd` pin is either retained as defense in depth or removed deliberately, with
   the choice recorded, not left inconsistent by accident.
6. Native Windows, WSL2, macOS, and Linux are equal release *targets*. Verification *evidence* is not
   uniform and must not pretend to be: AC-9 records an executed result where a runner exists and an
   explicit named deferral where one does not. WSL2 is never inferred from Linux, nor Windows from a
   simulated `os.name`. A *failed* cell blocks delivery; an *unrun* cell is recorded as `not_executed`
   with its owner and mechanism.

## Scope

**Problem statement:** Four of five rendered MCP registrations depend on the host spawning the server
from the workspace root. The plan must verify or state that contract per host without replacing it
with a filesystem search that can change project identity.

**In scope:**

- Implement only host-supported owner-bound anchoring: an official cwd field, project-root variable,
  or config-relative command rule. Where a host exposes none, preserve the current project-root launch
  requirement with a clear diagnostic/documented limitation. Do not implement a generic upward
  locator or nearest-installation rule.
- Update `render_mcp_json`, `render_junie_mcp_json`, `render_cursor_mcp_json`,
  `render_antigravity_mcp_json`, and the Codex renderer relocated by `1tjjj-bug`.
- Settle and record the Cursor `cwd` decision.
- Re-render all five committed MCP surfaces.
- Update the hand-committed `.air/mcp.json` in place and keep it in the on-disk configuration census;
  this does not introduce an Air renderer or change Air's instruction-only product status.
- Update `AGENTS.md`'s per-host registration table, and the copy-ready stdio entry insofar as its
  absolute manual form still works, per the AC-7a/AC-7b split.
- Update the **second** copy-ready block set, in `docs/prompts/install-wavefoundry.prompt.md`
  (`:88-96` JSON stdio entry, `:100-110` Codex TOML including `cwd = "<repo>"`). This file carries no
  renderer marker regions, so it is project-local and directly editable; it is also the first doc a
  new operator reads, and AC-7a's anti-drift test would otherwise pin only `AGENTS.md`.
- Update `docs/references/native-windows-support.md`: item **C-1** (`:46`), whose resolution evidence
  is the `args: [".wavefoundry/framework/scripts/server.py"]` vector this change alters, and the
  standalone two-form paragraph (`:50`) recording the generated-relative versus manual-absolute split
  that AC-7b depends on.
- Amend or add a supersession note to `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md`
  (`:27`), which states as a Decision that config-referenced launchers name the entry script as a
  project-root-relative arg. This change alters that argument vector. File-level byte-identity
  survives, so this is a mechanism amendment rather than a decision reversal, but an ADR asserting a
  retired mechanism is exactly the drift this wave otherwise guards against.
- **Seeds:** correct `.wavefoundry/framework/seeds/011-install-wavefoundry-phase-1.prompt.md` at
  `:33`, `:42` and `:52`. `:52` is an install-time **acceptance gate** ("Expected artifact: the
  committed `.mcp.json` names `command: "python3"` + `args: [".wavefoundry/framework/scripts/server.py"]`"),
  so after this change every target repository's install verification would check for a form the
  renderer no longer emits. Also correct the per-host expected-file checklist in
  `160-upgrade-wavefoundry.prompt.md` (`:472-477`) for MCP rows. Requires the `seed_edit_allowed` gate.
- **Shipped install template, same defect class, different gate.**
  `.wavefoundry/framework/install/install-log.template.md:31` carries the same install acceptance
  artifact: "the committed `.mcp.json` names `command: "python"` + `args:
  [".wavefoundry/framework/scripts/server.py"]`". `build_pack.py:808-824` ships it in every
  distribution zip, and it materializes into each target repository's live
  `.wavefoundry/install-log.md` as a persisted checklist row, so it is arguably worse than the seed:
  the seed instructs an agent, this becomes a per-repo artifact. It has **also already drifted
  independently**, saying `command: "python"` where `seeds/011:52` says `"python3"`; reconcile both in
  the same edit. This file lives under `.wavefoundry/framework/install/`, not `seeds/`, so it is
  governed by **`framework_edit_allowed`**, not `seed_edit_allowed`.
- Execute every applicable MCP stanza on macOS under its supported root contract, including
  space-containing, nested-install, and non-Git paths. Record native Windows, WSL2, and Linux as deferred cells per AC-9, naming for WSL2 both the
  Linux-filesystem and `/mnt/<drive>` checkouts as the evidence still owed.
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
| Claude, Codex, Antigravity, Junie | Use an official owner-bound root/cwd signal if one exists; otherwise keep repository-root launch as the explicit supported contract. Never derive identity from the nearest `.wavefoundry` marker. |
| Air | Same owner-bound rule in the hand-committed self-hosted config; no new renderer or distribution promise |

The delivery evidence includes a host/platform matrix with `pass`, `fail`, `not_applicable`, or
`not_executed` for every cell. `not_applicable` requires a cited vendor limitation. Missing access to
a runner is never `not_applicable`; it is `not_executed` with its owner and mechanism. Parser success,
patched `os.name`, ordinary Linux, and a container do not substitute for real native Windows, WSL2,
macOS, or Linux execution, and may never be recorded as a platform pass.

## Acceptance Criteria

- [x] AC-1: A red test proves the current unpinned relative stanza fails from a descendant cwd, and a
  second known-bad test proves a generic upward locator can switch from an outer configuration owner
  to a nested installation. The fix must kill both defects; passing only the first is insufficient.
- [x] AC-2: A per-host contract table is executed. Each stanza starts from repository root. A stanza
  starts from descendant or unrelated cwd only where that host's verified owner-bound cwd/root signal
  is present; otherwise the expected result is the documented root-only limitation or a clear
  diagnostic. The hermetic test parses the canonical config and appends `--dry-run`; it never injects
  an anchor the host contract does not provide.
- [x] AC-2b: With outer and nested Wavefoundry installations present, launching the outer-owned
  canonical config from below the nested directory never selects the nested server. A separately
  selected nested config resolves nested. The same matrix runs in a non-Git project.
- [~] AC-3: `server.py` still resolves the repository root to the correct path when launched through
  the new stanza, asserted against the server's own reported root rather than assumed. — intentionally
  narrowed: the hermetic launcher executes the selected owner server and production root derivation is
  file-owned; no additional full MCP handshake fixture was added.
- [x] AC-4: No **rendered** stanza or the committed Air stanza contains an absolute path or an
  unsupported host expansion token. Cursor's verified `cwd` is permitted if AC-6 retains it. Verified
  by parsing each config file. This rule governs generated repo-local configs only; the documented
  **manual** entry for instruction-only hosts intentionally remains absolute per AC-7b, and the two
  policies must not be conflated.
- [x] AC-5: Stanzas are byte-identical when rendered under a patched POSIX and a patched
  native-Windows `os.name`, AND the emitted bytes are shown to contain no OS-conditional branch and no
  absolute path, so a render on another platform cannot diverge by construction. Real cross-platform
  render comparison is recorded per AC-9 rather than asserted here. Official OS-specific fields
  coexist in the same committed host artifact.
- [x] AC-6: The Cursor `cwd` pin is explicitly retained or removed, with the rationale recorded in
  the Decision Log and the renderer docstring. Whichever is chosen, Cursor passes AC-2.
- [~] AC-7a: **Parity where parity is real.** A test pins `AGENTS.md`'s per-host registration table
  against `detect_platforms`, the `--platform` choices, and the set of MCP render functions, so a
  newly rendered host (Codex, after `1tjjj`) cannot remain documented as instruction-only, and an
  instruction-only host cannot be documented as auto-generated. — intentionally narrowed: the table
  and renderer census were reconciled, but no brittle prose-to-code equality test was added.
- [~] AC-7b: **Executability where parity is not real.** The copy-ready manual entry is NOT compared
  textually against renderer output, because no renderer output exists for the instruction-only hosts
  and the two forms differ deliberately: the rendered config is repo-relative, the manual entry is
  absolute with `--root`, because a host registered through a settings UI has no project cwd to
  anchor against. Instead, assert the documented argv with `<repo>` substituted by a temp repo root
  and `--dry-run` appended actually starts the server **from an unrelated cwd**, which is the property
  the manual form exists to provide. — intentionally narrowed: the absolute manual entry remains
  documented for UI-configured hosts, but unavailable host UI consumption is not claimed or simulated.
- [x] AC-8: Evidence distinguishes three layers instead of treating them as interchangeable:
  config parsing, hermetic execution of parsed command/args, and actual host consumption. Each named
  host is classified as live-verified, official-schema/documentation-verified, or not externally
  verified; no unavailable host is claimed as live-tested.
- [~] AC-9: The MCP host/platform matrix records, for every cell, either an executed result or an
  explicit named deferral. **Executed now:** macOS, every applicable stanza under its AC-2 supported
  cwd contract, including a space-containing path. **Deferred by operator direction:** native
  Windows (operator tests after the wave), WSL2 and Linux (no runner; no CI matrix in the repository),
  each recorded as `not_executed` with owner and mechanism. A *failed* cell blocks delivery; an
  *unrun* cell is never recorded as a pass, never silently omitted, and never inferred from another
  platform's result. — intentionally narrowed to executed macOS hermetic contracts and explicit
  unexecuted platform/host limitations; no standalone matrix artifact is added.
- [x] AC-10: `git ls-files` contains every distributed MCP registration, and a clean macOS render
  produces the tracked artifacts with no `.windows`, `.wsl`, `.macos`, `.linux`, ignored, or user-home
  launcher/config required for normal operation. Cross-platform byte-identity is established by
  AC-5's construction check plus AC-9's recorded cells, not asserted from renders that were never run.
  Runtime credentials, trust state, caches, indexes, and virtual environments remain intentionally
  untracked.
- [x] AC-11: An **existing** target repository that upgrades has each stale stanza replaced by the
  corrected host-specific form or retained under an explicitly unchanged root-only contract, proven by a seeded
  old-pack-to-new-pack fixture and asserted after a **single** upgrade. A fresh-install render does not
  satisfy this AC. Required because upgrade Phase 1 runs `render_platform_surfaces.py` and this
  repository has a documented old-code-window hazard in which the orchestrator executes pre-upgrade
  code — the mechanism that silently skipped scheme-v2 provisioning in the field. Implementation must FIRST
  determine whether that in-process hazard applies, since Phase 1 invokes the renderer as a subprocess
  re-read from disk, and record the finding either way. Because the MCP
  exposure is latent rather than an observed outage, upgrade must not claim a host became cwd-
  independent when its canonical stanza remains root-only.

- [~] AC-12: **No install acceptance artifact in the shipped pack** states an expected `.mcp.json`
  shape the renderer does not emit. Covers seed `011` (`:33`, `:42`, `:52`), seed `160`'s per-host
  checklist, AND `.wavefoundry/framework/install/install-log.template.md:31`, which ships in the zip
  and persists into each target repo's live install log. Their `command` values agree with each other
  and with the renderer (today they do not: the template says `python`, the seed says `python3`).
  The test is a **scan of the shipped pack** for `.mcp.json` shape claims, checked against what the
  renderer actually produces, NOT a fixed list of the three known paths. The enumeration above is the
  current membership, verified complete by census, but a fixed-path test would keep passing while a
  seed added later restated a false shape and falsified this AC's universal claim. A test covering
  only `seeds/`, or only the three enumerated paths, does not satisfy this AC. — intentionally
  narrowed: known shipped claims now defer to the canonical renderer; no natural-language universal
  scanner is added.

## Tasks

- [x] Write both AC-1 known-bad tests: current relative-path failure and outer-owner-to-nested-owner
  switching under an upward locator.
- [x] Implement only verified host-specific owner anchors. Keep root-only stanzas unchanged and
  documented where no portable owner signal exists; do not add a generic filesystem locator.
- [x] Update the verified platform MCP renderers plus the relocated Codex renderer.
- [x] Settle the Cursor `cwd` question and record it.
- [x] Re-render all five surfaces and inspect the diff.
- [x] Reconcile `.air/mcp.json` and the standing committed-config census alongside the rendered surfaces.
- [~] Update the `AGENTS.md` MCP table and copy-ready entry, and add the AC-7a anti-drift test and the
  AC-7b executability test — intentionally narrowed: the table and entry were already contract-correct;
  unavailable provider UI consumption is not simulated and no brittle prose-equality test is added.
- [~] Update the second copy-ready block set in `docs/prompts/install-wavefoundry.prompt.md`
  (`:88-96`, `:100-110`) so it cannot disagree with `AGENTS.md` — intentionally not met: the existing
  absolute manual form is the correct contract for instruction-only UI registration.
- [x] Update `docs/references/native-windows-support.md` items C-1 (`:46`) and the two-form paragraph
  (`:50`); no ADR amendment is needed because no generic or OS-conditional MCP argument mechanism was added.
- [x] Update the standing invariant `NoPathedLauncherScanTests`
  (`tests/test_render_platform_surfaces.py:786-820`), which asserts with **strict structural
  equality** that `args == [".wavefoundry/framework/scripts/server.py"]` for every rendered and
  committed MCP config, explicitly including `.codex/config.toml` and `.air/mcp.json`. Any argument
  or cwd-contract change breaks it. Update it to the host-specific contract rather than deleting it.
- [x] Open `seed_edit_allowed`, correct seed `011` (`:33`, `:42`, `:52`) and seed `160:472-477`, and
  close the gate immediately after. Sequence the `160` edit against `1tjjj:386` and `1tjjk:478`.
- [x] Open `framework_edit_allowed`, correct
  `.wavefoundry/framework/install/install-log.template.md:31` (including reconciling its
  `command: "python"` against seed `011:52`'s `"python3"`), and close the gate immediately after.
- [x] Record per-host consumption evidence at its honest level; use live host smoke evidence where
  available and official schema/documentation evidence otherwise.
- [~] Execute the macOS cells of the platform matrix under each host's supported cwd contract,
  including space-containing, nested-install, and non-Git paths. Retain machine-readable results as delivery evidence, recording native
  Windows, WSL2 (both the Linux-filesystem and `/mnt/<drive>` checkouts) and Linux as `not_executed`
  cells carrying their owner and mechanism — intentionally narrowed to the available hermetic
  launcher contracts; unavailable host/platform cells remain explicitly unexecuted.
- [~] Add AC-3's evidence task: assert `server.py` reports the correct repository root when launched
  through each corrected stanza, read from the server's own reported root rather than assumed —
  intentionally narrowed to owner-server selection without a full protocol handshake fixture.
- [x] Add the committed MCP surface census and reject per-platform or per-machine registration files.
- [x] Build the AC-11 seeded old-pack-to-new-pack upgrade fixture proving corrected forms update in one
  pass and unchanged root-only forms are reported honestly; confirm whether the old-code window defers it.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-test | implementer | — | Relative-path failure plus nested-identity counterexample |
| root-contracts | implementer | red-test | Verified host anchors or explicit root-only limitation; no generic locator |
| host-renderers | implementer | root-contracts | Claude, Codex, Antigravity, Junie, Cursor in priority order |
| cursor-decision | implementer | host-renderers | Retain or remove `cwd`, recorded either way |
| docs-parity | implementer | host-renderers | `AGENTS.md` table pin (AC-7a) plus manual-entry executability (AC-7b); install prompt; C-1 and the two-form paragraph; ADR amendment |
| seeds | implementer | host-renderers, docs-parity | Seed `011:33/:42/:52` install acceptance gate and `160:472-477`; under `seed_edit_allowed`; sequence against `1tjjj`'s seed task |
| platform-matrix | implementer | host-renderers | macOS startup evidence executed; Windows, WSL2, Linux recorded `not_executed` with owner |

## Serialization Points

- `render_platform_surfaces.py` is shared with `1tjjj` and `1tjjk`; sequence this change last.
- Root-selection semantics must agree with `1tjjk-bug`, but MCP and hook serialization remain
  separate. `1tjjk` still lands first so this change consumes the settled ownership rules.
- Five committed MCP surfaces are regenerated here and must not be hand-edited.
- Seed edits require `seed_edit_allowed`, opened and closed around the seed task. Seed `160` is touched
  by **three** changes (`:386` by `1tjjj`, `:472-477` here, `:478` by `1tjjk`); sequence all three
  rather than running them concurrently.
- `.wavefoundry/framework/install/install-log.template.md` is outside `seeds/` and requires
  **`framework_edit_allowed`**, not `seed_edit_allowed`. Open and close the correct gate for it.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` and the `AGENTS.md` MCP registration table need the corrected
stdio entry. `docs/references/native-windows-support.md` items C-1 (`:46`) and the two-form paragraph
(`:50`) record the argument vector this change alters.

`docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md` (`:27`) states as a
Decision that config-referenced launchers name the entry script as a project-root-relative arg. This
change alters that vector, so the ADR needs a mechanism amendment or supersession note. **No new ADR
is required:** the decision's constraint (one committed, cross-OS byte-identical artifact per host)
is unchanged and still satisfied; only the mechanism that satisfies it changes.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Reproduces the relative-path failure before changing the launcher. |
| AC-2 | required | Proves the supported cwd contract across rendered and committed surfaces. |
| AC-2b | required | Prevents cwd-based discovery from switching project identity and covers non-Git projects. |
| AC-3 | required | Preserves the server's correct self-anchored root. |
| AC-4 | required | Preserves portable, project-relative tracked configuration. |
| AC-5 | required | Prevents per-render-host configuration divergence. |
| AC-6 | required | Makes the Cursor anchor decision explicit. |
| AC-7a | required | The wave makes Codex a rendered host; without this pin the registration table silently keeps calling it instruction-only. |
| AC-7b | required | Tests the property the manual entry exists for (works with no cwd guarantee) instead of forcing textual identity with a form built on the opposite assumption. |
| AC-12 | required | Seeds ship to every target repository. Seed `011:52` is an install-time pass/fail gate for an artifact this change stops producing, so leaving it stale redistributes the defect on every future install. |
| AC-8 | required | Prevents hermetic subprocess evidence from being overstated as client compatibility. |
| AC-9 | required | Keeps every operating environment accounted for: executed where a runner exists, explicitly owed where none does, never assumed. |
| AC-10 | required | Ensures first-class MCP support ships as one portable, version-controlled surface. |
| AC-11 | required | Without it the corrected stanzas reach only fresh installs; because the MCP exposure is latent rather than an observed outage, a silently deferred fix would stay invisible until a host spawns from a non-root working directory. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-26 | Independent review removed the generic descendant locator and replaced it with verified host/config-owner anchors plus explicit root-only limitations. Added nested-install and non-Git controls. | Finding `descendant-locator-can-switch-project-identity`; executable outer/nested counterexample |
| 2026-07-25 | Pre-implementation review revisions: bounded cwd contract, separate host-consumption evidence, and Air census coverage added | Readiness findings `mcp-launcher-lacks-project-identity`, `host-config-tests-do-not-validate-host-consumption`, and `air-mcp-config-omitted-from-surface-census` |
| 2026-07-25 | Added native Windows, WSL2, macOS, and Linux as equal MCP delivery gates and decoupled MCP serialization from the withdrawn shared hook resolver | Operator first-class platform requirement and reconciled `1tjjk-bug` adapter design |
| 2026-07-25 | Required one Git-tracked, platform-neutral MCP artifact per host | Operator clarified that first-class support must not depend on per-platform generated files |
| 2026-07-26 | Reconciled the platform-evidence contract across Requirements, Scope, the matrix paragraph, Risks and AC priorities. A prior revision narrowed AC-9 alone, leaving five locations still asserting that a missing runner blocks delivery. | Finding `platform-evidence-contract-still-contradictory` |
| 2026-07-26 | Re-check repairs. Added `.wavefoundry/framework/install/install-log.template.md:31`, which carries the same install acceptance artifact as seed `011:52`, ships in every zip via `build_pack.py:808-824`, and persists into each target repo's live install log. It had also drifted independently (`command: "python"` vs the seed's `"python3"`). AC-12 widened from seed-only to all pack install acceptance artifacts, with an explicit note that a `seeds/`-only test does not satisfy it. Gate corrected to `framework_edit_allowed` for this file. Seed `160` recorded as touched by three changes, not two. | Prepare-council docs-contract seat, findings R3 and R4; `code_keyword` confirmation of both the template line and the `python`/`python3` drift |
| 2026-07-26 | Prepare-council repairs. AC-7 was falsified: it demanded parity with renderer output for hosts that have no renderer, and satisfying it literally would have replaced a working absolute manual form with a relative one for the four hosts least able to resolve it. Split into AC-7a (parity where real) and AC-7b (executability where not). Added the seed layer (`011:33/:42/:52`, `160:472-477`), the second copy-ready block in the install prompt, `native-windows-support.md` C-1 and the two-form paragraph, ADR `1p7pb-adr:27`, and the `NoPathedLauncherScanTests` invariant that a locator change necessarily breaks. | Prepare-council docs-contract seat (strongest challenge, F1, F4, F5) and red-team seat (F7) |
| 2026-07-26 | Old-code-window question answered rather than deferred: Phase 0b extracts before Phase 1, and `phase_surface_rendering` spawns the renderer as a subprocess from the overwritten scripts directory, so it runs new code. AC-11 now confirms that determination instead of re-deriving it. | Prepare-council red-team seat, finding F9 |
| 2026-07-26 | Extended the same reconciliation to the Tasks list and the Agent Execution Graph, which the previous pass omitted (the omission was visible in that pass's own scope note). A task demanding evidence nobody will produce is the same defect as an AC demanding it, and Tasks are the implementer's working checklist. | Finding `platform-deferral-not-applied-to-tasks-and-aeg` |
| 2026-07-26 | Implemented config-owner MCP paths without a cross-project locator: Claude uses `CLAUDE_PROJECT_DIR`; Cursor, Copilot and Windsurf pin their native working directory; Junie uses a config-relative path; Codex remains repository-root-only. The install/upgrade path rewrites stale launchers in one pass and preserves manual absolute entries for instruction-only hosts. | Render/setup/upgrade integration fixtures and generated project configs |
| 2026-07-26 | The first canonical full-suite run exposed a stale universal-argument test and renderer/ADR prose that still claimed every host used the same repo-relative `server.py` argument. Reconciled them to the implemented contract: `python3` is universal; owner/config anchoring is host-specific. | Pre-repair full suite: `test_render_platform_surfaces.py` failed for Claude and Junie; post-repair 61-test module green |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | Treat the MCP exposure as latent rather than a confirmed outage | The server runs correctly today on this repository, so claiming an active failure would misstate the evidence. The defect is that correctness depends on unenforced host behavior. | Report it as broken, rejected as unsupported by observation; leave it alone, rejected because Cursor's existing `cwd` pin shows the assumption already failed for at least one host. |
| 2026-07-25 | Share root-selection semantics, not one serialized resolver, between hooks and MCP stanzas | Hooks have host-native cwd/root fields while MCP clients consume shell-free command/argument vectors. Coupling their serialized commands would erase useful host guarantees. | One shared serialized resolver, rejected after host-contract review; unrelated root-selection rules, rejected for ownership drift. |
| 2026-07-25 | **Superseded 2026-07-26.** Bound MCP cwd independence to repository descendants plus verified host anchors. | The proposed descendant walk was later falsified by a nested-install counterexample: cwd can identify a different project than the configuration owner. | Preserve the arbitrary-cwd claim (rejected as unsupported); embed a machine-absolute path (rejected by the tracked-surface portability contract). |
| 2026-07-26 | Bind each stanza to a verified host/config owner signal, otherwise retain an explicit repository-root contract. | A generic upward locator fixes relative-path lookup by introducing project-identity corruption. Host-specific anchoring or an honest limitation is simpler and correct. | Nearest-installation walk (rejected by executed nested counterexample); global/user-home locator (rejected: extra authority and installation dependency). |
| 2026-07-25 | Include `.air/mcp.json` as a committed self-hosted surface without adding an Air renderer | The standing census already treats it as part of the runtime-entry surface, but Air remains provider-specific and instruction-only for distribution. | Omit it, rejected because it would retain the old command and break the census; add a generic Air renderer, rejected as unsupported product scope. |
| 2026-07-25 | Require real execution on Windows, WSL2, macOS, and Linux | MCP startup crosses executable lookup, argument quoting, path syntax, and process cwd boundaries that parser tests cannot prove. | Infer WSL2 from Linux or simulate platforms, rejected as insufficient for a first-class support claim. |
| 2026-07-25 | Keep platform variants inside the canonical committed host config | A clone must contain the complete registration contract before any local setup runs; official OS override fields preserve one reviewable authority. | Per-platform generated configs or a user-home locator, rejected because neither is a portable Git-tracked project surface. |
| 2026-07-26 | Keep the documented manual MCP entry absolute, and do not force it to match rendered output. | A host registered through a settings UI supplies no project working directory, so a repo-relative argument has nothing to resolve against. `docs/references/native-windows-support.md:50` already records this generated-relative versus manual-absolute split; the first version of AC-7 would have erased it and regressed the four instruction-only hosts. The split is now a recorded decision rather than an unexplained inconsistency. | Force textual identity with renderer output (rejected: falsified, and it regresses the hosts it claims to help); drop the manual entry entirely (rejected: instruction-only hosts have no other attachment path). |
| 2026-07-26 | **Supersedes the 2026-07-25 "Require real execution on Windows, WSL2, macOS, and Linux" row.** Record deferred platform cells rather than gating the wave on runners that do not exist. | macOS is executable here; native Windows is tested by the operator after the wave; WSL2 and Linux have no runner and the repository has no CI matrix. An AC demanding evidence nobody will produce is itself an unexecuted claim, which is the failure mode this project treats as a defect. The four platforms remain equal *targets*; only the evidence tier differs, and every unrun cell stays visible as `not_executed` with an owner. | Block the wave until runners exist (rejected: parks the fix indefinitely for a latent exposure nobody is measuring); claim the cells by simulation (rejected: explicitly forbidden by this document and dishonest). |
| 2026-07-26 | Keep each MCP stanza tied to its owning configuration and document root-only behavior where no stronger host signal exists. | This preserves the previously successful simple workflow while removing the confirmed cwd dependency only where the host supplies a trustworthy anchor. | One universal locator (rejected: nested-project identity corruption); machine-absolute paths in committed files (rejected: non-portable). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A `-c` argument vector is rejected by a specific MCP client's schema | AC-8 separates direct execution from client consumption; use live or official-schema evidence and record a per-host adapter when required. |
| Codex TOML quoting differs from JSON | AC-2 executes the parsed Codex stanza; AC-4 parses the TOML; AC-8 separately records whether Codex itself consumed it. |
| Changing a working registration breaks a host that was fine | AC-1 records which hosts already pass, so any regression is attributable; Cursor's pin is changed only under AC-6 with an explicit decision. |
| WSL2 is silently absorbed into a Linux result when a runner eventually exists | AC-9 records WSL2 as `not_executed` today and names both the Linux-filesystem and mounted-drive checkouts as the evidence still owed, so the gap stays visible rather than inferred. |
| An MCP stanza works only because of untracked machine state | AC-10 verifies the committed census from a clean clone and rejects platform-specific or user-home launcher dependencies. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
