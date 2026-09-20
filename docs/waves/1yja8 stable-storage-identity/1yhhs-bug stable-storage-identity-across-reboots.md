# Stable Storage Identity Across Reboots And Platforms

Change ID: `1yhhs-bug stable-storage-identity-across-reboots`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-20
Completed at: 2026-09-19
Wave: 1yja8 stable-storage-identity

## Rationale

**Brief.** Goal: a Wavefoundry index, setup check and interrupted upgrade survive a reboot or OS upgrade that renumbers filesystem device ids, on every supported platform. Audience: framework maintainers, and every consumer repository that reboots. Approach: stop gating persisted identity on `st_dev`; gate on the resolved path plus the inode where the platform supplies one, preserving existing recovery records and returning comparison-basis diagnostics separately. Constraints: recovery records are preserved rather than rewritten; no receipt-version bump; retain path and available-inode checks, with the operator-approved replacement-volume limitation. Success: a repository whose device id changed still reads its receipt, builds its index, passes the setup check and can resume an interrupted upgrade, while a changed bound path or differing nonzero inodes is still refused. This is a continuity heuristic, not a globally unique storage identity.

Observed on this repository on 2026-09-19. An overnight upgrade to macOS 27.2 (build `26B5086k`, boot at 01:19:51) renumbered the repository root's device from `16777231` to `16777233`; the inode, `428221259`, is unchanged, and the path is unchanged. The index data is intact and published: 62,834 nodes, 177,474 edges, 127 communities, graph builder 52. Nothing in the repository or the index changed. Yet `sqlite_storage_migration.read_receipt` raises `MigrationRequired("storage_receipt_identity_mismatch")`, `indexer.require_ready` turns that into a failed build, `index_health` reports the graph absent, and 21 graph-dependent tests skip. There is no recovery path in the code: the comparison is unconditional and every caller fails closed.

The defect spans storage migration, setup readiness observation, setup reconciliation, upgrade handoff and retrieval evaluation. The live census below governs implementation. Retrieval evaluation also gates comparisons against saved environment identity; it is not merely a recording site. Read-only observers and exact persisted-record continuity bindings must retain their existing authority and shape.

The operator approved accepting path plus available inode for this scoped reboot fix. A replacement filesystem mounted at the same path can reuse the recorded inode, so ignoring device can accept a replacement that the former check refused. If either inode is unavailable, path alone cannot distinguish replacement at that path. These limitations are explicit; this change does not promise no new false accepts. Existing independent ownership, schema, package and continuation checks remain necessary. Stable persistent volume identification and legacy-record recovery are outside this fix.

## Original-plan reconciliation

Reconciled on 2026-09-20 against the closed delivery in wave `1yja8`. The original adopt-and-restamp proposal was **superseded during readiness**, not implemented. The operator explicitly chose path plus available inode with the replacement-volume limitation documented, then chose to omit restamping and preserve pure recovery reads. These choices are recorded in the Decision Log and the wave's STORAGE-R1–R3 readiness evidence.

| Original proposal or expectation | Approved and delivered contract |
| --- | --- |
| Adopt a device-drifted identity and restamp persisted recovery records | Compare without rewriting records or returned recovered mappings; retain recorded devices as historical evidence |
| Preserve a no-new-false-accept guarantee | Accept the explicit same-path/reused-inode replacement-volume ambiguity; if either inode is zero, use the weaker path-only basis |
| Treat restamping as part of completion | Completion is against the amended Requirements 1–8 and AC-1–8 below; no restamping work is outstanding or claimed complete |

The goal remains recovery from device renumbering across reboot. A stronger durable-volume identity contract or coordinated restamping would require a separately planned change. The accepted [storage continuity ADR](../../architecture/decisions/1yja8-adr%20persisted-storage-continuity.md) records the final design and its limitations. This reconciliation changes documentation only; it does not reopen the closed wave or weaken the shipped checks.

## Requirements

