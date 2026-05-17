# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-17

wave-id: `12nbr code-intelligence-expansion`
Title: Code Intelligence Expansion

## Changes

Change ID: `12nax-enh code-callhierarchy`
Change Status: `complete`

Change ID: `12nb2-enh hnsw-vector-index`
Change Status: `complete`

Change ID: `12nbj-enh code-hover`
Change Status: `complete`

Change ID: `12nbj-enh code-impact`
Change Status: `complete`

Change ID: `12nbp-bug code-outline-missing-node-types`
Change Status: `complete`

Change ID: `12p2m-bug sql-outline-plpgsql-fallback`
Change Status: `complete`

Change ID: `12p2t-maint remove-legacy-json-fixtures`
Change Status: `complete`

Change ID: `12p2x-maint prune-framework-meta-json`
Change Status: `complete`

Change ID: `12p2y-bug framework-pack-index-follows-pack-filter`
Change Status: `complete`

Change ID: `12p2z-bug framework-health-excludes-pack-artifacts`
Change Status: `complete`

Change ID: `12p3a-bug code-ask-feedback-docs-penalty`
Change Status: `complete`

Change ID: `12p3b-enh code-ask-lower-vector-top-k`
Change Status: `complete`

## Objective

Expand the MCP tool surface with five new code-intelligence capabilities: call hierarchy tracing (`code_callhierarchy`), reverse dependency analysis (`code_impact`), line-targeted symbol hover (`code_hover`), a LanceDB-backed HNSW vector index replacing hnswlib, and code-outline fixes covering both TypeScript exports and SQL routine discovery.

Completed At: 2026-05-17

## Wave Summary

Eight changes derived from field observations and lsp-mcp capability comparison. The `code_outline` bug fix (TypeScript `export_statement` unwrap + SQL node type names) is independently deployable and highest-priority, and the follow-up `sql-outline-plpgsql-fallback` change covers the remaining PostgreSQL procedural SQL gap. The test-fixture cleanup change removes the last legacy JSON references from tests now that LanceDB is the only supported index layout. The new prune repair change keeps the shipped framework index metadata aligned with files that survive pack pruning. The three new read-only tools (`code_callhierarchy`, `code_hover`, `code_impact`) each reuse existing parser infrastructure and are mutually independent. The LanceDB migration replaces hnswlib with an embedded columnar store that supports true deletion, MVCC, and native HNSW indexing above a configurable threshold.
The new packaging-filter fix ensures the framework index is built from the same excluded-file set used for the zip so ghost entries do not survive into shipped `meta.json`. `MANIFEST` is also excluded from the packaged framework index so it does not become permanently stale after upgrade. The framework-health walker now ignores `MANIFEST`, `MANIFEST.pre-*`, and `VERSION` as packaging artifacts so the health surface stays quiet after installs.
The code-ask retrieval path now soft-demotes feedback, journal, and framework seed artifacts rather than suppressing them outright, and the response exposes partition metadata (`partition_applied`, `demotion_count`, `demoted`, `partition_reason`, `final_rank`) so the ranking inversion is explicit instead of ambiguous. A follow-up tuning change lowers the base candidate pool from 40/60 to 30/50 to reduce rerank cost while preserving the retrieval pipeline.

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all `server.py` and `test_server_tools.py` edits; `seed_edit_allowed` required for seed changes. Open immediately before edits; close immediately after.
- **Watchpoint:** `12nbp-bug code-outline-missing-node-types` — SQL node type names must be verified from an actual tree-sitter-sql grammar parse tree before editing `_TS_OUTLINE_FUNC_TYPES`. Do not add names speculatively.
- **Watchpoint:** `12p2m-bug sql-outline-plpgsql-fallback` — fallback should stay conservative and only activate when tree-sitter returns no usable SQL outline symbols.
- **Watchpoint:** `12nb2-enh hnsw-vector-index` — LanceDB `table.optimize()` default `cleanup_older_than=7 days`; must pass `timedelta(seconds=0)` explicitly to trigger immediate MVCC cleanup. Legacy `.npy`/`.json` files must not be deleted until Lance tables are confirmed non-empty.
- **Sequencing:** `12nbp-bug` (bug fix) can ship independently before the new tools. Within `code_outline` fix: `export_statement` unwrap (Step 1) must land before `lexical_declaration` branch (Step 3).
- **Sequencing:** `12nax-enh code-callhierarchy` incoming direction depends on `code_references_response` being stable; verify no in-flight changes to that function before implementation.

