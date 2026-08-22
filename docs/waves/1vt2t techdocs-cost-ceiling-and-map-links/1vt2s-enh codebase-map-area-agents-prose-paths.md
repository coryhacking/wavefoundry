# Emit per-area `AGENTS.md` references in the codebase map as prose paths, not hyperlinks

Change ID: `1vt2s-enh codebase-map-area-agents-prose-paths`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-20
Wave: 1vt2t techdocs-cost-ceiling-and-map-links

## Rationale

`docs/references/codebase-map.md` is a PUBLISHED page. Its per-area context lines link to
per-area `AGENTS.md` files, which `exclude_docs` deliberately keeps OUT of the built site, so
every one of those links 404s in TechDocs. Today's dogfood reports exactly two, and they are the
only two findings this repository has:

```
techdocs_link_outside_boundary  references/codebase-map.md -> ../../AGENTS.md
techdocs_link_outside_boundary  references/codebase-map.md -> ../design-system/AGENTS.md
```

Wave `1vqqi` examined both and chose the standing-explanation branch, recording that the
generator's orientation criterion (link every area's context file for a cold-start reader) and the
audit's publication criterion (every link on a published page resolves to a published page) are
both correct and cannot both be satisfied while per-area `AGENTS.md` files stay unpublished. That
decision stands as recorded; this change resolves the tension instead of restating it.

**Why an id rather than a sentence.** This follow-up has existed only as prose at
`docs/agents/session-handoff.md:94` since wave `1vqqi`, and a `1vqqi` readiness seat explicitly
flagged that nothing enforces it. The same wave demonstrated the failure mode twice: the audit
timeout sat in a Risks row until it was minted as `1vqqj`, and the crossing-group ceiling until
`1vt2r`. A follow-up named only in prose is one nothing picks up.

**Why it is cheap.** The link TEXT is already the repo-relative path. The rendered line reads
`- Area context: [docs/design-system/AGENTS.md](../design-system/AGENTS.md) ...`, so dropping the
`[...](...)` wrapper keeps every character a cold-start reader needs and removes only the click.

## Requirements

1. **Emit the area-context reference as a prose path.** `render_markdown` emits
   `- Area context: \`<repo-relative path>\` — conventions/gotchas; consult before working in this
   area.` with no markdown link.

   **Not boundary-aware, and two successive drafts got the REASON wrong.** The first claimed the
   variant would reverse an arrow `layering-rules.md` records; that file has no `gen_codebase_map`
   entry at all. The second claimed its scripts row permits stdlib plus `wave_lint_lib/` only, so
   the import would be a new undeclared edge; that misreads the row, which is a LAYER rule whose
   May-Not column is `src/wavefoundry/`, and line 25 already records `techdocs_audit_lib`
   importing `render_agent_surfaces`, `index_state_store` and `subprocess_util`, all scripts-layer
   siblings. Under that reading the shipped code would already be in violation, so the reading is
   wrong. **No layering argument is offered here at all.**

   The ground that holds is that the fix needs no boundary knowledge. Precisely: the two live
   targets fail publication for DIFFERENT reasons, which the audit itself distinguishes in its
   finding details. The root `AGENTS.md` is **outside `docs_dir`** and can never be a site page;
   `docs/design-system/AGENTS.md` is inside `docs_dir` but **removed by `exclude_docs`**. A
   conditional would have to model both and would compute an answer that is always the same.

   **"Prose path" governs the FORM of the reference, not whether the line is emitted.** The
   existing `if ctx_rel:` guard stays: an area with no `AGENTS.md` emits no area-context line at
   all, as `test_no_link_when_agents_md_absent` pins. An earlier draft said "unconditionally",
   which read literally would regress the wave `1p5xc` fix.

2. **Decide the fate of `_area_context_link_href` explicitly.** With no href emitted, the helper
   becomes dead code, and deleting it also retires the Windows regression pin it carries: wave
   `1p6d6` made it use `posixpath.relpath` rather than `os.path.relpath` precisely because
   `ntpath.relpath` emits a backslash href that breaks both the markdown link and docs-lint on a
   Windows-generated map. Removing the helper removes that hazard along with its guard, which is
   fine, but it must be a recorded decision rather than a silent deletion. Name whether the helper
   and its tests are removed or retained, and say why.

3. **The orientation value is preserved, and the tradeoff is stated.** A reader browsing the
   repository on GitHub loses a click; the path is still right there to open. A reader of the
   built TechDocs site gains a reference that does not 404. Record that trade rather than
   presenting the change as pure win.

