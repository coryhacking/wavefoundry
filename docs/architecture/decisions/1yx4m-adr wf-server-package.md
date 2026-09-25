# 1yx4m-adr — The MCP Server Implementation Lives In The `wf_server` Package

Owner: Engineering
Status: accepted
Last verified: 2026-09-25

## Context

ADR [1ye5y](1ye5y-adr%20flat-sibling-tool-registry.md) put the tool registry in a flat sibling module and deferred the package question until the flat modules beside the MCP surface passed roughly 15 to 20. By wave `1yzd0` the server owned a composition root, a registry and ten handler modules, all flat in the framework's global scripts namespace next to about a hundred unrelated scripts, CLIs and shared substrates. That namespace is global in a literal sense: the scripts root is put on `sys.path`, so every module there is a top-level import name inside the MCP process, beside every installed package and any module a distribution's extension declares.

Three constraints shaped the answer:

- **Hot reload.** `wf_reload_mcp` reloads `server_impl` in place after its module-top purge evicts the handler and substrate modules. The package must reload the same way, from the same unchanged runner.
- **Older upgrade runners.** An installed 1.25 or 1.26 runner validates each new pack with `upgrade_protocol._pack_module_names` and `_validate_imports`. Both count only flat modules and walk function-local imports too, and neither is changed by this wave: a mandatory upgrade module may never spell a package import, and the flat `server_impl` and `dashboard_handlers` files must stay importable.
- **Downstream code.** Distributions and tests import these modules by their flat names and patch private names on them; the extension contract lets extension modules use `server_impl` underscore helpers.

## Decision

> **Narrowed by the 2026-09-25 amendment (wave `1yxyw`) below.** Only `server_impl` and `dashboard_handlers` keep a flat alias; the other ten are reached as `wf_server.<name>`. The clauses marked *(narrowed)* read as amended.

Twelve modules move into `.wavefoundry/framework/scripts/wf_server/`: `server_impl`, `mcp_tool_registry`, and the ten `*_handlers` modules. Each keeps a flat file whose whole body is *(narrowed: the two retained modules only)*:

```python
import importlib
import sys

sys.modules[__name__] = importlib.import_module("wf_server.<name>")
```

Everything else stays flat, including the distribution-edited declarations (`mcp_tool_extensions.py`, `mcp_tool_roster.py`, `record_paths.py`) and `server.py`, the executable entry point.

- **One module object per implementation.** Importing a flat name returns the package module itself, so private names, `patch.object` on flat names, and the runner's attribute writes all reach the implementation.
- **Canonical imports inside the package.** Handlers import `from wf_server import server_impl` per call. `server_impl` imports handlers with `from wf_server.<module> import (...)` and the registry with `import wf_server.mcp_tool_registry as mcp_tool_registry`. The `from wf_server import <module>` form is not used for any module the purge evicts: it reads the attribute left on the never-evicted parent package and so keeps the stale module after a reload.
- **One alias table** *(narrowed)*. `_FLAT_ALIASES` in `wf_server/server_impl.py` names the moved modules. It is the single source for the eager aliases and for both reload purge key sets. `server_impl` registers the flat aliases after its last module-top import, only when it is loaded under its canonical name, so a private-name spec load never rebinds them.
- **Dual-key purge** *(narrowed: the retired names are purged through `_RETIRED_FLAT_NAMES`)*. The module-top purge evicts the flat and the `wf_server.<module>` key of every moved module except `server_impl`, and never evicts `wf_server` or `wf_server.server_impl`; evicting either makes the in-place reload raise `ImportError`.
- **Scripts root.** `server_impl.SCRIPTS_DIR` is the scripts root, one level above the package, and every lookup of a retained script goes through it. The package directory is never put on `sys.path`, which would import the handlers a second time under top-level names. `_audit_harness_coherence` is the one carve-out: it reads `server.py` from the scripts root and its own source from its package file.
- **The name.** The package is `wf_server`, chosen by the operator. `server` would shadow `server.py` for every `import server`; the scripts root is on `sys.path`, so the name is a top-level import and keeps the project prefix. `wf_server` and the twelve moved module names are reserved extension module names, so the static declaration check refuses them without MCP.

The flat names are the permanent public import surface *(narrowed: `server_impl` and `dashboard_handlers` only)*. Package names are internal, and every consumer outside the package, including every upgrade-mandatory module, keeps the flat spelling *(narrowed: upgrade-mandatory modules keep the two flat names; other consumers name the ten retired modules as `wf_server.<name>`)*.

This supersedes the "flat reloadable siblings" wording of wave `1y0h2` and the flat placement of ADR 1ye5y. The rows 1ye5y declined as "aliases" concern MCP tool-name aliases and are unaffected.

## Consequences

**Positive:**
- The server's modules have an explicit ownership boundary, and a new server module has an obvious home.
- Installed 1.25 and 1.26 runners accept and apply the new pack unchanged; the matrix is recorded in wave `1yzd0` evidence.
- *(Narrowed: for the two retained names only.)* Code that imports or patches the flat names keeps working, because the flat name is the same module object.

