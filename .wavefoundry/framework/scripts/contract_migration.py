"""Preview and apply the move of maintained behavior contracts into architecture."""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote

if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True

import bytecode_cache  # noqa: E402

if __name__ == "__main__":
    bytecode_cache.configure()

from contained_files import (read_contained_bytes, read_contained_identity, unlink_contained,
                             write_contained_bytes)
import line_endings
from path_containment import contained_path

LEGACY = "docs/specs/"
CANONICAL = "docs/architecture/contracts/"
CONFIG = "mkdocs.yml"
LIMIT = 16 * 1024 * 1024
_LINK = re.compile(r"(\]\(<?)([^)<>\n]+?)(>?\))")
_LITERAL = re.compile(r"(`+).*?\1|<!--.*?(?:-->|\Z)", re.S)


def _sha(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True).encode("ascii")


def _read(root, path):
    if contained_path(root, path, refuse_symlink_components=True) is None:
        raise ValueError(f"unsafe path: {path}")
    try:
        (root / path).lstat()
    except FileNotFoundError:
        return None
    return read_contained_bytes(root, path, max_bytes=LIMIT, follow_links=False)


def _unhandled_links(text):
    return re.finditer(
        r"""(?mi)^ {0,3}\[[^\]]+\]:[ \t]*(?P<ref><[^>]*>|[^\s]+)|"""
        r"""<(?:a|img|source)\s[^>]*?(?:href|src)=["'](?P<html>[^"']+)["']|"""
        r"""\]\((?P<titled>[^<>\n]*?)\s+["'][^\n]*?["']\)""", text)


def _files(root, start, skip, *, reject_links=False):
    def fail(error):
        raise error
    for directory, children, names in os.walk(root / start, onerror=fail):
        parent = Path(directory)
        children[:] = sorted(name for name in children if parent / name not in skip)
        if reject_links and any((parent / name).is_symlink() for name in children):
            raise ValueError(f"inspect the linked legacy folder under {parent.relative_to(root)}")
        for name in sorted(names):
            if name.endswith(".md"):
                yield (parent / name).relative_to(root).as_posix()


def _branch_url(root):
    """Only the target repository's current, named branch is mutable."""
    try:
        head = (_read(root, ".git/HEAD") or b"").decode().strip()
        if not head.startswith("ref: refs/heads/"):
            return ""
        config = configparser.RawConfigParser(strict=False)
        config.read_string((_read(root, ".git/config") or b"").decode())
        remote = config.get('remote "origin"', "url", fallback="")
        remote = remote.removesuffix(".git").replace("git@github.com:", "https://github.com/")
        if re.fullmatch(r"https://github\.com/[^/\s]+/[^/\s]+", remote):
            return remote + "/blob/" + head.removeprefix("ref: refs/heads/") + "/"
    except (OSError, ValueError, configparser.Error):
        pass
    return ""


def _rewrite(data, source, destination, moves, branch_url=""):
    """Rebase relative inline Markdown links, retaining fragments and code examples."""
    text = data.decode("utf-8")
    def link(match):
        prefix, href, suffix = match.groups()
        if branch_url and href.startswith(branch_url):
            path, separator, suffix_part = href[len(branch_url):].partition("#")
            if unquote(path) in moves:
                return prefix + branch_url + quote(moves[unquote(path)]) + separator + suffix_part + suffix
        if href.startswith(("#", "/", "?")) or re.match(r"[A-Za-z][\w+.-]*:", href):
            return match[0]
        parts = re.split(r"([?#])", href, maxsplit=1)
        address, fragment = parts[0], "".join(parts[1:])
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(address)))
        if target not in moves and source == destination:
            return match[0]
        replacement = posixpath.relpath(moves.get(target, target), posixpath.dirname(destination))
        return prefix + quote(replacement, safe="/-._~" + (" " if " " in address else "")) + fragment + suffix
    from change_doc_checklist import comment_visible_lines, fenced_line_flags
    lines = text.splitlines(keepends=True)
    visible_lines = comment_visible_lines(lines)
    result = []
    for original, visible, fenced in zip(lines, visible_lines, fenced_line_flags(visible_lines)):
        if fenced:
            result.append(original)
            continue
        # The comment mask preserves offsets. Splice only actual replacements
        # into the original so comments, line endings and code stay intact.
        edits = []
        def collect_links(start, stop):
            for match in _LINK.finditer(visible, start, stop):
                if match[0] == original[match.start():match.end()]:
                    edits.append((match.start(), match.end(), link(match)))
        end = 0
        for literal in _LITERAL.finditer(visible):
            collect_links(end, literal.start())
            value = literal.group()
            if value.startswith("`") and value.endswith("`") and value[1:-1] in moves:
                edits.append((literal.start(), literal.end(), "`" + moves[value[1:-1]] + "`"))
            end = literal.end()
        collect_links(end, len(visible))
        end = 0
        for start, stop, replacement in edits:
            result.extend((original[end:start], replacement))
            end = stop
        result.append(original[end:])
    return "".join(result).encode("utf-8")


