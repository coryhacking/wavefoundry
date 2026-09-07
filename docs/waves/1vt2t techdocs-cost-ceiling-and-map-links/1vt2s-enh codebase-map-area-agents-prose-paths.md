# Emit per-area `AGENTS.md` references in the codebase map as prose paths, not hyperlinks

Change ID: `1vt2s-enh codebase-map-area-agents-prose-paths`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-07
Wave: 1vt2t techdocs-cost-ceiling-and-map-links

## Rationale

`docs/references/codebase-map.md` is a PUBLISHED page. Its per-area context lines link to
per-area `AGENTS.md` files, which the publication boundary deliberately keeps OUT of the built
site, so those links 404 in TechDocs. The current generated map renders one such target and the
dogfood reports one finding, which is the repository's entire current finding set:

```
techdocs_link_outside_boundary  references/codebase-map.md -> ../../AGENTS.md
```

The nested `docs/design-system/AGENTS.md` case remains part of renderer fixtures and the
publication rule, but its graph area is not in the current map's rendered community set. The
change preserves both root-level and nested repo-relative paths whenever their areas render.

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

   The ground that holds is that the fix needs no boundary knowledge. Precisely: the two target
   shapes fail publication for DIFFERENT reasons, which the audit distinguishes when each area
   renders. The root `AGENTS.md` is **outside `docs_dir`** and can never be a site page;
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

4. **EIGHT primary shipped carriers assert that the map links a per-area `AGENTS.md`, and every one goes stale.**
   Two earlier drafts named two, because both searched for a single phrase (`links its
   AGENTS.md`) rather than for the claim. The census must be by MEANING:

   | Carrier | Class |
   | --- | --- |
   | `docs/index.md:49` | **published** landing page, nav entry 1 |
   | `docs/references/project-overview.md:49` | **published**, startup-order doc, `wavefoundry://overview` |
   | `docs/architecture/graph-index-system.md:628` | **published**, and names `render_markdown` explicitly |
   | `AGENTS.md:15` | repository entry surface |
   | `.wavefoundry/framework/seeds/020-run-contract.prompt.md:29` | **seed**, ships to every target repo |
   | `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md:120` | **seed** |
   | `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md:252` | **seed** |
   | `gen_codebase_map.render_markdown` docstring | the renderer's own stated contract |

   The primary-carrier table is not the complete active-source census. Related comments, helper
   docstrings, test names, test comments, and assertions in `gen_codebase_map.py`,
   `test_gen_codebase_map.py`, and `test_per_area_agents_context.py` also use link/href language and
   must be updated when the helper is deleted. AC-3b therefore checks both groups: the eight named
   primary carriers and all active contract prose in those three source/test files. Historical
   records under `docs/waves/`, `docs/plans/`, `docs/reports/`, and `CHANGELOG.md`, plus this change
   document's descriptions of the former behavior, are evidence rather than current contracts and
   are excluded from the zero-stale-claim assertion.

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

5. **Correct every active statement about regeneration ownership.** Ordinary
   `indexer.py::build_index` deliberately does not regenerate the map because that creates a
   self-referential write/reindex loop. Current owners are create-mode prepare-and-open and
   create-mode close hooks, upgrade, the forced on-demand `index_build(content='map')` path, the
   direct change-only `wf codebase-map` / generator CLI, and the map resource's missing-file
   fallback. That missing-file fallback may write `docs/references/codebase-map.md`, the
   `.wavefoundry/index/graph/.codebase-map.fingerprint` guard, and the marker-bounded modules block
   in `docs/repo-index.md`. Ready-only and dry-run lifecycle modes do not regenerate it, and an
   ordinary resource read of an existing map performs no general freshness check.

   Update the complete active carrier set: `gen_codebase_map.py`'s generated banner/how-to text,
   `generate_safe` lifecycle docstring, and completion messages (which flow into
   `docs/references/codebase-map.md`),
   `docs/references/project-overview.md`, `docs/architecture/graph-index-system.md`,
   `docs/prompts/index.md`, seed `040-docs-structure-bootstrap.prompt.md`, the
   `_regenerate_codebase_map_safe`, create-mode call-site, `index_build`, and
   `resource_codebase_map` documentation/comments in `server_impl.py`, all three ownership comments
   in `indexer.py` (including `always-regenerated`), the post-index ownership comment in
   `setup_index.py`, and both generated-map
   comments in `test_indexer.py`. The universal resource-read contract in
   `docs/architecture/data-and-control-flow.md` also names that complete conditional write set as
   the explicit exception. Seed 030's existing gate covers both its link and ownership edits; seed
   040 is the fourth independent `seed_edit_allowed` edit. The final ownership census starts from
   the active repository tree so an omitted source/test carrier cannot evade it, explicitly checks
   `always-regenerated`, `index-build lifecycle`, unqualified prepare/close, `every rebuild`, and
   resource-read/freshness variants, then excludes historical records on the same basis as AC-3b.

