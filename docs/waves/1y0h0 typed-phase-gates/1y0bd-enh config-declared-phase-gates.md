# Config-Declared Phase Gates

Change ID: `1y0bd-enh config-declared-phase-gates`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-14
Wave: `1y0h0 typed-phase-gates`

## Rationale

**Brief.** Goal: let a target repository require additional named sensors and review lanes at prepare, review, or close through committed, typed configuration, with the framework's own checks unchanged. Audience: Waveforge and any team with policy beyond the defaults, plus maintainers who want policy visible in one reviewed file. Approach: a new `phase_gates` key in `docs/workflow-config.json` consumed by gate units appended to the phase tuples from `1y044-ref extract-lifecycle-gate-units`. Constraints: no repository code loaded by the server; enumerated fields only; fail-closed; provenance in every response. Success: a fixture repository declares a close-time sensor and an extra review lane, and the phases block or pass exactly as declared.

This is the posture selected by the operator on 2026-09-14 over the RFC's convention-discovered policy modules. Verification found three config-driven policy mechanisms already shipped: `sensors` (project shell commands run by `wf_run_sensors`, read by `_read_project_sensors` at `server_impl.py:3454`), `required_review_lanes` (read at line 3252 and fed to `select_required_review_lanes`), and the `wave_review` council block. It also found that the `review_policies` key is hashed into the policy digest but never parsed, so that block is not a safe home for new fields. The established pattern is one dedicated top-level key with a small reader threaded into the lifecycle call site, and this change follows it.

## Requirements

1. A new optional top-level `phase_gates` object in `docs/workflow-config.json` with at most three keys, `prepare`, `review`, and `close`. Each is an object with two optional list fields: `required_sensors` (names from the existing `sensors` list) and `required_lanes` (lane names from `REVIEW_LANE_ORDER`). Any other key at any level, an unknown sensor name, or an unknown lane name is a docs-lint error naming the path in the config.
2. A `RequiredSensorsGate` unit, appended to the configured phase's tuple, runs each named sensor through the existing sensor execution path used by `wf_run_sensors`, including its timeout handling. That path is named precisely before implementation starts (its owning function, its return type, and what field constitutes "passing" — an exit-code check, at minimum), rather than left as "the existing path" in prose. If that function lives in `server_impl.py` today, it is extracted into a small shared module (analogous to `runtime_lock.py`/`gardener_metadata.py`) that both `server_impl.py` and `lifecycle_gates.py` import, so `lifecycle_gates.py` does not gain a top-level dependency on `server_impl.py` — consistent with the no-import-of-`server_impl` rule `1y0bf-ref codenav-graph-handler-modules` already applies to its own extracted modules. Any non-zero exit, timeout, or missing command produces a blocking `phase_sensor_failed` diagnostic carrying phase, sensor name, exit status, and the first lines of output. The gate never passes on error.
3. A `RequiredLanesGate` unit adds the configured lanes for `review` to the `project_lanes` input of `select_required_review_lanes`, additive to the existing `required_review_lanes` key, so `wf_prepare_wave` records them as required and `wf_review_wave` and `wf_close_wave` enforce them through the ledger as they do today.
4. `phase_gates` is included in `policy_input_digest`, so editing it after readiness lapses the collected approvals in the same way other policy edits do.
5. Dry-run modes run the configured sensors and report their outcomes, and the response marks them as gate checks so the operator can see what would block before writing anything.
6. Provenance: every prepare, review, and close response lists the configured gates that ran, their source key path, and their outcomes, so an operator can answer which project policy applied.
7. The default is unchanged: with no `phase_gates` key, the phase tuples end where `1y044` left them, and the existing lifecycle corpus passes unchanged.
8. Documentation: the workflow-config key reference documents `phase_gates` with its validation rules and an example, and the `wf_prepare_wave`, `wf_review_wave`, and `wf_close_wave` entries in `docs/specs/mcp-tool-surface.md` mention the configured-gate outcomes in the response.
9. The golden tool-surface fixture is unchanged: no tool gains or loses a parameter.

## Scope

**Problem statement:** A team that needs a policy beyond the defaults, such as a release checklist script that must pass before close, has no declarative way to attach it to a lifecycle phase.

**In scope:**

- The `phase_gates` key, validation, the two gate units, digest inclusion, provenance, and documentation.
- Fixture repositories exercising pass, fail, timeout, and unknown-name cases.

**Out of scope:**

- Loading Python policy modules from the repository by convention or by config (rejected posture; see Decision Log).
- New sensor kinds or changes to how `sensors` entries are shaped.
- Requiring a specific signoff key other than the existing lanes.
- Seed and `AGENTS.md` prose describing the key in target repositories; recorded as a seed-gated follow-up in the wave watchpoints.

## Acceptance Criteria