**Negative / tradeoffs:**
- *(Narrowed: the two retained modules only.)* Two spellings of each moved module exist. A test that reads a moved module's source by its flat path reads the three-line alias; `test_server_package` refuses such reads and flat `glob("*.py")` enumerations outside `tests/framework_files.py`.
- *(Narrowed: the two retained aliases only.)* The alias files cannot be removed yet (see the constraints below).
- Handlers still reach the composition root at invocation time; the package is a namespace boundary, not a decoupling.
- `setup_readiness.SOURCE_FILES` covers `wf_server/server_impl.py`, not the handler modules. Handler edits are served by `wf_reload_mcp` without a stale-code restart, as before; widening that scope would be its own decision.

**Constraints imposed:**
- *(Narrowed: the two retained aliases.)* A flat alias file holds exactly the three statements above. A structure test pins the bytes in this repository, and in every install the package refuses at import (`ImportError` naming the file) when a flat file is not the exact alias, compared with newlines normalized, so a merge that restores a full flat copy fails loudly instead of running a second implementation that breaks `wf_reload_mcp`. Fork edits go to `wf_server/<name>.py`, never over the alias.
- `wf_server/__init__.py` is empty and imports nothing. Editing it needs a full restart, because the parent package is never reloaded.
- **Alias-removal precondition** *(narrowed: the two retained aliases)*: the aliases stay until an upgrade-protocol change teaches pack validation to count package modules, and the minimum supported upgrade-from version is at or above that change.
- A distribution that ships its own top-level module named `wf_server` is shadowed by the package.

## Amendment (wave 1yxyw, 2026-09-25)

The ten optional aliases are retired before any release carries them: wave `1yxyw` ships in the same release as `1yzd0`, so forks migrate once, from full flat modules to package names.

- **Retained.** `server_impl` and `dashboard_handlers` keep their three-line aliases and the refusal of a non-exact alias. The alias-removal precondition above still governs them: installed 1.25 and 1.26 runners resolve every import of the upgrade-mandatory modules against flat stems, and those modules import these two. It never applied to the other ten, which no mandatory module imports.
- **Retired.** `mcp_tool_registry` and nine handler modules have no flat file. Every importer outside the package uses `import wf_server.<name> as <name>`, `from wf_server.<name> import ...`, `importlib.import_module("wf_server.<name>")` and `patch("wf_server.<name>.<attr>")`. `from wf_server import <name>` is refused outside the package for any module the purge evicts. A census in `test_server_package` enforces both.
- **Tables.** `_FLAT_ALIASES` names the two; `_RETIRED_FLAT_NAMES` names the ten. The purge evicts the flat and package keys of both sets except `server_impl`, so a stale flat module object an older host still holds is evicted on reload. `mcp_tool_extensions.RESERVED_MODULE_NAMES` keeps all twelve names and `wf_server`. `upgrade_extensions.RETIRED_FLAT_SERVER_MODULES` is a pinned copy, because an upgrade-mandatory module cannot import `wf_server`.
- **Leftovers.** The upgrade's MANIFEST-diff prune is the only deletion of the ten. A file that remains means the prune did not run or could not be proven (no saved old MANIFEST). It is reported, never refused and never deleted by other means: the upgrade's `post_pruning` hook prints a warning to delete it, and the server lists it as a `retired_flat_module_leftover` diagnostic in `wf_server_info` and on stderr. A leftover stays until deleted by hand, since the next upgrade's old MANIFEST no longer lists it, and meanwhile an unmigrated `import <name>` binds to the stale copy instead of failing.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| (b) Flat stubs that `from wf_server.<name> import *` | Loses private names, runner attribute writes and patching through the flat name; the demonstrated reload raises `AttributeError` |
| (b2) Star stubs plus a module `__getattr__` forwarding to the package | Still two live module objects per implementation, and the stub cannot refresh on reload |
| (c) A meta-path finder that maps flat names to package modules | Overwrites `__spec__`, making reload a silent no-op, and is unreachable for older runners and plain CLIs that do not install the finder |
| A `server/` package | Shadows `server.py` for every `import server` in production and tests |
| `mcp_server` | A generic top-level name more likely to collide, and `mcp_server.mcp_tool_registry` stutters |
| Keep the modules flat | The flat namespace kept growing; ADR 1ye5y's revisit threshold was reached |

## References

- [ADR 1ye5y — Flat sibling module for the tool registry](1ye5y-adr%20flat-sibling-tool-registry.md)
- Wave `1yxyw` change `1yxwn-ref retire-optional-flat-server-aliases`: the amendment, upgrade matrix and reload evidence
- Wave `1yzd0` change `1yxql-ref server-package-boundary`: readiness inventory, alias/reload demonstration, old-runner matrix, move-equivalence evidence
- `.wavefoundry/framework/scripts/tests/test_server_package.py`
