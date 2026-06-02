# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-01

wave-id: `131bt field-feedback-round-3`
Title: Field Feedback Round 3 — Coverage Close-Outs, Construction Edges, Framework Surface

## Objective

Address the three categories of follow-on work surfaced after wave 13129 closed at 1.2.1+319y:

1. **Cross-language coverage close-outs** (broadened during prepare value review):
   - `1319m` — directory aggregation extended from Go-only to eight languages (Go, Python, Java, Kotlin, C#, Scala, PHP, Swift) — every language with directory-as-grouping-unit semantics.
   - `1319o` — single-dominant-class merge extended from Python-only to Python + JavaScript + TypeScript — every popular language permitting multiple top-level classes per file.
   - `1319q` — receiver-type via optional annotations extended from JS/TS/Python to JS + TS + Python + PHP + Ruby — every supported language with optional/dynamic typing AND extractable annotations.
   Operator direction: cross-language scope from start avoids per-language reports driving fragmented scope expansion later.

2. **Construction-call edge attribution** (`1319s`) — Solaris field report on 1.2.1+319y: `code_callhierarchy(<ClassName>).incoming` returns empty despite known constructor callers, because the `1319g` PascalCase discriminator deferred the construction case without wiring the deferred path to route to the class node. Cross-language fix across Swift, Python, Kotlin, Scala, Ruby (bare-call construction); Java, C#, TS, JS, PHP (explicit-`new`); Rust (struct-literal `Foo { x: 1 }` PRIMARY + `Foo::new()` convention); and Go (composite-literal `&Foo{}` PRIMARY + `new(Foo)` builtin + `NewFoo()` factory convention) — the earlier "Go has no class constructors" framing was incorrect. New `CONSTRUCTION_RESOLVED` confidence tag preserves diagnostic clarity.

3. **Framework surface hygiene** — MCP tool descriptions are roughly 3 releases behind shipped capability (`131ar`), and the framework's release-history file structurally encourages chronological build logs rather than per-version operator-impact prose (`131at`). Both gaps surfaced in the Solaris feedback report. `131at` also renames `RELEASE_NOTES.md` → `CHANGELOG.md` (stronger filename convention) and relocates to `.wavefoundry/CHANGELOG.md` (project-level, not framework-internal). `131ar` additionally ships the `min_confidence` parameter on `code_impact`, `code_callhierarchy`, `code_graph_path` — operator direction during prepare: rather than documenting client-side filtering, the framework owns the filter at the source. `131at` should ship first so `131ar`'s changelog entry lands at the new location and format.

## Changes

Change ID: `1319m-enh go-file-grouping-package-to-directory`
Change Status: `implemented`

Change ID: `1319o-enh class-module-merge-python-dominant-class`
Change Status: `implemented`

Change ID: `1319q-enh receiver-type-js-ts-python-optional-annotations`
Change Status: `implemented`

Change ID: `1319s-bug construction-call-edges-to-class-node`
Change Status: `implemented`

Change ID: `131ar-doc mcp-tool-descriptions-sync-with-shipped-capabilities`
Change Status: `implemented`

Change ID: `131at-enh changelog-cumulative-project-level`
Change Status: `implemented`

Change ID: `131d8-enh mcp-reload-refreshes-tool-schemas`
Change Status: `implemented`

Change ID: `131e2-enh stale-graph-auto-rebuild-on-query`
Change Status: `implemented`

Change ID: `1319v-bug error-wrapped-class-declaration-recovery`
Change Status: `implemented`

Change ID: `131bu-bug mcp-reload-description-refresh-host-restart-signal-plus-polish`
Change Status: `implemented`

Change ID: `131ht-bug pack-selector-build-suffix-temporal-ordering`
Change Status: `implemented`

Completed At: 2026-06-02

## Wave Summary

Wave `131bt` (Field Feedback Round 3 — Coverage Close-Outs, Construction Edges, Framework Surface) delivered 11 changes: Directory Aggregation — Cross-Language Package/Namespace Collapse, Class/Module Merge — Single-Dominant-Class Convention (Python, JavaScript, TypeScript), Receiver-Type Resolution — Optional-Typing Languages (TS, Python, JS, PHP, Ruby), Construction Call Edges Not Attributed to Class Node, Sync MCP Tool Descriptions with 1.2.x Shipped Capabilities, Rename to CHANGELOG.md, Relocate to Project Level, Cumulative Per-Version Sections, `wave_mcp_reload` Re-Registers Tool Schemas to Eliminate FastMCP Wrapper-Signature Cache, Synchronously Rebuild Stale Graph on First Query After `GRAPH_BUILDER_VERSION` Bump, Recover ERROR-Wrapped Top-Level Class Declarations from Tree-Sitter Parse Failures, Honest Description-Refresh Signal on `wave_mcp_reload` + Two Polish Fixes, and Pack Selector Picks Stale Build When Multiple Same-Semver Packs Coexist.

**Changes delivered:**

- **Directory Aggregation — Cross-Language Package/Namespace Collapse** (`1319m-enh go-file-grouping-package-to-directory`) — 18 ACs completed. Key decisions: Broaden from Go-only to eight-language directory aggregation; Exclude Rust, Ruby, JS, TS
- **Class/Module Merge — Single-Dominant-Class Convention (Python, JavaScript, TypeScript)** (`1319o-enh class-module-merge-python-dominant-class`) — 25 ACs completed. Key decisions: Broaden from Python-only to Python + JavaScript + TypeScript; Dominance gate (exactly-one-class) is per-language opt-in via `_CLASS_MODULE_MERGE_DOMINANCE_GATE_LANGS` set
- **Receiver-Type Resolution — Optional-Typing Languages (TS, Python, JS, PHP, Ruby)** (`1319q-enh receiver-type-js-ts-python-optional-annotations`) — 15 ACs completed. Key decisions: Broaden from JS/TS/Python to JS+TS+Python+PHP+Ruby; Annotation-presence gate (no inference)
- **Construction Call Edges Not Attributed to Class Node** (`1319s-bug construction-call-edges-to-class-node`) — 26 ACs completed. Key decisions: Option B (route construction to class node); New `CONSTRUCTION_RESOLVED` confidence tag
- **Sync MCP Tool Descriptions with 1.2.x Shipped Capabilities** (`131ar-doc mcp-tool-descriptions-sync-with-shipped-capabilities`) — 18 ACs completed. Key decisions: Bundle Workstreams A + B + C in one change; Field 5 (RELEASE_NOTES in dist) closed without action
- **Rename to CHANGELOG.md, Relocate to Project Level, Cumulative Per-Version Sections** (`131at-enh changelog-cumulative-project-level`) — 20 ACs completed. Key decisions: Relocate to `.wavefoundry/CHANGELOG.md`; Single source of truth = wavefoundry repo's `.wavefoundry/CHANGELOG.md`; consumer copy is overwritten on upgrade
- **`wave_mcp_reload` Re-Registers Tool Schemas to Eliminate FastMCP Wrapper-Signature Cache** (`131d8-enh mcp-reload-refreshes-tool-schemas`) — 9 ACs completed. Key decisions: Extend `wave_mcp_reload` rather than replace the decorator-introspection model with explicit JSON schemas; Re-register all first-party tools rather than tracking per-tool dirty state
- **Synchronously Rebuild Stale Graph on First Query After `GRAPH_BUILDER_VERSION` Bump** (`131e2-enh stale-graph-auto-rebuild-on-query`) — 8 ACs completed. Key decisions: Synchronous rebuild on first query (~10 s once per upgrade); Per-process mtime cache to avoid re-checking the version on every query
- **Recover ERROR-Wrapped Top-Level Class Declarations from Tree-Sitter Parse Failures** (`1319v-bug error-wrapped-class-declaration-recovery`) — 17 ACs completed. Key decisions: Recover via source-text prefix pattern + `type_identifier` child presence; Scope recovery to `{swift, kotlin, scala, java, csharp}`
- **Honest Description-Refresh Signal on `wave_mcp_reload` + Two Polish Fixes** (`131bu-bug mcp-reload-description-refresh-host-restart-signal-plus-polish`) — 15 ACs completed. Key decisions: Send `notifications/tools/list_changed` ourselves rather than instructing operators to restart; Bundle polish 1 + polish 2 into the same change as Aceiss bug 1
- **Pack Selector Picks Stale Build When Multiple Same-Semver Packs Coexist** (`131ht-bug pack-selector-build-suffix-temporal-ordering`) — 9 ACs completed. Key decisions: Original plan: fix the selector tie-break, leave the suffix encoding alone; **Amendment: also fix the encoding** via [[131bu]] integer-packed packing
## Journal Watchpoints

- **Sequencing — land `131at` before `131ar`.** `131ar` writes a changelog entry as part of its release-notes step. If `131at` (rename + relocate + cumulative semantics) lands first, `131ar`'s entry lands at `.wavefoundry/CHANGELOG.md` with correct narrative shape. If reversed, `131ar` writes to the soon-to-be-removed `.wavefoundry/framework/RELEASE_NOTES.md` and has to be migrated.
- **Phase 0 audits required before code edits on `1319s`.** Two audits gate the framework gate: (a) baseline `walk_calls` behavior on `new_expression`/`object_creation_expression` for Java/C#/TS/JS/PHP and `::new` for Rust — determines whether AC-7 to AC-13 are close-out confirmations or extensions; (b) `server_impl.py` `code_callhierarchy` behavior on class-node queries — resolves the double-counting risk before edge emission. Both findings recorded in the change's Decision Log.
- **`GRAPH_BUILDER_VERSION` bumps.** `1319s` bumps 14 → 15. `1319m`, `1319o`, `1319q` all change graph-builder behavior and may need bumps too. Coordinate to a single bump per shipped release rather than per-change.
- **Broadened language scope from prepare review.** `1319m` (Go → 8 languages), `1319o` (Python → Python+JS+TS), `1319q` (JS/TS/Python → +PHP+Ruby), `1319s` (added Rust struct-literal + Go construction shapes). Implementation scope is significantly larger than the original drafts; per-language detection rules across the new languages drive most of the additional work.
- **MCP server restart no longer required for description / parameter changes after `131d8`.** Wave 131bt extended `wave_mcp_reload` to tear down and re-register the FastMCP tool surface so parameter schemas and description strings refresh in-process. Operators run `wave_mcp_reload` then `/mcp` (host reconnect) — no full server restart needed except when `server.py` itself changed.
- **Seed-first doc workflow applies to `131ar` and `131at`.** seed-211 / seed-240 edits land before per-project rendered prompts; downstream projects pick up the changes on upgrade. Open `seed_edit_allowed` for these edits.
- **Confidence-tag forward compatibility.** Resolved during prepare: `131ar` accepts `CONSTRUCTION_RESOLVED` in the `min_confidence` validator upfront, even though no edges carry the tag until `1319s` lands. When `1319s` ships, edges flow through the existing filter with no `131ar` follow-up. Level ordering treats `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` as peer level-1 — same evidence quality, different call shape.

## Review Evidence

- wave-council-readiness: approved 2026-06-01 — Six changes admitted, two themes: graph attribution coverage (`1319m` Go directory aggregation, `1319o` Python merge with dominance gate, `1319q` JS/TS/Python receiver-type via optional annotations, `1319s` cross-language construction-call edges) and framework surface hygiene (`131ar` MCP description sync, `131at` CHANGELOG rename+relocate+cumulative). Scope is coherent: closes the deferred exclusions from wave 13129 plus the Solaris field report drift items. Sequencing constraints captured in journal — `131at` before `131ar` (changelog rename lands first); `1319s` Phase 0a/Phase 0b audits gate the framework_edit_allowed gate. Cross-change coordination: `1319s` and `1319q` both touch `walk_calls` dispatch; `1319s`/`1319o`/`1319q` all bump `GRAPH_BUILDER_VERSION` — single bump per shipped release. Required reviewer lanes: code-reviewer for `1319m`/`1319o`/`1319q`/`1319s` graph-builder changes; qa-reviewer for all six (per-language regression test coverage); docs-contract-reviewer for `131ar` seed-211 restructure and `131at` seed-240 rewrite; release-reviewer for `131at` packaging-workflow change. Product-owner: N/A — framework field-feedback follow-on. Wave is ready for implementation.
- wave-council-readiness-supplement: approved 2026-06-01 — Operator direction during prepare value review broadened four changes for cross-language coverage: `1319m` (Go → Go + Python + Java + Kotlin + C# + Scala + PHP + Swift; eight directory-grouping languages); `1319o` (Python → Python + JavaScript + TypeScript; three multi-class-permitting languages with single-dominant-class convention); `1319q` (JS+TS+Python → JS + TS + Python + PHP + Ruby; five optional-typing languages); `1319s` (added Rust `struct_expression` as primary Rust construction shape plus Go composite-literal/`new()`/factory-convention shapes — correcting the prior "Go has no class constructors" framing). Implementation scope is significantly larger; helper-pattern reuse across languages mitigates the per-language detection cost. `131ar` reverted to option 1 (pure docs sync, no `min_confidence` parameter) per YAGNI value review — the Solaris field report asked for documentation, not for a server-side filter; client-side filtering is one line per consumer. Wave remains implementation-ready.
- wave-council-delivery: approved 2026-06-02 — Unanimous council synthesis at close. Eleven changes implemented (eight admitted + three added during close-out: `1319v` ERROR-class recovery for Solaris field validation, `131bu` MCP `tool_list_changed` notification + qualified-id alias + BFS confidence tie-break for Aceiss field validation, `131ht` pack-selector mtime tie-break + same-semver warning + integer-packed suffix encoding amendment). 2,169 framework tests green, docs-lint clean, all ACs checked across all eleven change docs. Code-reviewer verified cross-change consistency on `walk_calls` dispatch + `GRAPH_BUILDER_VERSION` single-bump-per-release coordination + the 131bu encoding-rewrite math; qa-reviewer verified per-change regression coverage including the late-added 1319v 12-unit-test predicate suite and 131bu's reload-path tests; docs-contract-reviewer verified `wave_graph_report` 117-line docstring + seed-160 restart-fallback semantics; release-reviewer verified 1.3.4 ship at `wavefoundry-1.3.4.p2q0.zip` with auto-rebuild safety-net via 131e2; red-team strongest concern (host doesn't honor `tools/list_changed`) mitigated by honest diagnostic + seed-160 fallback documentation; reality-checker verified Solaris + Aceiss field-validation closure. Documented non-blocking residuals: `_existing_prefixes` regex false-positive on "close-*" filenames (latent, scoped out of wave); 131hh FastMCP-primitives plan remains unattached for future work; prior 1.3.2 same-semver builds remain in dist (selector picks newer by mtime). Wave is ready to close.
- operator-signoff: approved 2026-06-02 — operator requested close after delivery council review.

## Prepare Review Evidence

- code-reviewer: approved 2026-06-01 — graph-builder changes for `1319m`, `1319o`, `1319q`, `1319s` reviewed; discriminator-chain ordering (construction → receiver-type → standard) and per-language detection rules consistent with existing `_resolve_<lang>_receiver_type` pattern. `131ar` parameter addition (`min_confidence` on three tools + shared level-ordering helper) reviewed; single source-of-truth ordering forward-compat with `CONSTRUCTION_RESOLVED`.
- qa-reviewer: approved 2026-06-01 — per-language regression test ACs cover every in-scope language with explicit positive + negative cases. `1319s` negative-case ACs (method-named-as-class, type-name-as-value reference, navigation-expression boundary, self-call preservation) verified. Gap noted: `1319q` Phase 2 JSDoc regex extraction needs fixture coverage for block-comment edge cases before phase 2 ships.
- docs-contract-reviewer: approved 2026-06-01 — `131ar` seed-211 restructure preserves anchors; `131at` seed-240 rewrite follows seed-first workflow; `1319s` seed updates for `code_callhierarchy`/`code_impact`/`code_graph_path` bundled in tasks. Confidence-level guidance in `131ar` written extensibly for `CONSTRUCTION_RESOLVED` forward-compat.
- release-reviewer: approved 2026-06-01 — `131at` packaging-workflow change reviewed; zip-layout invariant break accepted and documented; MANIFEST-based prune handles cross-directory relocation per Phase 0 audit plan. `GRAPH_BUILDER_VERSION` single-bump strategy across `1319s`/`1319o`/`1319q` ships coordinated. `131ar` `min_confidence` parameter on three tools requires MCP server restart to expose (same FastMCP wrapper-signature-cache limitation flagged in journal watchpoints); restart requirement carries into the changelog entry's required-action callout.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-01: PASS** (moderator: council-moderator; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: `1319s` symbol-lookup precondition must be scope-aware (lexical reachability), not name-only — method named `Foo` in `class Outer` with sibling `class Foo` is the false-positive case to verify; strongest-alternative: split `1319s` into `1319s-A` (5 bare-call languages) + `1319s-B` (6 explicit-`new` languages) for incremental value delivery — flagged as implementation-detail decision, not a prepare blocker)
  - Red-team strongest concern: scope-aware (lexical) symbol-lookup precondition on `1319s`; explicit test required for method-named-as-class + sibling-class case.
  - Reality-checker strongest alternative: split `1319s` into bare-call and explicit-`new` phases for incremental Swift Solaris-reproducer shipping; defer to implementation.
  - Docs-contract residual: `131ar` confidence-level guidance forward-compat for `1319s`'s `CONSTRUCTION_RESOLVED` tag — write extensibly, not as a closed enum.
  - Architecture, security, qa: no blocking concerns. QA gap on `1319q` Phase 2 JSDoc regex coverage carried into qa-reviewer Prepare Review Evidence.
- **Prepare wave — readiness verdict [prepare-readiness] — 2026-06-01: PASS**
  - All six admitted change docs are wave-owned under `docs/waves/131bt field-feedback-round-3/`.
  - Required sections are present on all change docs.
  - AC priority is recorded on each admitted change (populated at Prepare wave per the per-change AC Priority table).
  - Wave Council readiness signoff is recorded in `## Review Evidence`.
  - Product-owner acknowledgment is not required because this wave is framework field-feedback follow-on.

## Dependencies

- No external wave dependencies.
- Implicit dependency: closure of wave 13129 (already closed 2026-06-01 at 1.2.1+319y) — this wave addresses the deliberate exclusions and field-feedback drift from that wave's ship.
