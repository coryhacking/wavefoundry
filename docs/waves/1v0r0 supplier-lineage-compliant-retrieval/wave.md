# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v0r0 supplier-lineage-compliant-retrieval`
Title: Supplier Lineage Compliant Retrieval

## Objective

Replace the split BAAI-code/Arctic-XS-docs configuration with one Snowflake
Arctic S embedder shared by both semantic layers, retain MiniLM L6 for current
reranking semantics, and ship the changed offline model set as v2 with
Wavefoundry `1.16.0`. Keep document and code selection independently
configurable, while assigning Arctic S to both for this release.

## Changes

Change ID: `1v0qz-enh supplier-lineage-compliant-retrieval-models`
Change Status: `implemented`

## Participants

- Coordinator: implementation-coordinator
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer, security-reviewer

Completed At: 2026-08-11

## Wave Summary

Wave `1v0r0` (Supplier Lineage Compliant Retrieval) delivered one change: Supplier-Lineage-Compliant Retrieval Model Swap. Notable adjustments during implementation: Supplier-Lineage-Compliant Retrieval Model Swap: Expanded the document bake-off and selected Arctic S as the single embedder for both semantic layers.; Supplier-Lineage-Compliant Retrieval Model Swap: Removed automated jurisdiction validation and added model bundle v2 to the release scope.; Supplier-Lineage-Compliant Retrieval Model Swap: Added the bounded batch-log and canonical-bundle-binding repairs exposed by final lane review.

**Changes delivered:**

- **Supplier-Lineage-Compliant Retrieval Model Swap** (`1v0qz-enh supplier-lineage-compliant-retrieval-models`) — 10 ACs completed. Key decisions: Replace BAAI with Arctic S for code and retain Arctic XS for documents.; Retain the current L6 logical model and Xenova artifacts on CPU and GPU.
## Watchpoints

- Activation watchpoint: another session currently owns the single OPEN wave
  slot. Readiness may proceed in parallel and leaves this wave planned; only
  implementation activation must wait until the OPEN slot is released.
- The reranker remains MiniLM L6 at its independent batch 40. L2 is not an
  implementation option in this wave. Reranker removal is also out of scope:
  it requires revalidating `code_ask` relevance calibration, abstention,
  cross-source selection, and confidence through the broader `1seaw` suite.
- Arctic S is the only active/bundled/setup-required embedding model for v2;
  two separate document/code selectors both name it and resolve the same
  model-name-keyed in-process instance. Do not collapse those selectors into
  one authority.
  Existing Arctic XS cache bytes are benign unmanaged residue and are not part
  of the operator-requested retired-BAAI cleanup.
- Accurate historical records and unrelated or operator-managed caches are
  preserved, but no active/default/bundled/setup path may select or require
  BAAI. Starting with `1.16.0`, upgrade removes only exact retired BAAI-derived
  artifacts owned by Wavefoundry, and only after verified v2 model and complete
  semantic publication.
- Obsolete BAAI and Arctic XS runtime/acquisition/setup/package mappings are
  removed, not left behind as unreachable compatibility code. Only the exact
  cleanup, migration/comparison test, and truthful historical references remain.
- Equal-ID document/code builds choose one execution class before model load:
  bulk if either layer requires bulk, otherwise the existing small-run CPU
  class. This prevents a mixed incremental build from allocating two Arctic S
  instances while leaving divergent model IDs independently configurable.
- Supplier origin is reviewed manually whenever a model is swapped; no runtime
  jurisdiction validator is part of this wave.
- The next release must publish and select `wavefoundry-models-2.zip`; model set
  v1 remains an immutable historical bundle identity.
- Release version: `1.16.0`, including its exact VERSION stamp and changelog
  heading.
- **Accepted delivery residual (carried, optional future hardening):** the
  no-fd cleanup fallback `_remove_retired_component_no_follow` retains one
  single-syscall check-to-use sub-window between its pre-descent re-lstat and
  the `os.scandir` that follows. Independently reproduced by red-team and
  security: reached only on the native-Windows fallback path (permanently
  missing `dir_fd`/`rmtree.avoids_symlink_attacks`), it fails closed, is
  strictly narrower than the pre-repair window, and is disclosed verbatim in
  the function docstring and the CHANGELOG narrower-guarantee sentence. It is
  the irreducible limit of any path-based fallback without fd-anchoring (same
  class as the stdlib `shutil.rmtree` residual on such platforms). Fully
  closing it needs a Windows-native `O_NOFOLLOW` fd-scandir reimplementation,
  disproportionate to a single-syscall race with no attacker rendezvous;
  promotion trigger: a physical Windows host demonstrates practical
  exploitability, or the fd-scandir hardening is scheduled.

