# Incremental Secret-Scan Cache (SQLite, Tier-2-Ready)

Change ID: `1rsha-enh incremental-secret-scan-cache`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-11
Wave: `1rsh9 sqlite-index-substrate`

## Rationale

The secrets scanner runs during every project-layer index build (`indexer.py`) and is gated at `wave_close`. Its incremental mode scans only git-changed files and is already cheap — but its state is a single-field `scan-state.json` holding just `rules_hash`, and its one expensive event is unavoidable today: **any edit to the ruleset sets `rules_changed` and escalates to a full re-scan of every tracked file** (`scan_all = mode=="full" or rules_changed`). Ruleset edits therefore pay the whole-repo cost every time, and the scan has no memory that a file's exact content was already scanned clean under the exact same rules.

The graph subsystem solved the structurally identical problem in wave 1p9q3 with a per-file SQLite state store: content-fingerprinted, transactional, crash-safe, with fingerprint-gated skips and per-file deltas. Wave 1rsh9 now ships a general index-state store (`1rq4h`) that this scanner can share. This change moves secret-scan state onto that store as a per-file result cache.

Two tiers were considered (see Decision Log). This change ships **Tier 1** — the per-file content+rules cache — because the incremental path is already git-gated, so Tier 1's honest win is robustness, crash-safety, and decoupling from git, not a large speedup. The large speedup lives in **Tier 2** (rule-level delta scanning: on a ruleset change, run only added/modified rules and drop removed-rule findings with zero scanning), which carries a correctness-equivalence burden and a feasibility unknown about whether the betterleaks engine supports per-rule execution. Per operator direction, this change ships Tier 1 with a **Tier-2-ready model**: the schema persists a decomposed per-rule hash catalog and per-file scan provenance now, so moving to Tier 2 later is additive (new delta logic reading existing columns), not a schema migration or rewrite. A small non-committal feasibility spike records whether per-rule execution is viable, informing the later Tier-2 decision without shipping it here.

The load-bearing safety property: the cache is a skip optimization over the existing scanner, never a reinterpretation of it. A differential test proves the cached path yields findings identical to a full scan, and the derived-only rule from `1rq4h` applies — a missing or corrupt cache is a full re-scan, never a missed secret.

## Requirements

1. **Per-file scan cache on the `1rq4h` index-state store:** a table keyed by repo-relative path recording `content_hash`, the `rules_fingerprint` the file was last scanned under, `scanned_at`, a clean flag, and references to any findings produced. Writes are transactional (single transaction per scan pass) and crash-safe via the store's WAL posture. This supersedes the single-field `scan-state.json` as the working state; see Requirement 8 for the compatibility path.
2. **Fingerprint-gated skip (Tier 1 correctness):** a file is skipped only when its current `content_hash` **and** the current `rules_fingerprint` both match its cached row. Any mismatch re-scans the file with the full ruleset exactly as today. `content_hash` is content-addressed (not mtime/git-status), so the skip set is precise across branch switches, whitespace-only touches, and touch-and-revert.
3. **Rules-change behavior unchanged in Tier 1, but instrumented:** a ruleset change still re-scans affected files (every cached `rules_fingerprint` mismatches), preserving today's correctness. The scan output records how many files were skipped vs scanned and whether a rules change forced the escalation, so the cost of the full-rescan event is measurable ahead of any Tier 2 work.
4. **Tier-2-ready schema (no Tier-2 execution in this change):** persist a decomposed **per-rule hash catalog** (`rule_id -> rule_hash`) computed from the ruleset, and record each file's scan provenance against that catalog version. Tier 1 uses only the aggregate `rules_fingerprint` for skip decisions; the per-rule catalog is stored so a future Tier 2 can compute the added/removed/modified rule delta with no schema migration. Storing the catalog must not require per-rule execution — it is derived from parsing/hashing the ruleset.
5. **Feasibility spike (recorded, non-committal):** determine whether the betterleaks ruleset/engine supports running an individual rule (or an arbitrary subset) against a file while preserving the scanner's phase-2 exception/allowlist semantics. Record findings — viable / partially viable / not viable, with the blocking detail — in this change doc's Progress Log. This spike gates a **future** Tier 2 change; it does not ship delta scanning here.
6. **Differential equivalence safety net:** a test proves that a build using the cache produces exactly the same findings (same paths, same rule attributions, same count) as a `mode=full` scan with no cache, across add/modify/delete/rename/revert and rules-change fixtures. Any divergence fails the build; the cache never suppresses a finding a full scan would report.
7. **Derived-only and self-healing:** the cache lives under the store's derived-only rule — a missing, corrupt, or schema-mismatched cache degrades to a full scan with a loud diagnostic, never a silent skip and never a missed secret. Cache absence is a normal cold-start state, not an error.
8. **`scan-state.json` compatibility:** the `rules_hash` semantics other code relies on are preserved. Either keep writing `scan-state.json` as an exported snapshot (mirroring the `meta.json` pattern in `1rrr0`) or migrate its sole reader, whichever is lower-risk; record the choice in the Decision Log. No consumer of the current `rules_hash` field breaks.
9. **Findings contract unchanged:** `docs/scan-findings.json` remains the findings record with its existing statuses and shape; the `wave_close` secrets gate (`_check_secrets_gate`) and the build-time scan invocation are behaviorally unchanged except for which files are actually scanned.
10. **Local-only and portable:** no network, stdlib `sqlite3` only, no loadable extensions; Windows posture follows the store's (WAL, busy_timeout, UTF-8, no console-window regressions). Parallel-scan thresholds and worker sizing are unchanged.