## Scope

**Problem statement:** The current generated map contains one link to a page the built site does
not contain, which is the entire live finding set. The same renderer emits the failing form for
excluded nested `AGENTS.md` targets when those graph areas are present.

**In scope:**

- The area-context line in `gen_codebase_map.render_markdown`.
- The disposition of `_area_context_link_href` and the three tests that reference it.
- Regenerating `docs/references/codebase-map.md` and the modules block in `docs/repo-index.md`, both
  written by the required forced public map path. Their pending graph topology refresh is admitted
  as a mechanical generated-output update and both complete diffs are reviewed.
- The eight primary carriers of Requirement 4, three of them seeds behind the
  `seed_edit_allowed` gate and three of them published pages, plus related active contract prose in
  the renderer and its two test files.
- The active refresh-ownership carriers enumerated in Requirement 5, including the fourth gated
  seed, the data-and-control-flow resource exception, and prose-only source/test edits in
  `server_impl.py`, `indexer.py`, `setup_index.py`, and `test_indexer.py`.

**Out of scope:**

- Publishing per-area `AGENTS.md` files. They are agent surfaces and `exclude_docs` removes them
  deliberately; that is the boundary working, not a defect.
- Any change to the audit. It is reporting correctly, and this change removes its findings by
  fixing the generated page rather than by relaxing the check.
- Boundary-aware link emission. Requirement 1 rejects it because every known per-area `AGENTS.md`
  target requires the same prose form, so publication-boundary knowledge would add branching
  without changing the answer.

## Acceptance Criteria

- [x] AC-1: **This repository's dogfood reports ZERO publication findings.** Against the default
  `HEAD` comparison, `wf techdocs-audit` reports 62 survivors, 4 nav entries, zero findings, and no
  degradation other than `audience_not_informative`; that identity-only signal remains because
  `docs/ARCHITECTURE.md` is intentionally unchanged by this wave. The command may therefore retain
  a degraded verdict/exit while its publication finding set is clean. It reports 1 finding plus the
  same identity degradation today, so the finding-count assertion fails before the change. This is
  measured on the real tree, not a fixture; no cosmetic architecture-hub edit is admitted merely
  to change comparison identity.
- [x] AC-2: Every emitted area-context line still names its target in full. The live generated map
  contains `AGENTS.md` as a readable repo-relative path with the surrounding guidance intact, and
  rendered fixture coverage preserves `docs/design-system/AGENTS.md` for the nested case. A change
  that drops either reference rather than de-linking it fails this, since the orientation value is
  the reason the line exists.
- [x] AC-3: No markdown link to any per-area `AGENTS.md` remains in the generated map, asserted by
  a test over rendered output rather than by inspection, so a future regeneration cannot silently
  reintroduce one.
- [x] AC-3b: **No active carrier still claims the map "links" a per-area `AGENTS.md`.** All eight
  primary carriers in Requirement 4 and all related active contract prose in
  `gen_codebase_map.py`, `test_gen_codebase_map.py`, and `test_per_area_agents_context.py` describe
  the prose-path behavior. The LAST census searches those exact current-contract files for the
  claim rather than one phrasing (`links its`, `links each area`, `the map link`, `link to`,
  `linked to`, plus link/href test names and comments around area-context rendering). Historical
  waves, plans, reports, changelog entries, and this change document may still describe the former
  behavior and are excluded. `docs/index.md`'s three falsified assertions are corrected
  specifically, including its "two findings" count, which AC-1 takes to zero. Each of the three
  seed edits is bracketed by opening and closing `seed_edit_allowed`.
