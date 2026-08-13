# Generated Manifest Never Reconciles Against Its Default

Change ID: `1v7a0-bug generated-manifest-never-reconciles-against-default`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-12
Wave: 1v79z reconciliation-self-healing-and-dispositions

## Rationale

`prompt-surface-manifest.json` is renderer-managed, so the reconciliation scan excludes it by
basename. Nothing else reconciles it either. `docs_gardener.ensure_manifest` on an existing file
does exactly three things: `setdefault("schema_version", 1)`, `setdefault("seed_framework_source",
…)`, and stamp `last_gardened_at`. It never compares the file's list-valued keys against
`default_manifest_payload`. A renderer-managed file that neither self-heals nor gets scanned drifts
permanently and silently, which is the same failure shape wave `1v4mw` closed for rendered marker
regions.

Reported from a downstream repository on 1.16.2: `generated_artifacts` still listed
`docs/agents/journals/` and its README after the journal retirement, and because the file is
scan-excluded nothing surfaced it.

**Verified here, and the drift runs in BOTH directions**, which the report did not observe:

- **Stale entries linger.** This repository's manifest carries
  `"enabled_internal_features": ["agent_journals", …]`. `agent_journals` names the retired journal
  system, and `enabled_internal_features` is read by no framework script at all — a dead key that
  can never heal.
- **New default entries never arrive.** This repository's `generated_artifacts` is MISSING three
  entries the current default carries: `docs/waves/README.md`, `docs/agents/personas/README.md`,
  and `docs/reports/`. A repo installed before those were added never receives them.

The second direction matters more than the first: a missing entry means an artifact the framework
believes it generates is not declared as generated, so anything reasoning from that list reasons
from a false picture.

## Requirements

1. An existing manifest's list-valued keys reconcile against `default_manifest_payload` on the
   gardening pass, so entries retired from the default are removed and entries added to it arrive.
2. Reconciliation preserves project-authored content that the default does not own. The manifest
   carries operator/renderer keys beyond the default's own (`framework_revision`, `generated_at`,
   `generated_personas`, `upgrade_merge_notes`, `wave_root`, `public_prompt_surface`), and this
   change must not delete them.
3. The dead `agent_journals` entry and the `enabled_internal_features` key it sits in are resolved
   explicitly rather than left as permanent residue.
4. A repository whose manifest already matches the default is not rewritten, so the change adds no
   churn to healthy repos.

## Scope

**Problem statement:** a renderer-managed, scan-excluded file has no reconciliation path, so its
generated-artifact list drifts from the framework default permanently and in both directions.

**In scope:**

- Reconciling `generated_artifacts` against `default_manifest_payload` in `ensure_manifest`.
- Deciding and implementing the disposition of `enabled_internal_features` / `agent_journals`.

**Out of scope:**

- Removing `prompt-surface-manifest.json` from the scan's exclusion set. It is renderer-managed and
  correctly excluded; the fix is to make it self-heal, not to report it as operator-editable work.
- Any other renderer-managed generated file. If the census finds a second one with the same
  no-reconciliation shape, file it rather than widening this change.
- The manifest's schema or its consumers.

## Acceptance Criteria

- [x] AC-1: An entry present in a repository's `generated_artifacts` but absent from `default_manifest_payload` is removed by the gardening pass, asserted with the field-reported entry (`docs/agents/journals/`).
- [x] AC-2: An entry present in the default but absent from the repository's manifest is added, asserted with one of the three this repository is currently missing.
- [x] AC-3: Manifest keys the default does not own survive reconciliation unchanged, asserted with `framework_revision`, `upgrade_merge_notes`, and `generated_personas` present before and after.
- [x] AC-4: A manifest already matching the default is not rewritten, asserted by comparing bytes across a gardening pass so healthy repos gain no churn.
- [x] AC-5: This repository's own manifest self-heals: `agent_journals` is gone and the three missing `generated_artifacts` entries are present, asserted against the real file rather than a fixture.
- [x] AC-6: A malformed or partial manifest does not lose project content or crash the gardener, asserted with a manifest missing `generated_artifacts` entirely.

## Tasks

