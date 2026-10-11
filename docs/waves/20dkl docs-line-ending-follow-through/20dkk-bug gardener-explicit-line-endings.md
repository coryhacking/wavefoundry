# Docs LF Checkout Defaults, Gardener Preservation and Lint Compatibility

Change ID: `20dkk-bug gardener-explicit-line-endings`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-11
Wave: 20dkl docs-line-ending-follow-through

## Rationale

Make gardening safe for LF and CRLF documentation: metadata refreshes must not introduce host-dependent newlines, and resulting managed regions must still pass lint. The consumers are operators running the gardener directly or during install/upgrade on Windows, macOS, Linux or WSL2. Deliver a focused repair and regression coverage without another conversion hook, whole-tree pass or evidence folder.

Wave `20b39` already repaired review-evidence reprojection and managed-region parity for consistent LF and CRLF; those fixes are in the local 1.29.0+pvto pack. The remaining gardener publications use default text-mode writes: metadata stamping, manifest creation/update and missing handoff creation. Universal-newline reads lose the original convention; default Windows writes can produce CRLF even for an LF source. Git attributes do not control Python writes.

Product-owner acknowledgment: the operator explicitly requested automatic documentation LF attributes plus preparation, review and implementation on 2026-10-11. The docs rules are defaults; later project-owned exceptions retain authority.

## Requirements

1. Derive the publication set from every gardener-owned file write reached by the public gardener path. The four known sites above orient discovery; the actual census governs.
2. Stamp valid UTF-8, consistently LF or CRLF documents while preserving their convention and all content outside the intended date substitution. Explicit I/O must prevent host newline translation.
3. Create missing manifest/handoff files with LF bytes on every host. Reconcile existing LF/CRLF manifests in their existing convention, preserving project-owned values. Unchanged documents/manifests retain bytes and mtime; existing handoffs remain untouched.
4. Exercise actual gardening followed by production managed review-policy/review-protocol parity validation for LF and CRLF. Both valid conventions pass; content drift and malformed markers still fail. Preserve the existing upgrade reprojection and rendering behavior.
5. Preserve target selection, archive exclusion, output/MCP reporting and permissions. Add no extra upgrade scan, post-edit conversion hook, persistent report or evidence directory.
6. Install/setup/render/upgrade must publish managed defaults `docs/**/*.md text eol=lf` and `docs/**/*.json* text eol=lf`. Put their bounded managed block before project-owned attribute rules so Git last-match precedence preserves explicit project exceptions. Keep the existing framework launcher/hook/batch block and its precedence unchanged; retain project lines in their existing relative order and leave rules outside docs unaffected.
7. Create/update the docs defaults idempotently, including repeat renders without byte/mtime churn. Existing loose documentation rules remain project-owned. No automatic Git configuration changes or index renormalization. Explain checkout versus gardener publication behavior, project exceptions, optional operator-owned one-time renormalization and the existing separate LF-only JSONL ledger contract.

## Scope

**Problem statement:** Gardening writes host-dependent newlines despite the repaired lint support for consistent LF and CRLF.

**In scope:**

- Explicit gardener newline reads/writes, preferring local changes over a new shared abstraction.
- Byte/mtime regressions for each publication path and garden-then-lint integration.
- Existing CRLF lint/render/upgrade tests as compatibility controls.
- Managed docs LF defaults in the existing platform renderer, self-hosted `.gitattributes`, real Git attribute tests and short contributor/testing-architecture updates.

**Out of scope:**

- Git configuration changes, automatic renormalization, extra hooks or whole-tree conversion.
- Repairing mixed-newline files, changing encoding/security policy, ledger/digest semantics or gate requirements.
- Source changes in the existing lint/render/upgrade controls without admitting a demonstrated additional defect and repreparing.

## Acceptance Criteria