def _site(config):
    if config is None:
        return None
    from techdocs_audit_lib import parse_mkdocs, unsupported_patterns
    text = config.decode("utf-8")
    parsed = parse_mkdocs(text)
    patterns = parsed["exclude_docs"]
    if (not parsed["shape_ok"] or patterns is None or unsupported_patterns(patterns)
            or parsed["docs_dir"] != "docs" or parsed["draft_docs_present"]):
        raise ValueError("review the site's publication configuration")
    # Quoted/duplicated YAML keys and composed configurations have additional
    # semantics outside the project-file parser. Preserve those sites in place.
    keys = re.findall(r"""^(?:["']?)([\w<>-]+)(?:["']?)\s*:""", text, re.M)
    if (len(keys) != len(set(keys)) or {"INHERIT", "hooks", "<<", "not_in_nav"}.intersection(keys)
            or re.search(r":\s*[!&*]", text)):
        raise ValueError("review the site's publication configuration")
    # Examine complete root sections; blank lines cannot hide another plugin.
    if "plugins" in keys:
        lines = text.splitlines()
        index = next(i for i, line in enumerate(lines)
                     if re.match(r"""^["']?plugins["']?\s*:""", line))
        if lines[index].strip() != "plugins:":
            raise ValueError("review the site's configured plugins")
        for line in lines[index + 1:]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace() and not line.startswith("-"):
                break
            if line.strip() not in ("- techdocs-core", "- search"):
                raise ValueError("review the site's configured plugins")
    return parsed


def _config_after(data, routes, added):
    if data is None:
        return None
    original = data.decode("utf-8")
    text = line_endings.to_lf(original)
    nav_routes = {old.removeprefix("docs/"): new.removeprefix("docs/") for old, new in routes.items()}
    nav_item = re.compile(r"""^([ \t]*-[ \t]+(?:[^\n:]+:[ \t]+)?["']?)([^"'#\r\n]+?)(["']?[ \t]*(?:#[^\r\n]*)?)(\r?\n)?$""")
    lines = text.splitlines(keepends=True)
    in_nav = False
    for index, line in enumerate(lines):
        if line.strip() and not line.lstrip().startswith("#") and not line.startswith((" ", "\t", "- ")):
            in_nav = bool(re.fullmatch(r"nav:[ \t]*(?:#.*)?", line.rstrip("\r\n")))
            continue
        if in_nav:
            item = nav_item.fullmatch(line)
            if item and item[2] in nav_routes:
                lines[index] = item[1] + nav_routes[item[2]] + item[3] + (item[4] or "")
    text = "".join(lines)
    if added:
        # Require an unambiguous literal block that admits last-match exclusions.
        block = re.compile(r"(?m)^exclude_docs:[ \t]*\|[-+]?[ \t]*\r?\n(?:^[ \t]+[^\n]*\n?)*")
        matches = list(block.finditer(text))
        if len(matches) != 1:
            raise ValueError("use a single literal exclude_docs block or resolve publication manually")
        end = matches[0].end()
        first = matches[0].group().splitlines()[1:]
        indent = next((line[:len(line)-len(line.lstrip())] for line in first if line.strip()), "  ")
        extra = ("" if text[:end].endswith("\n") else "\n")
        extra += "".join(indent + rule + "\n" for rule in added)
        text = text[:end] + extra + text[end:]
    return line_endings.encode(line_endings.merge(original, text))


