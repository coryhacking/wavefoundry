"""Bounded project sensor execution, shared by explicit and lifecycle calls."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, TypedDict


class SensorResult(TypedDict):
    name: str
    dimension: str
    passed: bool
    exit_code: int | None
    output_summary: str
    duration_ms: int


def run_sensor(root: Path, sensor: Mapping[str, Any], *, timeout_seconds: float,
               shell: bool = False) -> SensorResult:
    import subprocess_util

    started = time.monotonic()
    result: SensorResult = {
        "name": str(sensor.get("name", "")),
        "dimension": str(sensor.get("dimension", "maintainability")),
        "passed": False, "exit_code": None, "output_summary": "", "duration_ms": 0,
    }
    try:
        cmd = sensor["command"]
        if not isinstance(cmd, list) and not shell:
            raise ValueError("Sensor command must be an argument list unless shell is explicitly enabled")
        proc = subprocess_util.isolated_run(
            cmd, shell=shell, cwd=str(root), timeout=timeout_seconds,
            capture_output=True, text=True,
        )
        result.update(passed=proc.returncode == 0, exit_code=proc.returncode,
                      output_summary="\n".join((proc.stdout + proc.stderr).strip().splitlines()[:20]))
    except subprocess.TimeoutExpired:
        result["output_summary"] = f"Sensor timed out after {timeout_seconds:g}s."
    except Exception as exc:
        result["output_summary"] = f"Sensor failed to run: {exc}"
    result["duration_ms"] = int((time.monotonic() - started) * 1000)
    return result
