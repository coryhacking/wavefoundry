#!/usr/bin/env python3
import sys

sys.dont_write_bytecode = True

import json
import re

MAX_INPUT_BYTES = 16384
AGENT_PATTERN = '^code-modernization:[A-Za-z0-9][A-Za-z0-9_-]*$'
BRIEFING = (
    "Wavefoundry modernization briefing: Read AGENTS.md and follow "
    ".wavefoundry/framework/seeds/180-implement-change.prompt.md, "
    "especially Host-neutral orchestration and its canonical retrieval rules "
    "(docs/agents/guru.md for code/documentation investigation). "
    "Stay within the assigned change/ACs and owned paths; honor forbidden paths "
    "and read-only assignments. Investigation may precede readiness; implementation "
    "requires the repository stage gate. Verify your actual available tools; use "
    "Wavefoundry MCP first when available, and follow the documented fallback with "
    "a Gapfill: note naming unavailable access when it is not. Return scoped cited "
    "evidence, checks and limitations to the coordinator, who owns lifecycle tracking. "
    "This briefing grants no tools or permissions. Plugin plan approval or proof "
    "does not replace Wavefoundry readiness/review or operator authorization for "
    "closure, commits and releases."
)

def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("hook_event_name") != "SubagentStart":
            return
        agent_type = payload.get("agent_type")
        if not isinstance(agent_type, str) or re.fullmatch(AGENT_PATTERN, agent_type) is None:
            return
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": BRIEFING,
        }}))
    except (ValueError, UnicodeError, RecursionError, OSError):
        return

if __name__ == "__main__":
    main()
