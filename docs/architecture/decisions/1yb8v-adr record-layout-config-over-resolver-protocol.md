# 1yb8v-adr — Record Layout Is a Set of Fork-Editable Constants, Not Configuration and Not a Discovered Resolver

Owner: Engineering
Status: accepted
Last verified: 2026-09-17

## Context

The wave and plan record roots (`docs/waves`, `docs/plans`) were hardcoded across 35 non-test modules: 16 two-token joins in `server_impl.py`, string-form joins in `wave_lint_lib`, and one or two sites each in 27 other scripts, plus path-prefix checks in retrieval ranking and in the `wave` document classifier. An integrator whose repository organizes records differently had to patch every site and re-patch on every upgrade. The modularity RFC (`docs/reports/wavefoundry-modularity-rfc.md`) proposed a `PathResolver` protocol bound by auto-discovering a Python module on a conventional path inside the target repository. Waveforge's real fork (`docs/reports/waveforge-fork-audit.md`) confirmed the need with its own bespoke `set_root` resolution layer.

The first delivery of wave `1y0gz` resolved the roots at runtime from a `record_layout` block in `docs/workflow-config.json`. The delivery review (2026-09-17) raised three findings that all trace to the layout being runtime-dynamic: a warm `McpRepoCache` keyed on the waves directory fingerprint alone and served stale wave paths after a layout edit; the lint corpus and gardener walkers followed `docs/` only, so a relocated root outside `docs/` was never linted; and the resolver's identity checks compared roots by spelling and containment rather than by identity. The operator redirected the design during that review: the roots are constants.

## Decision

Record roots are module constants in one stdlib-only module, `.wavefoundry/framework/scripts/record_paths.py`, and nowhere else: `WAVES_ROOT = "docs/waves"`, `PLANS_ROOT = "docs/plans"`, `NESTED = False`, `MAX_DEPTH = 4`. A downstream fork that keeps its records elsewhere edits these constants when it merges the framework. Nothing is read from configuration at runtime: a `record_layout` block in `docs/workflow-config.json` or a `wave_implement.wave_root` key is inert, there is no legacy fallback, and there is no migration hint. The server never imports repository-supplied code to find its records.

Validation is still fail-closed, applied to the constants against the repository root: an absolute, `..`, or empty root, a root or an ancestor of an absent root that is a file or a dangling symlink, a root that escapes the repository through a symlink, a root or ancestor that is a symlink alias or case alias of the canonical in-repository directory (an in-repository symlink is no longer accepted, because every lifecycle tool already refused it), equal or nested roots (by spelling or by inode, judged against the nearest existing ancestor of an absent root), a non-boolean `NESTED`, or a `MAX_DEPTH` outside 1 to 8 raises `RecordLayoutInvalid` from `load_record_roots`. Docs-lint reports that as the `record_layout_invalid` error, and every lifecycle tool returns the same `record_layout_invalid` diagnostic and performs no read or write. `layout_constants()` returns the four values at call time so caches fold them into their keys.

## Consequences

**Positive:**
- The layout of a process is fixed at import, so every consumer (server, docs-lint, gardener, indexer, memory backfill, dashboard, upgrade) sees the same roots and no cache can be warmed under one layout and read under another.
- No repository Python executes at MCP startup in any host that auto-starts the server, which the RFC's convention-discovery design would have required.
- The shipped constants produce paths byte-identical to the pre-change literals, so cache fingerprints, rendered paths, and the golden tool-surface fixture are unchanged.
- A whole-tree census test forbids the literals from creeping back outside an explicit allowlist of comments, messages, and `pinned_evidence` (the `graph_quality_eval.py` control-corpus literal, whose SHA-256 is pinned by a shipped report pair).
- Tests relocate by patching the constants (`tests/record_layout_support.py`), which exercises the same code path a fork takes.

**Negative / tradeoffs:**
- A consumer of the packaged zip cannot relocate its records without a fork of `record_paths.py`. This is the trade accepted: such a consumer never could relocate before this wave either, and the fork edit is one file, reviewable at merge.
- `RecordLayoutInvalid` deliberately does not subclass `ValueError`, because the lifecycle tools map `ValueError` to `invalid_arguments` and path-escape diagnostics; a new exception base is one more thing to know.
- Retrieval ranking helpers take a `prefixes` tuple threaded from the nearest root owner and degrade to the unvalidated constants (`unvalidated_record_roots`) on an invalid layout rather than refusing a search; ranking is observational, so this is accepted.
- Rendered prose in seeds, `AGENTS.md`, and prompt docs still names `docs/waves` as the conventional location; a seed follow-up under the seed gate is deferred.

**Constraints imposed:**
- No module other than `record_paths.py` may construct a record path from the literals `docs/waves` or `docs/plans`; the census test enforces it.
- `record_paths.py` stays stdlib-only so docs-lint imports it in hosts without the MCP runtime, and it sits on the `server_impl.py` module-eviction list so `wf_reload_mcp` picks up changes.
- Every cache keyed on record discovery folds `layout_constants()` into its key.
- A fork that relocates the waves root must place a `README.md` under it, because docs-lint requires `<waves_root>/README.md` (`wave_lint_lib/constants.py` `WAVES_ROOT_REQUIRED_DOCS`), and lint and gardener walkers union `docs/` with the resolved roots when a root lies outside `docs/`.
- Nested wave discovery (`NESTED`, `MAX_DEPTH`) is the companion change `1y043` and does not change this decision. It is off in the shipped constants, so the flat layout stays byte-identical; the walk is bounded (`MAX_DEPTH` counts the wave folder's own depth below the waves root, so 1 means direct children only; 1 to 8, shipped 4), never follows symlinks or dot-prefixed directories, and never descends into a discovered wave folder; a wave id found at two paths is refused as `ambiguous_wave_id` before any mutation. `wf_create_wave` keeps creating at the waves root and a wave folder may be moved deeper afterwards, because every lookup is by discovery and no record stores a depth-specific path. A `parent` argument on `wf_create_wave` (or a default parent) is deliberately deferred: it would change the public tool schema guarded by the golden fixture, and relocation covers the need until an integrator states it.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| RFC `PathResolver` protocol with a module auto-discovered under the target repository | The server would execute repository-supplied Python at startup in every host that auto-starts MCP; a constant in the framework tree is reviewable at merge, a dropped-in module is not |
| `record_layout` block in `docs/workflow-config.json` (the first delivery of this wave) | A runtime-dynamic layout needs input validation of operator-typed values, cache invalidation on every config edit, and every lint and gardener walker following the configured roots; those three costs are where three delivery-review findings came from (`warm-cache-layout-flip`, `lint-corpus-docs-only`, `resolver-identity-gaps`). The trade: consumers of the packaged zip cannot relocate without a fork, which they never could |
| Constants as defaults with a config override | Keeps the runtime-dynamic surface and every one of its three costs; the constants would only be the fallback |
| Environment-variable overrides | Zero-config for one operator but invisible to reviewers and not shared across a team |
| Extend `wave_implement.wave_root` and add `plans_root` beside it | `wave_implement` is implementation policy, not layout; the key is now inert |
| Warn and fall back to the shipped constants on an invalid layout | Writes records to the wrong tree while the maintainer believes the edit is honored; fail-closed keeps the tree single-brained |

## References

- Change `1y042-enh record-roots-config-and-resolver` and companion `1y043-enh nested-record-lookup` (wave `1y0gz`)
- `docs/reports/wavefoundry-modularity-rfc.md` (RFC-2), `docs/reports/waveforge-fork-audit.md`
- `docs/architecture/layering-rules.md`, "Shared path resolution"
