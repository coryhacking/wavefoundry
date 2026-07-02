# Incremental post-edit docs-lint: scope the hook to the changed file, keep the full corpus gate at close

Change ID: `1p9c1-enh incremental-docs-lint-hook`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

Every other post-edit reaction in the framework is incremental — the semantic index refreshes
only the edited file, and the secrets scan (`check_hardcoded_secrets`, `scan_all=False`) scans only
git-touched files. **Docs-lint is the one holdout:** the post-edit hook runs the entire
`wave_lint_lib.cli` — ~20 checks, several of which iterate the whole `docs/` tree — on every single
edit. On a large repository the field report showed this stalling the editing agent (the reason
`1p9bf` gave the hook a configurable timeout as a stopgap). The dominant cost is the whole-tree
per-file loops (`check_metadata`, `check_markdown_links`) and the per-subtree rglobs (journals,
personas, waves, plans, agents) running over hundreds of docs when only one changed.

The checks split cleanly:

- **Per-file (scopeable to the changed doc):** `check_metadata`, `check_markdown_links`, and the
  structural validators keyed to a doc's kind — `check_journal_docs`, `check_persona_docs`,
  `check_wave_docs`, `check_plan_filenames`, `_check_agent_role_metadata`,
  `_check_agent_category_metadata`.
- **Corpus-wide (cannot be reduced to one file):** `check_cross_artifact_consistency`,
  `check_factor_surface`, `check_closed_wave_requirements`, `check_prepare_council_verdict`, the
  repo-structure checks, design-system checks.

The right shape is the same one secrets already uses, **self-detecting the changed set** rather than
depending on the hook to thread an edited path: incremental docs-lint lints the **git working-tree
changed set** — reusing the sibling helper `_get_changed_files` in this same `wave_lint_lib` package
(`git diff --name-only HEAD` staged+unstaged, plus untracked-non-ignored) — filtered to `docs/**`
markdown, running only the per-file validators; the **full corpus lint stays at `wave_validate` and
`wave_close`**, which are — and remain — the authoritative gate. The post-edit hook was never the
hard gate (`1p9bf` already made its timeout advisory), so scoping it does not weaken any gate that
callers rely on. This also subsumes the `1p9bf` timeout stopgap: linting the working-set does not
time out.

**Why the git-changed-set, not the indexer's manifest.** The indexer self-detects via a
stat(mtime+size+inode)+content-hash manifest that lives *in the index state* and is rewritten on
every index build. Docs-lint has no such manifest and must not couple to the index's — its
"changed since" baseline would reset whenever the index rebuilds, unrelated to lint cadence. Secrets
already answers the same "what should I check on an edit" question with the git working-tree delta,
in this very package; docs-lint reusing that is one mechanism and one mental model
("docs-lint and secrets both lint the working-tree delta; the full corpus lint runs at close"). The
tradeoff vs the index's per-file precision: mid-wave the git delta is the whole uncommitted set (the
wave's files, not just the last edit) — still bounded to the working set, not the hundreds-of-docs
tree, and identical to what secrets already does.

## Requirements

1. `wave_lint_lib.cli` accepts a `--changed` flag. When present, docs-lint runs in **incremental
   mode**: it **self-detects** the changed set from the git working tree (reusing the sibling
   `_get_changed_files` helper — `git diff --name-only HEAD` + untracked-non-ignored), filters it to
   `docs/**` markdown, runs only the per-file validators on those files, and skips the corpus-wide
   checks. It does NOT require a path argument (parity with how secrets self-detects). When absent,
   behavior is byte-for-byte unchanged (full lint).
2. Incremental mode dispatches per changed markdown doc by kind: always `check_metadata` +
   `check_markdown_links` for that file; plus the structural validator matching its location
   (journal / persona / wave record / plan-or-change / agent doc), scoped to that file.
3. **Config-file fallback (correctness guard):** if the changed set contains a corpus/config file
   whose correctness is inherently cross-file — `docs/workflow-config.json`,
   `docs/prompts/prompt-surface-manifest.json`, or `docs/repo-profile.json` — incremental mode falls
   back to the **full** lint for that invocation (these edits are rare and high-consequence, and the
   per-file validators do not cover JSON). A changed set with no `docs/**` markdown and no config
   file is a no-op for docs-lint (nothing to check), still exiting `ok`.
