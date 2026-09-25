"""Probe one scenario in a FRESH interpreter; prints one JSON line of observations.

argv: <scripts_dir> <scenario> <strategy> [purge] [handler_import]
Every observation is computed, never assumed; exceptions are recorded as values.
"""
from __future__ import annotations

import gc
import importlib
import inspect
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

scripts = Path(sys.argv[1]).resolve()
scenario = sys.argv[2]
strategy = sys.argv[3]
purge = sys.argv[4] if len(sys.argv) > 4 else "both"
handler_import = sys.argv[5] if len(sys.argv) > 5 else "wavefoundry_server.graph_handlers"
sys.path.insert(0, str(scripts))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_tree  # noqa: E402

obs: dict = {"scenario": scenario, "strategy": strategy, "purge": purge, "python": sys.version.split()[0]}


def rec(name, fn):
    try:
        obs[name] = fn()
    except Exception as exc:  # noqa: BLE001
        obs[name] = f"ERROR {type(exc).__name__}: {exc}"


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(scripts))
    except Exception:
        return str(p)


def live_handler_modules():
    """Every live module object (gc) whose code came from a graph_handlers.py file."""
    found = []
    for o in gc.get_objects():
        if isinstance(o, types.ModuleType) and str(getattr(o, "__file__", "") or "").endswith("graph_handlers.py"):
            found.append(f"{o.__name__}@{rel(o.__file__)}#v={getattr(o, 'HANDLER_VERSION', None)}")
    return sorted(found)


def modules_by_key():
    keys = ("server_impl", "wavefoundry_server.server_impl", "graph_handlers", "wavefoundry_server.graph_handlers")
    return {k: (None if sys.modules.get(k) is None else f"id{id(sys.modules[k]) % 100000}:{sys.modules[k].__name__}@{rel(getattr(sys.modules[k], '__file__', '?'))}") for k in keys}


def common_static(runner):
    flat_impl = runner.server_impl
    pkg_impl = sys.modules.get("wavefoundry_server.server_impl")
    rec("flat_server_impl_is_package_module", lambda: sys.modules["server_impl"] is pkg_impl)
    rec("runner_ref_is_package_module", lambda: flat_impl is pkg_impl)
    import graph_handlers as flat_gh  # noqa: E402
    pkg_gh = sys.modules.get("wavefoundry_server.graph_handlers")
    rec("flat_graph_handlers_is_package_module", lambda: flat_gh is pkg_gh)
    rec("private_names_via_flat", lambda: {n: hasattr(flat_impl, n) for n in ("_load_script", "_script_cache", "_CACHE", "_runner_version", "_SETUP_LOADED_IDENTITY")})
    def mutable_shared():
        flat_impl._CACHE["k"] = 1
        return pkg_impl._CACHE.get("k") == 1
    rec("mutable_global_shared", mutable_shared)
    def rebinding():
        pkg_impl.set_runner_version("rebound-in-package")
        return getattr(flat_impl, "_runner_version", "<missing>")
    rec("flat_sees_package_global_rebind", rebinding)
    rec("package_sees_runner_attribute_write(read_identity)", lambda: pkg_impl.read_identity())
    def patch_flat_handler():
        with patch.object(flat_gh, "helper", lambda: "PATCHED"):
            return pkg_impl.respond()["helper"]
    rec("patch_object_on_flat_handler_affects_package_call", patch_flat_handler)
    def patch_flat_impl():
        with patch.object(flat_impl, "shared_helper", lambda: "PATCHED"):
            return pkg_impl.respond()["shared"]
    rec("patch_object_on_flat_server_impl_affects_handler", patch_flat_impl)
    rec("respond_via_runner", lambda: runner.server_impl.respond())
    rec("inspect_getsourcefile(flat.respond)", lambda: rel(inspect.getsourcefile(flat_impl.respond)))
    rec("flat_server_impl.__file__", lambda: rel(flat_impl.__file__))
    rec("flat_server_impl.__name__", lambda: flat_impl.__name__)
    rec("flat_server_impl.__spec__.name", lambda: getattr(flat_impl.__spec__, "name", None))
    rec("respond.__module__", lambda: flat_impl.respond.__module__)
    rec("_load_script(retained_tool).__file__", lambda: rel(flat_impl._load_script("retained_tool").__file__))
    rec("package_dir_on_sys_path", lambda: str(scripts / "wavefoundry_server") in sys.path)


if scenario == "static":
    import server as runner
    common_static(runner)
    rec("modules", modules_by_key)
    rec("live_graph_handler_module_objects", live_handler_modules)

