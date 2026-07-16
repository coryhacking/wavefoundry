# External Wave Event Ledger

Change ID: `1sl65-enh wave-events-jsonl-authority`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-07-15
Wave: `1slep external-wave-event-ledger`

## Rationale

Wave `1skt1` made executable review evidence machine-verifiable, but it stores the canonical append-only JSONL inside a fenced block in `wave.md`. That keeps human narrative, generated summaries, signoff display, and machine authority in one increasingly large file. Every append therefore reparses and replaces the whole Markdown record, and a contentious wave makes ordinary narrative diffs difficult to review.

No released Wavefoundry version has shipped this protocol. The framework can therefore establish the cleaner boundary now without carrying a dual-format reader or a v1/v2 compatibility layer: each wave directory owns one fixed `events.jsonl` append-only machine ledger; `wave.md` remains the human narrative and generated current-state projection. This cutover lands before the next framework release so no consumer ever receives the temporary inline format.

## Requirements

1. Make `docs/waves/<wave-id>/events.jsonl` the sole canonical authority for Executable Evidence, Review Run, Finding Synthesis, approval, repair, and convergence records. The filename is fixed relative to the wave directory; lifecycle callers cannot supply an arbitrary path.
2. Remove canonical JSONL and `review-evidence-protocol: 1` from `wave.md`. The exact unversioned header declaration is `review-evidence-source: events.jsonl`; it activates the external-ledger contract alongside retained adoption state. Keep a generated `## Finding Synthesis` current-head table/summary in Markdown. Validation and lifecycle gates derive state only from `events.jsonl`; the Markdown projection is never an independent authority.
3. Preserve the existing semantic record fields, relationships, actionability derivation, per-lane approval freshness, compact authoring behavior, and closure semantics while adding required operation identity metadata and changing persistence. Canonical record bytes are UTF-8 `json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"`. Reject BOM, CRLF, blank physical lines, missing terminal LF, noncanonical serialization, malformed/non-object JSON, and schema/relationship failures.
4. Replace full-record duplication in `docs/waves/review-evidence-adoptions.json` with bounded append-only proof: `record_count` plus `sha256(b"wavefoundry-review-events\0" + canonical_prefix_bytes).hexdigest()` over the exact first N canonical records. The N=0 value is the same formula over the domain prefix alone. Retained adoption state independently keeps the protocol applicable: after adoption, a missing/downgraded source declaration, missing ledger, proof-ahead count, prefix mismatch, or unknown unadopted suffix blocks lifecycle success without Git.
5. Serialize typed mutations under the existing project-global review-evidence lock so simultaneous reviewer/council writes cannot lose an update. The server derives a stable event identity from fields the compact tool already requires, discriminated per event kind so distinct records authored in one review pass never collide: every identity includes `(wave lifecycle id, event kind, actor, context ID)` — the wave lifecycle id is parsed with the canonical lifecycle-prefix grammar (currently 5 or 6 characters), never taken by a fixed-width slice — plus, for an `approval` event, the `signoff_key`; for a `finding` event, the `finding_id`, `run_kind`, and `cycle`; for a `run` event, the `run_kind` and `cycle`. Encode the identity as canonical structured data, never delimiter-joined text. The record kind alone is never the finding discriminator: multiple findings authored by one actor within a single context and cycle — the normal multi-finding review pass, as in 1skt1's own delivery ledger — must each receive a distinct identity via their `finding_id`. It stores that identity plus one SHA-256 digest of the server-normalized semantic request once on the leading canonical record of the generated bundle (not on every row and not in a separate replay registry). Defaults and documented set-like lane/boundary collections are normalized before hashing; transport-only `mode` is excluded and meaningful evidence-array order is preserved. An existing identity with the same digest is an idempotent response-loss retry and returns the originally committed records with `replayed: true`; the same identity with different content fails closed. A genuinely new repeated review uses a new context ID and therefore receives a new identity even when every other semantic field is unchanged. No caller-supplied operation ID or generic transaction abstraction is introduced. The lock covers re-read, prefix validation, duplicate/conflict detection, record construction, same-directory atomic replacement of `events.jsonl`, adoption-proof advance, and Markdown projection; event replacement is the authority commit point.
6. Treat `events.jsonl` as authoritative and the Markdown summary as a rebuildable projection. Failure before the event commit publishes nothing. Adoption failure after commit returns structured partial success with `event_committed: true` and `adoption_pending: true`, blocks clean lifecycle claims, and is repaired by replay without appending. Projection failure returns `event_committed: true` and `projection_stale: true`; readers derive current state from validated events or surface an explicit integrity/stale diagnostic, while only the locked transaction/reconciler repairs disk projection.
7. Perform a one-time self-hosting migration over exactly the currently adopted Wavefoundry wave keys under the same lock: emit a census manifest of every adopted key with source count/hash, migration state, and target count/hash; extract inline records, prove parsed equality, commit canonical bytes/count/hash, then remove inline authority and regenerate projection. Migrate the in-flight `1slep` wave last; immediately re-read it through the external-ledger path before any post-migration review evidence is recorded. A rerun skips already-proven census entries and resumes the remaining entries without a runtime dual reader. This extractor is never applied to consumer repositories.
8. Update new-wave creation, Init/install, upgrade, packaging, rendered prompts/carriers, docs lint, review, prepare, close, dashboard/resource reads, and the typed authoring surface to use the external ledger. Fresh Init and upgrade from the last shipped release install the new writer/readers and prove that subsequent public wave creation produces only the new format; they do not scan, parse, or rewrite historical target-project waves. Package extraction carries the same source contract. `wf setup` does not create, migrate, or repair wave event state; it only builds indexes that exclude canonical ledgers and retain generated summaries. New-wave creation writes empty `events.jsonl`, the fixed source declaration/projection, and zero-record adoption proof.
9. Exclude the normalized `docs/waves/<wave-id>/events.jsonl` path from full/incremental semantic documentation/code retrieval and stale-row cleanup when its exact source declaration is present or retained adoption proves that wave already owns canonical authority; source-declaration tamper must fail lifecycle validation without making the adopted raw ledger searchable. Keep the generated `wave.md` current-state summary searchable. Do not selectively chunk event fields: that would create a second projection contract and surface superseded history beside current heads. Structured lifecycle tools read canonical event history directly. Do not globally ignore unrelated files named `events.jsonl`, including unadopted lifecycle-shaped note directories; paired fixtures prove those remain eligible. The event mechanism remains local, filesystem-backed, Git-independent, and portable across supported platforms.

