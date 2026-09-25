"""What happens if a reload purge evicts by prefix 'wavefoundry_server' (parent package included)?"""
import importlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_tree
out = {}
with tempfile.TemporaryDirectory() as tmp:
    s = build_tree.build(Path(tmp), strategy="a", purge="both", version="v1")
    sys.path.insert(0, str(s))
    import server as runner
    # evict the whole package namespace (parent + submodules) before reload, as a naive prefix purge would
    for k in [k for k in sys.modules if k == "wavefoundry_server" or k.startswith("wavefoundry_server.")]:
        del sys.modules[k]
    try:
        runner.perform_reload()
        out["reload_after_prefix_purge"] = "ok"
    except Exception as exc:
        out["reload_after_prefix_purge"] = f"{type(exc).__name__}: {exc}"
print(json.dumps(out))
