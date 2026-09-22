# Handler Module Split Two Independent Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Phase: delivery. Contexts: `1ymzk-indep-code-20260921`, `1ymzk-indep-qa-20260921`, `1ymzk-indep-arch-20260921`, `1ymzk-indep-redteam-20260921`. Four contexts spawned fresh for this review; none was retained from readiness, implementation or the cycle-1 repair, and none is the builder. Requested at the operator's direction after the builder's delivery approvals; run against the uncommitted tree at HEAD `f7f95d5e`.

## Lanes

| Lane | Verdict | Basis |
| --- | --- | --- |
| code-reviewer | approve | All 48 moved definitions and objects absent from `server_impl.py`, present in their module, and AST-identical to HEAD after normalizing the mechanical rewrite (function-level `import server_impl`, qualified reads of eleven staying helpers). One rebinding block per module with no aliases; identity holds for every re-export including both caches, the bypass sentinel and the token regex. No module-top `server_impl` import; no handler-to-handler import at any scope; both purge entries present as plain strings. `register_mcp_surface` byte-identical to HEAD (234,786 bytes), golden fixtures untouched. `memory_cli` inverted, `memory_eval` unchanged, `_load_script` indirection kept, seven `server_impl.project_state_publication_lock` reads. Five stayers bound in `_STATE_SOURCE_EXTRACTORS`. |
| qa-reviewer | approve | Every hunk of the eight-file test diff maps to a plan item or a recorded cycle-1 repair; no assertion weakened. Seven scratch-tree mutants (two dropped re-exports, two dropped purge entries, a module-top `server_impl` import, a duplicate definition, a memory reach inserted into `code_search_response`) each killed by a named test. 2,069 tests across the eight named modules green, no skips. Exactly four moved-to-moved patch sites, all repointed and asserting the patch was hit. Receipt `58bd9cc3` matches `run_tests._hash_inputs()` on the current tree. |
| architecture-reviewer and docs-contract | approve | Import graph: composition root imports the four handler modules at module top; every handler reaches `server_impl` per call only; `memory_cli` imports `memory_handlers` at top; `memory_eval` still imports `server_impl` per call. Independent over-approximate closure from the four measured tools reaches 96 `server_impl` and 3 `codenav_handlers` definitions and zero memory or techdocs definitions; `retrieval_eval.py` unchanged. Architecture docs, the two standing-baseline references and the `test_docs_lint.py` pin agree on `retrieval-quality-1ymzk-after.json`; CHANGELOG bullet present; codebase map regenerated. |
| red-team (evidence) | two blocking record defects, repaired | Below. |
| coordinator run | green | Full suite with `--no-cache`: 9,481 tests, 119 files, 12 skips, OK. |

## Red-team findings and repair

1. The before receipt's `fail` and the after receipt's `pass` differ because of index composition, not code. Generation 1861 held thirteen test-directory paths the index policy excludes, occupying top-10 slots on both failing fixtures; the reaper pass at `2026-09-21T17:20:27-0600` removed 187 stranded paths and 3,651 rows before the after run at generation 1869. All three repetitions per side are rank-identical. The delivery review called the fail pre-existing and the computed before/after file the wave's comparable pair; both paragraphs are rewritten to name the reap and to rest the no-regression claim on the signed after receipt against `1y0bf-final`, whose baseline generation 1772 is a policy-conformant corpus under the same evaluator identity.
2. The builder's code/QA and architecture contexts were retained from readiness through the cycle-1 reverifications and the delivery approvals while recording `fresh_context: true`, which seed 209 defines as no retained context; the lane reports disclose the reuse and the context-id suffixes exist to avoid identity collisions. Repair: this review's four newly spawned contexts independently re-verified the code, the tests, both cycle-1 repairs (the record-layout literal moved with its only occurrence; the lock visitor now scans both owners and both call forms with negative controls, thirteen sites against a floor of eight) and the architecture docs, and their delivery approvals are recorded in the ledger from distinct contexts. The retained-context rows stay in the ledger as history with the disposition note in `delivery-review.md`.

Verified as holding: both content hashes the delivery review quotes, the evaluator identity in both receipts and the tree, the production digest of the after receipt, byte-level reproduction of the computed comparison from the documented command, the baseline choice (`post-1wybs` binds a different evaluator), the three suite logs and the receipt hash.

## Advisories

- The reaper strips the same ~187 policy-ineligible paths on every generation since 2026-09-19; something re-adds them. Framework defect, follow-up plan.
- Both change docs carry Progress Log rows appended after the Session Handoff section, one with run-together tokens.
- The committed invalid receipts `retrieval-quality-1ymzk-before.json` and `retrieval-quality-1yljp-before.json` are not listed in the evidence-retention record that `review-and-evals.md` designates for invalid attempts.
- The CHANGELOG diff carries eleven backfilled bullets for other waves.
- The first suite run's dashboard failures are attributed to the sandbox by shape, not by an error in the log; the host rerun of the unmodified file passed.
- The ledger carries no timestamps, so approval ordering is provable only by content (the final rows cite artifacts that exist only after the repair suite).

Requested lane settings: host default model and effort for all four lanes. Observed runtime identity: unknown. Limits: patch-site and closure censuses are AST-based and do not follow `_load_script` string dispatch; mutants ran in scratch copies where two root-fixture tests error for path reasons and are excluded from kill counts.
