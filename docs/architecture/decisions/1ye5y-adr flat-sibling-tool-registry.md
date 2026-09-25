# 1ye5y-adr — Flat Sibling Module For The Tool Registry

Owner: Engineering
Status: superseded
Last verified: 2026-09-25
Superseded by: [1yx4m-adr](1yx4m-adr%20wf-server-package.md) (placement only; the registry, the chain and the constraints on registration-time wrappers stand)

## Context

The MCP server registers its tools with FastMCP decorators inside `server_impl.register_mcp_surface`, then applies three post-registration wrappers: cost recording, the lifecycle mutation lock, and the upgrade-publication guard. Before wave `1y0h1` the order came from three direct calls; it was stated in a code comment and in `docs/contributing/build-and-verification.md`, and pinned by the `1y0do` wrapper-order test. Parity with the permission roster was checked by the AST census, the `1y0do` runtime parity test and an inline startup warning. What was missing was a runtime object that enumerates the surface and a single declared chain. Wave `1y0h1` adds an enumerable runtime registry of tool specifications and one explicit, ordered wrapper chain.

The Waveforge modularity RFC proposed a `server/` package for this. Two existing mechanisms constrain the choice: hot reload (`wf_reload_mcp`) clears `_script_cache` and purges a named list of sibling modules before re-importing `server_impl`, and `build_pack.py` walks the scripts directory to build the distribution.

## Decision

The registry and a generic chain applier live in a flat sibling module, `mcp_tool_registry.py`. It is stateless, imports nothing from `server_impl` at any scope, is on the reload purge list, and is imported by public name at the top of `server_impl`. The registry is built by reading FastMCP's own tool table after registration and cross-referencing `mcp_tool_roster`; no registration site changes. The chain, `MIDDLEWARE`, is declared in `server_impl.py` beside the three wrappers, which remain the only place a tool's callable is rebound. No aliases or public-name mapping are introduced.

## Consequences

**Positive:**
- Reload and packaging work unchanged: the module is one more purge entry and one more file in the walked directory.
- The wrapper order is an inspectable invariant. Each wrapped callable carries `__wf_middleware__` naming the wrappers that applied to it, and the declared tuple is testable.
- Permission tiers keep one source, `mcp_tool_roster`; the registry reads it rather than copying it.

**Negative / tradeoffs:**
- The registry reads FastMCP's private `_tool_manager._tools` attribute. The golden-snapshot and reload tests already read the same attribute, so a dependency bump that reshapes it fails visibly.
- Flat modules keep accumulating beside `server_impl`; the package question is deferred, not settled.

**Constraints imposed:**
- A registration-time wrapper stays in `server_impl.py` and is reached by name through `MIDDLEWARE`, so a module-level rebinding takes effect when the chain runs, and the published `configured_gates` provenance rule, which derives the key-less refusals from functions that rebind `tool.fn`, stays true.
- A sibling module on the purge list is imported by public name at module top. `test_reload_picks_up_every_added_module` looks each purge entry up by public name in `sys.modules` after reload, so a module loaded through `_load_script`, which caches it under a private key, fails that test, and a lazy import is proven fresh only when it happens to run during re-registration. A module-boundary test in `test_mcp_tool_registry` pins both the placement and the purge entry.
- Revisit the package question if flat modules adjacent to the MCP surface exceed roughly 15 to 20, or if two of them develop an import dependency on each other.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| A `server/` package, as the RFC proposed | Reload purge and `_load_script` caching semantics for a package are unproven here, and packaging would need its own change |
| Converting all registration sites to a decorator factory that records each spec | Rejected by the operator on 2026-09-16: a large mechanical diff with per-site transcription risk, for a per-site alias hook this change defers |
| Aliases or a namespace transform | No current consumer; every seed, prompt and host allowlist uses canonical names |

## References

- `docs/waves/1y0h1 tool-registry-dispatch/1y0be-ref tool-registry-and-wrapper-chain.md`
- `docs/reports/wavefoundry-modularity-rfc.md`
- `docs/reports/waveforge-fork-audit.md`


## First handler exemplar (wave 1y0h2)

Code navigation and graph response computation move into flat reloadable siblings while decorated closures remain in `server_impl.py`. The registry remains observational and reports those closure source modules unchanged. The response modules import the composition root only inside functions to resolve retained dependencies at invocation time; the root rebinds public response names for existing callers. Independent import-derived reload tests cover the siblings in addition to runtime registry parity.

## Distribution extension tools (wave 1yv9l)

A downstream distribution adds or explicitly overrides tools on the one server through a stdlib-only flat sibling, `mcp_tool_extensions.py`, whose declarations it edits at merge time; the contract is in `docs/specs/mcp-tool-surface.md` (**Distribution Extension Tools**). This section records how that hook relates to the constraints above.

- **Import-rule exception.** Purge-list siblings are imported by public name at module top. `mcp_tool_extensions` follows that rule and is on the purge list. The modules it declares are the exception: `server_impl` executes each one during registration, under its declared public name, from the exact bytes it hashes, and re-executes it on every reload. They are not imported at module top because the server does not know them until the declaration is read.
- **First sibling import dependency.** `mcp_tool_roster` imports `mcp_tool_extensions` so the renderer and upgrade validate and include declared tiers without starting the server. This is the first import dependency between flat siblings, one of this ADR's revisit triggers. It is a one-way, stdlib-only data dependency and does not by itself justify a package.
- **Package question.** Declined for this hook. Extension modules sit beside the other flat modules and count toward the 15 to 20 module revisit trigger, which stays in force. `_load_script` resolves siblings by flat filename and the upgrade path reads framework scripts by flat path from the archive, so a package would rewrite both for an organizational gain.
- **Aliases and namespace transforms.** Still declined, for a new reason: a fork is now a consumer, but declared overrides keep canonical names, so prompts, seeds, allowlists and server guidance keep working without an alias surface. Tool names are also embedded in many server responses (`next_tools`, recovery guidance), which a rename would leave pointing at names that no longer exist.