## Scope

**Problem statement:** Canonical review events are embedded in the human wave record, creating large noisy Markdown files and coupling machine persistence to narrative rendering.

**In scope:**

- Fixed sibling `events.jsonl` authority and direct JSONL parser/validator.
- Generated `wave.md` pointer, current-head table, and concise summary.
- Hash-and-count adoption proof with crash/retry behavior.
- One-time migration of current self-hosted adopted waves.
- Fresh install, upgrade, packaging, dashboard/resource, docs-lint, and lifecycle integration.
- Tests for malformed ledgers, append-only enforcement, projection drift/repair, failure boundaries, and no duplicate retry.

**Out of scope:**

- Moving objective, participants, admitted changes, dependencies, narrative checkpoints, or general wave status into the event ledger.
- A generated `wave.json` current-state snapshot.
- Selective semantic chunks derived directly from raw event fields; the generated Markdown current-state projection owns searchability.
- A database-backed ledger or generic event-sourcing framework.
- Supporting both inline and external review-event formats after cutover.
- User-visible protocol version negotiation before a released compatibility boundary exists.
- Generalized race-resistant filesystem traversal beyond the framework's existing fixed-path lifecycle write policy.

## Acceptance Criteria

- [x] AC-1: A newly created wave contains a sibling `events.jsonl`, no fenced canonical JSONL in `wave.md`, and a generated source declaration/current-state projection; all lifecycle gates read the sibling ledger as the sole authority.
- [x] AC-2: Existing record validation, actionability, supersession, convergence, approval chronology, compact authoring, review, prepare, and close fixtures pass against direct external JSONL, including malformed/truncated/reordered/rewritten negative controls.
- [x] AC-3: Canonical-byte fixtures pin UTF-8 serialization, LF/final-newline rules, rejection cases, the N=0 value, and domain-separated SHA-256 count/prefix proof; retained adoption detects missing authority, proof-ahead state, unadopted suffixes, and every adopted-prefix mutation without Git.
- [x] AC-4: Public typed-tool fixtures pin deterministic structured event identity and semantic-request digest normalization from existing required inputs, including both canonical 5- and 6-character lifecycle prefixes without fixed-width truncation or delimiter-shaped-value collisions, and prove one global lock, concurrent distinct writers without lost updates, identical response-loss replay without duplicate records, same-identity/different-content refusal, and atomic event replacement as the sole authority commit point. A fixture proves that multiple distinct findings authored by one actor within a single context and cycle each receive a distinct identity and coexist without a false same-identity conflict (the multi-finding review pass). A second fixture proves that an otherwise identical event with a new context ID is a new committed identity, while the same context replays or conflicts according to digest equality. The public tool gains no operation-ID argument.
- [x] AC-5: Fault injection at event replacement, adoption advance, projection replacement, and response loss produces the specified committed/pending/stale envelopes; every same-operation retry converges without losing an event, publishing a false clean result, or appending again.
- [x] AC-6: A one-time resumable migration emits a complete adopted-wave census manifest, converts exactly every listed self-hosted wave record-for-record, migrates `1slep` last and re-reads it externally, removes inline authority only after external commit, preserves human prose, and leaves docs lint plus lifecycle validation green with no runtime dual reader or fallback.
- [x] AC-7: Actual fresh Init/install, upgrade-from-last-shipped-release, and package extraction install only the external-ledger implementation, preserve project-authored Markdown/history, never scan or migrate consumer waves, and prove the subsequent public create-wave path produces the new format; `wf setup` performs no wave-state mutation.
- [x] AC-8: A reader-state matrix proves: valid events/current projection serves normally; valid events/stale or missing projection derives current state plus a structured stale diagnostic; invalid events/adoption proof fails closed without serving projection; adopted missing authority fails closed. Generated Markdown remains searchable, while exact declared ledgers and retained-adoption ledgers after source tamper—not unrelated or unadopted lifecycle-shaped same-named files—are excluded from full/incremental semantic retrieval and stale-row cleanup, with no selective event-field chunks.
- [x] AC-9: Full canonical framework tests, docs lint, and distribution verification pass on macOS/POSIX fixtures plus the existing platform-neutral Windows path tests; the implementation has no Git dependency.

