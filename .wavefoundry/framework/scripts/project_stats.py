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


def _line_counts(text: str, language: str) -> dict:
    syntax = COMMENT_SYNTAX.get(language)
    out = _counts(syntax is not None)
    out["files"] = 1
    block_end = None
    for line in text.splitlines():
        out["total_lines"] += 1
        if not line.strip():
            out["blank_lines"] += 1
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
            out["comment_lines"] += 1
        else:
            out["code_lines"] += 1
    return out


def _files(root: Path) -> tuple[list, dict]:
    import indexer
    import chunker
    dirs: set[str] = set()
    failures: set[str] = set()
    candidates = indexer.walk_repo(root, unreadable_dirs=dirs, unreadable_files=failures)
    prefixes = indexer._merged_project_include_prefixes_for_graph(root, ())
    candidates = indexer._filter_project_index_excludes(candidates, root, (), project_include_prefixes=prefixes)
    rows, binary, read_failures = [], 0, 0
    docs = CATEGORY_LANGUAGES["documentation"] | set(chunker.MARKDOWN_EXTENSIONS)
    for path in sorted(candidates):
        try:
            raw = path.read_bytes()
        except OSError:
            read_failures += 1
            continue
        if b"\0" in raw[:8192]:
            binary += 1
            continue
        ext = path.suffix.lower()
        lang = chunker._EXT_TO_LANGUAGE.get(ext, ext or "extensionless")
        category = "documentation" if ext in docs else "data" if lang in CATEGORY_LANGUAGES["data"] else "code"
        rel = path.relative_to(root).as_posix()
        is_test = category == "code" and (indexer._is_test_code_path(rel) or any(path.name.endswith(s) and len(path.name) > len(s) for s in TEST_SUFFIXES))
        rows.append((rel, lang, category, is_test, raw.decode("utf-8", errors="replace")))
    meta = {"scope": SCOPE_NOTE, "max_file_bytes": indexer._resolve_max_file_bytes(root),
            "size_cap_note": "indexing.max_file_bytes; zero disables the cap.",
            "binary_files": binary, "binary_note": "Binary candidates detected, not a repository-wide binary census.",
            "unreadable_directories": len(dirs), "unreadable_files": len(failures) + read_failures}
    return rows, meta


def _code(rows: list, meta: dict) -> dict:
    languages: dict[str, dict] = {}
    categories = {key: {"both": _counts(), **({"production": _counts(), "test": _counts()} if key == "code" else {})} for key in ("code", "documentation", "data")}
    for _, lang, category, is_test, text in rows:
        counts = _line_counts(text, lang)
        row = languages.setdefault(lang, {"category": category, "both": _counts(lang in COMMENT_SYNTAX), **({"production": _counts(lang in COMMENT_SYNTAX), "test": _counts(lang in COMMENT_SYNTAX)} if category == "code" else {})})
        _add_counts(row["both"], counts)
        _add_counts(categories[category]["both"], counts)
        if category == "code":
            key = "test" if is_test else "production"
            _add_counts(row[key], counts)
            _add_counts(categories[category][key], counts)
    for row in [*languages.values(), categories["code"]]:
        if "test" in row:
            row["test_code_ratio"] = row["test"]["code_lines"] / row["both"]["code_lines"] if row["both"]["code_lines"] else 0.0
    return {"available": True, "complete": True, "languages": dict(sorted(languages.items())), "categories": categories, **meta, "counting_note": LEXICAL_NOTE, "test_rule": TEST_NOTE}


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
    unadmitted = dashboard_lib.collect_checklist_counts(changes["plan"])
    unadmitted_unreadable = sum(bool(c.get("read_error")) for c in changes["plan"])
    unadmitted["coverage"] = {
        "complete": not unadmitted_unreadable,
        "unreadable_change_documents": unadmitted_unreadable,
        "warning": "Checklist coverage is incomplete; counts include only readable unadmitted plans." if unadmitted_unreadable else None,
    }
    return {"available": True, "waves": {"total": len(waves), "by_status": _by(waves, "status")},
            "changes": {key: {"total": len(changes[key]), "by_kind": _by(changes[key], "kind"), "by_status": _by(changes[key], "status")} for key in ("wave", "plan")},
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
    return {"available": True, "total": len(records), "by_status": _by(records, "status"), "active_by_kind": _by([r for r in records if r.get("status") == "active"], "kind"), "archive_note": "Archived bodies are counted once; the archive register is not added."}


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


def _token_savings(root: Path, waves: list) -> dict:
    import context_efficiency as ce
    import vocabulary_profile as vp
    totals = dict(ce.empty_checkpoint()["totals"])
    stages: dict[str, dict] = {}
    statuses: Counter = Counter()
    excluded, marked, missing, pending = [], 0, 0, 0
    for wave in waves:
        path = root / wave["path"]
        path = path.parent / vp.RECORD_FILENAME
        state = ce.parse_checkpoint_block(path.read_text(encoding="utf-8"))
        if state is None:
            missing += 1
            continue
        marked += 1
        status = state["measurement_status"]
        statuses[status] += 1
        pending += bool(state["pending"])
        if status != "healthy":
            excluded.append({"wave_id": wave["wave_id"], "measurement_status": status})
            continue
        for key, value in state["totals"].items():
            totals[key] = totals.get(key, 0) + value
        for stage, values in state["stages"].items():
            target = stages.setdefault(stage, {})
            for key, value in values.items():
                target[key] = target.get(key, 0) + value
    return {"available": True, "measurement": "estimates", "estimated_totals": totals, "estimated_stages": stages, "records_with_marker": marked, "records_without_marker": missing, "by_measurement_status": dict(sorted(statuses.items())), "pending_markers": pending, "excluded_records": excluded, "limitation": ce._CHECKPOINT_ESTIMATE_NOTE}


def _secrets(root: Path) -> dict:
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


def collect_project_stats(root: Path, sections: list[str] | None = None) -> dict:
    """Compute selected sections only; a failed section does not hide other figures."""
    selected = list(SECTIONS) if sections is None else sections
    if not isinstance(selected, list) or any(not isinstance(s, str) or s not in SECTIONS for s in selected):
        raise ValueError("sections must be a list containing only: " + ", ".join(SECTIONS))
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
                    value = (_code if section == "code" else _todo)(rows, meta)
            elif section in ("lifecycle", "token_savings"):
                import dashboard_lib
                if waves is None:
                    waves = dashboard_lib.collect_waves(root)
                if section == "lifecycle":
                    if changes is None:
                        changes = dashboard_lib.collect_changes(root)
                    value = _lifecycle(waves, changes)
                else:
                    value = _token_savings(root, waves)
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
    for name, value in payload["sections"].items():
        lines.extend(("", "## " + labels.get(name, name.replace("_", " ").capitalize()), ""))
        render(value)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    from repo_root import discover_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--section", action="append", choices=SECTIONS)
    args = parser.parse_args(argv)
    payload = collect_project_stats(discover_root(args.root), args.section)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True) if args.json else format_report(payload), end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    import venv_bootstrap
    import cli_stdio
    venv_bootstrap.activate_tool_venv()
    cli_stdio.configure_utf8_stdio()
    raise SystemExit(main())
