# Terminology Label Contract For The Dashboard

Change ID: `1yk1m-enh terminology-label-contract`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-21
Wave: `1ym4h waveforge-merge-prep`

## Rationale

`docs/workflow-config.json` carries a `dashboard.terminology` block (`{"wave": "wave", "change": "change", "task": "task"}`). The Waveforge fork independently extended the same key with its own tier names (`feature`, `set`, `wave`, `task`), and the fork audit (`docs/reports/waveforge-fork-audit.md`, "New finding: a mostly-unused configuration seam") recorded that the two sides key the map by different vocabularies: Waveforge's `wave` is Wavefoundry's `change`, and its `set` is Wavefoundry's `wave`. A label map read by Wavefoundry code under Wavefoundry tier names would render Waveforge's values against the wrong tier. The audit left this unscoped pending an operator decision; the operator chose to plan it before the merge.

The census for this plan established that the key is a dead seam today. The only reader is `dashboard_lib.read_dashboard_config`, which guards the value to a dict and returns it; `dashboard_lib.collect_dashboard_snapshot` copies exactly three keys (`poll_interval_ms`, `entrypoint`, `terminology`) into the payload's `config` object. Nothing in `dashboard.js` reads `config` at all, and nothing in `server_impl.py`, the renderers, docs-lint, the seeds or the upgrade materializers reads the key. `docs/references/dashboard-adapter-model.md` (Terminology Register) states that the dashboard JavaScript reads terminology and substitutes labels throughout and that the frontend pluralizer appends `s`; both statements are false against the tree (`dashboard.js` defines `p(n, singular, plural)` with an explicit plural argument). `docs/references/dashboard-install-upgrade.md` attributes seeding and backfill of the `dashboard` block to seeds 010 and 160; no seed or install template materializes the block. No test covers the key.

Because the key already sits under `dashboard`, its contract is a dashboard label register, not a framework-wide vocabulary. The framework's own wave, change and task nouns appear in hundreds of Python and JavaScript string literals across the server, lint and dashboard, and in seed-rendered prose; relabeling all of those is a rename project the audit deliberately placed outside configuration. This change fixes the contract, makes the one live consumer honor it, makes a wrong-vocabulary map detectable, and corrects the documentation, so that Waveforge's merge is a one-time key remap rather than silently mislabeled cards.

## Requirements

