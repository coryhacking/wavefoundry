# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-22
review-evidence-source: events.jsonl

wave-id: `1t9w8 memory-lifecycle-naming`
Title: Memory Lifecycle Naming

## Objective

Bring memory records into the repository-wide lifecycle-ID naming convention: new records mint `<lifecycleId>-mem <slug>` (space form, mirroring change IDs), legacy IDs stay valid forever for field stores, and this repository's existing records are renamed with IDs backdated from their created_at so filesystem order shows true chronology.

## Changes

Change ID: `1t9w7-enh lifecycle-id-memory-naming`
Change Status: `implemented`

Completed At: 2026-07-22

## Wave Summary

Wave `1t9w8` (Memory Lifecycle Naming) delivered one change: Memory Records Use Lifecycle-ID Naming. Notable adjustments during implementation: Memory Records Use Lifecycle-ID Naming: Operator directive: add the upgrade path so target repositories are renamed the same way — requirement 8, AC-4, and the revised field-migration decision added; the earlier out-of-scope line removed.; Memory Records Use Lifecycle-ID Naming: Local migration executed through the shipped function: 66 records renamed with backdated chronological prefixes (1suok...1t7xx order), 1 skipped (README), second run no-op, one live journal reference updated, docs lint clean, docs index refresh dispatched. memory_backfill_sources had no rows here (no paused runs); the store-update path is covered by the fixture test.; Memory Records Use Lifecycle-ID Naming: Gapfill: implement-stage instrumented retrieval reads zero because post-activation work used harness surfaces — built-in Reads required as Edit preconditions and quick region views on files already located during the MCP-first design investigation (whose code_keyword/code_read calls attributed to plan via the general-bucket fold). The lapse was not free: the grammar-consumer census ran with a glob that excluded the wave_lint_lib subdirectory, which is precisely how the second grammar spelling was missed until the docs gate caught it. Corrective recorded in the review_finding memory: censuses route through code_keyword with repository-wide scope, not single-directory globs, regardless of instrument.

**Changes delivered:**

- **Memory Records Use Lifecycle-ID Naming** (`1t9w7-enh lifecycle-id-memory-naming`) — 5 ACs completed. Key decisions: Space-separated `<lifecycleId>-mem <slug>`, widening the ID regex to a two-form union.; Backdate migrated IDs from `created_at`.
## Journal Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| bare-legacy-id-references-stranded | do_now | no | completed | — |
| migration-not-interruption-safe | do_now | no | completed | — |
| migration-skips-live-doc-surfaces | do_now | no | completed | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 37 records; 13 runs; 3 findings; current: do_now 3, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Prepare Review Evidence

Readiness council pass, 2026-07-22 (single change; claims verified against the tree during the design discussion):

- reality-checker: the `mem-` prefix is convention only — the census found exactly two production mint sites (`memory_add` default-ID builder and the propose/backfill drafter in server_impl.py) plus one test assertion, with no structural consumer parsing the prefix; the filename stem is the memory_id (`_contained_record_path` resolves `<memory_id>.md`), so the space form rides the existing resolution model exactly as change IDs do; `lifecycle_id.build_prefix` accepts an explicit timestamp and v2 entropy is deterministic blake2s(kind, slug), which makes the backdated migration idempotent as claimed.
- red-team: strongest challenge — widening the ID charset to include a space touches the path-containment boundary; answered by the plan's requirement that the space only ever joins two independently validated segments (lifecycle prefix and slug), with escape tests in both forms pinned as part of AC-2. Second challenge — the rename could orphan references; answered by the fail-loud residue grep over live surfaces with closed archives explicitly out of scope as immutable history, plus the reindex requirement.
- qa-reviewer: each AC is falsifiable (end-to-end mint/resolve/collide/advisory for the new form; both-form validation across every consumer; no-op second migration run proving idempotence; suite + lint). The one existing prefix-assertion test is named for update rather than silently deleted.
- docs-contract-reviewer: the three operator rulings (space form, rename-here, no fallback given the universal 1.10+ policy floor) are recorded verbatim in the Decision Log with the rejected alternatives; out-of-scope items (field renames, archive rewrites, prefix resolution) are explicit.

Synthesis verdict: READY.

Delta readiness pass (2026-07-22, operator-directed upgrade-path addition): reality-checker confirmed the upgrade seam exists and fits (version-gated migrations run from upgrade_wavefoundry/upgrade_extensions with the just-landed stale-module-reload hardening; deterministic backdated minting makes the field rename idempotent and interruption-safe by construction); red-team's strongest challenge — store rows keyed by memory_id could orphan — is answered by the required pre-write census of store references with append-only telemetry explicitly left as history and legacy-ID validation retained indefinitely as the safety margin; qa-reviewer confirmed AC-4's fixture-repo proof covers idempotence, live-reference updates, mapping reporting, and interrupted re-entry; docs-contract-reviewer confirmed the operator revision supersedes the earlier local-only ruling in the Decision Log with the rejected alternatives preserved. Synthesis: READY.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the readiness census refuted live by the docs gate (second grammar spelling in wave_lint_lib) — repaired to the identical union, captured as a durable memory, single-source follow-up flagged; strongest-alternative: deferring the local migration to the next upgrade run — rejected, dogfooding the shipped function here is the field rehearsal.)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-22 (delta, upgrade path): PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: memory-id-keyed store rows orphaning under the field rename — resolved by the required reference census, history-preserving policy, and indefinite legacy-ID validation; strongest-alternative: opt-in field migration — rejected by operator direction, convention drift would persist by default.)

