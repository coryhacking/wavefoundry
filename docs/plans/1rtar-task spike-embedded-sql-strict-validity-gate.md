# Spike: strict-validity gate for embedded-SQL capture (close the prose false-positive class)

Change ID: `1rtar-task spike-embedded-sql-strict-validity-gate`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-05
Wave: TBD

## Rationale

A **time-boxed spike** (investigation + prototype + decision, not a committed feature) to answer one question: should embedded-SQL capture route each candidate through a real dialect SQL parser used in STRICT mode (e.g. `sqlglot`) as a validity gate, to close the embedded-prose false-positive class the `1rs44` wave could only partially address?

Context: wave `1p9qi` bound SQL string literals at Java/C# sinks to table nodes. Prose that leads with a DML keyword and contains a mandatory-clause connective can mis-parse as SQL and mint a **confidently-wrong** `writes` edge (`jdbc.update("delete the row from cache")` → `writes cache`). Wave `1rs44` closed the TRUNCATE arm (any-ERROR gate) and the DELETE/UPDATE/INSERT **interior**-prose subclass (interior-vs-trailing ERROR discrimination), but two subclasses remain because tree-sitter-sql is an **error-recovering** parser — it never fails, so it cannot answer "is this string strictly valid SQL?":

- **Trailing-prose DELETE** (`delete from sessions periodically` → `writes sessions`): `DELETE FROM t` is a complete statement, so trailing English is a trailing ERROR, parse-shape-indistinguishable from a valid unmodeled trailing clause (`RETURNING`, MySQL `ORDER BY`/`LIMIT`).
- **SELECT-prose** (`select all items from inventory list` → `reads inventory`): some prose parses without any ERROR at all.

Both are **pre-existing** (in the `1p9qf`/`1p9qi` sniff set) and — critically — the `1rs44` real-corpus census (Apache Fineract) found **zero** live occurrences: every reproducer is a synthetic adversarial string. So this is a robustness/theoretical concern, not a live-corpus defect, which is why `1rs44` recorded it rather than paying a dependency cost pre-emptively.

## Requirements

The spike must PRODUCE A DECISION with evidence, not ship a gate. Deliverables:

1. **Feasibility + ceiling.** Confirm the theoretical ceiling: a string that is *simultaneously* valid SQL and plausible English (`delete from records`, `select name from users`) is irreducibly undecidable in isolation — measure how small that residual is with a real parser vs. the current tree-sitter gate.
2. **Prototype a `sqlglot` strict-validity gate** (behind a probe, not wired into the build): parse each captured candidate with `sqlglot.parse_one(sql, dialect=…, error_level=RAISE)`; a raise → prose/malformed → refuse; a clean parse → SQL → keep. Verify against the `1rs44` reproducer set (`delete the row from cache`, `delete from sessions periodically`, `truncate events now`, `select all items from inventory list`) AND the valid-dialect set (`RETURNING`, `ON CONFLICT`, `USING`, CTE-led DML, MySQL/T-SQL variants) — does it close the false positives WITHOUT dropping valid dialect SQL?
3. **Dependency + performance cost.** `sqlglot` is pure-Python, deterministic, no network (fits the local-only ethos) — but measure: install footprint, per-candidate parse latency, and total index-build impact on a real Java corpus (Fineract) where thousands of candidates are captured. Compare against the current tree-sitter reuse (near-zero marginal cost).
4. **Dialect-selection question.** The gate needs a dialect (Postgres vs MySQL vs T-SQL vs ANSI); embedded SQL at a sink has no declared dialect. Evaluate: try a permissive/ANSI parse first, or multi-dialect best-of? How much does dialect mismatch cause valid SQL to wrongly fail-parse (a new over-rejection risk)?
5. **Cheaper middle-option comparison.** Also prototype the no-dependency continuation-keyword allowlist (after the DML target require end-of-statement or a recognized clause keyword `WHERE`/`RETURNING`/`USING`/…). Quantify its coverage (closes the common `delete from <table> <adverb>` trailing shape) and its hole (prose that includes a real keyword, `delete from sessions where expired and stuff`). Compare the 80%-no-dependency option against the sqlglot ~100%-with-dependency option.
6. **Recommendation.** Given the zero-live-corpus frequency, recommend one of: (a) ship the sqlglot gate; (b) ship the cheap continuation-keyword gate; (c) do nothing — keep the recorded residual, revisit only on real field evidence. Record the decision as an ADR-shaped note.

## Scope

**Problem statement:** Determine, with prototype evidence and cost measurement, whether a strict-validity gate (real SQL parser) is worth adopting to close the embedded-prose false-positive class, or whether the cheaper gate / status-quo is the right call given the class does not occur in real corpora.