- [ ] AC-1: With no `phase_gates` key, the prepare, review, and close corpus passes unchanged and no configured gate appears in any response.
- [ ] AC-2: In a fixture declaring `close.required_sensors: ["release-check"]`, a passing sensor lets the close dry-run report ready, a failing sensor blocks with `phase_sensor_failed` naming the sensor and exit status, and a sensor that exceeds the timeout blocks with the same code.
- [ ] AC-3: In a fixture declaring `review.required_lanes: ["security-reviewer"]`, prepare records that lane as required, and close blocks until an approval for it exists in `events.jsonl`.
- [ ] AC-4: An unknown sensor name, an unknown lane name, an unknown phase key, and an unknown field each produce a docs-lint error naming the config path, and prepare refuses to record readiness while the error stands.
- [ ] AC-5: Editing `phase_gates` after readiness changes the policy digest and prepare reports that re-preparation is required.
- [ ] AC-6: Every phase response in the fixtures lists the configured gates that ran with their outcomes and source key path.
- [ ] AC-7: The golden tool-surface fixture is unchanged.
- [ ] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Add `phase_gates` schema validation to the workflow-config validation path in docs-lint.
- [ ] Add `_read_phase_gates(root)` beside the existing config readers and populate `GateContext` with it.
- [ ] Implement `RequiredSensorsGate` on the existing sensor execution path with fail-closed handling.
- [ ] Implement `RequiredLanesGate` feeding `select_required_review_lanes`.
- [ ] Include `phase_gates` in `policy_input_digest`.
- [ ] Add provenance fields to the three phase responses.
- [ ] Build fixtures and tests for AC-2 through AC-6.
- [ ] Update the workflow-config reference and `docs/specs/mcp-tool-surface.md`.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| schema         | implementer | `1y044` module | validation and reader |
| gates          | implementer | schema       | two units, digest, provenance |
| fixtures       | qa          | gates        | pass, fail, timeout, unknown-name |
| docs           | implementer | schema       | key reference and tool spec |


## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` gains the policy-extension boundary: project policy enters through typed configuration, never through imported code. A decision record under `docs/architecture/decisions/` records the choice of config-declared gates over auto-discovered policy modules with the security reasoning. `docs/specs/mcp-tool-surface.md` is updated as required above.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Default unchanged |
| AC-2 | required  | The integrator outcome for sensors, including fail-closed |
| AC-3 | required  | The integrator outcome for lanes |
| AC-4 | required  | Typed schema is the safety property of the design |
| AC-5 | required  | Policy edits must not bypass readiness |
| AC-6 | important | Provenance makes the policy auditable |
| AC-7 | required  | No public schema change |
| AC-8 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0h0 typed-phase-gates` | this document |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Config-declared typed gates; no imported policy code | Operator selection on 2026-09-14. Auto-importing repository Python at MCP startup would run untrusted code in every host that starts the server on project open; the RFC's precedent is wrong because upgrade hooks load from the pack, not the repository. Config is committed, reviewed, and already the project's extension idiom | (a) Convention-discovered `extensions/*_policy.py`: zero config, executes repository code. (b) Config-named module path with containment and fail-closed: safer than (a), still executes repository code; revisit only if a real policy cannot be expressed as a sensor |
| 2026-09-14 | Dedicated `phase_gates` key rather than fields inside `review_policies` | `review_policies` is digested but never parsed; giving it semantics now would change the meaning of existing configs | Extend `review_policies`: fewer top-level keys, ambiguous compatibility |
| 2026-09-14 | Sensors run in dry-run too | A dry-run that skips sensors would report ready for a close that then blocks | Skip in dry-run: faster, misleading |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A required sensor is a long-running command and slows every prepare | The existing sensor timeout applies; the key reference recommends fast checks and the response reports duration |
| Sensors already execute repository-declared shell commands under the server's privileges | Unchanged trust boundary from `wf_run_sensors`; the commands are visible in committed config, and this change adds no new discovery or implicit execution |
| Teams declare lanes no persona exists for | Lane names are validated against `REVIEW_LANE_ORDER` at lint time |
| "The existing sensor execution path" was an unnamed proposition, not falsifiable as written | Archetype Council (Spock, 2026-09-17): named the owning function, its shared-module home, and the passing signal directly in Requirement 2 rather than leaving them to be discovered at implementation time |
| This change's `phase_gates` validation and `1y042`'s sibling `record_layout` validation both extend docs-lint's workflow-config schema check; no test proves the two compose in one lint pass | Archetype Council (Sun Tzu, 2026-09-17), recommended not required: whichever of `1y042`/`1y0bd` lands second adds one fixture with both keys misconfigured and asserts docs-lint reports both errors independently in the same run |
| Waveforge's real fork has a git-branch-integrated, PR-gated review workflow (`review_policy.mode: pr_review`, `branch_at: wave`, `allow_self_attestation`) that `required_sensors`/`required_lanes` do not express | Confirmed 2026-09-17 (`docs/reports/waveforge-fork-audit.md`); explicitly out of scope for this change, not silently missed. Branch emission and PR-gating are a separate policy axis worth its own change if the operator wants Wavefoundry to generalize what Waveforge already built rather than leave it as their own fork-only code |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
