# Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Scope and baseline

Wave `1ypxw` implements all three admitted changes. The pre-wave snapshot includes the uncommitted completed `1ypy6` work; HEAD alone is not this wave's baseline. Source fingerprints are retained in `evidence/delivery-tree.json`, `evidence/delivery-tree-repaired.json` and `evidence/delivery-tree-final.json` for the original 45-path delivery tree, C-1 fixture repair, and final 48-path tree. Reviewer reports identify which snapshot they verified.

At delivery handoff neither commit nor closure was authorized; the operator subsequently authorized closure on 2026-09-22. Commit remains unauthorized. Both edit gates are closed. Native Windows and downstream package installation were not exercised.

## Independent review and repairs

Fresh delivery contexts reviewed code, QA, and architecture/docs contract. Architecture and docs-contract judgments share one context and are correlated; code and QA used separate contexts. Original reports are `evidence/delivery-code-review.md`, `evidence/delivery-qa-review.md` and `evidence/delivery-arch-docs-review.md`. They did not implement the wave or reuse readiness contexts. Requested runtime settings were inherited; observed model identity is unknown.

C-1 identified stale exact-source handler fixture hashes for the two deliberately changed tool descriptions. Only those hashes and fixture provenance changed; the other 87 hashes, hash algorithm and negative control remain intact. Fresh independent review in `evidence/C1-reverification.md` ran 27 registry tests and killed an affected-wrapper docstring mutant. All 110 wrapper ASTs match pre-wave after omitting docstrings.

C-2 identified two stale verification expectations: exactly five QA conditions despite the admitted conditional sixth rule, and a census allowlist entry for removed renderer prose. The repair updates the numbering/conditionality assertions and removes only the stale active allowlist entry; the historical SITES row remains. Fresh QA review in `evidence/C2-reverification.md` passed eight tests, verified the original five seed conditions byte-identical, and killed four missing-rule/relaxed-census mutants. Both findings are terminal in the typed ledger; history is retained.

## Verification

Builder verification: 407 core tool tests, 237 renderer/platform tests, 258 seed/surface tests and 13 public-tool golden tests passed in their documented focused runs. Independent code review passed 173 targeted tests; QA passed 44; architecture/docs passed 20. These are overlapping suites, not an additive unique-test count. Reports record exact commands, known-bad controls and limitations.

The first canonical full run executed 9,533 tests and failed three modules on the C-1/C-2 expectations above. The subsequent canonical full run passed all 9,533 tests across 121 files in 322.799 seconds, with 12 intentional skips; it wrote the current green framework receipt. Full docs validation passed after report metadata corrections. Final surface synchronization wrote no files. The tool-surface and both lifecycle golden JSON fixtures remain byte-identical to the pre-wave snapshot; the separate handler-digest fixture's two authorized updates are explicitly distinguished.

Public review prompt size changed from 10,221 to 9,127 UTF-8 bytes; the agent body changed from 5,968 to 4,780. The generic fresh-install template grows from 3,099 to 5,874 bytes to carry missing lifecycle requirements. These are entry-surface byte counts, not measured model-token savings or end-to-end efficiency gains. `seed-surface-inventory.md` records sentence disposition, propagation, retained naming hits, protected markers and manifest checks.

## Retrieval integration

The before receipt is `docs/reports/retrieval-quality-1ypxw-before.json`, recorded before source edits on stable complete generation 1944. The after receipt `docs/reports/retrieval-quality-1ypxw-after.json` passes the cross-generation comparison: generation 1949 remained complete with attempt `d483324f01a445edb23c97778e876222` throughout; production end digest verified; no invalidation reasons, operator-review reasons or quality violations across 27 compared fixture keys. After report file SHA-256: `ddd38ec7c9a081ca2b990af20407903c1e48ef6559f1558ebd85ffce7f7ab991`. Both constituent runs were stable; different corpus generations make this non-regression evidence, not a causal performance-improvement claim. Command: the retained `eval-quiet-window.py` wrapper with `--out docs/reports/retrieval-quality-1ypxw-after.json --baseline docs/reports/retrieval-quality-1ypxw-before.json`. All eleven before production-module hashes match the retained pre-wave files; only `server_impl.py` differs in the measured module set. `evidence/retrieval-production-reverse.patch` and `evidence/retrieval-production-delta.json` retain byte reconstruction and changed-function evidence. No index rebuild was requested.

The attached MCP's setup assessment retained `loaded_code_stale`; a fresh `wf setup --check --json` process reports ready with no reasons/actions. Index operations and evaluation use freshly loaded CLI code. The canonical test runner selects the existing shared tool venv; a standalone system-Python probe lacked `mcp`, but the full runner's registry failure was only the stale handler fixture, not a missing dependency. No packages were installed.

## Memory and handoff

`memory_propose` produced candidate `1yoc3`; focused curation rejected it as a duplicate of the canonical advisory-only evidence specification. Rejection history is retained; no memory was promoted.

All 16 ACs and every implementation task are complete. Code, QA, architecture and docs-contract delivery approvals are current in the typed ledger; C-1 and C-2 are terminal. The full-suite receipt is current (`inputs_hash: c7ad178ba2f8223f4ca113aa9970edfabba9cac9e2cb0f1bcd25d834afb8792e`, `result: ok`, 9,533 tests). Operator signoff, closure and commit remain pending explicit instruction.

## Close dry-run

Final dry-run proves the current green framework receipt and reports only the missing operator approval (including its aggregate evidence diagnostic). All required specialist approvals are current, all AC/task checkboxes are resolved, and both repair heads are terminal. Closure was not executed. Scanner coverage retains 13 pre-existing binary-file skip records; no new coverage claim is inferred for those files.

## Closure reconciliation

The operator supplied a further independent evaluation (tools: 1,094 focused tests and three controls; seeds: 163 and four controls; surfaces: 224 and two controls), plus a green 9,533-test whole-suite run. These are operator-reported results, not additional coordinator executions. The three final documentation corrections were checked: CHANGELOG covers the gate and fresh template; the propagation inventory maps local dispositions explicitly; the change log locates parity validation in `wave_lint_lib/core_validators.py`. The inventory's grouped seed-180 row count was corrected from eight to nine. Existing docstring wording remains precise.

Closure authorization supersedes the pending-operator statements above. No source edits or new behavior resulted from closure reconciliation. Folder cleanup retains unique reports, controls and historical fingerprints with stable cited paths; no disposable file was identified. Memory proposal at close returned zero candidates and retained the prior rejected duplicate. Scanner coverage still has 13 pre-existing binary skips.
