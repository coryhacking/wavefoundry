# Bound retained child logs and clean returned upgrade output

Change ID: `20gfh-bug bounded-upgrade-child-diagnostics`
Change Status: `implemented`
Owner: Engineering
Status: implementing
Last verified: 2026-10-11
Wave: 20gx0 bounded-upgrade-diagnostics

## Rationale

Child diagnostic streaming already contains file writes, scrubs output, bounds individual fragments and retains five run groups, but one noisy child can grow its log without limit. The MCP upgrade response bounds display length yet returns control characters in its main output field. Bound persistent diagnostics and apply the existing cleaning contract to returned display text while preserving child execution, useful failure context and structured protocol interpretation.

## Requirements

1. Cap each generated child log at 1 MiB of UTF-8 bytes, including any truncation marker. Preserve the initial output and a bounded final tail when output exceeds the cap; reserve up to 64 KiB for that tail. Small outputs retain their existing content.
2. Continue draining both child pipes and maintaining the existing bounded diagnostic tails after the log budget is exhausted. Truncation is diagnostic degradation, not child failure. Keep timeout/exit behavior and contained 0600 publication unchanged.
3. On normal completion, failure and timeout cleanup, finalize bounded retained output where the owned handle is still usable. A log I/O failure retains the existing diagnostic-error behavior and must not deadlock the child.
4. Clean the returned upgrade `data.output` using the existing `child_tee.clean_output` contract before its display cap, including known publisher-token redaction. Preserve raw structured-summary parsing and existing success/failure/recovery decisions; cleaning presentation must not reinterpret child exit status.
5. Disclose elision truthfully and retain existing five-run retention. This change adds no configuration knob, evidence file, scan, model download or upgrade phase.

## Scope

In scope: child log byte accounting/head-tail finalization, returned upgrade output cleaning, relevant focused tests and current diagnostic documentation.

Out of scope: a general process supervisor, changing the structured upgrade sentinel/schema, redesigning full captured stdout used by parser consumers, capping the separate primary upgrade log, or new historical cleanup. Existing capture_output parser contracts remain explicit boundaries; this change does not claim all subprocess memory is bounded.

## Acceptance Criteria

- [x] AC-1: Large real-child stdout/stderr, including multibyte text, produce a log no larger than the byte cap with explicit elision, retained opening context and final diagnostic tail. Small output is unchanged. Oracle: filesystem bytes and child results.
- [x] AC-2: Crossing the log cap does not deadlock either pipe or alter child exit/timeout behavior; bounded finalization also runs on failure/timeout where possible. Oracle: real bounded child fixtures and existing failure controls.
- [x] AC-3: Public upgrade responses remove terminal/control sequences and redact the known token before output bounding on success and error; structured summary, status and recovery semantics remain intact. Oracle: registered-handler controls with realistic subprocess output.
- [x] AC-4: Contained file ownership, permissions, run retention and log-error reporting continue to work. Oracle: existing containment/retention controls plus targeted cap-removal and cleaning-removal mutants.
- [x] AC-5: Edited spec/architecture documentation accurately states the per-child cap, tail/elision behavior and remaining capture/primary-log limits; edited docs validate.

## Tasks

- [x] Implement byte-bounded child-log retention with final tail and explicit elision; preserve live drain and owned cleanup.
- [x] Clean display output at the upgrade response boundary without changing raw protocol interpretation.
- [x] Add and run focused child-stream and registered-handler regression controls and relevant known-bad mutations.
- [x] Update diagnostic contracts and change-local documentation.
- [x] Complete required delivery reviews and canonical qualification, recording compact results in existing records.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Diagnostics implementation | Implementer | Readiness | Own child tee and output projection. |
| Verification | Required reviewers | Implementation | Independent read-only review of byte bounds and compatibility. |

## Serialization Points

- `.wavefoundry/framework/scripts/child_tee.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_child_tee.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_failure_surfacing.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/testing-architecture.md`

