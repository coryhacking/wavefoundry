# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-16

wave-id: `1p61u graph-layer-map-quality`
Title: Graph Layer Map Quality

## Objective

Fix the graph/index-layer and map-area-selection defects three field tests (teton TS/Nx, javaagent Java) isolated behind the codebase map, so the map's entry-point lists AND area selection reflect real product code, not noise. `1p61v` fixes TS symbol-kind extraction (type members/garbage). `1p61w` consumes the generated signal + per-module floor + non-code hubs + label disambiguation. `1p64t` adds the vendored/third-party axis (`repo-profile.json` globs + `.gitattributes linguist-vendored`). `1p64u` surfaces product modules absorbed into large communities (package-structure floor) + config-area responsibility + same-path label collisions. When this wave closes, a cold-start agent is routed to the product, not to bundled/vendored/generated dependencies.

## Changes

Change ID: `1p61v-bug ts-symbol-kind-extraction-faithfulness`
Change Status: `implemented`

Change ID: `1p61w-enh graph-clustering-granularity-stability`
Change Status: `implemented`

Change ID: `1p64t-enh map-vendored-axis`
Change Status: `implemented`

Change ID: `1p64u-enh map-package-floor-and-labels`
Change Status: `implemented`

Change ID: `1p64x-ref merge-dashboard-server-files`
Change Status: `implemented`

Change ID: `1p651-enh seed-vendored-paths-instruction`
Change Status: `implemented`

Change ID: `1p654-bug dashboard-lifecycle-reconciliation`
Change Status: `implemented`

Completed At: 2026-06-17

## Wave Summary

Wave `1p61u graph-layer-map-quality` (Graph Layer Map Quality) delivered 7 changes: TS symbol-kind extraction faithfulness (no type-fields-as-function, no garbage symbols), Codebase map: generator area-selection & labeling (generated/vendored noise, per-module floor, labels), Codebase map: vendored / third-party axis (javaagent 1b), Codebase map: package-structure area floor + label fixes, Merge the two dashboard-server files into one (lock holds startup info), Seed instruction: populate repo-profile.json vendored_paths (makes 1p64t usable), and Dashboard lifecycle: reconcile against real processes (orphans, port climb, dead-PID). Notable adjustments during implementation: TS symbol-kind extraction faithfulness (no type-fields-as-function, no garbage symbols): Adversarial faithfulness review caught an over-reach: the name guard's plain-identifier rule would drop legitimate non-identifier symbol names in other languages (C++ `operator==`, Rust operators, Ruby `valid?`/`save!`/`<=>`). Scoped the guard to TS/JS (where the `function`/`/` artifact originates). No real callable dropped.; Codebase map: generator area-selection & labeling (generated/vendored noise, per-module floor, labels): javaagent field test: vendored/generated EL dominates area selection (~13/24 areas; 99%-generated parser as area #3); product modules crowded out (shopizer absent); label collisions (5×parser/4×javax). Re-scoped this change to generator area-selection. Confirmed `generated_node_fraction` is persisted per community (27/27 in the project artifact) — 1a is generator-only, no cluster bump.; Dashboard lifecycle: reconcile against real processes (orphans, port climb, dead-PID): Delivery-review follow-up RESOLVED: relocated the cmdline scan to the shared `dashboard_lib.dashboard_cmdline_pids` (server_impl now delegates) and hardened `upgrade_wavefoundry._detect_dashboard` to cmdline-verify the recorded PID (was a bare `os.kill`, same recycled/zombie-PID class). Also added a direct parse/match test for the kill-decision logic (this-root-only, self/other-root/non-dashboard exclusion, `--root=`, None-on-failure). +5 tests; full suite 3274 green.

**Changes delivered:**

- **TS symbol-kind extraction faithfulness (no type-fields-as-function, no garbage symbols)** (`1p61v-bug ts-symbol-kind-extraction-faithfulness`) — 4 ACs completed. Key decisions: --------; Scope TS/JS only; separate from clustering work.
- **Codebase map: generator area-selection & labeling (generated/vendored noise, per-module floor, labels)** (`1p61w-enh graph-clustering-granularity-stability`) — 4 ACs completed. Key decisions: --------; Bundle granularity + contamination + stability into one change.
- **Codebase map: vendored / third-party axis (javaagent 1b)** (`1p64t-enh map-vendored-axis`) — 3 ACs completed. Key decisions: --------; Generator-only vendored axis (read signals at map time), not a graph-layer `vendored` tag.
- **Codebase map: package-structure area floor + label fixes** (`1p64u-enh map-package-floor-and-labels`) — 3 ACs completed. Key decisions: --------; Form areas by per-member representative directory (significant-dir floor), not the community's single dominant dir.
- **Merge the two dashboard-server files into one (lock holds startup info)** (`1p64x-ref merge-dashboard-server-files`) — 3 ACs completed. Key decisions: --------; The lock file carries the metadata; metadata write stays an in-place truncate-write.
- **Seed instruction: populate repo-profile.json vendored_paths (makes 1p64t usable)** (`1p651-enh seed-vendored-paths-instruction`) — 2 ACs completed. Key decisions: --------; Instruct the agent to populate `vendored_paths` (seed-030) rather than auto-detect vendor dirs in code.
- **Dashboard lifecycle: reconcile against real processes (orphans, port climb, dead-PID)** (`1p654-bug dashboard-lifecycle-reconciliation`) — 4 ACs completed. Key decisions: --------; Reconcile via a dependency-free `ps` cmdline scan, not `psutil`.
## Journal Watchpoints

