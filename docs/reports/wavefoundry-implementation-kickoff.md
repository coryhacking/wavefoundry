# Implementation Kickoff: Modularizing the Wavefoundry MCP Server

Status: Ready for maintainer execution
Audience: Wavefoundry maintainers
Companion: `wavefoundry-modularity-rfc.md` (the proposal this executes)
Upstream tip reviewed: v1.24.0+ppq7 (commit f8e4732, 2026-09-13)
Last updated: 2026-09-14

> This document turns the RFC into work the team can start on Monday. It is written for the
> maintainers: concrete slices, the files each touches, the interfaces to build, the tests that prove
> "no behavior change," and a definition of done per slice. Everything is framed as general
> open-source modularity; nothing here depends on any particular integrator. File and function names
> are anchors from the v1.24.0 tree — verify at the current tip, since the module is growing fast.

---

## 0. Ground rules for every slice

These constraints apply to all work below. They are what makes the refactor safe to land incrementally.

1. **Zero default-behavior change per slice.** Each slice ships behind the current behavior. The
   proof is a **golden snapshot of the public tool surface** (slice 0). If the snapshot changes
   without an intentional, reviewed update, the slice is wrong.
2. **Preserve hot reload.** Per-call state resolves through `get_handler()` today so `wf_mcp_reload`
   works. Any registry or pipeline must remain reload-safe: never cache a handler instance across
   reloads; resolve through the same indirection.
3. **Preserve middleware ordering.** The three post-registration wrappers —
   `_wrap_lifecycle_mutation_lock`, `_wrap_upgrade_publication_guard`, `_wrap_first_party_tool_costs`
   — encode an order (lock → guard → cost). When they become an explicit chain, that order is a tested
   invariant, not an accident of call sequence.
4. **`events.jsonl` stays the sole review-evidence authority.** Since v1.15 every gate reads typed
   ledger records through the facade in `review_evidence.py` (`read_review_event_ledger`). Any new
   gate or policy unit **must** consume that facade. No gate may re-parse prose or bypass the ledger.
5. **Names flow through the roster.** `mcp_tool_roster.py` is becoming the runtime source of truth
   (slice 1). Tool aliases and renames must flow through the roster *and* the self-healing host
   allowlist renderer (`.claude/settings.json` provenance-keyed merge, v1.15), or host permission
   rules silently break on rename.
6. **Anything auto-discovered from a repository is containment-checked and fail-closed.** See §2.
7. **Small PRs.** Each slice is one reviewable PR (or a short stack). No slice should touch
   `register_mcp_surface` *and* move handler bodies in the same change.

---

## 1. Implementation sequence (refined from RFC §6)

The RFC's landing order is kept, with one refinement: the **foundation layer moves before the
resolver SPI**, because the resolver and gate work both lean on `runtime_lock` and the containment
idiom that belong in the foundation. Techdocs (the reference subsystem) follows the gate pipeline so
it can demonstrate both a `TOOLS` list and a gate in one exemplar.

| Slice | Deliverable | RFC | Risk | Size |
|-------|-------------|-----|------|------|
| **0** | Golden snapshot of the tool surface + characterization tests | — | none | S |
| **1** | Declarative registry scaffold; roster promoted to runtime truth; explicit middleware chain | RFC-1a | low | M |
| **2** | `foundation/` package: `runtime_lock`, `index_state_store`, `gardener_metadata`, containment helpers | RFC-4a | low | M |
| **3** | `PathResolver` protocol + `FlatDocsResolver` default + convention auto-discovery | RFC-2 | med | M–L |
| **4** | `GatePipeline` + default gates extracted verbatim + convention auto-discovery | RFC-3 | med | L |
| **5** | Techdocs as the reference self-registering subsystem | RFC-4b | low | M |
| **6** | Handler module split — codenav and graph first | RFC-1b | med | L |
| **7** | Memory / context orchestration moved out of `server_impl.py` | RFC-4c | high | L |

Slices 0–2 are the safe, mechanical foundation and can start immediately. Slices 3–4 introduce the
two extension points. Slices 5–7 are the payoff and can be paced.

---

## 2. Security posture for convention-based auto-discovery (decide before slice 3)

