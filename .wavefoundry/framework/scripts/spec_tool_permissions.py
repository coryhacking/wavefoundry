"""Compare and migrate host policy for renamed stock spec operations.

Repository host settings are the only files this module writes, and only by
copying an existing exact old-name rule to the new name. User-level and
enterprise host settings outside the checkout are read, never written.
"""
from __future__ import annotations

import copy
from fnmatch import fnmatchcase
import hashlib
import json
import os
import platform
import re
import stat
import sys
from pathlib import Path

from contained_files import read_contained_bytes
import line_endings

CLAUDE_PROJECT = ".claude/settings.json"
CLAUDE_LOCAL = ".claude/settings.local.json"
CODEX_PROJECT = ".codex/config.toml"
CURSOR_PROJECT = ".cursor/settings.json"
MANAGED_ALLOW_KEY = "wavefoundryManagedAllow"
MAX_POLICY_BYTES = 4 * 1024 * 1024
# Overrides the enterprise managed-settings path, so tests and the subprocess
# render child can be isolated from the real machine.
MANAGED_SETTINGS_ENV = "WAVEFOUNDRY_MANAGED_SETTINGS_PATH"
# Claude Code enterprise managed settings by platform. Windows lists the
# documented ProgramData path and the Program Files path that current Claude
# Code releases use; both are read, never written.
MANAGED_SETTINGS_PATHS = {
    "darwin": ("/Library/Application Support/ClaudeCode/managed-settings.json",),
    "linux": ("/etc/claude-code/managed-settings.json",),
    "win32": (r"C:\ProgramData\ClaudeCode\managed-settings.json",
              r"C:\Program Files\ClaudeCode\managed-settings.json"),
}


def _read(root, rel):
    try:
        (root / rel).lstat()
    except FileNotFoundError:
        return None
    return read_contained_bytes(root, rel, max_bytes=MAX_POLICY_BYTES, follow_links=False).decode("utf-8")


def _strings(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected an array of strings")
    return value


def _mapping(value):
    if not isinstance(value, dict):
        raise ValueError("expected a policy object")
    return value


def _token(old):
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(old) + r"(?![A-Za-z0-9_])")


def _claude(data, rel, routes, prefix, held, manual, *, label=None, recommend=None):
    """Hold each route whose old name a rule names without the same rule for the new name.

    ``label`` marks a layer outside the checkout: its deny and ask rules hold
    the route and its allow rules only add a recommendation."""
    outside = label is not None
    settings = _mapping(json.loads(data))
    permissions = _mapping(settings.get("permissions", {}))
    claimed = _strings(settings.get(MANAGED_ALLOW_KEY, [])) if rel == CLAUDE_PROJECT else []
    for category in ("deny", "ask", "allow"):
        rules = _strings(permissions.get(category, []))
        # A manual allow in a personal file stays personal. A matching rule
        # in project policy keeps its original provenance.
        if category == "allow" and claimed:
            rules = [item for item in rules if item not in claimed]
        for old, new in routes.items():
            old_rule, new_rule = prefix + old, prefix + new
            for rule in rules:
                tool_pattern, _, _constraint = rule.partition("(")
                qualifies = tool_pattern.startswith("mcp__")
                matches_old = qualifies and fnmatchcase(old_rule, tool_pattern)
                matches_new = qualifies and fnmatchcase(new_rule, tool_pattern)
                if not outside and category == "allow" and (matches_old or matches_new):
                    manual.add(new)
                if not matches_old:
                    continue
                # The same rule, constraint included, must name the new tool.
                wanted = new_rule + rule[len(tool_pattern):]
                if matches_new or wanted in rules:
                    continue
                if not outside:
                    held.setdefault(new, f"Update the {category} rule for {old} in {rel} "
                                         f"for {new}, then restart the host.")
                    continue
                message = (f"Add the {category} rule {wanted} to {label} to match {rule}, "
                           "then restart the host.")
                if category == "allow":
                    if message not in recommend:
                        recommend.append(message)
                else:
                    held.setdefault(new, message)


