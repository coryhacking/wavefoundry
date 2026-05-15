# Dashboard: Distinguish Index Updates from Rebuilds

Change ID: `12khf-enh semantic-index-detail-distinguishes-update-vs-rebuild`
Change Status: `complete`
Owner: Engineering
Wave: `12jnb project-index-stale-use-index-inputs`
Status: complete
Last verified: 2026-05-13

## Rationale

The Semantic Index tile should stay coarse, but the dialog should be explicit about whether the index is being updated or rebuilt. That distinction is useful when the dashboard is watching a background rebuild versus a smaller incremental update, and the extra detail should live in the existing pill rather than a separate line or second pill.

## Requirements

1. The Semantic Index tile should keep generic status copy.
2. The index dialog should distinguish `updating` from `rebuilding` in its build detail copy.
3. The build detail should reuse the existing pill in the dialog, not create a second pill or standalone line.
4. The dialog should preserve layer-specific progress information.
5. Regression tests should cover the wording and layout split.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Build-state detection semantics
- Index health status calculations

## Acceptance Criteria

- The Semantic Index tile still shows generic `Indexing...` and `Stale...` wording.
- The dialog uses `updating` wording when the background index is being refreshed incrementally.
- The dialog uses `rebuilding` wording when the index is doing a full rebuild.
- The dialog keeps the build detail inside the existing pill.
- Regression coverage verifies the wording and layout split.

## Tasks

- Update Semantic Index dialog wording for update versus rebuild
- Reuse the existing dialog pill for build detail
- Preserve the generic tile copy
- Add regression coverage for the dialog wording split

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The tile should remain concise |
| AC-2 | required | The dialog should communicate the build mode accurately |
| AC-3 | required | The two states should not be conflated |
| AC-4 | required | The dialog should keep build detail inside the existing pill |
| AC-5 | required | Tests should protect the wording and layout contract |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The wording could become too specific to one build path | Keep the distinction limited to update versus rebuild |
| The tile could pick up detail again | Leave the tile copy generic and test it separately |

## Implementation Verification

The Semantic Index dialog now shows update/rebuild detail inside the existing pill, while the tile remains generic. Verification passed with `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `node --check .wavefoundry/framework/dashboard/dashboard.js`, and `./.wavefoundry/bin/docs-lint`.
