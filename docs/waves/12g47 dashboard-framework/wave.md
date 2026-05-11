# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-10

wave-id: `12g47 dashboard-framework`
Title: Dashboard Framework

## Objective

Define the generic architecture for a Wave Framework dashboard feature that can be seeded into all projects: a basic React UI, a Python loopback server, shared state-reader logic with the existing framework tooling, per-repository runtime port allocation that supports concurrent local dashboards, and a basic reusable dashboard design system.

## Coordinator

- `wave-coordinator`

## Changes

Change ID: `12g47-enh generic-project-dashboard`
Change Status: `complete`

Change ID: `12gtx-enh dashboard-auto-index`
Change Status: `complete`

Change ID: `12hjp-enh dashboard-ui-polish`
Previous Change Status: `planned`
Change Status: `complete`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | planning | `12g47-enh generic-project-dashboard` — generic dashboard architecture, transport split, adapter model |
| council-moderator | council synthesis | `12g47-enh generic-project-dashboard` — Wave Council readiness/delivery synthesis for the dashboard feature |
| architecture-reviewer | review | `12g47-enh generic-project-dashboard` — runtime topology, boundaries, and shared-reader extraction |
| code-reviewer | review | `12g47-enh generic-project-dashboard` — implementation approach for server/frontend/shared modules |
| qa-reviewer | review | `12g47-enh generic-project-dashboard` — graceful degradation, read-only guarantees, and contract verification |
| security-reviewer | review | `12g47-enh generic-project-dashboard` — loopback binding, read-only posture, file/path handling, and local trust-boundary constraints |
| docs-contract-reviewer | review | `12g47-enh generic-project-dashboard` — seed/install/upgrade and operator-facing dashboard contract |
| release-reviewer | review | `12g47-enh generic-project-dashboard` — packaging, seeding, and distribution behavior for the reusable dashboard feature |
| framework-operator | acceptance | `12g47-enh generic-project-dashboard` — seeded operator UX, startup contract, and install/upgrade expectations across target repos |

## Dependencies

- No external wave dependencies identified.
- Depends on deciding whether dashboard state comes from shared Python readers, dashboard-specific parsers, or a mixed adapter model before implementation starts.

## Current Assumptions

- The dashboard should be framework-generic, not Wavefoundry-specific.
- React is acceptable because the user explicitly requested a basic React implementation.
- Python should remain the server/runtime language because Wavefoundry already owns lifecycle parsing and MCP logic there.
- Browser runtime should not speak MCP directly; reuse the logic behind MCP instead.
- Config should express dashboard port preference, but the resolved runtime port should be stored as untracked `.wavefoundry` state so multiple repositories can run concurrently on one machine.

## Outputs Produced Or Expected

- A consolidated dashboard architecture proposal
- A generic dashboard framework change doc
- A planned wave container for later implementation
- Identified architecture docs and framework surfaces that would need updates

## Review Checkpoints

- Admission recorded 2026-05-08: `12g47-enh generic-project-dashboard` created as the architecture/planning change for a generic dashboard feature and admitted to `12g47 dashboard-framework`. Product-owner: N/A because this is framework tooling and generic project infrastructure, not a target-product behavior surface.
- Prepare wave — readiness verdict: **pass** on 2026-05-08. Admitted doc is already wave-owned at `docs/waves/12g47 dashboard-framework/12g47-enh generic-project-dashboard.md`; required planning sections are complete; AC priority is now fully recorded including `AC-3a`, `AC-5a`, and `AC-7a`; required lanes selected: `architecture-reviewer`, `code-reviewer`, `qa-reviewer`, `security-reviewer`, `docs-contract-reviewer`, and `release-reviewer`. `framework-operator` acceptance is required because this feature adds a seeded operator-facing dashboard/startup surface across target repositories; the operator requested that direction in this thread. Wave Council readiness is recorded with `council-moderator` synthesis and `docs-contract-reviewer` as the rotating fifth seat. Change Status advanced to `ready`; wave status advanced to `active`.

## Review Evidence

- wave-council-readiness: approved (moderator: council-moderator; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: docs-contract-reviewer — council aligned on React UI + Python loopback server, browser-owned UI state, shared Python readers, host-local endpoint metadata under `.wavefoundry/`, and an operator-facing `Start dashboard` command that opens the browser by default while always printing the final URL)
- wave-council-delivery: approved (2026-05-10 — all ACs satisfied: React+Python loopback dashboard shipped, auto-index daemon implemented, design system documented, adapter model and install/upgrade docs written, 1087 tests passing, UI polish complete with gradient tile borders and dark mode fixes, docs-lint extended for dashboard-required fields)
- code-reviewer: approved (2026-05-10 — IndexBuilder async logic correct: debounce, single-build gate, re-arm, rebuild-before-notify ordering, subprocess isolation; dashboard_lib pure-disk-reader contract preserved; SnapshotStore injection layer correct)
- release-reviewer: approved (2026-05-10 — dashboard assets ship via build_pack.py MANIFEST; React UMD files bundled as local statics; install via seed-010, upgrade via seed-160; no npm dependency in target repos)
- framework-operator: acknowledged (2026-05-08 — operator requested the seeded dashboard feature and approved the startup UX direction for implementation planning)
- operator-signoff: approved

## Journal Refs

- `docs/agents/session-handoff.md`

## Journal Watchpoints

- **Frontend/server/MCP boundary** — resolved: React → Python loopback only; browser never speaks to MCP or git. Documented in `data-and-control-flow.md` Path 7 and `cross-cutting-concerns.md`.
- **Watchpoint:** The dashboard must handle projects with rich status sources and projects with minimal status sources without misleading progress signals; block fake or inferred progress numbers.
- **Watchpoint:** Avoid a second independent parser stack for wave/change/review state if existing Python logic can be extracted cleanly; duplicate parsers would create long-term drift risk.
- **Watchpoint:** Do not treat the dashboard port as a committed single-source config value; runtime allocation must handle same-host multi-repo use without collisions or merge churn.
- **Watchpoint:** The dashboard needs a small explicit design system. Do not let layout, status colors, card structure, and empty/error/loading states accrete as ad hoc component-local CSS.

## Completion Criteria

- `12g47-enh generic-project-dashboard` reaches `complete`
- The framework has a clear generic dashboard architecture and implementation plan
- The framework has a clear basic dashboard design-system contract aligned with `docs/design-system/`
- Runtime boundaries, packaging, and adapter model are documented
- The change is ready for `Prepare wave` once the operator wants implementation to begin

## Handoff Or Next-Wave Notes

- Next lifecycle step is `Implement wave`.
- Before implementation, confirm whether the first slice should be architecture docs + shared reader extraction, or a thin end-to-end vertical slice.

Completed At: 2026-05-10

## Wave Summary

*(Populated at closure.)*