1. One pure shared comparison decides persisted-versus-live device/inode continuity. Device does not gate. Inode gates when both stored and live values are nonzero; zero on either side selects the weaker path-only basis. Missing/malformed identity mappings or invalid inode/device values remain invalid, rather than silently becoming inode-unavailable. The operator accepts same-path/reused-inode replacement-volume ambiguity and path-only ambiguity; this is not globally unique identity.
2. Preserve caller-owned path binding: compare resolved root/index locators with `os.path.normcase`, and retain validated artifact roles, allowlisted names and owned staging paths. Do not embed capture paths into existing `{device, inode}` mappings: a staged candidate is legitimately renamed to the live database. Existing authorization of that rename remains intact. POSIX normcase remains case-sensitive; simulated Windows tests exercise its normalization.
3. Re-derive all persisted-versus-live comparisons and route them through the shared helper. The verified census comprises `sqlite_storage_migration` root, published, source, work and artifact identities; `setup_readiness._owner` receipt/action/checkpoint comparisons; `setup_reconciliation.SetupReconciliation._inspect`; `upgrade_extensions._validate_index_guard_handoff`; and `retrieval_eval._compare_index_identity`. Retrieval evaluation retains repository inode matching in both comparison kinds and store inode matching only for same-generation comparison; cross-generation may recreate the store as today. Recorded device values remain historical diagnostic evidence.
4. Within-process snapshots/race checks and persisted-to-persisted continuity bindings remain strict and unchanged. This includes `context_efficiency._file_version_matches`, migration `_database_schema` snapshots, candidate-build/replacement checks within one run, exact receipt/checkpoint/restart-action equality, completed-parent receipt hashes, package hashes, migration IDs, checkpoint tokens and timestamps. Device tolerance never bypasses independent schema, ownership, safe-path or continuation validation.
5. No restamping. Neither on-disk records nor returned recovered mappings are rewritten or enriched by comparison. Keep existing receipt versions and identity shapes, including prior device values. Reading a device-drifted valid record succeeds without mutation; refusing any later validation likewise leaves recovery bytes unchanged. Normal explicitly authorized setup/upgrade state transitions retain their existing writes.
6. The shared comparison reports `path+inode` or `path` basis and device drift separately from stored records. Expose this diagnostic context from existing observation/report results where identity decisions are reported (storage detection, setup-readiness observation and retrieval comparison reporting); do not mutate continuation commands or receipts just to convey diagnostics. Old readers need not understand new diagnostic response fields, and new readers accept old-format records.
7. The helper is standard-library-only and available at bootstrap and pre-extraction upgrade-hook boundaries. Include it in the existing loaded-source identity/dependency inventory as appropriate. Preserve refusal identifiers and use the project's established loading mechanism; do not introduce a new loader protocol.
8. Document the observed macOS reboot failure and the portable API limitation: `st_dev` is not a portable durable volume identifier, and inode is unique only within its filesystem/device. Do not claim that every listed filesystem or Windows stat always returns zero, or that every reboot renumbers devices. Platform injection tests prove comparison logic, not native execution on platforms unavailable here. Architecture rationale records the operator-approved limitation and the within-run/persisted-record exclusions.

## Scope

**Problem statement:** Persisted storage identities gate on `st_dev`, which the portable stat contract does not establish as durable across remounts, so a routine OS upgrade leaves an intact index unreadable, the setup check failing, and an interrupted upgrade unresumable, with no recovery path in the code.

**In scope:**

- The shared identity comparison and its adoption at every persisted-identity site.
- Pure acceptance of device-only drift, preserving existing record bytes and returned mappings.
- Separate comparison-basis and drift diagnostics, with no receipt enrichment.
- Tests covering the platform matrix by injection, and the derivation test that keeps new sites on the shared comparison.

**Out of scope:**

- Within-run identity comparisons, including `context_efficiency._file_version_matches`, and strict persisted-to-persisted continuity bindings.
- Persistent volume identification and durable device restamping.
- `repair_ppol_memory_staging.py`, a one-off repair script pinned to a specific historical package.
- Any change to what an index contains, how it is built, or when it is rebuilt.
- Rebuilding or migrating existing indexes; a correct comparison makes the standing receipt readable again on its own.

## Acceptance Criteria

