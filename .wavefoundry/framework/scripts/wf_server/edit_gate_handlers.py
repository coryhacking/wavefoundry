"""Edit gate handlers: extracted response ownership."""
from __future__ import annotations

from lifecycle_gate_support import _diagnostic
from pathlib import Path
from typing import Any
from typing import Optional
import datetime
import re


def _update_handoff_wave_ref(existing: str, wave_id: Optional[str]) -> str:
    """Surgically update the Active wave reference and Last verified in session-handoff.md.

    Only the ``**Active wave:**`` line and the ``Last verified:`` metadata field are
    updated.  All other content is preserved unchanged.  If the file is empty or the
    ``**Active wave:**`` pattern is absent, a minimal valid scaffold is written instead.

    Args:
        existing: Current file content (empty string when the file does not exist).
        wave_id: Wave ID to mark as active, or None to clear (renders as ``*(none)*``).
    """
    active_ref = f"`{wave_id}`" if wave_id else "*(none)*"
    today = datetime.date.today().isoformat()

    if not existing.strip():
        status = "active" if wave_id else "idle"
        return (
            "# Session Handoff\n\n"
            "Owner: wave-coordinator\n"
            f"Status: {status}\n"
            f"Last verified: {today}\n\n"
            "## Current Session\n\n"
            f"**Active wave:** {active_ref}\n"
        )

    lines = existing.splitlines(keepends=True)
    found_active = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Active wave:**"):
            out.append(f"**Active wave:** {active_ref}\n")
            found_active = True
        elif stripped.startswith("Last verified:"):
            out.append(f"Last verified: {today}\n")
        else:
            out.append(line)

    if not found_active:
        # Active wave line absent — insert it under ## Current Session if that section
        # exists, preserving all other content.  Only fall back to a minimal scaffold
        # if the file has no Current Session section at all.
        result = "".join(out)
        if "## Current Session" in result:
            result = re.sub(
                r"(## Current Session\s*\n+)",
                rf"\1**Active wave:** {active_ref}\n",
                result,
                count=1,
            )
            return result
        # No Current Session section — append one.
        if not result.endswith("\n"):
            result += "\n"
        result += f"\n## Current Session\n\n**Active wave:** {active_ref}\n"
        return result

    return "".join(out)


_VALID_GATES = {"seed_edit_allowed", "framework_edit_allowed", "design_system_edit_allowed"}


def _read_guard_overrides(root: Path) -> dict[str, Any]:
    """Read .wavefoundry/guard-overrides.json; return empty dict on missing/malformed."""
    path = root / ".wavefoundry" / "guard-overrides.json"
    if not path.exists():
        return {}
    try:
        import json as _json
        return _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_guard_overrides(root: Path, data: dict[str, Any]) -> None:
    """Write data to .wavefoundry/guard-overrides.json."""
    import json as _json
    path = root / ".wavefoundry" / "guard-overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _force_gates_closed(root: Path, mode: str) -> list[dict[str, Any]]:
    """Close all edit gates and return a diagnostic listing which were open.

    In dry-run mode the gate file is not written; the diagnostic is still returned
    so callers can report what would have been closed.

    Args:
        root: Repository root.
        mode: ``"create"`` to write the gate file; any other value is a dry-run.
    """
    overrides = _read_guard_overrides(root)
    open_gates = [g for g in _VALID_GATES if overrides.get(g, {}).get("enabled", False)]
    if not open_gates:
        return []
    if mode == "create":
        for gate in _VALID_GATES:
            overrides.setdefault(gate, {})["enabled"] = False
        _write_guard_overrides(root, overrides)
    return [
        _diagnostic(
            "gates_forced_closed",
            f"The following edit gate(s) were open and have been {'closed' if mode == 'create' else 'detected (dry-run — not closed)' }: {', '.join(sorted(open_gates))}. "
            "Use wf_open_gate / wf_close_gate to manage gates explicitly.",
            recovery_tools=["wf_close_gate"],
            recovery_usage="wf_close_gate(gate='seed_edit_allowed')",
        )
    ]


def wave_open_gate_response(root: Path, gate: str) -> dict[str, Any]:
    """Open an edit gate, enabling the corresponding guard in guard-overrides.json."""
    from wf_server import server_impl
    gate_s = (gate or "").strip()
    if gate_s not in _VALID_GATES:
        return server_impl._response(
            "error",
            {"gate": gate_s, "valid_gates": sorted(_VALID_GATES)},
            diagnostics=[_diagnostic("invalid_arguments", f"Unknown gate '{gate_s}'. Valid gates: {sorted(_VALID_GATES)}.")],
            next_tools=["wf_open_gate"],
            usage=f"wf_open_gate(gate='seed_edit_allowed')",
        )
    overrides = _read_guard_overrides(root)
    if overrides.get(gate_s, {}).get("enabled", False):
        return server_impl._response(
            "error",
            {"gate": gate_s, "enabled": True},
            diagnostics=[_diagnostic(
                "gate_already_open",
                f"Gate '{gate_s}' is already open. Close it with wf_close_gate before opening again.",
                recovery_tools=["wf_close_gate"],
                recovery_usage=f"wf_close_gate(gate={gate_s!r})",
            )],
            next_tools=["wf_close_gate"],
            usage=f"wf_close_gate(gate={gate_s!r})",
        )
    overrides.setdefault(gate_s, {})["enabled"] = True
    _write_guard_overrides(root, overrides)
    return server_impl._response(
        "ok",
        {"gate": gate_s, "enabled": True},
        next_tools=["wf_close_gate"],
        usage=f"wf_close_gate(gate={gate_s!r})",
    )


