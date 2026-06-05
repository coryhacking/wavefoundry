# Red-team routes to Failure Path And Boundary Correctness patterns

Change ID: `1p3j5-enh red-team-cross-weave`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

`seed-221` (code-reviewer) gained 6 Failure Path And Boundary Correctness patterns in change `1p3ix`. The red-team's native frame — "what input would break this?" — is adversarial-probe-ready for those patterns: each pattern names a class of edge-case failure that an adversarial reviewer would routinely probe (exhaust a resource via unbounded input, swallow an unexpected exception, leave a lock held on the error path, etc.).

Cross-weaving (cross-reference, not duplication) so red-team reviewers in `abuse-path-review`, `failure-pressure-test`, and `council-adversarial-primer` modes can anchor their probes to the canonical patterns in `seed-221`. Patterns stay single-sourced; `seed-225` carries pattern names + adversarial-probe framings so the reviewer routes there when boundary-edge probes are the dominant stance.

## Requirements

1. `seed-225` gains a new section `## Failure Path And Boundary Correctness Patterns (Cross-Reference)` between `## Modes` (after `council-adversarial-primer`) and `### council-seat`.
2. The section lists all 6 patterns by name with their applies-when scopes, includes a one-line adversarial-probe framing per pattern (e.g., "what unbounded input would exhaust a resource?"), references `seed-221` for full definitions, and explains the cross-stance routing.
3. Pattern text is NOT duplicated — names, applies-when scopes, adversarial-probe framings, and a pointer to `seed-221`.
4. Other sections of `seed-225` are unchanged.

## Scope

**Problem statement:** Red-team reviewers in adversarial modes have no routing into the Failure Path And Boundary Correctness patterns in `seed-221`. Without the cross-reference, the patterns are discoverable only by reviewers who already know `seed-221`'s structure.

**In scope:**

- One new section in `seed-225`.
- CHANGELOG bullet under `[1.5.0]` `### Changed`.

**Out of scope:**

- Duplicating pattern definitions into `seed-225`.
- Restructuring `seed-225`'s other sections (Modes, Role Boundaries, Output Shape, etc.).

## Acceptance Criteria

- [x] AC-1: `seed-225` contains `## Failure Path And Boundary Correctness Patterns (Cross-Reference)` between `## Modes` and `### council-seat`.
- [x] AC-2: All 6 pattern names appear with applies-when scopes and an adversarial-probe framing per pattern.
- [x] AC-3: Section references `seed-221` as the canonical source; does not duplicate pattern descriptions.
- [x] AC-4: `docs-lint` returns clean.

## Tasks

- [x] Edit `seed-225`: add cross-reference section after `## Modes`.
- [x] Run docs-lint.
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Changed`.

## Affected Architecture Docs

N/A — single-seed cross-reference addition.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | The new section IS the change. |
| AC-2 | required     | All 6 patterns must be routable from the red-team adversarial stance. |
| AC-3 | required     | "Cross-reference, not duplicate" is the load-bearing design choice. |
| AC-4 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                                       | Evidence |
| ---------- | ------------------------------------------------------------ | -------- |
| 2026-06-05 | Change admitted into wave 1p3iv; implementation done in-session. | Edit to `seed-225` between Modes and council-seat; docs-lint clean. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Section placed between `## Modes` and `### council-seat` (the last mode), not as a sub-section of any single mode. | Patterns apply across multiple modes (abuse-path-review, failure-pressure-test, council-adversarial-primer, council-seat). Standalone section at the same level as Modes keeps it discoverable from every mode without forcing per-mode duplication. | (a) Inline pattern references into each relevant mode — rejected; multiplies maintenance and dilutes scanability. (b) Place at end of seed, after Do Not — rejected; adversarial probes are mid-review concerns, not closing concerns. |
| 2026-06-05 | Cross-reference includes a one-line adversarial-probe framing per pattern, not just the applies-when hint from `seed-221`. | Code-reviewer needs the question "does this hold under all inputs?"; red-team needs the question "what input forces it to break?". Same patterns, different verbalizations. The adversarial framing gives the red-team reviewer a probe-ready phrasing without reading `seed-221`. | (a) Use only the applies-when hints — rejected; reviewer would need to mentally translate to adversarial frame. (b) Duplicate full pattern text — rejected; that's what "cross-reference, not duplicate" disallows. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
