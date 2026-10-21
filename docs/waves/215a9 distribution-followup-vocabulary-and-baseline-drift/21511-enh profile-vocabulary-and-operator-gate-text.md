# Profile Vocabulary and Operator-Gate Text in Rendered Surfaces

Change ID: `21511-enh profile-vocabulary-and-operator-gate-text`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-20
Wave: 215a9 distribution-followup-vocabulary-and-baseline-drift

## Rationale

A downstream distribution refreshing to v1.34.0 reported that renaming the record vocabulary still needed rewrite rules for text Wavefoundry renders from literals, and that close skills on hosts without `disable-model-invocation` carry no instruction that closing is operator-owned (their Y2, Y4). Verified at `3d21af8e`:

- `ROOT_BRIDGE_BLOCK` (`.wavefoundry/framework/scripts/render_agent_surfaces.py:75-82`) hard-codes "open wave and change ids" and "open gates and wave status", although the skills around it already take nouns from `vocabulary_profile`.
- The `create_wave` scaffold (`wf_server/server_impl.py:8825-8830`) hard-codes "admitted changes", "wave card" and "<wave coordinator>"; only the title, id line and member heading come from `_vocab`.
- `operator_only=True` renders `disable-model-invocation: true` only into `.claude/skills` (`render_agent_surfaces.py:895-908`, deliberate per `2136l`). On `.codex/skills` and `.agents/skills` the body text is the only guard. The close-wave body already gates `mode="create"` on explicit operator instruction; the close-change body instead says "then `create` once the dry run is clean", which reads as permission, and the package body gates only publishing, not the build.
- Closing a `ready` change is permitted by design (`1zlu2`) and the tool reads no review evidence; the skill text does not state that required review still applies.

## Product Intent

Operators and distributions get rendered agent surfaces whose record nouns follow the vocabulary profile and whose operator-owned skills say, on every host, that the mutating step runs only on explicit operator instruction. Before: a renamed distribution rewrites four literals, and a Codex or `.agents` agent can read close-change as permission to close once a dry run is clean. After: the default profile renders byte-identical bridge and scaffold text, a renamed profile renders its own nouns, and the close-change and package skill bodies carry the same explicit-instruction gate close-wave has. Boundaries: no new mapping system (MCP tool names stay literal), no host-specific invocation controls beyond the existing Claude one, and no change to which statuses `wf_close_change` accepts. AC-1 with AC-3 tests whether the intent was established.

## Requirements

1. The root bridge block's compaction sentence takes its container and item nouns from `vocabulary_profile.tier_noun`; under the default profile its text is byte-identical to today's.
2. The `create_wave` Objective and Participants placeholders take their nouns ("admitted changes", "wave card", "wave coordinator") from `_vocab.tier_noun`; under the default profile the scaffold is byte-identical to today's.
3. The close-change skill body replaces "run `dry_run` (the default) first, then `create` once the dry run is clean" with: dry runs remain available freely, and `mode="create"` runs only when the operator explicitly instructs closing that change in the current request, never inferred from adjacent actions. It states the contract: the tool permits closure from `ready` and does not verify review evidence; required review must still be completed before closure.
4. The package skill body states that building the pack, as well as pushing tags and publishing, runs only on explicit operator instruction in the current request.
5. Requirements 3 and 4 render identically into every active skill host (`.claude/skills`, `.codex/skills`, `.agents/skills`); the Claude frontmatter behaviour is unchanged.
6. Wording uses existing profile helpers (`_vp_wave`, `_vp_change`, `_vp_shortcut`, `tier_noun`) only; MCP tool names (`wf_close_wave`, `wf_close_change`) stay literal.

## Scope

**Problem statement:** four sentences in rendered surfaces bypass the vocabulary profile, and two operator-owned skills lack the explicit-instruction gate on hosts that cannot disable model invocation.

**In scope:**

- `ROOT_BRIDGE_BLOCK`, the close-change and package skill bodies in `render_agent_surfaces.py`, and the `create_wave` scaffold text in `wf_server/server_impl.py`.
- Updating the skill-body pins, keeping the default-profile literal pin in `tests/test_per_area_agents_context.py`, and adding a renamed-profile oracle with hand-written expected strings.
- Re-rendering this repository's surfaces (`CLAUDE.md` bridge unchanged under the default profile; the three skill hosts' close-change and package `SKILL.md`).

**Out of scope:**

- Mapping MCP tool names through the profile (a separate proposal if wanted; noun substitution does not solve it).
- Host-specific manual-invocation controls for Codex or `.agents` (deferred until a host documents and we verify one).
- Changing the closable status set or adding a close-change review gate (declined, `1zlu2`).
- Seed 050's prose paraphrase of the bridge sentence (seed prose, not rendered from the renderer constant).
- The upgrade skill (it already requires approval of the patch plan).

## Acceptance Criteria

Name at least one AC, or a clearly identified combination, that tests whether the intent was established. Keep implementation checks where useful; delivery of guidance alone does not prove improved agent behavior.