def wf_close_wave_gate_response(root: Path, gate: str) -> dict[str, Any]:
    """Close an edit gate, disabling the corresponding guard in guard-overrides.json."""
    from wf_server import server_impl
    gate_s = (gate or "").strip()
    if gate_s not in _VALID_GATES:
        return server_impl._response(
            "error",
            {"gate": gate_s, "valid_gates": sorted(_VALID_GATES)},
            diagnostics=[_diagnostic("invalid_arguments", f"Unknown gate '{gate_s}'. Valid gates: {sorted(_VALID_GATES)}.")],
            next_tools=["wf_close_gate"],
            usage=f"wf_close_gate(gate='seed_edit_allowed')",
        )
    overrides = _read_guard_overrides(root)
    already_closed = not overrides.get(gate_s, {}).get("enabled", False)
    overrides.setdefault(gate_s, {})["enabled"] = False
    _write_guard_overrides(root, overrides)
    diagnostics: list[dict[str, Any]] = []
    if already_closed:
        diagnostics.append(_diagnostic(
            "gate_already_closed",
            f"Gate '{gate_s}' was already closed — no change made.",
        ))
    return server_impl._response(
        "ok",
        {"gate": gate_s, "enabled": False},
        diagnostics=diagnostics if diagnostics else None,
        next_tools=["wf_open_gate"],
        usage=f"wf_open_gate(gate={gate_s!r})",
    )


def wf_gate_status_response(root: Path) -> dict[str, Any]:
    """Return the current enabled/disabled state of all edit gates."""
    from wf_server import server_impl
    overrides = _read_guard_overrides(root)
    gates = {gate: overrides.get(gate, {}).get("enabled", False) for gate in sorted(_VALID_GATES)}
    return server_impl._response(
        "ok",
        {"gates": gates},
        next_tools=["wf_open_gate", "wf_close_gate"],
    )


def wf_get_handoff_response(root: Path) -> dict[str, Any]:
    """Read docs/agents/session-handoff.md and return its content and mtime."""
    from wf_server import server_impl
    handoff_path = root / "docs" / "agents" / "session-handoff.md"
    if not handoff_path.exists():
        return server_impl._response(
            "ok",
            {"path": "docs/agents/session-handoff.md", "content": None, "mtime": None},
            diagnostics=[
                _diagnostic(
                    "handoff_not_found",
                    "docs/agents/session-handoff.md does not exist. Use wf_set_handoff to create it.",
                    recovery_tools=["wf_current_wave"],
                    recovery_usage="wf_current_wave()",
                )
            ],
            next_tools=["wf_set_handoff", "wf_current_wave"],
            usage="wf_set_handoff(content='# Session Handoff\\n\\n...')",
        )
    try:
        content = handoff_path.read_text(encoding="utf-8")
        mtime = handoff_path.stat().st_mtime
    except OSError as exc:
        return server_impl._response("error", {"path": "docs/agents/session-handoff.md"}, diagnostics=[_diagnostic("read_error", str(exc))], next_tools=["wf_current_wave"], usage="wf_current_wave()")
    return server_impl._response(
        "ok",
        {"path": "docs/agents/session-handoff.md", "content": content, "mtime": mtime},
        next_tools=["wf_set_handoff", "wf_current_wave"],
        usage="wf_current_wave()",
    )


def wf_set_handoff_response(root: Path, content: str, cache: Optional[server_impl.McpRepoCache] = None) -> dict[str, Any]:
    """Write content to docs/agents/session-handoff.md, creating the file if absent."""
    from wf_server import server_impl
    handoff_path = root / "docs" / "agents" / "session-handoff.md"
    try:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return server_impl._response("error", {"path": "docs/agents/session-handoff.md"}, diagnostics=[_diagnostic("write_error", str(exc))], next_tools=["wf_current_wave"], usage="wf_current_wave()")
    server_impl._trigger_background_index_refresh_for_paths(root, ["docs/agents/session-handoff.md"])
    envelope = server_impl._response(
        "ok",
        {"path": "docs/agents/session-handoff.md", "written": True, "size": len(content)},
        next_tools=["wf_get_handoff", "wf_current_wave"],
        usage="wf_get_handoff()",
    )
    # wf_set_handoff has no `mode` param — it always writes. Pass "create"
    # so the lint integration fires.
    return server_impl._attach_lint_to_response(envelope, root, "create")


_EDIT_GOVERNANCE_GATE_MAP = (
    (".wavefoundry/framework/seeds/", "seed_edit_allowed"),
    (".wavefoundry/framework/scripts/", "framework_edit_allowed"),
    (".wavefoundry/framework/dashboard/", "framework_edit_allowed"),
)
