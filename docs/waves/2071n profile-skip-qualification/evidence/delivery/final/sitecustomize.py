"""Read-only output capture for canonical runner qualification (no result edits)."""
import json
import os
from pathlib import Path
import subprocess
import sys

if (Path(sys.argv[0]).name == "run_tests.py" and os.environ.get("WF_2071N_CAPTURE_DIR")
        and not os.environ.get("WF_2071N_CAPTURE_DISABLED")):
    _original_run = subprocess.run

    def _capture_run(*args, **kwargs):
        argv = args[0] if args else kwargs.get("args")
        worker = (isinstance(argv, (list, tuple)) and "unittest" in argv
                  and "discover" in argv and "-p" in argv)
        if worker:
            kwargs = dict(kwargs)
            kwargs["env"] = dict(kwargs.get("env") or os.environ)
            kwargs["env"]["WF_2071N_CAPTURE_DISABLED"] = "1"
        result = _original_run(*args, **kwargs)
        if worker:
            filename = str(argv[argv.index("-p") + 1])
            if filename.startswith("test_") and filename.endswith(".py") and Path(filename).name == filename:
                profile = (kwargs.get("env") or {}).get("WAVEFOUNDRY_TEST_PROFILE", "default")
                if profile not in {"default", "second", "declared"}:
                    raise RuntimeError("unexpected qualification profile")
                destination = Path(os.environ["WF_2071N_CAPTURE_DIR"]) / profile
                destination.mkdir(parents=True, exist_ok=True)
                (destination / (filename + ".json")).write_text(json.dumps({
                    "argv": list(argv), "returncode": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr,
                }, indent=2), encoding="utf-8")
        return result

    subprocess.run = _capture_run
