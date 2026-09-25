"""Codenav response handlers; registration and shared dependencies stay in server_impl."""
from __future__ import annotations

import marker_namespaces

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


def code_list_files_response(root: Path, glob: str = "") -> dict[str, Any]:
    """List repository files with optional glob filter."""
    from wf_server import server_impl
    try:
        all_files = server_impl._walk_repo_for_navigation(root)
    except Exception as exc:
        return server_impl._response("error", {"glob": glob}, diagnostics=[server_impl._diagnostic("navigation_error", f"File listing failed: {exc}")], next_tools=["wf_help"], usage="wf_help()")

    root_r = root.resolve()
    if glob:
        import fnmatch
        paths = [
            str(p.resolve().relative_to(root_r)).replace("\\", "/")
            for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]
    else:
        paths = [str(p.resolve().relative_to(root_r)).replace("\\", "/") for p in all_files]

    return server_impl._response("ok", {"glob": glob, "count": len(paths), "paths": paths}, next_tools=["code_read", "code_keyword"], usage="code_read(path='...', start_line=1, end_line=50)")

def _edit_governance_for_path(root: Path, repo_rel: str) -> Optional[dict[str, Any]]:
    """Return ``edit_governance`` hint dict when the path matches a gated area,
    else None. Reads guard-overrides.json via the existing
    ``_read_guard_overrides`` helper (server_impl.py:4877) for current state.

    Wave 1p3dk / 1p3ha: surfaces the gate requirement at read time so agents
    don't discover it the hard way via post-edit-hook BLOCKED messages.
    """
    from wf_server import server_impl
    matched_gate: Optional[str] = None
    for prefix, gate_name in server_impl._EDIT_GOVERNANCE_GATE_MAP:
        if repo_rel.startswith(prefix):
            matched_gate = gate_name
            break
    if matched_gate is None:
        return None
    try:
        overrides = server_impl._read_guard_overrides(root)
        gate_state = overrides.get(matched_gate, {})
        if isinstance(gate_state, dict) and bool(gate_state.get("enabled")):
            current_state = "open"
        else:
            current_state = "closed"
    except Exception:  # pragma: no cover — defensive
        current_state = "unknown"
    return {
        "requires_gate": matched_gate,
        "current_state": current_state,
        "open_with": f"wf_open_gate(gate={matched_gate!r})",
    }

def _marker_regions_in_range(text: str, lo: int, hi: int) -> list[dict[str, Any]]:
    """Find canonical or legacy ``<!-- wave:* begin/end -->`` regions that
    overlap the requested line range [lo, hi] (inclusive, 1-indexed).

    Returns a list of ``{name, start_line, end_line, warning}`` entries.
    Empty list (not omission) for shape consistency.

    Wave 1p3dk / 1p3ha: renderer-owned regions are rewritten on each
    ``render_platform_surfaces.py`` invocation; agent edits inside them are
    lost on the next render. Surfacing the regions at read time prevents
    wasted edit attempts.
    """
    regions: list[dict[str, Any]] = []
    inside_marker: Optional[tuple[str, int]] = None  # (name, start_line)
    for line_no, line in enumerate(text.splitlines(), 1):
        if inside_marker is None:
            m = marker_namespaces.MARKER_BEGIN_RE.search(line)
            if m:
                inside_marker = (m.group(1), line_no)
        else:
            end_match = marker_namespaces.MARKER_END_RE.search(line)
            if end_match and (
                end_match.group(1) is None
                or end_match.group(1) == inside_marker[0]
            ):
                name, start_line = inside_marker
                end_line = line_no
                # Overlap test: [start_line, end_line] intersects [lo, hi]?
                if start_line <= hi and end_line >= lo:
                    regions.append({
                        "name": name,
                        "start_line": start_line,
                        "end_line": end_line,
                        "warning": "renderer-owned region; edits will be overwritten on next render_platform_surfaces.py invocation",
                    })
                inside_marker = None
    return regions

def _find_smallest_containing_ts_node(
    node: Any, start_line: int, end_line: int, candidates: frozenset
) -> Optional[Any]:
    """Walk tree-sitter tree to find the smallest node of a named type whose
    line range fully contains [start_line, end_line] (1-indexed inclusive)."""
    # tree-sitter start_point/end_point are 0-indexed (row, col)
    node_start = node.start_point[0] + 1
    node_end = node.end_point[0] + 1
    if not (node_start <= start_line and node_end >= end_line):
        return None
    best = node if node.type in candidates else None
    for child in node.children:
        child_best = _find_smallest_containing_ts_node(child, start_line, end_line, candidates)
        if child_best is not None:
            # Child is strictly smaller and also a named symbol — prefer it
            best = child_best
    return best

def _find_node_at_line(node: Any, line: int) -> Optional[Any]:
    """Find the deepest non-trivial node that contains ``line`` (1-indexed)."""
    node_start = node.start_point[0] + 1
    node_end = node.end_point[0] + 1
    if not (node_start <= line <= node_end):
        return None
    best = node
    for child in node.children:
        child_best = _find_node_at_line(child, line)
        if child_best is not None:
            best = child_best
    return best

def _ts_node_name(node: Any) -> Optional[str]:
    """Extract the identifier name from a tree-sitter symbol node, if available."""
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier", "property_identifier"):
            try:
                return child.text.decode("utf-8", errors="replace")
            except (AttributeError, UnicodeDecodeError):
                return None
    return None

def _structural_python_ast(
    absolute_path: Path,
    start_line: int,
    end_line: int,
    source: str,
) -> Optional[dict[str, Any]]:
    """Python AST path for structural enrichment. Mirrors the tree-sitter
    path but uses stdlib `ast` since Python doesn't go through tree-sitter
    in this framework. Shares the cache module."""
    from wf_server import server_impl
    try:
        import tree_sitter_cache
    except ImportError:  # pragma: no cover
        return None

    def _parse():
        from wf_server import server_impl
        try:
            return server_impl.ast.parse(source)
        except SyntaxError:
            return None

    try:
        tree, _ = tree_sitter_cache.default_cache.get_or_parse(
            absolute_path, "python", _parse,
        )
    except Exception:
        return None
    if tree is None:
        return None

    # Find smallest FunctionDef/AsyncFunctionDef/ClassDef containing the range
    containing = None
    containing_size = float("inf")
    for node in server_impl.ast.walk(tree):
        if isinstance(node, (server_impl.ast.FunctionDef, server_impl.ast.AsyncFunctionDef, server_impl.ast.ClassDef)):
            node_end = getattr(node, "end_lineno", None) or node.lineno
            if node.lineno <= start_line and node_end >= end_line:
                size = node_end - node.lineno
                if size < containing_size:
                    containing = node
                    containing_size = size

    containing_symbol = None
    starts_mid = False
    ends_mid = False
    suggested_range = None
    construct_kind_at_start = None
    construct_kind_at_end = None

    if containing is not None:
        sym_start = containing.lineno
        sym_end = getattr(containing, "end_lineno", None) or containing.lineno
        complete = (start_line <= sym_start and end_line >= sym_end)
        kind = type(containing).__name__.lower()
        kind = "class" if "class" in kind else "function"
        containing_symbol = {
            "name": containing.name,
            "kind": kind,
            "start_line": sym_start,
            "end_line": sym_end,
            "complete_in_range": complete,
        }
        starts_mid = sym_start < start_line
        ends_mid = sym_end > end_line
        if starts_mid or ends_mid:
            suggested_range = [sym_start, sym_end]
        if starts_mid:
            construct_kind_at_start = kind
        if ends_mid:
            construct_kind_at_end = kind

    return {
        "containing_symbol": containing_symbol,
        "range_analysis": {
            "starts_mid_construct": starts_mid,
            "ends_mid_construct": ends_mid,
            "construct_kind_at_start": construct_kind_at_start,
            "construct_kind_at_end": construct_kind_at_end,
            "suggested_clean_range": suggested_range,
        },
    }

def _structural_for_range(
    absolute_path: Path,
    lang: str,
    start_line: int,
    end_line: int,
    source: str,
    size_bytes: Optional[int],
) -> Optional[dict[str, Any]]:
    """Return the structural enrichment block for the requested range, or None
    when the file is non-code, too large, or tree-sitter parse fails.

    Wave 1p3dk / 1p3ha Tier 5. Uses the shared tree-sitter cache
    (`tree_sitter_cache.default_cache`) so subsequent calls — and follow-on
    `1p3hd` consumers (`code_outline`, `code_definition`, etc.) — hit cache
    on the same `(path, lang)`. Python uses stdlib AST via the same cache.
    """
    from wf_server import server_impl
    if size_bytes is not None and size_bytes > server_impl._STRUCTURAL_PARSE_SIZE_BUDGET:
        return {
            "note": "file_too_large_for_structural_parse",
            "size_bytes": size_bytes,
            "budget_bytes": server_impl._STRUCTURAL_PARSE_SIZE_BUDGET,
        }
    if lang == "python":
        return _structural_python_ast(absolute_path, start_line, end_line, source)
    if lang not in server_impl._TS_SYMBOL_LANG_MAP:
        return None
    ts_lang = server_impl._TS_SYMBOL_LANG_MAP[lang]

    try:
        import tree_sitter_cache
    except ImportError:  # pragma: no cover — defensive
        return None

    def _parse():
        from wf_server import server_impl
        try:
            chunker = server_impl._get_chunker_module()
            return chunker._ts_parse(ts_lang, source)
        except Exception:
            return None

    try:
        tree, _was_hit = tree_sitter_cache.default_cache.get_or_parse(
            absolute_path, lang, _parse,
        )
    except Exception:
        return None
    if tree is None or not hasattr(tree, "root_node"):
        return None

    # containing_symbol: smallest named symbol fully containing the range
    containing_node = _find_smallest_containing_ts_node(
        tree.root_node, start_line, end_line, server_impl._STRUCTURAL_SYMBOL_NODE_TYPES,
    )
    containing_symbol: Optional[dict[str, Any]] = None
    if containing_node is not None:
        symbol_start = containing_node.start_point[0] + 1
        symbol_end = containing_node.end_point[0] + 1
        # complete_in_range: range fully covers the symbol (range == symbol or range ⊇ symbol)
        complete_in_range = (start_line <= symbol_start and end_line >= symbol_end)
        containing_symbol = {
            "name": _ts_node_name(containing_node),
            "kind": containing_node.type,
            "start_line": symbol_start,
            "end_line": symbol_end,
            "complete_in_range": complete_in_range,
        }

    # range_analysis: do the start/end boundaries split a construct?
    start_node = _find_node_at_line(tree.root_node, start_line)
    end_node = _find_node_at_line(tree.root_node, end_line)
    starts_mid_construct = False
    ends_mid_construct = False
    construct_kind_at_start: Optional[str] = None
    construct_kind_at_end: Optional[str] = None
    suggested_clean_range: Optional[list[int]] = None

    if containing_node is not None:
        symbol_start = containing_node.start_point[0] + 1
        symbol_end = containing_node.end_point[0] + 1
        starts_mid_construct = symbol_start < start_line
        ends_mid_construct = symbol_end > end_line
        if starts_mid_construct or ends_mid_construct:
            suggested_clean_range = [symbol_start, symbol_end]
        if starts_mid_construct and start_node is not None:
            construct_kind_at_start = start_node.type
        if ends_mid_construct and end_node is not None:
            construct_kind_at_end = end_node.type

    range_analysis = {
        "starts_mid_construct": starts_mid_construct,
        "ends_mid_construct": ends_mid_construct,
        "construct_kind_at_start": construct_kind_at_start,
        "construct_kind_at_end": construct_kind_at_end,
        "suggested_clean_range": suggested_clean_range,
    }

    return {
        "containing_symbol": containing_symbol,
        "range_analysis": range_analysis,
    }

