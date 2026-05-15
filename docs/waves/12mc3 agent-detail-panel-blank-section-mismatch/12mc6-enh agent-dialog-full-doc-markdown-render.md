# Dashboard: Agent Dialog Renders Full Doc with Markdown Formatting

Change ID: `12mc6-enh agent-dialog-full-doc-markdown-render`
Change Status: `complete`
Previous Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

The agent detail dialog currently renders only sections matching a hardcoded allowlist (`_DETAIL_SECTIONS`). Projects whose agent docs use different heading names — or flat prose with no H2 sections — get a blank dialog. Rather than growing and maintaining a heading allowlist (a fragile, ever-drifting approach), the dialog should render the full agent document with lightweight markdown formatting. This is more robust, shows the complete agent definition, and requires zero parser logic that can drift. The existing `renderMarkdownish` function already handles bullets and paragraphs — it needs `##`/`###` header and `**bold**`/`` `code` `` inline support added.

## Requirements

1. The Python `collect_agents` function must pass the full agent document body (metadata header stripped) as a single `body` field on the agent dict, replacing the section-extraction loop.
2. `renderMarkdownish` in `dashboard.js` must handle: `## text` → section heading, `### text` → subsection heading, `**text**` → bold inline, `` `text` `` → code inline, `- bullet` → list item (already handled), blank lines → paragraph breaks (already handled).
3. `AgentDialog` must render the full body via the extended `renderMarkdownish` rather than mapping over `details` sections.
4. The metadata header block must be stripped before the body is passed to the client. The strip list must cover: the `# Title` H1 line, and lines beginning with `Owner:`, `Status:`, `Last verified:`, `Role:`, `Actor:`, `Schema version:`, `Last distilled:`. The strip must tolerate blank lines *within* the header block (journal files have blank lines between metadata fields) — it must stop only at the first line that is non-blank AND does not match any strip-list prefix. It must not consume content after the header block.
5. The `_DETAIL_SECTIONS` allowlist and the section-extraction loop in `collect_agents` must be removed. The existing `_extract_section` helper is retained (it is used elsewhere).
6. If the resulting `body` string is empty or whitespace-only (stub agent file), the field must still be present but the dialog must display a graceful placeholder ("No details available.") rather than a blank panel.
7. Tables in agent docs render as raw pipe-delimited text (full table support is out of scope); this is acceptable and must be noted as a known limitation in the Scope section.
8. `_collect_agents_from_dir` must require a `Role:` metadata field to be present for a file to be included in the agent list. Files without `Role:` (e.g. `session-handoff.md`, `platform-mapping.md`) are not agent role docs and must be excluded. This is more robust than a filename exclusion list and future-proofs against any non-role doc that lands in `docs/agents/`.
9. `_classify_agent_category` in `dashboard_lib.py` must short-circuit stem matching for the `specialist` group. The function currently checks `persona` and `journal` groups first, then falls into stem matching (`_REVIEW_STEMS`, `_COORDINATE_STEMS`, `_BUILD_STEMS`, etc.), with `return "specialist"` only at the very end as a fallthrough. Agents in `docs/agents/specialists/` whose stems are hardcoded in `_REVIEW_STEMS` (e.g. `reality-checker`) or `_COORDINATE_STEMS` (e.g. `council-moderator`) hit those branches and are miscategorized before the specialist fallthrough fires. Fix: add `if group == "specialist": return "specialist"` after the journal check (line 711) and before the stem matching begins (line 712). This makes group membership authoritative over stem heuristics for specialist agents.
10. The `status` field must be removed from agent docs and the dashboard. Agent roles do not have a meaningful lifecycle status — the field is boilerplate on every file and renders ambiguous badges (e.g. "current") for any non-`"active"` value. Remove `status_m` extraction and `"status"` from the agent dict in `_collect_agents_from_dir`; remove the status badge render from `AgentDialog`.
11. `WavesDialog` must render pending waves when no active waves exist. Currently the dialog renders active waves or falls through to "No pending waves." — pending waves are never rendered despite the title correctly switching to "Pending Waves". Fix: when `active.length === 0`, render `pendingWaves(waves)` the same way active waves are rendered; only show "No pending waves." when both lists are empty.

## Scope

**Problem statement:** `_DETAIL_SECTIONS` is a brittle hardcoded allowlist that silently produces blank agent dialogs for any project whose docs deviate from the expected heading names.