## Tasks

- [x] Introduce fixed wave-event path resolution and direct JSONL parse/render primitives.
- [x] Refactor validation and lifecycle consumers to accept wave path plus external records instead of extracting a Markdown fence.
- [x] Change the typed authoring transaction, adoption proof, failure recovery, and idempotent retry behavior.
- [x] Render and reconcile the Markdown source declaration/current-state projection from canonical events.
- [x] Update wave creation, install/setup, upgrade, packaging, prompts/carriers, dashboard/resources, and indexing exclusions.
- [x] Implement and run the one-time self-hosted migration with record-equality verification.
- [x] Emit and verify the self-host migration census manifest and the reader-state behavior matrix.
- [x] Add focused negative/fault-injection/integration tests and run the canonical full suite.
- [x] Update architecture, specification, contributor, and handoff documentation.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Ledger contract and parser | implementer | — | Establish the sole-authority boundary first. |
| Lifecycle persistence and recovery | implementer | Ledger contract and parser | Includes adoption proof and idempotent retry. |
| Install/upgrade/render integration | implementer | Ledger contract and parser | Exercise public orchestration paths. |
| Migration and verification | qa-reviewer | All implementation workstreams | Record equality, failure injection, full suite. |
| Contract/architecture reconciliation | docs-contract-reviewer | All implementation workstreams | Keep source, carriers, and rendered surfaces aligned. |


## Serialization Points