elif scenario == "reload":
    import server as runner
    before = modules_by_key()
    build_tree.build(scripts.parent, strategy=strategy, purge=purge, version="v2", handler_import=handler_import,
                     flat_files=(strategy != "c"))
    importlib.invalidate_caches()
    rec("reload_call", lambda: runner.perform_reload().__name__)
    pkg_impl = sys.modules.get("wavefoundry_server.server_impl")
    rec("served_after_reload", lambda: runner.server_impl.respond())
    rec("runner_ref_is_sys_modules_server_impl", lambda: runner.server_impl is sys.modules["server_impl"])
    rec("runner_ref_is_package_module", lambda: runner.server_impl is pkg_impl)
    rec("impl_version_after_reload", lambda: runner.server_impl.IMPL_VERSION)
    rec("impl_bound_graph_response_version", lambda: runner.server_impl.graph_response.__globals__["HANDLER_VERSION"])
    rec("flat_gh_is_package_gh", lambda: sys.modules.get("graph_handlers") is sys.modules.get("wavefoundry_server.graph_handlers"))
    rec("parent_attr_is_sys_modules_entry", lambda: getattr(sys.modules["wavefoundry_server"], "graph_handlers", None) is sys.modules.get("wavefoundry_server.graph_handlers"))
    rec("parent_attr_version", lambda: getattr(getattr(sys.modules["wavefoundry_server"], "graph_handlers", None), "HANDLER_VERSION", None))
    rec("import_graph_handlers_version", lambda: importlib.import_module("graph_handlers").HANDLER_VERSION)
    rec("runner_identity_survives(read_identity)", lambda: runner.server_impl.read_identity())
    rec("runner_version_survives", lambda: runner.server_impl.read_runner_version())
    rec("shared_substrate_version", lambda: sys.modules["shared_substrate"].SUBSTRATE_VERSION)
    obs["modules_before"] = before
    rec("modules_after", modules_by_key)
    gc.collect()
    rec("live_graph_handler_module_objects", live_handler_modules)
    rec("second_reload_ok", lambda: (build_tree.build(scripts.parent, strategy=strategy, purge=purge, version="v3",
                                                      handler_import=handler_import, flat_files=(strategy != "c")),
                                     importlib.invalidate_caches(), runner.perform_reload(),
                                     runner.server_impl.respond()["handler_version"], runner.server_impl.IMPL_VERSION)[3:])

elif scenario == "old_runner":
    # tree was built as strategy "old" (installed 1.25/1.26-shaped flat monolith) before this process
    import server as runner
    rec("served_before_upgrade", lambda: runner.server_impl.respond())
    old_obj = runner.server_impl
    build_tree.build(scripts.parent, strategy=strategy, purge=purge, version="v2", handler_import=handler_import,
                     flat_files=(strategy != "c"))
    importlib.invalidate_caches()
    rec("reload_returned_name", lambda: runner.perform_reload().__name__)
    pkg_impl = sys.modules.get("wavefoundry_server.server_impl")
    rec("runner_ref_is_package_module", lambda: runner.server_impl is pkg_impl)
    rec("runner_ref_is_old_object", lambda: runner.server_impl is old_obj)
    rec("served_after_upgrade_reload", lambda: runner.server_impl.respond())
    rec("runner_identity_after(read_identity)", lambda: runner.server_impl.read_identity())
    rec("flat_gh_is_package_gh", lambda: sys.modules.get("graph_handlers") is sys.modules.get("wavefoundry_server.graph_handlers"))
    rec("modules_after", modules_by_key)
    gc.collect()
    rec("live_graph_handler_module_objects", live_handler_modules)
    rec("second_reload", lambda: (build_tree.build(scripts.parent, strategy=strategy, purge=purge, version="v3",
                                                   handler_import=handler_import, flat_files=(strategy != "c")),
                                  importlib.invalidate_caches(), runner.perform_reload(),
                                  runner.server_impl.respond()["handler_version"])[3])

elif scenario == "naive_root":
    import server as runner
    common_static(runner)
    rec("modules", modules_by_key)
    rec("live_graph_handler_module_objects", live_handler_modules)

elif scenario == "spec_load":
    import importlib.util as iu
    spec = iu.spec_from_file_location("_wavefoundry_server_impl", scripts / "server_impl.py")
    mod = iu.module_from_spec(spec)
    sys.modules["_wavefoundry_server_impl"] = mod
    rec("exec", lambda: spec.loader.exec_module(mod) or "ok")
    rec("returned_object_has_respond", lambda: hasattr(mod, "respond"))
    rec("returned_object_is_package_module", lambda: mod is sys.modules.get("wavefoundry_server.server_impl"))
    rec("sys_modules_private_key_is_package_module", lambda: sys.modules.get("_wavefoundry_server_impl") is sys.modules.get("wavefoundry_server.server_impl"))

elif scenario == "consumer":
    # like memory_cli: no runner, imports a handler by flat public name first
    rec("import_graph_handlers", lambda: rel(importlib.import_module("graph_handlers").__file__))
    rec("graph_response", lambda: importlib.import_module("graph_handlers").graph_response())
    rec("server_impl_is_package", lambda: importlib.import_module("server_impl") is sys.modules.get("wavefoundry_server.server_impl"))
    rec("package_initializer_imported_nothing_heavy", lambda: sorted(k for k in sys.modules if k.startswith("wavefoundry_server")))

print(json.dumps(obs, sort_keys=True))
