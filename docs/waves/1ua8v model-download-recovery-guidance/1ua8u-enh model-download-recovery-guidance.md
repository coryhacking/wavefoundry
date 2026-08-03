# Model Download Recovery Guidance

Change ID: `1ua8u-enh model-download-recovery-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-03
Wave: `1ua8v model-download-recovery-guidance`

## Rationale

When automatic model acquisition fails, operators currently receive only a
generic cache/status message. They need a deterministic, offline-safe recovery
path that names the exact release asset, where to obtain it, where to place it,
and how the next setup or upgrade run verifies and applies it.

## Requirements

1. On a model-download failure, surface a concise recovery message that names
   the exact independently versioned `wavefoundry-models-<set>.zip` asset
   required by the installed or selected feature package.
2. Document the manual recovery flow in the README and package/upgrade
   instructions: obtain the matching model-set asset from the same release or
   internal distribution, place it in the repository root, `~/`,
   `~/.wavefoundry/`, `~/.wavefoundry/dist/`, or `~/Downloads/`, then rerun
   the normal setup or upgrade command.
3. State that the model-set asset is never selected as a framework upgrade,
   that Wavefoundry validates provenance, hashes, licenses, and the declared
   model-set version before materialization, and that an invalid asset must not
   replace the existing verified cache.
4. Keep the standard online download path unchanged when no matching local
   model-set asset is available.

## Scope

**Problem statement:** Operators cannot reliably recover from blocked model
downloads without knowing which offline asset to obtain or where to place it.

**In scope:**

- Setup failure reporting and the affected model-download exception path.
- README, package, and upgrade operator guidance.
- Focused tests that prove the recovery text includes exact model-set and
  location information without changing the normal online behavior.

**Out of scope:**

- Downloading models automatically outside the existing canonical setup path.
- A remote release lookup, credentialed download helper, or a new installer.
- Changing the model-set artifact, validation, cache layout, or selection
  policy delivered by wave `1u95o`.

## Acceptance Criteria

- [x] AC-1: A blocked or failed model-download path identifies the exact
  `wavefoundry-models-<set>.zip` recovery asset and the standard directories
  where it can be placed before rerunning setup or upgrade.
- [x] AC-2: README and package/upgrade instructions provide the same bounded
  manual recovery flow, including validation/no-replacement guarantees.
- [x] AC-3: Existing online model download behavior remains unchanged when the
  matching local asset is absent.

## Tasks

- [x] Locate the model-download failure boundary and add recovery guidance
  using the declared model-set version.
- [x] Add focused failure-path coverage and preserve normal online-path tests.
- [x] Update README and package/upgrade documentation; validate docs and run
  the relevant framework tests.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Recovery path and tests | framework-engineer | — | Keep the change local to existing setup/model boundaries. |
| Operator documentation | docs-contract-reviewer | recovery path | Mirror the exact bounded recovery behavior. |


## Serialization Points

- Finalize the exact recovery wording and source boundary before updating all
  operator surfaces so the instructions cannot drift.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` and
`docs/architecture/testing-architecture.md` — the recovery path is part of
the offline model intake contract and its test surface.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The recovery outcome must be actionable without source inspection. |
| AC-2 | required | Release-facing instructions are the operator contract. |
| AC-3 | required | Offline guidance must not disrupt ordinary online setup. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-03 | Planned after operator requested an explicit manual download recovery path. | Existing `model_bundle` validation and discovery policy remain the authority; this change only makes recovery actionable. |
| 2026-08-03 | Implemented centralized recovery wording at `_model_failure_message` and mirrored it across release-facing guidance. | Focused failure and unchanged-online prewarm tests passed; `test_model_bundle.py` passed 11/11; `wf_validate_docs` passed. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-03 | Reuse standard distribution directories rather than introduce a special model location. | The feature/model selector already scans the shared locations and first-upgrade setup inherits the same contract. | New directory or separate downloader. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Recovery text drifts from actual selectors. | Derive wording and tests from the existing `model_bundle` and setup discovery contract. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