## Scope

**Problem statement:** Secret-scan state is a single-field JSON with no per-file memory, so a ruleset change re-scans the entire repo and content-identical files are re-scanned whenever git reports them changed. The `1rq4h` store makes a per-file, crash-safe, content-addressed cache cheap — and lets the schema be shaped so the larger rules-delta win is a later additive step.

**In scope:**

- Per-file scan-result cache table on the `1rq4h` store; transactional writes; content+rules fingerprint skip.
- Decomposed per-rule hash catalog + per-file provenance persisted for Tier-2 readiness (storage only, no delta execution).
- Instrumentation of skipped-vs-scanned counts and rules-change escalation.
- Feasibility spike on per-rule execution, findings recorded.
- Differential equivalence harness (cache vs full-scan) and derived-only self-heal.
- `scan-state.json` compatibility (snapshot or reader migration).
- Tests: skip correctness, content-addressing across git-noise cases, rules-change re-scan, corruption self-heal, findings-contract non-regression, differential equivalence.

**Out of scope:**

- **Tier 2 rule-delta scanning** (running only changed rules; dropping removed-rule findings without scanning) — deferred to a future change, gated by the Requirement 5 spike. This change only makes it reachable.
- Changing the betterleaks ruleset, detection rules, or finding semantics.
- The `wave_close` secrets gate logic or `scan-findings.json` schema.
- The store substrate itself (owned by `1rq4h`) and FTS/bookkeeping (owned by `1rrr0`).
- Any change to which files are *eligible* for scanning (`get_scan_files` selection policy) beyond the content-addressed skip.

## Acceptance Criteria

