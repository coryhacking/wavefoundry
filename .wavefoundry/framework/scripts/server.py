#!/usr/bin/env python3
"""Wavefoundry MCP server — thin runner (stdio transport, reloadable impl)."""
from __future__ import annotations

import argparse
import importlib
import io
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

sys.dont_write_bytecode = True

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Activate the shared tool venv IN-PROCESS before any heavy import (wave 1p7pl/1p802). Stdlib-only;
# no-op when already in the venv or when it does not exist yet (fresh bootstrap). No re-exec/child process.
import venv_bootstrap

venv_bootstrap.activate_tool_venv()

# Thin-runner protocol version — bump when transport/stub wiring changes (requires client reconnect).
SERVER_RUNNER_VERSION = "1"

import server_impl


def __getattr__(name: str) -> Any:
    """Re-export server_impl symbols for tests and legacy ``import server`` callers."""
    return getattr(server_impl, name)

_handler: Optional[server_impl.ImplHandler] = None
_mcp: Any = None  # Wave 131bt (131d8): MCP instance reference for tool re-registration on reload.
_reload_lock = threading.Lock()
_root: Optional[Path] = None  # Wave 1p8kz: stashed at build_server so _get_handler can lazy-build.


def _get_handler() -> server_impl.ImplHandler:
    # Wave 1p8kz — lazy-build the handler when it has not been set yet but the root is known, so a
    # started server never reports handler_not_ready in the startup / post-reload window. The error
    # remains only for a genuinely uninitialized server (no root known).
    global _handler
    if _handler is None:
        if _root is None:
            raise RuntimeError("MCP handler not initialized — call build_server first")
        _handler = server_impl.build_handler(_root)
    return _handler


def _set_handler(handler: server_impl.ImplHandler) -> None:
    global _handler
    _handler = handler


def _set_mcp(mcp: Any) -> None:
    global _mcp
    _mcp = mcp


# Wave 131bt (131d8): tools that survive the re-register pass.
# wave_mcp_reload is defined in build_server (this module) rather than in
# server_impl.register_mcp_surface, so it must not be removed during refresh.
_RELOAD_SURVIVOR_TOOLS: frozenset[str] = frozenset({"wave_mcp_reload"})


def _configure_stdio_for_mcp_transport() -> None:
    """Keep MCP stdio framing byte-stable across native Windows text streams."""
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            kwargs: dict[str, Any] = {"encoding": "utf-8", "newline": "\n"}
            if stream_name in ("stdout", "stderr"):
                kwargs["write_through"] = True
            reconfigure(**kwargs)
        except Exception:
            # Best-effort only: some host-provided stream objects do not support
            # every TextIOWrapper option. Never block MCP startup for diagnostics.
            continue


def _isolate_native_stdout_from_protocol() -> None:
    """Give the MCP JSON-RPC protocol a PRIVATE dup of stdout and point OS fd 1 at ``os.devnull``.

    Native C/C++ extensions — onnxruntime's DirectML/CUDA execution providers enumerating GPU
    adapters on their FIRST load — write diagnostics DIRECTLY to file descriptor 1. When fd 1 is the
    stdio JSON-RPC channel, those bytes corrupt the protocol framing and hang the first call that
    triggers a model load (`wave_gpu_doctor`, and every first semantic search — `code_search` /
    `code_ask` / `docs_search` — plus the background prewarm thread). `contextlib.redirect_stdout`
    only swaps the Python `sys.stdout` object and cannot intercept native fd-1 writes; a per-call
    `os.dup2` on fd 1 is process-global and so is unsafe against the concurrent background prewarm
    thread. This isolates fd 1 ONCE, process-wide and thread-safely.

    The mcp stdio transport writes via `TextIOWrapper(sys.stdout.buffer, …)`, captured when the
    transport starts — i.e. AFTER this runs. So we dup the real stdout to a private fd, repoint
    `sys.stdout` to a buffered writer over that private fd (the transport then writes there → the
    host), and redirect fd 1 → devnull so every native fd-1 write is dropped. Best-effort: build the
    new stream first and only swap when it is ready; on any failure leave `sys.stdout` / fd 1
    untouched so the transport can never be broken by this hardening. ``sys.stderr`` (fd 2) is left
    alone — Python logs still reach the host's stderr."""
    try:
        stdout_fd = sys.stdout.fileno()
    except Exception:
        return  # no real OS fd behind sys.stdout (captured/redirected) — nothing to isolate
    try:
        saved_fd = os.dup(stdout_fd)
    except Exception:
        return
    try:
        # Buffered writer over the PRIVATE dup of the real stdout; mcp reads `sys.stdout.buffer`.
        private_stdout = io.TextIOWrapper(
            io.BufferedWriter(io.FileIO(saved_fd, "w", closefd=True)),
            encoding="utf-8",
            newline="\n",
            write_through=True,
        )
    except Exception:
        try:
            os.close(saved_fd)
        except Exception:
            pass
        return
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, stdout_fd)  # fd 1 → devnull: native writes are dropped process-wide
        os.close(devnull_fd)
    except Exception:
        # Could not point fd 1 at devnull. fd 1 is unchanged (still the pipe); still hand the
        # protocol the private dup so output flows (degraded: no native isolation, but functional).
        pass
    sys.stdout = private_stdout


