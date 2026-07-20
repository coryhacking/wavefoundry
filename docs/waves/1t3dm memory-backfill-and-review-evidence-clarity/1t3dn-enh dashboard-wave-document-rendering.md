# Dashboard Wave-Document Rendering

Change ID: `1t3dn-enh dashboard-wave-document-rendering`
Change Status: `complete`
Owner: framework
Status: complete
Last verified: 2026-07-19
Wave: `1t3dm memory-backfill-and-review-evidence-clarity`

## Rationale

The dashboard document dialog fetches both `wave.md` and change documents as
raw Markdown and sends them through the shared `renderMarkdownish` function.
That renderer currently trims and emits every non-special physical source line
as its own `<p>`. A human-readable Markdown paragraph wrapped across several
source lines therefore appears double-spaced, and each source line stops before
the available dialog width, leaving a misleading empty column on the right.
Wrapped list-item continuations are split for the same reason.

The renderer also treats Wavefoundry-owned HTML comments such as
`<!-- wave:context-efficiency begin -->` and their JSON state comments as
ordinary paragraphs. Those comments are machine ownership/control metadata,
not document content, and standard Markdown presentation does not show them.

Change documents can appear acceptable when their prose happens to contain
longer physical lines, but both document types share the same defective parser.
The repair therefore belongs in the shared renderer, with wave- and
change-document fixtures proving parity rather than a `wave.md`-only
preprocessor.

## Requirements

1. **Hide control comments.** Outside fenced code blocks, HTML comments are
   non-rendering control content. At minimum every Wavefoundry-owned
   `<!-- wave:* -->` begin/end/state marker is removed from the rendered DOM;
   the comment's payload must not become visible text or leave an empty
   paragraph. The same literal text inside a fenced code block remains visible.
2. **Markdown soft-line semantics.** Consecutive nonblank prose lines within one
   block are joined as one paragraph and allowed to wrap at the browser's
   available width. A blank line or a structural block boundary ends the
   paragraph. Source formatting at 80–100 columns must not create visual
   paragraph spacing or an artificial right-side gutter.
3. **Wrapped list continuity.** A physical continuation line belonging to an
   unordered list item remains in that item rather than becoming a separate
   paragraph. Existing list, heading, table, thematic-break, inline-code/link,
   and fenced-code behavior remains intact.
4. **One shared path.** Wave records and change documents continue to use the
   same `DocDialog` and shared Markdown renderer. Do not add a wave-specific
   text-rewriting path or mutate the raw Markdown returned by `/api/doc`.
   Census every other `renderMarkdownish` caller and preserve or intentionally
   improve its block behavior with focused evidence; do not assume the helper
   is document-dialog-only.
5. **Responsive prose width.** The document body uses the available dialog
   width and wraps normal prose, links, inline code, and long identifiers
   without horizontal page overflow. Tables and fenced code may scroll within
   their own bounded container when their content is intrinsically wider.
6. **Owned metadata remains available.** Hiding marker comments is presentation
   only. It must not delete or rewrite markers, state JSON, or other raw file
   content, and it must not affect lifecycle parsers, indexing exclusions, or
   MCP/resource reads.
7. **Consumer delivery.** Install, upgrade, self-host, and packaged dashboard
   assets receive the same renderer and CSS behavior with no legacy fallback.
8. **Reproducible layout evidence.** A checked-in Markdown fixture reproduces
   both screenshots. Browser checks use fixed 1440×900 desktop and 390×844
   narrow viewports, assert block counts/hidden comments and
   `document.body.scrollWidth <= document.body.clientWidth`, and assert any
   intrinsic overflow is contained by the relevant `pre` or table wrapper.
   These geometry/DOM assertions are the cross-platform acceptance authority;
   fixed-viewport screenshots are retained as human review evidence rather
   than a font-rendering-sensitive pixel baseline.

## Scope

**Problem statement:** The dashboard displays machine marker comments and
renders hard-wrapped wave prose as multiple widely spaced paragraphs that fail
to use the available reading width.

**In scope:**

- Block accumulation in the shared `renderMarkdownish` parser.
- Non-rendering HTML/Wavefoundry control comments outside fenced code.
- Paragraph and unordered-list continuation semantics.
- Document-dialog wrapping, overflow, and responsive-width CSS.
- Wave/change parity fixtures using real hard-wrapped Markdown, marker regions,
  tables, lists, inline code, and fenced marker examples.
