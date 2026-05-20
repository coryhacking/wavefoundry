#!/usr/bin/env python3
"""Wavefoundry MCP server — thin runner (stdio transport, reloadable impl)."""
from __future__ import annotations

import argparse
import importlib
import sys
import threading
from pathlib import Path
from typing import Any, Optional

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Thin-runner protocol version — bump when transport/stub wiring changes (requires client reconnect).
SERVER_RUNNER_VERSION = "1"

import server_impl


def __getattr__(name: str) -> Any:
    """Re-export server_impl symbols for tests and legacy ``import server`` callers."""
    return getattr(server_impl, name)

_handler: Optional[server_impl.ImplHandler] = None
_reload_lock = threading.Lock()


def _get_handler() -> server_impl.ImplHandler:
    if _handler is None:
        raise RuntimeError("MCP handler not initialized — call build_server first")
    return _handler


def _set_handler(handler: server_impl.ImplHandler) -> None:
    global _handler
    _handler = handler


def perform_mcp_reload() -> dict[str, Any]:
    """Reload server_impl and replace handler. Returns version payload."""
    global server_impl
    with _reload_lock:
        try:
            old = _get_handler()
        except RuntimeError:
            return server_impl._response(
                "error",
                {},
                diagnostics=[server_impl._diagnostic("handler_not_ready", "MCP handler not initialized")],
            )
        close_warnings: list[dict] = []
        try:
            old.close()
        except Exception as exc:
            close_warnings.append(
                server_impl._diagnostic("handler_close_warning", f"Old handler close raised: {exc}")
            )
        server_impl._script_cache.clear()
        server_impl = importlib.reload(server_impl)
        server_impl.set_server_runner_version(SERVER_RUNNER_VERSION)
        try:
            new_handler = server_impl.build_handler(old.root)
        except Exception as exc:
            _set_handler(old)
            return server_impl._response(
                "error",
                {},
                diagnostics=[server_impl._diagnostic("reload_failed", str(exc))] + close_warnings,
            )
        _set_handler(new_handler)
        payload = server_impl.version_payload(
            old.root, server_runner_version=SERVER_RUNNER_VERSION
        )
        payload["ok"] = True
        return server_impl._response("ok", payload, diagnostics=close_warnings, usage="wave_mcp_reload()")


def build_server(root: Path):
    from mcp.server.fastmcp import FastMCP

    server_impl.set_server_runner_version(SERVER_RUNNER_VERSION)
    _set_handler(server_impl.build_handler(root))
    mcp = FastMCP("wavefoundry_mcp")
    server_impl.register_mcp_surface(mcp, _get_handler)

    _READONLY_TOOL = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
    _MUTATING_TOOL = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_mcp_reload(**kwargs: Any) -> dict[str, Any]:
        """Reload MCP implementation module without restarting the stdio server.

        Returns framework_version, server_runner_version, server_impl_version, and
        impl_matches_disk so callers can verify an upgrade was applied in-process.
        """
        bad = server_impl._ensure_no_extra_args("wave_mcp_reload", kwargs)
        if bad is not None:
            return bad
        return perform_mcp_reload()

    tool_names = server_impl._registered_mcp_tool_names(mcp)
    violations = server_impl.first_party_tool_names_violating_prefix(tool_names)
    if violations:
        raise RuntimeError(
            "MCP tool name prefix contract violated for: " + ", ".join(violations)
        )
    return mcp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wavefoundry MCP server (stdio transport)")
    parser.add_argument("--root", default=None, help="Repository root (default: auto-discover)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = server_impl._discover_root(args.root)
    mcp = build_server(root)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