- [x] AC-1: Metadata refresh through the real gardener path changes only the intended date in valid UTF-8 LF and CRLF fixtures; actual bytes prove convention preservation, including LF under native Windows translation or a separately labelled focused simulation.
- [x] AC-2: Every gardener-owned publication found by the census has byte-level coverage: fresh manifest/handoff files are LF; changed LF/CRLF manifests preserve convention and project values; unchanged publications preserve bytes and mtime.
- [x] AC-3: Gardened LF and CRLF managed regions pass production policy/protocol parity checks; genuine content drift and malformed markers fail. Existing rendering and upgrade CRLF controls remain green.
- [x] AC-4: Focused regressions preserve target/archive selection, reporting, handoff preservation and permissions. Results distinguish cross-host byte checks from native Windows qualification.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; no failure elsewhere is attributable to this change. Lasting outcomes and limitations are summarized in wave.md without a retained evidence folder.

- [x] AC-5: Fresh and existing attribute fixtures receive exactly one managed docs-default block with LF Markdown and JSON-family defaults. Real Git checks show LF despite autocrlf=true, project-owned CRLF/binary exceptions still win, launcher/batch rules are unchanged, operator rule order is preserved, and repeated renders preserve bytes and mtime.

## Tasks

- [x] Census gardener publications and implement the smallest explicit-newline repair for metadata, manifests and handoff creation.
- [x] Add byte/mtime regressions for all publication paths and native Windows coverage or a clearly labelled translation simulation.
- [x] Exercise garden-then-lint for LF/CRLF with content-drift and malformed-marker controls; run existing CRLF rendering and upgrade regressions.
- [x] Add the managed docs-default block before project rules; verify real Git checkout/attribute precedence, idempotence and unchanged launcher/batch policy.
- [x] Regenerate only self-hosted `.gitattributes`; update contributor guidance and the testing-architecture coverage row.
- [x] Complete scoped validation and required delivery reviews; consolidate lasting evidence in wave.md under the existing retention policy.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Publication repair | implementer | readiness | Owns gardener source and tests after Prepare passes |
| Compatibility validation | QA reviewer | publication repair | Uses production validators and rejection controls |
| Guidance and synthesis | coordinator | compatibility validation | Owns named docs and wave tracking |

## Serialization Points

