# Distribution read tools in the pre-edit exemption

Change ID: `20wqb-enh distribution-read-tools-pre-edit-exemption`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-17
Wave: 20x1k distribution-review-and-read-tool-follow-ups

## Rationale

A downstream distribution (item K4 of its 2026-10-17 note) reported that the rendered Claude pre-edit hook exempts only core read-tier tools. `render_platform_surfaces._claude_core_read_contract` keeps names from core `mcp_tool_roster.TOOL_TIERS` that stay read-tier and are not override or replacement targets. So a distribution's aliases, overrides, read-tier replacements and new read-tier extension tools all fall to `report_unknown_tool`: a `COMPATIBILITY: unfamiliar tool` warning on every call, and every explicit path they carry is gated, so a read of a framework file is blocked while the edit gate is closed.

The operator chose to exempt every tool whose effective tier is read, including new tools a distribution declares `read` in `EXTENSION_TOOL_TIERS`. This matches trust the framework already extends: the Claude permissions allow-list (`roster.allow_rules`) already auto-allows every effective read-tier tool from `roster.all_tool_tiers()`. The exemption stays bound to the same two source digests.

## Requirements

1. **Exempt set.** `_claude_core_read_contract` exempts every name whose effective tier in `roster.all_tool_tiers()` is read. That covers:
   - core read tools;
   - overrides of core read tools, which keep the core tier;
   - aliases whose canonical tier is read, including an alias of a hidden core read tool, which is a visible registered read tool;
   - replacements whose effective tier is read;
   - each replacement's `alias_for_core` name when its core tier is read, even when the replacement itself is raised to write;
   - `EXTENSION_TOOL_TIERS` entries declared `read`.

   Hidden names stay excluded, because they are absent from `all_tool_tiers`. The edit-gate tools and their aliases are never exempt, because they and their aliases are write-tier. No separate exclusion is added, since it could never be reached. The function's docstring and comments stop saying "core" only.
2. **Contract unchanged.** The contract stays the same two-file digest of `mcp_tool_roster.py` and `mcp_tool_extensions.py`, so the extensions digest binds every added name. These cases still grant no exemption at all, core reads included:
   - a stale, missing, non-regular or malformed contract;
   - an invalid declaration.

   The rendered hook's `CORE_READ_TOOLS` and `CORE_READ_CONTRACT` keep their names and shape; only the name set grows.
3. **No new paths to exemption.** Lifecycle and artifact tools cannot become exempt: `mcp_tool_extensions` already requires every `EXTENSION_LIFECYCLE_TOOLS` and `EXTENSION_ARTIFACT_PATH_FIELDS` entry to be a write-tier extension tool. Replacements cannot lower write to read, and aliases take their canonical tier. No validation rule changes.
4. **Default installs unchanged.** With no declaration (this repository and every shipped default), the exempt set and the committed `.claude/hooks/pre-edit.py` are byte-for-byte unchanged.
5. **Docs.** Every statement that distribution tools keep explicit-path gating is updated:
   - `docs/agents/platform-mapping.md`, the Claude core-read passage. It says the exemption covers every effective read-tier tool, including declared distribution tools, bound to the two-file digest, and that stale or malformed data grants none.
   - `docs/architecture/threat-model.md`:
     - one sentence in the existing "Declared extension tool modules" trust row, saying a declared read tier is the distribution's own assertion;
     - the "Unfamiliar received hook tool names" and "File-writing tools with unsupported input schemas" rows, which now say declared read-tier tools are exempt rather than unfamiliar.

     The trust sentence covers four things. A tool or override mislabelled `read` skips the pre-edit path gate, as it already gains Claude auto-allow. The hook only ever inspected argument paths, never writes made inside a tool's own code. Extension and helper modules are trusted Python that is not sandboxed. The digest binds the declaration's source text, not cached bytecode.
   - `docs/specs/mcp-tool-surface.md`, at the `EXTENSION_TOOL_TIERS` entry: declaring `read` also grants the Claude pre-edit exemption and the allow-list entry.
   - Seed 050: the sentence "Known read/shell identities retain their exemption" says declared distribution read-tier tools share it. Edited under `seed_edit_allowed`.

   No live doc still says that overrides, aliases or extension tools retain explicit-path gating.