- [x] AC-4: The three tests referencing `_area_context_link_href`
  (`test_gen_codebase_map.py` twice, `test_per_area_agents_context.py` once) are updated or removed
  per Requirement 2's recorded decision; the helper-only `posixpath` and `PurePosixPath` imports
  are removed; and the full suite is green with no new skips. A skipped Windows pin counts as a
  silent deletion.
- [x] AC-5: No active Requirement 5 carrier claims ordinary `indexer.py::build_index` regenerates
  the map or that every index rebuild does so. All carriers name create-mode prepare-and-open,
  create-mode close, upgrade, forced on-demand `index_build(content='map')`, direct change-only
  CLI, and the missing-file resource fallback with no ready-only, dry-run, or general existing-file
  resource regeneration claim. The data-and-control-flow page records the missing-file map,
  fingerprint, and marker-bounded repo-index module writes as the one exception to its
  resource-read rule. The ownership census starts across the active
  repository tree and checks the named stale variants from Requirement 5 before excluding
  historical evidence and running last; seed 040's edit is independently bracketed by
  `seed_edit_allowed`.

## Tasks

- [x] Change the area-context line in `render_markdown` to emit a prose path.
- [x] Record the `_area_context_link_href` decision, then apply it to the helper and its three
  referencing tests.
- [x] Regenerate `docs/references/codebase-map.md` and `docs/repo-index.md` via
  **`index_build(content='map')`**, which is the only public path that forces a re-render.
  `generate_codebase_map` skips whenever
  `_fingerprint_inputs` matches, and that fingerprint covers the graph artifact and each area's
  `AGENTS.md` bytes but **NOT the renderer**, so a renderer-only change can leave the map stale
  with every command reporting success. `wf codebase-map` exposes no `--force`.
- [x] Update all eight Requirement 4 primary carriers and related active contract prose in the
  renderer and its two test files, opening and closing `seed_edit_allowed` around each of the three
  seed edits, then run the scoped claim census of AC-3b LAST.
- [x] While updating the declared graph-index architecture carrier, replace its obsolete
  ordinary-index-rebuild statement and update every other Requirement 5 ownership carrier. Open
  and close `seed_edit_allowed` separately around seed 040, then run the scoped ownership census
  last with AC-3b's claim census.
- [x] Run the dogfood and confirm 0 publication findings, 62 survivors, 4 nav entries, and no
  degradation other than the explicitly permitted `audience_not_informative` identity signal.

## Agent Execution Graph


| Workstream | Role | Depends on | Notes |
| ---------- | ---- | ---------- | ----- |
| ws-1 emit prose path | implementer | — | The one-line change in `render_markdown`'s area-context line. |
| ws-2 helper disposition | implementer | ws-1 | Decide and apply the `_area_context_link_href` outcome per Requirement 2, including its three referencing tests and the wave `1p6d6` Windows pin they carry. |
| ws-3 carriers | implementer | ws-1 | The eight Requirement 4 primary carriers plus active source/test contract prose and every Requirement 5 ownership carrier, including setup/test comments. Four seed edits each bracketed by `seed_edit_allowed` open/close; three link-contract published pages; `docs/index.md` needs all three of its assertions corrected. |
| ws-4 regenerate + verify | implementer | ws-1, ws-2, ws-3 | Regenerate both generated outputs via `index_build(content='map')` (the fingerprint does not cover the renderer), review their complete diffs, run docs-lint, run the dogfood to zero findings with only the allowed identity degradation, then the scoped AC-3b claim census LAST. |


## Serialization Points

Declared review targets. **`./AGENTS.md` carries its `./` deliberately:** the target parser drops
a bullet whose path has no directory separator, so a bare `AGENTS.md` parses as prose and the file
falls outside the declared universe the close-time footprint advisory uses.



