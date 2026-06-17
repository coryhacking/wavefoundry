# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-17

wave-id: `1p66c codebase-map-round4`
Title: Codebase Map Round4

## Objective

Round-4 codebase-map fixes from teton field validation on `1.7.0+p664`. `1p66d` (generator + resource): per-area `AGENTS.md` resolution walks **up** to the nearest ancestor `AGENTS.md` so conventionally-placed project-root files (teton's 11) surface in both the map's `Area context:` link and the `wavefoundry://area/{id}` resource — and is robust to representative-path churn. `1p66e` (graph builder, headline): make code-graph **edge extraction reproducible** — identical input produced different edge counts (`75068` vs `74890`) because cross-file resolution outcomes depend on file/iteration order; fix the ordering + tie-breaks and emit an input-graph fingerprint to verify it, bumping `GRAPH_BUILDER_VERSION`. When this wave closes, per-area context links resolve for real-world placement and the map is reproducible across rebuilds (closing the root of round-3 `#3` and the typings/denominator churn).

## Changes

Change ID: `1p66d-bug area-agents-ancestor-walk-resolver`
Change Status: `implemented`

Change ID: `1p66e-bug graph-edge-extraction-determinism`
Change Status: `implemented`

Completed At: 2026-06-17

## Wave Summary

Wave `1p66c` (Codebase Map Round4) delivered two changes: Per-area AGENTS.md resolution walks up to the nearest ancestor (map link + area resource) and Code-graph edge extraction is nondeterministic on identical input.

**Changes delivered:**

- **Per-area AGENTS.md resolution walks up to the nearest ancestor (map link + area resource)** (`1p66d-bug area-agents-ancestor-walk-resolver`) — 5 ACs completed. Key decisions: --------; Resolve by walking up the directory tree to the nearest existing `AGENTS.md`, not by detecting an "owning project root" via `project.json`/`package.json`.
- **Code-graph edge extraction is nondeterministic on identical input** (`1p66e-bug graph-edge-extraction-determinism`) — 5 ACs completed. Key decisions: --------; Fix the input-graph (extraction) determinism, not the clusterer.
## Journal Watchpoints

- Both changes require `framework_edit_allowed`; `1p66d` also touches `server_impl.py` (resource) and possibly seeds (`seed_edit_allowed` only if a seed states the exact-rep-path rule — audit first).
- Sequencing: independent; `1p66d` is the smaller, lower-risk win and can land first. `1p66e` is the headline (determinism) and carries the version bump.
- `1p66e` bumps `GRAPH_BUILDER_VERSION` (edge-set shape stabilizes → consumer re-extract on upgrade); `1p66d` is no version bump.
- Faithfulness gate before close (`1p66e`): determinism hardening must NOT re-bind a wrong same-name twin, drop a previously-correct edge, or change unambiguous (`len==1`) resolutions — only stabilize ambiguous picks via an explicit documented tie-break. Adversarial faithfulness review per the graph symbol-resolution policy.
- `1p66e` was not locally reproducible in round 3 (teton's environment reproduces); the in-suite lock is a shuffle-invariance / double-run edge-set-identity test plus the emitted fingerprint for downstream confirmation.
- Key decision for prepare-council (`1p66d`): repo-root `AGENTS.md` excluded from the walk-up fallback for non-root areas (avoid linking the global guide from every area) — challenge the bound.
- Follow-up: validate downstream on teton (project-root AGENTS.md now linked + served; two identical rebuilds → identical fingerprint/edge set) and the multilang pack.

## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-17 (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; rotating: red-team). Both plans grounded in cited code (`_area_context_rel_path:1253`, `resource_area_context:17822`; resolution sites `7169/7199/7263/7279/7489`; `GRAPH_BUILDER_VERSION:28`). Strongest challenge: `1p66e` edge-count variance could be concurrency-driven candidate-set membership, not order — confirmed the resolution pass runs after all workers join over a complete symbol table (sorted artifacts at `7060`), so it is iteration-order, and the tie-break fix is in the right layer; implementer must not move resolution earlier (condition 1). Strongest alternative (fix clusterer only / cache first run) rejected — variance is upstream of clustering. Conditions carried into implement (non-blocking): (1) confirm complete-table post-join resolution before relying on tie-breaks; (2) prove the determinism test fails on pre-fix code (non-vacuous lock); (3) faithfulness no-regression — no `len==1` resolution changes, existing twin/loader/namespace/constant fixtures green, adversarial binding-faithfulness pass before close. `1p66d` repo-root-exclusion bound accepted (no regression). CHANGELOG entry deferred to delivery/release.
- wave-council-delivery: approved (PASS) — delivery-council 2026-06-17 over both changes (seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; rotating: docs-contract-reviewer). `1p66d`: single shared `_resolve_area_context_rel_path` consumed by both map link and resource; 8 resolver tests + resource walk-up test. `1p66e` binding-faithfulness gate passed — verified per-site that the three tie-breaks (`_pick_shorter_node_id` same-file collapse, smallest-FQN import collision, sorted rewrite-apply) change only genuinely-ambiguous/same-file choices, never a `len==1` outcome and never a wrong-FILE twin; external oracle = the existing adversarial `CrossFileResolutionTests` (per-language never-binds-wrong-twin / stays-external), all 38 pass unchanged. Non-vacuous determinism lock via `_pick_shorter_node_id` commutativity unit test (the pre-fix shorter-length rule kept first-seen on a length tie — order-dependent); fingerprint over sorted node/edge SET is membership-sensitive (the teton edge-count drift) not order-sensitive. Honest limitation logged: the small in-suite fixture was deterministic locally even pre-fix (round-3), so the integration tests are a regression lock, not a reproduction of teton's environment — the unit lock + emitted `input_fingerprint` are the real proof; teton validates downstream. Council condition 1 confirmed (resolution is a post-assembly second pass over sorted artifacts, `graph_indexer.py:7060`). Full suite 3297 green; docs-lint clean; only `1p66e` bumps `GRAPH_BUILDER_VERSION` (31→32). CHANGELOG entry deferred to the next release.
- operator-signoff: approved when operator confirms closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1p66e` edge-count variance on identical input could be concurrency-driven candidate-set membership rather than iteration order — confirmed resolution runs as a post-join second pass over a complete, sorted symbol table (`graph_indexer.py:7060`), so it is iteration-order and the deterministic-ordering + stable-tie-break fix is in the right layer; implementer must not move resolution earlier; strongest-alternative: fix the clusterer only / cache first-run results — rejected because edge-set variance is upstream of clustering and caching masks the bug; conditions carried into implement (non-blocking): (1) confirm complete-table post-join resolution before relying on tie-breaks; (2) prove the determinism test fails on pre-fix code so the regression lock is non-vacuous; (3) faithfulness no-regression — no `len==1` resolution changes, existing twin/loader/namespace/constant fixtures green, adversarial binding-faithfulness pass before close; `1p66d` repo-root-exclusion bound for non-root areas accepted as no-regression; CHANGELOG entry deferred to delivery/release)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-17: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; scope: both changes as delivered; substantive-finding: `1p66e` binding-faithfulness verified per-site — the three determinism tie-breaks change only same-file/degenerate-import-collision/identical-key-collapse choices, never a `len==1` resolution or a wrong-FILE twin; external oracle = existing adversarial `CrossFileResolutionTests`, all 38 green unchanged; honest limitation logged — the small in-suite fixture was deterministic locally even pre-fix (round-3), so integration tests are a regression lock not a reproduction of teton's environment, with the `_pick_shorter_node_id` commutativity unit test + emitted `input_fingerprint` as the real proof and teton as downstream validator; strongest-challenge: is the determinism lock vacuous? — no, the unit commutativity test fails on the pre-fix order-dependent rule; faithfulness gate, non-vacuous lock, and version bump (31→32) all satisfied; CHANGELOG entry deferred to next release; full suite 3297 green, docs-lint clean)

## Dependencies

- No external wave dependencies.