4. When git is unavailable or reports no worktree (`_get_changed_files` returns empty on non-git or
   git failure), incremental mode is a safe `ok` no-op — it never falls through to a whole-tree scan
   and never errors (the full gate at `wave_validate`/close still covers the corpus).
5. The rendered post-edit hook body invokes docs-lint with `--changed` (no path threading — the cli
   self-detects). **Only the post-edit hook is incremental.** Every authoritative gate runs the FULL
   corpus lint (no `--changed`): `wave_validate`, `wave_prepare` (readiness), `wave_close`, the
   **install** and **upgrade** docs gates, and CI/`wf docs-lint`. This is the operator-confirmed
   contract — incremental is only the fast per-edit feedback; the full scan runs at prepare, close,
   install, and upgrade.
6. Incremental mode preserves output/exit contract: prints `ERROR:`/`WARNING:` lines to stderr and
   `docs-lint: ok` + exit 0 on success, exactly like full mode, so the hook's advisory handling is
   unchanged.
7. The per-file structural validators are refactored to accept an optional scoping parameter
   (e.g. `only: set[Path] | None`) without changing their whole-tree behavior when unscoped — the
   full-lint call path is behavior-preserving (verified by the existing 253 docs-lint tests).
8. `run_tests.py` + `wave_validate` pass.

## Scope

**Problem statement:** the post-edit docs-lint hook runs a whole-`docs/`-tree lint on every edit —
the only non-incremental reaction left — which stalls the editing agent on large repos.

**In scope:**

- `wave_lint_lib/cli.py`: `--changed` flag; self-detect the changed set via the reused git helper;
  incremental per-file dispatch; config-file full fallback; non-git/empty safe no-op.
  *(framework_edit_allowed)*
