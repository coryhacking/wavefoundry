# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-03

wave-id: `1p9qi sql-graph-accuracy`
Title: SQL Graph Accuracy and Embedded SQL

## Objective

Turn SQL from the graph's noisiest, most hollow language into a first-class data layer, and connect code to it. When this wave closes: keyword tokens no longer mint fake external nodes (live-verified bug), SQL references are clause-aware with read/write direction and view lineage, procedures the grammar can't parse are recovered instead of vanishing, and — the enterprise payoff — SQL embedded in Java/C# data-access code and JPA/EF entity declarations bind to table nodes, making "which code touches table X" answerable.

## Changes

Change ID: `1p9qc-bug sql-keyword-noise-suppression`
Change Status: `planned`

Change ID: `1p9qd-enh sql-structured-statement-extraction`
Change Status: `planned`

Change ID: `1p9qe-enh sql-ddl-error-recovery`
Change Status: `planned`

Change ID: `1p9qf-enh embedded-sql-capture-and-bind`
Change Status: `planned`

Change ID: `1p9qg-enh orm-entity-table-mapping`
Change Status: `planned`

## Wave Summary

The SQL tier of the graph-accuracy investigation (2026-07-03), all findings live-verified against the real grammar: `1p9qc` kills keyword-token edge pollution (bug), `1p9qd` builds clause-aware extraction with a reusable statement-analysis unit (read/write kinds, view lineage, honest object kinds), `1p9qe` adds the ERROR-region DDL recovery tier (procedures currently vanish entirely), `1p9qf` captures SQL literals at known Java/C# sinks and binds code→table at `LITERAL_DERIVED` with a mandatory real-corpus locality census, `1p9qg` binds JPA/EF entities to tables via declared names only (conventions refused by standing decision).

## Journal Watchpoints

- Hard sequencing: `1p9qc` first (clean candidate space; later tests must not encode noise), then `1p9qd` (its statement-analysis unit is the frozen contract `1p9qe` body-recovery and `1p9qf` bind both consume), then `1p9qe`/`1p9qf`/`1p9qg`.
- Shared seams to build once: the annotation/attribute-argument capture mechanism (`1p9qf` + `1p9qg`), the read/write edge representation decision (`1p9qd` + `1p9qg`, one consumer sweep), and the `external::sql::` namespace (`1p9qf` + `1p9qg`).
- Single coordinated `GRAPH_BUILDER_VERSION` bump across all five changes at integration; if a `writes` relation is added, coordinate the `docs/specs/mcp-tool-surface.md` vocabulary edit with wave `1p9qh`'s (`extends`/`implements`) update.
- Blocking gate before close: `1p9qf`/`1p9qg`'s real-corpus locality census (standing literal-edge field lesson) — the default-on decision must be recorded on census evidence, not fixtures.
- All binding changes require the consolidated adversarial faithfulness review lane at implementation review (standing security-control-faithfulness rule); `1p9qe`'s recovery scan counts as a detection surface for that review.
- Follow-up candidates deliberately out of scope: JPQL binding (layers on `1p9qg`), column-level lineage, convention-derived table names, Python/Go/TS SQL sinks.

## Participants

- code-reviewer — all five changes touch `.wavefoundry/framework/scripts/*.py`
- qa-reviewer — required (bug fix `1p9qc` per `review_policies.require_qa_reviewer_for_bug_fixes`) and all change docs carry AC priority tables
- architecture-reviewer — potential relation-vocabulary addition (`writes`), the new statement-analysis unit seam, and the first code→data-layer edge family
- performance-reviewer — new scan patterns and per-file extraction additions (`1p9qe` recovery scan, `1p9qf` sink capture)
- red-team, reality-checker — council seats (prepare phase); consolidated adversarial faithfulness lane re-runs at implementation review

## Review Checkpoints

- Prepare wave — readiness verdict (2026-07-03): READY. Council ran at standard primer depth. Red-team's strongest challenge — the `1p9qf` bind stage can bind through query-local names that are not schema objects (temp tables `#t`/`@t`, derived-table aliases, CTEs), minting false code→table edges that would poison exactly the impact analysis the wave exists to enable — was accepted and resolved by amendment: `1p9qd` AC-6 now explicitly excludes temp-table/table-variable sigil forms and subquery aliases alongside CTEs/aliases, and the statement unit is the single shared extraction path so the exclusion covers `1p9qe` body recovery and `1p9qf` binds uniformly. Reality seat confirmed every claimed defect is live-verified (keyword-noise edges, ERROR-node procedure loss, dangling body references) and endorsed the census gate on `1p9qf`/`1p9qg` per the standing literal-edge field lesson. QA seat confirmed the exact-edge-set test discipline replaces the vacuous single SQL test and that both bug-fix flip directions are pinned. Architecture seat flagged the read/write representation decision (`writes` relation vs edge property) as correctly deferred to a consumer sweep shared with `1p9qg`, and the statement-unit contract freeze as the wave's key serialization point. Performance seat: recovery scan and sink capture are bounded and run only on ERROR regions / already-visited AST nodes — acceptable. Strongest alternative (repo-wide SQL-sniffing of all string literals instead of sink gating) recorded and declined — sink knowledge is what makes precision achievable; the false-positive surface of literal trawling scales with the repo. AC priorities recorded on all five change docs. Product-owner acknowledgment: not applicable (framework-internal accuracy work).
- Security seat (rotating): the recovery scan (`1p9qe`) and sink capture (`1p9qf`) process repo-local content with static anchored patterns, hard byte/line bounds, and no user-supplied patterns — no denial-of-build or injection surface; comment-stripping before the recovery scan prevents commented-out DDL from minting schema objects. The embedded-SQL edge family feeds review-support impact analysis, so false binds are an integrity concern — covered by the sniff gate, origin checks, unique-match-or-drop, the `external::sql::` namespace isolation, the temp-object exclusion amendment, and the census + adversarial lane before close. No security findings.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: the bind stage could bind through query-local names that are not schema objects, temp tables and derived-table aliases, poisoning code-to-table impact — resolved by the 1p9qd AC-6 temp-object and alias exclusion applied at the shared statement unit; strongest-alternative: repo-wide SQL-sniffing of all string literals instead of sink gating — declined, sink knowledge is what makes precision achievable)

## Review Evidence

- wave-council-readiness: approved 2026-07-03 — prepare council synthesis verdict READY after the 1p9qd temp-object exclusion amendment; census gate on 1p9qf/1p9qg affirmed; no unresolved blocking findings
- operator-signoff: pending operator confirmation at closure

## Dependencies

- Soft dependency on wave `1p9qh` only for shared spec-doc edits; no lifecycle blocking either direction.
