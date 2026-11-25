"""Compare repository-owned host policy for renamed stock spec operations."""
from __future__ import annotations

from fnmatch import fnmatchcase
import hashlib
import json
import os
import platform
import re
from pathlib import Path

from contained_files import read_contained_bytes

CLAUDE_PROJECT = ".claude/settings.json"
CLAUDE_LOCAL = ".claude/settings.local.json"
CODEX_PROJECT = ".codex/config.toml"
CURSOR_PROJECT = ".cursor/settings.json"
MANAGED_ALLOW_KEY = "wavefoundryManagedAllow"


def _read(root, rel):
    try:
        (root / rel).lstat()
    except FileNotFoundError:
        return None
    return read_contained_bytes(root, rel, max_bytes=4 * 1024 * 1024, follow_links=False).decode("utf-8")


def _strings(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected an array of strings")
    return value


def _mapping(value):
    if not isinstance(value, dict):
        raise ValueError("expected a policy object")
    return value


def _claude(data, rel, routes, prefix, held, manual):
    settings = _mapping(json.loads(data))
    permissions = _mapping(settings.get("permissions", {}))
    claimed = _strings(settings.get(MANAGED_ALLOW_KEY, [])) if rel == CLAUDE_PROJECT else []
    for category in ("deny", "ask", "allow"):
        rules = _strings(permissions.get(category, []))
        # A manual allow in a personal file stays personal. A matching rule
        # in project policy keeps its original provenance.
        if category == "allow" and rel == CLAUDE_PROJECT:
            rules = [item for item in rules if item not in claimed]
        for old, new in routes.items():
            old_rule, new_rule = prefix + old, prefix + new
            for rule in rules:
                tool_pattern, _, constraint = rule.partition("(")
                qualifies = tool_pattern.startswith("mcp__")
                matches_old = qualifies and fnmatchcase(old_rule, tool_pattern)
                matches_new = qualifies and fnmatchcase(new_rule, tool_pattern)
                if category == "allow" and (matches_old or matches_new):
                    manual.add(new)
                if not matches_old:
                    continue
                equivalent = matches_new or (tool_pattern == old_rule and new_rule in rules)
                if not equivalent or constraint:
                    held.setdefault(new, f"Update the {category} rule for {old} in {rel} "
                                         f"for {new}, then restart the host.")


def _codex(data, routes, server, held):
    import tomllib
    config = _mapping(tomllib.loads(data))
    servers = _mapping(config.get("mcp_servers", {}))
    settings = _mapping(servers.get(server, {}))
    entries = _mapping(settings.get("tools", {}))
    lists = {key: _strings(settings.get(key, [])) for key in ("enabled_tools", "disabled_tools")}
    for old, new in routes.items():
        unmatched = any(old in names and new not in names for names in lists.values())
        if old in entries and entries.get(new) != entries[old]:
            unmatched = True
        if unmatched:
            held[new] = f"Match the {old} and {new} tool settings in {CODEX_PROJECT}, then restart the host."


_FRESH_LINE = "Initial MCP vocabulary: spec-tools-v1"
_RECEIPT = "Operator reviewed the exact tool name across all effective host permission layers.\n"


def _requires_review(root):
    # Only the live first-install log is evidence. The shipped template is
    # replaced on every upgrade, including on a legacy runner's first hop.
    log = _read(root, ".wavefoundry/install-log.md")
    if log is None:
        return os.path.lexists(root / ".wavefoundry/framework")
    header = log.split("\n## ", 1)[0].splitlines()
    return _FRESH_LINE not in header


def _receipt_path(root, tool):
    # A project-local cache can be shared over a mounted volume. Scope the
    # decision to this workstation, user and absolute checkout as well.
    scope = json.dumps([platform.node(), str(Path.home()), str(root.resolve())])
    key = hashlib.sha256(scope.encode()).hexdigest()[:32]
    return f".wavefoundry/cache/spec-tool-permissions/{key}/{tool}.txt"


def _review_command(tool):
    from setup_commands import format_command
    return format_command(["python3", ".wavefoundry/framework/scripts/upgrade_wavefoundry.py",
                           "spec-permissions", "--root", ".", "--tool", tool,
                           "--confirm-effective-host-rules"])


def _review_held(root, routes, held):
    try:
        required = _requires_review(root)
    except (OSError, ValueError):
        required = True
    if not required:
        return
    for old, new in routes.items():
        try:
            valid = _read(root, _receipt_path(root, new)) == _RECEIPT
        except (OSError, ValueError):
            valid = False
        if not valid:
            held.setdefault(new, f"Review {old} and {new} in all effective host permission layers. "
                            "Preserve their restrictions and grant scope. From the target checkout's root, "
                            f"run `{_review_command(new)}`, then restart the host.")


def acknowledge(argv):
    import argparse
    import mcp_tool_extensions
    from contained_files import write_contained_bytes
    routes = mcp_tool_extensions.stock_spec_routes()
    parser = argparse.ArgumentParser(description="Record the operator's review of effective host permissions.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--tool", choices=sorted(routes.values()), required=True)
    parser.add_argument("--confirm-effective-host-rules", required=True, action="store_true",
                        help="I verified grant scope and ask/deny in every effective host policy for this checkout.")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / ".wavefoundry/framework").is_dir():
        parser.error("select an installed project root")
    try:
        rel = _receipt_path(root, args.tool)
        if _read(root, rel) != _RECEIPT:
            write_contained_bytes(root, rel, _RECEIPT.encode(), mode=0o600, no_links=True)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot record permission review: {error}\n")
    print(f"Recorded operator review for {args.tool}. Restart the host. Project policy still applies.")
    return 0


def assess(root, routes, prefix):
    """Return withheld routes and manual grants in the inspected repository files.

    The host owns effective permissions and personal or administrative policy
    outside the checkout. An MCP process cannot inspect a host's launch arguments.
    """
    held, manual = {}, set()
    if not routes:
        return held, manual
    if root is None:
        return {new: "Select the repository to verify its host rules." for new in routes.values()}, manual
    root = Path(root).resolve()
    server = prefix.removeprefix("mcp__").removesuffix("__")
    for rel in (CLAUDE_PROJECT, CLAUDE_LOCAL, CODEX_PROJECT, CURSOR_PROJECT):
        try:
            data = _read(root, rel)
            if data is None:
                continue
            if rel in (CLAUDE_PROJECT, CLAUDE_LOCAL):
                _claude(data, rel, routes, prefix, held, manual)
            elif rel == CODEX_PROJECT:
                _codex(data, routes, server, held)
            else:
                # Cursor and other host-owned extensions have no framework
                # permission writer. A matching token alone proves no grant.
                for old, new in routes.items():
                    if re.search(r"(?<![A-Za-z0-9])" + re.escape(old) + r"(?![A-Za-z0-9_])", data):
                        held[new] = f"Review and update {old} in {rel} for {new}, then restart the host."
        except (OSError, ValueError):
            for new in routes.values():
                held.setdefault(new, f"Inspect or repair {rel}, then restart the host to enable {new}.")
    _review_held(root, routes, held)
    return held, manual
