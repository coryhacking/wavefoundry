# Clarify TechDocs Publication-Boundary Repairs

Change ID: `1w3bt-doc techdocs-boundary-remediation-guidance`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-22
Wave: `1w047 review-plan-naming`

## Rationale

Field use of **Refresh TechDocs** correctly preserved useful repository links and reported 48 `techdocs_link_outside_boundary` findings, but then proposed two ineffective repairs: adding `repo_url` without rewriting the relative links, and removing a page from `nav` even though every page surviving `exclude_docs` remains published. The audit is correct; the authoring guidance needs to state its remediation semantics plainly enough that an agent cannot confuse navigation with publication or repository metadata with link rewriting.

## Requirements

1. State that `repo_url` does not rewrite Markdown links. A published page may keep a cross-boundary reference only by replacing its relative link with an explicit repository URL derived from an operator-configured remote/branch, or by naming the repository path in prose.
2. State that removing a page from `nav` changes discoverability only; it remains published and audited while it survives `exclude_docs`.
3. Describe the net ordered `exclude_docs` result: a page excluded by the final matching rule is not published, while a page re-included by a later `!` rule is published. A non-negated exclusion can reduce the publication set; a negated re-inclusion can expand it.
4. Preserve the current audit algorithm, finding schema, publication boundary, and operator ownership of the boundary.

## Scope

**Problem statement:** Ambiguous remediation prose led a downstream authoring agent to recommend changes that would not clear the findings it had just reported.

**In scope:**

- Canonical seed 178 wording and its self-hosted authored twin.
- Focused carrier assertions and audit regressions pinning nav/repository-URL polarity.
- The `1.19.0` changelog entry.

**Out of scope:**

- Changing the audit result schema or severity.
- Automatically rewriting links or guessing repository remotes/branches.
- Requiring nav coverage for every published page.
- Changing baseline generation, site rendering, or external dependencies.

## Acceptance Criteria

- [ ] AC-1: Seed 178 and `docs/prompts/refresh-techdocs.prompt.md` explicitly distinguish nav membership from publication and `repo_url` configuration from an explicit repository URL in page content.
- [ ] AC-2: A public audit fixture proves that a page omitted from `nav` remains a survivor and its outside-boundary relative link remains a finding.
- [ ] AC-3: The same fixture proves adding `repo_url` alone leaves the survivor set and outside-boundary finding unchanged, excluding the source page removes it from the publication set, and a later matching `!` rule re-includes it under ordered last-match semantics.
- [ ] AC-4: Existing TechDocs audit/carrier tests, docs validation, and diff check pass with no external renderer dependency.

## Tasks

- [ ] Amend seed 178 first, then manually synchronize its self-hosted authored twin.
- [ ] Add focused literal/semantic carrier assertions for nav, `repo_url`, and ordered exclude/re-include semantics.
- [ ] Add one audit polarity test covering nav omission, `repo_url`, source-page exclusion, and a later matching `!` re-inclusion.
- [ ] Update the `1.19.0` changelog and run focused/full verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance correction | technical-writer | — | Seed-first, then authored-twin parity |
| Boundary regression | qa-reviewer | Guidance correction | Exercise the public audit without changing its schema |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `docs/prompts/refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`
- `CHANGELOG.md`

## Affected Architecture Docs

N/A — this clarifies an existing documentation contract and pins already-implemented audit behavior; no architecture boundary changes.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Prevents the observed incorrect `repo_url` and nav advice. |
| AC-2 | required | Pins the actual publication-set definition. |
| AC-3 | required | Proves all three remediation polarities without changing the audit. |
| AC-4 | required | Keeps the documented Python-only verification boundary intact. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-22 | Planned from two downstream Refresh TechDocs reports. | Direct public audit probe: nav contained only `index.md`, yet `prompts/index.md` remained a survivor; adding `repo_url` left its outside-boundary finding unchanged. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-22 | Correct guidance and add one polarity regression; do not alter the audit. | The implementation already matches MkDocs publication semantics and all 84 focused audit tests pass. | Teach the audit to interpret `repo_url` (wrong layer); add an autofix/suggestion schema (broader contract); require every survivor in nav (rejects legitimate link-only pages). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Wording could still imply that `repo_url` alone repairs links. | Require the literal distinction between configured metadata and an explicit absolute repository URL in page content. |
| A test could check only nav output and miss survivor behavior. | Assert survivor membership and exact finding polarity before/after `repo_url` and `exclude_docs` changes. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