Readiness/delivery reviewers are read-only. Implementation writes begin only after admission and typed readiness. No seed, hook, generated prompt, Git configuration or Git index renormalization edit is authorized by this change. The renderer owns the new documentation-default attribute block; operator-authored rules are preserved. Root `.gitattributes` is an intended generated target. Declare and admit any necessary additional source path and reprepare before editing it.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/testing-architecture.md`

Existing agent renderer, upgrade and validator source is read-only compatibility evidence unless an additional defect is separately admitted.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md`: gardener byte/mtime and LF/CRLF integration coverage; explicit Windows qualification limits.
- `docs/contributing/build-and-verification.md`: Git checkout defaults versus framework publication, precedence for project exceptions and optional manual renormalization.
- `docs/ARCHITECTURE.md`: N/A; no new architecture page or route.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Repairs metadata rewrite behavior |
| AC-2 | required | Covers every publication and prevents repeated churn |
| AC-3 | required | Verifies the downstream symptom without weakening parity |
| AC-4 | required | Protects existing public behavior and truthful platform claims |
| AC-5 | required | Delivers requested checkout policy without overriding project exceptions |
| AC-6 | required | Requires attributable validation and concise lasting evidence |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-11 | Final matching quiet canonical qualification green: 12,336 tests, 185 files, 12 aggregate skips, 923.332 seconds; genuine receipt transferred byte-identically after matching source hashes. Fresh code/architecture reverifications cleared the repair; code, QA, architecture and focused Council delivery approvals are current. All ACs/tasks complete; pause for operator closure. | wave.md qualification and review checkpoints; current typed ledger. Native Windows/full upgrade unqualified; temporary diagnostic artifacts remain outside the repository. |
| 2026-10-11 | Initial independent delivery found silent project-rule loss from an unterminated new docs marker; typed finding and repair-start were recorded before mutation. Repaired only new docs marker handling in the existing traversal; malformed regions refuse before attributes publication, valid precedence and inherited launcher parsing remain. Added direct byte/mtime/mode and real CLI regressions. Repaired focused 52 tests pass, zero skips; original parser plus each of three omitted refusal guards fail their targeted assertions, zero errors/skips. | RenderGitattributesBlockTests.test_malformed_docs_regions_leave_operator_bytes_and_mtime_untouched; test_public_cli_refuses_unterminated_docs_region_without_attributes_write. Original parser -> CLI exit assertion; omitted EOF/nested/end refusal -> malformed matrix. First relative-PYTHONPATH mutant invocation was excluded; absolute-path rerun proves the intended assertions. New docs source and short recovery guidance await fresh focused independent verification. |
| 2026-10-11 | Two full isolated candidates ran all 12,334 tests across 185 files with 12 aggregate skips, but supply no green receipt. First had sandbox permissions and an unrelated scratch module shadow; second cleared those and passed all owned full files, failing only the existing context-efficiency warm-p95 benchmark (66.906 ms against 10 ms under six workers). Its unchanged 98-test file passed alone. | Preserve all assertions/budgets; final repaired-tree qualification will use four workers via the supported Python CPU-count setting. No permanent evidence folder or unrelated source repair. |
| 2026-10-11 | Readback: preserve existing LF/CRLF bytes outside metadata dates, preserve manifest no-ops, publish fresh gardener files as LF; add a separate leading docs-default attribute block and retain later project exceptions/unchanged launcher policy. Before: CRLF metadata becomes LF and Windows defaults can emit CRLF. After: only the date changes and checkout defaults are LF unless a project overrides them. Touch the declared gardener/renderer tests, contributor/testing docs and generated root attributes only. | AC-1 through AC-6; current readiness receipt and independent approvals |
| 2026-10-11 | Implemented all four gardener writes and raw metadata/manifest reads; CRLF-aware date matcher; leading managed docs defaults with loose project-rule ownership retained. Regenerated only root attributes. Focused 43 tests plus 7 existing upgrade/render controls passed, zero skips; six isolated mutants failed their targeted assertions with zero errors/skips. | GardenerLineEndingTests; ReviewCarrierCRLFParityTests; RenderGitattributesBlockTests; ReviewPolicyCRLFUpgradeTests; ReviewCarrierCRLFUpsertTests. Mutation table: old gardener and LF-only date matcher -> metadata exact-byte test; default writes -> fresh-manifest/handoff LF test; normalized manifest read -> manifest byte/no-op test; each omitted docs pin -> real-Git checkout/exception test. Temporary captures under /private/tmp, no retained evidence folder. Initial renderer invocation lacked PYTHONPATH and was excluded; corrected import/run passed. |
| 2026-10-11 | Planned gardener repair and downstream lint verification; no source edit/readiness claim | Current gardener publications; ReviewCarrierCRLFParityTests; wave 20b39 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-11 | Preserve existing consistent newlines with explicit I/O; create fresh gardener files as LF and verify production lint | Corrects the writer while keeping accepted CRLF projects working without extra upgrade work | Force every touched file to LF: whole-file churn and overrides existing conventions. Rely on Git settings or a conversion hook: does not repair the writer and adds configuration/runtime work. |
| 2026-10-11 | Add a separate leading docs-default managed block; retain the existing trailing launcher block | Git last-match precedence keeps project exceptions authoritative without changing existing launcher/batch protection | Append docs rules to the old trailing block: silently overrides explicit project docs rules. Change Git config or renormalize automatically: modifies operator checkout/index state beyond the requested defaults. |
| 2026-10-11 | Use the existing repaired lint implementation as the integration oracle | Tests already establish both valid conventions and rejected content drift | Duplicate newline-tolerant validator: extra authority/review surface and potential false acceptance. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Text reads conceal byte churn | Byte-built fixtures and exact published-byte/mtime assertions |
| POSIX tests miss Windows translation | Native Windows execution when available; otherwise an explicit simulation and qualification gap |
| Repair adds upgrade/index overhead | Preserve no-op writes/reporting and add no new scan or persistent artifact |
| Git attributes mistaken for writer guarantees | Separate checkout defaults from framework publication in guidance |
| Docs defaults override explicit project exceptions | Leading docs block and real Git last-match/binary-exception tests |

## Session Handoff

Planning only. Prepare wave and typed council readiness are required before implementation. See `docs/agents/session-handoff.md` for broader session state.