def _refresh_mcp_tool_surface(
    mcp_instance: Any,
) -> tuple[int, list[str], list[dict[str, Any]]]:
    """Tear down and re-register the FastMCP first-party tool set (wave 131d8).

    Returns ``(tools_reregistered_count, description_changed_tools, warnings)``.
    ``description_changed_tools`` lists tools whose docstring-derived description
    differs between the pre-reload and post-reload FastMCP registry snapshots —
    when non-empty, the operator's MCP host must perform a full restart to
    surface the new descriptions in its tool-list display (the MCP protocol's
    ``notifications/tools/list_changed`` propagation is host-implementation-
    dependent and ``/mcp`` reconnect alone does not refresh descriptions in
    Claude Code per field validation, wave 131bt 131bu).

    Server-side re-registration completes correctly — the FastMCP registry holds
    the freshly-introspected schemas. The propagation gap is between the server
    and the host; the diagnostic surfaces honestly so the operator knows when a
    full restart is required.

    Tools listed in ``_RELOAD_SURVIVOR_TOOLS`` (wave_mcp_reload itself) are
    NOT removed; they continue serving from the build_server closure.
    """
    warnings: list[dict[str, Any]] = []
    if mcp_instance is None:
        warnings.append(
            server_impl._diagnostic(
                "mcp_instance_unavailable",
                "MCP instance reference not set — tool re-registration skipped. "
                "Description-string and parameter changes will not be visible "
                "until a full server restart.",
            )
        )
        return 0, [], warnings
    pre_reload = server_impl._registered_mcp_tool_names(mcp_instance)
    pre_descriptions = server_impl._registered_mcp_tool_descriptions(mcp_instance)
    to_refresh = pre_reload - _RELOAD_SURVIVOR_TOOLS
    removed = 0
    for name in to_refresh:
        try:
            mcp_instance.remove_tool(name)
            removed += 1
        except Exception as exc:
            warnings.append(
                server_impl._diagnostic(
                    "tool_remove_warning",
                    f"Removing tool {name!r} during reload raised: {exc}",
                )
            )
    try:
        server_impl.register_mcp_surface(mcp_instance, _get_handler)
    except Exception as exc:
        warnings.append(
            server_impl._diagnostic(
                "register_surface_failed",
                f"register_mcp_surface re-registration failed: {exc}",
            )
        )
        return 0, [], warnings
    post_reload = server_impl._registered_mcp_tool_names(mcp_instance)
    post_descriptions = server_impl._registered_mcp_tool_descriptions(mcp_instance)
    re_added = len(post_reload & to_refresh)
    # Wave 131bt (131bu): server-side description change detection. Tools whose
    # description differs from the pre-reload snapshot require a full host
    # restart to surface in the host's tool-list display.
    description_changed = sorted(
        name
        for name in (pre_reload | post_reload) - _RELOAD_SURVIVOR_TOOLS
        if pre_descriptions.get(name, "") != post_descriptions.get(name, "")
    )
    return re_added, description_changed, warnings