4. **EIGHT carriers assert that the map links a per-area `AGENTS.md`, and every one goes stale.**
   Two earlier drafts named two, because both searched for a single phrase (`links its
   AGENTS.md`) rather than for the claim. The census must be by MEANING:

   | Carrier | Class |
   | --- | --- |
   | `docs/index.md:49` | **published** landing page, nav entry 1 |
   | `docs/references/project-overview.md:49` | **published**, startup-order doc, `wavefoundry://overview` |
   | `docs/architecture/graph-index-system.md:541` | **published**, and names `render_markdown` explicitly |
   | `AGENTS.md:15` | repository entry surface |
   | `.wavefoundry/framework/seeds/020-run-contract.prompt.md:29` | **seed**, ships to every target repo |
   | `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md:120` | **seed** |
   | `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md:252` | **seed** |
   | `gen_codebase_map.render_markdown` docstring | the renderer's own stated contract |

   `docs/index.md:49` is the sharpest: it asserts the entries "link to `AGENTS.md` files", that the
   audit reports "**two** `techdocs_link_outside_boundary` findings", and that "the repair belongs
   in `gen_codebase_map._area_context_link_href`". All three are falsified here, the second by
   AC-1 itself, and the third names a helper Requirement 2 may delete.

   **Three seeds, not one.** Each seed edit is bracketed by
   `wf_open_gate(gate="seed_edit_allowed")` and `wf_close_gate(gate="seed_edit_allowed")`.

   **A retracted exclusion.** An earlier draft recorded `docs/index.md` as "checked and NOT
   affected" on a search that appeared to return nothing. It did not: three of four terms hit line
   49, and the output was truncated before the match was visible. That exclusion, and the wave
   watchpoint built on it, are both withdrawn. A surface-form sweep must cover every way the claim
   can be phrased, and must run LAST.

## Scope

**Problem statement:** Two links on a published page point at pages the built site does not
contain, which is the entire finding set for this repository.

**In scope:**

- The area-context line in `gen_codebase_map.render_markdown`.
- The disposition of `_area_context_link_href` and the three tests that reference it.
- Regenerating `docs/references/codebase-map.md`.
- The eight carriers of Requirement 4, three of them seeds behind the `seed_edit_allowed` gate
  and three of them published pages.

**Out of scope:**

- Publishing per-area `AGENTS.md` files. They are agent surfaces and `exclude_docs` removes them
  deliberately; that is the boundary working, not a defect.
- Any change to the audit. It is reporting correctly, and this change removes its findings by
  fixing the generated page rather than by relaxing the check.
- Boundary-aware link emission, refused in Requirement 1 on dependency-direction grounds.

## Acceptance Criteria

- [ ] AC-1: **This repository's dogfood reports ZERO findings.** `wf techdocs-audit` returns
  `verdict: clean`, 62 survivors, 4 nav entries, `degraded: []`, and exits 0. It reports 2 findings
  and exits 1 today, so this fails before the change. This is the criterion the whole change exists
  for and it is measured on the real tree, not a fixture.
- [ ] AC-2: The generated map still names both targets in full. `docs/references/codebase-map.md`
  contains `docs/design-system/AGENTS.md` and `AGENTS.md` as readable repo-relative paths on their
  area-context lines, with the surrounding guidance text intact. A change that drops the reference
  rather than de-linking it fails this, since the orientation value is the reason the line exists.
- [ ] AC-3: No markdown link to any per-area `AGENTS.md` remains in the generated map, asserted by
  a test over rendered output rather than by inspection, so a future regeneration cannot silently
  reintroduce one.
- [ ] AC-3b: **No carrier still claims the map "links" a per-area `AGENTS.md`.** All eight of
  Requirement 4's carriers are updated to describe it as NAMING the path, verified by a census
  that searches for the CLAIM rather than one phrasing (`links its`, `links each area`, `the map
  link`, `link to`, `linked to`), run LAST. `docs/index.md`'s three falsified assertions are
  corrected specifically, including its "two findings" count, which AC-1 takes to zero. Each of
  the three seed edits is bracketed by opening and closing `seed_edit_allowed`. A run that changes
  the renderer while leaving any carrier intact ships a documented claim the code contradicts, on
  surfaces including three published pages and three seeds that reach every target repository.
- [ ] AC-4: The three tests referencing `_area_context_link_href`
  (`test_gen_codebase_map.py` twice, `test_per_area_agents_context.py` once) are updated or removed
  per Requirement 2's recorded decision, and the full suite is green with no new skips. A skipped
  Windows pin counts as a silent deletion.

## Tasks

- [ ] Change the area-context line in `render_markdown` to emit a prose path.
- [ ] Record the `_area_context_link_href` decision, then apply it to the helper and its three
  referencing tests.
