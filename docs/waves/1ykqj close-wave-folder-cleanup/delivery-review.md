# Cleanup Instruction Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Verdict: approved for the instruction-only docs contract. Independent docs-contract-reviewer context `1ykqj-cleanup-delivery-docs-independent` inspected the admitted change, wave, reviewer role and seed 209 protocol, then formed this assessment from the current source. Requested host-default model/effort; effective settings unknown. This requested report retains reproducible checks and the frozen review boundary.

## Reviewed boundary

Working-tree `git hash-object` values:

| Path | Blob |
| --- | --- |
| `.wavefoundry/framework/seeds/190-finalize-feature.prompt.md` | `7a0265b484d778f9c3ab867111cf3fcf56f55bda` |
| `docs/prompts/close-wave.prompt.md` | `79b9f94a98499d44d2e25252e7a07c556311f076` |
| `docs/prompts/finalize-feature.prompt.md` | `435b8c6cffdee68a9279b2ab223c00ddf345c00a` |
| `CHANGELOG.md` | `f32829d3e130028c2a7f0052c8213587e1ec6edc` |

SHA-256 of the path-to-blob dictionary encoded with Python `json.dumps(h, sort_keys=True)`: `de6a82e5e80ac4affa036605d88cd4dffbaa0f670637c635c0aadc8a7b7a555f`; matches briefing.

## Checks and observations

MCP `wf_get_change(change_id='1yk53')`, `wf_get_prompt` for Close wave and Finalize feature, `seed_get` and targeted `code_read` reached the real instruction surfaces. `git diff --` over the four paths confirmed bounded instruction and changelog edits. No runtime implementation changed in this reviewed diff. Seed task 16 now establishes report ownership by contents/references and preserves cited paths. The added policy is generic. Changelog accurately describes the instruction change.

The following `python3 -B` probe ran successfully from repository root (exit 0), including a known-bad in-memory mutation. It creates no files:

```python
from pathlib import Path
seed = Path('.wavefoundry/framework/seeds/190-finalize-feature.prompt.md').read_text()
close = Path('docs/prompts/close-wave.prompt.md').read_text()
finalize = Path('docs/prompts/finalize-feature.prompt.md').read_text()
block = close.split('## Wave-folder cleanup\n\n')[1].split('\n## ')[0].strip()
assert block in seed
assert finalize.index('7. Follow **Wave-folder cleanup**') < finalize.index('8. Update wave record')
clause = 'If ownership, uniqueness or reference use is uncertain, retain the artifact and note why.'
def verify(text):
    assert clause in text, 'uncertain evidence retention instruction absent'
verify(close)
try:
    verify(close.replace(clause, ''))
except AssertionError as error:
    print('KNOWN BAD REJECTED:', error)
else:
    raise RuntimeError('negative control survived')
```

Observed: canonical/local blocks identical; finalize points to that policy before completion; negative control printed `KNOWN BAD REJECTED: uncertain evidence retention instruction absent`.

## Scenario and mutation table

These are static policy judgments against the actual wording, not observed agent cleanup behavior.

| Input / proposed action | Expected and observed instruction result |
| --- | --- |
| Verified wave-owned disposable scratch, no references | Removal allowed after verification. |
| Duplicate report with no unique evidence or references | Removal allowed; duplicate status alone is insufficient. |
| Unique probe or historical fingerprint, even if named scratch | Retain: preservation clause controls. |
| Move ledger-cited evidence and rewrite ledger | Reject: stable cited paths and immutable history are explicit. |
| Move uncited supporting file into evidence/ | Optional; update mutable links/commands and verify usability. |
| Same-date report owned by another wave | Leave untouched: date is discovery-only. |
| Ownership or reference use uncertain | Retain and explain. |
| Delete uncertain-retention clause in memory | Targeted assertion failed as intended; no surviving mutant, no wider sweep needed. |

## Limits and follow-up

No contract defect found in this scope. No source edits, deletions, close operation, new tests or whole-suite rerun were performed. Executed assertions prove instruction presence, parity and ordering only. Scenario conclusions are inferred from the text; future agent adherence is unverified. Coordinator owns final docs validation, full framework receipt and AC-3 reconciliation. This review does not claim those checks passed. Keep this report at its ledger-cited path.