- [x] AC-1: A repository whose recorded device differs from the live device, with path and inode unchanged, reads its receipt successfully, and an index build proceeds rather than returning a failed build. Proven against a real receipt with an injected device drift, and failing when the comparison is reverted to include the device.
- [x] AC-2: A directory replaced at the same path with differing nonzero stored and live inodes is still refused, and a record whose resolved path differs is still refused. Neither refusal writes anything.
- [x] AC-3: A table-driven test covers the platform matrix by injecting stat results: device drifts; inode drifts; inode zero on the stored side only; inode zero on the live side only; inode zero on both sides; path differs; path differs only by case under simulated Windows `normcase`. Each case asserts the accept-or-refuse outcome and separate comparison basis; malformed identities are rejected.
- [x] AC-4: Every site in the Requirement 3 derivation uses the shared comparison. A source-derived regression guard covers persisted identity consumers and detects reintroduced direct device-sensitive equality, with explicit within-run and persisted-to-persisted exclusions. The census states limitations of static detection; it does not claim arbitrary dataflow proof.
- [x] AC-5: A receipt written in the pre-change format is accepted with no version bump, no rewritten bytes, and no enrichment of the returned recovered mapping.
- [x] AC-6: Device-only acceptance and refusal after valid root identity but invalid later schema/artifact/continuation checks leave recovery records byte-identical. Producer-generated pending receipt/checkpoint/action bindings remain resumable after injected device drift, without restamping. Prove the relevant boundaries on real temporary files.
- [x] AC-7: Setup observation, setup reconciliation and upgrade resume accept device-drifted valid records and refuse differing nonzero inode records through their public entry points. Retrieval evaluation preserves same-generation versus cross-generation behavior. Authorized staged-to-live rename still works. The bootstrap/pre-extraction helper dependency is exercised with the existing hook-loading path.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Re-derive the set of stored-versus-live identity comparisons from source and record it as a short table before editing. Evidence: source census below, independent implementer/Guru and security/architecture reads.
- [x] Add the shared comparison with the path, inode and device rules, separate diagnostic basis, and the `normcase` normalization.
- [x] Adopt it at each derived site, preserving each site's existing refusal semantics and error identifiers.
- [x] Preserve pure reads and existing record shape; report basis/drift separately and prove acceptance and downstream refusal write nothing.
- [x] Add the platform matrix test, the derivation test, the old-format acceptance test, and the public-entry-point/rename/bootstrap tests.
- [x] Verify on this machine that the standing receipt becomes readable, the graph reports ready, and the previously skipped graph tests run.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| derivation     | implementer | —            | the site census is a reviewed deliverable before edits start |
| comparison     | implementer | derivation   | pure shared helper and separate diagnostics |
| adoption       | implementer | comparison   | per-site, preserving refusal semantics |
| verification   | qa          | adoption     | platform matrix, derivation guard, real-file no-write controls |


## Serialization Points

- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/setup_readiness.py`, `.wavefoundry/framework/scripts/upgrade_extensions.py`, `.wavefoundry/framework/scripts/retrieval_eval.py`, `.wavefoundry/framework/scripts/setup_reconciliation.py`, the new shared identity helper and its bootstrap inventory, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` gains the rule that an identity persisted across runs may not gate on a value the operating system assigns at mount time, with the within-run exception named. `docs/architecture/decisions/` gains a record for the identity basis, since the change alters a recovery-path refusal rule that downstream repositories depend on.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The reported failure; without it the change does nothing |
| AC-2 | required  | The check must still refuse what it exists to refuse |
| AC-3 | required  | The platforms cannot be executed here, so the matrix is the only cross-platform evidence |
| AC-4 | required  | Without it a new site silently reintroduces the defect |
| AC-5 | required  | Every existing consumer repository holds a pre-change receipt |
| AC-6 | required  | Recovery records must not lose history, and a refusal must not write |
| AC-7 | required  | The setup check and upgrade resume are two of the four broken paths |
| AC-8 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-20 | Reconciled original adopt-and-restamp proposal with delivered wave 1yja8: original approach explicitly superseded by operator-approved pure path/available-inode comparisons and accepted ambiguity. Completion refers to the amended contract, not restamping | Original-plan reconciliation; Decision Log; STORAGE-R1–R3 readiness evidence; accepted ADR |
| 2026-09-19 | Defect observed and diagnosed on this repository after an overnight macOS 27.2 upgrade and reboot. Device drift `16777231` to `16777233` with inode and path unchanged; index data intact at 62,834 nodes and 177,474 edges; `read_receipt` and `detect` both raise `storage_receipt_identity_mismatch`. Census found the same stored-versus-live device comparison at four sites, extending the failure to the setup check, its CLI fallback and upgrade resume | live stat comparison against `.wavefoundry/index/sqlite-migration.json`; `sysctl kern.boottime`; source census of `st_dev`/`st_ino` users |


