# Make distribution test oracles portable

Change ID: `204ml-bug distribution-test-oracles`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-08
Wave: `204mp waveforge-follow-up`

## Rationale

Waveforge’s renamed tree still fails framework tests because the oracle assembles canonical keys, scans downstream-owned fixtures, reads a checkout-owned spec, or embeds rename-sensitive examples. Establish framework-owned, independent oracles without reducing coverage. Addresses Waveforge public request C1–C3 against `d11da852`, received 2026-10-08. Deliverable: framework fixes, focused regression evidence and documented compatibility behavior. This document authorizes planning only; implementation follows admission and readiness.

## Requirements

1. Write canonical prompt keys literally in the reconcile expectation; retain a controlled negative case proving assembled keys are detected.
2. Use a checked-in, sorted framework-relative text-file ownership inventory for the actor census, including zero-hit production files and framework-owned tests/fixtures. Downstream-added files are outside that set; unexpected occurrences in every owned file still fail. An explicit maintainer update command regenerates the inventory from the upstream tracked source tree; ordinary downstream test runs never expand it from their checkout. Missing owned files and stale occurrence allowances remain errors. Cover the inventory itself without creating self-referential token counts.
3. Check the shipped journal seed or a controlled fixture instead of the checkout’s project spec.
4. Derive legacy digest inputs from the declared legacy-key table and built-in legacy actor. Compute the expected digest with a test-local frozen pre-alias payload encoder for the tiny fixture: explicit schema/evaluator values and payload fields, literal fixture body hash, canonical JSON and hashlib only. It must not call policy_input_snapshot, _digest_wave_review, or the current body canonicalizer. Preserve a shipped-default golden vector and the no-phases pin as independent checks of that reference; on renamed profiles compare to the independently encoded legacy input instead of comparing renamed bytes to an upstream-language digest. Preserve legacy/current equivalence and reject a deliberately changed payload field or key normalization.
5. Use neutral override examples and a controlled synthetic chain that retains slug-reuse and collision coverage. Canonical lookup keys stay literal.

## Scope

In scope: the public request C1–C3 and the declared review targets below.

Out of scope: other requests, native host hook classification, packaging skip-parity policy, publishing, release creation, and unrelated refactors.

## Acceptance Criteria

- [x] AC-1: A renamed-profile fixture passes reconcile-key expectations, while a deliberately assembled production key is detected.
- [x] AC-2: A downstream-only actor fixture does not fail the census; an unexpected actor in a framework-owned source or fixture does.
- [x] AC-3: Changing the target checkout spec cannot affect the hook-contract test; a missing contract in its controlled source fails it.
- [x] AC-4: Legacy/current digest equivalence and an independent historical compatibility oracle both pass under default and renamed profiles; a digest behavior regression is detected.
- [x] AC-5: Neutral prompt examples retain chain-reuse, collision rejection and first-render identity coverage under both profiles.

## Tasks

- [x] Define the owned census set and independent historical digest oracle at readiness.
- [x] Repair literal-key, seed-contract, digest and prompt-chain fixtures.
- [x] Run affected tests in default and renamed profiles, including negative controls; record skip deltas.
- [x] Update testing documentation and collect independent code/QA delivery evidence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and fixtures | Implementer | Readiness | Own declared source/test edits only |
| Documentation | Technical writer | Contract | Own named documentation; coordinate shared files |
| Independent review | Code reviewer and QA reviewer | Implementation | Read-only review and evidence; additional lanes selected at Prepare |

## Serialization Points

One writer per shared file. Complete test-oracle repairs before consumers extend those tests; serialize `upgrade_extensions.py`, shared profile modules and the MCP surface specification across changes. Reviewers do not edit implementation files. Generated local surfaces are regenerated from canonical sources, never patched in lieu of seeds.

- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_council_signoff_keys.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/prompt-names.json`
- `.wavefoundry/framework/scripts/tests/fixtures/framework-text-ownership.json` (new explicit upstream census inventory)
- `.wavefoundry/framework/scripts/tests/` inventory-maintenance helper and directly affected support, scoped to this census

## Affected Architecture Docs

docs/architecture/testing-architecture.md: document framework-owned fixture boundaries and profile qualification. No runtime behavior changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Direct evidence for the requested compatibility behavior |
| AC-2 | required | Direct evidence for the requested compatibility behavior |
| AC-3 | required | Direct evidence for the requested compatibility behavior |
| AC-4 | required | Direct evidence for the requested compatibility behavior |
| AC-5 | required | Direct evidence for the requested compatibility behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Planned from public report and current source inspection; not implemented or readied | Declared source targets and request C1–C3 |
| 2026-10-08 | Readback: repair C1–C3 only. Expected literal lookup keys, a sorted upstream-owned inventory independent of downstream files, the shipped seed contract, and a frozen historical digest encoder. Neutral staged item names preserve the real prompt chain: implement-parcel moves to do-task while the container takes implement-parcel. Default pins remain unchanged. | AC-1–5; declared test files, fixture and census helper; no runtime source changes |
| 2026-10-08 | Thought/Observe: source reads confirmed verb concatenation, checkout-spec dependency, rename-sensitive digest pin/skip and actual-name chain. MCP code tools callable; pre-implementation memory brief and current-memory guidance read. Scope remains admitted C1–C3. | Source readback and current readied 204mp |
| 2026-10-08 | Observe: C1–C3 literal keys, explicit inventory, shipped-seed contract and independent historical payload oracle are complete. Neutral fixtures stage actual parcel slug ownership, preserving the two-stage migration rather than relying on a real distribution vocabulary. | Affected default owners: 107 tests, 0 skips, 46.597s; combined second-profile and literal prompt-key/built-in-actor renamed scratch tree: 51 tests, 1 pre-existing checkout-manifest default-only skip, 38.656s; new skip delta 0. Historical digest test executes under renaming. C2 controls: 3 tests, 0 skips, 0.076s. Inventory 523 paths; explicit maintainer check rejects omitted/extra owned paths, exit 2. |


## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Repair test inputs and preserve independent negative controls. | Preserve the requested behavior and existing compatibility boundaries | Skipping downstream failures loses coverage; teaching production code about test-only aliases expands the runtime contract without fixing the oracle. |

| 2026-10-08 | Select explicit tracked-source ownership inventory and a frozen test-local historical encoder with golden cross-checks. | Downstream files cannot silently enlarge the census; renamed legacy inputs retain an oracle independent of the implementation under test. | Scanning every checkout file conflates ownership; allowlist-only scanning misses new occurrences in zero-hit files; deriving expected hashes through current production functions is circular. |

## Risks

| Risk | Mitigation |
| --- | --- |
| An oracle derived entirely from the tested implementation could pass a shared defect. | Require independent compatibility evidence and known-bad controls, not only green renamed runs. |

## Session Handoff

See `docs/agents/session-handoff.md`. Readiness must resolve the design choices named above before implementation.
