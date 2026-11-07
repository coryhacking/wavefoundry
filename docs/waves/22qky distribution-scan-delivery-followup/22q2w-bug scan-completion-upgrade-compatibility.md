# Report incomplete secret scans and incompatible upgrades

Change ID: `22q2w-bug scan-completion-upgrade-compatibility`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-06
Wave: 22qky distribution-scan-delivery-followup

## Rationale

Waveforge's review found that an eligible file can exhaust scanner limits without failing the scan result, and that previously supported project rule syntax can become invalid only after an upgrade publishes the new scanner. A bounded current-tree probe confirmed the first mechanism: `check_hardcoded_secrets` returned no failures for a text file over the file-size guard and persisted a guard-skip notice. A second probe confirmed rejection of a project global filter under the current profile. Worker-failure and upgrade-publication consequences are source-grounded inferences pending delivery probes.

## Product Intent

Operators should be able to distinguish a completed scan from unexamined eligible content, and learn that project rules are incompatible before adopting an upgrade. AC-1 through AC-4 establish that operational outcome. This supports the adopted vision's trustworthy evidence and dependable tooling; it does not prove credential-detection completeness or change the product destination. Documentation should explain the Wavefoundry Python scanner clearly while retaining necessary upstream provenance and test evidence.

## Requirements

1. An eligible file whose scan cannot complete because of a worker failure, resource limit, unreadable input or incomplete result must produce an explicit incomplete outcome, never `clean: true`. Retain findings obtained before failure and do not clear prior dispositions or record affected content as clean in either cache producer. Preserve bounded execution and no unbounded fallback.
2. Separate intentional policy exclusions (including supported binary omissions, configured allowlists and excluded runtime directories) from failed attempts to scan eligible content. Existing explicit exclusions do not become failures merely because they were not scanned. Missing or malformed coverage evidence must not be interpreted as demonstrated completion.
3. Carry bounded structured completion, affected paths/reasons and truthful counts through the scanner CLI and MCP. Enforcing scanner/CI and close paths must reject unresolved eligible-content incompleteness, including an outstanding persisted failure when the current incremental run does not revisit its file. Retain record-only treatment of detected secrets during ordinary documentation recording; incompleteness is a distinct operational error. Resolve a stored failure only through proven complete coverage, confirmed removal or a currently applicable explicit exclusion. No new findings-disposition workflow or blanket suppression is introduced.
4. Before framework publication, supported upgrade preview/apply paths must assess the project's rules against the incoming framework profile and rules. Report incompatible fields with safe file, rule and field identifiers and a migration remedy; invalid or incomplete validation must not be represented as compatible. Preserve installed framework/project rule bytes on refusal. Check supported retained/retry paths at the point where new content could be published. Avoid project-value/source disclosure and do not execute provider actions or arbitrary imported expressions outside the existing bounded worker.
5. Do not silently discard legacy fields, reinterpret CEL as Expr, or automatically rewrite local policy. Document supported conversions and cases needing operator decisions. A prior runner cannot be retroactively patched: explain any requirement to use the updated supported runner/bridge for pre-publication protection, and do not claim that a post-publication check prevented installation.
6. Explain the rule-change full rescan and possible new findings, preserving matching prior dispositions. Do not broadly disable generic rules or exempt evidence JSON. Changes to detection/allowlisting require a demonstrated false-positive case with retained positive controls; this change does not presume such a rule change is needed.
7. Present the product as Wavefoundry's Python secret scanner. Consolidate upstream revision, rule/asset provenance, licenses and compatibility limits at their canonical notice/documentation owners. Preserve all applicable notices, source-only qualification fixtures and meaningful compatibility tests; no upstream binary dependency or upstream final-release wait is added. Stable internal profile identifiers and module names need not be renamed.
8. Label synthetic fixture credentials and upstream example-value allowlist patterns clearly. Remove contiguous credential-shaped example literals from the three rule configurations through behavior-equivalent regex representation, verified against original matching and non-allowlisted positive controls; retain provenance and distinguish adapted reference syntax from byte-identical upstream text. Do not obfuscate actual credentials or weaken detection. Explain optional `.gitleaksignore` interoperability with an explicit supported invocation/path. Add fingerprints only when produced by an observed compatible scan and verified to identify synthetic data; do not fabricate fingerprints, blanket-exclude fixture directories or claim another server reads the file. Explain GitHub's separate configuration and leave Wiz/Veracode compatibility unclaimed without documentation or execution. External security configuration remains project-owned. If the receiving scanner is unknown/unavailable, document the qualification step and limitation while preserving detection controls. This does not make `.gitleaksignore` a second Wavefoundry policy authority.