1. The contract SHALL be stated once, in `docs/references/dashboard-adapter-model.md` (Terminology Register): the keys of `dashboard.terminology` are Wavefoundry's own tier names `wave`, `change` and `task`; the values are display labels in singular form. The helper lowercases a value for running text and capitalizes its first letter for headings and titles, so a fork's capitalized values (`"Set"`, `"Wave"`) render correctly without a casing rule in the config. The plural is formed by appending `s`; irregular plurals remain unsupported and the limitation is stated. The doc also names the `config.terminology_ignored` payload field and the advisory it drives, and gives the Waveforge remap (`set` to `wave`, `wave` to `change`; `feature` has no Wavefoundry tier and is reported as ignored). The advisory reports unsupported keys but cannot disambiguate the valid overlapping `wave` key; correct tier labels require the downstream remap. Applied unremapped, a Waveforge map labels Wavefoundry's wave tier with Waveforge's `wave` value (their change-tier label) and its change tier with the default `change`, while the advisory reports only `feature` and `set`; the pill signals that a remap is pending, not which tier is wrong. Whether Waveforge's own dashboard reads the key is unknown from the audit and is recorded as a merge-time check.
2. `dashboard_lib.read_dashboard_config` SHALL normalize the block: keep only the three known keys whose values are non-empty strings, fill missing keys with the tier name, and record every dropped key or non-string value as a sorted list under `terminology_ignored`. `dashboard_lib.collect_dashboard_snapshot` SHALL add `terminology_ignored` explicitly to the payload's `config` object (the snapshot copies named keys, so the field must be named there). Normalization never raises and never changes any other config field; the three server-side callers of `read_dashboard_config` read named keys only and are unaffected.
3. `dashboard.js` SHALL keep a module-level label register that `App` updates from `snapshot.config.terminology` on every snapshot, and a helper (singular, plural, capitalized forms) that reads it. `FRAMEWORK_FLOW` is a module-level constant evaluated before any fetch, so its `title` and `flow` entries SHALL become a function of the register (or be rebuilt on register update); the implementer states which. The surfaces routed through the helper, by symbol: `FRAMEWORK_FLOW[*].title` and `.flow` entries; the `FrameworkFlow` heading (`"Wave lifecycle"`); the `ProgressCard` rows (`"Waves"`, `"Changes"`, `"ACs"`, `"Tasks"`) and the `WaveTasks` sparkline label (`"Tasks"`); the `WavesCard` heading, empty state and closed summary; every dialog title that carries a tier noun (`WavesDialog`, `ChangesDialog`); the `Metrics` labels and every `p()` call whose string arguments are tier nouns (`OpenWaveCard`, `PendingWaveRow`, `App` pending-changes summary); the `WaveChangeList` section label; and the `ChangesTable` title and its `th` headers. Derived aria-labels (`Open ${process.title}`, `${process.title} internal flow`) follow the display label; the literal aria-labels `"Waves"` and `"Wave Framework process flow"` also follow the display label, since the framework name is the product and the tier noun is the label. CSS class names, `variant` keys (`"waves"`, `"changes"`, `"tasks"`), and URL query keys (`type=wave`, `&wave=`) SHALL NOT change. The `FRAMEWORK_FLOW[*].body` explanatory paragraphs and `"Recent changes"` (the git activity panel, not the change tier) stay literal.
4. When `config.terminology_ignored` is non-empty, `Dashboard` SHALL render, inside its existing `hero-meta` row beside `GitPills`, a hook-free `TerminologyAdvisoryPill({ ignored })` component that returns `null` for an empty or absent list and one `meta-pill` naming the sorted keys otherwise, so a wrong-vocabulary map is visible on the page rather than silent. `Dashboard` itself uses hooks, routing and storage and cannot be rendered honestly as a test slice; `GitPills` is the hook-free precedent. No new panel, setting or gate.
5. Tests SHALL cover, in the default suite with no skip: normalization through the real `read_dashboard_config` for known keys, unknown keys, non-string values, an absent block and a non-dict block, asserting both `terminology` and `terminology_ignored`; the payload field through the real `collect_dashboard_snapshot` on a temp root, for the sprint/story map, the absent block and the Waveforge-shaped map (`feature` and `set` reported, sorted); a source-level census over the shipped `dashboard.js` (read through the existing `SCRIPTS_ROOT.parent / "dashboard" / "dashboard.js"` path) whose predicate is a string literal containing a capitalized `Wave`, `Change` or `Task` with optional `s`, any `p()` call whose string arguments are tier nouns, and any literal containing a space and a lowercase tier noun; identifiers without spaces are excluded by construction; every remaining hit must either reference the helper or appear in an allowlist keyed by exact literal with a stated reason (the `FRAMEWORK_FLOW[*].body` paragraphs and `"Recent changes"`), following the `test_record_layout_census.py` shape with its stale-allowlist check; and a polarity self-mutant that appends one literal `"Prepare Wave"` to the source in memory and asserts exactly one new hit. Node-gated (skip when `node` is absent) tests following the existing `vm` slice pattern render the helper with the `FrameworkFlow` table, the `ProgressRow` callers and the `WavesCard` heading under both registers and assert the rendered text; under the default register the text must equal a pinned list of today's literals. Extend these render slices by rendering `TerminologyAdvisoryPill` through the same `vm` slice: `["feature", "set"]` yields exactly one pill whose text names both keys; `[]` and `undefined` yield no node. A separate structural assertion checks that `Dashboard`'s `hero-meta` block calls `TerminologyAdvisoryPill` and passes `terminology_ignored`; that wiring check is the one place this plan accepts source evidence. An identifier occurrence count is not behavioral evidence for this requirement.
6. `docs/references/dashboard-adapter-model.md` and `docs/references/dashboard-install-upgrade.md` SHALL describe the behavior that ships. In the install-upgrade doc the sentences in the Install (seed-010) and Upgrade (seed-160) sections attributing dashboard-block seeding or backfill to a seed SHALL be corrected or removed. No seed materializes the `dashboard` block today and this change does not add one. The adapter-model doc carries a renderer-owned review-policy carrier region; the Terminology Register edit sits outside it and the region is not touched.

## Scope

**Problem statement:** the `dashboard.terminology` key has an undefined vocabulary, no consumer and false documentation, and Waveforge's merge would carry a map keyed by the wrong tier names.

**In scope:**

- The contract text, payload-field description and Waveforge remap note.
- Normalization in `read_dashboard_config` and the `terminology_ignored` field in `collect_dashboard_snapshot`.
- The label register and helper in `dashboard.js`, the listed surfaces, and the advisory pill.
- Tests: normalization, payload, the literal census with its self-mutant, the advisory render checks, and node-gated render slices.
- Correcting the two reference docs.
- A CHANGELOG Unreleased bullet.

**Out of scope:**