## Review Checkpoints

- **Product-owner acknowledgment — 2026-08-10: ACKNOWLEDGED.** The operator
  approved Arctic XS for documents, Arctic S for code, embedding FP16 GPU /
  INT8 CPU at batch 32, and retained L6 reranking at FP16 GPU / INT8 CPU with
  independent batch 40. The operator also approved model set v2 shipping with
  Wavefoundry `1.16.0`, followed by bounded removal of retired BAAI-derived
  Wavefoundry cache artifacts after successful v2 convergence.
- **Initial red-team primer — 2026-08-10: SUPERSEDED.** Context
  `1v0r0-redteam-20260810-supplier-lineage-01` found an L6 logical-ID/artifact
  conflation, an uncovered background cold-cache acquisition path,
  under-specified lineage validation, and a discretionary retrieval fixture.
  Its expanded-policy repair was later superseded when the operator narrowed
  the wave to the direct model swap, manual supplier review, and bundle v2.
- **Initial docs-contract recheck — 2026-08-10: SUPERSEDED.** Context
  `1v0r0-docs-contract-20260810-final-03` approved the repaired expanded draft;
  a new council review is required for the operator-narrowed plan.
- **Narrowed red-team primer — 2026-08-11: CHANGES REQUESTED, REPAIRED.**
  Context `1v0r0-redteam-20260811-modelswap-02` found that a v2 shared
  fingerprint cannot promise a code-only rebuild and that manual supplier fields
  cannot be appended only to the canonical generated manifest. The plan now
  requires one atomic full semantic rebuild and keeps the manual supplier
  decision in the separate model-selection record. Hardware timing is controlled
  release evidence rather than a portable CI assertion.
- **Architecture rotating seat — 2026-08-11: PASS.** Fresh context
  `1v0r0-architecture-20260811-modelswap-03` verified v1 immutability, complete
  v2 package/setup/upgrade selection, the shared-fingerprint full rebuild,
  generated-manifest equality, unreachable-only legacy BAAI aliases, and the
  controlled timing classification against current source.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  security-reviewer; rotating-seat: security-reviewer;
  strongest-challenge: migrate the shared model-set identity to v2 without
  mixed layers, breaking generated-manifest equality, or trusting a
  self-consistent substitute bundle; strongest-alternative: per-layer
  fingerprints could avoid rebuilding docs but are rejected as a broader
  architecture change than this model swap requires.)
- **QA readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh context
  `1v0r0-qa-20260811-modelswap-final-05` found that AC-9 could either overwrite
  the existing 32-query mixed benchmark or create an unnamed fixture. The plan
  now names a separate 28-query input, evaluator, committed result, controlled
  release command, and inference-free CI validator while preserving the
  existing fixture byte-identically. Final QA recheck remains required.
- **QA readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-qa-20260811-modelswap-recheck-06` verified AC-1 through AC-10,
  backward-compatible benchmark/test reuse, deterministic result validation,
  and existing 32-query fixture preservation against current test owners.
- **Code readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `1v0r0-code-recheck-20260811-modelswap-final-06` found the reranker
  success log uses embedding `STATIC_BATCH`; the plan now corrects it to
  `RERANK_STATIC_BATCH`, adds `server_impl.py`, and extends the existing success
  test to assert batch 40.
- **Security readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `1v0r0-security-20260811-modelswap-final-06` found offline
  materialization trusts a self-consistent incoming manifest without comparing
  it to the installed canonical authority. The plan now requires canonical
  equality and a self-consistent substitution mutant before cache publication.
- **Code readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-code-readiness-recheck-20260811-modelswap-07` verified the reranker-log
  repair, model-swap seams, shared-fingerprint rebuild, v2 packaging, and
  backward-compatible benchmark/test reuse against current source.
