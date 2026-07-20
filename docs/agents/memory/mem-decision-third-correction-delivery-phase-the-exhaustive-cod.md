# Decision: **Third correction (delivery-phase):** the "exhaustive `cod…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-third-correction-delivery-phase-the-exhaustive-cod`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p92t-bug ca-bundle-non-setup-launchers:6686f5a0c6ae98d2`
Validation: rewrite
Validated by: agent
Action delta: Census model-download behavior through call graphs and aliases, then verify TLS configuration and diagnostics at every path.
Validation rationale: The three correction rounds prove literal constructor searches are insufficient, while current code still has several distinct download entry paths.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-census-model-download-paths-by-behavior-not-constructor-spel`
## Summary

Decision (wave 1p939): **Third correction (delivery-phase):** the "exhaustive `code_keyword` sweep" claim was incomplete — `indexer.py::_text_embedding_cached_first()` is a fourth raw call site, invisible to a literal `TextEmbedding(` token search because the constructor is invoked via the `text_embedding_cls` parameter name. Expand scope to cover it (AC-7).. Rationale: Discovered independently during delivery-phase review by the qa-reviewer seat (AC-by-AC call-graph tracing), the reality-checker seat (independent call-graph trace), and the separate required code-reviewer lane (evidence-table audit) — three different methods, zero counter-evidence. It is the path every named launcher actually hits whenever GPU acceleration is unavailable, which falsified AC-1/AC-2 as originally evidenced..

## Evidence

- `1p92t-bug ca-bundle-non-setup-launchers`
- `1p939`

## Targets

- `indexer.py`
