# Refresh Shipped Guru Subagent Description

Change ID: `237ej-enh refresh-shipped-guru-subagent-description`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-12
Wave: `237ei tool-reference-and-guru-description-follow-ups`

## Rationale

When `.claude/agents/guru.md` already exists, the renderer refreshes only its body. `_merge_claude_agent` in `render_agent_surfaces.py` keeps the existing frontmatter verbatim so an operator's `model:`, `effort:` or other keys survive. The side effect is that a project never receives a changed subagent `description:`, and Claude Code picks the subagent from that line.

Two shipped changes have hit this:

1. The description moved from **Plan feature** to **Plan change**. Seed 160 (around line 538) tells the upgrading agent to edit the line by hand. `reconcile_scan._guru_description_hits` flags a description that still says **Plan feature**.
2. Change `237eg` dropped "or where to find implementation" from the description, so code-location lookups stop being routed to Guru. Seed 160 step 6 (around line 809) tells the upgrading agent to edit the line by hand. Nothing detects a project where that step was skipped, and such a project keeps routing direct lookups to the subagent.

`docs/prompts/upgrade-wavefoundry.prompt.md` repeats both instructions (around lines 444 and 560). The `237ef` delivery council named this gap as the strongest remaining challenge.

The file has two sources, and between them they have shipped five description texts before the current one.

1. **The renderer**, per git history of `render_agent_surfaces.py`:
   1. "PROACTIVELY use when the user asks how this repository's source code or project documentation works — behavior, architecture, specs, framework scripts, indexing, chunking, retrieval, or where to find implementation. Do not use for wave lifecycle commands (Plan feature, Implement wave, Close wave, Prepare wave, etc.)."
   2. The same text naming **Plan change**.
   3. The same text written with the `@PLAN@`, `@IMPLEMENT@`, `@CLOSE@` and `@PREPARE@` placeholders, which `_vp_shortcut` fills with the project's shortcut phrases. Under the default vocabulary this equals text 2.
2. **Seed 050's Claude Code template**, which an installing agent writes by hand before the renderer can run, per git history of the seed:
   1. "PROACTIVELY use when the user asks how this repository's source code or project documentation works. Do not use for wave lifecycle commands (Plan feature, Implement wave, Close wave, etc.)."
   2. The same text naming **Plan change**.

A project whose description equals one of these texts never customized it, so replacing it is safe. A customized description stays untouched.

## Product Intent

Projects that upgrade get the current Guru subagent routing without the upgrading agent having to edit frontmatter by hand, and operator-customized frontmatter is still preserved. Before: an upgraded project keeps a stale description unless the agent follows a manual seed 160 step. After: the renderer replaces any description either source previously shipped, leaves any other description and every other key alone, and seed 160 asks for a manual check only when the description was customized. AC-1 tests the intent.

## Requirements

1. **Replace a previously shipped description.** When the renderer merges an existing `.claude/agents/guru.md`, it replaces the `description:` line with the current description from `CLAUDE_GURU_AGENT` when all of these hold:
   1. The frontmatter is valid under the existing `_claude_agent_frontmatter` check.
   2. The frontmatter has exactly one `description:` line.
   3. That line's value, without its line ending, equals a known previously shipped description.

   The file's line ending (LF or CRLF) and any byte-order mark are kept. On replacement the renderer prints one stderr notice naming the file, so an operator who kept the old wording on purpose can see the change.
2. **The known set.** Keep the previously shipped descriptions as one named constant next to `CLAUDE_GURU_AGENT`, holding the five texts in the Rationale. The placeholder variant is filled by the same `_vp_shortcut` substitution the current constant uses. A comment says to add the outgoing text whenever the description changes in the renderer or in seed 050.
3. **Leave everything else alone.**
   1. A description that matches no known text, including the current one, is left as is.
   2. Every other frontmatter key and its order are kept byte for byte.
   3. Malformed or ambiguous frontmatter is still left unchanged, with the existing warning.
   4. Only the Guru subagent is affected. `_merge_claude_agent`'s only caller is the Guru tier-3 write, and no other Claude agent file changes behavior.