def _codex(data, routes, server, held, *, label=None, recommend=None):
    import tomllib
    outside = label is not None
    config = _mapping(tomllib.loads(data))
    servers = _mapping(config.get("mcp_servers", {}))
    settings = _mapping(servers.get(server, {}))
    entries = _mapping(settings.get("tools", {}))
    lists = {key: _strings(settings.get(key, [])) for key in ("enabled_tools", "disabled_tools")}
    for old, new in routes.items():
        if not outside:
            unmatched = any(old in names and new not in names for names in lists.values())
            if old in entries and entries.get(new) != entries[old]:
                unmatched = True
            if unmatched:
                held[new] = f"Match the {old} and {new} tool settings in {CODEX_PROJECT}, then restart the host."
            continue
        for key, names in lists.items():
            if old in names and new not in names:
                message = (f"Add {new} to {key} for the {server} server in {label}, "
                           "then restart the host.")
                # Disabling restricts; an enabled list only narrows the grant.
                if key == "disabled_tools":
                    held.setdefault(new, message)
                elif message not in recommend:
                    recommend.append(message)
        if old in entries and entries.get(new) != entries[old]:
            held.setdefault(new, f"Copy [mcp_servers.{server}.tools.{old}] to tools.{new} in {label}, "
                                 "then restart the host.")


# ── Outside layers (read-only) ───────────────────────────────────────────────

def _home(environ):
    for key in ("HOME", "USERPROFILE"):
        value = environ.get(key)
        if value:
            return Path(value)
    return Path.home()


def _platform_key(system=None):
    system = sys.platform if system is None else system
    if system.startswith(("win32", "cygwin")):
        return "win32"
    if system == "darwin":
        return "darwin"
    return "linux"


def outside_layer_paths(environ=None, system=None):
    """Return ``(kind, scope, path)`` for each host policy file outside the checkout.

    The user-level Claude settings (``$CLAUDE_CONFIG_DIR/settings.json``, else
    ``<home>/.claude/settings.json``), the Codex user config
    (``$CODEX_HOME/config.toml``, else ``<home>/.codex/config.toml``) and the
    Claude enterprise managed settings for this platform, which
    ``WAVEFOUNDRY_MANAGED_SETTINGS_PATH`` overrides. ``<home>`` is ``HOME``, else
    ``USERPROFILE``, else ``Path.home()``. On WSL2 these are the Linux home's files.
    """
    env = os.environ if environ is None else environ
    home = _home(env)
    claude_dir = Path(env["CLAUDE_CONFIG_DIR"]) if env.get("CLAUDE_CONFIG_DIR") else home / ".claude"
    codex_dir = Path(env["CODEX_HOME"]) if env.get("CODEX_HOME") else home / ".codex"
    layers = [("claude", "user", claude_dir / "settings.json"), ("codex", "user", codex_dir / "config.toml")]
    override = env.get(MANAGED_SETTINGS_ENV)
    managed = (override,) if override else MANAGED_SETTINGS_PATHS[_platform_key(system)]
    layers.extend(("claude", "enterprise", Path(path)) for path in managed)
    return layers