6. **Platforms.** Claude only. Copilot, Cursor and Windsurf pre-handlers have no read exemption and do not change. Behaviour is the same on Windows, macOS, Linux and WSL2: the hook is a Python body on every host, and the change is to the rendered name set only.

## Scope

**Problem statement:** the Claude pre-edit hook treats a distribution's declared read tools as unfamiliar.

**In scope:** Requirements 1 to 6 and their tests.

**Out of scope:**
- new declaration constants;
- digesting extension module sources;
- other hosts' hooks;
- any change to tier validation.

## Acceptance Criteria

- [x] AC-1: Each case runs in `tests/test_core_read_hook.py` under a real validated declaration, as a call carrying a framework path while the gates are closed.
  1. **Exempt (exit 0):**
    1. an override of a core read tool;
    1. an alias of a core read tool;
    1. an alias of a hidden core read tool;
    1. a read-tier replacement and its `alias_for_core` name;
    1. the `alias_for_core` name of a replacement raised to `write`;
    1. a new extension tool declared `read`.
  1. **Not exempt (exit 2):**
    1. a new extension tool declared `write`;
    1. an alias of a core write tool;
    1. an alias of `wf_open_gate`;
    1. a replacement raised to `write`;
    1. the hidden core name;
    1. `wf_open_gate`.
  1. **Fail closed:** a declaration that tries to lower a replacement from write to read is invalid, and the contract grants nothing, core reads included. The existing stale, missing, FIFO and malformed contract controls still fail closed.
  1. **Rewritten tests:** `test_overridden_core_and_aliases_are_not_exempt` and the alias assertion in `test_hidden_core_name_and_its_alias_are_not_exempt` are rewritten to the new rule, with `wf_gpu_doctor` itself kept at exit 2.
- [x] AC-2: With no declaration, `_claude_core_read_contract()` returns the same names as before this change, and the committed hook re-renders byte-for-byte.
- [x] AC-3: `test_render_platform_surfaces` declaration-aware hook parity passes under the default, `second` and `declared` profiles. `_expected_core_read_names` is re-derived without the renderer's code, in four steps:
  1. Take the committed default names.
  2. Remove replacements whose declared tier is `write`.
  3. Add aliases whose canonical name is read in the committed set, the declared tiers or a replacement tier, judged before hidden names are removed. Also add `alias_for_core` names of core read tools and `EXTENSION_TOOL_TIERS` names declared `read`.
  4. Remove hidden names, then sort.

  `test_expected_names_drop_hidden_overridden_and_replaced_names` is rewritten to the new rule, with a case for a raised replacement, and `DeclarationAwareHookParityTests` still refuses each known-bad shape. The `declared` profile covers aliases, the hidden-name alias and `dist_inventory`. Overrides and read replacements are covered by AC-1 only.
- [x] AC-4: In a scratch clone, each of these mutants of `_claude_core_read_contract` fails at least one AC-1 case:
  1. M1: the renderer change is reverted;
  1. M2: every declared name is exempt regardless of tier;
  1. M3: hidden names are not excluded;
  1. M4: a replacement's `alias_for_core` takes the replacement's tier instead of the core tier.
- [x] AC-5: A grep finds no live doc or seed outside `docs/waves` that still says overrides, aliases or extension tools retain explicit-path gating. Full docs validation passes, focused files pass, and the wave's single final whole-suite run passes with a fresh green receipt.

## Tasks