**In scope:**

- Remove `_DETAIL_SECTIONS` and section-extraction loop from `dashboard_lib.py`; retain `_extract_section`.
- Add `body` field (full cleaned doc text) to agent dict; remove `details` list.
- Extend `renderMarkdownish` in `dashboard.js` for `##` (section heading), `###` (subsection heading), `**bold**`, `` `code` `` support.
- Update `AgentDialog` to render `agent.body` via `renderMarkdownish`; show placeholder when body is empty.
- Add CSS for `h2`/`h3` elements rendered inside `.agent-dialog-body`.
- Update tests: assert `body` field, remove `details` assertions. Test file (`test_dashboard_server.py`) falls under `framework_edit_allowed` gate scope.
- Create `docs/agents/code-insight-agent.md` thin pointer doc so the CIA appears in the Agents panel alongside architecture-reviewer, security-reviewer, and code-reviewer.
- Add `Role:` required-field gate to `_collect_agents_from_dir` so non-agent docs (`session-handoff.md`, `platform-mapping.md`, etc.) are excluded from the Agents panel.

**Out of scope:**

- Full CommonMark compliance — only the formatting elements that appear in agent docs are needed.
- Table rendering — pipe-delimited table rows render as plain text (known limitation; acceptable for current agent docs).
- CSS restyling of the dialog beyond heading element styles.

## Acceptance Criteria

- AC-1: An agent doc with only flat prose produces a non-blank dialog showing the prose content.
- AC-2: An agent doc using `## Execution Contract` and `## Salience Triggers` renders those as visible section headings in the dialog.
- AC-3: `**bold text**` renders as bold; `` `inline code` `` renders as monospace in the dialog body.
- AC-4: The metadata header block (`Owner:`, `Status:`, `Last verified:`, `Role:`, `Actor:`, `Schema version:`, `Last distilled:` lines and the H1 title) is absent from the rendered body.
- AC-5: Existing agents with `## Operating Identity` render correctly under the new approach.
- AC-6: `### Subsection` headings render as visible subsection headings (smaller than H2) in the dialog.
- AC-7: A stub agent file with an empty body shows "No details available." rather than a blank panel.
- AC-8: The Code Insight Agent appears in the Agents panel alongside architecture-reviewer, security-reviewer, and code-reviewer.
- AC-9: `session-handoff.md` and `platform-mapping.md` do not appear in the Agents panel.
- AC-10: Agents in `docs/agents/specialists/` appear in the Specialist group on the dashboard, not in the Review or Coordinate groups.
- AC-11: The agent dialog shows no status badge — the category pill is the only classification chip displayed.
- AC-12: Opening the Waves tile dialog when no active waves exist shows the pending wave(s), not "No pending waves."

## Tasks

