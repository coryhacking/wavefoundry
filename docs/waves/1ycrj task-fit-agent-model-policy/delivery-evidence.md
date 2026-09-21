# Delivery Evidence

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Final result

Neutral fresh model/effort defaults, preservation of existing wrapper headers (including BOM and CRLF), and task-fit delegation guidance are implemented. Both typed findings are terminal: MODEL-READY-1 clarified whole-render preservation; MODEL-BOM-1 fixed silent loss of BOM-prefixed headers. Code, QA, docs-contract and readiness council approvals are current; the operator independently verified the repair and authorized closure.

- 236 focused renderer tests pass. BOM rows fail against the old check; independent valid and malformed old-check mutations were rejected.
- Full suite: 9,452 tests across 117 files, 12 skips, 293.628s. Green receipt recorded 2026-09-21T17:06:05.478207+00:00; framework inputs hash `f32695c6f1743b84f994f6d742e96bac32b21b74e643fa22257866900eb6fff0` independently verified by coordinator and QA.
- Docs validation and diff whitespace checks pass. Real-repository rendering is a no-op.
- Five local wrapper changes remove only their provenance-proven `model: sonnet` line. Existing permissions are preserved; upgrade guidance surfaces stale allowlists and protects deliberate restrictions.
- No live model calls, observed runtime identity, cost savings or complete packaged-upgrade claims. The upgrade probe proves fresh on-disk renderer loading in a subprocess; extraction ordering was source-verified.

## Evidence index

| Stage | Record |
| --- | --- |
| Original readiness | [readiness-review.md](readiness-review.md) |
| Whole-render contract repair | [readiness-delta.md](readiness-delta.md) |
| Initial delivery, before BOM discovery | [delivery-code-docs.md](delivery-code-docs.md), [delivery-qa.md](delivery-qa.md) |
| BOM repair and negative controls | [bom-code-docs-review.md](bom-code-docs-review.md), [bom-qa-review.md](bom-qa-review.md) |
| Final readiness delta | [bom-readiness-delta.md](bom-readiness-delta.md) |
| Final source packet | [evidence/delivery-fingerprint.json](evidence/delivery-fingerprint.json) |
| Historical packets | [initial](evidence/delivery-fingerprint-initial.json), [pre-BOM](evidence/delivery-fingerprint-pre-bom.json) |
| Upgrade reproduction | [evidence/upgrade-render-probe.py](evidence/upgrade-render-probe.py) |

Final source fingerprint: `1f5f39ecbe246fa2d9fd638adb2eddfd6d4a3bd7d15aee983c098e9198590ffa`. Reproduce by computing git blob hashes for the listed paths, then SHA256 of `json.dumps(paths, sort_keys=True).encode()` with default separators. Ledger-cited reports remain at their original paths; historical bare fingerprint filenames now resolve under `evidence/`. The append-only events ledger is unchanged by cleanup.

## Retrospective and memory disposition

Non-obvious lesson: recognize the UTF-8 BOM before deciding a wrapper is headerless, and verify every writer in the full rendering lifecycle. These behaviors are now pinned by regression tests; policy ownership and stale-allowlist reconciliation live in canonical seed guidance. No separate durable instruction is needed.

The attached MCP process could not establish its memory fence. The same canonical authoring API in a fresh local process created candidate `1yk7h-mem repaired-defect-model-bom-1`; supported CLI validation rejected it after evidence review because it targeted a disposable probe and duplicated tested behavior. Its rejected source-event disposition prevents regeneration. No memory candidates remain pending.

Scope checks preserved the preexisting prompt-surface-manifest.json, codebase-map.md and repo-index.md differences. Closure-generated refreshes are separate from those preexisting edits. No AC or task was deferred.