- [x] AC-1: Secret-scan state persists as a per-file table on the `1rq4h` store with `content_hash`, `rules_fingerprint`, `scanned_at`, clean flag, and finding refs; writes occur in a single transaction per scan pass and survive an interrupted build (crash-window fixture leaves the store consistent or triggers a clean full re-scan). — `secret_scan_cache` table (schema v3) + `secret_scan_record` single transaction; `SkipCorrectnessTests::test_cache_row_shape_and_finding_refs` / `test_interrupted_write_leaves_consistent_store` (mid-transaction crash rolls back atomically).
- [x] AC-2: A file whose `content_hash` and `rules_fingerprint` both match its cached row is skipped; any mismatch re-scans it; a content-identical file that git reports as changed (branch switch / whitespace / touch-revert fixtures) is correctly skipped. — `secret_scan_filter` content+rules gate; `SkipCorrectnessTests` (match-skip, content-change, rules-change, touch-and-revert, unreadable-never-skipped).
- [x] AC-3: A ruleset change re-scans affected files and the scan output reports skipped-vs-scanned counts and the rules-change escalation flag. — `files_skipped`/`files_scanned`/`rules_change_escalation` in the `update_secrets_scan` summary, saved scan-state, and `run_secrets_scan.py` output JSON; `InstrumentationAndCompatTests`.
- [x] AC-4: The per-rule hash catalog and per-file provenance are persisted from ruleset parsing (no per-rule execution required); a fixture shows the stored delta inputs are sufficient to identify added/removed/modified rules between two ruleset versions, with Tier-2 execution explicitly not performed. — `secret_rule_catalog` table + `_rule_catalog` (parse/hash via `load_merged_ruleset`, honoring merge/disable semantics); `RuleCatalogTests::test_stored_catalog_identifies_rule_deltas_between_versions` (added + modified + removed identified between v1/v2 catalogs).
- [x] AC-5: The feasibility spike result (viable / partially / not viable + blocking detail) is recorded in the Progress Log; no delta-execution code ships in this change. — recorded 2026-07-10 (verdict: partially viable); zero delta-execution code shipped.
- [x] AC-6: A differential test proves cache-path findings are identical to a no-cache `mode=full` scan across add/modify/delete/rename/revert and rules-change fixtures; divergence fails. — `DifferentialEquivalenceTests::test_equivalence_across_the_fixture_matrix` runs the REAL scanner over a git fixture repo through all six mutations, comparing normalized findings after every step; plus `test_cache_never_suppresses_a_finding_a_full_scan_reports`.
- [x] AC-7: A corrupt/missing/schema-mismatched cache degrades to a full scan with a loud diagnostic and never suppresses a finding; cache absence is a normal cold-start (no error). — fail-safe `secret_scan_filter` (unreadable store → all candidates scanned) + version-gate reset; `SelfHealTests` (absent, byte-corrupt, schema-mismatch fixtures).
- [x] AC-8: `scan-state.json` `rules_hash` consumers are unbroken (snapshot or migrated reader per the Decision Log), and `scan-findings.json` plus the `wave_close` secrets gate are behaviorally unchanged except for the scanned-file set. — scan-state.json kept as the exported snapshot (Decision Log 2026-07-10) with `rules_hash` semantics intact; findings ledger and `_check_secrets_gate` untouched; `InstrumentationAndCompatTests::test_scan_state_json_rules_hash_contract_preserved`.
- [x] AC-9: Full framework tests run bytecode-free and docs validation passes. — full suite 4,809 tests OK bytecode-free (run_tests.py, 2026-07-10); `wave_validate` clean.

## Tasks

