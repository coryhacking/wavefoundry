# Refuse a Carrier Destination That Is a Dangling Link

Change ID: `21ayx-bug baseline-destination-symlink-is-followed`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

A downstream distribution reported (their Y8), and reading the code at `1c5ba851` confirms: `_contained_review_carrier_path` (`.wavefoundry/framework/scripts/render_agent_surfaces.py:2320`) resolves the destination with `resolve(strict=False)` and checks only that the result is inside the repository. A dangling link at a destination whose target is inside the repository passes; `reconcile_lifecycle_prompt_baselines` (`:4377`) then sees `is_file()` false and writes the template at the link's target. `.git/` counts as inside the repository, so a link to `.git/hooks/pre-push` made the render create that file (template text, mode 0644). Every missing-only materializer that resolves through this helper has the same behaviour.

## Product Intent

A render never creates a file by following a dangling link at a carrier destination. Before: the template lands at whatever in-repository path the link names, including under `.git/`. After: the render refuses with a message naming the destination, and nothing is written. Boundaries: a link to an existing in-repository file keeps today's behaviour (present, not materialized); a link leaving the repository is refused as today. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. The affected set is derived: every caller of `_contained_review_carrier_path` (including the `techdocs_audit_lib` wrapper). The fix lives in the helper so the set is covered at once.
2. When the destination, or any of its ancestors below the repository root, is a link (symlink, or on Windows a junction or other link reparse point, detected per component with `lstat` and the existing link-metadata helper) whose resolved target does not exist, the helper raises the existing `RuntimeError` refusal type with a message naming the destination as a dangling link.
3. When the resolved path lies under `<root>/.git` (compared case-insensitively on macOS and native Windows), the helper refuses the same way, whether the link is at the destination or an ancestor and whether or not the target exists.
4. Other links whose target exists inside the repository resolve as today; a link leaving the repository is refused as today.
5. Read-only callers do not crash on the new refusal: docs-lint's carrier check (`wave_lint_lib/core_validators.py`) reports the destination as a finding instead of raising, and `techdocs_audit_lib` keeps mapping the refusal to its degrade result.

## Scope

**Problem statement:** a dangling link at a carrier destination makes a missing-only render create a file at the link's target.

**In scope:**

- The dangling-link refusal in the helper.
- Docs-lint's handling of the refusal.
- Tests for a dangling destination link into `.git/hooks/`, a dangling ancestor link, an ancestor link to an existing `.git/` folder, an existing in-repository link, an escaping link, and docs-lint over a repository with a dangling destination.

**Out of scope:**

- Reporting links as a separate upgrade finding (the refusal is the report).
- Links elsewhere in the repository that no carrier resolves.

## Acceptance Criteria

- [x] AC-1: A render over a repository whose `docs/prompts/close-wave.prompt.md` is a dangling link to `.git/hooks/pre-push` refuses with a message naming the destination, and `.git/hooks/pre-push` does not exist afterwards; on the current code it is created.
- [x] AC-2: A dangling link at an ancestor folder of a destination is refused the same way and creates no folder.
- [x] AC-3: An ancestor folder linked to an existing `.git/hooks/` folder is refused and nothing is written under `.git/`; a destination link to an existing in-repository file outside `.git/` behaves as today (not rewritten by missing-only materializers); a link leaving the repository is still refused with the existing message.
- [x] AC-4: Docs-lint over a repository with a dangling destination link completes and reports the destination instead of raising.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the dangling-link and `.git` checks to `_contained_review_carrier_path`.
- [x] Make docs-lint's carrier check report the refusal as a finding.
- [x] Add the link fixtures (skipped with a recorded reason where the platform cannot create a symlink).
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                    |
| ---------- | ----------- | ---------- | ------------------------ |
| fix        | implementer | none       | helper refusal           |
| tests      | implementer | fix        | link fixtures            |


## Serialization Points

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: a tighter refusal inside an existing containment helper; no boundary, flow or verification seam changes.

## Platform Behavior

macOS, Linux and WSL2: symlinks are detected by `lstat`. Native Windows: symlinks need privilege or Developer Mode, and junctions are link reparse points; detection uses the existing link-metadata helper so both are covered; the `.git` comparison ignores case on macOS and Windows, and a worktree's `.git` gitdir file is a file, so no carrier can resolve beneath it; and fixtures that cannot create a link are skipped with a reason rather than passing vacuously.

## AC Priority


| AC   | Priority | Rationale                     |
| ---- | -------- | ----------------------------- |
| AC-1 | required | the reported write            |
| AC-2 | required | ancestor link variant         |
| AC-3 | required | `.git` refused; others as now |
| AC-4 | required | read-only callers stay usable |
| AC-5 | required | change-local verification     |


## Progress Log


| Date       | Update  | Evidence                                          |
| ---------- | ------- | ------------------------------------------------- |
| 2026-10-21 | Planned | distribution follow-up Y8, verified at `1c5ba851` |
| 2026-10-21 | Readiness amendments: refuse any resolved path under `.git` (Requirement 3, AC-3); read-only callers report instead of raising (Requirement 5, AC-5). | readiness security-reviewer and code-reviewer findings |
| 2026-10-21 | Implemented: `_contained_review_carrier_path` walks each destination component with `os.lstat` and `contained_files._is_link_metadata`, refusing a link whose target is missing, then refuses any resolved path whose first component under the root is `.git` (case-folded on macOS and Windows); `_check_marker_family_parity` reports a refused destination as a finding. AC-1 to AC-4 marked. | new `tests/test_carrier_destination_links.py` (9 tests): 6 fail on the HEAD copies of both files, all pass now; a HEAD run reproduced `.git/hooks/pre-push` created at mode 0644; focused runs OK for test_render_agent_surfaces (172), test_docs_lint (350), test_techdocs_audit_lib (86), test_path_containment (23), test_vocabulary_prompt_names (36), test_lifecycle_gates_structure (15), test_record_layout_census (5) |
| 2026-10-21 | Delivery repair cycle 1: the `.git` comparison casefolds on every platform, covering WSL2 checkouts on a Windows drive where `sys.platform` is linux (finding E2). Deferred: the upgrade caller of `review_protocol_carriers_skipped_by_render` swallows any refusal, so a dangling destination drops its skipped-carrier warnings instead of reporting them; this predates the wave for escaping links. | `test_carrier_destination_links` 10 OK; platform-keyed revert fails the new test |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Refuse dangling links and `.git` targets in the shared helper | One place covers every caller; fails closed | Skip and report in each materializer (many call sites, easy to miss one); refuse every destination link (breaks repositories that link prompts to shared files); `O_EXCL|O_NOFOLLOW` writes on the spelled path (covers missing-only writers but not region upserts) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A repository relies on a dangling link being filled in | The message names the destination; removing the link restores materialization |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
