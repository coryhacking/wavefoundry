# Prune generated trees before reconciliation traversal

Change ID: `20kfp-bug reconciliation-generated-tree-scope`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12
Wave: 20kfr reconciliation-generated-tree-scope

## Rationale

The operator wants build output and caches excluded before traversal. A field scan reportedly visited about 70,000 entries and consumed about 129 MB across SwiftPM build trees, hitting both the 30-second deadline and, with more time, the total-byte cap. Those measurements are field evidence, not independently repeated. Current code already prunes __pycache__, .git, node_modules and root .local/target, but misses .build and does not consult Git ignores. A tiny isolated probe independently confirms root/nested .build JSON remains eligible despite a .gitignore entry, while root/nested __pycache__ is pruned. The byte cap already applies after suffix/scope eligibility; generated eligible JSON and Markdown exhaust it.

## Requirements

1. Prune known generated/cache trees during directory traversal, including SwiftPM .build at any depth. Match whole directory components or deliberate rooted prefixes; do not exclude near-miss source names or every generic directory named build without a documented rule.
2. For ordinary repository content, honor Git ignore decisions before descending into ignored directories or reading ignored files. Use bounded batched operations within the existing scan deadline, preserving tracked files and supported nested/negated ignore semantics. Query lexical directory paths without a trailing slash using default index-aware Git check-ignore semantics; tracked descendants keep their parent traversable. Bound batches and child timeouts by the existing work limits. Do not launch one Git subprocess per file or hand-roll an approximate ignore grammar.
3. Preserve required live agent instructions, lifecycle prompts and registered host permission/configuration carriers even when ignore rules would hide them. Mandatory carriers mean exact framework/native registered paths plus direct members of declared live prompt/role/rule directories. Derive lifecycle, role and skill destinations from canonical registries; permit TOML only for the exact .codex/config.toml carrier. Inspect those paths directly without traversing an ignored generated tree to find them. Static generated, history and framework exclusions take precedence; arbitrary instructions inside ignored generated output are not mandatory carriers.
4. Retain current file/entry/byte/candidate/deadline caps and contained reads. Legitimate scope exclusions are not incomplete scans; an in-scope unreadable input, exhausted budget or failed required ignore query remains truthfully incomplete. Non-Git repositories retain documented bounded static-scope behavior. A missing Git executable or failed repository/ignore probe in a Git target is not proof of non-Git status and must not trigger a broad fallback walk.
5. Do not delete diagnostic artifacts, raise scan limits, add a separate project exclusion configuration by default, or introduce a second unbounded fallback scan. Reuse the same scan scope in standalone and upgrade reporting.

## Scope

Reconciliation traversal and scope, bounded Git ignore integration, required-carrier preservation and regression/documentation changes. No scanner timeout increase, deletion of build/profile evidence, performance timing diagnosis, arbitrary project config surface, or changes to unrelated scanners.

## Acceptance Criteria

- [x] AC-1: Root and nested .build plus existing cache exclusions are pruned before descent or content reads. A generated-tree fixture cannot consume the live-source byte budget through excluded descendants; near-miss live directories remain eligible.
- [x] AC-2: Git ignored ordinary trees/files are excluded with correct tracked/nested/negated controls. Required live instruction/prompt/host-config findings remain detectable even under an ignore rule; scope choice is independently testable.
- [x] AC-3: Non-Git, Git-query failure/deadline, links/special files and actual live-content budget exhaustion yield the documented bounded result without false clean findings or weakened containment.
- [x] AC-4: Standalone and upgrade reporting retain three finding channels and incomplete-state semantics using the corrected traversal; representative live-source findings match baseline and no generated artifacts are removed.

## Tasks

- [x] T-1: Bound known generated exclusions, mandatory-carrier inclusion and Git ignore precedence before readiness; inspect existing ignore helpers without coupling to the semantic indexer.
- [x] T-2: Implement directory pruning and bounded ignore evaluation with required-carrier preservation.
- [x] T-3: Add small deterministic traversal/read-budget and semantic fixtures, then independent code/QA/security review; update scan-scope contracts and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation and focused tests | implementer | admission and readiness | Single write owner |
| Independent phase review | code, QA, security, architecture and docs-contract lanes as selected | phase-specific evidence | Read-only review |

## Serialization Points

