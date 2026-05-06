# Post-Edit Computational Sensors

Change ID: `12ecs-feat post-edit-computational-sensors`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-06
Wave: `12ecs agent-feedback-harness`

## Rationale

Wavefoundry's harness is feedforward-heavy: seeds, gates, and the wave lifecycle guide agents before they act, but there is no feedback layer that runs after an edit and reports results back to the agent. Böckeler's harness engineering model identifies post-edit computational sensors (linters, type-checkers, test runners) as the highest-leverage feedback mechanism — cheap to run, deterministic, and directly actionable. Without them, agents must self-report quality and operators must manually verify.

## Requirements

1. Wavefoundry must provide a mechanism for projects to register a set of post-edit sensor commands (e.g. `eslint`, `mypy`, `pytest`, `cargo check`) in a project config file.
2. After an agent-edit session, the implement-feature workflow must instruct agents to invoke the registered sensors and report results before declaring done.
3. Sensor output (pass/fail, error summary) must be surfaced in a structured way the agent can act on — not just printed to stdout.
4. Sensor registration must be optional and zero-config by default — projects with no sensors registered skip the step without error.
5. Sensors must be documented in the seed prompt surface so agents know the pattern exists and how to invoke it.

## Scope

**Problem statement:** Agents declare implementation complete with no automated verification of the output — quality is asserted, not measured.

**In scope:**

- A `sensors` config section in `workflow-config.json` (or equivalent project config) for registering named sensor commands
- A `wave_run_sensors` MCP tool (or equivalent seed guidance for shell invocation) that runs registered sensors and returns structured pass/fail results
- Updates to `180-implement-feature.prompt.md` and `190-finalize-feature.prompt.md` to invoke sensors as part of the done-check loop
- Seed documentation explaining the feedforward/feedback harness model and how sensors fit

**Out of scope:**

- Running sensors automatically as a background hook (no daemon/watcher)
- Inferential (LLM-run) sensors — covered by a separate change
- Sensors for non-code content (docs, prompts)
- CI/CD integration — sensors are local only

## Acceptance Criteria

- AC-1: A project can register sensor commands in config and they are discovered by the framework.
- AC-2: `180-implement-feature.prompt.md` instructs the agent to run sensors after editing and report results.
- AC-3: A failed sensor blocks "done" — the agent must address the failure or explicitly defer with rationale.
- AC-4: Projects with no sensors registered complete the workflow without error or noise.
- AC-5: Seed documentation explains computational vs. inferential sensors and when to use each.

## Tasks

- [ ] Design `sensors` config schema in `workflow-config.json`
- [ ] Implement sensor discovery and invocation (shell-based, structured output)
- [ ] Add `wave_run_sensors` MCP tool or seed-based invocation pattern
- [ ] Update `180-implement-feature.prompt.md` to include sensor step
- [ ] Update `190-finalize-feature.prompt.md` to require sensor pass before done
- [ ] Add seed doc explaining the harness model (feedforward vs. feedback, computational vs. inferential)
- [ ] Add tests for sensor config discovery and invocation

## Agent Execution Graph

| Workstream       | Owner       | Depends On    | Notes |
| ---------------- | ----------- | ------------- | ----- |
| config + tooling | implementer | —             |       |
| seed updates     | implementer | config schema |       |
| tests            | implementer | tooling       |       |

## Serialization Points

- `workflow-config.json` schema must be finalized before seed updates reference it

## Affected Architecture Docs

N/A — confined to workflow config and seed surface; no boundary or data-flow impact beyond the existing MCP tool surface.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority         | Rationale |
| ---- | ---------------- | --------- |
| AC-1 | required         | Core deliverable — sensors must be discoverable to have any value |
| AC-2 | required         | Agents must know to invoke sensors; without seed guidance the feature is invisible |
| AC-3 | required         | A failed sensor that doesn't block "done" is noise, not a harness |
| AC-4 | required         | Zero-config default is essential for adoption; no sensors registered must be silent |
| AC-5 | important        | Conceptual foundation for the broader harness model; improves long-term adoption |

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
| Sensor commands vary widely by stack — hard to standardize output | Return raw exit code + stderr summary; agent interprets |
| Agents may skip sensor step if optional | Make step explicit in seed with "if sensors registered" conditional |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