- Sequencing: implement `1p61v` first (high-confidence, independently shippable extraction fix; ships the trust win), then `1p61w` (fuzzier clustering tuning that needs an investigation phase before tuning).
- `1p61v` bumps `GRAPH_BUILDER_VERSION` (30→31). `1p61w` was re-scoped to generator area-selection and does NOT bump `CLUSTER_BUILDER_VERSION` (it consumes the already-persisted `generated_node_fraction` signal). Both required `framework_edit_allowed`.
- Follow-up: both need validation against the multilang test pack + the teton TS consumer as real-world oracle; an extraction-faithfulness review is required before closing `1p61v` (no real callables dropped), and an anti-over-merge check before closing `1p61w` (distinct subsystems not merged).
- Blocking: `1p5x8` currently holds the single OPEN slot — keep `1p61u` PLANNED until `1p5x8` closes (or is paused) before activating. (Resolved: `1p5x8` closed 2026-06-16; `1p61u` activated.)
- Scope (operator-directed, post-prepare): `1p64t` (vendored axis) + `1p64u` (package-floor + labels) were admitted mid-implementation on 2026-06-17 after javaagent/teton p64p re-evals showed area-selection is the dominant remaining defect. Both are generator-only (`gen_codebase_map.py`), no version bumps. The prepare-council reviewed `1p61v`/`1p61w`; the delivery-council must cover all four. Not silent scope creep — operator-directed additions to meet the wave's goal (map reflects product, not noise).
- Scope (operator-directed, UNRELATED): `1p64x` (merge the two dashboard-server sidecars into one — the lock file holds the startup metadata) was admitted 2026-06-17 at explicit operator request, acknowledged as off-theme for the codebase-map work but done now. Touches `dashboard_lib`/`server_impl`/`upgrade_wavefoundry`/`indexer` + tests; no version bumps. Delivery-council should note it as a standalone refactor (lock-integrity is the load-bearing concern — in-place write, no rename).
- Scope (operator-directed, UNRELATED): `1p654` (dashboard lifecycle reconciliation — cmdline scan so start/stop/restart converge to one instance; kills orphans; zombie/recycled-PID-safe liveness) was admitted 2026-06-17 at explicit operator request after a javaagent field report + a live repro (3 orphan dashboards accumulated on the self-host). `server_impl.py` dashboard lifecycle + tests; no version bumps; POSIX `ps` scan (Windows falls back to current behavior). Same dashboard surface as `1p64x`. Delivery-council: lock-integrity + faithful process matching (never kills another repo's dashboard) are the load-bearing concerns. NOTE: a pre-existing, unrelated test flake (`test_get_reranker_does_not_cache_none_on_failure`, env-dependent accel_embedder path) is not a regression — see memory `project-reranker-test-env-flake`.

## Review Evidence

- wave-council-readiness: READY — prepare-council passed 2026-06-16 (seats: architecture-reviewer, reality-checker, qa-reviewer, security-reviewer, red-team, docs-contract-reviewer). Two changes correctly split by version constant: `1p61v` (node shape, `GRAPH_BUILDER_VERSION`) fixes TS type-members-tagged-`function` + garbage symbol nodes; `1p61w` (community shape, `CLUSTER_BUILDER_VERSION`) tunes clustering granularity/contamination/stability. Core assumption (defect is in extraction, not the already-faithful map generator) is well-evidenced: `code_outline` returns zero symbols on a pure-type file while the graph surfaces its `: string` fields as function nodes. Faithfulness-gated (no real callables dropped — a graph fail-open) with an adversarial extraction review before close; no new network/file surface. Strongest alternative — fix `_kind_tag` defensively in the map — rejected because the graph is wrong for all consumers (`code_references`/`code_callhierarchy`), so the fix belongs at extraction. Strongest challenge — the `1p61v`↔`1p61w` node-inclusion interaction (re-kinded type members changing clustering inputs) — answered by a carried condition. Conditions carried into implement, not blockers: (1) pin the exact extraction site + the node-types producing garbage before editing; (2) run the TS fixtures under a venv with the TS grammar present and add a type-declaration fixture to the multilang pack (no vacuous gate); (3) verify clustering node-inclusion accounts for `1p61v`'s re-kinded type members (likely exclude non-callable type members from community formation, as constant nodes already are). Sequencing `1p61v` -> `1p61w` confirmed.
- wave-council-delivery: approved (PASS) — delivery-council 2026-06-17 over all 7 implemented changes (seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer). Map side (`1p61v`/`1p61w`/`1p64t`/`1p64u`/`1p651`) field-validated A− on javaagent + the p64p wins confirmed on teton; dashboard side (`1p64x`/`1p654`) suite-verified + orphan cleanup confirmed live. Faithfulness gates satisfied: `1p61v` drops no real callable (method sigs stay `function`; name guard TS/JS-gated so C++/Rust/Ruby operator names survive); `1p654` matches only a `dashboard_server.py` whose `--root` resolves to this exact root (never another repo's dashboard); `1p64x` preserves lock integrity (in-place truncate, no rename). One IN-SESSION FIX from the review: `_dashboard_cmdline_pids` parse/match (the kill-decision logic) was only ever mocked — added a direct test (this-root-only match, self/other-root/non-dashboard exclusion, `--root=` form, None-on-failure). One follow-up RESOLVED post-review (operator-directed): the cmdline scan was relocated to the shared `dashboard_lib.dashboard_cmdline_pids` and `upgrade_wavefoundry._detect_dashboard` now cmdline-verifies the recorded PID too (was a bare `os.kill`) — so the hardened liveness is consistent across start/stop/restart AND upgrade detection (+ a direct test for the kill-decision parse logic). Full suite 3274 green. Accepted/known: Swift/other-lang type-aliases still mislabel (`1p61v` TS-scoped); `1p64u` buried-module node double-count (orientation-acceptable); shopizer/ofbiz below the file floor. Full suite green (3271); docs-lint clean. An unrelated pre-existing test flake (`test_get_reranker_does_not_cache_none_on_failure`, env-dependent accel_embedder path) is not a regression — see memory `project-reranker-test-env-flake`.
- operator-signoff: approved — operator directed close of 1p61u on 2026-06-17 after round-3 validation confirmed rounds 1–2 landed on teton + javaagent (type fields, garbage node, name↔Responsibility, config detection, vendored_paths all confirmed); round-3 polish items (#1 key-files vendored filter, #2 clustering cohesion, #3 config-area name, #4 typings collapse, #5 structural-leaf naming) routed to a focused follow-up wave.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: security-reviewer; strongest-challenge: the `1p61v`->`1p61w` node-inclusion interaction — re-kinding TS type members away from `function` changes the nodes clustering forms communities over, and the cluster builder currently special-cases only constant nodes, so non-callable type members could pollute communities or undermine the granularity fix; answered by a carried implement condition to verify clustering node-inclusion handles `1p61v`'s re-kinded members; strongest-alternative: fix `_kind_tag` defensively in the map generator to treat `function` nodes from `.types.ts` as non-callable — rejected because the graph is wrong for ALL consumers (`code_references`/`code_callhierarchy` would still mis-report type fields as callable), so the fix belongs at extraction; conditions carried into implement (non-blocking): (1) pin the exact extraction site + the node-types producing garbage symbols before editing; (2) run TS fixtures under a venv with the TS grammar present + add a type-declaration fixture to the multilang pack so the gate isn't vacuous; (3) verify clustering node-inclusion accounts for `1p61v`'s re-kinded type members; sequencing `1p61v` -> `1p61w` confirmed; faithfulness-gated with an adversarial extraction review before close; no new network/file surface)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-16: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: security-reviewer; covered the original `1p61v`/`1p61w`; conditions carried into implement, all met — extraction site pinned, TS fixtures under venv, clustering node-inclusion verified.)

- **Delivery-phase Wave Council [delivery-council] — 2026-06-17: PASS WITH IN-SESSION FIX** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, security-reviewer, architecture-reviewer, docs-contract-reviewer; scope: all 7 implemented changes incl. the operator-directed `1p64x`/`1p654`/`1p651` additions; strongest-finding: `_dashboard_cmdline_pids` — the which-process-to-kill logic — was only ever mocked → added a direct parse/match test (this-root-only, self/other-root/non-dashboard exclusion, `--root=` form, None-on-failure) IN SESSION; follow-up RESOLVED post-review: cmdline scan relocated to shared `dashboard_lib.dashboard_cmdline_pids` + `upgrade_wavefoundry._detect_dashboard` hardened to cmdline-verify the PID (consistent liveness across lifecycle + upgrade) + direct parse-logic test; faithfulness verified: no callable dropped (`1p61v`), never kills another repo's dashboard (`1p654`), lock integrity preserved (`1p64x`); field-validated A− on javaagent + teton (map); full suite 3271 green; docs-lint clean; accepted-known: Swift type-alias TS-scope, `1p64u` node double-count, shopizer/ofbiz below floor.)

## Dependencies

- No external wave dependencies.