def recovery(root, digest=None):
    from setup_commands import format_command
    argv = [sys.executable, str(root / ".wavefoundry/framework/scripts/upgrade_wavefoundry.py"),
            "contracts", "--root", str(root)]
    if digest:
        argv.extend(["--apply", digest])
    return format_command(argv)


def remaining(root):
    legacy = root / LEGACY
    if not os.path.lexists(legacy):
        return []
    if contained_path(root, legacy, refuse_symlink_components=True) is None:
        raise ValueError("legacy collection is a link")
    return list(_files(root, LEGACY, {legacy / "changes"}, reject_links=True))


def _maintained(root):
    from record_paths import load_record_roots
    from memory_records import MEMORY_DIR, MEMORY_ARCHIVE_MANIFEST
    from history_paths import is_history_path
    layout = load_record_roots(root)
    excluded_dirs = {layout.waves, layout.plans, root / "docs/reports", root / LEGACY / "changes",
                     root / "docs/architecture/decisions", root / "docs/agents/history", root / MEMORY_DIR}
    if layout.archive:
        excluded_dirs.add(layout.archive)
    maintained = list(_files(root, "docs", excluded_dirs))
    maintained.extend(name for name in ("README.md", "AGENTS.md") if (root / name).is_file())
    return [p for p in maintained if p != MEMORY_ARCHIVE_MANIFEST and not is_history_path(p)]


def _unresolved_references(data, path, legacy_uris, branch_url):
    deferred = {}
    for match in _unhandled_links(data):
        href = next(value for value in match.groups() if value is not None).strip("<>")
        address = unquote(re.split(r"[?#]", href, maxsplit=1)[0])
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(path), address))
        if rel in legacy_uris:
            deferred[rel] = f"resolve the reference in {path} before moving"
    if not branch_url:
        for ref in re.finditer(r"/blob/[^()\s]+?/(docs/specs/[^()#?\s]+)", data):
            if unquote(ref[1]) in legacy_uris:
                deferred[unquote(ref[1])] = f"confirm the repository URL and branch in {path}"
    return deferred


