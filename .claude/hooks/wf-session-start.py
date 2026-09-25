#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / ".wavefoundry" / "framework" / "scripts"
MAX_REASONS = 8
MAX_LINE = 240
HEADER = "Wavefoundry setup readiness (tool output from the session-start hook):"
ASK = "Report this to the operator and ask before running any command."


def _clean(text):
    text = "".join(ch if ch.isprintable() else " " for ch in str(text))
    return text[:MAX_LINE]


def render(result, format_command):
    status = result.get("status")
    if status == "ready":
        return []
    reasons = result.get("reasons") or []
    if status != "action_required":
        first = reasons[0] if reasons else {"code": "unknown", "message": "no reason reported"}
        return [_clean("Wavefoundry setup readiness could not be determined ("
                       + str(first.get("code")) + ": " + str(first.get("message"))
                       + "); run `wf setup --check --json` by hand.")]
    lines = [HEADER]
    for item in reasons[:MAX_REASONS]:
        lines.append(_clean("- " + str(item.get("code")) + ": " + str(item.get("message"))))
    if len(reasons) > MAX_REASONS:
        lines.append("- (" + str(len(reasons) - MAX_REASONS) + " more reasons omitted)")
    for action in result.get("actions") or []:
        kind = action.get("kind")
        if kind == "restart":
            lines.append("Recommended: restart the agent host.")
            continue
        command = "Recommended: " + format_command(action.get("argv") or [])
        if len(command) > MAX_LINE:
            # Never show a cut-off command; point at the full one instead.
            command = "Recommended: the command shown by `wf setup --check` (too long to show here)."
        lines.append(_clean(command))
        if kind == "setup":
            lines.append("Setup ends by asking for an agent-host restart.")
        elif kind == "resume":
            lines.append("Stop the Wavefoundry hosts and run it from an external terminal.")
    lines.append(ASK)
    return lines


def main():
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or _ROOT)
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    try:
        import cli_stdio

        cli_stdio.configure_utf8_stdio()
    except Exception:
        pass
    import setup_readiness

    result = setup_readiness.assess_setup(root)
    if [item.get("code") for item in result.get("reasons") or []] == ["inputs_changed"]:
        # State changed while assessing (the MCP server starts concurrently); once.
        result = setup_readiness.assess_setup(root)
    return render(result, setup_readiness.format_command)


if __name__ == "__main__":
    try:
        for _line in main():
            print(_line)
    except BaseException as exc:
        try:
            print(_clean("Wavefoundry setup readiness check failed (" + type(exc).__name__ + ": "
                         + str(exc) + "); run `wf setup --check` by hand."))
        except BaseException:
            pass
    raise SystemExit(0)
