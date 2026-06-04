# Persona And Agent Discovery Polish With Role Field Enforcement

Change ID: `1p35l-enh persona-and-agent-discovery-polish-with-role-field-enforcement`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p35d install-flow-two-phase-with-log-and-audit`

## Rationale

Three connected failure modes from the consumer install retrospective:

1. **Agents generated `docs/agents/<role>.md` files without the `Role:` frontmatter field.** The dashboard reads `Role:` to surface and classify agents; missing field = silent skip. Result: install completed with agent docs present but dashboard showed an empty Agents panel.
2. **Seed-120 (persona synthesis) generated only the primary end-user persona.** Admin (`ROLE_ADMIN`), commissioner (`create-league.tsx`), and integration-consumer personas were all missed. The seed's coverage check ("are there usage patterns no persona represents?") is too weak — agents satisfice after the obvious persona.
3. **Seed-120 doesn't update `platform-mapping.md` after generating personas.** Personas land in `docs/agents/personas/` but the platform-mapping doc still shows zero personas because nothing updates it.

These are three separate fixes that share a root cause: **install verification doesn't catch silent gaps in user-facing surfaces** (dashboard empty panel = "feature unused", `platform-mapping.md` says "all roles available" when zero are present).

The wave-level fix is `wave_install_audit` (companion change `1p35h`) which would catch missing role docs as part of its checked-row validation. This change extends that gate to also enforce the **`Role:` frontmatter requirement** via `docs-lint` (so even non-install-time creation of agent docs without the field fails immediately) AND improves seed-120's persona-coverage discipline AND makes the dashboard explicit about discovery failures.

## Requirements

1. **`docs-lint` enforces `Role:` frontmatter on `docs/agents/*.md` and `docs/agents/specialists/*.md`.** Files without the field fail lint with the error `docs/agents/<file>.md: missing required Role: frontmatter field; the dashboard classifies agents by this field — missing field = invisible agent`.
2. **Exception list:** `docs/agents/README.md`, `docs/agents/specialists/README.md`, and any other clearly non-role files are excluded from the rule. Lint exclusion list lives in `wave_lint_lib/constants.py` alongside other doc-class exclusions.
3. **Seed-050 (agent-entry-bootstrap) prose explicitly requires `Role:` field in generated role docs.** Adds a bolded callout: "**Every generated role doc MUST include `Role: <role-name>` in the frontmatter. The dashboard classifies agents by this field; missing it makes the agent invisible.**" Currently the requirement is implicit; making it explicit reduces the agent's chance of skipping it.
4. **`wave_audit` adds `no_agent_role_docs` diagnostic** when `collect_agents()` returns empty or fewer than expected. Diagnostic includes recovery hint: "run seed-050 (Init agent surfaces) to generate role docs".
5. **Dashboard renders an empty Agents panel as guidance, not silence.** When zero agents are present, the panel displays: "No agent role docs found. Run **Init agent surfaces** (seed-050) to generate them." With the shortcut phrase as a clickable hint.
6. **Dashboard also surfaces malformed role docs.** Files matching the agent-doc path pattern but missing `Role:` are listed with a "missing Role: field — invisible" annotation. Counts toward a separate "needs attention" indicator. (Optional — can be deferred if scope tightens.)
7. **`platform-mapping.md` stub generator emits conditional content.** When zero per-role docs exist on disk, the stub says: "**Pending agent surface bootstrap.** Run **Init agent surfaces** (seed-050) to generate the per-role docs; this file becomes the availability matrix once roles exist." Currently the stub unconditionally claims all roles are available, which is false until seed-050 runs.
8. **Seed-120 (persona synthesis) gains a four-item explicit coverage checklist** before declaring done:
   - Is there a user with elevated privilege (admin, superuser, `ROLE_ADMIN`)?
   - Is there someone who installs, deploys, or operates the system?
   - Is there a user who configures or creates the structure others use?
   - Is there an API or integration consumer distinct from the end user?
9. **Seed-120 final step updates `platform-mapping.md`** with newly-generated personas. Step is mechanical (append rows to the personas table or refresh the file from a scan of `docs/agents/personas/`).
10. **Tests cover the new lint rule and the dashboard panel.** Lint test: file without `Role:` fails with the expected error. Dashboard test (if testable): empty Agents collection renders guidance.

## Scope

**In scope:**

- docs-lint `Role:` field enforcement on agent role docs
- Seed-050 prose update making `Role:` requirement explicit
- `wave_audit` `no_agent_role_docs` diagnostic
- Dashboard empty-panel guidance for Agents section
- `platform-mapping.md` stub conditional content
- Seed-120 four-item persona coverage checklist
- Seed-120 final step updating platform-mapping.md
- Tests for the lint rule

**Out of scope:**

- Dashboard malformed-doc annotations (optional / deferrable per requirement 6; can ship in a later change if scope tightens)
- Per-project persona templates (universal seed prose; project-specific evidence drives persona content)
- Rewriting seed-120 substantially — only the coverage checklist + final-step addition

## Acceptance Criteria

- [x] AC-1: docs-lint fails on `docs/agents/<role>.md` lacking the `Role:` frontmatter field with an actionable error message.
- [x] AC-2: Lint exclusion list includes `README.md` files under the agents tree.
- [x] AC-3: Seed-050 has a bolded `Role:` requirement callout in its generated-doc-format section.
- [x] AC-4: `wave_audit` emits `no_agent_role_docs` diagnostic when `collect_agents()` returns empty.
- [x] AC-5: Diagnostic includes a recovery hint pointing at seed-050.
- [x] AC-6: Dashboard Agents panel renders guidance text (with the `Init agent surfaces` shortcut) when zero agents are present.
- [x] AC-7: `platform-mapping.md` stub emits "Pending agent surface bootstrap" when zero per-role docs exist.
- [x] AC-8: `platform-mapping.md` stub generator is conditional on actual on-disk role-doc state, not unconditional.
- [x] AC-9: Seed-120 includes the four-item coverage checklist as an explicit numbered list before its "Synthesis" or "Output" section.
- [x] AC-10: Seed-120 includes a final step "Update `platform-mapping.md` with the newly-generated personas" with a concrete mechanism (append or regenerate from scan).
- [x] AC-11: Tests cover the new lint rule, including explicit positive cases for the three council role docs (`docs/agents/specialists/red-team.md`, `wave-council.md`, `archetype-council.md`) — verifies that these specific framework-default council docs are exercised by the `Role:` field enforcement and that they exist with the `Role:` field present in the self-host (post-1p33i state). Negative case verifies a synthetic role doc without `Role:` fails the lint.
- [x] AC-12: docs-lint passes.
- [x] AC-13: Full framework test suite passes.

## Tasks

- [x] Open `seed_edit_allowed` and `framework_edit_allowed` gates
- [x] Add agent-role-doc `Role:` enforcement to `docs-lint` validators
- [x] Add to lint exclusion list: README.md files under agents
- [x] Update seed-050 with bolded `Role:` requirement callout
- [x] Add `no_agent_role_docs` diagnostic to `wave_audit` / `collect_health()`
- [x] Update dashboard's Agents panel rendering to show guidance when empty
- [x] Update `platform-mapping.md` stub generator with conditional content
- [x] Update seed-120 with four-item coverage checklist
- [x] Update seed-120 with final-step `platform-mapping.md` update
- [x] Add tests for the lint rule
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Close gates

## Affected Architecture Docs

`N/A` — adds enforcement and conditional content to existing surfaces; no new components or boundaries.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (lint enforcement) | required | Catches the silent-skip failure at creation time, not at dashboard-render time. |
| AC-2 (exclusion list) | required | Without this, README.md files break lint. |
| AC-3 (seed-050 callout) | required | Explicit requirement reduces silent skips. |
| AC-4 (no_agent_role_docs diagnostic emitted) | required | Operators using wave_audit need to know about empty agent state. |
| AC-5 (diagnostic includes seed-050 recovery hint) | required | Without the pointer, the diagnostic isn't actionable. |
| AC-6 (dashboard guidance) | required | Empty panel = "unused feature"; guidance = "missing setup step". UX flip. |
| AC-7 (platform-mapping pending-bootstrap content) | required | Honest stub for the pre-seed-050 state. |
| AC-8 (stub generator is conditional) | required | The mechanism that makes AC-7 always-correct. |
| AC-9 (persona coverage checklist) | required | The retrospective's clearest seed-120 gap. |
| AC-10 (platform-mapping update step) | required | Without this, personas land but are invisible at the platform-mapping surface. |
| AC-11 (lint tests including three-councils positive cases) | required | Regression discipline + downstream-feedback-driven: invisible-in-dashboard agents were the failure mode; the three council docs are the canonical surfaces that MUST be visible. |
| AC-12 (docs-lint passes) | required | Standard hygiene. |
| AC-13 (framework test suite passes) | required | Regression discipline. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Enforce `Role:` field at lint time, not just at dashboard-render time | Catches silent failures earlier in the loop; lint runs every install audit (via 1p35h), so missing field surfaces immediately. | Surface only at dashboard — rejected; the dashboard is downstream of the failure. |
| 2026-06-03 | Conditional `platform-mapping.md` stub | Unconditional "all roles available" is factually wrong until seed-050 runs. Honest stub helps operators diagnose. | Keep unconditional and trust that seed-050 runs — rejected; the retrospective shows seed-050 doesn't always run successfully. |
| 2026-06-03 | Explicit four-item persona checklist rather than soft prose | Agents satisfice on soft prose. A numbered checklist with explicit items forces the agent to address each before declaring done. | Soft prose with stronger emphasis — rejected; satisficing is the documented behavior to prevent. |
| 2026-06-03 | Mark dashboard malformed-doc annotations (req 6) as optional/deferrable | Reduces scope risk without losing the load-bearing fix (the lint rule itself catches missing Role:). | Require the dashboard annotation — accepted as deferrable; not load-bearing. |

## Risks

| Risk | Mitigation |
|---|---|
| The lint rule fails on legitimate non-role docs under `docs/agents/` | Exclusion list. New non-role docs go on the exclusion list explicitly. |
| Dashboard guidance text drifts out of sync with seed-050 name | The shortcut phrase is the stable surface, not the seed number. The guidance says "Init agent surfaces" which is the operator-facing phrase. |
| `platform-mapping.md` stub becomes the source of truth instead of a stub | The stub is regenerated on install; operators editing it manually lose changes on next regen. Document explicitly: this file is generated; per-project edits go elsewhere. |
| Seed-120 four-item checklist forces personas that don't have evidence | Each item is "is there a..." — agent answers "no, no integrator pattern in this project" and moves on. The checklist makes the negative answer explicit, which IS the goal. |

## Related Work

- **`1p35f` (install log)** — Phase 2 of the log references seed-120 for persona synthesis. Improvements here flow through naturally.
- **`1p35h` (wave_install_audit)** — lint-as-you-go in the audit catches missing `Role:` fields when they happen.
- **`1p35j` (seed-050 authoritative-seed references)** — seed-050 prose is updated by both this change and 1p35j. Coordinate at implementation to avoid merge conflicts; semantically the two edits are non-conflicting.

## Session Handoff

Admitted to `1p35d` as a parallel-with-C3 polish change. Sequenced after `1p35f` and `1p35h`; can implement in parallel with `1p35j`.
