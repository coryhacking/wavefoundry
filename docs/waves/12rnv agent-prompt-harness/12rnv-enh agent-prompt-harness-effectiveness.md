# Agent Prompt Harness Effectiveness

Change ID: `12rnv-enh agent-prompt-harness-effectiveness`
Change Status: `implemented`
Owner: wave-coordinator
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

Agent quality in the Wave Framework depends on **orchestrated lanes**, not one long prompt. Research and operator practice converge on the same model:

1. **Cloudflare Project Glasswing** ([cyber frontier models](https://blog.cloudflare.com/cyber-frontier-models/)) — narrow scope, adversarial validate, split questions (defect vs reachability), parallel tasks with dedupe, structured reports.
2. **Environment over prompts** — durable operating surface (`AGENTS.md` as index), continuity (waves, handoff, journals), skills/MCP, and **skeptical review lanes** rather than “is my code good?” in the implementer thread.

Today, framework seeds mix **portable process** with **product-specific checks** (especially `213-security-reviewer`), lack a **briefing packet** contract, and do not define **disprove-only** validation or **structured finding records**. Coordinators can invoke “review the wave” without scoped inputs.

This change delivers **generic framework seeds first**. Each seed instructs agents to read **project evidence** (`threat-model`, `workflow-config`, `docs/agents/<role>.md`, etc.) and to add **`## Project harness extensions`** only when rendering target-repo surfaces (`050`), never inventing product facts in the seed.

**Sibling change:** `12rbe-enh security-reviewer-exploit-chains` in this wave owns generalized **seed-213** and security portions of `007`. Coordinate implementation order with the coordinator (security seeds may land first).

## Requirements

### R-Core — Shared harness (`209-agent-harness-core.prompt.md`, new)

1. Define **project evidence grounding** table and precedence (evidence over memory; stricter project rules win; record missing docs).
2. Define **briefing packet** required fields: `wave_id`, `phase`, `change_ids`, `trust_boundaries_touched`, `files_in_scope`, `architecture_refs`, `prior_artifacts`, `explicit_non_goals`, optional `recommended_model_tier`.
3. Define **finding record** schema (`finding_id`, file, lines, class, summary, reachability, confidence, severity, recommended_fix, components).
4. Define **reachability labels**: `reachable-from-caller-input`, `reachable-from-untrusted-content`, `not-externally-reachable` (document legacy alias mapping).
5. Define harness behaviors: narrow scope, no self-approval, split questions, parallel merge + dedupe, gapfill pointer.
6. Add seed to `MANIFEST`.

### R-Security — (owned by change `12rbe`)

Security seed generalization is specified in **`12rbe-enh security-reviewer-exploit-chains`**. This change must reference `209` and remain consistent with 213 after `12rbe` lands.

### R-Inferential — Other sensors

12. **`212-performance-reviewer`**: generic Context; Step 0 hot-path scope; reference `209`.
13. **`214-architecture-reviewer`**: generic Context; Step 0 scope; reference `209` (retain architecture read-first list).
14. **`221-code-reviewer.prompt.md`** (new): skeptical stance; no self-approval; AC/branch/re-entrant/multi-site; reference `209`; add to `MANIFEST`.

### R-Specialists — Harness specialists (new seeds)

15. **`217-senior-engineering-challenger`**: modes `plan-challenge` / `delivery-challenge`; pushback not praise; project evidence; output schema.
16. **`218-environment-auditor`**: read-only checks (entry surface, manifest/index, workflow-config, handoff, review evidence, hooks when seeded); attach summary to briefing packet.
17. **`219-operating-surface-gardener`**: `AGENTS.md` ≤ ~120 lines when layered model enabled; overflow to `docs/references/agent-operating-system.md`; manifest/index sync proposals.
18. **`216-reality-checker`**: modes `assumption-audit`, `finding-validation` (disprove-only, no new findings), `implementation-challenge` (lightweight); reference `209`.

### R-Review-system — `007-review-system-overview.md`

19. Subsection **Agent harness core** pointing to `209`.
20. Register `code-review` lane → `221`; harness specialist table (`217`–`219`, `216` modes).
21. Update security reachability labels to generic names; neutral exploit-chain example.
22. **Question ownership** table (defect → code-review, reachability → security-review, etc.).

### R-Bootstrap — Generation and coordination seeds

23. **`050`**: Harness specialist render rules (seed body + optional `## Project harness extensions` from repo evidence only); layered `AGENTS.md` guidance; align `code-reviewer.md` with `221`.
24. **`100`**: `prepare-wave` and `review-wave` require briefing packet; optional `environment-auditor`, `senior-engineering-challenger`, `reality-checker` finding-validation when policy enables.
25. **`020`**: **No self-approval** rule for implementers.
26. **`180`**: Briefing packet per lane; optional environment audit; parallel narrow tasks; merged `Observe:` dedupe; Gapfill in Progress Log.
27. **`215`**: Identical council packet; dedupe on synthesis.

### R-Wavefoundry-surface (follow-up within same change, docs only)

28. After seeds land, update **this repository’s** `docs/agents/security-reviewer.md` with Wavefoundry-specific checks removed from old seed-213 (path confinement, symbol two-hop, readonly tools, indexer secrets)—sourced from threat-model and code, not from memory.
29. Create or refresh `docs/agents/specialists/{senior-engineering-challenger,environment-auditor,operating-surface-gardener}.md` from seeds `217`–`219` with **Project harness extensions** when evidence exists.
30. Optional: begin `docs/references/agent-operating-system.md` and trim `AGENTS.md` per `050` (separate commit in implementation if large).

## Scope

**Problem statement:** Framework agent prompts do not enforce harness-shaped review and coordination; product-specific text in seeds blocks portability; operators cannot audit what each lane was asked to do.

**In scope:**

- New seeds: `209`, `217`, `218`, `219`, `221`
- Edits: `007`, `012`–`016` as listed above (`212`–`216`, `050`, `100`, `020`, `180`, `215`)
- `MANIFEST` updates
- Wavefoundry project agent doc updates (R-Wavefoundry-surface) after seed review
- Framework tests if any seed-referenced behavior is asserted in tests (unlikely; docs-lint on `docs/` edits)

**Out of scope:**

- MCP server / indexer code changes
- Automated job runner executing 50 parallel agents
- Mandatory second LLM vendor for validate seat (prompt mandate only)
- Changes to `12rb9` hot reload (`12rbc` wave remains separate)

## Acceptance Criteria

- AC-1: `209-agent-harness-core.prompt.md` exists in `MANIFEST` with briefing packet, finding record, evidence table, and reachability labels.
- AC-2: `213-security-reviewer.prompt.md` is product-agnostic and implements Steps 0–5 per R-Security.
- AC-3: `221-code-reviewer.prompt.md` exists in `MANIFEST` with skeptical stance and branch/re-entrant requirements.
- AC-4: Seeds `217`, `218`, `219` exist in `MANIFEST` with generic bodies and project-evidence hooks.
- AC-5: `216-reality-checker.prompt.md` documents `finding-validation` disprove-only mode.
- AC-6: `007` documents harness core, `code-review` lane, generic reachability labels, question ownership, and specialist table.
- AC-7: `050` and `100` require briefing packets and specialist render/extension rules.
- AC-8: `020` forbids implementer self-approval; `180` and `215` include packet, dedupe, and gapfill guidance.
- AC-9: `212` and `214` include Step 0 scope and reference `209`.
- AC-10: Wavefoundry `docs/agents/security-reviewer.md` contains relocated product-specific checks; seed-213 contains none of them.
- AC-11: `python3 -B .wavefoundry/framework/scripts/run_tests.py` passes after implementation.
- AC-12: `docs-lint` passes on edited `docs/` files.

## Tasks

- [x] Admit change to wave `12rnv agent-prompt-harness` (if not already admitted)
- [x] **Prepare wave** — operator review of this doc; record AC priority; select review lanes
- [x] Open `seed_edit_allowed`; implement R-Core through R-Bootstrap; close gate
- [x] Update `MANIFEST`
- [x] Implement R-Wavefoundry-surface (project docs only)
- [x] Run framework tests and docs-lint
- [x] **Review wave** — architecture-reviewer (seed portability), docs-contract, security-review on seed-213 reachability text
- [x] Hand off for operator commit (no agent commit unless requested)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-core-209 | implementer | Prepare wave | gate required |
| seed-security-213 | implementer | 209 | |
| seed-inferential-212-214-221 | implementer | 209 | parallel after 209 draft |
| seed-specialists-216-219 | implementer | 209 | parallel |
| seed-bootstrap-007-050-100-020-180-215 | implementer | 209 | |
| manifest | implementer | all seeds | |
| wf-agent-surfaces | implementer | seeds reviewed | docs/agents only |
| verify | qa-reviewer | all | tests + docs-lint |

## Serialization Points

- `209` must be drafted before other seeds reference it.
- `seed_edit_allowed` gate: single open/close around all seed edits.
- Project `docs/agents/` edits only after seed content is review-approved.

## Affected Architecture Docs

N/A — framework prompts and project agent operating docs only. No product runtime architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | -------- | --------- |
| AC-1 | required | Harness contract anchor |
| AC-2 | required | Security portability + Glasswing trace/chains |
| AC-3 | required | Skeptical code review seed |
| AC-4 | required | Challenger + environment + gardener |
| AC-5 | required | Disprove-only validate |
| AC-6 | required | Review system parity |
| AC-7 | required | Prompt surface generation |
| AC-8 | required | Coordinator behavior |
| AC-9 | important | Perf/arch scope |
| AC-10 | required | WF self-host correctness |
| AC-11 | required | Regression gate |
| AC-12 | required | Docs gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Change doc created; plan stub at `docs/plans/12rnv-*`. | planning discussion |
| 2026-05-19 | Paired with `12rbe` on wave `12rnv`; not superseded. | operator clarification |
| 2026-05-19 | Premature seed edits reverted; implementation deferred until Prepare wave. | `git checkout` on `.wavefoundry/framework/seeds/` |
| 2026-05-20 | Implemented: seeds 209, 217, 218, 219, 221 created; 007/020/050/100/180/212/214/215/216 edited; specialists docs created; MANIFEST updated. 1482/1482 tests green, docs-lint clean. | implementer |

## Decision Log

| Date | Decision | Reason |
| ---- | -------- | ------ |
| 2026-05-19 | Two changes on one wave (`12rbe` + `12rnv`) | Security slice separable from full harness; both will be implemented |
| 2026-05-19 | Seeds generic; extensions in rendered `docs/agents/` | Portable framework + evidence-backed targets |
| 2026-05-19 | New wave `12rnv` separate from `12rbc` hot reload | Different risk surface and reviewers |
| 2026-05-19 | `209` as shared harness seed | DRY across 212–221 and 216–219 |
| 2026-05-19 | Generic reachability labels | Applies to HTTP, CLI, MCP, jobs—not tool-arg only |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Large seed diff hard to review | Review wave per seed file; council optional |
| WF security checks missing until AC-10 | AC-10 required; block closure without relocation |
| Briefing packet not used in practice | `100`/`180` mandatory wording; coordinator Progress Log |

## Session Handoff

Implemented. Next operator step: review the completed seed work, then continue with wave review and closure when ready.

Coordinate with `12rbe` in the same wave.
