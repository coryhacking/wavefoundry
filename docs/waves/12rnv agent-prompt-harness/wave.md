# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-20

wave-id: `12rnv agent-prompt-harness`
Title: Agent Prompt Harness

## Objective

Upgrade the Wave Framework **agent prompt generation surface** so reviewer and coordinator behavior matches a multi-stage **harness** (narrow scope, split questions, adversarial disprove, structured findings, project-evidence grounding)—not a single monolithic chat. All deliverables are **framework seeds** and bootstrap references first; target-repo `docs/agents/` extensions are generated from seeds plus local evidence on upgrade, not hand-edited as substitutes for seeds.

## Changes

Change ID: `12rbe-enh security-reviewer-exploit-chains`
Change Status: `implemented`

Change ID: `12rnv-enh agent-prompt-harness-effectiveness`
Change Status: `implemented`

Change ID: `12rcp-enh prompt-preflight-rubric`
Change Status: `implemented`

Change ID: `12rcd-maint agents-md-implementation-principles`
Change Status: `implemented`

Change ID: `12rp6-doc agent-role-metadata-lint`
Change Status: `implemented`

Change ID: `12rp6-enh factor-agents-dashboard-group`
Change Status: `implemented`

Change ID: `12rpn-enh factor-agents-shared-taxonomy`
Change Status: `implemented`

Change ID: `12rps-enh agent-category-metadata-dashboard-grouping`
Change Status: `implemented`

Change ID: `12rqn-enh prompt-surface-manifest-version-bump`
Change Status: `implemented`

Change ID: `12rqj-enh dashboard-wave-framework-visualization`
Change Status: `implemented`

Change ID: `12rqs-enh agent-pill-counter-removal`
Change Status: `implemented`

Change ID: `12rqt-enh active-wave-card-status-pill-removal`
Change Status: `implemented`

Completed At: 2026-05-20

## Wave Summary

Twelve framework changes on this wave: **`12rbe`** generalizes security-review seeds (`213`, security sections of `007`); **`12rnv`** adds harness core (`209`), other inferential sensors, specialists (`217`–`219`), and coordinator/bootstrap updates; **`12rcp`** consolidates prompt-preflight language for ambiguity routing and evidence-first review; **`12rcd`** adds `AGENTS.md` implementation principles and keeps the bootstrap seed aligned; **`12rp6-doc`** adds a docs validation rule for dashboard-visible agent-doc role metadata while keeping current journal behavior; **`12rp6-enh`** adds a new top-level `Factor` dashboard group separate from specialists; **`12rpn`** moves factor agents into the shared agent taxonomy and keeps `.claude/agents/` as a pointer surface; **`12rps`** introduces `Category:` as the dashboard grouping field and broadens the category contract through seeds and host wrappers; **`12rqn`** records the packaged prompt-surface manifest and framework revision bump (`2026-05-20c`); **`12rqj`** adds a Wave Framework visualization section with clickable process guidance in the dashboard, using change/wave checkpoint language; **`12rqs`** removes the visible usage-count badge from dashboard agent pills; **`12rqt`** removes the visible status pill from the active-wave card. Independent of wave **`12rbc mcp-impl-hot-reload`** (MCP hot reload), which may implement in parallel.

## Journal Watchpoints

- **Watchpoint:** `seed_edit_allowed` gate required for all edits under `.wavefoundry/framework/seeds/` — open immediately before seed work, close immediately after.
- **Watchpoint:** No implementation until **Prepare wave** completes successfully on this change.
- **Watchpoint:** Framework seeds stay **product-agnostic**; Wavefoundry-specific security checks (MCP path confinement, symbol extraction, etc.) belong in `docs/agents/security-reviewer.md` **after** seed land, via upgrade render—not in seed-213.
- **Watchpoint:** Do not treat draft work in agent chat as shipped until tests pass and `MANIFEST` lists new seed files.

## Review checkpoints

### Prepare wave — readiness verdict (2026-05-20)

**Verdict:** Ready for implementation.

- All eleven wave-owned changes are under `docs/waves/12rnv agent-prompt-harness/` with complete Rationale, Requirements, Scope, ACs, Tasks, and AC Priority.
- Required delivery lanes: `architecture-reviewer`, `docs-contract-reviewer`, `qa-reviewer` (all have AC priority tables).
- `product-owner: N/A — internal framework tooling; no external product UX or API contract change.`
- **Wave Council readiness:** fixed seats + rotating `docs-contract-reviewer`; signoff recorded below.
- **Council items addressed during implementation:**
  1. Confirm seeds are clean (`git status`) before opening `seed_edit_allowed`.
  2. Draft `209` first; lock before wiring references in other seeds.
  3. `050` must prohibit `## Project harness extensions` from appearing in seed bodies.
  4. `209` briefing packet: required fields are `wave_id`, `phase`, `change_ids`, `trust_boundaries_touched`, `files_in_scope`; other fields optional.
  5. `100` and `180`: add mode-dispatch guidance for `reality-checker`.
  6. Confirm lane name `code-reviewer` (not `code-review`) for `221` in `007` and participant tables.
  7. `12rp6-doc`: journals keep the current dashboard behavior; validation applies only to dashboard-visible agent docs.
  8. `12rp6-enh`: Factor is a new top-level dashboard group, discovered from the factor surface, not a specialist subtype.
  9. `12rpn`: factor agents live in the shared taxonomy and `.claude/agents/` becomes a pointer surface.
  10. `12rps`: category metadata drives dashboard grouping and propagates through seeds and supported host wrappers.
  11. `12rqn`: packaging revisions must keep `VERSION`, `MANIFEST`, and `docs/prompts/prompt-surface-manifest.json` aligned.
 12. `12rqj`: the dashboard visualization must explain the framework process flow using change/wave language without changing wave data contracts.