- [x] Change the name derivation and wording in `_claude_core_read_contract`.
- [x] Rewrite the three named tests and add the AC-1 cases.
- [x] Re-derive `_expected_core_read_names`.
- [x] Run the AC-4 mutants in a scratch clone.
- [x] Update platform-mapping, the three threat-model rows, the spec entry and seed 050.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer-and-tests | implementer | none | Requirements 1 to 4 |
| docs | implementer | none | Requirement 5 (platform-mapping, threat model, spec, seed 050) |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_core_read_hook.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/architecture/threat-model.md`
- `docs/agents/platform-mapping.md`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (three rows). No boundary or flow change otherwise.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The behaviour and its refusals. |
| AC-2 | required | Default installs must not change. |
| AC-3 | required | Hook parity is the guard on the rendered hook. |
| AC-4 | required | The tests must detect both failure directions. |
| AC-5 | required | Receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-17 | Planned from a code investigation of the hook exemption, tier declarations and parity tests. | investigator report (session) |
| 2026-10-17 | Implemented. `_claude_core_read_contract` now exempts every name whose effective tier in `all_tool_tiers()` is read, under the same two-file contract, and its docstring is updated. No separate edit-gate exclusion was added because it is unreachable. `test_core_read_hook`: `test_overridden_core_and_aliases_are_not_exempt` was replaced by `test_declared_read_tier_names_are_exempt_and_write_tier_names_are_not`, which uses one validated declaration. It checks that override, alias, hidden-name alias, read replacement, both `alias_for_core` names and a declared read tool are exempt, and that a write tool, a write alias, an alias of `wf_open_gate`, a raised replacement, the hidden name, `wf_open_gate` and `wf_prepare_wave` are gated. `test_invalid_declaration_grants_no_exemption_at_all` adds a single-reason lower-to-read refusal, which grants nothing, core reads included. `test_hidden_core_name_and_its_alias_are_not_exempt` was folded into the new test. `_expected_core_read_names` was re-derived in four steps, and its unit test (renamed `test_expected_names_follow_effective_read_tiers`) adds the raised-replacement case. Docs updated: platform-mapping, the threat-model trust row and two hook rows, the spec `EXTENSION_TOOL_TIERS` entry and seed 050. AC-5 grep: no live doc or seed outside `docs/waves` says extension tools keep gating. Focused `test_core_read_hook`, `test_render_platform_surfaces` and `test_docs_lint` pass under default, `--profile second` and `--profile declared`. The committed `.claude/hooks/pre-edit.py` is unchanged. Scratch mutants M1 to M4 are all killed. Gapfill: shell edits and scratch runs for anchored edits and mutation probes. | scratchpad mut20x1k.log |
| 2026-10-17 | Delivery repair cycle 1. DEL-2 (security): the digest covers only the bytes of `mcp_tool_extensions.py`, so a declaration that imports its tiers from another module could change them after render. Platform-mapping and the threat-model trust sentence now say declaration values must be literal assignments in that file. No AST check was added, because the actor already holds server authority. | security probe secprobe/k4.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-17 | Exempt every effective read-tier tool, including self-declared extension read tools. | Operator choice; matches the existing Claude auto-allow trust in `allow_rules`. | Aliases and overrides only; drop K4. |
| 2026-10-17 | Keep the two-file digest contract. | Every added name comes from the extensions declaration, already digested; smaller work. | Also digest extension and helper module sources. |
| 2026-10-17 | Readiness folded in: the three tests to rewrite (code, QA), gate-alias and invalid-declaration cases (security), the four-step oracle and mutants M3/M4 (QA), the fuller trust sentence (security), and every doc that says extension tools keep gating (docs-contract). The unreachable edit-gate exclusion was dropped. | Readiness reviewers. | Keep the exclusion as defence in depth; not taken, because no test could ever fail on it. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A write tool mislabelled `read` skips the pre-edit path gate. | Documented as the distribution's assertion (Requirement 5); lifecycle, artifact and edit-gate tools are structurally write-tier. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
