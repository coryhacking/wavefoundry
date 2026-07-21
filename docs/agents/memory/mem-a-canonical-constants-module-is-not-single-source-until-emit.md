# A canonical constants module is not single-source until emitters consume it

Owner: Engineering
Status: active
Last verified: 2026-07-21

Memory ID: `mem-a-canonical-constants-module-is-not-single-source-until-emit`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-21
Updated: 2026-07-21
Source event: `finding:1seax:contract-vocabularies-not-consumed-by-handlers`
Validation: promote
Validated by: agent
Action delta: When introducing a canonical constants module, wire every EMITTING site onto it in the same change and census the real emitted values first; a module nobody consumes is a third truth, and the census itself may correct the module.
Validation rationale: The drafted summary is accurate but names only the repair verdict; the durable lesson is the two-part failure shape (declared-but-unconsumed canonical source; under-enumerated vocabulary corrected only when consumption was forced) and it should anchor to both modules.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1seax: public_contract.py was created as the single source for public vocabularies, but the emitting handlers kept their scattered literals, so the module was a THIRD truth rather than the one truth — and its SEARCH_MODES tuple was itself under-enumerated (2 of the real 5 modes) because it was derived from a partial grep instead of a producing-site census. Repair pattern: tuple-unpacked named aliases at the consumer (rename/reorder breaks at import), literals replaced at every emitting site, source pins against bare literals returning, and the census assertion pinning the full tuple.

## Evidence

- `1seax`
- `contract-vocabularies-not-consumed-by-handlers`
- `test_handlers_consume_the_vocabulary_aliases`
- `test_search_modes_cover_every_emitting_site`

## Targets

- `.wavefoundry/framework/scripts/public_contract.py`
- `.wavefoundry/framework/scripts/server_impl.py`
