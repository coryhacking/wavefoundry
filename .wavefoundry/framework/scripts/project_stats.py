#!/usr/bin/env python3
"""Read-only project figures shared by the CLI and MCP statistics surfaces."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__" or sys.pycache_prefix is None:
    sys.dont_write_bytecode = True

if __name__ == "__main__":
    import bytecode_cache
    bytecode_cache.configure(read_only=True)

SECTIONS = ("code", "todo", "lifecycle", "documents", "memories", "index", "token_savings", "secrets")
COUNT_KEYS = ("files", "total_lines", "blank_lines", "comment_lines", "code_lines")
# Language categories are disjoint; Markdown extensions are added from chunker.
CATEGORY_LANGUAGES = {
    "documentation": {".txt", ".rst", ".adoc"},
    "data": {"json", "yaml", "toml", "xml", "jupyter", ".csv", ".tsv", ".ini", ".cfg", ".properties", ".lock"},
}
# Deliberately lexical, not a programming-language parser.
COMMENT_SYNTAX = {
    **{lang: (("#",), ()) for lang in ("python", "ruby", "shell", "fish", "yaml", "toml", "terraform", "hcl", "helm")},
    **{lang: (("//",), (("/*", "*/"),)) for lang in ("javascript", "typescript", "java", "go", "rust", "csharp", "cpp", "c", "kotlin", "groovy", "scala", "swift")},
    "css": ((), (("/*", "*/"),)), "scss": (("//",), (("/*", "*/"),)),
    "sql": (("--",), (("/*", "*/"),)),
    "html": ((), (("<!--", "-->"),)), "xml": ((), (("<!--", "-->"),)),
    "powershell": (("#",), (("<#", "#>"),)),
}
TEST_SUFFIXES = (
    "_test.go", *(f".{kind}.{ext}" for kind in ("test", "spec") for ext in ("js", "jsx", "ts", "tsx", "mjs", "cjs")),
    "Test.java", "Tests.java", "Test.kt", "Tests.cs", "Tests.swift", "_spec.rb", "_test.rb",
)
LEXICAL_NOTE = "Line counts are lexical: a comment delimiter inside a string literal counts as a comment; unknown comment syntax is null and code lines then mean nonblank lines."
TEST_NOTE = "Test code uses the indexer's test/test(s)/__tests__ directories and test_/_test.py names, plus case-sensitive Go, JS/TS test/spec, Java/Kotlin/C#/Swift Test(s), and Ruby test/spec suffixes with non-empty stems. This is not test coverage."
SCOPE_NOTE = "File scope follows indexer.walk_repo exclusions and ignore rules, then project index exclusions with configured docs/code opt-ins; no seed fold or test exclusion is added."


def _unavailable(reason: str, **extra: Any) -> dict:
    return {"available": False, "reason": reason, **extra}


def _counts(known: bool = True) -> dict:
    return {key: (None if key == "comment_lines" and not known else 0) for key in COUNT_KEYS}


def _add_counts(target: dict, source: dict) -> None:
    for key in COUNT_KEYS:
        target[key] = None if target[key] is None or source[key] is None else target[key] + source[key]


def _line_kinds(text: str, language: str) -> list[str]:
    syntax = COMMENT_SYNTAX.get(language)
    kinds = []
    block_end = None
    for line in text.splitlines():
        if not line.strip():
            kinds.append("blank_lines")
            continue
        comment = False
        pos = 0
        if syntax:
            lines, blocks = syntax
            while pos < len(line):
                if block_end:
                    comment = True
                    end = line.find(block_end, pos)
                    if end < 0:
                        break
                    pos = end + len(block_end)
                    block_end = None
                    continue
                candidates = [(line.find(token, pos), token, None) for token in lines]
                candidates += [(line.find(start, pos), start, end) for start, end in blocks]
                candidates = [item for item in candidates if item[0] >= 0]
                if not candidates:
                    break
                start, token, end = min(candidates)
                comment = True
                if end is None:
                    break
                block_end = end
                pos = start + len(token)
        if comment:
            kinds.append("comment_lines")
        else:
            kinds.append("code_lines")
    return kinds



def _count_kinds(kinds: list[str], known: bool, *, files: int = 1) -> dict:
    out = _counts(known)
    out["files"] = files
    out["total_lines"] = len(kinds)
    for kind in kinds:
        out[kind] += 1
    return out


def _line_counts(text: str, language: str) -> dict:
    return _count_kinds(_line_kinds(text, language), language in COMMENT_SYNTAX)


def _files(root: Path) -> tuple[list, dict]:
    import indexer
    import chunker
    dirs: set[str] = set()
    failures: set[str] = set()
    observations: dict[str, dict] = {}
    candidates = indexer.walk_repo(root, unreadable_dirs=dirs, unreadable_files=failures, observations=observations)
    prefixes = indexer._merged_project_include_prefixes_for_graph(root, ())
    eligible = indexer._filter_project_index_excludes(candidates, root, (), project_include_prefixes=prefixes)
    for path in set(candidates) - set(eligible):
        indexer.record_walk_observation(observations, "policy_excluded_files", path.relative_to(root).as_posix())
    candidates = eligible
    rows, binary, read_failures = [], 0, 0
    docs = CATEGORY_LANGUAGES["documentation"] | set(chunker.MARKDOWN_EXTENSIONS)
    for path in sorted(candidates):
        try:
            raw = path.read_bytes()
        except OSError:
            read_failures += 1
            indexer.record_walk_observation(observations, "unreadable_files", path.relative_to(root).as_posix())
            continue
        if b"\0" in raw[:8192]:
            binary += 1
            indexer.record_walk_observation(observations, "binary_files", path.relative_to(root).as_posix())
            continue
        ext = path.suffix.lower()
        lang = chunker._EXT_TO_LANGUAGE.get(ext, ext or "extensionless")
        category = "documentation" if ext in docs else "data" if lang in CATEGORY_LANGUAGES["data"] else "code"
        rel = path.relative_to(root).as_posix()
        is_test = category == "code" and (indexer._is_test_code_path(rel) or any(path.name.endswith(s) and len(path.name) > len(s) for s in TEST_SUFFIXES))
        rows.append((rel, lang, category, is_test, raw.decode("utf-8", errors="replace")))
    meta = {"skip_reasons": dict(sorted(observations.items())),
            "exclusion_note": "Counts name observed files or pruned directories; descendants of pruned directories were not visited or counted. Examples are the first 10 sorted relative paths per reason.",
            "scope": SCOPE_NOTE, "max_file_bytes": indexer._resolve_max_file_bytes(root),
            "size_cap_note": "indexing.max_file_bytes; zero disables the cap.",
            "binary_files": binary, "binary_note": "Binary candidates detected, not a repository-wide binary census.",
            "unreadable_directories": len(dirs), "unreadable_files": len(failures) + read_failures}
    return rows, meta


def _path_roles(root: Path) -> list[tuple[str, str]]:
    from pathlib import PurePosixPath, PureWindowsPath
    try:
        profile = json.loads((root / "docs/repo-profile.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError, UnicodeError):
        raise ValueError("statistics_configuration_invalid") from None
    if not isinstance(profile, dict) or not isinstance(profile.get("statistics", {}), dict):
        raise ValueError("statistics_configuration_invalid")
    rows = profile.get("statistics", {}).get("path_roles", [])
    if not isinstance(rows, list):
        raise ValueError("statistics_configuration_invalid")
    normalized = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "role"}:
            raise ValueError("statistics_configuration_invalid")
        path, role = row["path"], row["role"]
        if (not isinstance(path, str) or not path or not all(c.isprintable() for c in path)
                or "\\" in path or PurePosixPath(path).is_absolute() or PureWindowsPath(path).drive
                or ".." in path.split("/") or not isinstance(role, str) or role not in {"shipped", "tooling", "test", "evidence", "generated"}):
            raise ValueError("statistics_configuration_invalid")
        clean = str(PurePosixPath(path))
        if clean == ".":
            raise ValueError("statistics_configuration_invalid")
        clean += "/" if path.endswith("/") else ""
        if clean in normalized and normalized[clean] != role:
            raise ValueError("statistics_configuration_invalid")
        normalized[clean] = role
    return sorted(normalized.items(), key=lambda pair: (-len(pair[0]), pair[0]))


def _rust_test_lines(text: str) -> tuple[set[int], str]:
    """Recognize syntax spans only, never expand macros or evaluate cfg expressions."""
    import indexer
    # Share the loaded index runtime and parser; changes require its host restart.
    tree = indexer._get_graph_indexer()._ts_parse("rust", text)
    if tree is None:
        return set(), "parser_unavailable_or_limit"
    if tree.root_node.has_error:
        return set(), "parse_error"
    source = text.encode("utf-8", errors="replace")
    selected: set[int] = set()
    unsupported = False
    pending_nodes = [tree.root_node]
    while pending_nodes:
        parent = pending_nodes.pop()
        attributes = []
        for node in parent.named_children:
            if node.type in {"attribute_item", "inner_attribute_item"}:
                value = b"".join(source[node.start_byte:node.end_byte].split())
                conditional = value.startswith((b"#[cfg(", b"#[cfg_attr(", b"#![cfg(", b"#![cfg_attr("))
                if conditional and value != b"#[cfg(test)]":
                    unsupported = True
                attributes.append((node, value))
                continue
            if node.type in {"line_comment", "block_comment"}:
                continue
            if attributes:
                is_test = any(value == b"#[cfg(test)]" or value == b"#[test]" and node.type == "function_item" for _, value in attributes)
                if is_test:
                    first = attributes[0][0].start_point.row
                    last = node.end_point.row + (node.end_point.column > 0)
                    selected.update(range(first, last))
                attributes = []
            pending_nodes.append(node)
    # Unsupported cfg may change which items exist. Keep labelled path-only
    # fallback rather than guessing an effective total from a partial tree.
    return (set(), "unsupported_conditional") if unsupported else (selected, "supported_syntax")


def _code(rows: list, meta: dict, roles: list[tuple[str, str]] | None = None, *, group_by: str | None = None) -> dict:
    languages: dict[str, dict] = {}
    categories = {key: {"both": _counts(), **({"production": _counts(), "test": _counts()} if key == "code" else {})} for key in ("code", "documentation", "data")}
    role_totals: dict[str, dict] = {}
    directories: dict[tuple[str, str], dict] = {}
    inline_status: Counter = Counter()
    partial = []
    unmatched = 0

    def add_effective(target: dict, counts: dict, test: dict, non_test: dict) -> None:
        for key, value in (("effective_test", test), ("effective_non_test", non_test)):
            _add_counts(target.setdefault(key, _counts(value["comment_lines"] is not None)), value)
        target["mixed_test_files"] = target.get("mixed_test_files", 0) + bool(test["files"] and non_test["files"])

    for rel, lang, category, is_test, text in rows:
        known = lang in COMMENT_SYNTAX
        kinds = _line_kinds(text, lang)
        counts = _count_kinds(kinds, known)
        role = next((role for path, role in roles or [] if rel == path or path.endswith("/") and rel.startswith(path)), None)
        configured = role is not None
        unmatched += not configured
        role = role or ("test" if is_test else "non_test")
        role_row = role_totals.setdefault(role, {"both": _counts(known), "configured_files": 0, "inferred_files": 0})
        role_row["configured_files" if configured else "inferred_files"] += 1
        _add_counts(role_row["both"], counts)
        row = languages.setdefault(lang, {"category": category, "both": _counts(known), **({"production": _counts(known), "test": _counts(known)} if category == "code" else {})})
        _add_counts(row["both"], counts)
        _add_counts(categories[category]["both"], counts)
        directory = rel.split("/", 1)[0] if "/" in rel else "."
        directory_row = None
        if group_by == "directory":
            directory_row = directories.setdefault((directory, lang), {"directory": directory, "language": lang, "category": category, "both": _counts(known), "roles": {}})
            _add_counts(directory_row["both"], counts)
            _add_counts(directory_row["roles"].setdefault(role, _counts(known)), counts)
        if category == "code":
            key = "test" if is_test else "production"
            _add_counts(row[key], counts)
            _add_counts(categories[category][key], counts)
            test_lines = set(range(len(kinds))) if is_test or role == "test" else set()
            if lang == "rust" and not (is_test or role == "test"):
                test_lines, status = _rust_test_lines(text)
                inline_status[status] += 1
                if status != "supported_syntax":
                    partial.append({"path": rel, "reason": status})
            test = _count_kinds([kind for n, kind in enumerate(kinds) if n in test_lines], known, files=int(bool(test_lines) or is_test or role == "test"))
            non_test = _count_kinds([kind for n, kind in enumerate(kinds) if n not in test_lines], known, files=int(len(test_lines) < len(kinds) or not kinds and not (is_test or role == "test")))
            for target in (row, categories[category], role_row, *([directory_row] if directory_row is not None else [])):
                add_effective(target, counts, test, non_test)
    for row in [*languages.values(), categories["code"], *role_totals.values(), *directories.values()]:
        if "test" in row:
            row["test_code_ratio"] = row["test"]["code_lines"] / row["both"]["code_lines"] if row["both"]["code_lines"] else 0.0
        if "effective_test" in row:
            denominator = row["effective_test"]["code_lines"] + row["effective_non_test"]["code_lines"]
            row["effective_test_code_ratio"] = row["effective_test"]["code_lines"] / denominator if denominator else 0.0
    result = {"available": True, "complete": True, "languages": dict(sorted(languages.items())), "categories": categories, **meta,
              "roles": dict(sorted(role_totals.items())), "unmatched_role_files": unmatched,
              "role_note": "Roles describe configured path responsibility, not packaged binaries. Evidence/generated stay in eligible file totals; mappings cannot restore excluded files. Test extent is separate from role.",
              "legacy_note": "production, test and test_code_ratio retain legacy path-only meanings. Effective counts include explicit test roles and supported Rust syntax. Mixed test/non-test file counts overlap; combined files are unique. Test share is not test coverage.",
              "inline_analysis": {"status": "partial" if partial else "supported_syntax", "by_status": dict(sorted(inline_status.items())), "fallback_files": partial[:10], "omitted": max(0, len(partial) - 10),
                                  "note": "Unsupported/unavailable Rust analysis uses path-only fallback; effective totals are then partial estimates. Macros are not expanded and hidden test semantics cannot be detected. Swift nonstandard test targets require explicit test roles; build manifests are never executed."},
              "counting_note": LEXICAL_NOTE, "test_rule": TEST_NOTE}
    if group_by == "directory":
        result["directories"] = [directories[key] for key in sorted(directories)]
    return result


def _todo(rows: list, meta: dict) -> dict:
    counts = Counter({key: 0 for key in ("TODO", "FIXME", "HACK", "XXX")})
    files = []
    for rel, _, category, _, text in rows:
        if category != "code":
            continue
        found = Counter(re.findall(r"\b(?:TODO|FIXME|HACK|XXX)\b", text))
        counts.update(found)
        if found:
            files.append({"path": rel, "count": sum(found.values())})
    return {"available": True, "complete": True, "by_marker": dict(counts), "total": sum(counts.values()), "top_files": sorted(files, key=lambda r: (-r["count"], r["path"]))[:10], **meta}


def _by(rows: list, field: str) -> dict:
    return dict(sorted(Counter(str(row.get(field) or "unknown").lower() for row in rows).items()))


def _lifecycle(waves: list, changes: dict) -> dict:
    import dashboard_lib
    all_changes = changes["wave"] + changes["plan"]
    progress = dashboard_lib.collect_progress(waves, changes)
    import vocabulary_profile as vp
    terminal = sorted(dashboard_lib._lint_constants().DONE_CHANGE_STATUSES)
    work = []
    for wave in sorted(waves, key=lambda row: row["wave_id"]):
        if str(wave.get("status") or "").lower() not in {"active", "implementing", "paused"}:
            continue
        members = [c for c in changes["wave"] if c.get("admitted_wave_id", c.get("wave_id")) == wave["wave_id"]]
        per_wave = dashboard_lib.collect_progress([wave], {"wave": members})
        work.append({"wave_id": wave["wave_id"], "status": wave.get("status"),
                     **{key: per_wave[key] for key in ("criteria", "tasks", "coverage")}})
    completion_rule = (f"{vp.CONTAINER_NAME_PLURAL} count as done at closed/completed. "
                       f"All admitted {vp.ITEM_NAME_PLURAL.lower()} in those {vp.CONTAINER_NAME_PLURAL.lower()} contribute to done; "
                       f"elsewhere, member statuses {', '.join(terminal)} count as done. "
                       "Acceptance criteria and implementation tasks always count their literal checkbox marks, independently of record status.")
    unadmitted = dashboard_lib.collect_checklist_counts(changes["plan"])
    unadmitted_unreadable = sum(bool(c.get("read_error")) for c in changes["plan"])
    unadmitted["coverage"] = {
        "complete": not unadmitted_unreadable,
        "unreadable_change_documents": unadmitted_unreadable,
        "warning": "Checklist coverage is incomplete; counts include only readable unadmitted plans." if unadmitted_unreadable else None,
    }
    return {"available": True, "waves": {"total": len(waves), "by_status": _by(waves, "status")},
            "changes": {key: {"total": len(changes[key]), "by_kind": _by(changes[key], "kind"), "by_status": _by(changes[key], "status")} for key in ("wave", "plan")},
            "completion_rule": completion_rule, "open_work_by_wave": work,
            "progress": progress, "raw_checkboxes": {group: progress[group] for group in ("criteria", "tasks")},
            "unadmitted_checkboxes": unadmitted,
            "missing_admitted_documents": progress["coverage"]["missing_admitted_documents"],
            "unreadable_change_documents": sum(bool(c.get("read_error")) for c in all_changes),
            "progress_note": "Dashboard Progress and checklist counts share all assigned documents: total = done + deferred + open. Not-this-scope criteria and unassigned plans are separate. Lifecycle rows describe record status. Unreadable-document totals cover assigned documents and unassigned plans; Progress coverage covers assigned documents only. Dashboard metric tiles retain their separate active scope."}


def _document_count(path: Path, adr_only: bool = False) -> int:
    import os
    if not path.exists():
        return 0
    def fail(error):
        raise error
    count = 0
    for _, _, names in os.walk(path, onerror=fail, followlinks=False):
        count += sum(name.endswith(".md") and (not adr_only or re.match(r"^[0-9a-z]+-adr(?:[ .-]|$)", name) is not None) for name in names)
    return count


def _documents(root: Path) -> dict:
    import dashboard_lib
    roles = dashboard_lib.collect_agents(root)
    manifest = dashboard_lib.read_prompt_manifest(root)
    prompts = manifest.get("public_prompt_surface", [])
    return {"available": True, "specifications": _document_count(root / "docs/specs"), "architecture": _document_count(root / "docs/architecture"),
            "decisions": _document_count(root / "docs/architecture/decisions", True), "agents": {"total": len(roles), "by_category": _by(roles, "category")},
            "public_prompts": len(prompts) if isinstance(prompts, list) else 0}


def _memories(root: Path) -> dict:
    from memory_records import load_memory_records
    records = load_memory_records(root)
    return {"available": True, "total": len(records), "by_status": _by(records, "status"), "active_by_kind": _by([r for r in records if r.get("status") == "active"], "kind"), "archive_note": "Archived bodies are counted once; the archive register is not added.", "candidate_records_awaiting_validation": sum(r.get("status") == "candidate" for r in records), "population_note": "Counts are parseable persisted memory records, not unwritten proposals, backfill candidates or pending transitions. The shared loader omits malformed/unreadable records; these counts do not establish complete record coverage."}


def _index(root: Path) -> dict:
    from index_state_store import state_store_path
    import dashboard_lib
    directory = root / ".wavefoundry/index"
    if not state_store_path(directory).is_file():
        return _unavailable("store_absent")
    state = directory / "index-build.json"
    try:
        raw = state.read_text(encoding="utf-8")
    except FileNotFoundError:
        pass
    except (OSError, UnicodeError):
        return _unavailable("build_state_unreadable")
    else:
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return _unavailable("build_state_invalid")
        except ValueError:
            return _unavailable("build_state_invalid")
    health = dashboard_lib.collect_health(root, 0, {"wave": [], "plan": []})
    embedding = health["index"]["project"]
    if not embedding.get("present") or embedding.get("diagnostic"):
        return _unavailable(str(embedding.get("diagnostic") or "index_not_present"))
    graph = health["graph"]["project"]
    lexical = health["lexical"]["project"]
    counts = graph.get("counts") or {}
    return {"available": True,
            "embedding": {k: embedding.get(k) for k in ("files_indexed", "doc_chunks", "code_chunks", "built_at", "model", "docs_model", "code_model")},
            "lexical": {k: lexical.get(k) for k in ("status", "entries", "term_occurrences", "distinct_terms", "reason") if k in lexical},
            "graph": {"present": graph.get("present", False), "nodes": counts.get("nodes", 0), "edges": counts.get("edges", 0), "clusters": (graph.get("clusters") or {}).get("community_count", 0), "generation": graph.get("generation"), "built_at": graph.get("generated_at")},
            "scope_note": "files_indexed is the index's file set, not the code section's file set. Use index_health for freshness and integrity verdicts."}


def _token_savings(root: Path, waves: list, *, include_wave_details: bool = False) -> dict:
    import context_efficiency as ce
    import vocabulary_profile as vp
    totals = dict(ce.empty_checkpoint()["totals"])
    stages: dict[str, dict] = {}
    statuses: Counter = Counter()
    excluded, marked, missing, pending = [], 0, 0, 0
    details = []
    for wave in waves:
        path = root / wave["path"]
        path = path.parent / vp.RECORD_FILENAME
        state = ce.parse_checkpoint_block(path.read_text(encoding="utf-8"))
        if state is None:
            missing += 1
            if include_wave_details:
                details.append({"wave_id": wave["wave_id"], "measurement_status": "missing", "included": False})
            continue
        marked += 1
        status = state["measurement_status"]
        statuses[status] += 1
        pending += bool(state["pending"])
        if include_wave_details:
            detail = {"wave_id": wave["wave_id"], "measurement_status": status,
                      "pending": bool(state["pending"]), "included": status == "healthy"}
            if status == "healthy":
                detail.update(estimated_totals=dict(state["totals"]), estimated_stages=state["stages"])
            details.append(detail)
        if status != "healthy":
            excluded.append({"wave_id": wave["wave_id"], "measurement_status": status})
            continue
        for key, value in state["totals"].items():
            totals[key] = totals.get(key, 0) + value
        for stage, values in state["stages"].items():
            target = stages.setdefault(stage, {})
            for key, value in values.items():
                target[key] = target.get(key, 0) + value
    result = {"available": True, "measurement": "estimates", "estimated_totals": totals, "estimated_stages": stages, "records_with_marker": marked, "records_without_marker": missing, "by_measurement_status": dict(sorted(statuses.items())), "pending_markers": pending, "excluded_records": excluded, "limitation": ce._CHECKPOINT_ESTIMATE_NOTE}
    result["paired_evaluation_count"] = totals["paired_evaluation_count"]
    result["paired_evaluation_note"] = "No paired evaluations recorded" if not totals["paired_evaluation_count"] else "Paired evaluations are recorded; this total remains an accounting estimate."
    result["debit_note"] = "Request and response debits are recorded accounting estimates, not total model consumption, reasoning tokens or billing."
    if include_wave_details:
        result["wave_details"] = sorted(details, key=lambda row: row["wave_id"])
    return result


def _secret_findings(root: Path) -> dict:
    path = root / "docs/scan-findings.json"
    statuses = ("false-positive", "confirmed-secret", "suspected-secret", "pending", "unclassified")
    out = {"available": True, "total": 0, "by_status": dict.fromkeys(statuses, 0), "by_rule": {}, "false_positive_confirmations": dict.fromkeys(("0", "1", "2", "3+"), 0), "false_positive_overrides": 0, "modified_at": None, "policy_note": "Counts do not establish confirmation policy compliance; docs-lint remains its authority. No scan was run."}
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        modified = path.stat().st_mtime
    except FileNotFoundError:
        out["note"] = "No scan has recorded findings."
        return out
    except (OSError, UnicodeError, ValueError):
        return _unavailable("findings_unreadable_or_invalid")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        return _unavailable("findings_invalid_shape")
    for entry in entries:
        status = entry.get("status", "pending")
        status = status if isinstance(status, str) and status in statuses else "unclassified"
        rule = entry.get("rule_id", "unknown")
        if not isinstance(rule, str):
            rule = "unknown"
        out["total"] += 1
        out["by_status"][status] += 1
        out["by_rule"].setdefault(rule, dict.fromkeys(statuses, 0))[status] += 1
        if status == "false-positive":
            confirmations = entry.get("confirmations")
            identities = {c["git_user_email"] for c in confirmations if isinstance(c, dict) and isinstance(c.get("git_user_email"), str) and c["git_user_email"]} if isinstance(confirmations, list) else set()
            out["false_positive_confirmations"][str(len(identities)) if len(identities) < 3 else "3+"] += 1
            out["false_positive_overrides"] += bool(entry.get("override_reason"))
    out["by_rule"] = dict(sorted(out["by_rule"].items()))
    out["modified_at"] = datetime.fromtimestamp(modified, timezone.utc).isoformat()
    return out


def _scan_health(root: Path) -> dict:
    import scanner_skips
    history = scanner_skips.scan_history(root)
    notice = scanner_skips.scanner_skip_notice(root)
    if "scanner_skips_error" in notice:
        outstanding = _unavailable("coverage_unreadable_or_invalid")
    elif not (root / scanner_skips.LEDGER_REL).is_file():
        outstanding = _unavailable("coverage_not_recorded")
    else:
        reasons: dict[str, set[str]] = {}
        known = set(scanner_skips.INTENTIONAL_SKIP_REASONS) | set(scanner_skips.FIXED_LIMIT_REASONS) | {"upstream scan incomplete", "input unreadable", "record read refused"}
        for row in notice.get("scanner_skips", []):
            reason = row["reason"] if row["reason"] in known else "other_incomplete"
            reasons.setdefault(reason, set()).add(row["file"])
        def summarize(intentional: bool) -> dict:
            result = {}
            for reason, paths in sorted(reasons.items()):
                if (reason in scanner_skips.INTENTIONAL_SKIP_REASONS) != intentional:
                    continue
                safe = sorted(path for path in paths if all(c.isprintable() for c in path))
                result[reason] = {"count": len(paths), "paths": safe[:10], "omitted": len(paths) - len(safe[:10])}
            return result
        outstanding = {"available": True, "incomplete_by_reason": summarize(False), "intentional_exclusions_by_reason": summarize(True),
                       "qualification": "Recorded outstanding coverage only; an empty list is not evidence that a full scan ran or that the current tree is clean."}
    import tomllib
    try:
        rules = tomllib.loads((root / "docs/scan-rules.toml").read_text(encoding="utf-8"))
        tables = [rules.get("allowlist", {})]
        if "allowlists" in rules or not isinstance(rules.get("rules", []), list):
            raise ValueError("unsupported project allowlist")
        for rule in rules.get("rules", []):
            if not isinstance(rule, dict) or not isinstance(rule.get("allowlists", []), list):
                raise ValueError("invalid rule allowlists")
            tables.extend(rule.get("allowlists", []))
        count = 0
        for allowlist in tables:
            paths = allowlist.get("paths", []) if isinstance(allowlist, dict) else None
            if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
                raise ValueError("invalid allowlist")
            count += len(paths)
        allowed = {"available": True, "path_entries": count}
    except FileNotFoundError:
        allowed = {"available": True, "path_entries": 0}
    except (OSError, ValueError, UnicodeError):
        allowed = _unavailable("project_allowlist_unreadable_or_invalid")
    allowed["qualification"] = "Configured project global allowlist and per-rule allowlists path entries, not matching files; framework allowlists are not included."
    return {"history": history, "outstanding": outstanding, "project_allowlist": allowed}


def _secrets(root: Path) -> dict:
    findings = _secret_findings(root)
    # Findings and coverage have independent availability; neither hides the other.
    try:
        findings["scan_health"] = _scan_health(root)
    except Exception:
        findings["scan_health"] = _unavailable("scan_health_unreadable_or_invalid")
    return findings


def collect_project_stats(root: Path, sections: list[str] | None = None, *, include_wave_details: bool = False, group_by: str | None = None) -> dict:
    """Compute selected sections only; a failed section does not hide other figures."""
    selected = list(SECTIONS) if sections is None else sections
    if not isinstance(selected, list) or any(not isinstance(s, str) or s not in SECTIONS for s in selected):
        raise ValueError("sections must be a list containing only: " + ", ".join(SECTIONS))
    if not isinstance(include_wave_details, bool):
        raise ValueError("include_wave_details must be a boolean")
    if group_by not in (None, "directory"):
        raise ValueError("group_by must be directory or omitted")
    root = Path(root).resolve()
    result: dict[str, dict] = {}
    files = None
    waves = None
    changes = None
    for section in dict.fromkeys(selected):
        try:
            if section in ("code", "todo"):
                if files is None:
                    files = _files(root)
                rows, meta = files
                if meta["unreadable_directories"] or meta["unreadable_files"]:
                    value = _unavailable("file_scope_incomplete", complete=False, **meta)
                else:
                    if section == "code":
                        try:
                            roles = _path_roles(root)
                        except ValueError:
                            value = _unavailable("statistics_configuration_invalid", complete=False)
                        else:
                            value = _code(rows, meta, roles, group_by=group_by)
                    else:
                        value = _todo(rows, meta)
            elif section in ("lifecycle", "token_savings"):
                import dashboard_lib
                if waves is None:
                    waves = dashboard_lib.collect_waves(root)
                if section == "lifecycle":
                    if changes is None:
                        changes = dashboard_lib.collect_changes(root)
                    value = _lifecycle(waves, changes)
                else:
                    value = _token_savings(root, waves, include_wave_details=include_wave_details)
            else:
                value = {"documents": _documents, "memories": _memories, "index": _index, "secrets": _secrets}[section](root)
        except Exception as exc:
            # Exception messages may contain finding content or document excerpts.
            value = _unavailable("collection_failed:" + type(exc).__name__, **({"complete": False} if section in ("code", "todo") else {}))
        result[section] = value
    return {"schema_version": 1, "sections": result}


def format_report(payload: dict) -> str:
    """Render returned figures, retaining all scope and availability qualifications."""
    import vocabulary_profile as vp
    assigned = f"{vp.ITEM_NAME_PLURAL} assigned to {vp.CONTAINER_NAME_PLURAL.lower()}"
    unassigned = f"Plans not assigned to a {vp.CONTAINER_NAME.lower()}"
    labels = {"lifecycle": f"{vp.CONTAINER_NAME_PLURAL} and {vp.ITEM_NAME_PLURAL}", "token_savings": "Token savings estimates", "todo": "Source-code TODO markers"}
    nouns = {
        "waves": vp.CONTAINER_NAME_PLURAL, "changes": vp.ITEM_NAME_PLURAL,
        "wave": assigned, "plan": unassigned,
        "progress": f"{assigned} — progress",
        "raw_checkboxes": f"{assigned} — acceptance criteria and implementation tasks",
        "unadmitted_checkboxes": f"{unassigned} — acceptance criteria and implementation tasks",
        "criteria": "Acceptance criteria", "tasks": "Implementation tasks",
        "wave_id": f"{vp.CONTAINER_NAME} ID",
        "missing_admitted_documents": f"Missing {vp.ITEM_NAME.lower()} documents assigned to {vp.CONTAINER_NAME_PLURAL.lower()}",
        "unreadable_change_documents": f"Unreadable {vp.ITEM_NAME.lower()} documents",
    }
    lines = ["# Project statistics"]
    def render(value: Any, depth: int = 0) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                label = nouns.get(key, key.replace("_", " ").capitalize())
                if isinstance(item, (dict, list)):
                    lines.append("  " * depth + f"- {label}:")
                    render(item, depth + 1)
                else:
                    lines.append("  " * depth + f"- {label}: {str(item).lower() if isinstance(item, bool) else 'unknown' if item is None else item}")
        elif isinstance(value, list):
            for item in value:
                render(item, depth)
        else:
            lines.append("  " * depth + f"- {str(value).lower() if isinstance(value, bool) else 'unknown' if value is None else value}")
    for name, value in payload["sections"].items():
        lines.extend(("", "## " + labels.get(name, name.replace("_", " ").capitalize()), ""))
        if name == "code" and value.get("available") and "roles" in value:
            lines.extend(["| Category | Unique files | Total lines | Code lines |", "| --- | ---: | ---: | ---: |"])
            for category, counts in value["categories"].items():
                both = counts["both"]
                lines.append(f"| {category.capitalize()} | {both['files']:,} | {both['total_lines']:,} | {both['code_lines']:,} |")
            lines.extend(["", "| Language | Unique files | Non-test code lines | Test code lines |", "| --- | ---: | ---: | ---: |"])
            for lang, counts in value["languages"].items():
                if counts.get("category") != "code":
                    continue
                lines.append(f"| {lang} | {counts['both']['files']:,} | {counts['effective_non_test']['code_lines']:,} | {counts['effective_test']['code_lines']:,} |")
            lines.append("\n" + value["inline_analysis"]["note"])
            lines.append("Inline analysis: " + value["inline_analysis"]["status"] + ". Test share is not test coverage.")
            lines.extend(["", "| Path role | Unique files | Configured files | Inferred files | Non-test code lines | Test code lines |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
            for role, counts in value["roles"].items():
                lines.append(f"| {role.replace('_', '-')} | {counts['both']['files']:,} | {counts['configured_files']:,} | {counts['inferred_files']:,} | {counts.get('effective_non_test', {}).get('code_lines', 0):,} | {counts.get('effective_test', {}).get('code_lines', 0):,} |")
            lines.append(value["role_note"])
            if "directories" in value:
                lines.extend(["", "| Directory | Language | Unique files | Code lines | Non-test code lines | Test code lines |", "| --- | --- | ---: | ---: | ---: | ---: |"])
                for row in value["directories"]:
                    lines.append(f"| {row['directory']} | {row['language']} | {row['both']['files']:,} | {row['both']['code_lines']:,} | {row.get('effective_non_test', {}).get('code_lines', 0):,} | {row.get('effective_test', {}).get('code_lines', 0):,} |")
            render({key: item for key, item in value.items() if key not in {"languages", "categories", "roles", "directories", "role_note"}})
            continue
        if name == "token_savings" and value.get("available"):
            total = value.get("estimated_totals", {})
            lines.append(f"Estimated tokens saved: {total.get('estimated_tokens_saved', 0):,}. {value.get('paired_evaluation_note', 'Paired evaluation status unknown')}. ")
            lines.append(value.get("debit_note", ""))
        elif name == "memories" and value.get("available"):
            lines.append(f"Candidate records awaiting validation: {value.get('candidate_records_awaiting_validation', 0)}.")
            lines.append(value.get("population_note", ""))
        elif name == "lifecycle" and value.get("completion_rule"):
            lines.append(value["completion_rule"])
        render(value)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    from repo_root import discover_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--section", action="append", choices=SECTIONS)
    parser.add_argument("--include-wave-details", action="store_true")
    parser.add_argument("--group-by", choices=("directory",))
    args = parser.parse_args(argv)
    payload = collect_project_stats(discover_root(args.root), args.section, include_wave_details=args.include_wave_details, group_by=args.group_by)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True) if args.json else format_report(payload), end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    import venv_bootstrap
    import cli_stdio
    venv_bootstrap.activate_tool_venv()
    cli_stdio.configure_utf8_stdio()
    raise SystemExit(main())