- **QA readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-qa-20260811-modelswap-last-07` verified all ACs remain testable using
  existing owners, and executed non-vacuous known-bad probes for the batch-log
  and self-consistent bundle-substitution cases.
- **Security readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-security-recheck-20260811-modelswap-final-07` executed the current
  self-consistent remanifest substitution, confirmed it is accepted today, and
  approved the bounded canonical-manifest binding and mutation test. No runtime
  jurisdiction validation is introduced.
- **Release readiness lane — 2026-08-11: CHANGES REQUESTED, REPAIRED.** Fresh
  context `CTX-1v0r0-release-final-20260811-A7C4` found that release and
  release-dry-run could still omit the companion model archive and that the
  exact framework version was unresolved. The plan now requires
  `--with-models` for both release modes, asserts the matching
  `wavefoundry-models-2.zip` receipt, and locks the release to `1.16.0`.
- **Release readiness final recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-release-readiness-recheck-20260811-1160-v2-08` verified exact
  `1.16.0` VERSION, changelog, feature-archive, and model-set-v2 agreement;
  traced existing setup/upgrade selection and shared-fingerprint behavior; and
  executed the current feature-only release-dry-run as a non-vacuous known-bad
  control for the new mandatory companion guard.
- **Post-readiness scope revision — 2026-08-11: RE-REVIEW REQUIRED.** The
  operator replaced the prior cache-preservation decision with bounded cleanup
  of retired BAAI-derived Wavefoundry cache artifacts on upgrades to `1.16.0`
  or later. The revision is destructive but narrowly contained: it runs only
  after verified v2 model and complete semantic publication, uses exact paths
  and ownership markers, preserves unrelated/shared caches and historical
  records, and makes failure explicit. The prior readiness receipt and affected
  approvals are superseded pending fresh review.
- **QA cleanup readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-qa-readiness-terminal-fields-recheck-20260811-14` verified the exact
  allowlist, no-follow and mutation-boundary controls, legacy marker fixtures,
  idempotent retry/failure projection, semantic version boundaries, stable
  all-layer authority, and Phase 4c suppression. Existing setup, upgrade, and
  model-bundle baselines passed, and the current detached follow-up is the
  non-vacuous known-bad control.
