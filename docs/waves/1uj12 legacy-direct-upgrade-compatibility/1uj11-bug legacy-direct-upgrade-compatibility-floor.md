# Legacy direct-upgrade compatibility floor

Change ID: `1uj11-bug legacy-direct-upgrade-compatibility-floor`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-05
Wave: 1uj12 legacy-direct-upgrade-compatibility

## Rationale

The protocol-2 bridge is intentionally a two-hop safety mechanism: a protocol-1 runner must not extract a modern feature pack and continue its old project-writing pipeline. However, the bridge currently requires the installed framework version to equal `1.14.0` exactly. A field user on an older valid installation (approximately 1.8) therefore had to upgrade to 1.14 first before reaching 1.15.3.

That intermediate step is a narrow, untested-source policy encoded as a hard stop, not a user-facing product requirement. The bridge itself swaps only the framework tree after validating its root, hashes, host quiescence, and protocol state. Wavefoundry should support direct upgrades from a clear, tested legacy floor: `1.8.0` or later protocol-1 installations. The bridge and its fail-closed safeguards remain; only the arbitrary `1.14.0` staging requirement is removed.

## Requirements

1. Define `1.8.0` as the minimum supported legacy source for a direct upgrade to the current protocol-2 release. A supported protocol-1 source at or above that floor must not be required to install 1.14 first.
2. Replace the bridge's exact installed-version equality guard and its singular `supported_source_version` selection contract with a minimum-source-version contract. Preserve fail-closed rejection for missing/malformed versions, sources below the floor, protocol mismatches, unquiesced hosts, invalid hashes, and unsafe roots.
3. Ensure the public legacy upgrade handoff reaches the standalone bridge before an old runner extracts the feature pack, then performs the existing explicit protocol-2 second hop. The user-facing route remains `upgrade wavefoundry`; no manual framework copy or arbitrary intermediate release is prescribed.
4. Correct upgrade guidance and structured failures to state the `1.8.0` floor, distinguish an unsupported older source from an invalid package, and give the next safe action. Remove claims that suggest `1.14.0` is a required stepping stone.
5. Prove the compatibility boundary with real tagged source fixtures at 1.8.0 and 1.14.0, plus a below-floor rejection control. Preserve the existing bridge integrity and second-hop coverage.

## Scope

**Problem statement:** The protocol bridge rejects every legacy installation except 1.14.0, forcing users of valid older deployments through an arbitrary intermediate upgrade despite the product's intended direct-upgrade experience.

**In scope:**

- Bridge selection metadata, bootstrap validation, and legacy handoff behavior required for direct 1.8.0+ protocol-1 upgrades.
- Canonical upgrade-prompt seed, rendered upgrade prompt, and error/recovery wording for the supported legacy floor.
- Targeted protocol and packaging tests using real tagged 1.8.0 and 1.14.0 fixtures, plus a below-floor control.

**Out of scope:**

- Supporting versions below 1.8.0.
- Claiming compatibility with every historical or hand-modified installation without verification.
- Weakening host-quiescence, hash, containment, rollback, protocol, or second-hop safeguards.
- Redesigning the protocol-2 upgrade flow.

## Acceptance Criteria

- [~] AC-1: A real tagged 1.8.0 protocol-1 fixture upgrades through the bridge to the candidate protocol-2 feature release without first installing 1.14.0, with the bridge result and explicit second-hop evidence recorded. *(Deferred: requires operator-run validation against a real historical project; local bridge and second-hop coverage remains passing.)*
- [~] AC-2: A real tagged 1.14.0 fixture continues to complete the same bridge and second-hop path. *(Deferred: requires operator-run validation against a real historical project; local bridge coverage remains passing.)*
- [x] AC-3: A 1.7.x (or other below-1.8.0) source is rejected before mutation with a structured diagnostic naming the minimum supported version and safe recovery.
- [x] AC-4: Invalid/missing source-version metadata and protocol-2/mismatched protocol sources remain rejected before mutation; host quiescence, archive hashes, root containment, rollback, and project-surface isolation retain their existing checks.
- [x] AC-5: The public `upgrade wavefoundry` guidance and bridge errors state that 1.8.0+ protocol-1 projects upgrade directly, do not require 1.14 first, and explain the next action for a below-floor installation.

## Tasks

- [x] Trace the actual 1.8.0 and 1.14.0 legacy entry paths to confirm where the incoming bridge handoff is discovered before changing its contract.
- [x] Replace exact-source bridge metadata and validation with the minimum supported legacy version contract.
- [x] Update the legacy handoff and recovery response so supported 1.8.0+ sources take the bridge path before feature extraction.
- [x] Add endpoint, below-floor, malformed-version, and protocol-mismatch regression coverage while retaining the existing integrity controls.
- [x] Update the canonical upgrade-prompt seed, regenerate its rendered prompt, and update the applicable architecture decision/reference documentation.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Legacy-path discovery and bridge contract | implementer | — | Identify the 1.8.0 handoff seam before modifying it. |
| Regression coverage | qa-reviewer | Legacy-path discovery and bridge contract | Exercise 1.8.0, 1.14.0, below-floor, and retained fail-closed controls. |
| Upgrade guidance | docs-contract-reviewer | Legacy-path discovery and bridge contract | Keep the public direct-upgrade rule and recovery text aligned with code. |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md`

List real repository-relative paths here. Prepare uses these paths—not Scope, Rationale, or other narrative—to select automatic review lanes. Name a semantic security or performance risk in the wave's existing `Requested review lanes` field.

## Affected Architecture Docs

Update `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md`: it defines the distribution-protocol and bridge boundary. No broader architecture document is required unless implementation discovery identifies a changed control-flow boundary beyond that decision.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The direct 1.8.0 upgrade is the reported defect and primary outcome. |
| AC-2 | required | 1.14.0 is the established bridge route and must not regress. |
| AC-3 | required | The new floor must fail safely and explain recovery. |
| AC-4 | required | The change must not relax the bridge's integrity boundary. |
| AC-5 | important | Accurate guidance prevents users from repeating the unnecessary intermediate upgrade. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-05 | Planned as a deferred change; current wave `1ui1d` remains open and is not modified. | Field report: an approximately 1.8 installation could reach 1.15.3 only after manually stepping through 1.14. Source verification: bridge currently compares installed version for exact equality with builder-stamped 1.14.0. |
| 2026-08-05 | Prepare review corrected the documentation carrier to seed 160 plus its rendered prompt. | The rendered prompt is not canonical framework source; changing it alone would drift or be overwritten on the next render. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-05 | Support direct protocol-1 upgrades from 1.8.0+, not only 1.14.0. | It gives users a simple, bounded compatibility rule while preserving the standalone bridge's safety model. | Keep the 1.14 stepping stone (rejected: arbitrary friction); remove the guard entirely (rejected: would claim untested legacy compatibility); set floor at 1.9+ (rejected: no evidence that 1.8 needs exclusion). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Broadening the bridge hides an older-runner incompatibility. | Trace real tagged endpoint entry paths and require successful 1.8.0 and 1.14.0 integration fixtures before declaring the range supported. |
| A looser version check weakens integrity protections. | Change only version eligibility; retain independent validation for protocol, hosts, hashes, containment, atomic swap, rollback, and second hop. |
| An old agent host cannot surface the handoff correctly. | Test the public legacy entry path and return a compact, action-specific recovery result before mutation. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