- [ ] Remove `_DETAIL_SECTIONS` and section-extraction loop from `dashboard_lib.py`; add `body` field (strip metadata header from doc text per Req 4); retain `_extract_section` helper.
- [ ] Extend `renderMarkdownish` in `dashboard.js` to handle `##` (h2), `###` (h3), `**bold**`, `` `code` ``; add graceful empty-body placeholder in `AgentDialog`.
- [ ] Update `AgentDialog` to render `agent.body` via `renderMarkdownish` instead of mapping `agent.details`.
- [ ] Add CSS for h2/h3 inside `.agent-dialog-body`.
- [ ] Create `docs/agents/code-insight-agent.md` thin pointer doc so CIA appears in Agents panel.
- [ ] Add `Role:` required-field gate to `_collect_agents_from_dir` so non-agent docs (`session-handoff.md`, `platform-mapping.md`, etc.) are excluded from the Agents panel.
- [ ] Add `if group == "specialist": return "specialist"` branch to `_classify_agent_category` in `dashboard_lib.py` after the journal check (approx. line 710), before stem matching begins.
- [ ] Remove `status_m` extraction, `_AGENT_STATUS_RE` usage, and `"status"` field from agent dict in `_collect_agents_from_dir`; remove status badge render from `AgentDialog` in `dashboard.js`.
- [ ] Fix `WavesDialog` in `dashboard.js`: render `pendingWaves(waves)` when `active.length === 0`; show empty state only when both active and pending are empty. No automated JS test exists — verify manually: with one planned wave and no active waves, the Waves tile dialog must show the pending wave row, not "No pending waves."
- [ ] Pre-step before removing `agent.details`: audit all JS call sites for `agent.details` (confirm only `AgentDialog` at line ~1052 reads it) before removing the field.
- [ ] Update tests (`test_dashboard_server.py`): assert `body` field, remove `details` assertions; add test for empty-body stub; add test for specialist group classification. (`framework_edit_allowed` gate covers this file.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| py-parser  | implementer | — | dashboard_lib.py: remove _DETAIL_SECTIONS, add body field; create CIA pointer doc |
| js-render  | implementer | py-parser | dashboard.js: renderMarkdownish + AgentDialog update + CSS |
| test-update | implementer | py-parser | test_dashboard_server.py: body assertions, empty-body stub test |

## Serialization Points

- `framework_edit_allowed` gate required for `dashboard_lib.py`, `dashboard.js`, and `test_dashboard_server.py`.

## Affected Architecture Docs

N/A — confined to dashboard agent rendering; no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Core fix — flat-prose agents must not be blank |
| AC-2 | required  | Heading structure must render visibly |
| AC-3 | important | Inline formatting common in agent docs |
| AC-4 | required  | Metadata clutter must not appear in the dialog |
| AC-5 | required  | Must not regress existing working projects |
| AC-6 | important | Subsection headings used in some agent docs (e.g. CIA prompt) |
| AC-7 | important | Stub files should degrade gracefully rather than blank |
| AC-8 | required  | CIA must appear in Agents panel — user-visible gap confirmed |
| AC-9 | required  | Non-agent docs must not appear as agents — root cause is same as _DETAIL_SECTIONS (no inclusion gate) |
| AC-10 | required  | Specialist agents silently miscategorized by stem matching — group branch missing from _classify_agent_category |
| AC-11 | required  | Status field has no meaningful lifecycle for agent roles; ambiguous values like "current" add noise with no signal |
| AC-12 | required  | WavesDialog title switches to "Pending Waves" correctly but content never renders pending waves — user sees empty dialog despite tile showing pending count |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Approach decided: full-doc render replaces allowlist; renderMarkdownish extension identified | Design review |
| 2026-05-14 | Red team + wave council review complete; 8 findings incorporated: extended strip list, empty-body AC/placeholder, ### AC, CSS task, table known-limitation, test file in gate scope, CIA pointer doc task, `details`→`body` API audit risk | Red team + wave council parallel review |
| 2026-05-14 | Product feedback: session-handoff.md and platform-mapping.md appear as agents (no Role: gate); Role: required-field inclusion added as Req 8 / AC-9 | Cross-project review |
| 2026-05-14 | Bug confirmed: _classify_agent_category missing group == "specialist" branch; specialists/ agents fall through to stem matching and get wrong category; one-line fix added as Req 9 / AC-10 | Cross-project review |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Full doc render over allowlist extension | Eliminates drift permanently; shows complete agent definition; simpler parser | Allowlist extension — still fragile, requires maintenance as new section names emerge |
| 2026-05-14 | Extend existing `renderMarkdownish` rather than a new renderer | Keeps rendering logic in one place | Separate `renderAgentDoc` function — unnecessary split |

## Risks

| Risk | Mitigation |
|------|------------|
| Long agent docs produce very tall dialogs | Dialog already uses `agent-dialog-body` with scroll; max-height CSS handles this |
| Metadata header lines leak into body | Explicit strip list: `# Title`, `Owner:`, `Status:`, `Last verified:`, `Role:`, `Actor:`, `Schema version:`, `Last distilled:` — strip stops at first non-metadata line |
| `Actor:` field after a blank line may not be caught | Strip must handle blank lines between header fields; pattern should match `Actor:` anywhere in the header prefix block, not just consecutive lines |
| Tables in agent docs render as raw pipes | Known limitation; acceptable for current agent docs. Noted in Scope. |
| `details`→`body` API change breaks any consumer reading `agent.details` | Audit all JS call sites for `agent.details` before removing the field |
| `Role:` gate excludes a legitimate agent doc that omits the field | Gate is applied only to `docs/agents/` subtree; any file that is intended as an agent role must have `Role:` — this is a doc authoring requirement, not a filtering heuristic |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