One implementer owns shared upgrade code and seed/rendered guidance; coordinate those paths with the runtime-reload plan. Reviewers are read-only. Root CHANGELOG.md is also an intended edit. Preserve published/local pack bytes and all consumer diagnostic artifacts. No code edit before admission and readiness.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/data-and-control-flow.md`

## Affected Architecture Docs

Update docs/architecture/data-and-control-flow.md and docs/specs/mcp-tool-surface.md for the changed decision/scope boundary; canonical seed 160 and rendered upgrade guidance must agree.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Preserves the requested behavior and its safety/compatibility boundary |
| AC-2 | required | Preserves the requested behavior and its safety/compatibility boundary |
| AC-3 | required | Preserves the requested behavior and its safety/compatibility boundary |
| AC-4 | required | Preserves the requested behavior and its safety/compatibility boundary |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Planned from field feedback; no repository code changed. | Isolated seven-file fixture: eligible paths were .build/generated.json, package/.build/generated.json and docs/guide.md; both pycache paths, root target and .local were excluded. A five-byte total cap returned incomplete/total_bytes after three bytes. No large field artifact or full field scan was copied or rerun. |
| 2026-10-12 | T-1 complete: bounded Git oracle and carrier precedence selected in Requirements. | Temporary real-Git fixture retained tracked descendants two levels below an ignored parent, nested rules and negated custom/keep.md; querying custom without a slash preserved traversal. Existing secrets helper is post-traversal and fails open, so is unsuitable. Add controls for ignored registered carriers, exact TOML, optional absence, Git errors/timeouts/malformed output, no-descent and contained-read refusal. |
| 2026-10-12 | Carrier implementation note under Requirement 3: project paths come from REVIEW_POLICY_CARRIER_REGISTRY, LIFECYCLE_PROMPT_BASELINES, SKILL_HOSTS and pure registry/declaration skill enumeration. Derive native wrappers from registered role stems, including agent-role-guru; avoid renderer discovery helpers that read target files. | Fixed host entry/config paths plus bounded direct members of docs/prompts, docs/agents, docs/agents/specialists, docs/agents/personas, .claude/agents and .cursor/rules; no recursive ignored-host exception. Every explicit candidate and directory enumeration shares existing work and containment limits. Independent architecture found no unresolved design choice; delivery must prove omitted-wrapper and no-descent controls. |

| 2026-10-12 | Upgrade consumer integration added and executed; seed/rendered scope contracts updated. | The real reporting child and direct scanner agree on all three nonempty channels while root/nested .build and ignored generated/host-cache sparse files stay unread and preserved. Removing .build exclusion in memory causes incomplete/file_bytes. BoundedReporting plus DryRun tests 21/21 and PendingUpgrade tests 12/12 pass in separate per-file processes; a mixed-loader diagnostic invocation failed and is not claimed green. |

| 2026-10-12 | T-2 and AC-1 through AC-4 implemented and verified with focused fixtures; source frozen for independent delivery lanes. | Scanner 83/83, upgrade reporting/dry-run 21/21 and paired preview 12/12 pass under per-file isolation. Seven scanner mutants and the generated-byte consumer mutant detected. Git child batches cap 256 paths and share remaining deadline; required carriers retain contained reads and all static exclusions. Final combined canonical qualification is pending. |

| 2026-10-12 | Delivery cycle 1 strengthens the exact-TOML regression boundary; production code unchanged. | Independent code reviewer showed broadening eligibility to all TOML survived 83 tests because the negative input was Git-ignored. Recorded repair_start before adding unignored ordinary.toml; original targeted test passes, broadened-suffix mutant now fails exactly on ordinary.toml (83 run, 1 assertion failure, 0 errors/skips). Fresh independent reverification requested. |

| 2026-10-12 | Cycle 1 code finding cleared by fresh independent reverification; source frozen for final qualification. | Reviewer confirmed ordinary.toml is unignored, broadened-TOML mutant fails specifically on that input, normal seven scope tests pass. Coordinator reran all 83 scanner tests; full docs validation and diff whitespace checks pass. Final canonical suite will qualify both waves together. |

| 2026-10-12 | Combined qualification completed 12,430 tests/185 files/12 skips with two integration failures; all earlier permission failures resolved and no tree movement reported. | Timed-call classification census lacks the new bounded Git helper row; staged delegated-summary reproduction loses its expected finding after scanner registry dependencies changed. Independent diagnosis requested before repair. These are regression integration checks for the admitted Git/carrier change, with no change to scope semantics, ACs, runtime limits or operator authority. |

| 2026-10-12 | Qualification repair cycle 2 adds the bounded Git helper to the timed-call census and stages seven already-shipped registry dependencies in the delegated-summary fixture. | Original assertions and production code unchanged. Three focused controls pass; fresh independent deletion mutants fail both original assertions. Code/QA/release reverification cleared the findings and the tool recorded convergence. Final canonical qualification remains pending. |

| 2026-10-12 | Final combined canonical qualification and all required independent specialist delivery reviews passed; all ACs and tasks are complete. | 12,430 tests across 185 files, 12 skips, exit 0. Fresh green framework receipt matches current inputs hash e4821ce2fb674828b350dd4b0f1048c2707714a34d65b55f3536078520a90345. No source or record movement during qualification; no waiver, timing conclusion or package claim. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Select traversal-time generated-directory pruning plus bounded Git ignore decisions, with explicit required-carrier precedence. Add .build alone: fixes this example but leaves custom generated trees. Raise limits: spends longer scanning irrelevant content. Blindly honor all ignores: can hide required agent/configuration surfaces. | Correct behavior at the shared boundary with bounded work | Alternatives and weaknesses stated with the selected approach |

## Risks

| Risk | Mitigation |
| --- | --- |
| Ignore precedence could hide required instructions or Git subprocess work could replace filesystem cost; explicit carrier controls and one shared bounded work budget are required. | Verify the change's own public-path controls before delivery approval |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