| 2026-09-19 | Operator resolved STORAGE-R1–R3 contract choices: accept path plus available inode with documented ambiguity, omit restamping. Amended the census, pure-read contract, rename semantics, malformed identity handling and bootstrap boundary before focused reverification | Current operator answers; independent source census and primer |

| 2026-09-19 | Readback: device-only drift accepts unchanged path/available inode without restamping; differing nonzero inode and path still refuse. AC-1–8 cover helper, migration, setup, upgrade and retrieval consumers. Example: historical device 16777231 with live 16777233 becomes readable with bytes preserved. Scope excludes exact persisted bindings and within-run races. Thought: implement helper first, migration and setup/upgrade in disjoint implementer lanes, then retrieval, regression guards and architecture documentation; integrate and verify before delivery review | Current operator decisions and completed readiness review |
| 2026-09-19 | Gapfill: indexed retrieval is unreliable due this very storage mismatch and stale loaded code. Use live MCP reads first and narrow filesystem reads for missing evidence; do not rebuild the index as a workaround | index_health storage_receipt_identity_mismatch |

| 2026-09-19 | Observe: shared helper and all five consumer adoptions complete; no restamping. Helper matrix 3 tests, retrieval 148, setup/upgrade 119 and migration 116 tests pass (migration has one explicit native Windows junction skip). Public incremental index build passes with injected device drift and unchanged producer-shaped completed receipt. Standing receipt SHA256 956edd279d6734dd6335dd572bdefe3c50e3e4bb8ce596597bdbd15f4aaa6146 unchanged; fresh-process require_ready succeeds and graph health reports present with 63037 nodes and 178076 edges | AC-1–7 code and named tests; full runner pending |
| 2026-09-19 | Reflect: integration found alias-based identity sites and function-wide census exemptions. Converted authority/fence aliases and strengthened exact AST exclusions across five consumers, with safe source mutants restoring migration/setup/retrieval equality all detected. This is bounded syntax detection, not arbitrary dataflow proof | test_direct_identity_equalities_are_only_reviewed_boundaries |
| 2026-09-19 | Landing controls: restore device gate fails explicit public build success assertion; bypass inode comparison fails matrix; malformed-as-unavailable fails malformed matrix. Remove checkpoint preservation fails producer resume assertion; bypass handoff comparison fails incoming hook refusal. No shared source mutated | in-memory mutant probes; test_build_accepts_device_drift_without_restamping_receipt; IdentityTests; setup/reconciliation/handoff regression tests |

| 2026-09-19 | Fresh canonical wf setup --check --json reports ready, no actions/reasons, with receipt path+inode/device_drift=true diagnostics. Five previously graph-blocked EvidenceNodesStayQueryableTests now execute and pass with zero skips. Full runner encountered unrelated dashboard process-visibility failures; direct ps probe is denied by sandbox, so rerun with host process visibility is in progress | /tmp/storage-setup-check.json; /tmp/storage-graph-regression.log; /tmp/storage-dashboard-tests.log |

| 2026-09-19 | Reflect: delivery security probe demonstrated the incoming helper could execute a changed selected archive before its recorded hash refused it. Restore validation ordering and execute only the exact archive bytes whose digest was checked; add a public-hook race regression and independently reverify before restoring AC-7 | STORAGE-D1; independent temporary archive marker probe |

