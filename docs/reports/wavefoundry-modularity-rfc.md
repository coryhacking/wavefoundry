# RFC: Modularizing the Wavefoundry MCP Server for Third-Party Integration and Extensibility

Status: Draft — for maintainer review
Audience: Wavefoundry maintainers
Framing: open-source modularity, clean architecture, and extension points
Upstream tip reviewed: v1.24.0+ppq7 (commit f8e4732, 2026-09-13)
Last updated: 2026-09-14

> This document is written from the perspective of an external integrator who runs Wavefoundry
> in an environment with somewhat different storage conventions, domain vocabulary, and governance
> policies. Everything below is proposed as a general improvement to modularity and extensibility
> that benefits **any** integrator — and the core project's own testability — rather than a
> request tailored to one consumer. Line numbers and file names cited are from the Wavefoundry
> tree as observed at v1.24.0+ppq7 (commit f8e4732); they are offered as concrete anchors, not criticism.

---

## 1. Summary

Wavefoundry's MCP server has matured into a powerful, feature-dense product. As a natural
consequence of that velocity, the server implementation (`server_impl.py`) has become a single
module of **35,291 lines** (v1.24.0, ~1.6 MB) — up ~2,760 lines in the ten days from v1.21.0 to
v1.24.0 alone — that concentrates tool registration, dispatch, search/index, lifecycle state
machines, gating/policy, and several independently valuable subsystems (memory, context-efficiency,
techdocs) in one place. The module is not only large; it is still accelerating, which sharpens the
case for RFC-1.

This is entirely reasonable for a single first-party distribution. It becomes friction, however,
for anyone who integrates Wavefoundry into an environment that differs from the defaults — a
different document layout, a different domain vocabulary, or additional policy requirements. Today
those integrators have only one option: patch core files in place. That makes every upstream
release a merge-conflict event and discourages integrators from staying current, which is bad for
the ecosystem and for upstream (integrators fork and drift instead of contributing back).

This RFC proposes four incremental, individually-shippable refactors that introduce **named
extension points** so integrators attach *alongside* core instead of editing it:

- **RFC-1** — Decompose `server_impl.py` into a `server/` package with a **declarative tool
  registry** and an explicit dispatch/wrapper chain.
- **RFC-2** — Introduce a **`PathResolver` / `StorageProvider` SPI** so document/record locations
  are pluggable, defaulting to today's flat layout.
- **RFC-3** — Replace inlined lifecycle gating with a **pluggable gate/policy pipeline**
  (chain-of-responsibility) so custom checks **auto-discover by convention (zero per-repo config)**.
- **RFC-4** — Package the independent subsystems (and a small shared base layer) as **self-registering
  modules** so a subsystem can be added or removed without editing the monolith.

None of these require a big-bang rewrite. Each can land behind current behavior with defaults that
preserve the existing distribution byte-for-byte in its behavior, and each is independently
test-coverable. The external integrator is willing to contribute reference implementations and PRs
(see §7).

---

## 2. Motivation

A modular MCP server is better for everyone, independent of any single integrator:

1. **Testability.** A 32k-line module is hard to unit-test in isolation. Domain-scoped handler
   modules with a declarative registry can be tested without booting the full transport.
2. **Reviewability.** Feature PRs that today touch the mega-function `register_mcp_surface` create
   large, hard-to-review diffs and frequent conflicts between concurrent workstreams.
3. **Extensibility.** Integrators with different storage layouts, domain vocabularies, or policy
   requirements can attach at named seams instead of forking core. This keeps them current and
   able to contribute upstream.
4. **Subsystem portability.** Several subsystems are already conceptually independent; making that
   explicit lets the core team (and integrators) enable/disable them cleanly and evolve them
   on their own cadence.

The guiding principle: **core ships opinionated defaults; integrators override at interfaces, not
in source.**

---

## 3. Current architecture (as observed)

These observations are factual anchors for the proposals; they reflect strong, deliberate design
that simply optimized for a single distribution.

- **Single-module server.** `server_impl.py` is **35,291 lines** at v1.24.0 — up from ~32,531 at
  v1.21.0, roughly +2,760 lines in ten days. Tool registration happens inside one function,
  `register_mcp_surface(mcp, get_handler)`, spanning ~4,100 lines and containing ~198 `@mcp.tool`
  decorated nested handlers.