## Review Evidence

- wave-council-readiness: approved-with-notes (2026-05-15 — Council initially blocked on two items in `12nbp-bug`: missing `qa-reviewer` lane designation (policy violation) and an unverified cross-wave scope reference to `12n63-enh code-outline.md`. Both resolved in-session before prepare: `qa-reviewer` + `code-reviewer` lanes added to the change doc; cross-wave reference confirmed to exist and path corrected. Eight advisory findings flagged for implementation phase. Seat roster: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team (fixed); performance-reviewer (rotating).)
- operator-signoff: approved (2026-05-17 — operator confirmed closure after final review)

## Review checkpoints

### Wave Council Readiness (2026-05-15)

Seat roster: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, red-team (fixed); performance-reviewer (rotating).

The council reviewed all five admitted change docs against readiness criteria. No material disagreements between seats arose. Two blocking items were identified and resolved before prepare was re-run.

**Blocking item 1 (qa-reviewer) — resolved:** `12nbp-bug code-outline-missing-node-types` is a bug fix. Per `review_policies.require_qa_reviewer_for_bug_fixes: true`, bug fix change docs must include an explicit `qa-reviewer` required lane designation. The change doc had a full AC priority table and test plan but no lane entry. Fixed in-session: `qa-reviewer` (required) and `code-reviewer` (required) added to a `## Required Review Lanes` section.

**Blocking item 2 (architecture-reviewer) — resolved:** The `12nbp-bug` scope section referenced `12n63-enh code-outline.md` without confirming the file existed. File confirmed present at `docs/waves/12mns code-ask-retrieval-quality/12n63-enh code-outline.md` (closed wave). Scope reference updated to the full path with a cross-wave note. Also corrected the `Wave:` header from the prior wave ID to `12nbr code-intelligence-expansion`.

**Advisory findings for implementation phase:**
- **security/red-team:** `code_impact` Heuristic 3 relative path resolution must be confirmed repo-root-confined at implementation time (not just at the entry-point boundary). Flag for `code-reviewer`.
- **security:** LanceDB `table.delete(f"path = '{file_path}'")`  f-string predicate interpolation — verify escaping or confirm repo-relative paths are safe to interpolate. Flag for `code-reviewer`.
- **red-team:** Partial or corrupted LanceDB directory (directory exists but empty or incomplete after interrupted build) not handled in `_ensure_loaded`. Implement fallback to `.npy` with a distinct warning rather than a hard failure.
- **red-team:** Confirm `code_impact` walk terminates after `max_results + 1` matches, not after scanning all files.
- **red-team:** Confirm whether `code_references_response` supports early termination for popular symbols in `code_callhierarchy` incoming direction.
- **performance:** `code_impact` performs a full-repo import parse (via `_IMPORT_PARSERS`) on every call — meaningfully heavier than `code_keyword` per file. Document as a known large-repo limitation.
- **performance:** `nprobes=20` / `refine_factor=10` in `_lance_search` are reasonable starting constants; validate against recall benchmarks post-implementation.
- **qa:** AC-7 in `12nb2-enh hnsw-vector-index` text references a two-step API; decision log resolved to single `optimize()` call — update AC-7 text before implementation to avoid re-litigation.

**Verdict:** Approved with notes. Both blockers resolved in-session. Eight advisories flagged for implementation and `code-reviewer` follow-through. All five changes are architecturally clean and ready to proceed.

## Dependencies

- No external wave dependencies.