- `review_evidence.py` establishes the record-loading and persistence API before lifecycle callers change.
- `server_impl.py` owns the public authoring transaction and must land before migration executes.
- Seed/carrier changes and self-hosted rendered surfaces reconcile only after the persistence contract is stable.
- The self-hosted migration is the final serialization point before full validation; no parallel edits to adopted wave records during migration.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — external event authority, adoption proof, write/recovery ordering, and Markdown projection.
- `docs/architecture/testing-architecture.md` — direct-ledger, failure-injection, migration, install, and upgrade evidence.
- `docs/specs/mcp-tool-surface.md` — typed authoring and lifecycle response/diagnostic contract if response fields change.
- `docs/contributing/review-and-evals.md` — operator-facing event-ledger location and human summary contract.
- `docs/ARCHITECTURE.md` only if the current-state summary names the inline persistence boundary.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Defines the new sole-authority boundary. |
| AC-2 | required | Prevents persistence relocation from weakening protocol correctness. |
| AC-3 | required | Append-only durability is a load-bearing guarantee. |
| AC-4 | required | Stable operation identity and serialization prevent duplicate/lost approvals. |
| AC-5 | required | Every partial-write boundary must converge without false success. |
| AC-6 | required | The self-hosting repository must not retain a hidden second format. |
| AC-7 | required | Fresh and upgraded target projects must receive the new format without historical rewrites. |
| AC-8 | required | Readers must never serve a stale projection as authoritative state, and retrieval must exclude only the intended ledger. |
| AC-9 | required | Portability and full verification are release gates. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-15 | Planned from operator direction after 1skt1 dogfooding showed that canonical inline JSONL makes contentious wave records large and noisy. | Operator selected fixed sibling `events.jsonl`; current parser/renderer/adoption/writer trace. |
| 2026-07-15 | Readiness primer plus architecture/security seats required a stable operation identity, one mutation lock/commit point, canonical byte/hash rules, explicit partial-success recovery, consumer-upgrade non-migration, stale-projection reader behavior, and exact path-scoped index exclusion. The plan was amended before implementation. | Code-grounded challenge against current suffix IDs, adoption-only lock, whole-wave writer, dashboard/resources, and index walker; no implementation edits. |
| 2026-07-15 | Proportionality review accepted the concrete concurrent-writer and response-loss hazards but rejected caller-managed operation IDs and a general replay protocol. Req 5 now derives identity from existing compact-event inputs and uses one digest plus the existing lock. The self-migrating wave is explicitly last in the census. | Current public writer reads and replaces `wave.md` outside the adoption lock, so concurrent review agents can lose an update; a response lost after replacement can cause a duplicate retry. No broader durability threat was identified. |
| 2026-07-15 | Review-round follow-up: the derived finding-event identity was ambiguous and omitted `finding_id`, which would have made the normal multi-finding-per-context review pass (as in 1skt1's own delivery ledger, shared context `1skt1-qa-delivery-1`) collide and fail closed on the 2nd..Nth finding. Req 5 identity is now stated per event kind with `finding_id` explicit for findings, and AC-4 pins a multi-finding-distinct-identity fixture. | 1skt1 delivery-ledger executable_evidence rows share one context/cycle across findings; the pre-fix identity `(wave, finding, actor, context, cycle)` would not distinguish them. |
| 2026-07-15 | Focused re-readiness review accepted the multi-finding discriminator and corrected its fixed-width lifecycle-ID wording: event identity uses the canonical parsed 5-or-6-character prefix, never the first five characters. | `LIFECYCLE_PREFIX_PATTERN` already accepts `{5,6}` and the lifecycle allocator documents the 6-character transition; AC-4 now pins both lengths. |
| 2026-07-15 | Focused QA proposed a second caller operation ID for otherwise identical identity tuples. The proposal was rejected as redundant with the required context ID, but its test gap was valid: AC-4 now proves a new context creates a new operation, same-context replay/conflict behavior, and structured identity encoding. | The approved contract defines `context_id` as the freshness/review-context discriminator; adding another caller identity would restore the authoring burden removed by the proportionality review without distinguishing a supported semantic case. |
| 2026-07-15 | Thought: begin implementation by stabilizing `review_evidence.py` as the sole ledger/parser/proof API, then serialize the public writer, then convert readers/install/index consumers, and migrate self-hosted waves last. Builder lane: implementer. Delivery lanes reserved: code-reviewer, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer, reality-checker, red-team, wave-council. | Pre-implementation packet review; serialization points and AC-3 through AC-8 evidence matrix. |
| 2026-07-15 | Gapfill: Wavefoundry code-navigation MCP tools are not attached in this session, so implementation grounding uses the generated codebase map plus targeted source reads and exact-token searches. | `docs/references/codebase-map.md`; root AGENTS fallback rule. |
| 2026-07-15 | Implemented the external authority, canonical parser/proof, serialized identity-aware authoring transaction, failure recovery, lifecycle/lint/dashboard/resource readers, exact index exclusion, and explicit self-host migrator. The migrator converted the complete two-wave adopted census record-for-record, with `1slep` last, then re-read both waves through the external-only validator. | Core 66 tests; lifecycle 39 tests; dashboard 175 tests; indexer 263 tests; migration fixture; `review-evidence-migration.json`; live counts 186 and 2 with matching retained proofs. |
| 2026-07-15 | Completed fresh-install, upgrade, and distribution-path coverage. Package extraction now proves an existing historical wave remains byte-stable, gains no ledger, and the shipped framework carries the external authoring and explicit self-host-only migration utilities. Canonical verification is green. | `run_tests.py`: 5,590 tests across 50 isolated files, OK; `test_build_pack.py`: 94 tests in the canonical run; docs-lint: ok; `git diff --check`: clean. |
| 2026-07-15 | Delivery review repairs completed through the security/docs-contract recheck: fail-closed adopted applicability, projection-vs-authority resource errors, exact source-declared index exclusion, direct packaging execution, atomic convergence authoring, wave-directory containment before reads/writes, reserved metadata collision rejection, canonical convergence documentation, and current handoff state. Each reproduced finding is fixture-locked and independently re-verified; the external ledger records all nine current heads as completed. | `events.jsonl`: 70 records / 23 runs / 9 completed current findings; focused writer/security/convergence suite green; review-evidence 66 OK; carrier registry and docs lint green. |
| 2026-07-15 | Red-team found that source-declaration tamper made an adopted ledger indexable while lifecycle correctly failed closed. The bounded repair excludes when either the exact declaration is valid or retained adoption proves the wave, preserving eligibility for unadopted lifecycle-shaped notes and unrelated same-named files. Independent replay closed removed/malformed-source attacks and stale-row cleanup. | `FileWalkerTests.test_retained_adoption_keeps_ledger_excluded_after_source_tamper`; focused 3/3, isolated indexer 264/264; final `run_tests.py` 5,596 tests across 50 files, OK; docs lint and diff check green. |
| 2026-07-15 | Final delivery council APPROVED after reconciling code, QA, architecture, security, docs-contract, reality, and red-team PASS. A typed readiness reconciliation was added for the historical pre-cutover Markdown approval. The close dry-run is green except for operator signoff, which remains operator-owned. | External ledger validates; all 10 current findings completed; specialist and both council approvals current; `wave_close(dry_run)` reports only `missing_operator_signoff`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-15 | Select a fixed sibling `events.jsonl` as the sole review-event authority and keep `wave.md` as human narrative plus generated projection. | Direct JSONL is simpler to parse and diff, while a generated Markdown view preserves operator usability. | Keep inline JSONL — simplest code but retains the burden. Use `wave-findings.jsonl` — rejected as too narrow for runs, approvals, repairs, and convergence. |
| 2026-07-15 | Make a bounded pre-release cutover with no v1/v2 reader or fallback. | No released consumer has received the inline protocol, so compatibility machinery would create two truths without protecting a real user. | Dual-format migration layer — rejected as premature compatibility complexity. |
| 2026-07-15 | Do not turn this change into full wave event sourcing. | The demonstrated problem is review-event persistence; moving all wave metadata would expand architecture and review scope without evidence. | General `wave.jsonl` lifecycle event stream or database — rejected as overbroad. |
| 2026-07-15 | Exclude canonical wave `events.jsonl` ledgers from semantic indexing and index only the generated `wave.md` current-state projection. | Raw append-only history contains superseded records and evidence detail that would add retrieval noise; selective field chunks would create another derived contract. | Index all JSONL — rejected as noisy. Chunk selected fields — rejected as a second projection and schema coupling. |
| 2026-07-15 | Derive idempotency from the existing event/context identity rather than adding a caller-supplied operation ID. | Concurrent public authoring and response loss are real bounded hazards, but callers should not serialize bookkeeping or maintain a new identity protocol. | No deduplication — leaves response-loss duplicates. Caller operation ID plus replay registry — rejected as disproportionate. Last-record-only deduplication — rejected because an intervening reviewer write can occur before retry. |
| 2026-07-15 | Land this cutover before the next framework release. | The inline format has not shipped, so pre-release cutover avoids a permanent consumer migration/dual-reader obligation. | Ship inline and fast-follow — rejected because the follow-up would then require consumer compatibility handling. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Event and Markdown projection cannot be replaced atomically together | Make events authoritative, projection rebuildable, and failure/retry state explicit and tested. |
| A cutover silently loses or reorders existing adopted history | Migrate record-for-record with deterministic equality and adopted-prefix verification before removing inline data. |
| External files become a second source rather than the source | Fixed filename, no inline fallback, and lifecycle gates ignore projection text for authority. |
| Hash-only adoption proof weakens history protection | Store both adopted count and deterministic prefix hash; validate that exact prefix before every append. |
| Scope expands into a generic event platform | Explicit out-of-scope boundary and focused review consequence. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