- **No enumerable dispatch table.** Tools are bound by decorator; per-call state is resolved via
  `get_handler()` to support hot reload. There is no first-class list of tool specs at runtime and
  no if/elif dispatch — cross-cutting behavior is applied as post-registration monkey-patch
  wrappers (`_wrap_lifecycle_mutation_lock`, `_wrap_upgrade_publication_guard`,
  `_wrap_first_party_tool_costs`).
- **A roster already exists but is advisory.** `mcp_tool_roster.py` is described as the canonical
  roster ("every first-party tool name plus a permission tier") and is consumed by surface
  rendering and a parity check. It is an excellent foundation for RFC-1 — it just isn't yet the
  runtime source of truth.
- **Path/storage assumptions are inlined.** The flat `docs/waves` / `docs/plans` layout appears as
  inline string joins in a few hundred call sites. `repo_root.py` performs root *discovery*
  (anchored on `docs/workflow-config.json`) but there is no record-path *resolution* abstraction.
- **The index storage engine was just consolidated (v1.22–1.24).** LanceDB has been retired in favor
  of a unified SQLite store (`index.sqlite`), with a dedicated `index_paths.py` for storage-path
  resolution and a resumable migration. This is exactly the kind of fast-moving, high-churn subsystem
  an integrator must be able to adopt *wholesale*: it is strong evidence for keeping storage-engine
  concerns behind clean module boundaries (RFC-4's `foundation` layer) so a downstream never has to
  fork the engine to stay current.
- **Gating is interleaved with lifecycle.** Prepare/review/close enforcement logic lives inside the
  handler bodies rather than in a separable policy component.
- **Independent subsystems keep orchestration in the monolith.** Memory (~2,000 lines of
  orchestration inlined, ~437 `memory_*` references), context-efficiency (~1,556 lines), and
  techdocs (~460 lines) register and orchestrate from within `server_impl.py`, even though several
  of their support modules are already clean (e.g. `techdocs_audit_lib.py:23` explicitly documents
  that it never imports `server_impl`).

A useful signal for prioritization: subsystems reached through the dynamic `_load_script(...)`
loader (`_load_script` in `server_impl.py`) are already loosely coupled and easy to relocate; subsystems bound
by top-level static imports are more entangled.

---

## 4. Proposals

### RFC-1 — `server/` package with a declarative tool registry

**Problem.** All tools register inside one function via decorators, with cross-cutting behavior
bolted on afterward. There is no enumerable registry and no seam to add, replace, alias, or
deprecate a tool without editing the mega-function.

**Proposal.** Split `server_impl.py` into a package:

```
server/
  registry.py        # ToolSpec dataclass + decorator that appends to a module-level registry
  dispatch.py        # kwargs validation, envelope building, wrapper chain (lock / guard / cost)
  transport/         # stdio / SSE protocol handling
  handlers/
    search.py        # docs_search, code_search, code_ask
    codenav.py       # read / keyword / definition / references / callhierarchy / deps / impact
    graph.py         # impact / callgraph / report / path / community
    lifecycle.py     # create / add / remove / prepare / review / close
    memory.py techdocs.py context.py   # optional subsystems, self-registering (see RFC-4)
```

- **Declarative registration.** Each handler module exposes `TOOLS: list[ToolSpec]`; the server
  composes the registry from the modules it loads. Promote `mcp_tool_roster.py` from an advisory
  parity check to the **runtime source of truth** for names and permission tiers.
- **Explicit wrapper chain.** Move the three post-registration wrappers into `dispatch.py` as an
  ordered, testable middleware chain rather than monkey-patches applied after the fact.
- **Name/namespace mapping hook.** Give `ToolSpec` optional `aliases: list[str]` and an optional
  `namespace_transform` callable. This is a general OSS capability — versioned tool aliases and
  clean deprecations — that additionally lets an integrator expose a handler under a different
  public name or prefix **without touching handler code**. (Wavefoundry already has one recorded
  tool rename with a `removed_in` semver; this generalizes that pattern into a first-class feature.)

**Incremental path.** The registry can be introduced by having the existing decorators append to it;
behavior is unchanged until the core team chooses to split handlers into modules. Codenav and graph
handlers are the natural first extraction — they are the largest, most self-contained blocks and
delegate through existing module loaders.

### RFC-2 — `PathResolver` / `StorageProvider` SPI

**Problem.** Record/plan/archive paths are inlined as `docs/waves` / `docs/plans` joins in a few
hundred sites. Any integrator whose repository organizes documents differently must patch every
one of those sites and re-patch after each release.

**Proposal.** Extract a small protocol and route all path construction through it:

```python
class PathResolver(Protocol):
    def plans_root(self) -> Path: ...
    def record_roots(self) -> tuple[Path, Path]:      # (live, archive)
    def resolve_record(self, record_id: str) -> Path: ...
    def scope_prefixes(self) -> list[str]: ...         # for startswith() scope checks
```

- Ship a default `FlatDocsResolver` that reproduces today's behavior exactly.
- **Bind by convention, not per-repo config (zero-config auto-discovery).** The resolver is selected
  by inspecting the environment, not by a `docs/workflow-config.json` switch each repository must set:
  if a non-flat records layout (e.g. a `docs/features/` tree) or a resolver module is present on a
  conventional path, the discovery engine auto-binds it; otherwise it falls back to `FlatDocsResolver`.
  An integrator drops in a module and it takes effect with no configuration edit, and the default
  distribution needs no config at all. (Convention over configuration keeps the extension invisible to
  repositories that don't use it.)
- Keep resolution **discovery-tolerant**: allow a resolver to locate records by scanning rather than
  by direct join, and to disambiguate deterministically. This makes non-flat and nested layouts
  possible without changing any handler.

**Contribution offer.** The external integrator maintains a production resolver for a **nested,
discovery-based layout with deterministic ambiguity resolution** and is willing to contribute it as
a second reference implementation. Two implementations against one interface is the best evidence
that the SPI is sufficient and not accidentally shaped to the default.

### RFC-3 — Pluggable gate/policy pipeline

**Problem.** Lifecycle gating (prepare/review/close) is enforced by checks interleaved directly into
handler control flow. Adding or varying a policy (extra sign-off requirements, an external-tracker
precondition, a stricter close gate) requires editing core lifecycle code.

**Proposal.** A chain-of-responsibility pipeline:

```python
class Gate(Protocol):
    def check(self, ctx: LifecycleCtx) -> list[Diagnostic]: ...

GATES: dict[str, list[Gate]] = {
    "prepare": [ ...core defaults... ],
    "review":  [ ...core defaults... ],
    "close":   [ ...core defaults... ],
}
```

- Core ships its default gates (the current checks, extracted verbatim).
- **Additional gates auto-discover by convention (zero per-repo config).** Rather than a
  `docs/workflow-config.json` entry each repository must maintain, the pipeline binds any policy
  module found on a conventional path (e.g. an `extensions/*_policy.py` module); absent one, only the
  core defaults run. Dropping in a policy module is the entire integration step — nothing to configure.
- Wavefoundry's own council/authority checks become the first citizens of this pipeline, which
  improves upstream testability (each gate is a pure, independently-testable unit) regardless of any
  integrator.

**Precedent — you have already shipped and accepted this exact pattern.** `upgrade_extensions.py`
defines a lifecycle-phase hook system for the *upgrade* path: named, optional `def <hook>(ctx)`
functions the runner calls if present — `post_preflight`, `pre_extract`, `post_extract`,
`pre_index_rebuild`, `pre_docs_gate` / `post_docs_gate`, and `pre_index_update` / `post_index_update`.
RFC-3's `GatePipeline` is simply the **runtime counterpart** to that already-proven system: the same
"named phase → optional `(ctx)` handler discovered by convention" contract, applied to the
prepare/review/close lifecycle instead of the upgrade lifecycle. Adopting it extends a design the
project already trusts rather than introducing a new paradigm — and using the same auto-discovery
convention keeps the two hook systems consistent.

This directly reduces the size and conflict-surface of the lifecycle handlers and turns "policy" into
data + small units instead of inlined branches.

### RFC-4 — Subsystem packaging + a shared base layer

**Problem.** The independent subsystems keep their orchestration inside `server_impl.py`, so the
apparent independence of their support modules understates the true cost of enabling/disabling them.
Three substrate modules recur across subsystems and would need to travel with almost any extraction:
`index_state_store`, `review_evidence`, and `runtime_lock`.

**Proposal (ordered by tractability, easiest first):**

1. **Extract a `foundation` base layer first** — `runtime_lock` (pure stdlib), `index_state_store`
   (self-contained git/state substrate), `gardener_metadata`. This unblocks everything above it.
2. **Package techdocs as the reference decoupled subsystem** — it already refuses to import
   `server_impl` and needs only `index_state_store`; it becomes two thin `TOOLS` entries plus a
   module.
3. **Move memory/context orchestration out of `server_impl.py`** into their own modules, leaving only
   a `TOOLS` list behind. Memory is the hardest (orchestration and ~437 references are currently
   inlined), so it is scheduled last.

Result: a subsystem is enabled or disabled by adding/removing a package and its `TOOLS` list — zero
edits to the monolith, and each subsystem evolves on its own cadence.

---

## 5. Cross-cutting: a note on naming and vocabulary

Integrators sometimes present the same lifecycle under different domain nouns. The cleanest way to
support this **without** vocabulary leaking into core is the RFC-1 alias/namespace hook plus a
data-driven public-name map, rather than hardcoded names throughout handlers. Core keeps its
canonical internal identifiers; the public surface is a projection. This also cleanly supports the
core team's own deprecations and renames over time (the existing `removed_in` mechanism generalizes
to exactly this).

---

## 6. Incremental adoption & backward compatibility

Every proposal is designed to land **without changing default behavior**:

- RFC-1: registry is populated by existing decorators first; module split is opt-in and staged.
- RFC-2: `FlatDocsResolver` is the default and reproduces current paths exactly.
- RFC-3: default gate chain is the current checks, extracted 1:1; no new policy is required.
- RFC-4: subsystems remain enabled by default; packaging changes wiring, not features.

Suggested landing order: **RFC-1 registry scaffold → RFC-4 foundation layer → RFC-2 resolver SPI →
RFC-3 gate pipeline → RFC-4 techdocs (reference subsystem) → RFC-1 handler split → RFC-4 remaining
subsystems.** The foundation layer lands before the resolver because the resolver and gate work both
lean on `runtime_lock` and a shared path-containment primitive that belong there. Each step is
shippable and test-covered on its own; the companion *Implementation Kickoff* document breaks these
into slices with tests and a definition of done.

---

## 7. What the external integrator can contribute

To make this concrete rather than a wish list, the integrator offers to:

1. Contribute a **second `PathResolver` reference implementation** (nested, discovery-based) once the
   SPI shape is agreed (RFC-2).
2. Contribute a **conformance test suite** for the `PathResolver` and `Gate` protocols, so third-party
   implementations can self-verify.
3. Prototype the **registry scaffold** (RFC-1) as a non-breaking change that populates from existing
   decorators, to de-risk the approach before any handler is moved.
4. Provide **real-world feedback** on the `Gate` pipeline shape from running additional lifecycle
   policies in production.

---

## 8. Appendix — observed coupling signals (Wavefoundry v1.24.0+ppq7)

| Area | Observation | Anchor |
|------|-------------|--------|
| Server module size | **35,291 lines** (v1.24.0; +2,760 vs v1.21.0 in ten days) | `server_impl.py` |
| Registration function | ~4,100 lines, ~198 decorated handlers | `register_mcp_surface` |
| Cross-cutting wrappers | applied as post-registration monkey-patches | `_wrap_lifecycle_mutation_lock`, `_wrap_upgrade_publication_guard`, `_wrap_first_party_tool_costs` |
| Tool roster | canonical list exists but is advisory | `mcp_tool_roster.py` |
| Root discovery vs path resolution | discovery exists; record-path resolution inlined | `repo_root.py` |
| Index storage engine | LanceDB retired → unified SQLite (v1.22–1.24) | `index.sqlite`, `index_paths.py`, `sqlite_vector_store.py` |
| Lifecycle-hook precedent | named phase hooks already shipped for the upgrade path | `upgrade_extensions.py` (`post_preflight`, `pre_extract`, `post_extract`, `pre_index_rebuild`, …) |
| Loosest subsystem seam | dynamic module loader | `_load_script` |
| Cleanest subsystem | refuses to import the server module | `techdocs_audit_lib.py` |
| Recurring substrates | travel with most extractions | `index_state_store`, `review_evidence`, `runtime_lock` |

*Line numbers are approximate and provided as navigation aids for the current tip; they will drift
as the code evolves.*
