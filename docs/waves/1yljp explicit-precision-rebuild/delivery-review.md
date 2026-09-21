# Explicit Precision Rebuild Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Council primer

Standard depth; context `1yljp-delivery-primer-20260921`. This is a primer on the implementation in progress, not delivery approval. Adversarial, constructive and simplicity stances were applied.

Strongest challenge: the regression matrix patches the precision predictor, and the initial fresh-CPU control used explicit full. Require a public ordinary fresh build with the real predictor, plus a provider-driven precision mismatch with that predictor intact. The implementer received these bounded checks before the delivery freeze.

Primer questions:

1. Does an ordinary fresh CPU build with `full=False` pass through the actual guard and real precision predictor, while a provider-driven conversion of a producer-built existing index fails before model resolution or epoch mutation?
2. Does refusal reach CLI/setup/MCP as an actionable failure while preserving canonical state, including scoped siblings, graph escalation and dry-run, without claiming an incomplete epoch?

Best alternative: preserve full precision through a compatible CPU embedder to maintain availability after GPU loss. That needs coordinated factory/cache/provenance changes; bounded refusal is the simpler repair for this wave. No live index or model execution was used for the primer.

## Verification

Delivery review and full-suite verification passed. The operator explicitly waived the benchmark pair for this fix; invalid before reports remain retained. No benchmark result is claimed as passing.

## Code and QA review

Context `1yljp-independent-delivery-20260921` APPROVE for AC-1–3; full-suite evidence for AC-4 remains pending. The reviewer did not implement the change. Code, QA and Council red-team perspectives share one context, including its earlier readiness and primer history; they are not three independent reviews.

Executed all 11 `ExplicitPrecisionRebuildTests`: passed in 14.705 seconds, no skips. An additional ordinary fresh CPU build with the real predictor and `full=False` succeeded, embedded two batches and published both INT8 identities. All five reviewed file fingerprints were unchanged after review.

| In-memory mutant | Detection |
| --- | --- |
| Remove guard | Both-directions/scopes/state test fails |
| Ignore code sibling | Untouched-sibling test fails |
| Guess legacy precision as full | Legacy-provenance test fails |
| Apply refusal to explicit full | Explicit conversion/incremental restoration test fails |
| Ignore CLI failed result | Real CLI refusal test fails |
| Restore false incomplete-epoch message | Setup consumer test fails |

All six failed assertions with zero errors or skips; no survivors required whole-file expansion. Primer questions answered yes: the real predictor and ordinary fresh CPU path are exercised, and the real CLI refusal feeds setup/MCP through substituted process boundaries. Canonical snapshots and factory/epoch spies prove preservation. Compatible full-precision CPU fallback remains a larger factory/cache/identity change and is not stronger for this bounded repair.

All five evidence-integrity checks affirmed; known-bad method `focused-mutation`. Limits: deterministic embeddings, simulated provider discovery, substituted process boundaries; no detached-process timing, native Windows, live model or benchmark execution claimed.

Focused readiness refresh against `review-policy-b230afcc648d7c87f358`: APPROVE. The explicit operator waiver is scoped to this change and leaves behavioral requirements and AC semantics unchanged. This is the same reviewer context, not a new review round.

## Architecture and docs-contract review

Context `1yljp-arch-docs-delivery-20260921` APPROVE for delivery and focused readiness refresh. Architecture and the rotating docs-contract Council seat share this independent context; the reviewer implemented none of this repair and did not read the other reviewer's outputs.

Independently executed the 11 regression tests (14.191 seconds, no skips), plus an ordinary fresh CPU build with the real predictor. Six in-memory mutants were killed: removed guard, omitted code sibling, refused explicit full, bypassed graph protection, guessed legacy precision and restored false setup epoch wording. Each failed the intended assertion; no survivors required expansion.

No new schema, connection owner, provider policy, dependency or persistent authority was introduced. Existing storage/recovery checks precede the guard; canonical snapshots, model and epoch-entry spies establish refusal before build mutation. README/pipeline wording matches the delivered distinction. Both primer questions were answered yes within the deterministic embedding and substituted subprocess boundaries. All five integrity checks were affirmed with `focused-mutation`; all frozen fingerprints remained unchanged.

## Council synthesis

The receipt selects targeted delivery with red-team and rotating docs-contract seats. These ran in two independent contexts; specialist code/QA/architecture perspectives share those contexts as disclosed above. A request for an additional fresh host thread was refused by the host thread limit; no additional reviewer or independence is claimed. Inherited models were selected for bounded state/compatibility judgment; observed runtime identity is unknown.