13. Active-wave cards should not show a visible status pill.
14. `12rqs`: agent pills should not show usage-count badges.

### Wave Council — readiness synthesis (2026-05-20)

**Seat roster:** architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team, docs-contract-reviewer (rotating).

**Agreement:** Scope is bounded to framework seeds and project agent docs. Serialization point (209 first) is recorded. AC-5 and AC-10 in `12rbe`/`12rnv` are structural guarantees for WF self-host correctness. `## Project harness extensions` boundary must be made explicit in `050`. Briefing packet required-field list must be enumerated in `209`. Journals keep the current dashboard behavior; factor agents get a new top-level `Factor` group.

**Material disagreements:** None.

**Council verdict:** Approved for implementation.

### Wave Council — delivery review (2026-05-20)

**Phase:** delivery  
**Seat roster (fixed):** architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team  
**Rotating seat:** docs-contract-reviewer

| Seat | Verdict | Key finding |
| ---- | ------- | ----------- |
| `architecture-reviewer` | **approved** | Docs-only wave; no module boundaries or runtime coupling. Seed-209 anchor pattern correct; harness extension placeholder cleanly demarcates seed/project boundary. ✓ |
| `security-reviewer` | **approved** | No new file-access tools or path arguments. Seed-213 verified clean — no `_resolve_repo_path`, `_SYMBOL_BLOCKLIST`, `MAX_SYMBOLS_EXTRACTED`, `_READONLY_TOOL`, or `.env` references. `docs/agents/security-reviewer.md` carries all relocated checks with correct reachability labels. AC-5 and AC-10 verified. ✓ |
| `qa-reviewer` | **needs-revision** (resolved) | AC-2 of 12rcd: `## Implementation Principles` placed after Stage Gate (line 173) rather than before it (line 106) — spirit of the AC (read at session start before gate) not achieved. **Resolved:** section moved to line 106, immediately before Stage Gate; re-verified 1482/1482, docs-lint clean. All other required ACs verified with evidence. |
| `reality-checker` | **approved-with-notes** | Key assumptions verified: seeds don't require tests ✓; generic seeds + project extensions = no product leakage ✓; briefing packet is convention not enforcement (acceptable trade-off). Advisory: new `code-reviewer` lane key is opt-in — no existing project references it; low risk. |
| `red-team` | **approved-with-notes** | Seed-213 WF-symbol removal verified clean. Advisory: `code-reviewer` lane name differs in suffix pattern from `architecture-review`, `security-review`, `performance-review` — cosmetic inconsistency; seed-221 `Lane:` header is authoritative and unambiguous. |
| `docs-contract-reviewer` | **approved-with-notes** | Seed-209 briefing packet contract and seed-216 mode definitions are clear and unambiguous. Seed-221 `Lane: code-reviewer` consistent with 007 table. Advisory: lane naming inconsistency (same as red-team). Seed-050 item 20 harness extension boundary clear and gate-enforced. ✓ |

**Material disagreements:** None.

**Council verdict: approved — AC-2 fix applied and re-verified; all required ACs met; 1482/1482 green.**

### Current state

Implementation and delivery review are complete. The wave remains active until operator signoff and closure.

## Review Evidence

- wave-council-readiness: approved (moderator: council-moderator; fixed seats + docs-contract-reviewer rotating; no material disagreements; pre-implementation items recorded above)
- wave-council-delivery: approved 2026-05-20 (all seats aligned; AC-2 AGENTS.md placement fixed and re-verified; 1482/1482 green; docs-lint clean)
- operator-signoff: approved 2026-05-20 (operator requested closure)

## Dependencies

- Informed by Cloudflare [Project Glasswing](https://blog.cloudflare.com/cyber-frontier-models/) harness lessons and community “environment over prompts” practice (layered entry surface, skeptical review, model-tier discipline).
- No code changes to `server.py` or MCP runtime in this wave.

## Serialization Points

- `209` must be drafted before other seeds reference it.
- `seed_edit_allowed` gate: single open/close around all seed edits.
- Shared bootstrap surfaces (`050`, `100`, `020`, `docs/prompts/index.md`) are a single write set; coordinate them as one serialized pass even if the surrounding seed bodies are split across changes.
- Packaging/version bumps must update the prompt-surface manifest and framework metadata together so the next packaging pass does not fail manifest revision checks.