- `.wavefoundry/framework/scripts/gen_codebase_map.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_gen_codebase_map.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_per_area_agents_context.py`
- `docs/references/codebase-map.md`
- `docs/repo-index.md`
- `./AGENTS.md`
- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md`
- `docs/index.md`
- `docs/prompts/index.md`
- `docs/references/project-overview.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/graph-index-system.md`

**No sibling coordination.** This wave carried a second change, `1vt2r-enh
techdocs-crossing-group-cost-ceiling`, which was WITHDRAWN at readiness after its premise was
falsified. Earlier drafts of this section coordinated a shared-dogfood constraint against that
change's AC-4; that coordination is void and is removed rather than left to confuse a reader.
This change now owns the dogfood outcome alone.

## Affected Architecture Docs

**NOT N/A.** `docs/architecture/graph-index-system.md:628` documents this mechanism by name:
"`render_markdown` links each area to its `AGENTS.md` when one exists", and lists "the map link"
as one of three discovery routes for per-area context. Changing the renderer makes that paragraph
false, which is the definition of an affected architecture doc. It is declared as a target, and
declaring it is what promotes **architecture-reviewer** into the required lane roster. Two earlier
drafts answered N/A here; the wave would have delivered an architecture-affecting change with the
architecture lane suppressed.

The immediately preceding sentence in that paragraph also says ordinary
`indexer.py::build_index` regenerates the map, while current `indexer.py` explicitly removed that
hook. The same false ownership claim survives in the startup overview, prompt index, seed 040,
renderer output, server tool/resource documentation, two imprecise indexer comments, the setup
wrapper, two staleness-test comments, and the data-flow page's universal no-write resource claim.
AC-5 covers that complete current-contract family and requires precise create-mode
prepare-and-open/close, upgrade, forced on-demand, direct CLI, and missing-file resource ownership.

`docs/architecture/data-and-control-flow.md` is also affected: its Path 6b says every resource read
has no writes or side effects, while a missing map invokes `generate_safe` and may write the map,
the graph fingerprint, and the marker-bounded repo-index modules block. The update preserves the
default read-only rule and records this complete fail-safe exception; existing-map reads remain
read-only.

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
| AC-1 | required | The zero-publication-findings dogfood is the entire point of the change and is measured on the real tree. It fails today at one finding; the independent `audience_not_informative` identity signal is explicitly allowed because an unchanged startup page remains outside scope. |
| AC-2 | required | De-linking must not become dropping. The orientation value is why the line exists, and a change that removes the reference satisfies AC-1 while defeating the purpose. |
| AC-3 | required | Asserted over rendered output rather than by inspection, so a later regeneration cannot silently reintroduce a link and quietly restore the findings. |
| AC-3b | required | Three seeds reach every target repository, so a stale "links" claim there is a framework-wide falsehood; three more carriers are PUBLISHED pages, one of which also asserts a finding count AC-1 takes to zero. Active renderer/test prose can preserve the same false contract under different names, so the census covers both enumerated primary carriers and scoped active source/test prose while excluding historical evidence. |
| AC-4 | important | The helper disposition changes no delivered behaviour. It is graded important because retiring wave `1p6d6`'s Windows pin silently, or leaving it as a skip, is the failure mode; the decision itself is legitimate either way. |
| AC-5 | required | The wave's forced-regeneration proof depends on accurate ownership across published docs, shipped seed guidance, generated output, and live source documentation. Correcting only one carrier would leave the active contract internally false. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-06 | Refreshed the pre-change dogfood baseline: 62 survivors, 4 nav entries, one `techdocs_link_outside_boundary` finding for the root `AGENTS.md` link, plus `audience_not_informative` because the audience pages still match `HEAD`. The nested design-system target is absent from the current rendered community set but remains covered as a renderer fixture. | `wf_techdocs_audit(compare_to="HEAD")`; `docs/references/codebase-map.md` area-context census. |
| 2026-09-06 | Prepare council found the wave record stale, the active claim census incomplete, and `docs/repo-index.md` missing from the forced-regeneration targets. The contract now distinguishes eight primary carriers from active source/test prose, excludes historical evidence from the final census, and admits both generated outputs plus their pending topology refresh. | `DOCS-PREP-1VT2T-001`, `DOCS-PREP-1VT2T-002`, `RED-PREP-1VT2T-002`; forced regeneration call-path and working-tree diff. |
| 2026-09-06 | QA proved `degraded: []` unreachable against default `HEAD`: `docs/ARCHITECTURE.md` remains identical and independently retains `audience_not_informative`. AC-1 now requires zero publication findings and permits only that named identity signal. | `QA-PREP-1VT2T-001`; live audit and in-memory `audience_report` probe. |
| 2026-09-06 | Architecture review found the declared graph-index paragraph still attributes map refresh to ordinary `indexer.py::build_index`, whose current source explicitly removed that hook. Requirement 5 and AC-5 now require the same paragraph to name current refresh ownership. | `ARCH-PREP-1VT2T-001`; `indexer.py` no-regeneration comment and `server_impl.index_build` map branch. |
| 2026-09-07 | Final current-contract census found the same obsolete ownership claim in the startup overview, prompt index, seeds 030/040, renderer/map prose, server documentation, both indexer comments, setup/test comments, and the data-flow resource contract. It also established create-mode-only lifecycle hooks, direct CLI ownership, and a missing-file-only resource fallback. Requirement 5 and AC-5 now start from the active tree, cover the complete family, and require a fourth gated seed. | `DOCS-PREP-1VT2T-004`; source call paths plus active-tree carrier census. |
| 2026-09-07 | Final architecture review traced the missing-map resource fallback through `generate_safe`: it may write the map, the graph fingerprint, and the marker-bounded repo-index modules block. The contract now names that complete conditional set while keeping existing-map reads read-only. | `ARCH-PREP-1VT2T-005`; resource-to-generator write-path trace. |
| 2026-09-07 | Implemented the prose-path renderer, deleted the obsolete href helper and imports, replaced its three direct test references with rendered root/nested/ancestor/absent coverage, corrected all declared link and ownership carriers, and forced both generated outputs through the public map-only tool after an in-process MCP reload. | Focused tests: 434 across the three affected test files (one fixture error repaired, rerun green); forced `index_build(content="map")` returned `regenerated: true`; complete generated diffs reviewed. |
| 2026-09-07 | Final verification passed. The TechDocs dogfood has 62 survivors, 4 nav entries, zero findings, and only `audience_not_informative`; docs lint has no errors; the active-source link and ownership censuses found no stale claim; the full framework suite recorded a fresh green receipt. | `wf_techdocs_audit(compare_to="HEAD")`; `wf_validate_docs`; MCP-first whole-tree census plus exclusion-scoped `rg`; `run_tests.py`: 8,524 tests across 75 files, 3 expected skips, OK. |
| 2026-09-07 | Delivery review found and repaired two contract gaps: Path 6b's adjacent state inventory contradicted its missing-map write exception, and the generated banner abbreviated the qualified regeneration-owner set. Code, QA, architecture, and docs-contract reviewers independently reverified the repairs; the standard-depth delivery council passed unanimously. | Delivery repair cycles 6 and 7 in `events.jsonl`; final declared-target fingerprint `45e868fba226cde5aef3eaa119ff47fc50fbb537b6fbcd68926fe1ee62b86be9`; fresh framework receipt: 8,524 tests across 75 files, OK. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-06 | Delete `_area_context_link_href` and replace its three href-specific tests with rendered prose-path coverage. | The renderer will no longer emit an href, so retaining the helper would be dead code. Removing it also removes the Windows backslash-href hazard at the same boundary; root and nested path preservation moves to output-level tests that exercise the delivered behavior. | Retain the unused helper and tests — rejected because it preserves no public behavior and leaves a misleading maintenance surface. |
| 2026-09-06 | Admit both generated files written by forced map regeneration and review their complete pending refresh. | `generate_codebase_map` always refreshes the repo-index modules block after rendering the map. The current graph artifact already produces topology changes in both outputs, so pretending the second write or broader refresh does not exist would make the declared footprint false. | Restore or hand-edit generated fragments after the public command — rejected because the checked-in outputs would no longer represent the generator's complete result. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A renderer-only edit can leave the generated map unchanged because the map fingerprint excludes renderer bytes. | Regenerate both outputs through `index_build(content='map')`, the public forced-render path required by the task, then inspect the emitted line and both complete diffs. |
| A surface-form-only search can miss stale claims that use different verbs or remain in test names/comments. | Update the eight enumerated primary carriers plus active renderer/test prose and run the scoped AC-3b meaning census last, excluding only named historical-evidence locations. |
| Seed prose can drift from the self-hosted docs if edited without its guard. | Open and close `seed_edit_allowed` around each of the four seed edits and validate the final rendered/public contract. |
| The default-HEAD audit remains degraded after its publication findings reach zero because one startup page is unchanged. | Grade AC-1 on the publication finding set and permit only `audience_not_informative`; do not add an unrelated edit merely to make comparison identity differ. |
| One ownership carrier could be corrected while another still promises ordinary index-build or general resource-read freshness. | AC-5 enumerates the active carrier family and requires a final scoped ownership census plus a separately gated seed-040 edit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