- Dashboard static-asset install/upgrade/package parity and focused visual
  verification at desktop and narrow viewport widths.

**Out of scope:**

- Replacing the lightweight renderer with a third-party Markdown dependency.
- Editing, canonicalizing, or removing markers from source documents.
- Full CommonMark coverage, raw-HTML rendering, syntax highlighting, or a rich
  Markdown editor.
- Redesigning dashboard typography, dialog navigation, or the wave card.
- Changing the review-status projection or historical-memory contracts in the
  other changes in this wave.

## Acceptance Criteria

- [x] AC-1: Rendering the current `1t3dm` `wave.md` produces no visible
  `<!-- wave:* -->` marker or state JSON and no empty paragraph in its place,
  while the raw `/api/doc` response remains byte-identical. (required)
- [x] AC-2: A paragraph split across four physical source lines renders as one
  `<p>` whose text has correct word spacing and reflows with the dialog width;
  a blank line still creates a new paragraph. (required)
- [x] AC-3: A hard-wrapped unordered list item renders as one `<li>` with its
  continuation text, without an intervening sibling `<p>`. (required)
- [x] AC-4: Marker-looking text inside a fenced code block remains visible and
  unchanged; headings, tables, thematic breaks, links, inline code, and
  unclosed-fence behavior retain their existing fixtures. (required)
- [x] AC-5: The same wave and change bodies produce equivalent block structure
  through `DocDialog`; there is no document-type branch or wave-only
  preprocessing. Every other shared-renderer caller is inventoried and has a
  regression fixture or an explicit unaffected-by-construction rationale.
  (required)
- [x] AC-6: Against the checked-in operator-case fixture at 1440×900 and
  390×844, normal prose and long inline
  identifiers remain inside the document body, use its available width, and do
  not cause page-level horizontal overflow
  (`scrollWidth <= clientWidth`). Intrinsically wide code/table content is
  bounded or locally scrollable. (required)
- [x] AC-7: Dashboard source, install, upgrade, and packaged artifacts contain
  the repaired shared renderer/CSS, with no fallback to older asset behavior.
  (required)
- [x] AC-8: Focused dashboard renderer/server/browser tests, package and
  install/upgrade parity tests, the full framework suite, docs lint, fixed
  viewport geometry assertions, and retained screenshots of both
  operator-reported cases pass. The renderer is executed from canonical,
  built-package, installed, and upgraded assets. (required)
  **Status:** dashboard passes 182/182 with the opt-in real-Chrome tier,
  package 97/97, upgrade 332/332, and docs lint clean. The final exact-tree
  framework run passed 5,972/5,972 across 56 isolated files. An earlier
  load-sensitive p95 failure passed 3/3 in isolation and did not recur.

## Tasks

- [x] Add paragraph and list-item block accumulation to
  `renderMarkdownish`, with explicit flush boundaries.
- [x] Suppress HTML/control comments outside code fences without touching raw
  source or fenced examples.
- [x] Reconcile document-body wrapping and local overflow CSS.
- [x] Add DOM-level wave/change parity and regression fixtures for both
  screenshots.
- [x] Census every shared-renderer caller and pin affected snippet/activity
  surfaces.
- [x] Add responsive visual checks and package/install/upgrade asset parity.
- [x] Check in the minimal screenshot-reproduction Markdown fixture and retain
  fixed-viewport review captures without making platform font rasterization a
  correctness oracle.
- [x] Update dashboard behavior and testing documentation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| renderer-block-parser | implementer | — | Paragraph/list accumulation and comment suppression |
| dialog-layout | implementer | renderer-block-parser | Width, wrapping, and bounded overflow |
| consumer-parity | qa-reviewer | renderer-block-parser, dialog-layout | Wave/change DOM, package/install/upgrade, responsive checks |
| docs-review | docs-contract-reviewer | consumer-parity | Presentation-only boundary and operator behavior |

## Serialization Points

- `.wavefoundry/framework/dashboard/ds/wfds.js` is the one Markdown-rendering
  chokepoint; do not implement competing cleanup in `DocDialog`.
- Parser block flushing and CSS changes must be tested together because a
  parser-correct paragraph can still overflow or look artificially narrow.
- Dashboard asset packaging and upgrade replacement must be verified after the
  canonical source change; there is no runtime fallback to stale assets.