def _read_outside(path):
    """Read a policy file read-only, following links; ``None`` when absent.

    The file is opened without blocking, and a special file (a FIFO or a
    device) or one over ``MAX_POLICY_BYTES`` raises ``ValueError``."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except (FileNotFoundError, NotADirectoryError):
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not a regular file")
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_POLICY_BYTES:
                raise ValueError("policy file too large")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _outside_holds(routes, prefix, held, recommend, files):
    server = prefix.removeprefix("mcp__").removesuffix("__")
    for kind, _scope, path in outside_layer_paths():
        label = str(path)
        try:
            data = _read_outside(path)
        except (OSError, ValueError):
            files.append({"path": label, "state": "unreadable"})
            for old, new in routes.items():
                held.setdefault(new, f"Inspect or repair {label}, then restart the host to enable {new}.")
            continue
        if data is None:
            files.append({"path": label, "state": "absent"})
            continue
        files.append({"path": label, "state": "read"})
        try:
            text = data.decode("utf-8")
            if kind == "claude":
                _claude(text, None, routes, prefix, held, set(), label=label, recommend=recommend)
            else:
                _codex(text, routes, server, held, label=label, recommend=recommend)
        except ValueError:
            # The host may still apply what this parser rejects (a byte-order
            # mark, for example). Hold every route the file names.
            files[-1]["state"] = "unparseable"
            visible = data.decode("utf-8", errors="replace")
            for old, new in routes.items():
                if _token(old).search(visible):
                    held.setdefault(new, f"Inspect or repair {label}, which names {old}, "
                                         f"then restart the host to enable {new}.")


# ── Review receipts ──────────────────────────────────────────────────────────

_FRESH_LINE = "Initial MCP vocabulary: spec-tools-v1"
_RECEIPT = "Operator reviewed the exact tool name across all effective host permission layers.\n"
_UPGRADE_RECEIPT = ("Upgrade verified the repository and the readable user-level and enterprise "
                    "host permission layers for this tool.\n")
_UPGRADE_LINE = re.compile(r"(?:Checked: [^\n]+ \((?:read|absent|unparseable)\)|Managed settings override: set)\Z")


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


def _receipt_valid(text):
    """An operator review or an upgrade verification body."""
    if text == _RECEIPT:
        return True
    if not isinstance(text, str) or not text.startswith(_UPGRADE_RECEIPT) or not text.endswith("\n"):
        return False
    return all(_UPGRADE_LINE.match(line) for line in text[len(_UPGRADE_RECEIPT):].split("\n")[:-1])


def _upgrade_body(files, override):
    lines = [f"Checked: {item['path']} ({item['state']})\n" for item in files]
    if override:
        lines.append("Managed settings override: set\n")
    return _UPGRADE_RECEIPT + "".join(lines)


def _write_receipt(root, tool, body):
    from contained_files import write_contained_bytes
    write_contained_bytes(root, _receipt_path(root, tool), body.encode(), mode=0o600, no_links=True)


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
            valid = _receipt_valid(_read(root, _receipt_path(root, new)))
        except (OSError, ValueError):
            valid = False
        if not valid:
            held.setdefault(new, f"Review {old} and {new} in all effective host permission layers. "
                            "Preserve their restrictions and grant scope. From the target checkout's root, "
                            f"run `{_review_command(new)}`, then restart the host.")


def acknowledge(argv):
    import argparse
    import mcp_tool_extensions
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
        if _read(root, _receipt_path(root, args.tool)) != _RECEIPT:
            _write_receipt(root, args.tool, _RECEIPT)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot record permission review: {error}\n")
    print(f"Recorded operator review for {args.tool}. Restart the host. Project policy still applies.")
    return 0


# ── Assessment ───────────────────────────────────────────────────────────────

def _repository_holds(root, routes, prefix, held, manual, texts):
    server = prefix.removeprefix("mcp__").removesuffix("__")
    for rel in (CLAUDE_PROJECT, CLAUDE_LOCAL, CODEX_PROJECT, CURSOR_PROJECT):
        try:
            data = texts[rel] if rel in texts else _read(root, rel)
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
                    if _token(old).search(data):
                        held[new] = f"Review and update {old} in {rel} for {new}, then restart the host."
        except (OSError, ValueError):
            for new in routes.values():
                held.setdefault(new, f"Inspect or repair {rel}, then restart the host to enable {new}.")


def assess_layers(root, routes, prefix, *, texts=None):
    """Return the holds by cause, the manual grants and the outside files read.

    ``repository`` holds come from host settings in the checkout, ``outside``
    holds from user-level and enterprise settings (read-only), and ``review``
    holds from a missing review or upgrade verification. ``texts`` replaces
    repository file contents, so a planned migration can be assessed unwritten.
    An MCP process cannot inspect a host's launch arguments, MDM profiles, the
    Windows registry or server-managed settings.
    """
    result = {"repository": {}, "outside": {}, "review": {}, "manual": set(), "recommendations": [],
              "outside_files": [], "managed_override": bool(os.environ.get(MANAGED_SETTINGS_ENV))}
    if not routes:
        return result
    if root is None:
        result["repository"] = {new: "Select the repository to verify its host rules." for new in routes.values()}
        return result
    root = Path(root).resolve()
    _repository_holds(root, routes, prefix, result["repository"], result["manual"], texts or {})
    _outside_holds(routes, prefix, result["outside"], result["recommendations"], result["outside_files"])
    _review_held(root, routes, result["review"])
    return result


def assess(root, routes, prefix):
    """Return the combined withheld routes and the manual grants in the repository files."""
    layers = assess_layers(root, routes, prefix)
    held = dict(layers["repository"])
    for cause in ("outside", "review"):
        for new, remedy in layers[cause].items():
            held.setdefault(new, remedy)
    return held, layers["manual"]


# ── Repository migration ─────────────────────────────────────────────────────

def _json_like(original, settings):
    """Serialize ``settings`` with the original indentation and termination."""
    match = re.search(r"^([ \t]+)\S", original, re.M)
    indent = match.group(1) if match else None
    text = json.dumps(settings, indent=indent, ensure_ascii=original.isascii())
    return text + "\n" if original.endswith("\n") else text


def _migrate_claude(text, rel, routes, prefix):
    settings = _mapping(json.loads(text))
    permissions = _mapping(settings.get("permissions", {}))
    # Framework-managed grants stay owned by the permissions render.
    claimed = set(_strings(settings.get(MANAGED_ALLOW_KEY, []))) if rel == CLAUDE_PROJECT else set()
    lists = {category: _strings(permissions[category]) for category in ("allow", "ask", "deny")
             if category in permissions}
    added = []
    for category, rules in lists.items():
        for rule in list(rules):
            if category == "allow" and rule in claimed:
                continue
            tool_pattern = rule.partition("(")[0]
            for old, new in routes.items():
                if tool_pattern != prefix + old:
                    continue
                wanted = prefix + new + rule[len(tool_pattern):]
                if wanted not in rules:
                    rules.append(wanted)
                    added.append((category, wanted, new))
    return (_json_like(text, settings) if added else text), added


def _toml_key(name):
    return name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else json.dumps(name)


def _key_pattern(name):
    return r"(?:" + re.escape(name) + r"|\"" + re.escape(name) + r"\")"


def _array_close(text, start):
    """Return ``(close, last)`` for the array opened at ``start``: the closing
    bracket and the last significant character before it."""
    depth, index, last, size = 0, start, start, len(text)
    while index < size:
        char = text[index]
        if char == "#":
            index = text.find("\n", index)
            if index < 0:
                return None
            continue
        if char in "\"'":
            quote = char * 3 if text.startswith(char * 3, index) else char
            cursor = index + len(quote)
            while True:
                if cursor >= size or (len(quote) == 1 and text[cursor] == "\n"):
                    return None
                if char == '"' and text[cursor] == "\\":
                    cursor += 2
                    continue
                if text.startswith(quote, cursor):
                    cursor += len(quote)
                    break
                cursor += 1
            last, index = cursor - 1, cursor
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index, last
        if not char.isspace():
            last = index
        index += 1
    return None


def _parses_as(text, expected):
    import tomllib
    try:
        return tomllib.loads(text) == expected
    except ValueError:
        return False


def _toml_array_append(text, key, value, expected):
    head = re.compile(r"^[ \t]*(?:(?:[A-Za-z0-9_-]+|\"[^\"\n]*\"|'[^'\n]*')[ \t]*\.[ \t]*)*"
                      + _key_pattern(key) + r"[ \t]*=[ \t]*\[", re.M)
    for match in head.finditer(text):
        found = _array_close(text, match.end() - 1)
        if found is None:
            continue
        last = found[1]
        separator = "" if text[last] == "[" else " " if text[last] == "," else ", "
        candidate = text[:last + 1] + separator + json.dumps(value) + text[last + 1:]
        if _parses_as(candidate, expected):
            return candidate
    raise ValueError(f"cannot place {value} in {key}")


def _toml_table_copy(text, server, old, new, expected):
    header = re.compile(r"^[ \t]*\[[ \t]*" + r"[ \t]*\.[ \t]*".join(
        _key_pattern(part) for part in ("mcp_servers", server, "tools", old)) + r"[ \t]*\][ \t]*(?:#[^\n]*)?$", re.M)
    following = re.compile(r"^[ \t]*\[", re.M)
    base = text if not text or text.endswith("\n") else text + "\n"
    for match in header.finditer(text):
        start = min(match.end() + 1, len(text))
        after = following.search(text, start)
        body = text[start:after.start() if after else len(text)].rstrip()
        candidate = (base + "\n" + f"[mcp_servers.{_toml_key(server)}.tools.{_toml_key(new)}]\n"
                     + (body + "\n" if body else ""))
        if _parses_as(candidate, expected):
            return candidate
    raise ValueError(f"cannot copy the {old} tool table")


def _migrate_codex(text, routes, server):
    """Insert the new names as text, so comments and layout survive.

    The edited file must parse to the original document plus exactly the
    added names and tables, or the original text is kept."""
    import tomllib
    config = _mapping(tomllib.loads(text))
    servers = _mapping(config.get("mcp_servers", {}))
    if server not in servers:
        return text, []
    settings = _mapping(servers[server])
    entries = _mapping(settings.get("tools", {}))
    lists = {key: _strings(settings.get(key, [])) for key in ("enabled_tools", "disabled_tools")}
    expected = copy.deepcopy(config)
    target = expected["mcp_servers"][server]
    added, current = [], text
    for key, names in lists.items():
        for old, new in routes.items():
            if old in names and new not in target.get(key, []):
                target[key].append(new)
                current = _toml_array_append(current, key, new, expected)
                added.append((key, new, new))
    for old, new in routes.items():
        if old in entries and new not in entries:
            target["tools"][new] = copy.deepcopy(entries[old])
            current = _toml_table_copy(current, server, old, new, expected)
            added.append(("tools", f"[mcp_servers.{server}.tools.{new}]", new))
    if added and tomllib.loads(current) != expected:
        raise ValueError("the edit changed more than the added names")
    return current, added


def migrate_repository(root, routes, prefix, write=None):
    """Copy each exact old-name rule in the repository's host settings to the new name.

    Returns ``migrated`` (file, category, rule, tool), ``planned`` (repository path
    to new text) and ``refused`` (files left unchanged because they could not
    be read, parsed, edited exactly or written). ``write(rel, text)``
    publishes a file; without it nothing is written. A symlinked file, or one
    resolving outside the checkout, is refused by the contained read.
    """
    root = Path(root).resolve()
    report = {"migrated": [], "planned": {}, "refused": []}
    if not routes:
        return report
    server = prefix.removeprefix("mcp__").removesuffix("__")
    for rel in (CLAUDE_PROJECT, CLAUDE_LOCAL, CODEX_PROJECT):
        try:
            disk = _read(root, rel)
            if disk is None:
                continue
            source = line_endings.to_lf(disk)
            if rel == CODEX_PROJECT:
                result, added = _migrate_codex(source, routes, server)
            else:
                result, added = _migrate_claude(source, rel, routes, prefix)
        except (OSError, ValueError):
            report["refused"].append(rel)
            continue
        if not added:
            continue
        text = line_endings.merge(disk, result)
        if write is not None:
            try:
                write(rel, text)
            except (OSError, RuntimeError, ValueError):
                report["refused"].append(rel)
                continue
        report["planned"][rel] = text
        report["migrated"].extend({"file": rel, "category": category, "rule": rule, "tool": tool}
                                  for category, rule, tool in added)
    return report


def record_verification(root, routes, prefix):
    """Write an upgrade-verification receipt for each route nothing readable still holds.

    A valid existing receipt, operator or upgrade, is left unchanged. Returns
    the verified, already verified and held routes, the recommendations and the
    outside files read."""
    root = Path(root).resolve()
    layers = assess_layers(root, routes, prefix)
    report = {"verified": [], "already_verified": [], "held": {},
              "recommendations": layers["recommendations"], "outside_files": layers["outside_files"]}
    try:
        required = _requires_review(root)
    except (OSError, ValueError):
        required = True
    body = _upgrade_body(layers["outside_files"], layers["managed_override"])
    for old, new in routes.items():
        blocked = layers["repository"].get(new) or layers["outside"].get(new)
        if blocked:
            report["held"][new] = blocked
            continue
        if not required:
            continue
        try:
            current = _read(root, _receipt_path(root, new))
        except (OSError, ValueError):
            current = None
        if _receipt_valid(current):
            report["already_verified"].append(new)
            continue
        try:
            _write_receipt(root, new, body)
        except (OSError, ValueError):
            report["held"][new] = layers["review"].get(new, f"Record the review for {new}.")
            continue
        report["verified"].append(new)
    return report


def setup_pending(root, routes, prefix):
    """Return what setup would change for the renamed spec tools, writing nothing.

    ``migrations`` are the rules setup would copy and ``unverified`` the
    routes it would verify. Routes a readable layer still restricts are in
    neither, because setup cannot change them."""
    root = Path(root).resolve()
    plan = migrate_repository(root, routes, prefix)
    layers = assess_layers(root, routes, prefix, texts=plan["planned"])
    try:
        required = _requires_review(root)
    except (OSError, ValueError):
        required = True
    unverified = []
    if required:
        for new in routes.values():
            if new in layers["repository"] or new in layers["outside"]:
                continue
            try:
                valid = _receipt_valid(_read(root, _receipt_path(root, new)))
            except (OSError, ValueError):
                valid = False
            if not valid:
                unverified.append(new)
    return {"migrations": plan["migrated"], "unverified": unverified}


def report_lines(report):
    """Summary lines for a migration and verification report."""
    lines = [f"Spec-tool rule migrated: {item['file']} {item['category']} {item['rule']}"
             for item in report.get("migrated", [])]
    lines += [f"Spec-tool rule migration skipped: {rel} (unchanged)" for rel in report.get("refused", [])]
    lines += [f"Spec-tool verified: {tool}" for tool in report.get("verified", [])]
    lines += [f"Spec-tool still withheld: {tool}: {remedy}" for tool, remedy in report.get("held", {}).items()]
    lines += [f"Spec-tool recommendation: {text}" for text in report.get("recommendations", [])]
    if lines:
        lines += [f"Spec-tool outside layer: {item['path']} ({item['state']})"
                  for item in report.get("outside_files", [])]
    return lines
