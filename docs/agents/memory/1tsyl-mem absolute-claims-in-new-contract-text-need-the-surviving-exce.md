# Absolute claims in new contract text need the surviving exceptions named

Owner: Engineering
Status: active
Last verified: 2026-07-27

Memory ID: `1tsyl-mem absolute-claims-in-new-contract-text-need-the-surviving-exce`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 1158805
Source event: `finding:1to78:DF7-spec-authority-paragraph-overclaim`
Validation: promote
Validated by: agent
Action delta: When a wave retires a derivation mechanism, sweep the shipped contract text for absolute claims (inert, sole, never) and qualify each with the surviving exceptions in the same change; an unqualified absolute in a spec or seed is a defect even when the code is correct.
Validation rationale: The generated summary carried no lesson. The durable signal: this wave wrote a spec paragraph claiming prose inert in both directions while two prose reads legitimately survived (structured verdict line, roster) and an implicit contract (one-currency-per-key lane approvals) went undeclared; five seats independently flagged it and the repair pattern (scope the absolute, declare the implicit contract, name behavior changes as follow-ups instead of implying them) generalizes to every future contract-retirement wave. This complements rather than duplicates the carrier-reconciliation habit because it targets absolutes in newly WRITTEN text, not stale existing carriers.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1to78's new spec authority paragraph claimed prose in wave.md was inert in both directions on declared waves, but two prose reads survive by design (the structured prepare-council verdict line gating activation and the Participants roster) and the one-currency-per-key lane-approval contract was left undeclared; all five delivery seats flagged the overclaim independently. Repair pattern: scope the absolute (inert as review evidence), enumerate the surviving exceptions in the same paragraph, declare implicit contracts explicitly, and record associated behavior changes as named follow-ups rather than implying them. Sweep newly written contract text for absolutes (inert, sole, never, always) before delivery review.

## Evidence

- `DF7-spec-authority-paragraph-overclaim`
- `ev-df7-spec-authority-paragraph-overclaim-3`
- `1to78`

## Targets

- `docs/specs/mcp-tool-surface.md`