- **Prepare-phase Wave Council [prepare-council] — 2026-07-22: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, reality-checker, qa-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the widened ID charset touching the path-containment boundary — resolved by validated-segment joining plus explicit escape tests in both forms; strongest-alternative: hyphen-only IDs avoiding the regex change — rejected by operator direction for structural consistency with every other lifecycle artifact.)

## Delivery Review Evidence

Delivery council pass, 2026-07-22, over the landed diff (memory_records.py grammar + mint + migration; wave_lint_lib/constants.py grammar; server_impl.py mint sites; upgrade_extensions.py version-gated hook; docs/spec/README convention text; five new test groups) plus the executed local migration:

- reality-checker: the landed grammar is one union spelling per module with a mirror comment naming its twin; `mint_memory_id` routes through `build_prefix` under the repository's own policy exactly as planned, with the timestamp parameter carrying backdated migration minting; the executed local migration renamed all 66 legacy records (README skipped), the second run was a no-op, and the live directory sorts chronologically — today's live-minted record (`1t7l9-mem ...`) sorts after every backdated prefix.
- red-team: strongest challenge — the readiness census was refuted live: the claim that no lint surface carried the memory-id grammar was wrong, and the docs gate proved it with 90 errors immediately after the migration. The repair widened `wave_lint_lib/constants.py` to the identical union, the miss is recorded in the Progress Log and captured as a durable review_finding memory targeting both spellings, and single-sourcing the grammar is flagged as a follow-up candidate. Second challenge — the space charset touching the path-containment boundary — is held by grammar-first validation plus resolved-path containment, with escape tests in both forms.
- qa-reviewer: grammar accept/reject and normalization, containment escapes in both forms, deterministic backdated minting with decoded day-ordering, collision suffixing that cannot corrupt the prefix, the full migration fixture (file rename, Memory ID line, backticked cross-refs, memory_backfill_sources row, idempotent re-run), and the upgrade-hook fixture with the at-version skip. Modules 148/341/41/828/1413 OK; full suite 6,128/6,128 OK on the final tree; live post-reload mint verified through the real tool path.
- docs-contract-reviewer: the spec's new Memory record identity paragraph, the memory README field table, and the change doc's real-time Progress Log (including the honest census-miss entry) are consistent; legacy ids documented as valid-but-frozen; append-only history untouched by the migration as required.

Synthesis verdict at cycle 0: PASS with the lint-grammar census miss repaired in-flight — then REFUTED by the operator's review, which found two blocking P1s the council had missed.

Repair cycle 1 (operator findings `migration-not-interruption-safe` and `migration-skips-live-doc-surfaces`, typed chains in the ledger): the migration's passes were driven by in-run bookkeeping and its reference scope never left the memory directory, so the operator's live probes showed a rename-only crash leaving stale references unrepairable, a write-before-unlink crash raising the self-created collision, and docs/live.md staying stale. The repair made every pass state-derived (same-internal-id residue completed, scanning discovery with slug-lookup resolution, live-surface scope with archives and ledgers untouched, loud residual reporting), turned the operator's reproductions into permanent regression tests, and re-ran the local migration clean (0 repairs, no residuals). Independent reverification by qa-reviewer executed the operator-authored reproductions, not implementer fixtures. Post-repair verdict at cycle 1: PASS, both chains terminal.

Repair cycle 2 (operator finding `bare-legacy-id-references-stranded`, resolved by operator scope ruling): the rename pass accepted ANY legacy id while reference discovery was `mem-`-scoped, so an explicit bare id (`custom-lesson`) was renamed with its references and store row silently stranded and residuals empty. The operator ruled the intended scope: generated legacy records are always `mem-*`; explicit bare ids stay frozen-valid and are never auto-renamed. The repair gates the rename pass to `mem-*` (no half-migration path exists for bare ids), aligns requirement 8, AC-4, the spec paragraph, and the function docstring to state that scope, reverts the briefly-started all-token discovery widening (a bare token is indistinguishable from prose), and pins the frozen behavior with the operator's reproduction inverted into assertions (file, live-doc reference, and store row untouched; frozen id still validates and resolves). Independent reverification by qa-reviewer executed against the operator-authored reproduction; convergence checkpoint derived over all three findings. Verdict: PASS, all chains terminal.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

operator-signoff: approved (2026-07-22, operator reviewed all three repair cycles and requested close in the current session)
- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 28 | 318,949 |
| implement | 9 | 0 |
| review | 80 | 1,403,297 |
| **Total** | **117** | **1,722,246** |

<!-- wave:context-efficiency-state {"generation":97,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":9,"content_source_credit":0,"derived_artifact_credit":20,"direct_net":-13530,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":362,"response_debit":13188,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":28,"content_source_credit":406620,"derived_artifact_credit":662,"direct_net":318949,"estimated_tokens_saved":318949,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1618,"response_debit":94060,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7345},"review":{"calls":80,"content_source_credit":1526181,"derived_artifact_credit":706,"direct_net":1403297,"estimated_tokens_saved":1403297,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17272,"response_debit":107407,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1089}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":117,"content_source_credit":1932801,"derived_artifact_credit":1388,"direct_net":1708716,"estimated_tokens_saved":1722246,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19252,"response_debit":214655,"source_credit_count":80,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8434},"wave_id":"1t9w8 memory-lifecycle-naming"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