- Relabeling server envelopes, `wf_help` text, docs-lint messages, prompt prose or any seed-rendered surface. These are Python and seed literals, not configuration; the audit assigns the renamed wave and change primitives to manual rename work at merge time.
- Seed materialization or upgrade backfill of the `dashboard` block.
- Irregular plurals, per-locale casing, or a plural override shape.
- The `terminology` stoplist entry in `graph_indexer.py`, which is a keyword-edge exclusion unrelated to this key.
- Waveforge's own remap edit, which happens in their tree at merge time.
- A whole-page browser test; the only Chrome test in the suite is opt-in behind `WAVEFOUNDRY_BROWSER_TESTS=1` and renders the design-system script, not `dashboard.js`. A headless screenshot may be attached as review evidence but is not a gate.

## Acceptance Criteria

- [x] AC-1: Under the sprint/story register the helper-driven components render sprint and story labels in the node-gated slice tests, and under the default register their rendered text equals the pinned list of today's literals; the Python snapshot tests prove the register reaches the payload for both configs.
- [x] AC-2: Unknown keys and non-string values are dropped, reported in `config.terminology_ignored` sorted, and wired to `TerminologyAdvisoryPill`; the render slice shows one pill naming `feature` and `set` for a Waveforge-shaped map and no node for an empty or absent list, and the structural check proves `Dashboard` passes the field to it. This exposes unsupported keys; it does not disambiguate the valid overlapping `wave` key or guarantee correct tier labels before the downstream remap.
- [x] AC-3: The literal census passes on the shipped `dashboard.js` with an allowlist that has no stale entries, and its polarity self-mutant reports exactly one new hit.
- [x] AC-4: The two reference docs state the shipped contract, the payload field, the Waveforge remap and the plural limitation, and no longer attribute the block to a seed; the two documents this change edits validate.
- [x] AC-5: The change's own suites and every test it adds pass, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write the contract, payload-field and remap paragraphs in the adapter-model doc; correct every seed-attribution sentence in the install-upgrade doc (four at readiness).
- [x] Implement normalization in `read_dashboard_config` and the field in `collect_dashboard_snapshot`; add the normalization and payload tests.
- [x] Add the register and helper to `dashboard.js`, route the listed surfaces through it, add the hook-free `TerminologyAdvisoryPill` beside `GitPills` in `hero-meta`; record any allowlisted literal with its reason.
- [x] Add the literal census with its self-mutant, the advisory render checks, and the node-gated render slices with the pinned default literal list.
- [x] Add the CHANGELOG bullet; run scoped checks and docs validation, then required delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| contract-and-docs | technical-writer | none | Fixes the doc contract first so the implementer codes to it. |
| dashboard-implementation | implementer | contract-and-docs | One owner for `dashboard_lib.py`, `dashboard.js` and their tests. |
| independent-review | required reviewers | dashboard-implementation | Fresh contexts; node slice output as AC-1 evidence. |

## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/references/dashboard-adapter-model.md`
- `docs/references/dashboard-install-upgrade.md`

## Affected Architecture Docs

`docs/references/dashboard-adapter-model.md` is the affected reference and is edited by this change; it is the only document describing the `/api/dashboard` payload, so no spec edit is needed. No architecture hub doc changes: the dashboard remains a read-only viewer of the same payload with one added field.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The key must have a consumer or the contract is prose. |
| AC-2 | required | Unsupported keys must be visible; overlapping valid keys still require the downstream remap. |
| AC-3 | required | Without a census the labels drift back to literals. |
| AC-4 | required | The current docs are false and are what a fork reads first. |
| AC-5 | required | Change-local correctness. |

## Progress Log

Observe: delivery code, QA and docs-contract judgments approved by an independent reviewer who implemented neither change; host thread limit required one shared review context, disclosed in `docs-delivery-review.md`. QA independently recomputed the full-suite receipt hash. All scoped ACs/tasks complete. Memory proposal produced zero candidates. AC scope gap check: downstream version invalidation and terminology remap remain explicitly assigned to the Waveforge merge; no additional work admitted.

Observe: full framework verification passed: `python3 .wavefoundry/framework/scripts/run_tests.py`, host execution, 9,468 tests across 119 files in 325.576s, 21 skipped, exit 0. Receipt `2026-09-21T19:10:31.635134+00:00`, input hash `8e2ce791dce8b17aa48677b5eb28f3e13ebad722eac6674f6985a40952f482da` matches fresh `_hash_inputs()`. Wave-specific independent probes had no skips. Final QA receipt reconciliation pending; no further source changes.