**In scope:**

- A throwaway prototype gate (probe scripts, not wired into `graph_indexer.py` build path) evaluated against the `1rs44` reproducer + valid-dialect sets and a real Java corpus.
- Dependency footprint + per-candidate + full-build performance measurement.
- The dialect-selection over-rejection risk assessment.
- A written recommendation (ship-sqlglot / ship-cheap-gate / do-nothing) with the evidence.

**Out of scope:**

- Shipping any gate into the build path — that is a follow-on change contingent on the spike's recommendation.
- The trailing-prose residual's live remediation (only a synthetic concern until field evidence appears).
- Any dialect parser other than `sqlglot` unless the spike finds `sqlglot` unfit (then note the alternative).

## Acceptance Criteria

- [ ] AC-1: The sqlglot strict-parse prototype is run against the `1rs44` reproducer set and the valid-dialect set; a results table records which each classifies (prose→refuse, valid→keep) vs the current tree-sitter gate.
- [ ] AC-2: The dependency footprint + per-candidate parse latency + full-build delta on a real Java corpus (Fineract) are measured and recorded.
- [ ] AC-3: The dialect-selection over-rejection risk is assessed (how many valid statements a single-dialect / ANSI parse wrongly rejects).
- [ ] AC-4: The no-dependency continuation-keyword middle option is prototyped and its coverage/holes quantified against the same sets.
- [ ] AC-5: A written recommendation (ship-sqlglot / ship-cheap-gate / do-nothing) with the theoretical-ceiling note and the zero-live-corpus context is recorded as the spike output; if "ship", a follow-on change is scoped.

## Tasks

- [ ] Prototype the sqlglot strict-parse gate as a probe; run the reproducer + valid-dialect matrix.
- [ ] Measure dependency + per-candidate + full-build cost on Fineract.
- [ ] Assess dialect-selection over-rejection.
- [ ] Prototype the continuation-keyword middle option; quantify coverage/holes.
- [ ] Write the recommendation + ceiling note; scope the follow-on change if "ship".

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| sqlglot-prototype | implementer | — | Strict-parse probe + reproducer/valid-dialect matrix + dialect-risk. |
| cost-measurement | implementer | sqlglot-prototype | Dependency footprint + per-candidate + full-build delta on Fineract. |
| cheap-option | implementer | — | Continuation-keyword allowlist probe + coverage/hole quantification. |
| recommendation | implementer | sqlglot-prototype, cost-measurement, cheap-option | Written decision + ceiling note; scope follow-on if ship. |


## Serialization Points

- None internal — the workstreams are probes. If the recommendation is "ship", the follow-on gate lands in `graph_indexer.py`'s embedded-SQL bind path and shares the SQL extractor region with `1rs45`/`1p9q8` (coordinate then).

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — only if the recommendation is "ship"; the spike itself produces a decision note, not a code change. The embedded-SQL capture/bind decision note would gain the strict-validity gate.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required / important / nice-to-have / not-this-scope | Set at Prepare — spike deliverables. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-05 | Spike authored at operator direction when closing wave `1rs44` — the embedded-prose false-positive class could only be partially closed there (interior-prose + TRUNCATE), and the robust fix needs a real SQL parser, which is a dependency + design decision warranting a time-boxed spike rather than an in-wave bolt-on. | `1rs44` `1rrx5` Decision Log (trailing-prose + SELECT-prose residuals; R8 re-review PASS WITH FINDINGS). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-05 | Frame the strict-validity work as a time-boxed SPIKE (investigation → decision), not a committed feature. | The residual is synthetic (zero live-corpus occurrences in the `1rs44` Fineract census), so a full SQL-parser dependency should not be adopted pre-emptively; the spike measures real cost/benefit before committing. | Ship a sqlglot gate directly (rejected: pre-emptive dependency for a class not seen in real corpora); do nothing and never revisit (rejected: a real field false-positive would want the principled fix on file). |


## Risks


| Risk | Mitigation |
| --- | --- |
| The sqlglot gate introduces a NEW over-rejection (valid SQL wrongly failing a single-dialect strict parse). | AC-3 explicitly measures dialect-mismatch over-rejection; a permissive/ANSI-first or multi-dialect best-of parse is evaluated. |
| The spike scope-creeps into shipping a gate. | Hard out-of-scope: no build-path wiring; the deliverable is a recommendation + evidence only. |
| The dependency/perf cost is judged too high but the residual later appears in the field. | The recommendation records the sqlglot design as the on-file answer to reach for if field evidence appears — decision is revisitable, not lost. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