## Scope

**In scope:** Scanner completion and persisted coverage readers, the two scanner cache producers, CLI/MCP and close integration, incoming-rule upgrade checks, focused regression tests, scanner/release/fixture documentation, explanatory TOML comments and equivalent example-value regex representation in scan-rules.toml and fixtures/betterleaks/baseline.toml and upstream.toml. Derive affected callers from completion publication/consumption and framework publication paths, rather than treating the field report's sample locations as exhaustive.

**Out of scope:** Changing detection semantics without demonstrated evidence, replacing Python regex or the worker, automatic local-rule migration, new network or binary dependencies, repository-wide historical prose rewrites, adoption of a future upstream release, Waveforge's own source edits, and unsupported claims of server push-policy qualification. No vision, seed, unrelated release version, existing product README work or generated platform surfaces are rewritten as part of this change except the existing scanner paragraph, preserving prior edits.

## Acceptance Criteria

- [x] AC-1: Public scanner entry points distinguish completed, explicitly excluded and attempted-incomplete files; timeout/worker failure and byte/line/match limit controls cannot yield clean success. Known-bad incomplete-as-empty behavior fails. Existing findings survive incomplete rescans and incomplete files remain eligible for retry in both cache producers.
- [x] AC-2: CLI/MCP report completion and bounded affected-path evidence accurately; close refuses an outstanding eligible scan failure even when an incremental scan touches another file. Complete retry/removal/current explicit exclusion clear that failure appropriately. Intentional binary/runtime/allowlist exclusions retain their existing admissible behavior, and malformed coverage evidence is explicit.
- [x] AC-3: Upgrade preview and apply exercise incoming-profile checks before framework publication. An incompatible project rule produces an actionable safe diagnostic and leaves installed/project bytes unchanged; valid custom rules, allowlist-only policy and absent project files remain supported. Tests distinguish incoming from installed rule syntax and cover a supported retry/retained path without claiming to update an older runner automatically.
- [x] AC-4: Migration guidance identifies retired fields and expression-language differences, explains rescan and existing-disposition behavior, and never promises generic rules or review evidence are broadly exempt. Changed docs agree with tested completion/enforcement behavior.
- [x] AC-5: Shipped scanner documentation identifies the Python implementation and links one canonical provenance/notice owner; required notices and packaged asset verification remain intact. The three configurations no longer contain contiguous Google-key example literals in their allowlist filters; equivalent representation still suppresses the same original examples while non-allowlisted positive controls remain detectable. Synthetic fixture/placeholder guidance describes `.gitleaksignore` accurately, includes no invented fingerprints and states unqualified receiving-server behavior. Existing positive fixtures remain effective; packaging excludes source-only oracles as before. Structural removal of literal shapes is measured separately from unobserved third-party alert reduction.
- [x] AC-6: The change's focused suites and added tests pass, its authored/edited documentation validates, and no failure elsewhere is attributable to this change. Regression controls cover a renamed distribution profile where paths/terms are configurable.

## Tasks

- [x] Define the completion/exclusion classification using existing per-file outcomes and persisted skip authority; implement reader, CLI/MCP and gate propagation.
- [x] Add incoming-rule compatibility preflight and safe migration diagnostics on supported upgrade paths.
- [x] Add public-path regression and known-bad controls, including cache retention, persistent failure, legitimate exclusions and upgrade non-publication.
- [x] Consolidate scanner/release/fixture guidance and placeholder comments without removing provenance or introducing unqualified suppressions.
- [x] Record verification and review outcomes, including remaining external scanner and native-platform limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Completion and compatibility | scanner implementer | readiness | Scanner-specific source/tests |
| Documentation and fixture guidance | coordinator | readiness; tested behavior | Preserve shared docs and unrelated edits |
| Independent review | required reviewer lanes | implementation | Read-only evidence and focused verification |