Readback: normalize dashboard labels, render all scoped tier labels and the hook-free TerminologyAdvisoryPill; unknown keys become visible but the downstream key remap remains necessary. AC-1 through AC-5 cover payload, rendered labels, census and docs. Before: sprint/story config has no visible effect; after: headings use configured labels and ignored keys appear in one pill. Thought: delegate dashboard code/tests while coordinator updates the two reference docs.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-21 | Planned from the fork audit's open recommendation after a census found the key has exactly one reader and no consumer. | `dashboard_lib.read_dashboard_config`; `dashboard.js` has zero reads of `config`; adapter-model doc Terminology Register. |
| 2026-09-21 | Readiness round: red-team and docs-contract council seats plus code and QA lanes. Two build-changing corrections folded in: the reader symbol was wrong (`read_dashboard_config`, not an invented name), and the census predicate and surface list were unstated; literal count in `dashboard.js` is 102 hits, about 44 visible labels, 16 prose sentences, 35 identifiers, 2 aria-labels, 5 URL keys. Also folded: `FRAMEWORK_FLOW` load-time evaluation, the `hero-meta` pill target, casing normalization in the helper, the opt-in browser test, node slice technique, three seed-attribution sentences, the carrier region risk, and the CHANGELOG bullet. | Readiness review in this wave directory; context `waveforge-merge-prep-readiness-20260921`. |
| 2026-09-21 | Implementation complete for dashboard labels: real config normalization and snapshot field, per-snapshot label register, dynamic lifecycle table (rebuilt at render, including selected dialog), all scoped label surfaces, and header advisory. Contract docs checked against shipped behavior. | `dashboard_lib.py`, `dashboard.js`; coordinator's two reference docs and CHANGELOG. AC-1 through AC-4 and first four tasks have evidence; final integration/review remains coordinator-owned. |
| 2026-09-21 | Scoped checks passed; literal census has six exact justified exceptions and no stale entries, and its appended Prepare Wave mutant reports exactly one new hit. Rendered default/custom/reset labels and advisory presence/absence pass. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_dashboard_terminology.py`: 6 passed; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p test_dashboard_server.py`: 215 tests passed, 1 existing opt-in browser skip (27.209s, host escalation for process identity/listener access). `node --check .wavefoundry/framework/dashboard/dashboard.js` and scoped `git diff --check` passed. |
| 2026-09-21 | Four meaningful in-memory render mutants rejected: ignore configured labels, hide the advisory, show an advisory for an empty list, and freeze lifecycle labels. No production mutant left behind. | Executed `test_dashboard_terminology.RENDER_SCRIPT` with Node against temporary mutated dashboard sources; all four exited nonzero. MCP-first targeted source reads succeeded; shell used for edits, literal extraction and tests. |

Operator-approved plan revision, 2026-09-21: replaced the advisory identifier-count pin with rendered presence/absence evidence and narrowed the vocabulary-detection claim. Earlier readiness evidence predates this revision; the wave was re-prepared against the revised plan (readiness-delta and currency contexts, 2026-09-21) before implementation.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-21 | Keys are Wavefoundry tier names; values are display labels. | The reader is Wavefoundry code and must not guess whose vocabulary a key is in; the fork remaps once at merge. | Keying by the fork's vocabulary breaks every other consumer; a bidirectional alias table is a registry nobody asked for. |
| 2026-09-21 | Scope is the dashboard label register only. | The key already lives under `dashboard`, and the framework's own nouns are hundreds of Python and seed literals the audit assigned to manual rename work. | Framework-wide dynamic labels would touch every envelope and prompt and change three-way merge behavior for no merge benefit. |
| 2026-09-21 | Unknown keys are dropped and reported, never an error. | Waveforge's config must load unchanged on merge day; the advisory tells them what to remap. | Failing lint on unknown keys would block their dashboard until the remap lands. |
| 2026-09-21 | Plural by appending `s`; casing normalized by the helper. | Matches what the doc promised; it is new helper behavior, since today's `p()` takes explicit plurals. Helper-side casing lets a fork's capitalized values work unchanged. | A plural override object adds a shape for a case no consumer has asked for; a config casing rule pushes the problem to the fork. |
| 2026-09-21 | Verify the advisory through rendered presence and absence, not identifier counts. | Operator accepted the review finding; a reference in unused code cannot prove visible behavior. The advisory does not resolve overlapping valid keys. | Static occurrence pin; rejected as insufficient. |
| 2026-09-21 | Census is the hard gate; node slices and screenshots are evidence. | The suite has no default-on JavaScript renderer; node tests skip without `node`, so the non-skipping census must stand alone. | Requiring a browser test would make AC-1 unprovable on most machines. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Substitution breaks a sentence that reads naturally only with the framework noun. | The `FRAMEWORK_FLOW[*].body` paragraphs stay literal by design and are allowlisted with a reason; any further exception is allowlisted the same way. |
| The dashboard has no JavaScript unit harness. | Python-side census over the source is the gate; node slice tests and an optional headless screenshot are evidence. |
| Waveforge's `feature` tier has no Wavefoundry home. | Reported as ignored by design; their feature-tier code is additive on their side per the audit. |
| The adapter-model doc carries a renderer-owned review-policy carrier region. | The Terminology Register edit is outside the region; the region is never touched and the renderer's convergence test would catch a stray edit. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
