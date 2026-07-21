# Repaired defect contract-vocabularies-not-consumed-by-handlers

Owner: Engineering
Status: superseded
Last verified: 2026-07-21

Memory ID: `mem-repaired-defect-contract-vocabularies-not-consumed-by-handle`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-21
Updated: 2026-07-21
Source exploration cost: 87497
Source event: `finding:1seax:contract-vocabularies-not-consumed-by-handlers`
Validation: rewrite
Validated by: agent
Action delta: When introducing a canonical constants module, wire every EMITTING site onto it in the same change and census the real emitted values first; a module nobody consumes is a third truth, and the census itself may correct the module.
Validation rationale: The drafted summary is accurate but names only the repair verdict; the durable lesson is the two-part failure shape (declared-but-unconsumed canonical source; under-enumerated vocabulary corrected only when consumption was forced) and it should anchor to both modules.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-a-canonical-constants-module-is-not-single-source-until-emit`
## Summary

Real defect fixed in wave 1seax: Repair confirmed at every emitting site with the suite clean; the census correction is itself pinned.

## Evidence

- `contract-vocabularies-not-consumed-by-handlers`
- `ev-contract-vocabularies-not-consumed-by-handlers-3`
- `1seax`

## Targets

- `server_impl.py`
