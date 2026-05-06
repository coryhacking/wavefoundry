# Harness Coherence Check

Change ID: `12ed1-feat harness-coherence-check`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Böckeler names "keeping guides and sensors synchronized without contradiction" as an open problem. Wavefoundry has 150+ numbered seeds covering the full lifecycle — as the surface grows, seeds can contradict each other or a sensor can enforce a rule that a guide has told the agent to bypass. There is currently no mechanism to detect this. An incoherent harness is worse than a thin one: agents receive conflicting instructions and resolve them unpredictably.

## Requirements

1. A `wave_harness_coherence` MCP tool (or a section in `wave_audit`) must scan the seed surface for common contradiction patterns and report findings as advisories.
2. Initial contradiction patterns to detect: (a) two seeds with conflicting instructions on the same keyword/topic, (b) a seed instructing an agent to skip a step that a required review lane enforces, (c) seeds referencing removed or renamed tools/gates.
3. Pattern matching must be keyword/heuristic-based — no LLM inference — to keep this a fast computational check.
4. Findings must be advisory only; coherence issues must never block a wave.
5. The seed surface scanned must include all files under `.wavefoundry/framework/seeds/` and `docs/prompts/`.

## Scope

**Problem statement:** As the seed surface grows, guides and sensors can contradict each other; there is no detection mechanism for harness-level incoherence.

**In scope:**

- Keyword-based contradiction scanner for the seed surface
- Detection of references to removed/renamed MCP tools (cross-referenced against the live tool list)
- Advisory diagnostics in `wave_audit` or a dedicated `wave_harness_coherence` tool
- Initial pattern library for three contradiction types (conflicting instructions, bypass of enforced lanes, stale tool references)

**Out of scope:**

- LLM-based semantic coherence analysis — computational only for v1
- Automatic repair of incoherent seeds
- Cross-project seed coherence

## Acceptance Criteria

- AC-1: The tool scans all seeds and prompts and reports any detected contradiction patterns.
- AC-2: Stale MCP tool references (tools named in seeds but absent from the server) are detected and reported.
- AC-3: All findings are advisory — `wave_audit` status is not affected by coherence issues.
- AC-4: Clean codebases (no detected issues) produce an empty findings list without noise.
- AC-5: New pattern types can be added without modifying the core scanner — pattern library is data-driven.

## Tasks

- [ ] Design pattern library schema (pattern ID, keyword set, contradiction type, message template)
- [ ] Implement keyword-based scanner over seed surface
- [ ] Implement stale tool reference check (compare seed tool mentions vs. live MCP tool list)
- [ ] Integrate findings into `wave_audit_response` or expose as `wave_harness_coherence`
- [ ] Seed initial pattern library (conflicting skip/enforce, bypass patterns, common stale tool names)
- [ ] Add tests: clean surface, stale tool reference, conflicting instruction pattern

## Agent Execution Graph

| Workstream      | Owner       | Depends On   | Notes |
| --------------- | ----------- | ------------ | ----- |
| scanner core    | implementer | —            |       |
| pattern library | implementer | scanner core |       |
| audit integration| implementer | scanner core |       |
| tests           | implementer | all above    |       |

## Serialization Points

- Pattern library schema must be finalized before scanner implementation

## Affected Architecture Docs

N/A — new scanning tool; no boundary impact.

## AC Priority

| AC   | Priority        | Rationale |
| ---- | --------------- | --------- |
| AC-1 | required        | Scanning is the core deliverable |
| AC-2 | required        | Stale tool references are the most common coherence failure today |
| AC-3 | required        | Advisory-only is non-negotiable — coherence issues must not block work |
| AC-4 | important       | False positives on clean codebases would cause operators to ignore the tool |
| AC-5 | important       | Extensible pattern library is what makes this useful long-term |

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
| Keyword matching produces false positives on legitimate uses of conflicting terms | Tune patterns conservatively; favour precision over recall in v1 |
| Seed surface grows faster than pattern library | Pattern library is extensible; ship with the highest-value patterns only |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