- [x] Add the per-file scan-cache schema (+ per-rule catalog + provenance) to the `1rq4h` store; bump the store schema version per convention. — `secret_scan_cache` + `secret_rule_catalog` tables; schema version bumped 2→3 (sequenced after 1rrr0's bump per the wave watchpoint).
- [x] Implement content_hash + rules_fingerprint skip in `run_secrets_scan.py` / `secrets_validators`, replacing the git-changed-only gate while keeping full-ruleset scanning for non-skipped files. — `secret_scan_filter`/`secret_scan_record` in the store module; `run_secrets_scan.py` incremental mode now takes ALL tracked files as candidates with the content-addressed skip deciding; `scan_secrets.update_secrets_scan` filters its changed-set through the cache; non-skipped files always scan with the full ruleset.
- [x] Persist the decomposed per-rule hash catalog and per-file provenance (parse/hash only). — `_rule_catalog` via `load_merged_ruleset` (merge/disable semantics honored); per-file provenance = the cache row's `rules_fingerprint` referencing the catalog version.
- [x] Add skipped-vs-scanned + escalation instrumentation to the scan output JSON. — `files_scanned`/`files_skipped`/`rules_change_escalation` in the build summary, saved scan-state, and the subprocess output JSON.
- [x] Run the per-rule-execution feasibility spike; record findings in the Progress Log. — recorded 2026-07-10: partially viable.
- [x] Build the differential equivalence harness (cache vs full-scan) across the fixture matrix. — `DifferentialEquivalenceTests` (real scanner, git fixture repo, add/modify/revert/rename/delete/rules-change).
- [x] Implement derived-only self-heal (corruption/version-mismatch → full scan + diagnostic). — fail-safe filter + version-gate reset; `SelfHealTests`.
- [x] Resolve `scan-state.json` compatibility (snapshot vs reader migration); record the decision. — kept as the exported snapshot (Decision Log 2026-07-10).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — full suite 4,809 tests OK bytecode-free (run_tests.py, 2026-07-10); `wave_validate` clean.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| cache-schema | implementer | — (store from 1rq4h) | Per-file table, per-rule catalog, provenance, version bump |
| skip-engine | implementer | cache-schema | Content+rules fingerprint skip, full-ruleset scan for misses |
| instrumentation | implementer | skip-engine | Skipped/scanned counts, escalation flag |
| feasibility-spike | qa-reviewer | cache-schema | Per-rule execution viability, recorded |
| equivalence-harness | qa-reviewer | skip-engine | Differential cache-vs-full fixtures |
| tests-docs | qa-reviewer | all implementation streams | Self-heal, compat, non-regression, validation |


## Serialization Points

- Hard dependency within the wave: `1rq4h` store substrate lands before this change adds its resident schema (same ordering as `1rrr0`).
- The differential equivalence harness (AC-6) must pass before the cached skip path replaces the current git-changed-only gate; until then the full scan is the fallback.
- The feasibility spike (AC-5) is informational and gates only a *future* Tier 2 change — it does not block this change's completion.
- Schema coordination with `1rrr0`: both add resident tables to the same store; their schema-version bumps must be sequenced, not concurrent, to avoid a version collision (coordinate in the shared wave).
- Maintenance is inherited, not re-implemented: the scan-cache tables (which have real delete churn on content changes and rules-change invalidation) rely on the shared-helper maintenance and `wave_index_optimize` coverage from `1rq4h` (Requirements 9–10); this change adds no separate vacuum/WAL handling.
- Integrity is inherited too: the scan-cache tables participate in the `1rq4h` integrity probe (Requirement 11) — structural `quick_check` plus source-fingerprint binding to `content_hash`/`rules_fingerprint` — so a corrupt or stale cache is detected and dropped to a full re-scan, reinforcing the fail-to-full-scan safety property (a bad cache never becomes a missed secret).

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — secret-scan cache in the build path; skip decision and self-heal flow.
- `docs/architecture/current-state.md` — scan cache as a resident schema on the index-state store.
- `docs/architecture/testing-architecture.md` — differential equivalence harness tier.
- ADR optional: Tier 1 cache with Tier-2-ready schema vs full rule-delta engine now (the Decision Log may suffice).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The per-file store schema is the substrate for every other behavior. |
| AC-2 | required | Content-addressed skip is the Tier 1 deliverable; false skips would miss secrets, false misses lose the win. |
| AC-3 | important | Instrumentation quantifies the rules-change cost but is not itself the optimization. |
| AC-4 | required | Tier-2 readiness is the explicit operator requirement; the schema must carry the delta inputs now. |
| AC-5 | important | The spike de-risks the future Tier 2 decision; it ships no behavior. |
| AC-6 | required | The equivalence net is the safety contract — a scan cache must never change what secrets are found. |
| AC-7 | required | Self-heal is what makes a cache safe: a bad cache must fail toward a full scan, never a missed secret. |
| AC-8 | required | Existing scan-state/findings/close-gate consumers must not break. |
| AC-9 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-05 | Drafted from operator direction to leverage the `1rq4h` SQLite store for incremental secret scanning as the graph did (1p9q3). Ships Tier 1 (per-file content+rules cache) with a Tier-2-ready schema (per-rule catalog + provenance persisted) so rule-delta scanning is a later additive step; feasibility spike recorded but non-committal. Admitted into wave 1rsh9 as its third change. | `run_secrets_scan.py` (single-field scan-state.json, rules-change full-rescan escalation); graph state store pattern (wave 1p9q3); `1rq4h` store substrate. |
| 2026-07-10 | Implemented Tier 1: cache schema (store v3), fail-safe filter/record, both entry points wired (`scan_secrets.update_secrets_scan` + `run_secrets_scan.py`), instrumentation, Tier-2 catalog, differential harness (19 tests in `test_secret_scan_cache.py`, all green). **Fixed a latent rules-hash bug found on the way:** both entry points hashed `.wavefoundry/scan-rules.toml` — a path that never exists (the framework ruleset lives at `.wavefoundry/framework/scan-rules.toml`, per `wave_lint_lib.constants.SCAN_RULES_FRAMEWORK_PATH`) — so a framework-rules change (e.g. via upgrade) silently missed the promised full-re-scan escalation. Corrected in both `_RULES_RELPATHS` (pinned by a cross-module test); one-time effect: the hash changes on upgrade → one full re-scan, which is exactly the correct behavior for a fingerprint that now actually covers the rules. | `_RULES_RELPATHS` in `scan_secrets.py`/`run_secrets_scan.py`; `InstrumentationAndCompatTests::test_rules_relpaths_cover_the_real_framework_ruleset`; 297KB framework ruleset previously outside the hash. |
| 2026-07-10 | **Feasibility spike (Req 5 / AC-5) — per-rule execution: PARTIALLY VIABLE.** (a) Mechanics: `check_hardcoded_secrets` loads the full merged ruleset internally (`load_merged_ruleset`) and exposes no rules-subset parameter — Tier 2 needs a small additive `rules_filter` argument (phase-1 matching already iterates rules independently, so subset execution is structurally safe; a filtered temp ruleset file is NOT an option because it would corrupt the rules-hash semantics). (b) Phase-2 semantics survive subsets: the global allowlist (paths/regexes/stopwords) is rule-independent and per-rule allowlists ride each rule dict, so running a subset preserves exception/allowlist behavior for the executed rules. (c) The blocking design question: REMOVED-rule disposal — dropping removed-rule findings with zero scanning means sweeping `scan-findings.json` entries by `rule_id`, which discards any false-positive confirmation history attached to them; a later re-added rule would need re-confirmation. Acceptable, but it must be an explicit Tier-2 decision, not incidental. No delta-execution code ships in this change. | `check_hardcoded_secrets` signature (root, scan_all, files, max_workers, as_of, record_only); `load_merged_ruleset` merge/disable flow; per-rule loop at `secrets_validators.py:1420`; finding entries carry `file` + rule attribution. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-05 | Ship Tier 1 (per-file content+rules cache) now on the `1rq4h` store, with a Tier-2-ready schema (decomposed per-rule catalog + per-file provenance persisted, delta execution deferred). | The incremental path is already git-gated, so Tier 1's honest win is robustness/crash-safety/git-decoupling; the large speedup is Tier 2 (rule delta), which carries an equivalence burden and a feasibility unknown. Storing the delta inputs now makes Tier 2 additive rather than a rewrite, matching the operator's "easily move toward Tier 2" direction. | **Tier 1 only, no Tier-2 schema:** weakness — a later Tier 2 would need a schema migration and re-derivation of per-rule state. **Full Tier 2 now:** weakness — commits to rule-delta correctness and per-rule execution before the feasibility spike, risking a scanner that finds fewer secrets than a full scan. **Do nothing:** weakness — leaves the whole-repo rules-change re-scan and git-coupled skip in place, and forgoes crash-safe state. |
| 2026-07-10 | `scan-state.json` kept as the exported snapshot (its `rules_hash` still written every pass); the cache supersedes it as the working skip state. | Lower-risk of the two Req-8 options: zero reader changes, the file is one small JSON, and the write already existed; migrating the sole reader buys nothing this change needs. | **Migrate the reader:** weakness — touches the escalation decision path for no functional gain. |
| 2026-07-10 | Incremental candidates: `run_secrets_scan.py` uses ALL tracked files with the content-addressed skip (git gate replaced — precise across branch switches/touch-revert, decoupled from git status; first post-ship scan is a one-time cold-cache full pass); the indexer build path keeps its precise changed-set as candidates and cache-filters within it. `--mode full` and rules/scanner-version escalations bypass the skip entirely and repopulate the cache. | The standalone scanner is where git-noise waste lived; the indexer already has exact change detection, so filtering within its changed-set adds robustness without re-hashing the repo every build. Full-mode bypass keeps an operator's explicit full scan a REAL full scan (cache-recovery escape hatch). | **Cache-filter full scans too:** weakness — an operator asking for a full scan after suspected cache trouble would silently get skips. **All-tracked candidates on the build path too:** weakness — hashes the whole repo on every post-edit hook build for marginal gain. |
| 2026-07-05 | Cache is a skip optimization over the unchanged scanner, protected by a differential equivalence harness and derived-only self-heal. | A secret scanner must never find fewer secrets because of a cache; the equivalence net + fail-to-full-scan on any cache problem make the optimization safe by construction. | **Trust the cache as source of truth:** weakness — a cache bug becomes a missed secret, the worst possible failure mode for this subsystem. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A cache defect suppresses a real secret finding | Differential equivalence harness (AC-6) on every build path; derived-only self-heal fails toward a full scan; cache never treated as authoritative over the scanner. |
| Tier-2-ready schema adds complexity that is never used | The per-rule catalog is cheap (parse+hash, no execution) and is also what powers the rules-change instrumentation; the feasibility spike decides whether Tier 2 is ever built, on evidence. |
| Schema-version collision with `1rrr0` on the shared store | Sequenced (not concurrent) schema-version bumps; coordination noted as a serialization point and a wave watchpoint. |
| `content_hash` computation cost offsets the skip win on large files | Hash is already needed for cache identity and is far cheaper than regex scanning + exception matching; instrumentation (AC-3) measures net effect and can inform tuning. |
| Feasibility spike reveals per-rule execution is not viable | Acceptable — Tier 1 still ships its robustness/crash-safety win, and the recorded finding prevents a doomed Tier 2 attempt; the persisted catalog remains useful for instrumentation. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
