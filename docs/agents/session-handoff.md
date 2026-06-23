# Session Handoff

Owner: Engineering
Status: in_progress
Last verified: 2026-06-23

## Active wave: `1p7de graph-edge-trust` (OPEN)
- **`1p7df` transitive-confidence-propagation — IMPLEMENTED.** AC-5 open (consumer-pack before/after pending a repacked build).
- **`1p7dg` cross-file-receiver-resolution — IMPLEMENTING + AC-1 COMPLETE + reframe pending sign-off.**
  - **Python promotion shipped locally** (`graph_indexer.py` ~5850 same-file extraction-site promotion): Python EXTRACTED 90.4%→36.5%, resolved 1,136→7,558. 6 tests; suite 3406 OK; gate closed.
  - **AC-1 spike complete across the consumer pack (6 surfaces):** Python PROMOTE 64.8%, Java (`aceiss/javaagent`) PROMOTE 32.1%, Swift (`solaris`) PROMOTE 36.8%, TypeScript (`aceiss/teton`) marginal (15.6% cross-file), JS DROP (near ceiling, already v23), SQL anomaly (100% EXTRACTED — no resolution pass; separate follow-on).
  - **DECISIVE FINDING:** `resolve_unique` (resolver-extension headroom) is negligible in ALL six (1.3–3.8%). The wave's original "extend the per-language resolvers" premise is empirically unsupported. The actionable, faithfulness-benign lever everywhere is **confidence promotion**. Cross-file promote bucket ≈2,721 edges across the pack (Py 552/Java 315/Swift 680/TS 713/JS 44/SQL 417).
  - **PROPOSED REFRAME (needs operator sign-off — council-approved scope change):** rescope `1p7dg` from "cross-file receiver resolution (extend resolvers)" to "generalize the confidence promotion": (a) one language-agnostic cross-file unique-resolution promotion in the rewrite stage; (b) per-language same-file promotions for Swift (~761) + Java (~247) [Python shipped]; NOT resolver extension, NOT the SQL pass. AC-6 faithfulness review is light (no new bindings, label-only).
  - **Open ACs:** AC-1 ✅; AC-5 builder bump (deferred, shared w/ 1p7dh); AC-6 faithfulness review (light); the reframe + the cross-file/same-file implementation itself.
- **`1p7dh` string-literal-arg-extraction — NOT STARTED.** Shares the deferred builder bump.

## Spike instrument
`experiments/1p7dg-spike-receiver-headroom.py` (canonical, correct — line 187 loads payload). NOTE: the hand-trimmed paste block forwarded to downstream agents dropped that one line; re-send the FILE verbatim if more runs are needed.

## Uncommitted (operator-directed + wave work — needs commit decision)
1. Lifecycle shortcut-phrase standardization (~30 files).
2. `1p7df` (+ reranker fix).
3. `1p7dg` (graph_indexer.py promotion + tests; change-doc AC-1 + spike findings; handoff; `experiments/` spike).
Recommend separate logical commits when ready.

## Done earlier this session
- 1.8.0 RELEASED; dist cleaned; live release page Upgrade section patched.

## Planned, not started
- `1p6lp cross-host-skills`.