def perform_mcp_reload() -> dict[str, Any]:
    """Reload server_impl + refresh FastMCP tool schemas. Returns version payload.

    Wave 131bt (131d8): after reloading ``server_impl`` for response-shape
    refresh, the FastMCP tool registry is also torn down and re-registered so
    parameter schema and tool description changes land without a server
    restart. Clients still need to reconnect their MCP session (e.g. ``/mcp``
    in Claude Code) to refetch the tool list — but the server-side stale
    schema is resolved in-process.
    """
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
        # Evict wave_lint_lib submodules so lazy imports in server_impl
        # (e.g. wave_scan_secrets_response) pick up the freshly-edited code
        # rather than the cached pre-reload module objects.
        import sys as _sys
        for _key in list(_sys.modules):
            if _key.startswith("wave_lint_lib"):
                del _sys.modules[_key]
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
        # Wave 131bt (131d8): tear down + re-register FastMCP tool schemas so
        # parameter and description changes land in the server-side registry.
        # Wave 131bt (131bu): detect when description strings actually changed
        # and explicitly send the MCP `notifications/tools/list_changed`
        # protocol notification — FastMCP's add_tool/remove_tool do NOT send
        # this notification automatically (verified via SDK source). Without it
        # the client never knows to re-fetch tools/list, which is why a consumer
        # observed description staleness across `/mcp` reconnect. Pushing the
        # notification ourselves uses the existing MCP propagation primitive a
        # spec-conformant client honors by re-fetching. If the host doesn't
        # honor the notification, a full restart remains the fallback — the
        # response surfaces that fallback with description_changed_tools.
        tools_reregistered, description_changed, refresh_warnings = _refresh_mcp_tool_surface(_mcp)
        notification_sent = False
        notification_send_error: str | None = None
        if description_changed:
            try:
                ctx = _mcp.get_context()
                session = ctx.request_context.session
                # send_tool_list_changed is async; schedule synchronously via
                # asyncio.run_coroutine_threadsafe or run on the existing loop.
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # We're inside an event loop (tool handler context) — use
                    # ensure_future + a task; the notification is fire-and-forget.
                    loop.create_task(session.send_tool_list_changed())
                    notification_sent = True
                except RuntimeError:
                    # No running loop — synchronously run the coroutine.
                    asyncio.run(session.send_tool_list_changed())
                    notification_sent = True
            except Exception as exc:
                notification_send_error = f"{type(exc).__name__}: {exc}"
        payload = server_impl.version_payload(
            old.root, server_runner_version=SERVER_RUNNER_VERSION
        )
        payload["ok"] = True
        payload["tools_reregistered"] = tools_reregistered
        payload["description_changed_tools"] = description_changed
        payload["tool_list_changed_notification_sent"] = notification_sent
        diagnostics = close_warnings + refresh_warnings
        if description_changed:
            if notification_sent:
                diagnostics.append(
                    server_impl._diagnostic(
                        "tool_list_changed_notification_sent",
                        "Tool descriptions changed for {n} tool(s): {tools}. "
                        "Sent `notifications/tools/list_changed` to the connected "
                        "MCP client; spec-conformant clients re-fetch `tools/list` "
                        "on receipt and surface the new descriptions without "
                        "operator action. If the new descriptions are not visible "
                        "after this reload, the client may not honor the "
                        "notification — fall back to a full host restart "
                        "(quit and relaunch Claude Code).".format(
                            n=len(description_changed),
                            tools=", ".join(description_changed),
                        ),
                    )
                )
            else:
                diagnostics.append(
                    server_impl._diagnostic(
                        "tool_list_changed_notification_failed",
                        "Tool descriptions changed for {n} tool(s): {tools}. "
                        "Attempted to send `notifications/tools/list_changed` but "
                        "could not reach the active session ({err}). The MCP host "
                        "will not be told to re-fetch — fall back to a full host "
                        "restart (quit and relaunch Claude Code) to surface the "
                        "new descriptions.".format(
                            n=len(description_changed),
                            tools=", ".join(description_changed),
                            err=notification_send_error or "unknown",
                        ),
                    )
                )
        return server_impl._response(
            "ok",
            payload,
            diagnostics=diagnostics,
            usage="wave_mcp_reload()",
        )


