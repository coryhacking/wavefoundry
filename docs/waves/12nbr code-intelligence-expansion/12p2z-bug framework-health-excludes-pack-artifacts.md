# Framework health walker should ignore pack artifacts

Change ID: `12p2z-bug framework-health-excludes-pack-artifacts`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-17
Wave: 12nbr code-intelligence-expansion

## Rationale

The framework package stamps `VERSION` and writes `MANIFEST` during packaging, but those files are packaging artifacts rather than framework source. The current framework health walker still considers them indexable, so post-upgrade health checks report them as added even though the framework index intentionally excludes them. That leaves the framework layer in a noisy stale state after every pack update.

This change makes the framework walker ignore `MANIFEST`, `MANIFEST.pre-*`, and `VERSION` before health comparison so packaging artifacts never appear in the indexability set.

## Requirements

1. The framework health walker must exclude `MANIFEST`, `MANIFEST.pre-*`, and `VERSION`.
2. The exclusion must apply before health comparison and stale-path detection.
3. The project layer behavior must remain unchanged.
4. The change must not affect `docs_search` / CIA availability.

## Scope

**Problem statement:** framework packaging artifacts are being treated as new indexable files by the framework layer health walker, causing persistent stale-path noise after upgrades.

**In scope:**

- `indexer.py`
- `test_indexer.py`

**Out of scope:**

- Rebuilding the framework index on every upgrade
- Changing packaging zip structure
- Project index behavior

## Acceptance Criteria

- AC-1: Framework health comparisons do not report `MANIFEST` or `VERSION` as added.
- AC-2: Framework health comparisons do not report `MANIFEST.pre-*` as added.
- AC-3: Project-layer indexing and health remain unchanged.
- AC-4: Tests prove the framework walker ignores these pack artifacts.

## Required Review Lanes

- `qa-reviewer` — required (affects upgrade-time framework health)
- `code-reviewer` — required (touches framework walker/filter logic)

## Tasks

- Extend the framework walker filter so packaging artifacts are excluded before indexability checks.
- Add regression coverage for `MANIFEST`, `MANIFEST.pre-*`, and `VERSION`.
- Verify that framework health no longer reports the artifacts as added/stale after a pack build.

## Affected Architecture Docs

N/A. This is a narrow framework-health consistency fix.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Eliminates the stale-path noise for MANIFEST |
| AC-2 | required | Covers future pre-manifest variants if they resurface |
| AC-3 | required | Prevents unintended project-layer regressions |
| AC-4 | important | Proves the walker exclusion is actually enforced |
