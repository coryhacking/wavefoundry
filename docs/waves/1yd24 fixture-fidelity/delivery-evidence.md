# Fixture-fidelity delivery evidence

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Implemented contract

`server_tools_support.make_declared_wave` creates/admit/prepares through real producers with explicit scoped lint, gardener, post-write lint and refresh stubs; only synthetic Status is a helper-owned record edit. Unexpected producer refusals fail at their source. Real receipt publication is checked even when initial Prepare reports the expected missing council approval. The final Prepare positive/omitted-readiness-run pair is the readiness oracle.

Five setup seams migrated: dashboard snapshot builder, memory-proposal wave builder, docs-lint typed readiness, phase aliases, and the policy fixture shared by readiness convergence. Stable dashboard/memory identifiers use a scoped producer ID-generator seam rather than rewriting generated wave records. Custom component inputs remain intentional subjects. Immutable fixtures/goldens and production modules are unchanged.

Current retained declaration census: 46 literal tokens across eight files, classified as 24 component fixtures, 12 declaration checks, and 10 negative fixtures. The token guard is bounded to literal tokens including f-string segments, not computed declarations. The reviewed inventory is in declaration-census.json. Baseline raw occurrences were 51 across ten files; removing valid handwritten setup reduced that inventory.

Seeds 209/239 clarify producer-built prerequisite state, independent expected-value oracles, deliberate input exceptions and reading setup refusal messages. QA still has five integrity conditions. Existing seed209 pointers and fresh239 role bodies carry the rule; existing target-owned prose is preserved. Self-hosted QA guidance was explicitly synchronized. Repository renderer run made no additional writes; preexisting generated diffs remain byte-identical to the saved baseline.

## Focused verification

- Guidance plus renderer/platform suites: 231 tests passed.
- Docs-lint module: 1106 tests passed.
- Policy/readiness: 66 tests passed.
- Migration/helper/golden: 43 tests passed; dashboard snapshot tests: 35 passed.
- Full-suite dashboard module subsequently passed all 215 tests with host process visibility, resolving sandbox-only focused-run failures.
- Seven helper/census in-memory mutations killed with assertion failures and zero infrastructure errors, recorded in author-mutations.json. Eight guidance phrase-deletion controls are durable tests in test_fixture_fidelity_guidance.py. These pins prove contract presence/transport only, not agent adherence.

Author mutation replay: run `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B 'docs/waves/1yd24 fixture-fidelity/author-mutation-probe.py'` from the repository root; this runs in-memory variants and disposable fixture roots. Interpreter must satisfy project test dependencies. Named tests and original outputs are summarized in author-mutations.json.

## Review identity and limits

Delivery-fingerprint.json contains per-path Git blob hashes and the aggregate. Recompute each with `git hash-object <path>`, then compute SHA-256 over Python `json.dumps(path_to_blob_hash, sort_keys=True).encode()` with default separators; this is the exact aggregate recipe. Source remains frozen for independent review; no commit, closure or operator approval is implied.

First frozen-tree full suite passed: 9,442 tests across 117 files in 290.430s, with 12 existing skips. Independent delivery review found missing discriminating controls for six strict helper guards. Two added tests exercise all six controls: explicit invalid helper inputs and malformed Prepare envelopes after real receipt publication. All six deletions now fail named tests with zero errors/skips; the 16 fixture/guidance tests pass. No helper behavior was changed. Both independent contexts completed focused reverification: all six mutants killed, 16 tests green, unchanged source fingerprint. Typed reverifications clear both blocking lanes. Final full suite passed: **9444 tests across117 files in281.625s**, with12 existing skips. Receipt result is `ok`; coordinator recomputed inputs hash `4decf445ea1e79f2584c875baea38b21ba8179d1aa445eb7abaa67b5107c6132` exactly. Full docs validation passed, with only the existing nonblocking AC wording advisory. The durable replay is repair-mutation-probe.py, using the same PYTHONPATH/interpreter command as the author probe; results are repair-mutations.json.

## Status-order repair integration

Operator-requested bounded repair applies synthetic status after every producer and rejects legacy ready. Two source paths changed; guidance and runtime remain unchanged. Independent code and QA reverification detected both old-order and ready-restoration mutants, plus all six earlier controls. See status-order-review.md and status-order-mutation-probe.py.

Final replacement receipt: **9444 tests across 117 files**, 12 existing skips, 294.428s, OK. Inputs hash `1b37f7821ab1163954e6ac71e32ca64496ef88208578afbcd0c4118ca65845c5` independently recomputed by coordinator against the current tree. Source fingerprint `cdc9ed9135af6cc1b508a349f858cca75810a0e1db9d00924f743c76447f2c61`. Prior receipt/fingerprint entries above are historical.
