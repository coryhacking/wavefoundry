"""Bootstrap-safe runtime policy. Return advisory data without printing or repair."""
from __future__ import annotations

import sys


def python_runtime_advisory() -> dict | None:
    """Describe the executing interpreter, independent of PATH or venv metadata."""
    version = sys.version_info
    if version[:2] not in ((3, 11), (3, 12)):
        return None
    return {
        "code": "python_runtime_deprecated",
        "severity": "warning",
        "actual_version": ".".join(str(part) for part in version[:3]),
        "recommended_minimum": "3.13",
        "executable": sys.executable,
        "message": (
            f"Python {version[0]}.{version[1]} is deprecated for Wavefoundry. "
            "Python 3.13 or newer is recommended. This advisory does not block execution; "
            "existing runtime checks still apply."
        ),
        "guidance": (
            "Install/select Python 3.13+ as python3 on PATH for setup and the restarted MCP host. "
            "Stop consumers of the shared tool environment before running wf setup with that Python; "
            "ordinary setup may replace an incompatible tool environment. Setup does not install Python."
        ),
    }


def format_advisory(advisory: dict) -> str:
    """Format a notice for an entry point that owns stderr emission."""
    return (f"wavefoundry: {advisory['message']} "
            f"(executing Python {advisory['actual_version']}: {advisory['executable']!r}) "
            f"{advisory['guidance']}")