def build_server(root: Path):
    from mcp.server.fastmcp import FastMCP

    global _root
    _root = root  # Wave 1p8kz: enable _get_handler lazy-build before/after the explicit _set_handler.
    server_impl.set_server_runner_version(SERVER_RUNNER_VERSION)
    _set_handler(server_impl.build_handler(root))
    mcp = FastMCP("wavefoundry_mcp")
    _set_mcp(mcp)  # Wave 131bt (131d8): expose for perform_mcp_reload tool refresh.
    server_impl.register_mcp_surface(mcp, _get_handler)

    _READONLY_TOOL = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
    _MUTATING_TOOL = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_mcp_reload(**kwargs: Any) -> dict[str, Any]:
        """Reload MCP implementation module without restarting the stdio server.

        Returns ``framework_version``, ``server_runner_version``, ``server_impl_version``,
        and ``impl_matches_disk`` so callers can verify an upgrade was applied
        in-process. Also returns ``tools_reregistered`` (count of FastMCP tool
        callables refreshed against the freshly-reloaded server_impl) and three
        description-change-propagation fields (wave 131bt 131bu):

        - ``description_changed_tools`` (list[str]): tool names whose docstring-
          derived description differs from the pre-reload snapshot. Empty list
          when no descriptions changed.
        - ``tool_list_changed_notification_sent`` (bool): ``True`` when the
          server sent the MCP `notifications/tools/list_changed` protocol
          notification to the connected client after detecting description
          changes. Spec-conformant clients re-fetch ``tools/list`` on receipt
          and surface the new descriptions without operator action — no
          restart, no ``/mcp`` reconnect required.

        When description changes were detected, the response also includes a
        structured diagnostic (``tool_list_changed_notification_sent`` on
        success or ``tool_list_changed_notification_failed`` on failure) with
        actionable next steps. If the client does not honor the notification,
        a full host restart (quit and relaunch Claude Code) remains the
        fallback.
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Verify the server can initialize without starting the stdio transport. "
            "Builds the server (imports, tool registration, framework state) and exits "
            "0 on success, non-zero on failure. Used by setup_wavefoundry.py as the "
            "harness installation smoke test."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = server_impl._discover_root(args.root)

    if args.dry_run:
        # Wave 1p35d (1p35f): smoke test invoked by setup_wavefoundry.py during
        # install Phase 1. Build the server (verifies all framework imports, tool
        # registration, and framework state) and exit cleanly without entering
        # the stdio transport loop. Any startup failure surfaces as a non-zero
        # exit + a clear error message.
        try:
            mcp = build_server(root)
        except Exception as exc:
            print(
                f"wavefoundry mcp-server --dry-run: FAILED — server build raised "
                f"{type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            return 1
        # Touch the handler to confirm it initialized.
        try:
            handler = _get_handler()
        except RuntimeError as exc:
            print(
                f"wavefoundry mcp-server --dry-run: FAILED — handler not initialized: {exc}",
                file=sys.stderr,
            )
            return 1
        print(
            f"wavefoundry mcp-server --dry-run: OK "
            f"(root={root}, handler={type(handler).__name__})",
            file=sys.stderr,
        )
        return 0

    _configure_stdio_for_mcp_transport()
    # wave 1p8vp: isolate native fd-1 writes (onnxruntime cold-load) from the JSON-RPC channel, once,
    # before the transport captures sys.stdout.buffer. Runs only on the real stdio path (dry-run
    # returns above).
    _isolate_native_stdout_from_protocol()
    mcp = build_server(root)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