The RFC asks for extension points that **auto-discover by convention** so a repository needs no
per-repo configuration. Auto-loading a module from repository content means the server executes
repository-supplied code. That is already true today for the upgrade path (`upgrade_extensions.py`
is loaded and its phase hooks run), so this is not a new class of behavior — but it deserves an
explicit posture. Three options, safest first:

**Option A — Convention + containment + fail-closed (recommended default).**
- Discovery only searches inside a **configured allowed root** (the server's existing boundary) and
  only at the fixed conventional paths (e.g. an `extensions/` directory under the root).
- Every candidate path passes the containment check before import — reuse the existing idiom
  (`_is_relative_to` in `indexer.py`, the `_contained_*` helpers in `memory_records.py` /
  `memory_backfill.py`) and refuse symlinks that escape the root, matching the symlink-containment
  check already used for skill rendering.
- **Fail-closed for gates, never-crash for the server:** a policy module that fails to import or
  raises inside a gate produces a blocking *diagnostic* for that phase; it never silently passes
  and never takes down the process. A resolver that fails to import falls back to
  `FlatDocsResolver` with a logged warning.
- **Provenance:** log and surface (in `wf_server_info` / `wf_audit`) which extension module was
  bound and from where, so an operator can always answer "what code is running my gates."
- Tradeoff: no explicit consent step. Acceptable because the trust boundary is the allowed root,
  which the operator already controls, and the upgrade path already accepts this.

**Option B — Option A + an explicit trust marker.**
- Same as A, plus require a small in-repo marker (e.g. a committed `extensions/TRUSTED` file or a
  hash manifest) before binding. Stricter, but it reintroduces a per-repo step the RFC is trying to
  remove. Reasonable if maintainers want an audit artifact; otherwise A suffices.

**Option C — Unrestricted import from any path (not recommended).**
- Simplest, but lets a repository outside the allowed root, or a symlink escape, run code in the
  server. Rejected.

**Proceed with Option A** unless maintainers prefer B. Either way, containment + fail-closed +
provenance are non-negotiable and must be covered by tests in slice 3/4.

---

## 3. Slice-by-slice work breakdown

### Slice 0 — Golden snapshot & characterization (start here)

**Goal.** Make "no behavior change" provable before touching anything.

**Work.**
- Add a test that boots the server registration and snapshots the **full public tool surface**:
  every tool name, its permission tier from the roster, and its input schema, serialized
  deterministically and committed as a golden file.
- Add a test asserting the **middleware order** (lock → guard → cost) by inspecting the wrapped
  callables, so slice 1 can prove it preserved the order.
- Extend the existing roster parity check (currently run at the end of `register_mcp_surface`) into
  a standalone test so it can run without booting the transport.

**Definition of done.** Golden file committed; parity and order tests green on the current tip;
CI fails on any unreviewed snapshot delta.

### Slice 1 — Declarative registry + explicit middleware chain (RFC-1a)

**Goal.** An enumerable runtime registry populated by the *existing* decorators. No handler moves.

**Work.**
- `server/registry.py`: a `ToolSpec` dataclass (`name`, `handler`, `permission_tier`,
  `annotations`, `aliases: list[str] = []`, `namespace_transform: Callable | None = None`) and a
  module-level registry the existing `@mcp.tool` sites append to via a thin wrapper decorator.
- Promote `mcp_tool_roster.py` from advisory parity check to **runtime source of truth**: the
  registry validates that every registered name and tier matches the roster at startup and fails
  fast on drift.
- `server/dispatch.py`: move the three `_wrap_*` monkey-patches into an explicit, ordered middleware
  list applied uniformly at registration. Keep `_ensure_no_extra_args` as the first stage.
- Wire `aliases` / `namespace_transform` so they are *reflected in the roster export* consumed by
  the allowlist renderer (ground rule 5). Ship the hook without using it — no aliases defined yet.

**Definition of done.** Slice-0 golden snapshot unchanged; middleware-order test green; roster
validation runs at startup; `wf_mcp_reload` still works (reload test).

### Slice 2 — `foundation/` package (RFC-4a)

**Goal.** Package the leaf substrates every later slice needs, with no logic change.

**Work.**
- Move `runtime_lock.py`, `index_state_store.py`, `gardener_metadata.py` under a `foundation/`
  package with re-export shims at the old import paths (so nothing breaks in the same PR).
- Add `foundation/containment.py`: consolidate the existing `_is_relative_to` / `_contained_*`
  helpers into one public, tested `contained_path(root, candidate) -> Path | None` (refuses
  escapes and escaping symlinks). This is the primitive §2 relies on.
- `index_paths.py` already follows the target style (import-light, one responsibility, "does not
  decide authority"); leave it in place and cite it in the package README as the pattern to copy.

**Definition of done.** All imports resolve via shims; test suite green; `containment.py` has
tests for `..` escape, absolute-path escape, and symlink escape.

### Slice 3 — `PathResolver` SPI with convention auto-discovery (RFC-2)

**Goal.** Route record/plan/archive path construction through a protocol; default reproduces
today's paths exactly.

**Work.**
- `foundation/paths.py` (or `server/paths.py`): the protocol from the RFC —
  `plans_root()`, `record_roots() -> (live, archive)`, `resolve_record(record_id)`,
  `scope_prefixes()`. Ship `FlatDocsResolver` implementing today's `docs/waves` / `docs/plans`
  behavior byte-for-byte.
- **Discovery engine (Option A):** at startup, inside the allowed root, check the conventional
  location(s) for a resolver module; if present and contained, import and bind it; otherwise bind
  `FlatDocsResolver`. Record which was bound (provenance).
- Route path construction through the bound resolver **incrementally**: start with the lifecycle
  handlers (create / add / remove / prepare / review / close), then inspection, then the rest. Each
  batch is its own commit; the golden snapshot and existing lifecycle tests guard each batch.
- Add a **conformance test suite** for `PathResolver` so any implementation (default or
  discovered) can self-verify: root invariants, deterministic ambiguity handling, scope-prefix
  behavior.

**Definition of done.** `FlatDocsResolver` passes conformance; default install produces identical
paths (golden + lifecycle tests); discovery binds a fixture resolver in a test root and falls back
correctly when the module is absent, uncontained, or broken; provenance is visible.

### Slice 4 — `GatePipeline` with convention auto-discovery (RFC-3)

**Goal.** Lifecycle gating becomes data + small units; current checks are extracted verbatim as
the defaults.

**Work.**
- `server/gates.py`: `Gate` protocol (`check(ctx: LifecycleCtx) -> list[Diagnostic]`) and
  `GATES: dict[phase, list[Gate]]` for `prepare` / `review` / `close`.
- Extract the existing prepare/review/close checks **1:1** into default gate units. No policy
  change. Each gate is a pure function of `ctx`; each gets a unit test.
- **Every gate reads evidence through `read_review_event_ledger` (ground rule 4).** Add a lint or
  test that no gate module imports anything that parses `wave.md` prose for sign-off.
- **Discovery engine (Option A):** bind a policy module found at the conventional path (e.g.
  `extensions/*_policy.py`) that exposes additional `Gate`s per phase; containment-checked;
  fail-closed (import/raise → blocking diagnostic for that phase, server keeps running);
  provenance surfaced.
- Mirror the shape of the accepted upgrade-time hooks in `upgrade_extensions.py`
  (`post_preflight`, `pre_extract`, `post_extract`, `pre_index_rebuild`, `pre/post_docs_gate`,
  `pre/post_index_update`): "named phase → optional `(ctx)` handler discovered by convention."
  Keeping the two hook systems consistent is a feature.
- Add a **conformance suite** for `Gate` implementations.

**Definition of done.** Default gate chain reproduces current diagnostics exactly on the existing
lifecycle test corpus; a fixture policy module is discovered, bound, and its gate runs; a broken
fixture policy fails closed without crashing; golden snapshot unchanged.

### Slice 5 — Techdocs as the reference subsystem (RFC-4b)

**Goal.** One fully decoupled subsystem that shows the target shape.

**Work.**
- `techdocs_audit_lib.py` already refuses to import `server_impl` and needs only
  `index_state_store`. Give it a `TOOLS: list[ToolSpec]` for `wf_techdocs_audit` and
  `wf_techdocs_baseline`, registered through the slice-1 registry, and remove the inline handlers
  from `server_impl.py`.
- Document it as the pattern: "a subsystem is a package + a `TOOLS` list (+ optional gates)."

**Definition of done.** Both tools still appear identically in the golden snapshot; the techdocs
handlers no longer live in `server_impl.py`.

### Slice 6 — Handler module split, codenav and graph first (RFC-1b)

**Goal.** Begin shrinking `server_impl.py` with the largest, most self-contained blocks.

**Work.**
- Move the code-navigation handlers (read / keyword / definition / references / callhierarchy /
  deps / impact) to `server/handlers/codenav.py` and the graph-query handlers to
  `server/handlers/graph.py`, each exposing `TOOLS`. They already delegate through module loaders
  (`_get_chunker_module()`, `_load_graph_query()`), so the seam is thin.
- Keep the thin MCP wrapper per tool in the registry; move only bodies.

**Definition of done.** Golden snapshot unchanged; `server_impl.py` line count drops measurably;
both handler modules unit-tested without the transport.

### Slice 7 — Memory / context orchestration out (RFC-4c)

**Goal.** The hardest extraction, last, on top of everything above.

**Work.**
- Move memory orchestration (the `memory_*` response builders and the ~400 inlined references)
  into the memory package with a `TOOLS` list; same for context-efficiency projection/persistence.
- Break the back-references: `memory_eval.py` and `memory_cli.py` currently import `server_impl`
  lazily — invert them to depend on the registry/foundation instead.

**Definition of done.** Memory and context tools unchanged in the golden snapshot; neither module
imports `server_impl`; `server_impl.py` is a composition root plus lifecycle, not an orchestrator.

---

## 4. Test strategy summary

| Guard | Proves | Introduced |
|-------|--------|-----------|
| Golden tool-surface snapshot | no unintended public change, every slice | 0 |
| Middleware-order test | lock → guard → cost preserved | 0 / 1 |
| Roster runtime validation | names/tiers can't drift from the roster | 1 |
| Reload test | registry is hot-reload safe | 1 |
| `containment.py` tests | `..`, absolute, and symlink escapes refused | 2 |
| `PathResolver` conformance | any resolver behaves; default is byte-identical | 3 |
| Discovery fixtures (present / absent / uncontained / broken) | auto-discovery binds correctly and fails closed | 3, 4 |
| `Gate` conformance + "no prose parsing" lint | gates use the ledger facade only | 4 |
| Lifecycle diagnostic parity | default gates reproduce current behavior exactly | 4 |

---

## 5. What the external integrator will contribute

To keep the team's load on core work, the integrator offers, on the team's timeline:

1. A **second `PathResolver` implementation** (nested, discovery-based, deterministic ambiguity
   resolution) as a PR against the slice-3 protocol — the proof that the SPI generalizes.
2. The **`PathResolver` and `Gate` conformance suites** (slices 3–4) as a PR, so they are not on
   the critical path.
3. A **prototype of the slice-1 registry scaffold** as a draft PR the team can adopt, adapt, or
   discard, to de-risk the approach before anyone moves a handler.
4. Ongoing **field feedback** on the `Gate` and discovery shapes from running additional policies.

---

## 6. Decisions for the maintainers

Please decide these before slice 3 starts; everything earlier is unaffected.

1. **Auto-discovery posture:** Option A (recommended) or Option B (add a trust marker)? — §2
2. **Conventional paths:** confirm the discovery locations (proposed: an `extensions/` directory
   under the allowed root; resolver and policy modules distinguished by suffix).
3. **Package layout:** `server/` + `foundation/` as proposed, or fold `foundation/` into the
   existing scripts tree with a namespace prefix? Either works; the shims in slice 2 make it
   reversible.
4. **Alias exposure:** should `aliases` appear in `wf_help` / the rendered allowlist immediately,
   or stay hidden until the first real rename uses them? (Recommended: reflect in the roster export
   now, expose in help later.)

---

## 7. Why this is worth it (one paragraph for the team)

`server_impl.py` grew ~2,760 lines in the ten days between v1.21.0 and v1.24.0 and now stands at
35,291 lines. Every one of those lines lands in a single file that every integrator must merge
around. The slices above do not slow that velocity — each is additive and behavior-preserving — but
they turn the monolith into a composition root with named seams, so new subsystems (like the recent
storage-engine consolidation) can be adopted wholesale by anyone downstream, and policy or layout
differences attach at an interface instead of in source. The project already trusts this pattern for
the upgrade path; this brings the same discipline to the runtime.