The coordinator integrates source changes and documentation; reviewers inspect. Preserve structured-summary semantics, publication/containment guards and operator-owned lifecycle actions. No prompt/seed/hook writes are planned.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` and `docs/architecture/testing-architecture.md`: bounded child logging and returned upgrade display; keep the public field contract in `docs/specs/mcp-tool-surface.md`.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Bounds persistent diagnostics without losing useful context. |
| AC-2 | required | Logging must not disrupt the child operation. |
| AC-3 | required | Returned display follows the same cleaning boundary as logs. |
| AC-4 | required | Preserves current containment and cleanup guarantees. |
| AC-5 | required | Makes operator expectations accurate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-11 | Current tee and upgrade handler inspected; plan authored before implementation. | child_tee.run and upgrade handler output projection. |
| 2026-10-11 | Readback: reserve marker and final 64 KiB tail within each 1 MiB UTF-8 child-log budget on the existing owned append handle; keep small bytes exact and both pipes draining; finalize before reporting log errors. Clean returned display with the known publisher token after raw summary/status interpretation and before the display cap. Before: a noisy child grows beyond 1 MiB and returned display keeps controls. After: retained head/elision/tail fits the byte cap and display is scrubbed. Raw capture and primary upgrade.log are outside scope. | AC-1–AC-5; child_tee.py, upgrade_handlers.py, owning tests and three listed contract docs. |

| 2026-10-11 | Observe: implementation and listed contracts updated; same owned append handle reserves head/suffix space without seek, reopen or truncate. Platform newlines are translated before UTF-8 accounting, preserving small bytes. Raw summary/status/recovery parsing remains separate from display cleaning. | `_BoundedLog.write/finalize`, `child_tee.run`, `wf_upgrade_response`; three listed contract docs. |
| 2026-10-11 | Observe: canonical focused run passed 429 tests across three files, zero skips, 123.248 seconds; no full-suite receipt claimed. | `python3 .wavefoundry/framework/scripts/run_tests.py --file test_child_tee.py --file test_upgrade_failure_surfacing.py --file test_server_tools.py`; counts 20/18/391. |
| 2026-10-11 | Landing controls: disposable source copies loosened the file cap to 8 MiB and the tail budget to 128 KiB; both failed independent literal filesystem limits. Removing display cleaning failed the registered before-cap assertion; removing pre-snapshot finalization failed reported OSError visibility. All four failed assertions with no import errors or skips. | `test_utf8_log_cap_edges_keep_exact_small_bytes_head_and_final_tail` (1048577 > 1048576; 131072 > 65536), `test_registered_upgrade_cleans_display_before_cap_without_reinterpreting_summary`, `test_final_log_io_error_is_reported_and_both_pipes_still_drain`. |
| 2026-10-11 | Handoff: AC-1–AC-4 and four implementation tasks are complete. AC-5 awaits full docs validation; required delivery reviews and final combined canonical qualification remain pending with the coordinator. Native Windows byte accounting is simulated, not native qualification; full parser capture and primary upgrade.log remain outside the cap. | Existing final review/qualification task remains unchecked; no lifecycle closure, commit or package action. |

| 2026-10-12 | Final implementation and required independent delivery review completed; all admitted ACs are supported. Paused for operator closure. See `wave.md` Review Checkpoints for consolidated findings, limits, source identity and reviewer roster. | Canonical final qualification: 12,402 tests / 185 files / 12 unchanged existing skips, 798.065 seconds, exit 0; matching receipt `d1ab96d12d77d992c99b700656f18ac2044068c89188efa82e531f416816d5ce`. Exact report worker/skip comparison and all reviewed source fingerprints verified. Full documentation validation passed with zero errors and warnings. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-11 | Use one fixed per-child byte cap with retained head/final tail and explicit elision. | Bounded storage and useful diagnostics without another knob or artifact. | Prefix-only logs lose late failures; rotating chunks add files and lifecycle complexity. |
| 2026-10-11 | Clean presentation after raw protocol interpretation, before display bounding. | Preserves machine protocol compatibility while cleaning text agents/operators receive. | Cleaning or truncating raw output before parsing can change structured-summary meaning. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Character counts understate UTF-8 storage. | Enforce encoded-byte limits including marker/tail. |
| Stopping reads when a log fills blocks a child. | Cap only retained writes; continue both drain loops and bounded tails. |
| Logging obscures an actual failure. | Retain final tail and preserve exit status and timeout semantics. |
| Broader output-memory guarantee is inferred. | Explicitly leave parser capture and primary upgrade log outside this change. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