- **Release cleanup readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-release-readiness-public-cleanup-recheck-20260811-11` verified pack
  `to_version` precedence, freshly loaded cleanup ordering before restart/lock
  removal, complete all-layer convergence, exact failure recovery carriers,
  model-set-v2 packaging, and the `1.16.0` release boundary.
- **Security cleanup readiness recheck — 2026-08-11: PASS.** Fresh context
  `1v0r0-security-cleanup-public-contract-final-20260811-13` verified exact paths,
  default/custom-root ownership, symlink and check/use defenses, current-model
  veto, stable epoch authority, and lock-retaining failure. A temporary-root
  known-bad probe proved current cleanup can remove its lock while an epoch is
  still building.
- **Code cleanup readiness final — 2026-08-11: PASS.** Fresh context
  `1v0r0-code-readiness-cleanup-schema-final-20260811-15` verified the real
  cache producers and overrides, legacy marker inventory domain, composite
  model-version shape, canonical v2-or-later authority, retry seam, exact
  result carrier, and complete living-surface census against current source.
- **Architecture cleanup readiness final — 2026-08-11: PASS.** Fresh context
  `1v0r0-architecture-readiness-cleanup-envelope-final-20260811-13` verified
  `index-state.sqlite` remains the sole semantic authority, the stable
  token/summary/token contract, synchronous all-layer convergence with Phase 4c
  suppression, later-model-set coherence, historical-v1 separation, and the
  one-way state-store-to-cleanup boundary.
- **Docs-contract cleanup readiness final — 2026-08-11: PASS.** Fresh context
  `1v0r0-docs-contract-cleanup-readiness-terminal-fields-20260811-16` verified
  the literal failure phase, five flat response/lock/status fields, fixed
  path-free target and reason vocabularies, protected summary/envelope capacity,
  exact upgrade dry-run sentinel, deterministic retry contract, and complete
  canonical/rendered upgrade and release-document owners.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: destructive cleanup could run under incomplete authority
  or partially fail while canonical, rendered, MCP, lock, status, and dry-run
  surfaces omit or contradict its recovery state; strongest-alternative: clean
  only fixed default roots after synchronous publication and keep detailed
  cleanup outcomes log-only; disposition: the final exact-path, no-follow,
  immutable-marker, canonical-state, fresh-process, idempotent-retry, and five
  flat protected-field contract is proportionate and implementation-ready;
  red-team context: `1v0r0-redteam-20260811-cleanup-reporting-final-12`;
  docs-contract context:
  `1v0r0-council-docs-contract-20260811-cleanup-reporting-final-13`.)
- **Single-embedder scope revision — 2026-08-11: RE-REVIEW REQUIRED.** The
  expanded 100-query document comparison and operator direction supersede the
  previously approved XS-docs/S-code split: Arctic S is now the only active,
  bundled, and setup-required embedder for both layers. L6 remains unchanged.
  The earlier council checkpoint remains historical evidence for the cleanup
  contract, but it does not approve this model-unification revision. Prepare
  dry-run derived a pending replacement receipt; fresh readiness review is
  required before implementation.
- **Fresh single-S Council seats — 2026-08-11: CHANGES REQUESTED, REPAIRED.**
  Red-team context `1v0r0-redteam-fresh-20260811-single-s-cacheclass-01`
  identified the mixed small-run/bulk cache-class boundary; the plan now chooses
  one build-level class before loading equal-ID layer embedders. Docs-contract
  context `1v0r0-docs-contract-fresh-20260811-1b03c65efcb372f5c2cb-01`
  identified overly broad legacy test exceptions and an omitted authority file;
  the plan now carries a closed legacy-residue matrix and explicitly reviews
  `index_state_store.py`. Fresh rechecks remain required.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: equal model IDs can still allocate two instances when
  independent document/code loads straddle the small-run/bulk threshold;
  strongest-alternative: cache only by model ID, rejected because the first
  layer would incorrectly determine the execution class; disposition: preselect
  one build-level execution class for equal-ID layers, construct once and share,
  retain divergent-ID independence, and enforce the closed legacy-residue
  matrix; red-team context:
  `1v0r0-redteam-20260811-equal-id-recheck-7f3c9a`; docs-contract context:
  `1v0r0-docs-contract-fresh-20260811-single-s-recheck-0b21e0fb623445858305-02`;
  moderator context:
  `1v0r0-wave-council-readiness-single-s-fresh-20260811-0b21e0fb623445858305-03`.)
- **Code readiness single-S review — 2026-08-11: CHANGES REQUESTED,
  REPAIRED.** Fresh context
  `1v0r0-code-readiness-single-s-final-20260811-0b21e0fb623445858305-04`
  found the public Package Wavefoundry prompt still makes the model companion
  optional for releases. The change now owns that prompt's Run, Output, and
  Options contract while preserving model-optional non-release local builds.
- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: automatic upgrade cleanup could destroy recoverable
  model data if authority, ownership, no-follow mutation checks, or partial
  failure projection were incomplete; strongest-alternative: require explicit
  opt-in cleanup or quarantine first; disposition: the exact finite allowlist,
  current-manifest veto, stable complete SQLite epoch, custom ownership proof,
  mutation-boundary no-follow validation, idempotence, and retained-lock retry
  make automatic removal proportionate for this operator-required transition;
  red-team context:
  `1v0r0-redteam-readiness-final-receipt-20260811-01`; docs-contract context:
  `1v0r0-docs-contract-readiness-final-receipt-20260811-915d860b9f84196061d1-01`;
  moderator context:
  `1v0r0-wave-council-readiness-final-receipt-20260811-915d860b9f84196061d1-01`.)
- **Delivery-phase Wave Council [wave-council-delivery] — 2026-08-11: PASS**
  (moderator: wave-council; primer-depth: standard; seats: red-team,
  docs-contract-reviewer; rotating-seat: docs-contract-reviewer;
  strongest-challenge: the destructive retired-model cleanup could delete
  content outside its cache root or wedge a supported platform;
  strongest-alternative: quarantine-rename instead of hard delete, rejected as
  heavier when the operator explicitly chose fallback deletion with a disclosed
  narrower guarantee; moderator context:
  `1v0r0-wave-council-delivery-20260811-01`.) Six specialist lanes APPROVE
  (code, qa, architecture, docs-contract, release, security). Twelve findings
  surfaced across two adversarial rounds, each repaired red-first and
  reverified by a fresh independent context: three severe platform-safety
  defects the initial six lanes missed and the adversarial reverification pass
  caught (`1v0r0-f1` native-Windows cleanup wedge freezing index publication;
  `1v0r0-f9` fallback top-level symlink-swap follow; `1v0r0-f10` fallback
  Windows-junction traversal), the `1v0r0-f2` retry-clears-failure integrity
  defect, five evidence-quality/disclosure repairs (`1v0r0-f4` vacuous
  substitution test, `1v0r0-f5` surviving allowlist mutant, `1v0r0-f6`
  changelog re-index/foreground disclosure, `1v0r0-f7` frozen-fixture census
  closure, `1v0r0-f8`/`1v0r0-f12` single-shared-embedder doc/seed sweep), and
  `1v0r0-f3`'s machine-wide-cache disclosure per the operator decision. The
  F1 fallback-deletion path and the F3 machine-wide removal semantics were both
  operator decisions recorded this session. One accepted residual is carried in
  Watchpoints (the single-syscall Windows-fallback TOCTOU sub-window). Final
  full suite 7167/62 OK rc=0; docs-lint ok. Material disagreements: none
  unresolved; every blocking finding reverified to completion. Operator signoff
  is the sole remaining gate.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| 1v0r0-f1-windows-cleanup-wedge | do_now | no | completed | — |
| 1v0r0-f10-fallback-junction-traversal | do_now | no | completed | — |
| 1v0r0-f12-seed-211-mixed-model-residual | do_now | no | completed | — |
| 1v0r0-f2-cleanup-retry-clears-failure-without-success | do_now | no | completed | — |
| 1v0r0-f3-shared-cache-single-repo-authority | do_now | no | completed | — |
| 1v0r0-f4-substitution-mutant-test-vacuous | do_now | no | completed | — |
| 1v0r0-f5-allowlist-exactness-not-behaviorally-pinned | do_now | no | completed | — |
| 1v0r0-f6-changelog-omits-reindex-and-phase4c-disclosure | do_now | no | completed | — |
| 1v0r0-f7-census-benchmark-fixture-baai-unlicensed | do_now | no | completed | — |
| 1v0r0-f8-architecture-doc-assignments-incomplete | do_now | no | completed | — |
| 1v0r0-f9-fallback-toctou-top-symlink-follow | do_now | no | completed | — |

*Machine review state — 11 findings; current: do_now 11, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| security-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Activation depends only on release of the repository's single OPEN wave slot;
  there is no content dependency on the currently implementing wave.
- The broader retrieval-intent golden-query framework remains owned by planned
  change `1seaw`; this wave commits only the focused migration gate it needs.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 473 | 6,105,524 |
| implement | 249 | 4,446,160 |
| review | 558 | 10,551,288 |
| **Total** | **1,280** | **21,102,972** |

<!-- wave:context-efficiency-state {"generation":866,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":249,"content_source_credit":4995593,"derived_artifact_credit":0,"direct_net":4446160,"estimated_tokens_saved":4446160,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7440,"response_debit":548242,"source_credit_count":182,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6249},"plan":{"calls":473,"content_source_credit":7914433,"derived_artifact_credit":4759,"direct_net":6105524,"estimated_tokens_saved":6105524,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25259,"response_debit":1796295,"source_credit_count":495,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":558,"content_source_credit":12245145,"derived_artifact_credit":4106,"direct_net":10551288,"estimated_tokens_saved":10551288,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":64308,"response_debit":1639457,"source_credit_count":478,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5802}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1280,"content_source_credit":25155171,"derived_artifact_credit":8865,"direct_net":21102972,"estimated_tokens_saved":21102972,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":97007,"response_debit":3983994,"source_credit_count":1155,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":19937},"wave_id":"1v0r0 supplier-lineage-compliant-retrieval"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 16 | 0 | 7 | 5,425,758 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":5425758,"surfaced_events":16} -->
<!-- wave:exploration-avoided end -->
