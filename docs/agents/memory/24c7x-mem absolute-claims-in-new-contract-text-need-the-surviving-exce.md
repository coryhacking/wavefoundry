# Absolute claims in new contract text need the surviving exceptions named

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24c7x-mem absolute-claims-in-new-contract-text-need-the-surviving-exce`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 1158805
Supersedes: `1tsyl-mem absolute-claims-in-new-contract-text-need-the-surviving-exce`
Retarget reason: The contract moved from docs/specs/mcp-tool-surface.md to docs/architecture/contracts/mcp-tool-surface.md; the same authority paragraph is at line 2133.
Checked at: 2026-11-26T06:32:45Z
Check note: Negative contract claims need to name surviving exceptions. The tool surface still contains phase- and mode-specific behavior. Reviewed docs/architecture/contracts/mcp-tool-surface.md:2077.
Check flags: none

## Summary

When writing new contract text that retires a mechanism, sweep it for absolutes (inert, sole, never, always) before delivery review and, in the same paragraph, scope each absolute and name the exceptions that survive by design; declare any implicit contract and record related behavior changes as named follow-ups. Wave 1to78's authority paragraph, now at docs/architecture/contracts/mcp-tool-surface.md (Review-evidence authority derivation), first claimed prose was inert in both directions while the prepare-council verdict line and the Participants roster still read prose; all five delivery seats flagged it (finding DF7-spec-authority-paragraph-overclaim).

## Evidence

- `DF7-spec-authority-paragraph-overclaim`
- `ev-df7-spec-authority-paragraph-overclaim-3`
- `1to78`

## Targets

- `docs/architecture/contracts/mcp-tool-surface.md`