- [x] Reproduce first: a fixture manifest carrying a retired entry and missing a current one must survive the gardening pass unchanged before the fix.
- [x] Reconcile `generated_artifacts` against the default, preserving keys the default does not own.
- [x] Resolve `enabled_internal_features` / `agent_journals`: confirm no reader exists, then remove the entry or the key with the rationale recorded.
- [x] Verify this repository's manifest self-heals rather than hand-editing it, so the fix is proven by the artifact it was built to repair.
- [x] Census the other renderer-managed generated files for the same no-reconciliation shape; file separately rather than widening.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | Fixture manifest that drifts in both directions; must pass before, fail after. |
| reconcile | implementer | reproduce | Key-scoped merge; must not touch keys the default does not own. |
| dead-key | implementer | — | `agent_journals` disposition; confirm no reader first. |
| census | implementer | — | Other renderer-managed files with no reconciliation path. File, do not absorb. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`
- `docs/prompts/prompt-surface-manifest.json`

## Affected Architecture Docs

`N/A`. This restores a reconciliation path to one generated file; it decides no boundary, contract,
or flow. The manifest's schema and consumers are unchanged.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported defect. |
| AC-2 | required | The direction the report did not observe, and the more consequential one: a missing entry means the framework's own picture of what it generates is wrong. |
| AC-3 | required | A merge that drops operator or renderer keys would trade a silent staleness for silent data loss, which is strictly worse. |
| AC-4 | required | Rewriting a healthy manifest on every gardening pass would add churn to every repo to fix a minority's drift. |
| AC-5 | required | Proving the fix on the artifact that motivated it, rather than on a fixture alone. |
| AC-6 | important | Fail-safe behavior on a partial manifest; the gardener runs inside the docs gate and must not break it. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | Filed from downstream 1.16.2 field feedback. Verified in this tree before planning rather than taken on report: `ensure_manifest` performs only two `setdefault` calls plus a `last_gardened_at` stamp on an existing file and never consults `default_manifest_payload`, and `prompt-surface-manifest.json` is excluded from the scan by basename. Both halves of the reporter's diagnosis hold. | `docs_gardener.ensure_manifest`; `docs_gardener.default_manifest_payload`; `reconcile_scan.EXCLUDED_BASENAMES`. |
| 2026-08-12 | **Post-implementation review found the fix did not reach the steady state, and the AC-5 evidence was obtained through a path real runs do not take.** `gardener_run` computes `bump_last_gardened = bool(updated_paths)`, and `ensure_manifest` returned EARLY on that flag before reaching the reconciliation. The flag is False exactly when no doc needed stamping, which is the normal state of a well-gardened repository, so the manifest healed only on runs that happened to stamp something else. The original AC-5 check called `ensure_manifest(..., bump_last_gardened=True)` directly and therefore bypassed the gate entirely. Repaired by reconciling on every run while leaving the DATE stamp gated, so a non-bumping run still does not churn `last_gardened_at` and the change-only write still prevents churn when nothing moved. Reproduced through the real `gardener_run` entry point before and after. | Pre-repair: `gardener_run` on a repo with fresh docs left `docs/agents/journals/` in place. `test_reconciles_through_the_real_entry_point_with_nothing_to_stamp`; `test_non_bumping_run_does_not_stamp_the_date` pins the gating that had to survive. |
| 2026-08-12 | Two consequences of always-reconciling, both surfaced by an existing test rather than by inspection, both correct and left as-is. First, the FIRST gardening run after this lands rewrites a manifest that is missing default entries even when no doc needed stamping, and reports it as an updated path; that is the self-heal, and it is a one-time transition per repository. Second, the same run normalizes manifest formatting, because the comparison now happens on a path that previously returned early. Neither affects a repository whose manifest is already current and gardener-written, which is every repository the gardener has touched. The pre-existing `test_empty_run_prints_nothing_to_report` failed on both counts because its fixture was hand-rolled and incomplete; the FIXTURE was corrected to be a real gardened manifest rather than the assertion weakened. | `test_empty_run_prints_nothing_to_report` failed twice with `['docs/prompts/prompt-surface-manifest.json'] != []`, then passed once the fixture carried the default list and was written through `normalize_manifest_json`. |
| 2026-08-12 | **Readiness council: AC-3's hazard is concrete, not theoretical.** The manifest keys the default does not own have real consumers OUTSIDE the gardener, so a wholesale payload replacement would break working behaviour rather than merely lose metadata: `framework_revision` is written by `build_pack` and read by `check_version` and `dashboard_lib`; `wave_root` is read by `wave_lint_lib` (`wave_validators`, `cli`), so clobbering it would break docs-lint itself; `upgrade_merge_notes` is referenced by `reconcile_scan` as the rationale for excluding this file from the scan. The merge MUST be scoped to the keys `default_manifest_payload` owns. | Consumers located per key across `scripts/*.py` excluding tests. |
| 2026-08-12 | Second possibly-dead key found while checking consumers: `generated_personas` has no Python reader either. NOT actioned in this change, and not assumed dead: unlike `enabled_internal_features`, it was not exhaustively searched across non-Python surfaces (the dashboard bundle in particular). Recorded so the implementer does not silently sweep it in with `agent_journals`; it needs its own census. | Per-key consumer search; `generated_personas` returned no `scripts/*.py` reader. |
| 2026-08-12 | Local reproduction found a SECOND drift direction the report did not observe: this repository's `generated_artifacts` is missing `docs/waves/README.md`, `docs/agents/personas/README.md` and `docs/reports/`, all present in the current default. Also found a dead key: `enabled_internal_features` carries `agent_journals`, and no framework script reads `enabled_internal_features` at all. | `docs/prompts/prompt-surface-manifest.json` compared against `default_manifest_payload`; grep for `enabled_internal_features` across `scripts/*.py` excluding tests returns nothing. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | Fix by reconciling in the gardener rather than by removing the file from the scan's exclusion set. | The file is renderer-managed, so reporting it as operator-editable work would be wrong: the operator cannot fix the underlying drift by editing it, because the next render rewrites it. Self-healing is the correct disposition for renderer-owned content, matching how `renderer_provenance_flags` are already treated as self-healing rather than actionable. | Un-exclude it from the scan (rejected: turns a renderer-owned artifact into recurring operator homework). Leave it and document the drift (rejected: the drift is invisible precisely because nothing reports it). |
| 2026-08-12 | Do NOT hand-edit this repository's manifest ahead of the fix. | The stale `agent_journals` key and the three missing entries are the local reproduction. Patching them by hand would remove the only evidence available for proving the fix works on a real artifact, and AC-5 exists to use it. | Clean the manifest now and test on fixtures only (rejected: discards the reproduction). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A key-scoped merge could delete operator or renderer content the default does not model, turning a silent staleness into silent data loss. | AC-3 asserts the non-default keys survive; the merge must be scoped to the keys the default owns rather than replacing the payload wholesale. |
| Reconciling on every gardening pass could rewrite healthy manifests and add churn to every repo. | AC-4 asserts byte equality across a pass on an already-matching manifest. |
| `enabled_internal_features` may have an out-of-tree reader (a target repo, a host integration) even though nothing in this tree reads it. | Confirm within this repository and remove the stale entry rather than the whole key unless the census clears the key too; record the reasoning rather than assuming. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