- `wave_lint_lib/secrets_validators.py` (or a small shared `helpers`/`context` move): expose
  `_get_changed_files` for reuse by the cli without duplicating the git logic (generalize in place or
  lift to a shared module; keep secrets' call site behavior identical). *(framework_edit_allowed)*
- `wave_lint_lib/wave_validators.py`: optional `only=` scoping param on the six per-file structural
  validators (behavior-preserving when unscoped). *(framework_edit_allowed)*
- `render_platform_surfaces.py`: invoke the post-edit docs-lint call with `--changed` (self-detecting,
  no path); re-render the hook mirrors. *(framework_edit_allowed)*
- Tests: incremental self-detected scoping runs only per-file checks; a broken changed file is caught;
  a clean changed file passes without touching siblings; the config-file fallback runs full; an
  empty/non-git changed set is an ok no-op; full-lint call path unchanged (regression).

**Out of scope:**

- Making the corpus-wide checks themselves incremental (they are inherently cross-file; the full gate
  at close covers them).
- Changing what `wave_validate` / `wave_close` run (they stay full-tree — the authoritative gate).
- Removing the `1p9bf` configurable timeout (it stays as defense-in-depth; incremental just makes a
  timeout far less likely).

## Acceptance Criteria

- [x] AC-1: with a clean changed doc, `docs-lint --changed` does NOT run the corpus-wide checks while
      the full lint does. Evidence: `test_incremental_skips_corpus_checks_that_full_reports` — a removed
      required file (a corpus check) is reported by `_run_full_checks` but NOT by
      `_run_incremental_checks(changed={clean journal})`. The changed set is self-detected from git (no
      path argument).
- [x] AC-2: incremental still catches a per-file defect in a changed file. Evidence:
      `test_incremental_catches_per_file_defect_in_changed_doc` — a journal with `## Governance` renamed
      reports `missing required section \`## Governance\`` in incremental mode.
- [x] AC-3: a **config** file in the changed set falls back to the full lint. Evidence:
      `test_incremental_config_change_falls_back_to_full` — `_run_incremental_checks` returns `None`
      (the full-lint signal) when `docs/workflow-config.json` is in the changed set.
- [x] AC-4: an empty or non-git changed set exits `ok` as a safe no-op, never a whole-tree fall-through.
      Evidence: `test_incremental_empty_and_non_doc_changed_set_is_noop` (unit) +
      `test_changed_flag_on_non_git_tree_is_ok_noop_end_to_end` (subprocess on the non-git fixture).
- [x] AC-5: the rendered post-edit hook invokes docs-lint with `--changed` (self-detecting); re-render
      is idempotent; the full-gate paths run full lint. Evidence:
      `test_converted_hook_bodies_launch_via_windowless_pythonw` asserts the `--changed` argv; the
      rendered `.claude/hooks/post-edit.py` / `.cursor` / `.windsurf` mirrors carry it; md5 re-render
      idempotency confirmed; `wave_validate` (full) clean.
- [x] AC-6: full-lint behavior is byte-for-byte unchanged when `--changed` is absent — the existing
      253 docs-lint tests pass untouched (the full path is now `_run_full_checks`, same checks/order).
- [x] AC-7: `run_tests.py` + `wave_validate` pass. Evidence: docs-lint + render subsuites green (367);
      full `run_tests.py` at the wave's final run; `wave_validate` clean.

## Tasks

- [x] Reuse `_get_changed_files` for the cli (imported from `.secrets_validators`, following the
      package's existing cross-module `_`-prefixed import convention) without changing secrets' behavior.
- [x] `wave_validators.py`: added optional `only=` scoping to `check_journal_docs`,
      `check_persona_docs`, `check_wave_docs`, `check_plan_filenames`, `_check_agent_role_metadata`,
      `_check_agent_category_metadata` (unscoped = current whole-tree behavior).
- [x] `cli.py`: added `--changed`; `_run_incremental_checks` self-detects the git changed set → filters
      to `docs/**` markdown (+ root entry files for links) → per-file dispatch; config-file → full
      fallback (returns None); empty/non-git safe no-op; secrets stays incremental+record-only; shared
      `_emit` preserves the output/exit contract; extracted `_run_full_checks` (behavior-preserving).
- [x] `render_platform_surfaces.py`: the post-edit docs-lint hook body now invokes `--changed`;
      re-rendered mirrors (`.claude`/`.cursor`/`.windsurf`); `wave_validate`/CLI full-lint paths unchanged.
- [x] Tests: `IncrementalDocsLintTests` (self-detected scoping, per-file defect, config fallback,
      empty/non-git no-op, end-to-end non-git) + updated render argv assertion; full-lint regression
      (253 unchanged).
- [x] `run_tests.py` + `wave_validate` (docs-lint + render subsuites green; full suite at the wave's
      final run).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane in `wave_lint_lib` + the rendered hook; the `only=` refactor is behavior-preserving and gated by the existing 253-test docs-lint suite, then the new incremental tests. |

## Serialization Points

- `wave_lint_lib/cli.py` `main()` is the shared full-lint path — the `--changed` branch must not
  alter the unscoped path (regression-gated by the existing suite).
- `render_platform_surfaces.py` hook body is a rendered surface — edit source + re-render, never
  hand-edit a rendered hook; assert idempotent re-render.

## Affected Architecture Docs

`docs/architecture/` index-triggers / hook-surface pattern doc if one enumerates the post-edit hook
reactions (index refresh, secrets scan, docs-lint) — add docs-lint's new incremental behavior so the
"every post-edit reaction is incremental" invariant is documented. Otherwise `N/A` — no boundary or
data-flow change; the authoritative docs gate (`wave_validate`/close) is unchanged.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core behavior — self-detected incremental scoping that skips corpus-wide checks. |
| AC-2 | required | Incremental must still catch the defect in a changed file. |
| AC-3 | required | The correctness guard — config edits must not silently skip cross-file checks. |
| AC-4 | required | Empty/non-git must be a safe no-op, never a whole-tree fall-through. |
| AC-5 | required | The hook must invoke `--changed`; full-gate paths must stay full. |
| AC-6 | required | No regression to the authoritative full lint. |
| AC-7 | required | Suite + docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned. Operator asked to make docs-lint incremental like every other post-edit reaction; chose to fold into the open `1p9bm` wave (4th change). Design: `--changed` incremental mode (per-file validators scoped to the edited doc), corpus-wide checks stay at the `wave_validate`/`wave_close` gate, config-file changes fall back to full lint. Subsumes the `1p9bf` timeout stopgap. | operator request; `wave_lint_lib/cli.py` `main()` check inventory; secrets `scan_all=False` incremental precedent. |
| 2026-07-01 | Refined after operator asked to "work off the same file change the indexer does": self-detect the changed set from the **git working-tree delta** (reuse secrets' `_get_changed_files`), not the indexer's index-state stat+hash manifest (wrong dependency for lint cadence) and not a hook-threaded path. `--changed` needs no path argument. | `secrets_validators._get_changed_files` (git diff + untracked); `indexer._detect_changes` (index-state manifest) — the distinction. |
| 2026-07-01 | Implemented under `framework_edit_allowed`. Six per-file validators got a behavior-preserving `only=` param; `cli.py` gained `--changed` with `_run_incremental_checks` (git self-detect → per-file dispatch, config→full fallback, empty/non-git no-op) + extracted `_run_full_checks`/`_emit`; the post-edit hook body now invokes `--changed` (re-rendered, idempotent). Operator-confirmed contract recorded: **only the post-edit hook is incremental; prepare/close/install/upgrade all run the full lint**. Full-lint regression: 253 docs-lint tests unchanged; +5 incremental tests; render argv test updated. docs-lint+render subsuites green (367); `wave_validate` clean. | `wave_validators.py`/`cli.py`/`render_platform_surfaces.py` diffs; `IncrementalDocsLintTests`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Hook runs per-file validators scoped to the changed doc; corpus-wide checks stay at the `wave_validate`/`wave_close` gate. | Mirrors the secrets + index incremental model; the hook was never the hard gate (`1p9bf` made its timeout advisory), so scoping it weakens no gate callers rely on. | Make every check incremental (rejected — cross-file checks cannot be correctly reduced to one file); keep whole-tree with a bigger timeout (rejected — the field-report stall + it stays O(n docs)). |
| 2026-07-01 | Self-detect the changed set via the **git working-tree delta** (reuse secrets' `_get_changed_files`), NOT the indexer's stat+hash manifest and NOT a hook-threaded `--changed <path>`. | Operator asked to reuse the changed-file signal. The indexer's manifest lives in index state and resets on index builds (wrong dependency for lint cadence); secrets already answers "what to check on an edit" with the git delta in this same package, giving one mechanism + one mental model; self-detection means the cli works for the hook AND manual `wf docs-lint --changed` without threading a path. | Reuse the indexer's stat+hash manifest (rejected — couples docs-lint to index-build state); thread the edited path from the hook (rejected — hook-only, doesn't self-detect, two mechanisms). |
| 2026-07-01 | Accept that mid-wave the git delta lints the whole uncommitted set, not just the last edit. | Still bounded to the wave working set (not the hundreds-of-docs tree), each file is cheap, and it is identical to what secrets already does — consistency beats squeezing to a single file. | Track a docs-lint-owned per-file manifest for last-edit precision (rejected — new persistent state to maintain for marginal gain). |
| 2026-07-01 | Config-file changes (`workflow-config.json`/`prompt-surface-manifest.json`/`repo-profile.json`) fall back to full lint in incremental mode. | Their correctness is inherently cross-file and the per-file validators don't cover JSON; these edits are rare and high-consequence. | Skip them like other files (rejected — would silently drop cross-artifact/factor-surface catching on the exact edits most likely to break it). |
| 2026-07-01 | Add an optional `only=` scoping param to the per-file validators rather than extracting new single-file helpers. | Minimal, backward-compatible; the unscoped path stays byte-for-byte identical and is regression-gated by the existing 253 tests. | Extract per-file helpers + rewrite the whole-tree loops (rejected — larger blast radius for no behavior gain). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Incremental mode misses cross-file breakage introduced by an edit (e.g. removing a `wave-id` another doc references). | Documented, accepted tradeoff — surfaces at the next `wave_validate`/`wave_close` (the hard gate); same tradeoff secrets + index already make; the hook is advisory. |
| The `only=` refactor subtly changes full-lint behavior. | Unscoped path is behavior-preserving; the existing 253 docs-lint tests run untouched as the regression gate before any new test. |
| A config edit slips the fallback and skips cross-artifact checks. | AC-3 tests the fallback explicitly with a real cross-artifact inconsistency present while a config file is the changed path. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
