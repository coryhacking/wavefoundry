# Active Wave Scoped Metric Tiles

Change ID: `12jvc-enh active-wave-scoped-metric-tiles`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard metric tiles for changes, ACs, and tasks should reflect only the current active wave(s). Grand totals belong in the progress bars, while the tiles should show current-wave scope so they do not mix in staged plans or non-active waves.

## Requirements

1. The Changes tile must count only changes that belong to active wave(s).
2. The ACs tile must count only ACs that belong to active wave(s).
3. The Tasks tile must count only tasks that belong to active wave(s).
4. Pending and total values for those tiles must exclude staged plans and non-active waves.
5. The Wave tile behavior must remain unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- wave documentation updates needed to track the new metric behavior

**Out of scope:**

- Progress bar calculations
- Wave lifecycle semantics

## Acceptance Criteria

- Changes, ACs, and tasks tiles use only active-wave data for their pending and total counts.
- Staged plans no longer contribute to the change/AC/task tile counts.
- The Wave tile still shows the repository-level wave counts unchanged.
- Regression coverage proves the tile counts stay scoped to active waves.

## Tasks

- Update dashboard metric tile calculations to use active-wave scope only
- Add regression coverage for scoped metric tile counts

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The dashboard must stop mixing staged work into active-wave tiles. |
| AC-2 | required | Current-wave counts must stay separate from progress bars. |
| AC-3 | required | The Wave tile should remain stable. |
| AC-4 | required | Regression coverage should lock the new scope. |