- [x] AC-1: With a renamed tier-noun profile, the rendered root bridge block and the `create_wave` scaffold contain the renamed container and item nouns and none of the default "wave"/"change" literals in the touched sentences; under the default profile both are byte-identical to `3d21af8e`. Expected strings for both profiles are written as literals in the test, independent of the profile helpers under test.
- [x] AC-2: The rendered close-change skill body, on each of `.claude/skills`, `.codex/skills` and `.agents/skills`, contains the explicit-operator-instruction gate for `mode="create"` and the closure-from-`ready` contract sentence, and no longer contains "then `create` once the dry run is clean".
- [x] AC-3: The rendered package skill body on each active skill host gates building, tag pushing and publishing on explicit operator instruction; the close-wave and upgrade bodies are unchanged.
- [x] AC-4: The Claude `disable-model-invocation: true` frontmatter is still emitted for exactly the same skills, and non-Claude hosts still receive only `name` and `description` frontmatter.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Build `ROOT_BRIDGE_BLOCK` from `vocabulary_profile.tier_noun`, keeping the no-backslash replacement constraint.
- [x] Replace the `create_wave` placeholder nouns with `_vocab.tier_noun` calls.
- [x] Rewrite the close-change skill body lines (gate plus contract sentence) and the package gate line.
- [x] Keep the `test_per_area_agents_context.py` default-profile literal pin; add a renamed-profile oracle for the bridge block and scaffold whose expected strings are hand-written literals, not built from the profile helpers; update skill-body pins.
- [x] Re-render surfaces (`render_platform_surfaces.py`) and confirm the diff is limited to the two skill bodies on each host.
- [x] Add a CHANGELOG Unreleased bullet.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                     |
| ---------- | ----------- | ---------- | ----------------------------------------- |
| render     | implementer | none       | renderer constant, skill bodies, scaffold |
| tests      | implementer | render     | profile-derived pins, renamed oracle      |
| surfaces   | implementer | tests      | re-render and diff check                  |


## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_per_area_agents_context.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.claude/skills/wf-close-change/SKILL.md`, `.codex/skills/wf-close-change/SKILL.md`, `.agents/skills/wf-close-change/SKILL.md`
- `.claude/skills/wf-package/SKILL.md`, `.codex/skills/wf-package/SKILL.md`, `.agents/skills/wf-package/SKILL.md`

## Affected Architecture Docs

N/A: wording and vocabulary sourcing inside one renderer and one scaffold; no module boundary, flow or verification seam changes.

## Platform Behavior

Identical on Windows, macOS, Linux and WSL2: the change alters string content only. Rendered files keep the existing platform-newline writer (`_write_repo_text_platform_newlines`), so CRLF handling on native Windows is unchanged.

## AC Priority


| AC   | Priority  | Rationale                                                 |
| ---- | --------- | --------------------------------------------------------- |
| AC-1 | required  | the vocabulary request itself, with default-profile safety |
| AC-2 | required  | the operator-gate guard on hosts without frontmatter       |
| AC-3 | important | package build gate                                         |
| AC-4 | required  | no regression of the existing Claude control               |
| AC-5 | required  | change-local verification                                  |


## Progress Log
| Date       | Update  | Evidence                                    |
| ---------- | ------- | ------------------------------------------- |
| 2026-10-20 | Planned | distribution v1.34.0 feedback Y2/Y4 triage |
| 2026-10-20 | Readback: render profile nouns in the root bridge and create-wave placeholders while preserving default bytes; replace automatic close wording and require explicit package-build instruction on all hosts. AC-1–5 cover literal profile oracles and unchanged frontmatter. Example: admitted changes becomes admitted waves under the Set/Wave profile. Own renderer/scaffold tests and generated skill bodies; no tool-name remap or new lifecycle gate. | Current admitted plan and readiness approval |
| 2026-10-20 | Implemented profile-derived bridge/scaffold nouns and explicit operator gates; regenerated exactly the six close-change/package skills. Callable regex replacements preserve literal backslashes in renamed nouns. | 21 focused renderer/vocabulary/frontmatter tests and 7 lifecycle scaffold tests passed. Full default bridge and generated wave record match `3d21af8e` byte-for-byte; historical hard-coded scaffold and replacement-string mutants were detected. Renderer manifest: six expected paths only. |
| 2026-10-20 | Related renderer, vocabulary, extension skill and lifecycle suites passed. Full source frozen for independent delivery review. | 904 tests passed in 169.964 seconds; 2 existing skips. Full documentation validation passed. |
| 2026-10-20 | Implementation and delivery review complete. All acceptance criteria and tasks have evidence; no deferrals. | Final canonical suite: 12,005 tests across 203 files, 12 existing skips, 714.645 seconds, OK; current framework receipt written. Full docs validation passed before final bookkeeping and is rerun at handoff. Six specialist and council delivery approvals recorded; all three cycle-1 findings independently reverified and terminal. |

## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-20 | Use existing profile helpers for nouns and add body-text gates on all hosts | smallest change that removes the rewrite rules and guards non-Claude hosts | (a) map MCP tool names through the profile too: a new mapping system, beyond the request's need; (b) emit invented frontmatter keys on Codex and `.agents`: unverified host behaviour, rejected in `2136l` |
| 2026-10-20 | Keep `ready` closable; state the contract in skill text | operator decision in `1zlu2`; the text closes the misreading without a new gate | add a per-change readiness gate: rejected in `1zlu2`, no lane model |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Default-profile output drifts by a byte and churns every target's `CLAUDE.md` | AC-1 byte-identity check against `3d21af8e` |
| A downstream rewrite rule now double-substitutes | release note names the four sentences now profile-driven |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
