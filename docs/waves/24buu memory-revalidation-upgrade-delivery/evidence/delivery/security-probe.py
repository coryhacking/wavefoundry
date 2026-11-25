"""Observe two restarted installed sessions in an isolated, local fixture."""
import asyncio
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

delivery = Path(__file__).resolve().parent
rehearsal = delivery.parent / "rehearsal"
spec = importlib.util.spec_from_file_location("rehearse", rehearsal / "rehearse.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
original = rehearsal / "pinned-cpu" / "mcp"

with tempfile.TemporaryDirectory() as tmp:
    target, host = Path(tmp) / "target", Path(tmp) / "home"
    subprocess.run(["cp", "-cR", str(original / "target"), str(target)], check=True)
    env = runner.environment(host, target)
    env["WAVEFOUNDRY_TOOL_VENV"] = str(original / "home/.wavefoundry/venv")
    env["PATH"] = "/opt/homebrew/bin:" + env["PATH"]
    env["WAVEFOUNDRY_EMBED_PROVIDER"] = "cpu"
    before = runner.snapshot(target)["legacy_records"]
    assert before and any("memory/" in key for key in before) and any("events.jsonl" in key for key in before)
    policy = host / ".claude/settings.json"
    for mode in ("relocated", "baseline", "restricted", "restart"):
        if mode == "baseline":
            subprocess.run([str(Path(env["WAVEFOUNDRY_TOOL_VENV"])/"bin/python"), "-B",
                            str(target/".wavefoundry/framework/scripts/render_platform_surfaces.py"),
                            "--repo-root", str(target), "--include-permissions"], check=True, env=env,
                           stdout=subprocess.DEVNULL)

        if mode == "restricted":
            policy.parent.mkdir(parents=True)
            policy.write_text(json.dumps({"permissions":{"deny":["mcp__wavefoundry__wf_get_change"]}}))
            saved = policy.read_bytes()
        out = asyncio.run(runner.call_served(target, env, ["inventory"], delivery / f"security-{mode}.json"))
        expected = set(runner.ROUTES)
        if mode == "relocated":
            expected.clear()
        if mode in ("restricted", "restart"):
            expected.remove("wf_get_spec")
            assert saved == policy.read_bytes()
        assert set(out["stock_spec_routes"]) == expected, out
        assert out["retired_change_routes"] == [] and out["memory_brief_status"] == "ok", out
        assert out["revalidation"]["active_records"] == 1, out
        assert before == runner.snapshot(target)["legacy_records"]
        print(mode, sorted(expected), "memory, ledger and wave bytes identical")
