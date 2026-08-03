# Drift Diff Parser Keeps Git's Tab Terminator on Space-Containing Paths, Killing Evaluation on Every Conforming Repo

Change ID: `1u91n-bug drift-diff-parser-drops-tab-terminated-paths`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-02
Wave: `1u8r2 memory-consolidation-and-drift-parser`

## Rationale

Solaris downstream field report (2026-08-02, on pack pgf6), root-caused by the target-repo
agent and verified line-for-line against this tree: `_gardener_only_pairs()` in
`index_state_store.py` parses the unified diff's `+++` line as `target = line[4:]` (:3545)
and strips only a `b/` prefix (:3553). Git appends a **TAB terminator** to the `+++` filename
whenever the path contains a space (standard unified-diff disambiguation; emitted regardless
of `core.quotepath=off`, which the invocation at :3473 already sets). The tab survives into
`rel`, the blob spec `f"{c_sha}:{rel}"` (:3602) names a nonexistent path, and the batch lookup
fails closed at :3614 with `blob_fetch_failed: changed blob missing <sha>:<path><TAB>`.

The impact is structural, not incidental: the framework's OWN lifecycle naming convention
generates space-containing paths (`<id> <slug>.md` plans/ADRs, `<id> <slug>/` wave
directories), and `wf_garden_docs` stamps `Last verified:` dates into exactly those docs,
which is what creates gardener-only candidates. So every conforming repo eventually has
doc-drift evaluation permanently dead: Solaris counts 178 tracked space-containing paths (177
under `docs/`), and this repository is in the same state. Before wave 1u8o0 the failure was
silent (`flagged_count: 0` read as "no drift"); 1u8o0's staleness diagnostic is what made the
field diagnosis possible, and the reporter confirmed the classifier now names the cause. This
is the remaining half: make the evaluation actually succeed.

## Requirements

1. **The `+++` target parse strips git's tab terminator:** everything from the first `\t`
   onward is removed from `target` before the `/dev/null` check and `b/` strip. A path
   containing a literal tab cannot be conflated: git C-quotes such paths (control characters
   force quoting even under `core.quotepath=off`), so an unquoted `+++` line's first tab is
   always the terminator, never path content. Record this reasoning as a code comment at the
   strip site.
2. **Red-first against a canonical producer:** the regression test creates a real temp git
   repo containing a space-named living doc (the lifecycle convention shape,
   `docs/plans/<id> <slug>.md`), commits a gardener-only `Last verified:` date change, and
   drives `_gardener_only_pairs` (or its public caller) over the real `git log -p` output.
   Red first: the current parser fails with `blob_fetch_failed` naming the tab-terminated
   path; green after: the pair classifies as gardener-only and evaluation succeeds. Per the
   fixtures-from-canonical-producers rule, the diff MUST come from real git, not a
   hand-written patch string (a hand-written fixture would encode the author's tab
   assumptions).
3. **Quoted-path frames stay fail-closed, not misparsed:** a `+++ "b/..."` C-quoted target
   (path with control characters or double quotes) is not silently treated as a valid
   relative path. Either parse the quoted form correctly or fail the classification with a
   reason naming the quoted path; pin whichever is chosen with a test driven by a real git
   commit of such a path where the platform allows creating one, else document the boundary
   at the parse site and pin the fail-closed reason with the closest constructible input.
4. **Recovery is observable on this repository:** after the fix, a drift evaluation pass on a
   repo with space-containing gardener-stamped docs succeeds and the 1u8o0 staleness state
   clears on first success (`drift_failure_count` reset path already exists; verify it clears
   here rather than assuming).

## Scope

**Problem statement:** doc-drift evaluation fails closed on every repo whose living docs
follow the framework's own space-containing naming convention, because the diff parser keeps
git's tab terminator in the extracted path.

**In scope:** the `+++` target parsing in `_gardener_only_pairs` (`index_state_store.py`
:3542-3554); regression tests in `test_doc_drift.py` (or the suite owning
`_gardener_only_pairs` coverage) built on real git output.

**Out of scope:** the drift classification semantics (candidate/confirm logic unchanged);
the 1u8o0 staleness bookkeeping (already shipped; only its clear-on-success is verified
here); `dashboard_lib.py`'s diff PRODUCER (:1307, emits clean paths, censused unaffected);
renaming any framework path convention.

## Acceptance Criteria

- [x] AC-1: A real-git gardener-only date change to a space-named doc classifies successfully
  (red-first: the pre-fix parser fails with the tab-terminated `blob_fetch_failed`).
- [x] AC-2: Clean paths (no spaces) and deletion frames (`+++ /dev/null`) behave exactly as
  before; the existing doc-drift suite passes unmodified except for deliberate additions.
- [x] AC-3: The quoted-path decision (Requirement 3) is implemented, pinned, and recorded in
  the Decision Log.
- [x] AC-4: Full framework suite passes; drift evaluation on this repository reaches a
  success (staleness cleared) in a post-fix verification run.

## Tasks

- [x] Red-first regression test via a real temp git repo (space-named doc, gardener-only edit)
- [x] Strip the tab terminator at the parse site with the quoting-reasoning comment
- [x] Requirement 3 quoted-path decision + pin
- [x] Doc-drift suite + full suite; post-fix staleness-clear verification on this repo
- [x] CHANGELOG Fixed bullet (1.15.0 unreleased section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          |       |


## Serialization Points

- `index_state_store.py` (shared with any concurrent index work)

## Affected Architecture Docs

Candidates at Prepare: none expected beyond CHANGELOG (parser-internal fix; the doc_drift
response shape is unchanged). Verify at Prepare whether the spec's doc_drift freshness text
names failure reasons in a way this changes.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Restores drift evaluation for the framework's own space-containing path convention. |
| AC-2 | required | Prevents the narrow parser repair from changing clean-path or deletion behavior. |
| AC-3 | required | Keeps unsupported C-quoted paths fail-closed instead of resolving the wrong blob. |
| AC-4 | required | Proves both repository-scale regression safety and observable recovery from the stale failure state. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-02 | Filed from the Solaris field report; root cause verified against this tree with code_read (:3545 parse, :3553 b/ strip, :3602 spec, :3614 failure) and the single-site blast radius confirmed with a code_keyword census (one parser; dashboard_lib :1307 is a producer; remainder tests). | Solaris session report 2026-08-02 (clean path resolves, tab-appended path fails `fatal: path ... does not exist`); code_read/code_keyword this session |
| 2026-08-02 | Implemented the narrow tab-terminator strip, retained fail-closed handling for C-quoted paths, and completed delivery verification. | `test_doc_drift.py`: 102 tests passed, including real-Git C-quoted control-character path coverage; full framework suite: 6,741 tests across 61 files passed; live `wf_audit` drift evaluation reported `status: evaluated`, `consecutive_failures: 0`, and `stale_since: null`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-02 | Fail closed on C-quoted `+++` targets. | The fix is limited to Git's unquoted TAB terminator; accepting an escaped pathname without a complete decoder could point blob lookup at the wrong file. | Decode C quoting here: deferred until a real need because it expands parser scope. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stripping at the wrong layer masks a genuinely malformed frame | Strip only the terminator on unquoted `+++` targets; malformed-patch and fail-closed semantics elsewhere unchanged, pinned by AC-2 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
