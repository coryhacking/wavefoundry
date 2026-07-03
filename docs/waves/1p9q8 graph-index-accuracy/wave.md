# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-03

wave-id: `1p9q8 graph-index-accuracy`
Title: Graph Index Accuracy

## Objective

Close the four highest-value recall gaps in graph-edge extraction while preserving the never-bind-on-ambiguity faithfulness stance: Python receiver-call resolution (the framework's own language has none), same-scope disambiguation for Rust/C# (already proven for Java/Kotlin/Go), degraded line-scan extraction for files over the 2 MB parse cap (today a silent graph hole), and AST-anchored DI edges for Python/TS (today JVM/.NET only). Every change carries a calibration gate and the wave carries an adversarial faithfulness review.

## Changes

Change ID: `1p9q4-enh python-receiver-annotation-resolution`
Change Status: `planned`

Change ID: `1p9q5-enh same-package-disambiguation-rust-csharp`
Change Status: `planned`

Change ID: `1p9q6-enh oversized-file-degraded-extraction`
Change Status: `planned`

Change ID: `1p9q7-enh di-signal-ast-and-language-expansion`
Change Status: `planned`

## Wave Summary

The accuracy track of the graph-index evaluation (2026-07-03): `1p9q4` Python receiver resolution from annotations/constructor assignments, `1p9q5` Rust/C# same-scope disambiguation keyed on language rules (module/namespace, not directory), `1p9q6` bounded line-scan fallback for oversized files (imports + top-level defines, labeled, no call edges), `1p9q7` AST-anchored FastAPI/NestJS-Inversify DI signals. Recall improvements only where an explicit syntactic or language-rule signal exists; ambiguity still refuses to bind.

## Journal Watchpoints

- All four changes are binding/detection-faithfulness changes: a consolidated adversarial review lane at wave review is required (security-control-faithfulness rule) — green unit tests alone are not sufficient evidence.
- Coordinate a single wave-level `GRAPH_BUILDER_VERSION` bump across all four changes at integration; `graph_indexer.py` is the shared hub (Python extractor: `1p9q4`+`1p9q7`; cross-file pass: `1p9q4`+`1p9q5`; size gate: `1p9q6`) — merge order matters more than parallelism.
- Multi-language pack fixture conventions are shared by `1p9q5` (Rust/C#) and `1p9q7` (Python/TS DI) — agree the fixture directory layout once before either lands; spawned test agents must use the `~/.wavefoundry/venv` interpreter or cross-language tests silently skip.
- Follow-up seam: `1p9q7` deliberately defers annotation-only `Depends()` to avoid entangling with `1p9q4`'s annotation model — if both land, evaluate the connection as a candidate follow-up change, not silent scope.
- If wave `1p9q3` (efficiency) implements first, its differential incremental-vs-full harness doubles as an extra oracle for these binding changes; if this wave lands first, all four re-extractions ride the full-rebuild path (version bump) with no interaction.

## Participants

- code-reviewer — all four changes touch `.wavefoundry/framework/scripts/*.py`
- qa-reviewer — all change docs carry AC priority tables
- architecture-reviewer — extraction/resolution module seams in `graph_indexer.py` shared by all four changes
- performance-reviewer — new per-file scan patterns and extractor hot-path additions (`1p9q6` line scan; `1p9q4`/`1p9q7` AST-walk additions)
- red-team, reality-checker — council seats (prepare phase); the consolidated adversarial faithfulness lane re-runs at implementation review for all four binding changes

## Review Checkpoints

- Prepare wave — readiness verdict (2026-07-03): READY. Council ran at standard primer depth. Red-team's strongest challenge — `1p9q6` fallback definitions entering candidate sets will demote some existing binds repo-wide (previously "unique" only because the oversized twin was invisible) — was examined and accepted as designed-correct behavior: the demotions are faithfulness restorations, the calibration counts make the delta visible, and the risk table already dispositions it. Amendments applied from seat findings: `1p9q5` AC-2 gained C# namespace-key normalization across nested/compound/file-scoped declaration styles (qa seat — the likeliest silent scope-key bug); `1p9q7` Requirement 4/AC-1 gained alias-aware idiom identification with same-named-impostor refusal (red-team follow-through — both over-fire and under-fire modes); `1p9q6` Requirement 3 gained encoding robustness for BOM/decode-error/no-final-newline shapes (reality seat — big generated files are exactly where odd encodings live). Reality seat also noted `1p9q4`'s calibration may show a modest delta on the self-hosted repo given its annotation density — the doc already handles this honestly (re-scope on negligible delta rather than ship on faith). Strongest alternative (imports-only line scan for `1p9q6`, halving invention risk) recorded and declined — definitions are the half that reconnects inbound references, and the invention risk is bounded by line anchoring plus adversarial fixtures. AC priorities recorded on all four change docs. Product-owner acknowledgment: not applicable (framework-internal accuracy work; no product behavior shift).
- Security seat (rotating): the `1p9q6` line scan runs static anchored patterns over repo files with a hard byte ceiling and line-length guard — no user-supplied patterns, no unbounded regex, no denial-of-build exposure from pathological files (the ceiling degrades to logged skip). Graph edges feed impact analysis used in reviews, so over-extraction is an integrity concern, not just accuracy — covered by the exact-set DI fixtures, the refusal-by-default stance, and the mandatory adversarial faithfulness lane at implementation review. No trust boundary is crossed by any of the four changes.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: 1p9q6 fallback definitions demote existing binds repo-wide where uniqueness came from twin invisibility — accepted as designed-correct faithfulness restoration, visible in calibration counts; strongest-alternative: imports-only line scan halving invention risk — declined, definitions are the half that reconnects inbound references and invention risk is bounded by anchoring plus adversarial fixtures)

## Review Evidence

- wave-council-readiness: approved 2026-07-03 — prepare council synthesis verdict READY after amendments (1p9q5 namespace normalization, 1p9q7 alias-aware idioms, 1p9q6 encoding robustness); no unresolved blocking findings
- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies.
