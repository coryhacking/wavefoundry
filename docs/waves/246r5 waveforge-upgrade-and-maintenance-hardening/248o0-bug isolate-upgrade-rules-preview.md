# Isolate the upgrade rules preview

Change ID: `248o0-bug isolate-upgrade-rules-preview`
Change Status: `implemented`
Owner: Engineering
Status: review
Last verified: 2026-11-24
Wave: 246r5 waveforge-upgrade-and-maintenance-hardening

## Rationale

An operator previews a selected pack before approving an upgrade. The child currently inherits the parent environment and runs Python without isolated startup.

## Product Intent

Preview compatibility under the incoming rules without exposing unrelated environment variables to the child. AC-1 and AC-2 cover isolation and usability.

## Requirements

1. Launch the installed inspector through the existing bounded runner with -I and -B. Build a minimal environment from explicitly named, necessary platform and locale variables. Preserve the explicit staged import path, timeout, result validation and incomplete outcome on failure.

## Scope

Keep pack trust as a prerequisite. This limits inherited state and does not sandbox incoming code or authenticate a pack.

## Acceptance Criteria

- [x] AC-1: A real child receives a harmless allowlist control but cannot see an unrelated parent sentinel. Its interpreter reports isolated mode and suppressed bytecode.
- [x] AC-2: Exercise the real inspector with a harmless staged fixture, retaining explicit trusted-pack semantics. Exercise a representative staged preview with a conflicting parent Python import path. Compatible and unsupported rules retain their correct outcomes; worker failure remains incomplete. Check native Windows prerequisites and identify any platform simulated in verification.

## Tasks

- [x] Launch the installed inspector through the existing bounded runner with -I and -B. Build a minimal environment from explicitly named, necessary platform and locale variables. Preserve the explicit staged import path, timeout, result validation and incomplete outcome on failure.
- [x] Exercise AC-1 and AC-2 and record evidence in the Progress Log.

## Agent Execution Graph

The implementer delivers the change and its checks. The reviewers verify the evidence independently.

## Serialization Points

- `.wavefoundry/framework/scripts/scanner_upgrade.py`
- `.wavefoundry/framework/scripts/tests/test_scanner_upgrade.py`

## Affected Architecture Docs

No architecture boundary changes. Keep the existing contract documentation consistent with this change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Verifies the primary outcome. |
| AC-2 | required | Verifies the compatibility boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from Waveforge’s v1.51.0 feedback. | Item A1. |
| 2026-11-24 | Readback: Launch the installed inspector with isolated startup, bytecode disabled and an explicit environment. A parent sentinel currently reaches the preview. After this change a staged fixture must see its locale control and neither the sentinel nor a conflicting Python path. Trusted packs still supply executable scanner code. | AC-1 and AC-2 cover `scanner_upgrade.py` and `test_scanner_upgrade.py`, including compatibility and incomplete outcomes. |
| 2026-11-24 | The real inspector on macOS passed the staged fixture's checks for isolated mode, suppressed bytecode, the locale control and the absence of the unrelated sentinel and parent Python path. A representative pack classified compatible and unsupported project rules correctly with a conflicting parent JSON module. An incoming worker that exited early produced an incomplete preview. | All 14 tests in `test_scanner_upgrade.py` passed. The Windows environment check simulated selection of SystemRoot and locale. Native Windows execution remains unverified. |

| 2026-11-24 | Delivery handoff | Implementation and focused verification are ready for independent delivery review. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Use the existing framework path. | Planner default within the operator-selected scope. | Filtering only Python variables would leave unrelated credentials inherited. |

## Risks

Keep pack trust as a prerequisite. This limits inherited state and does not sandbox incoming code or authenticate a pack.

## Session Handoff

Prepare the admitted spec before implementation.
