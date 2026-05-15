# Dashboard: Make Progress Card Use the Same Scoped Change Set as Metric Tiles

Change ID: `12khd-enh progress-card-uses-scoped-change-set`
Change Status: `complete`
Owner: Engineering
Wave: `12jnb project-index-stale-use-index-inputs`
Status: complete
Last verified: 2026-05-13

## Rationale

The dashboard metric tiles already switch between active-wave scope and pending scope depending on whether a wave is active. The Progress card still mixes a different change universe, which produces contradictory counts such as pending tiles showing open work while the progress rows still read from a narrower or historical set.

The Progress card should use the same scoped change set as the metric tiles for changes, ACs, and tasks so pending remains a subset of total progress instead of a separate universe.

## Requirements

1. The Progress card should use the same active-wave or pending change set as the summary tiles for changes, ACs, and tasks.
2. When no active wave exists, the progress rows should reflect the pending change set, including staged changes.
3. The wave row can remain repo-wide historical progress, but the change, AC, and task rows must stay internally consistent with the summary tiles.
4. Regression tests should cover both the active-wave and no-active-wave dashboard snapshots.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Changing the underlying wave lifecycle data model
- Changing the metric tile copy or the dialog titles

## Acceptance Criteria

- In active-wave mode, the progress rows for changes, ACs, and tasks use the active-wave scoped changes and stay aligned with the active metric tiles.
- In pending mode, the progress rows for changes, ACs, and tasks use the pending scoped changes and stay aligned with the pending metric tiles.
- The progress rows no longer report values that can exceed or conflict with the corresponding metric tile totals for the same scope.
- Regression tests confirm the progress card and metric tiles agree on the same scope inputs.

Implementation verification: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `python3 .wavefoundry/framework/scripts/run_tests.py` (1156 tests), and `./.wavefoundry/bin/docs-lint` all passed.

## Tasks

- Thread the scoped change set into the Progress card
- Update the progress-row calculations for changes, ACs, and tasks
- Add regression coverage for active and pending scope alignment

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The dashboard should present one consistent scope for progress and tiles |
| AC-2 | required | Pending counts should never be isolated from their matching totals |
| AC-3 | required | The fix should preserve the wave row's repo-wide completion view |
| AC-4 | required | Tests should prevent the scope mismatch from returning |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Progress rows could drift from the summary tiles again | Reuse the same scoped change list for both surfaces |
| The wave row could be accidentally converted to scoped behavior | Keep the wave row explicitly historical/repo-wide |
