# Expose ordered TLS trust bundle candidates

Change ID: `248o3-enh expose-trust-bundle-candidates`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-24
Wave: 246r5 waveforge-upgrade-and-maintenance-hardening

## Rationale

A downstream TLS client needs the model downloader’s bundle precedence without importing a private helper or changing process-wide CA variables.

## Product Intent

A caller can select a CA bundle for its own TLS context using the same ordering as setup (AC-1 and AC-2).

## Requirements

1. Expose a documented public Python accessor in a lightweight module that clients can import without initializing setup_index for the existing ordered bundle paths. Keep a single implementation shared with setup and preserve current setup behavior. Keep TLS verification enabled and leave provider selection outside this change.

## Scope

Expose discovery only. Preserve the private entry point where current callers rely on it. Document the supported import and contract for distributions.

## Acceptance Criteria

- [x] AC-1: On a fixture with duplicate, missing and distinct candidates, the public accessor returns the independently expected ordered existing paths and matches setup, including the existing fallback ordering.
- [x] AC-2: In a fresh Python child, snapshot the environment before importing the documented accessor. Import it and call it with controlled CA environment variables, use a returned test CA path to configure a verifying TLS context, and compare the complete environment to the pre-import snapshot. Include initially absent setup variables to detect import-time additions. No live network is required.

## Tasks

- [x] Expose a documented public Python accessor in a lightweight module that clients can import without initializing setup_index for the existing ordered bundle paths. Keep a single implementation shared with setup and preserve current setup behavior. Keep TLS verification enabled and leave provider selection outside this change.
- [x] Exercise AC-1 and AC-2 and record evidence in the Progress Log.

## Agent Execution Graph

The implementer delivers the change and its checks. The reviewers verify the evidence independently.

## Serialization Points

- `.wavefoundry/framework/scripts/trust_bundles.py`

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

## Affected Architecture Docs

Check the downstream extension reference for the public import and its stability contract.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Verifies the primary outcome. |
| AC-2 | required | Verifies the compatibility boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from Waveforge’s v1.51.0 feedback. | Item B1. |
| 2026-11-24 | Setup and downstream clients share the public `trust_bundles.trust_bundle_candidates` accessor. The shipped README and distribution extension reference document its import. | AC-1 passed against eight independently ordered fixture paths, one duplicate and one missing path. |
| 2026-11-24 | A fresh Python child loaded the fixture CA into a hostname-checking context with required verification. It checked the entire environment before import, after import, after discovery and after context creation. | AC-2 passed with all three setup variables initially absent. The managed Python environment passed all 210 setup-index tests and the framework module census passed. |

| 2026-11-24 | Delivery handoff | Implementation is ready for delivery review. The tests used local fixtures on macOS. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Use the existing framework path. | Planner default within the operator-selected scope. | Copying the path list into a downstream client would let its certificate precedence drift from setup. |

## Risks

Expose discovery only. Preserve the private entry point where current callers rely on it. Document the supported import and contract for distributions.

## Session Handoff

Prepare the admitted spec before implementation.
