# Dashboard AC and Task Continuation Lines

Change ID: `1t1un-bug dashboard-ac-task-continuation-lines`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-07-20
Wave: `1t1uo dashboard-multiline-ac-tasks`

## Rationale

The dashboard's Active/Pending AC and Task dialogs receive item text from
`dashboard_lib.py`. Before this change, the parser matched only the physical
source line containing the list marker, so hard-wrapped continuation lines were
discarded before the frontend rendered them. The shared dialog CSS already
permitted text wrapping; the missing text was a backend parsing defect.

## Requirements

1. Parse each AC or task as a complete Markdown list item using one bounded,
   deterministic rule with caller-specific starters: ACs accept the existing
   top-level `-` or `N.` markers, while Tasks retain their existing top-level
   `-` marker only. After that marker, join only nonblank prose lines indented
   beyond the marker's indentation. A blank line, unindented prose, heading,
   blockquote, table row, fenced-code delimiter, thematic break, or list marker
   at any indentation terminates the current item and does not participate in
   its text; only a later top-level marker starts another item. Section
   extraction remains bounded by the next `##` heading. Normalize joined prose
   lines with ordinary word spacing.
2. Preserve checkbox/deferred state, AC identity, priority mapping, counts,
   inline-code text, and existing support for unordered/ordered AC items and
   plain or checkbox task items.
3. Do not merge one sibling item into another or absorb unrelated prose.
4. Deliver the repair through canonical, packaged, installed, and upgraded
   dashboard backend assets without a frontend-only workaround.

## Scope

**Problem statement:** AC and task dialog rows show only the first physical
line of a hard-wrapped list item.

**In scope:**

- Shared AC/task Markdown-list extraction in `dashboard_lib.py`.
- Backend snapshot/API and package/install regression coverage.
- Live dashboard restart and operator-case verification.

**Out of scope:**

- Changing dialog layout, typography, or completion/deferred styling.
- A general-purpose Markdown parser replacement.
- Reopening Wave `1t3dm`.

## Acceptance Criteria

- [x] AC-1: A hard-wrapped AC from the operator case appears in `ac_items`
  with every continuation line present exactly once and normalized to ordinary
  inter-word spaces. (required)
- [x] AC-2: A hard-wrapped task appears in `tasks_items` with the same complete
  text behavior. (required)
- [x] AC-3: Adjacent AC/task siblings remain distinct and retain their original
  checkbox/deferred state, AC ID, priority, and counts. For both AC and Task
  sections, fixtures prove that blank/unindented prose, nested/sub-list
  markers, headings, blockquotes, tables, fences, and thematic breaks are not
  absorbed into item text. (required)
- [x] AC-4: Existing single-line, ordered AC, plain-bullet, inline-code, and
  terminal-status fixtures remain green; ordered-task support is not
  introduced. (required)
- [x] AC-5: Canonical, packaged, installed, and upgraded dashboard backend
  assets execute the same parser behavior. (required)
- [x] AC-6: After dashboard restart, the operator-case AC/task rows display the
  complete text and wrap naturally without page-level horizontal overflow
  under the existing CSS. This is an observational check; any newly discovered
  styling defect becomes a separate change rather than expanding this wave.
  (required)
- [x] AC-7: Focused dashboard/package/upgrade tests, docs lint, and the full
  canonical suite pass. (required)

## Tasks

- [x] Add a bounded shared list-item extraction helper for ACs and tasks.
- [x] Route both `_parse_ac_items` and `_parse_tasks` through the helper.
- [x] Add exact 2+-continuation-line, sibling-boundary, unrelated-prose,
  structural-line, state/priority, and inline-code regression fixtures for both
  AC and Task sections.
- [x] Execute the parser regression against an extracted package/install tree
  and a post-upgrade installed tree; source-string or asset-presence parity is
  insufficient.
- [x] Restart the dashboard and verify the operator case.
- [x] Run focused suites, docs lint, and the canonical suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| parser-and-tests | implementer | — | One shared backend chokepoint |
| live-verification | qa-reviewer | parser-and-tests | Restart and inspect operator case |
| delivery-review | wave-council | live-verification | Focused correctness/release review |

## Serialization Points

- `dashboard_lib.py` and `test_dashboard_server.py` are single-writer files.
- Package/install assertions follow the canonical parser repair; no parallel
  frontend workaround is permitted.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` only if the dashboard parsing-flow
description needs clarification. No architecture boundary changes are planned.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Direct operator-visible defect |
| AC-2 | required | Tasks share the same defect class |
| AC-3 | required | Prevents parser boundary regressions |
| AC-4 | required | Preserves existing format support |
| AC-5 | required | Framework delivery must match source |
| AC-6 | required | Confirms the actual dashboard outcome |
| AC-7 | required | Delivery verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-20 | Planned after the closed `1t3dm` dashboard follow-up report. | Current parser regexes capture one physical line; shared CSS already wraps supplied text. |
| 2026-07-20 | Implemented one shared, caller-specific list-item parser and routed AC/task payload construction through it. | Production snapshot regression preserves complete hard-wrapped text, sibling identity/state/priority/counts, and ordered-task exclusion. |
| 2026-07-20 | Independent attack review found and repaired two adjacent parser defects before delivery. | Section extraction now preserves common horizontal indentation; pipe-less Markdown header/separator pairs terminate items while ordinary inline-pipe prose remains valid. |
| 2026-07-20 | Proved distribution parity by execution, not file presence. | Extracted package/install and post-upgrade target probes import and execute `dashboard_lib.py` against multiline AC/task content. |
| 2026-07-20 | Restarted the live dashboard and verified the actual AC and Task dialogs. | Full hard-wrapped strings are present; long rows render at 40–60px over a ~20px line height, each row's `scrollWidth == clientWidth`, and page `scrollWidth == clientWidth` at the 1280px viewport. |
| 2026-07-20 | Completed final verification after all review repairs. | Dashboard 188/188 (1 existing skip); extracted package/install and post-upgrade execution probes green; canonical 5,978/5,978 across 56 isolated files; docs-lint green; `git diff --check` clean. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-20 | Repair backend list-item extraction, not CSS or frontend rendering. | The API payload has already discarded continuation text; the frontend cannot display data it never receives. | Force row height/ellipsis changes (rejected: presentation does not restore missing text). |
| 2026-07-20 | Use a small bounded section-list helper rather than a full Markdown parser. | AC/Task sections need sibling-boundary and continuation semantics only. | Replace dashboard parsing with a general Markdown AST (rejected: disproportionate scope). |
| 2026-07-20 | Preserve horizontal indentation at section extraction and recognize only table header/separator pairs when outer pipes are absent. | Common indentation is semantic input to sibling detection; paired detection stops real pipe-less tables without treating ordinary inline pipes as structure. | Strip all horizontal edges (rejected: loses sibling level); reject every line containing `|` (rejected: false positives in prose). |
| 2026-07-20 | Recognize only the unambiguous `=` Setext-heading underline in this bounded grammar; keep `---` as the explicit thematic-break boundary. | Treating hyphens as Setext would retroactively remove an accepted continuation and contradict the wave's pinned thematic-break behavior. | Implement full Markdown block precedence (rejected: outside the bounded parser contract). |

## Risks

| Risk | Mitigation |
| --- | --- |
| Continuation parsing absorbs the next item or prose. | Exact sibling and unrelated-prose boundary fixtures. |
| Nested formatting changes counts or identity. | Preserve existing marker/ID/priority logic and pin it in tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