Merit-first synthesis of anonymized outputs found agreement on canonical-state preservation, original full intent, recognized provenance and real failure propagation. Reattaching roles: red-team/code/QA and docs-contract/architecture both APPROVE, with no findings in their lanes. Agreement unanimous; maximum severity none. The primer improved the delivered tests by requiring an ordinary fresh CPU control and the real predictor, both independently verified afterward.

Strongest alternative: preserving full precision with a CPU embedder could improve availability, but requires broader factory/cache/identity work. It is not needed to prevent unrequested re-embedding. No additional code change is recommended within this scope.

### Falsification Check

Working verdict: APPROVE the bounded repair, subject to the full-suite and documentation gates. Strongest counterargument: mocked embedding and process seams could hide provider/consumer failures. Independent real-predictor controls, real CLI refusal propagation and targeted mutants reduce that risk; they do not claim native GPU/Windows execution or detached-process timing. Those limitations do not negate the verified refusal-before-work contract.

## Integration repair and focused recheck

The first full run executed 9,479 tests and failed only `test_indexer.py`: loading the MCP consumer in-process purged a module and broke the later `FileWalkerTests.test_wave_ledger_predicate_is_the_single_review_evidence_definition` identity assertion. The consumer probe now runs in a child interpreter, preserving its real producer and response assertions. Product code and documentation did not change.

Both independent contexts inspected that narrow repair and ran the revised consumer followed by the former failing identity test using the canonical tool-venv interpreter: both passed with zero skips (3.495 seconds code/QA; 3.478 seconds architecture/docs). Code/QA additionally removed the guard inside the child: MCP returned `ok` instead of `error`, the child assertion failed and exited 1, and the parent exit-status assertion failed. The child boundary therefore preserves detection rather than hiding failure. Both reviewers renewed approval; these are focused continuations, not new independent contexts.

Reviewed `git hash-object` values at the isolation checkpoint:

| Path | Hash |
| --- | --- |
| `.wavefoundry/framework/scripts/indexer.py` | `bfc54b3dfc2bc3785eb3d9fe3fd9fe0d12992b7b` |
| `.wavefoundry/framework/scripts/setup_index.py` | `bd33fba261eb7e633c3f46be4c100a3bd448011b` |
| `.wavefoundry/framework/scripts/tests/test_indexer.py` | `72f4f7ce64396fee9108530a0b3aa13475d33a80` |
| `.wavefoundry/framework/README.md` | `e2e6fc41acccfe78a9ac04e1ffed45131509fca8` |
| `docs/architecture/chunking-and-indexing-pipeline.md` | `997fe5570b2cd7f5b2bc3f0f7cd255d5e9c16ee5` |

## Legacy fixture correction

The second full run executed 9,479 tests and failed only two older indexer tests (three failing assertions). The scoped fingerprint-transition fixture hardcoded `full` even when its producer built INT8; the targeted model-identity fixture selected an unregistered model whose predictor also changed precision. Both therefore reached the new, legitimate precision refusal instead of the behavior they intended to test.

The fingerprint mutation now retains producer precision and adds an explicit no-failure assertion. The targeted currency fixture holds producer precision constant while changing its original identity inputs. Both-layer convergence, recovery text, no-mutation, row and generation assertions remain intact. No product code changed.

Both independent contexts rechecked these exact tests with the canonical interpreter: 2 passed, zero skips (2.311 seconds code/QA; 2.354 seconds architecture/docs). They renewed approval without a broader resweep; previous mutation evidence remains applicable. Final test-file hash is `8f54ab184a6851b237fae09b946c71fa562e8304`; all four product/documentation hashes above remain unchanged. Typed delivery recording identifiers distinguish phase/recheck operations but refer to the same two reviewer workers and history, not additional independent reviews.

## Final validation

`python3 .wavefoundry/framework/scripts/run_tests.py` passed: 9,479 tests across 119 files, 12 skipped, 278.162 seconds. Receipt timestamp `2026-09-21T22:09:20.866889+00:00`; inputs hash `f9fd14354f9b28459f3cb3cc718dfe5538c8839f874f0d355d43c4d1a9d904b3` independently recomputed to match. Final run log: `/private/tmp/1yljp-full-suite-verified.log`. The earlier failed attempts remain disclosed above; they are not green evidence. No live corpus rebuild was used to verify the repair.
