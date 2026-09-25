# Independent Package Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Verdict

Approve with an evidence qualification; no new blocking defect. Two reviewer contexts independently checked the final implementation: extension_code_security (code/security) and pin_readiness (QA/release). Both were reused from unrelated reviews and had no implementation or repair involvement in this wave. These are two contexts covering paired roles, not four isolated seats or a new council. The coordinator authored the original plan, reviewed current architecture/specs, reran equivalence and inspected the nine adapted functions; that work is not represented as a fresh independent council.

## Verified results

- Code/security: nine targeted identity, alias and reload tests pass. A real-runner probe completes three successive reloads: all 12 flat/canonical/parent bindings agree; 11 reloadable modules refresh; server_impl retains its object. Twenty reviewed-file fingerprints unchanged.
- QA/release: 25 package tests and 25 extension tests pass without skips. All 157 reviewed source/test fingerprints unchanged.
- Move equivalence: 559 top-level definitions across 12 modules have no unexpected difference after mechanical rewrites. Nine server_impl path adaptations were separately inspected. Module-level statements are an explicit exception, not covered by the definition-equivalence claim.
- QA independently recomputed the full-suite receipt: 9,661 tests, result ok, ran_at 2026-09-25T17:19:21.143111+00:00, inputs_hash 49ae41c820e0009933abc30c5fcf108fcfa6a447d48a77060cf7b9ba8e026566. No full-suite rerun in this review.
- Docs validation on review entry and git diff --check passed.

## Mutation evidence

| Lane | Mutation | Detection |
| --- | --- | --- |
| Code/security | Flat-only purge | Dual-key coverage assertion fails |
| Code/security | Remove eager aliases | Fresh-process identity observations fail |
| Code/security | Restore stale parent registry import | Actual reload retains old registry classes |
| Code/security | Remove full-flat refusal | Malformed compatibility file imports successfully |
| Code/security | Omit reserved handler name | Reserved-name inventory assertion fails; structural proof only |
| QA/release | Restore hollow loader return | Loader returns the hollow flat object instead of package implementation |
| QA/release | Read flat alias for harness coherence | Real wf_graph_report incorrectly reported stale |

All seven bounded mutations were detected; no surviving mutant required a broader sweep.

## Evidence qualifications

E1/E2 remain a valid historical comparison: evaluator and fixture identities match, complete generations are stable (2098 and 2106), and there are no violations or invalidation/operator-review reasons. E2 predates the final alias-integrity guard. Its production digest is 0f306808fe06bc1db7b4f65610cda86e57d0cb335be9b421bea308ae73447d5f, versus final ac5b0f7c74732946988a507bd4f40c55b09f6fe2a5d290cd953868d92a14686a; only measured server_impl differs. The reference narrative now qualifies this. No changed retrieval-ranking mechanism was identified; hash mismatch alone does not require a new benchmark. Final focused tests and reload probes cover the later repair, which the broad module-statements equivalence allowance cannot prove by itself.

The retained old-runner matrix proves installed 1.25/1.26 runners accept/extract the package and reach the historical-memory gate, after which the extracted tree passes dry-run and real stdio wf_server_info. It does not prove completed upgrade cleanup: cleanup correctly remains blocked pending memory handling. QA independently verified the release-tag validator functions are AST-identical to current and checked their committed positive/negative tests. This review did not rerun the historical upgrade/dashboard or retrieval matrix, and makes no native Windows claim.

Existing-resource warnings appeared during repeated reloads; identity checks still passed. No new security boundary issue was found within the documented trusted-distribution contract. No source changes, operator signoff, closure or commit were performed.
