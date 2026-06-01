# Go File-Grouping via Package-to-Directory Aggregation

Change ID: `1319m-enh go-file-grouping-package-to-directory`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

Wave 13129 deferred Go from the class/module merge feature (`13190`/`13196`/`1319i`/`1319k`) because Go's grouping model fundamentally differs from the other supported languages. Java/Kotlin/C#/Swift/Scala/PHP/Rust/Ruby/JS/TS use a **file-as-type-boundary** model (one dominant top-level type per file, basename usually matches type name). Go uses a **directory-as-package-boundary** model: every `.go` file in the same directory shares a `package foo` declaration, and the public API surface is the union of all `.go` files in that directory.

Applying the basename-match merge to Go would suppress nothing — Go file names (`server.go`, `handler.go`, `types.go`) don't match the type names they declare. The right Go analogue is to collapse a directory's worth of `.go` files into one node, the same way C# might collapse a `partial class` split across files.

This change designs and implements a **separate feature** — `collapse_package_to_directory` — that addresses the structural asymmetry without retrofitting class/module merge.

## Approach

A new graph-level transformation, applied as a sibling to `collapse_class_module_pairs`:

1. **Detection** — group all file-level nodes (`kind == "file"`) by directory. For each directory containing 2+ `.go` files where every file has `package <same-name>`, the directory is a candidate package.
2. **Merge** — produce a single `kind: "package"` node per directory; absorb the file nodes and re-attribute their declarations and edges to the package node. Preserve `path` as the directory path.
3. **Edge rewrite** — same pattern as the class/module merge: incoming edges from outside the package retarget to the package node; intra-package edges between merged files collapse.
4. **Opt-in flag** — new `wave_graph_report` parameter `collapse_package_to_directory` (default `False`, matching the cautious rollout of `collapse_class_module_pairs`).

## Requirements

1. New helper in `graph_indexer.py` (or a new `graph_collapse.py` module) implementing the package-to-directory collapse, mirroring `_collapse_class_module_pairs` structure.
2. New `wave_graph_report` parameter `collapse_package_to_directory: bool = False`; full MCP server restart required to expose at protocol layer (FastMCP wrapper signature cache — see wave 13129 carryover note).
3. Diagnostic field on the collapsed package node: `collapse_origin_files: list[str]` listing absorbed `.go` file paths.
4. Tests: multi-file Go package collapses to single node; single-file Go package is unchanged; non-Go files in same directory are untouched; mixed-package directories (rare but legal) skip collapse with a diagnostic.

## Scope

**Problem statement:** Go's package-equals-directory grouping has no analogue in the file-basename class/module merge feature. Operators reading a Go graph see a fragmented per-file view that doesn't match Go's mental model.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` (or new collapse module) — package collapse implementation.
- `.wavefoundry/framework/scripts/server_impl.py` — `wave_graph_report` parameter wiring.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — collapse regression tests.
- `.wavefoundry/framework/seeds/` — `wave_graph_report` parameter doc update.

**Out of scope:**

- Generalizing the collapse to other directory-package languages (Erlang OTP apps, Elixir umbrellas). Defer until operator demand.
- Cross-package symbol resolution improvements. This change is graph-structure-only.
- Renaming `collapse_class_module_pairs` for symmetry — both flags coexist.

## Acceptance Criteria

- [ ] AC-1: New collapse helper produces one package node per directory of same-package `.go` files.
- [ ] AC-2: `wave_graph_report(collapse_package_to_directory=True)` returns a graph with collapsed Go packages; default is unchanged.
- [ ] AC-3: Collapsed package node carries `collapse_origin_files` diagnostic.
- [ ] AC-4: Intra-package edges between merged files are absorbed; cross-package edges retarget to the package node.
- [ ] AC-5: Mixed-package or single-file directories are not collapsed.
- [ ] AC-6: All existing graph-builder tests continue to pass (no default-behavior regression).

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Implement directory grouping + package collapse
- [ ] Wire `wave_graph_report` parameter
- [ ] Add regression tests (multi-file, single-file, mixed-package fixtures)
- [ ] Update seed docs for `wave_graph_report`
- [ ] Run framework tests
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — graph collapse pipeline now has two flag-gated transformations.
- `docs/architecture/decisions/` — consider an ADR for "directory-as-package" treatment as a separate primitive from basename merge.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core collapse |
| AC-2 | required | Operator surface |
| AC-3 | required | Observability parity with `collapse_class_module_pairs` |
| AC-4 | required | Edge correctness |
| AC-5 | required | Safety on irregular packages |
| AC-6 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Separate feature from `collapse_class_module_pairs` | Conceptually distinct (directory grouping vs file-basename match); merging the implementations would over-couple them | Single unified collapse (rejected — conflates two different transformations) |

## Risks

| Risk | Mitigation |
|---|---|
| Large Go monorepos produce very few but very-large package nodes; readability could regress | Default off; document trade-off in `wave_graph_report` seed |
| `cmd/` directories with one `main.go` per binary (each its own package) collapse trivially | Single-file packages skipped by design |
| Build-tag-conditional files (`//go:build linux`) appear in multiple packages | Conservative: skip directories with conflicting package declarations |

## Related Work

- Sibling to `1312h-enh collapse-class-module-pairs` and the wave-13129 multi-language merge family. Closes the Go gap intentionally left in `1319i`.
- Sequencing note: this should land before any deep Go-receiver-resolution work to avoid double-rewrites of the same edges.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