- This change may share dashboard consumer fixtures with `1t3dl`, but it does
  not own or reinterpret review-state data.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — raw `/api/doc` content to
  presentation-only Markdown render flow and marker hiding boundary.
- `docs/architecture/testing-architecture.md` — DOM, responsive, and packaged
  dashboard asset parity fixtures.
- Dashboard/operator reference documentation describing the document viewer,
  if its current behavior is documented there.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Machine ownership markers must not appear as user content |
| AC-2 | required | Physical source wrapping must not control visual paragraphs |
| AC-3 | required | Wave records rely heavily on wrapped coordination bullets |
| AC-4 | required | Parser repair cannot regress existing supported blocks |
| AC-5 | required | One shared renderer prevents wave/change drift |
| AC-6 | required | The reported width defect must be verified, not inferred |
| AC-7 | required | Target-project dashboards need the same repaired assets |
| AC-8 | required | Visual and consumer delivery evidence close the defect |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-19 | Planned from dashboard screenshots showing visible `wave:context-efficiency` ownership markers and hard-wrapped wave prose rendered as separate paragraphs. | Operator screenshots; `wfds.js:360-480`; `dashboard.js:4030-4075`; `dashboard.css:3666-3765` |
| 2026-07-19 | Implemented shared paragraph/list block accumulation, comment suppression outside fences, responsive document-dialog wrapping, and local table/code overflow. The raw `/api/doc` authority is unchanged and the same renderer remains shared by wave/change documents and snippets. | `dashboard/ds/wfds.js`; `dashboard/dashboard.css`; `test_dashboard_server.py` |
| 2026-07-19 | Verified 1440×900 and 390×844 layouts against the checked-in operator fixture: page/dialog widths remained bounded, normal paragraphs had zero overflow, and ownership markers were absent. Package assets contain and execute the repaired source; screenshots are retained as human evidence. | `tests/fixtures/dashboard-wave-rendering.md`; `evidence/dashboard-wave-1440x900.jpg`; `evidence/dashboard-wave-390x844.jpg`; browser geometry probes; `test_build_pack.py` |
| 2026-07-19 | Delivery repair added an exact census of all six prose-bearing `renderMarkdownish` call sites so a new caller cannot silently bypass renderer-contract review. Browser probes recorded exact page/dialog/body geometry (1440/858/790 desktop; 390/369/301 mobile), zero prose/inline overflow, hidden ownership markers, and table-local scrolling. Package and full-upgrade fixtures execute the extracted `wfds.js` under Node. | `test_dashboard_server.py` (181); `test_build_pack.py` (97); `test_upgrade_wavefoundry.py` (321); retained browser evidence |
| 2026-07-19 | Final delivery repair converted the retained geometry evidence into a checked-in opt-in browser regression. It runs the real renderer and stylesheet at exact desktop/mobile viewport sizes, asserts non-vacuous DOM coverage and all overflow/marker/table contracts, and remains capability-gated when Chrome is unavailable. | `test_fixed_viewport_browser_geometry_has_no_document_overflow`; `WAVEFOUNDRY_BROWSER_TESTS=1`; `test_dashboard_server.py` (182) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-19 | Repair the shared block renderer, not `wave.md` preprocessing. | Wave and change dialogs already share `DocDialog`; the defect is physical-line parsing. | Wave-only cleanup (rejected: duplicate behavior and future drift) |
| 2026-07-19 | Treat comments as presentation metadata outside fences. | Ownership markers must remain in raw source but should follow Markdown's non-rendering comment semantics. | Delete markers from source (rejected: breaks machine ownership); hide only one named marker (rejected: recurring defect) |
| 2026-07-19 | Preserve the lightweight dependency-free renderer. | The required block behavior is bounded and does not justify a new runtime dependency. | Adopt a full Markdown library (rejected for this scoped repair) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Joining lines changes intended separation | Blank lines and every structural block remain explicit flush boundaries |
| Comment suppression swallows code examples | Fenced-code state is evaluated before comment handling and is fixture-pinned |
| Lists regress during block accumulation | Wrapped and adjacent list items, following prose, tables, and headings get structural fixtures |
| CSS repair hides table/code content | Only normal prose wraps globally; intrinsically wide blocks scroll locally |
| Consumer projects retain old assets | Install, upgrade, and package parity tests require canonical replacement |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