def code_read_response(
    root: Path,
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    with_line_numbers: bool = True,
) -> dict[str, Any]:
    """Read a file with optional line range, returning line-numbered content
    plus rich metadata that makes the follow-on Read/Edit workflow effortless.

    Wave 1p3dk / 1p3ha comprehensive enrichment:

    - **Internal efficiency:** ``itertools.islice`` over the file iterator for
      partial reads — only the required lines are read from disk. Full-file
      reads use ``read_text`` as before.
    - **Optional line-number prefix:** ``with_line_numbers=False`` returns raw
      content without the ``"%5d\\t"`` prefix. Default True preserves prior
      behavior.
    - **Follow-on Read invocation hint:** ``read_invocation`` carries the exact
      ``{file_path, offset, limit}`` to pass to the built-in ``Read`` tool to
      satisfy Edit's read-first precondition with minimal re-read.
    - **File metadata:** ``absolute_path``, ``mtime``, ``size_bytes`` for
      staleness detection and paging decisions.
    - **Edit governance hint:** ``edit_governance`` surfaces required edit
      gates when the path falls under a gated area (seeds, framework scripts,
      framework dashboard).
    - **Marker region detection:** ``marker_regions`` lists
      canonical or legacy ``<!-- wave:* begin/end -->`` blocks overlapping
      the requested range so agents don't waste an Edit inside renderer-owned
      content.
    - **``total_lines`` semantics shift:** returned only when the call read
      the full file or end_line reached EOF. For mid-file partial reads,
      ``has_more: bool`` is returned instead.

    NOTE: This tool's read does NOT satisfy the harness's Edit/Write
    "read-first" precondition (the harness tracks Read-tool calls only, not
    MCP tool calls). Use ``read_invocation`` to call the built-in ``Read`` tool
    when planning to subsequently edit the same range.
    """
    from wf_server import server_impl
    import itertools

    resolved = server_impl._resolve_repo_path(root, path)
    if resolved is None:
        return server_impl._response("error", {"path": path}, diagnostics=[server_impl._diagnostic("path_outside_root", f"Path '{path}' is outside the repository root or uses an absolute path. Use a repo-relative path.", recovery_tools=["code_list_files"], recovery_usage="code_list_files()")], next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return server_impl._response("error", {"path": path}, diagnostics=[server_impl._diagnostic("file_not_found", f"File '{path}' does not exist.", recovery_tools=["code_list_files"], recovery_usage="code_list_files()")], next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.is_file():
        return server_impl._response("error", {"path": path}, diagnostics=[server_impl._diagnostic("not_a_file", f"'{path}' is a directory, not a file.", recovery_tools=["code_list_files"], recovery_usage=f"code_list_files(glob='{path}/**')")], next_tools=["code_list_files"], usage="code_list_files()")

    # File metadata: collect before parsing so we have it even if parse fails
    absolute_path = str(resolved.resolve())
    try:
        stat = resolved.stat()
        mtime_iso = server_impl.datetime.datetime.fromtimestamp(stat.st_mtime, tz=server_impl.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        size_bytes = stat.st_size
    except OSError:
        mtime_iso = None
        size_bytes = None

    repo_rel = str(resolved.relative_to(root.resolve())).replace("\\", "/") if resolved.is_relative_to(root.resolve()) else path

    is_partial = start_line is not None or end_line is not None
    selected: list[str]
    total: Optional[int]
    has_more: bool
    raw_for_markers: str = ""

    if is_partial:
        # Wave 1p3dk / 1p3ha range-aware streaming: only read up to end_line+1
        # (the +1 detects has_more). For large files this is dramatic — reading
        # 10 lines of a 15K-line file no longer slurps 15K lines.
        lo = max(1, start_line) if start_line is not None else 1
        hi = end_line if end_line is not None else None
        try:
            with resolved.open(encoding="utf-8", errors="replace") as f:
                if hi is None:
                    # No upper bound: read from lo to end
                    iter_lines = itertools.islice(f, lo - 1, None)
                    selected = [line.rstrip("\n") for line in iter_lines]
                    total = lo + len(selected) - 1 if selected else 0
                    has_more = False
                else:
                    # Bounded: read lo through hi+1 to detect has_more
                    iter_lines = itertools.islice(f, lo - 1, hi + 1)
                    raw_selected = [line.rstrip("\n") for line in iter_lines]
                    has_more = len(raw_selected) > (hi - lo + 1)
                    selected = raw_selected[:hi - lo + 1]
                    total = None  # Mid-file partial; total omitted per AC-4
        except OSError as exc:
            return server_impl._response("error", {"path": path}, diagnostics=[server_impl._diagnostic("read_error", f"Could not read '{path}': {exc}")], next_tools=["code_list_files"], usage="code_list_files()")
        if not selected:
            # Range was beyond EOF
            return server_impl._response("error", {"path": path, "start_line": start_line, "end_line": end_line}, diagnostics=[server_impl._diagnostic("invalid_range", f"start_line ({lo}) is beyond EOF.")], next_tools=["code_read"], usage=f"code_read(path={path!r})")
        actual_lo = lo
        actual_hi = lo + len(selected) - 1
    else:
        # Full-file read: preserve original behavior, compute total_lines
        try:
            raw = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return server_impl._response("error", {"path": path}, diagnostics=[server_impl._diagnostic("read_error", f"Could not read '{path}': {exc}")], next_tools=["code_list_files"], usage="code_list_files()")
        raw_for_markers = raw
        all_lines = raw.splitlines()
        total = len(all_lines)
        selected = all_lines
        actual_lo = 1
        actual_hi = total
        has_more = False

    if actual_lo > actual_hi:
        return server_impl._response("error", {"path": path, "start_line": start_line, "end_line": end_line}, diagnostics=[server_impl._diagnostic("invalid_range", f"start_line ({actual_lo}) is greater than end_line ({actual_hi}).")], next_tools=["code_read"], usage=f"code_read(path={path!r})")

    # Format content: with or without line numbers
    if with_line_numbers:
        content = "\n".join(f"{i + actual_lo:5d}\t{line}" for i, line in enumerate(selected))
    else:
        content = "\n".join(selected)

    # Build the read_invocation hint — exact Read() call satisfying Edit precondition
    read_invocation = {
        "file_path": absolute_path,
        "offset": actual_lo,
        "limit": actual_hi - actual_lo + 1,
        "mtime": mtime_iso,
        "satisfies_edit_precondition_for_range": True,
        "note": "code_read does NOT satisfy Edit/Write read-first precondition; pass these to the built-in Read tool before editing",
    }

    # Edit governance hint (omitted entirely when path is not gated)
    edit_governance = _edit_governance_for_path(root, repo_rel)

    # Marker region detection
    # For partial reads we didn't slurp the whole file; do a separate quick pass
    # to find markers within the returned range. For full reads, reuse raw.
    if is_partial and raw_for_markers == "":
        # Quick second pass for marker detection on partial reads.
        # Acceptable cost: we already have I/O cache warm; marker scan is fast.
        try:
            raw_for_markers = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw_for_markers = ""
    marker_regions = _marker_regions_in_range(raw_for_markers, actual_lo, actual_hi) if raw_for_markers else []

    data: dict[str, Any] = {
        "path": path,
        "absolute_path": absolute_path,
        "start_line": actual_lo,
        "end_line": actual_hi,
        "content": content,
        "read_invocation": read_invocation,
        "marker_regions": marker_regions,
    }
    if total is not None:
        data["total_lines"] = total
    else:
        data["has_more"] = has_more
    if mtime_iso is not None:
        data["mtime"] = mtime_iso
    if size_bytes is not None:
        data["size_bytes"] = size_bytes
    if edit_governance is not None:
        data["edit_governance"] = edit_governance
    # 1p8gy Req 6 / AC-5: active memory attached to the file being read —
    # capped, cited, graceful absence (the edit_governance precedent).
    _mem_advisories = server_impl._memory_advisories_for_path(root, repo_rel)
    if _mem_advisories:
        data["memory_advisories"] = _mem_advisories

    # Tier 5: tree-sitter structural enrichment. Omitted for non-code files,
    # files >500KB, and files where parse fails. Source is whatever we have
    # in memory (raw_for_markers covers both partial and full reads).
    if raw_for_markers:
        lang_for_structural = server_impl._EXT_TO_LANG.get(resolved.suffix.lower(), "")
        if lang_for_structural:
            structural = _structural_for_range(
                resolved.resolve(),
                lang_for_structural,
                actual_lo,
                actual_hi,
                raw_for_markers,
                size_bytes,
            )
            if structural is not None:
                data["structural"] = structural

    return server_impl._response("ok", data, next_tools=["code_keyword", "code_definition"], usage=f"code_keyword(query='...', glob='*.py')")

def _apply_keyword_limit(
    results: list[dict[str, Any]], limit: int,
) -> tuple[list[dict[str, Any]], bool, int]:
    """Wave 1p3dk addendum: cap a result list at ``limit`` and report
    whether truncation occurred. ``limit <= 0`` means no cap (exhaustive).

    Returns ``(capped_results, truncated, total_matches_found)``.
    """
    total = len(results)
    if limit > 0 and total > limit:
        return results[:limit], True, total
    return results, False, total

def code_lexical_response(
    root: Path,
    query: str = "",
    table: str = "both",
    kind: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Direct BM25 exact-token search over the index-state store's FTS5 tables (1seiz).

    A ranked view of the SAME lexical corpus ``code_search``/``code_ask`` fuse
    (``fts_code``/``fts_docs``) — for exact-identifier lookups and lexical-layer
    verification. Every whitespace token is matched as a literal (the fusion
    path's safe expression builder); FTS operators never reach the engine.
    Degrades to ``ok`` + empty results + a recovery diagnostic on an absent
    store or FTS-less interpreter, and warns when a searched table is
    under-covered so zero results on a broken store never read as
    "absent from the corpus".
    """
    from wf_server import server_impl
    query = str(query or "").strip()
    if not query:
        return server_impl._response(
            "error", {"query": query},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "query must be a non-empty string.")],
            next_tools=["code_lexical"], usage="code_lexical(query='exact_identifier')",
        )
    table = str(table or "both").strip().lower()
    if table not in ("code", "docs", "both"):
        return server_impl._response(
            "error", {"query": query, "table": table},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "table must be 'code', 'docs', or 'both'.")],
            next_tools=["code_lexical"], usage="code_lexical(query='...', table='code')",
        )
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit if limit > 0 else 20, server_impl.CODE_LEXICAL_MAX_LIMIT))
    kind = str(kind or "").strip()
    tables = ("code", "docs") if table == "both" else (table,)
    index_dir = root / ".wavefoundry" / "index"
    data: dict[str, Any] = {
        "query": query, "table": table, "kind": kind or None, "limit": limit,
        "results": [], "result_count": 0,
    }
    diagnostics: list[dict[str, Any]] = []
    try:
        iss = server_impl._load_script("index_state_store")
    except Exception:
        iss = None
    if iss is None or not iss.state_store_path(index_dir).exists():
        diagnostics.append(server_impl._diagnostic(
            "lexical_layer_unavailable",
            "The index-state store is absent — the lexical layer has not been built. "
            "Run a build to provision it.",
            recovery_tools=["index_build", "index_health"],
            recovery_usage="index_build(content='all', mode='update')",
        ))
        return server_impl._response("ok", data, diagnostics=diagnostics,
                         next_tools=["index_build"], usage="index_build(content='all', mode='update')")
    # 1wpag (AC-3/AC-7): the lexical-only tool serves through the SAME probed
    # chokepoint as the hybrid half and the degraded fallbacks. A damaged FTS
    # table is a typed query_failed error, never a healthy zero; the healthy
    # path is an O(1) cached-verdict read plus the MATCH query itself (AC-8).
    epoch_state = server_impl._epoch_state(root)
    fetch = server_impl._fts_probed_fetch(root, tables, query, limit, kind=(kind or None), epoch_state=epoch_state)
    if fetch.get("coverage"):
        data["coverage"] = fetch["coverage"]
    if not fetch.get("available"):
        if fetch.get("failure_reason") == server_impl._REASON_STORE_ABSENT:
            diagnostics.append(server_impl._diagnostic(
                "lexical_layer_unavailable",
                "The index-state store is absent — the lexical layer has not been built. "
                "Run a build to provision it.",
                recovery_tools=["index_build", "index_health"],
                recovery_usage="index_build(content='all', mode='update')",
            ))
            return server_impl._response("ok", data, diagnostics=diagnostics,
                             next_tools=["index_build"], usage="index_build(content='all', mode='update')")
        data["failure_reason"] = server_impl._REASON_QUERY_FAILED
        if fetch.get("detail"):
            data["detail"] = fetch["detail"]
        if fetch.get("damage"):
            data["damaged_tables"] = sorted(fetch["damage"])
        diagnostics.append(server_impl._diagnostic(
            server_impl._REASON_QUERY_FAILED,
            "The lexical (FTS5) layer cannot serve this query: "
            + (fetch.get("detail") or "store damage")
            + ". This is an infrastructure failure, NOT an empty corpus: zero results "
            "here say nothing about the tokens' presence. Healing runs under the build "
            "lock on the next ordinary build (requested automatically, one heal per "
            "table per epoch); index_health shows the per-table verdict. For an exact "
            "match right now use code_keyword (live substring).",
            recovery_tools=["index_health", "code_keyword"],
            recovery_usage="index_health()",
        ))
        return server_impl._response("error", data, diagnostics=diagnostics,
                         next_tools=["index_health", "code_keyword"], usage="index_health()")
    if fetch.get("lexical_disabled") and not fetch.get("results"):
        diagnostics.append(server_impl._diagnostic(
            "lexical_layer_unavailable",
            "This interpreter's SQLite has no FTS5, so the lexical layer is not built. "
            "Use code_keyword (live substring) or code_pattern (regex) for exact matches.",
            recovery_tools=["code_keyword", "code_pattern"],
            recovery_usage="code_keyword(query='<exact_token>')",
        ))
        return server_impl._response("ok", data, diagnostics=diagnostics,
                         next_tools=["code_keyword"], usage="code_keyword(query='<exact_token>')")
    hits: list[dict[str, Any]] = list(fetch.get("results") or [])
    # sqlite bm25() is smaller-is-better (negative); best-first ascending.
    # Wave 1wpid (requirement 3+7): `table="both"` merges by rank rather than by
    # raw bm25, since the two tables normalize independently. Single-table
    # requests are order-identical, so the docs/code fallbacks are unchanged.
    _grouped: dict[str, list[dict[str, Any]]] = {}
    for _h in hits:
        _grouped.setdefault(str(_h.get("table") or ""), []).append(_h)
    for _rows in _grouped.values():
        _rows.sort(key=lambda h: h.get("bm25", 0.0))
    if len(_grouped) > 1:
        hits = server_impl._load_script("index_state_store").fuse_lexical_tables(_grouped)
    else:
        hits.sort(key=lambda h: h.get("bm25", 0.0))
    results: list[dict[str, Any]] = []
    for h in hits[:limit]:
        text = str(h.get("text") or "")
        truncated = len(text) > server_impl.CODE_LEXICAL_TEXT_CAP
        results.append({
            "id": h.get("id", ""),
            "path": str(h.get("path", "")).replace("\\", "/"),
            "kind": h.get("kind") or "",
            "language": h.get("language") or "",
            "lines": list(h.get("lines") or []),
            "text": text[:server_impl.CODE_LEXICAL_TEXT_CAP],
            "text_truncated": truncated,
            "bm25": h.get("bm25"),
            "table": h.get("table"),
        })
    # 1ro43: freshness annotation rides the same store this tool reads —
    # cheapest surface of all; annotation-only (BM25 order is never
    # partitioned; the relevance band is undefined off the reranker scale).
    server_impl._annotate_freshness(results, root, search_mode=None)
    data["results"] = results
    data["result_count"] = len(results)
    # Coverage tie-in (1sbfj): a zero/thin result on an under-covered table is
    # a store problem, not corpus absence — same compare index_health uses.
    # 1wpag/AC-8: read from the epoch-cached coverage the chokepoint already
    # resolved (computed once per build-state transition), never a per-call
    # quick_check / count_rows.
    try:
        coverage = dict(fetch.get("coverage") or {})
        uncovered = [t for t in tables if coverage.get(t, {}).get("covered") is False]
        if uncovered:
            diagnostics.append(server_impl._diagnostic(
                "chunk_index_undercovered",
                "The lexical index for " + ", ".join(sorted(uncovered)) + " covers materially "
                "less than the vector layers — results may be partial until it heals. "
                "Rebuild it directly (embedding-free, seconds): index_build(content='fts').",
                recovery_tools=["index_build", "index_health"],
                recovery_usage="index_build(content='fts')",
            ))
    except Exception:  # noqa: BLE001 - advisory only
        pass
    if not results and not diagnostics:
        # Healthy store, no hits: remind about token semantics — the common
        # miss is a partial compound identifier.
        data["note"] = (
            "No exact-token matches. FTS tokens keep '_' inside identifiers, so partial "
            "compound identifiers do not match (query 'webhook_activity' will not match "
            "'webhook_activity_inserted'). Use the full identifier, code_pattern for regex, "
            "code_keyword for live-file substring match, or code_search for concepts."
        )
    return server_impl._response(
        "ok", data, diagnostics=diagnostics,
        next_tools=["code_read", "code_keyword"],
        usage="code_read(path='...', start_line=N, end_line=M)",
    )

def code_keyword_response(
    root: Path,
    query: str = "",
    glob: str = "",
    queries: Optional[list[str]] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search repository files for an exact keyword/substring, returning path/line/snippet results.

    Pass either *query* (single string) or *queries* (list of strings); supplying both is an error.
    When *queries* is used each result includes ``matched_query`` showing which entry produced it.

    Wave 1p3dk: ``limit`` defaults to 50 (matching ``code_pattern`` / ``code_references``)
    so unbounded searches against prevalent tokens don't overflow the MCP response
    token cap. Pass ``limit=0`` for exhaustive results. When the cap fires, the
    response includes ``truncated: true`` and ``total_matches_found: <int>`` so
    the agent sees there's more and can refine.
    """
    from wf_server import server_impl
    has_query = bool(query.strip())
    has_queries = queries is not None

    if has_query and has_queries:
        return server_impl._response(
            "error", {"query": query, "queries": queries},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "Provide either 'query' or 'queries', not both.")],
            next_tools=["code_keyword"], usage="code_keyword(query='FOO')",
        )

    if not has_query and not has_queries:
        return server_impl._response(
            "error", {"query": query},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "Search query must be a non-empty string.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )

    # --- multi-query path ---
    if has_queries:
        assert queries is not None  # for type checker
        if not queries:
            return server_impl._response("ok", {"queries": queries, "glob": glob, "count": 0, "truncated": False, "total_matches_found": 0, "results": []},
                             next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")
        try:
            all_files = server_impl._walk_repo_for_navigation(root)
        except Exception as exc:
            return server_impl._response("error", {"queries": queries},
                             diagnostics=[server_impl._diagnostic("navigation_error", f"File walk failed: {exc}")],
                             next_tools=["wf_help"], usage="wf_help()")
        root_r = root.resolve()
        if glob:
            import fnmatch
            all_files = [
                p for p in all_files
                if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
                or fnmatch.fnmatch(p.name, glob)
            ]
        seen: set[tuple[str, int]] = set()
        merged: list[dict[str, Any]] = []
        for q in queries:
            for p in all_files:
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if q in line:
                        key = (rel, lineno)
                        if key not in seen:
                            seen.add(key)
                            merged.append({"path": rel, "line": lineno, "snippet": line.rstrip(), "matched_query": q})
        capped, truncated, total = _apply_keyword_limit(merged, limit)
        return server_impl._response("ok", {"queries": queries, "glob": glob, "count": len(capped), "truncated": truncated, "total_matches_found": total, "results": capped},
                         next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")

    # --- single-query path ---
    try:
        all_files = server_impl._walk_repo_for_navigation(root)
    except Exception as exc:
        return server_impl._response("error", {"query": query}, diagnostics=[server_impl._diagnostic("navigation_error", f"File walk failed: {exc}")], next_tools=["wf_help"], usage="wf_help()")

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    results: list[dict[str, Any]] = []
    for p in all_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            if query in line:
                results.append({"path": rel, "line": lineno, "snippet": line.rstrip()})

    capped, truncated, total = _apply_keyword_limit(results, limit)
    return server_impl._response("ok", {"query": query, "glob": glob, "count": len(capped), "truncated": truncated, "total_matches_found": total, "results": capped},
                     next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")

def _string_literal_end(text: str, i: int) -> Optional[int]:
    """If a string literal begins at ``text[i]``, return the index just past its closing quote;
    otherwise ``None``. Handles triple-quoted and single/double-quoted strings (with backslash
    escapes). The ONE string-skipping primitive shared by ``_bracket_depth`` and
    ``_take_balanced_value`` so the two stay consistent (a separator/bracket inside a string
    literal must never affect either)."""
    n = len(text)
    # Triple-quoted string — skip to closing triple-quote
    if text[i:i + 3] in ('"""', "'''"):
        q = text[i:i + 3]
        j = i + 3
        while j < n and text[j:j + 3] != q:
            j += 1
        return j + 3
    # Single/double-quoted string — skip to closing quote (respecting escapes)
    if text[i] in ('"', "'"):
        q = text[i]
        j = i + 1
        while j < n and text[j] != q:
            if text[j] == '\\':
                j += 1  # skip escaped character
            j += 1
        return j + 1  # skip closing quote
    return None

def _bracket_depth(text: str) -> int:
    """Net open-bracket depth of ``text``, treating quoted strings as opaque.

    Used by ``code_constants_response`` to detect multiline values.
    Triple-quoted and single-quoted strings are skipped entirely so bracket
    characters inside strings do not affect the depth count.
    """
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        se = _string_literal_end(text, i)
        if se is not None:
            i = se
            continue
        if text[i] in '([{':
            depth += 1
        elif text[i] in ')]}':
            depth -= 1
        i += 1
    return depth

def _strip_leading_comment_lines(text: str) -> str:
    """Drop leading blank + whole-line-comment lines from ``text`` (the leading comment block a
    chunker folds onto a const chunk), returning the body from the first real code line on. Only
    LEADING lines are removed, so an interior line of a multiline value is never touched."""
    from wf_server import server_impl
    lines = text.splitlines()
    k = 0
    while k < len(lines) and (not lines[k].strip() or server_impl._COMMENT_LINE_RE.match(lines[k])):
        k += 1
    return "\n".join(lines[k:])

def _take_balanced_value(rest: str) -> tuple[str, str]:
    """From the text immediately after a constant's ``=`` (or after a PHP ``define(`` comma),
    extract the value: consume until a TOP-LEVEL ``,`` / ``;`` / newline (statement end,
    multi-declarator boundary, or grouped-const member boundary) OR a depth-0 CLOSING bracket we
    did not open (the enclosing scope's — e.g. the `}` after a TS enum member or the `)` of a PHP
    `define(`); bracketed literals (``()`` ``[]`` ``{}``) are consumed whole. (value, kind)."""
    rest = rest.lstrip()
    depth = 0
    out: list[str] = []
    i = 0
    n = len(rest)
    while i < n:
        # A string literal is opaque: a `,`/`;`/`\n` or a `}`/`)`/`]` INSIDE a quoted string
        # is value content, not a separator/enclosing-scope close (e.g. CSV_SEP = "," or
        # `static final String SEP = "a;b;c"` or a dict value `{"k": "a}b"}`).
        se = _string_literal_end(rest, i)
        if se is not None:
            out.append(rest[i:se])
            i = se
            continue
        ch = rest[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break  # a closing bracket we didn't open = the enclosing scope's → value ended
            depth -= 1
        elif depth == 0 and ch in ",;\n":
            break
        out.append(ch)
        i += 1
    val = "".join(out).strip().rstrip(";,").strip()
    if not val:
        return val, "scalar"
    if _bracket_depth(val) != 0:
        return val, "multiline-truncated"
    return val, ("multiline" if "\n" in val else "scalar")

def _extract_const_value(decl: str, name: str) -> tuple[str, str]:
    """Language-agnostic value extraction for constant ``name`` from its declaration text (the
    1p4mf chunk-lane const chunk's body). Handles ``NAME = value`` at any indentation / with
    modifiers / a type annotation, per-declarator multi-const lines, PHP ``define('NAME', value)``,
    and multiline bracket literals. Returns (value, kind); ``('', 'scalar')`` when no assignment is
    found (e.g. a value-less interface/trait constant)."""
    from wf_server import server_impl
    # The chunk body can carry a LEADING comment block (chunkers fold leading comments into the
    # const chunk). Strip those leading comment/blank lines first, else a comment that mentions the
    # NAME (e.g. `# THRESHOLD = 10 was the old default` above `THRESHOLD = 99`) poisons the value
    # match — the `\bNAME\b` search would land in the comment (1p4pz review B1).
    text = _strip_leading_comment_lines(decl or "").strip()
    if not text:
        return "", "scalar"
    # PHP define('NAME', <value>) — the value is the second argument.
    mdef = server_impl.re.search(r"\bdefine\s*\(\s*['\"]" + server_impl.re.escape(name) + r"['\"]\s*,", text)
    if mdef:
        return _take_balanced_value(text[mdef.end():])
    # Otherwise: find the NAME token, then the first assignment '=' after it (skip ==/<=/>=/!=/=>).
    mname = server_impl.re.search(r"\b" + server_impl.re.escape(name) + r"\b", text)
    if not mname:
        return "", "scalar"
    i, n = mname.end(), len(text)
    while i < n:
        if text[i] == "=" and text[i - 1] not in "=<>!" and (i + 1 >= n or text[i + 1] not in "=>"):
            return _take_balanced_value(text[i + 1:])
        i += 1
    return "", "scalar"

def code_constants_response(root: Path, symbols: list[str], glob: str = "") -> dict[str, Any]:
    """Look up module-/type-level constant declarations by name across all languages, returning
    parsed values.

    Two detection passes are unioned (wave 1p4pz):
    1. A column-0 ``NAME = <value>`` / ``NAME: TYPE = <value>`` scan — fast, catches Python module
       assignments (incl. lowercase) and collects multiline literals via bracket-depth continuation.
    2. The **1p4mf chunk-lane constant detector** (one detector, three consumers — reused via the
       chunker module) — catches **indented / non-Python** constants the regex misses: Java
       ``static final``, Go/C# ``const``, Kotlin ``const val``, Rust ``const``, Swift ``static let``,
       Ruby/PHP constants, JS/TS ``const``, AND Python **class-level** constants. The right-hand-side
       value is extracted language-agnostically (after ``=`` at any indent; trailing ``;`` trimmed;
       PHP ``define('NAME', value)`` second arg; multiline literals preserved). Only files containing
       a requested symbol are chunked (cheap pre-filter). Function/block locals are NOT returned (the
       chunk lane's scope gate carries through). A constant the regex already returned is not
       duplicated (range-dedup, keeping the regex's richer value).

    Returns results in input ``symbols`` order. Symbols not found are included with ``value: null``.
    When a symbol appears in multiple files / scopes, all matches are returned (one entry per match).
    """
    from wf_server import server_impl
    if not symbols:
        return server_impl._response(
            "error", {"symbols": symbols},
            diagnostics=[server_impl._diagnostic("invalid_arguments", "symbols list must be non-empty.")],
            next_tools=["code_keyword"], usage="code_keyword(query='CONSTANT_NAME')",
        )
    try:
        all_files = server_impl._walk_repo_for_navigation(root)
    except Exception as exc:
        return server_impl._response(
            "error", {"symbols": symbols},
            diagnostics=[server_impl._diagnostic("navigation_error", f"File walk failed: {exc}")],
            next_tools=["wf_help"], usage="wf_help()",
        )

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    symbol_set = set(symbols)
    # matches[sym] accumulates all file matches for that symbol
    matches: dict[str, list[dict[str, Any]]] = {s: [] for s in symbol_set}

    import re as _re
    for p in all_files:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")

        i = 0
        while i < len(lines):
            line = lines[i]
            # Only consider unindented lines (module-level assignments)
            if line and not line[0].isspace():
                for sym in symbol_set:
                    if not line.startswith(sym):
                        continue
                    # NAME must be followed by whitespace, ':', or '='
                    after = line[len(sym):]
                    if not after or after[0] not in (' ', ':', '=', '\t'):
                        continue
                    m = _re.match(
                        r'^' + _re.escape(sym) + r'\s*(?::[^=]*)?\s*=\s*(.*)',
                        line,
                    )
                    if not m:
                        continue
                    val_start = m.group(1).rstrip()
                    lineno = i + 1
                    depth = _bracket_depth(val_start)
                    if depth == 0:
                        matches[sym].append({
                            "name": sym, "value": val_start,
                            "file": rel, "line": lineno, "kind": "scalar",
                        })
                    else:
                        val_lines = [val_start]
                        j = i + 1
                        count = 0
                        while j < len(lines) and depth != 0 and count < server_impl._CONSTANTS_MAX_CONTINUATION:
                            cont = lines[j].rstrip()
                            depth += _bracket_depth(cont)
                            val_lines.append(cont)
                            j += 1
                            count += 1
                        kind = "multiline" if depth == 0 else "multiline-truncated"
                        matches[sym].append({
                            "name": sym, "value": "\n".join(val_lines),
                            "file": rel, "line": lineno, "kind": kind,
                        })
            i += 1

    # --- Multi-language pass (wave 1p4pz): the column-0 scan above is Python-shaped (and misses
    # indented declarations). Reuse the 1p4mf chunk-lane constant detector to find constants the
    # regex missed — Java `static final`, Go `const`, C#/Kotlin/Rust/Swift/Ruby/PHP, JS/TS `const`,
    # AND Python CLASS-level constants (indented). Add only (name, file, line) not already matched
    # above, so a Python module const found by the richer-value regex is not duplicated. Chunk ONLY
    # files that mention a requested symbol (cheap substring pre-filter — never chunk the whole tree).
    # The column-0 regex above recorded each constant's PRECISE assignment line. Dedup a chunk-lane
    # const against it by RANGE: a chunk span can include a leading comment/decorator, so the chunk
    # is the SAME constant when the regex's line falls inside the chunk's [start, end]. (name, file)-scoped.
    regex_lines: dict[tuple[str, str], list[int]] = {}
    for _lst in matches.values():
        for _m in _lst:
            if _m.get("line") is not None:
                regex_lines.setdefault((_m["name"], str(_m["file"])), []).append(_m["line"])
    chunk_seen: set[tuple[str, str, Any]] = set()
    chunker = server_impl._get_chunker_module()
    const_suffix = getattr(chunker, "_CONST_SECTION_SUFFIX", " [const]")
    # Pre-filter on the LEAF token of each requested symbol too: a qualified query like
    # `Status.OK` is never a literal substring of the source (which has `Status` and `OK`
    # separately), so filtering on the bare leaf lets the file be chunked (1p4q4 review B3).
    prefilter_tokens = symbol_set | {s.rsplit(".", 1)[-1] for s in symbol_set}
    for p in all_files:
        ext = p.suffix.lower()
        fn_name = server_impl._CONST_CHUNKER_BY_EXT.get(ext)
        if fn_name is None:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not any(s in source for s in prefilter_tokens):
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        chunk_fn = getattr(chunker, fn_name, None)
        if chunk_fn is None:
            continue
        try:
            chunks = chunk_fn(source, rel)
        except Exception:
            chunks = None
        for chunk in (chunks or []):
            section = str(getattr(chunk, "section", "") or "")
            if not section.endswith(const_suffix):
                continue
            leaf = section[: -len(const_suffix)].rsplit(" > ", 1)[-1].strip()
            short = leaf.rsplit(".", 1)[-1]
            _clines = list(getattr(chunk, "lines", None) or [])
            start = _clines[0] if _clines else None
            end = _clines[-1] if _clines else start
            ctext = str(getattr(chunk, "text", "") or "")
            decl = ctext.split("\n\n", 1)[-1] if "\n\n" in ctext else ctext
            # Which requested symbols does this const chunk define, and at what line?
            #  (1) the chunk's section leaf — recorded under BOTH its short and qualified form
            #      when each is requested, so `OK` and `Status.OK` both resolve to the member
            #      (1p4q4 review B3); the primary keeps the chunk's [start, end] span.
            #  (2) every requested symbol that HEADS a body line — so a Go grouped `const (...)`
            #      / iota block (ONE chunk, MANY members) resolves each member to its own line,
            #      not just the first (review B2).
            chunk_defs: list[tuple[str, Optional[int], bool]] = []  # (requested_symbol, line, is_primary)
            # Accept the bare leaf, the full qualified name, AND every intermediate dotted suffix
            # (Outer.Inner.x → {x, Inner.x, Outer.Inner.x}) so a natural query naming the immediate
            # enclosing type resolves — not just the leaf or the fully-qualified outermost form
            # (1p5k0; pairs with the chunker nested-type qualification fix).
            _segs = leaf.split(".")
            _forms = [".".join(_segs[k:]) for k in range(len(_segs))]  # full → … → leaf
            for form in _forms:
                if form in symbol_set and all(form != d[0] for d in chunk_defs):
                    chunk_defs.append((form, start, True))
            # Go is the one language whose grouped `const (...)` / iota block stays a SINGLE chunk
            # named after its first member (`_go_const_chunk_name`); scan the body so the OTHER
            # members resolve too. Restricted to Go because Go const values are compile-time scalars
            # (no nested object/dict literals), so a body line head is always a real member — for
            # other languages a multiline value's `KEY: ...` entry could false-positive (review B2).
            if ext == ".go":
                for off, bl in enumerate(decl.split("\n")):
                    s_bl = bl.strip()
                    if not s_bl or server_impl._COMMENT_LINE_RE.match(bl):
                        continue
                    mtok = _re.match(r"[A-Za-z_]\w*", s_bl)
                    if not mtok:
                        continue
                    tok = mtok.group(0)
                    if tok in symbol_set and all(tok != d[0] for d in chunk_defs):
                        chunk_defs.append((tok, (start + off) if start is not None else None, False))
            for dsym, dline, is_primary in chunk_defs:
                prior = regex_lines.get((dsym, rel), [])
                if is_primary:
                    if start is not None and any(start <= L <= end for L in prior):
                        continue  # same constant the column-0 regex already returned (its richer value kept)
                elif dline is not None and any(L == dline for L in prior):
                    continue
                if (dsym, rel, dline) in chunk_seen:
                    continue
                chunk_seen.add((dsym, rel, dline))
                value, kind = _extract_const_value(decl, dsym.rsplit(".", 1)[-1])
                matches.setdefault(dsym, []).append(
                    {"name": dsym, "value": value, "file": rel, "line": dline, "kind": kind}
                )

    # Assemble results in input order; emit all matches per symbol, or null if none
    results: list[dict[str, Any]] = []
    for sym in symbols:
        sym_matches = matches.get(sym, [])
        if sym_matches:
            results.extend(sym_matches)
        else:
            results.append({"name": sym, "value": None, "file": None, "line": None, "kind": None})

    matched_count = sum(1 for r in results if r["value"] is not None)
    return server_impl._response(
        "ok",
        {"symbols": symbols, "matched": matched_count, "results": results},
        next_tools=["code_read"],
        usage="code_read(path='...', start_line=N, end_line=N+5)",
    )

def code_pattern_response(
    root: Path,
    pattern: str,
    glob: str = "",
    limit: int = 50,
    ignore_case: bool = False,
    max_results: Optional[int] = None,
) -> dict[str, Any]:
    """Regex pattern search across repository files.

    Skips files larger than ``_PATTERN_MAX_FILE_BYTES`` (1 MB) as a ReDoS
    mitigation — per-line ``re.search()`` is unbounded within a single line,
    so large generated files are excluded to prevent latency spikes from
    pathological patterns. Callers using pathological patterns against
    small files bear that risk themselves.

    Wave 1p3dk: ``limit`` is canonical (matches ``code_keyword`` /
    ``code_references`` convention). ``max_results`` is accepted as a
    backward-compat alias — when both are passed, ``max_results`` wins
    (operator-explicit value over the default). Pass ``limit=0`` for no cap.
    """
    from wf_server import server_impl
    # Back-compat alias resolution: explicit max_results wins over default limit.
    effective_limit = max_results if max_results is not None else limit
    flags = server_impl.re.IGNORECASE if ignore_case else 0
    try:
        compiled = server_impl.re.compile(pattern, flags)
    except server_impl.re.error as exc:
        return server_impl._response(
            "error", {"pattern": pattern},
            diagnostics=[server_impl._diagnostic("invalid_pattern", f"Invalid regex: {exc}")],
            next_tools=["code_keyword"], usage="code_keyword(query='literal text')",
        )

    try:
        all_files = server_impl._walk_repo_for_navigation(root)
    except Exception as exc:
        return server_impl._response(
            "error", {"pattern": pattern},
            diagnostics=[server_impl._diagnostic("navigation_error", f"File walk failed: {exc}")],
            next_tools=["wf_help"], usage="wf_help()",
        )

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    matches: list[dict[str, Any]] = []
    total = 0
    truncated = False
    unlimited = effective_limit <= 0

    for p in all_files:
        try:
            if p.stat().st_size > server_impl._PATTERN_MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            if compiled.search(line):
                total += 1
                if unlimited or len(matches) < effective_limit:
                    matches.append({"file": rel, "line": lineno, "text": line.rstrip()})
                else:
                    truncated = True

    return server_impl._response(
        "ok",
        {"pattern": pattern, "glob": glob, "matches": matches,
         "truncated": truncated, "total_matches_found": total},
        next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+5)",
    )

def _outline_ts_name(node: Any) -> str:
    """Extract the identifier name from a tree-sitter definition node."""
    from wf_server import server_impl
    for child in node.children:
        if child.type in server_impl._TS_IDENTIFIER_TYPES:
            return child.text.decode("utf-8", errors="replace").strip()
    return ""

def _outline_python(source: str, rel: str) -> dict[str, Any]:
    """Python AST-based outline extraction."""
    from wf_server import server_impl
    try:
        tree = server_impl.ast.parse(source)
    except SyntaxError as exc:
        return server_impl._response("error", {"path": rel},
                         diagnostics=[server_impl._diagnostic("unparseable", f"Python SyntaxError: {exc}")],
                         next_tools=[], usage="")

    def _end(node: ast.AST) -> int:
        return getattr(node, "end_lineno", getattr(node, "lineno", 0))

    def _docstring(node: ast.AST) -> Optional[str]:
        from wf_server import server_impl
        body = getattr(node, "body", [])
        if (body and isinstance(body[0], server_impl.ast.Expr)
                and isinstance(body[0].value, server_impl.ast.Constant)
                and isinstance(body[0].value.value, str)):
            return body[0].value.value.strip().splitlines()[0][:200]
        return None

    symbols: list[dict[str, Any]] = []
    for node in server_impl.ast.iter_child_nodes(tree):
        if isinstance(node, (server_impl.ast.FunctionDef, server_impl.ast.AsyncFunctionDef)):
            symbols.append({"name": node.name, "kind": "function",
                            "start_line": node.lineno, "end_line": _end(node),
                            "docstring": _docstring(node)})
        elif isinstance(node, server_impl.ast.ClassDef):
            symbols.append({"name": node.name, "kind": "class",
                            "start_line": node.lineno, "end_line": _end(node),
                            "docstring": _docstring(node)})
            for child in server_impl.ast.iter_child_nodes(node):
                if isinstance(child, (server_impl.ast.FunctionDef, server_impl.ast.AsyncFunctionDef)):
                    symbols.append({"name": child.name, "kind": "method",
                                    "start_line": child.lineno, "end_line": _end(child),
                                    "docstring": _docstring(child)})
        elif isinstance(node, server_impl.ast.Assign):
            for t in node.targets:
                if isinstance(t, server_impl.ast.Name) and t.id == t.id.upper() and t.id.replace("_", "").isalpha():
                    symbols.append({"name": t.id, "kind": "constant",
                                    "start_line": node.lineno, "end_line": _end(node),
                                    "docstring": None})
        elif isinstance(node, server_impl.ast.AnnAssign):
            if isinstance(node.target, server_impl.ast.Name):
                n = node.target.id
                if n == n.upper() and n.replace("_", "").isalpha():
                    symbols.append({"name": n, "kind": "constant",
                                    "start_line": node.lineno, "end_line": _end(node),
                                    "docstring": None})

    return server_impl._response("ok", {"file": rel, "parser_used": "python_ast", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")

def _outline_treesitter(source: str, rel: str, lang: str, absolute_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Tree-sitter outline. Returns None on any failure so caller can fall through to regex.

    Wave 1p3dk / 1p3hd: ``absolute_path`` is the file's absolute path used as
    cache key. When None, falls back to a fresh parse. When provided, shares
    the parsed tree with every other tree-sitter-consuming MCP tool that
    touches the same file in the same session.
    """
    from wf_server import server_impl
    tree = server_impl._cached_ts_parse(absolute_path, server_impl._TS_SYMBOL_LANG_MAP[lang], source)
    if tree is None:
        return None

    def _entry(node: Any, kind: str) -> Optional[dict[str, Any]]:
        name = _outline_ts_name(node)
        if not name:
            return None
        return {"name": name, "kind": kind,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "docstring": None}

    symbols: list[dict[str, Any]] = []
    for node in tree.root_node.children:
        # Unwrap export_statement (TypeScript/JavaScript top-level exports)
        inner = node
        if node.type == "export_statement":
            for child in node.children:
                if child.type not in ("export", "default", "type"):
                    inner = child
                    break
        # Also unwrap SQL statement wrapper (e.g. statement → create_function)
        elif node.type == "statement":
            for child in node.children:
                if child.type not in (";",):
                    inner = child
                    break
        if inner.type in server_impl._TS_OUTLINE_CLASS_TYPES:
            e = _entry(inner, "class")
            if e:
                symbols.append(e)
            # Walk one level into the class body for methods
            for child in inner.children:
                if child.type in server_impl._TS_OUTLINE_FUNC_TYPES:
                    m = _entry(child, "method")
                    if m:
                        symbols.append(m)
                elif hasattr(child, "children"):
                    for gc in child.children:
                        if gc.type in server_impl._TS_OUTLINE_FUNC_TYPES:
                            m = _entry(gc, "method")
                            if m:
                                symbols.append(m)
        elif inner.type in server_impl._TS_OUTLINE_FUNC_TYPES:
            e = _entry(inner, "function")
            if e:
                symbols.append(e)
        elif inner.type == "lexical_declaration":
            # Arrow function exports: export const fn = async (props) => {}
            for declarator in inner.children:
                if declarator.type == "variable_declarator":
                    value = next(
                        (c for c in declarator.children if c.type == "arrow_function"), None
                    )
                    if value:
                        name_node = next(
                            (c for c in declarator.children if c.type == "identifier"), None
                        )
                        if name_node:
                            symbols.append({
                                "name": name_node.text.decode("utf-8", errors="replace").strip(),
                                "kind": "function",
                                "start_line": inner.start_point[0] + 1,
                                "end_line": inner.end_point[0] + 1,
                                "docstring": None,
                            })

    return server_impl._response("ok", {"file": rel, "parser_used": "tree_sitter", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")

def _outline_regex_tier(source: str, rel: str) -> dict[str, Any]:
    """Regex-based outline for unsupported file types. end_line and docstring are always null."""
    from wf_server import server_impl
    symbols: list[dict[str, Any]] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        m = server_impl._OUTLINE_REGEX.match(line)
        if m:
            kw = m.group(1).lower()
            kind = "class" if kw == "class" else "function"
            symbols.append({"name": m.group(2), "kind": kind,
                            "start_line": lineno, "end_line": None,
                            "docstring": None})
    return server_impl._response("ok", {"file": rel, "parser_used": "regex", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")

def code_outline_response(root: Path, path: str) -> dict[str, Any]:
    """Return a structural symbol map of a source file using a tiered parser.

    Tier 1 — Python AST (for ``.py``).
    Tier 2 — tree-sitter for the 11 languages in ``_TS_SYMBOL_LANG_MAP``.
    Tier 3 — regex fallback for all other file types.
    """
    from wf_server import server_impl
    resolved = server_impl._resolve_repo_path(root, path)
    if resolved is None:
        return server_impl._response("error", {"path": path},
                         diagnostics=[server_impl._diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return server_impl._response("error", {"path": path},
                         diagnostics=[server_impl._diagnostic("file_not_found", f"File '{path}' does not exist.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.is_file():
        return server_impl._response("error", {"path": path},
                         diagnostics=[server_impl._diagnostic("not_a_file", f"'{path}' is a directory.")],
                         next_tools=["code_list_files"], usage=f"code_list_files(glob='{path}/**')")

    root_r = root.resolve()
    rel = str(resolved.relative_to(root_r)).replace("\\", "/")
    lang = server_impl._EXT_TO_LANG.get(resolved.suffix.lower(), "")

    try:
        source = resolved.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as exc:
        return server_impl._response("error", {"path": path},
                         diagnostics=[server_impl._diagnostic("unparseable", f"Cannot read '{path}': {exc}")],
                         next_tools=[], usage="")

    if lang == "python":
        return _outline_python(source, rel)
    if lang in server_impl._TS_SYMBOL_LANG_MAP:
        result = _outline_treesitter(source, rel, lang, absolute_path=resolved.resolve())
        if result is not None:
            return result
    return _outline_regex_tier(source, rel)

def _innermost_symbol(symbols: list[dict[str, Any]], line: int) -> Optional[dict[str, Any]]:
    """Return the innermost (smallest range) symbol that encloses *line*, or None."""
    from wf_server import server_impl
    best: Optional[dict[str, Any]] = None
    best_range: Optional[int] = None
    for sym in symbols:
        sl = sym.get("start_line")
        el = sym.get("end_line")
        if sl is None or el is None:
            continue
        if sl <= line <= el:
            rng = el - sl
            if best_range is None or rng < best_range:
                best = sym
                best_range = rng
    return best

def _hover_python(source: str, line: int) -> Optional[dict[str, Any]]:
    """Find the symbol enclosing *line* in a Python source file."""
    from wf_server import server_impl
    try:
        outline_resp = _outline_python(source, "<hover>")
        if outline_resp.get("status") != "ok":
            return None
        symbols = outline_resp["data"]["symbols"]
        sym = _innermost_symbol(symbols, line)
        if sym is None:
            return None
        # Re-parse to extract signature
        try:
            tree = server_impl.ast.parse(source)
        except SyntaxError:
            return {**sym, "signature": None}
        target_name = sym["name"]
        target_line = sym["start_line"]
        matched_node = None
        for node in server_impl.ast.walk(tree):
            if isinstance(node, (server_impl.ast.FunctionDef, server_impl.ast.AsyncFunctionDef, server_impl.ast.ClassDef)):
                if node.name == target_name and node.lineno == target_line:
                    matched_node = node
                    break
        if matched_node is None:
            return {**sym, "signature": None}
        if isinstance(matched_node, server_impl.ast.ClassDef):
            return {**sym, "signature": None}
        # Build signature for function/async function
        fn = matched_node
        args = fn.args
        params: list[str] = []
        # Build positional args with annotations and defaults
        all_args = []
        if args.posonlyargs:
            all_args.extend(args.posonlyargs)
        all_args.extend(args.args)
        # Defaults are right-aligned in all_args
        n_defaults = len(args.defaults)
        n_all = len(all_args)
        for i, arg in enumerate(all_args):
            s = arg.arg
            if arg.annotation is not None:
                try:
                    s += ": " + server_impl.ast.unparse(arg.annotation)
                except AttributeError:
                    pass
            default_idx = i - (n_all - n_defaults)
            if default_idx >= 0:
                try:
                    s += " = " + server_impl.ast.unparse(args.defaults[default_idx])
                except AttributeError:
                    pass
            params.append(s)
        if args.vararg:
            s = "*" + args.vararg.arg
            if args.vararg.annotation is not None:
                try:
                    s += ": " + server_impl.ast.unparse(args.vararg.annotation)
                except AttributeError:
                    pass
            params.append(s)
        if args.kwonlyargs:
            if not args.vararg:
                params.append("*")
            for i, arg in enumerate(args.kwonlyargs):
                s = arg.arg
                if arg.annotation is not None:
                    try:
                        s += ": " + server_impl.ast.unparse(arg.annotation)
                    except AttributeError:
                        pass
                if args.kw_defaults[i] is not None:
                    try:
                        s += " = " + server_impl.ast.unparse(args.kw_defaults[i])
                    except AttributeError:
                        pass
                params.append(s)
        if args.kwarg:
            s = "**" + args.kwarg.arg
            if args.kwarg.annotation is not None:
                try:
                    s += ": " + server_impl.ast.unparse(args.kwarg.annotation)
                except AttributeError:
                    pass
            params.append(s)
        sig = "(" + ", ".join(params) + ")"
        if fn.returns is not None:
            try:
                sig += " -> " + server_impl.ast.unparse(fn.returns)
            except AttributeError:
                pass
        return {**sym, "signature": sig}
    except Exception:
        return None

def _hover_treesitter(source: str, line: int, lang: str, absolute_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Find the symbol enclosing *line* in a tree-sitter-supported source file.

    Wave 1p3dk / 1p3hd: ``absolute_path`` keyed into the shared cache so a
    hover query reuses a parse done earlier in the session by `code_outline`
    or `code_read`'s structural block.
    """
    from wf_server import server_impl
    try:
        outline_resp = _outline_treesitter(source, "<hover>", lang, absolute_path=absolute_path)
        if outline_resp is None or outline_resp.get("status") != "ok":
            return None
        symbols = outline_resp["data"]["symbols"]
        sym = _innermost_symbol(symbols, line)
        if sym is None:
            return None
        # Re-parse to extract raw parameter text. Wave 1p3hd: shared cache —
        # this typically hits the same parse that `_outline_treesitter` just
        # made when called from the same `code_hover_response` invocation.
        try:
            tree = server_impl._cached_ts_parse(absolute_path, server_impl._TS_SYMBOL_LANG_MAP[lang], source)
            if tree is None:
                return {**sym, "signature": None}
        except Exception:
            return {**sym, "signature": None}
        target_start = sym["start_line"]
        signature: Optional[str] = None

        def _walk_for_func(node: Any) -> Optional[Any]:
            from wf_server import server_impl
            if node.start_point[0] + 1 == target_start and node.type in server_impl._TS_OUTLINE_FUNC_TYPES:
                return node
            for child in node.children:
                found = _walk_for_func(child)
                if found is not None:
                    return found
            return None

        func_node = _walk_for_func(tree.root_node)
        if func_node is not None:
            for child in func_node.children:
                if child.type == "parameters" or child.type == "formal_parameters":
                    signature = child.text.decode("utf-8", errors="replace").strip()
                    break
        return {**sym, "signature": signature}
    except Exception:
        return None

def _hover_regex(source: str, line: int) -> Optional[dict[str, Any]]:
    """Find the nearest preceding symbol to *line* using regex outline."""
    try:
        outline_resp = _outline_regex_tier(source, "<hover>")
        symbols = outline_resp["data"]["symbols"]
        best = None
        for sym in symbols:
            sl = sym.get("start_line")
            if sl is not None and sl <= line:
                best = sym
        if best is None:
            return None
        return {**best, "signature": None}
    except Exception:
        return None

def code_hover_response(root: Path, path: str, line: int) -> dict[str, Any]:
    """Return the symbol enclosing a given 1-based line number."""
    from wf_server import server_impl
    resolved = server_impl._resolve_repo_path(root, path)
    if resolved is None:
        return server_impl._response("error", {"path": path, "line": line},
                         diagnostics=[server_impl._diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return server_impl._response("error", {"path": path, "line": line},
                         diagnostics=[server_impl._diagnostic("file_not_found", f"File '{path}' does not exist.")],
                         next_tools=["code_list_files"], usage="code_list_files()")

    root_r = root.resolve()
    rel = str(resolved.relative_to(root_r)).replace("\\", "/")

    try:
        source = resolved.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as exc:
        return server_impl._response("ok", {"file": rel, "line": line, "symbol": None, "parser_used": "none"},
                         diagnostics=[server_impl._diagnostic("unparseable", f"Cannot read '{path}': {exc}")])

    lang = server_impl._EXT_TO_LANG.get(resolved.suffix.lower(), "")
    symbol: Optional[dict[str, Any]] = None
    parser_used = "regex"

    try:
        if lang == "python":
            parser_used = "python_ast"
            symbol = _hover_python(source, line)
        elif lang in server_impl._TS_SYMBOL_LANG_MAP:
            parser_used = "tree_sitter"
            symbol = _hover_treesitter(source, line, lang, absolute_path=resolved.resolve())
            if symbol is None:
                parser_used = "regex"
                symbol = _hover_regex(source, line)
        else:
            symbol = _hover_regex(source, line)
    except Exception:
        symbol = None

    return server_impl._response("ok", {"file": rel, "line": line, "symbol": symbol, "parser_used": parser_used})

def _sql_schema_retry_symbol(symbol: str) -> Optional[str]:
    symbol_s = symbol.strip()
    if "." not in symbol_s:
        return None
    retry = symbol_s.rsplit(".", 1)[-1].strip()
    return retry if retry and retry != symbol_s else None

def _sql_schema_doc_mention_refs(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Return doc/mention hits for a schema-qualified SQL symbol using the bare name."""
    from wf_server import server_impl
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if retry_symbol is None:
        return []
    refs: list[dict[str, Any]] = []
    for ref in server_impl._non_python_references(root, retry_symbol):
        if ref.get("reference_kind") in {"docs", "mention"}:
            ref["sql_query_symbol"] = retry_symbol
            refs.append(ref)
    return refs

def _definition_match_kind(name: str, symbol: str) -> str:
    return "exact" if name == symbol else "partial"

def _definition_sort_key(defn: dict[str, Any], symbol: str) -> tuple[int, int, int, int, str, int]:
    match_rank = 0 if str(defn.get("name", "")) == symbol else 1
    method_rank = {"ast": 0, "treesitter": 1, "regex": 2, "keyword_fallback": 3}.get(str(defn.get("method", "")), 4)
    language_rank = 0 if str(defn.get("language", "")) == "python" else 1
    kind_rank = {"class": 0, "interface": 1, "enum": 2, "struct": 3, "record": 4, "method": 5, "function": 6, "variable": 7, "symbol": 8}.get(str(defn.get("kind", "symbol")), 9)
    return (
        match_rank,
        method_rank,
        language_rank,
        kind_rank,
        str(defn.get("path", "")),
        int(defn.get("line", 0) or 0),
    )

def _python_definitions(
    root: Path,
    symbol: str,
    *,
    restrict_files: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Find function/class definitions matching *symbol* in Python files via AST.

    When ``restrict_files`` is non-None, the repo walk is skipped entirely — file
    paths are constructed directly from the restriction set (wave 12xr3, 1301h).
    This turns 10s+ cold walks into <50ms direct reads on the common path.
    """
    from wf_server import server_impl
    import ast as _ast
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    if restrict_files is not None:
        files: Iterable[Path] = (root_r / rel for rel in restrict_files)
    else:
        files = server_impl._walk_repo_for_navigation(root)
    for p in files:
        if p.suffix.lower() != ".py":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            tree = _ast.parse(source, filename=str(p))
        except (SyntaxError, OSError):
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for node in _ast.walk(tree):
            name = None
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                name = node.name
            if name and (name == symbol or symbol in name):
                results.append({
                    "path": rel,
                    "line": node.lineno,
                    "kind": type(node).__name__.lower().replace("asyncfunctiondef", "async_function").replace("functiondef", "function").replace("classdef", "class"),
                    "name": name,
                    "language": "python",
                    "method": "ast",
                    "match_kind": _definition_match_kind(name, symbol),
                })
    return results

def _python_references(root: Path, symbol: str, *, restrict_files: frozenset[str] | None = None, _files: list | None = None) -> list[dict[str, Any]]:
    """Find references to *symbol* in Python files via AST call-site detection plus text fallback."""
    from wf_server import server_impl
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    pattern = server_impl._symbol_search_pattern(symbol)
    call_sites_by_path: dict[str, set[int]] = {}
    for ref in server_impl._python_reference_call_sites(root, symbol, restrict_files=restrict_files, _files=_files):
        ref["reference_kind"] = "call_sites"
        ref["method"] = "ast"
        results.append(ref)
        call_sites_by_path.setdefault(ref["path"], set()).add(ref["line"])
    for p in (_files if _files is not None else server_impl._walk_repo_for_navigation(root)):
        if p.suffix.lower() != ".py":
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        if restrict_files is not None and rel not in restrict_files:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        call_site_lines = call_sites_by_path.get(rel, set())
        for lineno, line in enumerate(source.splitlines(), 1):
            if pattern.search(line):
                if lineno in call_site_lines:
                    continue
                results.append({
                    "path": rel,
                    "line": lineno,
                    "snippet": line.rstrip(),
                    "language": "python",
                    "method": "text",
                    "reference_kind": server_impl._text_reference_kind(rel, line, symbol),
                })
    return results

def _treesitter_definition_results(
    root: Path,
    symbol: str,
    *,
    restrict_files: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Find definitions in tree-sitter-backed languages using chunker parse helpers.

    When ``restrict_files`` is non-None, the repo walk is skipped — file paths are
    constructed directly from the restriction set.
    """
    from wf_server import server_impl
    chunker = server_impl._get_chunker_module()
    by_language = {
        "javascript": chunker.chunk_js_ts_treesitter,
        "typescript": chunker.chunk_js_ts_treesitter,
        "java": chunker.chunk_java_treesitter,
        "csharp": chunker.chunk_csharp_treesitter,
        "sql": chunker.chunk_sql,
    }
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    if restrict_files is not None:
        files: Iterable[Path] = (root_r / rel for rel in restrict_files)
    else:
        files = server_impl._walk_repo_for_navigation(root)
    for p in files:
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lang = server_impl._detect_language(rel)
        if lang not in server_impl._TREE_SITTER_DEFINITION_LANGS:
            continue
        chunk_fn = by_language.get(lang)
        if chunk_fn is None:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            chunks = chunk_fn(source, rel)
        except Exception:
            continue
        if not chunks:
            continue
        for chunk in chunks:
            if getattr(chunk, "kind", None) != "code":
                continue
            chunk_id = getattr(chunk, "id", "")
            if not chunk_id.startswith(f"{rel}::"):
                continue
            local_id = chunk_id.split("::", 1)[1]
            section = getattr(chunk, "section", "")
            line = getattr(chunk, "lines", (1, 1))[0]
            match_name = local_id
            kind = "symbol"
            if local_id.endswith(".__decl__"):
                match_name = local_id[: -len(".__decl__")]
                if lang in {"java", "csharp"}:
                    kind = "class"
                elif lang == "sql":
                    kind = "object"
                else:
                    kind = "class"
            elif "." in local_id:
                match_name = local_id.split(".")[-1]
                kind = "method"
            else:
                kind = "object" if lang == "sql" else "function"
            if (lang == "sql" and server_impl._sql_symbol_matches(match_name, symbol)) or match_name == symbol or symbol in match_name:
                results.append({
                    "path": rel,
                    "line": line,
                    "kind": kind,
                    "name": match_name,
                    "language": lang,
                    "method": "treesitter",
                    "section": section,
                    "match_kind": _definition_match_kind(match_name, symbol),
                })
    return results

def _regex_definitions(
    root: Path,
    symbol: str,
    *,
    restrict_files: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Find structural definitions in supported languages via regex (non-AST path).

    When ``restrict_files`` is non-None, the repo walk is skipped — file paths are
    constructed directly from the restriction set.
    """
    from wf_server import server_impl
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    if restrict_files is not None:
        files: Iterable[Path] = (root_r / rel for rel in restrict_files)
    else:
        files = server_impl._walk_repo_for_navigation(root)
    for p in files:
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lang = server_impl._detect_language(str(p))
        patterns = server_impl._DEFINITION_PATTERNS.get(lang)
        if not patterns:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            for kind, pattern in patterns:
                match = pattern.match(stripped)
                if not match:
                    continue
                name = match.group(1)
                if name == symbol or symbol in name:
                    results.append({
                        "path": rel,
                        "line": lineno,
                        "kind": kind,
                        "name": name,
                        "language": lang,
                        "method": "regex",
                        "match_kind": _definition_match_kind(name, symbol),
                    })
                break
    return results

def _css_definitions(
    root: Path,
    symbol: str,
    *,
    restrict_files: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Find CSS/SCSS class, ID, custom-property, keyframe, and mixin definitions.

    When ``restrict_files`` is non-None, the repo walk is skipped — file paths are
    constructed directly from the restriction set.
    """
    from wf_server import server_impl
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    structural_patterns = (
        ("custom-property", server_impl._CSS_PROP_RE),
        ("keyframes",       server_impl._CSS_KEYFRAME_RE),
        ("mixin",           server_impl._CSS_MIXIN_RE),
    )
    if restrict_files is not None:
        files: Iterable[Path] = (root_r / rel for rel in restrict_files)
    else:
        files = server_impl._walk_repo_for_navigation(root)
    for p in files:
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lang = server_impl._detect_language(str(p))
        if lang not in {"css", "scss"}:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            # Custom property / @keyframes / @mixin — anchored at line start
            matched_structural = False
            for kind, pat in structural_patterns:
                m = pat.match(stripped)
                if m:
                    matched_structural = True
                    name = m.group(1)
                    if name == symbol or symbol in name:
                        results.append({
                            "path": rel, "line": lineno, "kind": kind, "name": name,
                            "language": lang, "method": "regex",
                            "match_kind": _definition_match_kind(name, symbol),
                        })
                    break
            if matched_structural:
                continue
            # Class and ID selectors — only on lines that open a rule block
            if "{" not in stripped:
                continue
            for kind, pat in (("class", server_impl._CSS_CLASS_RE), ("id", server_impl._CSS_ID_RE)):
                for m in pat.finditer(stripped):
                    name = m.group(1)
                    if name == symbol or symbol in name:
                        results.append({
                            "path": rel, "line": lineno, "kind": kind, "name": name,
                            "language": lang, "method": "regex",
                            "match_kind": _definition_match_kind(name, symbol),
                        })
                        break
    return results

def _keyword_fallback_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Broad keyword fallback for unsupported or unmatched languages."""
    from wf_server import server_impl
    results = []
    root_r = root.resolve()
    pattern = server_impl._symbol_search_pattern(symbol)
    for p in server_impl._walk_repo_for_navigation(root):
        if len(results) >= server_impl._KEYWORD_FALLBACK_RESULT_CAP:
            break
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            if pattern.search(line):
                results.append({
                    "path": rel,
                    "line": lineno,
                    "snippet": line.rstrip(),
                    "language": server_impl._detect_language(rel),
                    "method": "keyword_fallback",
                    "match_kind": "exact" if pattern.search(line) and server_impl.re.search(rf"\b{server_impl.re.escape(symbol)}\b", line) else "partial",
                })
                if len(results) >= server_impl._KEYWORD_FALLBACK_RESULT_CAP:
                    break
    return results

def _dedupe_navigation_results(results: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Deduplicate navigation hits while preserving the earliest/strongest entry order."""
    from wf_server import server_impl
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in results:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped

def _reference_counts(refs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    for ref in refs:
        counts[_reference_bucket(str(ref.get("reference_bucket", ref.get("reference_kind", "other"))))] += 1
    return counts

def _reference_bucket(kind: str) -> str:
    if kind == "call_sites":
        return "call_sites"
    if kind == "tests":
        return "tests"
    if kind == "docs":
        return "docs"
    return "other"

def _reference_sort_key(ref: dict[str, Any]) -> tuple[int, int, int, str, int, str]:
    kind_rank = {
        "call_sites": 0,
        "definition": 1,
        "import": 2,
        "mention": 3,
        "other": 4,
        "docs": 5,
        "tests": 6,
    }.get(str(ref.get("reference_kind", "other")), 4)
    language_rank = 0 if ref.get("language") == "python" else 1
    method_rank = 0 if str(ref.get("method", "")).startswith("treesitter") else 1
    return (
        kind_rank,
        language_rank,
        method_rank,
        str(ref.get("path", "")),
        int(ref.get("line", 0) or 0),
        str(ref.get("snippet", "")),
    )

def _reference_detail_counts(refs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    for ref in refs:
        kind = str(ref.get("reference_kind", "other"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts

def _apply_reference_filters(
    refs: list[dict[str, Any]],
    *,
    exclude_tests: bool = False,
    exclude_docs: bool = False,
    call_sites_only: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
    """Normalize reference kinds, sort by signal, and apply optional filters."""
    from wf_server import server_impl
    all_counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    filtered_counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    detail_all_counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    detail_filtered_counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    filtered: list[dict[str, Any]] = []
    for ref in refs:
        detail_kind = str(ref.get("reference_kind", "other"))
        broad_kind = _reference_bucket(detail_kind)
        ref["reference_kind"] = detail_kind
        ref["reference_bucket"] = broad_kind
        all_counts[broad_kind] += 1
        detail_all_counts[detail_kind] = detail_all_counts.get(detail_kind, 0) + 1
        if call_sites_only and broad_kind != "call_sites":
            continue
        if exclude_tests and broad_kind == "tests":
            continue
        if exclude_docs and broad_kind == "docs":
            continue
        filtered_counts[broad_kind] += 1
        detail_filtered_counts[detail_kind] = detail_filtered_counts.get(detail_kind, 0) + 1
        filtered.append(ref)
    filtered.sort(key=_reference_sort_key)
    return filtered, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts

def _graph_definition_candidate_files(root: Path, symbol: str) -> frozenset[str] | None:
    """Return candidate file set from graph nodes whose label/id matches symbol.

    Returns:
        - ``None`` when the graph index is absent or fails to load — signals caller to
          fall back to full repo walk.
        - ``frozenset()`` (empty) when graph is present but no nodes match — caller
          should also fall back, since the symbol may be in code added since the last
          graph build.
        - A non-empty frozenset of repo-relative ``source_file`` paths when graph
          candidates match. Mirrors the scanner predicate ``name == symbol or
          symbol in name`` so substring queries still resolve.

    Implementation of wave 12xr3 / 1301h: short-circuits the four-pass full repo walk
    for the common case where the symbol is in the graph.
    """
    from wf_server import server_impl
    try:
        gq = server_impl._load_graph_query()
        index = gq.get_query_index(root, layer="project")
    except Exception:
        return None
    if not index.present:
        return None
    suffix_key = f"::{symbol}"
    files: set[str] = set()
    for nid, node in index._node_by_id.items():
        label = str(node.get("label") or "")
        # Mirror scanner predicate: exact match, suffix on id, or substring on label
        if label == symbol or nid.endswith(suffix_key) or symbol in label:
            sf = node.get("source_file")
            if isinstance(sf, str) and sf:
                files.add(sf)
    return frozenset(files)

def code_definition_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find definition(s) for a symbol across all supported languages using best available parser."""
    from wf_server import server_impl
    symbol = symbol_or_path_position.strip()
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if not symbol:
        return server_impl._response("error", {"symbol": symbol}, diagnostics=[server_impl._diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword"], usage="code_keyword(query='MyClass')")
    # Wave 12xr3 / 1301h: consult the graph to narrow the file set before scanning.
    candidate_files = _graph_definition_candidate_files(root, symbol)
    graph_present = candidate_files is not None
    if not graph_present:
        # Graph never built — emit an advisory diagnostic but degrade gracefully.
        # The pre-1301h full structural walk was 40+s (4 × walk_repo); we skip it
        # and go straight to the keyword fallback (single walk, ~10s) so the
        # response is bounded. Operators see the diagnostic and can run
        # index_build(content='graph') to enable the fast path on next call.
        graph_missing_diagnostic = server_impl._diagnostic(
            "graph_index_missing_degraded",
            "Graph index is not built. `code_definition` is running in degraded mode (keyword fallback, ~10s). For sub-300ms lookups, run `index_build(content='graph')` once.",
            recovery_tools=["index_build"],
            recovery_usage="index_build(content='graph', mode='create')",
        )
        lookup_method = "graph_index_missing_degraded"
    else:
        graph_missing_diagnostic = None
        lookup_method = "graph_narrowed" if candidate_files else "graph_refresh_pending"
    # When the graph is present but had no match, try a cheap incremental
    # graph update — recently-added code is a common case and refresh is ~4ms
    # when nothing has changed. Skip when graph was absent entirely.
    refresh_attempted = False
    if graph_present and not candidate_files:
        try:
            server_impl.index_build_response(root, content="graph", mode="update")
            refresh_attempted = True
            # Known rewrite: drop the cached index so the re-read reloads even
            # on a same-(mtime_ns, size) rewrite (coarse-mtime filesystems).
            try:
                server_impl._load_graph_query().invalidate_query_index_cache(root)
            except Exception:
                pass
            refreshed = _graph_definition_candidate_files(root, symbol)
            if refreshed:
                candidate_files = refreshed
                lookup_method = "graph_narrowed_after_refresh"
        except Exception:
            # Refresh attempt is best-effort; if it fails, fall through to definitive-not-found
            pass
    # When the graph is present and the incremental refresh confirmed no match,
    # the graph is the source of truth — skip the structural full walk and the
    # keyword fallback. Return a fast not-found response with a clear recovery hint.
    if refresh_attempted and not candidate_files:
        # Wave 1p2q3 (1p2qb): mirror code_callhierarchy's suggestions field on miss.
        # Operators chaining the two tools expect parallel recovery affordances —
        # a near-match suggestion helps recover from typos or stale names without
        # falling back to keyword search blindly.
        suggestions: list[dict[str, Any]] = []
        attribution_counts: dict[str, dict[str, int]] = {}
        try:
            gq = server_impl._load_graph_query()
            sugg_index = gq.get_query_index(root, layer="project")
            if sugg_index.present:
                suggestions = server_impl._suggest_near_symbols(sugg_index, symbol)
                # Wave 1p2q3 (1p2q9 B): when the graph spoke (definitive-not-found),
                # surface per-language attribution from the full graph so operators
                # can tell whether the empty result reflects a real absence or a
                # per-language coverage gap (e.g. typescript receiver-resolved=0).
                attribution_counts = server_impl._compute_attribution_counts_by_language(list(sugg_index.edges), sugg_index)
        except Exception:
            suggestions = []
            attribution_counts = {}
        return server_impl._response(
            "ok",
            {
                "symbol": symbol,
                "definitions": [],
                "method": "graph_definitive_not_found",
                "lookup_method": "graph_definitive_not_found",
                "suggestions": suggestions,
                "attribution_counts_by_language": attribution_counts,
            },
            diagnostics=[server_impl._diagnostic(
                "not_found",
                f"No definition for '{symbol}' in the project graph (refreshed). If the symbol is in a file type the graph does not index, fall back to code_keyword.",
                recovery_tools=["code_keyword"],
                recovery_usage=f"code_keyword(query={symbol!r})",
            )],
            next_tools=["code_keyword"],
            usage=f"code_keyword(query={symbol!r})",
        )
    # When graph is absent, fall back to the pre-1301h structural full walk so the
    # tests and callers that rely on `name`-bearing structural definitions still
    # work. The advisory diagnostic above ("graph_index_missing_degraded") tells
    # the operator to run index_build(content='graph') to switch to the fast
    # graph-narrowed path.
    restrict = candidate_files if candidate_files else None
    try:
        python_definitions = _python_definitions(root, symbol, restrict_files=restrict)
        treesitter_definitions = _treesitter_definition_results(root, symbol, restrict_files=restrict)
        regex_definitions = _regex_definitions(root, symbol, restrict_files=restrict)
        css_definitions = _css_definitions(root, symbol, restrict_files=restrict)
    except Exception as exc:
        return server_impl._response("error", {"symbol": symbol, "lookup_method": lookup_method}, diagnostics=[server_impl._diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    definitions = _dedupe_navigation_results(
        python_definitions + treesitter_definitions + regex_definitions + css_definitions,
        ("path", "line", "language", "name"),
    )
    note = None
    if not definitions and retry_symbol is not None:
        retry_candidates = _graph_definition_candidate_files(root, retry_symbol)
        retry_restrict = retry_candidates if retry_candidates else None
        if retry_candidates is not None and not retry_candidates:
            lookup_method = "full_walk"  # retry path falls through full-walk too
        try:
            python_definitions = _python_definitions(root, retry_symbol, restrict_files=retry_restrict)
            treesitter_definitions = _treesitter_definition_results(root, retry_symbol, restrict_files=retry_restrict)
            regex_definitions = _regex_definitions(root, retry_symbol, restrict_files=retry_restrict)
            css_definitions = _css_definitions(root, retry_symbol, restrict_files=retry_restrict)
        except Exception as exc:
            return server_impl._response("error", {"symbol": symbol, "lookup_method": lookup_method}, diagnostics=[server_impl._diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
        definitions = _dedupe_navigation_results(
            python_definitions + treesitter_definitions + regex_definitions + css_definitions,
            ("path", "line", "language", "name"),
        )
        if definitions:
            note = f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'."
    definitions.sort(key=lambda d: _definition_sort_key(d, symbol))
    if definitions:
        languages = sorted({d.get("language") for d in definitions if d.get("language")})
        definition_methods = {d.get("method") for d in definitions}
        method = "multi_language"
        structural_diagnostics = [graph_missing_diagnostic] if graph_missing_diagnostic is not None else []
        # Wave 1p2q3 (1p2q9 B): empty per-language counts on the found-definition
        # path — `code_definition` doesn't surface graph edges in this response,
        # so the diagnostic is consistently `{}` here. Operators wanting per-
        # language attribution should call `wf_graph_report`.
        _attr_empty: dict[str, dict[str, int]] = {}
        if definition_methods == {"ast"}:
            return server_impl._response(
                "ok",
                {"symbol": symbol, "language": "python", "definitions": definitions, "supported_languages": sorted(server_impl._SUPPORTED_DEFINITION_LANGS), "method": "ast", "lookup_method": lookup_method, "attribution_counts_by_language": _attr_empty, **({"note": note} if note else {})},
                diagnostics=structural_diagnostics,
                next_tools=["code_read"],
                usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
            )
        if definition_methods == {"treesitter"}:
            method = "treesitter"
        elif definition_methods == {"regex"}:
            method = "regex"
        return server_impl._response(
            "ok",
                {
                    "symbol": symbol,
                    "definitions": definitions,
                    "supported_languages": sorted(server_impl._SUPPORTED_DEFINITION_LANGS),
                    "method": method,
                    "languages": languages,
                    "lookup_method": lookup_method,
                    "attribution_counts_by_language": _attr_empty,
                    **({"note": note} if note else {}),
                },
                diagnostics=structural_diagnostics,
                next_tools=["code_read"],
                usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
            )
    fallback_symbol = retry_symbol or symbol
    # No structural definitions found — run keyword fallback across all files.
    try:
        fallback = _keyword_fallback_definitions(root, fallback_symbol)
    except Exception as exc:
        return server_impl._response("error", {"symbol": symbol, "lookup_method": lookup_method}, diagnostics=[server_impl._diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    fallback_diagnostics: list[dict[str, Any]] = []
    if graph_missing_diagnostic is not None:
        fallback_diagnostics.append(graph_missing_diagnostic)
    fallback_lookup_method = lookup_method if not graph_present else "keyword_fallback"
    if not fallback:
        fallback_diagnostics.append(server_impl._diagnostic("not_found", f"No definition found for '{symbol}' in any language.", recovery_tools=["code_keyword"], recovery_usage=f"code_keyword(query={symbol!r})"))
        return server_impl._response(
            "ok",
            {"symbol": symbol, "definitions": [], "method": "keyword_fallback", "lookup_method": fallback_lookup_method, "attribution_counts_by_language": {}},
            diagnostics=fallback_diagnostics,
            next_tools=["code_keyword"],
            usage=f"code_keyword(query={symbol!r})",
        )
    return server_impl._response(
        "ok",
        {"symbol": symbol, "definitions": fallback, "method": "keyword_fallback", "lookup_method": fallback_lookup_method, "attribution_counts_by_language": {}, "note": note or (f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'." if retry_symbol else "No structural definition matcher found a result. Returning broad keyword matches across the repo.")},
        diagnostics=fallback_diagnostics,
        next_tools=["code_read"],
        usage=f"code_read(path={fallback[0]['path']!r}, start_line={fallback[0]['line']}, end_line={fallback[0]['line'] + 20})",
    )

def _graph_constant_reader_refs(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Wave 1p4ls: graph-confirmed readers of a CONSTANT, as reference entries tagged
    ``reference_kind="reads"`` — DISTINCT from ``call_sites`` (callers). These are functions that
    read the constant's value, bound by the faithfulness-gated ``reads`` edge (never a coincidental
    same-name twin). Empty unless the symbol resolves to a ``kind="constant"`` node."""
    from wf_server import server_impl
    try:
        gq = server_impl._load_graph_query()
        index = gq.get_query_index(root, layer="project")
        if not index.present:
            return []
        node_id = index.resolve_symbol(symbol)
        if node_id is None:
            return []
        if (index.get_node(node_id) or {}).get("kind") != "constant":
            return []
        out: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for edge in index._in.get(node_id, []):
            if edge.get("relation") != "reads":
                continue
            src = edge.get("source")
            if not isinstance(src, str) or src.startswith("external::"):
                continue
            reader = index.get_node(src) or {}
            sf = reader.get("source_file")
            if not isinstance(sf, str) or not sf:
                continue
            loc = str(reader.get("source_location") or "")
            head = loc.split(":", 1)[0]
            line = int(head) if head.isdigit() else 0
            if (sf, line) in seen:
                continue
            seen.add((sf, line))
            snippet = ""
            try:
                fp = root / sf
                if line > 0 and fp.is_file():
                    snippet = fp.read_text(encoding="utf-8", errors="replace").splitlines()[line - 1].strip()[:200]
            except Exception:
                snippet = ""
            out.append({
                "path": sf,
                "line": line,
                "snippet": snippet,
                "language": server_impl._detect_language(sf),
                "method": "graph_reads",
                "reference_kind": "reads",
                "name": reader.get("label") or src.split("::")[-1],
            })
        return out
    except Exception:
        return []

def code_references_response(
    root: Path,
    symbol_or_path_position: str,
    *,
    exclude_tests: bool = False,
    exclude_docs: bool = False,
    call_sites_only: bool = False,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Find references to a symbol across known code languages with structural call-site detection where available."""
    from wf_server import server_impl
    symbol = symbol_or_path_position.strip()
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if not symbol:
        return server_impl._response("error", {"symbol": symbol}, diagnostics=[server_impl._diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword"], usage="code_keyword(query='my_func')")
    if limit is not None and limit < 0:
        return server_impl._response("error", {"symbol": symbol, "limit": limit}, diagnostics=[server_impl._diagnostic("invalid_arguments", "limit must be a non-negative integer or omitted.")], next_tools=["code_help"], usage="code_help()")
    restrict_files = _graph_references_candidate_files(root, symbol)
    # Wave 1304x / 1304r: refresh-then-recheck on graph miss before falling through to walk.
    if restrict_files is None:
        refreshed = server_impl._graph_refresh_then_recheck(root, lambda: _graph_references_candidate_files(root, symbol))
        if refreshed is not None:
            restrict_files = refreshed
    # When graph gives candidate files, build the Path list once — avoids 4× repo walks
    _ref_files: list | None = (
        [root / rel for rel in sorted(restrict_files) if (root / rel).is_file()]
        if restrict_files is not None else None
    )
    try:
        python_refs = _python_references(root, symbol, restrict_files=restrict_files, _files=_ref_files)
        treesitter_refs = server_impl._treesitter_references(root, symbol, restrict_files=restrict_files, _files=_ref_files)
        other_refs = server_impl._non_python_references(root, symbol, restrict_files=restrict_files, _files=_ref_files)
    except Exception as exc:
        return server_impl._response("error", {"symbol": symbol}, diagnostics=[server_impl._diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    refs = _dedupe_navigation_results(
        python_refs + treesitter_refs + other_refs,
        ("path", "line", "language", "snippet"),
    )
    note = None
    sql_doc_refs = _sql_schema_doc_mention_refs(root, symbol)
    if sql_doc_refs:
        refs = _dedupe_navigation_results(
            refs + sql_doc_refs,
            ("path", "line", "language", "snippet"),
        )
        note = f"Included docs and mention matches from schema-stripped SQL symbol '{_sql_schema_retry_symbol(symbol)}'."
    # Wave 1p4ls: graph-confirmed CONSTANT readers as a distinct `reads` bucket (functions that
    # read the constant's value) — faithfulness-gated, never merged into `call_sites` (callers).
    reads_refs = _graph_constant_reader_refs(root, symbol)
    if reads_refs:
        refs = _dedupe_navigation_results(refs + reads_refs, ("path", "line", "language", "snippet"))
    if refs:
        refs, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts = _apply_reference_filters(
            refs,
            exclude_tests=exclude_tests,
            exclude_docs=exclude_docs,
            call_sites_only=call_sites_only,
        )
        matched_count = len(refs)
        matched_counts = dict(filtered_counts)
        if limit is not None and limit > 0:
            refs = refs[:limit]
        returned_counts = _reference_counts(refs)
        detail_returned_counts = _reference_detail_counts(refs)
        languages = sorted({r.get("language") for r in refs if r.get("language")})
        ref_methods = {r.get("method") for r in refs}
        method = "multi_language"
        broad_buckets = {
            "call_sites": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
            "other": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "other"],
            "docs": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "docs"],
            "tests": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "tests"],
        }
        detail_buckets = {
            "call_sites": [r for r in refs if r["reference_kind"] == "call_sites"],
            "definition": [r for r in refs if r["reference_kind"] == "definition"],
            "import": [r for r in refs if r["reference_kind"] == "import"],
            "mention": [r for r in refs if r["reference_kind"] == "mention"],
            "reads": [r for r in refs if r["reference_kind"] == "reads"],
            "docs": [r for r in refs if r["reference_kind"] == "docs"],
            "tests": [r for r in refs if r["reference_kind"] == "tests"],
            "other": [r for r in refs if r["reference_kind"] == "other"],
        }
        if languages == ["python"] and ref_methods.issubset({"ast", "text"}):
            return server_impl._response(
                "ok",
                {
                    "symbol": symbol,
                    "language": "python",
                    "count": len(refs),
                    "matched_count": matched_count,
                    "total_count": sum(all_counts.values()),
                    "counts": returned_counts,
                    "matched_counts": matched_counts,
                    "all_counts": all_counts,
                    "detail_counts": detail_returned_counts,
                    "detail_matched_counts": detail_filtered_counts,
                    "detail_all_counts": detail_all_counts,
                    "references": refs,
                    "buckets": broad_buckets,
                    "detail_buckets": detail_buckets,
                    "method": "ast",
                    "supported_languages": sorted(server_impl._SUPPORTED_REFERENCE_LANGS),
                    "exclude_tests": exclude_tests,
                    "exclude_docs": exclude_docs,
                    "call_sites_only": call_sites_only,
                    "limit": limit,
                    "graph_assisted": restrict_files is not None,
                },
                next_tools=["code_read"],
                usage=f"code_read(path='...', start_line=N, end_line=N+20)",
            )
        if all(str(m).startswith("treesitter") for m in ref_methods):
            method = "treesitter"
        elif ref_methods == {"text"}:
            method = "text"
        return server_impl._response(
            "ok",
            {
                "symbol": symbol,
                "count": len(refs),
                "matched_count": matched_count,
                "total_count": sum(all_counts.values()),
                "counts": returned_counts,
                "matched_counts": matched_counts,
                "all_counts": all_counts,
                "detail_counts": detail_returned_counts,
                "detail_matched_counts": detail_filtered_counts,
                "detail_all_counts": detail_all_counts,
                "references": refs,
                "buckets": broad_buckets,
                "detail_buckets": detail_buckets,
                "method": method,
                "supported_languages": sorted(server_impl._SUPPORTED_REFERENCE_LANGS),
                "languages": languages,
                **({"note": note} if note else {}),
                "exclude_tests": exclude_tests,
                "exclude_docs": exclude_docs,
                "call_sites_only": call_sites_only,
                "limit": limit,
                "graph_assisted": restrict_files is not None,
            },
            next_tools=["code_read"],
            usage=f"code_read(path='...', start_line=N, end_line=N+20)",
        )
    if retry_symbol is not None:
        retry_restrict = _graph_references_candidate_files(root, retry_symbol)
        _retry_files: list | None = (
            [root / rel for rel in sorted(retry_restrict) if (root / rel).is_file()]
            if retry_restrict is not None else None
        )
        try:
            python_refs = _python_references(root, retry_symbol, restrict_files=retry_restrict, _files=_retry_files)
            treesitter_refs = server_impl._treesitter_references(root, retry_symbol, restrict_files=retry_restrict, _files=_retry_files)
            other_refs = server_impl._non_python_references(root, retry_symbol, restrict_files=retry_restrict, _files=_retry_files)
        except Exception as exc:
            return server_impl._response("error", {"symbol": symbol}, diagnostics=[server_impl._diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
        refs = _dedupe_navigation_results(
            python_refs + treesitter_refs + other_refs,
            ("path", "line", "language", "snippet"),
        )
        sql_doc_refs = _sql_schema_doc_mention_refs(root, symbol)
        if sql_doc_refs:
            refs = _dedupe_navigation_results(
                refs + sql_doc_refs,
                ("path", "line", "language", "snippet"),
            )
            note = f"Included docs and mention matches from schema-stripped SQL symbol '{retry_symbol}'."
        if refs:
            if note is None:
                note = f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'."
            refs, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts = _apply_reference_filters(
                refs,
                exclude_tests=exclude_tests,
                exclude_docs=exclude_docs,
                call_sites_only=call_sites_only,
            )
            matched_count = len(refs)
            matched_counts = dict(filtered_counts)
            if limit is not None and limit > 0:
                refs = refs[:limit]
            returned_counts = _reference_counts(refs)
            detail_returned_counts = _reference_detail_counts(refs)
            languages = sorted({r.get("language") for r in refs if r.get("language")})
            ref_methods = {r.get("method") for r in refs}
            method = "multi_language"
            broad_buckets = {
                "call_sites": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
                "other": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "other"],
                "docs": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "docs"],
                "tests": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "tests"],
            }
            detail_buckets = {
                "call_sites": [r for r in refs if r["reference_kind"] == "call_sites"],
                "definition": [r for r in refs if r["reference_kind"] == "definition"],
                "import": [r for r in refs if r["reference_kind"] == "import"],
                "mention": [r for r in refs if r["reference_kind"] == "mention"],
                "docs": [r for r in refs if r["reference_kind"] == "docs"],
                "tests": [r for r in refs if r["reference_kind"] == "tests"],
                "other": [r for r in refs if r["reference_kind"] == "other"],
            }
            if languages == ["python"] and ref_methods.issubset({"ast", "text"}):
                return server_impl._response(
                    "ok",
                    {
                        "symbol": symbol,
                        "language": "python",
                        "count": len(refs),
                        "matched_count": matched_count,
                        "total_count": sum(all_counts.values()),
                        "counts": returned_counts,
                        "matched_counts": matched_counts,
                        "all_counts": all_counts,
                        "detail_counts": detail_returned_counts,
                        "detail_matched_counts": detail_filtered_counts,
                        "detail_all_counts": detail_all_counts,
                        "references": refs,
                        "buckets": broad_buckets,
                        "detail_buckets": detail_buckets,
                        "method": "ast",
                        "supported_languages": sorted(server_impl._SUPPORTED_REFERENCE_LANGS),
                        "exclude_tests": exclude_tests,
                        "exclude_docs": exclude_docs,
                        "call_sites_only": call_sites_only,
                        "limit": limit,
                        **({"note": note} if note else {}),
                    },
                    next_tools=["code_read"],
                    usage=f"code_read(path='...', start_line=N, end_line=N+20)",
                )
            if all(str(m).startswith("treesitter") for m in ref_methods):
                method = "treesitter"
            elif ref_methods == {"text"}:
                method = "text"
            return server_impl._response(
                "ok",
                {
                    "symbol": symbol,
                    "count": len(refs),
                    "matched_count": matched_count,
                    "total_count": sum(all_counts.values()),
                    "counts": returned_counts,
                    "matched_counts": matched_counts,
                    "all_counts": all_counts,
                    "detail_counts": detail_returned_counts,
                    "detail_matched_counts": detail_filtered_counts,
                    "detail_all_counts": detail_all_counts,
                    "references": refs,
                    "buckets": broad_buckets,
                    "detail_buckets": detail_buckets,
                    "method": method,
                    "supported_languages": sorted(server_impl._SUPPORTED_REFERENCE_LANGS),
                    "languages": languages,
                    **({"note": note} if note else {}),
                    "exclude_tests": exclude_tests,
                    "exclude_docs": exclude_docs,
                    "call_sites_only": call_sites_only,
                    "limit": limit,
                },
                next_tools=["code_read"],
                usage=f"code_read(path='...', start_line=N, end_line=N+20)",
            )
    fallback_symbol = retry_symbol or symbol
    # No known-language references — run broad keyword fallback across all files.
    try:
        fallback = _keyword_fallback_definitions(root, fallback_symbol)
    except Exception as exc:
        return server_impl._response("error", {"symbol": symbol}, diagnostics=[server_impl._diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    if not fallback:
        return server_impl._response(
            "ok",
            {"symbol": symbol, "references": [], "count": 0, "method": "keyword_fallback"},
            diagnostics=[server_impl._diagnostic("not_found", f"No references found for '{symbol}'.", recovery_tools=["code_keyword"], recovery_usage=f"code_keyword(query={symbol!r})")],
            next_tools=["code_keyword"],
            usage=f"code_keyword(query={symbol!r})",
        )
    fallback_total = len(fallback)
    fallback, fallback_counts, fallback_all_counts, fallback_detail_counts, fallback_detail_all_counts = _apply_reference_filters(
        fallback,
        exclude_tests=exclude_tests,
        exclude_docs=exclude_docs,
        call_sites_only=call_sites_only,
    )
    fallback_matched_count = len(fallback)
    fallback_matched_counts = dict(fallback_counts)
    if limit is not None and limit > 0:
        fallback = fallback[:limit]
    fallback_returned_counts = _reference_counts(fallback)
    fallback_detail_returned_counts = _reference_detail_counts(fallback)
    fallback_buckets = {
        "call_sites": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
        "other": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "other"],
        "docs": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "docs"],
        "tests": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "tests"],
    }
    fallback_detail_buckets = {
        "call_sites": [r for r in fallback if r["reference_kind"] == "call_sites"],
        "definition": [r for r in fallback if r["reference_kind"] == "definition"],
        "import": [r for r in fallback if r["reference_kind"] == "import"],
        "mention": [r for r in fallback if r["reference_kind"] == "mention"],
        "docs": [r for r in fallback if r["reference_kind"] == "docs"],
        "tests": [r for r in fallback if r["reference_kind"] == "tests"],
        "other": [r for r in fallback if r["reference_kind"] == "other"],
    }
    return server_impl._response(
        "ok",
        {
            "symbol": symbol,
            "references": fallback,
            "count": len(fallback),
            "matched_count": fallback_matched_count,
            "total_count": fallback_total,
            "counts": fallback_returned_counts,
            "matched_counts": fallback_matched_counts,
            "all_counts": fallback_all_counts,
            "detail_counts": fallback_detail_returned_counts,
            "detail_matched_counts": fallback_detail_counts,
            "detail_all_counts": fallback_detail_all_counts,
            "buckets": fallback_buckets,
            "detail_buckets": fallback_detail_buckets,
            "method": "keyword_fallback",
            "exclude_tests": exclude_tests,
            "exclude_docs": exclude_docs,
            "call_sites_only": call_sites_only,
            "limit": limit,
            "note": "No known-language reference search found a result. Returning broad keyword matches across the repo.",
        },
        next_tools=["code_read"],
        usage=f"code_read(path='...', start_line=N, end_line=N+20)",
    )

def code_dependencies_response(root: Path, path: str) -> dict[str, Any]:
    """Return imported modules/files for a given repo-relative path, parsed on demand."""
    from wf_server import server_impl
    rel = path.strip().replace("\\", "/")
    if not rel:
        return server_impl._response("error", {"path": rel}, diagnostics=[server_impl._diagnostic("invalid_arguments", "path must be a non-empty repo-relative file path.")], next_tools=["code_list_files"], usage="code_list_files()")
    abs_path = server_impl._resolve_repo_path(root, rel)
    if abs_path is None:
        return server_impl._response("error", {"path": rel}, diagnostics=[server_impl._diagnostic("invalid_arguments", "path escapes the repository root or is absolute.")], next_tools=["code_list_files"], usage="code_list_files()")
    try:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return server_impl._response("error", {"path": rel}, diagnostics=[server_impl._diagnostic("file_not_found", f"File not found: {rel}")], next_tools=["code_list_files"], usage="code_list_files()")
    except OSError as exc:
        return server_impl._response("error", {"path": rel}, diagnostics=[server_impl._diagnostic("read_error", str(exc))], next_tools=[], usage="")

    suffix = Path(rel).suffix.lower()
    if suffix == ".py":
        lang = "python"
    elif suffix in server_impl._JS_TS_SUFFIXES:
        lang = server_impl._EXT_TO_LANG.get(suffix, "javascript")
    else:
        lang = server_impl._EXT_TO_LANG.get(suffix, "")

    parser_entry = server_impl._IMPORT_PARSERS.get(lang)
    if not parser_entry:
        return server_impl._response("ok", {"path": rel, "imports": [], "method": "unsupported"}, next_tools=[], usage="")

    parser_fn, method = parser_entry
    imports = parser_fn(source)
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped = []
    for entry in imports:
        mod = entry["module"]
        if mod not in seen:
            seen.add(mod)
            deduped.append(entry)

    return server_impl._response(
        "ok",
        {"path": rel, "imports": deduped, "method": method},
        next_tools=["code_read"],
        usage=f"code_read(path={rel!r})",
    )

def _graph_references_candidate_files(root: Path, symbol: str) -> frozenset[str] | None:
    """Return files the graph says reference symbol, or None if graph unavailable/empty."""
    from wf_server import server_impl
    try:
        gq = server_impl._load_graph_query()
        index = gq.get_query_index(root, layer="project")
        if not index.present:
            return None
        node_id = index.resolve_symbol(symbol)
        if node_id is None:
            return None
        files: set[str] = set()
        for edge in index._in.get(node_id, []):
            src = edge.get("source")
            if not isinstance(src, str) or src.startswith("external::"):
                continue
            src_node = index.get_node(src)
            if src_node:
                sf = src_node.get("source_file")
                if isinstance(sf, str) and sf:
                    files.add(sf)
            elif "::" in src:
                files.add(src.split("::")[0])
            else:
                files.add(src)
        return frozenset(files) if files else None
    except Exception:
        return None

def code_commit_provenance_response(
    root: Path,
    commit: str = "",
    path: str = "",
    line_start: int = 0,
    line_end: int = 0,
) -> dict[str, Any]:
    """Reverse provenance: a commit SHA (or file + line range) -> the wave(s)
    that produced it and their recorded reasoning. Local, read-only, honest on
    absence and on message/evidence conflict (both reported, never reconciled)."""
    from wf_server import server_impl
    cp = server_impl._load_script("commit_provenance")
    commit = (commit or "").strip()
    path = (path or "").strip()
    if bool(commit) == bool(path):
        return server_impl._response(
            "error", {"resolved": False, "waves": [], "provenance": []},
            diagnostics=[server_impl._diagnostic(
                "invalid_arguments",
                "Provide exactly one input mode: commit SHA, or file path with a line range.",
                recovery_tools=["code_commit_provenance"],
                recovery_usage="code_commit_provenance(commit='<sha>') or code_commit_provenance(path='<file>', line_start=N, line_end=M)")],
            next_tools=["code_commit_provenance"], usage="")
    if commit:
        if not cp.is_valid_sha(commit):
            return server_impl._response(
                "error", {"resolved": False, "waves": [], "provenance": []},
                diagnostics=[server_impl._diagnostic(
                    "invalid_arguments", "commit must be a 7-40 character hexadecimal SHA",
                    recovery_tools=["code_commit_provenance"],
                    recovery_usage="code_commit_provenance(commit='<sha>')")],
                next_tools=["code_commit_provenance"], usage="")
        data = cp.provenance_for_sha(root, commit)
    else:
        try:
            start = int(line_start)
            end = int(line_end or start)
        except (TypeError, ValueError):
            start = 0
            end = -1
        if start < 1 or end < start:
            return server_impl._response(
                "error", {"resolved": False, "waves": [], "provenance": []},
                diagnostics=[server_impl._diagnostic(
                    "invalid_arguments", "line range must satisfy 1 <= line_start <= line_end",
                    recovery_tools=["code_commit_provenance"],
                    recovery_usage="code_commit_provenance(path='<file>', line_start=N, line_end=M)")],
                next_tools=["code_commit_provenance"], usage="")
        data = cp.provenance_for_line(root, path, start, end)
    diagnostics = []
    # Per-call activity signal (not a token target): the atom that a
    # resolution_hit_rate / honest_absence_rate aggregates over. Honest, derived
    # only from what this call actually resolved.
    if data.get("conflict"):
        data["resolution"] = "conflict"
    elif data.get("partial"):
        data["resolution"] = "partial"
    elif not data.get("resolved"):
        data["resolution"] = "honest_absence"
    else:
        data["resolution"] = "resolved"
    if data.get("partial"):
        diagnostics.append(server_impl._diagnostic(
            "partial_provenance",
            "The requested range includes uncommitted lines; committed provenance is "
            "reported with explicit coverage and is not presented as complete.",
            recovery_tools=["code_commit_provenance"], recovery_usage=""))
    if not data.get("resolved") and not data.get("partial"):
        diagnostics.append(server_impl._diagnostic(
            "no_wave_provenance",
            "No wave provenance found for this commit/line — it may predate the "
            "framework, be a non-conventional commit, or have been rebased/squashed. "
            "Reported honestly, not guessed.",
            recovery_tools=["code_commit_provenance"], recovery_usage=""))
    if data.get("conflict"):
        diagnostics.append(server_impl._diagnostic(
            "provenance_conflict",
            "The commit-message and evidence-search paths named different waves; "
            "both are reported, not reconciled.",
            recovery_tools=["code_commit_provenance"], recovery_usage=""))
    return server_impl._response(
        "ok", data, diagnostics=diagnostics,
        next_tools=["wf_get_change", "code_read"],
        usage="wf_get_change(change_id=...)")