- [ ] Regenerate `docs/references/codebase-map.md` via **`index_build(content='map')`**, which is
  the only public path that forces a re-render. `generate_codebase_map` skips whenever
  `_fingerprint_inputs` matches, and that fingerprint covers the graph artifact and each area's
  `AGENTS.md` bytes but **NOT the renderer**, so a renderer-only change can leave the map stale
  with every command reporting success. `wf codebase-map` exposes no `--force`.
- [ ] Update all eight Requirement 4 carriers, opening and closing `seed_edit_allowed` around each
  of the three seed edits, then run the claim census of AC-3b LAST.
- [ ] Run the dogfood and confirm `verdict: clean`, 0 findings, exit 0.

## Agent Execution Graph


| Workstream | Role | Depends on | Notes |
| ---------- | ---- | ---------- | ----- |
| ws-1 emit prose path | implementer | — | The one-line change in `render_markdown`'s area-context line. |
| ws-2 helper disposition | implementer | ws-1 | Decide and apply the `_area_context_link_href` outcome per Requirement 2, including its three referencing tests and the wave `1p6d6` Windows pin they carry. |
| ws-3 carriers | implementer | ws-1 | The eight Requirement 4 carriers. Three seed edits each bracketed by `seed_edit_allowed` open/close; three published pages; `docs/index.md` needs all three of its assertions corrected. |
| ws-4 regenerate + verify | implementer | ws-1, ws-2, ws-3 | Regenerate via `index_build(content='map')` (the fingerprint does not cover the renderer), run docs-lint, run the dogfood to zero findings, then the AC-3b claim census LAST. |


## Serialization Points

Declared review targets. **`./AGENTS.md` carries its `./` deliberately:** the target parser drops
a bullet whose path has no directory separator, so a bare `AGENTS.md` parses as prose and the file
falls outside the declared universe the close-time footprint advisory uses.



- `.wavefoundry/framework/scripts/gen_codebase_map.py`
- `.wavefoundry/framework/scripts/tests/test_gen_codebase_map.py`
- `.wavefoundry/framework/scripts/tests/test_per_area_agents_context.py`
- `docs/references/codebase-map.md`
- `./AGENTS.md`
- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/index.md`
- `docs/references/project-overview.md`
- `docs/architecture/graph-index-system.md`

**No sibling coordination.** This wave carried a second change, `1vt2r-enh
techdocs-crossing-group-cost-ceiling`, which was WITHDRAWN at readiness after its premise was
falsified. Earlier drafts of this section coordinated a shared-dogfood constraint against that
change's AC-4; that coordination is void and is removed rather than left to confuse a reader.
This change now owns the dogfood outcome alone.

## Affected Architecture Docs

**NOT N/A.** `docs/architecture/graph-index-system.md:541` documents this mechanism by name:
"`render_markdown` links each area to its `AGENTS.md` when one exists", and lists "the map link"
as one of three discovery routes for per-area context. Changing the renderer makes that paragraph
false, which is the definition of an affected architecture doc. It is declared as a target, and
declaring it is what promotes **architecture-reviewer** into the required lane roster. Two earlier
drafts answered N/A here; the wave would have delivered an architecture-affecting change with the
architecture lane suppressed.

**Not affected, each checked rather than assumed:** `layering-rules.md` records no
`gen_codebase_map` entry in either direction, and this change adds no import, so no row moves.
`testing-architecture.md` carries no reference to `gen_codebase_map` or either of the two changing
test files, describes no tier or technique the three test edits alter, and pins no suite count.
Editing a seed's prose is not itself a flow change: `layering-rules.md` constrains seeds to text
files only, and seed `020`'s sentence renders into no surface in this repository.

**Removed:** an earlier draft justified refusing the boundary-aware variant here by claiming it
"would reverse the arrow `layering-rules.md` records". No such arrow exists. Requirement 1 now
disavows that reasoning, and this section no longer repeats it.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The zero-findings dogfood is the entire point of the change and is measured on the real tree. It fails today at 2 findings and exit 1. |
| AC-2 | required | De-linking must not become dropping. The orientation value is why the line exists, and a change that removes the reference satisfies AC-1 while defeating the purpose. |
| AC-3 | required | Asserted over rendered output rather than by inspection, so a later regeneration cannot silently reintroduce a link and quietly restore the findings. |
| AC-3b | required | Three seeds reach every target repository, so a stale "links" claim there is a framework-wide falsehood; three more carriers are PUBLISHED pages, one of which also asserts a finding count AC-1 takes to zero. Two earlier drafts found two of the eight by searching one phrase, which is why this AC pins the search key set rather than the file list alone. |
| AC-4 | important | The helper disposition changes no delivered behaviour. It is graded important because retiring wave `1p6d6`'s Windows pin silently, or leaving it as a skip, is the failure mode; the decision itself is legitimate either way. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
