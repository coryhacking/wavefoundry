# Dashboard: Simplify Semantic Index Tile Build Status Copy

Change ID: `12khe-enh semantic-index-tile-uses-generic-build-status`
Change Status: `complete`
Owner: Engineering
Wave: `12jnb project-index-stale-use-index-inputs`
Status: complete
Last verified: 2026-05-13

## Rationale

The Semantic Index tile currently exposes layer-specific and progress-heavy build messages that belong in the detail dialog. The tile should stay high-level and readable at a glance, using only generic build-state wording such as `Indexing...` or `Stale...`.

The detail dialog can keep the per-layer status, progress line, and background-build guidance.

## Requirements

1. The Semantic Index tile should use generic build-status copy while a build is running or the index is stale.
2. The detail dialog should continue to show layer-specific build state and progress.
3. The tile should avoid repeating progress details or layer names that are better suited to the dialog.
4. Regression tests should cover the simplified tile copy and the unchanged dialog detail behavior.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Changing build-state detection or index health semantics
- Changing the dialog's detailed build guidance

## Acceptance Criteria

- The Semantic Index tile shows a generic `Indexing...` message while a build is running.
- The Semantic Index tile shows a generic `Stale...` message while the index is stale.
- The Semantic Index dialog still shows the layer-specific running/failure/stale state and progress line.
- Regression tests verify both tile simplification and dialog detail preservation.

## Tasks

- Simplify Semantic Index tile build-status copy
- Preserve detailed build guidance in the index dialog
- Add regression coverage for the new tile/dialog split

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The tile should be concise and easy to scan |
| AC-2 | required | The dialog must remain the place for detailed build guidance |
| AC-3 | required | The two surfaces should not drift apart |
| AC-4 | required | Tests should keep the split behavior stable |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The tile could become too vague | Limit the tile to coarse state only, not detailed progress |
| The dialog could accidentally lose detail | Leave the dialog implementation unchanged except for any test expectations |

## Implementation Verification

The Semantic Index tile now shows generic `Indexing...` and `Stale...` copy while the detailed dialog continues to expose layer-specific build state and progress. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `node --check .wavefoundry/framework/dashboard/dashboard.js`, and `./.wavefoundry/bin/docs-lint`.