4. **Retire the manual steps, keep a fallback.** Replace the four hand-edit instructions: seed 160 near lines 538 and 809, and `docs/prompts/upgrade-wavefoundry.prompt.md` near lines 444 and 560. The replacement says:
   1. the renderer refreshes a previously shipped description;
   2. a customized description is kept;
   3. when a kept description still names a retired phrase (which `reconcile_scan` flags) or routes code-location lookups to Guru, the upgrading agent edits that one line and keeps every other key.

   Seed 160's model/effort pin row (near line 979) is unrelated and unchanged.
5. **Keep the reconcile scan as a backstop.** `reconcile_scan._guru_description_hits` stays, for customized descriptions. Update its comment (above `_CLAUDE_GURU_AGENT_FILE`) to say the renderer now replaces previously shipped descriptions, so a hit means a customized one.
6. **Platform behavior.** The comparison is text-only and is the same on Windows, macOS, Linux and WSL2. A CRLF file keeps CRLF line endings.

## Scope

**Problem statement:** Upgraded projects keep a stale Guru subagent description unless an agent edits it by hand, and nothing detects the skipped `237eg` edit.

**In scope:**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`: the known-description constant and the Guru merge
- `.wavefoundry/framework/scripts/reconcile_scan.py`: the comment only
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`: new tests, and `test_rendered_subagent_description_matches_the_renderer` inverted
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` and `docs/prompts/upgrade-wavefoundry.prompt.md`: the four instructions
- `CHANGELOG.md` `[Unreleased]`

**Out of scope:**

- Changing the description text itself
- Merge behavior for any other Claude agent file
- A new drift check (the cause is removed, and the reconcile scan stays for customized descriptions)
- Making the description framework-owned with an opt-out key (see Decision Log)

## Acceptance Criteria

- [x] AC-1: Rendering over an existing `.claude/agents/guru.md` whose description is each entry of the known set writes the current description and keeps every other frontmatter key byte for byte, in LF, CRLF and byte-order-mark files, with the stderr notice. The cases are built from the known-set constant, not literal copies. The placeholder variant is also checked under a non-default vocabulary. A test fails on the current renderer.
- [x] AC-2: These are each left unchanged by a render, each in a test:
   1. a customized description;
   2. the current description;
   3. malformed frontmatter;
   4. frontmatter with two `description:` lines.

   A test also asserts that the known set is non-empty and does not contain the current description.
- [x] AC-3: Seed 160 and the rendered upgrade prompt no longer tell the agent to edit a shipped Guru description by hand, and state the renderer behavior and the customized-description fallback. `test_rendered_subagent_description_matches_the_renderer` is inverted to assert this, and its comment no longer says the line is kept equal by hand. The `reconcile_scan` comment is updated.
- [x] AC-4: The changelog describes the change. The edited documents validate. The change's tests pass in the default, declared and second profiles.

## Tasks

- [x] Open `framework_edit_allowed`; add the known-description constant and the Guru description refresh; update the `reconcile_scan` comment; add and invert tests; close the gate.
- [x] Open `seed_edit_allowed`; edit seed 160's two instructions; close the gate; mirror the edits in the rendered upgrade prompt.
- [x] Add the changelog bullet.
- [x] Run focused tests in the default, declared and second profiles and full docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| renderer-and-seed | implementer | none | Renderer merge, tests, seed 160 and the rendered prompt |


## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

N/A: the change is confined to one renderer merge and the upgrade prompt text, with no boundary, flow or verification impact.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The intent: upgraded projects receive the current description |
| AC-2 | required | Operator customizations must survive, and the known set must stay correct |
| AC-3 | required | The manual step is retired, with a fallback for customized descriptions |
| AC-4 | required | Release notes and validation |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-12 | Planned from the `237ef` delivery council follow-up. | `git log` over `render_agent_surfaces.py` |
| 2026-11-12 | Readiness review round 1 amendments. Code (CR-EJ-1, blocking) and QA (QA-RDY-1) found that seed 050's two template texts were missing from the known set; red-team (RT-3) found the same. Added them. Also added: the single-description-line rule and the stderr notice (CR-EJ-4, RT-5); all four hand-edit sites and a customized-description fallback (DOC-1 and the docs seat note); the `reconcile_scan` backstop and comment (DOC-2, CR-EJ-2, RT-4); the inverted test (QA-RDY-3, CR-EJ-3); the known-set assertions (QA-RDY-2); the second profile and a non-default vocabulary case (QA-RDY-4, RT-3). The Rationale's "nothing checks" claim is narrowed to the `237eg` edit. | `.wavefoundry/work/237ei/code-readiness.md`, `qa-readiness.md`, `docs-readiness.md`, `redteam-readiness.md`; `git log` over seed 050 |
| 2026-11-12 | Readiness review round 2: code, QA, docs-contract and red-team confirmed the five-text known set against `git log --all`. QA advisory: AC-1 now also covers a byte-order-mark file, which Requirement 1 already promised. | `.wavefoundry/work/237ei/qa-readiness-r2.md`, `code-readiness-r2.md`, `redteam-readiness-r2.md` |
| 2026-11-12 | Implemented. `render_agent_surfaces.py`: `CLAUDE_GURU_DESCRIPTION`, `previous_guru_descriptions(shortcut=None)` (the five shipped texts; the placeholder form is filled at call time, so a renamed vocabulary is honored) and `_refresh_guru_description`, applied to the merged Guru content only after `_merge_claude_agent` accepts the header. The known set was checked byte for byte against every historical `description:` line in `git log` over the renderer and seed 050: all five match and the current description is absent. Seed 160 (both sites) and the rendered upgrade prompt (both sites) now state the refresh and the customized-description fallback, naming "where to find implementation"; the `reconcile_scan` comment is updated. Tests: `GuruDescriptionRefreshTests` (each shipped text in LF, CRLF and BOM files with the stderr notice; the placeholder form under a renamed vocabulary, and kept under the default one; customized, current, two-description and malformed headers kept; the known-set assertions; a control that empties the known set and fails) and the inverted `test_rendered_subagent_description_matches_the_renderer`. Focused run of six files: default 950 tests OK, no skips; declared and second profiles 0 of 6 files failed. | `run_tests.py --file test_render_agent_surfaces.py` and five other files, three profiles |
| 2026-11-12 | Delivery repair cycle 1, finding GURU-REFRESH-DEL-1 (red-team RT-DEL-1 and RT-DEL-2, reproduced by the code reviewer): a shipped first line followed by an indented continuation line was replaced, and a quoted duplicate `'description':` key was not counted. `_refresh_guru_description` now counts the key in any quoting or indentation, requires the single hit to be a plain unindented `description:` line, and keeps the header when the next line is indented. New kept cases: continuation line, single- and double-quoted duplicate keys, indented description; three failed before the fix. Red-team's strongest alternative is also adopted: `test_current_description_is_pinned` pins the current description (shortcuts as placeholders, so it holds under every profile) and fails on any change until the outgoing text is added to `previous_guru_descriptions()`. `test_render_agent_surfaces.py`: default 217 tests OK, no skips; declared and second 0 of 1 files failed. | `.wavefoundry/work/237ei/redteam-delivery.md`, `code-delivery.md`; `run_tests.py --file test_render_agent_surfaces.py`, three profiles |
| 2026-11-12 | Repair cycle 1 amended before reverification: the code reverifier found that a continuation after an empty line (`description: <shipped>`, blank line, indented text) was still replaced, because only the immediately following line was checked. The continuation check now uses the first non-empty following line, and a kept case covers the shape. A qa-reviewer approval recorded before this amendment reviewed the earlier code and is superseded by the re-approval that follows the reverification. `test_render_agent_surfaces.py`: default 217 OK, no skips; declared and second 0 of 1 files failed. | `.wavefoundry/work/237ei/code-reverify-c1.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-12 | Replace only a description the renderer or seed 050 previously shipped | It fixes every uncustomized project without touching operator choices | Keep the manual seed 160 step (the defect); a drift check (detects but does not fix); always overwrite the description (loses customizations) |
| 2026-11-12 | Keep the known-set design over a framework-owned description with an opt-out key (red-team's strongest alternative) | It needs no new frontmatter key and no migration for existing customized files; the known set grows by one entry per wording change, enforced by a comment and the AC-2 assertion | Framework-owned description with an opt-out key |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future description change forgets to add the outgoing text to the known set | The constant's comment states the rule; AC-2 asserts the current description is not in the set |
| An operator deliberately kept an old shipped wording | The stderr notice names the file on replacement |
| A project's shortcut vocabulary differs from the substitution used when the file was written | That description matches no known text and is left as is; the seed 160 fallback covers it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