| 2026-09-19 | Thought/Observe: repair cycle 2 recorded before code edits. Incoming helper now validates recorded archive digest before execution and executes the exact bytes it hashes, preventing hash/reopen races. Public pre_extract test injects replacement before validation and after outer hash; both refuse with marker absent and checkpoint bytes unchanged. Upgrade guard suite 25 tests passes; independent code/security replay pending. First host-visible full run passed 9375 tests/109 files, but repair invalidated that receipt; fresh full rerun started | STORAGE-D1; test_changed_archive_never_executes_incoming_identity_helper |

| 2026-09-19 | Observe: STORAGE-D1 independently completed in code and security lanes; both typed reverifications recorded, aggregate cycle 2 complete. Exact-byte hash guard removal fails the after-outer-hash regression. Source, security, architecture and docs delivery approvals recorded. Final QA/council await current-tree full suite. Clarification: the census label SetupReconciliation denotes the actual setup_reconciliation.session._inspect owner | /tmp/storage-d1-reverify.json; typed review ledger |

| 2026-09-19 | Observe: final post-repair framework run OK: 9376 tests across 109 files in 291.635s, 21 aggregate skips. Fresh receipt inputs_hash 2e520e4c28609f2978957bf00c5cd2b745c07262cba448e84e9ea83c15935b37 independently matches current framework. All required ACs complete; final QA/council approve. Five device-blocked graph tests pass0skips; graph-quality suite passes102 with seven skips caused by its retired JSON reader. No source change or manual index rebuild was used to remove those unrelated skips. All recovery bytes remain unchanged | framework/test-cache.json; test_graph_quality_eval._load_project_graph; full docs validation clean; independent review artifacts |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-19 | Operator selected path plus available inode with replacement-volume ambiguity documented | Scoped reboot fix; no globally unique identity or no-new-false-accept guarantee | Persistent volume identification plus legacy recovery: broader design |
| 2026-09-19 | Operator selected no restamping; preserve pure reads and existing records | Avoid observer writes, lost updates and broken receipt/checkpoint/action/hash bindings | Coordinated owner-transaction restamp: unnecessary mutation machinery for this bug |
| 2026-09-19 | Keep path binding in existing owning locators and artifact roles | Staged identities intentionally survive authorized rename | Embed paths in identity maps: breaks cutover and old equality readers |
| 2026-09-19 | Preserve within-run and persisted-to-persisted checks | These compare continuity under different lifetimes and protect race/owner binding | Broadly loosen every identity equality: unsafe scope expansion |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Same-path replacement volume reuses inode, or inode is unavailable | Explicit operator-accepted continuity limitation; retain independent schema/package/owner/continuation checks |
| Restamp or enriched returned mapping invalidates bound records | Omit restamping and enrichment entirely; test byte and mapping preservation |
| A persisted consumer retains device equality | Reviewed site census plus bounded source-derived guard and consumer regressions |
| New helper absent during bootstrap or incoming hook loading | Use existing loading mechanism and exercise pre-extraction boundary |
| Other platforms unavailable here | Injection verifies logic only; native qualification remains an explicit limitation |

## Verified Site Census

| Owner | Persisted comparison | Preserved boundary |
| ----- | -------------------- | ------------------ |
| sqlite_storage_migration | root, published/source/work/artifacts versus live stat | owned locators/roles, authorized rename, exact continuation records, same-run snapshots |
| setup_readiness._owner | receipt, action, checkpoint versus live root | read-only observation, canonical argv and owner binding |
| setup_reconciliation.SetupReconciliation._inspect | checkpoint versus live root | completed-parent SHA and exact persisted continuity |
| upgrade_extensions._validate_index_guard_handoff | handoff versus live root | package hash/token/target checks and incoming-hook loading |
| retrieval_eval._compare_index_identity | saved repository/store identity versus current identity | store inode gates same-generation only |

Census evidence: live MCP keyword/outline/read and documented shell fallback while the storage mismatch makes indexed retrieval unavailable. Historical repair script and within-run checks are excluded. Source claims were checked against current code rather than the original plan's list.


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
