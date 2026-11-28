"""Bootstrap-safe runtime policy. Return advisory data without printing or repair."""
from __future__ import annotations

import sys


def python_runtime_advisory() -> dict | None:
    """Describe the executing interpreter, independent of PATH or venv metadata.

    Python 3.11 to 3.13 are supported but security-only upstream, so python.org
    publishes no installers for their fixes. The machine code keeps its original
    ``python_runtime_deprecated`` name for compatibility with existing consumers."""
    version = sys.version_info
    if not (3, 11) <= tuple(version[:2]) < (3, 14):
        return None
    return {
        "code": "python_runtime_deprecated",
        "severity": "warning",
        "actual_version": ".".join(str(part) for part in version[:3]),
        "recommended_minimum": "3.14",
        "executable": sys.executable,
        "message": (
            f"Python {version[0]}.{version[1]} is supported but receives security fixes only. "
            "Python 3.14 is recommended. python.org publishes no installers for security-only "
            "versions, so a copy installed from python.org stops receiving security fixes; "
            "package-manager builds may continue to receive them. This advisory blocks nothing."
        ),
        "guidance": (
            "To move, install Python 3.14 and make it python3 on PATH for setup and the restarted MCP host. "
            "Every project on this machine shares one tool environment unless one selects an isolated "
            "environment, and setup under a different Python rebuilds it for all of them with this "
            "project's release; upgrade the other projects first, or isolate this project (framework "
            "README, Python runtime advisory and transition). "
            "Stop consumers of the shared tool environment before running wf setup with that Python. "
            "Setup does not install Python."
        ),
    }


def format_advisory(advisory: dict) -> str:
    """Format a notice for an entry point that owns stderr emission."""
    return (f"wavefoundry: {advisory['message']} "
            f"(executing Python {advisory['actual_version']}: {advisory['executable']!r}) "
            f"{advisory['guidance']}")
