# Graph-Quality Evaluator's Git Probe Ends Its Process Tree

Change ID: `1za2x-debt graph-quality-probe-tree-kill-remeasure`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1za2y code-tool-and-index-status-fixes

## Rationale

Wave `1z8ox` routed every timed subprocess call through `subprocess_util.run_with_tree_kill` except `graph_quality_eval._git_value`, which runs `git rev-parse HEAD` and `git status --porcelain` for the report's `repository_identity` with a 30-second timeout and kills only the direct child on timeout. It was left because the shipped graph-quality reports pin the evaluator's source hash, so editing `graph_quality_eval.py` means re-measuring them. `tests/test_tree_kill_routing.py` records it as an exclusion to route at the next re-measure.

Re-measuring is cheap: `graph_quality_eval.py --corpus docs/evals/graph-quality-golden.json --report docs/reports/graph-quality-<label>.json --label <baseline|post> --root <repo>` builds a four-file golden corpus in a temporary directory in seconds, with no index or network, and its scored numbers are deterministic (a test re-runs the post report and compares them). The baseline report was produced by running the current evaluator against the graph production at commit `f6790333` in a scratch checkout; that commit is still in history. The change doc of 1z8ow in wave 1z8ox (`1z8ow-bug remaining-timed-calls-end-process-tree.md`) says the baseline "cannot be re-measured", which is wrong and is corrected here, and the Unreleased CHANGELOG bullet for wave 1z8ox says this call is left unrouted.

## Requirements