## Serialization Points

Serialize `upgrade_wavefoundry.py` and `wf_server/docs_handlers.py` edits with change 22q2v. Coordinator owns shared CHANGELOG/spec/build documentation. Review targets below declare possible direct integration owners; narrow implementation to the actual completion/publication call paths.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/`
- `.wavefoundry/framework/scripts/scanner_skips.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/run_secrets_scan.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_lib.py`
- `.wavefoundry/framework/scripts/wf_server/docs_handlers.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/upgrade_handlers.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/scan/`
- `.wavefoundry/framework/scan-rules.toml`
- `.wavefoundry/framework/README.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/data-and-control-flow.md`

Root documentation scope: current unreleased CHANGELOG entries and the existing README scanner paragraph only. Framework README, build documentation, threat-model and MCP edits are limited to scanner paragraphs/contracts. `scan-rules.toml` and fixture `baseline.toml` / `upstream.toml` receive explanatory comments and behavior-equivalent example-value regex representation; add `tests/fixtures/betterleaks/README.md`. Keep `scan/NOTICE.md`, manifest, profile IDs and existing oracle bytes stable. `.gitleaksignore` is guidance only unless an actual compatible scanner report becomes available; no scanner is currently installed, so no fingerprint file is required or fabricated. A small dedicated compatibility helper may be added where the qualified upgrade publication path needs it.

## Affected Architecture Docs

Update `docs/architecture/data-and-control-flow.md` for scanner completion and upgrade preflight; `docs/architecture/threat-model.md` for bounded worker failure reporting. Update MCP and build documentation at the same boundaries. No architectural ownership transfer or new service.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevent incomplete work appearing clean |
| AC-2 | required | Make downstream gate consumers act on the evidence |
| AC-3 | required | Avoid publishing a knowingly incompatible rule upgrade |
| AC-4 | required | Give operators a usable migration path |
| AC-5 | required | Preserve provenance and positive controls while reducing clutter |
| AC-6 | required | Verify the changed surfaces and downstream compatibility |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | Delivery repair cycle 1: both cache producers evict prior rows for failed or unpublished attempts and retry persisted incomplete paths before cache filtering and the indexer no-work shortcut. Current exclusions and removals remain scanner-owned; no new ledger or automatic full scan was added. | 12 completion tests passed in 2.681s, including both real-cache transition matrices; 29 cache tests passed in 8.263s; 12 skip-ledger tests passed in 0.057s; 28 indexer-scan tests passed in 7.963s. Independent QA recheck and canonical suite remain pending. |
| 2026-11-06 | Implemented scanner completion propagation, persistent eligible-failure gates and incoming-rule preflight. AC-1 through AC-3 and implementation tasks are complete. | Focused controls: 11 completion tests, 1 MCP result matrix, 5 incoming-rule tests and 13 existing upgrade preview tests passed; 28 cache and 19 close controls passed. Existing 171 scanner tests had only an outdated provenance assertion fail after guard-expectation updates; the corrected provenance test passed separately. Full suite, renamed-profile qualification and independent delivery review remain with the coordinator. |
| 2026-11-06 | Actual repository retries completed the two formerly guard-skipped eligible files in 2.940s and retired their failures through the scanner owner. Zero outstanding incomplete files remain; 19 recorded intentional binary omissions remain visible. No exclusions or ledger rows were hand-edited. | `check_hardcoded_secrets(record_only=True)` on ELK bundle and 21xq1 evaluation evidence; disposable `eligible-retry.json`. This is two-file coverage, not a new whole-tree claim. |
| 2026-11-06 | Three TOMLs now use equivalent singleton-character example patterns, with provenance comments and source-fixture guidance. One hygiene test passes all 48 original cases and positive controls; a literal-restoration mutant fails all three subtests. Existing engine suite passes 30 tests, including pinned reference outputs and pack exclusion. No oracle bytes or notices changed; no external scanner alert reduction claimed. | `test_scanner_fixture_hygiene.py` (1 test, 0.101s), `test_betterleaks_engine.py` (30 tests, 8.623s); in-memory known-bad Path.read_text substitution. |
| 2026-11-06 | Readback: coordinator owns AC-4/AC-5 documentation, three TOML example-pattern representations and a focused hygiene test. Original example matching must stay identical while literal key shapes disappear; external scanner policy is documented, never silently installed. Shared source integration remains with assigned implementers. | Current readiness receipt and actual Expr/CEL feasibility probes; preserve NOTICE, asset manifest and oracle bytes. |
| 2026-11-06 | Additional read-only feasibility: the 16 example patterns in each TOML remain equivalent after replacing the literal initial A with a singleton character class; actual Expr/CEL evaluators suppress all examples and retain a non-allowlisted positive control. The current bounded worker scanned the complete 1,585,569-byte ELK bundle in 1.27 seconds with complete=true and no findings, without changing coverage records. | `expr_filter.compile_filter` / `evaluate_filter`, `cel_filter.eval_filter`; `betterleaks_worker.worker_request` full-fragment scan. Third-party scanner behavior remains unobserved. |
| 2026-11-06 | Planning only. Bounded temporary-root probe called `check_hardcoded_secrets` on a 280-byte ordinary text file with the file-size cap injected as 10 bytes: no failures, persisted `file too large` skip. A project global filter under the current profile returned the unsupported override diagnostic. No source changes or broad scan. | `check_hardcoded_secrets`, `load_merged_ruleset`, `scanner_skip_notice`; current source inspect of `_scan_upstream_raw`, `run_secrets_scan.main`, `wf_scan_secrets_response`, `phase_preflight` |
| 2026-11-06 | Readback: eligible incomplete scans will become explicit unsuccessful outcomes through scanner consumers and closure; intentional exclusions remain admissible. Incoming rule validation will refuse incompatible upgrades before publication. Preserve bounded workers, existing findings/dispositions and source fixtures. Long lines in the upstream profile may reach the already bounded full-fragment worker, avoiding the separate legacy truncation guard; legacy behavior stays bounded. | AC-1–AC-3; scanner core/cache readers, CLI/MCP/close consumers and upgrade preflight; shared writes serialized with sibling changes. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-06 | Extend existing per-file outcomes and skip authority into explicit completion enforcement. | The motivating incomplete-file probe must become visibly unsuccessful at its consumers; reusing evidence avoids another ledger. Legitimate exclusions need separate classification to avoid unnecessary blocks. Release success is observable when an injected incomplete run cannot report clean and a complete retry restores it. | Logging only leaves CI/MCP green; a second scanner ledger creates competing cleanup/authority paths. |
| 2026-11-06 | Validate incoming merged configuration before publication; refuse unsupported semantics with instructions. | Installed-only checking cannot predict a new parser's result. No automatic syntax substitution is proven equivalent. | Post-install warning is too late; automatic CEL translation risks changing local policy. |
| 2026-11-06 | Retain existing bounded worker and source fixtures; reduce repeated branding in prose only. | Own implementation qualification is the release criterion; upstream final release is not a dependency. | Renaming internal modules/profile IDs adds migration risk without improving user understanding; broad fixture exclusions weaken detection. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Historical advisory skips block legitimate workflows | Classify intentional exclusions separately; test persisted older entries and truthful absence/invalid evidence |
| Preflight executes new or hostile configuration with excess authority | Reuse bounded offline validation and verified incoming-pack boundaries; no provider execution; safe identifiers only |
| Integration overlaps another change | Serialize shared file writes and run consumer-level tests after integration |
| Server ignores `.gitleaksignore` or fingerprints differ by scan mode | Document supported invocation; retain external qualification limitation; no fabricated suppression claim |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