def preview(root, publish=()):
    from techdocs_audit_lib import excluded
    root = root.resolve()
    moves, deferred, additions, exposure = {}, {}, [], []
    branch_url = _branch_url(root)
    files = remaining(root)
    unknown = set(publish).difference(files)
    if unknown:
        raise ValueError("unknown selected contract: " + ", ".join(sorted(unknown)))
    config = _read(root, CONFIG)
    try:
        site = _site(config)
        if site is None and any((root / name).exists() for name in ("mkdocs.yaml", "catalog-info.yaml")):
            raise ValueError("establish the effective site configuration")
    except ValueError as error:
        return {"moves": {}, "deferred": {p: str(error) for p in files}, "actions": [],
                "exposure": [], "rules": [], "dependencies": {CONFIG: _sha(config)}}
    maintained = _maintained(root) if files else []
    legacy_uris = set(files)
    for path in maintained:
        data = _read(root, path).decode("utf-8")
        deferred.update(_unresolved_references(data, path, legacy_uris, branch_url))
    for source in files:
        if source in deferred:
            continue
        target = CANONICAL + source[len(LEGACY):]
        try:
            if not re.fullmatch(r"[A-Za-z0-9_./ -]+", source) or _read(root, target) is not None:
                raise ValueError("destination exists or the path needs manual review")
            content = _read(root, source).decode("utf-8")
            if (next(_unhandled_links(content), None) is not None
                    or re.search(r"\]\([^\n]*\([^\n]*\)", content)):
                raise ValueError("review reference, titled, nested or HTML links before moving")
            dest_path = Path(target)
            if dest_path.name.casefold() in ("index.md", "readme.md"):
                other = "README.md" if dest_path.name.casefold() == "index.md" else "index.md"
                aliases = [dest_path.parent.with_name(dest_path.parent.name + ".md"), dest_path.with_name(other)]
            else:
                aliases = [dest_path.with_suffix("") / "index.md", dest_path.with_suffix("") / "README.md"]
            if site and any((root / alias).is_file() or
                            LEGACY + alias.as_posix()[len(CANONICAL):] in files for alias in aliases):
                raise ValueError("another page may generate the same site URL")
            if site:
                if source[5:] in site["nav"]:
                    edited = _config_after(config, {source: target}, [])
                    expected = [target[5:] if page == source[5:] else page for page in site["nav"]]
                    if _site(edited)["nav"] != expected:
                        raise ValueError("maintained navigation needs a manual link update")
                old = excluded(source[5:], site["exclude_docs"])
                new = excluded(target[5:], site["exclude_docs"])
                if old != new:
                    exposure.append({"source": source, "destination": target,
                                     "currently_published": not old, "would_publish": not new})
                publish_target = source in publish or not old
                if publish_target == new:
                    rule = (("!/" if publish_target else "/") + target[5:])
                    candidate = _config_after(config, {}, additions + [rule])
                    if excluded(target[5:], _site(candidate)["exclude_docs"]) == publish_target:
                        raise ValueError("exclusion precedence needs manual review")
                    additions.append(rule)
            moves[source] = target
        except (OSError, ValueError) as error:
            deferred[source] = str(error)
    dependencies = {CONFIG: _sha(config)}
    if config is None:
        for alternate in ("mkdocs.yaml", "catalog-info.yaml"):
            dependencies[alternate] = None
    actions = []
    def action(kind, source, dest, before, after):
        actions.append(dict(kind=kind, source=source, path=dest, before=_sha(before), after=_sha(after)))
    adjusted = _config_after(config, moves, additions)
    if config != adjusted:
        action("config", CONFIG, CONFIG, config, adjusted)
    for source, dest in moves.items():
        body = _read(root, source)
        dependencies[source] = _sha(body)
        action("copy", source, dest, None, _rewrite(body, source, dest, moves, branch_url))
    if moves:
        for path in sorted(set(maintained).difference(moves)):
            data = _read(root, path)
            rewritten = _rewrite(data, path, path, moves, branch_url)
            if data != rewritten:
                action("links", path, path, data, rewritten)
    # Keep originals working until configuration, copies and referrers are durable.
    for source in moves:
        action("retire", source, source, _read(root, source), None)
    return {"branch_url": branch_url, "publish": sorted(set(publish)), "moves": moves, "deferred": deferred, "actions": actions,
            "exposure": exposure, "rules": additions, "dependencies": dependencies}


def _receipt(digest):
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("expected a complete preview digest")
    return f".wavefoundry/logs/contracts-{digest}.preview.log"


def save_preview(root, plan):
    data = _json(plan)
    digest = _sha(data)
    path = _receipt(digest)
    prior = _read(root, path)
    if prior is None:
        from render_agent_surfaces import _write_bytes_atomic_exclusive
        _write_bytes_atomic_exclusive(root / path, data, root=root, mode=0o600)
    elif prior != data:
        raise ValueError("preview log changed")
    return digest


def _validate_receipt(plan):
    """Limit diagnostic receipts to the owned migration operations on replay."""
    moves = plan["moves"]
    for src, dest in moves.items():
        if (not src.startswith(LEGACY) or not src.endswith(".md") or ".." in Path(src).parts
                or src.startswith(LEGACY + "changes/") or dest != CANONICAL + src[len(LEGACY):]):
            raise ValueError("invalid migration move")
    for row in plan["actions"]:
        kind, src, dest = row["kind"], row["source"], row["path"]
        if kind == "copy":
            valid = moves.get(src) == dest and row["before"] is None
        elif kind == "retire":
            valid = src in moves and src == dest and row["after"] is None
        elif kind == "config":
            valid = src == dest == CONFIG
        else:
            valid = (kind == "links" and src == dest and ".." not in Path(src).parts
                     and (src in ("README.md", "AGENTS.md") or src.startswith("docs/") and src.endswith(".md")))
        if not valid:
            raise ValueError("invalid migration action")