1. `graph_quality_eval._git_value` runs git through a `_run_tree_kill` resolver, lazily imported and falling back to `subprocess_util.isolated_run` when `run_with_tree_kill` is absent, as the other routed modules do. The baseline production's `subprocess_util` has no `run_with_tree_kill`, so the fallback is required.
2. Both shipped reports (`docs/reports/graph-quality-baseline.json` and `docs/reports/graph-quality-post.json`) are re-measured with the edited evaluator: post from the live scripts, baseline from the scripts at commit `f6790333` with the edited evaluator copied in, as the original baseline was produced. No report field is edited by hand.
3. The re-measured reports keep every measured field of the current ones: relations, totals, false-positive counts, `scored_relations`, `builder_versions`, `corpus.digest`, `graph_input_fingerprint`, `classification_controls` (including the baseline's `not_observed` list), `graph_bounds`, and the `production_identity` hashes other than `source_root` (for the post report, only where the live graph sources are unchanged since it was measured; see the Decision Log). Only the evaluator identity, timestamps, `repository_identity` (the commit becomes the current HEAD), environment and `report_digest` may change. Any other difference is a finding, not an accepted update.
4. The tree-kill census moves `graph_quality_eval._git_value` from the exclusions to the routed set.
5. The procedure used to re-measure each report, including which fields change, is recorded in `docs/architecture/testing-architecture.md` beside the graph fidelity corpus description, so the next re-measure is reproducible. The 1z8ow change doc's claim that the baseline cannot be re-measured is corrected with a dated note, and the Unreleased CHANGELOG bullet for wave 1z8ox no longer says this call is left unrouted.

## Scope

**Problem statement:** one timed git call still kills only its direct child, and the reason it was left is gone.

**In scope:**

- `graph_quality_eval._git_value`, both shipped reports, the census entry, the re-measure procedure in the testing architecture, and a correction note on the 1z8ow change doc.

**Out of scope:**

- Changing what the evaluator identity hashes, or moving the git probe to another module.
- Any change to scoring, the corpus, or the graph builders.

## Acceptance Criteria

- [x] AC-1: `_git_value` resolves the tree-kill helper at call time and falls back to `isolated_run`; a test confirms the call reaches `run_with_tree_kill` with the timeout (the helper's own tree-kill behaviour is already tested), and a test without `run_with_tree_kill` confirms the fallback.
- [x] AC-2: both reports carry the edited evaluator's `source_sha256`, and `ShippedReportPairTests` pass without a hand-edited field.
- [x] AC-3: every measured field listed in Requirement 3 equals the previous report's, for both reports.
- [x] AC-4: the tree-kill census lists `_git_value` as routed and has no exclusion for it.
- [x] AC-5: the testing architecture states the command, scratch setup and changing fields for each report; the 1z8ow change doc carries a dated correction; and the Unreleased CHANGELOG no longer says the call is left unrouted.
- [x] AC-6: the change's own suites and every test it adds pass, and the documents it edits validate.

## Tasks

- [x] Add the resolver and route `_git_value`.
- [x] Re-measure post from the live scripts; re-measure baseline from `git archive f6790333` scripts plus the edited evaluator in a scratch directory.
- [x] Compare scored fields with the previous reports.
- [x] Update the census, the testing architecture, the 1z8ow correction note and the 1z8ox CHANGELOG bullet.
- [x] CHANGELOG Changed entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Route and re-measure | implementer | readiness | |
| Review | code, QA reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/graph_quality_eval.py`, `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`, `.wavefoundry/framework/scripts/tests/test_graph_quality_eval.py`
- `docs/reports/graph-quality-baseline.json`, `docs/reports/graph-quality-post.json`
- `docs/architecture/testing-architecture.md`

Root release note: CHANGELOG.md.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`: the re-measure procedure for the graph-quality reports.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The routing |
| AC-2 | required | Honest provenance |
| AC-3 | required | Routing must not change measurement |
| AC-4 | required | The census reflects the code |
| AC-5 | important | The next re-measure is reproducible |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | Implemented. `_run_tree_kill` resolver (lazy `subprocess_util` import, call-time `run_with_tree_kill` or `isolated_run`) routes `_git_value`; census moves it from EXCLUDED to ROUTED and adds `graph_quality_eval` to `RESOLVER_MODULES`; spy tests for the helper with `timeout=30` and for the fallback with an older `subprocess_util`. Re-measured last: post from the live scripts, baseline from `git archive f6790333` scripts plus the edited evaluator in scratch. Field diff against the previous reports: baseline changed only `evaluator_identity.source_sha256` (`a7d75bbd…` to `abe21dba…`), `production_identity.source_root`, `repository_identity.commit`, timestamps and `report_digest`; post changed the same fields plus `production_identity.graph_indexer_sha256` and `graph_query_sha256` (see the Decision Log). Every measured field in Requirement 3 is equal in both. The first post run passed a relative corpus path, which changed `corpus.path`; re-run with the absolute path the original used. Procedure recorded in `testing-architecture.md`; dated correction in the 1z8ow doc; 1z8ox CHANGELOG bullet amended | `test_graph_quality_eval` and `test_tree_kill_routing` 134 OK (7 skipped); scratch field diff |
| 2026-09-29 | Readiness review folded in: every measured field pinned in AC-3, routing tested by spy instead of a 30-second hang, CHANGELOG bullet correction, explicit 1z8ow/1z8ox wording. | readiness review |
| 2026-09-29 | Planned. The evaluator hash is `evaluator_identity().source_sha256`; both reports hold `a7d75bbd…`; commit `f6790333` resolves. | `graph_quality_eval.evaluator_identity`, `ShippedReportPairTests`, both reports |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | Post report takes the live graph-source hashes | Commits `3433fb03`, `8545c4f9` and `24513060` edited `graph_indexer.py` and `graph_query.py` after the post report was measured at `5a30d7a5`, so a post measured from the live scripts (Requirement 2) cannot keep those two hashes (Requirement 3). The post report describes the production that ships; every measured number is unchanged, and `test_the_shipped_post_report_still_matches_a_fresh_run` already requires that | Measure post from the `5a30d7a5` scripts (keeps the hashes, but the post report would no longer describe the shipped production) |
| 2026-09-29 | Route in place and re-measure both reports | Keeps both reports honest and the pair attributable for seconds of compute | Move the git probe to a helper module (still edits the hashed file, so still re-measures, and adds a module the baseline scratch setup must copy); hash only the scoring functions (changes what the identity means, needs a schema bump, and still re-measures once); re-stamp the hash by hand (records provenance the reports were not measured under; already rejected in 1z8ow) |

## Risks

| Risk | Mitigation |
| --- | --- |
| The baseline scratch setup differs from the original | Follow the recorded original setup; AC-3 catches any scoring difference |
| The re-measure changes provenance fields reviewers read as results | Only identity, timestamps, repository identity and digest may change; AC-3 pins the rest |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
