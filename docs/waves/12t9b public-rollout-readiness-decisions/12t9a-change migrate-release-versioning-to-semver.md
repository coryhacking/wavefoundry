# Migrate Release Versioning To Semver

Change ID: `12t9a-change migrate-release-versioning-to-semver`
Change Status: `implemented`
Owner: planner
Status: implemented
Last verified: 2026-05-22
Wave: `12t9b public-rollout-readiness-decisions`

## Rationale

Wavefoundry currently uses a date-plus-letter release identifier for packaged framework artifacts and upgrade ordering. That works for internal sequencing, but it is a weak public contract for downstream operators because it does not communicate compatibility intent, expected upgrade scope, or the difference between patch, minor, and major changes. Before broader rollout, the framework should adopt semver for externally visible releases and define how build-date metadata coexists with release ordering.

## Requirements

1. Define a semver-based release contract for Wavefoundry's externally visible framework version.
2. Preserve deterministic upgrade ordering without relying on lexicographic comparison of date-shaped version strings.
3. Specify how packaged artifact names, `.wavefoundry/framework/VERSION`, manifest `framework_revision`, and upgrade checks map to the new version contract.
4. Document the migration path from existing date-based packs and installed revisions so current repos can upgrade safely.
5. Update tests and maintainer/operator documentation to reflect the new versioning contract.

## Scope

**Problem statement:** Wavefoundry's current date-based versioning is tightly embedded in packaging, upgrade, and docs surfaces, but it is not a strong public release contract for a larger audience.

**In scope:**

- Define the semver contract and compatibility rules for framework releases.
- Update packaging and upgrade assumptions that currently depend on `YYYY-MM-DDx` ordering.
- Decide whether date or build metadata remains visible alongside semver.
- Update release-facing docs, prompts, and verification guidance.
- Identify required code and test touch points for the implementation wave.

**Out of scope:**

- Publishing to PyPI, Homebrew, or any external package registry.
- Redesigning the framework zip distribution model itself.
- Bundling unrelated release-process changes that are not required for semver adoption.

## Acceptance Criteria

- [x] AC-1: The change doc names the current date-based version touch points and defines the target semver contract for public releases.
- [x] AC-2: The plan identifies the required implementation surfaces for packaging, upgrade comparison, artifact naming, tests, and docs.
- [x] AC-3: The migration path for repos already carrying date-based `VERSION` and `framework_revision` values is explicit.
- [x] AC-4: The plan states which legacy date fields, if any, remain as metadata rather than release-ordering keys.

## Tasks

- [x] Review `build_pack.py`, `check_version.py`, `upgrade_wavefoundry.py`, and release docs for date-based assumptions.
- [x] Define the target semver representation and artifact naming convention.
- [x] Decide backward-compatibility behavior for upgrading existing date-based installs.
- [x] Record required test updates and docs updates for the later implementation wave.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| version-audit | planner | — | Enumerate current version touch points in code and docs |
| contract-definition | planner | version-audit | Define semver contract and migration rules |
| implementation-scope | planner | contract-definition | Name required code/test/doc edits for execution |

## Serialization Points

- Packaging and upgrade code paths must agree on one ordering contract before implementation starts.
- Release docs and prompt surfaces should not be updated until the semver contract is finalized.

## Affected Architecture Docs

`docs/architecture/current-state.md`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/testing-architecture.md`, and `docs/architecture/decisions/` for the release-version contract.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The rollout needs a clear public release contract before implementation begins |
| AC-2 | required | Packaging and upgrade work cannot proceed safely without a complete touch-point map |
| AC-3 | required | Existing repos need an explicit migration path to avoid upgrade ambiguity |
| AC-4 | important | Metadata strategy materially affects rollout clarity but follows the core release contract |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Change scaffolded from rollout-readiness evaluation. | Repository inspection of `build_pack.py`, `check_version.py`, upgrade prompt/docs, and release docs. |
| 2026-05-22 | Completed version audit. Current touch points: `VERSION` file (`YYYY-MM-DDx`), `framework_revision` in `docs/prompts/prompt-surface-manifest.json`, zip artifact filename, `compare_versions()` in `check_version.py` (lexicographic string compare), and upgrade hooks in `upgrade_wavefoundry.py` that use raw string `<` to gate migration steps. Target contract defined: `MAJOR.MINOR.PATCH` semver for public releases starting at `1.0.0`; implementation surfaces and migration path recorded. | `build_pack.py`, `check_version.py`, `upgrade_wavefoundry.py`, `docs/prompts/prompt-surface-manifest.json`, `.wavefoundry/framework/VERSION`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-22 | Track semver migration as its own change rather than bundling it into a broader rollout umbrella. | Packaging, upgrade, tests, and docs all depend on the version contract. | Leave versioning as-is; defer until after wider rollout. |
| 2026-05-22 | Adopt `MAJOR.MINOR.PATCH` semver starting at `1.0.0` for the first public release. Operator-confirmed 2026-05-22. | Date-based strings are not a strong public release contract and do not communicate compatibility intent. `1.0.0` signals stable public API; `0.1.0` would signal pre-release with breaking changes expected — operator chose `1.0.0`. | Continue date strings; adopt `YYYY.MM.DD` calendar versioning; start at `0.1.0`. |
| 2026-05-22 | Drop date string from the primary version field; keep it available as optional build metadata (`1.0.0+20260521`) if needed for traceability. | Two parallel version identifiers in the same field add complexity with no benefit — semver is the ordering contract. | Keep `YYYY-MM-DDx` as a secondary field alongside semver. |
| 2026-05-22 | Replace lexicographic `compare_versions()` with proper semver parsing using `packaging.version.Version` from the `packaging` stdlib-adjacent package. | Lexicographic ordering breaks for semver (`1.10.0` < `1.9.0` lexicographically). | Use `importlib.metadata`; implement own parser. |
| 2026-05-22 | Migration path for existing date-based installs: treat any `framework_revision` matching `YYYY-MM-DDx` as pre-`1.0.0` — the upgrade script compares against a sentinel `"0.0.0"` when the installed revision is date-shaped. | Operators upgrading from date-based installs must not get a false "downgrade" or "same" verdict. | Require operators to manually reset `framework_revision` before upgrading to semver builds. |
| 2026-05-22 | Upgrade hooks that gate on `ctx.from_version < "2026-05-19a"` must be rewritten to use `packaging.version.Version` with an explicit date-string fallback (return `Version("0.0.0")` for date-shaped strings). | Raw string compare on semver breaks silently — hooks would never fire for old date-based installs upgrading through the transition. | Freeze all upgrade hooks at the semver transition and document them as pre-1.0 only. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Semver migration touches more files than initially expected because the date format is embedded in code, tests, and prompts. | Audit current touch points before implementation and keep the migration wave tightly scoped to version-contract surfaces. |
| Existing installed repos may need mixed-version upgrade handling. | Define backward-compatibility rules in the planning change before implementation begins. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