def apply(root, digest):
    from lifecycle_lock import lifecycle_mutation_lock
    raw = _read(root, _receipt(digest))
    if _sha(raw) != digest:
        raise ValueError("preview missing or changed; run preview again")
    plan = json.loads(raw)
    _validate_receipt(plan)
    with lifecycle_mutation_lock(root):
        initial = dict(plan["dependencies"])
        for row in plan["actions"]:
            initial.setdefault(row["path"], row["before"])
        # Recognize only an exact prefix of the reviewed writes on resume.
        actual = {p: _sha(_read(root, p)) for p in initial}
        state, start = dict(initial), None
        if state == actual:
            start = 0
        for i, row in enumerate(plan["actions"], 1):
            state[row["path"]] = row["after"]
            if state == actual:
                start = i
        if start == 0 and preview(root, plan.get("publish", [])) != plan:
            raise ValueError("the scope of the preview changed; run preview again")
        if start is None:
            raise ValueError("a reviewed input changed; run preview again")
        if plan.get("branch_url", "") != _branch_url(root):
            raise ValueError("repository branch changed; run preview again")
        if start and start < len(plan["actions"]):
            # The recipient may have created a new incoming link while the
            # process was stopped. It was outside the approved edit list.
            for rel in set(_maintained(root)).difference(initial):
                data = _read(root, rel)
                if (_unresolved_references(data.decode("utf-8"), rel, plan["moves"], plan["branch_url"])
                        or _rewrite(data, rel, rel, plan["moves"], plan["branch_url"]) != data):
                    raise ValueError(f"new reference in {rel}; run preview again")
        state = actual
        for row in plan["actions"][start:]:
            expected_sources = set(plan["deferred"]).union(
                p for p in plan["moves"] if state[p] is not None)
            if set(remaining(root)) != expected_sources:
                raise ValueError("legacy collection changed; run preview again")
            for p, expected in state.items():
                if _sha(_read(root, p)) != expected:
                    raise ValueError(f"{p} changed; run preview again")
            p, src, kind = row["path"], row["source"], row["kind"]
            data, entry, resolved = read_contained_identity(root, src, max_bytes=LIMIT, follow_links=False)
            if _sha(data) != state[src]:
                raise ValueError(f"{src} changed; run preview again")
            identity = (entry.st_dev, entry.st_ino)
            if kind == "retire":
                unlink_contained(root, resolved, expected_identity=identity)
            else:
                if kind == "config":
                    data = _config_after(data, plan["moves"], plan["rules"])
                else:
                    data = _rewrite(data, src, p, plan["moves"], plan["branch_url"])
                if _sha(data) != row["after"]:
                    raise ValueError(f"{src} changed; run preview again")
                permissions = entry.st_mode & 0o777
                if kind == "copy":
                    from render_agent_surfaces import _write_bytes_atomic_exclusive
                    _write_bytes_atomic_exclusive(root / p, data, root=root, mode=permissions)
                else:
                    write_contained_bytes(root, p, data, mode=permissions, no_links=True, expected_identity=identity)
            state[p] = row["after"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--publish", action="append", default=[], metavar="LEGACY_PATH")
    parser.add_argument("--apply", metavar="PREVIEW_DIGEST")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.apply:
            if args.publish:
                parser.error("select publication when creating the preview")
            apply(root, args.apply)
            print("Applied the reviewed contract migration.")
        else:
            plan = preview(root, args.publish)
            print(json.dumps(plan, indent=2))
            if plan["actions"]:
                digest = save_preview(root, plan)
                print("Apply or resume: " + recovery(root, digest))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Contract migration deferred: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
